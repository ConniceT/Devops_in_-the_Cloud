import json
import smtplib
from uuid import uuid4
import requests
import numpy as np
import pandas as pd

class Helper:
    @staticmethod
    def make_post_or_get_request(url, payload=None, post_or_get="GET"):
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': '{robinhood_bearer_auth}',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Content-Type': 'application/json'
        }

        response = requests.request(post_or_get, url, headers=headers, data=payload)
        status_code = 500
        while status_code >= 300:
            status_code = response.status_code
            if status_code != 200:
                print("response not 200", response.text)
                return response
            else:
                return json.loads(response.text)
        return

    @staticmethod
    def get_id(symbol):
        url = "https://nummus.robinhood.com/currency_pairs/"
        response = Helper.make_post_or_get_request(url)
        if 'results' in response:
            for result in response['results']:
                if result['asset_currency']['code'] == symbol:
                    return result['id']
        raise Exception("symbol not found")

    @staticmethod
    def get_current_price(symbol, key='mark_price'):
        crypto_id = Helper.get_id(symbol)
        url = f"https://api.robinhood.com/marketdata/forex/quotes/?ids={crypto_id}"
        response = Helper.make_post_or_get_request(url)
        return float(response['results'][0][key])

    @staticmethod
    def get_current_stock_price(symbol):
        url = f"https://api.robinhood.com/quotes/?symbols={symbol}"
        response = Helper.make_post_or_get_request(url)
        item = response['results'][0]
        return item['last_extended_hours_trade_price'] or item['last_trade_price']

    @staticmethod
    def get_history(symbol, index_range=0):
        crypto_id = Helper.get_id(symbol)
        url = f"https://api.robinhood.com/marketdata/forex/historicals/{crypto_id}/?bounds=24_7&interval=5minute&span=day"
        response = Helper.make_post_or_get_request(url)
        return [float(datapoint['close_price']) for datapoint in response['data_points'][index_range:]]

    @staticmethod
    def get_historical_crypto_data(symbol):
        crypto_id = Helper.get_id(symbol)
        url = f"https://api.robinhood.com/marketdata/forex/historicals/{crypto_id}/?bounds=24_7&interval=5minute&span=day"
        response = Helper.make_post_or_get_request(url)
        df = pd.DataFrame({"close_price": [float(datapoint['close_price']) for datapoint in response['data_points']]})
        df['close_price'] = df['close_price'].astype(float)
        return df

    @staticmethod
    def round_price(price):
        price = float(price)
        if price <= 1e-2:
            return round(price, 6)
        elif price < 1e0:
            return round(price, 4)
        else:
            return round(price, 2)

    @staticmethod
    def momentum_strategy(history):
        if len(history) < 3:
            return "hold"
        return "buy" if history[-1] > history[-2] > history[-3] else "sell" if history[-1] < history[-2] < history[-3] else "hold"

    @staticmethod
    def sma_strategy(prices, short_window=10, long_window=50):
        short_sma = np.mean(prices[-short_window:])
        long_sma = np.mean(prices[-long_window:])
        return "buy" if short_sma > long_sma else "sell" if short_sma < long_sma else "hold"

    @staticmethod
    def rsi_strategy(prices, period=14):
        """Relative Strength Index (RSI) Strategy"""
        delta = np.diff(prices)
        gain = np.maximum(delta, 0)
        loss = np.maximum(-delta, 0)
        avg_gain = np.mean(gain[-period:])
        avg_loss = np.mean(loss[-period:])
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return "buy" if rsi < 30 else "sell" if rsi > 70 else "hold"

    @staticmethod
    def macd_strategy(history):
        """MACD crossover strategy."""
        if len(history) < 26:
            return "hold"
        short_ema = np.mean(history[-12:])
        long_ema = np.mean(history[-26:])
        macd = short_ema - long_ema
        signal = np.mean(history[-9:])
        return "buy" if macd > signal else "sell" if macd < signal else "hold"

    @staticmethod
    def bollinger_bands_strategy(history, period=20):
        """Buy when price is near the lower band, sell near the upper band."""
        if len(history) < period:
            return "hold"
        sma = np.mean(history[-period:])
        std_dev = np.std(history[-period:])
        lower_band = sma - (2 * std_dev)
        upper_band = sma + (2 * std_dev)
        return "buy" if history[-1] <= lower_band else "sell" if history[-1] >= upper_band else "hold"

    @staticmethod
    def stochastic_oscillator_strategy(history, period=14):
        if len(history) < period:
            return "hold"
        high = max(history[-period:])
        low = min(history[-period:])
        close = history[-1]
        percent_k = 100 * (close - low) / (high - low) if high != low else 50
        return "buy" if percent_k < 20 else "sell" if percent_k > 80 else "hold"

    @staticmethod
    def get_trading_action(prices):
        strategies = [
            Helper.sma_strategy,
            Helper.rsi_strategy,
            Helper.momentum_strategy,
            Helper.macd_strategy
        ]
        result = {strategy.__name__: strategy(prices) for strategy in strategies}
        return result

    @staticmethod
    def process_decision(strategy_result):
        buy = sum(1 for val in strategy_result.values() if val == "buy")
        sell = sum(1 for val in strategy_result.values() if val == "sell")
        hold = sum(1 for val in strategy_result.values() if val == "hold")
        return "buy" if buy > max(sell, hold) else "sell" if sell > max(buy, hold) else "hold"

    @staticmethod
    def send_notification(message, send_email=False):
        if send_email:
            s = smtplib.SMTP('smtp.gmail.com', 587)
            s.starttls()
            s.login("{email_address}", "{app_password}")
            s.sendmail("{email_from}", "{email_to}", f"{message}")
            s.quit()
        else:
            url = "https://api.pushcut.io/{push_cut_key}/notifications/Crypto"
            payload = json.dumps({"input": "", "text": f"{message}", "title": f"{message}"})
            Helper.make_post_or_get_request(url, payload, "POST")
