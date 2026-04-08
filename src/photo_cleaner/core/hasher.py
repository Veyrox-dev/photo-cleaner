"""
Image hashing utilities for duplicate detection.

Uses perceptual hashing (pHash) via imagehash library and pixel-based file hashing via SHA256.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from PIL import Image

# Lazy load imagehash to avoid PyInstaller numpy initialization issues
_imagehash = None
_PHASH_AVAILABLE = None
_PHASH_ERROR = None
_PHASH_SCIPY_VERSION = None

def _get_imagehash():
    """Lazy load imagehash module - delays numpy initialization."""
    global _imagehash
    if _imagehash is None:
        import imagehash
        _imagehash = imagehash
    return _imagehash


def check_phash_support(logger_instance: logging.Logger | None = None) -> bool:
    """Check pHash dependencies and log status once."""
    global _PHASH_AVAILABLE, _PHASH_ERROR, _PHASH_SCIPY_VERSION
    if _PHASH_AVAILABLE is not None:
        return _PHASH_AVAILABLE

    log = logger_instance or logging.getLogger(__name__)
    try:
        # Pre-initialize numpy before scipy to avoid frozen-build TypeError
        import numpy as _np
        _np.zeros(1)
        import scipy

        _PHASH_SCIPY_VERSION = getattr(scipy, "__version__", "unknown")
        log.info(f"scipy version: {_PHASH_SCIPY_VERSION}")
        _get_imagehash()
        _PHASH_AVAILABLE = True
        log.info("pHash enabled = true")
    except Exception as exc:
        _PHASH_AVAILABLE = False
        _PHASH_ERROR = f"{type(exc).__name__}: {exc}"
        log.error(f"pHash disabled: {_PHASH_ERROR}")
        if isinstance(exc, ModuleNotFoundError):
            log.error("scipy is required for perceptual hashing. Install/bundle scipy to enable pHash.")
    return _PHASH_AVAILABLE

# Register HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    _HEIF_AVAILABLE = True
except ImportError:
    _HEIF_AVAILABLE = False

logger = logging.getLogger(__name__)

if not _HEIF_AVAILABLE:
    logger.info(
        "pillow-heif nicht installiert - HEIC/HEIF Dateien werden übersprungen. "
        "Installation: pip install pillow-heif"
    )


class ImageHasher:
    """Calculates perceptual and file hashes for images."""
    
    # P2.4: Valid image magic bytes (file signatures)
    VALID_IMAGE_MAGIC = {
        b'\xFF\xD8\xFF': 'JPEG',
        b'\x89PNG': 'PNG',
        b'GIF8': 'GIF',
        b'RIFF': 'WEBP/WAV',  # RIFF (check for WEBP later)
        b'\x00\x00\x01\x00': 'ICO',
        b'BM': 'BMP',
    }

    # ISO Base Media File Format brands that correspond to HEIC/HEIF containers
    HEIC_BRANDS = {
        b'heic', b'heix', b'hevc', b'hevx', b'heim', b'heis', b'hevm', b'hevs', b'mif1', b'msf1'
    }

    def __init__(self, hash_size: int = 8) -> None:
        """
        Initialize image hasher.

        Args:
            hash_size: Size of perceptual hash (default: 8, produces 64-bit hash)
        """
        self.hash_size = hash_size

    @staticmethod
    def _is_valid_image_magic(file_path: Path) -> bool:
        """
        P2.4: Validate image file by checking magic bytes (file signature).
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file appears to be a valid image
        """
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(12)  # Read first 12 bytes for all signatures

            # Check common signatures
            for sig_bytes, format_name in ImageHasher.VALID_IMAGE_MAGIC.items():
                if magic.startswith(sig_bytes):
                    # Extra check for WEBP
                    if sig_bytes == b'RIFF' and b'WEBP' not in magic[:12]:
                        continue
                    return True

            # HEIC/HEIF files start with a box length, then the literal "ftyp" and a brand.
            # Example: 00 00 00 18 66 74 79 70 68 65 69 63 (size=24, ftyp, brand=heic)
            if len(magic) >= 12 and magic[4:8] == b'ftyp' and magic[8:12] in ImageHasher.HEIC_BRANDS:
                return True

            return False
        except (IOError, OSError) as e:
            logger.warning(f"Could not read file magic bytes for {file_path}: {e}")
            return False

    def compute_phash(self, image_path: Path) -> Optional[str]:
        """
        Compute perceptual hash using pHash algorithm.

        Args:
            image_path: Path to image file

        Returns:
            Hexadecimal string representation of pHash, or None on failure
        """
        # P2.4: Validate magic bytes first
        if not self._is_valid_image_magic(image_path):
            # Log as INFO for HEIC if pillow-heif missing, else WARNING
            suffix = image_path.suffix.lower()
            if suffix in ('.heic', '.heif') and not _HEIF_AVAILABLE:
                logger.debug(f"HEIC/HEIF übersprungen (pillow-heif fehlt): {image_path.name}")
            else:
                logger.warning(f"Ungültiges Bildformat (magic bytes): {image_path}")
            return None
        
        if not check_phash_support(logger):
            return None

        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed (handles PNG with alpha, etc.)
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                phash = _get_imagehash().phash(img, hash_size=self.hash_size)
                return str(phash)
        # P6.6: Catch PIL errors for corrupted images
        except ModuleNotFoundError as e:
            logger.error(f"pHash dependency missing: {e}")
            return None
        except (OSError, IOError, Exception) as e:
            logger.warning(f"Failed to compute pHash for {image_path} (corrupted or unsupported): {e}")
            return None

    def compute_file_hash(self, file_path: Path, algorithm: str = "sha256") -> Optional[str]:
        """
        Compute cryptographic hash of image pixels, ignoring EXIF or file metadata.

        Args:
            file_path: Path to image file
            algorithm: Hash algorithm (sha256, md5, etc.)

        Returns:
            Hexadecimal hash string of pixels, or None on failure
        """
        try:
            with Image.open(file_path) as img:
                img = img.convert("RGB")  # Alpha-Kanal ignorieren
                data = img.tobytes()
                hash_obj = hashlib.new(algorithm)
                hash_obj.update(data)
                return hash_obj.hexdigest()
        # P6.6: Handle corrupted images gracefully
        except (OSError, IOError, Exception) as e:
            logger.warning(f"Failed to compute pixel hash for {file_path} (corrupted or unsupported): {e}")
            return None

    def compute_all_hashes(self, image_path: Path) -> dict[str, Optional[str]]:
        """
        Compute both perceptual and pixel-based file hashes.

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with 'phash' and 'file_hash' keys
        """
        file_hash = self.compute_file_hash(image_path)
        phash = self.compute_phash(image_path)

        if file_hash is None:
            logger.warning(f"File hash could not be computed for {image_path}")
        if phash is None:
            logger.warning(f"Perceptual hash could not be computed for {image_path}")

        return {
            "phash": phash,
            "file_hash": file_hash,
        }


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two hex hash strings.

    Args:
        hash1: First hash (hex string)
        hash2: Second hash (hex string)

    Returns:
        Hamming distance (number of differing bits)

    Raises:
        ValueError: If hashes have different lengths
    """
    if len(hash1) != len(hash2):
        raise ValueError("Hash strings must have the same length")

    # Convert hex to int and XOR
    xor = int(hash1, 16) ^ int(hash2, 16)

    # Count set bits
    return bin(xor).count("1")
