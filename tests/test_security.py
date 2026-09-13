from datetime import datetime, timedelta, timezone

import jwt
import pytest
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidSignatureError,
)

from app.config import settings
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_return_plaintext():
    plain_password = "example-password"
    hashed_password = hash_password(plain_password)
    assert hashed_password != plain_password


def test_verify_password_accepts_correct_password():
    plain_password = "example-password"
    hashed_password = hash_password(plain_password)
    assert verify_password(plain_password, hashed_password) is True


def test_verify_password_rejects_incorrect_password():
    plain_password = "example-password"
    hashed_password = hash_password(plain_password)
    assert verify_password("false-password", hashed_password) is False


def test_create_access_token_contains_string_subject_and_expiration():
    user_id = 123
    token = create_access_token(user_id)
    decoded_payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert decoded_payload["sub"] == "123"
    assert "exp" in decoded_payload


def test_decode_access_token_returns_subject():
    user_id = 123
    token = create_access_token(user_id)
    sub = decode_access_token(token)

    assert sub == "123"


def test_decode_access_token_rejects_token_signed_with_wrong_key():
    payload = {
        "sub": "123",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }

    wrong_key = "this-is-a-wrong-key-used-to-test"

    wrong_token = jwt.encode(
        payload,
        wrong_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidSignatureError):
        decode_access_token(wrong_token)


def test_decode_access_token_rejects_expired_token():
    payload = {
        "sub": "123",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }

    expired_token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(ExpiredSignatureError):
        decode_access_token(expired_token)
