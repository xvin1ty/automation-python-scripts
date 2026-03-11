# 📱 Telegram Alerts Setup

## Why Use Telegram?

Get instant notifications on your phone when:
- ✅ Trade executed
- ✅ Profit target reached
- ⚠️ Stop loss triggered
- 📊 Daily summary
- 🚨 Emergency alerts

## Step-by-Step Setup

### 1. Create Your Bot (2 minutes)

1. Open Telegram on your phone
2. Search for **@BotFather**
3. Start a chat
4. Type: `/newbot`
5. Name it: `My Trading Bot`
6. Username: `my_trading_bot` (must end in 'bot')
7. **COPY THE TOKEN** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID (1 minute)

1. Search for your bot by its username
2. Start a chat, send any message (like "hi")
3. Open this URL in browser:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
4. Look for: `"chat":{"id":123456789`
5. **Your Chat ID = 123456789** (your number will be different)

### 3. Configure the Bot

Edit the `.env` file in the polymarket folder:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### 4. Test It

Run: `python3 RUN_BOT.py`
Select option 5: Test Telegram

You should get a message on your phone!

## Example Alerts

### Trade Executed
```
💰 TRADE EXECUTED
Side: BUY
Size: $100
Token: Will Bitcoin hit $100k?
Price: $0.65
Time: 14:32:15
```

### Profit Alert
```
🟢 PROFIT TARGET REACHED
Daily P&L: +$127.50
Win Rate: 75%
Trades: 8
Great job! 📈
```

### Stop Loss
```
🔴 STOP LOSS TRIGGERED
Loss: -$50.00
Position closed automatically
Reason: Hit daily loss limit
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No message received | Check token is correct |
| Bot not found | Search by username, not name |
| Wrong chat ID | Make sure you messaged the bot first |
| "Forbidden" error | Blocked bot, unblock and try again |

