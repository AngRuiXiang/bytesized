# Daily AI Digest — Telegram Bot

Sends a curated AI news digest to a Telegram chat every morning at **8:00 AM Singapore Time**, hosted entirely on GitHub Actions (no server required).

## How it works

1. Fetches recent posts from 7 AI-focused RSS feeds (TechCrunch AI, VentureBeat AI, The Verge AI, Ars Technica, MIT Tech Review, Hacker News, Wired AI)
2. Passes them to **Gemini 2.0 Flash** (free tier) to filter, rank, and summarise the top 5–8 items relevant to business/end-users
3. Sends the formatted digest to your Telegram chat via the Bot API

---

## Setup

### 1. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot`
2. Copy the **Bot Token** it gives you (`123456:ABC-...`)
3. Start a chat with your new bot (or add it to a group)
4. Get your **Chat ID**:
   - For a personal chat: message [@userinfobot](https://t.me/userinfobot) — it returns your user ID
   - For a group: add [@RawDataBot](https://t.me/RawDataBot) briefly to get the group's chat ID (negative number, e.g. `-1001234567890`)

### 2. Get a Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key — the free tier is sufficient (runs once per day)

### 3. Add secrets to GitHub

In your repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Your user ID or group chat ID |
| `GEMINI_API_KEY` | Your Google AI Studio API key |

### 4. Enable GitHub Actions

Push this repo to GitHub. The workflow runs automatically at **00:00 UTC** (08:00 SGT) every day.

To test immediately: **Actions tab → Daily AI Digest → Run workflow**.

---

## Local testing

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
export GEMINI_API_KEY="..."
python main.py
```
