"""Rare durable transitions plus RAM status; no network, credentials or raw logs."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

OBSERVATIONS = {'backend', 'frontend', 'tailscale', 'peer', 'network', 'wan', 'dns'}
ACTIONS = {'backend', 'nginx', 'wifi', 'tailscale', 'peer', 'reboot'}


class HealthEvents:
    def __init__(self, directory=Path('/var/lib/sema-device-health'), runtime=Path('/run/sema-device-health')):
        self.path = directory/'events.db'
        self.status = runtime/'status.json'
        self.previous = None
        self.action_keys = set()
        with self.connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS metadata(source_id TEXT NOT NULL)')
            if not conn.execute('SELECT 1 FROM metadata').fetchone():
                conn.execute('INSERT INTO metadata VALUES(?)', (str(uuid4()),))
            conn.execute('''CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL, kind TEXT NOT NULL, severity TEXT NOT NULL, details TEXT NOT NULL)''')
        os.chmod(self.path, 0o640)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=0.3)
        conn.execute('PRAGMA journal_mode=DELETE')
        conn.execute('PRAGMA synchronous=FULL')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def event(self, kind, severity, details):
        with self.connect() as conn:
            conn.execute('INSERT INTO events(ts,kind,severity,details) VALUES(?,?,?,?)',
                         (time.time(), kind, severity, json.dumps(details, sort_keys=True)))
            conn.execute('DELETE FROM events WHERE id <= (SELECT COALESCE(MAX(id),0)-5000 FROM events)')

    def snapshot(self, observation, mode, paused):
        observation = {k: v for k, v in observation.items() if k in OBSERVATIONS}
        snapshot = dict(version=1, sampled_at=time.time(), observation=observation, mode=mode, paused=bool(paused))
        tmp = self.status.with_suffix('.tmp')
        tmp.write_text(json.dumps(snapshot))
        os.chmod(tmp, 0o640)
        os.replace(tmp, self.status)  # /run is RAM: this is not an SD write.
        if paused:
            return
        faults = sorted(k for k, v in observation.items()
                        if v in ('failed', 'needs_operator', 'local_down', 'upstream') or (k == 'wan' and v is False))
        if faults != self.previous:
            if faults:
                self.event('problem', 'warning', dict(components=faults, mode=mode))
            elif self.previous:
                self.event('recovered', 'info', dict(components=self.previous, mode=mode))
                self.action_keys.clear()
            self.previous = faults

    def action(self, action, outcome, mode):
        if action not in ACTIONS:
            return
        key = (action, outcome, mode)
        if mode == 'observe' and key in self.action_keys:
            return
        self.action_keys.add(key)
        self.event('recovery_action', 'warning' if action == 'reboot' else 'info',
                   dict(action=action, outcome=outcome, mode=mode))


class SafeHealthEvents:
    """Storage errors must never prevent the original recovery/watchdog logic."""
    def __init__(self, report):
        self.report = report
        self.store = None
        try:
            self.store = HealthEvents()
        except (OSError, sqlite3.Error):
            report('health_recorder_unavailable')

    def call(self, name, *args):
        if self.store:
            try:
                getattr(self.store, name)(*args)
            except (OSError, sqlite3.Error):
                self.report('health_recorder_write_failed')
