"""Live trading loop for DEMO/testnet (and paper) trading.

The loop mirrors the backtester exactly: it acts only on CLOSED candles,
manages stops bot-side, and lets the RiskManager veto every entry. Run it
against a demo account until the equity curve earns your trust.

Modes:
  paper — live market data, simulated fills (no keys needed)
  demo  — real orders on the exchange's testnet/demo environment (demo keys)
"""

from __future__ import annotations

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
        self.state_path = Path(state_path)
        self.strategy = PriceActionStrategy(cfg.strategy)
        self.risk = RiskManager(cfg.risk)

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
            self.broker.refresh(cfg.exchange.symbol)

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
                    "open_positions": [
                        {
                            "id": p.id, "direction": p.direction, "qty": p.qty,
                            "entry": p.entry, "stop": p.stop, "reason": p.reason,
                        }
                        for p in self.broker.positions.values()
                    ],
                },
                indent=2,
            )
        )

    # ------------------------------------------------------------------ data
    def _fetch(self) -> pd.DataFrame:
        ex = self.cfg.exchange
        need = self.cfg.strategy.structure_lookback + self.cfg.strategy.ema_slow + 50
        return fetch_ohlcv(
            ex.exchange_id, ex.symbol, ex.timeframe, limit=need, testnet=ex.testnet
        )

    # ------------------------------------------------------------------ tick
    def on_candle_close(self) -> None:
        """Run one decision cycle on the latest CLOSED candle."""
        raw = self._fetch()
        if len(raw) < self.cfg.strategy.ema_slow + 10:
            log.warning("Not enough candles yet (%d)", len(raw))
            return
        # Drop the still-forming candle: we only trade closed bars.
        raw = raw.iloc[:-1]
        data = add_indicators(raw, self.cfg.strategy)
        i = len(data) - 1
        price = float(data["close"].iat[i])
        a = float(data["atr"].iat[i])

        if self.mode == "demo":
            self.broker.refresh(self.cfg.exchange.symbol)

        # 1) manage open positions: stop hits and trailing
        for pos in list(self.broker.positions.values()):
            hit = (pos.direction > 0 and float(data["low"].iat[i]) <= pos.stop) or (
                pos.direction < 0 and float(data["high"].iat[i]) >= pos.stop
            )
            if hit:
                self.broker.close_position(pos.id, price)
                self.risk.release_position(pos.id)
                log.info("Stop hit -> closed %s", pos.id)
                continue
            pos.best_price = (
                max(pos.best_price, price) if pos.direction > 0 else min(pos.best_price, price)
            )
            new_stop = self.strategy.manage_stop(
                pos.direction, pos.entry, pos.initial_stop, pos.stop, pos.best_price, a
            )
            if new_stop != pos.stop:
                log.info("Trail %s stop %.2f -> %.2f", pos.id, pos.stop, new_stop)
                pos.stop = new_stop
                self.risk.update_position_risk(pos.id, pos.entry, pos.stop, pos.qty, pos.direction)

        # 2) equity + kill switch
        equity = self.broker.equity(price)
        if self.risk.check_kill_switch(equity):
            log.error(self.risk.halt_reason)
            self._save_state(equity)
            return

        # 3) new setups (one position at a time keeps demo results readable)
        if not self.broker.positions:
            sig = self.strategy.evaluate(data, i)
            if sig is not None:
                cash = (
                    self.broker.cash
                    if self.mode == "paper"
                    else self.broker.fetch_quote_balance(self.cfg.exchange.symbol)
                )
                qty, risk_amt = self.risk.position_size("new", price, sig.stop, equity, cash)
                if qty > 0:
                    pos = self.broker.open_position(
                        symbol=self.cfg.exchange.symbol, direction=sig.direction,
                        qty=qty, price=price, stop=sig.stop, risk_amount=risk_amt,
                        opened_at=datetime.now(timezone.utc).isoformat(), reason=sig.reason,
                    )
                    if pos is not None:
                        self.risk.register_position(pos.id, risk_amt)
                        log.info("ENTRY %s: %s", pos.id, sig.reason)
                else:
                    log.info("Signal found but risk manager sized it to zero: %s", sig.reason)

        self._save_state(equity)
        log.info(
            "equity=%.2f cash-mode=%s open=%d halted=%s",
            equity, self.mode, len(self.broker.positions), self.risk.halted,
        )

    # ------------------------------------------------------------------ loop
    def run_forever(self) -> None:
        tf_s = TIMEFRAME_SECONDS[self.cfg.exchange.timeframe]
        log.info(
            "Starting %s trading: %s %s on %s (testnet=%s). Budget=%.2f, "
            "risk/trade=%.2f%%, total-risk cap=%.1f%%, kill switch at -%.1f%%.",
            self.mode, self.cfg.exchange.symbol, self.cfg.exchange.timeframe,
            self.cfg.exchange.exchange_id, self.cfg.exchange.testnet,
            self.cfg.risk.allocated_budget, self.cfg.risk.risk_per_trade_pct,
            self.cfg.risk.max_total_risk_pct, self.cfg.risk.max_drawdown_pct,
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
