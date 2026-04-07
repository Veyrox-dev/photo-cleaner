# Windows 11 Test Checklist (Father Test)

## Goal

Run one complete usability and stability pass on a clean-ish Windows 11 user machine.

This checklist is optimized for the current launch gates:
- MSI install quality
- FREE/PRO licensing behavior
- basic workflow stability

---

## Setup

1. Use installer: `releases/msi/PhotoCleaner-0.8.4-x64.msi`
2. Ensure internet is available for license checks.
3. Prepare one photo folder with at least 300 images (to test FREE limit behavior).

---

## Test Steps

### A) Installer and App Start

1. Install MSI with default settings.
2. Launch app from Start Menu.
3. Confirm app starts without crash.

Pass criteria:
- install completes
- app starts
- no immediate error dialog

### B) Basic Workflow

1. Select an image folder.
2. Run one normal analysis.
3. Open review and navigate groups.
4. Perform one keep/delete flow.

Pass criteria:
- no crash/hang
- results are visible
- navigation and actions work

### C) FREE Limit Case (250)

1. Run/attempt processing beyond 250 images in FREE mode.
2. Verify clear limit message with upgrade hint.

Pass criteria:
- operation blocks correctly when limit reached
- message is understandable and actionable

### D) PRO Case (Unlimited)

1. Activate PRO key.
2. Re-run same larger folder.
3. Verify processing is not blocked by image limit.

Pass criteria:
- activation succeeds
- processing above 250 works

### E) Close and Reopen

1. Close app fully.
2. Start app again.
3. Verify no regression on startup or loaded state.

Pass criteria:
- restart works
- no new warnings/errors

---

## Required Artifacts

Please collect and hand over:

1. Test notes using template: `feedback/TEST_SESSION_TEMPLATE.md`
2. App log file(s), especially `feedback/PhotoCleaner.log` if present
3. Optional screenshots for confusing UI states or errors

---

## Severity Guide

- Critical: crash, data loss risk, install/uninstall broken
- High: core workflow blocked, activation impossible
- Medium: incorrect messages, strong UX friction
- Low: cosmetic issues, wording improvements
