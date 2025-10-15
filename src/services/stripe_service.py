import stripe
from fastapi import HTTPException, status
from stripe import StripeError, SignatureVerificationError

from config.settings import Settings

settings = Settings()
stripe.api_key = settings.stripe_secret_key


def create_checkout_session(
    amount: float,
    currency: str,
    success_url: str,
    cancel_url: str,
    metadata: dict | None = None,
) -> stripe.checkout.Session:
    try:
        metadata = metadata or {}
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": metadata.get("name", "Order"),
                        },
                        "unit_amount": int(amount * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata=metadata,
        )
        return session
    except StripeError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))


def verify_signature_and_construct_event(
    payload: bytes, sig_header: str
) -> stripe.Event:
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        return event
    except SignatureVerificationError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
