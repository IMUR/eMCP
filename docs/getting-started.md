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

Open **<http://localhost:3701>** to access the web UI.

### Custom Ports

If the default ports (3700, 3701) conflict with other services, add overrides to `.env`:

```env
EMCP_GATEWAY_PORT=3710
EMCP_MANAGER_PORT=3711
```

Then: `make down && make up`

## Connect Your AI Agent

Point your MCP client to:

```
http://localhost:3700/v0/groups/emcp-global/mcp
```

This is the MCP Streamable HTTP endpoint for the default `emcp-global` group. See [Connect Your Agent](connect.md) for platform-specific setup.

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
