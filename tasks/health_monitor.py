#!/usr/bin/env python3
"""
Aether-Claw System Health Monitor

Monitors system resources and detects anomalies.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import psutil for system stats
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not installed, health monitoring will be limited")


@dataclass
class SystemHealth:
    """System health metrics."""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_percent: float
    disk_available_mb: float
    process_count: int
    load_average: Optional[tuple[float, float, float]] = None
    uptime_seconds: Optional[float] = None


@dataclass
class HealthAnomaly:
    """Detected health anomaly."""
    anomaly_type: str
    severity: str  # low, medium, high, critical
    current_value: float
    threshold: float
    message: str


def check_cpu_usage() -> float:
    """
    Get current CPU usage percentage.

    Returns:
        CPU usage as percentage (0-100)
    """
    if PSUTIL_AVAILABLE:
        return psutil.cpu_percent(interval=1)
    return 0.0


def check_memory_usage() -> tuple[float, float]:
    """
    Get memory usage information.

    Returns:
        Tuple of (usage_percent, available_mb)
    """
    if PSUTIL_AVAILABLE:
        mem = psutil.virtual_memory()
        return mem.percent, mem.available / (1024 * 1024)
    return 0.0, 0.0


def check_disk_space(path: str = "/") -> tuple[float, float]:
    """
    Get disk usage information.

    Args:
        path: Path to check (default: root)

    Returns:
        Tuple of (usage_percent, available_mb)
    """
    if PSUTIL_AVAILABLE:
        try:
            disk = psutil.disk_usage(path)
            return disk.percent, disk.free / (1024 * 1024)
        except Exception:
            pass
    return 0.0, 0.0


def get_process_count() -> int:
    """Get number of running processes."""
    if PSUTIL_AVAILABLE:
        return len(psutil.pids())
    return 0


def get_load_average() -> Optional[tuple[float, float, float]]:
    """Get system load average."""
    if PSUTIL_AVAILABLE:
        try:
            return psutil.getloadavg()
        except AttributeError:
            pass
    return None


def get_uptime() -> Optional[float]:
    """Get system uptime in seconds."""
    if PSUTIL_AVAILABLE:
        try:
            boot_time = psutil.boot_time()
            return time.time() - boot_time
        except Exception:
            pass
    return None


def check_system_health() -> SystemHealth:
    """
    Get comprehensive system health metrics.

    Returns:
        SystemHealth object with current metrics
    """
    cpu = check_cpu_usage()
    mem_percent, mem_available = check_memory_usage()
    disk_percent, disk_available = check_disk_space()
    processes = get_process_count()
    load_avg = get_load_average()
    uptime = get_uptime()

    return SystemHealth(
        cpu_percent=cpu,
        memory_percent=mem_percent,
        memory_available_mb=mem_available,
        disk_percent=disk_percent,
        disk_available_mb=disk_available,
        process_count=processes,
        load_average=load_avg,
        uptime_seconds=uptime
    )


def detect_anomalies(
    health: SystemHealth,
    cpu_threshold: float = 80.0,
    memory_threshold: float = 90.0,
    disk_threshold: float = 90.0
) -> list[HealthAnomaly]:
    """
    Detect health anomalies based on thresholds.

    Args:
        health: SystemHealth to analyze
        cpu_threshold: CPU usage threshold
        memory_threshold: Memory usage threshold
        disk_threshold: Disk usage threshold

    Returns:
        List of detected anomalies
    """
    anomalies = []

    # CPU check
    if health.cpu_percent > cpu_threshold:
        severity = "critical" if health.cpu_percent > 95 else "high"
        anomalies.append(HealthAnomaly(
            anomaly_type="high_cpu",
            severity=severity,
            current_value=health.cpu_percent,
            threshold=cpu_threshold,
            message=f"CPU usage is {health.cpu_percent:.1f}% (threshold: {cpu_threshold}%)"
        ))

    # Memory check
    if health.memory_percent > memory_threshold:
        severity = "critical" if health.memory_percent > 95 else "high"
        anomalies.append(HealthAnomaly(
            anomaly_type="high_memory",
            severity=severity,
            current_value=health.memory_percent,
            threshold=memory_threshold,
            message=f"Memory usage is {health.memory_percent:.1f}% (threshold: {memory_threshold}%)"
        ))

    # Disk check
    if health.disk_percent > disk_threshold:
        severity = "critical" if health.disk_percent > 95 else "high"
        anomalies.append(HealthAnomaly(
            anomaly_type="high_disk",
            severity=severity,
            current_value=health.disk_percent,
            threshold=disk_threshold,
            message=f"Disk usage is {health.disk_percent:.1f}% (threshold: {disk_threshold}%)"
        ))

    # Low available memory warning
    if health.memory_available_mb < 500:
        anomalies.append(HealthAnomaly(
            anomaly_type="low_memory_available",
            severity="medium",
            current_value=health.memory_available_mb,
            threshold=500,
            message=f"Only {health.memory_available_mb:.0f}MB memory available"
        ))

    return anomalies


class ContinuousMonitor:
    """Continuous health monitoring with anomaly detection."""

    def __init__(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 90.0,
        disk_threshold: float = 90.0,
        cpu_duration_threshold: int = 60  # seconds
    ):
        """
        Initialize continuous monitor.

        Args:
            cpu_threshold: CPU usage threshold
            memory_threshold: Memory usage threshold
            disk_threshold: Disk usage threshold
            cpu_duration_threshold: Duration in seconds for CPU spike detection
        """
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.cpu_duration_threshold = cpu_duration_threshold

        # Tracking for duration-based alerts
        self._high_cpu_start: Optional[float] = None

    def check(self) -> tuple[SystemHealth, list[HealthAnomaly]]:
        """
        Perform a health check.

        Returns:
            Tuple of (health, anomalies)
        """
        health = check_system_health()
        anomalies = detect_anomalies(
            health,
            self.cpu_threshold,
            self.memory_threshold,
            self.disk_threshold
        )

        # Track CPU duration
        cpu_anomaly = next(
            (a for a in anomalies if a.anomaly_type == "high_cpu"),
            None
        )

        if cpu_anomaly:
            if self._high_cpu_start is None:
                self._high_cpu_start = time.time()
            elif time.time() - self._high_cpu_start > self.cpu_duration_threshold:
                # CPU has been high for too long - escalate to critical
                cpu_anomaly.severity = "critical"
                cpu_anomaly.message += f" for >{self.cpu_duration_threshold}s"
        else:
            self._high_cpu_start = None

        return health, anomalies


def main():
    """CLI entry point for health monitor."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Health Monitor')
    parser.add_argument(
        '--check',
        action='store_true',
        help='Perform a single health check'
    )
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Run continuous monitoring'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Monitoring interval in seconds'
    )
    parser.add_argument(
        '--cpu-threshold',
        type=float,
        default=80,
        help='CPU usage threshold'
    )
    parser.add_argument(
        '--memory-threshold',
        type=float,
        default=90,
        help='Memory usage threshold'
    )

    args = parser.parse_args()

    if args.check:
        health = check_system_health()
        anomalies = detect_anomalies(health)

        print("System Health:")
        print(f"  CPU: {health.cpu_percent:.1f}%")
        print(f"  Memory: {health.memory_percent:.1f}% ({health.memory_available_mb:.0f}MB available)")
        print(f"  Disk: {health.disk_percent:.1f}% ({health.disk_available_mb:.0f}MB available)")
        print(f"  Processes: {health.process_count}")

        if health.load_average:
            print(f"  Load Average: {health.load_average}")

        if anomalies:
            print(f"\nAnomalies ({len(anomalies)}):")
            for anomaly in anomalies:
                print(f"  [{anomaly.severity.upper()}] {anomaly.message}")
        else:
            print("\nNo anomalies detected")

    elif args.monitor:
        monitor = ContinuousMonitor(
            cpu_threshold=args.cpu_threshold,
            memory_threshold=args.memory_threshold
        )

        print("Starting continuous monitoring (Ctrl+C to stop)...")

        try:
            while True:
                health, anomalies = monitor.check()

                status = "OK" if not anomalies else "WARNING"
                print(f"[{status}] CPU: {health.cpu_percent:.1f}% | "
                      f"Mem: {health.memory_percent:.1f}% | "
                      f"Disk: {health.disk_percent:.1f}%")

                if anomalies:
                    for anomaly in anomalies:
                        print(f"  ! [{anomaly.severity}] {anomaly.message}")

                time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\nMonitoring stopped")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
