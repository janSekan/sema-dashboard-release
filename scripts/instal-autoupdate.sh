#!/bin/bash
set -e

echo "=== Installing SEMA auto-update ==="

echo "Updating update.sh..."
cat > /home/jan/sema/scripts/update.sh <<'EOF'
#!/bin/bash
set -e

cd /home/jan/sema

echo "Fetching latest release..."
git fetch origin

echo "Resetting to origin/main..."
git reset --hard origin/main

echo "Restarting SEMA service..."
sudo systemctl restart sema

echo "Status:"
sudo systemctl status sema --no-pager
EOF

chmod +x /home/jan/sema/scripts/update.sh

echo "Creating sema-update.service..."
sudo tee /etc/systemd/system/sema-update.service > /dev/null <<'EOF'
[Unit]
Description=SEMA Auto Update
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
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