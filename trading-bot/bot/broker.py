"""Execution layer: a paper broker (backtest + paper trading) and a ccxt
broker for demo/testnet accounts. Both expose the same tiny interface so the
live loop doesn't care which one it's driving.
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass, field

log = logging.getLogger("bot.broker")

_id_counter = itertools.count(1)


@dataclass
class Position:
    id: str
    symbol: str
    direction: int  # +1 long, -1 short
    qty: float
    entry: float
    initial_stop: float
    stop: float
    best_price: float  # most favourable close since entry
    risk_amount: float
    opened_at: object = None
    reason: str = ""
    partial_done: bool = False
    realized_pnl: float = 0.0  # banked by partial exits before the final close


@dataclass
class Fill:
    price: float
    qty: float
    fee: float


class PaperBroker:
    """Simulated fills with fees and slippage. Used by the backtester and by
    paper-trading mode (live prices, fake money)."""

    def __init__(self, starting_cash: float, fee_pct: float, slippage_pct: float):
        self.cash = starting_cash
        self.fee_pct = fee_pct / 100.0
        self.slip_pct = slippage_pct / 100.0
        self.positions: dict[str, Position] = {}

    # mark-to-market equity; price is a float (single symbol) or a
    # {symbol: last_price} dict for portfolio trading
    def equity(self, price) -> float:
        eq = self.cash
        for p in self.positions.values():
            px = price[p.symbol] if isinstance(price, dict) else price
            if p.direction > 0:
                eq += p.qty * px
            else:
                eq += p.qty * (2 * p.entry - px)  # short PnL on margin-less sim
        return eq

    def open_position(
        self, symbol: str, direction: int, qty: float, price: float,
        stop: float, risk_amount: float, opened_at=None, reason: str = "",
    ) -> Position | None:
        fill_price = price * (1 + self.slip_pct * direction)
        notional = qty * fill_price
        fee = notional * self.fee_pct
        if direction > 0 and notional + fee > self.cash + 1e-9:
            qty = max((self.cash - fee) / fill_price, 0.0)
            notional = qty * fill_price
            fee = notional * self.fee_pct
        if qty <= 0:
            return None
        self.cash -= fee
        if direction > 0:
            self.cash -= notional
        else:
            self.cash -= notional  # reserve full notional as short collateral
        pos = Position(
            id=f"P{next(_id_counter)}",
            symbol=symbol, direction=direction, qty=qty, entry=fill_price,
            initial_stop=stop, stop=stop, best_price=fill_price,
            risk_amount=risk_amount, opened_at=opened_at, reason=reason,
        )
        self.positions[pos.id] = pos
        return pos

    def close_partial(self, pos_id: str, qty: float, price: float) -> Fill:
        """Sell/cover part of a position; returns the fill for that slice."""
        pos = self.positions[pos_id]
        qty = min(qty, pos.qty)
        fill_price = price * (1 - self.slip_pct * pos.direction)
        notional = qty * fill_price
        fee = notional * self.fee_pct
        if pos.direction > 0:
            self.cash += notional - fee
            pnl = (fill_price - pos.entry) * qty - fee
        else:
            entry_notional = qty * pos.entry
            pnl = (pos.entry - fill_price) * qty - fee
            self.cash += entry_notional + (entry_notional - notional) - fee
        pos.qty -= qty
        pos.realized_pnl += pnl
        return Fill(price=fill_price, qty=qty, fee=fee)

    def close_position(self, pos_id: str, price: float) -> Fill:
        pos = self.positions.pop(pos_id)
        fill_price = price * (1 - self.slip_pct * pos.direction)
        notional = pos.qty * fill_price
        fee = notional * self.fee_pct
        if pos.direction > 0:
            self.cash += notional - fee
        else:
            entry_notional = pos.qty * pos.entry
            pnl = entry_notional - notional
            self.cash += entry_notional + pnl - fee
        return Fill(price=fill_price, qty=pos.qty, fee=fee)


class CcxtBroker:
    """Thin wrapper over a ccxt exchange in sandbox/testnet mode.

    Stops are managed by the bot loop (checked every closed candle and exited
    with market orders) so behaviour matches the backtest exactly and works on
    spot testnets that lack native OCO support.
    """

    def __init__(self, exchange_id: str, api_key: str, api_secret: str, testnet: bool = True):
        import ccxt

        klass = getattr(ccxt, exchange_id)
        self.ex = klass({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
        if testnet:
            self.ex.set_sandbox_mode(True)
        self.testnet = testnet
        self.positions: dict[str, Position] = {}

    def fetch_quote_balance(self, symbol: str) -> float:
        quote = symbol.split("/")[1]
        bal = self.ex.fetch_balance()
        return float(bal.get("free", {}).get(quote, 0.0) or 0.0)

    def equity(self, price) -> float:
        eq = self.fetch_quote_balance_cached()
        for p in self.positions.values():
            px = price[p.symbol] if isinstance(price, dict) else price
            eq += p.qty * px * (1 if p.direction > 0 else 0)
        return eq

    def fetch_quote_balance_cached(self) -> float:
        # simple passthrough; kept as a hook for rate-limit-friendly caching
        return self._last_quote_balance

    _last_quote_balance: float = 0.0

    def refresh(self, symbol: str) -> None:
        self._last_quote_balance = self.fetch_quote_balance(symbol)

    def open_position(
        self, symbol: str, direction: int, qty: float, price: float,
        stop: float, risk_amount: float, opened_at=None, reason: str = "",
    ) -> Position | None:
        if direction < 0:
            log.warning("Shorts are disabled on spot exchanges; skipping signal.")
            return None
        amount = float(self.ex.amount_to_precision(symbol, qty))
        if amount <= 0:
            return None
        order = self.ex.create_market_buy_order(symbol, amount)
        fill_price = float(order.get("average") or order.get("price") or price)
        pos = Position(
            id=str(order["id"]),
            symbol=symbol, direction=direction, qty=amount, entry=fill_price,
            initial_stop=stop, stop=stop, best_price=fill_price,
            risk_amount=risk_amount, opened_at=opened_at, reason=reason,
        )
        self.positions[pos.id] = pos
        log.info("OPENED %s %s qty=%s @ %.2f stop=%.2f (%s)", symbol, "LONG", amount, fill_price, stop, reason)
        return pos

    def close_partial(self, pos_id: str, qty: float, price: float) -> Fill:
        pos = self.positions[pos_id]
        amount = float(self.ex.amount_to_precision(pos.symbol, min(qty, pos.qty)))
        if amount <= 0:
            return Fill(price=price, qty=0.0, fee=0.0)
        order = self.ex.create_market_sell_order(pos.symbol, amount)
        fill_price = float(order.get("average") or order.get("price") or price)
        pos.qty -= amount
        pos.realized_pnl += (fill_price - pos.entry) * amount
        pos.partial_done = True
        log.info("PARTIAL close %s qty=%s @ %.2f (banked %.2f)", pos.symbol, amount, fill_price, pos.realized_pnl)
        return Fill(price=fill_price, qty=amount, fee=0.0)

    def close_position(self, pos_id: str, price: float) -> Fill:
        pos = self.positions.pop(pos_id)
        order = self.ex.create_market_sell_order(pos.symbol, pos.qty)
        fill_price = float(order.get("average") or order.get("price") or price)
        log.info("CLOSED %s qty=%s @ %.2f", pos.symbol, pos.qty, fill_price)
        return Fill(price=fill_price, qty=pos.qty, fee=0.0)
