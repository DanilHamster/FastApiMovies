from datetime import datetime, timezone
from typing import cast

from fastapi import APIRouter, Depends, Header, HTTPException, status
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
from database import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    UserGroupEnum,
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
from utils import (
    DEFAULT_BASE_URL,
    activation_link,
    commit_or_500,
    delete_activation_tokens,
    get_current_user,
    get_user_by_email,
    get_user_group,
)

router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_data: UserRegistrationRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> UserRegistrationResponseSchema:
    """Register a new user and send activation email."""
    existing_user = await get_user_by_email(db, str(user_data.email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists.",
        )

    user_group = await get_user_group(db, UserGroupEnum.USER)
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

        token = ActivationTokenModel(user_id=new_user.id)
        db.add(token)

        await commit_or_500(db, "An error occurred during user creation.")
        await db.refresh(new_user)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation.",
        ) from e

    link = activation_link(token.token, new_user.email)
    await email_sender.send_activation_email(new_user.email, link)
    return UserRegistrationResponseSchema.model_validate(new_user)


@router.post("/resend-activation/", response_model=MessageResponseSchema)
async def resend_activation_email(
    email_data: EmailRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> MessageResponseSchema:
    """Resend account activation email."""
    user = await get_user_by_email(db, str(email_data.email))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if user.is_active:
        return MessageResponseSchema(message="User account is already active.")

    await delete_activation_tokens(db, user.id)
    new_token = ActivationTokenModel(user_id=user.id)
    db.add(new_token)
    await commit_or_500(db)
    link = activation_link(new_token.token, user.email)
    await email_sender.send_activation_email(user.email, link)
    return MessageResponseSchema(
        message="A new activation email has been sent."
    )


@router.post("/activate/", response_model=MessageResponseSchema)
async def activate_account(
    activation_data: UserActivationRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> MessageResponseSchema:
    """Activate user account with token."""
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
            await commit_or_500(db)
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
    await commit_or_500(db)

    login_link = f"{DEFAULT_BASE_URL}/login/"
    await email_sender.send_activation_complete_email(
        str(activation_data.email), login_link
    )
    return MessageResponseSchema(
        message="User account activated successfully."
    )


@router.post("/change-password/", response_model=MessageResponseSchema)
async def change_password(
    data: ChangePasswordRequestSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    """Change password for current user."""
    if not current_user.verify_password(data.old_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect.",
        )

    current_user.password = data.new_password
    await commit_or_500(db, "An error occurred while changing the password.")
    return MessageResponseSchema(message="Password changed successfully.")


@router.post("/password-reset/request/", response_model=MessageResponseSchema)
async def request_password_reset_token(
    data: PasswordResetRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> MessageResponseSchema:
    """Request a password reset token."""
    user = await get_user_by_email(db, str(data.email))
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
    await commit_or_500(db)
    link = f"{DEFAULT_BASE_URL}/password-reset-complete/"
    await email_sender.send_password_reset_email(str(data.email), link)

    return MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )


@router.post("/reset-password/complete/", response_model=MessageResponseSchema)
async def reset_password(
    data: PasswordResetCompleteRequestSchema,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> MessageResponseSchema:
    """Reset user password using token."""
    user = await get_user_by_email(db, str(data.email))
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
            await db.delete(token_record)
            await commit_or_500(db)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token.",
        )

    if cast(datetime, token_record.expires_at).replace(
        tzinfo=timezone.utc
    ) < datetime.now(timezone.utc):
        await db.delete(token_record)
        await commit_or_500(db)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token.",
        )

    user.password = data.password
    await db.delete(token_record)
    await commit_or_500(db)

    login_link = f"{DEFAULT_BASE_URL}/login/"
    await email_sender.send_password_reset_complete_email(
        str(data.email), login_link
    )
    return MessageResponseSchema(message="Password reset successfully.")


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def login_user(
    login_data: UserLoginRequestSchema,
    db: AsyncSession = Depends(get_db),
    settings: BaseAppSettings = Depends(get_settings),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> UserLoginResponseSchema:
    """Authenticate user and return tokens."""
    user = await get_user_by_email(db, str(login_data.email))
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
    refresh_token = RefreshTokenModel.create(
        user_id=user.id,
        days_valid=settings.LOGIN_TIME_DAYS,
        token=jwt_refresh_token,
    )
    db.add(refresh_token)
    await commit_or_500(db)

    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})
    return UserLoginResponseSchema(
        access_token=jwt_access_token, refresh_token=jwt_refresh_token
    )


@router.post("/logout/", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(
    refresh_token: str = Header(
        ..., description="Refresh token to invalidate"
    ),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Logout user by invalidating refresh token."""
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

    await db.delete(token_obj)
    await commit_or_500(db)


@router.post("/refresh/", response_model=TokenRefreshResponseSchema)
async def refresh_access_token(
    token_data: TokenRefreshRequestSchema,
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> TokenRefreshResponseSchema:
    """Refresh access token using refresh token."""
    try:
        decoded_token = jwt_manager.decode_refresh_token(
            token_data.refresh_token
        )
        user_id = decoded_token.get("user_id")
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        )

    stmt = select(RefreshTokenModel).filter_by(token=token_data.refresh_token)
    result = await db.execute(stmt)
    refresh_token_record = result.scalars().first()
    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
        )

    user = await get_user_by_email(db, str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    new_access_token = jwt_manager.create_access_token({"user_id": user_id})
    return TokenRefreshResponseSchema(access_token=new_access_token)
