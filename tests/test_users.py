# -*- coding: utf-8 -*-
"""Tests for augur.users - Multi-User Support"""

import os
import tempfile
import pytest
from pathlib import Path

from augur.users import (
    UserManager,
    is_multi_user_enabled,
    _hash_password,
    _verify_password,
    _create_token,
    _decode_token,
)


@pytest.fixture
def user_manager(tmp_path):
    """Create a UserManager with a temporary database."""
    db_path = tmp_path / "test_users.db"
    return UserManager(db_path=db_path)


def test_is_multi_user_disabled_by_default():
    """Test that multi-user is disabled when env var is not set."""
    os.environ.pop("AUGUR_MULTI_USER", None)
    assert is_multi_user_enabled() is False


def test_is_multi_user_enabled():
    """Test that multi-user can be enabled via env var."""
    os.environ["AUGUR_MULTI_USER"] = "1"
    try:
        assert is_multi_user_enabled() is True
    finally:
        del os.environ["AUGUR_MULTI_USER"]


def test_hash_password():
    """Test password hashing produces consistent results with same salt."""
    hash1, salt1 = _hash_password("mypassword")
    hash2, _ = _hash_password("mypassword", salt1)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest


def test_hash_password_different_salts():
    """Test that different salts produce different hashes."""
    hash1, salt1 = _hash_password("mypassword")
    hash2, salt2 = _hash_password("mypassword")
    assert salt1 != salt2
    assert hash1 != hash2


def test_verify_password():
    """Test password verification."""
    hash_val, salt = _hash_password("correct_password")
    assert _verify_password("correct_password", hash_val, salt) is True
    assert _verify_password("wrong_password", hash_val, salt) is False


def test_create_user(user_manager):
    """Test creating a new user."""
    user = user_manager.create_user("testuser", "password123")
    assert user is not None
    assert user["username"] == "testuser"
    assert user["id"] == 1
    assert "created_at" in user


def test_create_user_duplicate(user_manager):
    """Test that duplicate usernames are rejected."""
    user_manager.create_user("testuser", "password123")
    result = user_manager.create_user("testuser", "differentpass")
    assert result is None


def test_create_user_invalid_username(user_manager):
    """Test that short/invalid usernames are rejected."""
    assert user_manager.create_user("ab", "password123") is None  # too short
    assert user_manager.create_user("", "password123") is None  # empty


def test_create_user_invalid_password(user_manager):
    """Test that short passwords are rejected."""
    assert user_manager.create_user("testuser", "12345") is None  # too short
    assert user_manager.create_user("testuser", "") is None  # empty


def test_authenticate_success(user_manager):
    """Test successful authentication returns a token."""
    user_manager.create_user("testuser", "password123")
    token = user_manager.authenticate("testuser", "password123")
    assert token is not None
    assert len(token) > 10
    assert "." in token


def test_authenticate_wrong_password(user_manager):
    """Test that wrong password returns None."""
    user_manager.create_user("testuser", "password123")
    token = user_manager.authenticate("testuser", "wrong_password")
    assert token is None


def test_authenticate_nonexistent_user(user_manager):
    """Test that nonexistent user returns None."""
    token = user_manager.authenticate("nouser", "password123")
    assert token is None


def test_verify_token(user_manager):
    """Test token verification."""
    user_manager.create_user("testuser", "password123")
    token = user_manager.authenticate("testuser", "password123")
    payload = user_manager.verify_token(token)
    assert payload is not None
    assert payload["username"] == "testuser"
    assert payload["user_id"] == 1


def test_verify_invalid_token(user_manager):
    """Test that invalid tokens are rejected."""
    assert user_manager.verify_token("invalid.token.here") is None
    assert user_manager.verify_token("") is None
    assert user_manager.verify_token("not-a-jwt") is None


def test_user_count(user_manager):
    """Test user count tracking."""
    assert user_manager.user_count() == 0
    user_manager.create_user("user1", "password123")
    assert user_manager.user_count() == 1
    user_manager.create_user("user2", "password123")
    assert user_manager.user_count() == 2


def test_get_user(user_manager):
    """Test getting user by ID."""
    user_manager.create_user("testuser", "password123")
    user = user_manager.get_user(1)
    assert user is not None
    assert user["username"] == "testuser"


def test_get_user_not_found(user_manager):
    """Test getting nonexistent user."""
    assert user_manager.get_user(999) is None


# ---------------------------------------------------------------------------
# Round 3 additions — focused coverage for users.py (v8)
# ---------------------------------------------------------------------------


