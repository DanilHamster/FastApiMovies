from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from config.settings import Settings
from services import stripe_service, payment_service
from database.session_postgresql import get_postgresql_db
from database.models.payments import PaymentStatus
from decimal import Decimal

from database import Base
from utils import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])

class CheckoutRequest(Base):
    order_id: int
    amount: Decimal
    currency: str = "usd"

@router.post("/checkout")
async def create_checkout(
    req: CheckoutRequest,
    db: AsyncSession = Depends(get_postgresql_db),
    current_user = Depends(get_current_user),
):
    metadata = {
        "user_id": str(current_user.id),
        "order_id": str(req.order_id),
    }
    session = stripe_service.create_checkout_session(
        amount=float(req.amount),
        currency=req.currency,
        success_url=Settings.app_base_url + "/payments/success",
        cancel_url=Settings.app_base_url + "/payments/cancel",
        metadata=metadata,
    )

    await payment_service.create_payment(
        db=db,
        user_id=current_user.id,
        order_id=req.order_id,
        amount=req.amount,
        external_payment_id=session.id,
        status=PaymentStatus.canceled,
    )

    return {"checkout_url": session.url, "session_id": session.id}

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
