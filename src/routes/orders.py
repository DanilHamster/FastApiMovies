from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, delete, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.dependencies import get_jwt_auth_manager
from database import (
    CartItemModel,
    CartModel,
    OrderItemModel,
    OrderModel,
    UserModel,
    get_db,
)
from database.models.accounts import UserGroupEnum, UserGroupModel
from database.models.orders import OrderStatusEnum
from database.models.payments import Payment, PaymentItem, PaymentStatus
from schemas.orders import OrderDetailOutSchema, OrderOutSchema
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface

router = APIRouter(prefix="/orders", tags=["Orders"])
admin_router = APIRouter(prefix="/admin/orders", tags=["Orders"])


async def get_current_user(
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """Resolve the current user from the access token and load it from DB."""
    try:
        claims = jwt_manager.decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    raw_user_id = claims.get("user_id") or claims.get("sub")
    try:
        user_id = int(raw_user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


@router.get(
    "/", status_code=status.HTTP_200_OK, response_model=list[OrderOutSchema]
)
async def list_orders(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: OrderStatusEnum | None = Query(
        None, alias="status", description="Filter by order status"
    ),
    limit: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
    offset: int = Query(0, ge=0, description="Items offset"),
):
    """
    Return all orders belonging to the current user.
    Supports optional filters: status, limit, offset. Sorted by newest first.
    """
    stmt = (
        select(OrderModel)
        .where(OrderModel.user_id == current_user.id)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.movie)
        )
        .order_by(OrderModel.created_at.desc(), OrderModel.id.desc())
        .limit(limit)
        .offset(offset)
    )

    if status_filter is not None:
        stmt = stmt.where(OrderModel.status == status_filter)

    res = await db.execute(stmt)
    orders: list[OrderModel] = list(res.scalars().unique().all())

    def serialize_order(o: OrderModel) -> dict:
        return {
            "id": o.id,
            "status": (
                o.status.value if hasattr(o.status, "value") else str(o.status)
            ),
            "total_amount": str(o.total_amount),
            "created_at": (
                o.created_at.isoformat()
                if getattr(o, "created_at", None)
                else None
            ),
            "items": [
                {
                    "movie_id": it.movie_id,
                    "price_at_order": str(it.price_at_order),
                }
                for it in o.items
            ],
        }

    return [serialize_order(o) for o in orders]


@router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=OrderOutSchema
)
async def create_order(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new order from the current user's cart with validations:
    - The cart must not be empty.
    - Exclude movies already purchased by the user.
    - Ensure there is no pending order with the same set of movies.
    - After successful creation, clear the user's cart.
    """
    cart_stmt: Select = (
        select(CartModel)
        .where(CartModel.user_id == current_user.id)
        .options(
            selectinload(CartModel.items).selectinload(CartItemModel.movie)
        )
    )
    cart_result = await db.execute(cart_stmt)
    cart: CartModel | None = cart_result.scalar_one_or_none()

    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty"
        )

    purchased_stmt = (
        select(distinct(OrderItemModel.movie_id))
        .join(PaymentItem, PaymentItem.order_item_id == OrderItemModel.id)
        .join(Payment, Payment.id == PaymentItem.payment_id)
        .join(OrderModel, OrderModel.id == Payment.order_id)
        .where(
            Payment.user_id == current_user.id,
            Payment.status == PaymentStatus.successful,
        )
    )
    purchased_res = await db.execute(purchased_stmt)
    purchased_movie_ids: set[int] = {mid for (mid,) in purchased_res.all()}

    cart_items = [
        ci for ci in cart.items if ci.movie_id not in purchased_movie_ids
    ]
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All movies in the cart are already purchased",
        )

    candidate_movie_ids: set[int] = {ci.movie_id for ci in cart_items}

    pending_orders_stmt = select(OrderModel).where(
        OrderModel.user_id == current_user.id,
        OrderModel.status == OrderStatusEnum.PENDING,
    )
    pending_orders_res = await db.execute(pending_orders_stmt)
    pending_orders: list[OrderModel] = list(pending_orders_res.scalars().all())

    if pending_orders:
        pending_order_ids = [o.id for o in pending_orders]
        if pending_order_ids:
            order_items_stmt = select(
                OrderItemModel.order_id, OrderItemModel.movie_id
            ).where(OrderItemModel.order_id.in_(pending_order_ids))
            order_items_res = await db.execute(order_items_stmt)
            order_to_movies: dict[int, set[int]] = {}
            for order_id, movie_id in order_items_res.all():
                order_to_movies.setdefault(order_id, set()).add(movie_id)

            if any(
                candidate_movie_ids == movie_ids
                for movie_ids in order_to_movies.values()
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="There is already a pending order with the same movies",
                )

    total_amount: Decimal = sum(
        (Decimal(ci.movie.price) for ci in cart_items), Decimal("0.00")
    )

    order = OrderModel(user_id=current_user.id, total_amount=total_amount)
    for ci in cart_items:
        order.items.append(
            OrderItemModel(
                movie_id=ci.movie_id, price_at_order=Decimal(ci.movie.price)
            )
        )

    db.add(order)
    await db.commit()
    await db.refresh(order)

    await db.execute(
        delete(CartItemModel).where(CartItemModel.cart_id == cart.id)
    )
    await db.commit()

    return {
        "id": order.id,
        "status": (
            order.status.value
            if hasattr(order.status, "value")
            else str(order.status)
        ),
        "total_amount": str(order.total_amount),
        "created_at": (
            order.created_at.isoformat()
            if getattr(order, "created_at", None)
            else None
        ),
        "items": [
            {
                "movie_id": item.movie_id,
                "price_at_order": str(item.price_at_order),
            }
            for item in order.items
        ],
    }


@router.get(
    "/{order_id}",
    status_code=status.HTTP_200_OK,
    response_model=OrderDetailOutSchema,
)
async def get_order_details(
    order_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return detailed view of a specific order. Users see only their orders; admins can see any."""
    group_res = await db.execute(
        select(UserGroupModel.name).where(
            UserGroupModel.id == current_user.group_id
        )
    )
    group_name = group_res.scalar_one_or_none()
    is_admin = group_name == UserGroupEnum.ADMIN

    stmt = (
        select(OrderModel)
        .where(OrderModel.id == order_id)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.movie)
        )
    )
    res = await db.execute(stmt)
    order: OrderModel | None = res.scalars().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    if not is_admin and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
        )

    return {
        "id": order.id,
        "status": (
            order.status.value
            if hasattr(order.status, "value")
            else str(order.status)
        ),
        "total_amount": str(order.total_amount),
        "created_at": (
            order.created_at.isoformat()
            if getattr(order, "created_at", None)
            else None
        ),
        "items": [
            {
                "movie": {
                    "id": item.movie.id,
                    "name": item.movie.name,
                },
                "price_at_order": str(item.price_at_order),
            }
            for item in order.items
        ],
    }


