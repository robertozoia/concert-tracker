from __future__ import annotations

import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from .config import settings
from .db import SessionLocal
from .models import Event
from .scraper import scrape_all

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_scrape() -> None:
    logger.info("Starting scheduled scrape")
    try:
        stats = scrape_all()
        logger.info("Scrape complete: %s", stats.to_dict())
    except Exception:
        logger.exception("Scheduled scrape failed")


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    sched = BackgroundScheduler(timezone=settings.timezone)
    sched.add_job(
        _run_scrape,
        trigger=CronTrigger(hour=settings.scrape_hour, minute=0, timezone=settings.timezone),
        id="daily-scrape",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sched.start()
    _scheduler = sched
    logger.info("Scheduler started; daily scrape at %02d:00 %s", settings.scrape_hour, settings.timezone)

    _maybe_initial_backfill()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _maybe_initial_backfill() -> None:
    with SessionLocal() as session:
        any_event = session.execute(select(Event.id).limit(1)).scalar_one_or_none()
    if any_event is not None:
        return
    logger.info("Empty database — kicking off initial backfill in background thread")
    threading.Thread(target=_run_scrape, name="initial-backfill", daemon=True).start()
