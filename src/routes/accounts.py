from datetime import datetime, timezone
from typing import cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    status,
)
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config import (
    BaseAppSettings,
    get_accounts_email_notificator,
    get_jwt_auth_manager,
    get_settings,
)
from config.settings import API_VERSION_PREFIX, BASE_URL
from database import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
    get_db,
)
from exceptions import BaseSecurityError
from notifications import EmailSenderInterface
from schemas import (
    ChangePasswordRequestSchema,
    EmailRequestSchema,
    MessageResponseSchema,
    PasswordResetCompleteRequestSchema,
    PasswordResetRequestSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
    UserActivationRequestSchema,
    UserLoginRequestSchema,
    UserLoginResponseSchema,
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
)
from security.interfaces import JWTAuthManagerInterface
from utils import get_current_user

router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    description="Register a new user with an email and password.",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "description": "Conflict - User with this email already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A user with this email test@example.com already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred during user creation.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred during user creation."
                    }
                }
            },
        },
    },
)
async def register_user(
    background_tasks: BackgroundTasks,
    user_data: UserRegistrationRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> UserRegistrationResponseSchema:
    """
    Registers a new user, hashes their password, and assigns them to the default user group.
    If a user with the same email already exists, an HTTP 409 error is raised.
    In case of any unexpected issues during the creation process, an HTTP 500 error is returned.
    """
    stmt = select(UserModel).where(UserModel.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists.",
        )

    stmt = select(UserGroupModel).where(
        UserGroupModel.name == UserGroupEnum.USER
    )
    result = await db.execute(stmt)
    user_group = result.scalars().first()
    if not user_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found.",
        )

    try:
        new_user = UserModel.create(
            email=str(user_data.email),
            raw_password=user_data.password,
            group_id=user_group.id,
        )
        db.add(new_user)
        await db.flush()

        activation_token = ActivationTokenModel(user_id=new_user.id)
        db.add(activation_token)

        await db.commit()
        await db.refresh(new_user)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation.",
        ) from e
    else:
        activation_link = f"{BASE_URL}{API_VERSION_PREFIX}/accounts/activate/?token={activation_token.token}&email={new_user.email}"
        background_tasks.add_task(
            email_sender.send_activation_email, new_user.email, activation_link
        )

        return UserRegistrationResponseSchema.model_validate(new_user)


@router.post(
    "/resend-activation/",
    response_model=MessageResponseSchema,
    summary="Resend Activation Email",
    description="Send a new activation email if the previous activation token expired.",
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Not Found - User with this email does not exist.",
            "content": {
                "application/json": {"example": {"detail": "User not found."}}
            },
        },
    },
)
async def resend_activation_email(
    background_tasks: BackgroundTasks,
    email_data: EmailRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> MessageResponseSchema:
    """
    Checks if the user exists and is not already active.
    Deletes any existing activation tokens for the user,
    creates a new activation token with a 24-hour expiry,
    and sends an activation email.
    """
    stmt = select(UserModel).where(UserModel.email == email_data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    if user.is_active:
        return MessageResponseSchema(message="User account is already active.")

    stmt = select(ActivationTokenModel).where(
        ActivationTokenModel.user_id == user.id
    )
    result = await db.execute(stmt)
    old_tokens = result.scalars().all()
    for token in old_tokens:
        await db.delete(token)

    new_token = ActivationTokenModel(user_id=user.id)
    db.add(new_token)
    await db.commit()

    activation_link = f"{BASE_URL}{API_VERSION_PREFIX}/accounts/activate/?token={new_token.token}&email={user.email}"
    background_tasks.add_task(
        email_sender.send_activation_email, user.email, activation_link
    )

    return MessageResponseSchema(
        message="A new activation email has been sent."
    )


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
    summary="Activate User Account",
    description="Activate a user's account using their email and activation token.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - The activation token is invalid or expired, "
            "or the user account is already active.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid or expired activation token."
                            },
                        },
                        "already_active": {
                            "summary": "Account Already Active",
                            "value": {
                                "detail": "User account is already active."
                            },
                        },
                    }
                }
            },
        },
    },
)
async def activate_account(
    background_tasks: BackgroundTasks,
    activation_data: UserActivationRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> MessageResponseSchema:
    """
    This endpoint verifies the activation token for a user by checking that the token record exists
    and that it has not expired. If the token is valid and the user's account is not already active,
    the user's account is activated and the activation token is deleted. If the token is invalid, expired,
    or if the account is already active, an HTTP 400 error is raised.
    """
    stmt = (
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .join(UserModel)
        .where(
            UserModel.email == activation_data.email,
            ActivationTokenModel.token == activation_data.token,
        )
    )
    result = await db.execute(stmt)
    token_record = result.scalars().first()

    now_utc = datetime.now(timezone.utc)
    if (
        not token_record
        or cast(datetime, token_record.expires_at).replace(tzinfo=timezone.utc)
        < now_utc
    ):
        if token_record:
            await db.delete(token_record)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token.",
        )

    user = token_record.user
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active.",
        )

    user.is_active = True
    await db.delete(token_record)
    await db.commit()

    login_link = f"{BASE_URL}{API_VERSION_PREFIX}/accounts/login/"
    background_tasks.add_task(
        email_sender.send_activation_complete_email,
        str(activation_data.email),
        login_link,
    )

    return MessageResponseSchema(
        message="User account activated successfully."
    )


