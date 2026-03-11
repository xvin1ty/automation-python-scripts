"""
Trend Following Strategy for Polymarket.

This strategy identifies and trades with market momentum:
1. Moving average crossovers
2. Price breakout detection
3. Volume confirmation
4. Momentum divergence

Key insight: Prediction markets often trend as new information is absorbed.
"""
from typing import List, Dict, Optional, Deque
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from loguru import logger
import numpy as np

from src.strategies.base import BaseStrategy, Signal, MarketData
from src.config import config


@dataclass
class PriceHistory:
    """Stores price history for trend analysis."""
    token_id: str
    max_length: int = 100
    prices: Deque[float] = None
    volumes: Deque[float] = None
    timestamps: Deque[datetime] = None
    
    def __post_init__(self):
        if self.prices is None:
            self.prices = deque(maxlen=self.max_length)
        if self.volumes is None:
            self.volumes = deque(maxlen=self.max_length)
        if self.timestamps is None:
            self.timestamps = deque(maxlen=self.max_length)
    
    def add(self, price: float, volume: float, timestamp: datetime):
        """Add new price point."""
        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
    
    def sma(self, period: int) -> Optional[float]:
        """Calculate simple moving average."""
        if len(self.prices) < period:
            return None
        return np.mean(list(self.prices)[-period:])
    
    def ema(self, period: int) -> Optional[float]:
        """Calculate exponential moving average."""
        if len(self.prices) < period:
            return None
        prices = list(self.prices)[-period:]
        alpha = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema
    
    def volatility(self, period: int = 20) -> Optional[float]:
        """Calculate price volatility (std dev)."""
        if len(self.prices) < period:
            return None
        return np.std(list(self.prices)[-period:])
    
    def momentum(self, period: int = 10) -> Optional[float]:
        """Calculate price momentum."""
        if len(self.prices) < period + 1:
            return None
        current = list(self.prices)[-1]
        past = list(self.prices)[-(period + 1)]
        return (current - past) / past if past != 0 else 0
    
    def rsi(self, period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index."""
        if len(self.prices) < period + 1:
            return None
        
        prices = list(self.prices)[-period-1:]
        deltas = np.diff(prices)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend following strategy using technical indicators.
    
    Strategy logic:
    1. Fast EMA crosses above Slow EMA -> BUY
    2. Fast EMA crosses below Slow EMA -> SELL
    3. RSI confirms (not overbought/oversold)
    4. Volume confirms trend
    """
    
    def __init__(self):
        super().__init__(
            name="TrendFollowing",
            config={
                "fast_period": 10,
                "slow_period": config.strategy.trend_lookback_period,
                "momentum_threshold": config.strategy.trend_threshold,
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "min_volume": 1000,
                "trend_confirmation_bars": 2
            }
        )
        self.price_history: Dict[str, PriceHistory] = {}
        self.last_signal: Dict[str, str] = {}  # Track last signal to avoid duplicates
        
    def get_required_data(self) -> List[str]:
        return ["mid_price", "volume_24h", "timestamp"]
    
    def analyze(self, market_data: List[MarketData]) -> List[Signal]:
        """Analyze markets for trend signals."""
        signals = []
        
        for data in market_data:
            # Skip low volume markets
            if data.volume_24h < self.config["min_volume"]:
                continue
            
            # Update price history
            signal = self._analyze_market(data)
            if signal:
                signals.append(signal)
        
        return signals
    
    def _analyze_market(self, data: MarketData) -> Optional[Signal]:
        """Analyze a single market for trend signals."""
        token_id = data.token_id
        
        # Get or create price history
        if token_id not in self.price_history:
            self.price_history[token_id] = PriceHistory(token_id=token_id)
        
        hist = self.price_history[token_id]
        hist.add(data.mid_price, data.volume_24h, data.timestamp)
        
        # Need enough data
        if len(hist.prices) < self.config["slow_period"] + 5:
            return None
        
        # Calculate indicators
        fast_ema = hist.ema(self.config["fast_period"])
        slow_ema = hist.ema(self.config["slow_period"])
        rsi = hist.rsi(self.config["rsi_period"])
        momentum = hist.momentum(10)
        volatility = hist.volatility(20)
        
        if fast_ema is None or slow_ema is None:
            return None
        
        # Determine trend
        trend = self._determine_trend(fast_ema, slow_ema, momentum, rsi)
        
        if not trend:
            return None
        
        # Check if signal changed
        last = self.last_signal.get(token_id)
        if last == trend:
            return None  # Avoid duplicate signals
        
        self.last_signal[token_id] = trend
        
        # Calculate position size based on volatility and confidence
        size = self._calculate_position_size(volatility, momentum)
        
        # Calculate confidence
        confidence = self._calculate_confidence(momentum, rsi, volatility)
        
        if trend == "BUY":
            return Signal(
                strategy_name=self.name,
                token_id=token_id,
                market_id=data.market_id,
                side="BUY",
                size=size,
                price=data.best_ask,  # Buy at ask
                confidence=confidence,
                reason=f"Trend UP: EMA{self.config['fast_period']}({fast_ema:.3f}) > "
                       f"EMA{self.config['slow_period']}({slow_ema:.3f}), "
                       f"Momentum: {momentum:.3f}, RSI: {rsi:.1f}"
            )
        elif trend == "SELL":
            return Signal(
                strategy_name=self.name,
                token_id=token_id,
                market_id=data.market_id,
                side="SELL",
                size=size,
                price=data.best_bid,  # Sell at bid
                confidence=confidence,
                reason=f"Trend DOWN: EMA{self.config['fast_period']}({fast_ema:.3f}) < "
                       f"EMA{self.config['slow_period']}({slow_ema:.3f}), "
                       f"Momentum: {momentum:.3f}, RSI: {rsi:.1f}"
            )
        
        return None
    
    def _determine_trend(self, fast_ema: float, slow_ema: float, 
                        momentum: Optional[float], rsi: Optional[float]) -> Optional[str]:
        """
        Determine trend direction based on indicators.
        
        Returns:
            "BUY", "SELL", or None
        """
        # EMA Crossover
        ema_bullish = fast_ema > slow_ema
        ema_bearish = fast_ema < slow_ema
        
        # Momentum confirmation
        momentum_bullish = momentum and momentum > self.config["momentum_threshold"]
        momentum_bearish = momentum and momentum < -self.config["momentum_threshold"]
        
        # RSI filter (avoid overbought/oversold)
        if rsi:
            if rsi > self.config["rsi_overbought"]:
                ema_bullish = False  # Overbought, don't buy
            if rsi < self.config["rsi_oversold"]:
                ema_bearish = False  # Oversold, don't sell
        
        # Generate signal
        if ema_bullish and momentum_bullish:
            return "BUY"
        elif ema_bearish and momentum_bearish:
            return "SELL"
        
        return None
    
    def _calculate_position_size(self, volatility: Optional[float], 
                                 momentum: Optional[float]) -> float:
        """
        Calculate position size based on volatility and momentum.
        
        Lower volatility = larger position
        Higher momentum = larger position
        """
        base_size = config.trading.max_position_size
        
        # Adjust for volatility
        if volatility:
            # Reduce size for high volatility
            vol_factor = max(0.2, 1.0 - volatility * 10)
            base_size *= vol_factor
        
        # Adjust for momentum strength
        if momentum:
            momentum_factor = min(1.5, 0.5 + abs(momentum) * 5)
            base_size *= momentum_factor
        
        # Ensure minimum and maximum
        return max(10, min(base_size, config.trading.max_position_size))
    
    def _calculate_confidence(self, momentum: Optional[float], 
                             rsi: Optional[float], volatility: Optional[float]) -> float:
        """Calculate signal confidence (0-1)."""
        confidence = 0.5
        
        # Momentum contribution
        if momentum:
            confidence += min(0.2, abs(momentum) * 0.5)
        
        # RSI contribution (neutral RSI = higher confidence)
        if rsi:
            rsi_neutral = abs(50 - rsi) / 50  # 0 when RSI=50, 1 when RSI=0 or 100
            confidence += (1 - rsi_neutral) * 0.2
        
        # Volatility penalty (high volatility = lower confidence)
        if volatility:
            confidence -= min(0.2, volatility)
        
        return max(0.1, min(0.95, confidence))
    
    def get_price_history(self, token_id: str) -> Optional[PriceHistory]:
        """Get price history for a token."""
        return self.price_history.get(token_id)
    
    def get_technical_summary(self, token_id: str) -> Optional[Dict]:
        """Get technical indicator summary for a token."""
        hist = self.price_history.get(token_id)
        if not hist or len(hist.prices) < 20:
            return None
        
        return {
            "sma_20": hist.sma(20),
            "ema_10": hist.ema(10),
            "ema_20": hist.ema(20),
            "rsi": hist.rsi(14),
            "momentum": hist.momentum(10),
            "volatility": hist.volatility(20),
            "data_points": len(hist.prices)
        }


class BreakoutStrategy(BaseStrategy):
    """
    Breakout strategy that trades price breakouts from ranges.
    
    Identifies consolidation periods and trades when price breaks out.
    """
    
    def __init__(self):
        super().__init__(
            name="Breakout",
            config={
                "lookback_period": 20,
                "breakout_threshold": 0.02,  # 2% breakout
                "volume_multiplier": 1.5,  # Volume must be 1.5x average
                "min_consolidation_periods": 5
            }
        )
        self.price_history: Dict[str, PriceHistory] = {}
        self.consolidation_ranges: Dict[str, Tuple[float, float]] = {}
        
    def get_required_data(self) -> List[str]:
        return ["mid_price", "high", "low", "volume"]
    
    def analyze(self, market_data: List[MarketData]) -> List[Signal]:
        """Look for breakout opportunities."""
        signals = []
        
        for data in market_data:
            signal = self._check_breakout(data)
            if signal:
                signals.append(signal)
        
        return signals
    
    def _check_breakout(self, data: MarketData) -> Optional[Signal]:
        """Check if price is breaking out of consolidation."""
        token_id = data.token_id
        
        if token_id not in self.price_history:
            self.price_history[token_id] = PriceHistory(token_id=token_id)
        
        hist = self.price_history[token_id]
        hist.add(data.mid_price, data.volume_24h, data.timestamp)
        
        if len(hist.prices) < self.config["lookback_period"]:
            return None
        
        prices = list(hist.prices)[-self.config["lookback_period"]:]
        
        # Calculate consolidation range
        high = max(prices)
        low = min(prices)
        range_size = high - low
        
        # Check if in consolidation (range is tight)
        avg_price = sum(prices) / len(prices)
        consolidation_pct = range_size / avg_price if avg_price > 0 else 1
        
        is_consolidating = consolidation_pct < 0.05  # Less than 5% range
        
        if is_consolidating:
            # Store consolidation range
            self.consolidation_ranges[token_id] = (low, high)
            return None
        
        # Check for breakout
        if token_id in self.consolidation_ranges:
            low_range, high_range = self.consolidation_ranges[token_id]
            current_price = data.mid_price
            
            # Breakout above
            if current_price > high_range * (1 + self.config["breakout_threshold"]):
                return Signal(
                    strategy_name=self.name,
                    token_id=token_id,
                    market_id=data.market_id,
                    side="BUY",
                    size=config.trading.max_position_size,
                    price=data.best_ask,
                    confidence=0.7,
                    reason=f"Breakout above {high_range:.3f} (current: {current_price:.3f})"
                )
            
            # Breakdown below
            elif current_price < low_range * (1 - self.config["breakout_threshold"]):
                return Signal(
                    strategy_name=self.name,
                    token_id=token_id,
                    market_id=data.market_id,
                    side="SELL",
                    size=config.trading.max_position_size,
                    price=data.best_bid,
                    confidence=0.7,
                    reason=f"Breakdown below {low_range:.3f} (current: {current_price:.3f})"
                )
        
        return None
