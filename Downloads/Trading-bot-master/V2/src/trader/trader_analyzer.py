
import pandas as pd
from .config import (
    VOLATILITY_THRESHOLD, MAX_TECHNICAL_SIGNAL_SCORE, 
    SENTIMENT_SCORE_NORMALIZER, DEFAULT_POSITION_MULTIPLIER,
    ORDER_FLOW_BASELINE
)
from ..market_analyzer import MarketAnalyzer
from ..order_flow_analyzer import OrderFlowAnalyzer
from ..utils.helper import (
    make_post_or_get_request, rsi_strategy, macd_strategy,
    bollinger_bands_strategy, stochastic_oscillator_strategy
)

class TradeAnalyzer:
    def __init__(self):
        self.market_analyzer = MarketAnalyzer()
        self.order_flow_analyzer = OrderFlowAnalyzer()

    def analyze(self, symbol):
        url = f"https://api.robinhood.com/marketdata/historicals/{symbol}/?interval=5minute&span=day"
        historical = make_post_or_get_request(url)
        if not historical or 'historicals' not in historical:
            return False, 0, 1.0

        df = pd.DataFrame(historical['historicals'])
        df['close_price'] = pd.to_numeric(df['close_price'])
        prices = df['close_price'].tolist()

        # Technical indicators
        signals = [
            rsi_strategy(prices),
            macd_strategy(prices),
            bollinger_bands_strategy(prices),
            stochastic_oscillator_strategy(prices)
        ]

        # Market & sentiment
        market_data = self.market_analyzer.get_market_sentiment(symbol)
        sentiment_score = market_data['sentiment']
        risk_level = market_data['risk_level']
        volatility = self.market_analyzer.calculate_volatility(prices)
        order_flow = self.order_flow_analyzer.analyze_order_flow(symbol)

        # Buy decision logic
        buy_signals = sum(1 for s in signals if s == "buy")
        technical_strength = buy_signals / MAX_TECHNICAL_SIGNAL_SCORE
        sentiment_factor = (sentiment_score + 2) / SENTIMENT_SCORE_NORMALIZER
        should_buy = (
            technical_strength > 0.5 and
            sentiment_factor >= 0.5 and
            volatility < VOLATILITY_THRESHOLD and
            order_flow['sentiment'] > 0.5
        )

        price = float(df['close_price'].iloc[-1])
        base_multiplier = self.market_analyzer.adjust_position_size(
            DEFAULT_POSITION_MULTIPLIER, volatility, risk_level
        )
        position_multiplier = base_multiplier * (ORDER_FLOW_BASELINE + order_flow['strength'])

        return should_buy, price, position_multiplier