#!/usr/bin/python3
"""Device-only recovery. No pump requests, tokens, shell commands or external packages."""
import argparse
import concurrent.futures
import fcntl
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import time
import urllib.request

CONFIG = Path('/etc/sema-device-watchdog.json')
STATE = Path('/var/lib/sema-device-watchdog/recovery.json')
DAEMON_LOCK = Path('/run/sema-device-watchdog/daemon.lock')
UPDATE_LOCK = Path('/home/jan/sema/.git/sema-update.lock')
WIFI_LOCK = Path('/tmp/sema-wifi-watch.lock')
DEFAULT = dict(interval=30, startup_grace=300, repair_after=90, reboot_after=300,
               action_cooldown=600, reboot_cooldown=10800, mode='observe')


def command(*args, timeout=5):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                           env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C'})
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 124, ''


def emit(event, **fields):
    print(json.dumps(dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                          event=event, **fields), sort_keys=True), flush=True)


def http(path, port):
    # Explicitly ignore proxy environment; never follow a redirect off the device.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(f'http://127.0.0.1:{port}{path}', timeout=3) as r:
        if r.status != 200:
            raise ValueError('HTTP status')
        return r.read(262144)


def valid_asset(data):
    return bool(data) and b'<html' not in data[:512].lower() and b'<!doctype html' not in data[:512].lower()


def dashboard():
    result = {}
    try:
        result['backend'] = 'ok' if json.loads(http('/device-api/health', 8000)).get('ok') is True else 'failed'
    except Exception:
        result['backend'] = 'failed'
    try:
        html = http('/', 80).decode('utf-8')
        asset = re.search(r'<script\b[^>]*\bsrc=[\"\'](/assets/[A-Za-z0-9_.-]+\.js)[\"\']', html)
        result['frontend'] = 'ok' if '<html' in html.lower() and asset and valid_asset(http(asset[1], 80)) else 'failed'
    except Exception:
        result['frontend'] = 'failed'
    return result


def wan():
    for host in ('1.1.1.1', '8.8.8.8'):
        try:
            with socket.create_connection((host, 443), timeout=2):
                return True
        except OSError:
            pass
    return False


def network():
    rc, raw = command('ip', '-j', '-4', 'route', 'show', 'default')
    try:
        routes = json.loads(raw) if rc == 0 else None
    except ValueError:
        routes = None
    rc, active = command('nmcli', '-t', '-f', 'NAME,DEVICE', 'connection', 'show', '--active')
    if rc:
        return dict(network='unknown', wan=wan())
    if any(line == 'sema-ap:wlan0' for line in active.splitlines()):
        return dict(network='setup', wan=False)
    # Pump eth0 is never an Internet uplink and must never be reset here.
    uplink = routes is not None and any(r.get('dev') not in ('eth0', 'tailscale0', 'lo', None) for r in routes)
    outside = wan()
    state = 'ok' if outside else ('upstream' if uplink else 'local_down')
    if routes is None:
        state = 'unknown'
    rc, _ = command('getent', 'ahostsv4', 'controlplane.tailscale.com', timeout=3)
    return dict(network=state, wan=outside, dns='ok' if rc == 0 else 'failed')


def tailscale():
    rc, raw = command('tailscale', 'status', '--json')
    try:
        status = json.loads(raw) if rc == 0 else {}
        if status.get('BackendState') in ('NeedsLogin', 'NeedsMachineAuth', 'Stopped'):
            return dict(tailscale='needs_operator', peer='unknown')
        healthy = status.get('BackendState') == 'Running' and status.get('Self', {}).get('Online') is True
        peers = [p for p in (status.get('Peer') or {}).values() if p.get('Online')]
        peer_state = 'unknown'
        for p in peers[:2]:
            for addr in p.get('TailscaleIPs', [])[:1]:
                ipaddress.ip_address(addr)
                rc, _ = command('tailscale', 'ping', '--timeout=2s', '--c=1', addr, timeout=4)
                peer_state = 'ok' if rc == 0 else 'failed'
                if rc == 0:
                    return dict(tailscale='ok' if healthy else 'failed', peer='ok')
        return dict(tailscale='ok' if healthy else 'failed', peer=peer_state)
    except (ValueError, TypeError, AttributeError):
        return dict(tailscale='failed', peer='unknown')


def probes():
    # Bounded independent probes keep one slow service from hiding the others.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(fn) for fn in (dashboard, network, tailscale)]
        result = {}
        for future in futures:
            result.update(future.result())
        return result


class Policy:
    def __init__(self, config):
        self.c = config
        self.since = {}
        self.actions = {}

    def evaluate(self, observation, now, paused=False):
        if paused or now < self.c['startup_grace']:
            self.since.clear()
            return []
        faults = dict(backend=observation['backend'] == 'failed',
                      nginx=observation['frontend'] == 'failed' and observation['backend'] == 'ok',
                      wifi=observation['network'] == 'local_down',
                      tailscale=observation['wan'] and observation['tailscale'] == 'failed',
                      peer=observation['wan'] and observation['tailscale'] == 'ok' and observation['peer'] == 'failed')
        for name, failed in faults.items():
            if failed:
                self.since.setdefault(name, now)
            else:
                self.since.pop(name, None)
                if name == 'peer':
                    self.actions.pop('peer', None)
        result = []
        for name, start in self.since.items():
            if name == 'peer' and name in self.actions:
                continue
            if now - start >= self.c['repair_after'] and now - self.actions.get(name, -1e12) >= self.c['action_cooldown']:
                result.append(name)
        # Peer refusal alone may be ACL/offline/remote service: never reboot for it.
        if any(name != 'peer' and now - start >= self.c['reboot_after'] for name, start in self.since.items()):
            result.append('reboot')
        return result


