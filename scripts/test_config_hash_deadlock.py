"""Stress test for Config-Hash initialization and QualityAnalyzer creation.

Runs sequential and multi-threaded QualityAnalyzer instantiation to detect
potential deadlocks around AppConfig and config-hash initialization.
"""

from __future__ import annotations

import threading
import time
from typing import List, Tuple

from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer


def _worker(worker_id: int, loops: int, results: List[Tuple[int, float, str]]) -> None:
    start = time.time()
    error = ""
    try:
        for i in range(loops):
            qa = QualityAnalyzer(use_face_mesh=False)
            del qa
            if (i + 1) % 10 == 0:
                print(f"[worker {worker_id}] {i + 1}/{loops} initialized")
    except Exception as exc:  # pylint: disable=broad-except
        error = f"{type(exc).__name__}: {exc}"
    duration = time.time() - start
    results.append((worker_id, duration, error))


def run_sequential(loops: int) -> None:
    print("[sequential] start")
    start = time.time()
    for i in range(loops):
        qa = QualityAnalyzer(use_face_mesh=False)
        del qa
        if (i + 1) % 10 == 0:
            print(f"[sequential] {i + 1}/{loops} initialized")
    duration = time.time() - start
    print(f"[sequential] done in {duration:.2f}s")


def run_parallel(threads: int, loops_per_thread: int, timeout_s: int) -> None:
    print("[parallel] start")
    results: List[Tuple[int, float, str]] = []
    workers = [
        threading.Thread(target=_worker, args=(i, loops_per_thread, results), daemon=True)
        for i in range(threads)
    ]

    for t in workers:
        t.start()

    start = time.time()
    for t in workers:
        t.join(timeout=timeout_s)

    elapsed = time.time() - start
    unfinished = [t for t in workers if t.is_alive()]

    if unfinished:
        print(f"[parallel] WARNING: {len(unfinished)} thread(s) still running after {timeout_s}s")
    else:
        print(f"[parallel] done in {elapsed:.2f}s")

    for worker_id, duration, error in sorted(results, key=lambda item: item[0]):
        status = "OK" if not error else f"ERROR: {error}"
        print(f"[worker {worker_id}] {status} in {duration:.2f}s")


def main() -> None:
    loops = 100
    threads = 10
    timeout_s = 300

    run_sequential(loops)
    run_parallel(threads, loops_per_thread=10, timeout_s=timeout_s)


if __name__ == "__main__":
    main()
