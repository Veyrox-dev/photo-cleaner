"""
Generate Synthetic Test Images for Phase 2 Profiling

Creates realistic test images with variations for profiling purposes.

Usage:
    python scripts/generate_test_images.py --output test_data_system/1k --count 1000
"""

import argparse
import logging
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_test_image(
    width: int,
    height: int,
    blur: bool = False,
    brightness: int = 128,
) -> Image.Image:
    """
    Generate a synthetic test image with variations.
    
    Args:
        width: Image width
        height: Image height
        blur: Add blur effect
        brightness: Brightness level (0-255)
    
    Returns:
        PIL Image
    """
    # Create base image with gradient
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # Random gradient background
    for y in range(height):
        # Create gradient from top to bottom
        intensity = int(brightness * (y / height))
        color = (
            min(255, intensity + random.randint(-30, 30)),
            min(255, intensity + random.randint(-30, 30)),
            min(255, intensity + random.randint(-30, 30)),
        )
        draw.line([(0, y), (width, y)], fill=color)
    
    # Add some random shapes
    for _ in range(random.randint(3, 8)):
        x1 = random.randint(0, width - 1)
        y1 = random.randint(0, height - 1)
        x2 = random.randint(0, width - 1)
        y2 = random.randint(0, height - 1)
        
        # Ensure x1 < x2 and y1 < y2
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        
        color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )
        shape = random.choice(['rectangle', 'ellipse'])
        if shape == 'rectangle':
            draw.rectangle([x1, y1, x2, y2], fill=color)
        else:
            draw.ellipse([x1, y1, x2, y2], fill=color)
    
    # Add text
    try:
        font_size = min(width, height) // 10
        draw.text(
            (width // 2, height // 2),
            f"Test {width}x{height}",
            fill=(255, 255, 255),
            anchor="mm"
        )
    except Exception:
        pass  # Font might not be available
    
    # Apply blur if requested
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=3))
    
    return img


def generate_test_dataset(
    output_folder: Path,
    count: int,
    variations: bool = True,
) -> dict:
    """
    Generate test image dataset with variations.
    
    Args:
        output_folder: Output folder
        count: Number of images to generate
        variations: Include resolution/quality variations
    
    Returns:
        Dict with results
    """
    output_folder.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Generating {count} test images...")
    logger.info(f"Output: {output_folder}")
    logger.info(f"Variations: {variations}")
    
    results = {
        "output_folder": str(output_folder),
        "count": count,
        "generated": 0,
        "failed": 0,
    }
    
    resolutions = [
        (1920, 1080),  # Full HD
        (2560, 1440),  # 2K
        (3840, 2160),  # 4K
        (4032, 3024),  # iPhone-like
        (1200, 800),   # Lower res
    ]
    
    for i in range(count):
        try:
            # Choose resolution
            if variations:
                width, height = random.choice(resolutions)
            else:
                width, height = 1920, 1080
            
            # Random variations
            blur = variations and random.random() < 0.2  # 20% blurry
            brightness = random.randint(100, 200) if variations else 128
            
            # Generate image
            img = generate_test_image(width, height, blur, brightness)
            
            # Save with unique filename
            filename = f"test_img_{i+1:05d}.jpg"
            output_path = output_folder / filename
            
            # Save with varying quality
            quality = random.randint(75, 95) if variations else 85
            img.save(output_path, 'JPEG', quality=quality)
            
            results["generated"] += 1
            
            if (i + 1) % 100 == 0:
                logger.info(f"  Generated {i + 1}/{count} images...")
                
        except Exception as e:
            logger.warning(f"Failed to generate image {i+1}: {e}")
            results["failed"] += 1
    
    logger.info(f"✓ Generated {results['generated']} images")
    if results["failed"] > 0:
        logger.warning(f"✗ Failed: {results['failed']} images")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic test images for profiling"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output folder for test images"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1000,
        help="Number of images to generate (default: 1000)"
    )
    parser.add_argument(
        "--no-variations",
        action="store_true",
        help="Disable resolution/quality variations (faster)"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("Synthetic Test Image Generator")
    logger.info("="*60)
    logger.info(f"Count: {args.count}")
    logger.info(f"Output: {args.output}")
    logger.info("")
    
    results = generate_test_dataset(
        output_folder=args.output,
        count=args.count,
        variations=not args.no_variations,
    )
    
    logger.info("\n" + "="*60)
    logger.info("GENERATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Generated: {results['generated']} images")
    logger.info(f"Output: {results['output_folder']}")
    logger.info("\nRun profiling with:")
    logger.info(f"  python scripts/profile_phase2_baseline.py --test-data {args.output.parent}")
    
    return 0


if __name__ == "__main__":
    exit(main())
