# eMCP

Tool Access Broker for MCP systems. Filters which tools AI agents can access to reduce context overhead and token costs.

## Quick Start

### Prerequisites

1. Install Infisical CLI:
```bash
# macOS
brew install infisical/brew/infisical

# Linux
curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | sudo -E bash
sudo apt-get update && sudo apt-get install -y infisical

# Verify installation
infisical --version
```

2. Authenticate with Infisical:
```bash
infisical login
```

3. Validate secrets are configured:
```bash
./validate-secrets.sh
```

### Starting eMCP

```bash
# Start all services with automated secret injection
./start-emcp.sh

# Build Ollama models (first time only)
docker exec emcp-ollama ollama create emcp-extractor -f /modelfiles/extractor.Modelfile
docker exec emcp-ollama ollama create emcp-selector -f /modelfiles/selector.Modelfile

# Extract taxonomy (run once, or when tools change)
python tools/extractor/extractor.py -v

# Select tools for a project
python tools/selector/selector.py /path/to/project -v
```

### Stopping eMCP

```bash
./stop-emcp.sh
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

## Secret Management

eMCP uses Infisical for secure secret management. Required secrets:

- `EMCP_GITHUB_SECRET` - GitHub personal access token
- `EMCP_GITEA_SECRET` - Gitea access token
- `GITEA_HOST` - Gitea server URL
- `EMCP_PERPLEXITY_SECRET` - Perplexity API key
- `MAPBOX_PUBLIC_API_KEY` - Mapbox public token
- `MAPBOX_DEV_API_KEY` - Mapbox dev token
- `ELEVENLABS_API_KEY` - ElevenLabs API key
- `HOME_ASSISTANT_ACCESS_TOKEN` - Home Assistant token
- `N8N_MCP_TOKEN` - n8n MCP authentication token
- `POSTGRES_USER` - PostgreSQL database user
- `POSTGRES_PASSWORD` - PostgreSQL database password

### Manual Secret Management (Fallback)

If Infisical is unavailable, you can create a `.env` file manually:

```bash
cp .env.example .env
# Edit .env with your secrets
./start-emcp.sh
```

**Note:** Never commit `.env` files to git. They are automatically excluded via `.gitignore`.
