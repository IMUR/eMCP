#!/bin/bash
# Install eMCP reload systemd units
# Run as root: sudo ./install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing eMCP reload systemd units..."

# Copy unit files
cp "$SCRIPT_DIR/emcp-reload.path" /etc/systemd/system/
cp "$SCRIPT_DIR/emcp-reload.service" /etc/systemd/system/

# Create trigger file with write permissions for container
touch /mnt/ops/docker/eMCP/.reload-trigger
chmod 666 /mnt/ops/docker/eMCP/.reload-trigger

# Reload systemd
systemctl daemon-reload

# Enable and start the path watcher
systemctl enable emcp-reload.path
systemctl start emcp-reload.path

echo "Done. Systemd is now watching for reload triggers."
echo "Test with: touch /mnt/ops/docker/eMCP/.reload-trigger"
