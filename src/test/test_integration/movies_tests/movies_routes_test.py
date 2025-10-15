import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from database import Base, MovieModel, get_db, CertificationModel
from main import app

API_PREFIX = "/api/v1/movies"

DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
AsyncSessionTest = async_sessionmaker(engine_test, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(scope="session", autouse=True)
async def prepare_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionTest() as session:
        await session.commit()

    yield

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncSession:
    async with AsyncSessionTest() as session:
        yield session



@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture
async def certification(db_session: AsyncSession) -> CertificationModel:
    result = await db_session.execute(
        select(CertificationModel).where(CertificationModel.name == "PG-13")
    )
    cert = result.scalars().first()
    if not cert:
        cert = CertificationModel(name="PG-13")
        db_session.add(cert)
        await db_session.commit()
        await db_session.refresh(cert)
    return cert


@pytest.mark.asyncio
async def test_create_movie(client: AsyncClient, certification: CertificationModel):
    payload = {
        "name": "Inception",
        "description": "A sci-fi movie about dreams within dreams",
        "year": 2010,
        "time": 148,
        "imdb": 9.0,
        "votes": 2000000,
        "price": 15.5,
        "certification_id": certification.id
    }
    response = await client.post(f"{API_PREFIX}/", json=payload)
    print(response.json())

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert "id" in data
    assert data["certification"]["name"] == certification.name


@pytest.mark.asyncio
async def test_list_movies(client: AsyncClient, db_session: AsyncSession, certification: CertificationModel):
    movies = [
        MovieModel(
            name=f"Movie {i}",
            description=f"Description {i}",
            year=2000 + i,
            time=120,
            imdb=7.5,
            votes=1000,
            price=9.99,
            certification_id=certification.id
        )
        for i in range(3)
    ]
    db_session.add_all(movies)
    await db_session.commit()

    response = await client.get(f"{API_PREFIX}/?page=1&per_page=2")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) <= 2
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_read_movie(client: AsyncClient, db_session: AsyncSession, certification: CertificationModel):
    movie = MovieModel(
        name="Matrix",
        description="A computer hacker learns about the true nature of reality.",
        year=1999,
        time=136,
        imdb=8.7,
        votes=1800000,
        price=11.5,
        certification_id=certification.id
    )
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    response = await client.get(f"{API_PREFIX}/{movie.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Matrix"

@pytest.mark.asyncio
async def test_update_movie(client: AsyncClient, db_session: AsyncSession, certification: CertificationModel):
    movie = MovieModel(
        name="Old title",
        description="Some description for the old movie",
        year=2005,
        time=100,
        imdb=6.0,
        votes=5000,
        price=8.5,
        certification_id=certification.id
    )
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    update_payload = {"name": "New title"}
    response = await client.patch(f"{API_PREFIX}/{movie.id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New title"


@pytest.mark.asyncio
async def test_delete_movie(client: AsyncClient, db_session: AsyncSession, certification: CertificationModel):
    movie = MovieModel(
        name="To Delete",
        description="Movie to be deleted",
        year=2020,
        time=130,
        imdb=7.0,
        votes=1500,
        price=10.0,
        certification_id=certification.id
    )
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    response = await client.delete(f"{API_PREFIX}/{movie.id}")
    assert response.status_code == 200
    assert response.json()["detail"] == "Movie deleted successfully."

    stmt = await db_session.execute(select(MovieModel).where(MovieModel.id == movie.id))
    assert stmt.scalars().first() is None
