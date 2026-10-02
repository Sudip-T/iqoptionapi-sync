"""
═══════════════════════════════════════════════════════════════════════════
IQ OPTION API - COMPLETE EXAMPLES FOR VIEWERS
═══════════════════════════════════════════════════════════════════════════

This file contains ready-to-run examples for every major feature.
Each function is self-contained and shows exactly how to use that feature.

Author: Sudip
YouTube: @BytecodeAutomation
═══════════════════════════════════════════════════════════════════════════
"""

import sys
import time
import logging
from datetime import datetime
from iqoptionapi.iqapi import IQOptionClient
from iqoptionapi.models import OptionsTradeParams, Direction, \
      OptionType, InstrumentType

# Configure logging for clean output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("IQOptionExample")

# Your credentials (replace with your own)
EMAIL='jitraders1216@gmail.com'
PASSWORD='jo121014'


# Create client (demo account by default)
client = IQOptionClient(EMAIL, PASSWORD, account_type='demo')

# Connect to IQ Option
print("🔌 Connecting to IQ Option...")
if client.connect():
    print("✅ Connected successfully!")
else:
    print("Something went wrong!")
    sys.exit(1)

print(client.get_actives(InstrumentType.BLITZ_OPTION))
sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════
# 1. BASIC CONNECTION & ACCOUNT
# ═══════════════════════════════════════════════════════════════════════

def example_connect_and_get_balance():
    """
    EP#01: Connect to IQ Option and get account balance.
    The foundation for everything else.
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: GET BALANCE")
    print("="*60)

    # Get account balance
    balance = client.get_balance()
    print(f"💰 Current balance: ${balance:.2f}")
    
    return client


def example_switch_account():
    """
    EP#01: Switch between demo and real accounts.
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: SWITCH ACCOUNT TYPE")
    print("="*60)
    
    # Switch to REAL account (be careful!)
    print("\n⚠️ Switching to REAL account...")
    client.switch_account('real')
    print(f"📊 Current account: REAL")
    print(f"💰 Balance: ${client.get_balance():.2f}")
    
    # Switch back to demo
    print("\n🔄 Switching back to DEMO...")
    client.switch_account('demo')
    



def example_refill_demo():
    """
    EP#01: Refill demo account (useful for testing).
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: REFILL DEMO ACCOUNT")
    print("="*60)
    
    old_balance = client.get_balance()
    print(f"💰 Old balance: ${old_balance:.2f}")
    
    # Add $10,000 to demo account
    print("💵 Refilling demo account +$10,000...")
    client.refill_demo(10000)
    
    time.sleep(1)  # Wait for update
    new_balance = client.get_balance()
    print(f"💰 New balance: ${new_balance:.2f}")
    



# ═══════════════════════════════════════════════════════════════════════
# 2. CANDLE DATA & REAL-TIME STREAMS
# ═══════════════════════════════════════════════════════════════════════

def example_get_historical_candles():
    """
    EP#01: Get historical candlestick data.
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: GET HISTORICAL CANDLES")
    print("="*60)
    
    # Get 50 candles of 1-minute EURUSD data
    print("📊 Fetching EURUSD 1-minute candles...")
    candles = client.get_candles("EURUSD-op", count=50, timeframe=60)
    
    print(f"✅ Retrieved {len(candles)} candles")
    print("\nLast 5 candles (most recent last):")
    print("-" * 70)
    print(f"{'Time':<12} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10}")
    print("-" * 70)
    
    for candle in candles[-5:]:
        time_str = datetime.fromtimestamp(candle['from']).strftime('%H:%M:%S')
        print(f"{time_str:<12} {candle['open']:<10.5f} {candle['max']:<10.5f} "
              f"{candle['min']:<10.5f} {candle['close']:<10.5f}")
    


