# Running without Docker

eMCP ships a fully native deployment path alongside the containerized one. Same architecture, same UI, same MCP endpoint shape — just no Docker.

The native path is the right choice when:

- You don't have Docker available (or don't want it).
- You want eMCP to integrate with the host's systemd, journald, and process supervision.
- You're running on a constrained device and want to skip the container overhead.
- You want the deployment to be transparent — every component is a file or a systemd unit you can inspect.

## Quick install

```bash
git clone https://github.com/IMUR/eMCP.git && cd eMCP
make native-install
```

What this does:

1. Downloads the pinned [MCPJungle](https://github.com/mcpjungle/MCPJungle) binary, verifies its SHA, installs to `/usr/local/bin/mcpjungle`.
2. Sets up a Python venv at `/opt/emcp-native/venv` (prefers `uv`, falls back to stdlib).
3. Installs the manager source (`app.py` + `index.html`) to `/opt/emcp-native/`.
4. Renders systemd unit templates with your paths, enables and starts `emcp-gateway` + `emcp-manager`.

When done:

- **Manager UI** — <http://localhost:3701>
- **Gateway** — <http://localhost:3700>
- **MCP client endpoint** — `http://localhost:3700/v0/groups/<name>/mcp`

## Customizing

Override defaults via env vars:

```bash
sudo EMCP_USER=mcp \
     EMCP_PREFIX=/opt/local \
     EMCP_EXTRA_PATH=/home/me/.local/share/mise/shims \
     ./native/install.sh
```

| Variable | Default | Purpose |
|---|---|---|
| `EMCP_PREFIX` | `/usr/local` | Where the `mcpjungle` binary goes |
| `EMCP_OPT` | `/opt/emcp-native` | Manager source + venv |
| `EMCP_ETC` | `/etc/emcp-native` | env file |
| `EMCP_DATA_DIR` | `/var/lib/emcp-native` | Groups, configs, SQLite |
| `EMCP_USER` | invoking user | Service runs as this user |
| `MCPJUNGLE_VERSION` | `0.4.1` | Pinned upstream version |
| `EMCP_EXTRA_PATH` | (empty) | Extra PATH dirs the service needs (e.g. mise shims) |

## Architecture, made literal

The containerized path bundles a lot of plumbing inside `docker-compose.yaml`. The native path makes everything explicit:

```
/usr/local/bin/mcpjungle         ← upstream binary at pinned version
/opt/emcp-native/
  app.py                         ← Flask manager (python)
  index.html                     ← dashboard
  venv/                          ← uv-managed
/etc/emcp-native/env             ← shared environment file
/var/lib/emcp-native/
  groups/*.json                  ← tool-group definitions (source of truth)
  configs/*.json                 ← server registration configs
  mcpjungle.db                   ← MCPJungle's embedded SQLite
/etc/systemd/system/
  emcp-gateway.service           ← MCPJungle as a service
  emcp-manager.service           ← Flask UI as a service
```

The two services talk to each other over plain HTTP on loopback (`http://127.0.0.1:3700`). MCP clients hit the gateway directly at `/v0/groups/<name>/mcp`.

## Day-to-day operation

```bash
# Service control via Make
make native-up           # start
make native-down         # stop
make native-restart      # restart
make native-status       # health + tool count
make native-logs         # tail journal

# Or directly with systemctl
sudo systemctl start emcp-gateway emcp-manager
sudo systemctl status emcp-gateway emcp-manager
sudo journalctl -fu emcp-gateway -u emcp-manager
```

## Adding MCP servers

The Manager API speaks the same shape as the containerized version:

```bash
# List currently registered servers
curl http://localhost:3701/api/servers

# Register a streamable-HTTP MCP server
mcpjungle --registry http://127.0.0.1:3700 register \
  --url https://example.com/mcp \
  --name example

# Or via the Manager API (stdio shape)
curl -X POST http://localhost:3701/api/servers \
  -H "Content-Type: application/json" \
  -d '{"name":"my-server","transport":"stdio","command":"my-mcp-binary","args":["--flag"]}'
```

## Creating tool groups

Groups are how you decide which tools each MCP client sees:

```bash
curl -X POST http://localhost:3701/api/groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "read-only",
    "description": "Read-only filesystem ops",
    "included_tools": [
      "filesystem__read_text_file",
      "filesystem__list_directory",
      "filesystem__search_files"
    ]
  }'
```

Then point your MCP client at: `http://localhost:3700/v0/groups/read-only/mcp`

Group definitions are JSON files in `/var/lib/emcp-native/groups/` — version-control them if you want.

## Uninstall

```bash
make native-uninstall
```

Removes the binary, app dir, config, and systemd units. **Preserves `/var/lib/emcp-native/`** so your groups and SQLite state survive — delete it manually if you want a clean wipe.

## Known limitations

### stdio servers can be slow on first registration

When `mcpjungle` spawns a stdio MCP server subprocess that fetches its npm or Python package on first run (e.g., `npx -y @modelcontextprotocol/server-filesystem`), the registration can exceed the default MCP initialization timeout (120s).

**Workaround**: pre-install the server's package globally before registering.

```bash
# Pre-install
npm install -g @modelcontextprotocol/server-filesystem

# Then register the binary directly
curl -X POST http://localhost:3701/api/servers \
  -H "Content-Type: application/json" \
  -d '{"name":"filesystem","transport":"stdio","command":"mcp-server-filesystem","args":["/tmp"]}'
```

### Streamable-HTTP transport is the safest default

HTTP-based MCP servers register in milliseconds and avoid all the stdio subprocess complexity. If your MCP server can run as a long-lived HTTP service (or you can wrap a stdio server with [supergateway](https://github.com/supercorp-ai/supergateway)), prefer that.

## Troubleshooting

**Service won't start**

```bash
sudo journalctl -u emcp-gateway -n 50 --no-pager
sudo journalctl -u emcp-manager -n 50 --no-pager
```

**Port conflict**

Edit `/etc/emcp-native/env`, change `EMCP_GATEWAY_PORT` / `EMCP_MANAGER_PORT`, then:

```bash
sudo systemctl restart emcp-gateway emcp-manager
```

**Manager can't reach gateway**

```bash
curl http://localhost:3701/api/health
# {"manager": "ok", "gateway": "ok", ...}    ← good
# {"manager": "ok", "gateway": "down: ..."}  ← gateway not reachable
```

If the manager says the gateway is down, check that the gateway is actually listening: `ss -tlnp | grep 3700`.

**Clean reinstall**

```bash
make native-uninstall
sudo rm -rf /var/lib/emcp-native
make native-install
```
