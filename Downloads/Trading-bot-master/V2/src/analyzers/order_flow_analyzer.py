import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from .utils.helper import make_post_or_get_request

class OrderFlowAnalyzer:
    def __init__(self):
        self.cache_duration = 300  # 5 minutes cache
        self._cache = {}
        
    def get_options_data(self, symbol: str) -> Dict:
        """Get options chain data including volume and open interest"""
        try:
            # Get instrument ID first
            instrument_url = f"https://api.robinhood.com/instruments/?symbol={symbol}"
            instrument_response = make_post_or_get_request(instrument_url)
            
            if not instrument_response or 'results' not in instrument_response or not instrument_response['results']:
                return {'call_volume': 0, 'put_volume': 0, 'put_call_ratio': 1.0}
            
            instrument_id = instrument_response['results'][0]['id']
            
            # Get options chain data
            chain_url = f"https://api.robinhood.com/options/chains/?equity_instrument_id={instrument_id}"
            chain_response = make_post_or_get_request(chain_url)
            
            if not chain_response or 'results' not in chain_response or not chain_response['results']:
                return {'call_volume': 0, 'put_volume': 0, 'put_call_ratio': 1.0}
            
            chain_id = chain_response['results'][0]['id']
            
            # Get options market data
            options_url = f"https://api.robinhood.com/options/instruments/?chain_id={chain_id}&state=active"
            options_response = make_post_or_get_request(options_url)
            
            if not options_response or 'results' not in options_response:
                return {'call_volume': 0, 'put_volume': 0, 'put_call_ratio': 1.0}
            
            # Get calls and puts
            total_call_volume = 0
            total_put_volume = 0
            
            # Process all options
            for option in options_response['results']:
                market_url = f"https://api.robinhood.com/marketdata/options/{option['id']}/"
                market_data = make_post_or_get_request(market_url)
            
                if market_data and 'volume' in market_data:
                    volume = float(market_data.get('volume', 0))
                    if option['type'] == 'call':
                        total_call_volume += volume
                    else:
                        total_put_volume += volume
            
            put_call_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else 1.0
            
            print(f"Options data for {symbol}:")
            print(f"Call volume: {total_call_volume}")
            print(f"Put volume: {total_put_volume}")
            print(f"Put/Call ratio: {put_call_ratio:.2f}")
            
            return {
                'call_volume': total_call_volume,
                'put_volume': total_put_volume,
                'put_call_ratio': put_call_ratio
            }
        except Exception as e:
            print(f"Error getting options data: {str(e)}")
            return {'call_volume': 0, 'put_volume': 0, 'put_call_ratio': 1.0}
    
    def get_order_book(self, symbol: str) -> Dict:
        """Get order book data from quotes"""
        try:
            # Get quote data
            quote_url = f"https://api.robinhood.com/quotes/{symbol}/"
            quote = make_post_or_get_request(quote_url)
            
            if not quote:
                return {'buy_volume': 0, 'sell_volume': 0, 'buy_sell_ratio': 1.0}
            
            # Get trading volume data
            volume = float(quote.get('volume', 0))
            prev_volume = float(quote.get('previous_close', 0))
            
            # Calculate buy/sell pressure using price movement
            current_price = float(quote.get('last_trade_price', 0))
            prev_price = float(quote.get('previous_close', 0))
            price_change = current_price - prev_price
            
            # Estimate buy/sell volume based on price movement
            if price_change > 0:
                buy_volume = volume * 0.6  # Assume 60% buys in upward movement
                sell_volume = volume * 0.4
            elif price_change < 0:
                buy_volume = volume * 0.4  # Assume 40% buys in downward movement
                sell_volume = volume * 0.6
            else:
                buy_volume = volume * 0.5  # Assume equal distribution if no price change
                sell_volume = volume * 0.5
            
            buy_sell_ratio = buy_volume / sell_volume if sell_volume > 0 else 1.0
            
            print(f"Volume data for {symbol}:")
            print(f"Total volume: {volume:,.0f}")
            print(f"Estimated buy volume: {buy_volume:,.0f}")
            print(f"Estimated sell volume: {sell_volume:,.0f}")
            print(f"Buy/Sell ratio: {buy_sell_ratio:.2f}")
            print(f"Price change: ${price_change:.2f}")
            
            return {
                'buy_volume': buy_volume,
                'sell_volume': sell_volume,
                'buy_sell_ratio': buy_sell_ratio,
                'total_volume': volume,
                'price_change': price_change
            }
        except Exception as e:
            print(f"Error getting order book: {str(e)}")
            return {'buy_volume': 0, 'sell_volume': 0, 'buy_sell_ratio': 1.0}
    
    def get_historical_volume(self, symbol: str) -> Dict:
        """Get historical trading volume patterns"""
        try:
            url = f"https://api.robinhood.com/marketdata/historicals/{symbol}/?interval=5minute&span=day"
            response = make_post_or_get_request(url)
            
            if not response or 'historicals' not in response:
                return {'avg_volume': 0, 'volume_trend': 0}
            
            volumes = [float(bar['volume']) for bar in response['historicals']]
            if not volumes:
                return {'avg_volume': 0, 'volume_trend': 0}
            
            avg_volume = sum(volumes) / len(volumes)
            # Calculate volume trend (positive means increasing volume)
            volume_trend = (volumes[-1] / avg_volume) - 1 if avg_volume > 0 else 0
            
            return {
                'avg_volume': avg_volume,
                'volume_trend': volume_trend
            }
        except Exception as e:
            print(f"Error getting historical volume: {str(e)}")
            return {'avg_volume': 0, 'volume_trend': 0}
    
    def analyze_order_flow(self, symbol: str) -> Dict:
        """Analyze order flow combining options data, order book, and volume patterns"""
        # Check cache first
        cache_key = f"{symbol}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self.cache_duration):
                return cached_data
        
        options_data = self.get_options_data(symbol)
        order_book = self.get_order_book(symbol)
        volume_data = self.get_historical_volume(symbol)
        
        # Combine signals
        bullish_signals = 0
        total_signals = 4
        
        # 1. Put/Call ratio below 1 is bullish
        if options_data['put_call_ratio'] < 1.0:
            bullish_signals += 1
            
        # 2. More buy orders than sell orders is bullish
        if order_book['buy_sell_ratio'] > 1.0:
            bullish_signals += 1
            
        # 3. Above average volume is bullish
        if volume_data['volume_trend'] > 0:
            bullish_signals += 1
            
        # 4. High call volume relative to historical average is bullish
        if options_data['call_volume'] > options_data['put_volume']:
            bullish_signals += 1
        
        sentiment = bullish_signals / total_signals
        
        analysis = {
            'options_data': options_data,
            'order_book': order_book,
            'volume_data': volume_data,
            'sentiment': sentiment,  # 0 to 1, where > 0.5 is bullish
            'strength': abs(sentiment - 0.5) * 2  # 0 to 1, where 1 is strongest signal
        }
        
        # Cache the results
        self._cache[cache_key] = (datetime.now(), analysis)
        
        return analysis


# if __name__ == "__main__":
#     # Test the analyzer
#     analyzer = OrderFlowAnalyzer()
#     result = analyzer.analyze_order_flow("AAPL")
#     print(json.dumps(result, indent=2))