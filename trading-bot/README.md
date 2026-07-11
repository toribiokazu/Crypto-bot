# Price-Action Crypto Trading Bot

A portfolio crypto trading bot (12 pairs, one shared budget) built around
two ideas:

1. **Price action** — trade with the trend, enter on pullbacks into
   support/EMA value zones, and only when a reversal candlestick pattern
   (engulfing, hammer/pin bar, momentum close) confirms.
2. **Risk management first** — profitability comes from asymmetry, not from
   predicting every move. Losers are cut at a fixed small loss (-1R); on
   winners the bot banks 30% of the position at +1R (locking the trade as a
   win and moving the stop to breakeven) and trails the remaining 70% with a
   3.5*ATR stop so trend winners stay big. Measured profile: ~48% win rate
   with the best PnL of every exit design tested.

## Hard risk rules (enforced in code, not just config)

| Rule | Value | What it means |
|------|-------|---------------|
| Per-trade risk | 0.75% of budget | Position size is derived from the stop distance |
| Total open risk cap | **10% of budget (hard ceiling)** | New trades are shrunk or rejected once the cap is reached |
| Kill switch | **-10% drawdown (hard ceiling)** | The bot stops opening trades entirely and requires a manual reset |
| Daily loss pause | -3% in one UTC day | No new trades until the next day — a bad day can't snowball |
| Volatility targeting | ATR ≤ 0.6% of price | Position risk scales down proportionally in hot markets |
| Cost-aware gate | stop ≥ 5x round-trip cost | Setups whose stop is tighter than 5x fees+slippage are rejected |
| No leverage | always | Notional is capped by available cash |

The two 10% ceilings are hard-coded maximums in `bot/risk.py` — the config
cannot raise them, only lower them. By construction the bot cannot lose more
than ~10% of the budget you allocate to it (plus minor fee/slippage/gap
overshoot on the final open position).

## How the strategy trades

```
TREND     EMA(21) vs EMA(55) alignment + swing structure (HH/HL) must agree
LOCATION  pullback into the fast EMA or a confirmed support zone
TRIGGER   bullish reversal pattern completes there, RSI not overbought
STOP      below the pattern low minus 0.5*ATR (wide stops = skipped setup)
EXIT      scale-out: bank 30% at +1R and move the stop to breakeven,
          then the 70% runner trails a 3.5*ATR stop until caught
```

Shorts are the mirror image and disabled by default (spot demo accounts are
long-only). All decisions use **closed candles only** — the backtester and
the live loop share the same logic, and a no-lookahead test guards this.

## Quick start

```bash
cd trading-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. sanity-check offline (no network needed)
python run_backtest.py --synthetic --seed 123 --trades

# 2. backtest on real BTC history (public data, no keys needed)
python run_backtest.py --fetch --limit 3000

# 3. paper trade: live prices, simulated fills, no keys needed
python run_live.py --mode paper

# 4. demo trade on the exchange testnet (see below)
python run_live.py --mode demo
```

## Setting up your demo account

The bot is **demo-first**: `run_live.py --mode demo` refuses to start unless
`exchange.testnet: true` in `config.yaml`.

**Binance testnet (recommended):**
1. Go to https://testnet.binance.vision and log in with GitHub.
2. Generate an API key/secret — the testnet gives you free fake balances.
3. `cp .env.example .env` and paste the keys in.
4. `python run_live.py --mode demo`

**Bybit demo:** create demo API keys at testnet.bybit.com and set
`exchange_id: bybit` in `config.yaml`.

**MEXC (and other ccxt exchanges):** supported for live/paper trading via
`exchange_id: mexc`, and its low spot fees (advertised 0% maker / 0.05%
taker — verify on their fee page) are genuinely attractive: fees are this
system's biggest cost. **But MEXC has no testnet**, so the demo phase can't
happen there. Sensible path: validate on the Binance testnet (the algorithm
is identical), optionally paper-trade against live MEXC prices
(`--mode paper` needs no keys), and only consider MEXC for the eventual
real-money stage — weighing that its regulatory standing and alt-pair
liquidity are a step below the top-tier venues. If you go that way, set
`fee_pct: 0.05` so the simulations model reality.

The bot logs every decision to `bot.log` and keeps its state (equity, open
positions, kill-switch status) in `state.json`.

## Starting with $90–100

Use the ready-made small-account profile:

```bash
python run_live.py --mode demo --config config.small.yaml
```

Decisions baked into it (see the comments in `config.small.yaml`):
- **$1 risk per trade** (1%), max **2 concurrent positions** — that's what
  $100 of unleveraged cash can genuinely fund while keeping every order
  and partial exit above the exchange's ~$5 minimum order size.
