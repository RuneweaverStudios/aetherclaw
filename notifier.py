#!/usr/bin/env python3
"""
Aether-Claw Notifier

Provides system notifications using plyer library.
"""

import logging
from enum import Enum
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import plyer, fall back to logging if not available
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    logger.warning("plyer not installed, notifications will be logged only")


class NotificationLevel(str, Enum):
    """Notification levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class Notifier:
    """Sends system notifications."""

    def __init__(self, app_name: str = "Aether-Claw"):
        """
        Initialize the notifier.

        Args:
            app_name: Application name for notifications
        """
        self.app_name = app_name
        self._stats = {
            'total_sent': 0,
            'successful': 0,
            'failed': 0
        }

    def _log_to_audit(self, action: str, details: str, level: str = "INFO") -> None:
        """Log to audit log if available."""
        try:
            from audit_logger import log_action
            log_action(
                level=level,
                agent="Notifier",
                action=action,
                details=details
            )
        except ImportError:
            logger.info(f"[Audit] {action}: {details}")

    def send(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        timeout: int = 10
    ) -> bool:
        """
        Send a system notification.

        Args:
            title: Notification title
            message: Notification message
            level: Notification level (affects logging)
            timeout: Notification timeout in seconds

        Returns:
            True if notification was sent successfully
        """
        self._stats['total_sent'] += 1

        # Log the notification
        log_level = logging.INFO
        if level == NotificationLevel.WARNING:
            log_level = logging.WARNING
        elif level == NotificationLevel.ERROR:
            log_level = logging.ERROR

        logger.log(log_level, f"[{level.value.upper()}] {title}: {message}")

        # Try to send system notification
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title=f"{self.app_name}: {title}",
                    message=message,
                    app_name=self.app_name,
                    timeout=timeout
                )
                self._stats['successful'] += 1

                self._log_to_audit(
                    action="NOTIFICATION_SENT",
                    details=f"{level.value}: {title}"
                )

                return True

            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
                self._stats['failed'] += 1
                return False
        else:
            # Log only mode
            self._log_to_audit(
                action="NOTIFICATION_LOGGED",
                details=f"{level.value}: {title} (plyer not available)"
            )
            return True

    def info(self, title: str, message: str) -> bool:
        """Send an info notification."""
        return self.send(title, message, NotificationLevel.INFO)

    def warning(self, title: str, message: str) -> bool:
        """Send a warning notification."""
        return self.send(title, message, NotificationLevel.WARNING)

    def error(self, title: str, message: str) -> bool:
        """Send an error notification."""
        return self.send(title, message, NotificationLevel.ERROR)

    def success(self, title: str, message: str) -> bool:
        """Send a success notification."""
        return self.send(title, message, NotificationLevel.SUCCESS)

    def send_confirmation_request(
        self,
        title: str,
        message: str
    ) -> bool:
        """
        Send a notification requesting user confirmation.

        Note: This just sends a notification. For actual confirmation,
        use safety_gate.request_confirmation().

        Args:
            title: Notification title
            message: Notification message

        Returns:
            True if notification was sent
        """
        full_message = f"{message}\n\nAction requires your confirmation."
        return self.warning(title, full_message)

    def send_skill_alert(
        self,
        skill_name: str,
        issue: str
    ) -> bool:
        """
        Send an alert about a skill issue.

        Args:
            skill_name: Name of the skill
            issue: Description of the issue

        Returns:
            True if notification was sent
        """
        return self.error(
            title=f"Skill Alert: {skill_name}",
            message=issue
        )

    def send_heartbeat_status(
        self,
        task_name: str,
        status: str,
        details: Optional[str] = None
    ) -> bool:
        """
        Send a heartbeat task status notification.

        Args:
            task_name: Name of the heartbeat task
            status: Status (running, completed, failed)
            details: Optional additional details

        Returns:
            True if notification was sent
        """
        message = f"Task '{task_name}' {status}"
        if details:
            message += f": {details}"

        level = NotificationLevel.INFO
        if status == "failed":
            level = NotificationLevel.ERROR

        return self.send("Heartbeat Status", message, level)

    def get_stats(self) -> dict:
        """Get notification statistics."""
        return self._stats.copy()


# Global instance for convenience
_global_notifier: Optional[Notifier] = None


def get_notifier() -> Notifier:
    """Get the global notifier instance."""
    global _global_notifier
    if _global_notifier is None:
        _global_notifier = Notifier()
    return _global_notifier


def send_notification(
    title: str,
    message: str,
    level: NotificationLevel = NotificationLevel.INFO
) -> bool:
    """Send a notification using global notifier."""
    return get_notifier().send(title, message, level)


def main():
    """CLI entry point for notifier."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Notifier')
    parser.add_argument(
        '--title', '-t',
        type=str,
        required=True,
        help='Notification title'
    )
    parser.add_argument(
        '--message', '-m',
        type=str,
        required=True,
        help='Notification message'
    )
    parser.add_argument(
        '--level', '-l',
        type=str,
        choices=['info', 'warning', 'error', 'success'],
        default='info',
        help='Notification level'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show notification statistics'
    )

    args = parser.parse_args()

    notifier = Notifier()

    if args.stats:
        stats = notifier.get_stats()
        print("Notification Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    else:
        level = NotificationLevel(args.level)
        success = notifier.send(args.title, args.message, level)
        if success:
            print("Notification sent successfully")
        else:
            print("Failed to send notification")


if __name__ == '__main__':
    main()
