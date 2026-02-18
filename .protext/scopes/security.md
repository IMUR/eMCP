# Scope: Security

## Focus
Secret management, container access controls, and pre-release security validation.

## Key Resources
- `.env` — Secrets file (gitignored, never committed)
- `.env.example` — Template with placeholder values
- `SECURITY.md` — Security policy
- Docker socket mounts in emcp-server and emcp-manager

## Current Priorities
1. Verify no secrets leak into git (TEST_VALIDATION Phase 11)
2. Confirm .env is gitignored and untracked
3. Review Docker socket exposure (required for server provisioning)

## Patterns
- Secrets stored in `.env` only — no hardcoded values in code
- Required env vars: `POSTGRES_USER`, `POSTGRES_PASSWORD`
- Additional API keys added per-server as needed
- Docker socket access is intentional — enables container management features

## Cautions
- Docker socket mount gives containers host-level container control
- Never commit .env files — check with `git status --porcelain .env`
- `emcp-manager` has write access to `configs/`, `groups/`, and compose directory
- Filesystem-mcp mounts demo-data as read-only (`:ro`) — good
