# eMCP

**Tool Access Broker for MCP systems.**

Every enabled MCP tool consumes tokens and adds cognitive overhead. eMCP sits between your AI agent and your MCP servers, letting you control exactly which tools are exposed.

## Install

```bash
git clone https://github.com/IMUR/eMCP.git && cd eMCP
make up
```

Open **<http://localhost:5010>** to manage your tools.

Connect your AI agent to:

```
http://localhost:8090/v0/groups/emcp-global/mcp
```

## How It Works

```
AI Agent
    |
    v
eMCP Gateway         ← filters tools by group
    |       |
    v       v
  MCP     MCP        ← your MCP servers
 Server  Server
```

You add MCP servers. You choose which tools to expose. Your agent only sees what you've enabled.

## Documentation

### User Guide

- [Getting Started](getting-started.md) — installation, configuration, custom ports
- [Adding Servers](adding-servers.md) — connect MCP servers via web UI or CLI
- [Groups](groups.md) — create tool sets for different workflows
- [Troubleshooting](troubleshooting.md) — something not working? start here

### MCP

- [Connect Your Agent](connect.md) — Claude Code, Cursor, VS Code, Gemini, and more

### Skill

- [eMCP Skill](skill.md) — install the AI agent skill for automated operations

### Reference

- [API](api-reference.md) — manager and gateway endpoints
- [Security](SECURITY.md) — secrets handling, deployment practices
- [Changelog](changelog.md) — release history

### Development

- [Contributing](contributing.md) — development setup, code style
- [Validation](development/validation.md) — test procedures
- [Release](development/release.md) — release checklist
