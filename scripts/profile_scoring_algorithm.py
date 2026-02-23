"""Scoring Algorithm Analysis Script

Analyzes how the current quality scoring algorithm makes decisions:
- Which factors influence the score most?
- How are face quality, sharpness, lighting weighted?
- Are there outliers (high score but bad image, or vice versa)?
- Distribution of scores across test images

Usage:
    python scripts/profile_scoring_algorithm.py --input test_data_system/5k --output profiling_results/scoring_analysis.json
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import statistics

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from photo_cleaner.db.schema import Database
from photo_cleaner.pipeline.quality_analyzer import QualityAnalyzer
from photo_cleaner.core.indexer import PhotoIndexer


def analyze_scoring(input_folder: Path, db_path: Path, output_file: Path, sample_size: int = 100):
    """Analyze scoring algorithm on sample images."""
    
    print(f"\n{'='*70}")
    print(f"SCORING ALGORITHM ANALYSIS")
    print(f"{'='*70}\n")
    
    print(f"📂 Input folder: {input_folder}")
    print(f"📊 Sample size: {sample_size} images")
    print(f"💾 Database: {db_path}")
    print(f"📄 Output: {output_file}\n")
    
    # Initialize components
    db = Database(db_path)
    db.connect()
    
    indexer = PhotoIndexer(db, max_workers=4)
    analyzer = QualityAnalyzer(use_face_mesh=True)
    
    # Index images
    print("⏳ Indexing images...")
    stats = indexer.index_folder(input_folder, skip_existing=False)
    print(f"✅ Indexed {stats['processed']} images (failed: {stats['failed']})\n")
    
    # Get sample images
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT file_id, path, file_size, 0 as width, 0 as height 
        FROM files 
        ORDER BY path
        LIMIT ?
    """, (sample_size,))
    
    images = cursor.fetchall()
    print(f"📸 Analyzing {len(images)} images...\n")
    
    # Analyze each image and collect detailed metrics
    results = []
    
    for idx, (photo_id, file_path, file_size, width, height) in enumerate(images, 1):
        # Convert string path to Path object
        file_path_obj = Path(file_path)
        print(f"[{idx}/{len(images)}] {file_path_obj.name}")
        
        # Run quality analysis
        quality_result = analyzer.analyze_image(file_path_obj)
        
        if quality_result.error:
            print(f"  ❌ Error: {quality_result.error}")
            continue
        
        # Extract detailed metrics
        metrics = {
            "file_path": str(file_path_obj),
            "file_name": file_path_obj.name,
            "resolution": f"{quality_result.width}×{quality_result.height}",
            "megapixels": round(quality_result.width * quality_result.height / 1_000_000, 1),
            
            # Overall score
            "quality_score": round(quality_result.total_score, 2),
            
            # Component scores
            "sharpness_score": round(quality_result.overall_sharpness, 2),
            "lighting_score": round(quality_result.lighting_score, 2),
            "resolution_score": round(quality_result.resolution_score, 2),
            
            # Face analysis
            "has_faces": quality_result.face_quality is not None and quality_result.face_quality.has_face,
            "face_count": quality_result.face_quality.face_count if quality_result.face_quality else 0,
            "all_eyes_open": quality_result.face_quality.all_eyes_open if quality_result.face_quality else None,
            
            # Metadata
            "iso": quality_result.iso_value,
            "exposure_time": quality_result.exposure_time,
            "f_number": quality_result.aperture_value,
            "camera_model": quality_result.camera_model,
        }
        
        results.append(metrics)
        
        # Print summary
        print(f"  Score: {metrics['quality_score']:.1f} | ", end="")
        print(f"Sharp: {metrics['sharpness_score']:.1f} | ", end="")
        print(f"Light: {metrics['lighting_score']:.1f} | ", end="")
        if metrics['has_faces']:
            eyes = "👁️ Open" if metrics['all_eyes_open'] else "👁️ Closed"
            print(f"Faces: {metrics['face_count']} {eyes}")
        else:
            print("No faces")
    
    # Statistical analysis
    print(f"\n{'='*70}")
    print("STATISTICAL ANALYSIS")
    print(f"{'='*70}\n")
    
    scores = [r['quality_score'] for r in results]
    sharpness_scores = [r['sharpness_score'] for r in results]
    lighting_scores = [r['lighting_score'] for r in results]
    
    stats_summary = {
        "total_images": len(results),
        "score_distribution": {
            "mean": round(statistics.mean(scores), 2),
            "median": round(statistics.median(scores), 2),
            "stdev": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
        },
        "component_means": {
            "sharpness": round(statistics.mean(sharpness_scores), 2),
            "lighting": round(statistics.mean(lighting_scores), 2),
        },
        "face_analysis": {
            "images_with_faces": sum(1 for r in results if r['has_faces']),
            "images_all_eyes_open": sum(1 for r in results if r.get('all_eyes_open') is True),
            "images_eyes_closed": sum(1 for r in results if r.get('all_eyes_open') is False),
        }
    }
    
    print(f"📊 Score Distribution:")
    print(f"  Mean:   {stats_summary['score_distribution']['mean']:.2f}")
    print(f"  Median: {stats_summary['score_distribution']['median']:.2f}")
    print(f"  StdDev: {stats_summary['score_distribution']['stdev']:.2f}")
    print(f"  Range:  {stats_summary['score_distribution']['min']:.2f} - {stats_summary['score_distribution']['max']:.2f}")
    
    print(f"\n📈 Component Averages:")
    print(f"  Sharpness: {stats_summary['component_means']['sharpness']:.2f}")
    print(f"  Lighting:  {stats_summary['component_means']['lighting']:.2f}")
    
    print(f"\n👥 Face Analysis:")
    print(f"  Images with faces:     {stats_summary['face_analysis']['images_with_faces']}")
    print(f"  All eyes open:         {stats_summary['face_analysis']['images_all_eyes_open']}")
    print(f"  Some eyes closed:      {stats_summary['face_analysis']['images_eyes_closed']}")
    
    # Top 10 highest scores
    print(f"\n{'='*70}")
    print("TOP 10 HIGHEST SCORING IMAGES")
    print(f"{'='*70}\n")
    
    top_10 = sorted(results, key=lambda x: x['quality_score'], reverse=True)[:10]
    for i, img in enumerate(top_10, 1):
        print(f"{i}. {img['file_name']}")
        print(f"   Score: {img['quality_score']:.1f} | Sharp: {img['sharpness_score']:.1f} | Light: {img['lighting_score']:.1f}")
        if img['has_faces']:
            eyes = "Open" if img['all_eyes_open'] else "Closed"
            print(f"   Faces: {img['face_count']}, Eyes: {eyes}")
    
    # Bottom 10 lowest scores
    print(f"\n{'='*70}")
    print("BOTTOM 10 LOWEST SCORING IMAGES")
    print(f"{'='*70}\n")
    
    bottom_10 = sorted(results, key=lambda x: x['quality_score'])[:10]
    for i, img in enumerate(bottom_10, 1):
        print(f"{i}. {img['file_name']}")
        print(f"   Score: {img['quality_score']:.1f} | Sharp: {img['sharpness_score']:.1f} | Light: {img['lighting_score']:.1f}")
        if img['has_faces']:
            eyes = "Open" if img['all_eyes_open'] else "Closed"
            print(f"   Faces: {img['face_count']}, Eyes: {eyes}")
    
    # Outlier detection: Images with mismatched scores
    print(f"\n{'='*70}")
    print("POTENTIAL OUTLIERS (Investigate These!)")
    print(f"{'='*70}\n")
    
    # High score but closed eyes
    high_score_closed_eyes = [
        r for r in results 
        if r['quality_score'] > 80 and r.get('all_eyes_open') is False
    ]
    
    if high_score_closed_eyes:
        print(f"⚠️  High Score BUT Closed Eyes ({len(high_score_closed_eyes)} images):")
        for img in high_score_closed_eyes[:5]:
            print(f"  - {img['file_name']}: Score {img['quality_score']:.1f}")
    else:
        print("✅ No high-scoring images with closed eyes")
    
    # Low score but all eyes open
    low_score_eyes_open = [
        r for r in results 
        if r['quality_score'] < 60 and r.get('all_eyes_open') is True
    ]
    
    if low_score_eyes_open:
        print(f"\n⚠️  Low Score BUT Eyes Open ({len(low_score_eyes_open)} images):")
        for img in low_score_eyes_open[:5]:
            print(f"  - {img['file_name']}: Score {img['quality_score']:.1f}")
            print(f"    Sharp: {img['sharpness_score']:.1f}, Light: {img['lighting_score']:.1f}")
    else:
        print("\n✅ No low-scoring images with eyes open")
    
    # Save detailed results
    output_data = {
        "metadata": {
            "input_folder": str(input_folder),
            "sample_size": sample_size,
            "analyzed_images": len(results),
        },
        "statistics": stats_summary,
        "images": results,
        "outliers": {
            "high_score_closed_eyes": high_score_closed_eyes,
            "low_score_eyes_open": low_score_eyes_open,
        }
    }
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"✅ Analysis complete!")
    print(f"📄 Detailed results saved to: {output_file}")
    print(f"{'='*70}\n")
    
    # Cleanup
    db.close()


def main():
    parser = argparse.ArgumentParser(description="Analyze scoring algorithm")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("test_data_system/5k"),
        help="Input folder with test images"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("profiling_results/scoring_analysis.json"),
        help="Output JSON file"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("photo_cleaner_scoring_analysis.db"),
        help="Temporary database path"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=100,
        help="Number of images to analyze"
    )
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"❌ Error: Input folder not found: {args.input}")
        sys.exit(1)
    
    analyze_scoring(args.input, args.db, args.output, args.sample)


if __name__ == "__main__":
    main()
