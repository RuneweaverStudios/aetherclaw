#!/usr/bin/env python3
"""
Aether-Claw Safe Skill Creator

Creates and cryptographically signs skills for the Aether-Claw system.
Skills are scanned for vulnerabilities before signing.
"""

import json
import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

from keygen import KeyManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_SKILLS_DIR = Path(__file__).parent / 'skills'


@dataclass
class SkillMetadata:
    """Metadata for a signed skill."""
    name: str
    version: str
    description: str
    author: str
    created_at: str
    scan_passed: bool
    scan_report: Optional[str] = None


@dataclass
class SignedSkill:
    """A skill with its cryptographic signature."""
    metadata: SkillMetadata
    code: str
    signature: str


class SecurityError(Exception):
    """Raised when a security check fails."""
    pass


class SafeSkillCreator:
    """Creates and signs skills with security scanning."""

    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        key_manager: Optional[KeyManager] = None
    ):
        """
        Initialize the safe skill creator.

        Args:
            skills_dir: Directory to store signed skills
            key_manager: Key manager for signing operations
        """
        self.skills_dir = Path(skills_dir) if skills_dir else DEFAULT_SKILLS_DIR
        self.key_manager = key_manager or KeyManager()

        # Ensure skills directory exists
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def scan_code(self, code: str) -> tuple[bool, str]:
        """
        Scan skill code for security vulnerabilities using bandit.

        Args:
            code: Python code to scan

        Returns:
            Tuple of (passed, report) where passed is True if no issues found
        """
        # Write code to temporary file for scanning
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Run bandit scan
            result = subprocess.run(
                ['bandit', '-r', temp_path, '-f', 'json'],
                capture_output=True,
                text=True
            )

            # Parse results
            if result.returncode == 0:
                # No issues found
                return True, "No security issues identified"

            # Parse JSON output for details
            try:
                report = json.loads(result.stdout)
                issues = report.get('results', [])

                if not issues:
                    return True, "No security issues identified"

                # Format issues for report
                issue_list = []
                for issue in issues:
                    issue_list.append(
                        f"  [{issue.get('issue_severity', '?')}] "
                        f"{issue.get('test_id', '?')}: "
                        f"{issue.get('issue_text', 'Unknown issue')} "
                        f"(line {issue.get('line_number', '?')})"
                    )

                report_text = (
                    f"Security issues found ({len(issues)} total):\n" +
                    "\n".join(issue_list)
                )
                return False, report_text

            except json.JSONDecodeError:
                # Fallback to raw output
                return False, result.stdout or result.stderr

        except FileNotFoundError:
            logger.warning("Bandit not installed, skipping security scan")
            return True, "Bandit not available - scan skipped"

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    def sign_skill(
        self,
        code: str,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        author: str = "Aether-Claw",
        passphrase: Optional[bytes] = None,
        skip_scan: bool = False
    ) -> SignedSkill:
        """
        Create and sign a skill.

        Args:
            code: Python code for the skill
            name: Skill name (used for filename)
            version: Skill version
            description: Skill description
            author: Skill author
            passphrase: Passphrase for encrypted private key
            skip_scan: Skip security scan (not recommended)

        Returns:
            SignedSkill object with code and signature

        Raises:
            SecurityError: If security scan fails
        """
        # Run security scan
        if not skip_scan:
            passed, report = self.scan_code(code)
            if not passed:
                raise SecurityError(
                    f"Security scan failed for skill '{name}':\n{report}"
                )
        else:
            passed = True
            report = "Scan skipped by user"

        # Create metadata
        metadata = SkillMetadata(
            name=name,
            version=version,
            description=description,
            author=author,
            created_at=datetime.now().isoformat(),
            scan_passed=passed,
            scan_report=report
        )

        # Sign the code
        code_bytes = code.encode('utf-8')
        signature = self.key_manager.sign_data(code_bytes, passphrase)
        signature_hex = signature.hex()

        signed_skill = SignedSkill(
            metadata=metadata,
            code=code,
            signature=signature_hex
        )

        logger.info(f"Skill '{name}' signed successfully")
        return signed_skill

    def save_skill(self, signed_skill: SignedSkill) -> Path:
        """
        Save a signed skill to the skills directory.

        Args:
            signed_skill: SignedSkill object to save

        Returns:
            Path to the saved skill file
        """
        skill_path = self.skills_dir / f"{signed_skill.metadata.name}.json"

        # Prepare data for JSON serialization
        skill_data = {
            'metadata': asdict(signed_skill.metadata),
            'code': signed_skill.code,
            'signature': signed_skill.signature
        }

        with open(skill_path, 'w', encoding='utf-8') as f:
            json.dump(skill_data, f, indent=2)

        logger.info(f"Skill saved: {skill_path}")
        return skill_path

    def load_skill(self, skill_name: str) -> SignedSkill:
        """
        Load a signed skill from the skills directory.

        Args:
            skill_name: Name of the skill to load

        Returns:
            SignedSkill object

        Raises:
            FileNotFoundError: If skill doesn't exist
        """
        skill_path = self.skills_dir / f"{skill_name}.json"

        if not skill_path.exists():
            raise FileNotFoundError(f"Skill not found: {skill_path}")

        with open(skill_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        metadata = SkillMetadata(**data['metadata'])
        signed_skill = SignedSkill(
            metadata=metadata,
            code=data['code'],
            signature=data['signature']
        )

        return signed_skill

    def verify_skill(self, skill_name: str) -> tuple[bool, str]:
        """
        Verify the signature of a skill.

        Args:
            skill_name: Name of the skill to verify

        Returns:
            Tuple of (valid, message)
        """
        try:
            signed_skill = self.load_skill(skill_name)

            code_bytes = signed_skill.code.encode('utf-8')
            signature = bytes.fromhex(signed_skill.signature)

            is_valid = self.key_manager.verify_signature(
                code_bytes,
                signature
            )

            if is_valid:
                return True, f"Skill '{skill_name}' signature is valid"
            else:
                return False, f"Skill '{skill_name}' signature is INVALID"

        except FileNotFoundError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Verification error: {e}"

    def list_skills(self) -> list[dict]:
        """
        List all skills with their verification status.

        Returns:
            List of dictionaries with skill info and status
        """
        skills = []

        if not self.skills_dir.exists():
            return skills

        for skill_file in self.skills_dir.glob('*.json'):
            skill_name = skill_file.stem
            try:
                signed_skill = self.load_skill(skill_name)
                is_valid, _ = self.verify_skill(skill_name)

                skills.append({
                    'name': skill_name,
                    'version': signed_skill.metadata.version,
                    'description': signed_skill.metadata.description,
                    'created_at': signed_skill.metadata.created_at,
                    'scan_passed': signed_skill.metadata.scan_passed,
                    'signature_valid': is_valid
                })
            except Exception as e:
                skills.append({
                    'name': skill_name,
                    'error': str(e),
                    'signature_valid': False
                })

        return skills

    def create_skill_from_file(
        self,
        file_path: Path,
        name: Optional[str] = None,
        **kwargs
    ) -> SignedSkill:
        """
        Create a signed skill from a Python file.

        Args:
            file_path: Path to the Python file
            name: Skill name (defaults to filename without extension)
            **kwargs: Additional arguments for sign_skill

        Returns:
            SignedSkill object
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.suffix == '.py':
            raise ValueError("File must be a Python file (.py)")

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        name = name or file_path.stem
        return self.sign_skill(code, name=name, **kwargs)


def main():
    """CLI entry point for safe skill creator."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Safe Skill Creator')
    parser.add_argument(
        '--create', '-c',
        type=str,
        help='Create and sign a skill from a Python file'
    )
    parser.add_argument(
        '--name', '-n',
        type=str,
        help='Skill name (default: filename without extension)'
    )
    parser.add_argument(
        '--description', '-d',
        type=str,
        default='',
        help='Skill description'
    )
    parser.add_argument(
        '--verify', '-v',
        type=str,
        help='Verify a skill signature'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all skills with status'
    )
    parser.add_argument(
        '--skip-scan',
        action='store_true',
        help='Skip security scan (not recommended)'
    )

    args = parser.parse_args()

    creator = SafeSkillCreator()

    if args.create:
        try:
            signed = creator.create_skill_from_file(
                Path(args.create),
                name=args.name,
                description=args.description,
                skip_scan=args.skip_scan
            )
            path = creator.save_skill(signed)
            print(f"Skill created and signed: {path}")

        except (FileNotFoundError, SecurityError) as e:
            print(f"Error: {e}")

    elif args.verify:
        is_valid, message = creator.verify_skill(args.verify)
        print(message)
        if not is_valid:
            exit(1)

    elif args.list:
        skills = creator.list_skills()
        if not skills:
            print("No skills found")
            return

        print("Skills:")
        print("-" * 60)
        for skill in skills:
            status = "VALID" if skill.get('signature_valid') else "INVALID"
            scan = "PASS" if skill.get('scan_passed') else "FAIL"
            print(f"  {skill['name']}")
            print(f"    Version: {skill.get('version', '?')}")
            print(f"    Signature: {status}")
            print(f"    Security Scan: {scan}")
            print(f"    Created: {skill.get('created_at', '?')}")
            if 'error' in skill:
                print(f"    Error: {skill['error']}")
            print()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