def example_real_time_candles():
    """
    EP#02: Subscribe to real-time candle streams.
    This is the most important feature for live trading.
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: REAL-TIME CANDLE STREAM")
    print("="*60)
    
    print("📡 Subscribing to EURUSD 60s candles...")
    
    # Register callback for new candles
    def on_candle(candle):
        print(f"🔥 NEW CANDLE: {candle.asset_name} {candle.timeframe}s")
        print(f"   Open: {candle.open:.5f}  Close: {candle.close:.5f}")
        print(f"   High: {candle.high:.5f}   Low: {candle.low:.5f}")
        print("-" * 40)
    
    client.on_new_candle(on_candle)
    
    # Start streaming
    success = client.start_candle_stream("EURUSD-op", 60)
    
    if success:
        print("✅ Subscribed! Waiting 30 seconds for candles...\n")
        time.sleep(30)
    else:
        print("❌ Subscription failed")
    
    # Cleanup
    client.stop_candle_stream("EURUSD-op", 60)
    print("✅ Stream stopped")


def example_get_current_price():
    """
    EP#02: Get current price from cached candles.
    """
    print("\n" + "="*60)
    print("EXAMPLE 6: GET CURRENT PRICE")
    print("="*60)
    
    # Subscribe first (to get live data)
    client.start_candle_stream("EURUSD-op", 60)
    time.sleep(3)  # Wait for first candle
    
    # Get current price
    price = client.get_current_price("-op")
    print(f"💰 EURUSD current price: {price:.5f}")
    
    # Get last 5 candles
    candles = client.get_last_candles("EURUSD-op", 60, count=5)
    print(f"\n📊 Last 5 candles stored: {len(candles)}")
    
    for i, candle in enumerate(candles):
        print(f"   Candle {i+1}: Close = {candle.close:.5f}")
    
    client.stop_candle_stream("EURUSD-op", 60)



# ═══════════════════════════════════════════════════════════════════════
# 3. TRADING
# ═══════════════════════════════════════════════════════════════════════

def example_place_binary_trade():
    """
    EP#03: Place a binary options trade.
    """
    print("\n" + "="*60)
    print("EXAMPLE 7: PLACE BINARY OPTIONS TRADE")
    print("="*60)
    
    # Get balance before trade
    balance_before = client.get_balance()
    print(f"💰 Balance before: ${balance_before:.2f}")
    
    # Place a CALL trade (predict price will go UP)
    trade_params = OptionsTradeParams(
        asset="EURUSD-op",
        expiry=1,  # 1 minute
        amount=10,  # $10
        direction=Direction.CALL,
        option_type=OptionType.BINARY_OPTION
    )
    
    print(f"\n📈 Placing CALL trade on EURUSD (${10})...")
    success, order_id = client.execute_options_trade(trade_params)
    
    if success:
        print(f"✅ Trade placed! Order ID: {order_id}")
        
        # Wait for result
        print("⏳ Waiting 65 seconds for trade result...")
        time.sleep(65)
        
        # Get outcome
        success, outcome, pnl = client.get_trade_outcome(order_id, expiry=1)
        
        if success:
            balance_after = client.get_balance()
            print(f"\n📊 TRADE RESULT:")
            print(f"   Outcome: {outcome.get('result', 'unknown').upper()}")
            print(f"   P&L: ${pnl:+.2f}")
            print(f"   Balance after: ${balance_after:.2f}")
    else:
        print(f"❌ Trade failed: {order_id}")
    


def example_place_digital_trade():
    """
    EP#03: Place a digital options trade.
    """
    print("\n" + "="*60)
    print("EXAMPLE 8: PLACE DIGITAL OPTIONS TRADE")
    print("="*60)
    
    # Digital options have higher payouts but different mechanics
    trade_params = OptionsTradeParams(
        asset="EURUSD",
        expiry=1,  # 1 minute
        amount=10,
        direction=Direction.PUT,  # Predict price will go DOWN
        option_type=OptionType.DIGITAL_OPTION
    )
    
    print(f"📉 Placing PUT trade on EURUSD (${10})...")
    success, order_id = client.execute_options_trade(trade_params)
    
    if success:
        print(f"✅ Digital trade placed! Order ID: {order_id}")
    else:
        print(f"❌ Trade failed: {order_id}")


# ═══════════════════════════════════════════════════════════════════════
# 4. POSITION HISTORY
# ═══════════════════════════════════════════════════════════════════════

def example_get_position_history():
    """
    EP#04: Get trading history.
    """
    print("\n" + "="*60)
    print("EXAMPLE 9: GET POSITION HISTORY")
    print("="*60)
    
    # Get last 10 binary option trades
    print("📜 Fetching last 10 binary option trades...")
    positions = client.get_position_history_by_page(
        instrument_type=["binary-option", "turbo-option"],
        limit=10,
        offset=0
    )
    
    print(f"\n✅ Found {len(positions)} positions")
    print("-" * 80)
    
    for pos in positions:
        pnl = pos.get('pnl_net', 0)
        result = "✅ WIN" if pnl > 0 else "❌ LOSS" if pnl < 0 else "➖ DRAW"
        print(f"   {result} | P&L: ${pnl:+.2f} | Asset: {pos.get('active_id')}")


def example_get_filtered_positions():
    """
    EP#04: Get filtered position history with readable dates.
    """
    print("\n" + "="*60)
    print("EXAMPLE 10: GET FILTERED POSITIONS")
    print("="*60)
    
    # Get filtered positions with clean output
    positions = client.account_manager.get_filtered_position_history(
        instrument_types=["binary-option", "turbo-option"],
        limit=20
    )
    
    print(f"✅ Found {len(positions)} positions\n")
    print(f"{'Time':<20} {'Asset':<10} {'Result':<8} {'P&L':<10} {'Amount':<10}")
    print("-" * 65)
    
    for pos in positions:
        open_time = pos.get('open_time', 'N/A')
        pnl = pos.get('pnl_net', 0)
        result = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "DRAW"
        result_color = "✅" if pnl > 0 else "❌" if pnl < 0 else "➖"
        
        print(f"{open_time:<20} {pos.get('active_id', 'N/A'):<10} "
              f"{result_color} {result:<5} ${pnl:+.2f}    ${pos.get('invest', 0):<10}")


# ═══════════════════════════════════════════════════════════════════════
# 5. ASSET MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

def example_get_underlying_assets():
    """
    EP#05: Get available trading assets.
    """
    print("\n" + "="*60)
    print("EXAMPLE 11: GET UNDERLYING ASSETS")
    print("="*60)
    
    # Get Forex assets
    print("📊 Fetching Forex assets...")
    forex = client.market_manager.get_underlying_assests('forex')
    print(f"✅ Found {len(forex)} Forex pairs")
    
    # Show first 10
    print("\nFirst 10 Forex pairs:")
    for asset in forex[:10]:
        print(f"   {asset['name']} (ID: {asset['active_id']})")
    
    # Get Crypto assets
    print("\n📊 Fetching Crypto assets...")
    crypto = client.market_manager.get_underlying_assests('crypto')
    print(f"✅ Found {len(crypto)} Crypto pairs")
    
    for asset in crypto[:5]:
        print(f"   {asset['name']} (ID: {asset['active_id']})")


# ═══════════════════════════════════════════════════════════════════════
# 6. ADVANCED: LIVE TRADING WITH SIGNALS
# ═══════════════════════════════════════════════════════════════════════

def example_simple_trading_bot():
    """
    EP#06: Simple trading bot using candle direction.
    This is the foundation for automated trading.
    """
    print("\n" + "="*60)
    print("EXAMPLE 12: SIMPLE TRADING BOT")
    print("="*60)
    
    print(f"💰 Starting balance: ${client.get_balance():.2f}")
    print("🤖 Bot will trade based on candle direction\n")
    
    # Subscribe to candles
    client.start_candle_stream("EURUSD", 60)
    
    trade_count = 0
    max_trades = 3  # Only do 3 trades for demo
    
    # Register callback for new candles
    def on_new_candle(candle):
        nonlocal trade_count
        
        if trade_count >= max_trades:
            return
        
        # Simple strategy: trade the direction of the closed candle
        if candle.close > candle.open:
            direction = Direction.CALL
            direction_name = "CALL (UP)"
        else:
            direction = Direction.PUT
            direction_name = "PUT (DOWN)"
        
        print(f"\n📊 Candle closed: {direction_name}")
        print(f"   Open: {candle.open:.5f} → Close: {candle.close:.5f}")
        
        # Place trade
        trade_params = OptionsTradeParams(
            asset="EURUSD",
            expiry=1,
            amount=5,  # Small amount for demo
            direction=direction,
            option_type=OptionType.BINARY_OPTION
        )
        
        print(f"📈 Placing {direction_name} trade...")
        success, order_id = client.execute_options_trade(trade_params)
        
        if success:
            trade_count += 1
            print(f"✅ Trade {trade_count}/{max_trades} placed (ID: {order_id})")
        else:
            print(f"❌ Trade failed: {order_id}")
    
    # client.on_new_candle(on_new_candle)
    client.candle_manager.on_new_candle_async(on_new_candle)
    
    print("⏳ Running for 4 minutes... (Ctrl+C to stop early)")
    
    try:
        time.sleep(max_trades*60)
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    
    # Cleanup
    client.stop_candle_stream("EURUSD", 60)
    print(f"\n💰 Final balance: ${client.get_balance():.2f}")


# ═══════════════════════════════════════════════════════════════════════
# RUN ALL EXAMPLES (for testing)
# ═══════════════════════════════════════════════════════════════════════

def run_all_examples():
    """
    Run all examples sequentially.
    Useful for testing the entire API.
    """
    print("\n" + "="*70)
    print("IQ OPTION API - RUNNING ALL EXAMPLES")
    print("="*70)
    
    examples = [
        ("Connect & Get Balance", example_connect_and_get_balance),
        ("Get Historical Candles", example_get_historical_candles),
        ("Get Current Price", example_get_current_price),
        ("Place Binary Trade", example_place_binary_trade),
        ("Get Position History", example_get_position_history),
        ("Get Underlying Assets", example_get_underlying_assets),
    ]
    
    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"❌ Error in {name}: {e}")
        
        print("\n" + "~"*70)
        input("Press Enter to continue to next example...")
    
    print("\n✅ All examples completed!")


# ═══════════════════════════════════════════════════════════════════════
# MENU SYSTEM FOR VIEWERS
# ═══════════════════════════════════════════════════════════════════════

def show_menu():
    """Interactive menu for viewers to choose examples."""
    print("\n" + "="*60)
    print("📚 IQ OPTION API - EXAMPLE MENU")
    print("="*60)
    print("""
    1  - Connect & Get Balance
    2  - Switch Account Type
    3  - Refill Demo Account
    4  - Get Historical Candles
    5  - Real-Time Candle Stream
    6  - Get Current Price
    7  - Place Binary Trade
    8  - Place Digital Trade
    9  - Get Position History
    10 - Get Filtered Positions
    11 - Get Underlying Assets
    12 - Simple Trading Bot
    13 - Run ALL Examples
    0  - Exit
    """)
    
    examples_map = {
        1: example_connect_and_get_balance,
        2: example_switch_account,
        3: example_refill_demo,
        4: example_get_historical_candles,
        5: example_real_time_candles,
        6: example_get_current_price,
        7: example_place_binary_trade,
        8: example_place_digital_trade,
        9: example_get_position_history,
        10: example_get_filtered_positions,
        11: example_get_underlying_assets,
        12: example_simple_trading_bot,
        13: run_all_examples,
    }
    
    while True:
        try:
            choice = int(input("\n👉 Enter your choice: "))
            
            if choice == 0:
                print("👋 Goodbye! Happy trading!")
                break
            
            if choice in examples_map:
                examples_map[choice]()
            else:
                print("❌ Invalid choice. Please try again.")
                
        except ValueError:
            print("❌ Please enter a number.")
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break

    # Disconnect when done
    client.disconnect()
    print("🔌 Disconnected")

# ═══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║     IQ OPTION API - COMPLETE EXAMPLES                          ║
    ║     YouTube: @BytecodeAutomation                               ║
    ║                                                                ║
    ║     ⚠️  IMPORTANT: Update EMAIL and PASSWORD variables         ║
    ║        at the top of this file before running!                 ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Show interactive menu
    show_menu()