"""
Database module for tracking trades, signals, and performance.
"""
import json
import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from loguru import logger

from src.config import config


@dataclass
class Trade:
    """Represents a completed trade."""
    id: Optional[int]
    timestamp: datetime
    token_id: str
    market_id: str
    strategy: str
    side: str
    size: float
    price: float
    pnl: float
    fees: float
    status: str


@dataclass
class SignalRecord:
    """Represents a generated signal."""
    id: Optional[int]
    timestamp: datetime
    strategy: str
    token_id: str
    market_id: str
    side: str
    size: float
    price: float
    confidence: float
    reason: str
    executed: bool


class Database:
    """SQLite database for bot data."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.database.database_url.replace("sqlite:///", "")
        self._ensure_directory()
        self._init_tables()
    
    def _ensure_directory(self):
        """Ensure database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _init_tables(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    token_id TEXT NOT NULL,
                    market_id TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    side TEXT NOT NULL,
                    size REAL NOT NULL,
                    price REAL NOT NULL,
                    pnl REAL DEFAULT 0,
                    fees REAL DEFAULT 0,
                    status TEXT DEFAULT 'open'
                )
            """)
            
            # Signals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    token_id TEXT NOT NULL,
                    market_id TEXT NOT NULL,
                    side TEXT NOT NULL,
                    size REAL NOT NULL,
                    price REAL,
                    confidence REAL,
                    reason TEXT,
                    executed INTEGER DEFAULT 0
                )
            """)
            
            # Market data cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    token_id TEXT NOT NULL,
                    market_id TEXT NOT NULL,
                    best_bid REAL,
                    best_ask REAL,
                    mid_price REAL,
                    volume REAL,
                    liquidity REAL,
                    data TEXT
                )
            """)
            
            # Performance metrics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    total_pnl REAL DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    volume REAL DEFAULT 0
                )
            """)
            
            conn.commit()
    
    def save_trade(self, trade: Trade):
        """Save a trade to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades 
                (timestamp, token_id, market_id, strategy, side, size, price, pnl, fees, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.timestamp.isoformat(),
                trade.token_id,
                trade.market_id,
                trade.strategy,
                trade.side,
                trade.size,
                trade.price,
                trade.pnl,
                trade.fees,
                trade.status
            ))
            conn.commit()
    
    def save_signal(self, signal: SignalRecord):
        """Save a signal to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO signals 
                (timestamp, strategy, token_id, market_id, side, size, price, confidence, reason, executed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.timestamp.isoformat(),
                signal.strategy,
                signal.token_id,
                signal.market_id,
                signal.side,
                signal.size,
                signal.price,
                signal.confidence,
                signal.reason,
                1 if signal.executed else 0
            ))
            conn.commit()
    
    def get_trades(self, limit: int = 100) -> List[Trade]:
        """Get recent trades."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, token_id, market_id, strategy, side, size, price, pnl, fees, status
                FROM trades
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [
                Trade(
                    id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    token_id=row[2],
                    market_id=row[3],
                    strategy=row[4],
                    side=row[5],
                    size=row[6],
                    price=row[7],
                    pnl=row[8],
                    fees=row[9],
                    status=row[10]
                )
                for row in rows
            ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get trading performance summary."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(pnl) as total_pnl,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades
                FROM trades
            """)
            
            row = cursor.fetchone()
            total_trades = row[0] or 0
            winning = row[2] or 0
            
            return {
                "total_trades": total_trades,
                "total_pnl": row[1] or 0,
                "winning_trades": winning,
                "losing_trades": row[3] or 0,
                "win_rate": (winning / total_trades * 100) if total_trades > 0 else 0,
                "total_volume": 0
            }
    
    def update_daily_performance(self, date: str, pnl: float, trades: int, 
                                  wins: int, losses: int, volume: float):
        """Update daily performance metrics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO performance (date, total_pnl, total_trades, winning_trades, losing_trades, volume)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_pnl = total_pnl + excluded.total_pnl,
                    total_trades = total_trades + excluded.total_trades,
                    winning_trades = winning_trades + excluded.winning_trades,
                    losing_trades = losing_trades + excluded.losing_trades,
                    volume = volume + excluded.volume
            """, (date, pnl, trades, wins, losses, volume))
            conn.commit()


# Global database instance
db = Database()
