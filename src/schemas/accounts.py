from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from database import validators


class BaseEmailPasswordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validators.validate_password_strength(value)


class EmailRequestSchema(BaseModel):
    email: EmailStr


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class ChangePasswordRequestSchema(BaseModel):
    email: EmailStr
    old_password: str
    new_password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validators.validate_password_strength(value)


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetCompleteRequestSchema(BaseEmailPasswordSchema):
    token: str


class UserLoginRequestSchema(BaseEmailPasswordSchema):
    pass


class UserLoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRegistrationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr


class UserActivationRequestSchema(BaseModel):
    email: EmailStr
    token: str


class MessageResponseSchema(BaseModel):
    message: str


class TokenRefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
