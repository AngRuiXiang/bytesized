import html
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import feedparser
import google.generativeai as genai
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)

RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://www.technologyreview.com/feed/",
    "https://hnrss.org/newest?q=artificial+intelligence&points=100",
    "https://www.wired.com/feed/tag/artificial-intelligence/latest/rss",
]

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

SGT = timezone(timedelta(hours=8))
GEMINI_MODEL = "gemini-2.5-flash-lite"
MAX_SUMMARY_CHARS = 600
TELEGRAM_MAX_CHARS = 4096


def strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_recent_items(hours: int = 48) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[dict] = []

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(
                feed_url,
                agent="AI-Digest-Bot/1.0 (github.com/user/bytesized)",
            )
            source_name = feed.feed.get("title", feed_url)
            for entry in feed.entries:
                published = None
                for attr in ("published_parsed", "updated_parsed"):
                    parsed = getattr(entry, attr, None)
                    if parsed:
                        published = datetime(*parsed[:6], tzinfo=timezone.utc)
                        break

                if published and published >= cutoff:
                    items.append(
                        {
                            "title": strip_html(entry.get("title", "")),
                            "url": entry.get("link", ""),
                            "summary": strip_html(
                                entry.get("summary", entry.get("description", ""))
                            )[:MAX_SUMMARY_CHARS],
                            "source": source_name,
                            "published": published.isoformat(),
                        }
                    )
        except Exception as exc:
            logging.error("Failed to fetch %s: %s", feed_url, exc)

    logging.info("Collected %d raw items from feeds", len(items))
    return items


def filter_and_summarize(items: list[dict]) -> str:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = f"""You are a curator for a daily AI news digest aimed at business users and end users (not researchers).

Below are raw RSS items from the last 48 hours in JSON:
{json.dumps(items, ensure_ascii=False, indent=2)}

INSTRUCTIONS:
1. INCLUDE items about: new model/product launches, new AI capabilities, agentic AI tools, open-source AI tools, AI in enterprise, responsible AI, prompt injection attacks or defenses, AI startup funding with clear product impact.
2. EXCLUDE: pure academic papers (arXiv, benchmark studies, dataset releases) unless they have immediate real-world business impact. Also exclude duplicates — keep the most informative version.
3. Pick the top 5–8 most relevant and impactful items.
4. For each selected item, write exactly this block (Telegram HTML format):

<b>Short descriptive title (max 10 words)</b>
• What happened — one plain-English sentence.
• Why it matters / who it affects — one plain-English sentence.
<a href="ORIGINAL_ARTICLE_URL">Read more</a>

5. Separate items with a blank line.
6. If fewer than 3 items are relevant, output only the exact string: NO_RELEVANT_NEWS

Output only the formatted digest. No preamble, no sign-off, no commentary."""

    response = model.generate_content(prompt)
    return response.text.strip()


def send_telegram(text: str) -> None:
    if len(text) > TELEGRAM_MAX_CHARS:
        text = text[: TELEGRAM_MAX_CHARS - 30] + "\n\n<i>…digest truncated</i>"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    logging.info("Telegram response: %s", resp.json().get("ok"))


def main() -> None:
    today = datetime.now(SGT).strftime("%A, %d %B %Y").lstrip("0").replace(" 0", " ")
    header = f"🤖 <b>AI News Digest — {today}</b>\n\n"

    items = fetch_recent_items(hours=48)

    if not items:
        logging.warning("No items fetched — all feeds may be down")
        send_telegram(header + "No major AI updates today — feeds were unreachable.")
        return

    logging.info("Calling Gemini to filter and summarise...")
    try:
        digest = filter_and_summarize(items)
    except Exception as exc:
        logging.error("Gemini API call failed: %s", exc)
        sys.exit(1)

    if digest == "NO_RELEVANT_NEWS":
        logging.info("Gemini found no relevant items")
        send_telegram(header + "No major AI updates today that meet our focus criteria.")
        return

    logging.info("Sending digest to Telegram...")
    send_telegram(header + digest)
    logging.info("Done.")


if __name__ == "__main__":
    main()
