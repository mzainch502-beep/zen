# ZEN 0.4.1 validation

Verified 2026-10-12. Testing build; not a claim of production-certified execution or profitable strategies.

## Install

[Download debug APK](https://github.com/mzainch502-beep/zen/releases/download/zen-debug-38255447759/app-debug.apk)

Version 0.4.1, versionCode 5. APK source f4f6274200907409bb7c5e2e84aaaaf6854e993b. APK SHA256: 2114debfce78d7b7bb01804f288d29fd638dee1aee21f1ce0c0ee6c897ff6d81. File size 17,053,273 bytes. Owner-managed production signing is still required.

## Evidence

- Backend CI run 38255447373: 81 tests passed; dependency audit and secret scanning passed.
- Android build/lint/release run 38255447759: success.
- Emulator UI run 38255447461: 4 tests passed. Samsung hardware performance is not certified.
- Railway API, public worker, privileged executor and PostgreSQL were online with successful deployments at release verification.
- API deployed source f4f6274200907409bb7c5e2e84aaaaf6854e993b; worker/executor source 46dd1d6495e9ceeda9f2ad86cfe7e3c0649f9b7d.
- Public MEXC contract feed observed BTC/ETH 500x and SOL 300x ceilings. These are contract metadata, not guarantees of private account eligibility or order acceptance.
- Isolated paper smoke using fresh public quotes: simulated capital 3 USDT; BTC SHORT at 10x; notional 8.2797120; final equity 2.970373578168; net -0.029626421832. No exchange credentials or real orders were used. This demonstrates accounting and execution flow, not predictive value.

## Delivered behavior

Native premium Compose interface and original ZEN monogram; real market data; explicit spot/futures paper workspaces; configurable simulated capital; paper LONG/SHORT; deterministic margin/precision/cost/liquidation checks; paper TP/SL/partial close; durable native MEXC manual live intents and separate executor; unknown-state reconciliation; owner activation controls; phone-downloadable APK releases.

Paused native accounts remain visibly LIVE. Risk settings route to the active workspace. Active live futures cannot be hidden by switching to Spot; close/reconcile and deactivate first.

## Remaining gates

Private MEXC credentials have not been supplied and private order acceptance has not been tested. Live requires eligible owner account, privately submitted keys, successful connection test and explicit activation. Manual live paths are experimental. Autonomous live strategies remain gated pending validation; no strategy profitability or daily profit is promised. Full native protection-status reconciliation, private WebSocket certification, funding ledger reconciliation and guarded learning promotion remain unfinished. Paper funding is reserved in entry planning but actual settlements are not simulated. Full live daily net P&L is withheld when incomplete.

The 25 USDT daily target is aspirational. Loss limits and WAIT remain effective. The persistent backend runs separately from the phone. Withdrawal/transfer permissions must be disabled.
