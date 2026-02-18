# Scope: Operations

## Focus
Docker service management, container health, Make targets, and systemd integration.

## Key Resources
- `make up` / `make down` — Start/stop all services
- `make status` — Container health + tool count
- `make register` — Re-register all MCP server configs
- `make logs` — Tail gateway logs
- `systemd/install.sh` — Install systemd path watcher for auto-reload

## Current Priorities
1. Ensure `make up` works on fresh clone (demo-data creation, no python3 dep)
2. Verify all 4 containers start healthy: emcp-db, emcp-server, emcp-manager, filesystem-mcp
3. Confirm tool registration persists across restarts

## Patterns
- Services use `emcp-network` bridge network
- Gateway port: 8090 (maps to internal 8080)
- Manager port: 5010 (maps to internal 5000)
- PostgreSQL port: 5432
- Docker socket mounted into emcp-server and emcp-manager for container management
- `restart: unless-stopped` on all services (emcp-server uses `restart: always`)

## Cautions
- `make clean` does full reset: removes containers, volumes, data/, demo-data/
- emcp-server depends on db healthcheck — first start may take 30-60s
- Registered servers are lost on `docker compose down -v` (destroys DB volume)
- Run `make register` after any fresh start to re-register configs
