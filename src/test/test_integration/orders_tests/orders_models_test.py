import pytest
from decimal import Decimal
from sqlalchemy import select

from database import UserModel, CertificationModel, MovieModel, OrderModel, OrderItemModel, Base
from database.models.orders import OrderStatusEnum

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
async def test_create_order_with_items(async_session):
    user = UserModel(email="test@example.com", password="StrongPass1!", group_id=1)
    cert = CertificationModel(name="PG-13")
    movie = MovieModel(
        name="Inception",
        year=2010,
        time=148,
        imdb=8.8,
        votes=2000000,
        description="A mind-bending thriller.",
        price=Decimal("12.50"),
        certification=cert,
    )
    order = OrderModel(user=user, total_amount=Decimal("12.50"))
    item = OrderItemModel(order=order, movie=movie, price_at_order=Decimal("12.50"))

    async_session.add_all([user, cert, movie, order, item])
    await async_session.commit()

    result = await async_session.get(OrderModel, order.id)
    assert result is not None
    assert result.user.email == "test@example.com"
    assert len(result.items) == 1
    assert result.items[0].movie.name == "Inception"
    assert result.status == OrderStatusEnum.PENDING


@pytest.mark.asyncio
async def test_order_repr(async_session):
    user = UserModel(email="john@example.com", password="StrongPass1!", group_id=1)
    order = OrderModel(user=user, total_amount=Decimal("30.00"))
    async_session.add_all([user, order])
    await async_session.commit()

    repr_str = repr(order)
    assert f"id={order.id}" in repr_str
    assert "total_amount=30.00" in repr_str


@pytest.mark.asyncio
async def test_order_item_repr(async_session):
    user = UserModel(email="repr@example.com", password="StrongPass1!", group_id=1)
    cert = CertificationModel(name="R")
    movie = MovieModel(
        name="Matrix",
        year=1999,
        time=136,
        imdb=8.7,
        votes=1800000,
        description="Neo discovers the truth.",
        price=Decimal("10.00"),
        certification=cert,
    )
    order = OrderModel(user=user, total_amount=Decimal("10.00"))
    item = OrderItemModel(order=order, movie=movie, price_at_order=Decimal("10.00"))

    async_session.add_all([user, cert, movie, order, item])
    await async_session.commit()

    repr_str = repr(item)
    assert f"order_id={order.id}" in repr_str
    assert f"movie_id={movie.id}" in repr_str


@pytest.mark.asyncio
async def test_cascade_delete_order(async_session):
    user = UserModel(email="del@example.com", password="StrongPass1!", group_id=1)
    cert = CertificationModel(name="PG")
    movie = MovieModel(
        name="Avatar",
        year=2009,
        time=162,
        imdb=7.8,
        votes=1300000,
        description="Pandora world.",
        price=Decimal("11.00"),
        certification=cert,
    )
    order = OrderModel(user=user, total_amount=Decimal("11.00"))
    item = OrderItemModel(order=order, movie=movie, price_at_order=Decimal("11.00"))

    async_session.add_all([user, cert, movie, order, item])
    await async_session.commit()

    await async_session.delete(order)
    await async_session.commit()

    result = await async_session.execute(select(OrderItemModel).where(OrderItemModel.id == item.id))
    deleted_item = result.scalar_one_or_none()
    assert deleted_item is None


@pytest.mark.asyncio
async def test_ondelete_user_cascade(async_session):
    user = UserModel(email="cascade@example.com", password="StrongPass1!", group_id=1)
    order = OrderModel(user=user, total_amount=Decimal("25.00"))

    async_session.add_all([user, order])
    await async_session.commit()

    await async_session.delete(user)
    await async_session.commit()

    result = await async_session.get(OrderModel, order.id)
    assert result is None