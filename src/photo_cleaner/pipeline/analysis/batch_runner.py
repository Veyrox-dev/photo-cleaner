from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable


def run_quality_batch(
    *,
    image_paths: list[Path],
    analyze_image: Callable[[Path], object],
    progress_callback: Callable[[int, int], None] | None,
    max_workers: int,
    logger,
    error_result_factory: Callable[[Path, Exception], object],
) -> list[object]:
    """Run quality analysis for multiple images in parallel while preserving order."""
    results: list[object] = [None] * len(image_paths)
    processed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(analyze_image, path): idx
            for idx, path in enumerate(image_paths)
        }

        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                results[idx] = future.result()
            except Exception as error:
                logger.error(f"Error analyzing {image_paths[idx]}: {error}", exc_info=True)
                results[idx] = error_result_factory(image_paths[idx], error)

            processed_count += 1

            if progress_callback:
                try:
                    progress_callback(processed_count, len(image_paths))
                except (TypeError, AttributeError):
                    logger.debug("Progress callback error", exc_info=True)

            if processed_count % 5 == 0 or processed_count == len(image_paths):
                logger.info(f"Analyzed {processed_count}/{len(image_paths)} images")

    return results
