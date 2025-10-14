import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base

if TYPE_CHECKING:
    from database.models.accounts import UserModel
    from database.models.orders import OrderItemModel, OrderModel


class PaymentStatus(enum.Enum):
    successful = "successful"
    canceled = "canceled"
    refunded = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.successful, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    external_payment_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="payments"
    )
    order: Mapped["OrderModel"] = relationship(
        "OrderModel", back_populates="payments"
    )
    items: Mapped[list["PaymentItem"]] = relationship(
        "PaymentItem", back_populates="payment"
    )


class PaymentItem(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    payment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("payments.id"), nullable=False
    )
    order_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("order_items.id"), nullable=False
    )
    price_at_payment: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )

    payment: Mapped["Payment"] = relationship(
        "Payment", back_populates="items"
    )
    order_item: Mapped["OrderItemModel"] = relationship(
        "OrderItem", back_populates="payment_items"
    )
