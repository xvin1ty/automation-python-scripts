"""
Risk Management Module for Polymarket Trading Bot.

Manages:
- Position sizing
- Stop losses
- Portfolio limits
- Exposure tracking
- Drawdown protection
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from src.config import config


@dataclass
class Position:
    """Represents an open position."""
    token_id: str
    market_id: str
    side: str  # "LONG" or "SHORT"
    size: float
    entry_price: float
    timestamp: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    
    def update_pnl(self, current_price: float):
        """Update unrealized PnL."""
        if self.side == "LONG":
            self.unrealized_pnl = self.size * (current_price - self.entry_price)
        else:
            self.unrealized_pnl = self.size * (self.entry_price - current_price)
    
    @property
    def value(self) -> float:
        """Current position value."""
        return self.size * self.entry_price


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_position_size: float = field(default_factory=lambda: config.trading.max_position_size)
    max_total_exposure: float = field(default_factory=lambda: config.trading.total_capital * 2)
    max_positions: int = field(default_factory=lambda: config.trading.max_open_positions)
    max_drawdown_pct: float = 20.0  # Max 20% drawdown
    daily_loss_limit: float = field(default_factory=lambda: config.trading.total_capital * 0.05)
    risk_per_trade: float = field(default_factory=lambda: config.trading.risk_per_trade)


class RiskManager:
    """
    Manages trading risk and enforces limits.
    
    Key responsibilities:
    1. Position sizing based on risk parameters
    2. Stop loss / take profit management
    3. Portfolio exposure limits
    4. Drawdown protection
    5. Daily loss limits
    """
    
    def __init__(self):
        self.limits = RiskLimits()
        self.positions: Dict[str, Position] = {}  # token_id -> Position
        self.daily_stats = {
            "date": datetime.now().date(),
            "trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "total_volume": 0.0
        }
        self.peak_capital = config.trading.total_capital
        self.current_drawdown = 0.0
        self.trading_enabled = True
        
    def can_open_position(self, token_id: str, size: float, 
                         price: float) -> tuple[bool, str]:
        """
        Check if a new position can be opened.
        
        Returns:
            (can_trade, reason)
        """
        if not self.trading_enabled:
            return False, "Trading disabled due to risk limits"
        
        # Check max positions
        if len(self.positions) >= self.limits.max_positions:
            return False, f"Max positions ({self.limits.max_positions}) reached"
        
        # Check if already have position in this token
        if token_id in self.positions:
            return False, "Already have position in this market"
        
        # Check position size
        if size > self.limits.max_position_size:
            return False, f"Position size {size} exceeds max {self.limits.max_position_size}"
        
        # Check total exposure
        total_exposure = sum(p.value for p in self.positions.values())
        new_exposure = size * price
        if total_exposure + new_exposure > self.limits.max_total_exposure:
            return False, "Max total exposure would be exceeded"
        
        # Check daily loss limit
        if self.daily_stats["total_pnl"] < -self.limits.daily_loss_limit:
            return False, "Daily loss limit reached"
        
        return True, "OK"
    
    def calculate_position_size(self, confidence: float, 
                               volatility: Optional[float] = None) -> float:
        """
        Calculate appropriate position size based on risk parameters.
        
        Args:
            confidence: Signal confidence (0-1)
            volatility: Market volatility (optional)
            
        Returns:
            Position size in USDC
        """
        # Base size from risk per trade
        base_size = (config.trading.total_capital * self.limits.risk_per_trade) / 100
        
        # Adjust for confidence
        size = base_size * confidence
        
        # Adjust for volatility (reduce size in volatile markets)
        if volatility:
            vol_factor = max(0.3, 1.0 - volatility * 5)
            size *= vol_factor
        
        # Ensure within limits
        size = min(size, self.limits.max_position_size)
        size = max(10, size)  # Minimum $10 position
        
        return size
    
    def add_position(self, token_id: str, market_id: str, side: str, 
                    size: float, entry_price: float,
                    stop_loss: Optional[float] = None,
                    take_profit: Optional[float] = None) -> Position:
        """Add a new position."""
        position = Position(
            token_id=token_id,
            market_id=market_id,
            side="LONG" if side == "BUY" else "SHORT",
            size=size,
            entry_price=entry_price,
            timestamp=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        self.positions[token_id] = position
        self.daily_stats["trades"] += 1
        self.daily_stats["total_volume"] += size * entry_price
        
        logger.info(f"Position opened: {token_id} {side} {size} @ {entry_price}")
        
        return position
    
    def close_position(self, token_id: str, exit_price: float) -> Optional[float]:
        """Close a position and calculate realized PnL."""
        if token_id not in self.positions:
            return None
        
        position = self.positions[token_id]
        
        # Calculate realized PnL
        if position.side == "LONG":
            realized_pnl = position.size * (exit_price - position.entry_price)
        else:
            realized_pnl = position.size * (position.entry_price - exit_price)
        
        # Update daily stats
        self.daily_stats["total_pnl"] += realized_pnl
        if realized_pnl > 0:
            self.daily_stats["winning_trades"] += 1
        else:
            self.daily_stats["losing_trades"] += 1
        
        # Remove position
        del self.positions[token_id]
        
        logger.info(f"Position closed: {token_id} PnL: ${realized_pnl:.2f}")
        
        return realized_pnl
    
    def update_positions(self, prices: Dict[str, float]):
        """Update all positions with current prices."""
        total_unrealized = 0.0
        
        for token_id, position in self.positions.items():
            if token_id in prices:
                position.update_pnl(prices[token_id])
                total_unrealized += position.unrealized_pnl
                
                # Check stop loss
                if position.stop_loss:
                    if position.side == "LONG" and prices[token_id] <= position.stop_loss:
                        logger.warning(f"Stop loss hit for {token_id}")
                    elif position.side == "SHORT" and prices[token_id] >= position.stop_loss:
                        logger.warning(f"Stop loss hit for {token_id}")
        
        # Update drawdown
        current_capital = config.trading.total_capital + total_unrealized + self.daily_stats["total_pnl"]
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital
        
        self.current_drawdown = ((self.peak_capital - current_capital) / self.peak_capital) * 100
        
        # Check drawdown limit
        if self.current_drawdown > self.limits.max_drawdown_pct:
            logger.error(f"Max drawdown reached: {self.current_drawdown:.2f}%")
            self.trading_enabled = False
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all positions."""
        total_value = sum(p.value for p in self.positions.values())
        total_unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        
        return {
            "open_positions": len(self.positions),
            "total_value": total_value,
            "total_unrealized_pnl": total_unrealized,
            "current_drawdown_pct": self.current_drawdown,
            "trading_enabled": self.trading_enabled,
            "positions": [
                {
                    "token_id": p.token_id,
                    "side": p.side,
                    "size": p.size,
                    "entry_price": p.entry_price,
                    "unrealized_pnl": p.unrealized_pnl
                }
                for p in self.positions.values()
            ]
        }
    
    def reset_daily_stats(self):
        """Reset daily statistics (call at midnight)."""
        today = datetime.now().date()
        if today != self.daily_stats["date"]:
            logger.info(f"Daily stats reset. Yesterday PnL: ${self.daily_stats['total_pnl']:.2f}")
            self.daily_stats = {
                "date": today,
                "trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                "total_volume": 0.0
            }
    
    def get_daily_stats(self) -> Dict:
        """Get daily trading statistics."""
        win_rate = 0
        if self.daily_stats["trades"] > 0:
            win_rate = (self.daily_stats["winning_trades"] / self.daily_stats["trades"]) * 100
        
        return {
            **self.daily_stats,
            "win_rate": win_rate,
            "avg_trade_size": (self.daily_stats["total_volume"] / max(1, self.daily_stats["trades"]))
        }
