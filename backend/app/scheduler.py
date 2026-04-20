import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import async_session_factory

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def start_scheduler(hour: int = 6, minute: int = 0) -> None:
    from app.services import ingestion_service
    from app.services.llm_service import get_llm_service

    async def _scheduled_ingestion():
        logger.info("Scheduled ingestion starting")
        try:
            llm = get_llm_service()
            async with async_session_factory() as db:
                await ingestion_service.run_ingestion(db, llm, triggered_by="scheduler")
        except Exception:
            logger.exception("Scheduled ingestion failed")

    scheduler.add_job(_scheduled_ingestion, "cron", hour=hour, minute=minute, id="daily_ingestion", replace_existing=True)
    if not scheduler.running:
        scheduler.start()
    logger.info(f"Scheduler started: daily ingestion at {hour:02d}:{minute:02d}")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
