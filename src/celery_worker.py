# from datetime import datetime, timezone
# from database import async_session_maker
#
# @celery.task
# async def cleanup_expired_activation_tokens():
#     async with async_session_maker() as db:
#         now = datetime.now(timezone.utc)
#         stmt = select(ActivationTokenModel).where(ActivationTokenModel.expires_at < now)
#         result = await db.execute(stmt)
#         expired_tokens = result.scalars().all()
#
#         for token in expired_tokens:
#             await db.delete(token)
#         await db.commit()
