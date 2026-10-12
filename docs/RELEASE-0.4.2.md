# ZEN 0.4.2 — owner-controlled automation

A single persistent Automatic trading switch controls new automatic entries in the active workspace. Its state is supplied by authenticated backend endpoints, never a local preference. Owner row locking serializes commands with order proposals. Repeated identical commands do not create duplicate audit events. Default OFF. Workspace changes disarm automation. Disabling leaves observation and existing protective exits running. Paused/emergency/live workspaces reject enable requests with an explicit reason.

Spot and futures research trials can run automatically in PAPER. Live automation remains unavailable until strategy promotion and private execution validation are completed. No credentials or exchange orders were used for this release. This does not complete the original adaptive research/live-certification scope.

API: GET/PUT /agent/automation; PUT body {"enabled":true|false}. Snapshot includes enabled, requested, can_enable, blocked_reason, product, mode, research_trial, exits_remain_active. enabled reflects permission to run; observer health and individual risk vetoes still determine whether any trade executes. requested retains the owner selection while paused, allowing disable without resuming. Reconnection reloads the server state.

Native layout uses a compact safe-area header, permanent mode indicator, a 72dp navigation dock above OS navigation, consistent screen gutters, and a server-controlled automation strip. An enable confirmation explains simulated capital and the unvalidated strategy. Network failure leaves last-known state and retry feedback, never an optimistic ON.

Validation results are recorded after the release CI runs. Private exchange execution, native protective-order reconciliation, learning promotion, and additional exchange certification remain pending. Daily profit is aspirational; no quota forces trades.
