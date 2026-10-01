import os
import sys
import time
import logging
import requests
import threading
from dotenv import load_dotenv
from typing import Optional, List, Callable

from iqoptionapi.models import *
from iqoptionapi.state import appstate
from iqoptionapi.trade import TradeManager
from iqoptionapi.markets import MarketManager
from iqoptionapi.utilities import get_asset_id
from iqoptionapi.accounts import AccountManager
from iqoptionapi.instruments import options_assests
from iqoptionapi.wsmanager.iqwebsocket import WebSocketManager
from iqoptionapi.wsmanager.message_handler import MessageHandler
from iqoptionapi.candles import CandleSubscriptionManager


logger = logging.getLogger("iqoption api")
load_dotenv()


class IQOptionClient:
    """
    Main client class for IQOption automated trading.
    
    Provides a unified interface for account management, market data,
    and trade execution through websocket connections.
    """
    def __init__(self, email=None, password=None, account_type='demo'):
        """
        Initialize the IQOption API client.
        
        Args:
            email (str, optional): Login email. Defaults to settings.EMAIL
            password (str, optional): Login password. Defaults to settings.PASSWORD  
            account_type (str, optional): Account type.
        """
        self.appstate = appstate
        self.email = email or os.getenv('IQ_EMAIL')
        self.password = password or os.getenv('IQ_PASSWORD')
        self.appstate.validate_account_type(account_type)

        # Initialize HTTP session for login requests
        self._connected = False
        self.subscribe_candle = []
        self.session = requests.Session()

        self.subscribe_candle = []
        self.trader_mood = []
        
        # Initialize core components
        self._init_components()
        
        logger.info('IQOptionAPIClient initialized successfully')
    
    def _init_components(self) -> None:
        """Initialize or re-initialize all core components."""        
        self.message_handler = MessageHandler()
        self.websocket = WebSocketManager(self.message_handler)
        self.account_manager = AccountManager(self.websocket, self.message_handler)
        self.market_manager = MarketManager(self.websocket, self.message_handler)
        self.trade_manager = TradeManager(self.websocket, self.message_handler)
        self.candle_manager = CandleSubscriptionManager(self.websocket)
        self.message_handler.set_candle_manager(self.candle_manager)

    def _login(self):
        """
        Authenticate with IQOption using email/password.
        
        Returns:
            bool: True if login successful, None otherwise
        """

        # Validate required credentials
        if not all([self.email, self.password]):
            print("Email and password are required!")
            sys.exit()

        if self._connected:
            logger.warning('Already connected to iqoption')
            return

        try:
            # Send login request
            response = self.session.post(
                url='https://api.iqoption.com/v2/login', 
                data={'identifier': self.email, 'password': self.password})
            response.raise_for_status()

            # Check if session ID was received (login success indicator)
            if self.get_session_id():
                logger.info(f'Successfully logged into an account')
                return True
        except Exception as e:
            logger.warning(e)

    
    def _logout(self, data=None):
        """
        Log out from IQOption and close session.
        
        Args:
            data (dict, optional): Additional logout data
        """
        if self.session.post(
            url="https://auth.iqoption.com/api/v1.0/logout", 
            data=data).status_code == 200:
            self._connected = False
            logger.info(f'Logged out Successfully')
    
    def get_session_id(self):
        """
        Get the current session ID (SSID) from cookies.
        
        Returns:
            str: Session ID if available, None otherwise
        """
        return self.session.cookies.get('ssid')
    
    def connect(self):
        """
        Establish full connection: login + websocket + authentication.
        
        Sets up the complete connection pipeline including websocket
        authentication and account initialization.
        """
        if self._login():
            # Start websocket connection
            self.websocket.start_websocket()

            # Authenticate websocket using session ID
            self.websocket.send_message('ssid', self.get_session_id())

            ## Wait for profile confirmation (indicates successful auth)
            while self.appstate.profile_msg is None:
                time.sleep(.1)

            self.account_manager._portfolio_position_change('subscribeMessage')

            self._connected = True
            return True
        
    # Expose manager methods for convenience
    def get_balance(self):
        """
        Get the balance of the currently active account.
        
        Returns:
            float: Current account balance
        """
        self._ensure_connected()
        return self.account_manager.get_balance()
    
    def refill_demo(self, amount=10000):
        """
        Refill demo account with specified amount.
        
        Args:
            amount (int): Amount to add to demo account. Defaults to 10000
            
        Returns:
            bool: True if refill successful
        """
        self._ensure_connected()
        return self.account_manager.refill_demo_balance(amount)
    
    def get_tournament_accounts(self):
        """
        Retrieve list of available tournament accounts.
        
        Returns:
            list: Available tournament accounts
        """
        self._ensure_connected()
        return self.account_manager.get_tournament_accounts()
    
    def switch_account(self, account_type: str):
        """
        Switch to a different account type (demo/real/tournament).
        
        Args:
            account_type (str): Target account type
            
        Returns:
            bool: True if switch successful, False if already on target account
        """
        self._ensure_connected()
        if account_type.lower() == self.appstate.balance_type_str:
            logger.warning(f'Already on {account_type.lower()} account. No switch needed.')
            return False
        return self.account_manager.switch_account(account_type)
    
    # Market Data Methods
    def get_candles(self, asset_name='EURUSD-op', count=50, timeframe=60):
        """
        Retrieve historical candlestick data for an asset.
        
        Args:
            asset_name (str): Asset symbol. Defaults to 'EURUSD-op'
            count (int): Number of candles to retrieve. Defaults to 50
            timeframe (int): Timeframe in seconds. Defaults to 60
            
        Returns:
            list: Historical candle data
        """
        self._ensure_connected()
        return self.market_manager.get_candle_history(asset_name, count, timeframe)
    
    def save_candles_to_csv(self, candles_data=None, filename='candles'):
        """
        Export candlestick data to CSV file.
        
        Args:
            candles_data (list, optional): Candle data to export
            filename (str): Output filename. Defaults to 'candles'
            
        Returns:
            bool: True if save successful
        """
        return self.market_manager.save_candles_to_csv(candles_data, filename)
    
    def _ensure_connected(self):
        """
        Verify that the client is connected before executing operations.
        
        Raises:
            Exception: If client is not connected
        """
        if not self._connected:
            raise Exception("Client is not connected. Call connect() first.")
        
    def get_position_history_by_time(self, instrument_type: List[str],
                                    start_time: Optional[str] = None,
                                    end_time: Optional[str] = None):
        """
        Retrieve position history within a specific time range.
        
        Args:
            instrument_type (List[str]): Types of instruments to include
            start_time (str, optional): Start time filter
            end_time (str, optional): End time filter
            
        Returns:
            list: Position history within specified time range
        """
        self._ensure_connected()
        return self.account_manager.get_position_history_by_time(instrument_type, start_time=start_time, end_time=end_time)
    
    def get_position_history_by_page(self, instrument_type: List[str],
                                    limit: int = 300,
                                    offset: int = 0):
        """
        Retrieve paginated position history.
        
        Args:
            instrument_type (List[str]): Types of instruments to include
            limit (int): Maximum records per page. Defaults to 300
            offset (int): Number of records to skip. Defaults to 0
            
        Returns:
            list: Paginated position history
        """
        self._ensure_connected()
        return self.account_manager.get_position_history_by_page(instrument_type, limit=limit, offset=offset)
    

    def execute_options_trade(self, trade_params: OptionsTradeParams):
        """
        Execute an options trade (digital or binary).
        
        Args:
            trade_params (TradeParams): Trade parameters object containing all trade details
                
        Returns:
            dict: Trade execution result with order ID
            
        Example:
            params = TradeParams(asset="EURUSD", amount=100, direction=Direction.CALL, 
                               expiry=5, option_type=OptionType.BINARY)
            result = place_trade(params)
        """
        self._ensure_connected()
        
        # Route to appropriate trade manager method based on option type
        if trade_params.option_type == OptionType.DIGITAL_OPTION:
            return self.trade_manager._place_digital_option_trade(
                trade_params.asset, 
                trade_params.amount, 
                trade_params.direction.value, 
                expiry=trade_params.expiry
            )
        elif trade_params.option_type == OptionType.BINARY_OPTION:
            return self.trade_manager._place_binary_options_trade(
                trade_params.asset, 
                trade_params.amount, 
                trade_params.direction.value, 
                expiry=trade_params.expiry
            )
        
    def get_trade_outcome(self, order_id: int, expiry: int):
        """
        Get the outcome of a completed trade.
        
        Args:
            order_id (int): ID of the trade order
            expiry (int): Expiry time in minutes
            
        Returns:
            dict: Trade outcome (win/loss/refund) and payout details
        """
        self._ensure_connected()
        return self.trade_manager.get_trade_outcome(order_id, expiry=expiry)
    
    def disconnect(self):
        """
        Gracefully disconnect from IQOption and close websocket.
        """
        if self.websocket:
            self.websocket.close()
        self._logout()
        self._connected = False
        logger.info("Disconnected from IQOption")


    # ------------------------Subscribe ONE SIZE-----------------------
    # -----------------------------------------------------------------
    # Legacy Candle Methods (delegated to CandleSubscriptionManager)
    # -----------------------------------------------------------------

    def start_candle_stream(self, asset: str, candle_size: int = 60) -> bool:
        """
        Start real-time candle stream for an asset.
        
        Legacy method wrapper that delegates to CandleSubscriptionManager.
        
        Args:
            asset: Asset name (e.g., "EURUSD", "GBPUSD")
            candle_size: Timeframe in seconds (60, 300, 900, etc.)
            
        Returns:
            True if subscription successful, False otherwise
            
        Example:
            client = IQOptionClient()
            client.connect()
            client.start_candle_stream("EURUSD", 60)
        """
        self._ensure_connected()
        return self.candle_manager.subscribe(asset, candle_size)

    def stop_candle_stream(self, asset: str, candle_size: int) -> bool:
        """
        Stop real-time candle stream for an asset.
        
        Legacy method wrapper that delegates to CandleSubscriptionManager.
        
        Args:
            asset: Asset name (e.g., "EURUSD", "GBPUSD")
            candle_size: Timeframe in seconds (60, 300, 900, etc.)
            
        Returns:
            True if unsubscription successful, False otherwise
        """
        self._ensure_connected()
        return self.candle_manager.unsubscribe(asset, candle_size)

    def subscribe_live_candles(self, actives) -> bool:
        """Subscribe to all active actives and register the candle callback."""

        results: dict[str, bool] = {}
        threads = []

        def subscribe_one(active):
            results[active.asset] = self.candle_manager.subscribe(
                active.candle_asset,
                timeframe=active.candle_timeframe,
            )

        for i, active in enumerate(actives):
            # Add delay before each subscription (except first)
            if i > 0:
                time.sleep(0.5)  # 200ms delay

            t = threading.Thread(target=subscribe_one, args=(active,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # failed = [a for a, ok in results.items() if not ok]
        # success = [a for a, ok in results.items() if ok]

        failed, success = [], []
        for asset, ok in results.items():
            (success if ok else failed).append(asset)

        if failed:
            logger.error("Failed to subscribe: %s", failed)

        # self.on_new_candle(self.on_new_candle)
        self._running = True
        return len(success) > 0
    

    def get_current_price(self, asset: str, timeframe: int = 60) -> Optional[float]:
        """
        Get current price for an asset using cached candle data.
        
        Legacy method wrapper that delegates to CandleSubscriptionManager.
        
        Args:
            asset: Asset name (e.g., "EURUSD", "GBPUSD")
            timeframe: Timeframe in seconds to use for price (default: 60)
            
        Returns:
            Current price as float, or None if not available
        """
        if not self._connected:
            return None
        return self.candle_manager.get_current_price(asset, timeframe)

    def get_last_candles(self, asset: str, timeframe: int, count: int = 10) -> List:
        """
        Get last N completed candles for an asset/timeframe.
        
        Args:
            asset: Asset name (e.g., "EURUSD")
            timeframe: Timeframe in seconds (60, 300, etc.)
            count: Number of candles to return
            
        Returns:
            List of Candle objects (most recent last)
        """
        if not self._connected:
            return []
        return self.candle_manager.get_candles(asset, timeframe, count)

    def get_latest_candle(self, asset: str, timeframe: int) -> Optional[dict]:
        """
        Get the most recent COMPLETED candle for an asset/timeframe.
        
        Args:
            asset: Asset name (e.g., "EURUSD")
            timeframe: Timeframe in seconds (60, 300, etc.)
            
        Returns:
            Candle object or None
        """
        if not self._connected:
            return None
        return self.candle_manager.get_latest_candle(asset, timeframe)

    def get_current_candle(self, asset: str, timeframe: int) -> Optional[dict]:
        """
        Get the LIVE (in-progress) candle for an asset/timeframe.
        
        Args:
            asset: Asset name (e.g., "EURUSD")
            timeframe: Timeframe in seconds (60, 300, etc.)
            
        Returns:
            Raw candle dict from IQ Option (live, still updating)
        """
        if not self._connected:
            return None
        return self.candle_manager.get_current_candle(asset, timeframe)

    def is_subscribed_to_candles(self, asset: str, timeframe: int) -> bool:
        """
        Check if actively subscribed to candle stream for an asset/timeframe.
        
        Args:
            asset: Asset name (e.g., "EURUSD")
            timeframe: Timeframe in seconds (60, 300, etc.)
            
        Returns:
            True if subscribed, False otherwise
        """
        if not self._connected:
            return False
        return self.candle_manager.is_subscribed(asset, timeframe)

    def on_new_candle(self, callback: Callable):
        """
        Register callback for when a new candle completes.
        
        Args:
            callback: Function that accepts a Candle object
            
        Example:
            def my_callback(candle):
                print(f"New candle: {candle.asset_name} close: {candle.close}")
            
            client.on_new_candle(my_callback)
        """
        self.candle_manager.on_new_candle(callback)

    def on_live_candle_update(self, callback: Callable):
        """
        Register callback for live candle price updates.
        
        Args:
            callback: Function that accepts (asset_name, timeframe, candle_dict)
            
        Example:
            def on_update(asset, tf, candle):
                print(f"Live update: {asset} price: {candle['close']}")
            
            client.on_live_candle_update(on_update)
        """
        self.candle_manager.on_live_candle_update(callback)


    # -----------------traders_mood----------------------
    def subscribe_traders_mood(self, ASSET, timeout: float = 5.0):
        if ASSET in self.trader_mood == False:
            self.trader_mood.append(ASSET)

        return self.market_manager.stream_traders_mood(ASSET)

    def unsubscribe_traders_mood(self, ASSET):
        if ASSET in self.trader_mood == True:
            del self.trader_mood[ASSET]

        self.market_manager.stop_traders_mood(ASSET)

    def get_traders_mood(self, ASSET):
        # return highter %
        try:
            return self.message_handler.traders_mood[get_asset_id(ASSET)]
        except Exception as e:
            return f'Something went wrong! Reason: {e}'

    def get_all_traders_mood(self):
        # return highter %
        return self.message_handler.traders_mood