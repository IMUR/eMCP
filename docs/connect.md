# Connect to eMCP

eMCP exposes a standard MCP Streamable HTTP endpoint. Any MCP-compatible client can connect to it.

## Endpoint

```
http://<host>:<port>/v0/groups/emcp-global/mcp
```

Default: `http://localhost:3700/v0/groups/emcp-global/mcp`

If you configured a custom gateway port in `.env`, replace `3700` with your `EMCP_GATEWAY_PORT` value. For remote access, replace `localhost` with the host's IP or Tailscale address.

---

## Claude Code

```bash
claude mcp add --transport http emcp http://localhost:3700/v0/groups/emcp-global/mcp
```

To remove:

```bash
claude mcp remove emcp
```

## Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "emcp": {
      "url": "http://localhost:3700/v0/groups/emcp-global/mcp"
    }
  }
}
```

Restart Claude Desktop after editing.

## Cursor

Add to `.cursor/mcp.json` in your project root or `~/.cursor/mcp.json` globally:

```json
{
  "mcpServers": {
    "emcp": {
      "url": "http://localhost:3700/v0/groups/emcp-global/mcp"
    }
  }
}
```

## Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "emcp": {
      "serverUrl": "http://localhost:3700/v0/groups/emcp-global/mcp"
    }
  }
}
```

## VS Code (GitHub Copilot)

Add to `.vscode/mcp.json` in your project:

```json
{
  "servers": {
    "emcp": {
      "type": "http",
      "url": "http://localhost:3700/v0/groups/emcp-global/mcp"
    }
  }
}
```

Or add to `settings.json`:

```json
{
  "github.copilot.chat.mcp.servers": {
    "emcp": {
      "type": "http",
      "url": "http://localhost:3700/v0/groups/emcp-global/mcp"
    }
  }
}
```

## Gemini CLI

```bash
gemini mcp add --transport http emcp http://localhost:3700/v0/groups/emcp-global/mcp
```

## OpenCode

Add to `~/.config/opencode/config.json`:

```json
{
  "mcpServers": {
    "emcp": {
      "type": "http",
      "url": "http://localhost:3700/v0/groups/emcp-global/mcp"
    }
  }
}
```

## Codex CLI

Add to `~/.codex/config.json`:

```json
{
  "mcpServers": {
    "emcp": {
      "url": "http://localhost:3700/v0/groups/emcp-global/mcp"
    }
  }
}
```

## Any MCP Client

eMCP uses MCP Streamable HTTP transport. Any client that supports this transport can connect by pointing to the endpoint URL. The protocol follows the [MCP specification](https://modelcontextprotocol.io/).

### Remote Access

For agents running on a different machine:

- **LAN**: Use the host's local IP (e.g., `http://192.168.1.100:3700/v0/groups/emcp-global/mcp`)
- **Tailscale/VPN**: Use the Tailscale IP (e.g., `http://100.64.0.2:3700/v0/groups/emcp-global/mcp`)
- **Internet**: Put a reverse proxy with TLS in front of the gateway

Run `./skill/scripts/cant-connect.sh` to print all reachable URLs for your host.
