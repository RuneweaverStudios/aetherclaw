# Aether-Claw

A **secure, swarm-based AI assistant** with persistent memory, proactive automation, and cryptographically signed skills.

## Features

- **Persistent Memory**: Long-term recall via Markdown-based storage with SQLite indexing
- **Proactive Automation**: Scheduled heartbeat tasks that run autonomously
- **Multi-Tool Integration**: Shell commands, file management, and API interactions
- **Skill Extensibility**: Create new skills with cryptographic signing
- **Local-First Execution**: Runs on your hardware for privacy
- **Swarm Orchestration**: Multiple AI agents working in parallel
- **Security Hardened**: Permission boundaries, audit logging, and kill switch

## Architecture

```
+-------------------+     +------------------+     +-------------------+
|   Claude Code     |---->|   Architect      |---->|   GLM-4.7 API     |
|   (Leader)        |     |   (Reasoning)    |     |   (Tier 1)        |
+-------------------+     +------------------+     +-------------------+
                                  |
                                  v
                    +------------------------+
                    |   Swarm Orchestrator   |
                    +------------------------+
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
    +------------+      +------------+      +------------+
    |  Worker 1  |      |  Worker 2  |      |  Worker 3  |
    |  (Action)  |      |  (Action)  |      |  (Action)  |
    +------------+      +------------+      +------------+
          |                   |                   |
          v                   v                   v
    +---------------------------------------------------+
    |              Isolation Layer (Docker/Worktree)    |
    +---------------------------------------------------+
```

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd newclaw

# Install dependencies
pip install -r requirements.txt

# Generate RSA keys for skill signing
python aether_claw.py keygen

# Index brain files
python aether_claw.py index
```

## Quick Start

### 1. Check System Status

```bash
python aether_claw.py status
```

### 2. Run Heartbeat (Proactive Tasks)

```bash
# Run once
python aether_claw.py heartbeat --run-once

# Start daemon
python aether_claw.py heartbeat
```

### 3. Launch Dashboard

```bash
python aether_claw.py dashboard
```

### 4. Execute a Task with Swarm

```bash
python aether_claw.py swarm --task "Write a Python function to sort a list"
```

## Directory Structure

```
aether-claw/
├── brain/                    # Memory system
│   ├── soul.md              # Identity and goals
│   ├── user.md              # User preferences
│   ├── memory.md            # Long-term memory log
│   ├── heartbeat.md         # Proactive task config
│   ├── audit_log.md         # Immutable audit trail
│   └── brain_index.db       # SQLite index (generated)
├── skills/                   # Signed skills registry
├── swarm/                    # Swarm orchestration
│   ├── worker.py            # Base worker class
│   ├── architect.py         # Architect agent
│   ├── action_worker.py     # Action worker
│   └── orchestrator.py      # Swarm manager
├── tasks/                    # Heartbeat tasks
│   ├── git_scanner.py       # Git repository scanner
│   ├── memory_updater.py    # Memory index updater
│   ├── skill_checker.py     # Skill integrity checker
│   └── health_monitor.py    # System health monitor
├── aether_claw.py           # Main CLI
├── dashboard.py             # Streamlit dashboard
├── brain_index.py           # Memory indexer
├── safe_skill_creator.py    # Skill signing utility
├── keygen.py                # RSA key generator
├── kill_switch.py           # Kill switch module
├── safety_gate.py           # Permission checker
├── config_loader.py         # Configuration loader
├── audit_logger.py          # Audit logging
├── glm_client.py            # GLM API client
├── notifier.py              # System notifications
├── heartbeat_daemon.py      # Heartbeat daemon
├── swarm_config.json        # Main configuration
├── requirements.txt         # Dependencies
└── pyproject.toml           # Project config
```

## Security Model

### Skill Signing

All skills must be cryptographically signed before execution:

```bash
# Create and sign a skill
python aether_claw.py sign-skill --create my_skill.py --name my_skill

# Verify all skills
python aether_claw.py verify-skills
```

### Safety Gate

Sensitive actions require confirmation:

- File writes
- Network requests
- System commands
- Skill loading

### Kill Switch

Immediate halt on security events:

- Unsigned skill execution
- Signature verification failure
- Unauthorized file access
- Resource anomalies

```bash
# Arm the kill switch
python aether_claw.py kill-switch --arm

# Reset after trigger
python aether_claw.py kill-switch --reset
```

## Configuration

Edit `swarm_config.json` to customize:

- Model routing (GLM endpoints)
- Safety gate settings
- Kill switch triggers
- Heartbeat interval
- Swarm worker limits

## API Configuration

Set your GLM API key:

```bash
export GLM_API_KEY="your-api-key"
```

Or it will use the default configured key.

## Development

```bash
# Run tests
pytest

# Type checking
mypy .

# Format code
black .
```

## License

MIT License

## Acknowledgments

Inspired by OpenClaw and built with security as the primary concern.
