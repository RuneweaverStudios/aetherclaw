#!/usr/bin/env python3
"""
Aether-Claw Git Repository Scanner

Scans local Git repositories for issues and potential problems.
"""

import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RepositoryIssue:
    """Represents an issue found in a repository."""
    repo_path: str
    issue_type: str
    description: str
    severity: str  # low, medium, high


@dataclass
class RepositoryStatus:
    """Status of a Git repository."""
    path: str
    branch: str
    is_clean: bool
    uncommitted_changes: int
    unpushed_commits: int
    stale_branches: list[str]
    issues: list[RepositoryIssue]


def run_git_command(repo_path: Path, args: list[str]) -> tuple[bool, str]:
    """
    Run a git command in a repository.

    Args:
        repo_path: Path to the repository
        args: Git command arguments

    Returns:
        Tuple of (success, output)
    """
    try:
        result = subprocess.run(
            ['git'] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def is_git_repository(path: Path) -> bool:
    """Check if a path is a Git repository."""
    git_dir = path / '.git'
    return git_dir.exists()


def get_current_branch(repo_path: Path) -> str:
    """Get the current branch name."""
    success, output = run_git_command(repo_path, ['branch', '--show-current'])
    return output if success else "unknown"


def get_uncommitted_changes(repo_path: Path) -> int:
    """Get count of uncommitted changes."""
    success, output = run_git_command(repo_path, ['status', '--porcelain'])
    if not success:
        return 0
    return len([l for l in output.split('\n') if l.strip()])


def get_unpushed_commits(repo_path: Path) -> int:
    """Get count of unpushed commits."""
    # Get current branch
    branch = get_current_branch(repo_path)
    if branch == "unknown":
        return 0

    # Check unpushed commits
    success, output = run_git_command(
        repo_path,
        ['log', f'origin/{branch}..HEAD', '--oneline']
    )
    if not success:
        # Might not have upstream
        return 0

    return len([l for l in output.split('\n') if l.strip()])


def get_stale_branches(repo_path: Path, days: int = 30) -> list[str]:
    """Get branches not updated in specified days."""
    cutoff_date = datetime.now() - timedelta(days=days)

    success, output = run_git_command(
        repo_path,
        ['for-each-ref', '--sort=-committerdate', '--format=%(refname:short) %(committerdate:iso)', 'refs/heads/']
    )

    if not success:
        return []

    stale = []
    for line in output.split('\n'):
        if not line.strip():
            continue

        parts = line.split()
        if len(parts) >= 2:
            branch_name = parts[0]
            date_str = parts[1]

            try:
                last_commit = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if last_commit.replace(tzinfo=None) < cutoff_date:
                    stale.append(branch_name)
            except ValueError:
                pass

    return stale


def scan_repository(repo_path: Path) -> RepositoryStatus:
    """
    Scan a single repository for issues.

    Args:
        repo_path: Path to the repository

    Returns:
        RepositoryStatus with scan results
    """
    issues: list[RepositoryIssue] = []

    # Check uncommitted changes
    uncommitted = get_uncommitted_changes(repo_path)
    if uncommitted > 0:
        issues.append(RepositoryIssue(
            repo_path=str(repo_path),
            issue_type="uncommitted_changes",
            description=f"Has {uncommitted} uncommitted changes",
            severity="medium" if uncommitted < 10 else "high"
        ))

    # Check unpushed commits
    unpushed = get_unpushed_commits(repo_path)
    if unpushed > 0:
        issues.append(RepositoryIssue(
            repo_path=str(repo_path),
            issue_type="unpushed_commits",
            description=f"Has {unpushed} unpushed commits",
            severity="low" if unpushed < 5 else "medium"
        ))

    # Check stale branches
    stale = get_stale_branches(repo_path)
    if len(stale) > 3:
        issues.append(RepositoryIssue(
            repo_path=str(repo_path),
            issue_type="stale_branches",
            description=f"Has {len(stale)} stale branches (>30 days)",
            severity="low"
        ))

    return RepositoryStatus(
        path=str(repo_path),
        branch=get_current_branch(repo_path),
        is_clean=len(issues) == 0,
        uncommitted_changes=uncommitted,
        unpushed_commits=unpushed,
        stale_branches=stale,
        issues=issues
    )


def find_repositories(
    search_path: Path,
    max_depth: int = 3
) -> list[Path]:
    """
    Find Git repositories in a directory tree.

    Args:
        search_path: Path to search
        max_depth: Maximum search depth

    Returns:
        List of repository paths
    """
    repositories = []

    def search_dir(path: Path, depth: int):
        if depth > max_depth:
            return

        try:
            if is_git_repository(path):
                repositories.append(path)
                return  # Don't search inside repos

            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    search_dir(item, depth + 1)

        except PermissionError:
            pass

    search_dir(search_path, 0)
    return repositories


def scan_all_repositories(
    search_paths: Optional[list[Path]] = None
) -> list[RepositoryStatus]:
    """
    Scan all repositories in common locations.

    Args:
        search_paths: List of paths to search (default: common locations)

    Returns:
        List of RepositoryStatus objects
    """
    if search_paths is None:
        # Common locations to search
        home = Path.home()
        search_paths = [
            home / 'Projects',
            home / 'projects',
            home / 'code',
            home / 'Code',
            home / 'Developer',
            home / 'src',
            home / 'workspace',
            Path('/Users/ghost/Desktop'),  # Current user
        ]

    all_status = []

    for search_path in search_paths:
        if not search_path.exists():
            continue

        logger.info(f"Searching for repositories in: {search_path}")
        repos = find_repositories(search_path)

        for repo in repos:
            try:
                status = scan_repository(repo)
                all_status.append(status)
                logger.debug(f"Scanned: {repo}")
            except Exception as e:
                logger.error(f"Error scanning {repo}: {e}")

    logger.info(f"Scanned {len(all_status)} repositories")
    return all_status


def main():
    """CLI entry point for git scanner."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Git Scanner')
    parser.add_argument(
        '--scan', '-s',
        type=str,
        help='Scan a specific repository'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Scan all repositories in common locations'
    )
    parser.add_argument(
        '--issues-only',
        action='store_true',
        help='Only show repositories with issues'
    )

    args = parser.parse_args()

    if args.scan:
        repo_path = Path(args.scan)
        if not is_git_repository(repo_path):
            print(f"Not a git repository: {repo_path}")
            return

        status = scan_repository(repo_path)
        print(f"Repository: {status.path}")
        print(f"Branch: {status.branch}")
        print(f"Clean: {status.is_clean}")
        print(f"Uncommitted: {status.uncommitted_changes}")
        print(f"Unpushed: {status.unpushed_commits}")
        print(f"Stale branches: {len(status.stale_branches)}")

        if status.issues:
            print("\nIssues:")
            for issue in status.issues:
                print(f"  [{issue.severity.upper()}] {issue.issue_type}: {issue.description}")

    elif args.all:
        results = scan_all_repositories()
        print(f"Found {len(results)} repositories\n")

        for status in results:
            if args.issues_only and status.is_clean:
                continue

            print(f"{status.path}")
            print(f"  Branch: {status.branch}")
            print(f"  Issues: {len(status.issues)}")

            for issue in status.issues:
                print(f"    [{issue.severity}] {issue.description}")
            print()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
