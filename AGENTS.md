# AGENTS.md

This file provides guidance for agentic coding assistants working in the eMCP repository.

---

## Development Commands

### Infrastructure
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f emcp-server

# Restart service after config changes
docker compose restart emcp-server
```

### Testing
```bash
curl http://localhost:5010/api/tools
curl http://localhost:5010/api/current
```

---

## Code Style Guidelines

### File Structure & Imports
- Use `#!/usr/bin/env python3` shebang for executable scripts
- Imports order: standard library, third-party, local (blank lines between groups)
- Use `if __name__ == "__main__":` guard for scripts
- **Functions/variables**: `snake_case`, **Constants**: `UPPER_SNAKE_CASE`, **Private**: `_prefix`

### Type Hints
Use type hints for function parameters and returns:
```python
def fetch_tools_from_mcpjungle() -> list: """Fetch all tools from MCPJungle API."""
def read_file(path: str) -> str: """Read contents of a file."""
```

### Docstrings
Use Google-style docstrings:
```python
def process_tool(tool: dict) -> dict:
    """Process a tool configuration.

    Args:
        tool: Tool dict with name and description

    Returns:
        dict: Processed tool configuration
    """
```

### Error Handling
- Catch specific exceptions: `FileNotFoundError`, `PermissionError`, `json.JSONDecodeError`
- Print errors to stderr: `print(f"Error: {e}", file=sys.stderr)`
- Provide graceful fallbacks when possible
- Use meaningful error messages with context

### JSON Handling
- Use `json.dump(data, f, indent=2)` for readable output
- Ensure parent directories exist before writing: `Path(path).parent.mkdir(parents=True, exist_ok=True)`
- Handle JSON parsing errors with try-except

### Path Handling
- Use `Path(__file__).parent` for script-relative paths
- Use `Path.mkdir(parents=True, exist_ok=True)` for creating directories
- Prefer `Path` objects over string concatenation

### Configuration
- Set constants at module level after imports
- Support environment variables with `os.getenv("KEY", "default")`

### Security
- Validate user inputs before filesystem operations
- Sanitize filenames to prevent path traversal
- Use allowed prefixes for shell commands
- Never expose secrets in error messages or logs

### Docker
- Use `docker exec` to run commands in containers
- Container names: `emcp-server`, `emcp-manager`
- Mount configs read-only where possible: `- ./configs:/configs:ro`

---

## Project-Specific Patterns

### MCPJungle Integration
- Tools format: `{server}__{tool_name}`
- API endpoint: `http://localhost:8090/api/v0/tools`
- Group files stored in `groups/` directory
- Default group: `emcp-global`

### Environment Variables
Required in `.env`: `POSTGRES_USER`, `POSTGRES_PASSWORD`

Optional (per MCP server): See `examples/` directory and `.env.example` for available variables.

---

## When Contributing

1. Add type hints to all new functions
2. Include docstrings for public functions
3. Test manually using API endpoints
4. Never commit secrets or API keys
