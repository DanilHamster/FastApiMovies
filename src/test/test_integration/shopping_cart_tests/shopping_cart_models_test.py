import pytest


from database import CartModel, CartItemModel, Base
from database.models.accounts import UserModel
from database.models.movies import MovieModel, CertificationModel

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


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
async def test_create_cart_with_items(async_session):

    user = UserModel(email="testcart@example.com", password="StrongPass1!", group_id=1)

    cert = CertificationModel(name="PG-13")
    movie1 = MovieModel(
        name="Inception", year=2010, time=148, imdb=8.8, votes=2000000,
        description="A mind-bending thriller.", price=12.50, certification=cert,
    )
    movie2 = MovieModel(
        name="Interstellar", year=2014, time=169, imdb=8.6, votes=1500000,
        description="Space exploration epic.", price=15.00, certification=cert,
    )

    cart = CartModel(user=user)

    item1 = CartItemModel(cart=cart, movie=movie1)
    item2 = CartItemModel(cart=cart, movie=movie2)

    async_session.add_all([user, cert, movie1, movie2, cart, item1, item2])
    await async_session.commit()

    await async_session.refresh(cart, ["items"])

    assert cart.user == user
    assert len(cart.items) == 2
    assert cart.items[0].movie in [movie1, movie2]
    assert cart.items[1].movie in [movie1, movie2]
    assert cart.items[0].added_at is not None
    assert cart.items[1].added_at is not None
