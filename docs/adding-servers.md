# Adding MCP Servers

## Via Web UI

1. Open http://localhost:5010
2. Click **Add MCP Server**
3. Enter a GitHub repo URL, npm package, or Docker image
4. The detector auto-configures the server
5. Enter any required environment variables
6. Click **Provision**

The manager communicates with Docker directly via the mounted socket to start new containers.

## Manually

### 1. Add Docker service

```yaml
# In docker-compose.yaml under services:
my-server:
  image: some-mcp-server:latest
  container_name: my-server
  command: ["node", "index.js", "stdio"]
  stdin_open: true
  tty: true
  environment:
    - API_KEY=${MY_API_KEY}
  networks:
    - emcp-network
  restart: unless-stopped
```

### 2. Create config

```json
// configs/my-server.json
{
    "name": "my-server",
    "transport": "stdio",
    "description": "My MCP server",
    "command": "docker",
    "args": ["exec", "-i", "my-server", "node", "index.js", "stdio"]
}
```

### 3. Start and register

```bash
docker compose up -d my-server
docker exec emcp-server /mcpjungle register -c /configs/my-server.json
```

### 4. Select tools

Open the web UI and add tools to your group, or edit `groups/emcp-global.json` directly.

## Removing a Server

```bash
docker exec emcp-server /mcpjungle deregister my-server
docker compose rm -sf my-server
rm configs/my-server.json
```

## Troubleshooting

- **Tools not appearing**: Run `make register` to re-register all servers
- **Tools disappeared after a container restart**: If an MCP server container restarts while the gateway is still running, its tools may silently stop being served. Run `make register` to fix. This deregisters and re-registers all servers.
- **Container not starting**: `docker compose logs my-server`
- **Connection errors**: Ensure the server is on `emcp-network`
