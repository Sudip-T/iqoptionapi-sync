import logging
from enum import Enum
from threading import Lock
from typing import Optional, Tuple
from dataclasses import dataclass, field
logger = logging.getLogger("api:appstate")


class AccountType(Enum):
    """Valid account types"""
    REAL = "real"
    DEMO = "demo"
    
    @classmethod
    def is_valid(cls, account_type: str) -> bool:
        """Check if account type is valid"""
        return account_type.lower() in [e.value for e in cls]
    
    @classmethod
    def get_valid_types(cls) -> list:
        """Get list of valid account types"""
        return [e.value for e in cls]


@dataclass
class _AppState:
    """Single source of truth. Access via module-level `state` singleton."""

    # Connection
    websocket_is_connected: bool = False
    ssl_mutex_read:         bool = False
    ssl_mutex_write:        bool = False
    check_ws_error:         bool = False
    ws_error_reason:        Optional[str] = None

    # Auth
    ssid:  Optional[str] = None
    is_demo: Optional[bool] = None

    profile_msg = None

    # Account
    balance_id:      Optional[int]   = None
    balance:         Optional[float] = None
    balance_type:    Optional[int]   = None
    balance_type_str:    Optional[str]   = None
    balance_updated: bool            = False
    account_list = {}
    balance_data = None

    # Trade results
    result:      Optional[bool] = None
    order_data:  dict           = field(default_factory=dict)
    order_open:  list           = field(default_factory=list)
    order_closed: list          = field(default_factory=list)
    closed_deals: list          = field(default_factory=list)

    # Market data
    pairs:       dict           = field(default_factory=dict)
    payout_data: Optional[str]  = None

    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    def update(self, **kwargs) -> None:
        """Thread-safe bulk update."""
        with self._lock:
            for k, v in kwargs.items():
                if not hasattr(self, k):
                    raise AttributeError(f"Unknown state key: {k!r}")
                setattr(self, k, v)

    def validate_account_type(self, account_type: str, exit_on_error: bool = True):
        """
        Validate account type with state tracking.
        
        Args:
            account_type: Account type to validate ('real' or 'demo')
            exit_on_error: Whether to exit on validation error
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        with self._lock:
            # Check if account type is valid
            if not AccountType.is_valid(account_type):
                error_msg = f"Invalid Account Type: '{account_type}'. Must be one of {AccountType.get_valid_types()}"
                logger.error(error_msg)
                self.account_validation_error = error_msg
                self.account_type_validated = False
                
                if exit_on_error:
                    import sys
                    sys.exit()
                
            self.balance_type_str = account_type
            self.balance_type     = 1 if account_type == 'real' else 4


appstate = _AppState()