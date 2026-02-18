# Adding MCP Servers

## Via Web UI

1. Open **<http://localhost:3701>**
2. Click **Add MCP Server**
3. Enter a GitHub repo URL, npm package, or Docker image
4. The detector auto-configures the server
5. Enter any required environment variables (stored in `.env`)
6. Click **Provision**

The server starts automatically and its tools appear in the tool list.

## Via Command Line

### 1. Add the Docker service

Add a service to `docker-compose.yaml`:

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

Add the API key to `.env`:

```env
MY_API_KEY=your_key_here
```

### 2. Create the registration config

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

Open the web UI and toggle tools on, or edit `groups/emcp-global.json` directly.

## Removing a Server

```bash
docker exec emcp-server /mcpjungle deregister my-server
docker compose rm -sf my-server
rm configs/my-server.json
```

If something isn't working after adding or removing a server, see [Troubleshooting](troubleshooting.md).
