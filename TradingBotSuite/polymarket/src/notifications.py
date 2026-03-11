"""
Notification module for Telegram and Discord alerts.
"""
import requests
from typing import Optional
from loguru import logger

from src.config import config


class NotificationManager:
    """Sends notifications to Telegram and Discord."""
    
    def __init__(self):
        self.telegram_token = config.notification.telegram_bot_token
        self.telegram_chat_id = config.notification.telegram_chat_id
        self.discord_webhook = config.notification.discord_webhook_url
        
        self.telegram_enabled = bool(self.telegram_token and self.telegram_chat_id)
        self.discord_enabled = bool(self.discord_webhook)
        
        if self.telegram_enabled:
            logger.info(f"Telegram notifications enabled for chat {self.telegram_chat_id}")
        if self.discord_enabled:
            logger.info("Discord notifications enabled")
    
    def send_telegram(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram."""
        if not self.telegram_enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def send_discord(self, message: str) -> bool:
        """Send message to Discord webhook."""
        if not self.discord_enabled:
            return False
        
        try:
            payload = {"content": message}
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False
    
    def notify(self, message: str, level: str = "info"):
        """Send notification to all enabled channels."""
        # Add emoji based on level
        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "trade": "💰",
            "profit": "📈",
            "loss": "📉"
        }
        emoji = emoji_map.get(level, "ℹ️")
        
        formatted_msg = f"{emoji} {message}"
        
        # Send to Telegram with HTML formatting
        if self.telegram_enabled:
            telegram_msg = message.replace("**", "<b>").replace("**", "</b>")
            self.send_telegram(telegram_msg)
        
        # Send to Discord
        if self.discord_enabled:
            self.send_discord(formatted_msg)
        
        # Also log it
        logger.info(f"Notification: {message}")
    
    # Convenience methods
    def notify_trade(self, side: str, size: float, token: str, price: float, pnl: float = 0):
        """Notify about a trade."""
        emoji = "🟢" if side == "BUY" else "🔴"
        pnl_str = f" | PnL: ${pnl:+.2f}" if pnl != 0 else ""
        
        msg = f"""
<b>{emoji} TRADE EXECUTED</b>

Side: {side}
Size: ${size:.2f}
Token: {token}
Price: ${price:.4f}{pnl_str}

Time: {datetime.now().strftime('%H:%M:%S')}
        """.strip()
        
        self.notify(msg, "trade")
    
    def notify_signal(self, strategy: str, side: str, confidence: float, reason: str):
        """Notify about a trading signal."""
        msg = f"""
<b>📊 SIGNAL: {strategy}</b>

Side: {side}
Confidence: {confidence:.1%}
Reason: {reason}
        """.strip()
        
        self.notify(msg, "info")
    
    def notify_daily_summary(self, pnl: float, trades: int, win_rate: float):
        """Send daily P&L summary."""
        emoji = "📈" if pnl > 0 else "📉" if pnl < 0 else "➖"
        
        msg = f"""
<b>{emoji} DAILY SUMMARY</b>

PnL: ${pnl:+.2f}
Trades: {trades}
Win Rate: {win_rate:.1f}%

Keep it up! 💪
        """.strip()
        
        self.notify(msg, "success" if pnl > 0 else "warning")
    
    def notify_error(self, error_msg: str):
        """Notify about an error."""
        self.notify(f"<b>❌ ERROR</b>\n\n{error_msg}", "error")
    
    def notify_startup(self, mode: str, capital: float):
        """Notify when bot starts."""
        msg = f"""
<b>🚀 BOT STARTED</b>

Mode: {mode}
Capital: ${capital:.2f}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Good luck! 🍀
        """.strip()
        
        self.notify(msg, "success")


from datetime import datetime

# Global instance
notifications = NotificationManager()
