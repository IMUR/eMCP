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

### Using eMCP

- [Getting Started](getting-started.md) — installation, configuration, custom ports
- [Adding Servers](adding-servers.md) — connect MCP servers via web UI or CLI
- [Groups](groups.md) — create tool sets for different workflows
- [Troubleshooting](troubleshooting.md) — something not working? start here

### Reference

- [API Reference](api-reference.md) — manager and gateway endpoints
- [Security](SECURITY.md) — secrets handling, deployment practices

### Contributing

- [Contributing](contributing.md) — development setup, code style
- [Changelog](changelog.md) — release history
