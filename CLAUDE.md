# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Market Pulse is a Python Telegram bot for cryptocurrency market monitoring. It collects crypto news from multiple sources (Twitter/Nitter, RSS feeds, DefiLlama scraping) and delivers curated digests twice daily (10:00 and 20:00 MSK).

**Current Status**: Specification exists in `CLAUDE_CODE_SPEC.md`, implementation needs to be built.

## Build & Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# Run digest immediately
python main.py

# Run on schedule (07:00 and 17:00 UTC = 10:00 and 20:00 MSK)
python main.py --schedule
```

## Architecture

```
Data Collection → Filtering & Ranking → Tagging → Formatting → Telegram Delivery
```

### Module Structure

| Module | Purpose |
|--------|---------|
| `collectors/twitter.py` | Nitter RSS scraping for 80+ crypto Twitter accounts |
| `collectors/fundraising.py` | DefiLlama scraping + news regex extraction for fundraising rounds |
| `collectors/articles.py` | RSS aggregation (CoinDesk, Medium, Substack, protocol blogs) |
| `filters/ranker.py` | Score & sort by engagement and topic relevance |
| `filters/tagger.py` | Tag content against priority topics (RWA, DeFi, derivatives, etc.) |
| `bot/telegram.py` | HTML formatting and Telegram API delivery |
| `main.py` | Entry point with scheduler and state management |

### Configuration Files (config/)

- `accounts.json` — Twitter accounts by category (regulatory, vc, founder, research, defi, derivatives, etc.)
- `rss_sources.json` — RSS feed URLs (news, Medium tags/pubs, Substack, protocol blogs)
- `topics.json` — Priority topics for content tagging and scoring
- `settings.json` — Telegram credentials, schedule times, content limits

### Data Models

- `Tweet` — id, author, text, engagement metrics, category, tags, score
- `FundraisingRound` — project, amount, round_type, investors, score
- `Article` — title, source, URL, tags, tag_appearances, score

### Scoring Algorithms

- **Tweets**: `likes + retweets*3 + replies*2 + category_multiplier + topic_bonus`
- **Fundraising**: `amount_bonus + top_investor_bonus + round_type_bonus`
- **Articles**: `tag_appearances*10 + source_bonus + topic_match`

### State Management

`state.json` tracks sent IDs to prevent duplicates. Limits: 1000 tweets, 500 articles, 200 fundraising entries.

## Key Technical Constraints

1. **No paid APIs** — All data sources are free (Nitter RSS, RSS feeds, HTML scraping)
2. **Nitter dependency** — May be unstable; code includes fallback instances (nitter.poast.org, nitter.privacydev.net, nitter.woodland.cafe)
3. **DefiLlama scraping** — Parses `__NEXT_DATA__` script tag; can break on redesigns
4. **Telegram message limit** — 4096 chars; messages split if longer
5. **Async I/O** — All collectors use asyncio/aiohttp
6. **Timezone** — All scheduling uses MSK (Europe/Moscow)
