#!/usr/bin/env python3
"""
Aether-Claw Kill Switch

Monitors for security events and halts all operations when triggered.
"""

import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Any
from dataclasses import dataclass

from config_loader import get_config_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_FLAG_FILE = Path(__file__).parent / '.kill_switch_flag'


class TriggerReason(str, Enum):
    """Reasons for triggering the kill switch."""
    UNSIGNED_SKILL = "unsigned_skill_execution"
    SIGNATURE_FAILURE = "signature_verification_failure"
    UNAUTHORIZED_ACCESS = "unauthorized_file_access"
    USER_COMMAND = "user_command_stop_swarm"
    CPU_THRESHOLD = "cpu_threshold_exceeded"
    MEMORY_THRESHOLD = "memory_threshold_exceeded"
    ANOMALY_DETECTED = "anomaly_detected"
    MANUAL = "manual_trigger"


@dataclass
class KillSwitchEvent:
    """Represents a kill switch event."""
    timestamp: str
    reason: TriggerReason
    details: str
    recovered: bool = False


class KillSwitch:
    """Monitors and manages kill switch functionality."""

    def __init__(
        self,
        flag_file: Optional[Path] = None,
        on_trigger: Optional[Callable[[TriggerReason], None]] = None
    ):
        """
        Initialize the kill switch.

        Args:
            flag_file: Path to the flag file
            on_trigger: Optional callback when kill switch is triggered
        """
        self.flag_file = Path(flag_file) if flag_file else DEFAULT_FLAG_FILE
        self._on_trigger = on_trigger

        self._armed = False
        self._triggered = False
        self._trigger_reason: Optional[TriggerReason] = None
        self._trigger_time: Optional[datetime] = None
        self._lock = threading.Lock()

        # Monitoring thread
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()

        # History
        self._history: list[KillSwitchEvent] = []

    def _log_to_audit(self, action: str, details: str, level: str = "SECURITY") -> None:
        """Log to audit log if available."""
        try:
            from audit_logger import log_action
            log_action(
                level=level,
                agent="KillSwitch",
                action=action,
                details=details
            )
        except ImportError:
            logger.info(f"[Audit] {action}: {details}")

    def arm(self) -> None:
        """
        Arm the kill switch and start monitoring.
        """
        with self._lock:
            if self._armed:
                logger.warning("Kill switch already armed")
                return

            self._armed = True
            self._stop_monitor.clear()

            # Start monitoring thread
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True
            )
            self._monitor_thread.start()

            logger.info("Kill switch ARMED")
            self._log_to_audit(
                action="KILL_SWITCH_ARMED",
                details="Kill switch monitoring started"
            )

    def disarm(self) -> None:
        """
        Disarm the kill switch and stop monitoring.
        """
        with self._lock:
            self._armed = False
            self._stop_monitor.set()

            if self._monitor_thread:
                self._monitor_thread.join(timeout=5)
                self._monitor_thread = None

            logger.info("Kill switch DISARMED")
            self._log_to_audit(
                action="KILL_SWITCH_DISARMED",
                details="Kill switch monitoring stopped"
            )

    def trigger(self, reason: TriggerReason, details: str = "") -> None:
        """
        Trigger the kill switch.

        Args:
            reason: Reason for triggering
            details: Additional details
        """
        with self._lock:
            if self._triggered:
                logger.warning(f"Kill switch already triggered: {self._trigger_reason}")
                return

            self._triggered = True
            self._trigger_reason = reason
            self._trigger_time = datetime.now()

            # Create flag file
            self._create_flag_file(reason, details)

            # Log the event
            self._log_to_audit(
                action="KILL_SWITCH_TRIGGERED",
                details=f"Reason: {reason.value}. {details}",
                level="SECURITY"
            )

            # Record in history
            self._history.append(KillSwitchEvent(
                timestamp=self._trigger_time.isoformat(),
                reason=reason,
                details=details
            ))

            logger.critical(f"KILL SWITCH TRIGGERED: {reason.value}")
            logger.critical(f"Details: {details}")

            # Call callback if set
            if self._on_trigger:
                try:
                    self._on_trigger(reason)
                except Exception as e:
                    logger.error(f"Error in kill switch callback: {e}")

    def _create_flag_file(self, reason: TriggerReason, details: str) -> None:
        """Create the flag file to indicate kill switch was triggered."""
        content = f"""# Aether-Claw Kill Switch Flag

TRIGGERED: {datetime.now().isoformat()}
REASON: {reason.value}
DETAILS: {details}

This file indicates that the kill switch was triggered.
To reset, run: aether-claw kill-switch --reset
"""
        with open(self.flag_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Kill switch flag file created: {self.flag_file}")

    def is_armed(self) -> bool:
        """Check if kill switch is armed."""
        return self._armed

    def is_triggered(self) -> bool:
        """Check if kill switch has been triggered."""
        # Also check for flag file
        if self.flag_file.exists() and not self._triggered:
            self._triggered = True
            self._trigger_reason = TriggerReason.MANUAL
        return self._triggered

    def get_trigger_reason(self) -> Optional[TriggerReason]:
        """Get the reason for triggering, if triggered."""
        return self._trigger_reason

    def get_trigger_time(self) -> Optional[datetime]:
        """Get the time of triggering, if triggered."""
        return self._trigger_time

    def reset(self) -> bool:
        """
        Reset the kill switch after manual review.

        Returns:
            True if reset successful, False if not triggered
        """
        with self._lock:
            if not self._triggered:
                logger.info("Kill switch not triggered, nothing to reset")
                return False

            # Remove flag file
            if self.flag_file.exists():
                self.flag_file.unlink()

            # Mark last event as recovered
            if self._history:
                self._history[-1].recovered = True

            self._triggered = False
            self._trigger_reason = None
            self._trigger_time = None

            logger.info("Kill switch RESET")
            self._log_to_audit(
                action="KILL_SWITCH_RESET",
                details="Kill switch reset by user"
            )

            return True

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        logger.info("Kill switch monitoring started")

        while not self._stop_monitor.is_set():
            try:
                # Check for trigger conditions
                self._check_triggers()

            except Exception as e:
                logger.error(f"Error in kill switch monitor: {e}")

            # Check every 5 seconds
            self._stop_monitor.wait(5)

        logger.info("Kill switch monitoring stopped")

    def _check_triggers(self) -> None:
        """Check for trigger conditions."""
        if not self._armed or self._triggered:
            return

        try:
            config = get_config_loader()
            triggers = config.get_kill_switch_triggers()

            # Check CPU threshold
            cpu_trigger = triggers.get('cpu_threshold_exceeded', {})
            if isinstance(cpu_trigger, dict):
                threshold = cpu_trigger.get('threshold', 80)
                duration = cpu_trigger.get('duration_seconds', 60)

                # Would need psutil for actual CPU monitoring
                # For now, just log that we're checking
                logger.debug(f"Checking CPU threshold: {threshold}% for {duration}s")

        except Exception as e:
            logger.debug(f"Could not check triggers: {e}")

    def check_and_raise(self, reason: TriggerReason, details: str = "") -> None:
        """
        Check condition and trigger kill switch if needed.

        Raises:
            KillSwitchTriggeredError: If kill switch is triggered
        """
        if self.is_triggered():
            raise KillSwitchTriggeredError(
                f"Kill switch already triggered: {self._trigger_reason}"
            )

        # Trigger the kill switch
        self.trigger(reason, details)

        # Raise error
        raise KillSwitchTriggeredError(
            f"Kill switch triggered: {reason.value}. {details}"
        )

    def get_history(self) -> list[KillSwitchEvent]:
        """Get history of kill switch events."""
        return self._history.copy()


class KillSwitchTriggeredError(Exception):
    """Raised when kill switch is triggered."""
    pass


# Global instance for convenience
_global_kill_switch: Optional[KillSwitch] = None


def get_kill_switch() -> KillSwitch:
    """Get the global kill switch instance."""
    global _global_kill_switch
    if _global_kill_switch is None:
        _global_kill_switch = KillSwitch()
    return _global_kill_switch


def arm_kill_switch() -> None:
    """Arm the global kill switch."""
    get_kill_switch().arm()


def trigger_kill_switch(reason: TriggerReason, details: str = "") -> None:
    """Trigger the global kill switch."""
    get_kill_switch().trigger(reason, details)


def is_kill_switch_armed() -> bool:
    """Check if global kill switch is armed."""
    return get_kill_switch().is_armed()


def is_kill_switch_triggered() -> bool:
    """Check if global kill switch is triggered."""
    return get_kill_switch().is_triggered()


def reset_kill_switch() -> bool:
    """Reset the global kill switch."""
    return get_kill_switch().reset()


def main():
    """CLI entry point for kill switch."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Kill Switch')
    parser.add_argument(
        '--arm',
        action='store_true',
        help='Arm the kill switch'
    )
    parser.add_argument(
        '--disarm',
        action='store_true',
        help='Disarm the kill switch'
    )
    parser.add_argument(
        '--trigger',
        type=str,
        choices=[r.value for r in TriggerReason],
        help='Trigger the kill switch with a reason'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset the kill switch'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show kill switch status'
    )
    parser.add_argument(
        '--details',
        type=str,
        default='',
        help='Details for trigger'
    )

    args = parser.parse_args()

    ks = KillSwitch()

    if args.arm:
        ks.arm()
        print("Kill switch ARMED")

    elif args.disarm:
        ks.disarm()
        print("Kill switch DISARMED")

    elif args.trigger:
        reason = TriggerReason(args.trigger)
        ks.trigger(reason, args.details)
        print(f"Kill switch TRIGGERED: {reason.value}")

    elif args.reset:
        if ks.reset():
            print("Kill switch RESET")
        else:
            print("Kill switch was not triggered")

    elif args.status:
        print(f"Armed: {ks.is_armed()}")
        print(f"Triggered: {ks.is_triggered()}")
        if ks.is_triggered():
            print(f"Reason: {ks.get_trigger_reason()}")
            print(f"Time: {ks.get_trigger_time()}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
