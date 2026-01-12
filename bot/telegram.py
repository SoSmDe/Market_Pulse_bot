"""Telegram bot - без обрезки URL и заголовков"""

from telegram import Bot
from telegram.constants import ParseMode

from collectors.fundraising import FundraisingRound
from collectors.articles import Article


PROTOCOL_EMOJI = {
    "uniswap": "🦄",
    "aave": "👻",
    "lido": "🌊",
    "makerdao": "🏛️",
    "compound": "🔷",
    "curve": "🔴",
    "eigenlayer": "🔲",
    "hyperliquid": "💎",
    "arbitrum": "🔵",
    "optimism": "🔴",
    "base": "🔷",
    "solana": "◎",
    "ethereum_foundation": "⟠",
    "pendle": "🔶",
    "gmx": "🔵",
    "dydx": "🟣",
    "synthetix": "💠",
    "ethena": "💵",
    "jupiter": "🪐",
}

VIP_EMOJI = {
    "a16z": "🅰️",
    "a16z_crypto_substack": "🅰️",
    "paradigm": "🔷",
    "delphi": "🐬",
    "messari": "📊",
    "messari_substack": "📊",
    "coinbase": "🔵",
    "chainalysis": "🔗",
    "ark_invest": "🚀",
    "grayscale": "⬛",
    "vaneck_crypto": "🟠",
    "bitwise": "🔶",
    "franklin_templeton": "🔷",
}


def format_round_type(round_type: str) -> str:
    """Форматирует тип раунда, убирает None/Unknown"""
    if not round_type or round_type.lower() in ['none', 'unknown', '']:
        return ""
    return round_type


def format_digest(
    fundraising: list[FundraisingRound],
    vip_articles: list[Article],
    regular_articles: list[Article],
    is_morning: bool = True,
    priority_topics: list[str] = None
) -> str:
    """Форматирует дайджест БЕЗ обрезки"""

    header = "☀️ MARKET PULSE — Morning" if is_morning else "🌙 MARKET PULSE — Evening"
    parts = [header, ""]

    # === FUNDRAISING ===
    if fundraising:
        parts.append("🔥 FUNDRAISING\n")
        for i, r in enumerate(fundraising[:10], 1):
            amount = f"${r.amount}M" if r.amount else "Undisclosed"
            lead = r.lead_investors[0] if r.lead_investors else "—"
            round_type = format_round_type(r.round_type)

            if round_type:
                parts.append(f"{i}. <b>{r.project}</b> — {amount} {round_type}")
            else:
                parts.append(f"{i}. <b>{r.project}</b> — {amount}")

            parts.append(f"   Lead: {lead}")
            if r.source_url:
                parts.append(f"   🔗 {r.source_url}")
            parts.append("")

    # === VIP: Research & Insights ===
    if vip_articles:
        research = [a for a in vip_articles if a.source_type == "vip"]
        protocols = [a for a in vip_articles if a.source_type == "protocol"]

        if research:
            parts.append("\n🔬 RESEARCH & INSIGHTS\n")
            for a in research[:7]:
                emoji = VIP_EMOJI.get(a.source, "📝")
                parts.append(f"{emoji} <b>{a.title}</b>")
                parts.append(f"   — {a.source}")
                parts.append(f"   🔗 {a.url}")
                parts.append("")

        if protocols:
            parts.append("\n⛓️ PROTOCOL UPDATES\n")
            for a in protocols[:7]:
                emoji = PROTOCOL_EMOJI.get(a.source, "📢")
                parts.append(f"{emoji} <b>{a.title}</b>")
                parts.append(f"   — {a.source}")
                parts.append(f"   🔗 {a.url}")
                parts.append("")

    # === Regular Articles ===
    if regular_articles:
        parts.append("\n📰 NEWS & ARTICLES\n")
        for i, a in enumerate(regular_articles[:10], 1):
            parts.append(f"{i}. <b>{a.title}</b>")
            parts.append(f"   — {a.source}")
            parts.append(f"   🔗 {a.url}")
            parts.append("")

    return "\n".join(parts)


async def send_digest(bot_token: str, chat_id: str, message: str):
    """Отправляет в Telegram с разбивкой на части если нужно"""
    bot = Bot(token=bot_token)

    # Telegram лимит 4096 символов
    if len(message) > 4000:
        # Разбиваем по секциям (двойной перенос строки)
        sections = message.split("\n\n")
        chunks = []
        current = ""

        for section in sections:
            if len(current) + len(section) + 2 < 4000:
                current += section + "\n\n"
            else:
                if current:
                    chunks.append(current.strip())
                current = section + "\n\n"

        if current:
            chunks.append(current.strip())

        for chunk in chunks:
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
