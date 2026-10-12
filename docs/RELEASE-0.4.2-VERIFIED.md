# ZEN 0.4.2 verified release

{
  "apk_commit": "41d7327549773b9877d8722d1211b017d872cdbf",
  "backend_commit": "8fd414b7cb13d2ec65ec2ee68761d2e045aceba3",
  "apk_url": "https://github.com/mzainch502-beep/zen/releases/download/zen-debug-38284906530/app-debug.apk",
  "apk_sha256": "sha256:1ae663f93ccaa9f331d6f1097861a5746af667470056b3f96b606451573b89d4",
  "backend_tests": 89,
  "android_ui_tests": 5,
  "ci_run": 38284906634,
  "apk_run": 38284906530,
  "ui_run": 38284906579,
  "services": [
    {
      "name": "zen-worker",
      "deployment": "d0c01ee0-d078-47c3-ad4f-b360dce7ac70",
      "status": "SUCCESS"
    },
    {
      "name": "Postgres",
      "deployment": "97beb124-5133-43cb-9c7c-e3ee0737cf3d",
      "status": "SUCCESS"
    },
    {
      "name": "zen-executor",
      "deployment": "c75f9a9b-35ea-4439-a354-d62a9d8673a4",
      "status": "SUCCESS"
    },
    {
      "name": "zen-api",
      "deployment": "927a2a9d-00d9-4824-9269-4c6ef5c7c47c",
      "status": "SUCCESS"
    }
  ],
  "live_credentials_supplied": false,
  "private_orders_tested": false,
  "automatic_mode": "paper only; live promotion gated"
}

Automatic trading is an authenticated, persisted backend permission for new paper entries. Default OFF. It does not force an entry or a profit quota. Protective exits and market observation remain running after OFF. Workspace switching disarms automation. Emergency/paused/live enable requests are rejected with explicit reasons. Settings cannot secretly re-arm the switch.

UI validation exercised sign-in, all five navigation tabs, risk controls, futures configuration, paused-live labeling and ON/OFF server commands. Final emulator screenshots were reviewed; bottom navigation labels remain on one line at 320dp. Test-only simulated balances are isolated in the instrumentation fixture and are not production account data. Samsung hardware performance is not certified.

The public deployed OpenAPI reports version 0.4.2 and GET/PUT /agent/automation. Health reports status ok, observer and executor online. Deployment updates preserve account/history and credential configuration.

Remaining original scope: private exchange certification, complete native protective-order reconciliation/editing, validated adaptive learning/model promotion, native funding/fill accounting completeness, additional exchange execution adapters and production signing. Automatic live remains gated. Exchange connection intentionally deferred by owner. A daily profit objective is aspirational.