@router.patch(
    "/{order_id}/cancel",
    status_code=status.HTTP_200_OK,
    response_model=OrderDetailOutSchema,
)
async def cancel_order(
    order_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending order. Users can cancel only their own pending orders; admins can cancel any pending order."""
    group_res = await db.execute(
        select(UserGroupModel.name).where(
            UserGroupModel.id == current_user.group_id
        )
    )
    group_name = group_res.scalar_one_or_none()
    is_admin = group_name == UserGroupEnum.ADMIN

    stmt = (
        select(OrderModel)
        .where(OrderModel.id == order_id)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.movie)
        )
    )
    res = await db.execute(stmt)
    order: OrderModel | None = res.scalars().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    if not is_admin and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
        )

    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be canceled",
        )

    order.status = OrderStatusEnum.CANCELED
    await db.flush()
    await db.commit()
    await db.refresh(order)

    return {
        "id": order.id,
        "status": (
            order.status.value
            if hasattr(order.status, "value")
            else str(order.status)
        ),
        "total_amount": str(order.total_amount),
        "created_at": (
            order.created_at.isoformat()
            if getattr(order, "created_at", None)
            else None
        ),
        "items": [
            {
                "movie": {
                    "id": item.movie.id,
                    "name": item.movie.name,
                },
                "price_at_order": str(item.price_at_order),
            }
            for item in order.items
        ],
    }


@admin_router.get(
    "/", status_code=status.HTTP_200_OK, response_model=list[OrderOutSchema]
)
async def admin_list_orders(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Query(None, description="Filter by user id"),
    status_filter: OrderStatusEnum | None = Query(
        None, alias="status", description="Filter by order status"
    ),
    date_from: datetime | None = Query(
        None, description="Filter by created_at from (ISO 8601)"
    ),
    date_to: datetime | None = Query(
        None, description="Filter by created_at to (ISO 8601)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
    offset: int = Query(0, ge=0, description="Items offset"),
):
    """
    Admin-only: list all orders with optional filters and pagination. Sorted by newest first.
    """
    group_res = await db.execute(
        select(UserGroupModel.name).where(
            UserGroupModel.id == current_user.group_id
        )
    )
    group_name = group_res.scalar_one_or_none()
    if group_name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    stmt = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.movie)
        )
        .order_by(OrderModel.created_at.desc(), OrderModel.id.desc())
        .limit(limit)
        .offset(offset)
    )

    if user_id is not None:
        stmt = stmt.where(OrderModel.user_id == user_id)
    if status_filter is not None:
        stmt = stmt.where(OrderModel.status == status_filter)

    if date_from is not None:
        stmt = stmt.where(OrderModel.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(OrderModel.created_at <= date_to)

    res = await db.execute(stmt)
    orders: list[OrderModel] = list(res.scalars().unique().all())

    def serialize_order(o: OrderModel) -> dict:
        return {
            "id": o.id,
            "status": (
                o.status.value if hasattr(o.status, "value") else str(o.status)
            ),
            "total_amount": str(o.total_amount),
            "created_at": (
                o.created_at.isoformat()
                if getattr(o, "created_at", None)
                else None
            ),
            "items": [
                {
                    "movie_id": it.movie_id,
                    "price_at_order": str(it.price_at_order),
                }
                for it in o.items
            ],
        }

    return [serialize_order(o) for o in orders]
