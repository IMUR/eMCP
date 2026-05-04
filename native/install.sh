#!/usr/bin/env bash
#
# eMCP Native installer — Docker-free deployment.
#
# Usage:
#   sudo ./install.sh                      # install with defaults
#   sudo EMCP_USER=alice ./install.sh      # install for a specific service user
#   sudo ./install.sh --no-systemd         # install files but skip systemd setup
#   sudo ./install.sh --uninstall          # remove everything (preserves data dir)
#
# What it does:
#   1. Downloads the pinned mcpjungle binary, verifies SHA, installs to ${EMCP_PREFIX}/bin/.
#   2. Creates ${EMCP_OPT}, ${EMCP_DATA_DIR}, ${EMCP_ETC}.
#   3. Sets up a Python venv in ${EMCP_OPT}/venv (uv preferred, falls back to python -m venv).
#   4. Renders systemd unit templates with your paths and enables the services.
#
# Environment overrides:
#   EMCP_PREFIX     /usr/local                       — where mcpjungle binary goes
#   EMCP_OPT        /opt/emcp-native                 — where the manager source + venv live
#   EMCP_ETC        /etc/emcp-native                 — where env file lives
#   EMCP_DATA_DIR   /var/lib/emcp-native             — where state (groups, configs, db) lives
#   EMCP_USER       (inferred via SUDO_USER, else current user) — service runs as this user
#   MCPJUNGLE_VERSION  0.4.1                         — pinned upstream version
#   EMCP_EXTRA_PATH (empty)                          — extra dirs to prepend to service PATH
#                                                       (e.g. mise shims, nvm, asdf)

set -euo pipefail

# ------------------------------------------------------------------- Defaults
EMCP_PREFIX="${EMCP_PREFIX:-/usr/local}"
EMCP_OPT="${EMCP_OPT:-/opt/emcp-native}"
EMCP_ETC="${EMCP_ETC:-/etc/emcp-native}"
EMCP_DATA_DIR="${EMCP_DATA_DIR:-/var/lib/emcp-native}"
EMCP_USER="${EMCP_USER:-${SUDO_USER:-$(id -un)}}"
MCPJUNGLE_VERSION="${MCPJUNGLE_VERSION:-0.4.1}"
EMCP_EXTRA_PATH="${EMCP_EXTRA_PATH:-}"

DO_SYSTEMD=1
DO_UNINSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-systemd) DO_SYSTEMD=0; shift ;;
    --uninstall) DO_UNINSTALL=1; shift ;;
    --help|-h) sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

# ----------------------------------------------------------- Utility functions
log() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m!! \033[0m%s\n' "$*" >&2; exit 1; }

require_root() {
  if [[ $EUID -ne 0 ]]; then
    err "This script needs root. Run with sudo."
  fi
}

detect_arch() {
  local m; m=$(uname -m)
  case "$m" in
    x86_64|amd64) echo "x86_64" ;;
    aarch64|arm64) echo "arm64" ;;
    *) err "Unsupported arch: $m" ;;
  esac
}

detect_os() {
  local s; s=$(uname -s)
  case "$s" in
    Linux) echo "Linux" ;;
    Darwin) echo "Darwin" ;;
    *) err "Unsupported OS: $s" ;;
  esac
}

# --------------------------------------------------------------- Uninstall path
uninstall() {
  require_root
  log "Stopping and disabling systemd units (if present)..."
  systemctl disable --now emcp-manager.service 2>/dev/null || true
  systemctl disable --now emcp-gateway.service 2>/dev/null || true
  rm -f /etc/systemd/system/emcp-gateway.service /etc/systemd/system/emcp-manager.service
  systemctl daemon-reload || true

  log "Removing binary, app dir, and config..."
  rm -f "${EMCP_PREFIX}/bin/mcpjungle"
  rm -rf "${EMCP_OPT}"
  rm -rf "${EMCP_ETC}"

  log "Preserved: ${EMCP_DATA_DIR}  (delete manually if you want to wipe state)"
  log "Done."
}

[[ $DO_UNINSTALL -eq 1 ]] && { uninstall; exit 0; }

# ------------------------------------------------------------- Install path
require_root

OS=$(detect_os)
ARCH=$(detect_arch)
log "Target: ${OS}_${ARCH}"
log "Service user: ${EMCP_USER}"

if ! id -u "${EMCP_USER}" >/dev/null 2>&1; then
  err "User '${EMCP_USER}' does not exist. Create it first or set EMCP_USER=<existing>."
fi

# 1. Download mcpjungle binary
log "Downloading mcpjungle ${MCPJUNGLE_VERSION}..."
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

TARBALL="mcpjungle_${OS}_${ARCH}.tar.gz"
URL="https://github.com/mcpjungle/MCPJungle/releases/download/${MCPJUNGLE_VERSION}/${TARBALL}"
curl -fsSL -o "${TMP}/${TARBALL}" "$URL" || err "Failed to download $URL"

curl -fsSL -o "${TMP}/checksums.txt" \
  "https://github.com/mcpjungle/MCPJungle/releases/download/${MCPJUNGLE_VERSION}/checksums.txt"

EXPECTED=$(grep "${TARBALL}$" "${TMP}/checksums.txt" | awk '{print $1}')
ACTUAL=$(sha256sum "${TMP}/${TARBALL}" | awk '{print $1}')
[[ "$EXPECTED" == "$ACTUAL" ]] || err "SHA256 mismatch (expected $EXPECTED, got $ACTUAL)"
log "SHA256 verified."

