import enum
from datetime import datetime

from sqlalchemy import Integer, ForeignKey, DateTime, func, DECIMAL, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, UserModel


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"

class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user = relationship("UserModel", back_populates="orders")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    status: Mapped[OrderStatusEnum] = mapped_column(
        Enum(OrderStatusEnum), default=OrderStatusEnum.PENDING, nullable=False
    )

    total_amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    items = relationship(
        "OrderItemModel",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<OrderModel(id={self.id}, user_id={self.user_id}, "
            f"status={self.status}, total_amount={self.total_amount})>"
        )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )

    price_at_order: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    order = relationship("OrderModel", back_populates="items")
    movie = relationship("MovieModel", back_populates="order_items")

    def __repr__(self) -> str:
        return (
            f"<OrderItemModel(id={self.id}, order_id={self.order_id}, "
            f"movie_id={self.movie_id}, price_at_order={self.price_at_order})>"
        )
