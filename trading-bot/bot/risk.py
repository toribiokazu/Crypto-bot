"""Risk management — the part of the bot that keeps you in the game.

Hard rules enforced here (they cannot be configured above their ceilings):

1. PER-TRADE RISK  — each trade risks a small, fixed % of the allocated
   budget (default 1.5%). Size is derived from the stop distance, so a
   wide stop automatically means a small position.
2. TOTAL OPEN RISK CAP (10%) — the sum of risk across all open positions
   can never exceed 10% of the allocated budget. New trades that would
   breach the cap are sized down or rejected.
3. KILL SWITCH (10%) — if equity drops 10% below the allocated budget,
   the bot flattens nothing on its own but refuses to open ANY new trade
   until a human resets it. Losing 10% of the budget is the worst case
   by construction.
4. NO LEVERAGE — position notional is additionally capped by available cash.
5. DAILY LOSS PAUSE — after losing daily_loss_pause_pct of the budget within
   one UTC day, no new trades until the next day. A bad day cannot snowball
   into the kill switch.
6. VOLATILITY TARGETING — when the market's ATR (as % of price) exceeds the
   target, per-trade risk scales down proportionally, the same way
   institutional desks size to a volatility budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import RiskConfig

HARD_MAX_TOTAL_RISK_PCT = 10.0
HARD_MAX_DRAWDOWN_PCT = 10.0


@dataclass
class OpenRisk:
    position_id: str
    risk_amount: float  # money lost if the stop is hit


@dataclass
class RiskManager:
    cfg: RiskConfig
    open_risks: dict[str, OpenRisk] = field(default_factory=dict)
    halted: bool = False
    halt_reason: str = ""
    day_start_equity: float | None = None
    current_day: object = None
    paused_day: object = None

    def __post_init__(self) -> None:
        # Belt and braces: even a hand-edited config cannot lift the ceilings.
        if self.cfg.max_total_risk_pct > HARD_MAX_TOTAL_RISK_PCT:
            raise ValueError("max_total_risk_pct above the 10% hard ceiling")
        if self.cfg.max_drawdown_pct > HARD_MAX_DRAWDOWN_PCT:
            raise ValueError("max_drawdown_pct above the 10% hard ceiling")

    # ------------------------------------------------------------ properties
    @property
    def budget(self) -> float:
        return self.cfg.allocated_budget

    @property
    def total_open_risk(self) -> float:
        return sum(r.risk_amount for r in self.open_risks.values())

    @property
    def max_total_risk(self) -> float:
        return self.budget * self.cfg.max_total_risk_pct / 100.0

    @property
    def equity_floor(self) -> float:
        return self.budget * (1.0 - self.cfg.max_drawdown_pct / 100.0)

    # ------------------------------------------------------------- lifecycle
    def check_kill_switch(self, equity: float) -> bool:
        """Halt all new trading if equity breaches the drawdown floor."""
        if not self.halted and equity <= self.equity_floor:
            self.halted = True
            self.halt_reason = (
                f"KILL SWITCH: equity {equity:.2f} breached floor "
                f"{self.equity_floor:.2f} ({self.cfg.max_drawdown_pct:.1f}% of "
                f"budget {self.budget:.2f}). No new trades until manual reset."
            )
        return self.halted

    def reset_halt(self) -> None:
        """Manual, deliberate reset only — never called by the bot itself."""
        self.halted = False
        self.halt_reason = ""

    def observe(self, equity: float, day) -> None:
        """Feed every equity mark with its UTC date; drives the daily pause."""
        if day != self.current_day:
            self.current_day = day
            self.day_start_equity = equity
        if (
            self.cfg.daily_loss_pause_pct is not None
            and self.paused_day != day
            and self.day_start_equity is not None
        ):
            day_loss = self.day_start_equity - equity
            if day_loss >= self.budget * self.cfg.daily_loss_pause_pct / 100.0:
                self.paused_day = day

    @property
    def paused_today(self) -> bool:
        return self.paused_day is not None and self.paused_day == self.current_day

    @property
    def can_open(self) -> bool:
        return not self.halted and not self.paused_today

    def vol_scalar(self, atr: float, price: float) -> float:
        """Risk multiplier in (0, 1]: full size at/below the vol target,
        proportionally smaller above it."""
        if self.cfg.vol_target_atr_pct is None or atr <= 0 or price <= 0:
            return 1.0
        atr_pct = atr / price * 100.0
        if atr_pct <= self.cfg.vol_target_atr_pct:
            return 1.0
        return self.cfg.vol_target_atr_pct / atr_pct

    # ---------------------------------------------------------------- sizing
    def position_size(
        self,
        position_id: str,
        entry: float,
        stop: float,
        equity: float,
        available_cash: float,
        vol_scalar: float = 1.0,
    ) -> tuple[float, float]:
        """Return (quantity, risk_amount) for a new trade, or (0, 0) if the
        trade must be rejected. Does NOT register the risk — call
        register_position after the order actually fills.
        """
        if not self.can_open:
            return 0.0, 0.0
        if len(self.open_risks) >= self.cfg.max_open_positions:
            return 0.0, 0.0
        stop_dist = abs(entry - stop)
        if stop_dist <= 0 or entry <= 0:
            return 0.0, 0.0
        # Cost-aware gate: fees+slippage are paid on the way in AND out; a
        # stop tighter than a few multiples of that cost is a losing game
        # no matter how good the signal looks.
        if self.cfg.min_stop_cost_mult is not None:
            round_trip = 2.0 * (self.cfg.fee_pct + self.cfg.slippage_pct) / 100.0
            if stop_dist / entry < self.cfg.min_stop_cost_mult * round_trip:
                return 0.0, 0.0

        risk_amount = self.budget * self.cfg.risk_per_trade_pct / 100.0
        risk_amount *= max(min(vol_scalar, 1.0), 0.0)
        # Never risk money the account no longer has.
        risk_amount = min(risk_amount, max(equity, 0.0))
        # Respect the 10% total-open-risk cap: shrink into remaining headroom.
        headroom = self.max_total_risk - self.total_open_risk
        if headroom <= 1e-9:
            return 0.0, 0.0
        risk_amount = min(risk_amount, headroom)
        # Don't bother with dust-sized trades (< 0.1% of budget of risk).
        if risk_amount < self.budget * 0.001:
            return 0.0, 0.0

        qty = risk_amount / stop_dist
        # Spot, no leverage: notional cannot exceed available cash.
        max_qty_by_cash = available_cash / entry if entry > 0 else 0.0
        if qty > max_qty_by_cash:
            qty = max_qty_by_cash
            risk_amount = qty * stop_dist
            if risk_amount < self.budget * 0.001:
                return 0.0, 0.0
        return qty, risk_amount

    # -------------------------------------------------------------- tracking
    def register_position(self, position_id: str, risk_amount: float) -> None:
        self.open_risks[position_id] = OpenRisk(position_id, risk_amount)

    def update_position_risk(self, position_id: str, entry: float, stop: float, qty: float, direction: int) -> None:
        """Recompute open risk after a stop moves (breakeven/trail => risk 0)."""
        if position_id not in self.open_risks:
            return
        adverse = (entry - stop) if direction > 0 else (stop - entry)
        self.open_risks[position_id].risk_amount = max(adverse, 0.0) * qty

    def release_position(self, position_id: str) -> None:
        self.open_risks.pop(position_id, None)
