# eMCP Operational Reference

## Port Configuration

Default ports and their environment variable overrides:

| Service | Default | Container Port | Override Variable |
|---------|---------|---------------|-------------------|
| Gateway | 3700 | 8080 | `EMCP_GATEWAY_PORT` |
| Manager | 3701 | 5000 | `EMCP_MANAGER_PORT` |
| Database | — | 5432 (internal only) | — |

The database is not exposed to the host. It is only accessible within the Docker network. Set port overrides in `.env` before `make up`.

## Registration Lifecycle

MCPJungle does not auto-discover config files. Every server in `configs/*.json` must be explicitly registered:

```bash
docker exec emcp-server /mcpjungle register -c /configs/<name>.json
```

`make up` handles this automatically. `make register` re-runs it for all configs (deregister + register cycle).

### When to run make register

- After restarting an MCP server container while the gateway is still running
- After adding a new config file to `configs/`
- After `make up` if tools are missing (shouldn't happen, but safe fallback)

### Why tools silently disappear

If an MCP server container restarts after the gateway started, the gateway may silently stop serving that server's tools. The registration metadata is intact (the server shows as registered), but the tools don't appear in MCP protocol responses. `make register` fixes this by forcing a fresh registration cycle.

## Image Sources

| Service | Image | Source |
|---------|-------|--------|
| emcp-server | `ghcr.io/imur/emcp-server:latest` | Built from `dockerfiles/Dockerfile.gateway` |
| emcp-manager | `ghcr.io/imur/emcp-manager:latest` | Built from `emcp-manager/Dockerfile` |
| emcp-db | `postgres:17` | Official PostgreSQL |
| filesystem-mcp | `node:22-slim` | Official Node.js (runs npx) |

For local development builds, use `make dev` which applies `docker-compose.dev.yaml` overlay.

## API Endpoints

### Gateway (emcp-server, default port 3700)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v0/tools` | GET | List all registered tools |
| `/v0/groups/{name}/mcp` | POST | MCP Streamable HTTP endpoint |

### Manager (emcp-manager, default port 3701)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Web UI |
| `/api/tools` | GET | All tools grouped by server |
| `/api/current` | GET | Currently selected tools in active group |
| `/api/tools/toggle` | POST | Enable/disable a tool in the group |

## Docker Compose Project Name

The project name is explicitly set to `emcp` in `docker-compose.yaml`. This prevents collisions when multiple eMCP installations exist on the same host (e.g., personal and test). If running a second installation, set a different `name:` in its compose file.
