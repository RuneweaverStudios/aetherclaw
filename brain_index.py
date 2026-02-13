#!/usr/bin/env python3
"""
Aether-Claw Brain Indexer

Indexes Markdown files in the brain/ directory into SQLite for RAG-style retrieval.
Provides full-text search capabilities and version history tracking.
"""

import sqlite3
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Directory setup
BRAIN_DIR = Path(__file__).parent / 'brain'
DB_FILE = BRAIN_DIR / 'brain_index.db'


class BrainIndexer:
    """Manages SQLite indexing of brain Markdown files."""

    def __init__(self, brain_dir: Optional[Path] = None, db_file: Optional[Path] = None):
        """
        Initialize the brain indexer.

        Args:
            brain_dir: Directory containing Markdown files (default: ./brain)
            db_file: Path to SQLite database file (default: ./brain/brain_index.db)
        """
        self.brain_dir = Path(brain_dir) if brain_dir else BRAIN_DIR
        self.db_file = Path(db_file) if db_file else DB_FILE

        # Ensure brain directory exists
        self.brain_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self.db_file))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Create database tables and indexes if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create main index table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brain_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                version INTEGER NOT NULL DEFAULT 1
            )
        ''')

        # Create full-text search virtual table
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS brain_index_fts
            USING fts5(file_name, content, timestamp)
        ''')

        # Create index on file_name for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_name
            ON brain_index(file_name)
        ''')

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_file}")

    def _extract_text(self, content: str) -> str:
        """
        Extract plain text from Markdown content.
        Removes frontmatter and converts common Markdown elements to plain text.

        Args:
            content: Raw Markdown content

        Returns:
            Plain text suitable for indexing
        """
        lines = content.split('\n')
        text_lines = []
        in_frontmatter = False

        for line in lines:
            # Handle YAML frontmatter
            if line.strip() == '---':
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter:
                continue

            # Remove Markdown formatting
            # Headers
            if line.startswith('#'):
                line = line.lstrip('#').strip()

            # Bold/Italic
            line = line.replace('**', '').replace('__', '')
            line = line.replace('*', '').replace('_', '')

            # Links [text](url) -> text
            import re
            line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)

            # Code blocks
            if line.startswith('```'):
                continue

            # Inline code
            line = line.replace('`', '')

            # List items
            if line.strip().startswith(('- ', '* ', '1. ', '2. ')):
                line = line.strip().lstrip('-*').lstrip('0123456789.').strip()

            # Tables
            if line.strip().startswith('|'):
                line = line.strip('|').replace('|', ' ')

            text_lines.append(line)

        return '\n'.join(text_lines)

    def index_file(self, file_path: Path) -> int:
        """
        Index a single Markdown file.

        Args:
            file_path: Path to the Markdown file

        Returns:
            The version number of the indexed file

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract plain text for better search
        plain_text = self._extract_text(content)

        file_name = file_path.name
        timestamp = datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        # Get latest version
        cursor.execute(
            "SELECT MAX(version) FROM brain_index WHERE file_name = ?",
            (file_name,)
        )
        result = cursor.fetchone()
        max_version = result[0] if result[0] is not None else 0
        new_version = max_version + 1

        # Insert into main table
        cursor.execute(
            "INSERT INTO brain_index (file_name, content, timestamp, version) VALUES (?, ?, ?, ?)",
            (file_name, plain_text, timestamp, new_version)
        )

        # Insert into FTS table
        cursor.execute(
            "INSERT INTO brain_index_fts (file_name, content, timestamp) VALUES (?, ?, ?)",
            (file_name, plain_text, timestamp)
        )

        conn.commit()
        conn.close()

        logger.info(f"Indexed {file_name} (version {new_version})")
        return new_version

    def index_all(self) -> dict[str, int]:
        """
        Index all Markdown files in the brain directory.

        Returns:
            Dictionary mapping file names to their version numbers
        """
        results = {}

        if not self.brain_dir.exists():
            logger.warning(f"Brain directory does not exist: {self.brain_dir}")
            return results

        for file_path in self.brain_dir.glob('*.md'):
            try:
                version = self.index_file(file_path)
                results[file_path.name] = version
            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}")

        logger.info(f"Indexed {len(results)} files")
        return results

    def search_memory(self, query: str, limit: int = 5) -> list[dict]:
        """
        Search the brain index for matching content.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of dictionaries with file_name, content, and timestamp
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Use FTS5 for full-text search
        try:
            cursor.execute('''
                SELECT file_name, content, timestamp
                FROM brain_index_fts
                WHERE brain_index_fts MATCH ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (query, limit))
            results = [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # Fallback to LIKE search if FTS fails
            cursor.execute('''
                SELECT file_name, content, timestamp
                FROM brain_index
                WHERE content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (f"%{query}%", limit))
            results = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return results

    def get_file_history(self, file_name: str) -> list[dict]:
        """
        Get the version history of a specific file.

        Args:
            file_name: Name of the file to get history for

        Returns:
            List of dictionaries with version, content, and timestamp
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT version, content, timestamp
            FROM brain_index
            WHERE file_name = ?
            ORDER BY version DESC
        ''', (file_name,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_stats(self) -> dict:
        """
        Get statistics about the brain index.

        Returns:
            Dictionary with total_files, total_versions, and last_indexed
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(DISTINCT file_name) FROM brain_index')
        total_files = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM brain_index')
        total_versions = cursor.fetchone()[0]

        cursor.execute('SELECT MAX(timestamp) FROM brain_index')
        last_indexed = cursor.fetchone()[0]

        conn.close()

        return {
            'total_files': total_files,
            'total_versions': total_versions,
            'last_indexed': last_indexed
        }

    def clear_index(self) -> None:
        """Clear all indexed data (use with caution)."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM brain_index')
        cursor.execute('DELETE FROM brain_index_fts')

        conn.commit()
        conn.close()
        logger.warning("Brain index cleared")


def main():
    """CLI entry point for brain indexer."""
    import argparse

    parser = argparse.ArgumentParser(description='Aether-Claw Brain Indexer')
    parser.add_argument(
        '--index', '-i',
        action='store_true',
        help='Index all Markdown files in brain/'
    )
    parser.add_argument(
        '--search', '-s',
        type=str,
        help='Search the brain index'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show index statistics'
    )
    parser.add_argument(
        '--history',
        type=str,
        help='Show version history for a file'
    )

    args = parser.parse_args()
    indexer = BrainIndexer()

    if args.index:
        results = indexer.index_all()
        print(f"Indexed {len(results)} files:")
        for name, version in results.items():
            print(f"  {name}: version {version}")

    elif args.search:
        results = indexer.search_memory(args.search)
        print(f"Found {len(results)} results for '{args.search}':")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['file_name']} ({result['timestamp']})")
            # Show snippet
            content = result['content'][:200]
            print(f"   {content}...")

    elif args.stats:
        stats = indexer.get_stats()
        print("Brain Index Statistics:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Total versions: {stats['total_versions']}")
        print(f"  Last indexed: {stats['last_indexed']}")

    elif args.history:
        history = indexer.get_file_history(args.history)
        print(f"Version history for {args.history}:")
        for entry in history:
            print(f"  v{entry['version']} - {entry['timestamp']}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
