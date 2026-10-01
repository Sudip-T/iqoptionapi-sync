# import time
# import logging
# from dataclasses import dataclass
# from collections import defaultdict, deque
# from typing import Optional, List, Callable
# from iqoptionapi.instruments.options_assests import UNDERLYING_ASSESTS

# logger = logging.getLogger(__name__)


# @dataclass
# class Candle:
#     """Clean candle data structure."""
#     asset_name: str
#     asset_id: int
#     timeframe: int
#     timestamp: int
#     open: float
#     close: float
#     high: float
#     low: float
#     volume: float
    
#     @classmethod
#     def from_iq_message(cls, asset_name: str, msg: dict) -> 'Candle':
#         return cls(
#             asset_name=asset_name,
#             asset_id=msg.get('active_id'),
#             timeframe=msg.get('size'),
#             timestamp=msg.get('from'),
#             open=msg.get('open'),
#             close=msg.get('close'),
#             high=msg.get('max'),
#             low=msg.get('min'),
#             volume=msg.get('volume', 0)
#         )


# class CandleSubscriptionManager:
#     """
#     COMPLETE OWNER of all candle-related operations.
#     MessageHandler knows nothing about candles - just forwards to us.
#     """
    
#     def __init__(self, websocket):
#         """
#         Args:
#             asset_id_map: {"EURUSD": 1, "GBPUSD": 2, ...}
#         """
#         self.websocket = websocket
#         self.asset_id_map = {v: k for k, v in UNDERLYING_ASSESTS.items()}
        
#         # ─── Candle Storage (replaces everything from MessageHandler) ───
#         # Structure: asset_name → timeframe → deque of candles (max 100)
#         self._candles: dict[str, dict[int, deque]] = defaultdict(
#             lambda: defaultdict(lambda: deque(maxlen=100))
#         )
        
#         # Live/current candle (being built)
#         self._current_candle: dict[str, dict[int, Optional[dict]]] = defaultdict(
#             lambda: defaultdict(lambda: None)
#         )
        
#         # ─── Subscription Management ───
#         self._active_subscriptions: set[str] = set()  # {"EURUSD,60"}
#         self._subscription_confirmed: dict[str, bool] = defaultdict(bool)
        
#         # ─── Callbacks ───
#         self._new_candle_callbacks: List[Callable] = []
#         self._live_candle_callbacks: List[Callable] = []

    
#     # -----------------------------------------------------------------
#     # Entry point - called by MessageHandler
#     # -----------------------------------------------------------------
    
#     def on_candle_message(self, message: dict) -> None:
#         """
#         Called by MessageHandler._handle_candles_generated().
#         This is the ONLY connection between MessageHandler and candles.
#         """
#         msg = message.get('msg', {})
#         timeframe = msg.get('size')
#         asset_name = str(self.asset_id_map.get(msg.get('active_id')))

#         if not asset_name:
#             logger.warning(f"Unknown asset: {asset_name}")
#             return
        
#         if not timeframe:
#             return

#         # Handle the candle
#         self._process_candle(asset_name, timeframe, msg)
    
#     def _process_candle(self, asset_name: str, timeframe: int, msg: dict):
#         """
#         Process incoming candle - detects new vs updated candle.
#         """
#         candle_id = msg.get('id')  # IQ Option's candle ID
#         timestamp = msg.get('from')
        
#         # Check if this is a new candle or update to current
#         current = self._current_candle[asset_name][timeframe]
        
#         if current is None or current.get('id') != candle_id:
#             # NEW CANDLE - previous candle is now closed
#             if current is not None:
#                 # Store the completed candle in history
#                 completed_candle = Candle.from_iq_message(asset_name, current)
#                 self._candles[asset_name][timeframe].append(completed_candle)
                
#                 # Notify new candle callbacks
#                 for cb in self._new_candle_callbacks:
#                     try:
#                         cb(completed_candle)
#                     except Exception as e:
#                         logger.error(f"New candle callback failed: {e}")
            
