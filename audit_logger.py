#!/usr/bin/env python3
"""
Aether-Claw Audit Logger

Provides structured logging for all swarm actions to an append-only audit log.
"""

import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_AUDIT_FILE = Path(__file__).parent / 'brain' / 'audit_log.md'


class LogLevel(str, Enum):
    """Audit log levels."""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    SECURITY = "SECURITY"
    AUDIT = "AUDIT"


@dataclass
class AuditEntry:
    """Represents a single audit log entry."""
    timestamp: str
    level: LogLevel
    agent: str
    action: str
    details: str
    outcome: Optional[str] = None


class AuditLogger:
    """Manages structured audit logging to Markdown file."""

    def __init__(self, audit_file: Optional[Path] = None):
        """
        Initialize the audit logger.

        Args:
            audit_file: Path to the audit log file
        """
        self.audit_file = Path(audit_file) if audit_file else DEFAULT_AUDIT_FILE
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Ensure the audit log file exists with header."""
        if not self.audit_file.exists():
            # Create parent directory if needed
            self.audit_file.parent.mkdir(parents=True, exist_ok=True)

            # Write initial header
            header = """# Aether-Claw Audit Log

> **Classification**: Immutable Audit Trail
> **Created**: {created}
> **Warning**: DO NOT MODIFY EXISTING ENTRIES

## Log Format

```
[TIMESTAMP] [LEVEL] [AGENT] [ACTION] - Details
```

Levels: INFO | WARN | ERROR | SECURITY | AUDIT

---

## Audit Entries

