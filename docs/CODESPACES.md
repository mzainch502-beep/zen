# Run ZEN backend in GitHub Codespaces

This configuration starts PostgreSQL, FastAPI and an independent paper market worker in a GitHub Codespace. It does not activate live execution. Codespaces is a temporary development runtime, can stop when idle and has metered compute/storage. It is not a continuous trading hosting guarantee.

## From Android

1. Open the ZEN repository in Chrome. Use Desktop site if the Code menu is cramped.
2. Select **Code → Codespaces → Create codespace on main**, using the smallest available machine.
3. Wait for configuration and Docker builds. Setup creates a private, git-ignored `.env` with fresh database password, encryption key and first-owner setup token. Existing values are retained on restart.
4. Open **Ports**. Port **8080** is the API. Open its forwarded URL and add `/health`; it should report `status: ok`. `worker_online` can take a few seconds to become true.
5. The default forwarded port is private and needs GitHub login. To connect the APK directly, you must deliberately set **Port visibility → Public** for 8080. This exposes the API to the internet; ZEN's own authentication still applies. Do not expose PostgreSQL or other ports.
6. Copy the forwarded **HTTPS base URL** into the APK.
7. Open the private `.env` file in the Codespaces editor and use only `BOOTSTRAP_TOKEN` for the APK's **Create owner account** form. Choose your own email and 12+ character password. Do not post this token or screenshot that file.
8. Remove the `BOOTSTRAP_TOKEN` line after owner creation and run `bash infra/codespaces-start.sh` once to recreate the API with setup disabled.
9. Sign in to the APK and use paper mode. Real exchange keys are optional for paper testing; no live order endpoint exists.

## Operations

- Restart services: `bash infra/codespaces-start.sh`.
- Stop services: `docker compose --env-file .env -f infra/compose.yml stop`, then **Stop codespace** to stop compute usage.
- Check API/worker logs: `docker compose --env-file .env -f infra/compose.yml logs --tail 50 api worker`. Do not enable request-body or shell trace logging.
- Never run `docker compose config` in a shared screenshot: it can expand private variables.
- Database storage is a Docker volume. Do not use `down -v`. Rebuild/delete operations can lose data; back up the database and encryption key before them.
- Workspace and container data are not an operational backup. Keep this environment disposable and paper-only.

## Limits

GitHub Pages is static hosting and cannot run FastAPI. GitHub-hosted Actions jobs have a six-hour execution limit and are for bounded workflows, not an always-on API/worker. Codespaces idle timeouts can be configured from 5 to 240 minutes. GitHub Free personal accounts currently include 120 core-hours/month (60 running hours on a two-core machine) and 15 GB-month storage. Account-specific usage, policies and billing can restrict creation earlier. Do not create keepalive or relaunch loops to evade platform limits.

For uninterrupted trading later, retain GitHub for source/builds and deploy PostgreSQL/API/worker to persistent external infrastructure. Railway provisioning is currently blocked in this session by its account resource limit.

Official references:
- https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- https://docs.github.com/en/actions/reference/limits
- https://docs.github.com/en/codespaces/setting-your-user-preferences/setting-your-timeout-period-for-github-codespaces
- https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace
- https://docs.github.com/en/billing/concepts/product-billing/github-codespaces

Validation: JSON and shell syntax plus secret-generation/restart handling checked locally. Docker/Codespaces provisioning has not been executed by the agent; create the Codespace to validate the full startup in your account.
