from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from database import Base, CertificationModel, DirectorModel, GenreModel, MovieModel, StarModel

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


@pytest.mark.asyncio
async def test_create_certification(async_session):
    cert = CertificationModel(name="PG-13")
    async_session.add(cert)
    await async_session.commit()
    await async_session.refresh(cert)
    assert cert.id is not None
    assert cert.name == "PG-13"
    assert "Certification" in repr(cert)


@pytest.mark.asyncio
async def test_create_movie_with_relations(async_session):
    cert = CertificationModel(name="R")
    genre = GenreModel(name="Action")
    star = StarModel(name="Tom Cruise")
    director = DirectorModel(name="Christopher McQuarrie")

    async_session.add_all([cert, genre, star, director])
    await async_session.flush()

    movie = MovieModel(
        name="Mission Impossible",
        year=2023,
        time=120,
        imdb=8.5,
        votes=250000,
        meta_score=76.0,
        gross=150.5,
        description="Ethan Hunt saves the world again.",
        price=15.99,
        certification_id=cert.id,
    )

    movie.genres.append(genre)
    movie.stars.append(star)
    movie.directors.append(director)

    async_session.add(movie)
    await async_session.commit()
    await async_session.refresh(movie)

    assert movie.id is not None
    assert isinstance(movie.uuid, UUID)
    assert movie.certification.name == "R"
    assert len(movie.genres) == 1
    assert len(movie.stars) == 1
    assert len(movie.directors) == 1
    assert "Mission Impossible" in repr(movie)


@pytest.mark.asyncio
async def test_unique_constraint_on_movie(async_session):
    cert = CertificationModel(name="PG")
    async_session.add(cert)
    await async_session.flush()

    movie1 = MovieModel(
        name="Interstellar",
        year=2014,
        time=169,
        imdb=8.6,
        votes=1500000,
        description="Space exploration and time dilation.",
        price=19.99,
        certification_id=cert.id,
    )
    async_session.add(movie1)
    await async_session.commit()

    movie2 = MovieModel(
        name="Interstellar",
        year=2014,
        time=169,
        imdb=8.6,
        votes=1500000,
        description="Duplicate entry should fail.",
        price=19.99,
        certification_id=cert.id,
    )
    async_session.add(movie2)

    with pytest.raises(IntegrityError):
        await async_session.commit()
        await async_session.rollback()


@pytest.mark.asyncio
async def test_cascade_delete(async_session):
    cert = CertificationModel(name="G")
    movie = MovieModel(
        name="Toy Story",
        year=1995,
        time=81,
        imdb=8.3,
        votes=950000,
        description="Animated toys adventure.",
        price=9.99,
        certification=cert,
    )
    async_session.add(movie)
    await async_session.commit()

    await async_session.delete(cert)
    await async_session.commit()

    result = await async_session.get(MovieModel, movie.id)
    assert result is None
