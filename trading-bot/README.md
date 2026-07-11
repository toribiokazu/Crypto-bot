# Price-Action Crypto Trading Bot

A crypto trading bot built around two ideas:

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
| Per-trade risk | 1.5% of budget | Position size is derived from the stop distance |
| Total open risk cap | **10% of budget (hard ceiling)** | New trades are shrunk or rejected once the cap is reached |
| Kill switch | **-10% drawdown (hard ceiling)** | The bot stops opening trades entirely and requires a manual reset |
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

The bot logs every decision to `bot.log` and keeps its state (equity, open
positions, kill-switch status) in `state.json`.

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

Sample backtests across 10 simulated market regimes (3000 x 4h candles each)
with default settings:

- Win rate: ~48% on average (regime-dependent; the floor requirement is 40%)
- Mean return +4.6%, median +3.1% — the best PnL of ~24 exit designs swept,
  beating both the full +2R-target profile (~36% win rate) and every
  higher-win-rate variant (banking more/earlier raises win rate but caps
  the winners that pay for the losses)
- Losing (choppy) regimes: capped at ~-10 to -11% by the kill switch

The exit design is the dial: bank earlier/more = higher win rate, lower
PnL. Bank later/less = lower win rate, higher PnL. The default sits at the
measured sweet spot that respects the 40% win-rate floor.

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
