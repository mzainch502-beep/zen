# Railway storage recovery — 16 October 2026 KST

## Evidence and repairs

Both workers stopped with PostgreSQL DiskFull while inserting operational heartbeats. The PostgreSQL volume is 500 MB. Read-only diagnostics found 234,698,431 database bytes, 210,763,776 bytes in audit_events, 248,152 audit records, and 184,549,376 WAL bytes. The transaction-log configuration allowed max_wal_size=1024 MB, exceeding the entire volume.

Maintenance set max_wal_size=64MB, min_wal_size=32MB, reloaded configuration and checkpointed. Removed only worker/executor/futures-observer/research-scanner heartbeat records older than 24 hours, in batches of 1,000, then ran ordinary VACUUM ANALYZE and CHECKPOINT. Result: 121,690 expired operational heartbeats removed and WAL at 67,108,864 bytes. Ordinary VACUUM makes space reusable inside the table; it does not shrink the reported table size. No trades, balances, fills, learning outcomes or decisions were deleted. WAL limits are checkpoint targets, not a hard disk cap.

## Code changes

Operational heartbeats and scan summaries now use atomic deterministic-key upserts. Financial audit events remain append-only. Database OperationalError/InterfaceError retries back off from 5 to 60 seconds without logging query parameters. Cancellation still propagates. Restarting execution uses the existing reconciliation and order-idempotency checks, not blind order resubmission.

## Why there were no recent entries

Account diagnostics showed Paper, combined workspace, automatic trading enabled, aggressive profile, and no live activation. Among the last 300 evaluations: 227 strategy/regime suspensions after losses, 48 expected movement below costs, 18 insufficient evidence, and 7 liquidity/volatility/mark-deviation exclusions. History contained 80 autonomous entries and 80 completed learning outcomes. Restoring workers does not prove future profitability or require a new position to be opened.

## Capacity limitation

The 500 MB volume is still small. Durable decision and financial history will grow; this repair is not unlimited storage. A larger volume or verified external archival is necessary for long-term retention. Do not erase financial history or reset drawdown/losses to force entries. No live activation or forced trade quota was introduced.

## Validation and rollout

Source: c453c2a9aa8d8130cde7a40689df6ee24d46c2d6. ZIP SHA256: 4d33c6a2b4a8d612b6b581d2934ca3baa65c0a072d6445922589e3e8c7b43844.

Local: 121 passed, 3 PostgreSQL tests skipped. GitHub Actions run 38815007873: 124 passed with PostgreSQL; security job passed. Tests cover bounded heartbeat cardinality, preservation of financial audit events, transaction rollback and bounded database retry/cancellation.

API, worker and executor reached Railway SUCCESS. Post-startup health: worker_online=true, futures_executor_online=true, research_scanner_online=true, catalogue=676, batch=24, candle_reads=23, data_errors=1, backoff=1. One exchange candle failure was isolated and backed off; it did not stop scanning. This is a point-in-time operational check, not proof of indefinite uptime or a new trade fill. Existing app works without APK reinstall. Owner's aggressive automatic paper settings were preserved.
