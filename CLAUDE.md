# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

eMCP is a Tool Access Broker that filters which MCP (Model Context Protocol) tools AI agents can access. The core goal is **resource conservation**: every enabled tool consumes tokens and adds cognitive overhead.

## Commands

```bash
make up         # Start all services (auto-registers configs)
make dev        # Start with locally built images (for development)
make down       # Stop all services
make logs       # Tail gateway logs
make status     # Service health + tool count
make register   # Re-register all configs with MCPJungle (requires jq)
make help       # Show all targets
```

## Secret Management

Secrets are stored in `.env` (never committed). `make up` auto-creates from `.env.example` if missing.

Add MCP server API keys here. Postgres credentials are hardcoded internally (db not exposed).

Add MCP server secrets as needed (e.g., API keys for servers you add).

## Architecture

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| MCPJungle Gateway | `emcp-server` container (port 3700) | Aggregates MCP servers, routes tool calls, manages groups |
| eMCP Manager | `emcp-manager/app.py` (port 3701) | Flask web UI and API for tool selection |

### Group System

- Groups are JSON files in `groups/` directory
- Default group: `emcp-global`
- Each group specifies `included_tools` array
- MCPJungle exposes groups at `/v0/groups/{group}/mcp`

## Adding MCP Servers

### Via Web UI

1. Open http://localhost:3701
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

Config files in `configs/` are auto-registered on `make up`. For manual operations:

```bash
docker exec emcp-server /mcpjungle register -c /configs/<name>.json
docker exec emcp-server /mcpjungle deregister <name>
make register   # Re-register all configs
```

## Design Principles

- **Server prefix indicates platform** — tool names like `server__tool` encode the source
- **Minimal by default** — ship only core infra, users add what they need
