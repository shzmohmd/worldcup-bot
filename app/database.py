"""
Database layer — Supabase (Postgres) via supabase-py
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self):
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        self.client: Client = create_client(url, key)

    # ─────────────────────────────────────────────
    # MATCHES
    # ─────────────────────────────────────────────

    def get_match(self, match_id: str) -> dict | None:
        res = self.client.table("matches").select("*").eq("id", match_id).single().execute()
        return res.data

    def get_upcoming_matches(self, limit: int = 5) -> list:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        res = (
            self.client.table("matches")
            .select("*")
            .is_("result_score1", "null")
            .gte("match_time", now)
            .order("match_time")
            .limit(limit)
            .execute()
        )
        return res.data or []

    def get_next_match(self) -> dict | None:
        matches = self.get_upcoming_matches(limit=1)
        return matches[0] if matches else None

    def set_match_result(self, match_id: str, score1: int, score2: int, pen_winner: int | None):
        self.client.table("matches").update({
            "result_score1": score1,
            "result_score2": score2,
            "pen_winner": pen_winner
        }).eq("id", match_id).execute()

    # ─────────────────────────────────────────────
    # PREDICTIONS
    # ─────────────────────────────────────────────

    def upsert_prediction(self, user_id: str, match_id: str, score1: int, score2: int, pen_winner: int | None):
        self.client.table("predictions").upsert({
            "user_id": user_id,
            "match_id": int(match_id),
            "predicted_score1": score1,
            "predicted_score2": score2,
            "predicted_pen_winner": pen_winner,
            "points": None
        }, on_conflict="user_id,match_id").execute()

    def get_predictions_for_match(self, match_id: str) -> list:
        res = (
            self.client.table("predictions")
            .select("*")
            .eq("match_id", match_id)
            .execute()
        )
        return res.data or []

    def get_user_predictions(self, user_id: str) -> list:
        res = (
            self.client.table("predictions")
            .select("*, matches(team1, team2, result_score1, result_score2, stage)")
            .eq("user_id", user_id)
            .order("match_id")
            .execute()
        )
        rows = []
        for p in (res.data or []):
            match = p.pop("matches", {}) or {}
            rows.append({**p, **match})
        return rows

    def update_prediction_score(self, prediction_id: int, points: int):
        self.client.table("predictions").update({"points": points}).eq("id", prediction_id).execute()

    # ─────────────────────────────────────────────
    # LEADERBOARD / USERS
    # ─────────────────────────────────────────────

    def update_user_total_points(self, user_id: str, delta: int):
        # Upsert user row and increment
        existing = self.client.table("leaderboard").select("*").eq("user_id", user_id).execute()
        if existing.data:
            row = existing.data[0]
            self.client.table("leaderboard").update({
                "total_points": row["total_points"] + delta
            }).eq("user_id", user_id).execute()
        else:
            self.client.table("leaderboard").insert({
                "user_id": user_id,
                "total_points": delta,
                "exact_scores": 0,
                "correct_winners": 0
            }).execute()

    def update_user_stats(self, user_id: str, exact: bool, correct_winner: bool):
        existing = self.client.table("leaderboard").select("*").eq("user_id", user_id).execute()
        if existing.data:
            row = existing.data[0]
            self.client.table("leaderboard").update({
                "exact_scores": row["exact_scores"] + (1 if exact else 0),
                "correct_winners": row["correct_winners"] + (1 if correct_winner else 0)
            }).eq("user_id", user_id).execute()
        else:
            self.client.table("leaderboard").insert({
                "user_id": user_id,
                "total_points": 0,
                "exact_scores": 1 if exact else 0,
                "correct_winners": 1 if correct_winner else 0
            }).execute()

    def get_leaderboard(self, limit: int = 15) -> list:
        res = (
            self.client.table("leaderboard")
            .select("*")
            .order("total_points", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def get_today_matches(self):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        res = (
            self.client.table("matches")
            .select("*")
            .is_("result_score1", "null")
            .gte("match_time", today_start.isoformat())
            .lte("match_time", today_end.isoformat())
            .order("match_time")
            .execute()
        )

        return res.data or []


db = Database()
