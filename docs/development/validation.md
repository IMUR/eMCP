# eMCP Full System Validation

End-to-end test procedure for validating eMCP on a clean system. Run this in a disposable VM to confirm the project works for a new user with no prior setup.

---

## Prerequisites

A fresh Linux VM (Debian/Ubuntu recommended) with:

- 2+ GB RAM
- 10 GB disk
- Internet access
- sudo privileges

---

## Phase 1: Environment Setup

### 1.1 Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

**Verify:**

```bash
docker --version
docker compose version
```

**Pass:** Both commands return version numbers.

### 1.2 Install Git

```bash
sudo apt-get update && sudo apt-get install -y git curl jq make
```

### 1.3 Clone the Repository

```bash
cd ~
git clone https://github.com/IMUR/eMCP.git
cd eMCP
```

**Verify:**

```bash
ls docker-compose.yaml emcp-manager/app.py configs/filesystem.json
```

**Pass:** All three files exist.

---

## Phase 2: Configuration

### 2.1 Create .env

```bash
cp .env.example .env
```

Edit `.env` — set a real password:

```
POSTGRES_USER=emcp
POSTGRES_PASSWORD=<your-password>
```

**Verify:**

```bash
cat .env | grep -c '='
```

**Pass:** Returns `2` (both variables present).

### 2.2 Create Demo Data

```bash
mkdir -p demo-data
echo "Hello from eMCP" > demo-data/hello.txt
echo '{"test": true}' > demo-data/sample.json
```

---

## Phase 3: First Start

### 3.1 Start Services

```bash
make up
```

**Verify:**

```bash
docker compose ps
```

**Pass:** Four containers running: `emcp-db`, `emcp-server`, `emcp-manager`, `filesystem-mcp`. All show status `Up` or `running`.

### 3.2 Wait for Healthy State

```bash
# Wait for database
until docker exec emcp-db pg_isready -U emcp 2>/dev/null; do sleep 2; done
echo "DB ready"

# Wait for gateway (may take 30-60s on first build)
until curl -sf http://localhost:8090/api/v0/tools > /dev/null 2>&1; do sleep 5; done
echo "Gateway ready"

# Wait for manager
until curl -sf http://localhost:5010/api/current > /dev/null 2>&1; do sleep 3; done
echo "Manager ready"
```

**Pass:** All three print "ready" without hanging indefinitely.

### 3.3 Check Logs for Errors

```bash
docker compose logs emcp-server 2>&1 | grep -i "error\|fatal\|panic" | head -5
docker compose logs emcp-manager 2>&1 | grep -i "error\|traceback" | head -5
```

**Pass:** No critical errors. Transient connection retries during startup are acceptable.

---

## Phase 4: Demo Server Validation

### 4.1 Register Demo Server

```bash
docker exec emcp-server /mcpjungle register -c /configs/filesystem.json
```

**Pass:** No error output (or confirmation message).

### 4.2 Verify Tools Appear

```bash
curl -s http://localhost:8090/api/v0/tools | jq '.[].name' | head -20
```

**Pass:** Output includes tool names prefixed with `filesystem__` (e.g., `filesystem__read_file`, `filesystem__list_directory`).

### 4.3 Count Registered Tools

```bash
TOOL_COUNT=$(curl -s http://localhost:8090/api/v0/tools | jq 'length')
echo "Tools registered: $TOOL_COUNT"
```

**Pass:** `TOOL_COUNT` is greater than 0.

---

## Phase 5: Web UI Validation

### 5.1 Dashboard Loads

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5010/
```

**Pass:** Returns `200`.

### 5.2 Tools API

```bash
curl -s http://localhost:5010/api/tools | jq '.servers | keys'
```

**Pass:** Returns a JSON object with server names as keys (should include `filesystem`).

### 5.3 Current Selection API

```bash
curl -s http://localhost:5010/api/current | jq '.group'
```

**Pass:** Returns `"emcp-global"`.

### 5.4 Visual Inspection (if GUI available)

Open `http://<vm-ip>:5010` in a browser.

**Check:**

- [ ] Dashboard loads without errors
- [ ] Tool list shows filesystem server tools
- [ ] Tools can be toggled on/off via checkboxes
- [ ] "Save" persists selection (refresh page to confirm)
- [ ] "Add MCP Server" button opens the provisioning dialog

---

## Phase 6: Group System Validation

### 6.1 Read Default Group

```bash
cat groups/emcp-global.json | jq .
```

**Pass:** Valid JSON with `name`, `description`, and `included_tools` fields.

### 6.2 Add a Tool to the Group

```bash
# Get the first available tool name
TOOL=$(curl -s http://localhost:8090/api/v0/tools | jq -r '.[0].name')
echo "Adding tool: $TOOL"

# Update group via API
curl -s -X POST http://localhost:5010/api/tools/toggle \
  -H "Content-Type: application/json" \
  -d "{\"tool\": \"$TOOL\", \"enabled\": true}" | jq .
```

**Pass:** Returns success response.

### 6.3 Verify Group Persists

```bash
cat groups/emcp-global.json | jq '.included_tools'
```

**Pass:** The tool name appears in the `included_tools` array.

### 6.4 Group MCP Endpoint

```bash
# Initialize a session first (MCP Streamable HTTP requires this)
SESSION_ID=$(curl -s http://localhost:8090/v0/groups/emcp-global/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  -D - -o /dev/null 2>&1 | grep -i 'mcp-session-id' | awk '{print $2}' | tr -d '\r')

# List tools using the session
curl -s http://localhost:8090/v0/groups/emcp-global/mcp -X POST \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | jq '.result.tools | length'
```

**Pass:** Returns the number of tools in the group (should match the tools you enabled).

### 6.5 Reset Group

