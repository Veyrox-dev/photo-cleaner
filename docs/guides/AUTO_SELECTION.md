# Auto-Best-Image Selection Feature

## Overview

The Auto-Best-Image Selection feature automatically identifies and marks the best image in each duplicate group based on deterministic quality criteria. This helps users make informed decisions without overwhelming them with manual analysis.

## Key Features

### 1. **Deterministic Selection**
- Not a "black box" ML algorithm
- Uses transparent, rule-based scoring
- Users can understand why an image was chosen

### 2. **Quality Criteria (Weighted)**
The selection considers multiple factors with the following weights:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Sharpness** | 35% | Laplacian variance (focus quality) |
| **Lighting** | 25% | Exposure balance (not too dark/bright) |
| **Resolution** | 20% | Image dimensions (width × height) |
| **Face Quality** | 15% | Open eyes detection, face orientation |
| **Recency** | 5% | EXIF datetime (newer = better for same scene) |

### 3. **Face Detection Scoring**
- Eyes open + frontal face: 70-100 points
- Eyes closed (malus): 20 points
- No face detected: 60 points (neutral)

### 4. **User Control**
- ❌ **NO auto-deletion** - recommendations only
- ✅ User can override any recommendation
- ✅ Manual KEEP selection updates recommendation
- ✅ Visual feedback with ⭐ badge

## Technical Implementation

### Database Schema Changes (v4)

Two new columns in the `files` table:

```sql
is_recommended BOOLEAN DEFAULT 0,      -- Flag: "this is the best image"
keeper_source TEXT DEFAULT 'undecided' -- Values: 'auto', 'manual', 'undecided'
```

### Pipeline Integration

The auto-selection runs in **Stage 5 (Scoring)** of the pipeline:

1. Quality analysis completes for all images
2. For each duplicate group:
   - Calculate weighted scores for all images
   - Select the best image
   - Mark as `is_recommended=1, keeper_source='auto'`
3. Results stored in database

### UI Integration

The main window (`main_window.py`) displays recommended images with:

- **⭐ Badge**: Prepended to filename in thumbnail list
- **Green Background**: Highlighted with `#4CAF50` color (80% alpha)
- **Tooltip**: Shows "(EMPFOHLEN)" in tooltip
- **Details Panel**: Displays "⭐ EMPFOHLEN (Auto-Auswahl)"

#### User Interaction

When the user manually selects KEEP on a different image:
1. All recommendations in the group are cleared
2. The new image is marked as `is_recommended=1, keeper_source='manual'`
3. UI updates to show the new recommendation

## Backend Components

### 1. `auto_selector.py`

Main selection logic:

```python
class AutoSelector:
    def select_best_image(
        images: list[Path], 
        quality_results: dict
    ) -> tuple[Path, ImageScoreComponents]:
        # Calculates weighted scores
        # Returns best image + score breakdown
```

### 2. `scorer.py`

Extended with:

```python
def auto_select_best_image(
    group_id: str,
    quality_results: list[QualityResult]
) -> Optional[Path]:
    # Wrapper for AutoSelector
    # Logs selection reason
```

### 3. `pipeline.py`

Integration in Stage 5:

```python
def _stage_score_and_mark():
    # After scoring each group:
    best_image = scorer.auto_select_best_image(group_id, results)
    if best_image:
        # Update DB: is_recommended=1, keeper_source='auto'
```

### 4. `main_window.py`

UI updates:

```python
class FileRow:
    # Added field:
    is_recommended: bool = False

def _load_group_files():
    # SQL query includes: COALESCE(f.is_recommended, 0)
    # Sort: recommended images first

def _set_recommended(path):
    # Clear all recommendations in group
    # Set new recommendation
```

## Usage

### 1. Run Pipeline

```bash
python debug_pipeline.py
```

This will:
- Index all images
- Detect duplicates
- Analyze quality
- **Auto-select best image per group** ⭐
- Store recommendations in database

### 2. Verify Auto-Selection

