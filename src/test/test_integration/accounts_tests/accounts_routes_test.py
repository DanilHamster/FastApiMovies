from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app
from database import get_db, Base, UserGroupModel, ActivationTokenModel


API_PREFIX = "/api/v1/accounts"

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(TEST_DATABASE_URL, echo=True)
AsyncSessionTest = sessionmaker(engine_test, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(scope="session", autouse=True)
async def prepare_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionTest() as session:
        session.add(UserGroupModel(id=1, name="user"))
        await session.commit()

    yield

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncSession:
    async with AsyncSessionTest() as session:
        yield session


@pytest.fixture(autouse=True)
def mock_email(monkeypatch):
    async def fake_send_activation_email(*args, **kwargs):
        return
    monkeypatch.setattr(
        "notifications.emails.EmailSender.send_activation_email",
        fake_send_activation_email
    )

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as ac:
        yield ac

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    payload = {"email": "testuser@example.com", "password": "Test123!"}
    response = await client.post(f"{API_PREFIX}/register/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]


@pytest.mark.asyncio
async def test_register_user_duplicate(client: AsyncClient):
    payload = {"email": "testuser@example.com", "password": "Test123!"}
    response = await client.post(f"{API_PREFIX}/register/", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_activation_flow(client, db_session):
    with patch("notifications.emails.EmailSender._send_email", new_callable=AsyncMock) as mock_send_email:
        mock_send_email.return_value = None

        payload = {"email": "activateuser@example.com", "password": "Test123!"}
        response = await client.post(f"{API_PREFIX}/register/", json=payload)
        assert response.status_code == 201

        stmt = await db_session.execute(
            select(ActivationTokenModel).order_by(ActivationTokenModel.id.desc()).limit(1)
        )
        token_record = stmt.scalars().first()
        assert token_record is not None

        activation_payload = {"email": "activateuser@example.com", "token": token_record.token}
        response = await client.post(f"{API_PREFIX}/activate/", json=activation_payload)
        assert response.status_code == 200

        mock_send_email.assert_called_once()


@pytest.mark.asyncio
async def test_login_user(client: AsyncClient, db_session: AsyncSession):
    payload = {"email": "testuser@example.com", "password": "Test123!"}

    with patch("notifications.emails.EmailSender._send_email", new_callable=AsyncMock):
        await client.post(f"{API_PREFIX}/register/", json=payload)

        stmt = await db_session.execute(
            select(ActivationTokenModel).order_by(ActivationTokenModel.id.desc()).limit(1)
        )
        token_record = stmt.scalars().first()
        assert token_record is not None

        activation_payload = {"email": payload["email"], "token": token_record.token}
        await client.post(f"{API_PREFIX}/activate/", json=activation_payload)

        response = await client.post(f"{API_PREFIX}/login/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    login_payload = {"email": "testuser@example.com", "password": "Test123!"}
    login_resp = await client.post(f"{API_PREFIX}/login/", json=login_payload)
    access_token = login_resp.json()["access_token"]

    payload = {"old_password": "Test123!", "new_password": "NewPass123!"}
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.post(f"{API_PREFIX}/change-password/", json=payload, headers=headers)
    assert response.status_code == 200
    assert "successfully" in response.json()["message"].lower()
