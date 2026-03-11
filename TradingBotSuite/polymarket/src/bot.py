"""
Main Trading Bot Engine for Polymarket.

Coordinates all components:
- Market data fetching
- Strategy execution
- Risk management
- Order execution
- Performance tracking
"""
import time
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from src.config import config
from src.polymarket_client import client
from src.strategies.base import StrategyManager, MarketData
from src.strategies.arbitrage import ArbitrageStrategy
from src.strategies.market_making import MarketMakingStrategy
from src.strategies.trend_following import TrendFollowingStrategy
from src.risk_manager import RiskManager
from src.database import db, Trade, SignalRecord


class PolymarketBot:
    """
    Main trading bot that orchestrates all components.
    """
    
    def __init__(self):
        self.running = False
        self.strategy_manager = StrategyManager()
        self.risk_manager = RiskManager()
        self.update_interval = config.strategy.get("price_update_interval", 5)
        
        # Initialize strategies
        self._init_strategies()
        
    def _init_strategies(self):
        """Initialize trading strategies based on config."""
        if config.strategy.enable_arbitrage:
            self.strategy_manager.register(ArbitrageStrategy())
            
        if config.strategy.enable_market_making:
            self.strategy_manager.register(MarketMakingStrategy())
            
        if config.strategy.enable_trend_following:
            self.strategy_manager.register(TrendFollowingStrategy())
            
        logger.info(f"Initialized {len(self.strategy_manager.get_all_strategies())} strategies")
    
    def connect(self) -> bool:
        """Connect to Polymarket API."""
        logger.info("Connecting to Polymarket...")
        
        if not client.connect():
            logger.error("Failed to connect to Polymarket")
            return False
        
        # Check balance
        balances = client.get_balances()
        logger.info(f"USDC Balance: ${balances.get('USDC', 0):.2f}")
        logger.info(f"Available: ${balances.get('available', 0):.2f}")
        
        return True
    
    def fetch_market_data(self) -> List[MarketData]:
        """Fetch and normalize market data."""
        markets = client.get_markets(limit=50, active=True)
        
        market_data = []
        for market in markets:
            try:
                # Get token IDs
                tokens = market.get("tokens", [])
                if not tokens:
                    continue
                
                for token in tokens:
                    token_id = token.get("token_id")
                    if not token_id:
                        continue
                    
                    # Get prices
                    best_bid = float(market.get("bestBid", 0) or 0)
                    best_ask = float(market.get("bestAsk", 1) or 1)
                    mid_price = (best_bid + best_ask) / 2 if best_bid > 0 and best_ask > 0 else 0.5
                    
                    data = MarketData(
                        token_id=token_id,
                        market_id=market.get("id", ""),
                        question=market.get("question", ""),
                        best_bid=best_bid,
                        best_ask=best_ask,
                        mid_price=mid_price,
                        volume_24h=float(market.get("volume", 0) or 0),
                        liquidity=float(market.get("liquidity", 0) or 0),
                        timestamp=datetime.now(),
                        extra={
                            "outcome": token.get("outcome", ""),
                            "slug": market.get("slug", ""),
                            "category": market.get("category", "")
                        }
                    )
                    market_data.append(data)
                    
            except Exception as e:
                logger.error(f"Error processing market: {e}")
                continue
        
        return market_data
    
    def process_signals(self, signals: List):
        """Process trading signals and execute orders."""
        for signal in signals:
            # Check risk limits
            can_trade, reason = self.risk_manager.can_open_position(
                signal.token_id, signal.size, signal.price
            )
            
            if not can_trade:
                logger.warning(f"Signal rejected: {reason}")
                continue
            
            # Save signal to database
            db.save_signal(SignalRecord(
                id=None,
                timestamp=signal.timestamp,
                strategy=signal.strategy_name,
                token_id=signal.token_id,
                market_id=signal.market_id,
                side=signal.side,
                size=signal.size,
                price=signal.price,
                confidence=signal.confidence,
                reason=signal.reason,
                executed=False
            ))
            
            # Execute order
            self._execute_signal(signal)
    
    def _execute_signal(self, signal):
        """Execute a trading signal."""
        try:
            logger.info(f"Executing signal: {signal.strategy_name} {signal.side} "
                       f"{signal.size} {signal.token_id} @ {signal.price}")
            
            if signal.price:
                # Limit order
                result = client.place_limit_order(
                    token_id=signal.token_id,
                    side=signal.side,
                    price=signal.price,
                    size=signal.size
                )
            else:
                # Market order
                result = client.place_market_order(
                    token_id=signal.token_id,
                    side=signal.side,
                    amount=signal.size
                )
            
            if result:
                logger.success(f"Order executed: {result.get('orderID', 'unknown')}")
                
                # Add to risk manager
                self.risk_manager.add_position(
                    token_id=signal.token_id,
                    market_id=signal.market_id,
                    side=signal.side,
                    size=signal.size,
                    entry_price=signal.price or result.get("price", 0)
                )
                
                # Save trade
                db.save_trade(Trade(
                    id=None,
                    timestamp=datetime.now(),
                    token_id=signal.token_id,
                    market_id=signal.market_id,
                    strategy=signal.strategy_name,
                    side=signal.side,
                    size=signal.size,
                    price=signal.price or result.get("price", 0),
                    pnl=0,
                    fees=0,
                    status="open"
                ))
                
            else:
                logger.error("Order execution failed")
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    def run_once(self):
        """Run one iteration of the trading loop."""
        try:
            # Reset daily stats if needed
            self.risk_manager.reset_daily_stats()
            
            # Fetch market data
            market_data = self.fetch_market_data()
            logger.info(f"Fetched {len(market_data)} markets")
            
            # Get current prices for position updates
            prices = {m.token_id: m.mid_price for m in market_data}
            self.risk_manager.update_positions(prices)
            
            # Run strategies
            signals = self.strategy_manager.analyze_all(market_data)
            logger.info(f"Generated {len(signals)} signals")
            
            # Process signals
            if signals:
                self.process_signals(signals)
            
            # Log status
            self._log_status()
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
    
    def _log_status(self):
        """Log current bot status."""
        stats = self.risk_manager.get_position_summary()
        daily_stats = self.risk_manager.get_daily_stats()
        
        logger.info(f"Status: {stats['open_positions']} positions, "
                   f"Unrealized: ${stats['total_unrealized_pnl']:.2f}, "
                   f"Drawdown: {stats['current_drawdown_pct']:.2f}%, "
                   f"Daily PnL: ${daily_stats['total_pnl']:.2f}")
    
    def run(self):
        """Run the bot continuously."""
        logger.info("Starting Polymarket Trading Bot...")
        
        if not self.connect():
            return
        
        self.running = True
        
        try:
            while self.running:
                self.run_once()
                
                # Sleep until next update
                logger.info(f"Sleeping for {self.update_interval} seconds...")
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            self.stop()
        except Exception as e:
            logger.error(f"Bot error: {e}")
            self.stop()
    
    def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping bot...")
        self.running = False
        
        # Cancel all orders
        client.cancel_all_orders()
        
        # Log final stats
        stats = self.risk_manager.get_position_summary()
        logger.info(f"Final PnL: ${stats['total_unrealized_pnl']:.2f}")
        
    def get_status(self) -> Dict:
        """Get bot status."""
        return {
            "running": self.running,
            "strategies": self.strategy_manager.get_stats(),
            "risk": self.risk_manager.get_position_summary(),
            "daily": self.risk_manager.get_daily_stats()
        }


# Global bot instance
bot = PolymarketBot()
