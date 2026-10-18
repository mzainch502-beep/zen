# Cloudflare migration status

This branch is a candidate port, not a completed Railway replacement.

## Verified on 18 October 2026

GitHub Actions run 39151213234 passed the actual Cloudflare workerd runtime checks:
Argon2 authentication, AES-GCM credential encryption, persistent storage, SQLAlchemy
transactions and nested rollback, owner login, paper SHORT execution, duplicate
prevention, emergency stop with reducing exits, and session revocation.
All market prices in these tests are fixtures. This is not evidence of live exchange execution.
Backend validation run 39151213240 also passed.

The remote `zen-migration-check` Worker verifies Cloudflare durable storage only.
It is not the app backend. The installed Android app still uses Railway.

## Deployment access

Use the Cloudflare account belonging to fatishorizon@gmail.com. Create a token
using the **Edit Cloudflare Workers** template, restricted to that account.
Save it in the repository's Actions secrets as `CLOUDFLARE_API_TOKEN`.
Never paste it into chat, source, logs or screenshots. Revoke it after migration
if ongoing deployment is not needed.

Run `deploy-cloudflare.yml` from this branch. It depends on the compatibility
suite and leaves a new backend inactive. It does not transfer data or activate
execution. The connector cannot create this API token, and its external fetch
capability rejected the packaged artifact URL.

## Required before cutover

1. Validate the deployed Python Worker and public exchange access.
2. Validate the import tests, restart recovery and background alarm behavior.
3. Complete context polling, event-stream compatibility and execution parity.
   The candidate currently supports the paper flow; the live executor is not ported.
4. Measure storage writes and CPU against the account plan. Free tier quotas
   can stop operations; do not treat free hosting as guaranteed uninterrupted service.
   No paid plan has been authorized or enabled by this migration.
5. Stop source execution and freeze source API mutations. Retain a verified backup.
6. Provision fresh target vault and migration secrets securely, export a consistent
   PostgreSQL snapshot, verify table counts and chained batch hashes, then activate.
7. Update Android's backend URL, build/install and verify the APK.
8. Retire Railway only after the target and account data have been verified.

`export_snapshot.py` preserves account records and reencrypts exchange credentials
for the destination. HTTP batch retries are idempotent. Restarting the exporter
with a new process is not yet supported when credential re-encryption changes a
batch: retain the consistent export or implement encrypted checkpointing first.
Never clear trading history or reset losses to make a migration pass.
