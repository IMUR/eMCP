# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

eMCP is a Tool Access Broker that filters which MCP (Model Context Protocol) tools AI agents can access. The core goal is **resource conservation**: every enabled tool consumes tokens and adds cognitive overhead.

## Commands

### Docker Compose (primary development)
```bash
docker compose up -d              # Start all services
docker compose logs -f emcp-server  # Watch gateway logs
docker compose restart emcp-server  # Restart after config changes
```

### Ollama Model Management
```bash
# Create/update the selector and extractor models
docker exec emcp-ollama ollama create emcp-selector -f /modelfiles/selector.Modelfile
docker exec emcp-ollama ollama create emcp-extractor -f /modelfiles/extractor.Modelfile
```

### Tool Selection (Python)
```bash
# Run taxonomy extraction (populates data/tool_metadata.json)
python tools/extractor/extractor.py -v

# Run agentic tool selection for a project
python tools/selector/selector.py /path/to/project -v
```

### eMCP Manager API
```bash
# Check current tool selection
curl http://localhost:5010/api/current

# List all available tools
curl http://localhost:5010/api/tools
```

## Architecture

### Two-Part System

1. **Taxonomy Extraction** (`tools/extractor/extractor.py`)
   - Fetches tools from MCPJungle API
   - Uses `emcp-extractor` Ollama model to classify each tool
   - Outputs: operations, domain, token_count per tool
   - Result stored in `data/tool_metadata.json`

2. **Tool Selection** (`tools/selector/selector.py`)
   - Agentic model with tools: `read_file`, `list_directory`, `run_command`, `read_tool_metadata`
   - Explores project to understand context (git remote, languages, structure)
   - Reasons from taxonomy + project context
   - Outputs JSON with `selected_tools` and `reasoning`

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| MCPJungle Gateway | `emcp-server` container (port 8090) | Aggregates MCP servers, routes tool calls, manages groups |
| eMCP Manager | `emcp-manager/app.py` (port 5010) | Flask web UI and API for manual tool selection |
| Extractor Model | `modelfiles/extractor.Modelfile` | Ollama model for taxonomy extraction |
| Selector Model | `modelfiles/selector.Modelfile` | Agentic Ollama model for tool selection |

### Tool Taxonomy Schema

```json
{
  "name": "github__create_pull_request",
  "operations": ["write"],
  "domain": "development.vcs",
  "token_count": 150
}
```

**Operations**: research, read, write, generate, transform, control
**Domains**: development.*, infrastructure.*, communication.*, knowledge.*, media.*, physical.*, business.*, identity.*

### Group System

- Groups are JSON files in `groups/` directory
- Default group: `emcp-global`
- Each group specifies `included_tools` array
- MCPJungle exposes groups at `/v0/groups/{group}/mcp`

## Configuration

### MCP Server Configs (`configs/`)
Each MCP server needs a JSON config specifying transport and command:
```json
{
  "name": "github",
  "transport": "stdio",
  "command": "docker",
  "args": ["exec", "-i", "github-mcp", "/server/github-mcp-server", "stdio"]
}
```

### Environment Variables
Required in `.env` or docker-compose environment:
- `GITHUB_PAT` - GitHub personal access token
- `GITEA_API_TOKEN` - Gitea access token
- `GITEA_HOST` - Gitea server URL
- `PERPLEXITY_API_KEY` - Perplexity API key
- `MAPBOX_PUBLIC_API_KEY`, `MAPBOX_DEV_API_KEY` - Mapbox tokens
- `ELEVENLABS_API_KEY` - ElevenLabs API key
- `HOME_ASSISTANT_ACCESS_TOKEN` - Home Assistant token

## Design Principles

- **The model performs analysis** - No pre-packaged inputs or intermediate schemas
- **Derived behavior, not encoded rules** - Selection emerges from taxonomy + context
- **Server prefix indicates platform** - Tool names like `github__`, `gitea__` encode platform
- **Write operations are platform-specific** - `github__write` only for GitHub projects
- **Research operations are portable** - Can be useful across platforms
