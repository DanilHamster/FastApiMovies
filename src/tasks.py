from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from celery_conf import celery_app
from database.models.accounts import ActivationTokenModel
from database.session_postgresql import sync_postgresql_engine

SyncPostgresqlSessionLocal = sessionmaker(
    bind=sync_postgresql_engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@celery_app.task(name="notify")
def task_for_clean_tokens() -> None:
    print("Clear Start")
    with SyncPostgresqlSessionLocal() as db:
        now_utc = datetime.now(timezone.utc)
        expired_tokens = db.execute(
            select(ActivationTokenModel).where(ActivationTokenModel.expires_at < now_utc)
        ).scalars().all()

        for token in expired_tokens:
            db.delete(token)

        db.commit()
    print("Clear End")