""".format(created=datetime.now().strftime('%Y-%m-%d'))

            with open(self.audit_file, 'w', encoding='utf-8') as f:
                f.write(header)

            logger.info(f"Created audit log file: {self.audit_file}")

    def _format_entry(self, entry: AuditEntry) -> str:
        """Format an audit entry for the log file."""
        lines = [
            f"### {entry.timestamp} | {entry.level.value} | {entry.agent} | {entry.action}",
            f"- {entry.details}"
        ]

        if entry.outcome:
            lines.append(f"- Result: {entry.outcome}")

        lines.append("")  # Empty line after entry
        return "\n".join(lines)

    def log(
        self,
        level: LogLevel,
        agent: str,
        action: str,
        details: str,
        outcome: Optional[str] = None
    ) -> None:
        """
        Write an entry to the audit log.

        Args:
            level: Log level (INFO, WARN, ERROR, SECURITY, AUDIT)
            agent: Name of the agent performing the action
            action: Type of action being performed
            details: Detailed description of the action
            outcome: Optional outcome (success/failure/pending)
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            agent=agent,
            action=action,
            details=details,
            outcome=outcome
        )

        formatted = self._format_entry(entry)

        # Append to file
        with open(self.audit_file, 'a', encoding='utf-8') as f:
            f.write(formatted)

        # Also log to standard logging
        log_level = logging.INFO
        if level == LogLevel.WARN:
            log_level = logging.WARNING
        elif level == LogLevel.ERROR:
            log_level = logging.ERROR
        elif level == LogLevel.SECURITY:
            log_level = logging.WARNING  # No SECURITY level in stdlib

        logger.log(log_level, f"[{agent}] {action}: {details}")

    def log_action(
        self,
        level: str,
        agent: str,
        action: str,
        details: str,
        outcome: Optional[str] = None
    ) -> None:
        """
        Convenience function for logging actions with string level.

        Args:
            level: Log level as string
            agent: Name of the agent
            action: Type of action
            details: Detailed description
            outcome: Optional outcome
        """
        try:
            log_level = LogLevel[level.upper()]
        except KeyError:
            log_level = LogLevel.INFO

        self.log(log_level, agent, action, details, outcome)

    def log_skill_execution(
        self,
        skill_name: str,
        agent: str,
        outcome: str,
        details: Optional[str] = None
    ) -> None:
        """
        Log a skill execution event.

        Args:
            skill_name: Name of the executed skill
            agent: Agent that executed the skill
            outcome: Outcome (success/failure)
            details: Optional additional details
        """
        self.log(
            level=LogLevel.AUDIT,
            agent=agent,
            action="SKILL_EXECUTION",
            details=details or f"Executed skill: {skill_name}",
            outcome=outcome
        )

    def log_security_event(
        self,
        event_type: str,
        details: str,
        agent: str = "SYSTEM",
        outcome: Optional[str] = None
    ) -> None:
        """
        Log a security-related event.

        Args:
            event_type: Type of security event
            details: Details of the event
            agent: Agent involved (default: SYSTEM)
            outcome: Optional outcome
        """
        self.log(
            level=LogLevel.SECURITY,
            agent=agent,
            action=f"SECURITY_{event_type.upper()}",
            details=details,
            outcome=outcome
        )

    def log_anomaly(
        self,
        anomaly_type: str,
        severity: str,
        resolution: Optional[str] = None
    ) -> None:
        """
        Log a detected anomaly.

        Args:
            anomaly_type: Type of anomaly detected
            severity: Severity level (low/medium/high/critical)
            resolution: How the anomaly was resolved
        """
        self.log(
            level=LogLevel.WARN,
            agent="SYSTEM",
            action="ANOMALY_DETECTED",
            details=f"[{severity.upper()}] {anomaly_type}",
            outcome=resolution or "pending"
        )

    def log_kill_switch(
        self,
        trigger: str,
        initiated_by: str = "SYSTEM"
    ) -> None:
        """
        Log a kill switch activation.

        Args:
            trigger: What triggered the kill switch
            initiated_by: Who initiated (default: SYSTEM)
        """
        self.log(
            level=LogLevel.SECURITY,
            agent=initiated_by,
            action="KILL_SWITCH_ACTIVATED",
            details=f"Trigger: {trigger}",
            outcome="all_operations_halted"
        )

    def get_recent_entries(self, count: int = 10) -> list[str]:
        """
        Get recent entries from the audit log.

        Args:
            count: Number of entries to retrieve

        Returns:
            List of log entry strings
        """
        if not self.audit_file.exists():
            return []

        entries = []
        current_entry = []

        with open(self.audit_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('### '):
                    if current_entry:
                        entries.append(''.join(current_entry))
                        if len(entries) >= count:
                            break
                    current_entry = [line]
                elif current_entry:
                    current_entry.append(line)

        return entries

    def search(self, query: str) -> list[str]:
        """
        Search the audit log for matching entries.

        Args:
            query: Search string

        Returns:
            List of matching entry strings
        """
        if not self.audit_file.exists():
            return []

        matches = []
        current_entry = []

        with open(self.audit_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('### '):
                    if current_entry:
                        entry_text = ''.join(current_entry)
                        if query.lower() in entry_text.lower():
                            matches.append(entry_text)
                    current_entry = [line]
                elif current_entry:
                    current_entry.append(line)

        return matches


# Global instance for convenience
_global_logger: Optional[AuditLogger] = None


def get_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = AuditLogger()
    return _global_logger


def log_action(
    level: str,
    agent: str,
    action: str,
    details: str,
    outcome: Optional[str] = None
) -> None:
    """Convenience function for logging using global logger."""
    get_logger().log_action(level, agent, action, details, outcome)


def log_security_event(
    event_type: str,
    details: str,
    agent: str = "SYSTEM",
    outcome: Optional[str] = None
) -> None:
    """Convenience function for logging security events."""
    get_logger().log_security_event(event_type, details, agent, outcome)


def main():
    """CLI entry point for audit logger."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Audit Logger')
    parser.add_argument(
        '--recent', '-r',
        type=int,
        default=10,
        help='Show recent entries (default: 10)'
    )
    parser.add_argument(
        '--search', '-s',
        type=str,
        help='Search for entries matching query'
    )
    parser.add_argument(
        '--log',
        type=str,
        nargs=4,
        metavar=('LEVEL', 'AGENT', 'ACTION', 'DETAILS'),
        help='Add a manual log entry'
    )

    args = parser.parse_args()

    audit = AuditLogger()

    if args.log:
        level, agent, action, details = args.log
        audit.log_action(level, agent, action, details)
        print(f"Logged: [{level}] [{agent}] [{action}]")

    elif args.search:
        matches = audit.search(args.search)
        if not matches:
            print(f"No entries found matching: {args.search}")
        else:
            print(f"Found {len(matches)} matching entries:")
            for entry in matches[:10]:  # Limit output
                print(entry)

    else:
        entries = audit.get_recent_entries(args.recent)
        if not entries:
            print("No audit entries found")
        else:
            print(f"Recent {len(entries)} entries:")
            for entry in entries:
                print(entry)


if __name__ == '__main__':
    main()
