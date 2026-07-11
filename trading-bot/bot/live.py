"""Live trading loop for DEMO/testnet (and paper) trading.

The loop mirrors the portfolio backtester: it acts only on CLOSED candles
across every configured symbol, manages stops bot-side, and lets the shared
RiskManager (10% cap, 10% kill switch, daily loss pause, vol targeting) veto
every entry. Run it against a demo account until the equity curve earns your
trust.

Modes:
  paper — live market data, simulated fills (no keys needed)
  demo  — real orders on the exchange's testnet/demo environment (demo keys)
"""

from __future__ import annotations

import csv
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .broker import CcxtBroker, PaperBroker
from .config import BotConfig, load_api_keys
from .data import fetch_ohlcv
from .indicators import add_indicators
from .risk import RiskManager
from .strategy import PriceActionStrategy

log = logging.getLogger("bot.live")

TIMEFRAME_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "1d": 86400,
}


class LiveTrader:
    def __init__(self, cfg: BotConfig, mode: str = "paper", state_path: str = "state.json"):
        if mode not in ("paper", "demo"):
            raise ValueError("mode must be 'paper' or 'demo'")
        self.cfg = cfg
        self.mode = mode
        self.symbols = cfg.exchange.symbol_list
        self.state_path = Path(state_path)
        self.journal_path = Path(f"trades_{mode}.csv")
        self.strategy = PriceActionStrategy(cfg.strategy)
        self.risk = RiskManager(cfg.risk)
        self.last_marks: dict[str, float] = {}

        if mode == "paper":
            self.broker = PaperBroker(
                cfg.risk.allocated_budget, cfg.risk.fee_pct, cfg.risk.slippage_pct
            )
        else:
            key, secret = load_api_keys(cfg.exchange)
            self.broker = CcxtBroker(
                cfg.exchange.exchange_id, key, secret, testnet=cfg.exchange.testnet
            )
            if not cfg.exchange.testnet:
                raise RuntimeError(
                    "Refusing to start: exchange.testnet is false. This bot is "
                    "demo-first — flip it back to true, or edit this guard only "
                    "after the demo period has proven the system."
                )
            self.broker.refresh(self.symbols[0])

        self._load_state()

    # ----------------------------------------------------------------- state
    def _load_state(self) -> None:
        if self.state_path.exists():
            st = json.loads(self.state_path.read_text())
            self.risk.halted = st.get("halted", False)
            self.risk.halt_reason = st.get("halt_reason", "")
            if self.risk.halted:
                log.warning("Loaded HALTED state: %s", self.risk.halt_reason)

    def _save_state(self, equity: float) -> None:
        self.state_path.write_text(
            json.dumps(
                {
                    "updated": datetime.now(timezone.utc).isoformat(),
                    "mode": self.mode,
                    "equity": equity,
                    "halted": self.risk.halted,
                    "halt_reason": self.risk.halt_reason,
                    "paused_today": self.risk.paused_today,
                    "open_positions": [
                        {
                            "id": p.id, "symbol": p.symbol, "direction": p.direction,
                            "qty": p.qty, "entry": p.entry, "stop": p.stop,
                            "reason": p.reason, "partial_done": p.partial_done,
                            "realized_pnl": p.realized_pnl,
                        }
                        for p in self.broker.positions.values()
                    ],
                },
                indent=2,
            )
        )

    # --------------------------------------------------------------- journal
    JOURNAL_COLUMNS = [
        "closed_at_utc", "mode", "symbol", "direction", "qty", "entry", "exit",
        "pnl", "r_multiple", "exit_reason", "entry_reason", "opened_at",
    ]

    def _journal(self, pos, fill, exit_reason: str) -> None:
        """Append the completed trade to the CSV journal — this file is the
        raw material for the weekly performance review."""
        if pos.direction > 0:
            pnl = (fill.price - pos.entry) * fill.qty - fill.fee
        else:
            pnl = (pos.entry - fill.price) * fill.qty - fill.fee
        pnl += pos.realized_pnl
        r = pnl / pos.risk_amount if pos.risk_amount > 0 else 0.0
        new_file = not self.journal_path.exists()
        with self.journal_path.open("a", newline="") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(self.JOURNAL_COLUMNS)
            w.writerow([
                datetime.now(timezone.utc).isoformat(), self.mode, pos.symbol,
                "long" if pos.direction > 0 else "short",
                f"{fill.qty:.8f}", f"{pos.entry:.8f}", f"{fill.price:.8f}",
                f"{pnl:.4f}", f"{r:.3f}", exit_reason, pos.reason, pos.opened_at,
            ])

    # ------------------------------------------------------------------ data
    def _fetch(self, symbol: str) -> pd.DataFrame:
        ex = self.cfg.exchange
        need = self.cfg.strategy.structure_lookback + self.cfg.strategy.ema_slow + 50
        # Paper mode always reads REAL market data — that's the point of
        # paper trading — and it keeps working on exchanges with no testnet
        # (e.g. MEXC). Only demo order flow goes to the sandbox.
        use_testnet = ex.testnet and self.mode == "demo"
        return fetch_ohlcv(
            ex.exchange_id, symbol, ex.timeframe, limit=need, testnet=use_testnet
        )

    def _positions_for(self, symbol: str):
        return [p for p in self.broker.positions.values() if p.symbol == symbol]

    # ------------------------------------------------------------------ tick
    def on_candle_close(self) -> None:
        """Run one decision cycle over every symbol's latest CLOSED candle."""
        scfg = self.cfg.strategy
        if self.mode == "demo":
            self.broker.refresh(self.symbols[0])

        enriched: dict[str, pd.DataFrame] = {}
        for symbol in self.symbols:
            try:
                raw = self._fetch(symbol)
            except Exception:
                log.exception("Fetch failed for %s; skipping this cycle", symbol)
                continue
            if len(raw) < scfg.ema_slow + 10:
                log.warning("Not enough candles yet for %s (%d)", symbol, len(raw))
                continue
            data = add_indicators(raw.iloc[:-1], scfg)  # closed bars only
            enriched[symbol] = data
            self.last_marks[symbol] = float(data["close"].iat[-1])

        # 1) manage open positions: stop, scale-out, runner target, trailing
        for symbol, data in enriched.items():
            i = len(data) - 1
            price = float(data["close"].iat[i])
            a = float(data["atr"].iat[i])
            bar_high = float(data["high"].iat[i])
            bar_low = float(data["low"].iat[i])

            for pos in self._positions_for(symbol):
                hit = (pos.direction > 0 and bar_low <= pos.stop) or (
                    pos.direction < 0 and bar_high >= pos.stop
                )
                if hit:
                    fill = self.broker.close_position(pos.id, price)
                    self.risk.release_position(pos.id)
                    self._journal(pos, fill, "stop")
                    log.info("Stop hit -> closed %s %s", symbol, pos.id)
                    continue

                r_dist = abs(pos.entry - pos.initial_stop)
                favourable = bar_high if pos.direction > 0 else bar_low

                if scfg.partial_take_r and not pos.partial_done:
                    level = pos.entry + pos.direction * scfg.partial_take_r * r_dist
                    reached = favourable >= level if pos.direction > 0 else favourable <= level
                    if reached:
                        from .backtest import _partial_slice

                        slice_qty = _partial_slice(
                            pos.qty, scfg.partial_take_fraction, price,
                            self.cfg.risk.min_order_notional,
                        )
                        if slice_qty > 0:
                            self.broker.close_partial(pos.id, slice_qty, price)
                        pos.partial_done = True
                        pos.stop = max(pos.stop, pos.entry) if pos.direction > 0 else min(pos.stop, pos.entry)
                        self.risk.update_position_risk(pos.id, pos.entry, pos.stop, pos.qty, pos.direction)
                        log.info("Banked %.0f%% of %s at +%.1fR; stop -> breakeven",
                                 scfg.partial_take_fraction * 100, pos.id, scfg.partial_take_r)

                if scfg.target_r:
                    target = pos.entry + pos.direction * scfg.target_r * r_dist
                    reached = favourable >= target if pos.direction > 0 else favourable <= target
                    if reached:
                        fill = self.broker.close_position(pos.id, price)
                        self.risk.release_position(pos.id)
                        self._journal(pos, fill, "target")
                        log.info("Runner target +%.1fR hit -> closed %s %s", scfg.target_r, symbol, pos.id)
                        continue

                pos.best_price = (
                    max(pos.best_price, price) if pos.direction > 0 else min(pos.best_price, price)
                )
                new_stop = self.strategy.manage_stop(
                    pos.direction, pos.entry, pos.initial_stop, pos.stop, pos.best_price, a
                )
                if new_stop != pos.stop:
                    log.info("Trail %s %s stop %.2f -> %.2f", symbol, pos.id, pos.stop, new_stop)
                    pos.stop = new_stop
                    self.risk.update_position_risk(pos.id, pos.entry, pos.stop, pos.qty, pos.direction)

        # 2) portfolio equity, kill switch, daily pause
        equity = self.broker.equity(self.last_marks)
        killed = self.risk.check_kill_switch(equity)
        self.risk.observe(equity, datetime.now(timezone.utc).date())
        if killed:
            log.error(self.risk.halt_reason)
            self._save_state(equity)
            return
        if self.risk.paused_today:
            log.warning("Daily loss pause active — no new trades until tomorrow (UTC).")

        # 3) new setups, one position per symbol
        if self.risk.can_open:
            for symbol, data in enriched.items():
                if self._positions_for(symbol):
                    continue
                i = len(data) - 1
                sig = self.strategy.evaluate(data, i)
                if sig is None:
                    continue
                price = float(data["close"].iat[i])
                a = float(data["atr"].iat[i])
                cash = (
                    self.broker.cash
                    if self.mode == "paper"
                    else self.broker.fetch_quote_balance(symbol)
                )
                vs = self.risk.vol_scalar(a, price)
                qty, risk_amt = self.risk.position_size(
                    "new", price, sig.stop, equity, cash, vol_scalar=vs
                )
                if qty > 0:
                    pos = self.broker.open_position(
                        symbol=symbol, direction=sig.direction,
                        qty=qty, price=price, stop=sig.stop, risk_amount=risk_amt,
                        opened_at=datetime.now(timezone.utc).isoformat(), reason=sig.reason,
                    )
                    if pos is not None:
                        self.risk.register_position(pos.id, risk_amt)
                        log.info("ENTRY %s %s: %s (vol scalar %.2f)", symbol, pos.id, sig.reason, vs)
                else:
                    log.info("%s signal sized to zero by risk manager: %s", symbol, sig.reason)

        self._save_state(equity)
        log.info(
            "equity=%.2f mode=%s open=%d halted=%s paused=%s",
            equity, self.mode, len(self.broker.positions), self.risk.halted,
            self.risk.paused_today,
        )

    # ------------------------------------------------------------------ loop
    def run_forever(self) -> None:
        tf_s = TIMEFRAME_SECONDS[self.cfg.exchange.timeframe]
        log.info(
            "Starting %s trading: %s %s on %s (testnet=%s). Budget=%.2f, "
            "risk/trade=%.2f%%, total-risk cap=%.1f%%, kill switch at -%.1f%%, "
            "daily pause at -%s%%.",
            self.mode, ", ".join(self.symbols), self.cfg.exchange.timeframe,
            self.cfg.exchange.exchange_id, self.cfg.exchange.testnet,
            self.cfg.risk.allocated_budget, self.cfg.risk.risk_per_trade_pct,
            self.cfg.risk.max_total_risk_pct, self.cfg.risk.max_drawdown_pct,
            self.cfg.risk.daily_loss_pause_pct,
        )
        while True:
            try:
                self.on_candle_close()
            except Exception:  # noqa: BLE001 — a bad tick must not kill the loop
                log.exception("Cycle failed; will retry next candle")
            now = time.time()
            sleep_s = tf_s - (now % tf_s) + 5  # wake shortly after each close
            log.info("Sleeping %.0fs until next %s candle", sleep_s, self.cfg.exchange.timeframe)
            time.sleep(sleep_s)
