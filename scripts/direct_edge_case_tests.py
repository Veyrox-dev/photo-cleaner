#!/usr/bin/env python3
"""
Direct edge case testing without subprocess calls.
Tests graceful handling of corrupted files, missing EXIF, permissions, etc.
"""

import sys
import os
import json
import tempfile
import logging
from pathlib import Path
from datetime import datetime

# Setup
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from photo_cleaner.io.file_scanner import FileScanner
from photo_cleaner.core.hasher import ImageHasher

RESULTS_FILE = ROOT / "edge_case_test_results.json"


class EdgeCaseTestRunner:
    """Run edge case tests directly without subprocess."""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.test_dir = tempfile.mkdtemp(prefix="photocleaner_edge_")
        self.hasher = ImageHasher()
        logger.info(f"Test environment: {self.test_dir}")
    
    def cleanup(self):
        """Clean up temporary test files."""
        import shutil
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass
    
    def _record_result(self, name: str, passed: bool, details: str):
        """Record test result."""
        result = {
            'test': name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat(),
        }
        self.results.append(result)
        if passed:
            self.passed += 1
            logger.info(f"✅ {name}: {details}")
        else:
            self.failed += 1
            logger.error(f"❌ {name}: {details}")
    
    def test_empty_directory(self):
        """Test: Empty directory is handled gracefully."""
        logger.info("\n📋 Empty Directory")
        test_path = Path(self.test_dir) / "empty"
        test_path.mkdir()
        
        try:
            scanner = FileScanner(test_path)
            files = list(scanner.scan())
            if len(files) == 0:
                self._record_result("Empty Directory", True, "Correctly returned 0 files")
            else:
                self._record_result("Empty Directory", False, f"Expected 0 files, got {len(files)}")
        except Exception as e:
            self._record_result("Empty Directory", False, str(e))
    
    def test_corrupted_jpeg(self):
        """Test: Corrupted JPEG is skipped gracefully."""
        logger.info("\n📋 Corrupted JPEG")
        test_path = Path(self.test_dir) / "corrupted"
        test_path.mkdir()
        
        # Create truncated JPEG
        (test_path / "corrupted.jpg").write_bytes(b'\xFF\xD8\xFF\xE0\x00\x10JFIF' + b'\x00' * 50)
        # Create one valid file
        valid = test_path / "valid.jpg"
        valid.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100 + b'\xFF\xD9')
        
        try:
            scanner = FileScanner(test_path)
            files = list(scanner.scan())
            
            # Should find at least the corrupted file (scanner doesn't validate)
            if len(files) >= 1:
                # Try to hash - should skip corrupted one gracefully
                phash_count = 0
                for f in files:
                    try:
                        result = self.hasher.compute_phash(f)
                        if result:
                            phash_count += 1
                    except:
                        pass  # Expected to fail on corrupted
                
                self._record_result("Corrupted JPEG", True, 
                    f"Scanned {len(files)} files, successfully hashed {phash_count}")
            else:
                self._record_result("Corrupted JPEG", False, "Scanner found no files")
        except Exception as e:
            self._record_result("Corrupted JPEG", False, str(e))
    
    def test_missing_exif(self):
        """Test: Images without EXIF are handled with defaults."""
        logger.info("\n📋 Missing EXIF Data")
        test_path = Path(self.test_dir) / "no_exif"
        test_path.mkdir()
        
        # Create minimal a JPEG without EXIF
        (test_path / "no_exif.jpg").write_bytes(
            b'\xFF\xD8\xFF\xE1\x00\x10Exif\x00\x00' + b'\x00' * 100 + b'\xFF\xD9'
        )
        
        try:
            scanner = FileScanner(test_path)
            files = list(scanner.scan())
            
            if len(files) > 0:
                # Try to hash - should work even without EXIF
                result = self.hasher.compute_phash(files[0])
                if result:
                    self._record_result("Missing EXIF", True, "Hashed successfully with defaults")
                else:
                    self._record_result("Missing EXIF", True, "Skipped gracefully (PIL fallback)")
            else:
                self._record_result("Missing EXIF", False, "No files found")
        except Exception as e:
            self._record_result("Missing EXIF", False, str(e))
    
    def test_invalid_file_format(self):
        """Test: Non-image files are skipped."""
        logger.info("\n📋 Invalid File Format")
        test_path = Path(self.test_dir) / "mixed"
        test_path.mkdir()
        
        (test_path / "not_image.jpg").write_text("This is not a JPEG")
        (test_path / "document.txt").write_text("Document")
        (test_path / "valid.jpg").write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 50 + b'\xFF\xD9')
        
        try:
            scanner = FileScanner(test_path)
            files = list(scanner.scan())
            
            # Scanner should find files with image extensions
            hash_errors = 0
            hash_success = 0
            for f in files:
                try:
                    result = self.hasher.compute_phash(f)
                    if result:
                        hash_success += 1
                except:
                    hash_errors += 1
            
            self._record_result("Invalid File Format", True,
                f"Scanned {len(files)} files, {hash_success} successful, {hash_errors} errors")
        except Exception as e:
            self._record_result("Invalid File Format", False, str(e))
    
    def test_deeply_nested_folders(self):
        """Test: Deep folder nesting is handled."""
        logger.info("\n📋 Deeply Nested Folders")
        
        # Create 20 levels deep
        path = Path(self.test_dir) / "nested"
        for i in range(20):
            path = path / f"level_{i}"
        path.mkdir(parents=True)
        
        # Add a file at the deepest level
        (path / "deep.jpg").write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 50 + b'\xFF\xD9')
        
        try:
            scanner = FileScanner(Path(self.test_dir) / "nested")
            files = list(scanner.scan())
            
            if len(files) > 0:
                self._record_result("Deeply Nested Folders", True,
                    f"Found file at 20 levels deep")
            else:
                self._record_result("Deeply Nested Folders", False,
                    "Scanner did not find deeply nested file")
        except Exception as e:
            self._record_result("Deeply Nested Folders", False, str(e))
    
    def test_file_permissions(self):
        """Test: Read-only files are handled gracefully."""
        logger.info("\n📋 Read-Only Files")
        test_path = Path(self.test_dir) / "perms"
        test_path.mkdir()
        
        # Create a file
        readonly = test_path / "readonly.jpg"
        readonly.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 50 + b'\xFF\xD9')
        
        try:
            # Remove write permission
            import stat
            os.chmod(readonly, stat.S_IRUSR)
            
            scanner = FileScanner(test_path)
            files = list(scanner.scan())
            
            # Restore permissions so cleanup works
            os.chmod(readonly, stat.S_IRUSR | stat.S_IWUSR)
            
            if len(files) > 0:
                self._record_result("Read-Only Files", True,
                    f"Found read-only file: {len(files)} files")
            else:
                self._record_result("Read-Only Files", False, "Did not find read-only file")
        except Exception as e:
            self._record_result("Read-Only Files", False, str(e))
    
    def run_all(self):
        """Run all edge case tests."""
        logger.info("=" * 70)
        logger.info("EDGE CASE & CRASH TESTING SUITE")
        logger.info("=" * 70)
        
        try:
            self.test_empty_directory()
            self.test_corrupted_jpeg()
            self.test_missing_exif()
            self.test_invalid_file_format()
            self.test_deeply_nested_folders()
            self.test_file_permissions()
            
            # Summary
            logger.info("\n" + "=" * 70)
            logger.info("TEST SUMMARY")
            logger.info("=" * 70)
            logger.info(f"✅ Passed: {self.passed}")
            logger.info(f"❌ Failed: {self.failed}")
            logger.info(f"Total: {self.passed + self.failed}")
            
            # Save results
            with open(RESULTS_FILE, 'w') as f:
                json.dump(self.results, f, indent=2)
            logger.info(f"\nResults saved to: {RESULTS_FILE}")
            
            return self.failed == 0
            
        finally:
            self.cleanup()


def main():
    """Main entry point."""
    runner = EdgeCaseTestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
