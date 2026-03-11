"""
Configuration management for the Polymarket trading bot.
"""
import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class WalletConfig:
    """Wallet configuration."""
    private_key: str = field(default_factory=lambda: os.getenv("POLYGON_PRIVATE_KEY", ""))
    address: str = field(default_factory=lambda: os.getenv("WALLET_ADDRESS", ""))
    signature_type: int = field(default_factory=lambda: int(os.getenv("SIGNATURE_TYPE", "0")))
    
    
@dataclass
class APIConfig:
    """API configuration."""
    clob_host: str = field(default_factory=lambda: os.getenv("CLOB_HOST", "https://clob.polymarket.com"))
    gamma_api_url: str = field(default_factory=lambda: os.getenv("GAMMA_API_URL", "https://gamma-api.polymarket.com"))
    chain_id: int = field(default_factory=lambda: int(os.getenv("CHAIN_ID", "137")))
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("API_KEY"))
    api_secret: Optional[str] = field(default_factory=lambda: os.getenv("API_SECRET"))
    api_passphrase: Optional[str] = field(default_factory=lambda: os.getenv("API_PASSPHRASE"))
    request_timeout: int = field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT", "30")))


@dataclass
class TradingConfig:
    """Trading configuration."""
    mode: str = field(default_factory=lambda: os.getenv("TRADING_MODE", "PAPER"))
    max_position_size: float = field(default_factory=lambda: float(os.getenv("MAX_POSITION_SIZE", "100")))
    total_capital: float = field(default_factory=lambda: float(os.getenv("TOTAL_CAPITAL", "1000")))
    risk_per_trade: float = field(default_factory=lambda: float(os.getenv("RISK_PER_TRADE", "2")))
    max_open_positions: int = field(default_factory=lambda: int(os.getenv("MAX_OPEN_POSITIONS", "5")))
    default_slippage: float = field(default_factory=lambda: float(os.getenv("DEFAULT_SLIPPAGE", "0.5")))


@dataclass
class StrategyConfig:
    """Strategy configuration."""
    enable_arbitrage: bool = field(default_factory=lambda: os.getenv("ENABLE_ARBITRAGE", "true").lower() == "true")
    enable_market_making: bool = field(default_factory=lambda: os.getenv("ENABLE_MARKET_MAKING", "false").lower() == "true")
    enable_trend_following: bool = field(default_factory=lambda: os.getenv("ENABLE_TREND_FOLLOWING", "true").lower() == "true")
    enable_news_trading: bool = field(default_factory=lambda: os.getenv("ENABLE_NEWS_TRADING", "false").lower() == "true")
    
    # Arbitrage settings
    min_arbitrage_spread: float = field(default_factory=lambda: float(os.getenv("MIN_ARBITRAGE_SPREAD", "0.02")))
    max_arbitrage_hold_time: int = field(default_factory=lambda: int(os.getenv("MAX_ARBITRAGE_HOLD_TIME", "3600")))
    
    # Market making settings
    mm_spread_basis_points: int = field(default_factory=lambda: int(os.getenv("MM_SPREAD_BASIS_POINTS", "50")))
    mm_order_size: float = field(default_factory=lambda: float(os.getenv("MM_ORDER_SIZE", "50")))
    
    # Trend following settings
    trend_lookback_period: int = field(default_factory=lambda: int(os.getenv("TREND_LOOKBACK_PERIOD", "20")))
    trend_threshold: float = field(default_factory=lambda: float(os.getenv("TREND_THRESHOLD", "0.05")))


@dataclass
class NotificationConfig:
    """Notification configuration."""
    telegram_bot_token: Optional[str] = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN"))
    telegram_chat_id: Optional[str] = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID"))
    discord_webhook_url: Optional[str] = field(default_factory=lambda: os.getenv("DISCORD_WEBHOOK_URL"))


@dataclass
class DatabaseConfig:
    """Database configuration."""
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///data/trading_bot.db"))


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    to_file: bool = field(default_factory=lambda: os.getenv("LOG_TO_FILE", "true").lower() == "true")
    file_path: str = field(default_factory=lambda: os.getenv("LOG_FILE_PATH", "logs/bot.log"))


class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.wallet = WalletConfig()
        self.api = APIConfig()
        self.trading = TradingConfig()
        self.strategy = StrategyConfig()
        self.notification = NotificationConfig()
        self.database = DatabaseConfig()
        self.logging = LoggingConfig()
        
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate wallet
        if not self.wallet.private_key or self.wallet.private_key == "0x":
            errors.append("POLYGON_PRIVATE_KEY is required")
        if not self.wallet.address:
            errors.append("WALLET_ADDRESS is required")
            
        # Validate trading config
        if self.trading.mode not in ["PAPER", "LIVE"]:
            errors.append("TRADING_MODE must be PAPER or LIVE")
        if self.trading.total_capital <= 0:
            errors.append("TOTAL_CAPITAL must be positive")
        if self.trading.risk_per_trade <= 0 or self.trading.risk_per_trade > 100:
            errors.append("RISK_PER_TRADE must be between 0 and 100")
            
        return errors
    
    def is_paper_trading(self) -> bool:
        """Check if in paper trading mode."""
        return self.trading.mode.upper() == "PAPER"
    
    def is_live_trading(self) -> bool:
        """Check if in live trading mode."""
        return self.trading.mode.upper() == "LIVE"


# Global config instance
config = Config()
