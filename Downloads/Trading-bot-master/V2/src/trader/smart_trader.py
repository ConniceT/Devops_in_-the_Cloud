from src.analyzers.market_analyzer import MarketAnalyzer
from src.analyzers.order_flow_analyzer import OrderFlowAnalyzer
from src.managers.position_manager import PositionManager
from src.utils.helper import (
    get_last_hour_historical,
    get_current_price,
    send_notification,
    get_crypto_holdings,
    place_crypto_order,
    get_trading_action,
    process_decision,
)
from src.config.settings import Config
import time

class SmartTrader:
    def __init__(self):
        self.market_analyzer = MarketAnalyzer()
        self.order_flow_analyzer = OrderFlowAnalyzer()
        self.position_manager = PositionManager(
            stop_loss_pct=Config.STOP_LOSS_PCT,
            take_profit_pct=Config.TAKE_PROFIT_PCT,
            trailing_stop_pct=Config.TRAILING_STOP_PCT,
            use_trailing_stop=Config.USE_TRAILING_STOP
        )
        self.symbols = Config.SYMBOLS
        self.stock_symbols = Config.STOCK_SYMBOLS
        self.base_position = Config.BASE_POSITION
        self.interval = Config.CHECK_INTERVAL

    def start(self):
        while True:
            for symbol in self.symbols:
                print(f"\n🔍 Evaluating {symbol}...")

                prices = get_last_hour_historical(self.stock_symbols, symbol)
                if len(prices) < 20:
                    print("Not enough historical data.")
                    continue

                decision_map = get_trading_action(prices)
                final_decision = process_decision(decision_map)
                print(f"🧠 Decision from strategy: {final_decision.upper()}")

                current_price = get_current_price(symbol)
                self.position_manager.update_peak_price(symbol, current_price)

                if self.position_manager.should_sell(symbol, current_price):
                    quantity = get_crypto_holdings(symbol)
                    self.execute_sell(symbol, quantity, reason="Stop condition met")
                    continue

                if final_decision == "buy" and not self.position_manager.has_position(symbol):
                    quantity = self.base_position / current_price
                    self.position_manager.add_position(symbol, current_price, quantity)
                    place_crypto_order(symbol, "buy", self.base_position)
                    send_notification(f"[BUY] {symbol} at ${current_price:.2f}")

                elif final_decision == "sell" and self.position_manager.has_position(symbol):
                    quantity = get_crypto_holdings(symbol)
                    self.execute_sell(symbol, quantity, reason="Strategy signal")

            print(f"\nWaiting {self.interval} seconds...\n")
            time.sleep(self.interval)

    def execute_sell(self, symbol, quantity, reason=""):
        print(f"💰 Selling {symbol}. Reason: {reason}")
        self.position_manager.remove_position(symbol)
        place_crypto_order(symbol, "sell", quantity * get_current_price(symbol))
        send_notification(f"[SELL] {symbol} triggered by: {reason}")
