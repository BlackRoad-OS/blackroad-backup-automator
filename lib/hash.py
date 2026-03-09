#!/usr/bin/env python3
"""
BlackRoad Hash Library
SHA-256 and Extensible Hashing System ("SHA Infinity")

Provides cryptographic hashing for:
- Configuration integrity
- State verification
- Endpoint validation
- Card/Task identification
- PR validation
"""

import hashlib
import hmac
import json
import os
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path


class HashAlgorithm:
    """Base class for hash algorithms"""

    name: str = "base"
    digest_size: int = 0

    def hash(self, data: bytes) -> str:
        raise NotImplementedError

    def verify(self, data: bytes, expected: str) -> bool:
        return self.hash(data) == expected


class SHA256(HashAlgorithm):
    """SHA-256 implementation"""

    name = "sha256"
    digest_size = 32

    def hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def hash_file(self, filepath: Union[str, Path]) -> str:
        """Hash a file in chunks for memory efficiency"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()


class SHA384(HashAlgorithm):
    """SHA-384 implementation"""

    name = "sha384"
    digest_size = 48

    def hash(self, data: bytes) -> str:
        return hashlib.sha384(data).hexdigest()


class SHA512(HashAlgorithm):
    """SHA-512 implementation"""

    name = "sha512"
    digest_size = 64

    def hash(self, data: bytes) -> str:
        return hashlib.sha512(data).hexdigest()


class SHA3_256(HashAlgorithm):
    """SHA3-256 implementation"""

    name = "sha3_256"
    digest_size = 32

    def hash(self, data: bytes) -> str:
        return hashlib.sha3_256(data).hexdigest()


class SHA3_512(HashAlgorithm):
    """SHA3-512 implementation"""

    name = "sha3_512"
    digest_size = 64

    def hash(self, data: bytes) -> str:
        return hashlib.sha3_512(data).hexdigest()


class BLAKE2b(HashAlgorithm):
    """BLAKE2b implementation (fast, secure)"""

    name = "blake2b"
    digest_size = 64

    def hash(self, data: bytes) -> str:
        return hashlib.blake2b(data).hexdigest()


class BLAKE2s(HashAlgorithm):
    """BLAKE2s implementation (optimized for 32-bit)"""

    name = "blake2s"
    digest_size = 32

    def hash(self, data: bytes) -> str:
        return hashlib.blake2s(data).hexdigest()


# SHA Infinity - Extensible Hash Registry
class SHAInfinity:
    """
    SHA Infinity - Extensible Hashing System

    Supports dynamic algorithm selection and chaining
    for maximum flexibility and future-proofing.
    """

    # Registry of available algorithms
    _algorithms: Dict[str, HashAlgorithm] = {
        'sha256': SHA256(),
        'sha384': SHA384(),
        'sha512': SHA512(),
        'sha3_256': SHA3_256(),
        'sha3_512': SHA3_512(),
        'blake2b': BLAKE2b(),
        'blake2s': BLAKE2s(),
    }

    # Default algorithm
    _default = 'sha256'

    @classmethod
    def register(cls, algorithm: HashAlgorithm) -> None:
        """Register a new hash algorithm"""
        cls._algorithms[algorithm.name] = algorithm

    @classmethod
    def get(cls, name: str) -> HashAlgorithm:
        """Get a hash algorithm by name"""
        if name not in cls._algorithms:
            raise ValueError(f"Unknown algorithm: {name}")
        return cls._algorithms[name]

    @classmethod
    def list_algorithms(cls) -> List[str]:
        """List all available algorithms"""
        return list(cls._algorithms.keys())

    @classmethod
    def hash(cls, data: Union[str, bytes, dict, list],
             algorithm: str = None) -> str:
        """
        Hash data using specified or default algorithm

        Args:
            data: Data to hash (str, bytes, dict, or list)
            algorithm: Algorithm name (default: sha256)

        Returns:
            Hex-encoded hash string
        """
        algo = cls.get(algorithm or cls._default)

        if isinstance(data, str):
            data = data.encode('utf-8')
        elif isinstance(data, (dict, list)):
            data = json.dumps(data, sort_keys=True).encode('utf-8')

        return algo.hash(data)

    @classmethod
    def hash_chain(cls, data: Union[str, bytes],
                   algorithms: List[str]) -> str:
        """
        Chain multiple hash algorithms for extra security

        Example: hash_chain(data, ['sha256', 'sha3_256', 'blake2b'])
        """
        if isinstance(data, str):
            data = data.encode('utf-8')

        result = data
        for algo_name in algorithms:
            algo = cls.get(algo_name)
            result = algo.hash(result).encode('utf-8')

        return result.decode('utf-8')

    @classmethod
    def hmac_hash(cls, data: Union[str, bytes], key: bytes,
                  algorithm: str = None) -> str:
        """Create HMAC using specified algorithm"""
        if isinstance(data, str):
            data = data.encode('utf-8')

        algo_name = algorithm or cls._default
        if algo_name.startswith('sha3') or algo_name.startswith('blake'):
            # Use standard hashlib for these
            return cls.hash(key + data, algo_name)

        hash_func = getattr(hashlib, algo_name)
        return hmac.new(key, data, hash_func).hexdigest()


class BlackRoadHasher:
    """
    High-level hashing utilities for BlackRoad systems
    """

    def __init__(self, algorithm: str = 'sha256'):
        self.algorithm = algorithm
        self.hasher = SHAInfinity

    def hash_config(self, config: dict) -> str:
        """Hash a configuration dictionary"""
        # Normalize and sort for consistent hashing
        normalized = json.dumps(config, sort_keys=True, separators=(',', ':'))
        return self.hasher.hash(normalized, self.algorithm)

    def hash_file(self, filepath: Union[str, Path]) -> str:
        """Hash a file"""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        algo = self.hasher.get(self.algorithm)
        if hasattr(algo, 'hash_file'):
            return algo.hash_file(filepath)

        with open(filepath, 'rb') as f:
            return self.hasher.hash(f.read(), self.algorithm)

    def hash_directory(self, dirpath: Union[str, Path],
                       pattern: str = '*') -> Dict[str, str]:
        """Hash all files in a directory matching pattern"""
        dirpath = Path(dirpath)
        results = {}

        for filepath in sorted(dirpath.glob(pattern)):
            if filepath.is_file():
                rel_path = str(filepath.relative_to(dirpath))
                results[rel_path] = self.hash_file(filepath)

        return results

    def generate_card_id(self, card_data: dict) -> str:
        """Generate unique ID for a kanban card"""
        # Include timestamp for uniqueness
        data = {
            **card_data,
            '_created': datetime.utcnow().isoformat()
        }
        return self.hasher.hash(data, self.algorithm)[:16]

    def generate_state_hash(self, state: dict) -> str:
        """Generate hash for state synchronization"""
        return self.hasher.hash(state, self.algorithm)

    def verify_integrity(self, data: Any, expected_hash: str,
                        algorithm: str = None) -> bool:
        """Verify data integrity against expected hash"""
        algo = algorithm or self.algorithm
        actual_hash = self.hasher.hash(data, algo)
        return hmac.compare_digest(actual_hash, expected_hash)

    def create_manifest(self, items: Dict[str, Any]) -> dict:
        """Create a hash manifest for multiple items"""
        manifest = {
            'algorithm': self.algorithm,
            'created': datetime.utcnow().isoformat(),
            'items': {}
        }

        for key, value in items.items():
            manifest['items'][key] = self.hasher.hash(value, self.algorithm)

        # Add manifest hash
        manifest['manifest_hash'] = self.hasher.hash(
            manifest['items'], self.algorithm
        )

        return manifest

    def verify_manifest(self, manifest: dict, items: Dict[str, Any]) -> dict:
        """Verify items against a manifest"""
        results = {
            'valid': True,
            'algorithm': manifest.get('algorithm', self.algorithm),
            'checks': {}
        }

        for key, value in items.items():
            expected = manifest.get('items', {}).get(key)
            if expected is None:
                results['checks'][key] = {'status': 'missing', 'valid': False}
                results['valid'] = False
            else:
                actual = self.hasher.hash(value, results['algorithm'])
                valid = hmac.compare_digest(actual, expected)
                results['checks'][key] = {
                    'status': 'valid' if valid else 'invalid',
                    'valid': valid,
                    'expected': expected[:16] + '...',
                    'actual': actual[:16] + '...'
                }
                if not valid:
                    results['valid'] = False

        return results


# Convenience functions
def sha256(data: Union[str, bytes, dict]) -> str:
    """Quick SHA-256 hash"""
    return SHAInfinity.hash(data, 'sha256')


def sha512(data: Union[str, bytes, dict]) -> str:
    """Quick SHA-512 hash"""
    return SHAInfinity.hash(data, 'sha512')


def blake2b(data: Union[str, bytes, dict]) -> str:
    """Quick BLAKE2b hash"""
    return SHAInfinity.hash(data, 'blake2b')


def hash_file(filepath: Union[str, Path], algorithm: str = 'sha256') -> str:
    """Hash a file with specified algorithm"""
    hasher = BlackRoadHasher(algorithm)
    return hasher.hash_file(filepath)


def verify(data: Any, expected: str, algorithm: str = 'sha256') -> bool:
    """Verify data against expected hash"""
    hasher = BlackRoadHasher(algorithm)
    return hasher.verify_integrity(data, expected, algorithm)


# CLI interface
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("BlackRoad Hash Library")
        print("Usage:")
        print("  python hash.py <file>              - SHA-256 hash of file")
        print("  python hash.py -a <algo> <file>    - Hash with specified algorithm")
        print("  python hash.py --list              - List available algorithms")
        sys.exit(0)

    if sys.argv[1] == '--list':
        print("Available algorithms:")
        for algo in SHAInfinity.list_algorithms():
            print(f"  - {algo}")
        sys.exit(0)

    algorithm = 'sha256'
    filepath = sys.argv[1]

    if sys.argv[1] == '-a' and len(sys.argv) >= 4:
        algorithm = sys.argv[2]
        filepath = sys.argv[3]

    try:
        result = hash_file(filepath, algorithm)
        print(f"{result}  {filepath}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
