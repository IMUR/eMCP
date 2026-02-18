# Scope: Development

## Focus
Release preparation, code fixes, CI/CD setup, and validation for v1.0.0 public release.

## Key Resources
- `Makefile` — Build/run targets (`up`, `down`, `register`, `status`, `clean`)
- `docker-compose.yaml` — Service stack definition
- `dockerfiles/Dockerfile.gateway` — Gateway image build
- `emcp-manager/app.py` — Flask web UI and API (main application code)
- `emcp-manager/index.html` — Frontend SPA
- `configs/filesystem.json` — Demo MCP server config
- `groups/emcp-global.json` — Default tool group

## Current Priorities
1. Execute RELEASE_PREP.md Step 1 — fix `python3` → `jq`, auto-create `demo-data/`
2. Execute RELEASE_PREP.md Step 2 — clean Dockerfile.gateway
3. Add GitHub Actions CI workflow (Step 3)
4. Validate on clean VM with TEST_VALIDATION.md (Step 6)

## Patterns
- MCP servers are registered via `docker exec emcp-server /mcpjungle register -c /configs/<name>.json`
- Tool names are prefixed with server name: `filesystem__read_file`
- Groups are plain JSON files in `groups/` — no database dependency
- Configs in `configs/` are NOT auto-discovered — explicit registration required

## Cautions
- Don't switch docker-compose.yaml to ghcr.io images until CI has pushed them
- The `infisical_client.py` module exists but all Infisical assumptions have been stripped
- `node:22-slim` + `npx` caching can be flaky for filesystem-mcp container
