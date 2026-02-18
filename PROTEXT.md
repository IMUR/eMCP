# Protext: eMCP
> Generated: 2026-02-18 | Scope: dev | Tokens: ~450

## Identity
<!-- marker:identity -->
Tool Access Broker for MCP systems. Filters which tools AI agents can access to reduce token costs and cognitive overhead. Docker-based stack with MCPJungle gateway (port 8090), Flask web UI (port 5010), and PostgreSQL.
<!-- /marker:identity -->

## Current State
<!-- marker:state -->
Active: v1.0.0 release preparation | Blocked: None | Recent: Initial public release committed
<!-- /marker:state -->

## Hot Context
<!-- marker:hot -->
- RELEASE_PREP.md has 7-step checklist — Steps 1-2 are code fixes, Steps 3-7 are CI/publish
- Makefile `register` and `status` targets still use `python3` — must switch to `jq`
- `make up` doesn't auto-create `demo-data/` — new users will hit mount failures
- Dockerfile.gateway has leftover dev comments — needs cleanup before release
- TEST_VALIDATION.md has 12 phases — must pass on clean VM before tagging v1.0.0
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
Last: Initial public release committed to main | Next: Execute RELEASE_PREP.md Step 1 (fix rough edges) | Caution: Do not tag v1.0.0 until TEST_VALIDATION passes on clean VM
<!-- /marker:handoff -->
