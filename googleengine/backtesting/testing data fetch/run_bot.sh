#!/bin/bash

# Configuration
BOT_SCRIPT="main.py"
LOG_FILE="bot_output.log"

# If no argument is provided, display the command helper guide
if [ -z "$1" ]; then
    echo "=================================================="
    echo "🤖 SMC TRADING BOT MANAGER - COMMAND GUIDE"
    echo "=================================================="
    echo "  ./run_bot.sh start    -> Start the bot"
    echo "  ./run_bot.sh status   -> Check status"
    echo "  ./run_bot.sh logs     -> Check logs"
    echo "  ./run_bot.sh restart  -> Restart the bot"
    echo "  ./run_bot.sh stop     -> Stop the bot"
    echo "=================================================="
    exit 0
fi

case "$1" in
    start)
        if pgrep -f "$BOT_SCRIPT" > /dev/null; then
            echo "⚠️ Bot is already running!"
        else
            echo "🚀 Starting SMC Bot in the background..."
            nohup bash -c "source ~/.bashrc && python3 -u $BOT_SCRIPT" > "$LOG_FILE" 2>&1 &
            echo "✅ Bot started successfully. Logging to $LOG_FILE"
        fi
        ;;
    stop)
        if pgrep -f "$BOT_SCRIPT" > /dev/null; then
            echo "🛑 Stopping SMC Bot..."
            pkill -f "$BOT_SCRIPT"
            echo "✅ Bot stopped."
        else
            echo "⚠️ Bot is not running."
        fi
        ;;
    restart)
        echo "🔄 Restarting SMC Bot..."
        pkill -f "$BOT_SCRIPT" 2>/dev/null
        sleep 2
        nohup bash -c "source ~/.bashrc && python3 -u $BOT_SCRIPT" > "$LOG_FILE" 2>&1 &
        echo "✅ Bot restarted successfully."
        ;;
    status)
        if pgrep -f "$BOT_SCRIPT" > /dev/null; then
            echo "🟢 Status: Bot is RUNNING."
            echo "--- Last 5 log lines ---"
            tail -n 5 "$LOG_FILE"
        else
            echo "🔴 Status: Bot is STOPPED."
        fi
        ;;
    logs)
        echo "📋 Showing live logs (Press Ctrl+C to exit):"
        tail -f "$LOG_FILE"
        ;;
    *)
        echo "❌ Invalid option. Run './run_bot.sh' without arguments to see the menu."
        exit 1
        ;;
esac