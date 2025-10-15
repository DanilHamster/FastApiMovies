import pytest
from pydantic import ValidationError

from database import validators
from schemas.accounts import (
    BaseEmailPasswordSchema,
    ChangePasswordRequestSchema,
    MessageResponseSchema,
    PasswordResetCompleteRequestSchema,
    TokenRefreshResponseSchema,
    UserLoginResponseSchema,
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
)


def test_base_email_password_schema_valid(monkeypatch):
    def mock_validate_password_strength(password):
        return password

    monkeypatch.setattr(validators, "validate_password_strength", mock_validate_password_strength)

    schema = BaseEmailPasswordSchema(email="USER@Example.com", password="StrongPass123")
    assert schema.email == "user@example.com"
    assert schema.password == "StrongPass123"


def test_base_email_password_schema_invalid_email():
    with pytest.raises(ValidationError):
        BaseEmailPasswordSchema(email="invalid-email", password="StrongPass123")


def test_base_email_password_schema_weak_password(monkeypatch):
    def mock_validate_password_strength(password):
        raise ValueError("Password too weak")

    monkeypatch.setattr(validators, "validate_password_strength", mock_validate_password_strength)

    with pytest.raises(ValidationError):
        BaseEmailPasswordSchema(email="user@example.com", password="weak")


def test_user_registration_request_inherits_base(monkeypatch):
    def mock_validate_password_strength(password):
        return password

    monkeypatch.setattr(validators, "validate_password_strength", mock_validate_password_strength)

    schema = UserRegistrationRequestSchema(email="User@Example.com", password="GoodPass123")
    assert schema.email == "user@example.com"


def test_change_password_request_schema_valid(monkeypatch):
    def mock_validate_password_strength(password):
        return password

    monkeypatch.setattr(validators, "validate_password_strength", mock_validate_password_strength)

    schema = ChangePasswordRequestSchema(old_password="Old123", new_password="NewPass456")
    assert schema.new_password == "NewPass456"


def test_change_password_request_schema_invalid(monkeypatch):
    def mock_validate_password_strength(password):
        raise ValueError("Weak")

    monkeypatch.setattr(validators, "validate_password_strength", mock_validate_password_strength)

    with pytest.raises(ValidationError):
        ChangePasswordRequestSchema(old_password="Old", new_password="123")


def test_password_reset_complete_schema_valid(monkeypatch):
    def mock_validate_password_strength(password):
        return password

    monkeypatch.setattr(validators, "validate_password_strength", mock_validate_password_strength)

    schema = PasswordResetCompleteRequestSchema(
        email="test@Example.com",
        password="Pass12345",
        token="abc123"
    )
    assert schema.email == "test@example.com"
    assert schema.token == "abc123"


def test_user_login_response_schema():
    schema = UserLoginResponseSchema(access_token="a1", refresh_token="r1")
    assert schema.token_type == "bearer"
    assert schema.access_token == "a1"
    assert schema.refresh_token == "r1"


def test_user_registration_response_schema():
    schema = UserRegistrationResponseSchema(id=1, email="user@example.com")
    assert schema.id == 1
    assert schema.email == "user@example.com"


def test_message_response_schema():
    schema = MessageResponseSchema(message="Operation successful")
    assert schema.message == "Operation successful"


def test_token_refresh_response_schema():
    schema = TokenRefreshResponseSchema(access_token="newtoken123")
    assert schema.access_token == "newtoken123"
    assert schema.token_type == "bearer"
