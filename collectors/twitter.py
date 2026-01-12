"""
Twitter collector via Nitter RSS.

Nitter instances (fallback):
- nitter.poast.org
- nitter.privacydev.net
- nitter.woodland.cafe

RSS format: https://{instance}/{handle}/rss
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
import feedparser

NITTER_INSTANCES = [
    "nitter.net",
    "nitter.cz",
    "nitter.poast.org",
    "nitter.privacydev.net",
]


@dataclass
class Tweet:
    id: str
    author: str
    author_category: str
    text: str
    url: str
    likes: int
    retweets: int
    replies: int
    created_at: datetime
    has_media: bool
    score: float = 0.0
    tags: list = field(default_factory=list)


async def get_working_nitter() -> Optional[str]:
    """Find a working Nitter instance."""
    async with aiohttp.ClientSession() as session:
        for instance in NITTER_INSTANCES:
            try:
                async with session.get(
                    f"https://{instance}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        return instance
            except Exception:
                continue
    return None


def parse_nitter_rss(
    feed_url: str,
    handle: str,
    category: str,
    hours: int = 12
) -> list[Tweet]:
    """Parse RSS feed from Nitter."""
    tweets = []
    cutoff = datetime.now() - timedelta(hours=hours)

    try:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:20]:
            # Parse date
            pub_date = None
            if entry.get('published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6])
            else:
                pub_date = datetime.now()

            if pub_date > cutoff:
                # Nitter RSS doesn't provide engagement metrics, set to 0
                tweet_id = entry.link.split('/')[-1] if entry.link else str(hash(entry.title))

                # Convert Nitter URL to Twitter URL
                twitter_url = entry.link
                for instance in NITTER_INSTANCES:
                    twitter_url = twitter_url.replace(instance, 'twitter.com')

                tweets.append(Tweet(
                    id=tweet_id,
                    author=handle,
                    author_category=category,
                    text=entry.title[:280] if entry.title else "",
                    url=twitter_url,
                    likes=0,
                    retweets=0,
                    replies=0,
                    created_at=pub_date,
                    has_media='pic.twitter.com' in entry.get('summary', ''),
                    tags=[]
                ))
    except Exception as e:
        print(f"Error parsing {handle}: {e}")

    return tweets


async def collect_tweets(accounts: list[dict], hours: int = 12) -> list[Tweet]:
    """
    Collect tweets from all accounts.

    accounts: [{"handle": "cobie", "category": "defi"}, ...]
    """
    nitter = await get_working_nitter()
    if not nitter:
        print("No working Nitter instance found!")
        return []

    print(f"Using Nitter instance: {nitter}")
    all_tweets = []

    for account in accounts:
        handle = account['handle']
        category = account['category']

        feed_url = f"https://{nitter}/{handle}/rss"
        tweets = parse_nitter_rss(feed_url, handle, category, hours)
        all_tweets.extend(tweets)

        await asyncio.sleep(0.5)  # Rate limiting

    return all_tweets
