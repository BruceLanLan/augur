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
