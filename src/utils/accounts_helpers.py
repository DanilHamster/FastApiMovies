from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    ActivationTokenModel,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)

DEFAULT_BASE_URL = "http://127.0.0.1/accounts"


async def get_user_by_email(
    db: AsyncSession, email: str
) -> Optional[UserModel]:
    """Return a user instance by email."""
    stmt = select(UserModel).filter_by(email=email)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_group(
    db: AsyncSession, name: UserGroupEnum
) -> Optional[UserGroupModel]:
    """Return a user group instance by name."""
    stmt = select(UserGroupModel).where(UserGroupModel.name == name)
    result = await db.execute(stmt)
    return result.scalars().first()


async def commit_or_500(
    db: AsyncSession, msg: str = "An error occurred."
) -> None:
    """Commit the session or raise HTTP 500 on failure."""
    try:
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg
        ) from e


async def delete_activation_tokens(db: AsyncSession, user_id: int) -> None:
    """Delete all activation tokens for the given user."""
    await db.execute(
        delete(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user_id
        )
    )


def activation_link(token: str, email: str) -> str:
    """Generate an activation link."""
    return f"{DEFAULT_BASE_URL}/activate/?token={token}&email={email}"
