"""
FIFA World Cup 2026 Prediction Bot for Slack
Stack: Python + Slack Bolt + Supabase (Postgres)
"""

import os
import json
import re
from datetime import datetime, timezone, timedelta
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
from dotenv import load_dotenv
from app.database import db
from app.scheduler import start_scheduler
from app.scoring import calculate_points
import logging
logger = logging.getLogger(__name__)

load_dotenv()

def to_ist(utc_time_str):
    dt = datetime.fromisoformat(utc_time_str)
    ist = dt + timedelta(hours=5, minutes=30)
    return ist.strftime("%d %b | %I:%M %p IST")

# Initialize Slack Bolt app
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)


# ─────────────────────────────────────────────
# SLASH COMMANDS
# ─────────────────────────────────────────────

@slack_app.command("/wc-predict")
def handle_predict(ack, body, client):
    """Open a modal to let user submit a score prediction."""
    ack()
    match_id = body.get("text", "").strip()

    if not match_id:
        # Show list of upcoming matches
        matches = db.get_upcoming_matches(limit=5)
        if not matches:
            client.chat_postEphemeral(
                channel=body["channel_id"],
                user=body["user_id"],
                text="No upcoming matches found. Check back soon! ⚽"
            )
            return
        match_id = str(matches[0]["id"])

    match = db.get_match(match_id)
    if not match:
        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=body["user_id"],
            text=f"Match #{match_id} not found."
        )
        return

    # Check deadline
    match_time = datetime.fromisoformat(match["match_time"])
    if datetime.now(timezone.utc) >= match_time:
        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=body["user_id"],
            text=f"⏰ Predictions for *{match['team1']} vs {match['team2']}* are now closed!"
        )
        return

    client.views_open(
        trigger_id=body["trigger_id"],
        view=_build_prediction_modal(match)
    )


@slack_app.command("/wc-leaderboard")
def handle_leaderboard(ack, body, client):
    """Post the current leaderboard."""
    ack()

    try:
        leaders = db.get_leaderboard(limit=15)
        blocks = _build_leaderboard_blocks(leaders)

        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=body["user_id"],
            blocks=blocks,
            text="🏆 World Cup Leaderboard"
        )
    except Exception as e:
        logger.error(f"Leaderboard failed: {e}")


@slack_app.command("/wc-mypredictions")
def handle_my_predictions(ack, body, client):
    """Show a user's own predictions and scores."""
    ack()
    user_id = body["user_id"]
    predictions = db.get_user_predictions(user_id)
    blocks = _build_my_predictions_blocks(predictions)
    client.chat_postEphemeral(
        channel=body["channel_id"],
        user=body["user_id"],
        blocks=blocks,
        text="⚽ Your Predictions"
    )


