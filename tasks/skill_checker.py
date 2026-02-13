#!/usr/bin/env python3
"""
Aether-Claw Skill Integrity Checker

Verifies cryptographic signatures of all skills.
"""

import logging
from dataclasses import dataclass
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SkillVerificationResult:
    """Result of verifying a single skill."""
    skill_name: str
    signature_valid: bool
    is_signed: bool
    error: Optional[str] = None


@dataclass
class IntegrityCheckResult:
    """Result of full integrity check."""
    total_skills: int
    valid_skills: int
    invalid_skills: int
    unsigned_skills: int
    skills: list[SkillVerificationResult]


def check_all_skills() -> IntegrityCheckResult:
    """
    Verify all skills in the skills directory.

    Returns:
        IntegrityCheckResult with verification status
    """
    import sys
    from pathlib import Path

    # Add parent to path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from safe_skill_creator import SafeSkillCreator

    creator = SafeSkillCreator()
    skills = creator.list_skills()

    results = []
    valid = 0
    invalid = 0
    unsigned = 0

    for skill in skills:
        name = skill.get('name', 'unknown')
        is_valid = skill.get('signature_valid', False)

        # Check if it was an error case
        if 'error' in skill:
            unsigned += 1
            results.append(SkillVerificationResult(
                skill_name=name,
                signature_valid=False,
                is_signed=False,
                error=skill['error']
            ))
        elif is_valid:
            valid += 1
            results.append(SkillVerificationResult(
                skill_name=name,
                signature_valid=True,
                is_signed=True
            ))
        else:
            invalid += 1
            results.append(SkillVerificationResult(
                skill_name=name,
                signature_valid=False,
                is_signed=True,
                error="Signature verification failed"
            ))

    return IntegrityCheckResult(
        total_skills=len(skills),
        valid_skills=valid,
        invalid_skills=invalid,
        unsigned_skills=unsigned,
        skills=results
    )


def check_skill_integrity(skill_name: str) -> SkillVerificationResult:
    """
    Check integrity of a specific skill.

    Args:
        skill_name: Name of the skill to check

    Returns:
        SkillVerificationResult
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from safe_skill_creator import SafeSkillCreator

    creator = SafeSkillCreator()

    try:
        is_valid, message = creator.verify_skill(skill_name)
        return SkillVerificationResult(
            skill_name=skill_name,
            signature_valid=is_valid,
            is_signed=True,
            error=None if is_valid else message
        )
    except FileNotFoundError:
        return SkillVerificationResult(
            skill_name=skill_name,
            signature_valid=False,
            is_signed=False,
            error="Skill not found"
        )
    except Exception as e:
        return SkillVerificationResult(
            skill_name=skill_name,
            signature_valid=False,
            is_signed=True,
            error=str(e)
        )


def trigger_on_failure(result: IntegrityCheckResult) -> bool:
    """
    Check if kill switch should be triggered based on results.

    Args:
        result: IntegrityCheckResult to evaluate

    Returns:
        True if kill switch should be triggered
    """
    # Trigger if any invalid skills found (signed but tampered)
    return result.invalid_skills > 0


def main():
    """CLI entry point for skill checker."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Skill Checker')
    parser.add_argument(
        '--check-all',
        action='store_true',
        help='Check all skills'
    )
    parser.add_argument(
        '--skill',
        type=str,
        help='Check a specific skill'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    args = parser.parse_args()

    import json as json_module

    if args.check_all:
        result = check_all_skills()

        if args.json:
            output = {
                'total': result.total_skills,
                'valid': result.valid_skills,
                'invalid': result.invalid_skills,
                'unsigned': result.unsigned_skills,
                'skills': [
                    {
                        'name': s.skill_name,
                        'valid': s.signature_valid,
                        'signed': s.is_signed,
                        'error': s.error
                    }
                    for s in result.skills
                ]
            }
            print(json_module.dumps(output, indent=2))
        else:
            print(f"Total skills: {result.total_skills}")
            print(f"Valid: {result.valid_skills}")
            print(f"Invalid: {result.invalid_skills}")
            print(f"Unsigned: {result.unsigned_skills}")

            if result.invalid_skills > 0 or result.unsigned_skills > 0:
                print("\nProblematic skills:")
                for skill in result.skills:
                    if not skill.signature_valid:
                        print(f"  - {skill.skill_name}: {skill.error or 'Invalid signature'}")

    elif args.skill:
        result = check_skill_integrity(args.skill)

        if args.json:
            output = {
                'name': result.skill_name,
                'valid': result.signature_valid,
                'signed': result.is_signed,
                'error': result.error
            }
            print(json_module.dumps(output, indent=2))
        else:
            print(f"Skill: {result.skill_name}")
            print(f"Signed: {result.is_signed}")
            print(f"Valid: {result.signature_valid}")
            if result.error:
                print(f"Error: {result.error}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
