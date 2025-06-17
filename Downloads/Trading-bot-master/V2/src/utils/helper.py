"""Util for re-usable functions"""
import json
import smtplib
from uuid import uuid4
import requests
import numpy as np
import pandas as pd

def make_post_or_get_request(url, payload=None, post_or_get="GET"):
    """Make post or get request"""
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': '{robinhood_bearer_auth}',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Content-Type': 'application/json'
    }

    response = requests.request(
        post_or_get, url, headers=headers, data=payload)

    status_code = 500
    while status_code >= 300:
        status_code = response.status_code
        if status_code != 200:
            print("response not 200", response.text)
            return response
        else:
            return json.loads(response.text)
    return

def get_id(symbol):
    """Get crypto id"""
    url = "https://nummus.robinhood.com/currency_pairs/"
    response = make_post_or_get_request(url)
    if 'results' in response:
        for result in response['results']:
            if result['asset_currency']['code'] == symbol:
                return result['id']
    else:
        raise Exception("result not found")

    raise Exception("symbol not found")

def get_current_price(symbol, key = 'mark_price'):
    """Get current price"""
    crypto_id = get_id(symbol)
    url = f"https://api.robinhood.com/marketdata/forex/quotes/?ids={crypto_id}"
    response = make_post_or_get_request(url)
    if len(response['results']) > 1:
        pass
    return float(response['results'][0][key])

def get_current_stock_price(symbol):
    """Get current stock price"""
    url = f"https://api.robinhood.com/quotes/?symbols={symbol}"
    response = make_post_or_get_request(url)
    item = response['results'][0]

    if item['last_extended_hours_trade_price'] is None:
        return item['last_trade_price']
    else:
        return item['last_extended_hours_trade_price']

def get_history(symbol, index_range = 0):
    """Get crypto history price"""
    crypto_id = get_id(symbol)
    url = f"https://api.robinhood.com/marketdata/forex/historicals/{crypto_id}/?bounds=24_7&interval=5minute&span=day"
    response = make_post_or_get_request(url)
    return [float(data_point['close_price']) for data_point in response['data_points'][index_range:]]


def get_historical_crypto_data(symbol):
    """Get crypto history price"""
    crypto_id = get_id(symbol)
    url = f"https://api.robinhood.com/marketdata/forex/historicals/{crypto_id}/?bounds=24_7&interval=5minute&span=day"
    response = make_post_or_get_request(url)
    df = pd.DataFrame({"close_price": [float(
        data_point['close_price']) for data_point in response['data_points']]})
    df['close_price'] = df['close_price'].astype(float)
    return df

def get_stock_history(symbol, index_range:int = 0):
    """Get stock history price"""
    url = f"https://api.robinhood.com/quotes/historicals/?symbols={symbol}&interval=5minute&span=day&bounds=extended"
    response = make_post_or_get_request(url)
    return [float(data_point['close_price']) for data_point in response['results'][0]['historicals'][index_range:]]

def get_account_id():
    """Get account id from account info"""
    url = "https://nummus.robinhood.com/accounts/"
    response = make_post_or_get_request(url)
    return response['results'][0]['id']

def round_price(price):
    """Takes a price and rounds it to an appropriate decimal place that Robinhood will accept.

    :param price: The input price to round.
    :type price: float or int
    :returns: The rounded price as a float.

    """
    price = float(price)
    if price <= 1e-2:
        return_price = round(price, 6)
    elif price < 1e0:
        return_price = round(price, 4)
    else:
        return_price = round(price, 2)

    return return_price

def momentum_strategy(history):
    """Buy if price is increasing steadily, sell if decreasing."""
    if len(history) < 3:
        return "hold"
    return "buy" if history[-1] > history[-2] > history[-3] else "sell" if history[-1] < history[-2] < history[-3] else "hold"

def sma_strategy(prices, short_window=10, long_window=50):
    """Simple Moving Average (SMA) Strategy"""
    short_window_prices = prices[-short_window:]
    short_sma = sum(short_window_prices)/len(short_window_prices)

    long_window_prices = prices[-long_window:]
    long_sma = sum(long_window_prices)/len(long_window_prices)
    if short_sma > long_sma:
        return "buy"
    elif short_sma < long_sma:
        return "sell"
    return "hold"

def rsi_strategy(prices, period=14):
    """Relative Strength Index (RSI) Strategy"""
    delta = np.diff(prices)
    gain = np.maximum(delta, 0)
    loss = np.maximum(-delta, 0)

    avg_gain = np.mean(gain[-period:])
    avg_loss = np.mean(loss[-period:])

    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))

    if rsi < 30:
        return "buy"
    elif rsi > 70:
        return "sell"
    return "hold"

