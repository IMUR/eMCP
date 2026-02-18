# Adding MCP Servers

eMCP ships with a single demo server (filesystem). You add your own MCP servers via the web UI or manually.

## Via Web UI (Easiest)

1. Open http://localhost:5010
2. Click **Add MCP Server**
3. Enter a GitHub repo URL, npm package, or Docker image
4. Follow the prompts to configure

## Manual Steps

1. Add a service to `docker-compose.yaml` (must include `stdin_open: true`, `tty: true`, and `networks: [emcp-network]`)
2. Create a config in `configs/<name>.json`
3. Start: `docker compose up -d <name>`
4. Register: `docker exec emcp-server /mcpjungle register -c /configs/<name>.json`
5. Select tools in the web UI at http://localhost:5010

## Example: Adding a Server

### docker-compose.yaml entry

```yaml
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

### configs/my-server.json

```json
{
    "name": "my-server",
    "transport": "stdio",
    "description": "My MCP server",
    "command": "docker",
    "args": ["exec", "-i", "my-server", "node", "index.js", "stdio"]
}
```

### .env entry

```
MY_API_KEY=your_key_here
```

Any MCP server that supports stdio transport can be added this way.
