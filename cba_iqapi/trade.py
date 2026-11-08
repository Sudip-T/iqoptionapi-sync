import time
import logging
from datetime import datetime, UTC
from cba_iqapi.instruments.options_assests import UNDERLYING_ASSESTS
from cba_iqapi.utilities import *
from cba_iqapi.state import appstate

logger = logging.getLogger("api:trade")


# Custom exceptions for better error categorization
class TradeExecutionError(Exception):
    """Base exception for trade execution errors"""
    pass

class InvalidTradeParametersError(TradeExecutionError):
    """Raised when trade parameters are invalid"""
    pass


class TradeManager:
    """
    Manages IQOption trading operations
    
    Handles trade parameter validation, order execution, confirmation waiting,
    and trade outcome tracking.
    """
    def __init__(self, websocket_manager, message_handler):
        self.ws_manager = websocket_manager
        self.message_handler = message_handler

    def _place_digital_option_trade(self, asset:str, amount:float, direction:str, expiry:int=1):
        """
        Execute a digital option trade with validation and error handling.
        
        Args:
            asset: Asset name to trade
            amount: Trade amount in dollars (minimum $1)
            direction: 'put' or 'call' trade direction
            expiry: Expiry time in minutes (default: 1)
            
        Returns:
            tuple: (success: bool, order_id: int or error_message: str)
        """

        try:
            direction = direction.lower()

            # Validate all parameters before execution
            self._validate_options_trading_parameters(asset, amount, direction, expiry)

            # Convert direction to API format
            direction_map = {'put': 'P', 'call': 'C'}        
            direction = direction_map[direction]

            # Build message and send trade request
            msg = self.prepare_digital_trade_payload(asset, amount, expiry, direction)
            request_id = self.ws_manager.send_message("sendMessage", msg)

            return self.wait_for_order_confirmation(request_id, expiry)
            
        except (InvalidTradeParametersError, TradeExecutionError, KeyError) as e:
                    logger.error(f"Trade execution failed: {e}")
        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error during trade execution: {e}", exc_info=True)

    def wait_for_order_confirmation(self, request_id:int, expiry:int, timeout:int=10):
        """
        Wait for trade order confirmation from the server.
        
        Args:
            request_id: Unique request identifier to track
            timeout: Maximum wait time in seconds (default: 10)
            
        Returns:
            tuple: (success: bool, order_id: int or error_message: str)
        """
        start_time = time.time()
        
        # Poll for order confirmation within timeout
        while time.time() - start_time < timeout:
            result = self.message_handler.orders_confirmation.get(request_id)
            if result is not None:
                if isinstance(result, int):
                    # Success: result is order ID
                    expires_in = get_remaining_secs(self.message_handler.server_time, expiry)
                    logger.info(f'Order Placed, ID: {result}, Expires in: {expires_in} Seconds')
                    return True, result
                else:
                    # Failure: result is error message
                    return False, result
            time.sleep(0.1)
                
        logger.error(f"Order Confirmation timed out after {timeout} seconds")


    def prepare_digital_trade_payload(self, asset: str, amount: float, 
                           expiry: int, direction: str) -> str:
        """
        Build WebSocket message body for digital options trade.
        
        Args:
            asset: Asset name to trade
            amount: Trade amount in dollars
            expiry: Expiry time in minutes
            direction: Trade direction ('P' for put, 'C' for call)
            
        Returns:
            Formatted message dictionary for API
        """

        # Get asset ID and calculate expiration timestamp
        active_id = str(get_asset_id(asset))
        expiration = get_expiry_timestamp(self.message_handler.server_time, expiry)
        date_formatted = datetime.fromtimestamp(expiration, UTC).strftime("%Y%m%d%H%M")

        # Build instrument ID following IQOption format
        instrument_id = f"do{active_id}A{date_formatted[:8]}D{date_formatted[8:]}00T{expiry}M{direction}SPT"

        return {
            "name": "digital-options.place-digital-option",
            "version": "3.0",
            "body": {
                "user_balance_id": appstate.balance_id,
                "instrument_id": str(instrument_id),
                "amount": str(amount),
                "asset_id": int(active_id),
                "instrument_index": 0,
                # "instrument_index": 83931
            }
        }
    
    def _validate_options_trading_parameters(self, asset: str, amount: float, direction: str, expiry: int) -> None:
        """
        Validate all trade parameters before order execution.
            
        Raises:
            InvalidTradeParametersError: If any parameter is invalid
            TradeExecutionError: If account is not available
        """

        # Validate asset name
        if not isinstance(asset, str) or not asset.strip():
            raise InvalidTradeParametersError("Asset name cannot be empty")
        
        # Validate trade amount (minimum $1)
        if not isinstance(amount, (int, float)) or amount < 1:
            raise InvalidTradeParametersError(f"Minimum Bet Amount is $1, got: {amount}")
        
        # Validate trade direction
        direction = direction.lower().strip()
        if direction not in ['put', 'call']:
            raise InvalidTradeParametersError(f"Direction must be 'put' or 'call', got: {direction}")
        
        # Validate expiry time
        if not isinstance(expiry, int) or expiry < 1:
            raise InvalidTradeParametersError(f"Expiry must be positive integer, got: {expiry}")
        
        # Ensure active account is available
        if not appstate.balance_id:
            raise TradeExecutionError("No active account available")
        
    def _place_binary_options_trade(self, asset:str, amount:float, direction:str, expiry:int=1):
        """Place a binary/turbo option trade."""
        try:
            expiration = get_expiry_timestamp(self.message_handler.server_time, expiry)

            if expiry < 5:
                option_type_id = 3 # turbo (exp > 5mins )
            else:
                option_type_id = 1 # binary ( exp > 5 mins )

            msg = {
                    "body":{
                            "price": int(amount),
                            "active_id": int(get_asset_id(asset)),
                            "expired": int(expiration),
                            "direction": direction.lower(),
                            "option_type_id": option_type_id,
                            "user_balance_id": appstate.balance_id
                        },
                    "name": "binary-options.open-option",
                    "version": "1.0"
                    }
            
            request_id = self.ws_manager.send_message("sendMessage", msg)
            return self.wait_for_order_confirmation(request_id, expiry)
            
        except Exception as e:
            logger.error(f"Binary trade failed: {e}")
            return False, str(e)

    def get_trade_outcome(self, order_id: int, expiry:int=1):
        """
        Monitor trade and return outcome when closed.
        
        Args:
            order_id: Order ID to monitor
            expiry: Original expiry time in minutes for timeout calculation
            
        Returns:
            tuple: (success: bool, pnl: float or None)
                success=True with PnL if trade closed, False if timeout
        """
        start_time = time.time()
        timeout = get_remaining_secs(self.message_handler.server_time, expiry)

        # Poll for trade closure with timeout + 3-second buffer
        while time.time() - start_time < timeout + 3:
            order_data = self.message_handler.position_info.get(order_id, {})

            # Check if trade is closed
            if order_data:
                order_data = order_data.to_dict()
                # logger.info(f"IDs: {order_id} | Result: {order_data['result']}, PnL: ${order_data['pl_amount']:.2f}")
                return True, order_data, order_data['pl_amount']
            
            time.sleep(.5) # Check every 500ms

        # Trade did not close within expected timeframe
        return False, None