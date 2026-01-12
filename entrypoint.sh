#!/bin/bash

# Export all environment variables for cron
printenv >> /etc/environment

# Create log file
touch /var/log/cron.log

# Start cron daemon
cron

# Keep container running and show logs
echo "Market Pulse started. Waiting for scheduled runs at 07:00 and 17:00 UTC (10:00 and 20:00 MSK)..."
echo "Run manually: docker exec market-pulse python main.py"

# Follow the log file (create empty first if doesn't exist)
tail -f /var/log/cron.log
