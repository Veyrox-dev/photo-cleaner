# Week 4 Onboarding + Smart Filter

## Goal

Week 4 reduces first-run friction and guides users through safe decisions.

Primary product target:

- New users should reach the first confident decision quickly.
- Risky actions (delete/export) should remain explicit and understandable.

## Scope

1. Guided onboarding for first run
2. Smart review filters for faster manual validation
3. Quota and upgrade messaging in-context
4. Safe-review hints during early sessions

## Deliverables

### 1. First-Run Onboarding

- Lightweight onboarding dialog after initial import/indexing
- Explains statuses: Keep, Delete, Unsure
- Explains confidence and needs-review semantics
- Includes shortcut hints and one-click "Start review"

Acceptance:

- Onboarding appears only on first run (or after explicit reset)
- Onboarding can be skipped without blocking workflow
- Settings persist onboarding completion state

### 2. Smart Filter Bar

- Add filter chips/toggles in review panel:
  - Needs Review only
  - Open decisions only
  - Low confidence groups
  - High-impact groups (many files)
- Counter badges for each active subset

Acceptance:

- Filter updates group list without UI freeze
- Filter state is visible and resettable in one click
- Group counters remain consistent with current filter

### 3. Quota/Upgrade Messaging

- Replace generic warnings with contextual, action-oriented copy
- Show free-quota progress in relevant moments (not spammy)
- Add clear "what happens next" wording for limits and upgrades

Acceptance:

- User understands why an action is blocked and next step
- Messaging shown only when relevant
- DE/EN i18n coverage complete for all new strings

### 4. Safe-Review Guidance

- Highlight low-confidence and uncertain groups with short guidance text
- Show "recommended next action" in review header
- Keep hints concise and dismissible

Acceptance:

- Hints reduce ambiguity without hiding core controls
- No interference with keyboard-driven workflows

## Technical Plan

### UI Components

- Extend main review toolbar in modern window for filter controls
- Add onboarding dialog component and persistent setting key
- Add lightweight guidance label in group/detail header

### Data/State

- Persist onboarding completion in user settings
- Reuse existing confidence and needs-review metadata for filters
- Keep filter logic deterministic and testable

### Testing

- Unit tests:
  - filter predicate behavior
  - onboarding state persistence
  - message builder logic for quota/upgrade
- Integration tests:
  - first-run flow (onboarding shown once)
  - filter + navigation interplay
  - no regressions on delete/export safety flows

## Week 4 Execution Order

1. Onboarding state + dialog skeleton
2. Smart filter logic and UI toggles
3. Quota/upgrade messaging cleanup
4. Safe-review hints and final polish
5. Regression and smoke-test pass

## Definition of Done

- All Week 4 deliverables implemented with DE/EN strings
- New unit and integration tests green
- MSI smoke test confirms first-run onboarding and filter behavior
- No regression in Week 3 delete/export safety paths
