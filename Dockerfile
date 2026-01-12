FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Setup cron jobs (10:00 and 20:00 MSK = 07:00 and 17:00 UTC)
# Только дайджест, без саммари (Claude CLI слишком тяжёлый)
RUN echo "0 7 * * * cd /app && /usr/local/bin/python main.py >> /var/log/cron.log 2>&1" > /etc/cron.d/market-pulse \
    && echo "0 17 * * * cd /app && /usr/local/bin/python main.py >> /var/log/cron.log 2>&1" >> /etc/cron.d/market-pulse \
    && chmod 0644 /etc/cron.d/market-pulse \
    && crontab /etc/cron.d/market-pulse \
    && touch /var/log/cron.log

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
