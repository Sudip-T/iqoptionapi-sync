import time
import logging
from typing import Optional
from datetime import datetime, timedelta
from cba_iqapi.instruments.options_assests import UNDERLYING_ASSESTS

logger = logging.getLogger(__name__)


def get_timestamps(start_str: str = None, end_str: str = None) -> tuple:
    """   
    This function creates a time range by converting datetime strings to Unix timestamps.
    If no parameters are provided, it defaults to a 24-hour range ending at the current time.
    
    Returns:
        tuple: A tuple containing (start_timestamp, end_timestamp) as integers,
               or (None, None) if an error occurs during parsing.
    
    Example:
        >>> get_timestamps("2024-01-01 00:00:00", "2024-01-01 12:00:00")
        (1704067200, 1704110400)
        
        >>> get_timestamps()  # Returns last 24 hours from now
        (1693756800, 1693843200)
    """
        
    try:
        # If no end date provided, use current time
        if end_str is None:
            end_dt = datetime.now()
        else:
            end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")

        # If no start date provided, default to 24 hours before end time
        if start_str is None:
            start_dt = end_dt - timedelta(hours=24)
        else:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")

        # Convert datetime objects to Unix timestamps (seconds since epoch)
        return int(start_dt.timestamp()), int(end_dt.timestamp())
    except Exception as e:
        logger.error(str(e))
        logger.error('Plase make sure date is within valid range')
        return None, None


def get_expiry_timestamp(timestamp:int, expiry:int=1):
    """
    Calculate expiration timestamp based on a given timestamp and expiry duration.
    
    Args:
        timestamp (int): Input timestamp in milliseconds since epoch.
        expiry (int, optional): Expiry duration in minutes. Defaults to 1.
    
    Returns:
        float: Expiration timestamp in seconds since epoch.
    
    Note:
        - The function ensures a minimum of 31 seconds between the current time
          and expiration to prevent immediate expiry.
        - Input timestamp is expected in milliseconds but output is in seconds.
    
    Example:
        >>> get_expiry_timestamp(1693843200000, 5)  # 5-minute expiry
        1693843500.0
    """

    # Minimum time needed before expiration (in seconds)
    min_time_needed = 31

    # Convert timestamp from milliseconds to seconds
    timestamp = timestamp / 1000

    # Create datetime object from timestamp
    now_date = datetime.fromtimestamp(timestamp)

    # Round down to nearest minute (remove seconds and microseconds)
    # This ensures consistent expiration times on minute boundaries
    now_date_hm = now_date.replace(second=0, microsecond=0)

    # Calculate expiration based on conditions
    if expiry == 1:
        if (now_date_hm + timedelta(minutes=1)).timestamp() - timestamp >= min_time_needed:
            expiration = now_date_hm + timedelta(minutes=1)
        else:
            expiration = now_date_hm + timedelta(minutes=2)
    else:
        time_until_expiry = (now_date_hm + timedelta(minutes=1)).timestamp() - timestamp

        expiration = now_date_hm + timedelta(minutes=expiry)
        
        if time_until_expiry < min_time_needed:
            expiration = now_date_hm + timedelta(minutes=expiry+1)

    # Return expiration time as timestamp in seconds
    return expiration.timestamp()


def get_remaining_secs(timestamp, duration):
    """
    Calculate the remaining seconds until expiration for a given duration.
    
    Args:
        timestamp (int): Current timestamp in milliseconds since epoch.
        duration (int): Duration in minutes until expiration.
    
    Example:
        >>> get_remaining_secs(1693843200000, 5) # 5 minutes
        300.0 or 304.0 as seconds
    
    Note:
        This function relies on get_expiry_timestamp() to calculate the actual
        expiration timestamp, which includes logic for minimum time requirements.
    """

    # Get the expiration timestamp
    expiry_ts = get_expiry_timestamp(timestamp, duration)

    # Calculate remaining seconds by subtracting current time from expiration time
    return expiry_ts - int(timestamp/1000)


def generate_request_id(request_id: Optional[str] = None) -> str:
    """
    Generate a unique request ID for API calls.
    
    Args:
        request_id: Optional pre-existing request ID. If None, a new one will be generated.
        
    Returns:
        str: The request ID to use for the API call.
        
    Example:
        >>> generate_request_id()
        '456123'  # Random microseconds-based ID
        >>> generate_request_id("custom_id")
        'custom_id'
    """
    # If request_id is provided, return it unchanged
    if request_id is not None:
        return request_id
    
    # Generate unique ID from current timestamp microseconds
    microsecond_part = str(time.time()).split('.')[1]
    
    return microsecond_part


def get_asset_id(asset_name: str) -> int:
    if asset_name in UNDERLYING_ASSESTS:
        return UNDERLYING_ASSESTS[asset_name]
    raise KeyError(f"Asset '{asset_name}' not found in underlying assets")