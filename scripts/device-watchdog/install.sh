#!/bin/bash
# Root installation; automatic release mode is observe-only for new devices.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run explicitly with sudo on an authorized SEMA device.' >&2; exit 1; }
case ${1:---observe} in
 --observe) mode=observe ;;
 --recover) mode=recover ;;
 --auto-observe) mode=auto ;;
 *) echo 'Usage: install.sh [--observe|--recover|--auto-observe]' >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || exit 2
here=$(cd -- "$(dirname -- "$0")" && pwd)
if [[ $mode == auto ]]; then
 decision=$(python3 "$here/auto_policy.py" "$here")
 case "$decision" in
  skip_*) echo "DEVICE_WATCHDOG_AUTO $decision"; exit 0 ;;
  observe|recover) mode=$decision ;;
  *) echo 'Invalid automatic installation decision' >&2; exit 1 ;;
 esac
fi
for binary in python3 systemctl systemd-analyze nmcli tailscale ip flock timedatectl getent runuser journalctl find; do
 command -v "$binary" >/dev/null || { echo "Missing dependency: $binary" >&2; exit 1; }
done
[[ -d /home/jan/sema/.git ]] || { echo 'SEMA runtime checkout missing' >&2; exit 1; }
# Validate files before modifying system configuration.
python3 - "$here" <<'PY'
import ast, sys
from pathlib import Path
for name in ('watchdog.py', 'health_events.py'):
    ast.parse((Path(sys.argv[1])/name).read_text())
PY
systemd-analyze verify "$here/sema-device-watchdog.service"
backup=$(mktemp -d /var/backups/sema-device-watchdog-XXXXXXXX)
chmod 700 "$backup"
files=(/usr/local/lib/sema-device-watchdog/health_events.py /usr/local/lib/sema-device-watchdog/watchdog.py /etc/systemd/system/sema-device-watchdog.service /etc/systemd/journald.conf.d/90-sema-device-watchdog.conf /etc/sema-device-watchdog.json)
for i in "${!files[@]}"; do
 if [[ -e ${files[$i]} || -L ${files[$i]} ]]; then cp -a -- "${files[$i]}" "$backup/$i"; fi
done
was_active=$(systemctl is-active sema-device-watchdog.service || true)
was_enabled=$(systemctl is-enabled sema-device-watchdog.service 2>/dev/null || true)
rollback() {
 trap - ERR
 systemctl stop sema-device-watchdog.service || true
 for i in "${!files[@]}"; do
  rm -f -- "${files[$i]}"
  if [[ -e $backup/$i || -L $backup/$i ]]; then cp -a -- "$backup/$i" "${files[$i]}"; fi
 done
 systemctl daemon-reload
 [[ $was_enabled == enabled ]] || systemctl disable sema-device-watchdog.service 2>/dev/null || true
 systemctl restart systemd-journald.service || true
 if [[ $was_active == active ]]; then systemctl start sema-device-watchdog.service || true; fi
 echo "INSTALL_FAILED, previous configuration restored; backup=$backup" >&2
}
trap rollback ERR
install -d -m 755 /usr/local/lib/sema-device-watchdog /etc/systemd/journald.conf.d
install -d -o root -g jan -m 0750 /var/lib/sema-device-health
install -m 644 "$here/health_events.py" /usr/local/lib/sema-device-watchdog/health_events.py
install -m 644 "$here/watchdog.py" /usr/local/lib/sema-device-watchdog/watchdog.py
install -m 644 "$here/sema-device-watchdog.service" /etc/systemd/system/sema-device-watchdog.service
install -m 644 "$here/journald.conf" /etc/systemd/journald.conf.d/90-sema-device-watchdog.conf
printf '{"mode":"%s"}\n' "$mode" > /etc/sema-device-watchdog.json
chmod 600 /etc/sema-device-watchdog.json
# Match updater and existing Wi-Fi watcher locks; never truncate or replace them.
runuser -u jan -- python3 - <<'PY'
import os, stat
p='/home/jan/sema/.git/sema-update.lock'
f=os.open(p, os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK, 0o600)
assert stat.S_ISREG(os.fstat(f).st_mode)
os.close(f)
PY
python3 - <<'PY'
import os, stat
p='/tmp/sema-wifi-watch.lock'
f=os.open(p, os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK, 0o600)
assert stat.S_ISREG(os.fstat(f).st_mode)
os.close(f)
PY
systemctl restart systemd-journald.service
journalctl --flush
# Capture effective configuration: persistent journal requires the final Storage setting.
systemd-analyze cat-config systemd/journald.conf | python3 -c 'import sys; values=[x.split("=",1)[1].strip() for x in sys.stdin if x.strip().startswith("Storage=")]; assert values and values[-1]=="persistent", "Storage overridden by a later drop-in"'
[[ -n $(find /var/log/journal -name '*.journal' -print -quit) ]]
systemctl daemon-reload
systemctl enable sema-device-watchdog.service
systemctl restart sema-device-watchdog.service
systemctl is-active --quiet sema-device-watchdog.service
trap - ERR
echo "DEVICE_WATCHDOG_OK mode=$mode backup=$backup"
