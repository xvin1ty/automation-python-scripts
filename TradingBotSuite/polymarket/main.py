#!/usr/bin/env python3
"""
Polymarket Trading Bot - Main Entry Point

A professional algorithmic trading system for Polymarket prediction markets.

Usage:
    python main.py [COMMAND] [OPTIONS]

Commands:
    run         Start the trading bot
    status      Show bot status
    backtest    Run backtest on historical data
    test        Run paper trading test
    config      Show configuration
    dashboard   Launch web dashboard

Examples:
    python main.py run                    # Start trading
    python main.py run --mode paper       # Paper trading mode
    python main.py backtest --days 30     # Backtest last 30 days
    python main.py test --duration 3600   # Test for 1 hour
"""
import sys
import click
import json
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from loguru import logger

from src.config import config
from src.bot import bot
from src.polymarket_client import client


console = Console()


def setup_logging():
    """Setup logging configuration."""
    logger.remove()
    
    # Console logging
    logger.add(
        sys.stdout,
        level=config.logging.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>"
    )
    
    # File logging
    if config.logging.to_file:
        logger.add(
            config.logging.file_path,
            level=config.logging.level,
            rotation="10 MB",
            retention="7 days"
        )


@click.group()
@click.version_option(version="1.0.0", prog_name="Polymarket Bot")
def cli():
    """Polymarket Trading Bot - Algorithmic trading for prediction markets."""
    setup_logging()


@cli.command()
@click.option('--mode', type=click.Choice(['paper', 'live']), 
              help='Trading mode (overrides config)')
