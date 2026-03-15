from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PreparedAnalysisImage:
    img: Any
    pil_img: Any
    original_width: int
    original_height: int


def prepare_image_for_quality_analysis(
    image_path: Path,
    *,
    cv2_module,
    np_module,
    image_module,
    mtcnn_available: bool,
    mtcnn_detector_cache,
    max_analysis_dimension: int = 2000,
    logger=None,
) -> PreparedAnalysisImage | None:
    """Load image + optional downsampling, preserving original dimensions for scoring."""
    if cv2_module is None:
        return None

    img = None
    pil_img = None
    original_width = None
    original_height = None
    pil_downsampled = False

    downsample_enabled = True
    if mtcnn_available and mtcnn_detector_cache is not None:
        downsample_enabled = False
        if logger:
            logger.debug("  [PERF] Downsampling disabled (MTCNN requires higher resolution)")

    try:
        img = cv2_module.imread(str(image_path))
        if img is not None:
            original_height, original_width = img.shape[:2]
    except Exception:
        pass

    if img is None and image_module is not None:
        try:
            pil_img = image_module.open(image_path)
            original_width, original_height = pil_img.size

            if downsample_enabled and (
                original_width > max_analysis_dimension
                or original_height > max_analysis_dimension
            ):
                target_size = (max_analysis_dimension, max_analysis_dimension)
                try:
                    pil_img.draft("RGB", target_size)
                except Exception:
                    pass

                resample = image_module.Resampling.LANCZOS if hasattr(image_module, "Resampling") else image_module.LANCZOS
                pil_img.thumbnail(target_size, resample)
                pil_downsampled = True
                if logger:
                    logger.debug(
                        f"  [PERF] Downsampling (PIL) {original_width}x{original_height} "
                        f"-> {pil_img.size[0]}x{pil_img.size[1]} for quality analysis"
                    )

            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            rgb = np_module.asarray(pil_img)
            img = rgb[:, :, ::-1].copy()
        except (OSError, IOError, AttributeError, ValueError) as e:
            if logger:
                logger.debug(f"PIL fallback failed for {image_path}: {e}", exc_info=True)

    if img is None:
        return None

    if pil_img is None and image_module is not None:
        try:
            pil_img = image_module.open(image_path)
        except (OSError, IOError):
            if logger:
                logger.debug(f"Could not open image with PIL for EXIF: {image_path}", exc_info=True)

    if original_width is None or original_height is None:
        original_height, original_width = img.shape[:2]

    if downsample_enabled and not pil_downsampled and (
        original_width > max_analysis_dimension or original_height > max_analysis_dimension
    ):
        scale_factor = min(
            max_analysis_dimension / original_width,
            max_analysis_dimension / original_height,
        )
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)

        if logger:
            logger.debug(
                f"  [PERF] Downsampling {original_width}x{original_height} → {new_width}x{new_height} "
                f"(scale={scale_factor:.2f}) for quality analysis"
            )

        img = cv2_module.resize(img, (new_width, new_height), interpolation=cv2_module.INTER_AREA)

    return PreparedAnalysisImage(
        img=img,
        pil_img=pil_img,
        original_width=original_width,
        original_height=original_height,
    )
