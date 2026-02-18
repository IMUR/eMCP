#!/usr/bin/env bash
# Symptom: "My AI agent can't see eMCP" or "can't connect"
# Verifies the endpoint is reachable and prints the correct URL.

set -euo pipefail

if [[ -f .env ]]; then source .env 2>/dev/null || true; fi
GATEWAY_PORT="${EMCP_GATEWAY_PORT:-3700}"
MANAGER_PORT="${EMCP_MANAGER_PORT:-3701}"

echo "Checking eMCP connectivity..."
echo ""

# 1. Are containers running?
RUNNING=$(docker compose ps --format '{{.Name}}' 2>/dev/null | wc -l)
if [[ "$RUNNING" -eq 0 ]]; then
    echo "FOUND: No eMCP containers running."
    echo "FIX:   Run: make up"
    exit 1
fi

# 2. Gateway responding locally?
if ! curl -sf "http://localhost:${GATEWAY_PORT}/api/v0/tools" >/dev/null 2>&1; then
    echo "FOUND: Gateway not responding on localhost:${GATEWAY_PORT}."
    echo "FIX:   Run: ./skill/scripts/no-tools.sh"
    exit 1
fi

TOOL_COUNT=$(curl -sf "http://localhost:${GATEWAY_PORT}/api/v0/tools" | jq 'length' 2>/dev/null || echo 0)

# 3. Detect host IPs for remote access
echo "Gateway is healthy with ${TOOL_COUNT} tools."
echo ""
echo "MCP endpoint URLs (use whichever is reachable from your client):"
echo ""
echo "  Local:     http://localhost:${GATEWAY_PORT}/v0/groups/emcp-global/mcp"

# Get non-loopback IPs
if command -v ip &>/dev/null; then
    ip -4 addr show scope global 2>/dev/null | grep -oP 'inet \K[\d.]+' | while read -r addr; do
        echo "  LAN:       http://${addr}:${GATEWAY_PORT}/v0/groups/emcp-global/mcp"
    done
elif command -v ifconfig &>/dev/null; then
    ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | while read -r addr; do
        echo "  LAN:       http://${addr}:${GATEWAY_PORT}/v0/groups/emcp-global/mcp"
    done
fi

# Tailscale?
if command -v tailscale &>/dev/null; then
    TS_IP=$(tailscale ip -4 2>/dev/null || true)
    if [[ -n "$TS_IP" ]]; then
        echo "  Tailscale: http://${TS_IP}:${GATEWAY_PORT}/v0/groups/emcp-global/mcp"
    fi
fi

echo ""
echo "Web UI: http://localhost:${MANAGER_PORT}"
echo ""
echo "To add this endpoint in Claude Code:"
echo "  claude mcp add --transport http emcp http://localhost:${GATEWAY_PORT}/v0/groups/emcp-global/mcp"
