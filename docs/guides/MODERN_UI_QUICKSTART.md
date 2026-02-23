# PhotoCleaner Modern UI - Quick Start Guide

## Installation

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt
```

## Quick Start

### Option 1: Test with Fake Data
```bash
# Create test database
python create_test_db.py

# Launch modern UI
python test_modern_ui.py
```

### Option 2: Use with Real Photos
```bash
# Run full pipeline (index + find duplicates)
python -m photo_cleaner.cli scan /path/to/photos

# Launch modern UI with generated database
python -c "from photo_cleaner.ui.modern_window import run_modern_ui; run_modern_ui('photo_cleaner.db')"
```

## 5-Minute Tutorial

### 1. **Navigation**
- Click a group in the left panel
- Grid shows all images in that group
- ⭐ = Recommended (auto-selected best image)

### 2. **Inspect Quality**
- Click any thumbnail card
- Detail view opens with zoom controls
- Use mousewheel to zoom in/out
- Drag to pan around image
- Check EXIF data in right panel

### 3. **Make Decisions**
- Close detail view (or press Escape)
- Click card to select it
- Press `K` to keep (green)
- Press `D` to delete (red)
- Press `U` if unsure (orange)

### 4. **Lock Protection**
- Press `Space` to lock important images
- Locked images (🔒) are protected from bulk actions

### 5. **Undo Mistakes**
- Press `Z` to undo last action
- Undo history is preserved

### 6. **Export**
- Click "Finalize & Export" when done
- All KEEP images are copied to output folder
- Organized in YYYY/MM/DD structure

## Essential Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `K` | Keep image |
| `D` | Delete image |
| `U` | Mark unsure |
| `Space` | Lock/unlock |
| `Z` | Undo |
| `Ctrl+J` | Next group |
| `Ctrl+K` | Previous group |
| `?` | Show all shortcuts |

## Zoom Controls (in Detail View)

| Control | Action |
|---------|--------|
| Mousewheel | Zoom in/out |
| Ctrl+Wheel | Fine zoom |
| `+` / `-` | Step zoom |
| `0` | Reset zoom |
| Double-click | Fit to view |
| Drag | Pan image |

## Visual Indicators

### Status Colors
- 🟢 **Green:** KEEP (will be exported)
- 🔴 **Red:** DELETE (will be discarded)
- 🟠 **Orange:** UNSURE (needs review)
- ⚪ **Gray:** UNDECIDED (not yet reviewed)

### Badges
- ⭐ **Star:** Recommended (auto-selected best quality)
- 🔒 **Lock:** Protected from accidental changes

### Group Status
- ✓ **Green:** All files decided
- ⚠ **Orange:** Has deletions
- ○ **Gray:** Not yet reviewed

## Tips & Tricks

### Fast Review Workflow
1. Let auto-selection do the work (⭐ images are pre-selected)
2. Only review images you're unsure about
3. Use `Z` liberally - undo is instant
4. Lock your favorites immediately with `Space`

### Quality Assessment
1. Open detail view and zoom to 100%+
2. Check sharpness in faces/text
3. Compare EXIF settings (ISO, shutter speed)
4. Higher resolution doesn't always mean better quality

### Batch Processing
1. Use search to filter specific groups
2. Navigate with `Ctrl+J` / `Ctrl+K`
3. Make decisions without using mouse
4. Export periodically to save progress

## Themes

Switch theme via dropdown in top bar:

- **Dark (Default):** Best for extended use, reduces eye strain
- **Light:** Clean interface for bright environments  
- **System:** Matches your OS theme automatically
- **High-Contrast:** Accessibility mode with maximum contrast

## Modes

Switch mode via dropdown in top bar:

- **SAFE:** Read-only, no changes possible
- **REVIEW:** Can mark files, deletion staged only
- **CLEANUP:** Full access, can delete files permanently

⚠️ **Important:** Start with REVIEW mode, switch to CLEANUP only when ready to execute deletions.

## Common Questions

**Q: Can I compare two images side-by-side?**  
A: Not yet - open each in detail view separately. Feature planned for future.

**Q: Where are thumbnails cached?**  
A: In `.cache/thumbnails/` - safe to delete, will regenerate.

**Q: Can I export to different folder per group?**  
A: Not currently - all KEEP images go to one output folder with date structure.

**Q: What if I accidentally delete the wrong image?**  
A: Press `Z` immediately to undo. Full undo history is maintained.

**Q: Does zoom affect the actual image?**  
A: No - zoom is view-only. Original images are never modified.

## Performance Tips

### For Large Collections (10,000+ images)
- Use search to filter groups
- Process in batches (1000 images at a time)
- Export periodically to free up decided groups

### For Slow Zooming
- Reduce detail view max size (edit modern_window.py line ~780)
- Use SSD for image storage
- Close other applications to free RAM

## Getting Help

- Press `?` in app for keyboard shortcuts
- See `docs/MODERN_UI.md` for full documentation
- Check GitHub issues for known problems
- Report bugs with screenshots

## Next Steps

After mastering the basics:

1. **Explore EXIF Data:** Learn what camera settings produce best images
2. **Use Keyboard Shortcuts:** 2x faster workflow
3. **Customize Themes:** Find what works for your eyes
4. **Export Often:** Don't lose decisions if app crashes
5. **Share Feedback:** Help improve the UI

---

**Happy Cleaning! 📸✨**
