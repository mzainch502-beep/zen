# ZEN 0.5 verified build

```json
{
  "apk_commit": "6de954306043462efd01f85f5843c912e6fb67f5",
  "backend_commit": "b91065268abcb6e7a9a5f1a86c564f2a4f6fdb26",
  "apk_url": "https://github.com/mzainch502-beep/zen/releases/download/zen-debug-38325299603/app-debug.apk",
  "apk_sha256": "sha256:7c254dce4c8f9de9af5e7431e60fa81036ab5a599079ceb46ce2b49cf6e19339",
  "backend_tests": 103,
  "android_ui_tests": 6,
  "ci_run": 38325705716,
  "apk_run": 38325299603,
  "ui_run": 38325299613,
  "services": [
    {
      "name": "zen-executor",
      "id": "cbfe757b-a7f4-4cd6-bfd5-45a38210ab40",
      "status": "SUCCESS"
    },
    {
      "name": "Postgres",
      "id": "97beb124-5133-43cb-9c7c-e3ee0737cf3d",
      "status": "SUCCESS"
    },
    {
      "name": "zen-api",
      "id": "e14b798d-7cf3-4010-92c1-64a48d452c33",
      "status": "SUCCESS"
    },
    {
      "name": "zen-worker",
      "id": "f28b1b5f-4f9a-4c85-983d-5ade4f072138",
      "status": "SUCCESS"
    }
  ],
  "observed_futures_catalogue": 673,
  "replay": {
    "version": "2.0.1",
    "completed_trades": 52,
    "adaptive_realized_net": -1.81291052,
    "frozen_realized_net": -2.77677238,
    "adaptive_oos_net": -0.55384537,
    "promoted": false
  },
  "private_exchange_orders_certified": false,
  "automatic_live": false
}
```

Install the debug APK, sign in, then choose Home → Aggressive → Start paper. This explicitly selects simulated futures, the reviewed preset and automatic PAPER entries. Settings → Trading controls can reset simulated capital, including 3 USDT, after closing paper positions. Profile and automation persist across sign-ins. Trading continues on the backend while the app is closed or signed out; turn the switch OFF or use pause/emergency stop to prevent new entries.

The release replaces sparse three-market breakout research with a discovered USDT perpetual catalogue and rotating liquid/API-eligible candle batches. The deployed observer reported 673 supported instruments with fresh public quotes during verification. Not every derivative product or account jurisdiction is supported. Invalid, stale, thin or API-disabled products do not qualify for automatic entry.

Six emulator tests passed including explicit aggressive-profile activation, server automation ON/OFF, all five tabs, live/paused labeling, futures controls and learning-journal scrolling. Final screenshots were reviewed for 320dp layout, first-viewport preset actions and accessible selected-tab semantics. Instrumentation fixtures are synthetic and do not enter the production app. Samsung hardware performance has not been certified.

The corrected historical replay used three saved datasets of 999 completed 1m candles each; 599 train/400 out-of-sample bars. A prior harness could re-enter at a bar open after learning from that bar close. Version 2.0.1 prevents same-bar re-entry, and the corrected ledger proves subsequent entries occur after the previous exit bar. Raw inputs and corrected results are in docs/evidence/0.5/. Both adaptive and frozen baselines lost after modeled costs. Reduced loss in this sample is not proof of profitable or 5x more accurate trading. Funding settlement, tick-level liquidity, multi-position margin and open unrealized exposure are not covered by this replay; it cannot authorize live promotion.

Learning updates bounded strategy/regime preferences after a complete exposure closes, with partial-close aggregation, sample gates, loss-streak suspension and auditable prior/new weights. It cannot guarantee improvement on every outcome. Heuristic rankings are not calibrated probabilities or human professional discretion. No live strategy mutation or withdrawal workflow was introduced.

The backend observer and research tasks are supervised and restart after unexpected termination; quotes and paper exits remain separate from candle retrieval. Source archives are pinned and checksum verified. Deployed OpenAPI reports 0.5.0 and exposes authenticated research/profile contracts. All four Railway services reached SUCCESS. No private exchange order validation was performed by this build.

Remaining original scope includes private execution certification, complete native protective-order reconciliation, full funding accounting, additional exchange futures adapters, broader walk-forward/shadow validation and production signing. Automatic live remains gated. Debug signing can require uninstalling an older APK before installing; backend history remains intact.
