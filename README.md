# blackroad-backup-automator

Part of the BlackRoad Product Suite - 100+ tools for modern development.

## Overview

Backup Automator with integrated kanban project management, multi-service API support, and comprehensive state synchronization across Cloudflare, Salesforce, and Git.

## Features

- **Kanban Project Management** - Salesforce-style boards in GitHub
- **Multi-Service API Integration** - Cloudflare, Salesforce, Vercel, Digital Ocean, Claude, GitHub
- **SHA-256 & SHA Infinity Hashing** - Extensible cryptographic verification
- **Mobile Tool Support** - Working Copy, Pyto, iSH, Shellfish
- **Terminal Integration** - Termius SSH host sync
- **Raspberry Pi Cluster** - Edge compute backup distribution
- **PR Quality Gates** - Automated validation to prevent failed PRs
- **State Synchronization** - CRM/Cloudflare hold state, Git holds files

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/BlackRoad-OS/blackroad-backup-automator.git
cd blackroad-backup-automator

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Then run health checks
python scripts/health_check.py
```

### Configuration

1. Copy `.env.example` to `.env`
2. Fill in your API credentials
3. Review `config/endpoints.yaml` for service configuration
4. Review `kanban/projects.yaml` for board setup

## Project Structure

```
blackroad-backup-automator/
├── .github/
│   ├── workflows/           # CI/CD workflows
│   │   └── pr-validation.yml
│   └── ISSUE_TEMPLATE/      # Issue templates
├── agents/                  # Agent-specific scripts
├── config/
│   └── endpoints.yaml       # All API endpoint configs
├── integrations/
│   ├── apis/               # API client implementations
│   │   └── base.py         # Cloudflare, Salesforce, Vercel, DO, Claude, GitHub
│   ├── mobile/             # iOS tool integrations
│   │   └── mobile_tools.py # Working Copy, Pyto, iSH, Shellfish
│   └── terminal/           # Terminal integrations
│       └── termius_sync.py # Termius SSH host sync
├── kanban/
│   └── projects.yaml       # Kanban board configuration
├── lib/
│   └── hash.py             # SHA-256 & SHA Infinity hashing
├── scripts/
│   ├── health_check.py     # Endpoint health monitoring
│   ├── validate_pr.py      # PR quality gate validation
│   └── sync_state.py       # State synchronization
├── AGENTS.md               # AI agent instructions
├── LICENSE
└── README.md
```

## Supported Integrations

### Cloud Services
| Service | Type | Features |
|---------|------|----------|
| Cloudflare | CDN/DNS/KV | State storage, Workers, R2 |
| Vercel | Deployment | Edge functions, Analytics |
| Digital Ocean | Infrastructure | Droplets, K8s, Spaces |

### CRM & Business
| Service | Type | Features |
|---------|------|----------|
| Salesforce | CRM | Project sync, Custom objects |

### AI Services
| Service | Type | Features |
|---------|------|----------|
| Claude | AI Assistant | Code gen, PR review, Docs |

### Mobile Tools
| Tool | Platform | Features |
|------|----------|----------|
| Working Copy | iOS | Full Git client |
| Pyto | iOS | Python IDE |
| iSH | iOS | Alpine Linux shell |
| Shellfish | iOS | SFTP/SSH client |

### Terminal Tools
| Tool | Type | Features |
|------|------|----------|
| Termius | SSH Manager | Host sync, Team sharing |

### Hardware
| Device | Type | Features |
|--------|------|----------|
| Raspberry Pi | Edge Compute | Cluster backup, Local sync |

## Hash Verification

All configurations use SHA-256 hashing for integrity verification:

```python
from lib.hash import BlackRoadHasher, sha256

# Quick hash
hash_value = sha256("data to hash")

# File hashing
hasher = BlackRoadHasher()
file_hash = hasher.hash_file("config/endpoints.yaml")

# Manifest creation
manifest = hasher.create_manifest({
    'config': config_data,
    'state': state_data
})
```

### SHA Infinity - Extensible Hashing

```python
from lib.hash import SHAInfinity

# Available algorithms
algorithms = SHAInfinity.list_algorithms()
# ['sha256', 'sha384', 'sha512', 'sha3_256', 'sha3_512', 'blake2b', 'blake2s']

# Chain multiple algorithms
chained = SHAInfinity.hash_chain(data, ['sha256', 'blake2b'])
```

## Agent Instructions

AI agents working on this repository should read `AGENTS.md` for:
- Task workflow guidelines
- Service integration guide
- Hash verification requirements
- Quality gate checklist
- TODO list for agents

## PR Quality Gates

Every PR is validated against:

1. **Branch Naming** - Must use `claude/`, `feature/`, `fix/`, etc.
2. **Merge Conflicts** - No conflict markers
3. **Debug Code** - No obvious debug statements
4. **Config Hash** - Valid configuration hashes
5. **Required Files** - README.md, LICENSE, AGENTS.md
6. **YAML Syntax** - Valid YAML files
7. **Python Syntax** - Valid Python files
8. **Large Files** - No files > 10MB
9. **Secrets Check** - No .env files committed

Run locally:
```bash
python scripts/validate_pr.py
```

## State Synchronization

State flows between three systems:

```
Git (files) ←→ Cloudflare KV (state) ←→ Salesforce (CRM)
```

```bash
# Sync state to all backends
python scripts/sync_state.py

# View sync manifest
python scripts/sync_state.py --manifest
```

## Health Checks

Monitor all endpoints:

```bash
# Run all health checks
python scripts/health_check.py

# Export report
python scripts/health_check.py --output health-report.json
```

## Environment Variables

See `.env.example` for all required environment variables:

- `CLOUDFLARE_API_TOKEN` - Cloudflare API access
- `VERCEL_TOKEN` - Vercel deployment
- `DIGITALOCEAN_TOKEN` - Digital Ocean infrastructure
- `SF_*` - Salesforce OAuth2 credentials
- `ANTHROPIC_API_KEY` - Claude AI
- `GITHUB_TOKEN` - GitHub API
- `PI_*` - Raspberry Pi cluster

## About BlackRoad

BlackRoad OS is building the future of development tools and infrastructure.

- **Website**: https://blackroad.io
- **Email**: blackroad.systems@gmail.com
- **GitHub**: https://github.com/BlackRoad-OS

## License

See [LICENSE](LICENSE) for terms.
