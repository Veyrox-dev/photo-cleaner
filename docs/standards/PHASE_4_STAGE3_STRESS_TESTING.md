# Phase 4 Stage 3: Stress Testing (10k - 100k Images)

Date: 2026-02-06
Owner: PhotoCleaner QA
Status: In Progress

## Goals
- Validate full pipeline stability and performance at 10k, 50k, 100k images.
- Identify the longest-running step and top bottlenecks.
- Capture reproducible timing and memory data.

## Data Sets
Source: C:\Users\chris\OneDrive\Bilder\01_Photocleaner\Input
Output root: test_data_system

Planned sets:
- 10k images: test_data_system/10k
- 50k images: test_data_system/50k
- 100k images: test_data_system/100k

Notes:
- Duplication is allowed for throughput testing when unique images are insufficient.

## Setup
### 1 Build datasets
Command:
```bash
C:/Users/chris/projects/photo-cleaner/.venv/Scripts/python.exe scripts/setup_test_data.py \
  --source "C:\Users\chris\OneDrive\Bilder\01_Photocleaner\Input" \
  --output test_data_system \
  --include-50k \
  --include-100k
```

Expected output:
- test_data_system/10k
- test_data_system/50k
- test_data_system/100k

### 2 Run full pipeline profiling
Command:
```bash
C:/Users/chris/projects/photo-cleaner/.venv/Scripts/python.exe scripts/profile_phase2_baseline.py \
  --test-data test_data_system \
  --output profiling_results
```

Outputs:
- profiling_results/profile_10k.db
- profiling_results/profile_50k.db
- profiling_results/profile_100k.db
- profiling_results/phase2_baseline_YYYYMMDD.json

## Measurements Captured
- Total duration (seconds)
- Per-image average (ms)
- Peak memory delta (MB)
- Top 5 bottlenecks (cProfile cumulative time)

## Longest Step Identification
Method:
- Use cProfile output from profile_phase2_baseline.py
- Aggregate Top 5 by cumulative time across 10k/50k/100k runs

Expected (to confirm with data):
- Likely dominant: face detection / quality analysis in quality_analyzer
- Secondary: image decode + EXIF IO
- Third: cache/database writes

## Run Log
### 10k Run
- Start:
- End:
- Duration:
- Per-image avg:
- Memory delta:
- Top bottleneck:

### 50k Run
- Start:
- End:
- Duration:
- Per-image avg:
- Memory delta:
- Top bottleneck:

### 100k Run
- Start:
- End:
- Duration:
- Per-image avg:
- Memory delta:
- Top bottleneck:

## Findings (to be filled after runs)
- Longest step:
- Scaling behavior:
- Bottleneck changes vs scale:
- Regression risks:

## Next Actions
- If face detection dominates: consider further downsampling or batch scheduling.
- If IO dominates: check thumbnail cache hits and disk throughput.
- If DB dominates: profile WAL mode, indexes, batch sizes.
