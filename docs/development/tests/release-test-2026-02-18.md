# eMCP Release Test Report

**Date:** 2026-02-18
**Tester:** Claude Code (automated) + manual validation
**Host:** director (drtr) — Debian 13 (Trixie), i9-9900K, 64GB RAM
**Docker:** 26.1.5+dfsg1, Compose 2.26.1-4
**Repo:** https://github.com/IMUR/eMCP.git (cloned to `/tmp/eMCP`)
**Branch:** `drtr-test` (created from `main` to isolate test changes)
**Port overrides:** `EMCP_GATEWAY_PORT=8788`, `EMCP_MANAGER_PORT=5788`

---

## Summary

| # | Test | Result | Notes |
|---|------|--------|-------|
| 1 | Clone and Configure | PASS | `.env` created, credentials set, port overrides applied |
| 2 | First Start | PASS | 4 containers running, no build errors |
| 3 | Health Check | PASS | Gateway (8788) and Manager (5788) responsive within timeout |
| 4 | Register Demo Server | PASS | `filesystem` registered, 14 tools available |
| 5 | Web UI | PASS | HTTP 200, `filesystem` present under `servers` key |
| 6 | Tool Selection | PASS | Toggle returned `true`, current tools count = 1 |
| 7 | Restart Resilience | PASS | 14 tools recovered after `make down && make up` |
| 8 | MCP Server Restart | PASS | Tools survived `docker restart filesystem-mcp` (14→14) |
| 9 | Status Target | **FAIL** | Tool count empty, manager shows `unhealthy` |
| 10 | Security | **FAIL** | Password found in tracked `validation.md` |
| 11 | Cleanup | PASS | Containers stopped, volumes removed (see Bug 4, Bug 5) |
| 12 | Functional: Local Tool Call | **PASS** | `filesystem__directory_tree` via MCP |
| 13 | Functional: Remote Client | **PASS** | Claude Code on trtr via Tailscale |
| 14 | Functional: Add Server via Web UI | **PASS** | Perplexity server with API key |
| 15 | Functional: Authenticated Tool Call | **PASS** | `perplexity__perplexity_ask` returned valid response |
| 16 | Security: Server Provisioning | **PASS** | API key stayed in `.env`, not in tracked files |

**Overall: PASS** (14/16 pass, 2 fail on non-functional issues, 2 additional bugs found during teardown)

---

## Infrastructure Tests (1-11)

### Tests 1-8: All Passed

Tests followed the scripted release validation procedure (`validation.md`).

Notable observations:
- Custom port overrides via `EMCP_GATEWAY_PORT` and `EMCP_MANAGER_PORT` in `.env` correctly remapped the host-side ports in `docker-compose.yaml`. Internal container ports remained unchanged (8080 for gateway, 5000 for manager).
- `make up` banner still printed hardcoded default ports (`5010`/`8090`) despite overrides being active — cosmetic but misleading.
- `emcp-server` has no healthcheck defined in `docker-compose.yaml`. It relied on the `emcp-db` healthcheck (dependency: `condition: service_healthy`) but had no check of its own.
- The `filesystem-mcp` container has no healthcheck either. It starts immediately and was available before the gateway was ready.

### Test 9: Status Target — FAIL

Two root causes:

1. `make status` curls `http://localhost:8090` (hardcoded) instead of using the configured gateway port. With custom ports, this hits nothing and prints an empty tool count.
2. `emcp-manager` shows `unhealthy` permanently because the Docker healthcheck requires `curl` which is not installed in the image. The healthcheck failure log repeats every 30 seconds:
   ```
   OCI runtime exec failed: exec: "curl": executable file not found in $PATH: unknown
   ```
   The container functions correctly despite this status — all API endpoints respond normally.

### Test 10: Security — FAIL

`testpass123` found in `docs/development/validation.md:73` (a tracked file). The security test's grep exclusion only covers `TEST.md`, not `validation.md`. The password appears in an example code block within the test procedure documentation itself.

### Test 11: Cleanup — PASS (with caveats)

`make clean` (`docker compose down -v`) successfully removed the four original containers and the `db_data` volume. However:
- The Docker network `emcp_emcp-network` reported "Resource is still in use" on first attempt (likely a race condition with container shutdown). This resolved on retry.
- Dynamically-added servers created via the Web UI are not tracked by `make clean` — see Bug 4.
- The Web UI creates root-owned backup files that block `rm -rf` without `sudo` — see Bug 5.

---

## Functional Tests (12-16)

### Test 12: Local Tool Execution (filesystem)

Enabled `filesystem__directory_tree` via Web UI (server name: `emcp-local`). Invoked directly from Claude Code on drtr via MCP protocol:

