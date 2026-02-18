#!/usr/bin/env bash
# Collect eMCP diagnostic info for troubleshooting.
# Run from the eMCP project root.

set -euo pipefail

# Load .env if it exists
if [[ -f .env ]]; then
    # shellcheck disable=SC1091
    source .env 2>/dev/null || true
fi

GATEWAY_PORT="${EMCP_GATEWAY_PORT:-8090}"
MANAGER_PORT="${EMCP_MANAGER_PORT:-5010}"

echo "eMCP Diagnostics"
echo "================"
echo ""

# System info
echo "## System"
echo "OS: $(uname -s) $(uname -m)"
echo "Docker: $(docker --version 2>/dev/null || echo 'not found')"
echo "Compose: $(docker compose version 2>/dev/null || echo 'not found')"
echo "jq: $(jq --version 2>/dev/null || echo 'not found')"
echo ""

# Container status
echo "## Containers"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "docker compose not available or not in project directory"
echo ""

# Gateway health
echo "## Gateway (port ${GATEWAY_PORT})"
if curl -sf "http://localhost:${GATEWAY_PORT}/api/v0/tools" >/dev/null 2>&1; then
    TOOL_COUNT=$(curl -sf "http://localhost:${GATEWAY_PORT}/api/v0/tools" | jq 'length' 2>/dev/null || echo "?")
    echo "Status: responding"
    echo "Tools: ${TOOL_COUNT}"
else
    echo "Status: not responding"
fi
echo ""

# Manager health
echo "## Manager (port ${MANAGER_PORT})"
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:${MANAGER_PORT}/" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
    echo "Status: responding (HTTP ${HTTP_CODE})"
else
    echo "Status: not responding (HTTP ${HTTP_CODE})"
fi
echo ""

# Registered servers
echo "## Registered Servers"
docker exec emcp-server /mcpjungle list servers 2>/dev/null || echo "Cannot reach gateway container"
echo ""

# Config files
echo "## Config Files"
for f in configs/*.json; do
    if [[ -f "$f" ]]; then
        name=$(jq -r '.name' "$f" 2>/dev/null || echo "?")
        echo "  ${f} -> ${name}"
    fi
done
echo ""

# Group state
echo "## Active Group"
if [[ -f groups/emcp-global.json ]]; then
    TOOL_COUNT=$(jq '.included_tools | length' groups/emcp-global.json 2>/dev/null || echo "?")
    echo "emcp-global: ${TOOL_COUNT} tools selected"
else
    echo "emcp-global.json not found"
fi
echo ""

# Recent gateway logs
echo "## Recent Gateway Logs (last 10 lines)"
docker compose logs emcp-server --tail 10 --no-log-prefix 2>/dev/null || echo "Cannot read logs"
