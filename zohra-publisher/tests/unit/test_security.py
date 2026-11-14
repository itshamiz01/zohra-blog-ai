"""
Tests for security utilities — password hashing, JWT tokens, auth flow.
"""

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Password hashing/verification tests."""

    def test_hash_and_verify(self):
        plain = "my-secure-password"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_hash_is_not_plaintext(self):
        plain = "my-password"
        hashed = hash_password(plain)
        assert hashed != plain
        assert hashed.startswith("$2b$")

    def test_invalid_hash_returns_false(self):
        assert verify_password("any", "not-a-valid-hash") is False


class TestJWT:
    """JWT token tests."""

    def test_create_and_decode_token(self):
        token = create_access_token(subject="admin")
        payload = decode_access_token(token)
        assert payload["sub"] == "admin"
        assert "exp" in payload
        assert "jti" in payload

    def test_token_with_extra_claims(self):
        token = create_access_token(subject="admin", extra={"role": "admin"})
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_invalid_token_raises(self):
        with pytest.raises(JWTError):
            decode_access_token("invalid.token.here")

    def test_tampered_token_raises(self):
        token = create_access_token(subject="admin")
        # Tamper with the payload
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_access_token(tampered)
