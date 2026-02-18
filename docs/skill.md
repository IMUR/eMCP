# eMCP Skill

eMCP ships with a platform-agnostic AI agent skill in the `skill/` directory. The skill gives any AI agent the knowledge to install, operate, and troubleshoot eMCP without needing to read the full documentation.

## What's in the Skill

```
skill/
├── SKILL.md                 # Main instructions for the agent
├── scripts/
│   ├── check-ports.sh       # Pre-install: detect port conflicts
│   ├── wont-start.sh        # Fix: missing deps, .env, ports
│   ├── no-tools.sh          # Fix: tools disappeared
│   ├── cant-connect.sh      # Fix: agent can't reach eMCP
│   ├── fix-unhealthy.sh     # Fix: unhealthy containers
│   └── diagnose.sh          # Collect diagnostic info
└── references/
    └── operations.md        # Detailed operational reference
```

## How It Works

`SKILL.md` is the entry point. It contains architecture context, common operations, and a troubleshooting table that maps symptoms to auto-fix scripts. An agent reads it and knows how to manage eMCP.

The scripts are named by what the user sees ("no tools", "won't start", "can't connect"), not by what's technically wrong. Each script detects the root cause and applies the fix.

## Installing the Skill

The skill follows the cross-platform skill format. Copy or symlink the `skill/` directory to your agent's skill path:

### Claude Code

```bash
ln -sf /path/to/eMCP/skill ~/.claude/skills/emcp
```

### Gemini CLI

```bash
ln -sf /path/to/eMCP/skill ~/.gemini/skills/emcp
```

### Google Antigravity

```bash
ln -sf /path/to/eMCP/skill ~/.gemini/antigravity/skills/emcp
```

### Codex CLI

```bash
ln -sf /path/to/eMCP/skill ~/.agents/skills/emcp
```

### OpenCode

```bash
ln -sf /path/to/eMCP/skill ~/.config/opencode/skills/emcp
```

### Cursor

```bash
ln -sf /path/to/eMCP/skill ~/.cursor/skills/emcp
```

## Using the Skill

Once installed, invoke it by name or by describing what you need:

- "Set up eMCP on this machine"
- "My eMCP tools disappeared"
- "Check if eMCP ports are available"
- "Run eMCP diagnostics"

The agent reads `SKILL.md`, identifies the relevant operation or script, and executes it.

## Updating

If you cloned eMCP and used symlinks, the skill updates automatically when you `git pull`. If you copied the files, re-copy after updates.
