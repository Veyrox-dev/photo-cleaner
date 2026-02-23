r"""
Setup Test Data for Phase 2 Profiling

Copies images from a source folder into structured test folders (1k, 5k, 10k)
for performance profiling.

Usage:
    python scripts/setup_test_data.py --source "C:\\Users\\chris\\Pictures" --output test_data_system
"""

import argparse
import logging
import random
import shutil
from pathlib import Path
from typing import List

try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
    # Register HEIC support
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        logger = logging.getLogger(__name__)
        logger.info("HEIC support enabled via pillow-heif")
    except ImportError:
        logger = logging.getLogger(__name__)
        logger.warning("pillow-heif not available - HEIC files will be copied without variations")
except ImportError:
    PIL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("PIL not available - synthetic duplicates disabled")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp', '.bmp'}


def find_all_images(source_folder: Path) -> List[Path]:
    """
    Recursively find all image files in source folder.
    
    Returns:
        List of image paths
    """
    logger.info(f"Scanning {source_folder} for images...")
    images = []
    
    for ext in IMAGE_EXTENSIONS:
        images.extend(source_folder.glob(f"**/*{ext}"))
        images.extend(source_folder.glob(f"**/*{ext.upper()}"))
    
    logger.info(f"Found {len(images)} images")
    return images


def generate_image_variation(
    source_path: Path,
    target_path: Path,
    variation_seed: int
) -> bool:
    """
    Generate a variation of an image with transformations.
    
    Args:
        source_path: Source image path
        target_path: Target image path
        variation_seed: Seed for variation (determines transformations)
    
    Returns:
        True if successful
    """
    if not PIL_AVAILABLE:
        return False
    
    try:
        with Image.open(source_path) as img:
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # Apply variations based on seed
            var_type = variation_seed % 6
            
            if var_type == 0:
                # Resize (90-95% of original)
                scale = 0.90 + (variation_seed % 5) * 0.01
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            elif var_type == 1:
                # Rotate (5-15 degrees)
                angle = 5 + (variation_seed % 10)
                img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))
            
            elif var_type == 2:
                # Adjust brightness (90-110%)
                enhancer = ImageEnhance.Brightness(img)
                factor = 0.90 + (variation_seed % 20) * 0.01
                img = enhancer.enhance(factor)
            
            elif var_type == 3:
                # Adjust contrast (90-110%)
                enhancer = ImageEnhance.Contrast(img)
                factor = 0.90 + (variation_seed % 20) * 0.01
                img = enhancer.enhance(factor)
            
            elif var_type == 4:
                # Adjust saturation (85-100%)
                enhancer = ImageEnhance.Color(img)
                factor = 0.85 + (variation_seed % 15) * 0.01
                img = enhancer.enhance(factor)
            
            else:  # var_type == 5
                # Slight crop and resize back (95-98% crop)
                crop_percent = 0.95 + (variation_seed % 3) * 0.01
                new_w = int(img.width * crop_percent)
                new_h = int(img.height * crop_percent)
                left = (img.width - new_w) // 2
                top = (img.height - new_h) // 2
                img = img.crop((left, top, left + new_w, top + new_h))
                img = img.resize((int(img.width / crop_percent), int(img.height / crop_percent)), Image.Resampling.LANCZOS)
            
            # Save with slight quality variation
            quality = 85 + (variation_seed % 10)
            img.save(target_path, quality=quality)
            return True
            
    except Exception as e:
        logger.warning(f"Failed to create variation of {source_path}: {e}")
        return False


