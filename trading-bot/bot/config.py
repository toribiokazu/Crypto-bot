"""Configuration loading and validation (config.yaml + .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml


@dataclass
class StrategyConfig:
    ema_fast: int = 21
    ema_slow: int = 55
    atr_period: int = 14
    rsi_period: int = 14
    swing_left: int = 3
    swing_right: int = 3
    structure_lookback: int = 120  # bars searched for swings / zones
    zone_cluster_atr_mult: float = 0.5
    zone_touch_atr_mult: float = 0.25  # how close price must come to a zone
    min_pattern_score: float = 0.45
    rsi_long_max: float = 70.0  # don't buy into overbought
    rsi_short_min: float = 30.0  # don't sell into oversold
    stop_atr_buffer: float = 0.5  # stop = pattern extreme -/+ this * ATR
    max_stop_atr_mult: float = 3.0  # skip setups with absurdly wide stops
    # --- exits: >=40% win-rate floor, tuned for max PnL ---
    # A small slice is banked at +partial_take_r (locking the trade as a
    # win), the stop jumps to breakeven, and the large remainder trails so
    # trend winners stay big. Best measured profile: ~48% win rate.
    partial_take_r: float | None = 1.0  # scale-out level in R (None = off)
    partial_take_fraction: float = 0.3  # fraction of the position banked there
    breakeven_at_r: float = 1.0  # move stop to entry at this R
    trail_atr_mult: float = 3.5  # chandelier trail (used when target_r is None)
    target_r: float | None = None  # optional runner take-profit in R
    allow_shorts: bool = False  # spot demo accounts are long-only
    cooldown_bars: int = 3  # bars to wait after closing a trade


@dataclass
class RiskConfig:
    allocated_budget: float = 1000.0  # money the bot is allowed to manage
    risk_per_trade_pct: float = 0.75  # % of budget risked on one trade
    max_total_risk_pct: float = 10.0  # hard cap: open risk never exceeds this
    max_drawdown_pct: float = 10.0  # kill switch: halt if equity falls this far
    daily_loss_pause_pct: float | None = 3.0  # pause new trades for the rest
    # of the UTC day after losing this % of budget intraday (None = off)
    vol_target_atr_pct: float | None = 0.6  # ATR as % of price at which full
    # per-trade risk is taken; risk scales DOWN linearly above it (None = off)
    min_stop_cost_mult: float | None = 5.0  # reject trades whose stop distance
    # is under this multiple of the round-trip cost (fees+slippage both ways);
    # tighter stops than this mathematically cannot be profitable (None = off)
    max_open_positions: int = 6  # one per symbol, at most this many at once
    fee_pct: float = 0.10  # taker fee per side (0.10% = Binance default)
    slippage_pct: float = 0.05


@dataclass
class ExchangeConfig:
    exchange_id: str = "binance"
    testnet: bool = True  # ALWAYS default to the demo/test environment
    symbol: str = "BTC/USDT"  # used when symbols is empty
    symbols: list[str] = field(
        default_factory=lambda: [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "LINK/USDT", "DOT/USDT",
            "LTC/USDT", "NEAR/USDT",
        ]
    )
    timeframe: str = "2h"
    api_key_env: str = "EXCHANGE_API_KEY"
    api_secret_env: str = "EXCHANGE_API_SECRET"

    @property
    def symbol_list(self) -> list[str]:
        return self.symbols or [self.symbol]


@dataclass
class BotConfig:
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)

    def validate(self) -> None:
        r = self.risk
        if not (0 < r.risk_per_trade_pct <= 5):
            raise ValueError("risk_per_trade_pct must be in (0, 5]")
        if not (0 < r.max_total_risk_pct <= 10):
            raise ValueError("max_total_risk_pct must be in (0, 10] — 10% is the hard ceiling")
        if not (0 < r.max_drawdown_pct <= 10):
            raise ValueError("max_drawdown_pct must be in (0, 10] — 10% is the hard ceiling")
        if r.risk_per_trade_pct > r.max_total_risk_pct:
            raise ValueError("risk_per_trade_pct cannot exceed max_total_risk_pct")
        if r.allocated_budget <= 0:
            raise ValueError("allocated_budget must be positive")
        if r.daily_loss_pause_pct is not None and not (
            0 < r.daily_loss_pause_pct <= r.max_drawdown_pct
        ):
            raise ValueError("daily_loss_pause_pct must be in (0, max_drawdown_pct]")
        if r.vol_target_atr_pct is not None and r.vol_target_atr_pct <= 0:
            raise ValueError("vol_target_atr_pct must be positive")
        s = self.strategy
        if s.ema_fast >= s.ema_slow:
            raise ValueError("ema_fast must be shorter than ema_slow")
        if s.partial_take_r is not None:
            if not (0 < s.partial_take_fraction < 1):
                raise ValueError("partial_take_fraction must be in (0, 1)")
            if s.partial_take_r <= 0:
                raise ValueError("partial_take_r must be positive")
            if s.target_r is not None and s.target_r <= s.partial_take_r:
                raise ValueError("target_r must be beyond partial_take_r")


def _apply(section_cls, data: dict):
    valid = {f.name for f in fields(section_cls)}
    unknown = set(data) - valid
    if unknown:
        raise ValueError(f"Unknown {section_cls.__name__} keys: {sorted(unknown)}")
    return section_cls(**data)


def load_config(path: str | Path = "config.yaml") -> BotConfig:
    p = Path(path)
    raw = {}
    if p.exists():
        raw = yaml.safe_load(p.read_text()) or {}
    cfg = BotConfig(
        strategy=_apply(StrategyConfig, raw.get("strategy", {})),
        risk=_apply(RiskConfig, raw.get("risk", {})),
        exchange=_apply(ExchangeConfig, raw.get("exchange", {})),
    )
    cfg.validate()
    return cfg


def load_api_keys(cfg: ExchangeConfig) -> tuple[str, str]:
    """Read API keys from the environment (.env is loaded by the entrypoint)."""
    key = os.environ.get(cfg.api_key_env, "")
    secret = os.environ.get(cfg.api_secret_env, "")
    if not key or not secret:
        raise RuntimeError(
            f"Missing API keys: set {cfg.api_key_env} and {cfg.api_secret_env} "
            "in your environment or .env file (use your DEMO/testnet keys)."
        )
    return key, secret
