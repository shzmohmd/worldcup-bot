"""
Seed all 32 FIFA World Cup 2026 knockout stage matches into Supabase.
Run once: python scripts/seed_matches.py

The team names are placeholders until the group stage completes.
Update the actual team names before each round.

Match IDs 1-32 are reserved for the knockout stage.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

MATCHES = [
    # ── ROUND OF 32 (Round of 16 in expanded WC 2026 = 48 teams → 32 qualify) ──
    # FIFA WC 2026 expands to 48 teams with 32 advancing from groups.
    # The knockout stage is: R32 (32 matches) → R16 → QF → SF → 3rd place + Final
    # Seeding with placeholder names. Update team1/team2 after group stage.

    # ─── ROUND OF 32 ───
    {"id": 1,  "team1": "Group A Winner",   "team2": "Group B Runner-up", "stage": "Round of 32", "match_time": "2026-06-27T18:00:00+00:00", "venue": "MetLife Stadium, New York",   "is_knockout": True},
    {"id": 2,  "team1": "Group B Winner",   "team2": "Group A Runner-up", "stage": "Round of 32", "match_time": "2026-06-27T21:00:00+00:00", "venue": "SoFi Stadium, Los Angeles",  "is_knockout": True},
    {"id": 3,  "team1": "Group C Winner",   "team2": "Group D Runner-up", "stage": "Round of 32", "match_time": "2026-06-28T18:00:00+00:00", "venue": "AT&T Stadium, Dallas",       "is_knockout": True},
    {"id": 4,  "team1": "Group D Winner",   "team2": "Group C Runner-up", "stage": "Round of 32", "match_time": "2026-06-28T21:00:00+00:00", "venue": "Hard Rock Stadium, Miami",   "is_knockout": True},
    {"id": 5,  "team1": "Group E Winner",   "team2": "Group F Runner-up", "stage": "Round of 32", "match_time": "2026-06-29T18:00:00+00:00", "venue": "Arrowhead Stadium, KC",      "is_knockout": True},
    {"id": 6,  "team1": "Group F Winner",   "team2": "Group E Runner-up", "stage": "Round of 32", "match_time": "2026-06-29T21:00:00+00:00", "venue": "Levi's Stadium, San Jose",   "is_knockout": True},
    {"id": 7,  "team1": "Group G Winner",   "team2": "Group H Runner-up", "stage": "Round of 32", "match_time": "2026-06-30T18:00:00+00:00", "venue": "Lincoln Financial, Philly",  "is_knockout": True},
    {"id": 8,  "team1": "Group H Winner",   "team2": "Group G Runner-up", "stage": "Round of 32", "match_time": "2026-06-30T21:00:00+00:00", "venue": "Gillette Stadium, Boston",   "is_knockout": True},
    {"id": 9,  "team1": "Group I Winner",   "team2": "Group J Runner-up", "stage": "Round of 32", "match_time": "2026-07-01T18:00:00+00:00", "venue": "NRG Stadium, Houston",       "is_knockout": True},
    {"id": 10, "team1": "Group J Winner",   "team2": "Group I Runner-up", "stage": "Round of 32", "match_time": "2026-07-01T21:00:00+00:00", "venue": "Estadio Azteca, Mexico City","is_knockout": True},
    {"id": 11, "team1": "Group K Winner",   "team2": "Group L Runner-up", "stage": "Round of 32", "match_time": "2026-07-02T18:00:00+00:00", "venue": "BC Place, Vancouver",        "is_knockout": True},
    {"id": 12, "team1": "Group L Winner",   "team2": "Group K Runner-up", "stage": "Round of 32", "match_time": "2026-07-02T21:00:00+00:00", "venue": "BMO Field, Toronto",         "is_knockout": True},
    {"id": 13, "team1": "Group M Winner",   "team2": "Group N Runner-up", "stage": "Round of 32", "match_time": "2026-07-03T18:00:00+00:00", "venue": "Estadio BBVA, Monterrey",    "is_knockout": True},
    {"id": 14, "team1": "Group N Winner",   "team2": "Group M Runner-up", "stage": "Round of 32", "match_time": "2026-07-03T21:00:00+00:00", "venue": "Rose Bowl, Pasadena",        "is_knockout": True},
    {"id": 15, "team1": "Group O Winner",   "team2": "Group P Runner-up", "stage": "Round of 32", "match_time": "2026-07-04T18:00:00+00:00", "venue": "MetLife Stadium, New York",  "is_knockout": True},
    {"id": 16, "team1": "Group P Winner",   "team2": "Group O Runner-up", "stage": "Round of 32", "match_time": "2026-07-04T21:00:00+00:00", "venue": "SoFi Stadium, Los Angeles",  "is_knockout": True},

    # ─── ROUND OF 16 ───
    {"id": 17, "team1": "Winner Match 1",  "team2": "Winner Match 2",  "stage": "Round of 16", "match_time": "2026-07-09T18:00:00+00:00", "venue": "MetLife Stadium, New York",  "is_knockout": True},
    {"id": 18, "team1": "Winner Match 3",  "team2": "Winner Match 4",  "stage": "Round of 16", "match_time": "2026-07-09T21:00:00+00:00", "venue": "AT&T Stadium, Dallas",       "is_knockout": True},
    {"id": 19, "team1": "Winner Match 5",  "team2": "Winner Match 6",  "stage": "Round of 16", "match_time": "2026-07-10T18:00:00+00:00", "venue": "Hard Rock Stadium, Miami",   "is_knockout": True},
    {"id": 20, "team1": "Winner Match 7",  "team2": "Winner Match 8",  "stage": "Round of 16", "match_time": "2026-07-10T21:00:00+00:00", "venue": "SoFi Stadium, Los Angeles",  "is_knockout": True},
    {"id": 21, "team1": "Winner Match 9",  "team2": "Winner Match 10", "stage": "Round of 16", "match_time": "2026-07-11T18:00:00+00:00", "venue": "Estadio Azteca, Mexico City","is_knockout": True},
    {"id": 22, "team1": "Winner Match 11", "team2": "Winner Match 12", "stage": "Round of 16", "match_time": "2026-07-11T21:00:00+00:00", "venue": "BC Place, Vancouver",        "is_knockout": True},
    {"id": 23, "team1": "Winner Match 13", "team2": "Winner Match 14", "stage": "Round of 16", "match_time": "2026-07-12T18:00:00+00:00", "venue": "Estadio BBVA, Monterrey",    "is_knockout": True},
    {"id": 24, "team1": "Winner Match 15", "team2": "Winner Match 16", "stage": "Round of 16", "match_time": "2026-07-12T21:00:00+00:00", "venue": "Rose Bowl, Pasadena",        "is_knockout": True},

    # ─── QUARTER-FINALS ───
    {"id": 25, "team1": "Winner Match 17", "team2": "Winner Match 18", "stage": "Quarter-Final", "match_time": "2026-07-16T18:00:00+00:00", "venue": "MetLife Stadium, New York",  "is_knockout": True},
    {"id": 26, "team1": "Winner Match 19", "team2": "Winner Match 20", "stage": "Quarter-Final", "match_time": "2026-07-16T21:00:00+00:00", "venue": "SoFi Stadium, Los Angeles",  "is_knockout": True},
    {"id": 27, "team1": "Winner Match 21", "team2": "Winner Match 22", "stage": "Quarter-Final", "match_time": "2026-07-17T18:00:00+00:00", "venue": "AT&T Stadium, Dallas",       "is_knockout": True},
    {"id": 28, "team1": "Winner Match 23", "team2": "Winner Match 24", "stage": "Quarter-Final", "match_time": "2026-07-17T21:00:00+00:00", "venue": "Hard Rock Stadium, Miami",   "is_knockout": True},

    # ─── SEMI-FINALS ───
    {"id": 29, "team1": "Winner QF 1",     "team2": "Winner QF 2",     "stage": "Semi-Final",   "match_time": "2026-07-21T21:00:00+00:00", "venue": "MetLife Stadium, New York",  "is_knockout": True},
    {"id": 30, "team1": "Winner QF 3",     "team2": "Winner QF 4",     "stage": "Semi-Final",   "match_time": "2026-07-22T21:00:00+00:00", "venue": "Rose Bowl, Pasadena",        "is_knockout": True},

    # ─── 3RD PLACE ───
    {"id": 31, "team1": "SF1 Loser",       "team2": "SF2 Loser",       "stage": "3rd Place Play-off", "match_time": "2026-07-25T20:00:00+00:00", "venue": "Hard Rock Stadium, Miami", "is_knockout": True},

    # ─── FINAL ───
    {"id": 32, "team1": "SF1 Winner",      "team2": "SF2 Winner",      "stage": "🏆 FINAL",     "match_time": "2026-07-26T21:00:00+00:00", "venue": "MetLife Stadium, New York",  "is_knockout": True},
]


def seed():
    print("Seeding matches...")
    for match in MATCHES:
        try:
            client.table("matches").upsert(match, on_conflict="id").execute()
            print(f"  ✅ Match {match['id']}: {match['team1']} vs {match['team2']} ({match['stage']})")
        except Exception as e:
            print(f"  ❌ Match {match['id']} failed: {e}")
    print(f"\nDone! {len(MATCHES)} matches seeded.")


if __name__ == "__main__":
    seed()
