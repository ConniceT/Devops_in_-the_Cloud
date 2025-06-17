from typing import Dict
from datetime import datetime
from .utils.helper import place_crypto_order, send_notification
from .utils.config import MAX_TRADE_RETRY, TRADE_RETRY_DELAY, PROFIT_TAKE_PERCENT, STOP_LOSS_PERCENT, USE_TRAILING_STOP, TRAILING_STOP_PERCENT

class TradeExecutor:
    def __init__(self):
        self.positions: Dict[str, Dict] = {}  # Active trades: {symbol: {entry_price, quantity, highest_price, ...}}
        self.use_trailing_stop = USE_TRAILING_STOP
        self.trailing_stop_pct = TRAILING_STOP_PERCENT / 100

    def execute_buy(self, symbol: str, quantity: float, price: float, reason: str):
        print(f"[BUY] {symbol} @ ${price:.2f} | Qty: {quantity:.4f} | Reason: {reason}")
        response = place_crypto_order(symbol, "buy", buying_or_selling_price=quantity * price)
        send_notification(f"[BUY] {symbol} @ ${price:.2f}\nReason: {reason}")
        if response:
            self.positions[symbol] = {
                'entry_price': price,
                'quantity': quantity,
                'timestamp': datetime.now(),
                'highest_price': price
            }

    def execute_sell(self, symbol: str, quantity: float, reason: str):
        if symbol not in self.positions:
            print(f"[WARN] Tried to sell {symbol} but not in positions")
            return

        price = self.positions[symbol]['entry_price']
        print(f"[SELL] {symbol} @ approx ${price:.2f} | Qty: {quantity:.4f} | Reason: {reason}")
        response = place_crypto_order(symbol, "sell", buying_or_selling_price=quantity * price)
        send_notification(f"[SELL] {symbol} @ approx ${price:.2f}\nReason: {reason}")
        if response:
            del self.positions[symbol]

    def check_position(self, symbol: str, current_price: float):
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        entry_price = position['entry_price']
        quantity = position['quantity']

        # Take profit
        if current_price >= entry_price * (1 + PROFIT_TAKE_PERCENT / 100):
            self.execute_sell(symbol, quantity, reason="Profit target hit")
            return

        # Stop loss
        if current_price <= entry_price * (1 - STOP_LOSS_PERCENT / 100):
            self.execute_sell(symbol, quantity, reason="Stop loss triggered")
            return

        # Update highest price for trailing stop
        if current_price > position['highest_price']:
            position['highest_price'] = current_price

        # Check trailing stop
        if self.use_trailing_stop and current_price <= position['highest_price'] * (1 - self.trailing_stop_pct):
            self.execute_sell(symbol, quantity, reason="Trailing stop triggered")
