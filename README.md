# eMCP

Tool Access Broker for MCP systems. Filters which tools AI agents can access to reduce context overhead and token costs.

## Quick Start

```bash
# Start infrastructure
docker compose up -d

# Build Ollama models
docker exec emcp-ollama ollama create emcp-extractor -f /modelfiles/extractor.Modelfile
docker exec emcp-ollama ollama create emcp-selector -f /modelfiles/selector.Modelfile

# Extract taxonomy (run once, or when tools change)
python tools/extractor/extractor.py

# Select tools for a project
python tools/selector/selector.py /path/to/project
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| emcp-server | 8090 | MCPJungle gateway - MCP endpoint |
| emcp-manager | 5010 | Web UI for manual tool selection |
| emcp-ollama | 11434 | Ollama inference server |
| emcp-db | 5432 | PostgreSQL for MCPJungle |

## How It Works

1. **Taxonomy Extraction** - Classifies tools by operations (research/read/write/etc.) and domain (development.vcs, media.audio, etc.)

2. **Tool Selection** - Agentic model explores your project and selects relevant tools based on context

The model does the analysis. No hardcoded rules.

## Directory Structure

```
eMCP/
├── configs/          # MCP server configurations
├── data/             # Generated tool metadata
├── dockerfiles/      # Container build files
├── docs/             # Architecture documentation
├── emcp-manager/     # Web UI (Flask)
├── groups/           # Tool group definitions
├── modelfiles/       # Ollama model definitions
└── tools/            # Extractor and selector scripts
```

## Documentation

- [Architecture](docs/architecture.md) - System design and components
- [Taxonomy](docs/taxonomy.md) - Tool classification schema

## Environment Variables

Required in `.env`:

```
GITHUB_PAT=
GITEA_API_TOKEN=
GITEA_HOST=
PERPLEXITY_API_KEY=
MAPBOX_PUBLIC_API_KEY=
MAPBOX_DEV_API_KEY=
ELEVENLABS_API_KEY=
HOME_ASSISTANT_ACCESS_TOKEN=
POSTGRES_PASSWORD=
```
