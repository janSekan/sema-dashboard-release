#!/usr/bin/python3
"""Transactional device updater. All Git/data operations run as jan, never root.
Code rollback retains the current DB; schema/destructive migrations need a separate plan.
"""
import argparse
from contextlib import closing
import fcntl
import json
import os
import pwd
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from uuid import uuid4

REPO = Path('/home/jan/sema')
STATE = Path('/home/jan/.local/state/sema-update')
GUARD = Path('/usr/local/lib/sema-update/update_manager.py')
PENDING = {'prepared', 'installed', 'testing', 'rolling_back'}
SHA = re.compile(r'^[0-9a-f]{40}$')


class UpdateError(Exception):
    pass


def emit(event, **fields):
    print(json.dumps(dict(event=event, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **fields)), flush=True)


def run(*args, timeout=20):
    try:
        return subprocess.run(args, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise UpdateError('command_unavailable_or_timeout') from None


def ctl(*args, timeout=20):
    return run('sudo', '-n', '/usr/bin/systemctl', *args, timeout=timeout)


def http(path, port):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(f'http://127.0.0.1:{port}{path}', timeout=2) as response:
            if response.status != 200:
                raise ValueError('HTTP status')
            return response.read(262144)
    except urllib.error.HTTPError as exc:
        exc.close()
        raise ValueError('HTTP status') from None


def application_healthy():
    try:
        state = ctl('show', 'sema.service', '-p', 'ActiveState', '--value')
        if state.returncode or state.stdout.strip() != b'active':
            return False
        payload=json.loads(http('/device-api/health', 8000))
        if not isinstance(payload,dict) or payload.get('ok') is not True:
            return False
        page = http('/', 80).decode('utf-8')
        asset = re.search(r'<script\b[^>]*\bsrc=["\'](/assets/[A-Za-z0-9_.-]+\.js)["\']', page)
        if '<html' not in page.lower() or not asset:
            return False
        data = http(asset[1], 80)
        return bool(data) and b'<html' not in data[:512].lower() and b'<!doctype html' not in data[:512].lower()
    except (OSError, ValueError, TypeError, UpdateError):
        return False


def wait_healthy(timeout=90, stable=3):
    deadline = time.monotonic()+timeout
    successes = 0
    while time.monotonic() < deadline:
        successes = successes+1 if application_healthy() else 0
        if successes >= stable:
            return True
        time.sleep(2)
    return False


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(data, out, allow_nan=False)
            out.flush();os.fsync(out.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        Path(name).unlink(missing_ok=True)


def trusted_file(path, data):
    if not path.is_file() or path.is_symlink():return False
    stat=path.stat();parent=path.parent.stat()
    return stat.st_uid==0 and parent.st_uid==0 and not (stat.st_mode | parent.st_mode) & 0o022 and path.read_bytes()==data


def ensure_guard(repo, commit):
    """One-time bounded root install using existing sudo systemctl, no sudo Git."""
    mapping = {'update_manager.py':'scripts/update_manager.py',
               'install.py':'scripts/update-recovery/install.py',
               'sema-update-recovery.service':'scripts/update-recovery/sema-update-recovery.service',
               'sema-update-recovery.timer':'scripts/update-recovery/sema-update-recovery.timer'}
    targets = {'update_manager.py': GUARD,
               'sema-update-recovery.service':Path('/etc/systemd/system/sema-update-recovery.service'),
               'sema-update-recovery.timer':Path('/etc/systemd/system/sema-update-recovery.timer')}
    payload = {}
    for name, relative in mapping.items():
        result = run('git', '-C', str(repo), 'show', f'{commit}:{relative}')
        if result.returncode: raise UpdateError('recovery_bundle_missing')
        payload[name] = result.stdout
    if GUARD.exists() and ctl('is-enabled','--quiet','sema-update-recovery.timer').returncode:
        raise UpdateError('recovery_guard_disabled')
    if all(trusted_file(dest, payload[name]) for name,dest in targets.items()):
        if ctl('is-active', '--quiet', 'sema-update-recovery.timer').returncode == 0:
            return
    unit = 'sema-update-guard-install.service'
    state = ctl('show', unit, '-p', 'LoadState', '--value')
    if state.returncode or state.stdout.strip() not in (b'not-found', b''):
        raise UpdateError('recovery_installer_unavailable')
    stage = Path(tempfile.mkdtemp(prefix='sema-update-guard-', dir='/var/tmp'))
    linked = False
    cleanup = True
    try:
        for name,data in payload.items(): (stage/name).write_bytes(data)
        bridge = stage/unit
        bridge.write_text(f'[Unit]\nDescription=Install SEMA update recovery guard\n[Service]\nType=oneshot\nUser=root\nTimeoutStartSec=60\nExecStart=/usr/bin/python3 {stage}/install.py\n')
        if ctl('link', '--runtime', str(bridge)).returncode: raise UpdateError('recovery_install_link_failed')
        linked = True
        result = ctl('start', unit, timeout=80)
        if result.returncode: raise UpdateError('recovery_install_failed')
        if not all(trusted_file(dest, payload[name]) for name,dest in targets.items()):
            raise UpdateError('recovery_install_verification_failed')
        if ctl('is-active', '--quiet', 'sema-update-recovery.timer').returncode:
            raise UpdateError('recovery_guard_inactive')
    except UpdateError as exc:
        if str(exc) == 'command_unavailable_or_timeout': cleanup = False
        raise
    finally:
        if cleanup:
            if linked:
                ctl('disable', '--runtime', unit);ctl('reset-failed', unit);ctl('daemon-reload')
            shutil.rmtree(stage)


class Manager:
    def __init__(self, repo=REPO, state=STATE):
        self.repo, self.directory = Path(repo), Path(state)
        self.path = self.directory/'transaction.json'

    def git(self, *args):
        result = run('git', '-C', str(self.repo), *args, timeout=60)
        if result.returncode: raise UpdateError('git_operation_failed')
        return result.stdout.decode().strip()

    def load(self):
        if not self.path.exists(): return dict(version=1,phase='idle',failed=[])
        try:
            if self.path.is_symlink() or self.path.stat().st_size > 32768: raise ValueError()
            data = json.loads(self.path.read_text())
            assert data.get('version') == 1 and isinstance(data.get('failed'), list) and len(data['failed'])<=20
            assert data.get('phase') in PENDING | {'idle','complete','rolled_back','rollback_failed'}
            assert all(isinstance(s,str) and SHA.fullmatch(s) for s in data['failed'])
            if data.get('phase') in PENDING | {'rollback_failed'}:
                assert SHA.fullmatch(data['previous']) and SHA.fullmatch(data['target'])
                assert re.fullmatch(r'[0-9a-f]{32}',data['id'])
            return data
        except (OSError, ValueError, TypeError, KeyError, AssertionError):
            raise UpdateError('recovery_state_invalid') from None

    def save(self, data):
        atomic_json(self.path, data)

    def lock(self):
        fd = os.open(self.repo/'.git/sema-update.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd);raise UpdateError('update_busy') from None
        return fd

    def backup(self, tx):
        dest = self.directory/'backups'/tx['id']
        dest.mkdir(mode=0o700, parents=True)
        db = self.repo/'backend/data.db'
        if not db.is_file(): raise UpdateError('database_missing')
        if shutil.disk_usage(self.directory).free < max(64*1024**2, db.stat().st_size*2):
            raise UpdateError('backup_disk_space_low')
        with closing(sqlite3.connect(f'file:{db}?mode=ro',uri=True,timeout=5)) as src, closing(sqlite3.connect(dest/'data.db')) as out:
            src.backup(out)
            if out.execute('PRAGMA quick_check').fetchone()[0] != 'ok':raise UpdateError('database_backup_invalid')
        (dest/'data.db').chmod(0o600)
        env = self.repo/'.env'
        if env.is_file(): shutil.copy2(env,dest/'device.env');(dest/'device.env').chmod(0o600)
        atomic_json(dest/'manifest.json',dict(previous=tx['previous'],target=tx['target']))

    def validate_candidate(self, target):
        names=self.git('ls-tree','-r','--name-only',target).splitlines()
        for name in names:
            path=Path(name)
            if path.name=='.env' or '.venv' in path.parts or 'node_modules' in path.parts or path.suffix in ('.db','.sqlite','.sqlite3') or name.startswith('backend/data.db-'):
                raise UpdateError('release_contains_device_data')

    def stop(self):
        if ctl('stop', 'sema.service').returncode:raise UpdateError('application_stop_failed')
        state=ctl('show','sema.service','-p','ActiveState','--value')
        if state.returncode or state.stdout.strip() not in (b'inactive',b'failed'):
            raise UpdateError('application_did_not_stop')

    def start(self):
        if ctl('start','sema.service').returncode:raise UpdateError('application_start_failed')

    def prune_backups(self, protected):
        root=self.directory/'backups'
        if not root.exists():return
        try:
            paths=[p for p in root.iterdir() if not p.is_symlink() and p.is_dir() and re.fullmatch(r'[0-9a-f]{32}',p.name)]
            paths.sort(key=lambda p:p.stat().st_mtime,reverse=True)
            keep={protected,*[p.name for p in paths if p.name!=protected][:2]}
            for path in paths:
                if path.name not in keep:shutil.rmtree(path)
        except OSError:emit('backup_retention_warning')

    def rollback(self, tx):
        reject=tx.get('candidate_started',False) or tx['phase'] in ('installed','testing','rolling_back')
        tx['attempts']=tx.get('attempts',0)+1
        if tx['attempts']>3:
            tx['phase']='rollback_failed';self.save(tx)
            emit('rollback_retry_limit_manual_attention');return False
        tx['phase']='rolling_back';self.save(tx)
        try:
            self.stop()
            self.git('reset','--hard',tx['previous'])
            self.start()
            if not wait_healthy():raise UpdateError('previous_version_unhealthy')
            if reject:tx['failed']=list(dict.fromkeys([*tx['failed'],tx['target']]))[-20:]
            tx['phase']='rolled_back';tx['last_good']=tx['previous'];self.save(tx)
            self.prune_backups(tx['id'])
            emit('rollback_succeeded',previous=tx['previous'],rejected=tx['target'],database='retained')
            return True
        except Exception:
            tx['phase']='rollback_failed';self.save(tx)
            emit('rollback_failed_manual_attention',previous=tx['previous'],target=tx['target'])
            return False

    def recover(self):
        tx=self.load()
        if tx['phase']=='rollback_failed':raise UpdateError('rollback_needs_manual_attention')
        if tx['phase'] not in PENDING:return False
        emit('interrupted_update_found',previous=tx['previous'],target=tx['target'])
        if not self.rollback(tx):raise UpdateError('rollback_needs_manual_attention')
        return True

    def rollout_watchdog(self, commit):
        # Idempotent: also finish adoption when the old Bash updater fetched this
        # release but could not finish its optional hook after replacing itself.
        hook=self.repo/'scripts/device-watchdog/rollout.py'
        if hook.is_file():
            try:
                result=run('/usr/bin/python3',str(hook),str(self.repo),commit,timeout=180)
                if result.returncode:emit('optional_watchdog_warning')
            except UpdateError:emit('optional_watchdog_warning')

    def update(self, channel, retry_failed=False):
        fd=self.lock()
        try:
            self.recover()
            if not wait_healthy(timeout=15,stable=1):raise UpdateError('current_version_unhealthy')
            previous=self.git('rev-parse','HEAD')
            ensure_guard(self.repo,previous)
            self.git('fetch','origin',f'+refs/heads/{channel}:refs/remotes/origin/{channel}')
            target=self.git('rev-parse','--verify',f'refs/remotes/origin/{channel}^{{commit}}')
            if not SHA.fullmatch(target) or not SHA.fullmatch(previous):raise UpdateError('invalid_commit')
            tx=self.load()
            if target==previous:
                self.rollout_watchdog(target)
                emit('update_unchanged',commit=target);return 0
            if target in tx['failed'] and not retry_failed:
                emit('update_quarantined',commit=target);return 1
            self.git('cat-file','-e',f'{previous}^{{commit}}')
            self.validate_candidate(target)
            if not (self.repo/'.env').is_file() or not (self.repo/'backend/data.db').is_file():
                raise UpdateError('device_data_missing_before_update')
            tx=dict(version=1,phase='prepared',id=uuid4().hex,previous=previous,target=target,
                    failed=tx['failed'],started_at=time.time())
            # Reserve recovery BEFORE stopping/resetting the running version.
            self.save(tx)
            try:
                self.stop();self.backup(tx)
                self.git('reset','--hard',target)
                tx['phase']='installed';tx['candidate_started']=True;self.save(tx)
                self.start()
                tx['phase']='testing';self.save(tx)
                if not wait_healthy():raise UpdateError('candidate_unhealthy')
                tx['phase']='complete';tx['last_good']=target;self.save(tx)
                self.prune_backups(tx['id'])
                emit('update_succeeded',commit=target)
            except (Exception, KeyboardInterrupt) as exc:
                emit('candidate_rejected',reason=str(exc) if isinstance(exc,UpdateError) else 'update_interrupted')
                if not self.rollback(tx):raise UpdateError('rollback_needs_manual_attention')
                return 1
            self.rollout_watchdog(target)
            return 0
        finally: os.close(fd)


def channel():
    for path in (Path('/etc/sema/update-channel'),Path('/home/jan/.config/sema/update-channel')):
        if path.exists():
            value=path.read_text().strip();break
    else:value='main'
    if value not in ('main','testing'):raise UpdateError('invalid_channel')
    return value


def interrupted(signum, frame):
    raise UpdateError('update_interrupted')


def main():
    parser=argparse.ArgumentParser()
    options=parser.add_mutually_exclusive_group()
    options.add_argument('--recover-only',action='store_true')
    options.add_argument('--retry-failed',action='store_true')
    args=parser.parse_args()
    if os.geteuid()==0 or pwd.getpwuid(os.geteuid()).pw_name!='jan':
        raise SystemExit('Run updater as jan; never sudo Git.')
    manager=Manager()
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGHUP,interrupted)
    try:
        if args.recover_only:
            if manager.load()['phase'] not in PENDING:return 0
            try:fd=manager.lock()
            except UpdateError as exc:
                if str(exc)=='update_busy':return 0
                raise
            try: manager.recover()
            finally:os.close(fd)
            return 0
        return manager.update(channel(),args.retry_failed)
    except (UpdateError,OSError) as exc:
        emit('update_failed',reason=str(exc) if isinstance(exc,UpdateError) else 'local_io_error')
        return 1


if __name__=='__main__':raise SystemExit(main())
