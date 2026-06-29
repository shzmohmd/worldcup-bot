# ⚽ FIFA World Cup 2026 — Slack Prediction Bot

A fully-featured score prediction bot for your company Slack, built with Python + Supabase + Railway.

---

## 🎮 Features

| Feature | How it works |
|---|---|
| Score predictions | `/wc-predict <match_id>` opens a modal |
| Auto polls | Bot posts 2h before each match + 30-min reminder |
| Leaderboard | `/wc-leaderboard` or auto-posted every morning |
| My picks | `/wc-mypredictions` shows your history & points |
| Match schedule | `/wc-schedule` shows upcoming matches |
| Admin results | `/wc-result <id> <s1> <s2> [pen]` sets result & auto-scores |
| Penalty bonus | Predict shootout winner for +1 pt |

## 📊 Points System

| Prediction | Points |
|---|---|
| 🎯 Exact score (e.g. 2-1 → 2-1) | **3 pts** |
| ⚖️ Correct goal difference (e.g. 2-0 → 3-1) | **2 pts** |
| ✅ Correct winner only | **1 pt** |
| 🥊 Correct penalty winner bonus | **+1 pt** |
| ❌ Wrong result | 0 pts |

---

## 🚀 Setup Guide

### Step 1 — Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → From scratch
2. Name it `World Cup 2026` and select your workspace
3. Under **OAuth & Permissions**, add these **Bot Token Scopes**:
   - `chat:write`
   - `chat:write.public`
   - `commands`
   - `im:write`
   - `users:read`
4. Click **Install to Workspace** and copy the **Bot User OAuth Token** (`xoxb-...`)
5. Under **Basic Information** → copy the **Signing Secret**

### Step 2 — Add Slash Commands

Go to **Slash Commands** and create these (Request URL = your bot URL + `/slack/events`):

| Command | Description |
|---|---|
| `/wc-predict` | Submit a score prediction |
| `/wc-leaderboard` | View the leaderboard |
| `/wc-mypredictions` | See your predictions |
| `/wc-schedule` | Upcoming match schedule |
| `/wc-result` | *(Admin)* Set a match result |

### Step 3 — Enable Interactivity

Under **Interactivity & Shortcuts**:
- Toggle **on**
- Set **Request URL** to `https://your-bot-url.railway.app/slack/actions`

### Step 4 — Set Up Supabase

1. Go to [supabase.com](https://supabase.com) → New project (free tier)
2. In the **SQL Editor**, run the contents of `data/schema.sql`
3. Copy your **Project URL** and **service_role key** from Settings → API

### Step 5 — Deploy to Railway

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Push this repo to GitHub first, then connect it
3. Add these **Environment Variables** in Railway:

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SUPABASE_URL=https://...supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
WC_CHANNEL=#world-cup-2026
ADMIN_USER_IDS=U012AB3CD   ← your Slack user ID
```

4. Railway auto-detects the Procfile and deploys. Copy your Railway URL.
5. Go back to Slack App settings and update your slash command + interactivity URLs.

### Step 6 — Seed Matches & Invite Bot

```bash
# Install dependencies locally first
pip install -r requirements.txt

# Copy and fill env vars
cp .env.example .env

# Seed all 32 knockout matches
python scripts/seed_matches.py
```

Then in Slack, invite the bot to your channel:
```
/invite @World Cup 2026
```

---

## 📋 Admin Commands

```
# Set match result (after the match ends)
/wc-result 1 2 1           → Match 1 result: 2-1
/wc-result 5 1 1 2         → Match 5 result: 1-1, team 2 wins on penalties
```

To find your Slack User ID: Click your profile → ··· → Copy Member ID

---

## 🔄 Updating Team Names

As the tournament progresses, update placeholder team names via Supabase Table Editor or SQL:

```sql
-- After R32 results come in, update R16 teams:
UPDATE matches SET team1 = 'Brazil', team2 = 'France' WHERE id = 17;
```

Or run:
```bash
python scripts/update_teams.py   # (create this file with your updates)
```

---

## 🗂️ Project Structure

```
worldcup-slack-bot/
├── app/
│   ├── bot.py          ← Main Slack app, commands, modals
│   ├── database.py     ← Supabase DB layer
│   ├── scoring.py      ← Points calculation
│   └── scheduler.py    ← Auto polls & reminders
├── data/
│   └── schema.sql      ← Run once in Supabase SQL editor
├── scripts/
│   └── seed_matches.py ← Seeds all 32 matches
├── requirements.txt
├── Procfile            ← Railway/Render deployment
└── .env.example        ← Copy to .env and fill in
```

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| Bot not responding | Check Railway logs; verify Request URL in Slack app settings |
| `401 invalid_auth` | Re-copy Bot Token from Slack app settings |
| Supabase errors | Check service_role key (not anon key) in env vars |
| Scheduler not posting | Make sure `WC_CHANNEL` is set and bot is invited to channel |
