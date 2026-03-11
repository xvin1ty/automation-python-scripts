"""
Polymarket API Client Wrapper
Handles authentication, market data, and order execution.
"""
import json
import time
from typing import Optional, Dict, List, Any, Tuple
from decimal import Decimal
import requests
from loguru import logger

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, MarketOrderArgs, OrderType, BookParams
    from py_clob_client.order_builder.constants import BUY, SELL
    PY_CLOB_AVAILABLE = True
except ImportError:
    PY_CLOB_AVAILABLE = False
    logger.warning("py-clob-client not installed. Using mock client.")

from src.config import config


class PolymarketClient:
    """
    Polymarket API Client for trading on prediction markets.
    Wraps the official py-clob-client with additional functionality.
    """
    
    def __init__(self):
        self.clob_client: Optional[Any] = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PolymarketBot/1.0',
            'Accept': 'application/json',
        })
        self._api_cache: Dict[str, Tuple[Any, float]] = {}
        self.cache_ttl = 5  # Cache TTL in seconds
        
    def connect(self) -> bool:
        """
        Connect to Polymarket API with credentials.
        Returns True if successful.
        """
        try:
            if not PY_CLOB_AVAILABLE:
                logger.warning("Running in mock mode - no real trades will be executed")
                return True
                
            if config.is_paper_trading():
                # Read-only client for paper trading
                self.clob_client = ClobClient(config.api.clob_host)
                logger.info("Connected to Polymarket (PAPER TRADING MODE)")
                return True
            
            # Live trading client with authentication
            self.clob_client = ClobClient(
                host=config.api.clob_host,
                key=config.wallet.private_key,
                chain_id=config.api.chain_id,
                signature_type=config.wallet.signature_type,
                funder=config.wallet.address
            )
            
            # Generate API credentials
            api_creds = self.clob_client.create_or_derive_api_creds()
            self.clob_client.set_api_creds(api_creds)
            
            logger.info("Connected to Polymarket (LIVE TRADING MODE)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Polymarket: {e}")
            return False
    
    def get_markets(self, limit: int = 100, active: bool = True, 
                   tag: Optional[str] = None) -> List[Dict]:
        """
        Fetch markets from Polymarket.
        
        Args:
            limit: Maximum number of markets to fetch
            active: Only fetch active markets
            tag: Filter by tag (e.g., 'Politics', 'Crypto', 'Sports')
            
        Returns:
            List of market dictionaries
        """
        cache_key = f"markets_{limit}_{active}_{tag}"
        
        # Check cache
        if cache_key in self._api_cache:
            data, timestamp = self._api_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return data
        
        try:
            url = f"{config.api.gamma_api_url}/markets"
            params = {
                "limit": limit,
                "active": active,
                "closed": "false" if active else "true",
                "order": "volume",
                "ascending": "false"
            }
            if tag:
                params["tag_slug"] = tag.lower()
                
            response = self.session.get(url, params=params, timeout=config.api.request_timeout)
            response.raise_for_status()
            
            data = response.json()
            markets = data.get("markets", [])
            
            # Cache the result
            self._api_cache[cache_key] = (markets, time.time())
            
            return markets
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    def get_market(self, market_id: str) -> Optional[Dict]:
        """Get detailed information about a specific market."""
        try:
            url = f"{config.api.gamma_api_url}/markets/{market_id}"
            response = self.session.get(url, timeout=config.api.request_timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching market {market_id}: {e}")
            return None
    
    def get_events(self, limit: int = 50) -> List[Dict]:
        """Fetch events from Polymarket."""
        try:
            url = f"{config.api.gamma_api_url}/events"
            params = {
                "limit": limit,
                "active": "true",
                "order": "volume",
                "ascending": "false"
            }
            response = self.session.get(url, params=params, timeout=config.api.request_timeout)
            response.raise_for_status()
            return response.json().get("events", [])
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []
    
    def get_order_book(self, token_id: str) -> Optional[Dict]:
        """
        Get order book for a specific token.
        
        Args:
            token_id: The token ID (from market data)
            
        Returns:
            Order book dictionary with bids and asks
        """
        if self.clob_client and PY_CLOB_AVAILABLE:
            try:
                return self.clob_client.get_order_book(token_id)
            except Exception as e:
                logger.error(f"Error fetching order book: {e}")
                return None
        else:
            # Mock order book for testing
            return {
                "bids": [{"price": 0.48, "size": 100}, {"price": 0.47, "size": 200}],
                "asks": [{"price": 0.52, "size": 100}, {"price": 0.53, "size": 200}],
                "token_id": token_id
            }
    
    def get_price(self, token_id: str, side: str = "BUY") -> Optional[float]:
        """
        Get current price for a token.
        
        Args:
            token_id: The token ID
            side: "BUY" or "SELL"
            
        Returns:
            Price as float, or None if error
        """
        if self.clob_client and PY_CLOB_AVAILABLE:
            try:
                price_data = self.clob_client.get_price(token_id, side)
                return float(price_data.get("price", 0))
            except Exception as e:
                logger.error(f"Error fetching price: {e}")
                return None
        else:
            # Mock price
            return 0.50
    
    def get_midpoint(self, token_id: str) -> Optional[float]:
        """Get midpoint price for a token."""
        if self.clob_client and PY_CLOB_AVAILABLE:
            try:
                midpoint_data = self.clob_client.get_midpoint(token_id)
                return float(midpoint_data.get("mid", 0))
            except Exception as e:
                logger.error(f"Error fetching midpoint: {e}")
                return None
        else:
            return 0.50
    
    def get_spread(self, token_id: str) -> Optional[Dict]:
        """Get bid-ask spread for a token."""
        if self.clob_client and PY_CLOB_AVAILABLE:
            try:
                return self.clob_client.get_spread(token_id)
            except Exception as e:
                logger.error(f"Error fetching spread: {e}")
                return None
        else:
            return {"bid": 0.48, "ask": 0.52}
    
    def get_balances(self) -> Dict[str, float]:
        """Get wallet balances."""
        if self.clob_client and PY_CLOB_AVAILABLE and not config.is_paper_trading():
            try:
                return self.clob_client.get_balances()
            except Exception as e:
                logger.error(f"Error fetching balances: {e}")
                return {"USDC": 0.0, "available": 0.0}
        else:
            # Mock balances for paper trading
            return {
                "USDC": config.trading.total_capital,
                "available": config.trading.total_capital,
                "locked": 0.0
            }
    
    def place_limit_order(self, token_id: str, side: str, price: float, 
                         size: float, order_type: str = "GTC") -> Optional[Dict]:
        """
        Place a limit order.
        
        Args:
            token_id: Token to trade
            side: "BUY" or "SELL"
            price: Limit price (0-1)
            size: Order size
            order_type: "GTC", "GTD", "FOK", "FAK"
            
        Returns:
            Order response dictionary
        """
        if config.is_paper_trading():
            logger.info(f"[PAPER TRADE] Limit {side} {size} @ {price}")
            return {
                "orderID": f"paper_{int(time.time())}",
                "status": "live",
                "token_id": token_id,
                "side": side,
                "price": price,
                "size": size
            }
        
        if not self.clob_client or not PY_CLOB_AVAILABLE:
            logger.error("Cannot place order - client not connected")
            return None
        
        try:
            # Map side string to constant
            side_const = BUY if side.upper() == "BUY" else SELL
            
            # Map order type string
            order_type_map = {
                "GTC": OrderType.GTC,
                "GTD": OrderType.GTD,
                "FOK": OrderType.FOK,
                "FAK": OrderType.FAK
            }
            order_type_enum = order_type_map.get(order_type.upper(), OrderType.GTC)
            
            # Create order
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=side_const
            )
            
            # Sign and post order
            signed_order = self.clob_client.create_order(order_args)
            response = self.clob_client.post_order(signed_order, order_type_enum)
            
            logger.info(f"Order placed: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def place_market_order(self, token_id: str, side: str, 
                          amount: float) -> Optional[Dict]:
        """
        Place a market order (buy by dollar amount).
        
        Args:
            token_id: Token to trade
            side: "BUY" or "SELL"
            amount: Dollar amount to spend (for BUY) or shares to sell (for SELL)
            
        Returns:
            Order response dictionary
        """
        if config.is_paper_trading():
            logger.info(f"[PAPER TRADE] Market {side} ${amount}")
            return {
                "orderID": f"paper_market_{int(time.time())}",
                "status": "matched",
                "token_id": token_id,
                "side": side,
                "amount": amount
            }
        
        if not self.clob_client or not PY_CLOB_AVAILABLE:
            logger.error("Cannot place order - client not connected")
            return None
        
        try:
            side_const = BUY if side.upper() == "BUY" else SELL
            
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=side_const
            )
            
            signed_order = self.clob_client.create_market_order(order_args)
            response = self.clob_client.post_order(signed_order, OrderType.FOK)
            
            logger.info(f"Market order placed: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        if config.is_paper_trading():
            logger.info(f"[PAPER TRADE] Cancel order {order_id}")
            return True
        
        if not self.clob_client or not PY_CLOB_AVAILABLE:
            return False
        
        try:
            self.clob_client.cancel(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    def cancel_all_orders(self) -> bool:
        """Cancel all open orders."""
        if config.is_paper_trading():
            logger.info("[PAPER TRADE] Cancel all orders")
            return True
        
        if not self.clob_client or not PY_CLOB_AVAILABLE:
            return False
        
        try:
            self.clob_client.cancel_all()
            logger.info("All orders cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return False
    
    def get_open_orders(self) -> List[Dict]:
        """Get list of open orders."""
        if config.is_paper_trading():
            return []
        
        if not self.clob_client or not PY_CLOB_AVAILABLE:
            return []
        
        try:
            return self.clob_client.get_orders()
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []
    
    def get_positions(self) -> List[Dict]:
        """Get current positions."""
        if config.is_paper_trading():
            return []
        
        if not self.clob_client or not PY_CLOB_AVAILABLE:
            return []
        
        try:
            return self.clob_client.get_positions()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    def get_trades(self) -> List[Dict]:
        """Get trade history."""
        if config.is_paper_trading():
            return []
        
        if not self.clob_client or not PY_CLOB_AVAILABLE:
            return []
        
        try:
            return self.clob_client.get_trades()
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []


# Global client instance
client = PolymarketClient()
