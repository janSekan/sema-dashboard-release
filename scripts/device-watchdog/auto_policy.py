"""Read-only automatic-install decision. Never promotes observe to recover."""
import json
from pathlib import Path
import subprocess
import sys

PAYLOAD = {
    'health_events.py': 'usr/local/lib/sema-device-watchdog/health_events.py',
    'watchdog.py': 'usr/local/lib/sema-device-watchdog/watchdog.py',
    'sema-device-watchdog.service': 'etc/systemd/system/sema-device-watchdog.service',
    'journald.conf': 'etc/systemd/journald.conf.d/90-sema-device-watchdog.conf',
}


def decide(source, root=Path('/'), enabled=True, active=True):
    if (root/'etc/sema/device-watchdog-auto-disabled').exists():
        return 'skip_optout'
    config = root/'etc/sema-device-watchdog.json'
    unit = root/PAYLOAD['sema-device-watchdog.service']
    if unit.exists() and not enabled:
        return 'skip_disabled'
    mode = 'observe'
    if config.exists():
        c = json.loads(config.read_text())
        if not isinstance(c, dict) or set(c) != {'mode'} or c['mode'] not in ('observe', 'recover'):
            raise ValueError('Invalid existing watchdog configuration; refusing overwrite')
        mode = c['mode']
    identical = config.exists() and all(
        (root/target).is_file() and (root/target).read_bytes() == (source/name).read_bytes()
        for name, target in PAYLOAD.items())
    if identical and enabled and active:
        return 'skip_current'
    return mode


def main():
    enabled = subprocess.run(['systemctl', 'is-enabled', '--quiet', 'sema-device-watchdog.service'],
                             timeout=10, check=False).returncode == 0
    active = subprocess.run(['systemctl', 'is-active', '--quiet', 'sema-device-watchdog.service'],
                            timeout=10, check=False).returncode == 0
    print(decide(Path(sys.argv[1]), enabled=enabled, active=active))


if __name__ == '__main__':
    main()
