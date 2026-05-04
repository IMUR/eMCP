# eMCP Native — Quick Start

Run eMCP without Docker. Installs the upstream MCPJungle binary directly, sets up a Python venv for the manager, and wires both into systemd.

## Install

```bash
sudo ./install.sh
```

That's it. The script:

1. Downloads MCPJungle 0.4.1 (pinned), verifies SHA, installs to `/usr/local/bin/mcpjungle`.
2. Sets up the manager venv at `/opt/emcp-native/venv` (uses `uv` if available, falls back to `python -m venv`).
3. Renders systemd unit templates with your paths and starts both services.

When done:

- **Manager UI** — <http://localhost:3701>
- **Gateway** — <http://localhost:3700>
- **MCP client endpoint** — `http://localhost:3700/v0/groups/<group-name>/mcp`

## Customizing the install

Override defaults via env vars. Examples:

```bash
# Install for a specific service user (default: invoking user)
sudo EMCP_USER=mcp ./install.sh

# Use a different MCPJungle version
sudo MCPJUNGLE_VERSION=0.4.0 ./install.sh

# Install to a different prefix
sudo EMCP_PREFIX=/opt/local ./install.sh

# Add extra dirs to the service PATH (mise shims, asdf, nvm, etc.)
sudo EMCP_EXTRA_PATH=/home/me/.local/share/mise/shims ./install.sh

# Skip systemd setup (just install files)
sudo ./install.sh --no-systemd
```

| Variable | Default | Purpose |
|---|---|---|
| `EMCP_PREFIX` | `/usr/local` | Where the `mcpjungle` binary goes |
| `EMCP_OPT` | `/opt/emcp-native` | Manager source + venv |
| `EMCP_ETC` | `/etc/emcp-native` | env file |
| `EMCP_DATA_DIR` | `/var/lib/emcp-native` | Groups, configs, SQLite |
| `EMCP_USER` | invoking user / `$SUDO_USER` | Service runs as this user |
| `MCPJUNGLE_VERSION` | `0.4.1` | Pinned upstream version |
| `EMCP_EXTRA_PATH` | (empty) | Extra PATH dirs the service needs |

## Uninstall

```bash
sudo ./install.sh --uninstall
```

Removes the binary, app dir, config, and systemd units. **Preserves `${EMCP_DATA_DIR}`** so your groups and SQLite survive — delete it manually if you want a clean wipe.

## Architecture

eMCP Native is two processes connected by HTTP on loopback:

```
┌──────────────────────────────────────┐
│  AI Client (Claude/Cursor/Codex/...) │
└──────────────┬───────────────────────┘
               │ MCP over HTTP (streamable)
               ▼
       ┌────────────────────┐
       │  MCPJungle gateway │ :3700  ← upstream binary, pinned
       └─┬──────────────┬───┘
 stdio /  │              │  admin API (HTTP)
 HTTP     ▼              ▲
 ┌───────────────┐       │
 │ MCP server N  │       │
 │ (subprocess   │       │
 │  or remote)   │       │
 └───────────────┘       │
                         │
                ┌────────┴───────────┐
                │  eMCP Manager      │ :3701 ← Flask, in venv
                │  (UI + provisioning)│
                └────────────────────┘
```

Compare to the containerized path: same processes, same ports, same env-var contract — just running directly on the host instead of in containers.

## Layout after install

```
/usr/local/bin/mcpjungle         # upstream binary, pinned
/opt/emcp-native/
  app.py                         # Flask manager
  index.html                     # dashboard
  requirements.txt
  venv/                          # uv-managed
/etc/emcp-native/
  env                            # ports, paths, timeouts (edit + restart)
/var/lib/emcp-native/
  groups/                        # JSON tool-group definitions (source of truth)
  configs/                       # JSON server registration configs
  mcpjungle.db                   # MCPJungle's SQLite state
/etc/systemd/system/
  emcp-gateway.service           # rendered from template
  emcp-manager.service           # rendered from template
```

## Operating

```bash
# Start / stop / restart
sudo systemctl start emcp-gateway emcp-manager
sudo systemctl stop  emcp-manager emcp-gateway
sudo systemctl restart emcp-gateway emcp-manager

# Logs
sudo journalctl -fu emcp-gateway -u emcp-manager

# Health
curl http://localhost:3701/api/health

# Or via Make targets
make native-status
make native-logs
make native-restart
```

## Adding MCP servers

Three channels (in order of permanence):

1. **Manager API** — `POST http://localhost:3701/api/servers` with the server config JSON.
2. **CLI** — `mcpjungle register -c <config.json>`. Configs land in `/var/lib/emcp-native/configs/`.
3. **Web UI** — coming back later with provisioning support.

Example: register a streamable-HTTP MCP server:

```bash
mcpjungle --registry http://127.0.0.1:3700 register \
  --url https://example.com/mcp \
  --name example
```

Then create a group selecting which tools to expose:

```bash
curl -X POST http://localhost:3701/api/groups \
  -H "Content-Type: application/json" \
  -d '{"name":"demo","included_tools":["example__some_tool"]}'
```

Point your MCP client at: `http://localhost:3700/v0/groups/demo/mcp`

## Known limitations

- **stdio MCP servers can be slow on first registration.** When `mcpjungle` spawns a stdio subprocess that fetches its npm/Python package on first run, the registration can exceed the default init timeout. The `MCP_SERVER_INIT_REQ_TIMEOUT_SEC` in `/etc/emcp-native/env` is set to 120s; pre-installing the server's package globally (e.g., `npm install -g @modelcontextprotocol/server-filesystem`) avoids the issue entirely.
- **Streamable-HTTP servers are the safe default.** They register in milliseconds and are fully native-friendly.

## Troubleshooting

**Service won't start:**

```bash
sudo journalctl -u emcp-gateway -n 50
sudo journalctl -u emcp-manager -n 50
```

**Port conflict:** edit `/etc/emcp-native/env` and change `EMCP_GATEWAY_PORT` / `EMCP_MANAGER_PORT`, then `sudo systemctl restart emcp-gateway emcp-manager`.

**Manager can't reach gateway:** check `curl http://localhost:3701/api/health`. The `gateway` field tells you whether the manager can talk to the gateway over loopback.

**Need a clean reinstall:** `sudo ./install.sh --uninstall && sudo rm -rf /var/lib/emcp-native && sudo ./install.sh`
