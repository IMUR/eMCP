# Getting Started

## Prerequisites

- Docker and Docker Compose
- `jq` (JSON processor)
- `make`

## Installation

```bash
git clone https://github.com/IMUR/eMCP.git
cd eMCP
```

## Configuration

Create your environment file:

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
POSTGRES_USER=emcp
POSTGRES_PASSWORD=your-secure-password
```

## First Start

```bash
make up
```

This starts four containers:

| Container | Purpose |
|-----------|---------|
| `emcp-db` | PostgreSQL database |
| `emcp-server` | MCPJungle gateway (port 8090) |
| `emcp-manager` | Web UI (port 5010) |
| `filesystem-mcp` | Demo filesystem MCP server |

## Register the Demo Server

```bash
make register
```

This registers the included filesystem server with the gateway, making its 14 tools available.

## Verify

```bash
make status
```

You should see all containers healthy and 14 tools registered.

Open **<http://localhost:5010>** to access the web UI.

## Connect Your AI Agent

Point your MCP client to:

```
http://localhost:8090/v0/groups/emcp-global/mcp
```

This is the MCP Streamable HTTP endpoint for the default `emcp-global` group.

## Make Targets

```
make help       Show all targets
make up         Start all services
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
