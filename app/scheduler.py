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

CHANNEL = os.environ.get("WC_CHANNEL")


def post_daily_leaderboard(app):
    """Send leaderboard to all participants every day."""
    from app.bot import _build_leaderboard_blocks
    top_leaders = db.get_leaderboard(limit=15)
    all_users = db.get_leaderboard()

    if not top_leaders:
        return

    blocks = _build_leaderboard_blocks(top_leaders)

    for user in all_users:
        try:
            user_rank = db.get_user_rank(user["user_id"])
            user_blocks = blocks.copy()

            if user_rank and user_rank["rank"] > 15:
                user_blocks.append({"type": "divider"})
                user_blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text":
                            f"📍 *Your Rank:* #{user_rank['rank']} — *{user_rank['points']} pts*"
                    }
                })

            app.client.chat_postMessage(
                channel=user["user_id"],
                blocks=user_blocks,
                text="🏆 Daily Leaderboard Update"
            )
        except Exception as e:
            logger.error(f"Leaderboard DM failed for {user['user_id']}: {e}")


def post_daily_schedule(app):
    """Post today's matches every day at 11 AM IST."""
    from app.bot import _build_schedule_blocks
    matches = db.get_today_matches()

    if not matches:
        logger.info("No matches today")
        return

    blocks = _build_schedule_blocks(matches)

    app.client.chat_postMessage(
        channel=CHANNEL,
        blocks=blocks,
        text="🏆 Today's World Cup Matches"
    )

    logger.info("Posted daily match schedule")


def post_evening_prediction_reminder(app):
    """5 PM reminder to users with pending predictions."""
    from app.bot import _build_schedule_blocks
    matches = db.get_today_matches()

    if not matches:
        logger.info("No matches today for reminder")
        return

    leaders = db.get_leaderboard()

    for user in leaders:
        try:
            user_predictions = db.get_user_predictions(user["user_id"])
            predicted_match_ids = [p["match_id"] for p in user_predictions]

            pending_matches = [
                match for match in matches
                if match["id"] not in predicted_match_ids
            ]

            if pending_matches:
                blocks = _build_schedule_blocks(pending_matches)

                app.client.chat_postMessage(
                    channel=user["user_id"],
                    blocks=blocks,
                    text="⏰ Reminder! You still have pending World Cup predictions."
                )

        except Exception as e:
            logger.error(f"Reminder DM failed for {user['user_id']}: {e}")


def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone="UTC")

    # Daily schedule at 11 AM IST
    scheduler.add_job(
      post_daily_schedule,
      CronTrigger(hour=15, minute=05, timezone="Asia/Kolkata"),
      args=[app],
      id="daily_schedule",
      replace_existing=True,
      misfire_grace_time=300
    )

    # Daily leaderboard DM at 11 AM IST
    scheduler.add_job(
      post_daily_leaderboard,
      CronTrigger(hour=15, minute=15, timezone="Asia/Kolkata"),
      args=[app],
      id="daily_leaderboard",
      replace_existing=True,
      misfire_grace_time=300
    )

    # Pending prediction reminder
    scheduler.add_job(
        post_evening_prediction_reminder,
        CronTrigger(hour=15, minute=10, timezone="Asia/Kolkata"),
        args=[app],
        id="evening_prediction_reminder",
        replace_existing=True,
        misfire_grace_time=300
    )

    scheduler.start()
    logger.info("Scheduler started")