@slack_app.command("/wc-result")
def handle_result(ack, body, client):
    """Admin: Set the result of a match. Usage: /wc-result <match_id> <score1> <score2> [pen_winner]"""
    ack()
    user_id = body["user_id"]

    # Check admin
    admins = os.environ.get("ADMIN_USER_IDS", "").split(",")
    if user_id not in admins:
        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=user_id,
            text="🚫 Only admins can set match results."
        )
        return

    parts = body.get("text", "").strip().split()
    if len(parts) == 1:
        match_id = parts[0]
        match = db.get_match(match_id)

        if not match:
            client.chat_postEphemeral(
                channel=body["channel_id"],
                user=user_id,
                text="Match not found."
            )
            return

        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=user_id,
            text=(
                f"📊 *Set Result for Match #{match_id}*\n\n"
                f"1️⃣ {match['team1']}\n"
                f"2️⃣ {match['team2']}\n\n"
                f"Use:\n"
                f"`/wc-result {match_id} <team1_score> <team2_score>`\n\n"
                f"Example:\n"
                f"`/wc-result {match_id} 2 0`\n\n"
                f"If draw:\n"
                f"`/wc-result {match_id} 1 1 1`\n\n"
                f"Penalty winner:\n"
                f"`1 = {match['team1']}`\n"
                f"`2 = {match['team2']}`"
            )
        )
        return

    if len(parts) < 3:
        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=user_id,
            text="Usage: `/wc-result <match_id> <score1> <score2> [pen_winner]`"
        )
        return

    match_id = parts[0]

    try:
        score1 = int(parts[1])
        score2 = int(parts[2])
        pen_winner = int(parts[3]) if len(parts) > 3 else None
    except ValueError:
        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=user_id,
            text="Invalid score input. Use numbers only."
        )
        return

    match = db.get_match(match_id)
    if not match:
        client.chat_postEphemeral(channel=body["channel_id"], user=user_id, text="Match not found.")
        return

    db.set_match_result(match_id, score1, score2, pen_winner)

    # Score all predictions for this match
    predictions = db.get_predictions_for_match(match_id)
    for pred in predictions:
        pts = calculate_points(
            pred["predicted_score1"],
            pred["predicted_score2"],
            pred.get("predicted_pen_winner"),
            score1,
            score2,
            pen_winner
        )

        db.update_prediction_score(pred["id"], pts)
        db.update_user_total_points(pred["user_id"], pts)

        # Stats update
        exact = (
            pred["predicted_score1"] == score1
            and pred["predicted_score2"] == score2
        )

        pred_winner = (
            1 if pred["predicted_score1"] > pred["predicted_score2"]
            else 2 if pred["predicted_score2"] > pred["predicted_score1"]
            else 0
        )

        actual_winner = (
            1 if score1 > score2
            else 2 if score2 > score1
            else 0
        )

        correct_winner = pred_winner == actual_winner

        db.update_user_stats(
            pred["user_id"],
            exact=exact,
            correct_winner=correct_winner
        )

    client.chat_postEphemeral(
        channel=body["channel_id"],
        user=user_id,
        text=(
            f"✅ Result saved successfully:\n"
            f"{match['team1']} {score1} - {score2} {match['team2']}"
        )
    )


@slack_app.command("/wc-schedule")
def handle_schedule(ack, body, client):
    ack()

    matches = db.get_today_matches()

    if not matches:
        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=body["user_id"],
            text="⚽ No matches today."
        )
        return

    blocks = _build_schedule_blocks(matches)

    client.chat_postEphemeral(
        channel=body["channel_id"],
        user=body["user_id"],
        blocks=blocks,
        text="🏆 Today's World Cup Matches"
    )


# ─────────────────────────────────────────────
# MODAL SUBMISSION: Prediction
# ─────────────────────────────────────────────

@slack_app.view("submit_prediction")
def handle_prediction_submission(ack, body, view, client):
    user_id = body["user"]["id"]
    values = view["state"]["values"]
    match_id = view["private_metadata"]

    try:
        score1 = int(values["score1"]["score1_input"]["value"])
        score2 = int(values["score2"]["score2_input"]["value"])
    except ValueError:
        ack(
            response_action="errors",
            errors={
                "score1": "Enter valid number",
                "score2": "Enter valid number"
            }
        )
        return

    if score1 < 0 or score2 < 0:
        ack(
            response_action="errors",
            errors={
                "score1": "Score cannot be negative"
            }
        )
        return

    pen_winner_val = values.get("pen_winner", {}).get("pen_winner_select", {}).get("selected_option")
    pen_winner = int(pen_winner_val["value"]) if pen_winner_val else None

    # Penalty winner validation
    if score1 != score2 and pen_winner:
        ack(
            response_action="errors",
            errors={
                "pen_winner": "Penalty winner should only be selected if the match is a draw."
            }
        )
        return

    if score1 == score2 and not pen_winner:
        ack(
            response_action="errors",
            errors={
                "pen_winner": "Please select penalty winner for a draw."
            }
        )
        return

    match = db.get_match(match_id)
    ack()

    # Upsert prediction
    db.upsert_prediction(user_id, match_id, score1, score2, pen_winner)

    # Confirm to user
    pen_text = ""
    if pen_winner:
        winner_name = match["team1"] if pen_winner == 1 else match["team2"]
        pen_text = f" (Penalties: {winner_name})"

    client.chat_postMessage(
        channel=user_id,
        text=f"✅ Prediction saved!\n*{match['team1']}* {score1} – {score2} *{match['team2']}*{pen_text}\n\nGood luck! 🤞"
    )


