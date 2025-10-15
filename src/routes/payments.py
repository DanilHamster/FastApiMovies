from fastapi import APIRouter, Depends, Request, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, Integer, Numeric, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from config.settings import Settings
from database.models.orders import OrderStatusEnum
from services import stripe_service, payment_service
from database.session_postgresql import get_postgresql_db
from database.models.payments import PaymentStatus
from decimal import Decimal

from database import Base, OrderModel
from utils import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])

class CheckoutRequest(Base):
    __tablename__ = "checkout_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="usd")

class CheckoutRequestSchema(BaseModel):
    order_id: int
    amount: Decimal
    currency: str = "usd"

settings = Settings()

@router.post("/checkout")
async def create_checkout(
    req: CheckoutRequestSchema,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user=Depends(get_current_user),
):
    stmt = select(OrderModel).where(
        OrderModel.id == req.order_id, OrderModel.user_id == current_user.id
    )
    order = (await db.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order not pending")

    metadata = {"user_id": str(current_user.id), "order_id": str(order.id)}
    session = stripe_service.create_checkout_session(
        amount=float(order.total_amount),
        currency="usd",
        success_url=f"{settings.app_base_url}/payments/success",
        cancel_url=f"{settings.app_base_url}/payments/cancel",
        metadata=metadata,
    )
    amount = Decimal(str(order.total_amount))
    await payment_service.create_payment(
        db=db,
        user_id=current_user.id,
        order_id=order.id,
        amount=amount,
        external_payment_id=session.id,
        status=PaymentStatus.canceled,  # тимчасово
    )

    return {"checkout_url": session.url}

@router.post("/webhook")
async def stripe_webhook(
    request: Request, db: AsyncSession = Depends(get_postgresql_db)
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    event = stripe_service.verify_signature_and_construct_event(payload, sig_header)

    if event.type == "checkout.session.completed":
        session = event.data.object
        external_id = session["id"]
        payment = await payment_service.get_payment_by_external_id(db, external_id)
        if payment:
            await payment_service.update_payment_status(db, payment, PaymentStatus.successful)
            stmt = select(OrderModel).where(OrderModel.id == payment.order_id)
            order = (await db.execute(stmt)).scalar_one_or_none()
            if order:
                order.status = OrderStatusEnum.PAID
                await db.commit()

    elif event.type == "checkout.session.expired" or event.type == "checkout.session.canceled":
        session = event.data.object
        external_id = session["id"]
        payment = await payment_service.get_payment_by_external_id(db, external_id)
        if payment:
            await payment_service.update_payment_status(db, payment, PaymentStatus.canceled)


    return JSONResponse(status_code=status.HTTP_200_OK, content={"received": True})

@router.get("/success")
async def pay_success():
    return {"message": "Payment succeeded"}

@router.get("/cancel")
async def pay_cancel():
    return {"message": "Payment canceled"}
