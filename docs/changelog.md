# Changelog

## [1.0.0] - 2026-02-18

### Added
- MCPJungle gateway for aggregating MCP servers
- Web UI and API for tool selection and server management
- Group system for organizing tool access
- Dynamic server provisioning via web UI (Docker socket orchestration)
- Filesystem demo MCP server (no API keys required)
- CI workflow for building and publishing Docker images to ghcr.io
- `make dev` target for local development with locally built images
- `make register` for re-registering all server configs

### Changed

- Makefile `register` and `status` targets use `jq` instead of Python
- `make up` auto-creates `demo-data/` directory and seed file
