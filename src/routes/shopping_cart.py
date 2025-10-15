from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from decimal import Decimal

from database import (
    CartModel,
    CartItemModel,
    MovieModel,
    OrderModel,
    OrderItemModel,
    get_db, PaymentStatus,
)
from database.models.orders import OrderStatusEnum
from utils import get_current_user
from services import stripe_service, payment_service
from config.settings import Settings
from pydantic import BaseModel

router = APIRouter(prefix="/cart", tags=["shopping_cart"])
settings = Settings()

class CartAddItemSchema(BaseModel):
    movie_id: int

@router.get("/", status_code=status.HTTP_200_OK)
async def get_cart(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(CartModel).where(CartModel.user_id == current_user.id).options(
        selectinload(CartModel.items).selectinload(CartItemModel.movie)
    )
    cart = (await db.execute(stmt)).scalar_one_or_none()
    if not cart or not cart.items:
        return {"items": [], "total_amount": "0.00"}

    total_amount = sum(Decimal(item.movie.price) for item in cart.items)
    items = [{"movie_id": i.movie_id, "name": i.movie.name, "price": str(i.movie.price)} for i in cart.items]
    return {"items": items, "total_amount": str(total_amount)}

@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_to_cart(item: CartAddItemSchema, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    movie = (await db.execute(select(MovieModel).where(MovieModel.id == item.movie_id))).scalar_one_or_none()
    if not movie:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Movie not found")

    cart = (await db.execute(select(CartModel).where(CartModel.user_id == current_user.id).options(selectinload(CartModel.items)))).scalar_one_or_none()
    if not cart:
        cart = CartModel(user_id=current_user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    if any(ci.movie_id == item.movie_id for ci in cart.items):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Movie already in cart")

    cart.items.append(CartItemModel(movie_id=item.movie_id))
    await db.commit()
    await db.refresh(cart)
    return {"message": "Movie added to cart"}

@router.delete("/remove/{movie_id}", status_code=status.HTTP_200_OK)
async def remove_from_cart(movie_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cart = (await db.execute(select(CartModel).where(CartModel.user_id == current_user.id).options(selectinload(CartModel.items)))).scalar_one_or_none()
    if not cart or not cart.items:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cart is empty")

    cart.items = [ci for ci in cart.items if ci.movie_id != movie_id]
    await db.commit()
    return {"message": "Movie removed from cart"}

@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout_cart(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cart = (await db.execute(select(CartModel).where(CartModel.user_id == current_user.id).options(selectinload(CartModel.items).selectinload(CartItemModel.movie)))).scalar_one_or_none()
    if not cart or not cart.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    total_amount = sum(Decimal(item.movie.price) for item in cart.items)
    order = OrderModel(user_id=current_user.id, total_amount=total_amount, status=OrderStatusEnum.PENDING)
    for ci in cart.items:
        order.items.append(OrderItemModel(movie_id=ci.movie_id, price_at_order=Decimal(ci.movie.price)))

    db.add(order)
    cart.items = []
    await db.commit()
    await db.refresh(order)

    metadata = {"user_id": str(current_user.id), "order_id": str(order.id)}
    session = stripe_service.create_checkout_session(
        amount=float(order.total_amount),
        currency="usd",
        success_url=f"{settings.app_base_url}/payments/success",
        cancel_url=f"{settings.app_base_url}/payments/cancel",
        metadata=metadata,
    )

    await payment_service.create_payment(
        db=db,
        user_id=current_user.id,
        order_id=order.id,
        amount=Decimal(str(order.total_amount)),
        external_payment_id=session.id,
        status=PaymentStatus.canceled,
    )

    return {"checkout_url": session.url, "order_id": order.id}
