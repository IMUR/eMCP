# API Reference

eMCP exposes two sets of endpoints: the **Manager API** (port 3701) for administration, and the **Gateway API** (port 3700) for MCP protocol access.

## Manager API (port 3701)

### Dashboard

```
GET /
```

Returns the web UI.

---

### Get All Tools

```
GET /api/tools
```

Returns all registered tools grouped by server.

```json
{
  "success": true,
  "servers": {
    "filesystem": [
      {"name": "filesystem__read_file", "description": "..."},
      {"name": "filesystem__write_file", "description": "..."}
    ]
  }
}
```

---

### Get Current Selection

```
GET /api/current
```

Returns the active group and its enabled tools.

```json
{
  "success": true,
  "group": "emcp-global",
  "tools": ["filesystem__read_file", "filesystem__write_file"]
}
```

---

### Toggle Tool

```
POST /api/tools/toggle
Content-Type: application/json

{"tool": "filesystem__read_file"}
```

Enables or disables a tool in the active group. Returns the updated tool list.

---

### List Servers

```
GET /api/servers
```

Returns all registered MCP servers with their container status and tool counts.

---

### Provision Server

```
POST /api/servers/provision
Content-Type: application/json

{
  "name": "my-server",
  "image": "docker-image:tag",
  "command": ["cmd", "args"],
  "env_vars": {"API_KEY": "value"},
  "description": "My MCP server"
}
```

Provisions a new MCP server: pulls the image, starts the container, waits for MCP readiness, and registers tools.

---

### Delete Server

```
DELETE /api/servers/{name}
```

Stops the container, deregisters tools, and removes the server from configuration.

---

### Restart Server

```
POST /api/servers/{name}/restart
```

Restarts the server's Docker container.

---

### Secrets Status

```
GET /api/servers/secrets-status
```

Returns the active secret management method (`env_file` or `infisical`).

---

## Gateway API (port 3700)

### MCP Protocol Endpoint

```
POST /v0/groups/{group-name}/mcp
```

MCP Streamable HTTP endpoint. Requires session initialization:

```bash
# Step 1: Initialize session
SESSION_ID=$(curl -s http://localhost:3700/v0/groups/emcp-global/mcp \
  -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  -D - -o /dev/null 2>&1 | grep -i 'mcp-session-id' | awk '{print $2}' | tr -d '\r')

# Step 2: List tools
curl -s http://localhost:3700/v0/groups/emcp-global/mcp \
  -X POST -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

### List All Registered Tools

```
GET /api/v0/tools
```

Returns a flat list of all tools registered in the gateway (regardless of group).
