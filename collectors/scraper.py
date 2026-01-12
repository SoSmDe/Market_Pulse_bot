"""
Scraper для сайтов без RSS (ARK Invest, Grayscale, Bitwise)
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup


@dataclass
class ScrapedArticle:
    title: str
    url: str
    source: str
    published_at: Optional[datetime]
    author: str = ""
    summary: str = ""
    tags: list = field(default_factory=list)


async def scrape_ark_invest(hours: int = 72) -> list[ScrapedArticle]:
    """
    Scrape ARK Invest articles
    https://www.ark-invest.com/articles
    """
    url = "https://www.ark-invest.com/articles"
    articles = []

    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'lxml')

                # ARK uses cards with links
                article_links = soup.find_all('a', href=re.compile(r'/articles/'))

                seen_urls = set()
                for link in article_links:
                    href = link.get('href', '')
                    if href in seen_urls or not href:
                        continue
                    seen_urls.add(href)

                    # Получаем заголовок
                    title_elem = link.find(['h2', 'h3', 'h4'])
                    if not title_elem:
                        title_elem = link

                    title = title_elem.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue

                    # Фильтруем только crypto-related
                    crypto_keywords = ['bitcoin', 'crypto', 'blockchain', 'defi',
                                       'stablecoin', 'digital asset', 'ethereum']
                    title_lower = title.lower()
                    if not any(kw in title_lower for kw in crypto_keywords):
                        # Проверяем теги если есть
                        tags_text = str(link.parent)
                        if not any(kw in tags_text.lower() for kw in crypto_keywords):
                            continue

                    full_url = f"https://www.ark-invest.com{href}" if href.startswith('/') else href

                    articles.append(ScrapedArticle(
                        title=title,
                        url=full_url,
                        source="ark_invest",
                        published_at=datetime.now(),
                        author="ARK Invest"
                    ))

                    if len(articles) >= 10:
                        break

        except Exception as e:
            print(f"    Error scraping ARK: {e}")

    return articles[:5]


async def scrape_grayscale_research(hours: int = 72) -> list[ScrapedArticle]:
    """
    Scrape Grayscale Research
    https://research.grayscale.com/
    """
    url = "https://research.grayscale.com/"
    articles = []

    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": "Mozilla/5.0"}

        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'lxml')

                # Grayscale использует карточки
                cards = soup.find_all(['article', 'div'], class_=re.compile(r'card|post|article'))

                for card in cards[:10]:
                    link = card.find('a', href=True)
                    if not link:
                        continue

                    title_elem = card.find(['h2', 'h3', 'h4'])
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    href = link.get('href', '')

                    if not title or not href:
                        continue

                    full_url = f"https://research.grayscale.com{href}" if href.startswith('/') else href

                    articles.append(ScrapedArticle(
                        title=title,
                        url=full_url,
                        source="grayscale",
                        published_at=datetime.now(),
                        author="Grayscale Research"
                    ))

        except Exception as e:
            print(f"    Error scraping Grayscale: {e}")

    return articles[:5]


async def collect_scraped_articles() -> list[ScrapedArticle]:
    """Собирает статьи со всех scrape источников"""
    all_articles = []

    print("  Scraping ARK Invest...")
    ark = await scrape_ark_invest()
    all_articles.extend(ark)
    print(f"    ARK: {len(ark)} articles")

    print("  Scraping Grayscale...")
    grayscale = await scrape_grayscale_research()
    all_articles.extend(grayscale)
    print(f"    Grayscale: {len(grayscale)} articles")

    return all_articles
