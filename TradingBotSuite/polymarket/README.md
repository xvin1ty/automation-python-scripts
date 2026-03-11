# Polymarket Trading Bot

A professional, production-ready algorithmic trading bot for Polymarket prediction markets.

## Features

### Trading Strategies
- **Arbitrage Strategy**: Exploits YES/NO price mismatches (should sum to $1.00)
- **Market Making**: Provides liquidity with inventory-skewed quotes
- **Trend Following**: EMA crossover with RSI confirmation
- **Breakout Detection**: Identifies price consolidation and breakouts

### Risk Management
- Position sizing based on volatility and confidence
- Portfolio exposure limits
- Drawdown protection (auto-stop at max drawdown)
- Daily loss limits
- Stop-loss and take-profit management

### Data & Analytics
- SQLite database for trade tracking
- Real-time and historical market data
- Performance metrics and reporting
- Paper trading mode for testing

## Installation

```bash
# Clone repository
cd polymarket-bot

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

## Configuration

Edit `.env` file:

```env
# Wallet Configuration
POLYGON_PRIVATE_KEY=0x...
WALLET_ADDRESS=0x...

# Trading Mode: PAPER or LIVE
TRADING_MODE=PAPER

# Capital Settings
TOTAL_CAPITAL=1000
MAX_POSITION_SIZE=100
RISK_PER_TRADE=2

# Strategy Settings
ENABLE_ARBITRAGE=true
ENABLE_TREND_FOLLOWING=true
```

## Usage

### Paper Trading (Recommended for Testing)

```bash
python main.py run --mode paper
```

### Live Trading

```bash
python main.py run --mode live
```

### Run Backtest

```bash
python main.py backtest --days 30
```

### View Status

```bash
python main.py status
```

### List Markets

```bash
python main.py markets
```

## Trading Strategies Explained

### 1. Arbitrage Strategy

**Logic**: In binary prediction markets, YES + NO should equal $1.00.

**Opportunity**: When YES + NO < $1.00, buy both and hold until resolution.

**Example**:
- YES price: $0.48
- NO price: $0.49
- Sum: $0.97
- Profit: $0.03 (3%) guaranteed at resolution

### 2. Market Making

**Logic**: Place buy orders below mid price and sell orders above.

**Profit**: Capture the bid-ask spread.

**Risk Management**: Skew quotes based on inventory (reduce size when heavily positioned).

### 3. Trend Following

**Logic**: Trade with momentum using EMA crossovers.

**Entry**: Fast EMA crosses above Slow EMA + RSI confirmation
**Exit**: Fast EMA crosses below Slow EMA

### 4. Breakout Strategy

**Logic**: Identify consolidation periods and trade breakouts.

**Entry**: Price breaks above resistance or below support
**Confirmation**: Volume spike

## Risk Management

### Position Sizing
Formula: `Size = (Capital × Risk%) × Confidence × Volatility_Factor`

### Limits
- Max position size: Configurable (default $100)
- Max open positions: Configurable (default 5)
- Max drawdown: 20% (trading stops automatically)
- Daily loss limit: 5% of capital

### Stop Losses
- Automatic stop-loss at 50% of position value
- Trailing stops for profitable positions

## Project Structure

```
polymarket-bot/
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── bot.py              # Main bot engine
│   ├── polymarket_client.py # API client wrapper
│   ├── risk_manager.py     # Risk management
│   ├── database.py         # Data persistence
│   └── strategies/
│       ├── __init__.py
│       ├── base.py         # Base strategy class
│       ├── arbitrage.py    # Arbitrage strategy
│       ├── market_making.py # Market making
│       └── trend_following.py # Trend strategy
├── data/                   # Database storage
├── logs/                   # Log files
├── tests/                  # Unit tests
├── main.py                 # CLI entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Performance Expectations

### Arbitrage
- Win rate: ~95% (almost risk-free)
- Return per trade: 1-3%
- Frequency: 2-5 opportunities per day

### Market Making
- Win rate: ~60-70%
- Return per trade: 0.5-1%
- Risk: Inventory accumulation in trending markets

### Trend Following
- Win rate: ~45-55%
- Return per trade: 5-15%
- Risk: False breakouts, whipsaws

## Safety Warnings

⚠️ **IMPORTANT**:

1. **Start with PAPER trading** - Test for at least 1 week
2. **Use small capital** - Start with $100-500
3. **Monitor the bot** - Don't leave unattended for days initially
4. **Understand the risks** - Prediction markets can be volatile
5. **Keep software updated** - Polymarket API may change

## Troubleshooting

### Connection Issues
```bash
# Test API connection
python -c "from src.polymarket_client import client; client.connect(); print('Connected')"
```

### No Trades Executing
- Check if strategies are enabled in config
- Verify you have sufficient USDC balance
- Check risk limits (position size, exposure)

### Database Errors
```bash
# Reset database
rm data/trading_bot.db
```

## Disclaimer

This software is for educational purposes only. Trading prediction markets involves substantial risk of loss. Past performance does not guarantee future results. Use at your own risk.

## License

MIT License - See LICENSE file

## Resources

- [Polymarket API Docs](https://docs.polymarket.com/)
- [py-clob-client](https://github.com/Polymarket/py-clob-client)
- [Prediction Markets Paper](https://arxiv.org/abs/2508.03474)

## Support

For issues and questions:
1. Check logs in `logs/bot.log`
2. Run `python main.py status` for diagnostics
3. Review configuration with `python main.py config`
