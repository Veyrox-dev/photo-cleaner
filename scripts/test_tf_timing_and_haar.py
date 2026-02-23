"""One-shot TensorFlow import timing and Haar cascade resolver check."""

from __future__ import annotations

import os
import time


def main() -> None:
    t0 = time.perf_counter()
    import tensorflow as tf  # pylint: disable=import-error

    dt = time.perf_counter() - t0
    cuda = os.environ.get("CUDA_VISIBLE_DEVICES")
    print("TF import", tf.__version__, "in", f"{dt:.2f}s", f"(CUDA_VISIBLE_DEVICES={cuda})")

    from photo_cleaner.pipeline.quality_analyzer import _resolve_haar_cascade_dir

    cascade_dir = _resolve_haar_cascade_dir()
    print("Haar cascade dir:", cascade_dir)


if __name__ == "__main__":
    main()
