# AGENTS.md

Guidance for agentic coding assistants working in this repository.

## Development Commands

```bash
docker compose up -d                      # Start all services
docker compose logs -f emcp-server        # Watch gateway logs
docker compose restart emcp-server        # Restart after config changes
curl http://localhost:5010/api/tools      # List available tools
curl http://localhost:5010/api/current    # Current tool selection
```

## Code Style

- **Python**: `snake_case`, type hints, Google-style docstrings
- **Shell**: `set -euo pipefail`, quote variables
- **JSON**: 4-space indent
- **Imports**: stdlib, third-party, local (blank lines between)
- **Errors**: Catch specific exceptions, print to stderr, never expose secrets

## Project Patterns

- Tools format: `{server}__{tool_name}`
- MCPJungle API: `http://localhost:8090/api/v0/tools`
- Group files in `groups/`, default group: `emcp-global`
- Environment variables with `os.getenv("KEY", "default")`
- Docker containers accessed via `docker exec`
- Configs mounted read-only where possible

## Required env vars

`POSTGRES_USER`, `POSTGRES_PASSWORD` (in `.env`)

## When Contributing

1. Add type hints to new functions
2. Include docstrings for public functions
3. Test manually using API endpoints
4. Never commit secrets or API keys