@router.post(
    "/change-password/",
    response_model=MessageResponseSchema,
    summary="Change Password",
    description="Change password by providing old and new passwords.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - Old password is incorrect or validation failed.",
            "content": {
                "application/json": {
                    "example": {"detail": "Old password is incorrect."}
                }
            },
        },
        401: {
            "description": "Unauthorized - User not authenticated.",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated."}
                }
            },
        },
        500: {
            "description": "Internal Server Error - Error during password change.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while changing the password."
                    }
                }
            },
        },
    },
)
async def change_password(
    data: ChangePasswordRequestSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    """
    Change password endpoint with old password.
    """
    if not current_user.verify_password(data.old_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect.",
        )

    try:
        current_user.password = data.new_password
        await db.flush()
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while changing the password.",
        )

    return MessageResponseSchema(message="Password changed successfully.")


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseSchema,
    summary="Request Password Reset Token",
    description=(
        "Allows a user to request a password reset token. If the user exists and is active, "
        "a new token will be generated and any existing tokens will be invalidated."
    ),
    status_code=status.HTTP_200_OK,
)
async def request_password_reset_token(
    background_tasks: BackgroundTasks,
    data: PasswordResetRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> MessageResponseSchema:
    """
    If the user exists and is active, invalidates any existing password reset tokens and generates a new one.
    Always responds with a success message to avoid leaking user information.
    """
    stmt = select(UserModel).filter_by(email=data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.is_active:
        return MessageResponseSchema(
            message="If you are registered, you will receive an email with instructions."
        )

    await db.execute(
        delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )

    reset_token = PasswordResetTokenModel(user_id=cast(int, user.id))
    db.add(reset_token)
    await db.commit()

    password_reset_complete_link = f"{BASE_URL}{API_VERSION_PREFIX}/accounts/password-reset-complete/?token={reset_token.token}"
    background_tasks.add_task(
        email_sender.send_password_reset_email,
        str(data.email),
        password_reset_complete_link,
    )

    return MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )


@router.post(
    "/reset-password/complete/",
    response_model=MessageResponseSchema,
    summary="Reset User Password",
    description="Reset a user's password if a valid token is provided.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": (
                "Bad Request - The provided email or token is invalid, "
                "the token has expired, or the user account is not active."
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_email_or_token": {
                            "summary": "Invalid Email or Token",
                            "value": {"detail": "Invalid email or token."},
                        },
                        "expired_token": {
                            "summary": "Expired Token",
                            "value": {"detail": "Invalid email or token."},
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while resetting the password.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while resetting the password."
                    }
                }
            },
        },
    },
)
async def reset_password(
    background_tasks: BackgroundTasks,
    data: PasswordResetCompleteRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> MessageResponseSchema:
    """
    Validates the token and updates the user's password if the token is valid and not expired.
    Deletes the token after a successful password reset.
    """
    stmt = select(UserModel).filter_by(email=data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token.",
        )

    stmt = select(PasswordResetTokenModel).filter_by(user_id=user.id)
    result = await db.execute(stmt)
    token_record = result.scalars().first()

    if not token_record or token_record.token != data.token:
        if token_record:
            await db.run_sync(lambda s: s.delete(token_record))
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token.",
        )

    expires_at = cast(datetime, token_record.expires_at).replace(
        tzinfo=timezone.utc
    )
    if expires_at < datetime.now(timezone.utc):
        await db.run_sync(lambda s: s.delete(token_record))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token.",
        )

    try:
        user.password = data.password
        await db.run_sync(lambda s: s.delete(token_record))
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password.",
        )

    login_link = f"{BASE_URL}{API_VERSION_PREFIX}/accounts/login/"
    background_tasks.add_task(
        email_sender.send_password_reset_complete_email,
        str(data.email),
        login_link,
    )

    return MessageResponseSchema(message="Password reset successfully.")


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
    summary="User Login",
    description="Authenticate a user and return access and refresh tokens.",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {
            "description": "Unauthorized - Invalid email or password.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid email or password."}
                }
            },
        },
        403: {
            "description": "Forbidden - User account is not activated.",
            "content": {
                "application/json": {
                    "example": {"detail": "User account is not activated."}
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while processing the request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while processing the request."
                    }
                }
            },
        },
    },
)
async def login_user(
    login_data: UserLoginRequestSchema,
    db: AsyncSession = Depends(get_db),
    settings: BaseAppSettings = Depends(get_settings),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> UserLoginResponseSchema:
    """
    Authenticates a user using their email and password.
    If authentication is successful, creates a new refresh token and returns both access and refresh tokens.
    """
    stmt = select(UserModel).filter_by(email=login_data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.verify_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    jwt_refresh_token = jwt_manager.create_refresh_token({"user_id": user.id})

    try:
        refresh_token = RefreshTokenModel.create(
            user_id=user.id,
            days_valid=settings.LOGIN_TIME_DAYS,
            token=jwt_refresh_token,
        )
        db.add(refresh_token)
        await db.flush()
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        )

    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})
    return UserLoginResponseSchema(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token,
    )