tar -xzf "${TMP}/${TARBALL}" -C "${TMP}"
install -m 0755 -o root -g root "${TMP}/mcpjungle" "${EMCP_PREFIX}/bin/mcpjungle"
log "Installed: ${EMCP_PREFIX}/bin/mcpjungle"

# 2. Provision directories
log "Provisioning directories..."
install -d -m 0755 -o "${EMCP_USER}" -g "${EMCP_USER}" "${EMCP_OPT}"
install -d -m 0755 -o "${EMCP_USER}" -g "${EMCP_USER}" "${EMCP_DATA_DIR}"
install -d -m 0755 -o "${EMCP_USER}" -g "${EMCP_USER}" "${EMCP_DATA_DIR}/groups"
install -d -m 0755 -o "${EMCP_USER}" -g "${EMCP_USER}" "${EMCP_DATA_DIR}/configs"
install -d -m 0755 -o root -g root "${EMCP_ETC}"

# 3. Install manager source
log "Installing manager source..."
SRC="$(cd "$(dirname "$0")" && pwd)"
install -m 0644 -o "${EMCP_USER}" -g "${EMCP_USER}" "${SRC}/app.py" "${EMCP_OPT}/app.py"
install -m 0644 -o "${EMCP_USER}" -g "${EMCP_USER}" "${SRC}/index.html" "${EMCP_OPT}/index.html"
install -m 0644 -o "${EMCP_USER}" -g "${EMCP_USER}" "${SRC}/requirements.txt" "${EMCP_OPT}/requirements.txt"

# 4. Set up Python venv (prefer uv)
log "Setting up Python venv..."
if command -v uv >/dev/null 2>&1; then
  sudo -u "${EMCP_USER}" uv venv "${EMCP_OPT}/venv"
  sudo -u "${EMCP_USER}" "${EMCP_OPT}/venv/bin/python" -m pip install -q --upgrade pip
  sudo -u "${EMCP_USER}" sh -c "VIRTUAL_ENV='${EMCP_OPT}/venv' uv pip install -q -r '${EMCP_OPT}/requirements.txt'"
else
  if ! command -v python3 >/dev/null 2>&1; then
    err "Need python3 (>=3.10) or uv. Install one first."
  fi
  sudo -u "${EMCP_USER}" python3 -m venv "${EMCP_OPT}/venv"
  sudo -u "${EMCP_USER}" "${EMCP_OPT}/venv/bin/pip" install -q --upgrade pip
  sudo -u "${EMCP_USER}" "${EMCP_OPT}/venv/bin/pip" install -q -r "${EMCP_OPT}/requirements.txt"
fi
log "Venv ready: ${EMCP_OPT}/venv"

# 5. Render env file
log "Writing ${EMCP_ETC}/env..."
sed \
  -e "s#__EMCP_DATA_DIR__#${EMCP_DATA_DIR}#g" \
  -e "s#__EMCP_PREFIX__#${EMCP_PREFIX}#g" \
  "${SRC}/env.template" > "${EMCP_ETC}/env"
chmod 0644 "${EMCP_ETC}/env"

# 6. Render systemd units (Linux only)
if [[ "$OS" == "Linux" && $DO_SYSTEMD -eq 1 ]]; then
  log "Rendering systemd units..."
  if [[ -n "$EMCP_EXTRA_PATH" ]]; then
    PATH_LINE="Environment=PATH=${EMCP_EXTRA_PATH}:/usr/local/bin:/usr/bin:/bin"
  else
    PATH_LINE="Environment=PATH=/usr/local/bin:/usr/bin:/bin"
  fi

  for unit in emcp-gateway.service emcp-manager.service; do
    sed \
      -e "s#__EMCP_USER__#${EMCP_USER}#g" \
      -e "s#__EMCP_OPT__#${EMCP_OPT}#g" \
      -e "s#__EMCP_ETC__#${EMCP_ETC}#g" \
      -e "s#__EMCP_DATA_DIR__#${EMCP_DATA_DIR}#g" \
      -e "s#__EMCP_PREFIX__#${EMCP_PREFIX}#g" \
      -e "s#__EMCP_PATH_LINE__#${PATH_LINE}#g" \
      "${SRC}/systemd/${unit}.template" > "/etc/systemd/system/${unit}"
    chmod 0644 "/etc/systemd/system/${unit}"
  done

  systemctl daemon-reload
  log "Enabling and starting services..."
  systemctl enable --now emcp-gateway.service
  sleep 2
  systemctl enable --now emcp-manager.service
  sleep 2

  if systemctl is-active --quiet emcp-gateway.service && \
     systemctl is-active --quiet emcp-manager.service; then
    GATEWAY_PORT=$(grep '^EMCP_GATEWAY_PORT=' "${EMCP_ETC}/env" | cut -d= -f2)
    MANAGER_PORT=$(grep '^EMCP_MANAGER_PORT=' "${EMCP_ETC}/env" | cut -d= -f2)
    log "Both services active."
    log "Manager UI: http://localhost:${MANAGER_PORT}"
    log "Gateway:    http://localhost:${GATEWAY_PORT}"
    log "MCP client endpoint pattern: http://localhost:${GATEWAY_PORT}/v0/groups/<name>/mcp"
  else
    err "Services failed to start. Check: journalctl -u emcp-gateway -u emcp-manager"
  fi
elif [[ "$OS" == "Darwin" ]]; then
  log "macOS detected — systemd skipped. Start manually:"
  log "  ${EMCP_PREFIX}/bin/mcpjungle start --port 3700"
  log "  ${EMCP_OPT}/venv/bin/python ${EMCP_OPT}/app.py"
elif [[ $DO_SYSTEMD -eq 0 ]]; then
  log "--no-systemd requested. Skipped systemd setup."
fi

log "Install complete."
