# ZEN 0.8.0 — active research and forward paper recovery

## What changed

- Futures candle batches increased from 12 to 24, with bounded concurrency. Priority uses 24-hour range among liquid, tight-spread, fresh, API-eligible markets, while rotating the eligible catalogue. Open exposures and pending shadow trials receive priority. It is not limited to BTC/ETH/SOL, but not every listed contract passes tradability/liquidity checks.
- Automatic paper leverage now fits the proposed stop distance, maintenance margin, initial-margin requirement and cost buffer, within the configured and discovered ceilings. Previously, always requesting the ceiling could make otherwise usable hypotheses fail liquidation checks. The independent governor still checks every proposal, including exchange quantity limits and risk tiers.
- Suspended strategy/regime groups can collect forward-only shadow trials. These never open positions or alter cash. A trial enters at the next complete minute's open, uses stop-first handling when OHLC touches both exits, deducts modeled costs, and expires if forward candles are missing. One sequential trial per group; at least 30 minutes between starts.
- Eight completed post-loss shadow samples, five positive outcomes, positive aggregate net, profit factor above 1.25 and at least one hour of forward coverage can allow **paper probation only**. A subsequent actual loss invalidates older recovery evidence. This is an experimental gate, not statistically established predictive ability or live promotion.
- AI shows scan age/staleness, batch evaluations/fills/vetoes, shadow progress, and an accessible confirmed paper-profile selector.
- Slate surfaces, restrained blue controls, readable light/dark palettes and concise recovery labels replace the previous emerald-heavy presentation. Profit/loss colors remain distinct.

No fixed 80-trade quota, automatic $1 profit claim, unconditional 500× execution, withdrawal flow or live-strategy activation was added. Existing account history, risk limits and automation settings are preserved. More trades do not establish better outcomes.

## Evidence

Backend source: `c6412964040a6e224a548e132b9be27ee133e1dc`. ZIP SHA256: `7a602362a66892ac82b2d1217658a20aee60614a3ca66ec7ee5c317f15bffdcd`.

- Local suite: **116 passed, 3 PostgreSQL-only tests skipped**. Initial local migration check used the wrong Python executable; rerunning with the virtual environment on PATH passed.
- [Backend/PostgreSQL/security CI](https://github.com/mzainch502-beep/zen/actions/runs/38636363477): **121 passed, 0 failed, 0 skipped**; migration, secret scanning and dependency audit succeeded.
- [Public historical replay](https://github.com/mzainch502-beep/zen/actions/runs/38635413123): 999 completed 1-minute candles for each of BTC, SOL and DOGE. Net modeled outcomes were **−0.38760578**, **−1.02920564**, and **−0.87431267** respectively; out-of-sample net outcomes were also negative. No strategy was promoted. This replay evaluates existing ranking and cost assumptions; it does not validate the new forward shadow lifecycle's future profitability.
- Railway API, worker and executor reached SUCCESS on the verified source archive. API reports version 0.8.0; post-deployment public health reported both workers online and 673 discovered contracts. Public health does not prove an owner's automatic-entry permission or diagnose their private account's exact 24-hour history.
- [Android UI validation](https://github.com/mzainch502-beep/zen/actions/runs/38635789944): **11 passed, zero failures/skips**. Screenshots reviewed for compact dark/light layouts.
- [Download Android 0.8.0](https://github.com/mzainch502-beep/zen/releases/download/zen-debug-38635789882/app-debug.apk), source `8fcd4b228bd7f4c6d24065ebf429cde6d9133470`. APK SHA256: `a98d7d88b973ba45d127ebc2018d73cdc8101d7d24450772ea972114ba0f34fd`.
- Candle failures now receive bounded per-symbol backoff rather than occupying every scan. Public scanner health separately reports actual candle reads. Local exchange candle requests failed, including BTC; GitHub historical reads succeeded. This is not evidence that every market endpoint works everywhere.
- Final deployment initially failed its integrity check because a TAR checksum was supplied to the ZIP launcher. Corrected to the verified ZIP checksum; verification remains enforced.

## Important operational limits

A fresh market feed is not proof of a functioning complete scan: the AI screen now distinguishes stale scans. Groups can still withhold trades while shadow trials lose or remain incomplete. Daily-loss/drawdown, spread, position-count, minimum-quantity and exposure vetoes remain effective; no loss history was erased to make the screen appear active. Portfolio-level drawdown may need an explicit owner risk review.

Shadow results are unleveraged OHLC counterfactuals, not exchange fills. They use a fixed cost estimate at observation time, not actual funding settlement, order-book queue position or intrabar tick reconstruction. Recovery evidence is pooled by strategy/regime rather than statistically validated per asset. Forward monitoring and broader walk-forward evaluation remain necessary.

MFA, recovery workflows, public multi-user onboarding, audited live strategy promotion, certified private exchange protection, and public fund-management readiness remain unfinished. This is an owner-managed debug APK. A visual redesign is not a public-launch certification.

Official ticker field reference: https://mexcdevelop.github.io/apidocs/contract_v1_en/ (high24Price, lower24Price, amount24).

## Final deployment verification — 2026-10-15 UTC

API, worker and executor all reached SUCCESS on c641296. Public health reported research_scanner_online=true, batch=24, candle_reads=24, data_errors=0, backoff=0; both workers were online. Catalogue contained 675 contracts at the check. This verifies cloud candle ingestion, not owner-specific fills or profitable execution. Live execution remains disabled.
