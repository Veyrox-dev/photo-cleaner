#!/usr/bin/env python3
"""
Comprehensive Test Image Generator for PhotoCleaner

Generates test images for various testing scenarios:
- Exact duplicates (identical files)
- Similar images (perceptual duplicates)
- Unique images with variations
- Face detection test images (cartoon faces)
- Large-scale performance testing

Usage:
    python scripts/test_image_generator.py --mode basic --output test_images
    python scripts/test_image_generator.py --mode performance --count 5000 --output test_big
    python scripts/test_image_generator.py --mode faces --output test_faces --count 10
    python scripts/test_image_generator.py --mode all --output test_all
"""

import argparse
import random
from pathlib import Path
from typing import Literal

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow not installed. Install with: pip install Pillow")
    exit(1)


class ImageGenerator:
    """Generate test images for PhotoCleaner testing."""
    
    def __init__(self, output_dir: Path):
        """Initialize generator with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.created_files = []
    
    def generate_basic_set(self) -> list[Path]:
        """
        Generate basic test set with duplicates and variations.
        
        Creates:
        - 2 exact duplicates (red images)
        - 1 similar image (red with line)
        - 2 perceptual duplicates (blue, blue rotated)
        - 1 unique random noise image
        
        Returns:
            List of created file paths
        """
        print("Generating basic test set...")
        
        # Exact duplicate pair (identical files)
        img1 = Image.new("RGB", (256, 256), "red")
        p1 = self.output_dir / "img1.png"
        img1.save(p1)
        self.created_files.append(p1)
        
        p1_copy = self.output_dir / "img1_copy.png"
        img1.save(p1_copy)
        self.created_files.append(p1_copy)
        
        # Similar image: same base with a small black line
        img1_sim = img1.copy()
        draw = ImageDraw.Draw(img1_sim)
        draw.line((0, 0, 255, 10), fill=(0, 0, 0), width=4)
        p_sim = self.output_dir / "img1_similar.png"
        img1_sim.save(p_sim)
        self.created_files.append(p_sim)
        
        # Another pair: blue and slightly rotated blue
        img2 = Image.new("RGB", (256, 256), "blue")
        p2 = self.output_dir / "img2.png"
        img2.save(p2)
        self.created_files.append(p2)
        
        img2_rot = img2.rotate(5, expand=False)
        p2_rot = self.output_dir / "img2_rotated.png"
        img2_rot.save(p2_rot)
        self.created_files.append(p2_rot)
        
        # Unique random-noise image
        rand = Image.new("RGB", (256, 256))
        pixels = [
            (random.randrange(256), random.randrange(256), random.randrange(256))
            for _ in range(256 * 256)
        ]
        rand.putdata(pixels)
        p_rand = self.output_dir / "unique_random.png"
        rand.save(p_rand)
        self.created_files.append(p_rand)
        
        print(f"  Created {len(self.created_files)} basic test images")
        return self.created_files.copy()
    
    def generate_performance_set(self, count: int = 5000, duplicates: int = 200) -> list[Path]:
        """
        Generate large set for performance testing.
        
        Args:
            count: Total number of images to generate
            duplicates: Number of duplicate images
        
        Returns:
            List of created file paths
        """
        print(f"Generating performance test set ({count} images, {duplicates} duplicates)...")
        
        # Create base unique images
        unique_count = count - duplicates
        for i in range(unique_count):
            color = (
                random.randrange(256),
                random.randrange(256),
                random.randrange(256),
            )
            img = Image.new("RGB", (128, 128), color)
            draw = ImageDraw.Draw(img)
            
            # Add random patterns for variation
            for _ in range(5):
                x1 = random.randrange(128)
                y1 = random.randrange(128)
                x2 = min(127, x1 + random.randrange(5, 40))
                y2 = min(127, y1 + random.randrange(5, 40))
                rect_color = (
                    random.randrange(256),
                    random.randrange(256),
                    random.randrange(256),
                )
                draw.rectangle([x1, y1, x2, y2], outline=rect_color)
            
            p = self.output_dir / f"img_{i:05d}.png"
            img.save(p, optimize=True)
            self.created_files.append(p)
            
            if (i + 1) % 1000 == 0:
                print(f"  Created {i + 1}/{unique_count} unique images...")
        
        # Create duplicates by copying random existing images
        existing = self.created_files.copy()
        if existing:
            print(f"  Creating {duplicates} duplicates...")
            for j in range(duplicates):
                src = random.choice(existing)
                dst = self.output_dir / f"dup_{j:04d}_{src.name}"
                img = Image.open(src)
                img.save(dst, optimize=True)
                self.created_files.append(dst)
        
        print(f"  Created {len(self.created_files)} total images")
        return self.created_files.copy()
    
    def generate_face_test_set(self, count: int = 10) -> list[Path]:
        """
        Generate images with cartoon faces for face detection testing.
        
        Args:
            count: Number of face images to generate
        
        Returns:
            List of created file paths
        """
        print(f"Generating face test set ({count} images)...")
        
        for i in range(count):
            width = 600 + i * 50
            height = 800 + i * 50
            
            img = self._create_cartoon_face(width, height, i + 1)
            p = self.output_dir / f"face_{i+1:03d}.jpg"
            img.save(p, quality=95)
            self.created_files.append(p)
        
        print(f"  Created {len(self.created_files)} face test images")
        return self.created_files.copy()
    
    def generate_duplicate_groups(self, groups: int = 10, images_per_group: int = 4) -> list[Path]:
        """
        Generate organized duplicate groups for testing duplicate detection.
        
        Args:
            groups: Number of duplicate groups
            images_per_group: Images in each group (with slight variations)
        
        Returns:
            List of created file paths
        """
        print(f"Generating {groups} duplicate groups with {images_per_group} images each...")
        
        quality_levels = ["best", "good", "medium", "poor"]
        
        for g in range(groups):
            # Base image for this group
            base_color = (
                random.randrange(100, 256),
                random.randrange(100, 256),
                random.randrange(100, 256),
            )
            
            for d in range(images_per_group):
                img = Image.new("RGB", (800, 600), base_color)
                draw = ImageDraw.Draw(img)
                
                # Add group label
                label = f"Group {g+1:02d} - {quality_levels[d % len(quality_levels)]}"
                try:
                    font = ImageFont.truetype("arial.ttf", 40)
                except:
                    font = ImageFont.load_default()
                
                draw.text((50, 250), label, fill=(255, 255, 255), font=font)
                
                # Add slight noise for variation
                noise_level = d * 2
                for _ in range(noise_level):
                    x = random.randrange(800)
                    y = random.randrange(600)
                    noise_color = (
                        random.randrange(256),
                        random.randrange(256),
                        random.randrange(256),
                    )
                    draw.point((x, y), fill=noise_color)
                
                quality = quality_levels[d % len(quality_levels)]
                p = self.output_dir / f"test_g{g+1:02d}_d{d+1}_{quality}.jpg"
                
                # Vary JPEG quality
                jpeg_quality = 95 - (d * 10)
                img.save(p, quality=max(60, jpeg_quality))
                self.created_files.append(p)
        
        print(f"  Created {len(self.created_files)} images in {groups} groups")
        return self.created_files.copy()
    
    def _create_cartoon_face(self, width: int, height: int, face_id: int) -> Image.Image:
        """Create a simple cartoon face for testing."""
        # Create background
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Head (large oval)
        head_box = [width//4, height//6, 3*width//4, 2*height//3]
        draw.ellipse(head_box, fill='peachpuff', outline='black', width=3)
        
        # Eyes
        eye_y = height//3
        left_eye_center = (width//3, eye_y)
        right_eye_center = (2*width//3, eye_y)
        eye_radius = 30
        
        # Left eye
        draw.ellipse(
            [left_eye_center[0]-eye_radius, left_eye_center[1]-eye_radius,
             left_eye_center[0]+eye_radius, left_eye_center[1]+eye_radius],
            fill='white', outline='black', width=2
        )
        draw.ellipse(
            [left_eye_center[0]-15, left_eye_center[1]-15,
             left_eye_center[0]+15, left_eye_center[1]+15],
            fill='brown', outline='black', width=2
        )
        
        # Right eye
        draw.ellipse(
            [right_eye_center[0]-eye_radius, right_eye_center[1]-eye_radius,
             right_eye_center[0]+eye_radius, right_eye_center[1]+eye_radius],
            fill='white', outline='black', width=2
        )
        draw.ellipse(
            [right_eye_center[0]-15, right_eye_center[1]-15,
             right_eye_center[0]+15, right_eye_center[1]+15],
            fill='brown', outline='black', width=2
        )
        
        # Nose
        nose_tip = (width//2, height//2)
        draw.polygon(
            [nose_tip, (nose_tip[0]-20, nose_tip[1]-30), (nose_tip[0]+20, nose_tip[1]-30)],
            fill='tan', outline='black', width=2
        )
        
        # Mouth
        mouth_y = height//2 + 60
        draw.arc(
            [width//3, mouth_y-30, 2*width//3, mouth_y+30],
            start=0, end=180, fill='black', width=4
        )
        
        # Hair
        draw.ellipse(
            [width//4-20, height//6-40, 3*width//4+20, height//4+20],
            fill='brown', outline='black', width=2
        )
        
        # Add face ID label
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 10), f"Face #{face_id}", fill='black', font=font)
        
        return img
    
    def generate_all(self) -> list[Path]:
        """Generate comprehensive test set with all variations."""
        print("Generating comprehensive test set...")
        self.generate_basic_set()
        self.generate_duplicate_groups(groups=3, images_per_group=4)
        self.generate_face_test_set(count=5)
        print(f"\nTotal images created: {len(self.created_files)}")
        return self.created_files.copy()
    
    def print_summary(self):
        """Print summary of generated images."""
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Output directory: {self.output_dir.resolve()}")
        print(f"Total images: {len(self.created_files)}")
        print("\nSample files:")
        for p in self.created_files[:10]:
            print(f"  {p.name}")
        if len(self.created_files) > 10:
            print(f"  ... and {len(self.created_files) - 10} more")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate test images for PhotoCleaner testing"
    )
    parser.add_argument(
        "--mode",
        choices=["basic", "performance", "faces", "groups", "all"],
        default="all",
        help="Test image generation mode"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="test_images",
        help="Output directory for generated images"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5000,
        help="Number of images (for performance mode)"
    )
    parser.add_argument(
        "--duplicates",
        type=int,
        default=200,
        help="Number of duplicates (for performance mode)"
    )
    parser.add_argument(
        "--groups",
        type=int,
        default=10,
        help="Number of duplicate groups (for groups mode)"
    )
    
    args = parser.parse_args()
    
    generator = ImageGenerator(args.output)
    
    if args.mode == "basic":
        generator.generate_basic_set()
    elif args.mode == "performance":
        generator.generate_performance_set(args.count, args.duplicates)
    elif args.mode == "faces":
        generator.generate_face_test_set(args.count)
    elif args.mode == "groups":
        generator.generate_duplicate_groups(args.groups, images_per_group=4)
    elif args.mode == "all":
        generator.generate_all()
    
    generator.print_summary()


if __name__ == "__main__":
    main()