def copy_images_to_target(
    images: List[Path],
    target_folder: Path,
    count: int,
    randomize: bool = True,
    allow_duplicates: bool = False
) -> int:
    """
    Copy specified number of images to target folder.
    If allow_duplicates is True and count > len(images), generates variations.
    
    Args:
        images: List of source image paths
        target_folder: Destination folder
        count: Number of images to copy
        randomize: Shuffle images before copying
        allow_duplicates: Allow generating variations to reach count
    
    Returns:
        Number of images actually copied
    """
    target_folder.mkdir(parents=True, exist_ok=True)
    
    # Determine strategy
    need_variations = count > len(images) and allow_duplicates
    
    if need_variations:
        if not PIL_AVAILABLE:
            logger.error("PIL not available - cannot generate variations")
            logger.info("Install Pillow: pip install Pillow")
            return 0
        
        logger.info(f"Generating {count} images from {len(images)} originals with variations")
        
        # Calculate how many times to repeat each image
        repeats_per_image = (count // len(images)) + 1
        total_slots = len(images) * repeats_per_image
        
    else:
        # Normal copying without variations
        repeats_per_image = 1
        total_slots = min(count, len(images))
    
    # Select images
    if randomize:
        selected_images = random.sample(images, len(images))
    else:
        selected_images = images
    
    copied = 0
    variation_counter = 0
    
    for repeat_idx in range(repeats_per_image):
        if copied >= count:
            break
        
        for img_idx, img_path in enumerate(selected_images, 1):
            if copied >= count:
                break
            
            try:
                # Create unique filename
                if repeat_idx == 0:
                    # First copy: use original name with index
                    target_name = f"{img_path.stem}_{img_idx:05d}{img_path.suffix}"
                    target_path = target_folder / target_name
                    shutil.copy2(img_path, target_path)
                else:
                    # Subsequent copies: generate variation
                    var_suffix = f"_var{repeat_idx}_{img_idx:05d}"
                    target_name = f"{img_path.stem}{var_suffix}.jpg"
                    target_path = target_folder / target_name
                    
                    # Generate variation with unique seed
                    variation_seed = variation_counter
                    variation_counter += 1
                    
                    if not generate_image_variation(img_path, target_path, variation_seed):
                        # Fallback: copy original
                        shutil.copy2(img_path, target_path)
                
                copied += 1
                
                if copied % 500 == 0:
                    logger.info(f"  Processed {copied}/{count} images...")
                    
            except Exception as e:
                logger.warning(f"Failed to process {img_path}: {e}")
    
    logger.info(f"✓ Created {copied} images in {target_folder}")
    return copied


def setup_test_folders(
    source_folder: Path,
    output_folder: Path,
    include_1k: bool = True,
    include_5k: bool = True,
    include_10k: bool = True,
    include_50k: bool = False,
    include_100k: bool = False,
    randomize: bool = True,
    allow_duplicates: bool = False,
) -> dict:
    """
    Setup test data folders (1k, 5k, 10k, 50k, 100k).
    If allow_duplicates is True, generates variations to reach target counts.
    
    Returns:
        Dict with results
    """
    # Find all images
    all_images = find_all_images(source_folder)
    
    if not all_images:
        logger.error(f"No images found in {source_folder}")
        return {"error": "No images found"}
    
    results = {
        "source_folder": str(source_folder),
        "output_folder": str(output_folder),
        "total_images_available": len(all_images),
        "folders_created": {}
    }
    
    # Create test folders
    test_configs = []
    
    if include_1k:
        test_configs.append(("1k", 1000))
    if include_5k:
        test_configs.append(("5k", 5000))
    if include_10k:
        test_configs.append(("10k", 10000))
    if include_50k:
        test_configs.append(("50k", 50000))
    if include_100k:
        test_configs.append(("100k", 100000))
    
    for folder_name, target_count in test_configs:
        logger.info(f"\n{'='*60}")
        logger.info(f"Creating {folder_name} folder ({target_count} images)")
        logger.info(f"{'='*60}")
        
        target_folder = output_folder / folder_name
        
        if len(all_images) < target_count:
            if allow_duplicates:
                logger.info(
                    f"Generating variations: Need {target_count}, have {len(all_images)} originals"
                )
                copied = copy_images_to_target(
                    all_images,
                    target_folder,
                    target_count,
                    randomize=randomize,
                    allow_duplicates=True
                )
            else:
                logger.warning(
                    f"Not enough images! Need {target_count}, have {len(all_images)}. "
                    f"Copying all {len(all_images)} images. Use --allow-duplicates to generate variations."
                )
                copied = copy_images_to_target(
                    all_images,
                    target_folder,
                    len(all_images),
                    randomize=randomize,
                    allow_duplicates=False
                )
        else:
            copied = copy_images_to_target(
                all_images,
                target_folder,
                target_count,
                randomize=randomize,
                allow_duplicates=False
            )
        
        results["folders_created"][folder_name] = {
            "path": str(target_folder),
            "images_copied": copied,
            "target": target_count
        }
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Setup test data folders for Phase 2 profiling"
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Source folder with images (will be scanned recursively)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("test_data_system"),
        help="Output folder for test data (default: test_data_system)"
    )
    parser.add_argument(
        "--skip-1k",
        action="store_true",
        help="Skip creating 1k folder"
    )
    parser.add_argument(
        "--skip-5k",
        action="store_true",
        help="Skip creating 5k folder"
    )
    parser.add_argument(
        "--skip-10k",
        action="store_true",
        help="Skip creating 10k folder"
    )
    parser.add_argument(
        "--include-50k",
        action="store_true",
        help="Create 50k folder"
    )
    parser.add_argument(
        "--include-100k",
        action="store_true",
        help="Create 100k folder"
    )
    parser.add_argument(
        "--no-randomize",
        action="store_true",
        help="Don't randomize image selection (use first N images)"
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Generate image variations to reach target count when source has insufficient images"
    )
    
    args = parser.parse_args()
    
    # Validate source
    if not args.source.exists():
        logger.error(f"Source folder not found: {args.source}")
        return 1
    
    logger.info("="*60)
    logger.info("Phase 2 Test Data Setup")
    logger.info("="*60)
    logger.info(f"Source: {args.source}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Randomize: {not args.no_randomize}")
    logger.info(f"Allow Duplicates: {args.allow_duplicates}")
    logger.info("")
    
    # Setup folders
    results = setup_test_folders(
        source_folder=args.source,
        output_folder=args.output,
        include_1k=not args.skip_1k,
        include_5k=not args.skip_5k,
        include_10k=not args.skip_10k,
        include_50k=args.include_50k,
        include_100k=args.include_100k,
        randomize=not args.no_randomize,
        allow_duplicates=args.allow_duplicates,
    )

    if "error" in results:
        logger.error(results["error"])
        return 1
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SETUP COMPLETE")
    logger.info("="*60)
    logger.info(f"Source images: {results['total_images_available']}")
    logger.info(f"Output folder: {results['output_folder']}")
    logger.info("")
    
    for folder_name, info in results.get("folders_created", {}).items():
        logger.info(f"✓ {folder_name}/ → {info['images_copied']} images")
    
    logger.info("\n" + "="*60)
    logger.info("NEXT STEPS")
    logger.info("="*60)
    logger.info("Run profiling with:")
    logger.info(f"  python scripts/profile_phase2_baseline.py --test-data {args.output}")
    logger.info("")
    
    return 0


if __name__ == "__main__":
    exit(main())
