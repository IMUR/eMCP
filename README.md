# eMCP

**Tool Access Broker for MCP systems.** Filters which tools AI agents can access to reduce token costs and cognitive overhead.

```
AI Agent → eMCP Gateway → MCP Servers
              ↑
        Web UI (tool toggle)
```

## Two ways to run eMCP

eMCP ships in two flavors. Same architecture, same UI, same MCP endpoint shape — pick the deployment style that fits.

### Containerized (Docker)

```bash
git clone https://github.com/IMUR/eMCP.git && cd eMCP
make up
```

### Native (no Docker)

```bash
git clone https://github.com/IMUR/eMCP.git && cd eMCP
make native-install        # downloads mcpjungle binary, sets up venv, systemd
```

Either way: open **<http://localhost:3701>** for the dashboard, point your AI client at `http://localhost:3700/v0/groups/<group-name>/mcp`.

See [docs/native.md](docs/native.md) for the native install in detail.

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

**Containerized:**

```
make up         Start all services (auto-registers configs)
make down       Stop all services
make dev        Build and start locally (for development)
make status     Service health + tool count
make register   Re-register all server configs
make clean      Remove containers, volumes, data
```

**Native:**

```
make native-install    Install native eMCP (mcpjungle binary + venv + systemd)
make native-uninstall  Remove native install (preserves data dir)
make native-up         Start native services
make native-down       Stop native services
make native-status     Service health + tool count
make native-logs       Tail journal logs
```

Run `make help` for the full list.

## License

[MIT](LICENSE)
