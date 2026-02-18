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
make up
```

Open **<http://localhost:3701>** — toggle tools on/off in the web UI.

Connect your AI agent to: `http://localhost:3700/v0/groups/emcp-global/mcp`

## Documentation

Full docs at **[imur.github.io/eMCP](https://imur.github.io/eMCP)** or run `make docs` locally.

| Topic | Link |
|-------|------|
| Setup & configuration | [Getting Started](docs/getting-started.md) |
| Adding MCP servers | [Adding Servers](docs/adding-servers.md) |
| Tool groups | [Groups](docs/groups.md) |
| Something not working? | [Troubleshooting](docs/troubleshooting.md) |
| API endpoints | [API Reference](docs/api-reference.md) |
| Contributing | [Contributing](docs/contributing.md) |

## Make Targets

```
make help       Show all targets
make up         Start all services (auto-registers configs)
make down       Stop all services
make dev        Build and start locally (for development)
make status     Service health + tool count
make register   Re-register all server configs
make clean      Remove containers, volumes, data
make docs       Serve documentation locally
```

## License

[MIT](LICENSE)
