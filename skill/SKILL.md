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
AI Agent → eMCP Gateway (MCPJungle, port 3700) → MCP Servers
                ↑
          Web UI (port 3701)
          PostgreSQL (internal only, not exposed)
```

Ports are configurable via `.env`:
- `EMCP_GATEWAY_PORT` (default: 3700)
- `EMCP_MANAGER_PORT` (default: 3701)

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

Run the script that matches what you see:

| Symptom | Script |
|---------|--------|
| "I see no tools" / tools disappeared | `./skill/scripts/no-tools.sh` |
| "It won't start" / make up fails | `./skill/scripts/wont-start.sh` |
| "My agent can't connect" | `./skill/scripts/cant-connect.sh` |
| Container shows unhealthy | `./skill/scripts/fix-unhealthy.sh` |

Each script detects the root cause and applies the fix automatically. Run `./skill/scripts/diagnose.sh` to collect full diagnostic output if the above don't resolve the issue.

## Key Files

| File | Purpose |
|------|---------|
| `docker-compose.yaml` | Service definitions (pulls from ghcr.io) |
| `docker-compose.dev.yaml` | Local build override for contributors |
| `.env` | Port overrides and MCP server API keys |
| `configs/*.json` | MCPJungle server registration configs |
| `groups/emcp-global.json` | Default tool group (which tools are exposed) |
| `Makefile` | All operational commands |

## Scripts

| Script | Purpose |
|--------|---------|
| `check-ports.sh` | Pre-install: detect port conflicts, suggest overrides |
| `wont-start.sh` | Fix: missing dependencies, .env, port conflicts |
| `no-tools.sh` | Fix: tools disappeared or never appeared |
| `cant-connect.sh` | Fix: agent can't reach eMCP, prints correct URLs |
| `fix-unhealthy.sh` | Fix: unhealthy containers, restarts and re-registers |
| `diagnose.sh` | Info: collect full diagnostic output |