```bash
echo '{"name":"emcp-global","description":"Default global tool group for eMCP","included_tools":[]}' > groups/emcp-global.json
```

**Pass:** File written, group is now empty.

---

## Phase 7: Manual Server Addition

### 7.1 Add a Second Demo Server

Add to `docker-compose.yaml` (append before `volumes:`):

```yaml
  filesystem-mcp-2:
    image: node:22-slim
    container_name: filesystem-mcp-2
    command: ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/demo"]
    stdin_open: true
    tty: true
    volumes:
      - ./demo-data:/demo:ro
    networks:
      - emcp-network
    restart: unless-stopped
```

### 7.2 Create Config

```bash
cat > configs/filesystem2.json << 'EOF'
{
    "name": "filesystem2",
    "transport": "stdio",
    "description": "Second filesystem server for testing",
    "command": "docker",
    "args": ["exec", "-i", "filesystem-mcp-2", "npx", "@modelcontextprotocol/server-filesystem", "/demo"]
}
EOF
```

### 7.3 Start and Register

```bash
docker compose up -d filesystem-mcp-2
docker exec emcp-server /mcpjungle register -c /configs/filesystem2.json
```

**Verify:**

```bash
curl -s http://localhost:5010/api/tools | jq 'keys'
```

**Pass:** Output includes both `filesystem` and `filesystem2`.

### 7.4 Deregister and Remove

```bash
docker exec emcp-server /mcpjungle deregister filesystem2
docker compose rm -sf filesystem-mcp-2
rm configs/filesystem2.json
```

**Verify:**

```bash
curl -s http://localhost:5010/api/tools | jq 'keys'
```

**Pass:** Only `filesystem` remains.

---

## Phase 8: Make Targets

### 8.1 Stop

```bash
make down
```

**Verify:**

```bash
docker compose ps
```

**Pass:** No containers running (or all show `Exited`).

### 8.2 Start

```bash
make up
```

**Pass:** Output shows URLs for Web UI and Gateway. All containers come back up.

### 8.3 Status

```bash
make status
```

**Pass:** Shows container status table and tool count.

### 8.4 Re-register

```bash
make register
```

**Pass:** Loops through configs, registers each, then lists servers. Tools reappear in the API.

### 8.5 Help

```bash
make help
```

**Pass:** Lists all available targets with descriptions.

---

## Phase 9: Resilience

### 9.1 Gateway Restart Recovery

```bash
docker restart emcp-server
sleep 10
curl -s http://localhost:8090/api/v0/tools | jq 'length'
```

**Pass:** Tools are still available after restart.

### 9.2 Database Restart Recovery

```bash
docker restart emcp-db
sleep 15
curl -s http://localhost:8090/api/v0/tools | jq 'length'
```

**Pass:** Gateway reconnects and tools remain available.

### 9.3 Full Stack Restart

```bash
docker compose down
docker compose up -d
sleep 30
curl -s http://localhost:5010/api/tools | jq 'keys'
```

**Pass:** All services recover. Note: tools may need re-registration after a full restart — run `make register` if tools are missing.

### 9.4 MCP Server Container Restart

```bash
# Record tool count before
BEFORE=$(curl -s http://localhost:8090/api/v0/tools | jq 'length')
echo "Tools before: $BEFORE"

# Restart only the MCP server container (not the gateway)
docker restart filesystem-mcp
sleep 10

# Check if tools are still served
AFTER=$(curl -s http://localhost:8090/api/v0/tools | jq 'length')
echo "Tools after: $AFTER"
```

If tools are missing after the restart, re-register:

```bash
make register
FIXED=$(curl -s http://localhost:8090/api/v0/tools | jq 'length')
echo "Tools after re-register: $FIXED"
```

**Pass:** Tools return after `make register`. This confirms that restarting an MCP server container can cause its tools to stop being served. `make register` is the fix.

---

## Phase 10: Security Checks

### 10.1 No Secrets in Repo

```bash
grep -rn 'password\|secret\|token\|key' . \
  --include='*.yaml' --include='*.json' --include='*.sh' --include='*.md' \
  | grep -v '.git/' \
  | grep -v 'example\|placeholder\|template\|changeme\|your_\|POSTGRES_PASSWORD\|POSTGRES_USER\|API_KEY=\${' \
  | grep -v '\.env\.example' \
  | grep -v 'TEST_VALIDATION'
```

**Pass:** No lines contain actual secret values. Only variable references and documentation.

### 10.2 .env Permissions

```bash
# Linux:
stat -c '%a' .env
# macOS:
stat -f '%A' .env
```

**Pass:** Returns `600` or `644`.

### 10.3 .env Not Tracked

```bash
git status --porcelain .env
```

**Pass:** Returns empty (file is gitignored) or `??` (untracked). Never `A` or `M`.

### 10.4 Docker Socket Access

```bash
docker exec emcp-manager ls /var/run/docker.sock
```

**Pass:** File exists (required for server provisioning feature).

---

## Phase 11: Cleanup

```bash
cd ~
docker compose -f eMCP/docker-compose.yaml down -v
rm -rf eMCP
```

**Pass:** All containers stopped, volumes removed, directory deleted.

---

## Results Summary

| Phase | Description | Pass/Fail |
|-------|-------------|-----------|
| 1 | Environment Setup | |
| 2 | Configuration | |
| 3 | First Start | |
| 4 | Demo Server | |
| 5 | Web UI | |
| 6 | Group System | |
| 7 | Manual Server Addition | |
| 8 | Make Targets | |
| 9 | Resilience | |
| 10 | Security Checks | |
| 11 | Cleanup | |

**Tested on:** *(OS, Docker version, date)*
**Result:** *(PASS / FAIL — list failures)*