#             # Start tracking new current candle
#             self._current_candle[asset_name][timeframe] = msg
#         else:
#             # UPDATE to current candle (live price changes)
#             self._current_candle[asset_name][timeframe] = msg
            
#             # Notify live update callbacks
#             for cb in self._live_candle_callbacks:
#                 try:
#                     cb(asset_name, timeframe, msg)
#                 except Exception as e:
#                     logger.error(f"Live candle callback failed: {e}")
        
#         # Mark subscription as confirmed (for subscribe() wait loop)
#         sub_key = f"{asset_name},{timeframe}"
#         if sub_key in self._active_subscriptions:
#             self._subscription_confirmed[sub_key] = True
        
#         print(f"📊 Candle: {asset_name} {timeframe}s @ {timestamp}")
#         print(self._active_subscriptions)
    
#     # -----------------------------------------------------------------
#     # Subscription Methods (same as before)
#     # -----------------------------------------------------------------
    
#     def subscribe(self, asset: str, timeframe: int = 60, timeout: int = 20) -> bool:
#         """Subscribe to real-time candles."""
#         if not self.websocket:
#             logger.error("WebSocket not set")
#             return False
        
#         sub_key = f"{asset},{timeframe}"
        
#         if sub_key in self._active_subscriptions:
#             logger.debug(f"Already subscribed to {sub_key}")
#             return True
        
#         print(asset)
#         asset_id = UNDERLYING_ASSESTS[asset]
#         if not asset_id:
#             logger.error(f"Unknown asset: {asset}")
#             return False
        
#         self._subscription_confirmed[sub_key] = False
#         print(self._subscription_confirmed)
        
#         payload = {
#             "name": "candle-generated",
#             "params": {
#                 "routingFilters": {
#                     "active_id": asset_id,
#                     "size": timeframe
#                 }
#             }
#         }
        
#         logger.info(f"🔌 Subscribing to {asset} {timeframe}s candles...")
#         self.websocket.send_message("subscribeMessage", payload)
        
#         start_time = time.time()
#         while time.time() - start_time < timeout:
#             if self._subscription_confirmed.get(sub_key, False):
#                 self._active_subscriptions.add(sub_key)
#                 logger.info(f"✅ Subscribed to {asset} {timeframe}s candles")
#                 return True
#             time.sleep(0.5)
        
#         logger.error(f"❌ Subscription timeout for {asset} {timeframe}s")
#         return False
    
#     def unsubscribe(self, asset: str, timeframe: int) -> bool:
#         """Unsubscribe from real-time candles."""
#         if not self.websocket:
#             return False
        
#         sub_key = f"{asset},{timeframe}"
        
#         if sub_key not in self._active_subscriptions:
#             return True
        
#         asset_id = self.asset_id_map.get(asset)
#         if not asset_id:
#             return False
        
#         payload = {
#             "name": "candle-generated",
#             "params": {
#                 "routingFilters": {
#                     "active_id": asset_id,
#                     "size": timeframe
#                 }
#             }
#         }
        
#         logger.info(f"🔌 Unsubscribing from {asset} {timeframe}s candles...")
#         self.websocket.send_message("unsubscribeMessage", payload)
        
#         self._active_subscriptions.discard(sub_key)
#         self._subscription_confirmed.pop(sub_key, None)
        
#         return True
    
#     def unsubscribe_all(self):
#         """Unsubscribe from all active streams."""
#         for sub_key in list(self._active_subscriptions):
#             asset, size = sub_key.split(',')
#             self.unsubscribe(asset, int(size))
    
#     # -----------------------------------------------------------------
#     # Data Access Methods
#     # -----------------------------------------------------------------
    
#     def get_candles(self, asset: str, timeframe: int, count: int = 10) -> List[Candle]:
#         """Get last N completed candles."""
#         dq = self._candles[asset][timeframe]
#         if not dq:
#             return []
#         return list(dq)[-count:]
    
#     def get_latest_candle(self, asset: str, timeframe: int) -> Optional[Candle]:
#         """Get most recent COMPLETED candle."""
#         dq = self._candles[asset][timeframe]
#         return dq[-1] if dq else None
    
