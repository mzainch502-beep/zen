# ZEN 0.6.1 — learning-screen corrections

The owner's screenshots exposed cramped strategy/regime labels and an unclear suspension status. This Android-only patch:

- Uses a separate full-width strategy/regime heading and a compact second row for completed samples and status.
- Shows every recorded strategy/regime group instead of silently limiting the journal to six.
- Labels losing groups **Review required** and explains that automatic entries can remain enabled while particular groups withhold proposals.
- States the current recovery limitation: there is no timed resumption or validated shadow-recovery workflow.
- Bounds both key/value columns and stacks very long values, preventing wide values from squeezing labels into fragments.
- Labels WAIT execution **No order proposed** and displays ranking scores to three decimals; scores are not win probabilities.

This patch does not erase paper losses, reset learned weights, resume suspended strategies or change any risk/execution policy. Existing server state and history remain intact. Backend 0.6.0 remains compatible.

Code review confirms that suspension is based on at least five completed exposures and four consecutive losses for a pooled strategy/regime group. Recovery currently needs a new completed outcome; suspended groups cannot generate that through their own entries. A controlled shadow-evaluation/revalidation workflow is unfinished. Automatically reopening losing strategies or treating a timer as evidence of improvement would not validate their recovery.

The number 66 on the owner's screen is a completed-exposure count, not 66% accuracy or evidence of profit. BTC's movement-below-costs rejection is distinct from a suspension and is expected when its modeled opportunity cannot clear fees/spread/slippage. This UI fix does not establish profitable performance.

## Verified delivery

- APK source: `6621c53c3c7fbd8a940a16a80c51467de39d587c`.
- [Phone-installable APK](https://github.com/mzainch502-beep/zen/releases/download/zen-debug-38473409677/app-debug.apk).
- SHA-256: `5127b6be2d4f2615fa9a4e50afab681cb4fed53ee398ff3eefe37757313941aa`, matched after download.
- [Compile/lint](https://github.com/mzainch502-beep/zen/actions/runs/38473409677): SUCCESS.
- [Android emulator regression](https://github.com/mzainch502-beep/zen/actions/runs/38473409758): **8 passed, 0 failed**. The added test exercises six suspended and two other strategy/regime groups with synthetic fixtures. Final screenshots were inspected for readable model/strategy labels and every group.
- [Backend/security CI](https://github.com/mzainch502-beep/zen/actions/runs/38473410300): SUCCESS. Backend trading logic was not modified or redeployed by this patch.

No account learning data was cleared, no strategy was resumed, and no order was placed as part of the fix. Debug signing can require uninstalling the prior APK and signing in again; server history and automation preferences remain intact.
