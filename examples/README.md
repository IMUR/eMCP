# Adding MCP Servers to eMCP

Each file in `servers/` contains a complete configuration for one MCP server: a docker-compose service block and an MCPJungle config.

## Quick Steps

1. **Copy the compose block** from the server's `.yaml` file into your `docker-compose.yaml` under `services:`
2. **Copy the config JSON** into `configs/<server-name>.json`
3. **Add secrets** to your `.env` file (if the server requires API keys)
4. **Start the service**: `docker compose up -d <service-name>`
5. **Register with MCPJungle**:
   ```bash
   docker exec emcp-server /mcpjungle register -c /configs/<server-name>.json
   ```
6. **Add tools to your group** via the web UI at http://localhost:5010

## Available Examples

| Server | File | Requires Secrets |
|--------|------|-----------------|
| GitHub | `servers/github.yaml` | Yes (`EMCP_GITHUB_SECRET`) |
| Perplexity | `servers/perplexity.yaml` | Yes (`EMCP_PERPLEXITY_SECRET`) |
| Gitea | `servers/gitea.yaml` | Yes (`EMCP_GITEA_SECRET`, `GITEA_HOST`) |
| ElevenLabs | `servers/elevenlabs.yaml` | Yes (`ELEVENLABS_API_KEY`) |
| Mapbox | `servers/mapbox.yaml` | Yes (`MAPBOX_PUBLIC_API_KEY`) |
| Svelte | `servers/svelte.yaml` | No |
| Ollama | `servers/ollama.yaml` | No |

## Using the Web UI

The eMCP Manager at http://localhost:5010 can also auto-detect and provision servers from:
- GitHub repository URLs
- npm package names
- Docker image references

Click "Add MCP Server" in the dashboard to get started.
