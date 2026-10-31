#!/bin/bash
set -euo pipefail

# Git must always run as the application owner, including manual sudo invocation
# and older root-run systemd services. Root Git creates refs jan cannot update.
if [[ $(id -u) == 0 ]]; then
    exec runuser -u jan -- /bin/bash "$0" "$@"
fi
if [[ $(id -un) != jan ]]; then
    echo "Run the SEMA updater as jan (or through sema-update.service)." >&2
    exit 1
fi
case "${1:-}" in
    ''|--check) ;;
    *) echo "Usage: $0 [--check]" >&2; exit 2 ;;
esac
if (( $# > 1 )); then
    echo "Usage: $0 [--check]" >&2
    exit 2
fi

# These configuration files are local to the device, never part of a release.
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
if [[ ! -d .git || ! -w .git ]]; then
    echo "SEMA Git metadata is missing or not writable by jan. Update aborted." >&2
    exit 1
fi
# Check metadata AND checkout. Skip dependency trees, never follow symlinks.
BAD_OWNER=$(find . -xdev \( -name .venv -o -name node_modules \) -prune -o ! -user jan -print -quit)
if [[ -n "$BAD_OWNER" ]]; then
    echo "SEMA ownership error: $BAD_OWNER is not owned by jan. Update aborted before fetch/reset." >&2
    echo "An administrator must repair ownership: sudo chown -R jan:jan /home/jan/sema" >&2
    exit 1
fi
# Read-only probe verifies actual passwordless sudo, without restarting anything.
# -l alone also lists commands that still require a password and is insufficient.
if ! sudo -n /usr/bin/systemctl show sema --property=LoadState --value >/dev/null; then
    echo "Passwordless systemctl is unavailable. Check /etc/sudoers.d/sema before updating." >&2
    exit 1
fi
if [[ ${1:-} == --check ]]; then
    echo "SEMA update checks passed (user jan, ownership, passwordless systemctl, channel $CHANNEL). No update performed."
    exit 0
fi

# Prevent timer and manual updates from running at the same time.
exec 9>.git/sema-update.lock
flock -n 9 || { echo "Another SEMA update is running." >&2; exit 1; }

echo "Fetching SEMA channel: $CHANNEL"
git fetch origin "+refs/heads/$CHANNEL:refs/remotes/origin/$CHANNEL"
TARGET=$(git rev-parse --verify "refs/remotes/origin/$CHANNEL^{commit}")
echo "Installing release: $TARGET"
git reset --hard "$TARGET"

sudo -n /usr/bin/systemctl restart sema
sudo -n /usr/bin/systemctl status sema --no-pager
