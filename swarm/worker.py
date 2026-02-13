#!/usr/bin/env python3
"""
Aether-Claw Swarm Worker Base

Base class for all swarm worker agents.
"""

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkerStatus(str, Enum):
    """Worker status states."""
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class WorkerRole(str, Enum):
    """Worker role types."""
    ARCHITECT = "architect"
    ACTION = "action"
    TESTER = "tester"
    DOCUMENTER = "documenter"


@dataclass
class Task:
    """Represents a task to be executed."""
    id: str
    description: str
    priority: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class ThinkingStep:
    """Represents a thinking step in the reasoning process."""
    timestamp: str
    thought: str
    decision: Optional[str] = None


class Worker(ABC):
    """Base class for swarm workers."""

    def __init__(
        self,
        role: WorkerRole,
        worker_id: Optional[str] = None
    ):
        """
        Initialize a worker.

        Args:
            role: Worker role
            worker_id: Optional worker ID (auto-generated if not provided)
        """
        self.id = worker_id or str(uuid.uuid4())[:8]
        self.role = role
        self.status = WorkerStatus.IDLE

        self._current_task: Optional[Task] = None
        self._thinking_process: list[ThinkingStep] = []
        self._completed_tasks: list[Task] = []
        self._start_time: Optional[float] = None

    def _log_to_audit(self, action: str, details: str, level: str = "INFO") -> None:
        """Log to audit log if available."""
        try:
            from audit_logger import log_action
            log_action(
                level=level,
                agent=f"Worker-{self.id}",
                action=action,
                details=details
            )
        except ImportError:
            logger.info(f"[Audit] {action}: {details}")

    def log_thinking(self, thought: str, decision: Optional[str] = None) -> None:
        """
        Log a thinking step before producing output.

        Args:
            thought: The thought or reasoning
            decision: Optional decision made
        """
        step = ThinkingStep(
            timestamp=datetime.now().isoformat(),
            thought=thought,
            decision=decision
        )
        self._thinking_process.append(step)

        logger.debug(f"[Thinking] {thought}")
        if decision:
            logger.debug(f"[Decision] {decision}")

    def get_thinking_process(self) -> list[ThinkingStep]:
        """Get the thinking process for current task."""
        return self._thinking_process.copy()

    def clear_thinking(self) -> None:
        """Clear the thinking process."""
        self._thinking_process = []

    def assign_task(self, task: Task) -> None:
        """
        Assign a task to this worker.

        Args:
            task: Task to assign
        """
        self._current_task = task
        self.status = WorkerStatus.WORKING
        task.started_at = datetime.now().isoformat()
        self._start_time = time.time()

        self._log_to_audit(
            action="TASK_ASSIGNED",
            details=f"Task {task.id}: {task.description[:50]}..."
        )

        logger.info(f"Worker {self.id} assigned task {task.id}")

    @abstractmethod
    def execute_task(self) -> Any:
        """
        Execute the assigned task.

        Returns:
            Task result

        Raises:
            Exception: If task execution fails
        """
        pass

    def run(self) -> Task:
        """
        Run the worker on its assigned task.

        Returns:
            Completed Task with result
        """
        if not self._current_task:
            raise ValueError("No task assigned")

        self.status = WorkerStatus.WORKING
        self.clear_thinking()

        try:
            # Log thinking before execution
            self.log_thinking(
                f"Starting task execution: {self._current_task.description[:100]}",
                f"Using role: {self.role.value}"
            )

            # Execute
            result = self.execute_task()

            # Mark complete
            self._current_task.result = result
            self._current_task.completed_at = datetime.now().isoformat()
            self.status = WorkerStatus.COMPLETED

            self._log_to_audit(
                action="TASK_COMPLETED",
                details=f"Task {self._current_task.id} completed successfully"
            )

            # Move to completed
            self._completed_tasks.append(self._current_task)
            completed = self._current_task
            self._current_task = None

            return completed

        except Exception as e:
            self.status = WorkerStatus.FAILED
            if self._current_task:
                self._current_task.error = str(e)
                self._current_task.completed_at = datetime.now().isoformat()

            self._log_to_audit(
                action="TASK_FAILED",
                details=f"Task {self._current_task.id if self._current_task else '?'} failed: {str(e)}",
                level="ERROR"
            )

            logger.error(f"Worker {self.id} task failed: {e}")
            raise

    def report_progress(self) -> dict:
        """
        Get current progress report.

        Returns:
            Dictionary with progress information
        """
        elapsed = time.time() - self._start_time if self._start_time else 0

        return {
            'worker_id': self.id,
            'role': self.role.value,
            'status': self.status.value,
            'current_task': self._current_task.id if self._current_task else None,
            'thinking_steps': len(self._thinking_process),
            'elapsed_seconds': elapsed,
            'completed_tasks': len(self._completed_tasks)
        }

    def stop(self) -> None:
        """Stop the worker gracefully."""
        self.status = WorkerStatus.STOPPED
        self._log_to_audit(
            action="WORKER_STOPPED",
            details=f"Worker {self.id} stopped"
        )
        logger.info(f"Worker {self.id} stopped")

    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            'id': self.id,
            'role': self.role.value,
            'status': self.status.value,
            'tasks_completed': len(self._completed_tasks),
            'failed_tasks': len([t for t in self._completed_tasks if t.error])
        }