#     def get_current_candle(self, asset: str, timeframe: int) -> Optional[dict]:
#         """Get the LIVE (in-progress) candle."""
#         return self._current_candle[asset][timeframe]
    
#     def get_current_price(self, asset: str, timeframe: int = 60) -> Optional[float]:
#         """Get current price (close of latest candle OR live price)."""
#         # Prefer current live candle's close
#         current = self.get_current_candle(asset, timeframe)
#         if current:
#             return current.get('close')
        
#         # Fall back to last completed candle
#         latest = self.get_latest_candle(asset, timeframe)
#         return latest.close if latest else None
    
#     def get_candle_count(self, asset: str, timeframe: int) -> int:
#         """Get number of stored candles."""
#         return len(self._candles[asset][timeframe])
    
#     def is_subscribed(self, asset: str, timeframe: int) -> bool:
#         """Check if actively subscribed."""
#         return f"{asset},{timeframe}" in self._active_subscriptions
    
#     # -----------------------------------------------------------------
#     # Callbacks
#     # -----------------------------------------------------------------
    
#     def on_new_candle(self, callback: Callable[[Candle], None]) -> None:
#         """Register callback for every NEW completed candle."""
#         self._new_candle_callbacks.append(callback)
    
#     def on_live_candle_update(self, callback: Callable) -> None:
#         """Register callback for live candle price updates."""
#         self._live_candle_callbacks.append(callback)





import time
import logging
from dataclasses import dataclass
from collections import defaultdict, deque
from typing import Optional, List, Callable
from iqoptionapi.instruments.options_assests import UNDERLYING_ASSESTS

logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """Clean candle data structure."""
    asset_name: str
    asset_id: int
    timeframe: int
    timestamp: int
    open: float
    close: float
    high: float
    low: float
    volume: float
    
    @classmethod
    def from_iq_message(cls, asset_name: str, asset_id: int, msg: dict) -> 'Candle':
        return cls(
            asset_name=asset_name,
            asset_id=asset_id,
            timeframe=msg.get('size'),
            timestamp=msg.get('from'),
            open=msg.get('open'),
            close=msg.get('close'),
            high=msg.get('max'),
            low=msg.get('min'),
            volume=msg.get('volume', 0)
        )


