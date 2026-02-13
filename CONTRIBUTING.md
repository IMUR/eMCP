# Contributing to eMCP

Thanks for your interest in contributing to eMCP.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/eMCP.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Test locally with `docker compose up -d`
6. Commit and push
7. Open a Pull Request

## Development Setup

```bash
cp .env.example .env
# Edit .env with your values
docker compose up -d
```

The web UI is at http://localhost:5010 and the gateway API is at http://localhost:8090.

## Code Style

- **Python**: Use type hints, Google-style docstrings, `snake_case` for functions/variables
- **Shell scripts**: Use `set -euo pipefail`, quote variables
- **JSON configs**: 4-space indent

## Adding MCP Server Examples

To add a new server example:

1. Create `examples/servers/<server-name>.yaml`
2. Include both the docker-compose service block and the MCPJungle config JSON
3. Document required environment variables
4. Update `examples/README.md` table

## Security

- Never commit secrets or API keys
- Use environment variables for all sensitive values
- Report vulnerabilities via the process in [SECURITY.md](SECURITY.md)
