# Continuous paper research loop — 0.3.0

The worker now scans actual BTC/USDT, ETH/USDT and SOL/USDT public spot data continuously, evaluates completed 1m candles approximately every minute, records LONG/SHORT/WAIT observations, and automatically submits eligible LONG paper proposals to the independent governor. SHORT observations remain WAIT for execution: futures and short accounting are not implemented.

This is an **experimental paper research trial**, not a promoted profitable strategy. There is no calibrated confidence, LLM order authority, uncontrolled strategy mutation, or daily income guarantee. The earlier research-only baseline was not promoted. The new breakout candidate is a separately versioned paper experiment to collect forward execution/outcome evidence.

A 10/30-bar trend agreement, completed 20-bar breakout, observed movement greater than twice modeled costs, spread envelope and volatility envelope control eligibility. Stop distance uses 14-bar ranges with a minimum 0.5% distance and maximum 3%. These rules are hypotheses, not demonstrated predictive edges. The scanner can legitimately return WAIT for long periods.

Each entry is capped at $10 simulated notional and remaining exposure, cash and trade-loss limits. Sizing never references the $25 aspirational target. The governor applies owner loss, drawdown, exposure, position, spread, cooldown, stale-data and rate limits. Paused/emergency modes keep observing but veto new positions. No withdrawal or live-order API is called.

Account row locks serialize decisions with manual orders. A deterministic owner/symbol/version/candle decision key persists each processed bar; unique order client IDs and fingerprints reject duplicate execution. Decisions, proposals, approvals/vetoes, fills and portfolio events are committed together. A rejected proposal retains its decision/veto audit.

Every worker pass checks fresh bid prices for stops and targets. Automatic entries also have a 15-minute maximum hold; exits remain active while paused/emergency stopped and use reduce-only simulated sells. Outcome records contain gross-minus-entry-and-exit-fee P&L for the remaining closed position, cause, holding duration and entry/exit order references. Manual partial closes remain in the existing fill ledger. Protective exits are backend simulation, not native exchange orders; stale feeds prevent fills and gaps can exceed intended losses.

## Evidence and limitations

- Local test run: 54 passed, two PostgreSQL-only tests skipped locally. GitHub CI run 38211288952 passed all 56 tests, PostgreSQL migration/concurrency validation, dependency scanning and secret scanning.
- Synthetic fixtures exercise automatic entry, subsequent real-time-style TP close, repeat-bar/restart duplicate prevention, paused/emergency veto, maximum-hold close, fee accounting, stale exits and historical chronology/cost behavior. Synthetic gains are not strategy results.
- An isolated background worker process fetched actual quotes/candles for all three symbols and persisted three decisions with zero market/research errors (`autonomous-worker-smoke.json`).
- Railway API and worker deployments reached SUCCESS; public HTTPS reports API 0.3.0, autonomous paper enabled, worker online and paper-breakout-trial-v1 heartbeat (`AUTONOMOUS-DEPLOYMENT.json`).
- Real Bitget BTC/ETH/SOL observations are in `autonomous-public-observation.json`. The sampled market produced WAIT; no live orders or forced paper entries were placed.
- `autonomous-historical-replay.json` retains 999 real completed BTC 1m candles and chronological holdout summaries. This narrow sample produced zero closed trades and zero P&L. It establishes neither profitability nor validation; no model was promoted.
- Reproduce the recorded replay with `python -m research.trial docs/autonomous-historical-replay.json`. Modeled fees are 10 bps per side, slippage 10 bps per side, spread 2 bps. Actual historical bid/ask and fills were unavailable; OHLC replay conservatively chooses a stop when both exits could be touched.
- Full futures LONG/SHORT, margin/leverage, private execution streams, native exchange protective orders, exchange position reconciliation, broader strategy selection, validated learning and release signing remain unfinished. Live activation still returns HTTP 409.

The existing Android APK reads the same snapshot/events contract and displays decisions, positions, outcomes and pause/resume controls; this backend release requires no APK installation change. Select Paper/resume to allow experiments; Pause blocks new entries. $200 is explicitly simulated capital, separate from any exchange balance.
