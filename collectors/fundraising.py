"""
Fundraising collector.
- DefiLlama API (неделя)
- RSS новости про fundraising
- Regex extraction из заголовков
"""

import aiohttp
import feedparser
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class FundraisingRound:
    project: str
    amount: Optional[float]
    round_type: str
    lead_investors: list[str] = field(default_factory=list)
    other_investors: list[str] = field(default_factory=list)
    category: str = ""
    date: datetime = None
    source_url: str = ""
    source: str = ""
    score: float = 0.0
    tags: list[str] = field(default_factory=list)


TOP_INVESTORS = [
    "a16z", "Andreessen Horowitz", "Paradigm", "Polychain",
    "Pantera", "Dragonfly", "Multicoin", "Framework",
    "Coinbase Ventures", "Binance Labs", "Sequoia",
    "Galaxy Digital", "Lightspeed", "Bessemer",
    "ICONIQ", "Tiger Global", "SoftBank",
]


def clean_url(url: str) -> str:
    """Убирает UTM параметры из URL"""
    if '?' in url:
        base = url.split('?')[0]
        return base
    return url


async def fetch_defillama_raises() -> list[dict]:
    """DefiLlama API"""
    url = "https://api.llama.fi/raises"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("raises", [])
        except Exception as e:
            print(f"DefiLlama error: {e}")
    return []


def parse_fundraising_rss(feeds: dict, hours: int = 168) -> list[FundraisingRound]:
    """
    Парсит RSS feeds про fundraising и извлекает раунды из заголовков.
    """
    rounds = []
    cutoff = datetime.now() - timedelta(hours=hours)

    # Паттерны для извлечения fundraising
    patterns = [
        r"(.+?)\s+raises?\s+\$?([\d.]+)\s*(million|m|M|billion|b|B)",
        r"(.+?)\s+closes?\s+\$?([\d.]+)\s*(million|m|M|billion|b|B)",
        r"(.+?)\s+secures?\s+\$?([\d.]+)\s*(million|m|M|billion|b|B)",
        r"(.+?)\s+bags?\s+\$?([\d.]+)\s*(million|m|M|billion|b|B)",
        r"(.+?)\s+lands?\s+\$?([\d.]+)\s*(million|m|M|billion|b|B)",
    ]

    round_keywords = ["seed", "series", "funding", "raised", "raises", "investment",
                      "venture", "valuation", "round", "backs", "leads"]

    for source_name, feed_url in feeds.items():
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:30]:
                title = entry.get('title', '')
                title_lower = title.lower()

                # Проверяем, похоже ли на fundraising
                if not any(kw in title_lower for kw in round_keywords):
                    continue

                # Парсим дату
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                else:
                    pub_date = datetime.now()

                if pub_date < cutoff:
                    continue

                # Извлекаем сумму
                amount = None
                for pattern in patterns:
                    match = re.search(pattern, title, re.IGNORECASE)
                    if match:
                        try:
                            amount = float(match.group(2))
                            unit = match.group(3).lower()
                            if unit in ['billion', 'b']:
                                amount *= 1000
                        except:
                            pass
                        break

                # Извлекаем название проекта
                project = "Unknown"
                for pattern in patterns:
                    match = re.search(pattern, title, re.IGNORECASE)
                    if match:
                        project = match.group(1).strip()
                        break

                if project == "Unknown":
                    # Fallback: первые слова до ключевого слова
                    for kw in ["raises", "closes", "secures", "bags", "lands"]:
                        if kw in title_lower:
                            idx = title_lower.index(kw)
                            project = title[:idx].strip()
                            break

                # Определяем тип раунда
                round_type = "Unknown"
                for rt in ["Series D", "Series C", "Series B", "Series A", "Seed", "Pre-Seed", "Strategic"]:
                    if rt.lower() in title_lower:
                        round_type = rt
                        break

                rounds.append(FundraisingRound(
                    project=project[:50],  # лимит длины
                    amount=amount,
                    round_type=round_type,
                    lead_investors=[],
                    other_investors=[],
                    category="",
                    date=pub_date,
                    source_url=clean_url(entry.link),
                    source=source_name
                ))

        except Exception as e:
            print(f"Error parsing {source_name}: {e}")

    return rounds


async def collect_fundraising(hours: int = 168, rss_feeds: dict = None) -> list[FundraisingRound]:
    """
    Собирает fundraising из:
    1. DefiLlama API
    2. RSS feeds (crypto.news, theblock, coindesk)
    """
    all_rounds = []
    cutoff = datetime.now() - timedelta(hours=hours)

    # 1. DefiLlama API
    print("  Fetching DefiLlama...")
    raw_raises = await fetch_defillama_raises()

    # Sort by date descending
    raw_raises_sorted = sorted(raw_raises, key=lambda x: x.get('date', 0), reverse=True)

    for r in raw_raises_sorted:
        date_val = r.get("date", 0)
        if date_val:
            date = datetime.fromtimestamp(date_val)
        else:
            continue

        if date > cutoff:
            all_rounds.append(FundraisingRound(
                project=r.get("name", "Unknown"),
                amount=r.get("amount"),
                round_type=r.get("round", "Unknown"),
                lead_investors=r.get("leadInvestors", []),
                other_investors=r.get("otherInvestors", []),
                category=r.get("category", ""),
                date=date,
                source_url=clean_url(r.get("source", "")),
                source="defillama"
            ))
        else:
            break  # Sorted by date, can stop early

    print(f"  DefiLlama: {len(all_rounds)} rounds")

    # 2. RSS feeds
    if rss_feeds:
        print("  Parsing RSS feeds...")
        rss_rounds = parse_fundraising_rss(rss_feeds, hours)
        all_rounds.extend(rss_rounds)
        print(f"  RSS: {len(rss_rounds)} rounds")

    # Dedupe по project name (case insensitive)
    seen = {}
    unique = []
    for r in all_rounds:
        key = r.project.lower().strip()
        if key not in seen:
            seen[key] = r
            score_fundraising(r)
            unique.append(r)
        else:
            # Если уже есть — берём с большей суммой
            existing = seen[key]
            if (r.amount or 0) > (existing.amount or 0):
                unique.remove(existing)
                seen[key] = r
                score_fundraising(r)
                unique.append(r)

    unique.sort(key=lambda x: x.score, reverse=True)
    print(f"  Total unique: {len(unique)} rounds")

    return unique


def score_fundraising(r: FundraisingRound) -> float:
    """Scoring"""
    score = 0.0

    # Amount
    if r.amount:
        if r.amount >= 100:
            score += 50
        elif r.amount >= 50:
            score += 35
        elif r.amount >= 20:
            score += 25
        elif r.amount >= 10:
            score += 15
        else:
            score += 5

    # Top investors
    all_investors = r.lead_investors + r.other_investors
    for inv in all_investors:
        if any(top.lower() in inv.lower() for top in TOP_INVESTORS):
            score += 20
            break

    # Round type
    round_bonuses = {
        "Series D": 18,
        "Series C": 15,
        "Series B": 12,
        "Series A": 10,
        "Seed": 5,
        "Pre-Seed": 3,
    }
    score += round_bonuses.get(r.round_type, 0)

    # Source bonus (DefiLlama более надёжен)
    if r.source == "defillama":
        score += 5

    r.score = score
    return score
