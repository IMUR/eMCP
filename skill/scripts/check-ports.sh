#!/usr/bin/env bash
# Check if eMCP default ports are available, suggest overrides if not.
# Works on Linux and macOS.

set -euo pipefail

# Load .env if it exists
if [[ -f .env ]]; then
    # shellcheck disable=SC1091
    source .env 2>/dev/null || true
fi

GATEWAY_PORT="${EMCP_GATEWAY_PORT:-3700}"
MANAGER_PORT="${EMCP_MANAGER_PORT:-3701}"

check_port() {
    local port="$1"
    local name="$2"
    local var="$3"

    if command -v ss &>/dev/null; then
        if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
            local proc
            proc=$(ss -tlnp 2>/dev/null | grep ":${port} " | head -1)
            echo "CONFLICT: Port ${port} (${name}) is in use"
            echo "  ${proc}"
            echo "  Fix: Add ${var}=<free-port> to .env"
            echo ""
            return 1
        fi
    elif command -v lsof &>/dev/null; then
        if lsof -iTCP:"${port}" -sTCP:LISTEN -P -n &>/dev/null; then
            local proc
            proc=$(lsof -iTCP:"${port}" -sTCP:LISTEN -P -n 2>/dev/null | tail -1)
            echo "CONFLICT: Port ${port} (${name}) is in use"
            echo "  ${proc}"
            echo "  Fix: Add ${var}=<free-port> to .env"
            echo ""
            return 1
        fi
    else
        echo "WARN: Cannot check port ${port} (neither ss nor lsof available)"
        return 0
    fi

    echo "OK: Port ${port} (${name}) is available"
    return 0
}

echo "eMCP Port Check"
echo "==============="
echo ""

CONFLICTS=0

check_port "$GATEWAY_PORT" "gateway" "EMCP_GATEWAY_PORT" || ((CONFLICTS++))
check_port "$MANAGER_PORT" "manager" "EMCP_MANAGER_PORT" || ((CONFLICTS++))

if [[ "$CONFLICTS" -gt 0 ]]; then
    echo "---"
    echo "${CONFLICTS} port conflict(s) found. Add overrides to .env before running make up."
    exit 1
else
    echo ""
    echo "All ports available. Ready for make up."
fi
