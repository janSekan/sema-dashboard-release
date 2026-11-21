#!/usr/bin/python3
"""Unprivileged optional post-update hook; only existing sudo systemctl permission.

A disposable runtime unit installs a bundle from the exact Git commit. Persistent
root services execute only root-owned installed files. No sudoers edits or sudo Git.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

UNIT = 'sema-device-watchdog-install.service'
BUNDLE = ('health_events.py', 'watchdog.py', 'install.sh', 'journald.conf', 'sema-device-watchdog.service', 'auto_policy.py')
PREFIX = 'scripts/device-watchdog/'


def run(*args, timeout=15):
    return subprocess.run(args, capture_output=True, timeout=timeout, check=False)


def systemctl(*args, timeout=15):
    return run('sudo', '-n', '/usr/bin/systemctl', *args, timeout=timeout)


def materialize(repo, commit, stage):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Expected full Git commit SHA')
    head = run('git', '-C', str(repo), 'rev-parse', 'HEAD')
    if head.returncode or head.stdout.decode().strip() != commit:
        raise ValueError('Release checkout moved; skip watchdog installation')
    for name in BUNDLE:
        # Never execute untracked/modified worktree files as root.
        result = run('git', '-C', str(repo), 'show', f'{commit}:{PREFIX}{name}')
        if result.returncode:
            raise ValueError('Release does not contain complete watchdog bundle')
        (stage/name).write_bytes(result.stdout)
    unit = stage/UNIT
    unit.write_text(f'''[Unit]
Description=One-time SEMA watchdog release installation
[Service]
Type=oneshot
User=root
UMask=0077
TimeoutStartSec=120
ExecStart=/bin/bash {stage}/install.sh --auto-observe
''')
    return unit


def rollout(repo, commit):
    # A persistent foreign unit must never be replaced by this bridge.
    existing = systemctl('show', UNIT, '-p', 'LoadState', '--value')
    if existing.returncode or existing.stdout.strip() not in (b'not-found', b''):
        return 'skipped_installer_unit_present_or_sudo_unavailable'
    stage = Path(tempfile.mkdtemp(prefix='sema-watchdog-', dir='/var/tmp'))
    linked = False
    safe_to_remove = True
    try:
        unit = materialize(repo, commit, stage)
        result = systemctl('link', '--runtime', str(unit))
        if result.returncode:
            return 'warning_link_failed'
        linked = True
        result = systemctl('start', UNIT, timeout=150)
        if result.returncode:
            return 'warning_install_failed'
        return 'install_job_succeeded'
    except subprocess.TimeoutExpired:
        safe_to_remove = False  # Keep files while the root job could still be using them.
        return 'warning_install_timeout_stage_retained'
    except (ValueError, OSError):
        return 'warning_bundle_or_system_error'
    finally:
        if safe_to_remove:
            if linked:
                # Remove only the temporary runtime link created by this invocation.
                systemctl('disable', '--runtime', UNIT)
                systemctl('reset-failed', UNIT)
                systemctl('daemon-reload')
            shutil.rmtree(stage)


def main():
    try:
        repo, commit = sys.argv[1:]
        result = rollout(Path(repo), commit)
    except Exception:
        # Optional infrastructure must not fail a successful dashboard update.
        result = 'warning_optional_watchdog_hook_failed'
    print(f'SEMA_WATCHDOG_ROLLOUT {result}', flush=True)


if __name__ == '__main__':
    main()
