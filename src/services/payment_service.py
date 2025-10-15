import stripe
from fastapi import HTTPException, status
from config.settings import Settings

from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models.payments import Payment, PaymentStatus

settings = Settings()
stripe.api_key = settings.stripe_secret_key


def verify_signature_and_construct_event(
    payload: bytes, sig_header: str
) -> stripe.Event:
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        return event
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid payload")


async def create_payment(
    db: AsyncSession,
    user_id: int,
    order_id: int,
    amount: Decimal,
    external_payment_id: str,
    status: PaymentStatus = PaymentStatus.canceled,
) -> Payment:
    payment = Payment(
        user_id=user_id,
        order_id=order_id,
        amount=amount,
        external_payment_id=external_payment_id,
        status=status,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def get_payment_by_external_id(
    db: AsyncSession, external_payment_id: str
) -> Payment | None:
    stmt = select(Payment).where(Payment.external_payment_id == external_payment_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_payment_status(
    db: AsyncSession, payment: Payment, new_status: PaymentStatus
) -> Payment:
    payment.status = new_status
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment
