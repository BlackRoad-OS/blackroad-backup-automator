#!/usr/bin/env python3
"""
BlackRoad Endpoint Health Check System
Validates all configured endpoints and APIs
"""

import os
import sys
import json
import time
import socket
import argparse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'integrations' / 'apis'))

try:
    from hash import BlackRoadHasher, sha256
except ImportError:
    BlackRoadHasher = None
    sha256 = lambda x: "hash-unavailable"

try:
    from base import APIRegistry, HealthCheckResult
except ImportError:
    APIRegistry = None
    HealthCheckResult = None

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class EndpointCheck:
    """Result of an endpoint check"""
    name: str
    type: str
    endpoint: str
    healthy: bool
    status_code: Optional[int] = None
    latency_ms: float = 0
    error: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class HealthReport:
    """Complete health check report"""
    timestamp: str
    total_checks: int
    healthy_count: int
    unhealthy_count: int
    checks: List[EndpointCheck]
    config_hash: str
    report_hash: str = ""

    def __post_init__(self):
        if not self.report_hash:
            self.report_hash = sha256(json.dumps(asdict(self), default=str))[:16]


class HealthChecker:
    """
    Comprehensive health checker for all BlackRoad endpoints
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config()
        self.config = self._load_config()
        self.results: List[EndpointCheck] = []

    def _find_config(self) -> str:
        """Find endpoints.yaml configuration"""
        possible_paths = [
            Path(__file__).parent.parent / 'config' / 'endpoints.yaml',
            Path.cwd() / 'config' / 'endpoints.yaml',
            Path.home() / '.blackroad' / 'endpoints.yaml'
        ]
        for path in possible_paths:
            if path.exists():
                return str(path)
        return str(possible_paths[0])  # Default even if doesn't exist

    def _load_config(self) -> Dict[str, Any]:
        """Load endpoint configuration"""
        if not Path(self.config_path).exists():
            print(f"Warning: Config not found at {self.config_path}")
            return {}

        if yaml is None:
            print("Warning: PyYAML not installed, using empty config")
            return {}

        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}

    def check_tcp_port(self, host: str, port: int, timeout: int = 5) -> bool:
        """Check if a TCP port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def check_http_endpoint(self, url: str, timeout: int = 10) -> EndpointCheck:
        """Check an HTTP endpoint"""
        try:
            import requests
        except ImportError:
            return EndpointCheck(
                name="http",
                type="http",
                endpoint=url,
                healthy=False,
                error="requests library not installed"
            )

        start = time.time()
        try:
            response = requests.get(url, timeout=timeout)
            latency = (time.time() - start) * 1000
            return EndpointCheck(
                name=url,
                type="http",
                endpoint=url,
                healthy=response.ok,
                status_code=response.status_code,
                latency_ms=latency
            )
        except Exception as e:
            return EndpointCheck(
                name=url,
                type="http",
                endpoint=url,
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )

    def check_ssh_host(self, host: str, port: int = 22) -> EndpointCheck:
        """Check SSH connectivity"""
        start = time.time()
        is_open = self.check_tcp_port(host, port)
        latency = (time.time() - start) * 1000

        return EndpointCheck(
            name=f"ssh://{host}:{port}",
            type="ssh",
            endpoint=f"{host}:{port}",
            healthy=is_open,
            latency_ms=latency,
            error=None if is_open else "Port closed or unreachable"
        )

    def check_api_endpoints(self) -> List[EndpointCheck]:
        """Check all API endpoints using the API registry"""
        results = []

        if APIRegistry is None:
            return [EndpointCheck(
                name="api_registry",
                type="internal",
                endpoint="internal",
                healthy=False,
                error="API registry not available"
            )]

        api_results = APIRegistry.health_check_all()
        for name, result in api_results.items():
            results.append(EndpointCheck(
                name=name,
                type="api",
                endpoint=result.endpoint,
                healthy=result.healthy,
                status_code=result.status_code,
                latency_ms=result.latency_ms,
                error=result.error
            ))

        return results

    def check_pi_cluster(self) -> List[EndpointCheck]:
        """Check Raspberry Pi cluster connectivity"""
        results = []

        hardware = self.config.get('hardware', {})
        pi_config = hardware.get('raspberry_pi', {})
        cluster = pi_config.get('endpoints', {}).get('cluster', [])

        for pi in cluster:
            host = pi.get('host', '').replace('${', '').split(':-')[-1].rstrip('}')
            port = pi.get('port', 22)
            name = pi.get('name', host)

            result = self.check_ssh_host(host, port)
            result.name = f"pi:{name}"
            results.append(result)

        return results

    def check_cloud_services(self) -> List[EndpointCheck]:
        """Check cloud service endpoints"""
        results = []

        cloud = self.config.get('cloud', {})

        for service_name, service_config in cloud.items():
            health_check = service_config.get('health_check', {})
            base_url = service_config.get('endpoints', {}).get('api', '')

            if base_url and health_check.get('endpoint'):
                full_url = f"{base_url.rstrip('/')}{health_check['endpoint']}"
                result = self.check_http_endpoint(full_url)
                result.name = service_name
                result.type = "cloud"
                results.append(result)

        return results

    def run_all_checks(self) -> HealthReport:
        """Run all health checks and generate report"""
        print("Running BlackRoad Health Checks...")
        print("=" * 50)

        all_results = []

        # API endpoints
        print("\nChecking API endpoints...")
        api_results = self.check_api_endpoints()
        all_results.extend(api_results)
        for r in api_results:
            self._print_result(r)

        # Pi cluster
        print("\nChecking Pi cluster...")
        pi_results = self.check_pi_cluster()
        all_results.extend(pi_results)
        for r in pi_results:
            self._print_result(r)

        # Calculate config hash
        config_hash = "no-config"
        if BlackRoadHasher and Path(self.config_path).exists():
            hasher = BlackRoadHasher()
            config_hash = hasher.hash_file(self.config_path)[:16]

        healthy_count = sum(1 for r in all_results if r.healthy)

        report = HealthReport(
            timestamp=datetime.utcnow().isoformat(),
            total_checks=len(all_results),
            healthy_count=healthy_count,
            unhealthy_count=len(all_results) - healthy_count,
            checks=all_results,
            config_hash=config_hash
        )

        self._print_summary(report)

        return report

    def _print_result(self, result: EndpointCheck) -> None:
        """Print a single check result"""
        status = "✓" if result.healthy else "✗"
        latency = f"{result.latency_ms:.0f}ms" if result.latency_ms else "N/A"

        print(f"  {status} {result.name}: ", end="")
        if result.healthy:
            print(f"healthy ({latency})")
        else:
            error = result.error[:40] if result.error else "unknown error"
            print(f"unhealthy - {error}")

    def _print_summary(self, report: HealthReport) -> None:
        """Print health check summary"""
        print("\n" + "=" * 50)
        print("HEALTH CHECK SUMMARY")
        print("=" * 50)
        print(f"Timestamp: {report.timestamp}")
        print(f"Config Hash: {report.config_hash}")
        print(f"Report Hash: {report.report_hash}")
        print(f"\nTotal Checks: {report.total_checks}")
        print(f"  Healthy: {report.healthy_count}")
        print(f"  Unhealthy: {report.unhealthy_count}")

        if report.unhealthy_count > 0:
            print("\nUnhealthy Endpoints:")
            for check in report.checks:
                if not check.healthy:
                    print(f"  - {check.name}: {check.error}")

        overall = "HEALTHY" if report.unhealthy_count == 0 else "DEGRADED"
        print(f"\nOverall Status: {overall}")

    def export_report(self, report: HealthReport, filepath: str) -> None:
        """Export report to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        print(f"\nReport exported to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description='BlackRoad Endpoint Health Check')
    parser.add_argument('-c', '--config', help='Path to endpoints.yaml')
    parser.add_argument('-o', '--output', help='Export report to JSON file')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    checker = HealthChecker(config_path=args.config)
    report = checker.run_all_checks()

    if args.output:
        checker.export_report(report, args.output)

    if args.json:
        print(json.dumps(asdict(report), indent=2, default=str))

    # Exit with error code if any unhealthy
    sys.exit(0 if report.unhealthy_count == 0 else 1)


if __name__ == '__main__':
    main()
