"""
Worker Process Implementation for Photo Analysis

Processes a single image through the complete analysis pipeline.
Can be run in worker process without shared mutable state.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import traceback

logger = logging.getLogger(__name__)


def analyze_image_worker(image_path: Path, config: Any) -> Dict[str, Any]:
    """
    Process a single image through the complete analysis pipeline.
    
    This function is designed to run in a worker process. It:
    - Loads the image
    - Analyzes face/eye quality
    - Scores the image
    - Handles all exceptions internally
    
    Args:
        image_path: Path to image file
        config: Configuration object containing:
            - quality_analyzer: QualityAnalyzer instance
            - scorer: ImageScorer instance
            - cheap_filter: CheapFilter instance (optional)
    
    Returns:
        Dict with analysis results:
        {
            'success': bool,
            'score_components': ScoreComponents or None,
            'quality_result': FaceQuality or None,
            'cheap_filter_score': float or None,
            'disqualified': bool,
            'error': str or None,
        }
    """
    image_path = Path(image_path)
    
    # P1.1: Defensive null-checks for config and quality_analyzer
    if config is None:
        logger.error(f"Worker received None config for {image_path}")
        return {
            'success': False,
            'score_components': None,
            'quality_result': None,
            'cheap_filter_score': None,
            'disqualified': True,
            'error': 'Configuration error: config is None',
        }
    
    if not hasattr(config, 'quality_analyzer') or config.quality_analyzer is None:
        logger.error(f"Worker config missing quality_analyzer for {image_path}")
        return {
            'success': False,
            'score_components': None,
            'quality_result': None,
            'cheap_filter_score': None,
            'disqualified': True,
            'error': 'Configuration error: quality_analyzer is None',
        }
    
    try:
        # Stage 1: Cheap Filter (if available)
        cheap_filter_score = None
        if hasattr(config, 'cheap_filter') and config.cheap_filter is not None:
            try:
                cheap_filter_score = config.cheap_filter.score(image_path)
                # Cheap filter returns None if image fails basic checks
                if cheap_filter_score is None:
                    return {
                        'success': True,
                        'score_components': None,
                        'quality_result': None,
                        'cheap_filter_score': None,
                        'disqualified': True,
                        'error': 'Failed cheap filter',
                    }
            except Exception as e:
                logger.warning(f"Cheap filter failed for {image_path}: {e}")
                # Don't fail completely, continue to analysis
        
        # Stage 2: Quality Analysis (face/eye detection)
        try:
            quality_result = config.quality_analyzer.analyze_image(image_path)
        except Exception as e:
            logger.exception(f"Quality analysis failed for {image_path}")
            return {
                'success': False,
                'score_components': None,
                'quality_result': None,
                'cheap_filter_score': cheap_filter_score,
                'disqualified': True,
                'error': f'Quality analysis failed: {str(e)}',
            }
        
        # Stage 3: Check hard rule (eyes must be open)
        if quality_result is None:
            return {
                'success': True,
                'score_components': None,
                'quality_result': None,
                'cheap_filter_score': cheap_filter_score,
                'disqualified': True,
                'error': 'No quality result (possibly no faces detected)',
            }
        
        # Hard rule: If ANY person has closed eyes, disqualify immediately
        if not quality_result.all_eyes_open:
            return {
                'success': True,
                'score_components': None,
                'quality_result': quality_result,
                'cheap_filter_score': cheap_filter_score,
                'disqualified': True,
                'error': 'Hard rule violation: Closed eyes detected',
            }
        
        # Stage 4: Scoring
        try:
            score_components = config.scorer.score_image(
                image_path,
                quality_result,
                cheap_filter_score=cheap_filter_score,
            )
        except Exception as e:
            logger.exception(f"Scoring failed for {image_path}")
            return {
                'success': False,
                'score_components': None,
                'quality_result': quality_result,
                'cheap_filter_score': cheap_filter_score,
                'disqualified': True,
                'error': f'Scoring failed: {str(e)}',
            }
        
        # Success
        return {
            'success': True,
            'score_components': score_components,
            'quality_result': quality_result,
            'cheap_filter_score': cheap_filter_score,
            'disqualified': False,
            'error': None,
        }
    
    except Exception as e:
        logger.exception(f"Unexpected error processing {image_path}")
        return {
            'success': False,
            'score_components': None,
            'quality_result': None,
            'cheap_filter_score': None,
            'disqualified': True,
            'error': f'Unexpected error: {str(e)}',
        }
