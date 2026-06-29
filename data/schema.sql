-- ============================================================
-- FIFA World Cup 2026 Prediction Bot — Supabase Schema
-- Run this in your Supabase SQL Editor before deploying
-- ============================================================

-- MATCHES TABLE
CREATE TABLE IF NOT EXISTS matches (
    id              INTEGER PRIMARY KEY,
    team1           TEXT NOT NULL,
    team2           TEXT NOT NULL,
    stage           TEXT NOT NULL DEFAULT 'Knockout',
    match_time      TIMESTAMPTZ NOT NULL,
    venue           TEXT,
    is_knockout     BOOLEAN DEFAULT TRUE,
    result_score1   INTEGER,
    result_score2   INTEGER,
    pen_winner      INTEGER,         -- 1 = team1, 2 = team2
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- PREDICTIONS TABLE
CREATE TABLE IF NOT EXISTS predictions (
    id                    BIGSERIAL PRIMARY KEY,
    user_id               TEXT NOT NULL,              -- Slack user ID (e.g. U012AB3CD)
    match_id              INTEGER NOT NULL REFERENCES matches(id),
    predicted_score1      INTEGER NOT NULL,
    predicted_score2      INTEGER NOT NULL,
    predicted_pen_winner  INTEGER,                    -- 1 or 2
    points                INTEGER,                    -- NULL until result is set
    submitted_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, match_id)                        -- one prediction per user per match
);

-- LEADERBOARD TABLE (denormalized for fast reads)
CREATE TABLE IF NOT EXISTS leaderboard (
    user_id         TEXT PRIMARY KEY,
    total_points    INTEGER DEFAULT 0,
    exact_scores    INTEGER DEFAULT 0,
    correct_winners INTEGER DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- INDEXES for common queries
CREATE INDEX IF NOT EXISTS idx_predictions_user    ON predictions (user_id);
CREATE INDEX IF NOT EXISTS idx_predictions_match   ON predictions (match_id);
CREATE INDEX IF NOT EXISTS idx_matches_time        ON matches (match_time);
CREATE INDEX IF NOT EXISTS idx_leaderboard_points  ON leaderboard (total_points DESC);

-- Enable Row Level Security (RLS) — bot uses service role key so it bypasses
ALTER TABLE matches     ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaderboard ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- HELPFUL VIEWS
-- ============================================================

-- Full leaderboard with rank
CREATE OR REPLACE VIEW leaderboard_ranked AS
SELECT
    ROW_NUMBER() OVER (ORDER BY total_points DESC, exact_scores DESC) AS rank,
    user_id,
    total_points,
    exact_scores,
    correct_winners
FROM leaderboard;

-- Match results with prediction count
CREATE OR REPLACE VIEW match_summary AS
SELECT
    m.id,
    m.team1,
    m.team2,
    m.stage,
    m.match_time,
    m.venue,
    m.result_score1,
    m.result_score2,
    m.pen_winner,
    COUNT(p.id) AS prediction_count,
    AVG(p.predicted_score1)::NUMERIC(4,1) AS avg_pred_score1,
    AVG(p.predicted_score2)::NUMERIC(4,1) AS avg_pred_score2
FROM matches m
LEFT JOIN predictions p ON p.match_id = m.id
GROUP BY m.id;
