# Trading Bot

A high-performance trading bot for stocks and crypto using Robinhood's API.

## Features

- Real-time market analysis
- Technical indicators
- Market sentiment analysis
- Order flow analysis
- Position sizing optimization
- Risk management
- Parallel processing
- Caching system

## Structure

```
trading_bot/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── smart_trader.py      # Main trading logic
│   ├── order_flow_analyzer.py  # Order flow analysis
│   ├── market_analyzer.py    # Market sentiment analysis
│   ├── cache_manager.py     # Caching system
│   └── utils/               # Utility functions
│       ├── __init__.py
│       └── helper.py         # Helper functions
├── requirements.txt         # Dependencies
├── README.md               # Documentation
└── run.py                  # Entry point
```

## Usage

```python
from trading_bot.src import SmartTrader

# Initialize and start the trading bot
trader = SmartTrader()
trader.start()
```

## Configuration

- Set daily profit/loss limits in `smart_trader.py`
- Adjust technical indicators and thresholds
- Modify watchlist of symbols
- Configure cache TTLs

## Dependencies

- pandas
- numpy
- requests
- zoneinfo
