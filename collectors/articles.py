"""
Articles collector с расширенным списком источников.
"""

import feedparser
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Article:
    title: str
    author: str
    url: str
    source: str
    source_type: str
    published_at: datetime
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    tag_appearances: int = 1
    score: float = 0.0
    is_vip: bool = False


GENERIC_TITLES = [
    "here's what happened",
    "what happened in crypto today",
    "daily crypto",
    "crypto news roundup",
    "weekly roundup",
    "this week in crypto",
    "price prediction",
    "price analysis",
]


def is_generic_title(title: str) -> bool:
    title_lower = title.lower()
    return any(g in title_lower for g in GENERIC_TITLES)


def clean_url(url: str) -> str:
    if '?' in url:
        base = url.split('?')[0]
        # Сохраняем важные параметры (например, ID статьи)
        if '/p/' in url or '/post/' in url:
            return url
        return base
    return url


def clean_html(text: str) -> str:
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text(separator=' ', strip=True)


def parse_rss(url: str, source: str, source_type: str, hours: int = 24, is_vip: bool = False) -> list[Article]:
    """Парсит RSS feed"""
    articles = []
    cutoff = datetime.now() - timedelta(hours=hours)

    try:
        feed = feedparser.parse(url)

        for entry in feed.entries[:30]:
            title = entry.get('title', 'No title')

            # Skip generic (но не для VIP)
            if not is_vip and is_generic_title(title):
                continue

            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6])
            else:
                pub_date = datetime.now()

            if pub_date > cutoff:
                articles.append(Article(
                    title=title,
                    author=entry.get('author', source),
                    url=clean_url(entry.link),
                    source=source,
                    source_type=source_type,
                    published_at=pub_date,
                    summary=clean_html(entry.get('summary', ''))[:500],
                    is_vip=is_vip
                ))
    except Exception as e:
        print(f"    Error parsing {source}: {e}")

    return articles


def collect_articles(sources: dict, hours: int = 24) -> tuple[list[Article], list[Article]]:
    """
    Собирает статьи из всех источников.

    Returns:
        (vip_articles, regular_articles)
    """
    vip_articles = []
    regular_articles = []
    seen_urls = set()

    # === VIP Sources ===
    print("  Collecting VIP sources...")
    for name, url in sources.get("vip_sources", {}).items():
        articles = parse_rss(url, name, "vip", hours=48, is_vip=True)
        for a in articles:
            if a.url not in seen_urls:
                seen_urls.add(a.url)
                vip_articles.append(a)
    print(f"    VIP research: {len(vip_articles)}")

    # === Protocol Blogs ===
    print("  Collecting protocol blogs...")
    protocol_count = 0
    for name, url in sources.get("protocol_blogs", {}).items():
        articles = parse_rss(url, name, "protocol", hours=48, is_vip=True)
        for a in articles:
            if a.url not in seen_urls:
                seen_urls.add(a.url)
                vip_articles.append(a)
                protocol_count += 1
    print(f"    Protocols: {protocol_count}")

    # === Main News ===
    print("  Collecting news...")
    news_count = 0
    for name, url in sources.get("news", {}).items():
        articles = parse_rss(url, name, "news", hours=hours, is_vip=False)
        for a in articles:
            if a.url not in seen_urls:
                seen_urls.add(a.url)
                regular_articles.append(a)
                news_count += 1
    print(f"    News: {news_count}")

    # === DeFi News ===
    for name, url in sources.get("news_defi", {}).items():
        articles = parse_rss(url, name, "news", hours=hours, is_vip=False)
        for a in articles:
            if a.url not in seen_urls:
                seen_urls.add(a.url)
                regular_articles.append(a)

    # === Regulation News ===
    for name, url in sources.get("news_regulation", {}).items():
        articles = parse_rss(url, name, "news", hours=hours, is_vip=False)
        for a in articles:
            if a.url not in seen_urls:
                seen_urls.add(a.url)
                regular_articles.append(a)

    # === Substack ===
    print("  Collecting Substack...")
    for name, url in sources.get("substack", {}).items():
        articles = parse_rss(url, name, "substack", hours=hours, is_vip=False)
        for a in articles:
            if a.url not in seen_urls:
                seen_urls.add(a.url)
                regular_articles.append(a)

    # === Russian Sources ===
    print("  Collecting Russian sources...")
    for name, url in sources.get("russian", {}).items():
        articles = parse_rss(url, name, "russian", hours=hours, is_vip=False)
        for a in articles:
            if a.url not in seen_urls:
                seen_urls.add(a.url)
                regular_articles.append(a)

    # === Medium Tags ===
    print("  Collecting Medium tags...")
    url_to_article = {}
    for tag in sources.get("medium_tags", []):
        url = f"https://medium.com/feed/tag/{tag}"
        articles = parse_rss(url, f"medium/{tag}", "medium", hours=hours, is_vip=False)
        for a in articles:
            if a.url in seen_urls:
                continue
            if a.url in url_to_article:
                url_to_article[a.url].tag_appearances += 1
            else:
                url_to_article[a.url] = a

    for a in url_to_article.values():
        if a.url not in seen_urls:
            seen_urls.add(a.url)
            regular_articles.append(a)

    print(f"    Medium: {len(url_to_article)}")

    print(f"  Total: {len(vip_articles)} VIP, {len(regular_articles)} regular")

    return vip_articles, regular_articles


def rank_articles(articles: list[Article], priority_topics: list[str]) -> list[Article]:
    """Ранжирует статьи"""

    # Бонусы по источникам
    SOURCE_BONUSES = {
        # Tier 1
        "coindesk": 25,
        "cointelegraph": 25,
        "theblock": 25,
        "decrypt": 20,
        "dlnews": 20,
        "thedefiant": 20,
        "blockworks": 20,
        # Tier 2
        "bitcoinmagazine": 15,
        "cryptoslate": 15,
        "cryptonews": 15,
        "rekt": 15,
        "cryptobriefing": 15,
        # Substack
        "bankless": 20,
        "week_in_ethereum": 20,
        # Russian
        "forklog": 10,
        "bits_media": 10,
    }

    for a in articles:
        if a.is_vip:
            a.score = 1000
            continue

        score = 0.0

        # Source bonus
        score += SOURCE_BONUSES.get(a.source, 5)

        # Tag appearances (Medium popularity)
        score += a.tag_appearances * 10

        # Source type bonus
        type_bonuses = {"substack": 15, "news": 10, "medium": 5, "russian": 8}
        score += type_bonuses.get(a.source_type, 0)

        # Topic match
        text = f"{a.title} {a.summary}".lower()
        for topic in priority_topics:
            if topic.lower() in text:
                score += 8

        a.score = score

    articles.sort(key=lambda x: (-x.is_vip, -x.score))
    return articles
