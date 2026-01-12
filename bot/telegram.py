"""Telegram bot - без обрезки URL и заголовков"""

import io
from telegram import Bot
from telegram.constants import ParseMode

from collectors.fundraising import FundraisingRound
from collectors.articles import Article


SUMMARY_PROMPT = '''Ты — криптоаналитик. Проанализируй дайджест крипто-новостей ниже.

## Твои задачи:

1. **Прочитай каждую ссылку** — зайди внутрь и посмотри полный текст статьи
   - Если доступа нет — напиши "⚠️ Нет доступа к [URL]" и найди похожую новость в интернете
   - Используй найденную информацию, но отметь что оригинал недоступен

2. **Отфильтруй мусор** — игнорируй:
   - Рекламные статьи и спонсорский контент
   - Повторяющиеся новости об одном и том же
   - Незначительные события (мелкие листинги, минорные апдейты)
   - Кликбейт без содержания

3. **Сделай анализ:**

### 📋 КРАТКАЯ ВЫЖИМКА (5-7 ключевых событий)
Только важное. 1-2 предложения на каждое событие.

### 📊 НАСТРОЕНИЕ РЫНКА
- Bullish / Bearish / Neutral
- Почему? (2-3 причины)

### ⚡ НА ЧТО ОБРАТИТЬ ВНИМАНИЕ
- 1-3 события которые могут повлиять на рынок в ближайшее время

### ⚠️ НЕДОСТУПНЫЕ ИСТОЧНИКИ (если есть)
Список ссылок к которым не было доступа

---

Формат: кратко, по делу, на русском. Без воды и общих фраз.

=== ДАЙДЖЕСТ ===

'''


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


def generate_prompt_file(digest: str) -> io.BytesIO:
    """Генерирует файл с промптом + дайджестом для отправки в Claude"""
    content = SUMMARY_PROMPT + digest

    # Создаём байтовый поток для отправки как файл
    file_buffer = io.BytesIO()
    file_buffer.write(content.encode('utf-8'))
    file_buffer.seek(0)
    file_buffer.name = "digest_for_claude.txt"

    return file_buffer


async def send_digest(bot_token: str, chat_id: str, message: str):
    """Отправляет в Telegram с разбивкой на части если нужно + файл для Claude"""
    bot = Bot(token=bot_token)

    # Отправляем файл с промптом + дайджестом для Claude
    prompt_file = generate_prompt_file(message)
    await bot.send_document(
        chat_id=chat_id,
        document=prompt_file,
        filename="digest_for_claude.txt",
        caption="📎 Файл для отправки в Claude (промпт + дайджест)"
    )

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
