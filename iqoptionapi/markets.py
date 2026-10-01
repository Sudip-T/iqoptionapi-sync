import time
import logging
import pandas as pd
import mplfinance as mpf
from typing import List, Dict
from iqoptionapi.utilities import get_asset_id
from iqoptionapi.iqapi import InstrumentType

logger = logging.getLogger(__name__)


class MarketManager:
    """
    Manages IQOption market data operations including candle history, asset management etc.
    
    Handles historical/real-time candle data, live chart plotting with threading,
    asset ID lookups, and WebSocket message processing.
    """
    def __init__(self, websocket_manager, message_handler):
        self.ws_manager = websocket_manager
        self.message_handler = message_handler
    
    def get_candle_history(self, asset_name: str, count: int = 50, timeframe: int = 60):
        """
        Get historical candle data for an asset
        
        Args:
            asset_name: Name of the trading asset
            count: Number of candles to retrieve
            timeframe: Timeframe of each candle in seconds
        """

        # Reset state and prepare request
        self.message_handler.candles = None
        
        name = "sendMessage"
        msg = {
            "name": "get-candles",
            "version": "2.0",
            "body": {
                "active_id": get_asset_id(asset_name),
                "size": timeframe,
                "count": count,
                "to": self.message_handler.server_time,
                "only_closed": True,
                "split_normalization": True
            }
        }
        
        self.ws_manager.send_message(name, msg)
        
        # Wait for response
        while self.message_handler.candles is None:
            time.sleep(0.1)

        return self.message_handler.candles
    
    def plot_candles(self, candles_data=None):
        """
        Display candlestick chart using mplfinance.
        
        Args:
            candles_data: Candle data list (uses cached data if None)
        """
        if candles_data is None:
            candles_data = self.message_handler.candles
        
        if not candles_data:
            print("No candle data available")
            return
        
        # Convert and format data
        df = pd.DataFrame(candles_data)
        df = df.rename(columns={
            'open': 'Open',
            'max': 'High',
            'min': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        
        df['timestamp'] = pd.to_datetime(df['from'], unit='s')
        df = df.set_index('timestamp')
        
        # Create candlestick chart
        mpf.plot(
            df,
            type='candle',
            style='charles',
            title='IQOption Candles',
            ylabel='Price',
            volume=False
        )
    
    def save_candles_to_csv(self, candles_data=None, filename: str = 'candles'):
        """
        Export candle data to CSV file.
        
        Args:
            candles_data: Data to save (uses cached if None)
            filename: Output filename without extension
        """
        if candles_data is None:
            candles_data = self.message_handler.candles
        
        if not candles_data:
            print("No candle data to save")
            return
        
        # Format data and export
        df = pd.DataFrame(candles_data)
        df = df.rename(columns={'max': 'high','min': 'low'})

        df['from'] = pd.to_datetime(df['from'], unit='s')
        df['to'] = pd.to_datetime(df['to'], unit='s')
        
        df.to_csv(f'{filename}.csv', index=False)

    def _build_msg_body(self, instrument_type:str):
        """
        Construct WebSocket message body for different instrument types.
        
        This private method creates the appropriate message structure based on
        the instrument type, as each type requires different API endpoints and parameters.
        
        Args:
            instrument_type (str): Type of instrument ('digital-option', 'binary-option',
                'forex', 'cfd', or 'crypto')
                
        Returns:
            dict: Formatted message body for WebSocket transmission
            
        Note:
            - Digital options use v3.0 API with suspension filtering
            - Binary options use v4.0 initialization data endpoint
            - Marginal instruments (forex/cfd/crypto) use v1.0 specific endpoints
        """
        if instrument_type == 'digital-option':
            msg = {
                "name": "digital-option-instruments.get-underlying-list",
                "version": "3.0",
                "body": {
                    "filter_suspended": True
                }
            }
        elif instrument_type == 'binary-option':
            msg= {
                'body':{},
                'name':'get-initialization-data',
                'version':'4.0'
            }
        elif instrument_type in ['forex', 'cfd', 'crypto']:
            msg = {
                'body':{},
                'version':'1.0',
                'name':f'marginal-{instrument_type}-instruments.get-underlying-list'
            }

        return msg
    
    def get_underlying_assests(self, instrument_type:str):
        """
        Retrieve list of available underlying assets for a specific instrument type.
        
        Validates the instrument type, sends an API request, and waits
        for the response containing available trading instruments.
        
        Args:
            instrument_type (str): Type of instrument to query. Must be one of:
                'forex', 'cfd', 'crypto', 'digital-option', 'binary-option'
                
        Returns:
            list: List of underlying asset dictionaries containing asset information
            
        Raises:
            ValueError: If instrument_type is not supported
    
        """

        # Validate instrument type against enum values
        valid_types = {instrument.value for instrument in InstrumentType}
        if instrument_type not in valid_types:
            raise ValueError(f"Unsupported instrument type: {instrument_type}. "
                           f"Must be one of: {', '.join(valid_types)}")

        # Reset state to ensure fresh data
        self.message_handler._underlying_assests = None

        self.ws_manager.send_message('sendMessage', self._build_msg_body(instrument_type))

        # Wait for response (blocking operation)
        while self.message_handler._underlying_assests == None:
            time.sleep(.1)

        return self.message_handler._underlying_assests


    def save_underlying_assests_to_file(self):
        """        
        Retrieves assets from multiple instrument types, filters out
        suspended instruments, and generates two separate Python files containing
        asset dictionaries for easy import and use.
        
        Generated files:
            - options_assests.py: Contains digital and binary options assets
            - marginal_assests.py: Contains forex, CFD, and crypto assets
            
        Returns:
            None: Creates Python files in the current directory
            
        Note:
            - Only active (non-suspended) assets are included
            - Assets are sorted by ID for consistent ordering
            - Files are auto-generated with proper Python dictionary format
        """

        # Initialize storage dictionaries
        options_underlying_assets = {}
        marginal_underlying_assets = {}

        # Get underlying assets for marginal trading instruments (forex, CFD, crypto)
        for instrument in ['forex', 'cfd', 'crypto']:
            underlying_list = self.get_underlying_assests(instrument)
            for item in underlying_list:
                if item['is_suspended'] == False:
                    marginal_underlying_assets[item['name']] = item['active_id']

        # Get underlying assets for digital options
        digital_underlying = self.get_underlying_assests('digital-option')

        # Get underlying assets for binary options
        initialization_data = self.get_underlying_assests('binary-option')

        # Filters out suspended asset and add to options_underlying_assets
        for assest in digital_underlying:
            if assest['is_suspended'] == False:
                options_underlying_assets[assest['name']] = assest['active_id']

        instruments = ['binary', 'blitz', 'turbo']
        for instrument in instruments:
            if instrument in initialization_data:
                for _, value  in initialization_data[instrument]['actives'].items():
                    if value['is_suspended'] == False:
                        options_underlying_assets[value['ticker']] = value['id']

        # Export to separate files for different trading types
        self._export_assets_to_fiel(options_underlying_assets, 'options_assests.py')
        self._export_assets_to_fiel(marginal_underlying_assets, 'marginal_assests.py')

    def _export_assets_to_fiel(self, data:dict, file:str) -> None:
        """        
        Creates a Python file containing a dictionary of assets
        sorted by ID, with proper formatting for easy import and readability.
        
        Args:
            data (dict): Dictionary mapping asset names to IDs
            file (str): Output filename including extension
            
        Returns:
            None: Creates a formatted Python file
        """

        # Sort assets by ID for consistent file output
        data = dict(sorted(data.items(), key=lambda item:item[-1]))

        # Write formatted Python file
        with open(f'{file}', 'w') as file:
            file.write('#Auto-Generated Underlying List\n')
            file.write('UNDERLYING_ASSESTS = {\n')
            for key,value in data.items():
                file.write(f"   '{key}':{value},\n")
            file.write('}\n')

    def subscribe_candles(self, asset_name: str, timeframe: int = 60, plot_timeout: int = None):
        """
        Subscribe to real-time candle data with live plotting capability.
        
        Args:
            asset_name (str): Name of the asset to subscribe to (e.g., 'EURUSD')
            timeframe (int, optional): Candle timeframe in seconds. Defaults to 60.
                Common values: 60 (1min), 300 (5min), 900 (15min), 3600 (1hr)
        """
        
        # Subscribe to real-time candle data via WebSocket
        self.ws_manager.send_message('subscribeMessage', {
            'name': 'candle-generated',
            'params': {
                'routingFilters': {
                    'active_id': get_asset_id(asset_name),
                    'size': timeframe
                }
            }
        })

    def _convert_to_dataframe(self, candles_data: List[Dict]) -> pd.DataFrame:
        """Convert candle data to pandas DataFrame."""
        if not candles_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(candles_data)
        # df['datetime'] = pd.to_datetime(df['from'], unit='s')
        # df = df[['datetime', 'open', 'close', 'min', 'max', 'volume']]
        # df.rename(columns={'min': 'low', 'max': 'high'}, inplace=True)
        # # df.set_index('datetime', inplace=True)
        # df.to_csv('candles.csv')
        return df



    def stream_traders_mood(self, ASSET: str, timeout: float = 5.0):
        asset_id = get_asset_id(ASSET)
        name = "subscribeMessage"
        msg = {
            "name": "traders-mood-changed",
            "params":{"routingFilters":
                        {
                            "instrument":"turbo-option",
                            "asset_id":asset_id
                        }
                    }
        }
        
        self.ws_manager.send_message(name, msg)
        
        deadline = time.monotonic() + timeout
        # while time.monotonic() < deadline:
        while True:
            if asset_id in self.message_handler.traders_mood:
                return True, f"✅ Trader mood subscribed for {ASSET} (id={asset_id})"
            time.sleep(0.1)

        return False, f"Timeout after {timeout}s waiting for {ASSET} (id={asset_id})"
    
    def stop_traders_mood(self, ASSET: str, timeout: float = 5.0):
        asset_id = get_asset_id(ASSET)
        name = "unsubscribeMessage"
        msg = {
            "name": "traders-mood-changed",
            "params":{"routingFilters":
                        {
                            "instrument":"turbo-option",
                            "asset_id":asset_id
                        }
                    }
        }
        
        self.ws_manager.send_message(name, msg)