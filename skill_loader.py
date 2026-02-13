#!/usr/bin/env python3
"""
Aether-Claw Skill Loader

Loads and verifies skills before execution. All skills must have valid
cryptographic signatures to be loaded.
"""

import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from safe_skill_creator import SafeSkillCreator, SignedSkill

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_SKILLS_DIR = Path(__file__).parent / 'skills'


class SecurityError(Exception):
    """Raised when a security check fails."""
    pass


@dataclass
class LoadedSkill:
    """A skill that has been loaded and verified."""
    name: str
    module: Any
    metadata: dict
    signature_valid: bool
    loaded_at: str


class SkillLoader:
    """Loads and manages skills with signature verification."""

    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        auto_log: bool = True
    ):
        """
        Initialize the skill loader.

        Args:
            skills_dir: Directory containing signed skills
            auto_log: Whether to automatically log to audit log
        """
        self.skills_dir = Path(skills_dir) if skills_dir else DEFAULT_SKILLS_DIR
        self.creator = SafeSkillCreator(skills_dir=self.skills_dir)
        self.auto_log = auto_log

        # Track loaded skills
        self._loaded_skills: dict[str, LoadedSkill] = {}

    def _log_to_audit(self, message: str, level: str = "INFO") -> None:
        """Log a message to the audit log."""
        if not self.auto_log:
            return

        try:
            from audit_logger import log_action
            log_action(
                level=level,
                agent="SkillLoader",
                action="skill_operation",
                details=message
            )
        except ImportError:
            logger.info(f"[Audit] {message}")

    def load_skill(self, skill_name: str, verify: bool = True) -> LoadedSkill:
        """
        Load a skill after verifying its signature.

        Args:
            skill_name: Name of the skill to load
            verify: Whether to verify signature (default: True)

        Returns:
            LoadedSkill object

        Raises:
            SecurityError: If signature verification fails
            FileNotFoundError: If skill doesn't exist
        """
        from datetime import datetime

        # Verify signature if required
        if verify:
            is_valid, message = self.creator.verify_skill(skill_name)
            if not is_valid:
                self._log_to_audit(
                    f"Skill load REJECTED: {skill_name} - {message}",
                    level="SECURITY"
                )
                raise SecurityError(
                    f"Cannot load skill '{skill_name}': {message}"
                )

        # Load the signed skill
        signed_skill = self.creator.load_skill(skill_name)

        # Create a module from the skill code
        module = self._create_module(skill_name, signed_skill.code)

        # Create loaded skill record
        loaded = LoadedSkill(
            name=skill_name,
            module=module,
            metadata={
                'version': signed_skill.metadata.version,
                'description': signed_skill.metadata.description,
                'author': signed_skill.metadata.author,
                'created_at': signed_skill.metadata.created_at,
                'scan_passed': signed_skill.metadata.scan_passed
            },
            signature_valid=True,
            loaded_at=datetime.now().isoformat()
        )

        # Store in loaded skills
        self._loaded_skills[skill_name] = loaded

        self._log_to_audit(
            f"Skill loaded: {skill_name} v{loaded.metadata['version']}"
        )

        logger.info(f"Skill '{skill_name}' loaded successfully")
        return loaded

    def _create_module(self, name: str, code: str) -> Any:
        """
        Create a Python module from skill code.

        Args:
            name: Module name
            code: Python code

        Returns:
            Module object
        """
        # Create a unique module name
        module_name = f"aether_skill_{name}"

        # Create module spec
        spec = importlib.util.spec_from_loader(module_name, loader=None)
        if spec is None:
            raise RuntimeError(f"Failed to create module spec for {name}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        # Execute the code in the module's namespace
        exec(code, module.__dict__)

        return module

    def unload_skill(self, skill_name: str) -> bool:
        """
        Unload a skill from memory.

        Args:
            skill_name: Name of the skill to unload

        Returns:
            True if skill was unloaded, False if it wasn't loaded
        """
        if skill_name not in self._loaded_skills:
            return False

        # Remove from loaded skills
        del self._loaded_skills[skill_name]

        # Remove from sys.modules
        module_name = f"aether_skill_{skill_name}"
        if module_name in sys.modules:
            del sys.modules[module_name]

        self._log_to_audit(f"Skill unloaded: {skill_name}")

        logger.info(f"Skill '{skill_name}' unloaded")
        return True

    def get_skill(self, skill_name: str) -> Optional[LoadedSkill]:
        """
        Get a loaded skill by name.

        Args:
            skill_name: Name of the skill

        Returns:
            LoadedSkill object or None if not loaded
        """
        return self._loaded_skills.get(skill_name)

    def execute_skill_function(
        self,
        skill_name: str,
        function_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function from a loaded skill.

        Args:
            skill_name: Name of the skill
            function_name: Name of the function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Function result

        Raises:
            ValueError: If skill is not loaded or function doesn't exist
        """
        loaded = self.get_skill(skill_name)
        if loaded is None:
            raise ValueError(f"Skill '{skill_name}' is not loaded")

        if not hasattr(loaded.module, function_name):
            raise ValueError(
                f"Skill '{skill_name}' has no function '{function_name}'"
            )

        func = getattr(loaded.module, function_name)

        self._log_to_audit(
            f"Executing skill function: {skill_name}.{function_name}"
        )

        return func(*args, **kwargs)

    def list_skills(self) -> list[dict]:
        """
        List all available skills with their status.

        Returns:
            List of skill information dictionaries
        """
        skills = self.creator.list_skills()

        # Add loaded status
        for skill in skills:
            skill['loaded'] = skill['name'] in self._loaded_skills

        return skills

    def list_loaded_skills(self) -> list[str]:
        """
        List names of currently loaded skills.

        Returns:
            List of loaded skill names
        """
        return list(self._loaded_skills.keys())

    def verify_all_loaded(self) -> dict[str, tuple[bool, str]]:
        """
        Re-verify signatures of all loaded skills.

        Returns:
            Dictionary mapping skill names to (valid, message) tuples
        """
        results = {}

        for skill_name in self._loaded_skills:
            is_valid, message = self.creator.verify_skill(skill_name)
            results[skill_name] = (is_valid, message)

            if not is_valid:
                self._log_to_audit(
                    f"Skill verification FAILED: {skill_name} - {message}",
                    level="SECURITY"
                )

        return results

    def reload_skill(self, skill_name: str) -> LoadedSkill:
        """
        Reload a skill (unload and load again with fresh verification).

        Args:
            skill_name: Name of the skill to reload

        Returns:
            Newly loaded LoadedSkill object
        """
        self.unload_skill(skill_name)
        return self.load_skill(skill_name)


def main():
    """CLI entry point for skill loader."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Skill Loader')
    parser.add_argument(
        '--load', '-l',
        type=str,
        help='Load a skill'
    )
    parser.add_argument(
        '--unload', '-u',
        type=str,
        help='Unload a skill'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all skills with status'
    )
    parser.add_argument(
        '--loaded',
        action='store_true',
        help='List loaded skills'
    )
    parser.add_argument(
        '--verify-all',
        action='store_true',
        help='Verify all loaded skills'
    )
    parser.add_argument(
        '--no-verify',
        action='store_true',
        help='Skip signature verification (dangerous)'
    )

    args = parser.parse_args()

    loader = SkillLoader()

    if args.load:
        try:
            loaded = loader.load_skill(args.load, verify=not args.no_verify)
            print(f"Skill loaded: {loaded.name}")
            print(f"  Version: {loaded.metadata['version']}")
            print(f"  Description: {loaded.metadata['description']}")

        except SecurityError as e:
            print(f"Security error: {e}")
            exit(1)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            exit(1)

    elif args.unload:
        if loader.unload_skill(args.unload):
            print(f"Skill unloaded: {args.unload}")
        else:
            print(f"Skill was not loaded: {args.unload}")

    elif args.list:
        skills = loader.list_skills()
        if not skills:
            print("No skills found")
            return

        print("Available Skills:")
        print("-" * 60)
        for skill in skills:
            sig_status = "VALID" if skill.get('signature_valid') else "INVALID"
            load_status = "LOADED" if skill.get('loaded') else "unloaded"
            print(f"  {skill['name']} [{load_status}]")
            print(f"    Signature: {sig_status}")
            print(f"    Version: {skill.get('version', '?')}")

    elif args.loaded:
        loaded = loader.list_loaded_skills()
        if not loaded:
            print("No skills loaded")
        else:
            print("Loaded skills:")
            for name in loaded:
                print(f"  - {name}")

    elif args.verify_all:
        results = loader.verify_all_loaded()
        if not results:
            print("No skills loaded")
        else:
            print("Verification results:")
            for name, (valid, msg) in results.items():
                status = "VALID" if valid else "INVALID"
                print(f"  {name}: {status}")
                if not valid:
                    print(f"    {msg}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
