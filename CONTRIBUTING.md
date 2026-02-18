# Contributing to eMCP

## Getting Started

1. Fork the repository
2. Clone your fork
3. `cp .env.example .env` and edit
4. `docker compose up -d`
5. Create a branch, make changes, open a PR

## Development

- Web UI: http://localhost:5010
- Gateway API: http://localhost:8090

## Code Style

- **Python**: Type hints, Google-style docstrings, `snake_case`
- **Shell**: `set -euo pipefail`, quote variables
- **JSON**: 4-space indent

## Security

- Never commit secrets or API keys
- Use environment variables for all sensitive values
- Report vulnerabilities via [SECURITY.md](SECURITY.md)
