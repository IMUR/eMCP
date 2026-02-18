#!/usr/bin/env bash
# Symptom: "Container shows unhealthy" or "something seems wrong"
# Finds unhealthy containers and restarts them.

set -euo pipefail

if [[ -f .env ]]; then source .env 2>/dev/null || true; fi
GATEWAY_PORT="${EMCP_GATEWAY_PORT:-3700}"

echo "Checking container health..."
echo ""

UNHEALTHY=()
STOPPED=()

# Check each expected container
for CONTAINER in emcp-db emcp-server emcp-manager filesystem-mcp; do
    STATE=$(docker inspect --format='{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "missing")
    HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER" 2>/dev/null || echo "unknown")

    if [[ "$STATE" == "missing" ]]; then
        echo "  ${CONTAINER}: not found"
        STOPPED+=("$CONTAINER")
    elif [[ "$STATE" != "running" ]]; then
        echo "  ${CONTAINER}: ${STATE}"
        STOPPED+=("$CONTAINER")
    elif [[ "$HEALTH" == "unhealthy" ]]; then
        echo "  ${CONTAINER}: running but unhealthy"
        UNHEALTHY+=("$CONTAINER")
    else
        echo "  ${CONTAINER}: ok"
    fi
done

echo ""

# Fix stopped containers
if [[ ${#STOPPED[@]} -gt 0 ]]; then
    echo "FOUND: ${#STOPPED[@]} container(s) not running: ${STOPPED[*]}"
    echo "FIX:   Starting all services..."
    make up
    exit 0
fi

# Fix unhealthy containers
if [[ ${#UNHEALTHY[@]} -gt 0 ]]; then
    for CONTAINER in "${UNHEALTHY[@]}"; do
        # Special case: emcp-manager healthcheck is cosmetic
        if [[ "$CONTAINER" == "emcp-manager" ]]; then
            MANAGER_PORT="${EMCP_MANAGER_PORT:-3701}"
            if curl -sf "http://localhost:${MANAGER_PORT}/api/current" >/dev/null 2>&1; then
                echo "NOTE: emcp-manager reports unhealthy but API responds fine."
                echo "      This is a known cosmetic issue with the healthcheck."
                continue
            fi
        fi

        echo "FIX:   Restarting ${CONTAINER}..."
        docker restart "$CONTAINER"
    done

    # Wait and re-register if gateway was restarted
    if printf '%s\n' "${UNHEALTHY[@]}" | grep -q emcp-server; then
        echo "       Waiting for gateway..."
        until curl -sf "http://localhost:${GATEWAY_PORT}/api/v0/tools" >/dev/null 2>&1; do sleep 2; done
        echo "FIX:   Re-registering configs..."
        make register
    fi

    exit 0
fi

echo "All containers healthy."