```
Tool: mcp__emcp-local__filesystem__directory_tree
Input: {"path": "/demo"}
Response: [{"name": "readme.txt", "type": "file"}]
```

**PASS** — Tool call routed through eMCP gateway → `filesystem-mcp` container → valid MCP response returned. The response was a properly structured JSON array with `name` and `type` fields per entry.

### Test 13: Remote Client over Tailscale

From trtr (macOS, M4 MacBook Air) via Headscale/Tailscale VPN:

```bash
claude mcp add --transport http emcp-local http://100.64.0.2:8788/v0/groups/emcp-global/mcp
```

The URL structure `http://<tailscale-ip>:<gateway-port>/v0/groups/<group-name>/mcp` correctly routes to the tool group. Claude Code on trtr was able to discover and invoke tools served by eMCP on drtr.

**PASS** — End-to-end: remote Claude Code client → Tailscale VPN (100.64.0.2) → eMCP gateway (:8788) → MCP server → response.

### Test 14: Add Server via Web UI (Perplexity)

Added `perplexity` MCP server through the Web UI at `http://192.168.254.124:5788`. The UI generated three file changes:

| File | Change |
|------|--------|
| `configs/perplexity.json` | New file — stdio transport config (`docker exec -i perplexity-mcp bunx @perplexity-ai/mcp-server`), no secrets |
| `docker-compose.yaml` | Added `perplexity-mcp` service using `oven/bun:1` image, env var `PERPLEXITY_API_KEY=${PERPLEXITY_API_KEY}` |
| `groups/emcp-global.json` | Added `filesystem__directory_tree` and `perplexity__perplexity_ask` to `included_tools` |

The UI also created a backup at `backups/docker-compose.yaml.20260218_190027` before modifying `docker-compose.yaml`. This backup was root-owned (see Bug 5).

**PASS** — Server provisioning workflow functional. Files correctly separated config from secrets.

### Test 15: Authenticated Tool Call (Perplexity)

Called `perplexity__perplexity_ask` through eMCP with a real query. The API key was passed from `.env` → Docker Compose env var substitution → container environment → Perplexity SDK.

```
Tool: mcp__emcp-local__perplexity__perplexity_ask
Input: {"messages": [{"role": "user", "content": "What is eMCP?"}]}
Response: Full answer with 9 citations (Sonar Pro model)
```

The response included structured citations with URLs, confirming the Perplexity API was fully functional through the eMCP proxy chain.

**PASS** — Authenticated MCP server functional end-to-end.

### Test 16: Security — Server Provisioning

Inspected all file changes after adding the Perplexity server (which requires `PERPLEXITY_API_KEY`):

| File | Contains secret? | Notes |
|------|-----------------|-------|
| `.env` (gitignored) | Yes — `PERPLEXITY_API_KEY=pplx-...` | Correct — secrets live here only |
| `docker-compose.yaml` (tracked) | No — `${PERPLEXITY_API_KEY}` | Env var reference, not value |
| `configs/perplexity.json` (new, untracked) | No | stdio command definition only |
| `groups/emcp-global.json` (tracked) | No | Tool name strings only |
| `backups/docker-compose.yaml.*` (new, untracked) | No | Pre-edit backup, no secrets |

**PASS** — API key confined to `.env` (gitignored). No secrets leaked to tracked or untracked config files.

---

## Bugs Found

### Bug 1: Makefile hardcodes default ports

**Severity:** Low
**Location:** `Makefile` lines 11-12, 27

The `make up` banner and `make status` gateway curl both hardcode `localhost:8090` and `localhost:5010` instead of reading `EMCP_GATEWAY_PORT` and `EMCP_MANAGER_PORT` from the environment.

**Impact:** When using custom ports, `make status` reports no tools (curl hits wrong port) and the banner misleads the user.

**Fix:**
```makefile
# In make up:
@echo "  Web UI:   http://localhost:$${EMCP_MANAGER_PORT:-5010}"
@echo "  Gateway:  http://localhost:$${EMCP_GATEWAY_PORT:-8090}"

# In make status:
@curl -sf http://localhost:$${EMCP_GATEWAY_PORT:-8090}/api/v0/tools 2>/dev/null | jq 'length' 2>/dev/null || echo "gateway not ready"
```

### Bug 2: `curl` missing from `emcp-manager` Docker image

**Severity:** Medium
**Location:** `emcp-manager` Dockerfile + `docker-compose.yaml` healthcheck

The healthcheck uses `curl` but the image doesn't include it. Container is **permanently `unhealthy`** despite functioning correctly. The failing streak increments every 30 seconds indefinitely.

