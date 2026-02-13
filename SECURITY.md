# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in eMCP, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the maintainers or use GitHub's private vulnerability reporting feature
3. Include steps to reproduce the issue
4. Allow reasonable time for a fix before public disclosure

## Security Design

eMCP handles API keys and tokens for connected MCP servers. The security model:

- Secrets are managed via [Infisical](https://infisical.com) or local `.env` files
- `.env` files are created with `600` permissions (owner read/write only)
- Secrets are never logged or exposed in API responses
- The `.gitignore` excludes all secret-containing files

## Best Practices

When deploying eMCP:

- Use Infisical or another secret manager for production deployments
- Never commit `.env` files to version control
- Restrict Docker socket access to trusted containers only
- Use a reverse proxy with TLS for external access
