# Aether-Claw Skills

This directory contains cryptographically signed skills for Aether-Claw.

## What are Skills?

Skills are Python modules that extend Aether-Claw's capabilities. Each skill:
- Provides useful functions or utilities
- Must be cryptographically signed before loading
- Is scanned for security vulnerabilities before signing
- Runs in a sandboxed environment

## Skill Signing Workflow

### 1. Create Your Skill

Write a Python module with your desired functions:

```python
# skills/my_skill.py

def my_function(arg: str) -> str:
    """Do something useful."""
    return f"Processed: {arg}"
```

### 2. Sign the Skill

```bash
python aether_claw.py sign-skill --create skills/my_skill.py --name my_skill --description "My custom skill"
```

This will:
1. Scan the code with Bandit for security issues
2. Generate a cryptographic signature
3. Save the signed skill to `skills/my_skill.json`

### 3. Verify the Skill

```bash
python aether_claw.py sign-skill --verify my_skill
```

### 4. Use the Skill

The skill can now be loaded and executed by Aether-Claw:

```python
from skill_loader import SkillLoader

loader = SkillLoader()
skill = loader.load_skill("my_skill")
result = loader.execute_skill_function("my_skill", "my_function", "test")
```

## Security Requirements

Skills MUST pass these checks to be signed:

1. **Bandit Scan**: No high/critical security vulnerabilities
2. **Code Review**: Manual review for suspicious patterns
3. **Signature**: Valid RSA signature from authorized key

## Current Skills

| Skill | Description | Status |
|-------|-------------|--------|
| example_skill | Example demonstrating signing workflow | Unsigned (template) |

## Adding New Skills

1. Create your skill Python file in this directory
2. Test it thoroughly
3. Sign it using the CLI
4. Verify it loads correctly
5. Update this README

## Skill Template

```python
#!/usr/bin/env python3
"""
Skill Name - Brief Description

Detailed description of what this skill does.
"""

from typing import Optional


def main_function(arg: str) -> str:
    """
    Main function description.

    Args:
        arg: Description of argument

    Returns:
        Description of return value
    """
    # Implementation
    return result


def get_skill_info() -> dict:
    """Return skill metadata."""
    return {
        "name": "skill_name",
        "version": "1.0.0",
        "description": "Brief description",
        "functions": {
            "main_function": "What it does"
        }
    }
```
