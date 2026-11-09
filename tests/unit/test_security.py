import jwt

from app.config import get_settings
from app.utilities.security import create_access_token, encrypt_password, verify_password


def test_hash_is_not_plaintext():
    assert encrypt_password("secret123") != "secret123"


def test_verify_correct_password():
    hashed = encrypt_password("secret123")
    assert verify_password("secret123", hashed)


def test_verify_wrong_password():
    hashed = encrypt_password("secret123")
    assert not verify_password("wrong", hashed)


def test_token_contains_subject_and_role():
    token = create_access_token({"sub": "7", "role": "advisor"})
    payload = jwt.decode(token, get_settings().secret_key, algorithms=[get_settings().jwt_algorithm])
    assert payload["sub"] == "7"
    assert payload["role"] == "advisor"
    assert "exp" in payload