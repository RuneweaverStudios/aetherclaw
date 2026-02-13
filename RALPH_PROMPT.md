# Ralph Agent Instructions for Aether-Claw

You are an autonomous coding agent working on building Aether-Claw - a secure, swarm-based AI assistant system.

## API Configuration

You have access to a GLM-4 API. Configure via environment variable:
- **API Key**: Set `GLM_API_KEY` environment variable
- **Base URL**: `https://open.bigmodel.cn/api/paas/v4/`

## Your Task

1. Read the PRD at `prd.json` (in the same directory as this file)
2. Read the progress log at `progress.txt` (check Codebase Patterns section first)
3. Check you're on the correct branch from PRD `branchName`. If not, check it out or create from main.
4. Pick the **highest priority** user story where `passes: false`
5. Implement that single user story
6. Run quality checks (e.g., typecheck, lint, test - use whatever your project requires)
7. Update documentation files if you discover reusable patterns
8. If checks pass, commit ALL changes with message: `feat: [Story ID] - [Story Title]`
9. Update the PRD to set `passes: true` for the completed story
10. Append your progress to `progress.txt`

## Project Structure

```
/Users/ghost/Desktop/newclaw/
├── brain/                    # Memory system
│   ├── soul.md              # Identity and goals
│   ├── user.md              # User preferences
│   ├── memory.md            # Long-term memory log
│   ├── heartbeat.md         # Proactive task config
│   ├── audit_log.md         # Immutable audit trail
│   └── brain_index.db       # SQLite index (generated)
├── skills/                   # Signed skills registry
├── swarm_config.json         # Main configuration
├── brain_index.py            # Memory indexing utility
├── safe_skill_creator.py     # Skill signing utility
├── heartbeat_daemon.py       # Proactive task runner
├── dashboard.py              # Streamlit dashboard
└── prd.json                  # Ralph task list
```

## Progress Report Format

APPEND to progress.txt (never replace, always append):
```
## [Date/Time] - [Story ID]
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered (e.g., "this codebase uses X for Y")
  - Gotchas encountered (e.g., "don't forget to update Z when changing W")
  - Useful context (e.g., "the evaluation panel is in component X")
---
```

The learnings section is critical - it helps future iterations avoid repeating mistakes and understand the codebase better.

## Quality Requirements

- ALL commits must pass quality checks
- Do NOT commit broken code
- Keep changes focused and minimal
- Follow existing code patterns
- Use proper Python type hints and docstrings

## Key Security Requirements

For this Aether-Claw project:
1. All skill code must be cryptographically signed
2. Use the `cryptography` library for RSA signing
3. Store keys securely in `~/.claude/secure/`
4. Log all actions to `brain/audit_log.md`
5. Validate all inputs before processing

## Stop Condition

After completing a user story, check if ALL stories have `passes: true`.

If ALL stories are complete and passing, reply with:
<promise>COMPLETE</promise>

If there are still stories with `passes: false`, end your response normally (another iteration will pick up the next story).

## Important

- Work on ONE story per iteration
- Commit frequently
- Keep CI green
- Read the Codebase Patterns section in progress.txt before starting