class CandleSubscriptionManager:
    """
    COMPLETE OWNER of all candle-related operations.
    """
    
    def __init__(self, websocket):
        """Initialize with WebSocket connection."""
        self.websocket = websocket
        
        # FIXED: Build maps correctly from UNDERLYING_ASSESTS
        # UNDERLYING_ASSESTS format: {"EURUSD": 1, "GBPUSD": 2, ...}
        self.name_to_id = UNDERLYING_ASSESTS  # "EURUSD" → 1
        self.id_to_name = {v: k for k, v in UNDERLYING_ASSESTS.items()}  # 1 → "EURUSD"
        
        # ─── Candle Storage ───
        self._candles: dict[str, dict[int, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=100))
        )
        
        # Live/current candle (being built)
        self._current_candle: dict[str, dict[int, Optional[dict]]] = defaultdict(
            lambda: defaultdict(lambda: None)
        )
        
        # ─── Subscription Management ───
        self._active_subscriptions: set[str] = set()  # {"EURUSD,60"}
        self._subscription_confirmed: dict[str, bool] = {}  # FIXED: Regular dict, not defaultdict
        
        # ─── Callbacks ───
        self._new_candle_callbacks: List[Callable] = []
        self._live_candle_callbacks: List[Callable] = []
    
    # -----------------------------------------------------------------
    # Entry point - called by MessageHandler
    # -----------------------------------------------------------------
    
    def on_candle_message(self, message: dict) -> None:
        """
        Called by MessageHandler._handle_candles_generated().
        This is the ONLY connection between MessageHandler and candles.
        """
        msg = message.get('msg', {})
        asset_id = msg.get('active_id')
        timeframe = msg.get('size')
        
        if not asset_id or not timeframe:
            logger.warning(f"Missing asset_id or timeframe: {msg}")
            return
        
        # FIXED: Get asset name from ID using id_to_name
        asset_name = self.id_to_name.get(asset_id)

        if not asset_name:
            logger.warning(f"Unknown asset_id: {asset_id}")
            return
        
        logger.debug(f"Received candle: {asset_name} {timeframe}s @ {msg.get('from')}")
        
        # Process the candle
        self._process_candle(asset_name, asset_id, timeframe, msg)
    
    def _process_candle(self, asset_name: str, asset_id: int, timeframe: int, msg: dict):
        """Process incoming candle - detects new vs updated candle."""
        candle_id = msg.get('id')
        timestamp = msg.get('from')
        
        # Check if this is a new candle or update to current
        current = self._current_candle[asset_name][timeframe]
        
        if current is None or current.get('id') != candle_id:
            # NEW CANDLE - previous candle is now closed
            if current is not None:
                # Store the completed candle in history
                completed_candle = Candle.from_iq_message(asset_name, asset_id, current)
                self._candles[asset_name][timeframe].append(completed_candle)

                # Snapshot AFTER appending, so it includes the just-closed candle
                history = list(self._candles[asset_name][timeframe])

                logger.debug(f"✅ New candle closed: {asset_name} {timeframe}s @ {completed_candle.timestamp}")
                
                # Notify new candle callbacks
                for cb in self._new_candle_callbacks:
                    try:
                        cb(completed_candle, history)
                    except Exception as e:
                        logger.error(f"New candle callback failed: {e}")
            
            # Start tracking new current candle
            self._current_candle[asset_name][timeframe] = msg
        else:
            # UPDATE to current candle (live price changes)
            self._current_candle[asset_name][timeframe] = msg
            
            # Notify live update callbacks
            for cb in self._live_candle_callbacks:
                try:
                    cb(asset_name, timeframe, msg)
                except Exception as e:
                    logger.error(f"Live candle callback failed: {e}")
        
        # FIXED: Mark subscription as confirmed for subscribe() wait loop
        sub_key = f"{asset_name},{timeframe}"
        if sub_key in self._active_subscriptions:
            self._subscription_confirmed[sub_key] = True
            logger.debug(f"✅ Subscription confirmed: {sub_key}")
    
    # -----------------------------------------------------------------
    # Subscription Methods
    # -----------------------------------------------------------------
    
    def subscribe(self, asset: str, timeframe: int = 60, timeout: int = 20) -> bool:
        """Subscribe to real-time candles."""
        if not self.websocket:
            logger.error("WebSocket not set")
            return False
        
        sub_key = f"{asset},{timeframe}"
        
        # Already subscribed?
        if sub_key in self._active_subscriptions:
            logger.debug(f"Already subscribed to {sub_key}")
            return True
        
        # FIXED: Get asset ID from name_to_id
        asset_id = self.name_to_id.get(asset)
        if not asset_id:
            logger.error(f"Unknown asset: {asset}. Available: {list(self.name_to_id.keys())[:10]}")
            return False
        
        # Reset confirmation flag for this subscription
        self._subscription_confirmed[sub_key] = False
        
        # Build subscription payload
        payload = {
            "name": "candle-generated",
            "params": {
                "routingFilters": {
                    "active_id": asset_id,
                    "size": timeframe
                }
            }
        }
        
        logger.info(f"🔌 Subscribing to {asset} (ID:{asset_id}) {timeframe}s candles...")
        
        # Send subscription request
        self.websocket.send_message("subscribeMessage", payload)
        
        # Add to active subscriptions BEFORE waiting for confirmation
        self._active_subscriptions.add(sub_key)
        
        # Wait for confirmation (first candle)
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._subscription_confirmed.get(sub_key, False):
                logger.info(f"✅ Subscribed to {asset} {timeframe}s candles")
                return True
            time.sleep(0.5)
        
        # Timeout - remove from active subscriptions
        self._active_subscriptions.discard(sub_key)
        self._subscription_confirmed.pop(sub_key, None)
        
        logger.error(f"❌ Subscription timeout for {asset} {timeframe}s (waited {timeout}s)")
        return False
    
    def unsubscribe(self, asset: str, timeframe: int) -> bool:
        """Unsubscribe from real-time candles."""
        if not self.websocket:
            return False
        
        sub_key = f"{asset},{timeframe}"
        
        if sub_key not in self._active_subscriptions:
            logger.debug(f"Not subscribed to {sub_key}")
            return True
        
        asset_id = self.name_to_id.get(asset)
        if not asset_id:
            logger.error(f"Unknown asset: {asset}")
            return False
        
        payload = {
            "name": "candle-generated",
            "params": {
                "routingFilters": {
                    "active_id": asset_id,
                    "size": timeframe
                }
            }
        }
        
        logger.info(f"🔌 Unsubscribing from {asset} {timeframe}s candles...")
        self.websocket.send_message("unsubscribeMessage", payload)
        
        self._active_subscriptions.discard(sub_key)
        self._subscription_confirmed.pop(sub_key, None)
        
        return True
    
    def unsubscribe_all(self):
        """Unsubscribe from all active streams."""
        for sub_key in list(self._active_subscriptions):
            asset, size = sub_key.split(',')
            self.unsubscribe(asset, int(size))
    
    # -----------------------------------------------------------------
    # Data Access Methods
    # -----------------------------------------------------------------
    
    def get_candles(self, asset: str, timeframe: int, count: int = 10) -> List[Candle]:
        """Get last N completed candles."""
        dq = self._candles[asset][timeframe]
        if not dq:
            return []
        return list(dq)[-count:]
    
    def get_latest_candle(self, asset: str, timeframe: int) -> Optional[Candle]:
        """Get most recent COMPLETED candle."""
        dq = self._candles[asset][timeframe]
        return dq[-1] if dq else None
    
    def get_current_candle(self, asset: str, timeframe: int) -> Optional[dict]:
        """Get the LIVE (in-progress) candle."""
        return self._current_candle[asset][timeframe]
    
    def get_current_price(self, asset: str, timeframe: int = 60) -> Optional[float]:
        """Get current price (close of latest candle OR live price)."""
        current = self.get_current_candle(asset, timeframe)
        if current:
            return current.get('close')
        
        latest = self.get_latest_candle(asset, timeframe)
        return latest.close if latest else None
    
    def get_candle_count(self, asset: str, timeframe: int) -> int:
        """Get number of stored candles."""
        return len(self._candles[asset][timeframe])
    
    def is_subscribed(self, asset: str, timeframe: int) -> bool:
        """Check if actively subscribed."""
        return f"{asset},{timeframe}" in self._active_subscriptions
    
    # -----------------------------------------------------------------
    # Callbacks
    # -----------------------------------------------------------------
    
    def on_new_candle(self, callback: Callable[[Candle], None]) -> None:
        """Register callback for every NEW completed candle."""
        self._new_candle_callbacks.append(callback)
    
    def on_live_candle_update(self, callback: Callable) -> None:
        """Register callback for live candle price updates."""
        self._live_candle_callbacks.append(callback)
    
    # -----------------------------------------------------------------
    # Debug Helpers
    # -----------------------------------------------------------------
    
    def get_status(self) -> dict:
        """Get current status for debugging."""
        return {
            "active_subscriptions": list(self._active_subscriptions),
            "confirmed": dict(self._subscription_confirmed),
            "candle_counts": {
                f"{asset},{tf}": len(self._candles[asset][tf])
                for asset in self._candles
                for tf in self._candles[asset]
            }
        }
    

    def on_new_candle_async(self, callback: Callable[[Candle], None]) -> None:
        """
        Register callback that runs in a separate thread pool.
        This prevents blocking the WebSocket thread.
        """
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
        def wrapped_callback(candle):
            executor.submit(callback, candle)
        
        self._new_candle_callbacks.append(wrapped_callback)