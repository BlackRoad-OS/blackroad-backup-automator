#!/usr/bin/env python3
"""
BlackRoad Termius Integration
Sync SSH hosts and configurations with Termius
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TermiusHost:
    """Termius host configuration"""
    label: str
    address: str
    port: int = 22
    username: Optional[str] = None
    ssh_key: Optional[str] = None
    group: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TermiusGroup:
    """Termius group/folder configuration"""
    label: str
    parent: Optional[str] = None


class TermiusSync:
    """
    Sync BlackRoad infrastructure hosts to Termius

    Supports:
    - Raspberry Pi cluster
    - Cloud servers (DO, AWS, etc.)
    - Development machines
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TERMIUS_API_KEY")
        self.api_base = "https://api.termius.com"

    def create_blackroad_groups(self) -> List[TermiusGroup]:
        """Create BlackRoad group hierarchy"""
        return [
            TermiusGroup(label="BlackRoad"),
            TermiusGroup(label="Pi Cluster", parent="BlackRoad"),
            TermiusGroup(label="Cloud Servers", parent="BlackRoad"),
            TermiusGroup(label="Development", parent="BlackRoad"),
        ]

    def create_pi_cluster_hosts(
        self,
        hosts: List[Dict[str, Any]],
        username: str = "pi"
    ) -> List[TermiusHost]:
        """Create Termius hosts for Pi cluster"""
        return [
            TermiusHost(
                label=host.get('name', f"pi-{i}"),
                address=host['host'],
                port=host.get('port', 22),
                username=username,
                ssh_key=host.get('ssh_key'),
                group="Pi Cluster",
                tags=["blackroad", "raspberry-pi", "cluster"]
            )
            for i, host in enumerate(hosts)
        ]

    def create_cloud_hosts(
        self,
        provider: str,
        hosts: List[Dict[str, Any]]
    ) -> List[TermiusHost]:
        """Create Termius hosts for cloud servers"""
        return [
            TermiusHost(
                label=host.get('name', f"{provider}-{i}"),
                address=host['ip'],
                port=host.get('port', 22),
                username=host.get('username', 'root'),
                ssh_key=host.get('ssh_key'),
                group="Cloud Servers",
                tags=["blackroad", provider.lower()]
            )
            for i, host in enumerate(hosts)
        ]

    def generate_sync_manifest(
        self,
        groups: List[TermiusGroup],
        hosts: List[TermiusHost]
    ) -> Dict[str, Any]:
        """Generate a sync manifest for Termius"""
        return {
            "version": "1.0",
            "generated": datetime.utcnow().isoformat(),
            "source": "blackroad-backup-automator",
            "groups": [asdict(g) for g in groups],
            "hosts": [h.to_dict() for h in hosts],
            "metadata": {
                "total_groups": len(groups),
                "total_hosts": len(hosts)
            }
        }

    def export_to_json(self, filepath: str, manifest: Dict[str, Any]) -> None:
        """Export manifest to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(manifest, f, indent=2)


def create_default_infrastructure() -> Dict[str, Any]:
    """Create default BlackRoad infrastructure configuration"""
    sync = TermiusSync()

    # Create groups
    groups = sync.create_blackroad_groups()

    # Create Pi cluster hosts (using env vars for actual IPs)
    pi_hosts = [
        {"name": "pi-master", "host": os.getenv("PI_MASTER_HOST", "192.168.1.100")},
        {"name": "pi-worker-1", "host": os.getenv("PI_WORKER_1_HOST", "192.168.1.101")},
        {"name": "pi-worker-2", "host": os.getenv("PI_WORKER_2_HOST", "192.168.1.102")},
        {"name": "pi-worker-3", "host": os.getenv("PI_WORKER_3_HOST", "192.168.1.103")},
    ]
    pi_cluster = sync.create_pi_cluster_hosts(pi_hosts)

    # Create cloud hosts (placeholder)
    do_hosts = []
    if os.getenv("DO_SERVER_IP"):
        do_hosts = sync.create_cloud_hosts("digitalocean", [
            {"name": "do-primary", "ip": os.getenv("DO_SERVER_IP")}
        ])

    all_hosts = pi_cluster + do_hosts

    return sync.generate_sync_manifest(groups, all_hosts)


if __name__ == '__main__':
    print("BlackRoad Termius Sync")
    print("=" * 40)

    manifest = create_default_infrastructure()

    print(f"Groups: {manifest['metadata']['total_groups']}")
    print(f"Hosts: {manifest['metadata']['total_hosts']}")

    print("\nGroups:")
    for group in manifest['groups']:
        parent = f" (in {group['parent']})" if group.get('parent') else ""
        print(f"  - {group['label']}{parent}")

    print("\nHosts:")
    for host in manifest['hosts']:
        print(f"  - {host['label']}: {host['address']}:{host['port']}")

    # Export manifest
    output_file = "termius_sync_manifest.json"
    TermiusSync().export_to_json(output_file, manifest)
    print(f"\nManifest exported to: {output_file}")
