# Security Policy

## Reporting Vulnerabilities

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Use GitHub's private vulnerability reporting feature
3. Include steps to reproduce
4. Allow reasonable time for a fix before disclosure

## Security Design

eMCP handles API keys and tokens for connected MCP servers:

- Secrets are stored in `.env` files (never committed to git)
- `.env` files are created with `600` permissions (owner read/write only)
- Secrets are never logged or exposed in API responses
- `.gitignore` excludes all secret-containing files

## Deployment Best Practices

- Never commit `.env` files to version control
- Restrict Docker socket access to trusted containers only
- Use a reverse proxy with TLS for external access
