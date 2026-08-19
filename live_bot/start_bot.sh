#!/bin/bash

echo "=========================================="
echo "🔄 MANAGING GOLD SMC TRADING BOT"
echo "=========================================="

# 1. Kill any existing instances of main.py safely
echo "🛑 Stopping any existing bot processes..."
pkill -f "python main.py"
sleep 2

# 2. Start the new bot instance in the background with logging
echo "🚀 Starting fresh bot instance..."
nohup python3 -u main.py > live_bot.log 2>&1 &

# 3. Confirmation output
echo "✅ Bot is now running cleanly in the background!"
echo "💡 To view logs live, run: tail -f live_bot.log"
echo "=========================================="