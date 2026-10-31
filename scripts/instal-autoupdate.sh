#!/bin/bash
set -euo pipefail

echo "=== Installing SEMA auto-update ==="

# Use the distributed updater; do not overwrite it with a main-only copy.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ "$SCRIPT_DIR/update.sh" != /home/jan/sema/scripts/update.sh ]]; then
    sudo install -o jan -g jan -m 755 "$SCRIPT_DIR/update.sh" /home/jan/sema/scripts/update.sh
else
    sudo chown jan:jan /home/jan/sema/scripts/update.sh
    sudo chmod 755 /home/jan/sema/scripts/update.sh
fi

# Validate ownership and effective sudo before enabling unattended updates.
# The installer itself needs administrator privileges; the updater does not.
sudo -u jan /bin/bash /home/jan/sema/scripts/update.sh --check

echo "Creating sema-update.service..."
sudo tee /etc/systemd/system/sema-update.service > /dev/null <<'EOF'
[Unit]
Description=SEMA Auto Update
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=jan
WorkingDirectory=/home/jan/sema
ExecStart=/home/jan/sema/scripts/update.sh
EOF

echo "Creating sema-update.timer..."
sudo tee /etc/systemd/system/sema-update.timer > /dev/null <<'EOF'
[Unit]
Description=Run SEMA update after boot

[Timer]
OnBootSec=3min
Unit=sema-update.service

[Install]
WantedBy=timers.target
EOF

echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling timer..."
sudo systemctl enable sema-update.timer
sudo systemctl start sema-update.timer

echo "Timer status:"
systemctl list-timers | grep sema-update || true

echo "=== SEMA auto-update installed ==="