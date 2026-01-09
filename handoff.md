# eMCP Handoff

**Date:** 2026-01-09
**Status:** Ready for testing

---

## What's Done

- Full directory structure created
- docker-compose.yaml with all 9 MCP servers
- emcp-manager ported from MyCP (Flask web UI)
- Modelfiles for extractor and selector
- Python scripts for extractor and selector (with agentic tool calling)
- All MCP server configs copied
- Documentation (docs/, CLAUDE.md, README.md)

---

## What's Left: Testing

### 1. Start the stack

```bash
cd /media/crtr/fortress/docker/eMCP
docker compose up -d
```

Wait for services to be healthy:
- emcp-db (PostgreSQL)
- emcp-server (MCPJungle gateway)
- emcp-ollama (Ollama)
- emcp-manager (Flask UI)

### 2. Build Ollama models

```bash
docker exec emcp-ollama ollama create emcp-extractor -f /modelfiles/extractor.Modelfile
docker exec emcp-ollama ollama create emcp-selector -f /modelfiles/selector.Modelfile
```

### 3. Run taxonomy extraction

```bash
python tools/extractor/extractor.py -v
```

This fetches tools from MCPJungle API and generates `data/tool_metadata.json`.

### 4. Test selector

```bash
python tools/selector/selector.py /path/to/some/project -v
```

The selector model will:
- Explore the project (list_directory, read_file, run_command)
- Read tool_metadata.json
- Reason about which tools fit
- Output JSON with selected_tools

---

## Architecture Recap

**Two parts only:**

1. **Taxonomy Extraction** - Runs when tool inventory changes
   - Fetches tools from MCPJungle
   - LLM extracts: operations, domain, token_count
   - Outputs: `data/tool_metadata.json`

2. **Tool Selection** - Runs per project
   - Agentic model with tools (read_file, list_directory, run_command, read_tool_metadata)
   - Model explores project, reads metadata, reasons, outputs selection

**Key insight:** The model performs all analysis. No intermediate schemas, no profiler, no hardcoded rules. Modelfile explains the taxonomy schema; metadata file contains the tool inventory.

---

## Files Changed Today

- `tools/extractor/extractor.py` - Fixed API endpoint (`/api/v0/tools`), fixed path resolution
- `tools/selector/selector.py` - Fixed metadata path resolution
- `docker-compose.yaml` - Added all 9 MCP servers, updated Dockerfile paths
- `dockerfiles/` - Moved Dockerfiles here for cleaner root

---

## Potential Issues to Watch

1. **Ollama model context** - If selector runs out of context, may need to bump `num_ctx` in Modelfile
2. **MCPJungle API** - Verify the exact response format matches what extractor expects
3. **Tool calling** - Verify qwen2.5-coder:1.5b supports Ollama's tool calling format
4. **Permissions** - Scripts need to read project directories and metadata file

---

## Environment Variables

Required in `.env`:

```
POSTGRES_PASSWORD=
GITHUB_PAT=
GITEA_API_TOKEN=
GITEA_HOST=
PERPLEXITY_API_KEY=
MAPBOX_PUBLIC_API_KEY=
MAPBOX_DEV_API_KEY=
ELEVENLABS_API_KEY=
HOME_ASSISTANT_ACCESS_TOKEN=
```
