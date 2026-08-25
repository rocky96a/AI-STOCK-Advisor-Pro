# ==========================================
# Portfolio Manager
# File:
# backend/portfolio/portfolio_manager.py
# ==========================================

from backend.data.symbol_utils import normalize_symbol

from dataclasses import dataclass, asdict
from typing import List


@dataclass
class Position:
    symbol: str
    quantity: int
    entry_price: float
    current_price: float = 0.0

    @property
    def invested_value(self):
        return self.quantity * self.entry_price

    @property
    def current_value(self):
        return self.quantity * self.current_price

    @property
    def pnl(self):
        return self.current_value - self.invested_value

    @property
    def pnl_percent(self):
        if self.invested_value == 0:
            return 0.0

        return (self.pnl / self.invested_value) * 100

    def to_dict(self):
        data = asdict(self)

        data["invested_value"] = round(
            self.invested_value, 2
        )

        data["current_value"] = round(
            self.current_value, 2
        )

        data["pnl"] = round(
            self.pnl, 2
        )

        data["pnl_percent"] = round(
            self.pnl_percent, 2
        )

        # Frontend/API compatibility aliases.
        data["entry"] = round(self.entry_price, 2)
        data["current"] = round(self.current_price, 2)

        return data


class PortfolioManager:

    def __init__(self, initial_cash=0.0):

        self.cash = float(initial_cash)

        self.positions: List[Position] = []

        # Session-level equity tracking used by the risk endpoint.
        # This is intentionally in-memory; persistent portfolio storage
        # can be added later without changing the API shape.
        self.peak_equity = self.cash
        self.max_drawdown_value = 0.0
        self.max_drawdown_percent = 0.0

    # ======================================
    # Add Position
    # ======================================

    def add_position(
        self,
        symbol,
        quantity,
        entry_price
    ):

        quantity = int(quantity)
        entry_price = float(entry_price)

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than 0"
            )

        if entry_price <= 0:
            raise ValueError(
                "Entry price must be greater than 0"
            )

        required_cash = quantity * entry_price

        if required_cash > self.cash:
            raise ValueError(
                f"Insufficient cash. Required {required_cash:.2f}, "
                f"available {self.cash:.2f}"
            )

        position = Position(
            symbol=normalize_symbol(symbol),
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
        )

        self.cash -= required_cash
        self.positions.append(position)

        return position

    # ======================================
    # Update Current Price
    # ======================================

    def update_price(
        self,
        symbol,
        current_price
    ):

        symbol = normalize_symbol(symbol)
        current_price = float(current_price)

        for position in self.positions:

            if position.symbol == symbol:

                position.current_price = current_price

                return position

        return None

    # ======================================
    # Remove Position
    # ======================================

    def remove_position(self, symbol):

        symbol = normalize_symbol(symbol)
        remaining = []
        released_cash = 0.0

        for position in self.positions:
            if position.symbol == symbol:
                released_cash += position.current_value
            else:
                remaining.append(position)

        self.positions = remaining
        self.cash += released_cash
        return released_cash

    # ======================================
    # Total Invested
    # ======================================

    def total_invested(self):

        return sum(
            position.invested_value
            for position in self.positions
        )

    # ======================================
    # Current Portfolio Value
    # ======================================

    def total_value(self):
        """Total account equity = available cash + market value."""

        value = self.cash + sum(
            position.current_value
            for position in self.positions
        )

        self._update_drawdown(value)
        return value

    def _update_drawdown(self, equity):
        equity = float(equity)

        if equity > self.peak_equity:
            self.peak_equity = equity

        if self.peak_equity > 0:
            drawdown_value = max(
                0.0,
                self.peak_equity - equity,
            )
            drawdown_percent = (
                drawdown_value / self.peak_equity
            ) * 100

            self.max_drawdown_value = max(
                self.max_drawdown_value,
                drawdown_value,
            )
            self.max_drawdown_percent = max(
                self.max_drawdown_percent,
                drawdown_percent,
            )

    # ======================================
    # Total P&L
    # ======================================

    def total_pnl(self):

        return sum(
            position.pnl
            for position in self.positions
        )

    # ======================================
    # Portfolio Summary
    # ======================================

    def summary(self):

        invested = self.total_invested()
        value = self.total_value()
        pnl = self.total_pnl()

        pnl_percent = (
            (pnl / invested) * 100
            if invested > 0
            else 0.0
        )

        return {

            "total_value": round(
                value,
                2
            ),

            "invested": round(
                invested,
                2
            ),

            "available_cash": round(
                self.cash,
                2
            ),

            "total_pnl": round(
                pnl,
                2
            ),

            "pnl_percent": round(
                pnl_percent,
                2
            ),

            "open_positions": len(
                self.positions
            ),

            "peak_equity": round(
                self.peak_equity,
                2,
            ),

            "max_drawdown_value": round(
                self.max_drawdown_value,
                2,
            ),

            "max_drawdown_percent": round(
                self.max_drawdown_percent,
                2,
            ),

            "positions": [
                position.to_dict()
                for position in self.positions
            ]
        }