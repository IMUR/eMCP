# eMCP

**Tool Access Broker for MCP systems.**

Filters which tools AI agents can access to reduce token costs and cognitive overhead.

Every enabled MCP tool consumes tokens. eMCP sits between your AI agent and your MCP servers, letting you control exactly which tools are exposed through a web UI.

## Architecture

```
AI Agent
    |
    v
eMCP Gateway (MCPJungle)     <-- Aggregates servers, filters by group
    |         |
    v         v
  MCP       MCP              <-- Your MCP servers
 Server    Server
```

| Service | Port | Purpose |
|---------|------|---------|
| `emcp-server` | 8090 | MCPJungle gateway — aggregates servers, routes tool calls |
| `emcp-manager` | 5010 | Web UI for tool selection and server management |
| `emcp-db` | 5432 | PostgreSQL for gateway state |

## Quick Start

See [Getting Started](getting-started.md) for full setup instructions.

```bash
git clone https://github.com/IMUR/eMCP.git && cd eMCP
cp .env.example .env    # Edit with your Postgres credentials
make up                 # Start all services
make register           # Register the demo server
```

Open **<http://localhost:5010>** to manage your tools.

## Key Features

- **Tool filtering** — expose only the tools your agent needs
- **Group system** — create named tool sets for different workflows
- **Web UI** — toggle tools on/off, add servers, manage groups
- **MCP Streamable HTTP** — standard MCP transport for any client
- **Zero-config demo** — ships with a filesystem server, ready to use
- **Dynamic provisioning** — add MCP servers through the web UI
