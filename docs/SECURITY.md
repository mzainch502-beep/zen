# Threat model and operational security

Protect: exchange credentials, owner sessions, audit integrity, capital actions, and market-data provenance.

- AES-256-GCM ciphertext with random 96-bit nonces, owner/exchange/version authenticated context. Master key in hosting secrets; never source/APK. API does not return saved credentials. Only use read-only keys with withdrawals and trading off. API-permission flags are not certified across adapters.
- Argon2 password hashing; random bearer tokens stored only as SHA-256 hashes with 12-hour expiry and revocation. Android stores session only in memory; OS backup and screenshots disabled. No private info is logged intentionally; disable request-body logging at proxies/APM.
- TLS required by Android, redirect following disabled for API requests. Credential-input errors are redacted. Server authorization restricts every position/connection/audit to its owner. Login global limit 20/minute per process; production multi-replica deployment needs shared rate limiting and account/IP abuse controls.
- First-owner setup is gated by random hosting token and disabled if any owner exists; remove token afterward. Multi-instance simultaneous bootstrap is not certified. Provision once with API one replica. Public signup/password recovery is absent.
- Replay trade submissions use per-owner unique IDs and fingerprint checks. PostgreSQL locks serialize account mutations. Do not enable live mode until exchange-side idempotency and unknown-state reconciliation are separately implemented and validated.
- Worker never decrypts keys. Docker runs under unprivileged UID. Database should be private; hosting admin accounts require MFA. Separate least-privilege DB roles are not yet configured. Dependency and secret-scanning workflows exist; passing scans are necessary but not a security audit.
- Never give ZEN withdrawal or transfer permission. Cross margin would expose additional account equity; cross margin is disabled here.

## Backup/recovery

Schedule encrypted PostgreSQL backups and store master-key backups separately under owner control. Test restore into isolated staging. Keep trading stopped through restore; compare external account state before any future live activation. For this paper release, ledger is source of truth; never synthesize missing market observations. Rotate credentials by removing saved connection, revoking exchange key, creating a new read-only key, and re-testing. Master-key rotation needs a deliberate decrypt/re-encrypt migration; no automatic rotation claim.

## Remaining live launch gates

Private-stream/order-state recovery, signed command policy, futures-specific contract sizing and tick rules, exchange-native exits, liquidation margin tiers, hedge/cross behavior, regional permissions, incident drills, calibration, shadow/paper evaluation evidence, production API authorization audit, distributed rate limits, monitored backups, release signing, and explicit owner activation. Live activation is blocked even if paper tests pass.
