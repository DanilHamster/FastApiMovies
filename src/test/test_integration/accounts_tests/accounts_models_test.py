import uuid
from datetime import datetime

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from database import (
    ActivationTokenModel,
    Base,
    PasswordResetTokenModel,
    RefreshTokenModel,
    UserGroupEnum,
    UserGroupModel,
    UserModel,
)

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="module")
async def async_session():
    engine = create_async_engine(DATABASE_URL, future=True, echo=False)
    async_session_local = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_local() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
async def clean_database(async_session):
    """Очищає таблиці перед кожним тестом."""
    await async_session.execute(delete(ActivationTokenModel))
    await async_session.execute(delete(PasswordResetTokenModel))
    await async_session.execute(delete(RefreshTokenModel))
    await async_session.execute(delete(UserModel))
    await async_session.execute(delete(UserGroupModel))
    await async_session.commit()
    yield


@pytest.mark.anyio
async def test_create_user_group(async_session):
    group = UserGroupModel(name=UserGroupEnum.USER)
    async_session.add(group)
    await async_session.commit()
    await async_session.refresh(group)

    assert group.id is not None
    assert group.name == UserGroupEnum.USER
    assert "UserGroupModel" in repr(group)


@pytest.mark.anyio
async def test_create_user(async_session):
    group = UserGroupModel(name=UserGroupEnum.MODERATOR)
    async_session.add(group)
    await async_session.commit()
    await async_session.refresh(group)

    user = UserModel.create(
        email=f"user_{uuid.uuid4()}@example.com",
        raw_password="StrongPass123!",
        group_id=group.id,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    assert user.id is not None
    assert user.verify_password("StrongPass123!") is True
    assert user.has_group(UserGroupEnum.MODERATOR)
    assert user.is_active is False
    assert "UserModel" in repr(user)


@pytest.mark.anyio
async def test_activation_token(async_session):
    group = UserGroupModel(name=UserGroupEnum.ADMIN)
    async_session.add(group)
    await async_session.commit()
    await async_session.refresh(group)

    email = f"admin_{uuid.uuid4()}@example.com"
    user = UserModel.create(email, "StrongPass123!", group.id)
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    token = ActivationTokenModel(user_id=user.id)
    async_session.add(token)
    await async_session.commit()
    await async_session.refresh(token)

    assert token.token is not None
    assert token.expires_at > datetime.utcnow()
    assert "ActivationTokenModel" in repr(token)


@pytest.mark.anyio
async def test_password_reset_token(async_session):
    group = UserGroupModel(name=UserGroupEnum.USER)
    async_session.add(group)
    await async_session.commit()
    await async_session.refresh(group)

    user = UserModel.create(f"reset_{uuid.uuid4()}@example.com", "StrongPass123!", group.id)
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    token = PasswordResetTokenModel(user_id=user.id)
    async_session.add(token)
    await async_session.commit()
    await async_session.refresh(token)

    assert token.token is not None
    assert token.expires_at > datetime.utcnow()
    assert "PasswordResetTokenModel" in repr(token)


@pytest.mark.anyio
async def test_refresh_token(async_session):
    group = UserGroupModel(name=UserGroupEnum.USER)
    async_session.add(group)
    await async_session.commit()
    await async_session.refresh(group)

    user = UserModel.create(f"refresh_{uuid.uuid4()}@example.com", "StrongPass123!", group.id)
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    token = RefreshTokenModel.create(user.id, days_valid=3, token="test_refresh_token")
    async_session.add(token)
    await async_session.commit()
    await async_session.refresh(token)

    assert token.token == "test_refresh_token"
    assert (token.expires_at - datetime.utcnow()).days <= 3
    assert "RefreshTokenModel" in repr(token)