def updating():
    rc, state = command('systemctl', 'show', 'sema-update.service', '-p', 'ActiveState', '--value')
    return rc != 0 or state.strip() in ('active', 'activating', 'deactivating', 'reloading')


def setup_active():
    try:
        return time.time() - Path('/tmp/sema-wifi-setup-active').stat().st_mtime < 300
    except FileNotFoundError:
        return False


def lock(path):
    # Never create root-owned locks in application checkout; reject symlinks.
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError('Not a regular lock file')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except Exception:
        os.close(fd)
        raise


def reserve_reboot(path, wall):
    # Fail closed when NTP is not synchronized or persisted budget is unreadable.
    rc, sync = command('timedatectl', 'show', '-p', 'NTPSynchronized', '--value')
    if rc or sync.strip() != 'yes':
        return False
    try:
        previous = json.loads(path.read_text())
        if type(previous['until']) not in (float, int) or not math.isfinite(previous['until']):
            return False
        if wall < previous['until']:
            return False
    except FileNotFoundError:
        pass
    except (OSError, ValueError, KeyError, TypeError):
        return False
    try:
        tmp = path.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            os.chmod(tmp, 0o600)
            json.dump(dict(until=wall + 10800, reserved_at=wall), f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return True
    except OSError:
        return False


def diagnostic():
    # Fixed, non-secret fields only. Never dump env, NM profiles or full TS JSON.
    rc, units = command('systemctl', 'show', 'sema.service', 'nginx.service',
                        'tailscaled.service', 'NetworkManager.service',
                        '-p', 'Id,ActiveState,SubState,Result,NRestarts')
    try:
        memory = [s for s in Path('/proc/meminfo').read_text().splitlines()
                  if s.startswith(('MemAvailable:', 'SwapFree:'))]
    except OSError:
        memory = []
    emit('diagnostic', units=units.splitlines() if rc == 0 else [], memory=memory)


def recover(name, config):
    if name == 'reboot':
        if not reserve_reboot(STATE, time.time()):
            return 'blocked_budget_or_clock'
        command('journalctl', '--sync', timeout=5)
        rc, _ = command('systemctl', '--no-block', 'reboot')
    elif name in ('tailscale', 'peer'):
        rc, _ = command('systemctl', '--no-block', 'restart', 'tailscaled.service')
    elif name in ('backend', 'nginx'):
        unit = 'sema.service' if name == 'backend' else 'nginx.service'
        rc, _ = command('systemctl', '--no-block', 'restart', unit)
    elif name == 'wifi':
        try:
            fd = lock(WIFI_LOCK)
        except OSError:
            return 'blocked_wifi_lock'
        try:
            # Existing saved profiles only, no deletion/disconnect of eth0 or AP.
            rc, _ = command('nmcli', '--wait', '20', 'device', 'connect', 'wlan0', timeout=23)
        finally:
            os.close(fd)
    else:
        return 'invalid_action'
    return 'requested' if rc == 0 else 'command_failed'


def load_config():
    c = dict(DEFAULT)
    if CONFIG.exists():
        custom = json.loads(CONFIG.read_text())
        if set(custom) - {'mode'}:
            raise ValueError('Only mode is configurable; safety timings are fixed')
        c.update(custom)
    if c['mode'] not in ('observe', 'recover'):
        raise ValueError('mode must be observe or recover')
    return c


def singleton():
    fd = os.open(DAEMON_LOCK, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError('Not a regular daemon lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except Exception:
        os.close(fd)
        raise


def create_health_store():
    from health_events import SafeHealthEvents
    return SafeHealthEvents(emit)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='One read-only probe; no state writes/actions')
    args = parser.parse_args()
    config = load_config()
    if args.check:
        emit('check', observation=probes(), updating=updating())
        return
    daemon_fd = singleton()  # Keep descriptor alive until process exit.
    health_store = create_health_store()
    policy = Policy(config)
    last = None
    heartbeat = 0
    emit('started', mode=config['mode'])
    while True:
        start = time.monotonic()
        observation = probes()
        fd = None
        paused = updating() or setup_active() or observation['network'] == 'setup'
        try:
            fd = lock(UPDATE_LOCK)
        except OSError:
            paused = True
        try:
            health_store.call('snapshot', observation, config['mode'], paused or start < config['startup_grace'])
            actions = policy.evaluate(observation, start, paused)
            snapshot = dict(observation=observation, paused=paused)
            if snapshot != last or start - heartbeat >= 600:
                emit('status', **snapshot)
                last, heartbeat = snapshot, start
            for action in actions:
                # Mark attempted actions even in observe/blocked mode to avoid floods.
                policy.actions[action] = start
                if action == 'reboot' and start - policy.actions.get('reboot_attempt', -1e12) < 600:
                    continue
                policy.actions['reboot_attempt' if action == 'reboot' else action] = start
                diagnostic()
                health_store.call('action', action, 'requested' if config['mode'] == 'recover' else 'observe_only', config['mode'])
                emit('recovery_requested', action=action, mode=config['mode'], observation=observation)
                outcome = recover(action, config) if config['mode'] == 'recover' else 'observe_only'
                health_store.call('action', action, outcome, config['mode'])
                emit('recovery', action=action, observation=observation, outcome=outcome)
        finally:
            if fd is not None:
                os.close(fd)
        time.sleep(max(1, config['interval'] - (time.monotonic() - start)))


if __name__ == '__main__':
    main()
