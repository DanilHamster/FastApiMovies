from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from database.models.accounts import UserModel
from database.models.movies import CertificationModel, MovieModel
from database.models.orders import OrderItemModel, OrderModel
from database.models.payments import Payment, PaymentItem

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
async def test_create_payment_with_items(async_session):
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

    payment = Payment(user=user, order=order, amount=Decimal("12.50"))
    payment_item = PaymentItem(payment=payment, order_item=item, price_at_payment=Decimal("12.50"))

    async_session.add_all([user, cert, movie, order, item, payment, payment_item])
    await async_session.commit()

    assert payment.amount == Decimal("12.50")
    assert payment.items[0].price_at_payment == Decimal("12.50")
    assert payment.order == order
    assert payment.user == user
    assert payment.items[0].order_item == item
