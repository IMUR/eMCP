#!/bin/bash
# Install eMCP reload systemd units
# Run as root: sudo ./install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EMCP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Installing eMCP reload systemd units..."
echo "  eMCP root: $EMCP_ROOT"

# Render template files with actual path
sed "s|__EMCP_ROOT__|${EMCP_ROOT}|g" "$SCRIPT_DIR/emcp-reload.path.tpl" > /etc/systemd/system/emcp-reload.path
sed "s|__EMCP_ROOT__|${EMCP_ROOT}|g" "$SCRIPT_DIR/emcp-reload.service.tpl" > /etc/systemd/system/emcp-reload.service

# Create trigger file with write permissions for container
touch "${EMCP_ROOT}/.reload-trigger"
chmod 666 "${EMCP_ROOT}/.reload-trigger"

# Reload systemd
systemctl daemon-reload

# Enable and start the path watcher
systemctl enable emcp-reload.path
systemctl start emcp-reload.path

echo "Done. Systemd is now watching for reload triggers."
echo "Test with: touch ${EMCP_ROOT}/.reload-trigger"
