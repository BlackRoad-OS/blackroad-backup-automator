#!/usr/bin/env python3
"""
BlackRoad Mobile Tools Integration
Support for iOS development tools: iSH, Shellfish, Working Copy, Pyto
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import quote, urlencode


@dataclass
class MobileToolConfig:
    """Configuration for a mobile tool"""
    name: str
    url_scheme: str
    features: List[str]
    setup_required: bool = False


class WorkingCopyIntegration:
    """
    Working Copy - iOS Git Client Integration

    URL Scheme: working-copy://
    X-Callback-URL supported for automation
    """

    URL_SCHEME = "working-copy://"
    X_CALLBACK = "working-copy://x-callback-url"

    @staticmethod
    def clone_url(repo_url: str, path: Optional[str] = None) -> str:
        """Generate URL to clone a repository"""
        params = {'url': repo_url}
        if path:
            params['path'] = path
        return f"{WorkingCopyIntegration.X_CALLBACK}/clone?{urlencode(params)}"

    @staticmethod
    def pull_url(repo_name: str) -> str:
        """Generate URL to pull a repository"""
        return f"{WorkingCopyIntegration.X_CALLBACK}/pull?repo={quote(repo_name)}"

    @staticmethod
    def push_url(repo_name: str) -> str:
        """Generate URL to push a repository"""
        return f"{WorkingCopyIntegration.X_CALLBACK}/push?repo={quote(repo_name)}"

    @staticmethod
    def commit_url(repo_name: str, message: str, add_all: bool = True) -> str:
        """Generate URL to commit changes"""
        params = {
            'repo': repo_name,
            'message': message
        }
        if add_all:
            params['add'] = 'all'
        return f"{WorkingCopyIntegration.X_CALLBACK}/commit?{urlencode(params)}"

    @staticmethod
    def open_file_url(repo_name: str, path: str) -> str:
        """Generate URL to open a file"""
        return f"{WorkingCopyIntegration.X_CALLBACK}/open?repo={quote(repo_name)}&path={quote(path)}"

    @staticmethod
    def chain_actions(actions: List[Dict[str, Any]]) -> str:
        """
        Chain multiple Working Copy actions

        Actions format: [{'action': 'pull', 'repo': 'myrepo'}, ...]
        """
        urls = []
        for action in actions:
            action_type = action.get('action')
            if action_type == 'pull':
                urls.append(WorkingCopyIntegration.pull_url(action['repo']))
            elif action_type == 'push':
                urls.append(WorkingCopyIntegration.push_url(action['repo']))
            elif action_type == 'commit':
                urls.append(WorkingCopyIntegration.commit_url(
                    action['repo'],
                    action.get('message', 'Auto commit')
                ))
        return urls


class PytoIntegration:
    """
    Pyto - iOS Python IDE Integration

    Supports running Python scripts on iOS
    with Shortcuts integration
    """

    URL_SCHEME = "pyto://"

    SUPPORTED_PACKAGES = [
        'requests', 'numpy', 'pandas', 'PIL',
        'cryptography', 'beautifulsoup4', 'lxml',
        'matplotlib', 'scipy', 'scikit-learn'
    ]

    @staticmethod
    def run_script_url(script_path: str) -> str:
        """Generate URL to run a Python script"""
        return f"pyto://run?script={quote(script_path)}"

    @staticmethod
    def open_url(file_path: str) -> str:
        """Generate URL to open a file in Pyto"""
        return f"pyto://open?path={quote(file_path)}"

    @staticmethod
    def generate_backup_script() -> str:
        """Generate a backup automation script for Pyto"""
        return '''#!/usr/bin/env python3
"""
BlackRoad Backup Script for Pyto
Run this on iOS to sync configurations
"""

import os
import json
import requests
from datetime import datetime

# Configuration
CLOUDFLARE_API = "https://api.cloudflare.com/client/v4"
API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")

def backup_to_cloudflare(data: dict, key: str):
    """Backup data to Cloudflare KV"""
    # Implementation would go here
    print(f"Backing up {key}...")
    return True

def main():
    timestamp = datetime.now().isoformat()
    print(f"BlackRoad Backup - {timestamp}")

    # Your backup logic here
    backup_data = {
        "timestamp": timestamp,
        "device": "ios",
        "source": "pyto"
    }

    print("Backup complete!")

if __name__ == "__main__":
    main()
'''


class ISHIntegration:
    """
    iSH - iOS Alpine Linux Shell Integration

    Provides Alpine Linux environment on iOS
    for running shell scripts and tools
    """

    DEFAULT_PORT = 8022

    ESSENTIAL_PACKAGES = [
        'git', 'python3', 'py3-pip', 'openssh',
        'curl', 'jq', 'bash', 'vim', 'tmux'
    ]

    @staticmethod
    def generate_setup_script() -> str:
        """Generate iSH setup script"""
        packages = ' '.join(ISHIntegration.ESSENTIAL_PACKAGES)
        return f'''#!/bin/sh
# BlackRoad iSH Setup Script
# Run this in iSH to set up the environment

echo "BlackRoad iSH Setup"
echo "==================="

# Update package index
apk update

# Install essential packages
apk add {packages}

# Create BlackRoad directory
mkdir -p ~/blackroad
cd ~/blackroad

# Clone repositories (if git credentials are set)
if [ -n "$GITHUB_TOKEN" ]; then
    git clone https://$GITHUB_TOKEN@github.com/BlackRoad-OS/blackroad-backup-automator.git
fi

# Setup Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install requests pyyaml

echo "Setup complete!"
echo "Run 'source ~/blackroad/venv/bin/activate' to activate Python environment"
'''

    @staticmethod
    def generate_backup_script() -> str:
        """Generate backup shell script for iSH"""
        return '''#!/bin/sh
# BlackRoad Backup Script for iSH
# Syncs local data to cloud endpoints

TIMESTAMP=$(date -Iseconds)
BACKUP_DIR="$HOME/blackroad/backups"

mkdir -p "$BACKUP_DIR"

echo "BlackRoad Backup - $TIMESTAMP"

# Create backup archive
tar -czf "$BACKUP_DIR/backup-$TIMESTAMP.tar.gz" \
    -C "$HOME/blackroad" \
    --exclude="*.tar.gz" \
    --exclude="venv" \
    .

echo "Backup created: $BACKUP_DIR/backup-$TIMESTAMP.tar.gz"

# Sync to cloud (requires configured credentials)
if [ -n "$CLOUDFLARE_API_TOKEN" ]; then
    echo "Syncing to Cloudflare..."
    # Add Cloudflare sync logic
fi

echo "Backup complete!"
'''


class ShellfishIntegration:
    """
    Shellfish - iOS SFTP/SSH Client Integration

    For file transfers and SSH terminal access
    """

    @staticmethod
    def generate_connection_config(
        host: str,
        username: str,
        port: int = 22,
        key_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate Shellfish connection configuration"""
        config = {
            "name": f"BlackRoad - {host}",
            "host": host,
            "port": port,
            "username": username,
            "protocol": "sftp"
        }
        if key_name:
            config["privateKey"] = key_name
        return config

    @staticmethod
    def generate_pi_cluster_configs(
        hosts: List[Dict[str, str]],
        username: str = "pi"
    ) -> List[Dict[str, Any]]:
        """Generate configs for Pi cluster"""
        return [
            ShellfishIntegration.generate_connection_config(
                host=h['host'],
                username=username,
                port=h.get('port', 22),
                key_name=h.get('key_name')
            )
            for h in hosts
        ]


