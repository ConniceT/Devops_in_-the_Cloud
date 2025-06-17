from datetime import datetime
from typing import Dict


class PositionManager:
    def __init__(self):
        self.positions: Dict[str, Dict] = {}

    def add_position(self, symbol: str, quantity: float, price: float):
        self.positions[symbol] = {
            "entry_price": price,
            "quantity": quantity,
            "entry_time": datetime.now(),
            "highest_price": price
        }

    def update_highest_price(self, symbol: str, current_price: float):
        if symbol in self.positions and current_price > self.positions[symbol]["highest_price"]:
            self.positions[symbol]["highest_price"] = current_price

    def should_take_profit(self, symbol: str, current_price: float, profit_threshold: float) -> bool:
        entry_price = self.positions[symbol]["entry_price"]
        return current_price >= entry_price * (1 + profit_threshold)

    def should_stop_loss(self, symbol: str, current_price: float, stop_loss_threshold: float) -> bool:
        entry_price = self.positions[symbol]["entry_price"]
        return current_price <= entry_price * (1 - stop_loss_threshold)

    def should_trigger_trailing_stop(self, symbol: str, current_price: float, trailing_stop_pct: float) -> bool:
        highest_price = self.positions[symbol]["highest_price"]
        return current_price <= highest_price * (1 - trailing_stop_pct)

    def remove_position(self, symbol: str):
        if symbol in self.positions:
            del self.positions[symbol]

    def get_position(self, symbol: str):
        return self.positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions

    def update_quantity(self, symbol: str, new_quantity: float):
        if symbol in self.positions:
            self.positions[symbol]["quantity"] = new_quantity
