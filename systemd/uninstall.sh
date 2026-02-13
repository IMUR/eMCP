#!/bin/bash
# Uninstall eMCP reload systemd units
# Run as root: sudo ./uninstall.sh

set -e

echo "Removing eMCP reload systemd units..."

# Stop and disable the path watcher
systemctl stop emcp-reload.path 2>/dev/null || true
systemctl disable emcp-reload.path 2>/dev/null || true

# Remove unit files
rm -f /etc/systemd/system/emcp-reload.path
rm -f /etc/systemd/system/emcp-reload.service

# Reload systemd
systemctl daemon-reload

echo "Done. Systemd units removed."
