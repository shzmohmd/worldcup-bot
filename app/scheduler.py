"""
APScheduler jobs:
  1. Post a match poll 2 hours before each match
  2. Post a reminder 30 minutes before kick-off
  3. Post leaderboard every morning at 9am UTC
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import db

logger = logging.getLogger(__name__)

CHANNEL = os.environ.get("WC_CHANNEL", "#world-cup-2026")


def post_match_poll(app, match):
    """Post a pre-match prediction reminder to the channel."""
    match_time = datetime.fromisoformat(match["match_time"]).strftime("%b %d, %H:%M UTC")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"⚽ Time to Predict! — {match.get('stage', 'Knockout')}"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{match['team1']}* 🆚 *{match['team2']}*\n"
                    f"🕐 Kick-off: *{match_time}*\n"
                    f"🏟️ Venue: {match.get('venue', 'TBD')}\n\n"
                    f"Submit your score prediction before kick-off!\n"
                    f"Use `/wc-predict {match['id']}` to enter your prediction."
                )
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "⚽ Predict Score"},
                    "style": "primary",
                    "action_id": f"predict_match_{match['id']}",
                    "value": str(match["id"])
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📊 Leaderboard"},
                    "action_id": "view_leaderboard_button"
                }
            ]
        }
    ]

    app.client.chat_postMessage(
        channel=CHANNEL,
        blocks=blocks,
        text=f"⚽ Predict: {match['team1']} vs {match['team2']}"
    )


def post_closing_reminder(app, match):
    """30-minute warning before predictions close."""
    app.client.chat_postMessage(
        channel=CHANNEL,
        text=(
            f"⏰ *30 minutes left!* Predictions close at kick-off for "
            f"*{match['team1']} vs {match['team2']}*.\n"
            f"Use `/wc-predict {match['id']}` to submit yours! 🔒"
        )
    )


def post_daily_leaderboard(app):
    """Post the leaderboard each morning."""
    leaders = db.get_leaderboard(limit=10)
    if not leaders:
        return

    medals = ["🥇", "🥈", "🥉"]
    rows = []
    for i, row in enumerate(leaders):
        rank = medals[i] if i < 3 else f"*{i+1}.*"
        rows.append(f"{rank} <@{row['user_id']}> — *{row['total_points']} pts*")

    app.client.chat_postMessage(
        channel=CHANNEL,
        blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🌅 Good morning! Today's Leaderboard"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(rows)}
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "Use `/wc-schedule` to see today's matches | `/wc-mypredictions` for your picks"}]
            }
        ],
        text="🏆 World Cup 2026 Leaderboard"
    )


def check_and_schedule_match_jobs(app, scheduler):
    """
    Run every hour: look at upcoming matches and schedule
    poll & reminder jobs if not already scheduled.
    """
    from datetime import timedelta
    matches = db.get_upcoming_matches(limit=10)
    now = datetime.now(timezone.utc)

    for match in matches:
        match_time = datetime.fromisoformat(match["match_time"])
        if match_time.tzinfo is None:
            match_time = match_time.replace(tzinfo=timezone.utc)

        poll_time = match_time - timedelta(hours=2)
        reminder_time = match_time - timedelta(minutes=30)

        poll_job_id = f"poll_{match['id']}"
        reminder_job_id = f"reminder_{match['id']}"

        if poll_time > now and not scheduler.get_job(poll_job_id):
            scheduler.add_job(
                post_match_poll,
                "date",
                run_date=poll_time,
                args=[app, match],
                id=poll_job_id,
                replace_existing=True
            )
            logger.info(f"Scheduled poll for match {match['id']} at {poll_time}")

        if reminder_time > now and not scheduler.get_job(reminder_job_id):
            scheduler.add_job(
                post_closing_reminder,
                "date",
                run_date=reminder_time,
                args=[app, match],
                id=reminder_job_id,
                replace_existing=True
            )
            logger.info(f"Scheduled reminder for match {match['id']} at {reminder_time}")


def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone="UTC")

    # Daily leaderboard at 9am UTC
    scheduler.add_job(
        post_daily_leaderboard,
        CronTrigger(hour=9, minute=0),
        args=[app],
        id="daily_leaderboard"
    )

    # Re-check for new matches every hour
    scheduler.add_job(
        check_and_schedule_match_jobs,
        CronTrigger(minute=0),
        args=[app, scheduler],
        id="check_matches"
    )

    scheduler.start()
    logger.info("Scheduler started")

    # Run immediately on startup
    check_and_schedule_match_jobs(app, scheduler)
