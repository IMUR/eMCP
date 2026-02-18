# Protext: eMCP
> Generated: 2026-02-18 | Scope: dev | Tokens: ~450

## Identity
<!-- marker:identity -->
Tool Access Broker for MCP systems. Filters which tools AI agents can access to reduce token costs and cognitive overhead. Docker-based stack with MCPJungle gateway (port 8090), Flask web UI (port 5010), and PostgreSQL.
<!-- /marker:identity -->

## Current State
<!-- marker:state -->
Active: VM test validation in progress | Blocked: Step 4 awaits first CI push | Recent: Steps 1-3, 5 completed
<!-- /marker:state -->

## Hot Context
<!-- marker:hot -->
- Steps 1, 2, 3, 5 done — Step 4 (switch compose to ghcr.io images) blocked on first CI tag push
- VM test validation running from trtr — awaiting results
- `infisical_client.py` may be dead code — check before tagging v1.0.0
- CI workflow builds on main push, publishes only on `v*` tag — confirm OWNER=imur matches GitHub account
- README, CONTRIBUTING, CLAUDE.md all updated to reflect new `make dev` and `jq` dep
<!-- /marker:hot -->

## Scope Signals

- `@ops` → .protext/scopes/ops.md
- `@dev` → .protext/scopes/dev.md
- `@security` → .protext/scopes/security.md
- `@deep:release-prep` → RELEASE_PREP.md
- `@deep:test-validation` → TEST_VALIDATION.md

## Links
<!-- marker:links -->
<!-- No cross-project links yet. Use `protext link` to add. -->
<!-- /marker:links -->

## Handoff
<!-- marker:handoff -->
Last: Steps 1-3, 5 completed; docs updated; VM test initiated from trtr | Next: Await VM test results, then Step 4 + tag | Caution: Do not apply Step 4 until CI has pushed images to ghcr.io
<!-- /marker:handoff -->
