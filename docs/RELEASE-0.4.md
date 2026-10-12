# ZEN 0.4 — redesigned native terminal and futures execution paths

## Implemented

- New original mint ZEN monogram and launcher icon; larger typography, gradient portfolio surface, simpler market rows, clearer LONG/SHORT cards and five-tab navigation.
- Futures control screen: spot/futures selection, explicit leverage ceiling 1–500, discovered-maximum option, margin/notional/loss limits, paper automation, simulated capital reset (including $3), encrypted native MEXC connection and explicit manual live activation.
- Native MEXC Open-API signing, clock offset, decimal JSON, public contracts/tickers/candles/depth, private account/position/fee/risk-tier reads, market LONG/SHORT intents with attached fair-price TP/SL, one-way isolated entries and close-only reductions.
- Durable order intents committed before a submission attempt; uncertain submissions are reconciled by external ID and never blindly resubmitted. Cumulative partial fills are checked for monotonicity. Acknowledgment is not reported as a fill.
- Isolated linear-perpetual paper ledger on real MEXC quotes, both directions, modeled entry/exit costs, minimum contract sizes, leverage/tier ceilings, liquidation-envelope vetoes, reductions, TP/SL and maximum holding time.
- Separate privileged executor entry point. Public observation does not require the credential decryption key. Pending entry intents are checked against live activation and current mode before submission.

## What is not certified

This is not a profitable or production-certified trading system. No real private exchange credential or order has been supplied or validated in this development session. Tests with synthetic exchange responses establish control-flow behavior, not exchange acceptance. MEXC public requests from the local development environment returned HTML unavailability responses; cloud egress must be checked independently before claiming usable market connectivity.

Only MEXC has a native private futures implementation in this release. Other directory exchanges remain read-only. Native futures require the owner's lawful account eligibility, KYC, permitted API access, order/account-read permissions, one-way position mode, and withdrawals/transfers disabled. Permission flags are owner-attested, not independently enumerated by an API.

Manual live activation requires explicit owner confirmation and a fresh private account plus executor heartbeat. Live autonomous strategy promotion remains blocked: the experimental breakout trial has no proven out-of-sample edge or approved promotion evidence. Setting a paper automation toggle does not authorize autonomous real-money trading.

Leverage 500 is a configurable **ceiling**, not a universal contract or account capability. Effective leverage is bounded by discovered contract, country configuration, risk tier, account fee response and owner limits. Fee schedules that depend on leverage remain rejected until certified. Maximum-leverage requests can be vetoed because the stop cannot fit ahead of modeled liquidation or because available cash cannot cover margin and both-side fee reserves. $3 × 300 = $900 before costs; $3 × 500 = $1,500 before costs. Neither implies an order can be accepted with only $3 total available cash.

Cross margin, hedge-mode execution, unrestricted simultaneous live symbols, native protective-order-status reconciliation/editing, private streaming fills, live automatic reversals, full fee/funding accounting, calibrated adaptive learning and signed production releases remain unfinished. New live entries request native TP/SL; acceptance/protection must be verified on the exchange. An exchange outage or gap can exceed planned loss.

Paper taker fees use a conservative 8 bps per-side floor, or the higher public contract rate; actual private account fees are not fabricated. Paper funding is reserved conservatively at entry but actual funding settlement is not simulated. The app labels it unavailable rather than reporting fabricated zero costs. Paper liquidation prices are isolated-model estimates; live liquidation values use native reported fields when available. Complete daily live P&L is withheld until the full fee/funding ledger is certified.

## Phone workflow

1. Install the debug APK; sign in to the existing owner account.
2. Settings → Trading controls → Perpetual futures → save. It remains paper by default.
3. Adjust paper limits and simulated capital; enable automatic **paper** trials if desired.
4. Markets → select a contract → Open futures order → LONG or SHORT → margin/leverage/exit prices → review. Governor vetoes are real controls.
5. Positions → Manage → reduce, close or edit simulated exits.
6. Native private access: Trading controls → Connect MEXC futures → enter credentials privately in the app. Keys are encrypted server-side and never returned. Do not paste credentials into chat.
7. Manual live authorization is a separate explicit action. Automated live strategy deployment is not validated and is not enabled by this release.

See test artifacts, the public-probe report, and the deployment report for actual outcomes. Do not interpret synthetic gains or a successful APK build as validation of live trading or daily income.
