# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

eMCP is a Tool Access Broker that filters which MCP (Model Context Protocol) tools AI agents can access. The core goal is **resource conservation**: every enabled tool consumes tokens and adds cognitive overhead.

## Commands

```bash
make up         # Start all services
make down       # Stop all services
make logs       # Tail gateway logs
make status     # Service health + tool count
make register   # Re-register all configs with MCPJungle
make help       # Show all targets
```

## Secret Management

Secrets are stored in `.env` (never committed). Copy `.env.example` and fill in values.

Required: `POSTGRES_USER`, `POSTGRES_PASSWORD`

Add MCP server secrets as needed (e.g., API keys for servers you add).

## Architecture

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| MCPJungle Gateway | `emcp-server` container (port 8090) | Aggregates MCP servers, routes tool calls, manages groups |
| eMCP Manager | `emcp-manager/app.py` (port 5010) | Flask web UI and API for tool selection |

### Group System

- Groups are JSON files in `groups/` directory
- Default group: `emcp-global`
- Each group specifies `included_tools` array
- MCPJungle exposes groups at `/v0/groups/{group}/mcp`

## Adding MCP Servers

### Via Web UI

1. Open http://localhost:5010
2. Click "Add MCP Server"
3. Enter a GitHub repo URL, npm package, or Docker image
4. Configure and provision

### Manually

1. Add service to `docker-compose.yaml`
2. Create config in `configs/<name>.json`
3. `docker compose up -d <name>`
4. `docker exec emcp-server /mcpjungle register -c /configs/<name>.json`

See `examples/README.md` for details.

### MCPJungle Registration

Config files in `configs/` are NOT auto-discovered. Servers must be registered:

```bash
docker exec emcp-server /mcpjungle register -c /configs/<name>.json
docker exec emcp-server /mcpjungle deregister <name>
make register   # Re-register all configs
```

### Systemd (for Add Server feature)

```bash
cd systemd && sudo ./install.sh
```

Watches `.reload-trigger` and runs `docker compose up -d` when the web UI provisions a server.

## Design Principles

- **Server prefix indicates platform** — tool names like `server__tool` encode the source
- **Minimal by default** — ship only core infra, users add what they need