class MobileToolsManager:
    """
    Manager for all mobile tool integrations
    """

    def __init__(self):
        self.working_copy = WorkingCopyIntegration()
        self.pyto = PytoIntegration()
        self.ish = ISHIntegration()
        self.shellfish = ShellfishIntegration()

    def get_all_tools(self) -> List[MobileToolConfig]:
        """Get configuration for all mobile tools"""
        return [
            MobileToolConfig(
                name="Working Copy",
                url_scheme="working-copy://",
                features=["git", "github", "code_editing", "pr_management"],
                setup_required=False
            ),
            MobileToolConfig(
                name="Pyto",
                url_scheme="pyto://",
                features=["python", "pip", "shortcuts"],
                setup_required=True
            ),
            MobileToolConfig(
                name="iSH",
                url_scheme="ish://",
                features=["alpine_linux", "apk", "shell", "git"],
                setup_required=True
            ),
            MobileToolConfig(
                name="Shellfish",
                url_scheme="shellfish://",
                features=["sftp", "ssh", "file_transfer"],
                setup_required=False
            )
        ]

    def generate_all_setup_scripts(self) -> Dict[str, str]:
        """Generate setup scripts for all tools"""
        return {
            "ish_setup.sh": self.ish.generate_setup_script(),
            "ish_backup.sh": self.ish.generate_backup_script(),
            "pyto_backup.py": self.pyto.generate_backup_script()
        }

    def get_working_copy_workflow(self, repo_name: str) -> List[str]:
        """Get complete Working Copy workflow URLs"""
        return [
            self.working_copy.pull_url(repo_name),
            # User makes changes
            self.working_copy.commit_url(repo_name, "Update from iOS"),
            self.working_copy.push_url(repo_name)
        ]


if __name__ == '__main__':
    manager = MobileToolsManager()

    print("BlackRoad Mobile Tools Integration")
    print("=" * 40)

    for tool in manager.get_all_tools():
        status = "⚙️ Setup required" if tool.setup_required else "✓ Ready"
        print(f"\n{tool.name} ({tool.url_scheme})")
        print(f"  Status: {status}")
        print(f"  Features: {', '.join(tool.features)}")

    print("\n" + "=" * 40)
    print("Setup Scripts Generated:")
    for name, _script in manager.generate_all_setup_scripts().items():
        print(f"  - {name}")
