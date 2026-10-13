# ZEN 0.6 verified release — 13 October 2026

## Build evidence

- APK source: `68914a53fd5803cfc8a82b9c16df4e4dab5bf9a3`.
- [Installable debug APK](https://github.com/mzainch502-beep/zen/releases/download/zen-debug-38446791918/app-debug.apk), 17,270,674 bytes.
- APK SHA-256: `b86d381291d0174a7d0fd547cb894d688d773ec400f87418135b0763477cf7c0`, matched the GitHub release asset digest after download.
- [APK compile/lint workflow](https://github.com/mzainch502-beep/zen/actions/runs/38446791918): SUCCESS.
- [Android emulator workflow](https://github.com/mzainch502-beep/zen/actions/runs/38446791983): **7 passed, 0 failed** on API 35 x86_64. Test screenshots and HTML report are in its Android-UI-QA artifact.
- Backend source: `5ae226353746af5729cbcc32367ffed6dff2076c`. Its Android source is unchanged from the APK commit; the subsequent change enforces the shared paper entry-rate budget and adds tests/documentation.
- Verified backend archive SHA-256: `1cc21e76ba932178e67d9a16e896bf8d0fa76431c0afc12c2a59ea6663074ef6`.
- [Backend CI](https://github.com/mzainch502-beep/zen/actions/runs/38447084599): **114 passed**, PostgreSQL migration/concurrency checks passed, secret/dependency scan jobs passed.
- Local Python 3.12 suite: **111 passed, 3 skipped**; the skips are PostgreSQL tests because the local database service is absent. They ran and passed in CI. There are no sandbox private-order passes to report.

## Native verification

The emulator checks sign-in, five-tab navigation, agent pause confirmation, position empty-state navigation, explicit futures risk settings, server automation ON/OFF, aggressive paper-profile activation, learning-journal navigation, stock-linked empty filters, theme switching and persistent LIVE/PAUSED labeling. Captured 320dp dark/light screens, system insets, keyboard interaction, headers, bottom tabs, portfolio empty state and futures control sheet were visually inspected. Two earlier failed checks targeted uncomposed lazy-list items; they were corrected to scroll their containers and the final suite passed.

UI financial fixtures are synthetic and exist only in the instrumentation APK. They do not show a user's account or prove profitability. Samsung hardware, tablet/desktop/iOS layouts, all possible accessibility settings and exhaustive end-to-end interaction coverage are not certified. Full-screen charts and shared capital use real backend data; insufficient history and errors are explicit.

## Deployed operations

The final pinned source was installed on the existing Railway production services; every latest deployment reached terminal SUCCESS:

| Service | Deployment |
| --- | --- |
| API | `3b32208f-1fee-4859-9506-2679dfff7913` |
| Market/research worker | `b7d56019-871a-4d6e-b627-0b3572eb81ec` |
| Execution worker | `c407fc20-804f-4570-99a6-210922d84c73` |
| PostgreSQL (preserved) | `97beb124-5133-43cb-9c7c-e3ee0737cf3d` |

[Final public health evidence](RELEASE-0.6-HEALTH.json) records API version 0.6.0, active worker/executor heartbeats and 673 discovered supported futures contracts at verification time. Counts and venue limits can change. Public connectivity is not private order certification.

The added tests verify nonduplicated shared capital, replay/idempotency behavior, conflicting command rejection, open-position reset refusal, combined exposure and order-rate vetoes, reductions remaining available after the rate limit, bounded risk recommendations, shared-mode automation, live-workspace separation, derivative identity labels, XML entity/domain protections, emergency-state reset refusal, and one learning sample only after a spot exposure's final partial close with both-side fee accounting.

BBC World public RSS returned 20 accepted publisher-domain headline records in a real parser smoke check. Federal Reserve access returned HTTPError from the local environment; the worker records fetch failures for the UI. This verifies a limited feed path, not comprehensive news or geopolitical coverage. Local direct MEXC metadata smoke requests were unavailable; deployed public observer health confirms fresh venue quotes. Stock classification is metadata-based and has fixture tests; underlying market sessions/corporate actions are unverified.

## Research outcome and unfinished scope

The research scoring/evaluation kernel is unchanged from the corrected 0.5 replay. That prior replay used three saved sets of 999 completed 1m candles, with 599 training and 400 out-of-sample bars. It completed 52 trades: adaptive net **−1.81291052**, frozen net **−2.77677238**, adaptive out-of-sample net **−0.55384537** in the recorded modeled scenarios. Neither was promoted. These are historical replay results, not new 0.6 live performance. No new one-week paper result is claimed; the owner must run and inspect that trial.

Combined paper accounting does not model funding settlements or exchange queue/adverse-selection fills. VaR, calibrated confidence, corporate calendars and synchronized correlations are unavailable. The bounded risk recommendation is an engineering policy, not statistically established optimal risk sizing. Cross margin and exchange-native hedge automation are not added by this release. The system can reduce/close paper losses; it does not guarantee loss-free hedging or income.

Automatic live strategies remain disabled. Native MEXC manual execution is experimental and private exchange order acceptance/protective reconciliation were not validated. Additional private futures adapters, secure MFA/password recovery, an LLM research provider, owner-managed production signing, desktop/iOS and public fund management remain unfinished. Direct stock brokers are intentionally deferred. See [workflow details](INSTITUTIONAL-0.6.md) and the current README for actual owner operation.
