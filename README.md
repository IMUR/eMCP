# eMCP

**Tool Access Broker for MCP systems.** Filters which tools AI agents can access to reduce token costs and cognitive overhead.

```
AI Agent → eMCP Gateway → MCP Servers
              ↑
        Web UI (tool toggle)
```

## Quick Start

```bash
git clone https://github.com/IMUR/eMCP.git && cd eMCP
cp .env.example .env    # Set POSTGRES_USER and POSTGRES_PASSWORD
make up                 # Start all services
make register           # Register the demo server
```

Open **<http://localhost:5010>** — toggle tools on/off in the web UI.

Connect your AI agent to: `http://localhost:8090/v0/groups/emcp-global/mcp`

## Documentation

Full docs at [docs/](docs/) or run `make docs` to serve locally.

| Topic | Link |
|-------|------|
| Setup & installation | [Getting Started](docs/getting-started.md) |
| Adding MCP servers | [Adding Servers](docs/adding-servers.md) |
| Tool groups | [Groups](docs/groups.md) |
| API endpoints | [API Reference](docs/api-reference.md) |
| Security | [Security](docs/SECURITY.md) |
| Contributing | [Contributing](docs/contributing.md) |

## Make Targets

```
make help       Show all targets
make up         Start all services
make down       Stop all services
make status     Service health + tool count
make register   Re-register all server configs
make clean      Remove containers, volumes, data
make docs       Serve documentation locally
```

## License

[MIT](LICENSE)
