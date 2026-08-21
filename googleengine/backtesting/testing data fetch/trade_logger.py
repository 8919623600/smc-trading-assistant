import csv
import os
from datetime import datetime

def log_trade_event(symbol, event_type, entry, sl, tp1, tp2, tp3, pnl_or_rr):
    file_exists = os.path.isfile('trade_history.csv')
    
    with open('trade_history.csv', mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            # Write header row once
            writer.writerow(['Timestamp', 'Symbol', 'Event', 'Entry', 'SL', 'TP1', 'TP2', 'TP3', 'Details'])
        
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        writer.writerow([timestamp, symbol, event_type, entry, sl, tp1, tp2, tp3, pnl_or_rr])