"""Read-only bridge from root-owned watchdog records to token-protected heartbeat."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import time

DB = Path('/var/lib/sema-device-health/events.db')
STATUS = Path('/run/sema-device-health/status.json')


def export_watchdog(after=0, source=None):
    if not DB.is_file():
        return {'version': 1, 'available': False}
    try:
        with closing(sqlite3.connect(f'file:{DB}?mode=ro', uri=True, timeout=0.3)) as conn:
            conn.row_factory = sqlite3.Row
            source_id = conn.execute('SELECT source_id FROM metadata').fetchone()[0]
            cursor = after if source == source_id else 0
            earliest = conn.execute('SELECT COALESCE(MIN(id),0) FROM events').fetchone()[0]
            rows = conn.execute('SELECT * FROM events WHERE id>? ORDER BY id LIMIT 100', (cursor,)).fetchall()
        try:
            snapshot = json.loads(STATUS.read_text())
            if not isinstance(snapshot, dict):
                snapshot = None
        except (OSError, ValueError):
            snapshot = None
        return dict(version=1, available=True, source_id=source_id, snapshot=snapshot,
                    stale=not snapshot or time.time()-snapshot.get('sampled_at', 0)>120,
                    gap=bool(earliest and cursor < earliest-1),
                    events=[dict(id=row['id'], ts=row['ts'], kind=row['kind'], severity=row['severity'],
                                 details=json.loads(row['details'])) for row in rows])
    except (OSError, sqlite3.Error, ValueError, TypeError):
        return {'version': 1, 'available': False}