- The bot still **scans all 12 pairs** and takes the best 2 setups.
- **4h chart, ~3 trades/week, stricter pattern filter (0.60)** — we raced
  ~6/week (2h), ~3/week (4h) and ~1/week (ultra-selective) head-to-head:
  3/week nearly doubled the expectancy of 6/week (+1.65% vs +0.98% per
  30 days) with a milder worst case, because the marginal daily trades
  were only feeding fees.
- Dollar risk rails: lose **$3 in a day** → paused until tomorrow; lose
  **$10 total** → kill switch, manual reset required.
- **16 pairs scanned** (widened from 12 — measured +0.5%/30d for free) and
  the config points out the BNB fee discount, worth another ~+0.1%/30d.
- Measured in portfolio sims (8 regime sets): ~48% win rate, ~3
  trades/week, +2.3%/30d mean, worst regime -3.8%, zero kill-switch hits.

Be realistic about the goal at this size: with a ~$100 budget the expected
profit is on the order of **a few dollars a month** — this stage is about
proving the system works live with capped risk, not about income. If the
demo (and later a small real run) stays green for months, the same
percentages scale with the budget.

## Weekly review workflow

The live loop journals every completed trade to `trades_demo.csv` /
`trades_paper.csv` (entry, exit, PnL, R-multiple, exit reason, signal that
triggered it). Weekly routine:

```bash
python run_report.py         # local summary + mechanical warnings + verdict
git add trades_*.csv && git commit -m "journal week N" && git push
```

Pushing the journal lets the maintainer (or Claude) analyze the data and
tune the algorithm. Two rules the review follows:

1. **Mechanical issues get fixed at any sample size** — stops slipping past
   -1.25R, losses averaging worse than -1R, trade frequency far off
   projection. These mean the execution doesn't match the model.
2. **Strategy parameters are only retuned on 30+ trades of evidence.**
   Re-fitting the algorithm to one week (~3 trades) of results is
   curve-fitting to noise and makes bots worse, not better. The report's
   verdict enforces this distinction explicitly.

## Recommended evaluation process

1. **Backtest** on 2–3 years of real 4h candles (`--fetch --limit 5000`).
   Look at profit factor, expectancy per trade, and max drawdown — not just
   the total return.
2. **Paper trade** for a couple of weeks. Confirm live behaviour matches the
   backtest.
3. **Demo trade** on the testnet for at least 1–3 months / 30+ trades.
   A handful of trades proves nothing either way.
4. Only after all of that, decide about real funds — and if you ever go
   there, start with a small budget and keep `testnet: true` until the
   moment you consciously flip it.

## What results to expect

Portfolio backtests (12 simulated pairs x 2000 2h candles, 5 independent
seed-sets) with default settings:

- ~1.4 trades/day on average across the portfolio (0.7–1.8 by regime)
- Win rate ~52% on average
- Mean return ≈ +1.7% per 30 days; best regimes +16 to +27% over ~6 months
- Worst regime -10.5%, stopped by the kill switch — the hard floor held

## Why not more trades per day?

We measured it: frequency and profit pull in opposite directions at retail
fees. On 15m candles the same strategy traded more but lost ~10%/month with
EVERY run hitting the kill switch, because a 15m stop (~0.5% wide) barely
exceeds the ~0.3% round-trip cost of fees+slippage. Institutions trade fast
because they pay maker rebates (≈0 or negative fees); retail accounts pay
0.1% taker per side, so the viable path to more trades is more pairs on a
slower chart — that's what the 12-pair portfolio does. If you push
`timeframe` below 1h anyway, the cost gate will start rejecting most
setups — that's the math protecting you, not a bug. Fee reductions (BNB
discount, VIP tiers) directly improve every number above.

## Honest disclaimers

- **No bot can predict the market.** This one doesn't try to; it reacts to
  structure and manages risk. Forecasting in this codebase means "identify
  the trend and assume it's more likely to continue than reverse."
- Backtest results (especially on synthetic data) do not guarantee future
  performance. Real edge can only be judged on real data over many trades.
- Crypto is volatile and you can lose money. Never allocate funds you cannot
  afford to lose, even with the 10% cap.

## Project layout

```
bot/
  indicators.py   EMA, ATR, RSI, swing detection (lookahead-safe)
  patterns.py     candlestick pattern recognition with conviction scores
  structure.py    trend classification + support/resistance zones
  strategy.py     the trading playbook (signals + trailing-stop management)
  risk.py         position sizing, 10% cap, kill switch  <- the important file
  broker.py       PaperBroker (sim) and CcxtBroker (testnet/demo)
  backtest.py     event-driven backtester with fees/slippage + metrics
  live.py         live loop: paper/demo trading on closed candles
  data.py         ccxt fetch, CSV loader, synthetic market generator
run_backtest.py   backtesting CLI
run_live.py       paper/demo trading CLI
config.yaml       all knobs, documented
tests/            20 tests incl. risk caps, kill switch, no-lookahead
```
