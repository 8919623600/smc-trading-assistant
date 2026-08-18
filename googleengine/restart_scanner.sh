#!/bin/bash

# Define your script name
SCRIPT_NAME="googlesmc.py"
LOG_FILE="scanner.log"

echo "=================================================="
echo "  RESTARTING SMC GOLD SCANNER                     "
echo "=================================================="

# 1. Kill any running instances of the scanner
if pgrep -f "$SCRIPT_NAME" > /dev/null; then
    echo "🛑 Stopping currently running scanner process(es)..."
    pkill -f "$SCRIPT_NAME"
    sleep 2
    echo "✔ Old process terminated."
else
    echo "ℹ️ No running scanner process found."
fi

# 2. Clean/clear the log file
if [ -f "$LOG_FILE" ]; then
    echo "🧹 Cleaning $LOG_FILE..."
    > "$LOG_FILE"
    echo "✔ Log file cleared."
else
    echo "ℹ️ $LOG_FILE does not exist yet. It will be created."
fi

# 3. Start the script fresh in the background
echo "🚀 Starting $SCRIPT_NAME in the background..."
nohup python3 -u "$SCRIPT_NAME" > "$LOG_FILE" 2>&1 &

# 4. Verify startup
sleep 2
if pgrep -f "$SCRIPT_NAME" > /dev/null; then
    echo "SUCCESS: Scanner is now running cleanly in the background!"
    echo "--------------------------------------------------"
    echo "To view live logs, run: tail -f $LOG_FILE"
    echo "=================================================="
else
    echo "❌ ERROR: Scanner failed to start. Check $LOG_FILE for details."
fi