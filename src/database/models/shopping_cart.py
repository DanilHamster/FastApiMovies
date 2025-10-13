from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    user = relationship("UserModel", back_populates="cart")

    items = relationship(
        "CartItemModel",
        back_populates="cart",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CartModel(id={self.id}, user_id={self.user_id})>"


class CartItemModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cart = relationship("CartModel", back_populates="items")
    movie = relationship("MovieModel", back_populates="cart_items")

    __table_args__ = (UniqueConstraint("cart_id", "movie_id"),)

    def __repr__(self) -> str:
        return (
            f"<CartItemModel(id={self.id}, cart_id={self.cart_id}, "
            f"movie_id={self.movie_id}, added_at={self.added_at})>"
        )
