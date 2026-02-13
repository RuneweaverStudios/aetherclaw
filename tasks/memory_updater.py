#!/usr/bin/env python3
"""
Aether-Claw Memory Updater Task

Updates the brain index when memory files change.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
BRAIN_DIR = Path(__file__).parent.parent / 'brain'
HASH_FILE = BRAIN_DIR / '.file_hashes.json'


@dataclass
class FileChange:
    """Represents a file change."""
    file_name: str
    change_type: str  # new, modified, deleted
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None


def compute_file_hash(file_path: Path) -> str:
    """Compute MD5 hash of a file."""
    hasher = hashlib.md5()

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_stored_hashes() -> dict[str, str]:
    """Load stored file hashes from disk."""
    if not HASH_FILE.exists():
        return {}

    try:
        with open(HASH_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading hashes: {e}")
        return {}


def save_stored_hashes(hashes: dict[str, str]) -> None:
    """Save file hashes to disk."""
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(HASH_FILE, 'w') as f:
        json.dump(hashes, f, indent=2)


def check_memory_changes() -> list[FileChange]:
    """
    Check for changes in memory files.

    Returns:
        List of FileChange objects
    """
    changes = []
    stored_hashes = load_stored_hashes()
    current_hashes = {}

    # Get all markdown files
    if not BRAIN_DIR.exists():
        logger.warning(f"Brain directory not found: {BRAIN_DIR}")
        return changes

    md_files = list(BRAIN_DIR.glob('*.md'))

    for file_path in md_files:
        file_name = file_path.name
        current_hash = compute_file_hash(file_path)
        current_hashes[file_name] = current_hash

        if file_name not in stored_hashes:
            # New file
            changes.append(FileChange(
                file_name=file_name,
                change_type='new',
                new_hash=current_hash
            ))
        elif stored_hashes[file_name] != current_hash:
            # Modified file
            changes.append(FileChange(
                file_name=file_name,
                change_type='modified',
                old_hash=stored_hashes[file_name],
                new_hash=current_hash
            ))

    # Check for deleted files
    for file_name in stored_hashes:
        if file_name not in current_hashes:
            changes.append(FileChange(
                file_name=file_name,
                change_type='deleted',
                old_hash=stored_hashes[file_name]
            ))

    return changes


def update_index_for_changes(changes: list[FileChange]) -> dict:
    """
    Update the brain index for changed files.

    Args:
        changes: List of file changes

    Returns:
        Dictionary with update results
    """
    from brain_index import BrainIndexer

    indexer = BrainIndexer()
    results = {
        'indexed': [],
        'errors': [],
        'skipped': []
    }

    for change in changes:
        if change.change_type == 'deleted':
            # Can't index deleted files
            results['skipped'].append({
                'file': change.file_name,
                'reason': 'deleted'
            })
            continue

        try:
            file_path = BRAIN_DIR / change.file_name
            version = indexer.index_file(file_path)
            results['indexed'].append({
                'file': change.file_name,
                'version': version,
                'change_type': change.change_type
            })
            logger.info(f"Indexed {change.file_name} (v{version})")

        except Exception as e:
            results['errors'].append({
                'file': change.file_name,
                'error': str(e)
            })
            logger.error(f"Error indexing {change.file_name}: {e}")

    return results


def run_memory_update() -> dict:
    """
    Run the full memory update process.

    Returns:
        Dictionary with update results
    """
    logger.info("Checking for memory changes...")

    # Check for changes
    changes = check_memory_changes()

    if not changes:
        logger.info("No memory changes detected")
        return {
            'changes_detected': 0,
            'indexed': 0,
            'errors': 0
        }

    logger.info(f"Detected {len(changes)} changes")

    # Update index
    results = update_index_for_changes(changes)

    # Update stored hashes for non-deleted files
    new_hashes = load_stored_hashes()
    for change in changes:
        if change.change_type == 'deleted':
            new_hashes.pop(change.file_name, None)
        else:
            new_hashes[change.file_name] = change.new_hash

    save_stored_hashes(new_hashes)

    return {
        'changes_detected': len(changes),
        'indexed': len(results['indexed']),
        'errors': len(results['errors']),
        'details': results
    }


def main():
    """CLI entry point for memory updater."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Memory Updater')
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check for changes without updating'
    )
    parser.add_argument(
        '--update',
        action='store_true',
        help='Update index for any changes'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reindex of all files'
    )

    args = parser.parse_args()

    if args.check:
        changes = check_memory_changes()
        if not changes:
            print("No changes detected")
        else:
            print(f"Detected {len(changes)} changes:")
            for change in changes:
                print(f"  [{change.change_type}] {change.file_name}")

    elif args.update:
        results = run_memory_update()
        print(f"Changes detected: {results['changes_detected']}")
        print(f"Files indexed: {results['indexed']}")
        print(f"Errors: {results['errors']}")

    elif args.force:
        from brain_index import BrainIndexer

        indexer = BrainIndexer()
        indexer.clear_index()
        results = indexer.index_all()

        # Update hashes
        new_hashes = {}
        for file_path in BRAIN_DIR.glob('*.md'):
            new_hashes[file_path.name] = compute_file_hash(file_path)
        save_stored_hashes(new_hashes)

        print(f"Force reindexed {len(results)} files")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
