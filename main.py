"""
Market Pulse Bot — с SQLite дедупликацией
"""

import asyncio
import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

import pytz
import schedule
from dotenv import load_dotenv

from collectors.fundraising import collect_fundraising
from collectors.articles import collect_articles, rank_articles, Article
from collectors.scraper import collect_scraped_articles
from filters.tagger import tag_content
from bot.telegram import format_digest, send_digest
from db.database import (
    is_article_sent,
    is_fundraising_sent,
    mark_article_sent,
    mark_fundraising_sent,
    cleanup_old_records,
    get_stats
)

load_dotenv()

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def run_digest():
    print(f"\n{'='*50}")
    print(f"[{datetime.now()}] Running digest...")
    print(f"{'='*50}")

    # Load configs
    rss_sources = load_json(CONFIG_DIR / "rss_sources.json")
    topics = load_json(CONFIG_DIR / "topics.json")
    settings = load_json(CONFIG_DIR / "settings.json")

    priority_topics = topics.get("priority_topics", [])
    fundraising_hours = settings.get("fundraising_hours", 168)

    # DB stats
    stats = get_stats()
    print(f"DB stats: {stats['articles']} articles, {stats['fundraising']} fundraising in history")

    # === COLLECT ===

    # Fundraising
    print("\nCollecting fundraising...")
    fundraising_feeds = rss_sources.get("fundraising_news", {})
    all_fundraising = await collect_fundraising(
        hours=fundraising_hours,
        rss_feeds=fundraising_feeds
    )

    # Filter out already sent
    fundraising = []
    for f in all_fundraising:
        if not is_fundraising_sent(f.project, f.round_type or "unknown"):
            fundraising.append(f)
    print(f"   New fundraising: {len(fundraising)} (filtered {len(all_fundraising) - len(fundraising)} duplicates)")

    # Articles (VIP + regular)
    print("\nCollecting articles...")
    vip_articles, regular_articles = collect_articles(rss_sources, hours=24)

    # Scrape institutional
    print("\nScraping institutional sources...")
    scraped = await collect_scraped_articles()
    for s in scraped:
        vip_articles.append(Article(
            title=s.title,
            author=s.author,
            url=s.url,
            source=s.source,
            source_type="vip",
            published_at=s.published_at or datetime.now(),
            is_vip=True
        ))

    # Filter out already sent articles
    vip_filtered = [a for a in vip_articles if not is_article_sent(a.url)]
    regular_filtered = [a for a in regular_articles if not is_article_sent(a.url)]

    print(f"   VIP: {len(vip_filtered)} new (filtered {len(vip_articles) - len(vip_filtered)} duplicates)")
    print(f"   Regular: {len(regular_filtered)} new (filtered {len(regular_articles) - len(regular_filtered)} duplicates)")

    # Rank regular
    regular_filtered = rank_articles(regular_filtered, priority_topics)

    # Tag
    for a in vip_filtered + regular_filtered:
        a.tags = tag_content(a.title + " " + (a.summary or ""), priority_topics)

    # === FORMAT ===
    msk = pytz.timezone("Europe/Moscow")
    now = datetime.now(msk)
    is_morning = now.hour < 14

    message = format_digest(
        fundraising[:10],
        vip_filtered,
        regular_filtered[:10],
        is_morning=is_morning,
        priority_topics=priority_topics
    )

    # === SEND ===
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("\nTELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        print("\n--- PREVIEW ---\n")
        print(message)
        return

    await send_digest(bot_token, chat_id, message)

    # === MARK AS SENT ===
    print("\nSaving to database...")

    for f in fundraising[:10]:
        mark_fundraising_sent(f.project, f.round_type or "unknown", f.amount, f.source_url)

    for a in vip_filtered:
        mark_article_sent(a.url, a.title, a.source)

    for a in regular_filtered[:10]:
        mark_article_sent(a.url, a.title, a.source)

    print(f"\nDigest sent!")
    print(f"   Fundraising: {len(fundraising[:10])}")
    print(f"   VIP articles: {len(vip_filtered)}")
    print(f"   Regular articles: {min(len(regular_filtered), 10)}")

    # Cleanup old records (once a day)
    if now.hour == 10:
        cleanup_old_records(days=30)


def run_scheduler():
    schedule.every().day.at("07:00").do(lambda: asyncio.run(run_digest()))
    schedule.every().day.at("17:00").do(lambda: asyncio.run(run_digest()))

    print("Scheduler running (07:00, 17:00 UTC = 10:00, 20:00 MSK)")
    print("Press Ctrl+C to stop")

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="Market Pulse Bot")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule")
    parser.add_argument("--stats", action="store_true", help="Show DB stats")
    parser.add_argument("--cleanup", type=int, help="Cleanup records older than N days")
    args = parser.parse_args()

    if args.stats:
        stats = get_stats()
        print(f"Database stats:")
        print(f"  Articles sent: {stats['articles']}")
        print(f"  Fundraising sent: {stats['fundraising']}")
        return

    if args.cleanup:
        cleanup_old_records(days=args.cleanup)
        return

    if args.schedule:
        run_scheduler()
    else:
        asyncio.run(run_digest())


if __name__ == "__main__":
    main()