def macd_strategy(history):
    """MACD crossover strategy."""
    if len(history) < 26:
        return "hold"

    short_ema = sum(history[-12:]) / 12
    long_ema = sum(history[-26:]) / 26
    macd = short_ema - long_ema
    signal = sum(history[-9:]) / 9

    return "buy" if macd > signal else "sell" if macd < signal else "hold"

def bollinger_bands_strategy(history, period=20):
    """Buy when price is near the lower band, sell near the upper band."""
    if len(history) < period:
        return "hold"

    sma = sum(history[-period:]) / period
    std_dev = (sum((p - sma) ** 2 for p in history[-period:]) / period) ** 0.5

    lower_band = sma - (2 * std_dev)
    upper_band = sma + (2 * std_dev)

    return "buy" if history[-1] <= lower_band else "sell" if history[-1] >= upper_band else "hold"

def stochastic_oscillator_strategy(history, period=14):
    """Buy if %K crosses above %D in oversold region, sell in overbought."""
    if len(history) < period:
        return "hold"

    highest_high = max(history[-period:])
    lowest_low = min(history[-period:])
    current_close = history[-1]

    percent_k = 100 * (current_close - lowest_low) / (highest_high - lowest_low) if highest_high != lowest_low else 50

    return "buy" if percent_k < 20 else "sell" if percent_k > 80 else "hold"

def get_trading_action(prices):
    """Determine buy/sell decision based on majority vote"""
    strategies = [
        sma_strategy,
        rsi_strategy,
        momentum_strategy,
        macd_strategy
    ]
    strategy_result = {}
    for strategy in strategies:
        action = strategy(prices)
        strategy_result[strategy.__name__] = action
    return strategy_result  # Return action with most votes

def process_decision(strategy_result):
    buy_signals = sum(1 for decision in strategy_result.values() if "buy" in decision)
    sell_signals = sum(1 for decision in strategy_result.values() if "sell" in decision)
    hold_signals = sum(1 for decision in strategy_result.values() if "hold" in decision)

    if hold_signals > sell_signals and hold_signals > buy_signals:
        return "hold"

    if buy_signals > sell_signals and buy_signals > hold_signals:
        return "buy"
    elif sell_signals > buy_signals and sell_signals > hold_signals:
        if hold_signals == sell_signals:
            return "hold"
        else:
            return "sell"
    else:
        return "hold"

def send_notification(message, should_send_email=False):
    """Sending email"""
    if should_send_email:
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login("{email_address}", "{app_password}")
        s.sendmail("{email_from}", "{email_to}", f"{message}")
        s.quit()
    else:
        url = "https://api.pushcut.io/{push_cut_key}/notifications/Crypto"
        payload = json.dumps({
            "input": "",
            "text": f"{message}",
            "title": f"{message}"
        })
        response = make_post_or_get_request(url, payload, "POST")

class RiskManager:
    """Risk Management: Stop-loss, Take-profit, Trailing Stop-loss"""
    def __init__(self, stop_loss_pct=2, take_profit_pct=5, trailing_stop_pct=2):
        self.stop_loss_pct = stop_loss_pct / 100
        self.take_profit_pct = take_profit_pct / 100
        self.trailing_stop_pct = trailing_stop_pct / 100
        self.entry_price = None
        self.highest_price = None

    def should_exit_trade(self, current_price):
        """Exit Strategy"""
        if self.entry_price is None:
            return False

        if current_price <= self.entry_price * (1 - self.stop_loss_pct):
            return "sell"
        if current_price >= self.entry_price * (1 + self.take_profit_pct):
            return "sell"
        if self.highest_price and current_price <= self.highest_price * (1 - self.trailing_stop_pct):
            return "sell"

        self.highest_price = max(self.highest_price or self.entry_price, current_price)
        return False

def place_crypto_order(symbol, side, buying_or_selling_price, order_type="market"):
    """Buy or sell crypto"""
    # side is buy or sell
    current_ask_price = get_current_price(symbol, 'ask_price')
    current_bid_price = get_current_price(symbol, 'bid_price')

    if side == 'buy':
        price = current_ask_price #has to be 1% increase of the price to buy and 5% decrease of the price to sell
    elif side == 'sell':
        price = current_bid_price #has to be 1% increase of the price to buy and 5% decrease of the price to sell

    account_id = get_account_id()
    crypto_id = get_id(symbol)
    price = round_price(price)
    quantity = round_price(buying_or_selling_price/price)
    time_in_force = "gtc"

    url = "https://nummus.robinhood.com/orders/"
    data = {
        "account_id": f"{account_id}",
        "currency_pair_id": f"{crypto_id}",
        # "is_quantity_collared": False,
        "price": f"{price}",
        "quantity": f"{quantity}",
        "ref_id": f"{str(uuid4())}",
        "side": f"{side}",
        "time_in_force": f"{time_in_force}",
        "type": f"{order_type}"
    }

    print(f"Attempting to {side} symbol={symbol}; price={price}; quantity={quantity}; order_type={order_type}")

    # if order_type == "market":
    #     data["entered_amount"] = f"{buying_or_selling_price}"

    payload = json.dumps(data)

    return make_post_or_get_request(url, payload, "POST")

