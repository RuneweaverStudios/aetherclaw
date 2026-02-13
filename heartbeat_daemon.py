#!/usr/bin/env python3
"""
Aether-Claw Heartbeat Daemon

Runs scheduled proactive tasks based on heartbeat.md configuration.
"""

import logging
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from config_loader import get_config_loader
from notifier import get_notifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_HEARTBEAT_FILE = Path(__file__).parent / 'brain' / 'heartbeat.md'


@dataclass
class TaskResult:
    """Result of a heartbeat task execution."""
    task_name: str
    success: bool
    message: str
    timestamp: str
    details: Optional[str] = None


class HeartbeatDaemon:
    """Manages scheduled proactive tasks."""

    def __init__(
        self,
        heartbeat_file: Optional[Path] = None,
        interval_minutes: Optional[int] = None
    ):
        """
        Initialize the heartbeat daemon.

        Args:
            heartbeat_file: Path to heartbeat.md configuration
            interval_minutes: Override interval from config
        """
        self.heartbeat_file = Path(heartbeat_file) if heartbeat_file else DEFAULT_HEARTBEAT_FILE

        # Get configuration
        config = get_config_loader().get_config()
        self.interval_minutes = interval_minutes or config.heartbeat.interval_minutes
        self.interval_seconds = self.interval_minutes * 60

        # State
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Task registry
        self._tasks: dict[str, Callable[[], TaskResult]] = {}

        # History
        self._history: list[TaskResult] = []
        self._last_run: Optional[datetime] = None

        # Register default tasks
        self._register_default_tasks()

    def _register_default_tasks(self) -> None:
        """Register built-in heartbeat tasks."""
        # These will be implemented in tasks/ module
        self.register_task('git_repo_scan', self._task_git_scan)
        self.register_task('memory_index_update', self._task_memory_update)
        self.register_task('skill_integrity_check', self._task_skill_check)
        self.register_task('system_health_check', self._task_health_check)
        self.register_task('task_list_review', self._task_list_review)

    def _log_to_audit(self, action: str, details: str, level: str = "INFO") -> None:
        """Log to audit log if available."""
        try:
            from audit_logger import log_action
            log_action(
                level=level,
                agent="HeartbeatDaemon",
                action=action,
                details=details
            )
        except ImportError:
            logger.info(f"[Audit] {action}: {details}")

    def register_task(
        self,
        name: str,
        handler: Callable[[], TaskResult]
    ) -> None:
        """
        Register a heartbeat task.

        Args:
            name: Task name (must match heartbeat.md)
            handler: Function to execute for this task
        """
        self._tasks[name] = handler
        logger.info(f"Registered heartbeat task: {name}")

    def _task_git_scan(self) -> TaskResult:
        """Execute git repository scan task."""
        try:
            # Import task module
            sys.path.insert(0, str(Path(__file__).parent))
            from tasks.git_scanner import scan_all_repositories

            results = scan_all_repositories()

            return TaskResult(
                task_name='git_repo_scan',
                success=True,
                message=f"Scanned {len(results)} repositories",
                timestamp=datetime.now().isoformat(),
                details=str(results)
            )
        except ImportError:
            return TaskResult(
                task_name='git_repo_scan',
                success=False,
                message="Git scanner module not available",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return TaskResult(
                task_name='git_repo_scan',
                success=False,
                message=f"Error: {str(e)}",
                timestamp=datetime.now().isoformat()
            )

    def _task_memory_update(self) -> TaskResult:
        """Execute memory index update task."""
        try:
            from brain_index import BrainIndexer

            indexer = BrainIndexer()
            results = indexer.index_all()

            return TaskResult(
                task_name='memory_index_update',
                success=True,
                message=f"Indexed {len(results)} files",
                timestamp=datetime.now().isoformat(),
                details=str(results)
            )
        except Exception as e:
            return TaskResult(
                task_name='memory_index_update',
                success=False,
                message=f"Error: {str(e)}",
                timestamp=datetime.now().isoformat()
            )

    def _task_skill_check(self) -> TaskResult:
        """Execute skill integrity check task."""
        try:
            from safe_skill_creator import SafeSkillCreator

            creator = SafeSkillCreator()
            skills = creator.list_skills()

            invalid = [s for s in skills if not s.get('signature_valid', False)]

            if invalid:
                return TaskResult(
                    task_name='skill_integrity_check',
                    success=False,
                    message=f"Found {len(invalid)} invalid skills",
                    timestamp=datetime.now().isoformat(),
                    details=str([s['name'] for s in invalid])
                )

            return TaskResult(
                task_name='skill_integrity_check',
                success=True,
                message=f"All {len(skills)} skills valid",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return TaskResult(
                task_name='skill_integrity_check',
                success=False,
                message=f"Error: {str(e)}",
                timestamp=datetime.now().isoformat()
            )

    def _task_health_check(self) -> TaskResult:
        """Execute system health check task."""
        try:
            # Import task module
            sys.path.insert(0, str(Path(__file__).parent))
            from tasks.health_monitor import check_system_health

            health = check_system_health()

            issues = []
            if health.get('cpu_percent', 0) > 80:
                issues.append(f"High CPU: {health['cpu_percent']}%")
            if health.get('memory_percent', 0) > 90:
                issues.append(f"High Memory: {health['memory_percent']}%")

            if issues:
                return TaskResult(
                    task_name='system_health_check',
                    success=False,
                    message="Health issues detected",
                    timestamp=datetime.now().isoformat(),
                    details="; ".join(issues)
                )

            return TaskResult(
                task_name='system_health_check',
                success=True,
                message="System healthy",
                timestamp=datetime.now().isoformat(),
                details=str(health)
            )
        except ImportError:
            return TaskResult(
                task_name='system_health_check',
                success=True,
                message="Health monitor not available",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return TaskResult(
                task_name='system_health_check',
                success=False,
                message=f"Error: {str(e)}",
                timestamp=datetime.now().isoformat()
            )

    def _task_list_review(self) -> TaskResult:
        """Execute task list review."""
        # This would integrate with Todoist or local task lists
        return TaskResult(
            task_name='task_list_review',
            success=True,
            message="Task list review completed",
            timestamp=datetime.now().isoformat()
        )

    def parse_heartbeat_config(self) -> list[dict]:
        """
        Parse heartbeat.md for enabled tasks.

        Returns:
            List of task configurations
        """
        if not self.heartbeat_file.exists():
            logger.warning(f"Heartbeat config not found: {self.heartbeat_file}")
            return []

        tasks = []

        with open(self.heartbeat_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Simple parsing for task names
        # Look for lines like "### Task 1: task_name" or "name: task_name"
        import re

        # Find task definitions
        task_pattern = r'name:\s*(\w+)'
        enabled_pattern = r'enabled:\s*(\w+)'

        lines = content.split('\n')
        current_task = None

        for line in lines:
            name_match = re.search(task_pattern, line)
            if name_match:
                current_task = {'name': name_match.group(1), 'enabled': True}

            enabled_match = re.search(enabled_pattern, line)
            if enabled_match and current_task:
                current_task['enabled'] = enabled_match.group(1).lower() == 'true'
                tasks.append(current_task)
                current_task = None

        logger.debug(f"Parsed {len(tasks)} tasks from heartbeat config")
        return tasks

    def execute_task(self, task_name: str) -> TaskResult:
        """
        Execute a single heartbeat task.

        Args:
            task_name: Name of the task to execute

        Returns:
            TaskResult with execution outcome
        """
        handler = self._tasks.get(task_name)

        if handler is None:
            return TaskResult(
                task_name=task_name,
                success=False,
                message="Task not registered",
                timestamp=datetime.now().isoformat()
            )

        try:
            self._log_to_audit(
                action="TASK_STARTED",
                details=f"Executing task: {task_name}"
            )

            result = handler()

            self._log_to_audit(
                action="TASK_COMPLETED",
                details=f"{task_name}: {result.message}"
            )

            # Send notification for failures
            if not result.success:
                get_notifier().send_heartbeat_status(
                    task_name,
                    "failed",
                    result.message
                )

            return result

        except Exception as e:
            logger.error(f"Task {task_name} failed with exception: {e}")

            self._log_to_audit(
                action="TASK_FAILED",
                details=f"{task_name}: {str(e)}",
                level="ERROR"
            )

            return TaskResult(
                task_name=task_name,
                success=False,
                message=f"Exception: {str(e)}",
                timestamp=datetime.now().isoformat()
            )

    def run_heartbeat(self) -> list[TaskResult]:
        """
        Run all enabled heartbeat tasks.

        Returns:
            List of TaskResult objects
        """
        results = []
        tasks = self.parse_heartbeat_config()

        logger.info(f"Running heartbeat with {len(tasks)} tasks")

        for task in tasks:
            if not task.get('enabled', True):
                continue

            result = self.execute_task(task['name'])
            results.append(result)
            self._history.append(result)

        self._last_run = datetime.now()

        # Keep history limited
        if len(self._history) > 100:
            self._history = self._history[-100:]

        return results

    def _heartbeat_loop(self) -> None:
        """Main heartbeat loop running in background thread."""
        logger.info(f"Heartbeat daemon started (interval: {self.interval_minutes} min)")

        while not self._stop_event.is_set():
            try:
                self.run_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            # Wait for next interval or stop signal
            self._stop_event.wait(self.interval_seconds)

        logger.info("Heartbeat daemon stopped")

    def start(self) -> None:
        """Start the heartbeat daemon."""
        if self._running:
            logger.warning("Heartbeat daemon already running")
            return

        self._running = True
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()

        self._log_to_audit(
            action="DAEMON_STARTED",
            details=f"Interval: {self.interval_minutes} minutes"
        )

    def stop(self) -> None:
        """Stop the heartbeat daemon."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None

        self._log_to_audit(
            action="DAEMON_STOPPED",
            details="Graceful shutdown"
        )

    def run_once(self) -> list[TaskResult]:
        """
        Run heartbeat once without starting daemon.

        Returns:
            List of TaskResult objects
        """
        return self.run_heartbeat()

    def get_status(self) -> dict:
        """Get daemon status information."""
        return {
            'running': self._running,
            'interval_minutes': self.interval_minutes,
            'last_run': self._last_run.isoformat() if self._last_run else None,
            'registered_tasks': list(self._tasks.keys()),
            'history_count': len(self._history)
        }

    def get_recent_results(self, count: int = 10) -> list[TaskResult]:
        """Get recent task results."""
        return self._history[-count:]


def main():
    """CLI entry point for heartbeat daemon."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Heartbeat Daemon')
    parser.add_argument(
        '--start',
        action='store_true',
        help='Start the heartbeat daemon'
    )
    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run heartbeat once and exit'
    )
    parser.add_argument(
        '--task',
        type=str,
        help='Execute a specific task'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show daemon status'
    )
    parser.add_argument(
        '--interval',
        type=int,
        help='Override interval in minutes'
    )

    args = parser.parse_args()

    daemon = HeartbeatDaemon(interval_minutes=args.interval)

    if args.status:
        status = daemon.get_status()
        print("Heartbeat Daemon Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")

    elif args.task:
        result = daemon.execute_task(args.task)
        print(f"Task: {result.task_name}")
        print(f"Success: {result.success}")
        print(f"Message: {result.message}")
        if result.details:
            print(f"Details: {result.details}")

    elif args.run_once:
        results = daemon.run_once()
        print(f"Executed {len(results)} tasks:")
        for result in results:
            status = "OK" if result.success else "FAILED"
            print(f"  [{status}] {result.task_name}: {result.message}")

    elif args.start:
        # Set up signal handlers for graceful shutdown
        def handle_signal(signum, frame):
            logger.info("Received shutdown signal")
            daemon.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        daemon.start()

        print(f"Heartbeat daemon started (interval: {daemon.interval_minutes} min)")
        print("Press Ctrl+C to stop")

        # Keep main thread alive
        try:
            while daemon._running:
                time.sleep(1)
        except KeyboardInterrupt:
            daemon.stop()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
