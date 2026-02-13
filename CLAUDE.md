# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

eMCP is a Tool Access Broker that filters which MCP (Model Context Protocol) tools AI agents can access. The core goal is **resource conservation**: every enabled tool consumes tokens and adds cognitive overhead.

## Commands

### Docker Compose (primary development)

```bash
docker compose up -d              # Start all services
docker compose logs -f emcp-server  # Watch gateway logs
docker compose restart emcp-server  # Restart after config changes
```

### eMCP Manager API

```bash
# Check current tool selection
curl http://localhost:5010/api/current

# List all available tools
curl http://localhost:5010/api/tools
```

## Secret Management

eMCP supports Infisical for automated secret injection, with `.env` file as fallback.

### Quick Start

```bash
# Copy and fill in secrets
cp .env.example .env

# Start services
docker compose up -d

# Or with Infisical integration:
./scripts/start-emcp.sh
```

### Required Secrets

Core infrastructure (always required):
- `POSTGRES_USER`, `POSTGRES_PASSWORD`

MCP server secrets (add as needed per server):
- See `.env.example` and `examples/` directory for available variables

## Architecture

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| MCPJungle Gateway | `emcp-server` container (port 8090) | Aggregates MCP servers, routes tool calls, manages groups |
| eMCP Manager | `emcp-manager/app.py` (port 5010) | Flask web UI and API for manual tool selection |

### Group System

- Groups are JSON files in `groups/` directory
- Default group: `emcp-global`
- Each group specifies `included_tools` array
- MCPJungle exposes groups at `/v0/groups/{group}/mcp`

## Configuration

### MCP Server Configs (`configs/`)

Each MCP server needs a JSON config specifying transport and command:

```json
{
  "name": "server-name",
  "transport": "stdio",
  "command": "docker",
  "args": ["exec", "-i", "container-name", "command", "args"]
}
```

## Adding MCP Servers

### Via Web UI

The eMCP Manager dashboard (http://localhost:5010) has an "Add MCP Server" button that allows:

1. Enter a GitHub repo URL, npm package, or Docker image
2. Auto-detects configuration (image, command, required env vars)
3. Enter environment variable values
4. Provisions container and config automatically

### Via API

```bash
# Detect server configuration from URL
curl -X POST http://localhost:5010/api/servers/detect \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/org/mcp-server"}'

# Provision a new server
curl -X POST http://localhost:5010/api/servers/provision \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-server",
    "image": "ghcr.io/org/server:latest",
    "command": ["node", "dist/index.js", "stdio"],
    "env_vars": {"API_KEY": "secret"},
    "description": "My MCP server"
  }'
```

### MCPJungle Server Registration

Config files in `/configs/` are NOT auto-discovered. Servers must be explicitly registered:

```bash
docker exec emcp-server /mcpjungle register -c /configs/server-name.json
docker exec emcp-server /mcpjungle deregister server-name
docker exec emcp-server /mcpjungle list servers
python3 scripts/re-register-tools.py
```

### Systemd Setup (Required for Add Server feature)

The web UI cannot run `docker compose` directly. A systemd path unit watches for changes:

```bash
cd systemd
sudo ./install.sh
```

This installs units that watch `.reload-trigger` and run `docker compose up -d` when triggered.

## Design Principles

- **Server prefix indicates platform** - Tool names like `github__`, `gitea__` encode platform
- **Write operations are platform-specific** - `github__write` only for GitHub projects
- **Research operations are portable** - Can be useful across platforms