def calculate_trend(symbol):
    df = get_historical_crypto_data(symbol)
    df["SMA_20"] = df["close_price"].rolling(window=20).mean()
    df["Momentum"] = df["close_price"].diff()
    
    if df["Momentum"].iloc[-1] > 0 and df["close_price"].iloc[-1] > df["SMA_20"].iloc[-1]:
        return "buy"
    elif df["Momentum"].iloc[-1] < 0:
        return "sell"
    return "hold"

def load_portfolio_profile():
    """Load portfolio profile to get equity balance"""
    url = "https://api.robinhood.com/portfolios/"
    response = make_post_or_get_request(url)
    return response['results'][0]

def load_account_profile():
    """Load account profile to get equity balance"""
    url = "https://api.robinhood.com/accounts/?default_to_all_accounts=true"
    response = make_post_or_get_request(url)
    return response['results']

def get_last_hour_historical(stock_symbols, symbol, last_hour=-12):
    """Get historical data in the last hour"""
    if symbol in stock_symbols:
        return get_stock_history(symbol, index_range=last_hour)
    else:
        return get_history(symbol, index_range=last_hour)

def get_open_stock_positions():
    url = "https://api.robinhood.com/positions/?nonzero=true"
    response = make_post_or_get_request(url)
    return response['results']

def get_crypto_holdings(symbol, key = 'quantity_available'):
    url = "https://nummus.robinhood.com/holdings/"
    response = make_post_or_get_request(url)
    for item in response['results']:
        if item['currency']['code'] == symbol:
            return item[key]



def build_holdings():
    """Builds a dictionary of important information regarding the stocks and positions owned by the user.

    :param with_dividends: True if you want to include divident information.
    :type with_dividends: bool
    :returns: Returns a dictionary where the keys are the stock tickers and the value is another dictionary \
    that has the stock price, quantity held, equity, percent change, equity change, type, name, id, pe ratio, \
    percentage of portfolio, and average buy price.

    """
    positions_data = get_open_stock_positions()
    portfolios_data = load_portfolio_profile()
    accounts_data = load_account_profile()[0]

    # user wants dividend information in their holdings
    # if with_dividends is True:
    #     dividend_data = get_dividends()

    if not positions_data or not portfolios_data or not accounts_data:
        return({})

    if portfolios_data['extended_hours_equity'] is not None:
        total_equity = max(float(portfolios_data['equity']), float(
            portfolios_data['extended_hours_equity']))
    else:
        total_equity = float(portfolios_data['equity'])

    cash = "{0:.2f}".format(
        float(accounts_data['cash']) + float(accounts_data['uncleared_deposits']))

    holdings = {}
    for item in positions_data:
        # It is possible for positions_data to be [None]
        if not item:
            continue

        try:
            instrument_data = make_post_or_get_request(item['instrument'])
            symbol = instrument_data['symbol']
            # fundamental_data = get_fundamentals(symbol)[0]

            price = get_current_stock_price(symbol)[0]
            quantity = item['quantity']
            equity = float(item['quantity']) * float(price)
            equity_change = (float(quantity) * float(price)) - \
                (float(quantity) * float(item['average_buy_price']))
            percentage = float(item['quantity']) * float(price) * \
                100 / (float(total_equity) - float(cash))
            if (float(item['average_buy_price']) == 0.0):
                percent_change = 0.0
            else:
                percent_change = (float(
                    price) - float(item['average_buy_price'])) * 100 / float(item['average_buy_price'])
            if (float(item['intraday_average_buy_price']) == 0.0):
                intraday_percent_change = 0.0
            else:
                intraday_percent_change = (float(
                    price) - float(item['intraday_average_buy_price'])) * 100 / float(item['intraday_average_buy_price'])
            holdings[symbol] = ({'price': price})
            holdings[symbol].update({'quantity': quantity})
            holdings[symbol].update(
                {'average_buy_price': item['average_buy_price']})
            holdings[symbol].update({'equity': "{0:.2f}".format(equity)})
            holdings[symbol].update(
                {'percent_change': "{0:.2f}".format(percent_change)})
            holdings[symbol].update(
                {'intraday_percent_change': "{0:.2f}".format(intraday_percent_change)})
            holdings[symbol].update(
                {'equity_change': "{0:2f}".format(equity_change)})
            holdings[symbol].update({'type': instrument_data['type']})
            # holdings[symbol].update(
            #     {'name': get_name_by_symbol(symbol)})
            holdings[symbol].update({'id': instrument_data['id']})
            # holdings[symbol].update({'pe_ratio': fundamental_data['pe_ratio']})
            holdings[symbol].update(
                {'percentage': "{0:.2f}".format(percentage)})

            # if with_dividends is True:
            #     # dividend_data was retrieved earlier
            #     holdings[symbol].update(get_dividends_by_instrument(
            #         item['instrument'], dividend_data))

        except:
            pass

    return(holdings)