def test_password_hash_not_stored_as_plaintext(user_manager):
    """Passwords must be stored as PBKDF2 hashes, never plaintext on disk."""
    import sqlite3
    plaintext = "supersecret123"
    user = user_manager.create_user("hashcheck", plaintext)
    assert user is not None

    conn = sqlite3.connect(str(user_manager.db_path))
    try:
        row = conn.execute(
            "SELECT password_hash, salt FROM users WHERE username = ?",
            ("hashcheck",),
        ).fetchone()
    finally:
        conn.close()

    stored_hash, salt = row
    assert plaintext not in stored_hash
    assert plaintext.encode().hex() != stored_hash
    # PBKDF2-SHA256 produces 64 hex chars
    assert len(stored_hash) == 64
    assert len(salt) == 32  # 16 random bytes hex-encoded
    # The hash must verify against the plaintext
    assert _verify_password(plaintext, stored_hash, salt) is True


def test_get_user_by_username(user_manager):
    """Lookup by username returns the same record as lookup by id."""
    user_manager.create_user("alice", "password123")
    user_manager.create_user("bob", "password456")

    alice = user_manager.get_user_by_username("alice")
    assert alice is not None
    assert alice["username"] == "alice"
    assert "id" in alice and "created_at" in alice

    # Round-trip: username lookup matches id lookup
    by_id = user_manager.get_user(alice["id"])
    assert by_id == alice

    # Nonexistent username
    assert user_manager.get_user_by_username("ghost") is None


def test_user_deletion_via_schema(user_manager, tmp_path):
    """A user row removed via SQL is no longer findable / authenticatable.

    The public API does not expose a delete_user method, but the schema must
    support removal (e.g. for GDPR / account-closure flows) and the manager
    must immediately reflect the deletion in lookups, authentication, and
    user_count.
    """
    import sqlite3

    user = user_manager.create_user("todelete", "password123")
    assert user is not None
    assert user_manager.user_count() == 1
    assert user_manager.get_user(user["id"]) is not None
    assert user_manager.authenticate("todelete", "password123") is not None

    # Remove the row directly to simulate an admin / cleanup path
    conn = sqlite3.connect(str(user_manager.db_path))
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
        conn.commit()
    finally:
        conn.close()

    assert user_manager.user_count() == 0
    assert user_manager.get_user(user["id"]) is None
    assert user_manager.get_user_by_username("todelete") is None
    assert user_manager.authenticate("todelete", "password123") is None


def test_tampered_token_rejected(user_manager):
    """Mutating any segment of a valid token invalidates the signature."""
    user_manager.create_user("tamper", "password123")
    token = user_manager.authenticate("tamper", "password123")
    assert token is not None

    header, payload, sig = token.split(".")
    # Flip a byte in the signature
    flipped = "A" if sig[0] != "A" else "B"
    bad_sig = flipped + sig[1:]
    assert user_manager.verify_token(f"{header}.{payload}.{bad_sig}") is None

    # Mutate the payload (e.g. escalate user_id) — signature no longer matches
    assert user_manager.verify_token(f"{header}.{payload}AAAA.{sig}") is None

    # Drop a segment entirely
    assert user_manager.verify_token(f"{header}.{payload}") is None


def test_token_rejected_with_different_secret(user_manager, monkeypatch):
    """A token signed with a different JWT secret must be rejected."""
    user_manager.create_user("secuser", "password123")
    token = user_manager.authenticate("secuser", "password123")

    # Force the module to use a different secret and re-decode
    import augur.users as users_mod

    monkeypatch.setattr(users_mod, "_JWT_SECRET", "totally-different-secret-xyz")
    assert users_mod._decode_token(token) is None
    # The manager's verify_token routes through the same private decoder
    assert user_manager.verify_token(token) is None


def test_token_expiry_marks_payload_invalid(user_manager, monkeypatch):
    """A token whose exp is in the past must be rejected."""
    import time as _time
    import augur.users as users_mod

    payload = {
        "user_id": 1,
        "username": "expired",
        "iat": _time.time() - 7200,
        "exp": _time.time() - 3600,  # expired one hour ago
    }
    token = users_mod._create_token(payload)
    assert users_mod._decode_token(token) is None
    assert user_manager.verify_token(token) is None

    # Sanity: a freshly-issued token still decodes
    user_manager.create_user("expired", "password123")
    fresh = user_manager.authenticate("expired", "password123")
    assert users_mod._decode_token(fresh) is not None
