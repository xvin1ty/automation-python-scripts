"""
Arbitrage Strategy for Polymarket.

This strategy identifies and exploits price discrepancies between:
1. Related markets (YES/NO mispricing within same event)
2. Cross-market arbitrage (same event, different markets)
3. Liquidity arbitrage (spread capture)

Key insight: In prediction markets, YES + NO should sum to $1 (minus fees).
When they don't, there's an arbitrage opportunity.
"""
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass
from loguru import logger

from src.strategies.base import BaseStrategy, Signal, MarketData
from src.config import config


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity."""
    market_id: str
    yes_token: str
    no_token: str
    yes_price: float
    no_price: float
    sum_price: float
    expected_profit: float
    profit_pct: float
    trade_size: float
    arb_type: str  # "intra_market", "cross_market", "spread"


class ArbitrageStrategy(BaseStrategy):
    """
    Arbitrage strategy that finds mispriced markets.
    
    Strategy logic:
    1. For binary markets, YES + NO should = $1.00
    2. If YES + NO < $1.00, buy both and hold until resolution
    3. If YES + NO > $1.00, sell both (short if possible)
    4. Capture bid-ask spreads in liquid markets
    """
    
    def __init__(self):
        super().__init__(
            name="Arbitrage",
            config={
                "min_spread": config.strategy.min_arbitrage_spread,
                "max_hold_time": config.strategy.max_arbitrage_hold_time,
                "min_liquidity": 1000,
                "max_position_size": config.trading.max_position_size
            }
        )
        self.opportunities_found = 0
        self.arbitrages_executed = 0
        
    def get_required_data(self) -> List[str]:
        return ["best_bid", "best_ask", "mid_price", "liquidity", "volume"]
    
    def analyze(self, market_data: List[MarketData]) -> List[Signal]:
        """Analyze markets for arbitrage opportunities."""
        signals = []
        
        # Group by market to find YES/NO pairs
        market_groups = self._group_by_market(market_data)
        
        for market_id, tokens in market_groups.items():
            if len(tokens) >= 2:
                # Find arbitrage within this market
                arb = self._find_intra_market_arbitrage(market_id, tokens)
                if arb and arb.profit_pct >= self.config["min_spread"]:
                    signal = self._create_arbitrage_signal(arb)
                    if signal:
                        signals.append(signal)
                        self.opportunities_found += 1
                        
        return signals
    
    def _group_by_market(self, market_data: List[MarketData]) -> Dict[str, List[MarketData]]:
        """Group tokens by their parent market."""
        groups = defaultdict(list)
        for data in market_data:
            groups[data.market_id].append(data)
        return groups
    
    def _find_intra_market_arbitrage(self, market_id: str, 
                                     tokens: List[MarketData]) -> Optional[ArbitrageOpportunity]:
        """
        Find arbitrage opportunity within a binary market.
        
        For binary markets:
        - Buy YES at ask price
        - Buy NO at ask price  
        - If YES_ask + NO_ask < 1.00, profit = 1.00 - (YES_ask + NO_ask)
        """
        if len(tokens) < 2:
            return None
        
        # Find YES and NO tokens (by question text or outcome type)
        yes_token = None
        no_token = None
        
        for token in tokens:
            question_lower = token.question.lower()
            if "yes" in question_lower or token.extra.get("outcome") == "Yes":
                yes_token = token
            elif "no" in question_lower or token.extra.get("outcome") == "No":
                no_token = token
        
        if not yes_token or not no_token:
            return None
        
        # Calculate sum of asks (cost to buy both sides)
        yes_ask = yes_token.best_ask
        no_ask = no_token.best_ask
        sum_ask = yes_ask + no_ask
        
        # Arbitrage exists if sum < 1.00
        if sum_ask >= 1.0:
            return None
        
        # Calculate expected profit
        expected_profit = 1.0 - sum_ask
        profit_pct = expected_profit / sum_ask if sum_ask > 0 else 0
        
        # Check minimum liquidity
        min_liquidity = min(yes_token.liquidity, no_token.liquidity)
        if min_liquidity < self.config["min_liquidity"]:
            return None
        
        # Calculate optimal trade size
        trade_size = min(
            self.config["max_position_size"],
            min_liquidity * 0.1  # Use 10% of available liquidity
        )
        
        return ArbitrageOpportunity(
            market_id=market_id,
            yes_token=yes_token.token_id,
            no_token=no_token.token_id,
            yes_price=yes_ask,
            no_price=no_ask,
            sum_price=sum_ask,
            expected_profit=expected_profit * trade_size,
            profit_pct=profit_pct,
            trade_size=trade_size,
            arb_type="intra_market"
        )
    
    def _create_arbitrage_signal(self, arb: ArbitrageOpportunity) -> Optional[Signal]:
        """Create a trading signal from arbitrage opportunity."""
        # For intra-market arbitrage, we buy both YES and NO
        # This is a two-legged trade
        
        confidence = min(0.95, 0.5 + arb.profit_pct * 10)  # Higher profit = higher confidence
        
        # Create signal for YES side
        signal = Signal(
            strategy_name=self.name,
            token_id=arb.yes_token,
            market_id=arb.market_id,
            side="BUY",
            size=arb.trade_size,
            price=arb.yes_price,
            confidence=confidence,
            reason=f"Intra-market arbitrage: YES+NO={arb.sum_price:.4f}, "
                   f"Expected profit: {arb.profit_pct*100:.2f}%"
        )
        
        logger.info(f"Arbitrage opportunity found: {signal.reason}")
        
        return signal
    
    def find_spread_arbitrage(self, market_data: MarketData) -> Optional[Signal]:
        """
        Find spread arbitrage opportunities.
        Buy at bid, sell at ask if spread is wide enough.
        """
        spread_pct = market_data.spread_pct
        
        if spread_pct < self.config["min_spread"] * 100:
            return None
        
        # Only trade liquid markets
        if market_data.liquidity < self.config["min_liquidity"]:
            return None
        
        confidence = min(0.8, spread_pct / 100)
        
        return Signal(
            strategy_name=self.name,
            token_id=market_data.token_id,
            market_id=market_data.market_id,
            side="BUY",
            size=min(self.config["max_position_size"], market_data.liquidity * 0.05),
            price=market_data.best_bid,
            confidence=confidence,
            reason=f"Spread arbitrage: {spread_pct:.2f}% spread"
        )


class CrossMarketArbitrage(BaseStrategy):
    """
    Cross-market arbitrage strategy.
    
    Finds the same event priced differently across multiple markets
    or across Polymarket and other prediction markets.
    """
    
    def __init__(self):
        super().__init__(
            name="CrossMarketArbitrage",
            config={"min_price_diff": 0.05}
        )
        
    def get_required_data(self) -> List[str]:
        return ["mid_price", "volume", "question"]
    
    def analyze(self, market_data: List[MarketData]) -> List[Signal]:
        """Find arbitrage across related markets."""
        signals = []
        
        # Group by similar questions (simplified matching)
        question_groups = defaultdict(list)
        for data in market_data:
            # Normalize question for grouping
            normalized = self._normalize_question(data.question)
            question_groups[normalized].append(data)
        
        for question, markets in question_groups.items():
            if len(markets) >= 2:
                arb_signals = self._find_cross_market_arb(markets)
                signals.extend(arb_signals)
        
        return signals
    
    def _normalize_question(self, question: str) -> str:
        """Normalize question text for grouping."""
        # Remove common words, lowercase, etc.
        words = question.lower().split()
        # Keep only significant words (longer than 3 chars)
        significant = [w for w in words if len(w) > 3]
        return " ".join(sorted(significant[:5]))  # First 5 significant words
    
    def _find_cross_market_arb(self, markets: List[MarketData]) -> List[Signal]:
        """Find price differences between similar markets."""
        signals = []
        
        # Sort by price
        markets_sorted = sorted(markets, key=lambda x: x.mid_price)
        
        cheapest = markets_sorted[0]
        expensive = markets_sorted[-1]
        
        price_diff = expensive.mid_price - cheapest.mid_price
        
        if price_diff >= self.config["min_price_diff"]:
            # Buy cheap, sell expensive
            signal = Signal(
                strategy_name=self.name,
                token_id=cheapest.token_id,
                market_id=cheapest.market_id,
                side="BUY",
                size=config.trading.max_position_size,
                price=cheapest.best_ask,
                confidence=0.7,
                reason=f"Cross-market arb: {price_diff:.2f} price difference"
            )
            signals.append(signal)
        
        return signals
