# BlackRoad Agent Instructions

## Overview

This document provides instructions and guidelines for AI agents (Claude, etc.) working on BlackRoad repositories. Following these guidelines ensures consistency across the 100+ repos in the BlackRoad ecosystem.

## Agent Identification

When working on this repository, agents should:

1. **Identify the branch pattern**: `claude/{task-description}-{session-id}`
2. **Check kanban status**: Review `kanban/projects.yaml` for current tasks
3. **Verify hash integrity**: Use `lib/hash.py` before making changes
4. **Update state**: Sync changes to configured endpoints

## Pre-Work Checklist

Before starting any task:

- [ ] Read this AGENTS.md file
- [ ] Check `config/endpoints.yaml` for service configurations
- [ ] Verify you're on the correct branch
- [ ] Review existing TODOs in the codebase
- [ ] Check PR history for context on failed PRs

## Task Workflow

### 1. Task Assignment

```
Kanban Board → Agent Tasks → Queued → Assigned (to you)
```

When assigned a task:
1. Move card to "Executing" column
2. Generate task hash for tracking
3. Begin work following these guidelines

### 2. Code Changes

#### DO:
- Write clean, well-documented code
- Follow existing patterns in the codebase
- Run tests before committing
- Update relevant documentation
- Verify endpoint connectivity if making API changes

#### DON'T:
- Make changes outside the scope of the task
- Skip hash verification steps
- Push without running validation
- Ignore failing tests
- Bypass PR quality gates

### 3. Commit Guidelines

```bash
# Format
<type>(<scope>): <description>

# Types
feat:     New feature
fix:      Bug fix
docs:     Documentation
style:    Formatting (no code change)
refactor: Code restructuring
test:     Adding tests
chore:    Maintenance

# Example
feat(kanban): add salesforce sync for project boards
```

### 4. PR Creation

Every PR MUST include:
- [ ] Clear title describing the change
- [ ] Description of what was changed and why
- [ ] Reference to kanban card/issue
- [ ] Hash verification results
- [ ] Endpoint health check results (if applicable)

## Service Integration Guide

### Cloudflare (State Storage)
```python
# KV operations for state
namespace = "blackroad-kanban"
key_pattern = "board:{board_id}:state"
```

### Salesforce (CRM Sync)
```python
# Custom objects to update
- BlackRoad_Project__c
- BlackRoad_Task__c
- BlackRoad_Integration__c
```

### GitHub Projects
```yaml
# Sync kanban state to GitHub Projects
- Use GraphQL API for project operations
- Mirror board columns to project columns
- Keep issues linked to cards
```

### Raspberry Pi Cluster
```bash
# SSH into Pi cluster for backup operations
ssh -i $PI_SSH_KEY user@$PI_MASTER_HOST
```

### Mobile Tools
- **Working Copy**: Use URL schemes for git operations
- **Pyto**: Python scripts run locally on iOS
- **iSH**: Alpine Linux for shell operations
- **Shellfish**: SFTP file transfers

## Hash Verification

All significant operations require hash verification:

```python
from lib.hash import BlackRoadHasher, sha256

hasher = BlackRoadHasher()

# Before making changes
original_hash = hasher.hash_config(config)

# After making changes
new_hash = hasher.hash_config(updated_config)

# Include in commit
# Hash: {original_hash} → {new_hash}
```

## Quality Gates

### PR Quality Gate Checklist

1. **Hash Integrity** ✓
   - Config files have valid hashes
   - State changes are tracked

2. **Endpoint Health** ✓
   - All configured endpoints are reachable
   - API credentials are valid

3. **Tests Pass** ✓
   - Unit tests pass
   - Integration tests pass

4. **Documentation** ✓
   - AGENTS.md is current
   - Config changes documented

5. **Kanban Updated** ✓
   - Card moved to appropriate column
   - State synced to Cloudflare/Salesforce

## Common Issues & Solutions

### Failed PR: "Hash mismatch"
```bash
# Regenerate hash manifest
python lib/hash.py --manifest config/
```

### Failed PR: "Endpoint unreachable"
```bash
# Check endpoint health
python scripts/health_check.py
```

### Failed PR: "State sync failed"
```bash
# Manual sync
python scripts/sync_state.py --force
```

## Agent TODO List

Current tasks for agents working on this repo:

### High Priority
- [ ] Implement backup scheduler in main script
- [ ] Add endpoint health monitoring
- [ ] Create Salesforce custom object sync
- [ ] Set up GitHub Actions for CI/CD

### Medium Priority
- [ ] Add Cloudflare KV state management
- [ ] Implement Pi cluster communication
- [ ] Create mobile app integration hooks
- [ ] Add comprehensive logging

### Low Priority
- [ ] Documentation improvements
- [ ] Code cleanup and refactoring
- [ ] Performance optimization
- [ ] Additional hash algorithms

## Repository Standards

### File Organization
```
blackroad-backup-automator/
├── .github/
│   ├── workflows/        # CI/CD
│   └── ISSUE_TEMPLATE/   # Issue templates
├── agents/               # Agent-specific scripts
├── config/               # Configuration files
├── integrations/         # Service integrations
│   ├── apis/
│   ├── cloud/
│   ├── mobile/
│   └── terminal/
├── kanban/               # Kanban configuration
├── lib/                  # Core libraries
├── scripts/              # Utility scripts
├── AGENTS.md             # This file
├── LICENSE
└── README.md
```

### Naming Conventions
- Files: `snake_case.py`, `kebab-case.yaml`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Branches: `claude/{task}-{session}`

## Contact & Support

- **Email**: blackroad.systems@gmail.com
- **Website**: https://blackroad.io
- **Issues**: Use GitHub Issues with appropriate labels

---

*This document is part of the BlackRoad Product Suite. See LICENSE for terms.*
