"""
FIFA World Cup 2026 Prediction Bot for Slack
Stack: Python + Slack Bolt + Supabase (Postgres)
"""

import os
import json
from datetime import datetime, timezone
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
from dotenv import load_dotenv
from app.database import db
from app.scheduler import start_scheduler
from app.scoring import calculate_points

load_dotenv()

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
    leaders = db.get_leaderboard(limit=15)
    blocks = _build_leaderboard_blocks(leaders)
    client.chat_postEphemeral(
        channel=body["channel_id"],
        user=body["user_id"],
        blocks=blocks,
        text="🏆 World Cup Leaderboard"
    )


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
    if len(parts) < 3:
        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=user_id,
            text="Usage: `/wc-result <match_id> <score1> <score2> [pen_winner: 1 or 2]`\nExample: `/wc-result 5 1 1 2`"
        )
        return

    match_id = parts[0]
    score1 = int(parts[1])
    score2 = int(parts[2])
    pen_winner = int(parts[3]) if len(parts) > 3 else None

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

    # Announce result in channel
    channel = os.environ.get("WC_CHANNEL", body["channel_id"])
    client.chat_postMessage(
        channel=channel,
        blocks=_build_result_announcement(match, score1, score2, pen_winner, predictions),
        text=f"📊 Result: {match['team1']} {score1} – {score2} {match['team2']}"
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
        blocks=blocks
    )


# ─────────────────────────────────────────────
# MODAL SUBMISSION: Prediction
# ─────────────────────────────────────────────

@slack_app.view("submit_prediction")
def handle_prediction_submission(ack, body, view, client):
    ack()
    user_id = body["user"]["id"]
    values = view["state"]["values"]
    match_id = view["private_metadata"]

    score1 = int(values["score1"]["score1_input"]["value"])
    score2 = int(values["score2"]["score2_input"]["value"])
    pen_winner_val = values.get("pen_winner", {}).get("pen_winner_select", {}).get("selected_option")
    pen_winner = int(pen_winner_val["value"]) if pen_winner_val else None

    match = db.get_match(match_id)

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
    match_time = datetime.fromisoformat(match["match_time"]).strftime("%b %d, %Y %H:%M UTC")
    is_knockout = match.get("is_knockout", True)

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{match['team1']}* 🆚 *{match['team2']}*\n📅 {match_time} | 🏟️ {match.get('stage', 'Knockout')}"
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
    rows = []
    for i, row in enumerate(leaders):
        rank = medals[i] if i < 3 else f"*{i+1}.*"
        rows.append(f"{rank} <@{row['user_id']}> — *{row['total_points']} pts* "
                    f"({row['exact_scores']} exact, {row['correct_winners']} winners)")

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🏆 World Cup 2026 Leaderboard"}
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(rows) if rows else "No predictions yet!"}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "🎯 Exact score: 3pts | ✅ Correct winner: 1pt | ⚖️ Correct goal diff: 2pts | 🥊 Penalty winner: +1pt"}]
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
    if not matches:
        return [{"type": "section", "text": {"type": "mrkdwn", "text": "No upcoming matches scheduled."}}]

    rows = []
    for m in matches:
        t = datetime.fromisoformat(m["match_time"]).strftime("%b %d %H:%M UTC")
        rows.append(f"• *#{m['id']}* {m['team1']} 🆚 {m['team2']} — _{m.get('stage', '')}_ | {t}\n  Use `/wc-predict {m['id']}` to predict")

    return [
        {"type": "header", "text": {"type": "plain_text", "text": "📅 Upcoming Matches"}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(rows)}}
    ]


def _build_result_announcement(match, score1, score2, pen_winner, predictions):
    pen_text = ""
    if pen_winner:
        winner_name = match["team1"] if pen_winner == 1 else match["team2"]
        pen_text = f"\n🥊 *Penalties:* {winner_name} win"

    winner = match["team1"] if score1 > score2 else (match["team2"] if score2 > score1 else "Draw")
    winner_text = f"🏆 Winner: *{winner}*" if winner != "Draw" else "🤝 *Draw*"

    # Top predictors for this match
    scored = [p for p in predictions if p.get("points") is not None]
    scored.sort(key=lambda x: x["points"], reverse=True)
    top = scored[:3]
    top_text = ""
    if top:
        top_lines = [f"<@{p['user_id']}> ({p['points']} pts)" for p in top]
        top_text = f"\n\n🎯 *Top predictors:* {', '.join(top_lines)}"

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📊 Final Result: {match['stage']}"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{match['team1']}* *{score1}* – *{score2}* *{match['team2']}*{pen_text}\n"
                    f"{winner_text}{top_text}"
                )
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🏆 View Leaderboard"},
                    "style": "primary",
                    "action_id": "view_leaderboard_button"
                }
            ]
        }
    ]


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


if __name__ == "__main__":
    start_scheduler(slack_app)
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
