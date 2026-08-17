"""Optional daily scheduler.

Run: python -m src.scheduler
By default it only generates videos for review (POST_ON_SCHEDULE=false).
Set POST_ON_SCHEDULE=true in .env once you're confident in the pipeline
and your TikTok app has passed audit for public posting.
"""
import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import config
from src.orchestrator import run_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")

POST_ON_SCHEDULE = os.environ.get("POST_ON_SCHEDULE", "false").lower() == "true"
SCHEDULE_HOUR = int(os.environ.get("SCHEDULE_HOUR", "18"))


def job():
    logger.info("Rodando pipeline agendado (post=%s)...", POST_ON_SCHEDULE)
    try:
        result = run_pipeline(niche=config.content_niche, post=POST_ON_SCHEDULE)
        logger.info("Concluido: %s -> %s", result["idea"], result["video_path"])
    except Exception:
        logger.exception("Pipeline agendado falhou")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="America/Sao_Paulo")
    scheduler.add_job(job, "cron", hour=SCHEDULE_HOUR, minute=0)
    logger.info("Agendador iniciado, rodando todo dia as %dh (America/Sao_Paulo).", SCHEDULE_HOUR)
    scheduler.start()
