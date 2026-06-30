"""
APScheduler jobs:
  1. Post daily match schedule in channel
  2. Send daily leaderboard via DM
  3. Send pending prediction reminder via DM
"""

import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import db

logger = logging.getLogger(__name__)

CHANNELS = os.environ.get("WC_CHANNELS", "").split(",")


def post_daily_schedule(app):
    """Post today's matches every day at 11 AM IST."""
    from app.bot import _build_schedule_blocks
    matches = db.get_upcoming_matches(limit=5)

    if not matches:
        logger.info("No matches today")
        return

    blocks = _build_schedule_blocks(matches)

    for channel in CHANNELS:
        app.client.chat_postMessage(
            channel=channel.strip(),
            blocks=blocks,
            text="🏆 Today's World Cup Matches"
        )

    logger.info("Posted daily match schedule")


def post_evening_prediction_reminder(app):
    """5 PM reminder to users with pending predictions."""
    from app.bot import _build_reminder_blocks
    matches = db.get_upcoming_matches()

    if not matches:
        logger.info("No matches today for reminder")
        return

    participants = db.get_all_participants()

    for user_id in participants:
        try:
            user_predictions = db.get_user_predictions(user_id)
            predicted_match_ids = [p["match_id"] for p in user_predictions]

            pending_matches = [
                match for match in matches
                if match["id"] not in predicted_match_ids
            ]

            if pending_matches:
                blocks = _build_reminder_blocks(pending_matches)

                app.client.chat_postMessage(
                    channel=user_id,
                    blocks=blocks,
                    text=(
                        "⏰ *YOUGotaGift Prediction Reminder*\n"
                        "You still have pending fixtures for today.\n"
                        "Mark your predictions before kick-off ⚽"
                    )
                )

        except Exception as e:
            logger.error(f"Reminder DM failed for {user_id}: {e}")


def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone="UTC")

    # Daily schedule at 11 AM IST
    scheduler.add_job(
      post_daily_schedule,
      CronTrigger(hour=18, minute=58, timezone="Asia/Kolkata"),
      args=[app],
      id="daily_schedule",
      replace_existing=True,
      misfire_grace_time=300
    )

    # Pending prediction reminder
    scheduler.add_job(
        post_evening_prediction_reminder,
        CronTrigger(hour=19, minute=1, timezone="Asia/Kolkata"),
        args=[app],
        id="evening_prediction_reminder",
        replace_existing=True,
        misfire_grace_time=300
    )

    scheduler.start()
    logger.info("Scheduler started")
