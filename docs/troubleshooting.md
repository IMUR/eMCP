# Troubleshooting

Find the symptom that matches what you're seeing. Each section explains what's happening and how to fix it.

eMCP includes diagnostic scripts in `skill/scripts/` that automate these fixes. Run the one that matches your problem, or follow the manual steps below.

## I see no tools

**Likely cause:** Server configs aren't registered with the gateway.

```bash
# Auto-fix
./skill/scripts/no-tools.sh

# Manual fix
make register
```

If an MCP server container restarted while the gateway was still running, its tools silently stop being served. `make register` forces a fresh registration cycle for all servers and restores them.

## It won't start

**Likely cause:** Missing dependency, port conflict, or no `.env` file.

```bash
# Auto-fix (checks all prerequisites, installs jq, resolves ports)
./skill/scripts/wont-start.sh
```

**Manual checklist:**

1. Docker and Docker Compose installed? `docker compose version`
2. `jq` installed? `jq --version`
3. `.env` exists? If not: `cp .env.example .env`
4. Ports free? Check with `./skill/scripts/check-ports.sh`

If ports 3700 or 3701 are taken, add overrides to `.env`:

```env
EMCP_GATEWAY_PORT=3710
EMCP_MANAGER_PORT=3711
```

Then: `make down && make up`

## My agent can't connect

**Likely cause:** Wrong endpoint URL, or the gateway isn't reachable from the agent's network.

```bash
# Auto-fix (prints all reachable URLs)
./skill/scripts/cant-connect.sh
```

The MCP endpoint follows this pattern:

```
http://<host>:<gateway-port>/v0/groups/emcp-global/mcp
```

- **Local agent:** `http://localhost:3700/v0/groups/emcp-global/mcp`
- **Remote agent (LAN):** Use the host's IP instead of `localhost`
- **Remote agent (Tailscale):** Use the Tailscale IP

To add eMCP as an MCP source in Claude Code:

```bash
claude mcp add --transport http emcp http://localhost:3700/v0/groups/emcp-global/mcp
```

## Container shows unhealthy

**Likely cause:** The healthcheck is failing but the service is actually working.

```bash
# Auto-fix (restarts unhealthy containers, re-registers if needed)
./skill/scripts/fix-unhealthy.sh
```

`emcp-manager` may report "unhealthy" even when it's fully functional. Verify by checking if the API responds:

```bash
curl -s http://localhost:3701/api/current | jq .
```

If that returns valid JSON, the container is fine — the healthcheck status is cosmetic.

## Tools disappeared after a restart

When an MCP server container restarts while the gateway is still running, the gateway silently stops serving that server's tools. The server still appears as registered, but its tools won't show up in MCP protocol responses.

```bash
make register
```

This deregisters and re-registers all servers, which restores the tools.

## Orphaned containers after cleanup

If you added servers through the web UI and then run `make down`, those dynamically-added containers may not be cleaned up.

```bash
make clean
```

`make clean` uses `--remove-orphans` to catch containers that aren't in the current compose file.

## Collect diagnostic info

If none of the above fixes your issue, collect full diagnostics:

```bash
./skill/scripts/diagnose.sh
```

This prints system info, container status, gateway health, registered servers, group state, and recent logs.
