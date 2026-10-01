import json
import logging
logger = logging.getLogger(__name__)
from iqoptionapi.state import appstate
from collections import defaultdict, deque
from iqoptionapi.models import TradeOutcomeChecker
from iqoptionapi.candles import CandleSubscriptionManager


def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n - 1, type))


class MessageHandler:
    """
    Handles various types of messages received from IQ Option Websocket.
    """
    def __init__(self, candle_manager:CandleSubscriptionManager=None):
        """
        Initialize the MessageHandler with default values for all message types.
        
        Sets up storage for profile data, balance information, market data, and position tracking.
        """

        self.candle_manager = candle_manager
        
        # Keep existing non-candle attributes
        self.server_time = None
        self.underlying_list = None
        self._underlying_assests = None
        self.initialization_data = None
        self.hisory_positions = None
        self.position_info = {}
        self.traders_mood = {}
        self.orders_confirmation = {}
        self.trade_outcome_checker = TradeOutcomeChecker()


        # self.server_time = None

        # # Market and time data
        # self.candles = None
        # self.underlying_list = None
        # self.initialization_data = None

        # self.candle_generated_check = nested_dict(2, dict)

        # # Position tracking
        # self.hisory_positions = None

        # self.position_info = {}
        # self.orders_confirmation = {}

        # self.trade_outcome_checker = TradeOutcomeChecker()

        # self.real_time_candles = nested_dict(3, dict)
        # self.candle_generated_check = nested_dict(2, dict)
        # self.real_time_candles_maxdict_table = nested_dict(2, dict)

        # self.candles = defaultdict(lambda: defaultdict(lambda: deque(maxlen=10)))

        # # Candle history storage
        # self._current_candle = None
        # self._current_id     = None
        # self.candle_history  = nested_dict(2, lambda: deque(maxlen=9))
        # self._new_candle_callback = None   # called when a new candle opens

    def set_candle_manager(self, candle_manager):
        """Inject candle manager after initialization."""
        self.candle_manager = candle_manager

    def handle_message(self, message):
        """
        Route incoming messages to appropriate handler method based on message name.
        
        Args:
            message (dict): The incoming message containing 'name' and other data
        """
        message_name = message.get('name')

        # Map message names to their corresponding handler methods
        handlers = {
            'profile': self._handle_profile,
            'candles': self._handle_candles,
            'balances': self._handle_balances,
            'balance-changed': self._handle_balance_changed,
            'timeSync': self._handle_server_time,
            'underlying-list': self._handle_underlying_list,
            'initialization-data': self._handle_initialization_data,
            'training-balance-reset': self._handle_training_balance_reset,
            "history-positions":self._handle_position_history,
            "digital-option-placed":self._handle_option_opened,
            "position-changed":self._handle_position_changed,
            "option":self._handle_option_opened,

            "socket-option-closed":self._handle_socket_option_closed,
            "candle-generated":self._handle_candles_generated,
            # "candle-generated": self._on_candle,
            "traders-mood-changed":self._handle_traders_mood_changed,
        }

        # Get the appropriate handler and invoke it if found
        handler = handlers.get(message_name)
        if handler:
            handler(message)
    
    def _handle_server_time(self, message):
        """
        Handle server time synchronization messages.
        
        Args:
            message (dict): Message containing server time information in 'msg' field
        """
        self.server_time = message['msg']
    
    def _handle_profile(self, message):
        """
        Handle user profile messages and extract active balance ID for demo account.
        
        Processes profile data and identifies the demo account balance ID (type 4).
        Real account balance has type 1, demo account has type 4.
        
        Args:
            message (dict): Profile message containing user account information and balances
        """
        appstate.profile_msg = message
        for balance in message['msg']['balances']:
            if balance['type'] == appstate.balance_type:
                appstate.update(balance_id=balance['id'])
            appstate.account_list['type'] = balance

    def _handle_balances(self, message):
        """
        Handle balance update messages.
        
        Args:
            message (dict): Message containing current balance information
        """
        balance = next(
            (account['amount'] for account in message['msg']
            if account['type'] == appstate.balance_type),
            None
        )
        appstate.update(balance=balance, balance_data=message['msg'])

    def _handle_balance_changed(self, message):
        appstate.update(balance=message['msg']['current_balance']['amount'])
    
    def _handle_training_balance_reset(self, message):
        """
        Handle demo account balance reset responses.
        
        Logs the result of balance reset operations with appropriate log levels
        based on the status code received.
        
        Args:
            message (dict): Response message from balance reset request
                          Contains 'status' field and optional error message
        """
        if message['status'] == 2000: # Success status code
            logger.info('Demo Acoount Balance Reset Successfully')
        elif message['status'] == 4001: # Error status code
            logger.warning(message['msg']['message'])
        else:
            logger.info(message)
    
    def _handle_initialization_data(self, message):
        """
        Handle platform initialization data.
        
        Args:
            message (dict): Initialization message containing underlying assets and platform data
        """
        self._underlying_assests = message['msg']
    
    def _handle_candles(self, message):
        """
        Handle candlestick/OHLCV price data messages.
        
        Args:
            message (dict): Message containing candle data in 'msg.candles' field
        """
        self.candles = message['msg']['candles']
    
    def _handle_underlying_list(self, message):
        """
        Handle underlying asset list messages.
        
        Processes different types of underlying asset lists based on the message type.
        Digital options and other instrument types may have different data structures.
        
        Args:
            message (dict): Message containing underlying asset information
        """
        if message['msg'].get('type', None) == 'digital-option':
            # Digital options have underlying assets in 'underlying' field
            self._underlying_assests = message['msg']['underlying']
        else:
            # marginal instrument types have assets in 'items' field
            self._underlying_assests = message['msg']['items']

    def _save_data(self, message, filename):
        """
        Utility method to save message data to a JSON file.
        
        Args:
            message (dict): The message data to save
            filename (str): The filename (without .json extension) to save to
        """
        with open(f'{filename}.json', 'w') as file:
            json.dump(message, file, indent=4)
        
    def _handle_position_history(self, message):
        """
        Handle historical position data messages.
        
        Args:
            message (dict): Message containing historical position data in 'msg.positions' field
        """
        self.hisory_positions = message['msg']['positions']

    def _handle_option_opened(self, message):
        """
        Handle digital option placement confirmation messages.
        
        Stores the option ID or error message based on the placement result.
        Uses request_id as the key to track placement requests.
        
        Args:
            message (dict): Placement confirmation containing either option ID or error message
        """
        if message["msg"].get("id") != None: # Successful placement - store the option ID
            self.orders_confirmation[message["request_id"]] = message["msg"].get("id")
        else: # Failed placement - store the error message
            self.orders_confirmation[message["request_id"]] = message["msg"].get("message")

        # self._save_data(message['msg'], 'positions_opened')

    def _handle_position_changed(self, message):
        """
        Handle position status change messages.
        
        Updates position information and saves the latest position data to file.
        Uses the first order ID from the raw event as the key for tracking.
        
        Args:
            message (dict): Position change message containing updated position status
        """

        if message['msg']['status'] == 'closed':
            self.position_info[int(message["msg"]["raw_event"]["order_ids"][0])] = \
            self.trade_outcome_checker.check_trade_outcome(message['msg'])

        # Save position data to file for debugging/logging purposes
        # self._save_data(message['msg'], 'positions')

    def _handle_socket_option_closed(self, message):
        """
        Handle position status change messages.
        
        Updates position information and saves the latest position data to file.
        Uses the first order ID from the raw event as the key for tracking.
        
        Args:
            message (dict): Position change message containing updated position status
        """

        self.position_info[int(message["msg"]["id"])] = \
            self.trade_outcome_checker.check_trade_outcome(message['msg'])

    def _handle_candles_generated(self, message: dict):
        """
        Handle candle-generated messages.
        DOES NOTHING except forward to candle manager.
        """
        if self.candle_manager:
            self.candle_manager.on_candle_message(message)

    def _handle_traders_mood_changed(self, message: dict):
        self.traders_mood[message["msg"]["asset_id"]]=message["msg"]["value"]