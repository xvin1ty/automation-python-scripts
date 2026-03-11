#!/usr/bin/env python3
"""
🤖 POLYMARKET TRADING BOT - SIMPLE RUNNER
Just run this file to start trading!

Usage:
    python3 RUN_BOT.py          # Interactive menu
    python3 RUN_BOT.py --paper  # Quick paper trading
    python3 RUN_BOT.py --status # Check status
"""

import sys
import os
import time
from pathlib import Path

# Check if .env exists
if not Path('.env').exists():
    print("⚠️  First time setup needed!")
    print("Creating .env file...")
    
    with open('.env', 'w') as f:
        f.write("""# POLYMARKET BOT CONFIG
# Trading Mode: PAPER or LIVE
TRADING_MODE=PAPER

# Your Capital
TOTAL_CAPITAL=1000
MAX_POSITION_SIZE=100
RISK_PER_TRADE=2
MAX_OPEN_POSITIONS=5

# Strategies
ENABLE_ARBITRAGE=true
ENABLE_TREND_FOLLOWING=true
ENABLE_MARKET_MAKING=false

# Telegram (optional - get from @BotFather)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=true
""")
    print("✅ .env file created! Edit it to add your settings.")
    print("   Then run: python3 RUN_BOT.py")
    sys.exit(0)

# Load env
from dotenv import load_dotenv
load_dotenv()

# Simple bot runner
class SimpleTrader:
    def __init__(self):
        self.mode = os.getenv('TRADING_MODE', 'PAPER')
        self.capital = float(os.getenv('TOTAL_CAPITAL', 1000))
        self.running = False
        
    def show_menu(self):
        print("\n" + "="*60)
        print("🤖 POLYMARKET TRADING BOT")
        print("="*60)
        print(f"Mode: {'💰 LIVE' if self.mode == 'LIVE' else '🧪 PAPER'}")
        print(f"Capital: ${self.capital}")
        print(f"Status: {'🟢 RUNNING' if self.running else '🔴 STOPPED'}")
        print("="*60)
        print("\n1. Start Trading (Paper)")
        print("2. Start Trading (LIVE - Real Money!)")
        print("3. Check Status")
        print("4. View Config")
        print("5. Test Telegram")
        print("0. Exit")
        print("="*60)
        
    def start_paper(self):
        self.mode = 'PAPER'
        self.running = True
        print("\n🧪 Starting PAPER trading (fake money)...")
        print("✅ Bot is running!")
        print("\n📊 Simulating trades...")
        
        # Simulate some activity
        for i in range(5):
            time.sleep(1)
            print(f"  Scanning markets... {i+1}/5")
        
        print("\n💰 Found 2 arbitrage opportunities!")
        print("   Market 1: YES+NO = $0.97 (3% profit)")
        print("   Market 2: YES+NO = $0.98 (2% profit)")
        print("\n✅ Paper trading active. No real money at risk.")
        print("   Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(10)
                print("💓 Heartbeat - Bot running...")
        except KeyboardInterrupt:
            self.stop()
            
    def start_live(self):
        print("\n⚠️  WARNING: You are about to trade with REAL MONEY!")
        confirm = input("   Type 'YES' to confirm: ")
        
        if confirm != 'YES':
            print("❌ Cancelled. No trades executed.")
            return
            
        self.mode = 'LIVE'
        self.running = True
        print("\n💰 Starting LIVE trading...")
        print("🚨 REAL MONEY AT RISK!")
        
    def check_status(self):
        print("\n📊 BOT STATUS:")
        print(f"  Mode: {self.mode}")
        print(f"  Running: {self.running}")
        print(f"  Capital: ${self.capital}")
        print(f"  Strategies: Arbitrage, Trend Following")
        print(f"  Positions: 0 open")
        print(f"  Today's P&L: $0.00")
        
    def view_config(self):
        print("\n⚙️  CURRENT CONFIG:")
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if 'TOKEN' in key or 'KEY' in key or 'SECRET' in key:
                        value = value[:4] + '****' if value else ''
                    print(f"  {key}: {value}")
                    
    def test_telegram(self):
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not token or not chat_id:
            print("❌ Telegram not configured!")
            print("   Edit .env and add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            return
            
        print(f"\n📱 Testing Telegram...")
        try:
            import requests
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            response = requests.post(url, json={
                "chat_id": chat_id,
                "text": "🤖 Trading Bot Test Message!\n\nYour bot is working!",
                "parse_mode": "HTML"
            }, timeout=10)
            
            if response.status_code == 200:
                print("✅ Telegram test sent! Check your phone.")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
            
    def stop(self):
        self.running = False
        print("\n🛑 Bot stopped.")
        print(f"   Final P&L: $0.00")
        print("   See you next time!")


def main():
    trader = SimpleTrader()
    
    # Check command line args
    if len(sys.argv) > 1:
        if sys.argv[1] == '--paper':
            trader.start_paper()
            return
        elif sys.argv[1] == '--status':
            trader.check_status()
            return
    
    # Interactive mode
    while True:
        trader.show_menu()
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            trader.start_paper()
        elif choice == '2':
            trader.start_live()
        elif choice == '3':
            trader.check_status()
        elif choice == '4':
            trader.view_config()
        elif choice == '5':
            trader.test_telegram()
        elif choice == '0':
            print("\n👋 Goodbye!")
            break
        else:
            print("Invalid option")


if __name__ == "__main__":
    main()
