# Adding MCP Servers to eMCP

This guide covers all methods for adding MCP servers to your eMCP instance.

## Method 1: Web UI (Easiest)

1. Open the eMCP Manager at http://localhost:5010
2. Click **Add MCP Server**
3. Enter one of:
   - A GitHub repository URL (e.g., `https://github.com/github/github-mcp-server`)
   - An npm package name (e.g., `@modelcontextprotocol/server-filesystem`)
   - A Docker image reference (e.g., `ghcr.io/github/github-mcp-server:latest`)
4. The detector will auto-configure the server
5. Enter any required environment variables (API keys, tokens)
6. Click **Provision**

The web UI handles container creation, config generation, and MCPJungle registration automatically.

**Note:** Requires systemd integration for automatic container startup. See the systemd section in the main README.

## Method 2: Manual Configuration

### Step 1: Add Docker service

Add a service block to `docker-compose.yaml`:

```yaml
services:
  # ... existing services ...

  my-mcp-server:
    image: some-image:latest
    container_name: my-mcp-server
    command: ["node", "index.js", "stdio"]
    stdin_open: true     # Required for stdio transport
    tty: true            # Required for stdio transport
    environment:
      - API_KEY=${MY_API_KEY}
    networks:
      - emcp-network     # Must be on the eMCP network
    restart: unless-stopped
```

### Step 2: Create MCPJungle config

Create `configs/my-server.json`:

```json
{
    "name": "my-server",
    "transport": "stdio",
    "description": "My custom MCP server",
    "command": "docker",
    "args": ["exec", "-i", "my-mcp-server", "node", "index.js", "stdio"]
}
```

### Step 3: Start and register

```bash
# Start the container
docker compose up -d my-mcp-server

# Register with MCPJungle
docker exec emcp-server /mcpjungle register -c /configs/my-server.json
```

### Step 4: Add tools to group

Open the web UI and add the server's tools to your desired group, or edit the group JSON directly:

```json
{
    "name": "emcp-global",
    "included_tools": [
        "my-server__tool_name"
    ]
}
```

## Method 3: API

```bash
# Auto-detect from URL
curl -X POST http://localhost:5010/api/servers/detect \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/org/mcp-server"}'

# Provision
curl -X POST http://localhost:5010/api/servers/provision \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-server",
    "image": "ghcr.io/org/server:latest",
    "command": ["node", "dist/index.js", "stdio"],
    "env_vars": {"API_KEY": "secret"},
    "description": "My MCP server"
  }'
```

## Removing a Server

```bash
# Deregister from MCPJungle
docker exec emcp-server /mcpjungle deregister my-server

# Stop and remove container
docker compose rm -sf my-mcp-server

# Delete config
rm configs/my-server.json

# Remove from docker-compose.yaml (manual edit)
```

## Troubleshooting

- **Tools not appearing:** Run `python3 scripts/re-register-tools.py` to re-register all configs
- **Container not starting:** Check `docker compose logs my-mcp-server`
- **Connection errors:** Ensure the server is on `emcp-network`