@router.post(
    "/logout/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User Logout",
    description="Logs out the user by invalidating the refresh token.",
    responses={
        401: {
            "description": "Unauthorized - Invalid or missing token.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or missing refresh token."}
                }
            },
        },
        500: {
            "description": "Internal Server Error - Error during logout process.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred during logout."}
                }
            },
        },
    },
)
async def logout_user(
    refresh_token: str = Header(
        ..., description="Refresh token to invalidate"
    ),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Logs out the user by deleting the refresh token from the database.
    """
    stmt = select(RefreshTokenModel).where(
        RefreshTokenModel.token == refresh_token
    )
    result = await db.execute(stmt)
    token_obj = result.scalars().first()

    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing refresh token.",
        )

    try:
        await db.delete(token_obj)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout.",
        )


@router.post(
    "/refresh/",
    response_model=TokenRefreshResponseSchema,
    summary="Refresh Access Token",
    description="Refresh the access token using a valid refresh token.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - The provided refresh token is invalid or expired.",
            "content": {
                "application/json": {
                    "example": {"detail": "Token has expired."}
                }
            },
        },
        401: {
            "description": "Unauthorized - Refresh token not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Refresh token not found."}
                }
            },
        },
        404: {
            "description": "Not Found - The user associated with the token does not exist.",
            "content": {
                "application/json": {"example": {"detail": "User not found."}}
            },
        },
    },
)
async def refresh_access_token(
    token_data: TokenRefreshRequestSchema,
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> TokenRefreshResponseSchema:
    """
    Validates the provided refresh token, extracts the user ID from it, and issues
    a new access token. If the token is invalid or expired, an error is returned.
    """
    try:
        decoded_token = jwt_manager.decode_refresh_token(
            token_data.refresh_token
        )
        user_id = decoded_token.get("user_id")
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    stmt = select(RefreshTokenModel).filter_by(token=token_data.refresh_token)
    result = await db.execute(stmt)
    refresh_token_record = result.scalars().first()
    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
        )

    stmt = select(UserModel).filter_by(id=user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    new_access_token = jwt_manager.create_access_token({"user_id": user_id})

    return TokenRefreshResponseSchema(access_token=new_access_token)
