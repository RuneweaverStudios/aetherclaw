#!/usr/bin/env python3
"""
Aether-Claw Key Generator

Generates RSA key pairs for cryptographic signing of skills.
Keys are stored securely in ~/.claude/secure/
"""

import os
import stat
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default key storage paths
DEFAULT_KEY_DIR = Path.home() / '.claude' / 'secure'
PRIVATE_KEY_FILE = 'secure_key.pem'
PUBLIC_KEY_FILE = 'public_key.pem'


class KeyManager:
    """Manages RSA key generation, storage, and retrieval."""

    def __init__(self, key_dir: Optional[Path] = None):
        """
        Initialize the key manager.

        Args:
            key_dir: Directory to store keys (default: ~/.claude/secure)
        """
        self.key_dir = Path(key_dir) if key_dir else DEFAULT_KEY_DIR
        self.private_key_path = self.key_dir / PRIVATE_KEY_FILE
        self.public_key_path = self.key_dir / PUBLIC_KEY_FILE

    def _ensure_key_dir(self) -> None:
        """Create key directory with restrictive permissions."""
        self.key_dir.mkdir(parents=True, exist_ok=True)
        # Set directory permissions to 700 (owner only)
        self.key_dir.chmod(stat.S_IRWXU)
        logger.info(f"Key directory ready: {self.key_dir}")

    def generate_key_pair(
        self,
        key_size: int = 2048,
        passphrase: Optional[bytes] = None,
        overwrite: bool = False
    ) -> tuple[Path, Path]:
        """
        Generate a new RSA key pair.

        Args:
            key_size: Size of the RSA key in bits (default: 2048)
            passphrase: Optional passphrase to encrypt the private key
            overwrite: Whether to overwrite existing keys

        Returns:
            Tuple of (private_key_path, public_key_path)

        Raises:
            FileExistsError: If keys already exist and overwrite is False
        """
        # Check for existing keys
        if self.private_key_path.exists() and not overwrite:
            raise FileExistsError(
                f"Key file already exists: {self.private_key_path}. "
                "Use overwrite=True to replace."
            )

        self._ensure_key_dir()

        # Generate private key
        logger.info(f"Generating {key_size}-bit RSA key pair...")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )

        # Determine encryption for private key
        if passphrase:
            encryption = serialization.BestAvailableEncryption(passphrase)
        else:
            encryption = serialization.NoEncryption()

        # Serialize and save private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        )

        with open(self.private_key_path, 'wb') as f:
            f.write(private_pem)

        # Set restrictive permissions on private key (600)
        self.private_key_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        logger.info(f"Private key saved: {self.private_key_path}")

        # Extract and save public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        with open(self.public_key_path, 'wb') as f:
            f.write(public_pem)

        # Public key can be readable (644)
        self.public_key_path.chmod(
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        )
        logger.info(f"Public key saved: {self.public_key_path}")

        return self.private_key_path, self.public_key_path

    def load_private_key(self, passphrase: Optional[bytes] = None):
        """
        Load the private key from storage.

        Args:
            passphrase: Passphrase if the key is encrypted

        Returns:
            RSAPrivateKey object

        Raises:
            FileNotFoundError: If the private key doesn't exist
        """
        if not self.private_key_path.exists():
            raise FileNotFoundError(
                f"Private key not found: {self.private_key_path}"
            )

        with open(self.private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=passphrase,
                backend=default_backend()
            )

        logger.debug("Private key loaded successfully")
        return private_key

    def load_public_key(self):
        """
        Load the public key from storage.

        Returns:
            RSAPublicKey object

        Raises:
            FileNotFoundError: If the public key doesn't exist
        """
        if not self.public_key_path.exists():
            raise FileNotFoundError(
                f"Public key not found: {self.public_key_path}"
            )

        with open(self.public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

        logger.debug("Public key loaded successfully")
        return public_key

    def key_exists(self) -> bool:
        """Check if key pair exists."""
        return self.private_key_path.exists() and self.public_key_path.exists()

    def get_key_info(self) -> dict:
        """
        Get information about the stored keys.

        Returns:
            Dictionary with key information
        """
        info = {
            'key_dir': str(self.key_dir),
            'private_key_exists': self.private_key_path.exists(),
            'public_key_exists': self.public_key_path.exists(),
        }

        if self.private_key_path.exists():
            stat_info = self.private_key_path.stat()
            info['private_key_created'] = datetime.fromtimestamp(
                stat_info.st_ctime
            ).isoformat()
            info['private_key_modified'] = datetime.fromtimestamp(
                stat_info.st_mtime
            ).isoformat()
            info['private_key_size_bytes'] = stat_info.st_size

        return info

    def sign_data(self, data: bytes, passphrase: Optional[bytes] = None) -> bytes:
        """
        Sign data using the private key.

        Args:
            data: Data to sign
            passphrase: Passphrase for encrypted private key

        Returns:
            Signature bytes
        """
        private_key = self.load_private_key(passphrase)

        signature = private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        logger.debug(f"Signed {len(data)} bytes of data")
        return signature

    def verify_signature(
        self,
        data: bytes,
        signature: bytes,
        public_key=None
    ) -> bool:
        """
        Verify a signature using the public key.

        Args:
            data: Original data that was signed
            signature: Signature to verify
            public_key: Optional public key (loads from file if not provided)

        Returns:
            True if signature is valid, False otherwise
        """
        if public_key is None:
            public_key = self.load_public_key()

        try:
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            logger.debug("Signature verification successful")
            return True
        except Exception as e:
            logger.warning(f"Signature verification failed: {e}")
            return False


def main():
    """CLI entry point for key generator."""
    import argparse
    import getpass

    parser = argparse.ArgumentParser(description='Aether-Claw Key Generator')
    parser.add_argument(
        '--generate', '-g',
        action='store_true',
        help='Generate a new key pair'
    )
    parser.add_argument(
        '--overwrite', '-o',
        action='store_true',
        help='Overwrite existing keys'
    )
    parser.add_argument(
        '--passphrase', '-p',
        action='store_true',
        help='Prompt for passphrase to encrypt private key'
    )
    parser.add_argument(
        '--info', '-i',
        action='store_true',
        help='Show key information'
    )
    parser.add_argument(
        '--key-dir',
        type=str,
        help='Custom key directory'
    )

    args = parser.parse_args()

    key_dir = Path(args.key_dir) if args.key_dir else None
    manager = KeyManager(key_dir)

    if args.generate:
        passphrase = None
        if args.passphrase:
            passphrase = getpass.getpass('Enter passphrase: ').encode()

        try:
            private_path, public_path = manager.generate_key_pair(
                passphrase=passphrase,
                overwrite=args.overwrite
            )
            print(f"Key pair generated successfully!")
            print(f"  Private key: {private_path}")
            print(f"  Public key: {public_path}")
            print("\nWARNING: Keep your private key secure!")

        except FileExistsError as e:
            print(f"Error: {e}")
            print("Use --overwrite to replace existing keys")

    elif args.info:
        info = manager.get_key_info()
        print("Key Information:")
        print(f"  Key directory: {info['key_dir']}")
        print(f"  Private key exists: {info['private_key_exists']}")
        print(f"  Public key exists: {info['public_key_exists']}")

        if info['private_key_exists']:
            print(f"  Private key created: {info['private_key_created']}")
            print(f"  Private key size: {info['private_key_size_bytes']} bytes")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
