# Market Pulse Bot

Telegram-бот для мониторинга крипто-рынка. Собирает новости, fundraising и VIP-аналитику из 44+ источников.

## Возможности

- **Fundraising** — раунды из DefiLlama API
- **VIP Research** — a16z, Messari, Coinbase, Chainalysis и др.
- **Protocol Updates** — Aave, Lido, Curve, EigenLayer и др.
- **News** — 20+ новостных источников
- **Scraping** — ARK Invest, Grayscale Research
- **Дедупликация** — SQLite база для предотвращения повторов

## Быстрый старт

### Локальный запуск

```bash
# Клонировать репозиторий
git clone <repo-url>
cd market-pulse

# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
cp .env.example .env
# Отредактировать .env — добавить токен бота и chat_id

# Запустить один раз
python main.py

# Или по расписанию (10:00 и 20:00 MSK)
python main.py --schedule
```

### Docker

```bash
# Настроить переменные
cp .env.example .env
nano .env

# Запустить
docker-compose up -d

# Смотреть логи
docker-compose logs -f

# Остановить
docker-compose down
```

## Команды

```bash
# Отправить дайджест сейчас
python main.py

# Запустить по расписанию
python main.py --schedule

# Показать статистику БД
python main.py --stats

# Очистить записи старше N дней
python main.py --cleanup 14
```

## Расписание

| Время (MSK) | Время (UTC) | Дайджест |
|-------------|-------------|----------|
| 10:00 | 07:00 | Morning |
| 20:00 | 17:00 | Evening |

## Конфигурация

### .env

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
```

### config/settings.json

```json
{
  "fundraising_hours": 168
}
```

### config/topics.json

```json
{
  "priority_topics": ["DeFi", "L2", "RWA"]
}
```

## Структура проекта

```
market-pulse/
├── bot/
│   └── telegram.py      # Форматирование и отправка
├── collectors/
│   ├── articles.py      # RSS-сборщик
│   ├── fundraising.py   # DefiLlama API
│   └── scraper.py       # ARK, Grayscale
├── config/
│   ├── rss_sources.json # Источники RSS
│   ├── settings.json    # Настройки
│   └── topics.json      # Темы
├── db/
│   └── database.py      # SQLite дедупликация
├── filters/
│   ├── ranker.py        # Ранжирование
│   └── tagger.py        # Теги
├── data/
│   └── market_pulse.db  # SQLite база
├── main.py              # Entry point
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Источники (44)

### VIP Research (7)
a16z, Messari, Coinbase, Chainalysis, CoinMetrics + ARK Invest, Grayscale (scraping)

### Protocol Blogs (9)
Aave, Lido, Compound, Curve, EigenLayer, Arbitrum, Ethereum Foundation, Synthetix, Bancor

### News (20)
CoinDesk, Cointelegraph, The Block, Decrypt, DL News, CryptoSlate, Bitcoin Magazine, The Defiant, Blockworks и др.

### Other
- DeFi: DeFi Prime
- Regulation: CoinDesk Policy, Cointelegraph Regulation
- Substack: The Defiant, Week in Ethereum
- Russian: ForkLog, Incrypted

## Troubleshooting

### Бот не отправляет сообщения

1. Проверить токен: `echo $TELEGRAM_BOT_TOKEN`
2. Проверить chat_id: `echo $TELEGRAM_CHAT_ID`
3. Убедиться, что бот добавлен в чат

### Нет новых статей

```bash
python main.py --stats
```

Если много записей — очистить:
```bash
python main.py --cleanup 7
```

### Docker не запускается

```bash
# Пересобрать образ
docker-compose build --no-cache

# Проверить логи
docker-compose logs market-pulse
```

## License

MIT
