# QA Baseline Comparison Report (Risk-Based Scope)

Date: 2026-04-06
Scope: Consolidate available QA artifacts and define a practical baseline strategy for real usage.

## 1) Data sources used

- `results/threadpool_test_1k.json`
- `results/threadpool_test_5k.json`
- `results/async_write_test_1k.json`
- `results/async_write_test_5k.json`
- `results/async_write_test_5k_batch500.json`
- `results/quality_profile_5k.json`
- `results/stress_test_results.json`

## 2) Consolidated baseline table

| Dataset | Run type | Success | Duration (s) | Throughput | Notes |
|---|---|---:|---:|---:|---|
| 1k | ThreadPool | yes | 30.87 | 32.40 img/s | speedup 4.67x vs baseline 144.14s |
| 1k | Async Write Queue | yes | 20.44 | 48.93 img/s | speedup 7.05x vs baseline 144.14s |
| 5k | ThreadPool | yes | 142.36 | 35.12 img/s | near baseline, status ACCEPTABLE |
| 5k | Async Write Queue | yes | 170.07 | 29.40 img/s | slower than baseline |
| 5k | Async Write Queue (batch=500) | yes | 148.52 | 33.67 img/s | improved vs async default, still below ThreadPool |
| 5k | Quality Analyzer profile | yes | 1172.44 | 4.26 img/s | full analyzer profile, not directly comparable to pipeline-only runs |
| 10k | Stress harness run #1 | no | 0.10 | 101787.44 img/s | invalid measurement (`return_code=2`) |
| 10k | Stress harness run #2 | no | 0.08 | 118281.68 img/s | invalid measurement (`return_code=1`) |
| 10k | Stress harness run #3 | no | 0.15 | 66216.27 img/s | invalid measurement (`return_code=1`) |
| 10k | Stress harness run #4 | no | 0.23 | 43134.41 img/s | invalid measurement (`return_code=1`) |
| 10k | Stress harness run #5 | no | 0.48 | 20803.99 img/s | invalid measurement (`return_code=1`) |
| 50k | Baseline | no data | - | - | out of primary scope (non-blocking) |
| 100k | Baseline | no data | - | - | out of primary scope (non-blocking) |

## 3) Interpretation

- 1k/5k: usable historical baseline exists and is representative for expected usage.
- 10k: artifacts exist but all runs failed (`success=false`); keep as optional stress/soak scenario.
- 50k/100k: no artifacts available; keep out of blocking QA scope.

Conclusion: baseline strategy finalized as risk-based QA model.

## 4) Recommended execution order to finish point 15

1. Keep 1k/5k baselines as release-gate checks.
2. Run 10k only for performance investigations or pre-release soak tests.
3. Treat 50k/100k as research scenarios (non-blocking), not mandatory release criteria.

Suggested command:

```powershell
$env:PYTHONPATH='src'; python scripts/profile_phase2_baseline.py --test-data stress_test_datasets --output profiling_results
```

Optional stress-test dataset structure:

- `stress_test_datasets/10k/`
- `stress_test_datasets/50k/`
- `stress_test_datasets/100k/`

(Or adapt `--test-data` to the folder that contains `1k/5k/10k/50k/100k` subfolders.)
