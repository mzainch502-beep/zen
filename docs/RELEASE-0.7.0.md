# ZEN 0.7.0 — compact Android design

This release changes Android presentation only. API contracts, trading permissions, risk limits, stored learning outcomes, credentials and the Railway deployment are unchanged.

## Design changes

- Compact two-level application header: original ZEN monogram, persistent paper/live label, notifications, account and emergency halt. Automatic trading retains its server-authoritative switch, with an explanation dialog available by tapping its label.
- Home prioritizes NAV, daily net outcome, available capital and open P&L. Positions and Markets are immediately below the summary; optional paper setup no longer displaces these actions.
- Consistent 16dp screen gutters, 14dp card padding, restrained borders, compact typography and five-tab navigation. Controls retain at least 44dp touch targets.
- AI learning summaries stay concise. Expand **Review learning evidence** for every strategy/regime group, model version and limitations. Suspended groups remain clearly identified. Decision evidence expands separately; reasons and execution status remain visible.
- Portfolio exposes summary metrics first and detailed exposure on demand. Workspace navigation uses shorter rows with consistent icons and chevrons.
- Trading charts and order/settings sheets use the same spacing system. Order entry is directly below the market chart. All order confirmations and risk messaging remain in place.
- Explicit light and dark palettes, bundled Inter/IBM Plex Mono fonts and the original vector launcher icon remain supported.

## Verification

- APK source: `7652842df43229dd702f33b8c512da42309db78b`.
- [Phone-installable APK](https://github.com/mzainch502-beep/zen/releases/download/zen-debug-38477006878/app-debug.apk).
- Downloaded APK: 17,287,703 bytes; SHA-256 `66586233b4eeb97b82a9d682a5756a23879e70b8a3f8a21209db67ba868e891b`, matched against the release asset.
- [Compile and Android lint](https://github.com/mzainch502-beep/zen/actions/runs/38477006878): SUCCESS.
- [Backend/security CI](https://github.com/mzainch502-beep/zen/actions/runs/38477006851): SUCCESS; backend source and deployed services unchanged.
- [Final Android UI validation](https://github.com/mzainch502-beep/zen/actions/runs/38477006803): **10 passed, 0 failed, 0 skipped**. Coverage includes navigation, authentication forms, automation confirmation, explicit futures settings, strategy selection, theme/filter behavior, learning disclosure and 1.3× font scaling.

Final emulator screenshots were inspected for compact Home, dark/light themes, market filters, candlestick detail, learning disclosure and expanded strategy rows. The 1.3× font-scale navigation check passed. Screenshots use test-only fixtures and are not performance evidence.

Measured text/card contrast ratios: dark primary 15.38:1, dark secondary 6.59:1, light primary 15.96:1, light secondary 6.46:1; accent text 8.66:1 dark and 6.30:1 light. These are palette checks, not a complete accessibility certification.

Instrumentation uses synthetic repository responses only in the test APK. Production screens continue to use backend data. No invented performance curves, model confidence or trade results were introduced.

## Boundaries

This design does not fix the previously documented strategy suspension/recovery limitation or establish trading profitability. Public signup, MFA, secure password recovery and public fund-management operations remain unfinished. This is an owner-managed debug APK for MVP evaluation, not a certified public investment product. Physical Samsung-device, TalkBack and broad device-matrix testing remain owner acceptance work.

If Android rejects an update because debug signing changed, uninstall the prior test app and sign in after installing. Backend account history persists. Backend automation follows its saved state even while the app is uninstalled.