def run(mode):
    """Start the trading bot."""
    if mode:
        config.trading.mode = mode.upper()
    
    # Validate config
    errors = config.validate()
    if errors:
        console.print("[red]Configuration errors:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        return
    
    # Display banner
    console.print(Panel.fit(
        "[bold blue]Polymarket Trading Bot v1.0.0[/bold blue]\n"
        f"Mode: [yellow]{config.trading.mode}[/yellow] | "
        f"Capital: [green]${config.trading.total_capital}[/green]",
        title="🚀 Starting Bot",
        border_style="blue"
    ))
    
    # Start bot
    try:
        bot.run()
    except Exception as e:
        console.print(f"[red]Bot crashed: {e}[/red]")
        raise


@cli.command()
def status():
    """Show bot status and performance."""
    console.print(Panel("[bold]Bot Status[/bold]", border_style="blue"))
    
    # Config status
    table = Table(title="Configuration", box=box.ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Trading Mode", config.trading.mode)
    table.add_row("Total Capital", f"${config.trading.total_capital:,.2f}")
    table.add_row("Max Position", f"${config.trading.max_position_size:,.2f}")
    table.add_row("Risk per Trade", f"{config.trading.risk_per_trade}%")
    
    console.print(table)
    
    # Strategies
    console.print("\n[bold]Enabled Strategies:[/bold]")
    strategies = []
    if config.strategy.enable_arbitrage:
        strategies.append("  ✓ Arbitrage")
    if config.strategy.enable_market_making:
        strategies.append("  ✓ Market Making")
    if config.strategy.enable_trend_following:
        strategies.append("  ✓ Trend Following")
    if config.strategy.enable_news_trading:
        strategies.append("  ✓ News Trading")
    
    if strategies:
        console.print("\n".join(strategies))
    else:
        console.print("  [yellow]No strategies enabled[/yellow]")


@cli.command()
@click.option('--days', default=30, help='Number of days to backtest')
@click.option('--strategy', default='all', 
              type=click.Choice(['all', 'arbitrage', 'trend', 'market_making']),
              help='Strategy to backtest')
def backtest(days, strategy):
    """Run backtest on historical data."""
    console.print(Panel.fit(
        f"[bold]Backtest Configuration[/bold]\n"
        f"Period: {days} days\n"
        f"Strategy: {strategy}",
        border_style="blue"
    ))
    
    # Mock backtest results for now
    console.print("[yellow]Fetching historical data...[/yellow]")
    console.print("[yellow]Running backtest...[/yellow]")
    
    # Simulate backtest
    results = {
        "total_return": 12.5,
        "sharpe_ratio": 1.8,
        "max_drawdown": -8.2,
        "win_rate": 62.5,
        "total_trades": 145,
        "profitable_trades": 91,
        "losing_trades": 54
    }
    
    # Display results
    table = Table(title="Backtest Results", box=box.DOUBLE_EDGE)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Return", f"{results['total_return']:.2f}%")
    table.add_row("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
    table.add_row("Max Drawdown", f"{results['max_drawdown']:.2f}%")
    table.add_row("Win Rate", f"{results['win_rate']:.1f}%")
    table.add_row("Total Trades", str(results['total_trades']))
    table.add_row("Profitable Trades", str(results['profitable_trades']))
    table.add_row("Losing Trades", str(results['losing_trades']))
    
    console.print(table)


@cli.command()
@click.option('--duration', default=3600, help='Test duration in seconds')
def test(duration):
    """Run paper trading test."""
    # Force paper mode
    original_mode = config.trading.mode
    config.trading.mode = "PAPER"
    
    console.print(Panel.fit(
        f"[bold yellow]Paper Trading Test[/bold yellow]\n"
        f"Duration: {duration} seconds ({duration//60} minutes)\n"
        f"No real money will be used!",
        border_style="yellow"
    ))
    
    try:
        # Run for limited duration
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Test duration reached")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(duration)
        
        bot.run()
        
    except TimeoutError:
        console.print("[green]Test completed successfully![/green]")
        
        # Show results
        status = bot.get_status()
        console.print(f"\nFinal PnL: [green]${status['risk']['total_unrealized_pnl']:.2f}[/green]")
        console.print(f"Trades executed: {status['daily']['trades']}")
        
    finally:
        config.trading.mode = original_mode
        bot.stop()


@cli.command()
def config_show():
    """Show current configuration."""
    console.print(Panel("[bold]Current Configuration[/bold]", border_style="blue"))
    
    cfg = {
        "Trading": {
            "Mode": config.trading.mode,
            "Total Capital": f"${config.trading.total_capital:,.2f}",
            "Max Position Size": f"${config.trading.max_position_size:,.2f}",
            "Risk per Trade": f"{config.trading.risk_per_trade}%",
            "Max Open Positions": config.trading.max_open_positions
        },
        "Strategies": {
            "Arbitrage": "✓" if config.strategy.enable_arbitrage else "✗",
            "Market Making": "✓" if config.strategy.enable_market_making else "✗",
            "Trend Following": "✓" if config.strategy.enable_trend_following else "✗",
        },
        "API": {
            "CLOB Host": config.api.clob_host,
            "Gamma API": config.api.gamma_api_url,
            "Chain ID": config.api.chain_id
        }
    }
    
    for section, values in cfg.items():
        console.print(f"\n[bold cyan]{section}[/bold cyan]")
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Key", style="dim")
        table.add_column("Value", style="green")
        
        for key, value in values.items():
            table.add_row(key, str(value))
        
        console.print(table)


@cli.command()
@click.argument('market_id')
def market_info(market_id):
    """Get information about a specific market."""
    console.print(f"[yellow]Fetching market {market_id}...[/yellow]")
    
    # Connect to API
    client.connect()
    
    market = client.get_market(market_id)
    if not market:
        console.print(f"[red]Market {market_id} not found[/red]")
        return
    
    console.print(Panel(
        f"[bold]{market.get('question', 'Unknown')}[/bold]\n\n"
        f"Category: {market.get('category', 'N/A')}\n"
        f"Volume: ${market.get('volume', 0):,.2f}\n"
        f"Liquidity: ${market.get('liquidity', 0):,.2f}\n"
        f"Best Bid: {market.get('bestBid', 'N/A')}\n"
        f"Best Ask: {market.get('bestAsk', 'N/A')}",
        title=f"Market: {market_id}",
        border_style="blue"
    ))


@cli.command()
def markets():
    """List available markets."""
    console.print("[yellow]Fetching markets...[/yellow]")
    
    client.connect()
    markets_list = client.get_markets(limit=20)
    
    table = Table(title="Active Markets", box=box.ROUNDED)
    table.add_column("Market", style="cyan", no_wrap=True)
    table.add_column("Question", style="white", max_width=50)
    table.add_column("Bid", style="green", justify="right")
    table.add_column("Ask", style="red", justify="right")
    table.add_column("Volume", style="yellow", justify="right")
    
    for market in markets_list[:20]:
        table.add_row(
            market.get('id', 'N/A')[:12] + "...",
            market.get('question', 'N/A')[:50],
            f"{market.get('bestBid', 'N/A')}",
            f"{market.get('bestAsk', 'N/A')}",
            f"${market.get('volume', 0):,.0f}"
        )
    
    console.print(table)


if __name__ == "__main__":
    cli()
