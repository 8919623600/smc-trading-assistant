#!/bin/bash

echo "🛑 Stopping any existing Python processes..."
pkill -f python

echo "📂 Navigating to bot directory..."
cd /home/ec2-user/trading/live_bot || exit

echo "🚀 Starting trading bot in the background..."
nohup python main.py > live_bot.log 2>&1 &

echo "📋 Tailing logs (Press Ctrl+C to exit log view at any time)..."
sleep 2
tail -f live_bot.log