# ─────────────────────────────────────────────
# BLOCK BUILDERS
# ─────────────────────────────────────────────

def _build_prediction_modal(match):
    match_id = str(match["id"])
    match_time = to_ist(match["match_time"])
    is_knockout = match.get("is_knockout", True)

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"🏆 *{match.get('stage', 'Knockout')}*\n"
                    f"*{match['team1']}* ⚔️ *{match['team2']}*\n"
                    f"🕒 {match_time}"
                )
            }
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "score1",
            "label": {"type": "plain_text", "text": f"{match['team1']} Goals"},
            "element": {
                "type": "plain_text_input",
                "action_id": "score1_input",
                "placeholder": {"type": "plain_text", "text": "0"},
                "initial_value": "0"
            }
        },
        {
            "type": "input",
            "block_id": "score2",
            "label": {"type": "plain_text", "text": f"{match['team2']} Goals"},
            "element": {
                "type": "plain_text_input",
                "action_id": "score2_input",
                "placeholder": {"type": "plain_text", "text": "0"},
                "initial_value": "0"
            }
        }
    ]

    # Penalty winner option (only for knockout matches)
    if is_knockout:
        blocks.append({
            "type": "input",
            "block_id": "pen_winner",
            "label": {"type": "plain_text", "text": "If draw, who wins on penalties? (optional)"},
            "optional": True,
            "element": {
                "type": "static_select",
                "action_id": "pen_winner_select",
                "placeholder": {"type": "plain_text", "text": "Select team"},
                "options": [
                    {"text": {"type": "plain_text", "text": match["team1"]}, "value": "1"},
                    {"text": {"type": "plain_text", "text": match["team2"]}, "value": "2"}
                ]
            }
        })

    return {
        "type": "modal",
        "callback_id": "submit_prediction",
        "private_metadata": match_id,
        "title": {"type": "plain_text", "text": "⚽ Score Prediction"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks
    }


def _build_leaderboard_blocks(leaders):
    medals = ["🥇", "🥈", "🥉"]

    names = [
        f"@{user['display_name']}"
        if user.get("display_name")
        else f"<@{user['user_id']}>"
        for user in leaders
    ]

    max_name_length = max(len(name) for name in names) if names else 10

    rows = []

    for i, user in enumerate(leaders):
        # Medal separate from rank
        badge = medals[i] if i < 3 else "  "

        # Fixed-width columns
        rank = f"{i+1}.".ljust(8)    
        name = names[i][:20].ljust(20)    
        points = str(user["total_points"]).rjust(3)

        rows.append(f"{badge} {rank}{name}{points}")

    table = (
        f"{'':<2}"        # keep header aligned with medal space
        f"{'Rank'.ljust(8)}"
        f"{'Player'.ljust(21)}"
        f"{'Pts'.ljust(5)}\n"
    )

    table += "\n".join(rows)

    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🏆 World Cup Leaderboard"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{table}```"
            }
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text":
                        "🎯 Exact = 3 pts | ⚖️ Goal Diff = 2 pts | ✅ Winner Pick = 1 pt | 🥊 Penalty Pick = +1 pt"
                }
            ]
        }
    ]


def _build_my_predictions_blocks(predictions):
    if not predictions:
        return [{"type": "section", "text": {"type": "mrkdwn", "text": "You haven't made any predictions yet!\nUse `/wc-predict` to get started. ⚽"}}]

    rows = []
    for p in predictions:
        status = ""
        if p.get("points") is not None:
            status = f" → *{p['points']} pts*"
        elif p.get("result_score1") is None:
            status = " _(pending)_"

        pen = f" (pen: {p['team1'] if p.get('predicted_pen_winner') == 1 else p['team2']})" if p.get("predicted_pen_winner") else ""
        rows.append(f"• *{p['team1']} vs {p['team2']}* — {p['predicted_score1']}:{p['predicted_score2']}{pen}{status}")

    return [
        {"type": "header", "text": {"type": "plain_text", "text": "⚽ Your Predictions"}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(rows)}}
    ]


