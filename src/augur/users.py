# -*- coding: utf-8 -*-
"""
augur.users - Multi-User Support with SQLite Storage

Provides user registration, authentication, and JWT-like session management.
Gated behind AUGUR_MULTI_USER environment variable.

Architecture:
    - UserManager: SQLite-backed CRUD for user accounts
    - JWT-like tokens: base64 + HMAC-SHA256 (no PyJWT dependency)
    - PBKDF2 password hashing with 100k iterations (no bcrypt dependency)

Security:
    - JWT secret persists to ~/.augur/jwt_secret (survives restarts)
    - Passwords stored as PBKDF2-HMAC-SHA256 with random salt
    - Token expiry set to 7 days
    - Constant-time comparison for password and signature verification

Error Handling:
    - SQLite lock timeout: 10-second timeout on all connections
    - Database corruption: auto-recreates database schema
    - IntegrityError: returns None for duplicate usernames

Configuration:
    - AUGUR_MULTI_USER=1: Enable multi-user mode
    - AUGUR_JWT_SECRET: Override JWT secret (optional, auto-generates otherwise)

Usage:
    from augur.users import UserManager, is_multi_user_enabled
    if is_multi_user_enabled():
        manager = UserManager()
        user = manager.create_user("alice", "password123")
        token = manager.authenticate("alice", "password123")
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


# JWT secret - require from env or persist to disk (survives restarts)
_JWT_EXPIRY = 86400 * 7  # 7 days
_PBKDF2_ITERATIONS = 100_000


def _get_jwt_secret() -> str:
    """Get the JWT secret from env var or persisted file.

    Priority: AUGUR_JWT_SECRET env var > ~/.augur/jwt_secret file > generate and persist.
    """
    env_secret = os.environ.get("AUGUR_JWT_SECRET")
    if env_secret:
        return env_secret

    secret_path = Path.home() / ".augur" / "jwt_secret"
    if secret_path.exists():
        return secret_path.read_text(encoding="utf-8").strip()

    # Generate and persist a new secret
    new_secret = secrets.token_hex(32)
    secret_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    secret_path.write_text(new_secret, encoding="utf-8")
    try:
        secret_path.chmod(0o600)
    except OSError:
        pass
    return new_secret


_JWT_SECRET = _get_jwt_secret()


def is_multi_user_enabled() -> bool:
    """Check if multi-user mode is enabled via AUGUR_MULTI_USER env var."""
    return os.environ.get("AUGUR_MULTI_USER", "").lower() in ("1", "true", "yes")


def _get_db_path() -> Path:
    """Get the SQLite database path."""
    augur_dir = Path.home() / ".augur"
    augur_dir.mkdir(parents=True, exist_ok=True)
    return augur_dir / "users.db"


def _hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with 100k iterations.

    Args:
        password: The plaintext password.
        salt: Optional hex-encoded salt. If None, generates a random one.

    Returns:
        Tuple of (password_hash, salt).
    """
    if salt is None:
        salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    ).hex()
    return password_hash, salt


def _verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verify a password against its hash."""
    computed_hash, _ = _hash_password(password, salt)
    return hmac.compare_digest(computed_hash, password_hash)


def _create_token(payload: Dict[str, Any]) -> str:
    """
    Create a JWT-like token using base64 + HMAC-SHA256.

    Token format: base64(header).base64(payload).base64(signature)
    """
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header).encode()
    ).rstrip(b"=").decode()

    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()

    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        _JWT_SECRET.encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT-like token.

    Returns payload dict if valid, None if invalid or expired.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts

        # Reject unexpected algorithms (e.g. alg=none)
        padding = 4 - len(header_b64) % 4
        if padding != 4:
            header_b64_padded = header_b64 + "=" * padding
        else:
            header_b64_padded = header_b64
        header = json.loads(base64.urlsafe_b64decode(header_b64_padded))
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            return None

        # Verify signature
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            _JWT_SECRET.encode(),
            signing_input.encode(),
            hashlib.sha256,
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode()

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None

        # Decode payload - add padding back
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes)

        # Check expiry
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


class UserManager:
    """
    SQLite-backed user management system.

    Provides user CRUD operations with password hashing and JWT sessions.
    """

    def __init__(self, db_path: Path = None):
        """
        Initialize UserManager.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.augur/users.db.
        """
        self.db_path = db_path or _get_db_path()
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        created_at REAL NOT NULL
                    )
                """)
                conn.commit()
            finally:
                conn.close()
        except sqlite3.DatabaseError:
            # Handle corruption: remove and recreate
            if self.db_path.exists():
                self.db_path.unlink()
            conn = sqlite3.connect(str(self.db_path), timeout=10)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        created_at REAL NOT NULL
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def create_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Create a new user.

        Args:
            username: Unique username (3-32 chars, alphanumeric + underscore).
            password: Password (minimum 6 characters).

        Returns:
            User dict with id, username, created_at, or None if username exists.
        """
        if not username or not _USERNAME_RE.match(username):
            return None
        if not password or len(password) < 6:
            return None

        password_hash, salt = _hash_password(password)
        created_at = time.time()

        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10)
            try:
                conn.execute(
                    "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
                    (username, password_hash, salt, created_at),
                )
                conn.commit()
                user_id = conn.execute(
                    "SELECT id FROM users WHERE username = ?", (username,)
                ).fetchone()[0]
                return {
                    "id": user_id,
                    "username": username,
                    "created_at": created_at,
                }
            except sqlite3.IntegrityError:
                return None
            finally:
                conn.close()
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            # Handle lock timeout or corruption
            return None

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate a user and return a JWT token.

        Args:
            username: The username.
            password: The password.

        Returns:
            JWT token string if authentication succeeds, None otherwise.
        """
        if not username or not _USERNAME_RE.match(username):
            return None
        if not password:
            return None

        conn = sqlite3.connect(str(self.db_path), timeout=10)
        try:
            row = conn.execute(
                "SELECT id, password_hash, salt FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not row:
                return None

            user_id, stored_hash, salt = row
            if not _verify_password(password, stored_hash, salt):
                return None

            payload = {
                "user_id": user_id,
                "username": username,
                "iat": time.time(),
                "exp": time.time() + _JWT_EXPIRY,
            }
            return _create_token(payload)
        finally:
            conn.close()

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        try:
            row = conn.execute(
                "SELECT id, username, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "username": row[1],
                "created_at": row[2],
            }
        finally:
            conn.close()

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        try:
            row = conn.execute(
                "SELECT id, username, created_at FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "username": row[1],
                "created_at": row[2],
            }
        finally:
            conn.close()

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a JWT token and return the payload.

        Returns:
            Decoded payload dict if valid, None otherwise.
        """
        return _decode_token(token)

    def user_count(self) -> int:
        """Get total user count."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        try:
            row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
