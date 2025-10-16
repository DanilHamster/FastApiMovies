from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse as FastAPIJSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from database import (
    CartItemModel,
    CartModel,
    MovieModel,
    OrderItemModel,
    OrderModel,
    UserModel,
    get_db,
)
from database.models.orders import OrderStatusEnum
from utils import get_current_user

router = APIRouter(prefix="/cart", tags=["Shopping cart"])


class CartAddItemSchema(BaseModel):
    movie_id: int


@router.get("/", status_code=status.HTTP_200_OK)
async def get_cart(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FastAPIJSONResponse:
    stmt = (
        select(CartModel)
        .where(CartModel.user_id == current_user.id)
        .options(
            selectinload(CartModel.items).selectinload(CartItemModel.movie)
        )
    )
    cart = (await db.execute(stmt)).scalar_one_or_none()
    if not cart or not cart.items:
        return JSONResponse(content={"items": [], "total_amount": "0.00"})

    total_amount = sum(Decimal(item.movie.price) for item in cart.items)
    items = [
        {
            "movie_id": i.movie_id,
            "name": i.movie.name,
            "price": str(i.movie.price),
        }
        for i in cart.items
    ]
    return JSONResponse(
        content={"items": items, "total_amount": str(total_amount)}
    )


@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    item: CartAddItemSchema,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FastAPIJSONResponse:
    movie = (
        await db.execute(
            select(MovieModel).where(MovieModel.id == item.movie_id)
        )
    ).scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )

    cart = (
        await db.execute(
            select(CartModel)
            .where(CartModel.user_id == current_user.id)
            .options(selectinload(CartModel.items))
        )
    ).scalar_one_or_none()
    if not cart:
        cart = CartModel(user_id=current_user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    if any(ci.movie_id == item.movie_id for ci in cart.items):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Movie already in cart"
        )

    cart.items.append(CartItemModel(movie_id=item.movie_id))
    await db.commit()
    await db.refresh(cart)
    return JSONResponse(content={"message": "Movie added to cart"})


@router.delete("/remove/{movie_id}", status_code=status.HTTP_200_OK)
async def remove_from_cart(
    movie_id: int,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FastAPIJSONResponse:
    cart = (
        await db.execute(
            select(CartModel)
            .where(CartModel.user_id == current_user.id)
            .options(selectinload(CartModel.items))
        )
    ).scalar_one_or_none()
    if not cart or not cart.items:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cart is empty")

    cart.items = [ci for ci in cart.items if ci.movie_id != movie_id]
    await db.commit()
    return JSONResponse(content={"message": "Movie removed from cart"})


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout_cart(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FastAPIJSONResponse:
    cart = (
        await db.execute(
            select(CartModel)
            .where(CartModel.user_id == current_user.id)
            .options(
                selectinload(CartModel.items).selectinload(CartItemModel.movie)
            )
        )
    ).scalar_one_or_none()
    if not cart or not cart.items:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cart is empty"
        )

    total_amount = sum(Decimal(item.movie.price) for item in cart.items)
    order = OrderModel(
        user_id=current_user.id,
        total_amount=total_amount,
        status=OrderStatusEnum.PENDING,
    )
    for ci in cart.items:
        order.items.append(
            OrderItemModel(movie_id=ci.movie_id, price_at_order=ci.movie.price)
        )

    db.add(order)
    cart.items = []
    await db.commit()
    await db.refresh(order)

    # Stripe is not implemented anymore; just return created order information
    return JSONResponse(
        content={"order_id": order.id, "message": "Order created"}
    )
