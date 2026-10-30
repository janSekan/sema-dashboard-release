#!/bin/bash
set -euo pipefail

# Older installed services run as root; fetch with the device user's SSH identity.
if [[ $(id -u) == 0 ]]; then
    exec runuser -u jan -- "$0" "$@"
fi

# These configuration files are local to the device, never part of a release.
# System configuration takes precedence; use a fixed home path even under systemd.
CHANNEL_FILE=/etc/sema/update-channel
if [[ ! -e "$CHANNEL_FILE" && ! -L "$CHANNEL_FILE" ]]; then
    CHANNEL_FILE=/home/jan/.config/sema/update-channel
fi
CHANNEL=main
if [[ -f "$CHANNEL_FILE" ]]; then
    CHANNEL=$(cat "$CHANNEL_FILE")
fi
case "$CHANNEL" in
    main|testing) ;;
    *) echo "Invalid update channel; expected main or testing. Update aborted." >&2; exit 1 ;;
esac

cd /home/jan/sema
# Prevent timer and manual updates from running at the same time.
exec 9>.git/sema-update.lock
flock -n 9 || { echo "Another SEMA update is running." >&2; exit 1; }

echo "Fetching SEMA channel: $CHANNEL"
# Fetch exactly this branch even on a clone originally limited to main.
git fetch origin "+refs/heads/$CHANNEL:refs/remotes/origin/$CHANNEL"
TARGET=$(git rev-parse --verify "refs/remotes/origin/$CHANNEL^{commit}")
echo "Installing release: $TARGET"
git reset --hard "$TARGET"

sudo systemctl restart sema
sudo systemctl status sema --no-pager