def _build_schedule_blocks(matches):
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🏆 YOUGotaGift World Cup Prediction Contest"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "R32 | Today’s Fixtures — Lock your predictions now ⚽"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🎯 Mark your score before kick-off."
                }
            ]
        },
        {"type": "divider"}
    ]

    for match in matches:
        blocks.extend([
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text":
                        f"🏆 *{match['team1']} vs {match['team2']}*\n"
                        f"📍 {match['stage']}\n"
                        f"🕒 {to_ist(match['match_time'])}"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "⚽ Predict Now"
                    },
                    "style": "primary",
                    "action_id": f"predict_match_{match['id']}",
                    "value": str(match["id"])
                }
            },
            {"type": "divider"}
        ])

    return blocks


def _build_result_announcement(match, score1, score2, pen_winner, predictions):
    pen_text = ""
    if pen_winner:
        winner_name = match["team1"] if pen_winner == 1 else match["team2"]
        pen_text = f"\n🥊 *Penalties:* {winner_name} win"

    winner = (
        match["team1"] if score1 > score2
        else match["team2"] if score2 > score1
        else "Draw"
    )

    winner_text = (
        f"🏆 Winner: *{winner}*" if winner != "Draw"
        else "🤝 *Match Drawn*"
    )

    # Top predictors for this match
    scored = [p for p in predictions if p.get("points") is not None]
    scored.sort(key=lambda x: x["points"], reverse=True)
    top = scored[:3]

    top_text = "_No top predictors for this match_"
    if top:
        top_lines = [
            f"• <@{p['user_id']}> — *{p['points']} pts*"
            for p in top
        ]
        top_text = "\n".join(top_lines)

    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 Final Result • {match['stage']}"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"⚽ *{match['team1']}* *{score1}* — *{score2}* *{match['team2']}*\n"
                    f"{winner_text}{pen_text}"
                )
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🎯 *Top Predictors*\n{top_text}"
            }
        }
    ]


def _build_reminder_blocks(matches):
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "⏰ Prediction Reminder"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "You still have pending fixtures today. Submit before kick-off ⚽"
            }
        },
        {"type": "divider"}
    ]

    for match in matches:
        blocks.extend([
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text":
                        f"🏆 *{match['team1']} vs {match['team2']}*\n"
                        f"📍 {match['stage']}\n"
                        f"🕒 {to_ist(match['match_time'])}"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "⚽ Predict Now"
                    },
                    "style": "primary",
                    "action_id": f"predict_match_{match['id']}",
                    "value": str(match["id"])
                }
            },
            {"type": "divider"}
        ])

    return blocks


@slack_app.action("view_leaderboard_button")
def handle_leaderboard_button(ack, body, client):
    ack()
    leaders = db.get_leaderboard(limit=15)
    blocks = _build_leaderboard_blocks(leaders)
    client.chat_postEphemeral(
        channel=body["channel"]["id"],
        user=body["user"]["id"],
        blocks=blocks,
        text="🏆 Leaderboard"
    )


@slack_app.action(re.compile("^predict_match_"))
def open_prediction_from_schedule(ack, body, client):
    ack()

    match_id = body["actions"][0]["value"]
    match = db.get_match(match_id)

    if not match:
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=body["user"]["id"],
            text="Match not found."
        )
        return

    client.views_open(
        trigger_id=body["trigger_id"],
        view=_build_prediction_modal(match)
    )


# ─────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/slack/actions", methods=["POST"])
def slack_actions():
    return handler.handle(request)


@flask_app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "worldcup-bot"}, 200


start_scheduler(slack_app)

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
