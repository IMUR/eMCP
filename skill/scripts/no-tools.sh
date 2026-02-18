#!/usr/bin/env bash
# Symptom: "I see no tools" or "tools disappeared"
# Detects why tools aren't showing and fixes it.

set -euo pipefail

if [[ -f .env ]]; then source .env 2>/dev/null || true; fi
GATEWAY_PORT="${EMCP_GATEWAY_PORT:-3700}"
GATEWAY="http://localhost:${GATEWAY_PORT}"

echo "Checking why tools aren't appearing..."
echo ""

# 1. Is the gateway running?
if ! docker compose ps emcp-server --format '{{.State}}' 2>/dev/null | grep -q running; then
    echo "FOUND: Gateway container is not running."
    echo "FIX:   Starting services..."
    make up
    exit 0
fi

# 2. Is the gateway responding?
if ! curl -sf "${GATEWAY}/api/v0/tools" >/dev/null 2>&1; then
    echo "FOUND: Gateway is running but not responding on port ${GATEWAY_PORT}."
    echo "FIX:   Restarting gateway and re-registering..."
    docker restart emcp-server
    sleep 10
    make register
    exit 0
fi

# 3. Are any tools registered?
TOOL_COUNT=$(curl -sf "${GATEWAY}/api/v0/tools" | jq 'length' 2>/dev/null || echo 0)
if [[ "$TOOL_COUNT" -eq 0 ]]; then
    echo "FOUND: Gateway is healthy but zero tools registered."
    echo "FIX:   Registering all configs..."
    make register
    AFTER=$(curl -sf "${GATEWAY}/api/v0/tools" | jq 'length' 2>/dev/null || echo 0)
    echo "RESULT: ${AFTER} tools now registered."
    exit 0
fi

# 4. Tools registered but not in the group?
GROUP_COUNT=$(jq '.included_tools | length' groups/emcp-global.json 2>/dev/null || echo 0)
if [[ "$GROUP_COUNT" -eq 0 ]]; then
    echo "FOUND: ${TOOL_COUNT} tools registered, but none selected in emcp-global group."
    echo "FIX:   Open the web UI and toggle tools on, or edit groups/emcp-global.json."
    echo "       Web UI: http://localhost:${EMCP_MANAGER_PORT:-3701}"
    exit 0
fi

echo "OK: ${TOOL_COUNT} tools registered, ${GROUP_COUNT} selected in emcp-global."
echo "    If your MCP client still shows no tools, check the endpoint URL:"
echo "    ${GATEWAY}/v0/groups/emcp-global/mcp"
