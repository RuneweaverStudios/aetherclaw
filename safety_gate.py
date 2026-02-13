#!/usr/bin/env python3
"""
Aether-Claw Safety Gate

Provides permission checking and user confirmation for sensitive actions.
"""

import logging
import os
from enum import Enum
from typing import Optional, Callable, Any
from dataclasses import dataclass

from config_loader import requires_confirmation, get_config_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ActionCategory(str, Enum):
    """Categories of actions that may require permission."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    NETWORK_REQUEST = "network_request"
    SYSTEM_COMMAND = "system_command"
    SKILL_CREATION = "skill_creation"
    SKILL_LOADING = "skill_loading"
    GIT_OPERATIONS = "git_operations"
    PACKAGE_INSTALLATION = "package_installation"
    DOCKER_OPERATIONS = "docker_operations"
    MEMORY_MODIFICATION = "memory_modification"
    CONFIG_CHANGE = "config_change"


@dataclass
class PermissionResult:
    """Result of a permission check."""
    allowed: bool
    reason: str
    requires_confirmation: bool
    confirmation_message: Optional[str] = None


class SafetyGate:
    """Manages permission checking and user confirmation for actions."""

    def __init__(
        self,
        unsafe_mode: bool = False,
        confirmation_handler: Optional[Callable[[str], bool]] = None
    ):
        """
        Initialize the safety gate.

        Args:
            unsafe_mode: If True, bypass all safety checks (for testing only)
            confirmation_handler: Optional function to handle confirmations
        """
        self._unsafe_mode = unsafe_mode or os.environ.get(
            'AETHER_UNSAFE_MODE', ''
        ).lower() in ('1', 'true', 'yes')

        self._confirmation_handler = confirmation_handler or self._default_confirmation
        self._blocked_actions: set[ActionCategory] = set()
        self._allowed_actions: set[ActionCategory] = set()

        # Track statistics
        self._stats = {
            'total_checks': 0,
            'allowed': 0,
            'denied': 0,
            'confirmations_requested': 0,
            'confirmations_granted': 0
        }

    def _default_confirmation(self, message: str) -> bool:
        """Default confirmation handler using stdin."""
        try:
            response = input(f"{message} [y/N]: ").strip().lower()
            return response in ('y', 'yes')
        except EOFError:
            return False

    def _log_to_audit(self, action: str, details: str, level: str = "INFO") -> None:
        """Log to audit log if available."""
        try:
            from audit_logger import log_action
            log_action(
                level=level,
                agent="SafetyGate",
                action=action,
                details=details
            )
        except ImportError:
            logger.info(f"[Audit] {action}: {details}")

    def check_permission(
        self,
        action_type: ActionCategory,
        details: str = "",
        resource: Optional[str] = None
    ) -> PermissionResult:
        """
        Check if an action is allowed.

        Args:
            action_type: Category of the action
            details: Description of the action
            resource: Optional resource being accessed

        Returns:
            PermissionResult with decision and details
        """
        self._stats['total_checks'] += 1

        # Unsafe mode bypasses all checks
        if self._unsafe_mode:
            self._stats['allowed'] += 1
            logger.warning(f"UNSAFE MODE: Allowing {action_type}")
            return PermissionResult(
                allowed=True,
                reason="Unsafe mode enabled",
                requires_confirmation=False
            )

        # Check if explicitly blocked
        if action_type in self._blocked_actions:
            self._stats['denied'] += 1
            self._log_to_audit(
                action="PERMISSION_DENIED",
                details=f"Action {action_type} is blocked: {details}",
                level="SECURITY"
            )
            return PermissionResult(
                allowed=False,
                reason=f"Action type {action_type} is blocked",
                requires_confirmation=False
            )

        # Check if explicitly allowed
        if action_type in self._allowed_actions:
            self._stats['allowed'] += 1
            return PermissionResult(
                allowed=True,
                reason="Action explicitly allowed",
                requires_confirmation=False
            )

        # Check configuration
        needs_confirmation = requires_confirmation(action_type.value)

        if not needs_confirmation:
            self._stats['allowed'] += 1
            self._log_to_audit(
                action="PERMISSION_GRANTED",
                details=f"{action_type}: {details}"
            )
            return PermissionResult(
                allowed=True,
                reason="Auto-approved by configuration",
                requires_confirmation=False
            )

        # Needs confirmation
        confirmation_msg = (
            f"Action required: {action_type.value}\n"
            f"Details: {details}"
        )
        if resource:
            confirmation_msg += f"\nResource: {resource}"

        self._stats['confirmations_requested'] += 1

        return PermissionResult(
            allowed=False,  # Not allowed until confirmed
            reason="Requires user confirmation",
            requires_confirmation=True,
            confirmation_message=confirmation_msg
        )

    def request_confirmation(
        self,
        action_type: ActionCategory,
        details: str = "",
        resource: Optional[str] = None
    ) -> bool:
        """
        Check permission and request confirmation if needed.

        Args:
            action_type: Category of the action
            details: Description of the action
            resource: Optional resource being accessed

        Returns:
            True if action is allowed, False otherwise
        """
        result = self.check_permission(action_type, details, resource)

        if result.allowed:
            return True

        if not result.requires_confirmation:
            return False

        # Request confirmation
        if result.confirmation_message:
            confirmed = self._confirmation_handler(result.confirmation_message)

            if confirmed:
                self._stats['confirmations_granted'] += 1
                self._stats['allowed'] += 1
                self._log_to_audit(
                    action="CONFIRMATION_GRANTED",
                    details=f"{action_type}: {details}"
                )
                return True
            else:
                self._stats['denied'] += 1
                self._log_to_audit(
                    action="CONFIRMATION_DENIED",
                    details=f"{action_type}: {details}",
                    level="WARN"
                )
                return False

        return False

    def block_action(self, action_type: ActionCategory, reason: str = "") -> None:
        """
        Block a specific action type.

        Args:
            action_type: Action type to block
            reason: Reason for blocking
        """
        self._blocked_actions.add(action_type)
        logger.warning(f"Action blocked: {action_type}. Reason: {reason}")

        self._log_to_audit(
            action="ACTION_BLOCKED",
            details=f"{action_type}: {reason}",
            level="SECURITY"
        )

    def unblock_action(self, action_type: ActionCategory) -> None:
        """
        Unblock a previously blocked action type.

        Args:
            action_type: Action type to unblock
        """
        self._blocked_actions.discard(action_type)
        logger.info(f"Action unblocked: {action_type}")

    def allow_action(self, action_type: ActionCategory) -> None:
        """
        Explicitly allow an action type (bypasses config).

        Args:
            action_type: Action type to allow
        """
        self._allowed_actions.add(action_type)
        logger.info(f"Action explicitly allowed: {action_type}")

    def disallow_action(self, action_type: ActionCategory) -> None:
        """
        Remove explicit allowance for an action type.

        Args:
            action_type: Action type to disallow
        """
        self._allowed_actions.discard(action_type)
        logger.info(f"Action explicit allowance removed: {action_type}")

    def get_stats(self) -> dict:
        """Get permission check statistics."""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            'total_checks': 0,
            'allowed': 0,
            'denied': 0,
            'confirmations_requested': 0,
            'confirmations_granted': 0
        }

    def is_unsafe_mode(self) -> bool:
        """Check if running in unsafe mode."""
        return self._unsafe_mode


def check_permission(
    action_type: ActionCategory,
    details: str = "",
    resource: Optional[str] = None
) -> PermissionResult:
    """
    Convenience function to check permission using global gate.

    Args:
        action_type: Category of the action
        details: Description of the action
        resource: Optional resource being accessed

    Returns:
        PermissionResult
    """
    gate = SafetyGate()
    return gate.check_permission(action_type, details, resource)


def request_confirmation(
    action_type: ActionCategory,
    details: str = "",
    resource: Optional[str] = None
) -> bool:
    """
    Convenience function to request confirmation using global gate.

    Args:
        action_type: Category of the action
        details: Description of the action
        resource: Optional resource being accessed

    Returns:
        True if allowed, False otherwise
    """
    gate = SafetyGate()
    return gate.request_confirmation(action_type, details, resource)


def main():
    """CLI entry point for safety gate."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Safety Gate')
    parser.add_argument(
        '--check',
        type=str,
        choices=[a.value for a in ActionCategory],
        help='Check if action requires confirmation'
    )
    parser.add_argument(
        '--confirm',
        type=str,
        choices=[a.value for a in ActionCategory],
        help='Request confirmation for action'
    )
    parser.add_argument(
        '--details',
        type=str,
        default='',
        help='Details for the action'
    )
    parser.add_argument(
        '--unsafe',
        action='store_true',
        help='Run in unsafe mode (bypass all checks)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics'
    )

    args = parser.parse_args()

    gate = SafetyGate(unsafe_mode=args.unsafe)

    if args.check:
        action = ActionCategory(args.check)
        result = gate.check_permission(action, args.details)
        print(f"Action: {action.value}")
        print(f"Allowed: {result.allowed}")
        print(f"Requires confirmation: {result.requires_confirmation}")
        print(f"Reason: {result.reason}")

    elif args.confirm:
        action = ActionCategory(args.confirm)
        allowed = gate.request_confirmation(action, args.details)
        print(f"Action {'allowed' if allowed else 'denied'}")

    elif args.stats:
        stats = gate.get_stats()
        print("Safety Gate Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
