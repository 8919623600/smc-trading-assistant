#!/bin/bash

BOT_SCRIPT="backtesting/3_live_bot.py"
LOG_FILE="scanner.log"
SCREEN_NAME="smc_bot"

echo "=================================================="
echo "🚀 STARTING SMC LIVE SCANNER & BOT"
echo "=================================================="

# 1. Stop any existing background bot session if running
if screen -list | grep -q "$SCREEN_NAME"; then
    echo "🔄 Stopping existing bot session..."
    screen -S "$SCREEN_NAME" -X quit
fi

# 2. Remove old log file and create a fresh one
if [ -f "$LOG_FILE" ]; then
    echo "🗑️ Removing old $LOG_FILE..."
    rm -f "$LOG_FILE"
fi

touch "$LOG_FILE"
echo "✅ Created fresh $LOG_FILE"

# 3. Launch the python bot in a detached screen session, piping output to scanner.log
echo "🤖 Launching bot in background screen session ($SCREEN_NAME)..."
screen -dmS "$SCREEN_NAME" bash -c "python3 $BOT_SCRIPT > $LOG_FILE 2>&1"

# 4. Verify startup
sleep 2
if screen -list | grep -q "$SCREEN_NAME"; then
    echo "✅ Success! SMC Scanner is running successfully."
    echo ""
    echo "Handy Log & Control Commands:"
    echo "View live output in real-time: tail -f scanner.log"
    echo "Stop the scanner completely: screen -S smc_bot -X quit"
else
    echo "❌ Error: Bot failed to start. Check $LOG_FILE for details."
fi
echo "=================================================="