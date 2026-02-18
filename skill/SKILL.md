---
name: emcp
description: Manage eMCP installations — setup, port selection, registration, troubleshooting, and operational tasks for the Tool Access Broker.
---

# eMCP Operations

Manage eMCP (Tool Access Broker for MCP systems) on any host. Handles installation, configuration, port conflicts, server registration, and troubleshooting.

## When to Use

- Setting up eMCP on a new system
- Diagnosing why tools aren't appearing
- Adding or removing MCP servers
- Resolving port conflicts
- Checking system health

## Do Not Use When

- The task is unrelated to eMCP or MCP server management
- Working on MCPJungle internals (upstream project)

## Architecture

```
AI Agent → eMCP Gateway (MCPJungle, port 8090) → MCP Servers
                ↑
          Web UI (port 5010)
          PostgreSQL (port 5432)
```

All three ports are configurable via `.env`:
- `EMCP_GATEWAY_PORT` (default: 8090)
- `EMCP_MANAGER_PORT` (default: 5010)
- `EMCP_DB_PORT` (default: 5432)

## Installation

Run the port check script first if the host may have conflicting services:

```bash
./skill/scripts/check-ports.sh
```

Then install:

```bash
git clone https://github.com/IMUR/eMCP.git && cd eMCP
make up
```

`make up` handles everything: `.env` creation, container startup, gateway health wait, and config registration.

## Common Operations

### Check health
```bash
make status
```

### Re-register all servers after a container restart
```bash
make register
```

### Add an MCP server via CLI
```bash
# 1. Add service to docker-compose.yaml
# 2. Create config in configs/<name>.json
# 3. Start and register:
docker compose up -d <name>
docker exec emcp-server /mcpjungle register -c /configs/<name>.json
```

### Connect an AI agent
Point the MCP client to:
```
http://<host>:<gateway-port>/v0/groups/emcp-global/mcp
```

## Troubleshooting

### Tools not appearing
Run `make register`. This deregisters and re-registers all server configs. If an MCP server container restarted while the gateway was running, its tools silently stop being served. Re-registration fixes this.

### Gateway not ready
Check if the gateway container is running and healthy:
```bash
docker compose ps emcp-server
docker compose logs emcp-server --tail 20
```

### Port conflict
Run the port check script:
```bash
./skill/scripts/check-ports.sh
```
If ports are taken, add overrides to `.env`:
```env
EMCP_GATEWAY_PORT=8091
EMCP_MANAGER_PORT=5011
EMCP_DB_PORT=5433
```
Then restart: `make down && make up`

### Manager shows unhealthy but works fine
The healthcheck uses Python's urllib inside the container. If it reports unhealthy but the web UI loads at the manager URL, the container is functional. Check with:
```bash
curl -s http://localhost:${EMCP_MANAGER_PORT:-5010}/api/current | jq .
```

### Containers from Web UI not cleaned up
Servers added via the Web UI modify `docker-compose.yaml`. Use:
```bash
make clean
```
This runs `docker compose down -v --remove-orphans` which catches dynamically-added containers.

## Key Files

| File | Purpose |
|------|---------|
| `docker-compose.yaml` | Service definitions (pulls from ghcr.io) |
| `docker-compose.dev.yaml` | Local build override for contributors |
| `.env` | Credentials and port overrides |
| `configs/*.json` | MCPJungle server registration configs |
| `groups/emcp-global.json` | Default tool group (which tools are exposed) |
| `Makefile` | All operational commands |

## Scripts

- `skill/scripts/check-ports.sh` — Detect port conflicts before installation
- `skill/scripts/diagnose.sh` — Collect diagnostic info for troubleshooting
