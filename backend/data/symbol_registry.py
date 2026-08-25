"""
Indian stock symbol registry.

Separates the logical stock identity from provider-specific symbols.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SymbolRecord:
    symbol: str

    yahoo_nse: Optional[str] = None
    yahoo_bse: Optional[str] = None

    name: Optional[str] = None

    active: bool = True

    providers: dict = field(default_factory=dict)


class SymbolRegistry:

    def __init__(self):
        self._symbols = {}

    def register(
        self,
        symbol,
        yahoo_nse=None,
        yahoo_bse=None,
        name=None,
        active=True,
        providers=None,
    ):
        symbol = str(symbol).strip().upper()

        if not symbol:
            return

        self._symbols[symbol] = SymbolRecord(
            symbol=symbol,
            yahoo_nse=yahoo_nse,
            yahoo_bse=yahoo_bse,
            name=name,
            active=active,
            providers=providers or {},
        )

    def get(self, symbol):
        symbol = str(symbol).strip().upper()
        return self._symbols.get(symbol)

    def exists(self, symbol):
        return self.get(symbol) is not None

    def all(self):
        return list(self._symbols.values())

    def active_symbols(self):
        return [
            record.symbol
            for record in self._symbols.values()
            if record.active
        ]

    def yahoo_symbol(self, symbol):
        record = self.get(symbol)

        if record is None:
            return None

        return record.yahoo_nse

    def mark_provider_unavailable(
        self,
        symbol,
        provider,
    ):
        record = self.get(symbol)

        if record is None:
            return

        record.providers[provider] = {
            "available": False,
        }

    def mark_provider_available(
        self,
        symbol,
        provider,
    ):
        record = self.get(symbol)

        if record is None:
            return

        record.providers[provider] = {
            "available": True,
        }