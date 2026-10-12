# Architecture and implementation boundaries

Android → TLS FastAPI → PostgreSQL. Background observer/exits worker → public exchange data → PostgreSQL. Research → append-only decision events. Capital mutations → independent risk governor → paper ledger. No live order route exists. Credential vault is accessible only in the API process; worker never loads private credentials.

| Requested role | Implemented source | Current boundary |
|---|---|---|
| Market observer | backend/worker.py, exchange_adapters/ccxt_adapter.py | Spot executable quotes, Binance public book feed, completed 1m candles; trades/depth/OI/funding missing |
| Regime classifier | agents/pipeline.py | Descriptive trend/range/volatility/compression/liquidity flags; not predictive certification |
| Trend researcher | agents/pipeline.py | Completed-candle descriptive drift; single timeframe in worker |
| Opportunity evaluator | agents/pipeline.py | Research hypothesis; no claimed expected edge or probability |
| Strategy selector | agents/pipeline.py | Version registry interface; no validated executable strategies |
| Decision agent | agents/pipeline.py | WAIT with evidence/contradictions; no live authority |
| Risk governor | risk/governor.py | Spot paper constraints; reduction path independent from entry suspension |
| Execution agent | backend/service.py, exchange_adapters/state.py | Transactional paper fills; state tracker unit tested; no exchange order execution |
| Position manager | backend/worker.py | Backend paper stop/take-profit reductions, not exchange-native conditional exits |
| Learning/evaluation | research/evaluation.py | Reproducible baseline and validation predicate; model-training and guarded deployment missing |
| Portfolio | backend/service.py | Spot equity, costs, cash, P&L; stale marks yield unavailable equity |
| Reconciliation/audit | database/models.py, backend/service.py | Persistent paper ledger; no private exchange reconciliation |

## Persistence

Users, sessions, encrypted exchange connections, orders, positions, market quotes, model registry, audit events. Fills/fees/risk approvals/decisions/snapshots are schema-versioned events. Separate normalized fills, funding, signals, balance history and evaluation-result tables are future schema work. Existing migration is initial-only and imports current metadata; freeze explicit DDL before making future schema revisions.

Order IDs are unique per owner; request fingerprint mismatch is rejected. PostgreSQL user row locks serialize equity/risk/order writes. Paper fills are atomic. SQLite concurrency is not a production substitute. No network order retries occur because live order placement is absent.

## Risk semantics

Defaults: $2 modeled loss per trade, $6 daily realized/net loss ceiling with negative unrealized losses included conservatively, $20 drawdown ceiling, $40 total/correlated spot exposure, 2 positions, 1×, 20 bps maximum spread, modeled 10 bps slippage, 6 orders/minute, 300-second cooldown after 3 losing exits. No averaging into existing positions. Limits bound modeled outcomes; gapped exits can exceed planned loss. Spot sells must reduce existing quantity. Emergency stop leaves existing positions open; reductions remain possible using fresh quotes.

Binance WebSocket book feed uses receipt timestamps when exchange event timestamps are unavailable; midpoint is a quote-derived reference, not last trade. REST ticker source supplies actual last trade. Feed receipt freshness cannot prove exchange event freshness. Market adapter precision helper is independently tested but not yet wired to every paper order from discovered exchange rules.

## API/event contract

OpenAPI is generated from typed input schemas. HTTP errors do not reflect credential request bodies. WebSocket `/events`: first client frame is bearer token; server frames `{schema_version:1,type:"snapshot",timestamp,portfolio,positions}`. Auth is rechecked every 3 seconds. No URL query tokens. Output Decimal values are strings; absent/stale metrics are null.

Endpoints: `/auth/setup`, `/auth/login`, `/auth/logout`, `/health`, `/snapshot`, `/markets`, `/candles`, `/paper/orders`, `/agent/mode`, `/risk`, `/positions/{id}/exits`, `/exchanges`, `/connections`, `/audit/export`. `/live/activate` is a hard rejection.
