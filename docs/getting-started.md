# Getting Started

## Prerequisites

- Docker and Docker Compose
- `jq` (JSON processor)
- `make`

## Install and Run

```bash
git clone https://github.com/IMUR/eMCP.git
cd eMCP
make up
```

That's it. This will:

1. Create a default `.env` from `.env.example` (if one doesn't exist)
2. Start four containers (database, gateway, web UI, demo filesystem server)
3. Wait for the gateway to be ready
4. Register the demo server's 14 tools
5. Print container status and URLs

Open **<http://localhost:5010>** to access the web UI.

### Custom Credentials

By default, the database uses `emcp`/`emcp`. To set your own credentials, edit `.env` before running `make up`:

```bash
cp .env.example .env
# Edit POSTGRES_USER and POSTGRES_PASSWORD
make up
```

### Custom Ports

If the default ports (5010, 8090, 5432) conflict with other services, add overrides to `.env`:

```env
EMCP_MANAGER_PORT=5011
EMCP_GATEWAY_PORT=8091
EMCP_DB_PORT=5433
```

## Connect Your AI Agent

Point your MCP client to:

```
http://localhost:8090/v0/groups/emcp-global/mcp
```

This is the MCP Streamable HTTP endpoint for the default `emcp-global` group.

## Make Targets

```
make help       Show all targets
make up         Start all services (auto-registers configs)
make down       Stop all services
make dev        Build and start locally (for development)
make restart    Restart all services
make logs       Tail gateway logs
make status     Service health + tool count
make register   Re-register all configs with MCPJungle
make clean      Remove containers, volumes, runtime data
```

## Next Steps

- [Add MCP Servers](adding-servers.md) — connect your own tools
- [Groups](groups.md) — create custom tool sets
- [API Reference](api-reference.md) — programmatic access
- [Troubleshooting](troubleshooting.md) — something not working?
