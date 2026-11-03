"""Portal-only, durable and idempotent maintenance requests; fixed systemd commands."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID
import hmac
import logging
import os
import sqlite3
import subprocess
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from data.config.config import DEVICE_ID, PROXY_TOKEN
from services.device_info import get_versions

ACTIONS = ('restart_dashboard', 'reboot', 'update')
TERMINAL = ('success', 'failed', 'unknown')
STORE_PATH = Path.home() / '.config/sema/maintenance.db'
logger = logging.getLogger(__name__)
router = APIRouter(prefix='/device-api/maintenance', tags=['maintenance'])


def authorize(request: Request):
    token = request.headers.get('X-SEMA-Proxy-Token', '')
    if not PROXY_TOKEN or not hmac.compare_digest(token, PROXY_TOKEN):
        raise HTTPException(401, 'Portal authentication required.')
    if (request.headers.get('X-SEMA-Proxy-Role') not in ('admin', 'superadmin')
            or not request.headers.get('X-SEMA-Proxy-User')
            or request.headers.get('Authorization', '').lower().startswith('bearer sema_ha_')):
        raise HTTPException(403, 'Portal administrator required.')


def execute(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def process_id():
    # PID plus kernel start tick avoids accepting PID reuse as the same process.
    return f"{os.getpid()}:{Path('/proc/self/stat').read_text().split(') ', 1)[1].split()[19]}"


def unit_state():
    result = execute('/usr/bin/systemctl', 'show', 'sema-update.service',
                     '--property=ActiveState,Result,ExecMainStartTimestampMonotonic')
    if result.returncode:
        raise RuntimeError('Cannot read update unit')
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def channel():
    paths = [Path('/etc/sema/update-channel'), Path.home()/'.config/sema/update-channel']
    value = next((p.read_text().strip() for p in paths if p.exists()), 'main')
    if value not in ('main', 'testing'):
        raise HTTPException(409, 'Invalid update channel.')
    return value


@contextmanager
def database():
    STORE_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(STORE_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    conn = sqlite3.connect(STORE_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, action TEXT NOT NULL, requested REAL NOT NULL,
        status TEXT NOT NULL, boot TEXT NOT NULL, process TEXT NOT NULL,
        unit_start TEXT, dispatched INTEGER NOT NULL DEFAULT 0, actor TEXT NOT NULL)''')
    conn.commit()
    try:
        yield conn
    finally:
        conn.close()


def reconcile(conn):
    for row in conn.execute("SELECT * FROM jobs WHERE status NOT IN ('success','failed','unknown')").fetchall():
        status = row['status']
        if row['dispatched']:
            if row['action'] == 'reboot' and boot_id() != row['boot']:
                status = 'success'
            elif row['action'] == 'restart_dashboard' and (boot_id() != row['boot'] or process_id() != row['process']):
                status = 'success'
            elif row['action'] == 'update':
                unit = unit_state()
                if (boot_id() == row['boot'] and unit.get('ExecMainStartTimestampMonotonic') != row['unit_start']
                        and unit.get('ActiveState') not in ('active', 'activating', 'deactivating')):
                    status = 'success' if unit.get('Result') == 'success' else 'failed'
        if status not in TERMINAL and time.time()-row['requested'] > 600:
            status = 'unknown'
        conn.execute('UPDATE jobs SET status=? WHERE id=?', (status, row['id']))
    conn.commit()


def public(row):
    return dict(id=row['id'], action=row['action'], status=row['status'],
                requested_at=datetime.fromtimestamp(row['requested'], timezone.utc).isoformat())


class Submit(BaseModel):
    id: UUID
    device_id: str
    action: Literal['restart_dashboard', 'reboot', 'update']


def dispatch(job_id):
    # Called after the 202 response. Never replay a claimed request after a crash.
    time.sleep(1)
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        job = conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not job or job['status'] != 'accepted':
            conn.rollback()
            return
        conn.execute("UPDATE jobs SET status='running',dispatched=1 WHERE id=?", (job_id,))
        conn.commit()
        commands = {
            'restart_dashboard': ('restart', '--no-block', 'sema.service'),
            'reboot': ('reboot', '--no-block'),
            'update': ('start', '--no-block', 'sema-update.service'),
        }
        try:
            result = execute('/usr/bin/sudo', '-n', '/usr/bin/systemctl', *commands[job['action']])
            if result.returncode < 0:
                # systemd stops the entire service cgroup, including our sudo /
                # systemctl child. SIGTERM is expected during a self-restart and
                # does not prove rejection. Keep running until identity confirms it.
                logger.info('Maintenance %s: command interrupted by signal %s; awaiting confirmation',
                            job_id, -result.returncode)
            elif result.returncode > 0:
                logger.warning('Maintenance %s: systemctl rejected request (exit %s)', job_id, result.returncode)
                conn.execute("UPDATE jobs SET status='failed' WHERE id=?", (job_id,))
                conn.commit()
        except (OSError, subprocess.TimeoutExpired):
            logger.warning('Maintenance %s: command result is unknown', job_id)
            # Timeout does not prove failure: the command might have reached systemd.
            conn.execute("UPDATE jobs SET status='unknown' WHERE id=?", (job_id,))
            conn.commit()


@router.get('', dependencies=[Depends(authorize)])
def capabilities(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return dict(device_id=DEVICE_ID, version=1, actions=list(ACTIONS), channel=channel(),
                dashboard_version=get_versions()['dashboard'])


@router.get('/jobs/{job_id}', dependencies=[Depends(authorize)])
def get_job(job_id: UUID, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    with database() as conn:
        reconcile(conn)
        row = conn.execute('SELECT * FROM jobs WHERE id=?', (str(job_id),)).fetchone()
        if not row:
            raise HTTPException(404, 'Unknown maintenance request.')
        return dict(device_id=DEVICE_ID, **public(row))


@router.post('/jobs', status_code=202, dependencies=[Depends(authorize)])
def submit(payload: Submit, request: Request, response: Response, tasks: BackgroundTasks):
    response.headers['Cache-Control'] = 'no-store'
    if payload.device_id != DEVICE_ID:
        raise HTTPException(409, 'Device identity mismatch.')
    with database() as conn:
        reconcile(conn)
        conn.execute('BEGIN IMMEDIATE')
        old = conn.execute('SELECT * FROM jobs WHERE id=?', (str(payload.id),)).fetchone()
        if old:
            if old['action'] != payload.action:
                raise HTTPException(409, 'Request ID already used for another action.')
            return dict(device_id=DEVICE_ID, **public(old))
        if conn.execute("SELECT 1 FROM jobs WHERE status IN ('accepted','running')").fetchone():
            raise HTTPException(409, 'A maintenance request is already running.')
        if conn.execute('SELECT 1 FROM jobs WHERE requested>?', (time.time()-60,)).fetchone():
            raise HTTPException(429, 'Wait at least one minute between maintenance requests.')
        unit = unit_state()
        if unit.get('ActiveState') in ('active', 'activating', 'deactivating'):
            raise HTTPException(409, 'An update is already running; wait before maintenance.')
        if payload.action == 'update':
            channel()  # Validate; never allow the request to change channels.
        conn.execute('INSERT INTO jobs (id,action,requested,status,boot,process,unit_start,actor) VALUES (?,?,?,?,?,?,?,?)',
                     (str(payload.id), payload.action, time.time(), 'accepted', boot_id(), process_id(),
                      unit.get('ExecMainStartTimestampMonotonic'), request.headers['X-SEMA-Proxy-User'][:200]))
        conn.commit()
        row = conn.execute('SELECT * FROM jobs WHERE id=?', (str(payload.id),)).fetchone()
        tasks.add_task(dispatch, str(payload.id))
        return dict(device_id=DEVICE_ID, **public(row))
