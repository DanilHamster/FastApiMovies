from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config import get_jwt_auth_manager
from database import UserModel, get_db
from exceptions import BaseSecurityError
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface


async def get_current_user(
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    token: str = Depends(get_token),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """Get current user by JWT token"""
    try:
        payload = jwt_manager.decode_access_token(token)
        token_user_id = payload.get("user_id")

        if token_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing user_id",
            )

    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        )

    user = await db.scalar(
        select(UserModel)
        .where(UserModel.id == token_user_id)
        .options(joinedload(UserModel.group)),
    )

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active",
        )

    return user
