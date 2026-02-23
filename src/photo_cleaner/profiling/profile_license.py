"""
License System Performance Profiling.

Profile license system operations:
- Machine ID computation
- License initialization
- Feature flag checks
- License validation
- Cloud snapshot loading

Usage:
    python -m photo_cleaner.profiling.profile_license
"""

import json
import logging
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any

from photo_cleaner.profiling.profiler import PerformanceProfiler, PerformanceSession
from photo_cleaner.license import LicenseManager, LicenseType, LicenseInfo, FeatureFlagsManager

logger = logging.getLogger(__name__)


class LicenseSystemProfiler:
    """Profile license system performance."""

    def __init__(self):
        self.profiler = PerformanceProfiler("License System", target="license")

    def profile_machine_id_computation(self) -> Dict[str, Any]:
        """Profile machine ID computation."""
        logger.info("Profiling machine ID computation...")

        from photo_cleaner.license.license_manager import compute_machine_id

        # Measure machine ID computation
        with self.profiler.measure_sync("compute_machine_id"):
            machine_id = compute_machine_id()

        return {
            "machine_id_sample": machine_id[:16] + "...",
            "machine_id_length": len(machine_id),
        }

    def profile_license_initialization(self) -> Dict[str, Any]:
        """Profile license manager initialization."""
        logger.info("Profiling license initialization...")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Measure initialization
            with self.profiler.measure_sync("LicenseManager.__init__"):
                manager = LicenseManager(Path(tmpdir))

            return {
                "machine_id": manager.machine_id[:16] + "...",
                "license_type": manager.license_info.license_type.value,
                "valid": manager.license_info.valid,
            }

    def profile_feature_flag_checks(self) -> Dict[str, Any]:
        """Profile feature flag checking."""
        logger.info("Profiling feature flag checks...")

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))
            flags = FeatureFlagsManager(manager)

            # Measure individual flag checks
            features = [
                ("can_batch_process", flags.can_batch_process),
                ("can_use_extended_cache", flags.can_use_extended_cache),
                ("has_unlimited_images", flags.has_unlimited_images),
                ("has_api_access", flags.has_api_access),
            ]

            results = {}
            for feature_name, method in features:
                with self.profiler.measure_sync(f"FeatureFlags.{feature_name}"):
                    result = method()
                    results[feature_name] = result

            return results

    def profile_image_limit_check(self) -> Dict[str, Any]:
        """Profile image processing limit checks."""
        logger.info("Profiling image limit checks...")

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            test_counts = [100, 500, 1000, 5000, 10000]
            results = {}

            for count in test_counts:
                with self.profiler.measure_sync(f"can_process_images({count})"):
                    can_process = manager.can_process_images(count)
                results[f"can_process_{count}"] = can_process

            return results

    def profile_license_status_retrieval(self) -> Dict[str, Any]:
        """Profile license status retrieval."""
        logger.info("Profiling license status retrieval...")

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Measure status retrieval
            with self.profiler.measure_sync("get_license_status"):
                status = manager.get_license_status()

            return {
                "status_keys": list(status.keys()),
                "license_type": status.get("license_type"),
                "valid": status.get("valid"),
            }

    def profile_license_activation(self) -> Dict[str, Any]:
        """Profile license activation workflow."""
        logger.info("Profiling license activation...")

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Create activation code
            now = datetime.now(timezone.utc)
            exp_date = (now + timedelta(days=365)).date()

            code = {
                "mid": manager.machine_id,
                "type": "PRO",
                "exp": exp_date.isoformat(),
                "nonce": "benchmark-nonce",
            }

            code["sig"] = "benchmark-sig"
            code["user"] = "Benchmark User"

            # Measure activation
            from photo_cleaner.license import crypto_utils
            original_verify = crypto_utils.verify_ed25519_signature
            crypto_utils.verify_ed25519_signature = lambda payload, sig: True
            try:
                with self.profiler.measure_sync("activate_with_code"):
                    success = manager.activate_with_code(json.dumps(code))
            finally:
                crypto_utils.verify_ed25519_signature = original_verify

            return {
                "success": success,
                "license_type": manager.license_info.license_type.value,
            }

    def profile_cloud_snapshot_loading(self) -> Dict[str, Any]:
        """Profile cloud snapshot loading."""
        logger.info("Profiling cloud snapshot loading...")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create cloud snapshot
            snapshot_path = Path(tmpdir) / "license_snapshot.json"
            now = datetime.now(timezone.utc)
            expires_at = (now + timedelta(days=365)).isoformat()

            snapshot_data = {
                "fetched_at": now.isoformat(),
                "data": {
                    "license_id": "LIC-BENCH-001",
                    "plan": "pro",
                    "status": "active",
                    "expires_at": expires_at,
                },
            }

            snapshot_path.write_text(json.dumps(snapshot_data))
            signature_path = snapshot_path.parent / "license_signature"
            signature_path.write_text("benchmark-sig")

            # Mock cloud snapshot location
            home_snapshot = Path.home() / ".photocleaner" / "license_snapshot.json"
            home_snapshot.parent.mkdir(parents=True, exist_ok=True)
            home_snapshot.write_text(json.dumps(snapshot_data))
            (home_snapshot.parent / "license_signature").write_text("benchmark-sig")

            try:
                # Measure loading
                manager = LicenseManager(Path(tmpdir))

                with self.profiler.measure_sync("_load_cloud_snapshot"):
                    manager.refresh()

                return {
                    "license_type": manager.license_info.license_type.value,
                    "valid": manager.license_info.valid,
                }
            finally:
                # Cleanup
                try:
                    home_snapshot.unlink(missing_ok=True)
                except OSError:
                    pass

    def run_all_profiles(self) -> PerformanceSession:
        """Run all license system profiles."""
        logger.info("=" * 70)
        logger.info("STARTING LICENSE SYSTEM PERFORMANCE PROFILING")
        logger.info("=" * 70)

        # Run all profiles
        profiles = {
            "machine_id_computation": self.profile_machine_id_computation,
            "license_initialization": self.profile_license_initialization,
            "feature_flag_checks": self.profile_feature_flag_checks,
            "image_limit_checks": self.profile_image_limit_check,
            "license_status": self.profile_license_status_retrieval,
            "license_activation": self.profile_license_activation,
            "cloud_snapshot": self.profile_cloud_snapshot_loading,
        }

        results = {}
        for profile_name, profile_func in profiles.items():
            try:
                logger.info(f"\n→ Running {profile_name}...")
                results[profile_name] = profile_func()
                logger.info(f"✓ {profile_name} complete")
            except Exception as e:
                logger.error(f"✗ {profile_name} failed: {e}", exc_info=True)
                results[profile_name] = {"error": str(e)}

        # Get performance session
        session = self.profiler.get_session()

        # Log results
        logger.info("\n" + self.profiler.report())

        logger.info("\nDETAILED RESULTS:")
        logger.info("-" * 70)
        for profile_name, result in results.items():
            logger.info(f"\n{profile_name}:")
            for key, value in result.items():
                logger.info(f"  {key}: {value}")

        return session


def main():
    """Run license system profiling."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    profiler = LicenseSystemProfiler()
    session = profiler.run_all_profiles()

    # Save results
    output_dir = Path("profiling_results")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"license_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    profiler.profiler.save(output_file)
    logger.info(f"\nResults saved to {output_file}")

    return session


if __name__ == "__main__":
    main()
