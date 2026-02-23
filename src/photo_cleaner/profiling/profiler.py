"""
Performance Profiling Framework for PhotoCleaner.

This module provides utilities for profiling and benchmarking critical code paths:
1. License system validation
2. Image processing pipeline
3. Database operations
4. Cache system

Usage:
    python -m photo_cleaner.profiling.profiler [--target license|pipeline|cache|all]
"""

import functools
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import sys

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance measurement."""
    name: str
    duration_ms: float
    memory_mb: Optional[float] = None
    operation_count: Optional[int] = None
    timestamp: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class PerformanceSession:
    """Performance profiling session with multiple metrics."""
    name: str
    target: str
    metrics: List[PerformanceMetric]
    total_duration_ms: float
    start_time: str = None
    end_time: str = None
    system_info: Dict[str, Any] = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now().isoformat()
        if self.system_info is None:
            self.system_info = self._get_system_info()

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for context."""
        try:
            import platform
            return {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "processor": platform.processor(),
            }
        except Exception:
            return {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "target": self.target,
            "metrics": [m.to_dict() for m in self.metrics],
            "total_duration_ms": self.total_duration_ms,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "system_info": self.system_info,
        }

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)


class PerformanceProfiler:
    """Main profiler for measuring code performance."""

    def __init__(self, name: str, target: str = "general"):
        """Initialize profiler."""
        self.name = name
        self.target = target
        self.metrics: List[PerformanceMetric] = []
        self.start_time = None
        self.end_time = None

    def measure(self, operation_name: str, func: Callable, *args, **kwargs) -> Any:
        """Measure execution time of a function."""
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = (time.perf_counter() - start_time) * 1000  # ms
            metric = PerformanceMetric(
                name=operation_name,
                duration_ms=duration,
            )
            self.metrics.append(metric)
            logger.debug(f"Metric: {operation_name} = {duration:.2f}ms")

    def measure_sync(self, operation_name: str) -> 'MeasureContext':
        """Context manager for measuring code blocks."""
        return MeasureContext(self, operation_name)

    def get_session(self) -> PerformanceSession:
        """Get performance session with all metrics."""
        if not self.metrics:
            total_duration = 0.0
        else:
            total_duration = sum(m.duration_ms for m in self.metrics)

        return PerformanceSession(
            name=self.name,
            target=self.target,
            metrics=self.metrics,
            total_duration_ms=total_duration,
        )

    def report(self) -> str:
        """Generate performance report."""
        session = self.get_session()
        lines = [
            "=" * 70,
            f"PERFORMANCE PROFILE: {self.name} [{self.target}]",
            "=" * 70,
            "",
        ]

        # Summary
        lines.append(f"Total Duration: {session.total_duration_ms:.2f}ms")
        lines.append(f"Operation Count: {len(self.metrics)}")
        lines.append("")

        # Details
        lines.append("METRICS:")
        lines.append("-" * 70)

        for metric in sorted(self.metrics, key=lambda m: m.duration_ms, reverse=True):
            lines.append(
                f"  {metric.name:40s} {metric.duration_ms:10.2f}ms"
            )

        lines.append("-" * 70)
        lines.append("")

        return "\n".join(lines)

    def save(self, output_path: Path) -> None:
        """Save performance data to JSON file."""
        session = self.get_session()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(session.to_json())
        logger.info(f"Performance data saved to {output_path}")


class MeasureContext:
    """Context manager for measuring code execution."""

    def __init__(self, profiler: PerformanceProfiler, operation_name: str):
        self.profiler = profiler
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.perf_counter() - self.start_time) * 1000  # ms
        metric = PerformanceMetric(
            name=self.operation_name,
            duration_ms=duration,
        )
        self.profiler.metrics.append(metric)
        logger.debug(f"Metric: {self.operation_name} = {duration:.2f}ms")


def profile_function(target: str = "general") -> Callable:
    """Decorator for profiling function execution."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler = PerformanceProfiler(
                name=func.__name__,
                target=target,
            )

            with profiler.measure_sync(f"{func.__name__}"):
                result = func(*args, **kwargs)

            # Log performance
            logger.info(profiler.report())

            return result

        return wrapper

    return decorator


# Convenience function for quick benchmarking
def quick_benchmark(name: str, func: Callable, iterations: int = 1) -> PerformanceMetric:
    """Quick benchmark of a function."""
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        func()
        duration = (time.perf_counter() - start) * 1000
        times.append(duration)

    avg_time = sum(times) / len(times)
    metric = PerformanceMetric(
        name=name,
        duration_ms=avg_time,
        operation_count=iterations,
    )

    return metric


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Quick test
    profiler = PerformanceProfiler("test_profile", target="general")

    # Simulate some work
    with profiler.measure_sync("operation_1"):
        time.sleep(0.01)

    with profiler.measure_sync("operation_2"):
        time.sleep(0.02)

    print(profiler.report())
