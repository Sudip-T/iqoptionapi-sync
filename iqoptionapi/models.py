from enum import Enum
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any

class InstrumentType(Enum):
    """Trading instrument types supported by IQOption API."""
    FOREX = 'forex'
    CFD = 'cfd'
    CRYPTO = 'crypto'
    DIGITAL_OPTION = 'digital-option'
    BINARY_OPTION = 'binary'
    BLITZ_OPTION = 'blitz'
    TURBO_OPTION = 'turbo'
    
class OptionType(Enum):
    DIGITAL_OPTION = "digital-option"
    BINARY_OPTION = "binary-option"
    TURBO_OPTION = "turbo-option"

class Direction(Enum):
    PUT = "put"
    CALL = "call"
    INDECISION = 'none'

@dataclass
class OptionsTradeParams:
    """Trade parameters with validation"""
    asset: str
    expiry: int
    amount: float
    direction: Direction
    option_type: OptionType
    
    def __post_init__(self):
        if self.amount < 1:
            raise ValueError("Amount must be positive")
        if self.expiry < 1:
            raise ValueError("Expiry must be positive")
        

class TradeResult(Enum):
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"


@dataclass
class TradeOutcome:
    """Data class representing a standardized trade outcome"""
    trade_id: Any
    asset: str
    invest_amount: float
    pl_amount: float
    is_win: bool
    is_loss: bool
    is_breakeven: bool
    open_price: Optional[float]
    close_price: Optional[float]
    open_time: Optional[datetime]
    close_time: Optional[datetime]
    direction: str
    currency: str
    option_type: OptionType

    @property
    def result(self) -> TradeResult:
        """Get the trade result as an enum"""
        if self.is_win:
            return TradeResult.WIN
        elif self.is_loss:
            return TradeResult.LOSS
        else:
            return TradeResult.BREAKEVEN
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'trade_id': self.trade_id,
            'asset': self.asset,
            'invest_amount': self.invest_amount,
            'pl_amount': self.pl_amount,
            'is_win': self.is_win,
            'is_loss': self.is_loss,
            'is_breakeven': self.is_breakeven,
            'result': self.result.value,
            'open_price': self.open_price,
            'close_price': self.close_price,
            'open_time': self.open_time,
            'close_time': self.close_time,
            'direction': self.direction,
            'currency': self.currency,
            'option_type': self.option_type.value,
        }
    

