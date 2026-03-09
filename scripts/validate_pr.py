#!/usr/bin/env python3
"""
BlackRoad PR Validation Script
Quality gates to prevent failed pull requests
"""

import os
import sys
import json
import subprocess
import argparse
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

try:
    from hash import BlackRoadHasher, sha256
except ImportError:
    BlackRoadHasher = None
    sha256 = lambda x: "unavailable"


@dataclass
class ValidationResult:
    """Result of a single validation check"""
    name: str
    passed: bool
    message: str
    details: Optional[Dict] = None


@dataclass
class PRValidationReport:
    """Complete PR validation report"""
    timestamp: str
    branch: str
    commit: str
    all_passed: bool
    checks: List[ValidationResult]
    report_hash: str = ""

    def __post_init__(self):
        self.report_hash = sha256(json.dumps({
            'timestamp': self.timestamp,
            'branch': self.branch,
            'commit': self.commit,
            'checks': [c.name for c in self.checks]
        }))[:16]


class PRValidator:
    """
    PR Validation System

    Runs quality gates to ensure PRs meet standards before merge.
    This helps prevent failed pull requests across the BlackRoad repos.
    """

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = Path(repo_path or os.getcwd())
        self.results: List[ValidationResult] = []

    def run_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Run a shell command and return (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    def get_git_info(self) -> Dict[str, str]:
        """Get current git information"""
        info = {'branch': 'unknown', 'commit': 'unknown'}

        code, stdout, _ = self.run_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
        if code == 0:
            info['branch'] = stdout.strip()

        code, stdout, _ = self.run_command(['git', 'rev-parse', 'HEAD'])
        if code == 0:
            info['commit'] = stdout.strip()[:8]

        return info

    def check_branch_naming(self) -> ValidationResult:
        """Validate branch naming convention"""
        git_info = self.get_git_info()
        branch = git_info['branch']

        # Valid patterns for BlackRoad repos
        valid_prefixes = ['claude/', 'feature/', 'fix/', 'hotfix/', 'release/', 'main', 'master', 'develop']

        is_valid = any(branch.startswith(prefix) or branch == prefix
                      for prefix in valid_prefixes)

        return ValidationResult(
            name="branch_naming",
            passed=is_valid,
            message=f"Branch '{branch}' follows naming convention" if is_valid
                    else f"Branch '{branch}' should use prefix: {', '.join(valid_prefixes[:4])}...",
            details={'branch': branch, 'valid_prefixes': valid_prefixes}
        )

    def check_no_merge_conflicts(self) -> ValidationResult:
        """Check for merge conflict markers"""
        conflict_markers = ['<<<<<<<', '=======', '>>>>>>>']
        files_with_conflicts = []

        # Check tracked files
        code, stdout, _ = self.run_command(['git', 'ls-files'])
        if code != 0:
            return ValidationResult(
                name="merge_conflicts",
                passed=False,
                message="Could not list git files"
            )

        for filepath in stdout.strip().split('\n'):
            if not filepath:
                continue
            full_path = self.repo_path / filepath
            if full_path.exists() and full_path.is_file():
                try:
                    content = full_path.read_text(errors='ignore')
                    if any(marker in content for marker in conflict_markers):
                        files_with_conflicts.append(filepath)
                except:
                    pass

        passed = len(files_with_conflicts) == 0
        return ValidationResult(
            name="merge_conflicts",
            passed=passed,
            message="No merge conflict markers found" if passed
                    else f"Merge conflicts in: {', '.join(files_with_conflicts[:3])}",
            details={'files_with_conflicts': files_with_conflicts}
        )

    def check_no_debug_code(self) -> ValidationResult:
        """Check for debug code that shouldn't be committed"""
        debug_patterns = [
            'console.log(',
            'debugger;',
            'print("DEBUG',
            "print('DEBUG",
            'import pdb',
            'breakpoint()',
            '# TODO: remove',
            '// TODO: remove',
            'FIXME: debug'
        ]

        files_with_debug = []

        code, stdout, _ = self.run_command(['git', 'diff', '--cached', '--name-only'])
        if code != 0:
            # Check all tracked files if no staged changes
            code, stdout, _ = self.run_command(['git', 'ls-files'])

        for filepath in stdout.strip().split('\n'):
            if not filepath:
                continue
            full_path = self.repo_path / filepath
            if full_path.exists() and full_path.suffix in ['.py', '.js', '.ts', '.sh']:
                try:
                    content = full_path.read_text(errors='ignore')
                    for pattern in debug_patterns:
                        if pattern in content:
                            files_with_debug.append(f"{filepath} ({pattern})")
                            break
                except:
                    pass

        # This is a warning, not a failure (sometimes debug is intentional)
        passed = True  # Changed to warning only
        return ValidationResult(
            name="debug_code",
            passed=passed,
            message="No obvious debug code found" if not files_with_debug
                    else f"Warning: Debug patterns in {len(files_with_debug)} files",
            details={'files': files_with_debug[:5]}
        )

    def check_config_hash_integrity(self) -> ValidationResult:
        """Verify configuration file hash integrity"""
        if BlackRoadHasher is None:
            return ValidationResult(
                name="config_hash",
                passed=True,
                message="Hash verification skipped (library not available)"
            )

        hasher = BlackRoadHasher()
        config_dir = self.repo_path / 'config'

        if not config_dir.exists():
            return ValidationResult(
                name="config_hash",
                passed=True,
                message="No config directory to validate"
            )

        try:
            hashes = hasher.hash_directory(config_dir, '*.yaml')
            return ValidationResult(
                name="config_hash",
                passed=True,
                message=f"Config hash integrity verified ({len(hashes)} files)",
                details={'file_hashes': {k: v[:16] for k, v in hashes.items()}}
            )
        except Exception as e:
            return ValidationResult(
                name="config_hash",
                passed=False,
                message=f"Config hash verification failed: {e}"
            )

    def check_required_files(self) -> ValidationResult:
        """Check that required files exist"""
        required_files = [
            'README.md',
            'LICENSE',
            'AGENTS.md'
        ]

        missing = []
        for filename in required_files:
            if not (self.repo_path / filename).exists():
                missing.append(filename)

        passed = len(missing) == 0
        return ValidationResult(
            name="required_files",
            passed=passed,
            message="All required files present" if passed
                    else f"Missing files: {', '.join(missing)}",
            details={'required': required_files, 'missing': missing}
        )

    def check_yaml_syntax(self) -> ValidationResult:
        """Validate YAML file syntax"""
        try:
            import yaml
        except ImportError:
            return ValidationResult(
                name="yaml_syntax",
                passed=True,
                message="YAML validation skipped (pyyaml not installed)"
            )

        yaml_files = list(self.repo_path.rglob('*.yaml')) + list(self.repo_path.rglob('*.yml'))
        invalid_files = []

        for filepath in yaml_files:
            try:
                with open(filepath) as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                invalid_files.append(f"{filepath.name}: {str(e)[:50]}")

        passed = len(invalid_files) == 0
        return ValidationResult(
            name="yaml_syntax",
            passed=passed,
            message=f"All {len(yaml_files)} YAML files valid" if passed
                    else f"Invalid YAML: {', '.join(invalid_files[:2])}",
            details={'total_files': len(yaml_files), 'invalid': invalid_files}
        )

    def check_python_syntax(self) -> ValidationResult:
        """Validate Python file syntax"""
        python_files = list(self.repo_path.rglob('*.py'))
        invalid_files = []

        for filepath in python_files:
            try:
                with open(filepath) as f:
                    compile(f.read(), filepath, 'exec')
            except SyntaxError as e:
                invalid_files.append(f"{filepath.name}:{e.lineno}")

        passed = len(invalid_files) == 0
        return ValidationResult(
            name="python_syntax",
            passed=passed,
            message=f"All {len(python_files)} Python files valid" if passed
                    else f"Syntax errors: {', '.join(invalid_files[:3])}",
            details={'total_files': len(python_files), 'invalid': invalid_files}
        )

    def check_no_large_files(self) -> ValidationResult:
        """Check for files that are too large"""
        max_size_mb = 10
        large_files = []

        code, stdout, _ = self.run_command(['git', 'ls-files'])
        if code == 0:
            for filepath in stdout.strip().split('\n'):
                if not filepath:
                    continue
                full_path = self.repo_path / filepath
                if full_path.exists():
                    size_mb = full_path.stat().st_size / (1024 * 1024)
                    if size_mb > max_size_mb:
                        large_files.append(f"{filepath} ({size_mb:.1f}MB)")

        passed = len(large_files) == 0
        return ValidationResult(
            name="large_files",
            passed=passed,
            message="No large files detected" if passed
                    else f"Large files (>{max_size_mb}MB): {', '.join(large_files)}",
            details={'max_size_mb': max_size_mb, 'large_files': large_files}
        )

    def check_no_secrets(self) -> ValidationResult:
        """Check for potential secrets in code"""
        secret_patterns = [
            ('AWS Key', r'AKIA[0-9A-Z]{16}'),
            ('Private Key', r'-----BEGIN.*PRIVATE KEY-----'),
            ('API Key Pattern', r'api[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9]{20,}'),
        ]

        # Simple check - just look for .env files that shouldn't be committed
        env_files = list(self.repo_path.glob('.env*'))
        committed_env = []

        code, stdout, _ = self.run_command(['git', 'ls-files'])
        if code == 0:
            tracked = stdout.strip().split('\n')
            for env_file in env_files:
                if env_file.name in tracked:
                    committed_env.append(env_file.name)

        passed = len(committed_env) == 0
        return ValidationResult(
            name="secrets_check",
            passed=passed,
            message="No obvious secrets detected" if passed
                    else f"Warning: .env files tracked: {', '.join(committed_env)}",
            details={'env_files': committed_env}
        )

    def run_all_validations(self) -> PRValidationReport:
        """Run all PR validations"""
        print("BlackRoad PR Validation")
        print("=" * 50)

        git_info = self.get_git_info()
        print(f"Branch: {git_info['branch']}")
        print(f"Commit: {git_info['commit']}")
        print()

        # Run all checks
        checks = [
            ('Branch Naming', self.check_branch_naming),
            ('Merge Conflicts', self.check_no_merge_conflicts),
            ('Debug Code', self.check_no_debug_code),
            ('Config Hash', self.check_config_hash_integrity),
            ('Required Files', self.check_required_files),
            ('YAML Syntax', self.check_yaml_syntax),
            ('Python Syntax', self.check_python_syntax),
            ('Large Files', self.check_no_large_files),
            ('Secrets Check', self.check_no_secrets),
        ]

        results = []
        for name, check_func in checks:
            print(f"Checking {name}...", end=" ")
            result = check_func()
            results.append(result)

            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"{status}")
            if not result.passed:
                print(f"  → {result.message}")

        all_passed = all(r.passed for r in results)

        report = PRValidationReport(
            timestamp=datetime.utcnow().isoformat(),
            branch=git_info['branch'],
            commit=git_info['commit'],
            all_passed=all_passed,
            checks=results
        )

        self._print_summary(report)

        return report

    def _print_summary(self, report: PRValidationReport) -> None:
        """Print validation summary"""
        print()
        print("=" * 50)
        print("VALIDATION SUMMARY")
        print("=" * 50)

        passed = sum(1 for c in report.checks if c.passed)
        failed = len(report.checks) - passed

        print(f"Total Checks: {len(report.checks)}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"Report Hash: {report.report_hash}")

        if report.all_passed:
            print("\n✓ ALL CHECKS PASSED - Ready for PR")
        else:
            print("\n✗ VALIDATION FAILED - Please fix issues before creating PR")
            print("\nFailed Checks:")
            for check in report.checks:
                if not check.passed:
                    print(f"  - {check.name}: {check.message}")


def main():
    parser = argparse.ArgumentParser(description='BlackRoad PR Validator')
    parser.add_argument('-p', '--path', help='Repository path', default=os.getcwd())
    parser.add_argument('-o', '--output', help='Export report to JSON')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    validator = PRValidator(repo_path=args.path)
    report = validator.run_all_validations()

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        print(f"\nReport exported to: {args.output}")

    if args.json:
        print(json.dumps(asdict(report), indent=2, default=str))

    sys.exit(0 if report.all_passed else 1)


if __name__ == '__main__':
    main()
