#!/usr/bin/env python3
"""
Example Skill for Aether-Claw

This is an example skill demonstrating the signing workflow.
It provides simple utility functions for demonstration purposes.
"""

from typing import Optional


def greet(name: str = "World") -> str:
    """
    Generate a greeting message.

    Args:
        name: Name to greet (default: "World")

    Returns:
        Greeting string
    """
    return f"Hello, {name}! Welcome to Aether-Claw."


def calculate(a: float, b: float, operation: str = "add") -> float:
    """
    Perform a simple calculation.

    Args:
        a: First number
        b: Second number
        operation: Operation to perform (add, subtract, multiply, divide)

    Returns:
        Result of the calculation

    Raises:
        ValueError: If operation is unknown or division by zero
    """
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None
    }

    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}")

    result = operations[operation](a, b)

    if result is None:
        raise ValueError("Division by zero")

    return result


def format_timestamp(timestamp: Optional[float] = None) -> str:
    """
    Format a timestamp as a human-readable string.

    Args:
        timestamp: Unix timestamp (default: current time)

    Returns:
        Formatted timestamp string
    """
    import time
    from datetime import datetime

    if timestamp is None:
        timestamp = time.time()

    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_skill_info() -> dict:
    """
    Get information about this skill.

    Returns:
        Dictionary with skill metadata
    """
    return {
        "name": "example_skill",
        "version": "1.0.0",
        "description": "Example skill demonstrating Aether-Claw signing workflow",
        "functions": {
            "greet": "Generate a greeting message",
            "calculate": "Perform a simple calculation",
            "format_timestamp": "Format a timestamp",
            "get_skill_info": "Get skill metadata"
        }
    }


if __name__ == "__main__":
    # Demo
    print(get_skill_info())
    print()
    print(greet("Developer"))
    print(f"5 + 3 = {calculate(5, 3)}")
    print(f"Current time: {format_timestamp()}")
