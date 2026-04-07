# Week 1 Trust Foundation

## Goal

Week 1 builds the first visible trust layer for review: explainable scores, an initial confidence signal, and the technical baseline for later merge/split and undo work.

The main product problem is not raw automation quality. It is that users cannot quickly understand why a photo was recommended and when they should double-check the result.

## Scope

This week covers three streams:

1. Explainable Score Breakdown
2. Confidence Badge plus Needs-Review heuristic
3. Technical prep for Merge/Split and Undo

## Explainable Score Breakdown

The current pipeline already persists these components on the files table:

- quality_score
- sharpness_component
- lighting_component
- resolution_component
- face_quality_component

Week 1 uses those fields directly in the Modern UI instead of showing only a flat total score.

### UX rule

Every detailed image view should answer three questions in under three seconds:

1. Why was this image scored this way?
2. What is the strongest signal?
3. What looks weak enough that I should manually verify it?

### First implementation slice

- Show overall score plus per-component breakdown in the Modern detail views.
- Add a short text summary: strongest driver and weakest component.
- Add explicit strengths and concerns text.
- Preserve a fallback for old data that only contains an overall score.

### Data rule

`NULL` component values must stay `NULL` in the UI loading path.

This is important because `COALESCE(..., 0)` makes missing analysis look like a real 0 percent result and produces misleading explanations.

## Confidence Badge

Week 1 does not attempt a complex ML confidence model. It starts with a deterministic heuristic on top of existing component scores.

### Initial heuristic

- High confidence:
  overall score is strong, no weak component, all core signals stable
- Medium confidence:
  mixed but acceptable signals, user should briefly verify
- Low confidence:
  two or more weak components, very low total score, or a clearly weak single signal
- Incomplete:
  only legacy total score exists and the image should be re-analyzed for details

### Product meaning

- High confidence reduces review friction.
- Medium confidence keeps the user in the loop.
- Low confidence is the first building block for a future Needs-Review queue.

## Merge/Split Prep

Merge/Split is not implemented in this slice, but the design should assume:

- group-level confidence can later aggregate file-level confidence
- action history must record manual regrouping events
- merge and split must be reversible through the same undo pipeline as manual keep/delete changes

Relevant code paths already identified:

- `src/photo_cleaner/core/duplicate_groups.py`
- `src/photo_cleaner/session_manager.py`
- `src/photo_cleaner/ui/modern_window.py`
- `src/photo_cleaner/ui_actions.py`

## Acceptance Criteria

- Modern detail views show explainable score output, not only a flat total.
- Old rows with only `quality_score` show an explicit re-analysis hint.
- The UI never renders fake 0 percent components for missing data.
- Score-to-confidence mapping is covered by unit tests.

## Status

Started in this slice:

- added a reusable score explanation helper
- wired explainability into Modern UI detail surfaces
- added unit tests for confidence mapping and legacy-score fallback

Next slices:

1. route low-confidence items into a review queue
2. add group-level confidence and group diagnostics
3. implement merge/split persistence plus undo integration