# def order(symbol, quantity, side, limitPrice=None, stopPrice=None, account_number=None, timeInForce='gtc', extendedHours=False, jsonify=True, market_hours='regular_hours'):
#     """A generic order function.

#     :param symbol: The stock ticker of the stock to sell.
#     :type symbol: str
#     :param quantity: The number of stocks to sell.
#     :type quantity: int
#     :param side: Either 'buy' or 'sell'
#     :type side: str
#     :param limitPrice: The price to trigger the market order.
#     :type limitPrice: float
#     :param stopPrice: The price to trigger the limit or market order.
#     :type stopPrice: float
#     :param account_number: the robinhood account number.
#     :type account_number: Optional[str]
#     :param timeInForce: Changes how long the order will be in effect for. 'gtc' = good until cancelled. \
#     'gfd' = good for the day.
#     :type timeInForce: str
#     :param extendedHours: Premium users only. Allows trading during extended hours. Should be true or false.
#     :type extendedHours: Optional[str]
#     :param jsonify: If set to False, function will return the request object which contains status code and headers.
#     :type jsonify: Optional[str]
#     :returns: Dictionary that contains information regarding the purchase or selling of stocks, \
#     such as the order id, the state of order (queued, confired, filled, failed, canceled, etc.), \
#     the price, and the quantity.

#     """ 
#     try:
#         symbol = symbol.upper().strip()
#     except AttributeError as message:
#         print(message, file=get_output())
#         return None

#     orderType = "market"
#     trigger = "immediate"

#     if side == "buy":
#         priceType = "ask_price"
#     else:
#         priceType = "bid_price"

#     if limitPrice and stopPrice:
#         price = round_price(limitPrice)
#         stopPrice = round_price(stopPrice)
#         orderType = "limit"
#         trigger = "stop"
#     elif limitPrice:
#         price = round_price(limitPrice)
#         orderType = "limit"
#     elif stopPrice:
#         stopPrice = round_price(stopPrice)
#         if side == "buy":
#             price = stopPrice
#         else:
#             price = None
#         trigger = "stop"
#     else:
#         price = round_price(next(iter(get_latest_price(symbol, priceType, extendedHours)), 0.00))
        
#     from datetime import datetime
#     payload = {
#         'account': load_account_profile(account_number=account_number, info='url'),
#         'instrument': get_instruments_by_symbols(symbol, info='url')[0],
#         'symbol': symbol,
#         'price': price,
#         'ask_price': round_price(next(iter(get_latest_price(symbol, "ask_price", extendedHours)), 0.00)),
#         'bid_ask_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
#         'bid_price': round_price(next(iter(get_latest_price(symbol, "bid_price", extendedHours)), 0.00)),
#         'quantity': quantity,
#         'ref_id': str(uuid4()),
#         'type': orderType,
#         'stop_price': stopPrice,
#         'time_in_force': timeInForce,
#         'trigger': trigger,
#         'side': side,
#         'market_hours': market_hours, # choices are ['regular_hours', 'all_day_hours', 'extended_hours']
#         'extended_hours': extendedHours,
#         'order_form_version': 4
#     }
#     # adjust market orders
#     if orderType == 'market':
#         if trigger != "stop":
#             del payload['stop_price']
#         # if market_hours == 'regular_hours': 
#         #     del payload['extended_hours'] 
        
#     if market_hours == 'regular_hours':
#         if side == "buy":
#             payload['preset_percent_limit'] = "0.05"
#             payload['type'] = 'limit' 
#         # regular market sell
#         elif orderType == 'market' and side == 'sell':
#             del payload['price']   
#     elif market_hours in ('extended_hours', 'all_day_hours'):
#         payload['type'] = 'limit' 
#         payload['quantity']=int(payload['quantity']) # round to integer instead of fractional
        
#     url = orders_url(account_number=account_number)
#     # print(payload)
#     data = request_post(url, payload, jsonify_data=jsonify)

#     return(data)
