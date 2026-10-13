# ZEN 0.6 — institutional Android desk

This is an owner-managed experimental trading research application. The interface is inspired by professional financial workflows; no BlackRock technology or investment performance is reproduced. Direct stock brokers, public fund management, iOS and a desktop web app are deferred.

## Android workflows

Home shows authentic account NAV, cash and net outcomes. Portfolio exposes spot/futures positions and their existing position controls. Trade searches the live venue catalogue and filters stock-linked derivatives. AI shows actual decisions and bounded learning history. More opens strategies, risk management, recorded performance, connections, public market context, audit export and settings. The original adaptive launcher icon uses a restrained Z monogram. Licensed, locally bundled Inter and IBM Plex Mono fonts cover Latin text and financial symbols, with platform fallback for other glyphs. Both light and dark palettes are designed explicitly.

Install the debug APK from the GitHub release, or run Actions → Build Android APK → Run workflow from a phone. Download/extract the APK artifact and allow installation from the chosen browser/file manager. Debug signing is not an owner-managed production signing key; Android may require uninstalling an earlier build signed by a different runner. This removes local session data, while server account history remains. Sign in again. Never put exchange keys in an APK or repository.

## Shared simulated capital

Home → Paper capital setup initializes one amount, explicitly split equally between two separate simulated books. It does **not** give both books the full stated capital. Open paper positions must be closed first. Capital commands have durable idempotency keys and reject conflicting reuse. Combined reporting and charts use recorded server snapshots after the latest reset; there are no interpolated or invented performance curves.

The global Automatic trading switch controls entries in both books in the shared workspace. OFF, pause and emergency halt prevent new entries; protective management continues. Backend workers run independently of the phone. Spot LONG hypotheses use the spot venue's own completed candles; spot cannot open a naked SHORT. Both books obey their own risk governor plus aggregate exposure, position-count, daily-loss and drawdown checks. WAIT is valid, including on critical days. Buying spot does not guarantee capital preservation or profit.

The setup supports simulated capital from 1 to 1 billion USDT and a paper leverage ceiling up to 500×. A ceiling does not force leverage, override venue capabilities/minimums, or assure a fill. With automatic risk recommendations enabled, limited or losing evidence tightens leverage to 1× and loss budgets. Positive paper outcomes after 30 samples permit only a bounded recommendation up to 3×, still below the owner ceiling. These are engineering safeguards, not validated optimal financial advice. 500× stress settings still face costs, liquidation-distance checks and venue limits; there is no fabricated universal 500× exchange capability.

## Research and context boundaries

The existing contextual research engine compares momentum, pullback and range hypotheses with costs and bounded completed-outcome feedback. Spot completed outcomes join the learning journal. A completed exposure is one sample; partial closes are accounted before completion. Learning does not grant live authority or unconstrained strategy mutation. Out-of-sample profitability and professional judgment are not established.

A backend worker polls Federal Reserve and BBC World public RSS metadata every 15 minutes. Parsing is bounded, uses XML entity protection, and accepts only publisher HTTPS domains. Publisher failures are recorded. Headlines are untrusted research input; they cannot call tools or place orders. Recent reviewed headline keywords may tighten automatic risk recommendations, never supply a directional execution command. Coverage is limited and does not establish comprehensive geopolitical analysis.

Stock-linked/index-linked perpetual labels are discovered from exchange symbol/display metadata. They are derivatives, not direct shares or share ownership rights. Underlying sessions and corporate-action rules remain marked unverified; no claim is made that every exchange product follows the same schedule, funding or legal rules. Every venue/account/jurisdiction requires separate private execution validation.

## API additions

All portfolio/risk/instrument/context/capability routes require an authenticated owner session.

- `GET /portfolio/overview`: combined simulated valuation and positions; live native activation rejects combined reporting.
- `POST /portfolio/paper-capital`: Decimal total, futures_fraction, leverage_ceiling, auto_risk, automatic, explicit confirmation, client_id; atomically resets both books only with no positions.
- `GET /portfolio/history?period=1D|7D|30D|90D|1Y|ALL`: up to 5000 authentic consolidated snapshots after reset.
- `GET /risk/overview`: aggregate exposure, bounded recommendation and clearly labeled static shock estimates. VaR/correlation are unavailable, not invented.
- `GET /instruments`: metadata classification, API eligibility and freshness.
- `GET /context/events`: public publisher metadata and source fetch state.
- `GET /platform/capabilities`: explicit implemented/unavailable capabilities.

No database schema migration is needed for these additions; existing versioned JSON audit records persist snapshots, outcomes and source states. PostgreSQL remains required for deployment, with separate API, observer/research worker and execution worker services. Hosting has ongoing usage costs and requires persistent uptime; the backend cannot depend on a phone background process.

## Release limitations

Automatic live strategy promotion remains disabled. Native MEXC private execution exists behind explicit owner activation but is experimental and not certified by these tests. Other venue adapters do not imply universal private futures execution. No live exchange orders or exchange credentials were used for this release. Funding settlement is not modeled in combined paper accounting. Statistical VaR, calibrated confidence, corporate calendars, MFA, password recovery and an LLM research provider remain unavailable and are labeled accordingly. There is no guaranteed daily income, loss-free hedging or lifetime investment support. Public fund management needs a separate legal, operational and security programme.
