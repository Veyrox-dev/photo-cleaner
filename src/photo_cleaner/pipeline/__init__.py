"""
PhotoCleaner Pipeline Package

Final optimized pipeline for photo cleanup with minimal AI overhead.
"""

from photo_cleaner.pipeline.pipeline import run_final_pipeline
from photo_cleaner.pipeline.cheap_filter import CheapFilter

# Lazy load QualityAnalyzer and GroupScorer to avoid numpy initialization on import
_QualityAnalyzer = None
_GroupScorer = None

def __getattr__(name):
    """Lazy load heavy modules on first access."""
    if name == "QualityAnalyzer":
        global _QualityAnalyzer
        if _QualityAnalyzer is None:
            from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer as _QA
            _QualityAnalyzer = _QA
        return _QualityAnalyzer
    elif name == "GroupScorer":
        global _GroupScorer
        if _GroupScorer is None:
            from photo_cleaner.pipeline.scorer import GroupScorer as _GS
            _GroupScorer = _GS
        return _GroupScorer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
