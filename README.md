# Aether-Claw

A **secure, swarm-based AI assistant** with persistent memory, proactive automation, and cryptographically signed skills.

## Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/your-repo/aether-claw/main/install.sh | bash
```

Or manually:

```bash
git clone https://github.com/your-repo/aether-claw.git ~/.aether-claw
cd ~/.aether-claw
pip install -r requirements.txt
```

## Onboarding

After installation, run the interactive setup:

```bash
aetherclaw onboard
```

This will:
1. Check/configure API keys
2. Generate RSA keys for skill signing
3. Index brain memory files
4. Verify skill signatures
5. Run system health check

## API Keys

Set your OpenRouter API key (recommended):

```bash
export OPENROUTER_API_KEY="your-key"
```

Or add to `~/.aether-claw/.env`:

```
OPENROUTER_API_KEY=your-key
```

## Usage

```bash
aetherclaw status              # View system status
aetherclaw onboard             # Interactive setup
aetherclaw heartbeat           # Start scheduled tasks
aetherclaw heartbeat --run-once  # Run tasks once
aetherclaw dashboard           # Launch web UI
aetherclaw swarm -t "task"     # Execute swarm task
aetherclaw sign-skill --create file.py  # Create signed skill
aetherclaw verify-skills       # Verify all skill signatures
```

## Features

- **Persistent Memory**: Long-term recall via Markdown-based storage with SQLite indexing
- **Proactive Automation**: Scheduled heartbeat tasks that run autonomously
- **Multi-Tool Integration**: Shell commands, file management, and API interactions
- **Skill Extensibility**: Create new skills with cryptographic RSA signing
- **Local-First Execution**: Runs on your hardware for privacy
- **Swarm Orchestration**: Multiple AI agents working in parallel
- **Security Hardened**: Permission boundaries, audit logging, and kill switch

## Architecture

```
+-------------------+     +------------------+     +-------------------+
|   Claude Code     |---->|   Architect      |---->|   OpenRouter API  |
|   (Leader)        |     |   (Reasoning)    |     |   claude-3.5      |
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

## Directory Structure

```
~/.aether-claw/
├── brain/                    # Memory system
│   ├── soul.md              # Identity and goals
│   ├── user.md              # User preferences
│   ├── memory.md            # Long-term memory log
│   ├── heartbeat.md         # Proactive task config
│   ├── audit_log.md         # Immutable audit trail
│   └── brain_index.db       # SQLite index (generated)
├── skills/                   # Signed skills registry
├── swarm/                    # Swarm orchestration
├── tasks/                    # Heartbeat tasks
├── .env                      # API keys (gitignored)
├── aether_claw.py           # Main CLI
└── swarm_config.json        # Configuration
```

## Security Model

### Skill Signing

All skills must be cryptographically signed with RSA-2048:

```bash
# Create and sign a skill
aetherclaw sign-skill --create my_skill.py --name my_skill

# List skills
aetherclaw sign-skill --list

# Verify all skills
aetherclaw verify-skills
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
aetherclaw kill-switch --arm     # Arm kill switch
aetherclaw kill-switch --reset   # Reset after trigger
```

## Configuration

Edit `swarm_config.json` to customize:
- Model routing
- Safety gate settings
- Kill switch triggers
- Heartbeat interval
- Swarm worker limits

## Heartbeat Tasks

Automated tasks that run on a schedule:

| Task | Description |
|------|-------------|
| `git_repo_scan` | Scan for git repositories |
| `memory_index_update` | Update brain index |
| `skill_integrity_check` | Verify skill signatures |
| `system_health_check` | Monitor CPU/memory |
| `task_list_review` | Review task lists |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy .
```

## License

MIT License

## Acknowledgments

Inspired by OpenClaw with security as the primary design concern.