```bash
python test_auto_selection.py
```

Expected output:
```
✅ Column 'is_recommended' exists
📊 Total recommended images: 8
✅ Recommendations found in 8 groups:
   ✓ Group 0: 1 recommended image(s)
   ✓ Group 1: 1 recommended image(s)
   ...
```

### 3. Open UI

```bash
python run_ui.py --db test_pipeline_debug.db
```

Look for:
- ⭐ badge on recommended images
- Green background highlight
- "(EMPFOHLEN)" in tooltip
- Details panel shows recommendation status

### 4. Override Recommendation

1. Select a different image in the group
2. Press `K` (or click KEEP button)
3. ⭐ badge moves to the new image
4. `keeper_source` changes from `'auto'` to `'manual'`

## Testing Checklist

- [ ] Pipeline runs without errors
- [ ] Each duplicate group has exactly 1 recommended image
- [ ] UI displays ⭐ badge correctly
- [ ] Green background visible on recommended images
- [ ] Tooltip shows "(EMPFOHLEN)"
- [ ] Details panel shows "⭐ EMPFOHLEN (Auto-Auswahl)"
- [ ] Manual KEEP updates recommendation
- [ ] Recommendation persists after reload
- [ ] Works with HEIC images (pillow-heif registered)

## Design Philosophy

### Why Deterministic, Not ML?

1. **Trust**: Users understand the criteria
2. **Transparency**: Scores are explainable
3. **Control**: Users can override any decision
4. **Consistency**: Same inputs = same output

### Why No Auto-Delete?

1. **Safety**: Accidental deletion prevention
2. **Trust Building**: User reviews recommendations first
3. **Flexibility**: User might want to keep multiple images
4. **Context**: User knows the scene better than algorithm

## Future Enhancements

Potential additions (not currently implemented):

- [ ] Tooltip shows score breakdown (sharpness: X, lighting: Y, etc.)
- [ ] Keyboard shortcut to accept recommendation (e.g., Space)
- [ ] "Accept All Recommendations" batch button
- [ ] Display reason for selection in UI
- [ ] User-configurable weights (advanced settings)

## Troubleshooting

### Issue: No ⭐ badges visible

**Cause**: Auto-selection didn't run or database is old

**Solution**:
1. Check schema version: `SELECT value FROM meta WHERE key='schema_version'` → should be `4`
2. Re-run pipeline: `python debug_pipeline.py`
3. Verify: `python test_auto_selection.py`

### Issue: Multiple images marked in one group

**Cause**: Logic error or manual database edit

**Solution**:
1. Check pipeline logs for errors
2. Manually fix: 
   ```sql
   UPDATE files SET is_recommended = 0 WHERE group_id = 'X';
   UPDATE files SET is_recommended = 1 WHERE path = 'Y';
   ```

### Issue: Recommendation doesn't update on KEEP

**Cause**: UI not connected to `_set_recommended()` method

**Solution**:
1. Verify `_apply_status()` calls `self._set_recommended(fr.path)` for KEEP
2. Check database after setting KEEP: 
   ```sql
   SELECT path, is_recommended, keeper_source FROM files WHERE group_id = 'X';
   ```

## Code References

- Auto-selection logic: [`auto_selector.py`](src/photo_cleaner/pipeline/auto_selector.py)
- Pipeline integration: [`pipeline.py`](src/photo_cleaner/pipeline/pipeline.py#L376)
- Scorer extension: [`scorer.py`](src/photo_cleaner/pipeline/scorer.py#L223)
- Database schema: [`schema.py`](src/photo_cleaner/db/schema.py)
- UI implementation: [`main_window.py`](src/photo_cleaner/ui/main_window.py)

## Related Issues

- [x] HEIC support fixed (pillow-heif registration)
- [x] Face detection working (MediaPipe 0.10.31)
- [x] Quality analysis complete (sharpness, lighting, resolution)
- [x] Auto-selection integrated (Stage 5)
- [x] UI displaying recommendations
