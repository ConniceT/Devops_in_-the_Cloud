# === Configuration Settings ===
class Config:
    STOP_LOSS_PCT = 0.02               # 2% stop loss
    TAKE_PROFIT_PCT = 0.03            # 3% fixed profit target
    TRAILING_STOP_PCT = 0.015         # 1.5% trailing stop
    USE_TRAILING_STOP = True

    MAX_DAILY_LOSS = 500              # in US dollars
    MAX_DAILY_PROFIT = 500

    WATCHLIST = ["TSLA", "META", "MSTR", "MSFT", "GOOGL", "BTC", "ETH"]

    VOLATILITY_THRESHOLD = 0.02       # max acceptable daily std deviation

    CHECK_INTERVAL_SECONDS = 5        # how often to scan market
    MARKET_OPEN_TIME = "09:30"
    MARKET_CLOSE_TIME = "16:00"

    # Decision weighting and scoring
    MAX_TECHNICAL_SIGNAL_SCORE = 4
    SENTIMENT_SCORE_NORMALIZER = 4
    DEFAULT_POSITION_MULTIPLIER = 1.0
    ORDER_FLOW_BASELINE = 0.5
