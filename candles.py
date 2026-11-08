# -----------------------------------------------------------------
# Usage Example
# -----------------------------------------------------------------

import logging
import time
from cba_iqapi.iqapi import IQOptionClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Get logger for this module
logger = logging.getLogger(__name__)


def example_usage():
    """Example usage of IQ Option client with candle streaming."""
    
    logger.info("=" * 60)
    logger.info("Starting IQ Option Candle Stream Example")
    logger.info("=" * 60)
    
    # Initialize client with credentials
    client = IQOptionClient("", "")
    
    # Connect to IQ Option
    logger.info("Connecting to IQ Option...")
    client.connect()
    logger.info("✅ Connected successfully")
    
    # Get initial balance
    balance = client.get_balance()
    logger.info(f"💰 Current balance: ${balance:.2f}")
    
    # Subscribe to 60-second candles for EURUSD
    logger.info("Subscribing to EURUSD 60s candles...")
    success = client.start_candle_stream("EURUSD", 60)
    
    if success:
        logger.info("✅ Subscription successful, waiting for candles...")
    else:
        logger.error("❌ Subscription failed")
        return
    
    # Wait for candles to arrive
    wait_time = 10
    logger.info(f"⏳ Waiting {wait_time} seconds for candles to arrive...")
    time.sleep(wait_time)
    
    # Get candles using direct manager access
    candles = client.candle_manager.get_candles("EURUSD", 60, count=10)
    logger.info(f"📊 Retrieved {len(candles)} candles via direct access")
    
    # Display candle data if available
    if candles:
        logger.info("-" * 60)
        logger.info("Recent candles (most recent last):")
        logger.info("-" * 60)
        
        for i, candle in enumerate(candles):
            logger.info(
                f"Candle {i+1}: {candle.asset_name} | "
                f"Time: {candle.timestamp} | "
                f"O: {candle.open:.5f} | "
                f"H: {candle.high:.5f} | "
                f"L: {candle.low:.5f} | "
                f"C: {candle.close:.5f}"
            )
        
        # Calculate some basic stats
        closes = [c.close for c in candles]
        logger.info("-" * 60)
        logger.info(f"📈 Statistics:")
        logger.info(f"   Open:  {candles[0].open:.5f}")
        logger.info(f"   Close: {candles[-1].close:.5f}")
        logger.info(f"   High:  {max(closes):.5f}")
        logger.info(f"   Low:   {min(closes):.5f}")
        logger.info(f"   Change: {candles[-1].close - candles[0].open:+.5f}")
    else:
        logger.warning("No candles received yet. Try increasing wait time.")
    
    # Get current price using wrapper method
    current_price = client.get_current_price("EURUSD")
    if current_price:
        logger.info(f"💵 Current price (EURUSD): {current_price:.5f}")
    
    # Check subscription status
    is_subscribed = client.is_subscribed_to_candles("EURUSD", 60)
    logger.info(f"📡 Subscription status: {'Active' if is_subscribed else 'Inactive'}")
    
    # Get subscription status summary
    status = client.candle_manager.get_status()
    logger.info(f"📊 Active subscriptions: {status['active_subscriptions']}")
    logger.info(f"📊 Candle counts: {status['candle_counts']}")
    
    # Optional: Register a callback for new candles
    def on_new_candle(candle):
        logger.info(f"🔥 NEW CANDLE! {candle.asset_name} {candle.timeframe}s | Close: {candle.close:.5f}")
    
    client.on_new_candle(on_new_candle)
    logger.info("📧 Registered callback for new candles")
    
    # Keep running to see callbacks
    logger.info("=" * 60)
    logger.info("Listening for candles for 30 more seconds...")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopped by user")
    
    # Cleanup
    logger.info("Unsubscribing from all candle streams...")
    client.candle_manager.unsubscribe_all()
    
    logger.info("Disconnecting...")
    client.disconnect()
    
    logger.info("=" * 60)
    logger.info("Example completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    example_usage()