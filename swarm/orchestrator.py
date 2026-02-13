#!/usr/bin/env python3
"""
Aether-Claw Swarm Orchestrator

Coordinates multiple workers for distributed task execution.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from queue import Queue

from .worker import Worker, WorkerStatus, Task
from .architect import Architect
from .action_worker import ActionWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SwarmStatus:
    """Current status of the swarm."""
    total_workers: int
    active_workers: int
    pending_tasks: int
    completed_tasks: int
    failed_tasks: int


@dataclass
class WorkerInfo:
    """Information about a worker in the swarm."""
    worker_id: str
    role: str
    status: str
    current_task: Optional[str]


class SwarmOrchestrator:
    """
    Orchestrates the swarm of workers for task execution.

    Responsibilities:
    - Spawn and manage workers
    - Distribute tasks
    - Collect results
    - Monitor progress
    """

    def __init__(self, max_workers: int = 3):
        """
        Initialize the orchestrator.

        Args:
            max_workers: Maximum number of concurrent workers
        """
        self.max_workers = max_workers

        # Worker management
        self._workers: dict[str, Worker] = {}
        self._architect: Optional[Architect] = None

        # Task management
        self._task_queue: Queue[Task] = Queue()
        self._completed_tasks: list[Task] = []
        self._failed_tasks: list[Task] = []

        # Execution
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures: dict[str, Future] = {}

        # State
        self._running = False
        self._lock = threading.Lock()

    def _log_to_audit(self, action: str, details: str, level: str = "INFO") -> None:
        """Log to audit log if available."""
        try:
            from audit_logger import log_action
            log_action(
                level=level,
                agent="SwarmOrchestrator",
                action=action,
                details=details
            )
        except ImportError:
            logger.info(f"[Audit] {action}: {details}")

    def spawn_architect(self) -> Architect:
        """
        Spawn an architect worker.

        Returns:
            Architect worker instance
        """
        if self._architect is not None:
            logger.warning("Architect already exists")
            return self._architect

        self._architect = Architect()
        self._workers[self._architect.id] = self._architect

        self._log_to_audit(
            action="ARCHITECT_SPAWNED",
            details=f"Architect {self._architect.id} created"
        )

        logger.info(f"Spawned architect: {self._architect.id}")
        return self._architect

    def spawn_workers(self, count: int = 1) -> list[ActionWorker]:
        """
        Spawn action workers.

        Args:
            count: Number of workers to spawn

        Returns:
            List of spawned workers
        """
        spawned = []

        for _ in range(count):
            if len(self._workers) >= self.max_workers:
                logger.warning(f"Max workers ({self.max_workers}) reached")
                break

            worker = ActionWorker()
            self._workers[worker.id] = worker
            spawned.append(worker)

            self._log_to_audit(
                action="WORKER_SPAWNED",
                details=f"Action worker {worker.id} created"
            )

        logger.info(f"Spawned {len(spawned)} workers")
        return spawned

    def add_task(self, task: Task) -> None:
        """
        Add a task to the queue.

        Args:
            task: Task to add
        """
        self._task_queue.put(task)

        self._log_to_audit(
            action="TASK_QUEUED",
            details=f"Task {task.id}: {task.description[:50]}..."
        )

        logger.info(f"Task {task.id} added to queue")

    def add_tasks(self, tasks: list[Task]) -> None:
        """
        Add multiple tasks to the queue.

        Args:
            tasks: Tasks to add
        """
        for task in tasks:
            self.add_task(task)

    def _get_available_worker(self) -> Optional[Worker]:
        """Get an available worker."""
        for worker in self._workers.values():
            if worker.status == WorkerStatus.IDLE:
                return worker
        return None

    def _execute_worker(self, worker: Worker, task: Task) -> Task:
        """Execute a task on a worker."""
        try:
            worker.assign_task(task)
            return worker.run()
        except Exception as e:
            logger.error(f"Worker {worker.id} failed on task {task.id}: {e}")
            task.error = str(e)
            return task

    def distribute_tasks(self, tasks: Optional[list[Task]] = None) -> None:
        """
        Distribute tasks to available workers.

        Args:
            tasks: Optional list of tasks (uses queue if not provided)
        """
        if tasks:
            self.add_tasks(tasks)

        self._log_to_audit(
            action="DISTRIBUTING_TASKS",
            details=f"Queue size: {self._task_queue.qsize()}"
        )

        distributed = 0

        while not self._task_queue.empty():
            worker = self._get_available_worker()
            if worker is None:
                break

            task = self._task_queue.get()

            if self._executor:
                # Async execution
                future = self._executor.submit(self._execute_worker, worker, task)
                self._futures[task.id] = future
            else:
                # Sync execution
                result = self._execute_worker(worker, task)
                if result.error:
                    self._failed_tasks.append(result)
                else:
                    self._completed_tasks.append(result)

            distributed += 1

        logger.info(f"Distributed {distributed} tasks")

    def collect_results(self) -> list[Task]:
        """
        Collect completed task results.

        Returns:
            List of completed tasks
        """
        if not self._executor:
            return self._completed_tasks.copy()

        results = []

        # Check completed futures
        completed_ids = []
        for task_id, future in self._futures.items():
            if future.done():
                try:
                    task = future.result()
                    if task.error:
                        self._failed_tasks.append(task)
                    else:
                        results.append(task)
                        self._completed_tasks.append(task)
                except Exception as e:
                    logger.error(f"Future {task_id} failed: {e}")

                completed_ids.append(task_id)

        # Clean up completed futures
        for task_id in completed_ids:
            del self._futures[task_id]

        return results

    def monitor_progress(self) -> SwarmStatus:
        """
        Get current swarm status.

        Returns:
            SwarmStatus with current metrics
        """
        active = sum(
            1 for w in self._workers.values()
            if w.status == WorkerStatus.WORKING
        )

        return SwarmStatus(
            total_workers=len(self._workers),
            active_workers=active,
            pending_tasks=self._task_queue.qsize(),
            completed_tasks=len(self._completed_tasks),
            failed_tasks=len(self._failed_tasks)
        )

    def get_worker_info(self) -> list[WorkerInfo]:
        """
        Get information about all workers.

        Returns:
            List of WorkerInfo objects
        """
        info = []

        for worker in self._workers.values():
            info.append(WorkerInfo(
                worker_id=worker.id,
                role=worker.role.value,
                status=worker.status.value,
                current_task=worker._current_task.id if worker._current_task else None
            ))

        return info

    def start(self) -> None:
        """Start the orchestrator with thread pool."""
        if self._running:
            return

        self._running = True
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

        # Ensure we have workers
        if not self._workers:
            self.spawn_architect()
            self.spawn_workers(min(2, self.max_workers - 1))

        self._log_to_audit(
            action="ORCHESTRATOR_STARTED",
            details=f"Max workers: {self.max_workers}"
        )

        logger.info("Orchestrator started")

    def stop(self, wait: bool = True) -> None:
        """
        Stop the orchestrator.

        Args:
            wait: Whether to wait for running tasks
        """
        self._running = False

        # Stop all workers
        for worker in self._workers.values():
            worker.stop()

        # Shutdown executor
        if self._executor:
            self._executor.shutdown(wait=wait)
            self._executor = None

        self._log_to_audit(
            action="ORCHESTRATOR_STOPPED",
            details=f"Completed: {len(self._completed_tasks)}, Failed: {len(self._failed_tasks)}"
        )

        logger.info("Orchestrator stopped")

    def run_until_complete(self) -> list[Task]:
        """
        Run until all tasks are complete.

        Returns:
            List of all completed tasks
        """
        self.start()

        try:
            while not self._task_queue.empty() or self._futures:
                self.distribute_tasks()
                self.collect_results()
                time.sleep(0.5)

        finally:
            self.stop()

        return self._completed_tasks

    def get_all_results(self) -> dict:
        """Get all results from the swarm."""
        return {
            'completed': [
                {'id': t.id, 'result': t.result}
                for t in self._completed_tasks
            ],
            'failed': [
                {'id': t.id, 'error': t.error}
                for t in self._failed_tasks
            ]
        }


def main():
    """Test the swarm orchestrator."""
    orchestrator = SwarmOrchestrator(max_workers=3)

    # Add some tasks
    tasks = [
        Task(id="task-1", description="Write a hello world function", priority=1),
        Task(id="task-2", description="Write tests for hello world", priority=2),
        Task(id="task-3", description="Document the hello world function", priority=3),
    ]

    orchestrator.add_tasks(tasks)

    # Run
    results = orchestrator.run_until_complete()

    print(f"\nCompleted {len(results)} tasks:")
    for task in results:
        print(f"  - {task.id}: {task.result.get('type', 'unknown') if task.result else 'no result'}")

    # Get status
    status = orchestrator.monitor_progress()
    print(f"\nFinal status: {status.completed_tasks} completed, {status.failed_tasks} failed")


if __name__ == '__main__':
    main()
