#!/bin/bash

# ==========================================
# SMC LIVE SCANNER LAUNCHER SCRIPT
# ==========================================

echo "=================================================="
echo "🚀 STARTING SMC LIVE SCANNER & BOT"
echo "=================================================="

# Stop any existing screen session named 'smc_bot' if running
if screen -list | grep -q "smc_bot"; then
    echo "🔄 Stopping existing bot session..."
    screen -S smc_bot -X quit
fi

# Reset scanner log safely
LOG_FILE="scanner.log"
if [ -f "$LOG_FILE" ]; then
    rm "$LOG_FILE"
    echo "🗑️ Removing old scanner.log..."
fi

touch "$LOG_FILE"
echo "✅ Created fresh scanner.log"

# Launch python script inside detached screen session
# Using direct path since we are in the backtesting folder
echo "🤖 Launching bot in background screen session (smc_bot)..."
screen -dmS smc_bot python3 3_live_bot.py > "$LOG_FILE" 2>&1

echo "=================================================="
echo "✨ Bot launched successfully in screen session 'smc_bot'!"
echo "Run 'screen -r smc_bot' to view live interactive terminal."
echo "Run 'tail -f scanner.log' to view log outputs."
echo "=================================================="