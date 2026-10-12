# Android build and release

Pinned build: JDK 17, Gradle 8.11.1, AGP 8.9.2, Kotlin/Compose compiler 2.1.20, SDK 35, min SDK 26. CI installs Gradle explicitly; repository does not carry a Gradle wrapper JAR. Build: `gradle :app:assembleDebug :app:lintDebug` from android/.

The five-tab Compose client uses TLS and memory-only sessions. Some large numeric values are displayed as exact backend decimal strings. This release is functional source, pending full real-device visual/accessibility/performance QA. Android UI smoke test covers offline sign-in inputs, not a full backend-backed navigation test. There is no claim that all requested futures screens are finished.

## Owner-managed release signing

Generate and keep a release keystore offline under owner control. Do not commit any keystore/password. Configure a local signing config or encrypted CI signing secrets in a private authorized workflow; this repository intentionally only builds debug APK. Review CI secret access before adding signing. Use one stable key for upgrades, securely back it up, and publish only after real-device and security review. A debug key is not a production release identity.