class TradeOutcomeChecker:
    """
    A class to process and analyze trade outcomes from websocket messages
    for both Digital Options and Binary Options
    """
    
    def __init__(self):
        self.processed_trades = []

    def check_trade_outcome(self, trade_message: Dict[str, Any]) -> TradeOutcome:
        """
        Process trade message and return standardized outcome
        
        Args:
            trade_message (dict): The websocket message containing trade data
            
        Returns:
            TradeOutcome: Standardized trade outcome object
            
        Raises:
            ValueError: If the trade message format is unknown
        """
        
        trade_type = self._identify_trade_type(trade_message)
        if trade_type == OptionType.BINARY_OPTION:
            outcome = self._process_binary_option_outcome(trade_message)
        elif trade_type == OptionType.DIGITAL_OPTION:
            outcome = self._process_digital_option_outcome(trade_message)

        # Store the processed trade
        self.processed_trades.append(outcome)

        return outcome

    def _identify_trade_type(self, trade_message: Dict[str, Any]) -> Optional[OptionType]:
        """Identify the trade type from the message structure"""
        if (trade_message.get('instrument_type') == 'digital-option' and 
            'pnl' in trade_message):
            return OptionType.DIGITAL_OPTION
        elif ('win' in trade_message and 'type_name' in trade_message):
            return OptionType.BINARY_OPTION
        else:
            return None
        
    def _process_binary_option_outcome(self, trade_message: Dict[str, Any]) -> TradeOutcome:
        """Process binary options trade message"""
        invest_amount = float(trade_message.get('sum', 0))
        pl_amount = float(trade_message.get('profit_amount', 0)) - invest_amount

        return TradeOutcome(
            trade_id=trade_message.get('id'),
            asset=trade_message.get('active'),
            invest_amount=invest_amount,
            pl_amount=pl_amount,
            is_win=pl_amount > 0,
            is_loss=pl_amount < 0,
            is_breakeven=(pl_amount  == invest_amount),
            open_price=float(trade_message.get('value', 0)),
            close_price=float(trade_message.get('exp_value', 0)),
            direction=trade_message.get('dir', 'unknown'),
            currency=trade_message.get('currency', 'USD'),
            option_type=OptionType.BINARY_OPTION,
            open_time=self._timestamp_to_datetime(trade_message.get('created'), is_seconds=True),
            close_time=self._timestamp_to_datetime(trade_message.get('expired'), is_seconds=True),
        )
    

    def _process_digital_option_outcome(self, trade_message: Dict[str, Any]) -> TradeOutcome:
        """Process binary options trade message"""
        invest_amount = float(trade_message.get('invest', 0))
        pl_amount = float(trade_message.get('pnl_realized', 0))

        raw_event = trade_message.get('raw_event', {})

        return TradeOutcome(
            trade_id=raw_event["order_ids"][0],
            asset=raw_event.get('instrument_underlying', 'unknown'),
            invest_amount=invest_amount,
            pl_amount=pl_amount,
            is_win=pl_amount > 0,
            is_loss=pl_amount < 0,
            is_breakeven=pl_amount == float(0),
            open_price=float(trade_message.get('open_quote', 0)),
            close_price=float(trade_message.get('close_quote', 0)),
            open_time=self._timestamp_to_datetime(trade_message.get('open_time')),
            close_time=self._timestamp_to_datetime(trade_message.get('close_time')),
            direction=raw_event.get('instrument_dir', 'unknown'),
            option_type=OptionType.DIGITAL_OPTION,
            currency=raw_event.get('currency', 'USD'),
        )

    def _timestamp_to_datetime(self, timestamp: Optional[Any], is_seconds: bool = False) -> Optional[datetime]:
        """Convert timestamp to datetime object"""
        if timestamp is None:
            return None
        
        try:
            timestamp = float(timestamp)
            if is_seconds:
                return datetime.fromtimestamp(timestamp)
            else:
                # Assume milliseconds
                return datetime.fromtimestamp(timestamp / 1000)
        except (ValueError, TypeError):
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for all processed trades
        
        Returns:
            dict: Trading statistics
        """
        if not self.processed_trades:
            return {"message": "No trades processed yet"}
        
        total_trades = len(self.processed_trades)
        wins = sum(1 for trade in self.processed_trades if trade.is_win)
        losses = sum(1 for trade in self.processed_trades if trade.is_loss)
        breakevens = sum(1 for trade in self.processed_trades if trade.is_breakeven)
        
        total_invested = sum(trade.invest_amount for trade in self.processed_trades)
        total_pnl = sum(trade.pnl for trade in self.processed_trades)
        
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        
        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "breakevens": breakevens,
            "win_rate": f"{win_rate:.2f}%",
            "total_invested": total_invested,
            "total_pnl": total_pnl,
            "roi": f"{(total_pnl / total_invested * 100):+.2f}%" if total_invested > 0 else "0.00%"
        }
    
    def get_trades_by_type(self, trade_type: OptionType) -> list[TradeOutcome]:
        """Get all trades of a specific type"""
        return [trade for trade in self.processed_trades if trade.trade_type == trade_type]
    
    def get_winning_trades(self) -> list[TradeOutcome]:
        """Get all winning trades"""
        return [trade for trade in self.processed_trades if trade.is_win]
    
    def get_losing_trades(self) -> list[TradeOutcome]:
        """Get all losing trades"""
        return [trade for trade in self.processed_trades if trade.is_loss]
    
    def clear_history(self):
        """Clear all processed trades from history"""
        self.processed_trades.clear()