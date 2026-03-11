"""
Market Making Strategy for Polymarket.

This strategy provides liquidity by placing bid and ask orders around the mid price.
Profit comes from:
1. Capturing the bid-ask spread
2. Maker rebates (if available)
3. Skewing quotes based on inventory

Risk management is crucial as adverse selection can lead to losses.
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from loguru import logger

from src.strategies.base import BaseStrategy, Signal, MarketData
from src.config import config


@dataclass
class InventoryState:
    """Tracks inventory for a market."""
    token_id: str
    position: float = 0.0
    avg_price: float = 0.0
    open_orders: List[Dict] = None
    
    def __post_init__(self):
        if self.open_orders is None:
            self.open_orders = []
    
    @property
    def unrealized_pnl(self, current_price: float = 0.5) -> float:
        if self.position == 0:
            return 0.0
        return self.position * (current_price - self.avg_price)


class MarketMakingStrategy(BaseStrategy):
    """
    Market making strategy with inventory skew.
    
    Key features:
    1. Places bid/ask orders around mid price
    2. Adjusts quotes based on inventory (skew)
    3. Manages position limits
    4. Cancels stale orders
    """
    
    def __init__(self):
        super().__init__(
            name="MarketMaking",
            config={
                "spread_bps": config.strategy.mm_spread_basis_points,  # Basis points
                "order_size": config.strategy.mm_order_size,
                "max_inventory": config.trading.max_position_size * 2,
                "inventory_skew_factor": 0.5,  # How much to skew quotes
                "order_refresh_time": 60,  # Seconds
                "min_spread_bps": 10,
                "max_spread_bps": 200
            }
        )
        self.inventory: Dict[str, InventoryState] = {}
        self.last_orders: Dict[str, datetime] = {}
        
    def get_required_data(self) -> List[str]:
        return ["mid_price", "spread", "liquidity", "volume"]
    
    def analyze(self, market_data: List[MarketData]) -> List[Signal]:
        """Generate market making signals."""
        signals = []
        
        for data in market_data:
            # Skip illiquid markets
            if data.liquidity < 5000:
                continue
            
            # Skip wide spread markets
            if data.spread_pct > 5:  # More than 5% spread
                continue
            
            mm_signals = self._generate_mm_signals(data)
            signals.extend(mm_signals)
            
        return signals
    
    def _generate_mm_signals(self, data: MarketData) -> List[Signal]:
        """Generate market making orders for a single market."""
        signals = []
        token_id = data.token_id
        
        # Get or create inventory state
        if token_id not in self.inventory:
            self.inventory[token_id] = InventoryState(token_id=token_id)
        
        inv = self.inventory[token_id]
        
        # Calculate skew based on inventory
        skew = self._calculate_skew(inv)
        
        # Calculate optimal spread
        spread = self._calculate_spread(data)
        
        # Calculate bid and ask prices with skew
        mid = data.mid_price
        half_spread = spread / 2
        
        bid_price = mid - half_spread * (1 + skew)
        ask_price = mid + half_spread * (1 - skew)
        
        # Ensure prices are valid (0.01 to 0.99)
        bid_price = max(0.01, min(0.99, bid_price))
        ask_price = max(0.01, min(0.99, ask_price))
        
        # Check if we need to refresh orders
        should_refresh = self._should_refresh_orders(token_id)
        
        if should_refresh:
            # Generate buy signal (bid)
            if inv.position < self.config["max_inventory"]:
                buy_signal = Signal(
                    strategy_name=self.name,
                    token_id=token_id,
                    market_id=data.market_id,
                    side="BUY",
                    size=self.config["order_size"],
                    price=round(bid_price, 3),
                    confidence=0.6,
                    reason=f"MM Bid @ {bid_price:.3f} (skew: {skew:.2f})"
                )
                signals.append(buy_signal)
            
            # Generate sell signal (ask)
            if inv.position > -self.config["max_inventory"]:
                sell_signal = Signal(
                    strategy_name=self.name,
                    token_id=token_id,
                    market_id=data.market_id,
                    side="SELL",
                    size=self.config["order_size"],
                    price=round(ask_price, 3),
                    confidence=0.6,
                    reason=f"MM Ask @ {ask_price:.3f} (skew: {skew:.2f})"
                )
                signals.append(sell_signal)
            
            self.last_orders[token_id] = datetime.now()
        
        return signals
    
    def _calculate_skew(self, inv: InventoryState) -> float:
        """
        Calculate price skew based on inventory.
        
        Positive inventory (long) -> negative skew (lower bids)
        Negative inventory (short) -> positive skew (higher asks)
        """
        max_inv = self.config["max_inventory"]
        if max_inv == 0:
            return 0.0
        
        # Normalize inventory to [-1, 1]
        normalized = inv.position / max_inv
        
        # Apply skew factor
        skew = -normalized * self.config["inventory_skew_factor"]
        
        return skew
    
    def _calculate_spread(self, data: MarketData) -> float:
        """
        Calculate optimal spread based on market conditions.
        
        Wider spreads for:
        - High volatility
        - Low liquidity
        - High inventory
        """
        base_spread_bps = self.config["spread_bps"]
        
        # Adjust for market spread
        market_spread_bps = data.spread_pct * 100
        
        # Use wider of base or market spread
        spread_bps = max(base_spread_bps, market_spread_bps * 1.5)
        
        # Adjust for liquidity (wider for low liquidity)
        if data.liquidity < 10000:
            spread_bps *= 1.5
        
        # Clamp to min/max
        spread_bps = max(self.config["min_spread_bps"], 
                        min(self.config["max_spread_bps"], spread_bps))
        
        # Convert to price (0-1 range)
        spread = spread_bps / 10000
        
        return spread
    
    def _should_refresh_orders(self, token_id: str) -> bool:
        """Check if orders should be refreshed."""
        if token_id not in self.last_orders:
            return True
        
        elapsed = (datetime.now() - self.last_orders[token_id]).total_seconds()
        return elapsed >= self.config["order_refresh_time"]
    
    def update_inventory(self, token_id: str, fill_size: float, fill_price: float, side: str):
        """Update inventory after a fill."""
        if token_id not in self.inventory:
            self.inventory[token_id] = InventoryState(token_id=token_id)
        
        inv = self.inventory[token_id]
        
        # Update position
        if side == "BUY":
            # Calculate new average price
            total_cost = inv.position * inv.avg_price + fill_size * fill_price
            inv.position += fill_size
            if inv.position > 0:
                inv.avg_price = total_cost / inv.position
        else:  # SELL
            inv.position -= fill_size
            # Keep avg_price the same for shorts
        
        logger.info(f"Inventory updated: {token_id} position={inv.position:.2f} "
                   f"avg_price={inv.avg_price:.3f}")
    
    def get_inventory_summary(self) -> Dict:
        """Get summary of all inventory."""
        total_position = sum(inv.position for inv in self.inventory.values())
        total_exposure = sum(abs(inv.position) for inv in self.inventory.values())
        
        return {
            "total_position": total_position,
            "total_exposure": total_exposure,
            "markets_traded": len(self.inventory),
            "inventory_details": {
                token_id: {
                    "position": inv.position,
                    "avg_price": inv.avg_price
                }
                for token_id, inv in self.inventory.items()
            }
        }
