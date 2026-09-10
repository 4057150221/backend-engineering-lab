from app.security import hash_password, verify_password


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