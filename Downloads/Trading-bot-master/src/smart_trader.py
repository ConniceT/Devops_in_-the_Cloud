import pandas as pd
import time
from datetime import datetime, timedelta
import os
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo
from .utils.helper import (make_post_or_get_request, get_current_stock_price, 
                         load_account_profile, get_open_stock_positions, 
                         rsi_strategy, macd_strategy, bollinger_bands_strategy,
                         stochastic_oscillator_strategy, send_notification)
from .market_analyzer import MarketAnalyzer
from .order_flow_analyzer import OrderFlowAnalyzer
from .cache_manager import cache
import json
from functools import lru_cache

class SmartTrader:
    def __init__(self):
        self.stop_loss_percentage = 0.02  # 2% stop loss
        self.profit_target_percentage = 0.03  # 3% profit target
        self.max_daily_loss = 500  # Maximum daily loss in dollars
        self.max_daily_profit = 500  # Take profits for the day after reaching this
        self.daily_profit = 0
        self.daily_loss = 0
        self.positions = {}
        self.market_analyzer = MarketAnalyzer()
        self.order_flow_analyzer = OrderFlowAnalyzer()
        self.volatility_threshold = 0.02  # 2% volatility threshold



    @lru_cache(maxsize=1)
    def get_buying_power(self) -> float:
        """Get available buying power with 1-second cache"""
        try:
            cached = cache.get('buying_power', ttl_seconds=1)
            if cached is not None:
                return cached
                
            account = load_account_profile()
            power = float(account[0]['buying_power'])
            cache.set('buying_power', power)
            return power
        except Exception as e:
            print(f"Error getting buying power: {str(e)}")
            return 0.0

    def analyze_stock(self, symbol: str) -> Tuple[bool, float, float]:
        """
        Analyze if we should buy a stock based on technical indicators and market sentiment
        Returns: (should_buy, suggested_price, position_multiplier)
        """
        try:
            # Get historical data
            url = f"https://api.robinhood.com/marketdata/historicals/{symbol}/?interval=5minute&span=day"
            historical = make_post_or_get_request(url)
            if not historical or 'historicals' not in historical:
                return False, 0, 1.0

            df = pd.DataFrame(historical['historicals'])
            df['close_price'] = pd.to_numeric(df['close_price'])
            prices = df['close_price'].tolist()
            
            # Calculate technical indicators
            rsi_signal = rsi_strategy(prices)
            macd_signal = macd_strategy(prices)
            bb_signal = bollinger_bands_strategy(prices)
            stoch_signal = stochastic_oscillator_strategy(prices)
            
            # Get market sentiment using BLS data
            market_data = self.market_analyzer.get_market_sentiment(symbol)
            sentiment_score = market_data['sentiment']  # Already adjusted for sector
            risk_level = market_data['risk_level']
            
            # Log economic conditions
            if 'economic_data' in market_data:
                print(f"Economic indicators for {symbol} ({market_data['sector']}):\n" + 
                      "\n".join([f"{k}: {v['latest']} (change: {v['change']:.2f}%)" 
                                 for k, v in market_data['economic_data'].items()]))
            
            # Calculate volatility
            volatility = self.market_analyzer.calculate_volatility(prices)
            
            # Count buy signals
            buy_signals = sum(1 for signal in [rsi_signal, macd_signal, bb_signal, stoch_signal] 
                             if signal == "buy")
            
            # Determine if we should buy based on multiple factors
            technical_strength = buy_signals / 4  # Percentage of buy signals
            sentiment_factor = (sentiment_score + 2) / 4  # Normalize to 0-1 range
            
            # Get order flow analysis
            order_flow = self.order_flow_analyzer.analyze_order_flow(symbol)
            
            # Only buy if we have strong technical signals, positive sentiment, and favorable order flow
            should_buy = (technical_strength > 0.5 and 
                        sentiment_factor >= 0.5 and 
                        volatility < self.volatility_threshold and
                        order_flow['sentiment'] > 0.5)
            
            current_price = float(df['close_price'].iloc[-1])
            
            # Calculate position size multiplier based on market conditions and order flow
            base_multiplier = self.market_analyzer.adjust_position_size(
                base_position=1.0,
                volatility=volatility,
                risk_level=risk_level
            )
            
            # Further adjust position size based on order flow strength
            order_flow_multiplier = order_flow['strength']  # 0 to 1
            position_multiplier = base_multiplier * (0.5 + order_flow_multiplier)  # Adjust by ±50% based on order flow
            
            return should_buy, current_price, position_multiplier
        except Exception as e:
            print(f"Error analyzing {symbol}: {str(e)}")
            return False, 0

    def place_buy_order(self, symbol: str, price: float, quantity: int):
        """Place a buy order with stop loss and take profit"""
        try:
            # Place buy order
            url = "https://api.robinhood.com/orders/"
            payload = json.dumps({
                "account": load_account_profile()['account_number'],
                "instrument": f"https://api.robinhood.com/instruments/{symbol}/",
                "symbol": symbol,
                "type": "market",
                "time_in_force": "gtc",
                "trigger": "immediate",
                "quantity": str(quantity),
                "side": "buy"
            })
            order = make_post_or_get_request(url, payload, "POST")
            
            if order['status'] == 'filled':
                stop_price = price * (1 - self.stop_loss_percentage)
                profit_price = price * (1 + self.profit_target_percentage)
                
                # Set stop loss
                stop_loss_payload = json.dumps({
                    "account": load_account_profile()['account_number'],
                    "instrument": f"https://api.robinhood.com/instruments/{symbol}/",
                    "symbol": symbol,
                    "type": "market",
                    "time_in_force": "gtc",
                    "trigger": "stop",
                    "stop_price": str(stop_price),
                    "quantity": str(quantity),
                    "side": "sell"
                })
                make_post_or_get_request(url, stop_loss_payload, "POST")
                
                # Set take profit
                take_profit_payload = json.dumps({
                    "account": load_account_profile()['account_number'],
                    "instrument": f"https://api.robinhood.com/instruments/{symbol}/",
                    "symbol": symbol,
                    "type": "limit",
                    "time_in_force": "gtc",
                    "price": str(profit_price),
                    "quantity": str(quantity),
                    "side": "sell"
                })
                
                self.positions[symbol] = {
                    'quantity': quantity,
                    'entry_price': price,
                    'stop_loss': stop_price,
                    'take_profit': profit_price
                }
                print(f"Bought {quantity} shares of {symbol} at {price}")
        except Exception as e:
            print(f"Error placing buy order for {symbol}: {str(e)}")

    def check_positions(self):
        """Monitor open positions and update daily P/L"""
        try:
            positions = get_open_stock_positions()
            for position in positions:
                symbol = position['symbol']
                quantity = float(position['quantity'])
                if quantity > 0:
                    current_price = float(get_current_stock_price(symbol))
                    entry_price = float(position['average_buy_price'])
                    pl = (current_price - entry_price) * quantity
                    
                    if pl > 0:
                        self.daily_profit += pl
                    else:
                        self.daily_loss -= pl
                        
                    # Check if we hit daily limits
                    # if self.daily_loss >= self.max_daily_loss or self.daily_profit >= self.max_daily_profit:
                    #     self.close_all_positions()
                    #     print("Daily limit reached. Closing all positions.")
                    #     return
        except Exception as e:
            print(f"Error checking positions: {str(e)}")

    def close_all_positions(self):
        """Close all open positions"""
        try:
            positions = get_open_stock_positions()
            for position in positions:
                symbol = position['symbol']
                quantity = float(position['quantity'])
                if quantity > 0:
                    url = "https://api.robinhood.com/orders/"
                    payload = json.dumps({
                        "account": load_account_profile()['account_number'],
                        "instrument": f"https://api.robinhood.com/instruments/{symbol}/",
                        "symbol": symbol,
                        "type": "market",
                        "time_in_force": "gtc",
                        "trigger": "immediate",
                        "quantity": str(quantity),
                        "side": "sell"
                    })
                    make_post_or_get_request(url, payload, "POST")
                    print(f"Closed position in {symbol}")
        except Exception as e:
            print(f"Error closing positions: {str(e)}")

    def run_trading_session(self):
        """Main trading loop with parallel processing"""
        # Reset daily P/L
        self.daily_profit = 0
        self.daily_loss = 0
        
        # List of stocks/crypto to monitor
        watchlist = ['TSLA', 'META', 'MSTR', 'MSFT', 'GOOGL', 'BTC', 'ETH']  # Add your preferred symbols
        
        while True:
            # Convert current time to ET
            current_time = datetime.now(ZoneInfo('America/New_York')).time()
            market_open = datetime.strptime('09:30', '%H:%M').time()
            market_close = datetime.strptime('16:00', '%H:%M').time()
            
            # Only trade during market hours (9:30 AM - 4:00 PM ET)
            if market_open <= current_time <= market_close:
                # Get buying power first
                buying_power = self.get_buying_power()
                
                # Check current positions
                self.check_positions()
                
                # Analyze each symbol sequentially
                for symbol in watchlist:
                    try:
                        should_buy, price, position_multiplier = self.analyze_stock(symbol)
                        if should_buy and buying_power > price * 100:  # Minimum 100 shares
                            send_notification(f"{symbol} BUY")
                            base_quantity = int(buying_power / price)
                            adjusted_quantity = int(base_quantity * position_multiplier)
                            if adjusted_quantity >= 100:  # Ensure we still meet minimum
                                self.place_buy_order(symbol, price, adjusted_quantity)
                    except Exception as e:
                        print(f"Error processing {symbol}: {str(e)}")
                
            time.sleep(5)  # Check every minute

    def start(self):
        """Start the trading bot"""
        try:
            print("Starting SmartTrader bot...")
            self.run_trading_session()
        except KeyboardInterrupt:
            print("Shutting down bot...")
            # self.close_all_positions()
            # rh.logout()
