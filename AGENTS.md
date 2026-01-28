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

### Ollama Model Management
```bash
# Create/update models
docker exec emcp-ollama ollama create emcp-selector -f /modelfiles/selector.Modelfile
docker exec emcp-ollama ollama create emcp-extractor -f /modelfiles/extractor.Modelfile
```

### Python Scripts
```bash
# Run taxonomy extraction (populates data/tool_metadata.json)
python tools/extractor/extractor.py -v

# Run agentic tool selection for a project
python tools/selector/selector.py /path/to/project -v
```

### Testing
Currently no formal test suite. Manual testing:
```bash
python tools/extractor/extractor.py -v
python tools/selector/selector.py /path/to/test/project -v
curl http://localhost:5010/api/tools
curl http://localhost:5010/api/current
```

---

## Code Style Guidelines

### File Structure & Imports
- Use `#!/usr/bin/env python3` shebang for executable scripts
- Imports order: standard library → third-party → local (blank lines between groups)
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
def extract_taxonomy(tool: dict) -> dict:
    """Extract taxonomy metadata for a single tool using the extractor model.

    Args:
        tool: Tool dict with name and description

    Returns:
        dict: Tool with operations and domain added
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
- Resolve paths relative to eMCP root using `EMCP_ROOT = Path(__file__).parent.parent.parent`

### Command-Line Interfaces
- Use `argparse` for CLI arguments
- Provide `-v` / `--verbose` flags for debugging
- Include helpful help text: `parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")`

### Function Design
- Keep functions focused and short (< 50 lines ideally)
- Use helper functions to break down complex logic
- Define helper functions before their callers
- Return consistent types (dict for structured data, str for messages)

### Security
- Validate user inputs before filesystem operations
- Sanitize filenames to prevent path traversal
- Use allowed prefixes for shell commands
- Never expose secrets in error messages or logs

### Docker
- Use `docker exec` to run commands in containers
- Container names: `emcp-server`, `emcp-manager`, `emcp-ollama`
- Mount configs read-only where possible: `- ./configs:/configs:ro`

---

## Project-Specific Patterns

### Tool Metadata Schema
```python
{
    "name": "github__create_pull_request",
    "server": "github",
    "description": "...",
    "operations": ["write"],  # research, read, write, generate, transform, control
    "domain": "development.vcs",
    "token_count": 150
}
```

### MCPJungle Integration
- Tools format: `{server}__{tool_name}`
- API endpoint: `http://localhost:8090/api/v0/tools`
- Group files stored in `groups/` directory
- Default group: `emcp-global`

### Environment Variables
Required in `.env`: `GITHUB_PAT`, `GITEA_API_TOKEN`, `GITEA_HOST`, `PERPLEXITY_API_KEY`, `MAPBOX_PUBLIC_API_KEY`, `MAPBOX_DEV_API_KEY`, `ELEVENLABS_API_KEY`, `HOME_ASSISTANT_ACCESS_TOKEN`, `POSTGRES_PASSWORD`

---

## When Contributing

1. Follow patterns in `tools/extractor/extractor.py` and `tools/selector/selector.py`
2. Add type hints to all new functions
3. Include docstrings for public functions
4. Test manually: run scripts with `-v` flag
5. Update documentation in `docs/` if adding new features
6. Never commit secrets or API keys
