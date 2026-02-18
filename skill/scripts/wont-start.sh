#!/usr/bin/env bash
# Symptom: "make up fails" or "containers won't start"
# Checks every prerequisite and fixes what it can.

set -euo pipefail

echo "Checking why eMCP won't start..."
echo ""

FIXES=0

# 1. Docker installed?
if ! command -v docker &>/dev/null; then
    echo "FOUND: Docker is not installed."
    echo "FIX:   Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 2. Docker running?
if ! docker info &>/dev/null 2>&1; then
    echo "FOUND: Docker daemon is not running."
    echo "FIX:   Start Docker and try again."
    exit 1
fi

# 3. Docker Compose available?
if ! docker compose version &>/dev/null 2>&1; then
    echo "FOUND: Docker Compose is not available."
    echo "FIX:   Install Docker Compose v2: https://docs.docker.com/compose/install/"
    exit 1
fi

# 4. jq installed?
if ! command -v jq &>/dev/null; then
    echo "FOUND: jq is not installed (required for make register)."
    if command -v apt-get &>/dev/null; then
        echo "FIX:   Installing jq..."
        sudo apt-get update -qq && sudo apt-get install -y -qq jq
        ((FIXES++))
    elif command -v brew &>/dev/null; then
        echo "FIX:   Installing jq..."
        brew install jq
        ((FIXES++))
    else
        echo "FIX:   Install jq manually: https://jqlang.github.io/jq/download/"
        exit 1
    fi
fi

# 5. .env exists?
if [[ ! -f .env ]]; then
    echo "FOUND: No .env file."
    echo "FIX:   Creating from .env.example..."
    cp .env.example .env
    ((FIXES++))
fi

# 6. Port conflicts?
if [[ -f .env ]]; then source .env 2>/dev/null || true; fi
GATEWAY_PORT="${EMCP_GATEWAY_PORT:-3700}"
MANAGER_PORT="${EMCP_MANAGER_PORT:-3701}"

check_port() {
    local port="$1" name="$2" var="$3"
    local in_use=false

    if command -v ss &>/dev/null; then
        ss -tlnp 2>/dev/null | grep -q ":${port} " && in_use=true
    elif command -v lsof &>/dev/null; then
        lsof -iTCP:"${port}" -sTCP:LISTEN -P -n &>/dev/null && in_use=true
    fi

    if [[ "$in_use" == "true" ]]; then
        # Check if it's our own container
        if docker compose ps 2>/dev/null | grep -q "${name}"; then
            return 0  # Our container, fine
        fi
        echo "FOUND: Port ${port} (${name}) is already in use by another service."
        # Find a free port nearby
        local try=$((port + 1))
        while [[ $try -lt $((port + 100)) ]]; do
            if command -v ss &>/dev/null; then
                ss -tlnp 2>/dev/null | grep -q ":${try} " || break
            elif command -v lsof &>/dev/null; then
                lsof -iTCP:"${try}" -sTCP:LISTEN -P -n &>/dev/null || break
            else
                break
            fi
            ((try++))
        done
        echo "FIX:   Adding ${var}=${try} to .env"
        echo "${var}=${try}" >> .env
        ((FIXES++))
    fi
}

check_port "$GATEWAY_PORT" "gateway" "EMCP_GATEWAY_PORT"
check_port "$MANAGER_PORT" "manager" "EMCP_MANAGER_PORT"

# 7. docker-compose.yaml exists?
if [[ ! -f docker-compose.yaml ]]; then
    echo "FOUND: No docker-compose.yaml. Are you in the eMCP directory?"
    exit 1
fi

echo ""
if [[ "$FIXES" -gt 0 ]]; then
    echo "Applied ${FIXES} fix(es). Try make up now."
else
    echo "All prerequisites met. If make up still fails, run:"
    echo "  docker compose up -d 2>&1 | tail -20"
    echo "  docker compose logs --tail 20"
fi
