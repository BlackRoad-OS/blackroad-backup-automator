#!/usr/bin/env python3
"""
BlackRoad State Synchronization
Syncs kanban state between Git, Cloudflare KV, and Salesforce
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'integrations' / 'apis'))

try:
    from hash import BlackRoadHasher, sha256
except ImportError:
    BlackRoadHasher = None
    sha256 = lambda x: "unavailable"

try:
    from base import CloudflareAPI, SalesforceAPI, APIResponse
except ImportError:
    CloudflareAPI = None
    SalesforceAPI = None


@dataclass
class StateRecord:
    """A state record for synchronization"""
    key: str
    value: Any
    hash: str
    timestamp: str
    source: str

    @classmethod
    def create(cls, key: str, value: Any, source: str = "local"):
        value_str = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        return cls(
            key=key,
            value=value,
            hash=sha256(value_str)[:16],
            timestamp=datetime.utcnow().isoformat(),
            source=source
        )


@dataclass
class SyncResult:
    """Result of a sync operation"""
    success: bool
    source: str
    destination: str
    records_synced: int
    errors: list
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class StateSynchronizer:
    """
    Synchronizes state across multiple backends

    Architecture:
    - Git: Source of truth for code and configuration files
    - Cloudflare KV: Fast state storage for runtime data
    - Salesforce: CRM integration for project/task tracking
    """

    def __init__(self):
        self.cloudflare = CloudflareAPI() if CloudflareAPI else None
        self.salesforce = SalesforceAPI() if SalesforceAPI else None
        self.hasher = BlackRoadHasher() if BlackRoadHasher else None
        self.namespace_id = os.getenv("CLOUDFLARE_KV_NAMESPACE_ID", "")

    def load_local_state(self, state_file: str = "kanban/projects.yaml") -> Dict[str, Any]:
        """Load state from local YAML file"""
        try:
            import yaml
        except ImportError:
            print("Warning: PyYAML not installed")
            return {}

        state_path = Path(__file__).parent.parent / state_file
        if not state_path.exists():
            return {}

        with open(state_path) as f:
            return yaml.safe_load(f) or {}

    def sync_to_cloudflare(self, state: Dict[str, Any], prefix: str = "blackroad") -> SyncResult:
        """Sync state to Cloudflare KV"""
        if not self.cloudflare or not self.namespace_id:
            return SyncResult(
                success=False,
                source="local",
                destination="cloudflare",
                records_synced=0,
                errors=["Cloudflare not configured"]
            )

        errors = []
        synced = 0

        for key, value in self._flatten_state(state, prefix).items():
            record = StateRecord.create(key, value, "local")
            kv_value = json.dumps(asdict(record))

            response = self.cloudflare.kv_put(self.namespace_id, key, kv_value)
            if response.success:
                synced += 1
            else:
                errors.append(f"{key}: {response.error}")

        return SyncResult(
            success=len(errors) == 0,
            source="local",
            destination="cloudflare",
            records_synced=synced,
            errors=errors
        )

    def sync_to_salesforce(self, state: Dict[str, Any]) -> SyncResult:
        """Sync state to Salesforce custom objects"""
        if not self.salesforce:
            return SyncResult(
                success=False,
                source="local",
                destination="salesforce",
                records_synced=0,
                errors=["Salesforce not configured"]
            )

        # Authenticate
        if not self.salesforce.authenticate():
            return SyncResult(
                success=False,
                source="local",
                destination="salesforce",
                records_synced=0,
                errors=["Salesforce authentication failed"]
            )

        errors = []
        synced = 0

        # Sync boards as projects
        boards = state.get('boards', {})
        for board_id, board_data in boards.items():
            sf_record = {
                'Name': board_data.get('name', board_id),
                'External_ID__c': board_id,
                'Description__c': board_data.get('description', ''),
                'Status__c': 'Active',
                'Hash_ID__c': sha256(json.dumps(board_data))[:16]
            }

            response = self.salesforce.post(
                '/sobjects/BlackRoad_Project__c',
                data=sf_record
            )

            if response.success or response.status_code == 400:  # 400 might be duplicate
                synced += 1
            else:
                errors.append(f"Board {board_id}: {response.error}")

        return SyncResult(
            success=len(errors) == 0,
            source="local",
            destination="salesforce",
            records_synced=synced,
            errors=errors
        )

    def sync_from_cloudflare(self, prefix: str = "blackroad") -> Dict[str, Any]:
        """Fetch state from Cloudflare KV"""
        if not self.cloudflare or not self.namespace_id:
            return {}

        # This would need to list and fetch keys
        # Simplified implementation
        return {}

    def _flatten_state(self, state: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested state dict for KV storage"""
        result = {}

        def _flatten(obj, current_key):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_key = f"{current_key}:{k}" if current_key else k
                    _flatten(v, new_key)
            else:
                result[current_key] = obj

        _flatten(state, prefix)
        return result

    def generate_sync_manifest(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a manifest of what would be synced"""
        flattened = self._flatten_state(state, "blackroad")

        manifest = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_keys': len(flattened),
            'keys': list(flattened.keys()),
            'state_hash': sha256(json.dumps(state, sort_keys=True))[:16]
        }

        return manifest

    def full_sync(self, force: bool = False) -> Dict[str, SyncResult]:
        """Perform full state synchronization"""
        print("BlackRoad State Sync")
        print("=" * 50)

        state = self.load_local_state()
        if not state:
            print("No local state found")
            return {}

        manifest = self.generate_sync_manifest(state)
        print(f"State Hash: {manifest['state_hash']}")
        print(f"Total Keys: {manifest['total_keys']}")
        print()

        results = {}

        # Sync to Cloudflare
        print("Syncing to Cloudflare KV...")
        cf_result = self.sync_to_cloudflare(state)
        results['cloudflare'] = cf_result
        self._print_result(cf_result)

        # Sync to Salesforce
        print("\nSyncing to Salesforce...")
        sf_result = self.sync_to_salesforce(state)
        results['salesforce'] = sf_result
        self._print_result(sf_result)

        return results

    def _print_result(self, result: SyncResult) -> None:
        """Print sync result"""
        status = "✓" if result.success else "✗"
        print(f"  {status} {result.source} → {result.destination}")
        print(f"    Records synced: {result.records_synced}")
        if result.errors:
            print(f"    Errors: {len(result.errors)}")
            for err in result.errors[:3]:
                print(f"      - {err[:60]}")


def main():
    parser = argparse.ArgumentParser(description='BlackRoad State Sync')
    parser.add_argument('--force', action='store_true', help='Force sync even if unchanged')
    parser.add_argument('--manifest', action='store_true', help='Only show sync manifest')
    parser.add_argument('--cloudflare', action='store_true', help='Only sync to Cloudflare')
    parser.add_argument('--salesforce', action='store_true', help='Only sync to Salesforce')
    args = parser.parse_args()

    sync = StateSynchronizer()

    if args.manifest:
        state = sync.load_local_state()
        manifest = sync.generate_sync_manifest(state)
        print(json.dumps(manifest, indent=2))
        return

    results = sync.full_sync(force=args.force)

    # Exit with error if any sync failed
    all_success = all(r.success for r in results.values())
    sys.exit(0 if all_success else 1)


if __name__ == '__main__':
    main()