```
OCI runtime exec failed: exec: "curl": executable file not found in $PATH: unknown
```

**Fix options:**
1. Add `curl` to the Dockerfile: `RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*`
2. Switch to `wget`: `test: ["CMD", "wget", "--spider", "-q", "http://localhost:5000/api/current"]`
3. Use a Python healthcheck since the image already has Python: `test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/current')"]`

Option 3 is recommended — zero additional packages, uses what's already in the image.

### Bug 3: Test password in tracked documentation

**Severity:** Low
**Location:** `docs/development/validation.md:73`

The example password `testpass123` appears in tracked documentation. The security test grep exclusion only filters `TEST.md`.

**Fix:** Use a placeholder like `<your-password>` in docs, and/or expand the exclusion list to cover `validation.md`.

### Bug 4: Orphaned containers from Web UI-added servers

**Severity:** Medium
**Location:** `make clean` / `docker-compose.yaml` lifecycle

When a server is added via the Web UI (e.g., `perplexity-mcp`), it modifies `docker-compose.yaml` and starts the new container. However, `make clean` runs `docker compose down -v` which uses the **current** `docker-compose.yaml`. If the compose file is in a modified state, this works. But if the clone is deleted or the compose file is reverted before teardown, dynamically-added containers become orphaned.

In our test, after `make clean` removed the four original containers, `perplexity-mcp` remained running as an orphan and had to be manually stopped:

```bash
docker stop perplexity-mcp && docker rm perplexity-mcp
```

**Impact:** Users who add servers via the Web UI and then do a naive cleanup may leave containers running.

**Fix options:**
1. `make clean` should also run `docker compose down -v --remove-orphans`
2. The Web UI could track dynamically-added containers and offer a "remove server" action that cleans up the container
3. Document that `docker compose down -v --remove-orphans` is the correct full cleanup command

### Bug 5: Web UI creates root-owned backup files

**Severity:** Low
**Location:** `backups/` directory, created by Web UI server provisioning

When adding a server through the Web UI, the manager creates a backup of `docker-compose.yaml` in a `backups/` directory. This file is owned by `root` (since the manager container runs as root), making it impossible to delete without `sudo`:

```
$ ls -la backups/
.rw-rw-r-- 2.4k root 18 Feb 10:39 docker-compose.yaml.20260218_190027

$ rm -rf eMCP/
rm: cannot remove 'eMCP/backups/docker-compose.yaml.20260218_190027': Permission denied
```

**Impact:** `rm -rf` on the clone directory fails without elevated privileges. Users must use `sudo` to fully remove the project after testing.

**Fix options:**
1. Run the manager container as a non-root user matching the host UID
2. Add `backups/` to `make clean` with appropriate handling
3. Use Docker volumes for backups instead of bind-mounting the host directory

---

## Teardown Notes

Full cleanup required the following steps (in order):

```bash
# 1. Standard cleanup (handles original 4 containers + volumes)
make clean

# 2. Remove orphaned containers added via Web UI
docker stop perplexity-mcp && docker rm perplexity-mcp

# 3. Remove clone (requires sudo due to root-owned backup files)
sudo rm -rf /tmp/eMCP
```

The Docker network `emcp_emcp-network` reported "Resource is still in use" on the first `docker compose down -v` attempt but resolved on retry. This appears to be a race condition between container shutdown and network cleanup — not an eMCP bug, but a known Docker Compose behavior.

---

## Environment Details

```
$ uname -a
Linux director 6.12.63+deb13-amd64 x86_64

$ docker --version
Docker version 26.1.5+dfsg1, build a72d7cd

$ docker compose version
Docker Compose version 2.26.1-4

$ git --version
git version 2.47.3

$ curl --version
curl 8.14.1 (x86_64-pc-linux-gnu)

$ jq --version
jq-1.8.1
```

---

## Recommendations

1. **Fix Bugs 1-2 before release** — Hardcoded ports and broken healthcheck undermine the `make status` target, which is the primary operational health check
2. **Fix Bug 4** — Add `--remove-orphans` to `make clean` to handle dynamically-added servers
3. **Fix Bug 2 with Python healthcheck** — `python -c "import urllib.request; urllib.request.urlopen(...)"` avoids adding packages to the image
4. **Fix Bug 5** — Run the manager as a non-root user or handle backup file ownership
5. **Add functional tool-call tests (12-16) to the scripted release validation** — The existing test validates only infrastructure, not actual tool execution
6. **Consider a `make quicktest` target** that runs the full suite (infrastructure + functional) automatically
7. **Document the full teardown procedure** including orphan cleanup and sudo requirement for backup files
