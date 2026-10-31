"""Low-write telemetry: observe in RAM, commit batches, never control the pump."""
import asyncio
import json
import logging
import math
import os
import time
from datetime import datetime, timezone
import requests
import xml.etree.ElementTree as ET

from db import get_conn
from heatpump_client import get_device_url, get_auth

log = logging.getLogger(__name__)


def interval(name, default, minimum):
    try:
        value = float(os.getenv(name, str(default)))
        return value if math.isfinite(value) and value >= minimum else default
    except ValueError:
        return default


POLL_SECONDS = interval('TELEMETRY_POLL_SECONDS', 15, 5)
SAMPLE_SECONDS = interval('TELEMETRY_SAMPLE_SECONDS', 300, 60)
FLUSH_SECONDS = interval('TELEMETRY_FLUSH_SECONDS', 300, 30)
MAX_BUFFERED_EVENTS = 256


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def number(value):
    try:
        result = float(str(value).replace('°C', '').replace('%', '').strip())
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def read_xml(name):
    response = requests.get(get_device_url(name), auth=get_auth(), timeout=5)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    # Keep all XML fields for later decoding; bound size and retain no credentials.
    fields = {}
    for child in list(root)[:128]:
        fields[child.tag[:100]] = ''.join(child.itertext()).strip()[:2000]
    return fields


def fetch_snapshot():
    raw, availability = {}, {}
    for name in ('status', 'temperatures', 'control'):
        try:
            raw[name] = read_xml(name + '.xml')
            availability[name] = True
        except (requests.RequestException, ET.ParseError, ValueError):
            raw[name] = {}
            availability[name] = False
    status = raw['status']
    # Only successfully observed fields are compared. Missing data is never OFF.
    state = {f'{section}.{key}': value for section in ('status', 'control')
             for key, value in raw[section].items()
             if key != 'rtcc' and not key.startswith('tep') and key != 'pwr'}
    state.update({f'available.{key}': value for key, value in availability.items()})
    for flag, key, on in [('defrost', 'st1', '4'), ('fault', 'st1', '5'), ('setback', 'st4', '1'), ('high_tariff', 'st5', '1')]:
        if key in status and status[key] in (('1','2','3','4','5') if key == 'st1' else ('0','1')):
            state[flag] = status[key] == on
    if status.get('st1') in ('1','2','3','4','5') and status.get('st3') in ('0','1','2'):
        state['dhw'] = status['st3'] in ('1', '2')
        power = number(status.get('pwr'))
        if power is not None:
            state['heating'] = status['st1'] == '1' and status['st3'] == '0' and power > 0
    values = {}
    mapping = {'ot': ('status','tep8'), 'it': ('status','tep2'), 'wt': ('status','tep4'), 'ht': ('status','tep3'),
               'ext': ('temperatures','tep1'), 'eqt': ('temperatures','tep9'), 'et': ('temperatures','tep5'),
               'ft': ('temperatures','tep6'), 'gt': ('temperatures','tep7'), 'pr': ('status','pwr')}
    for column, (section, field) in mapping.items():
        values[column] = number(raw[section].get(field))
    return {'ts': utc_now(), 'raw': raw, 'state': state, 'values': values}


def source_id():
    conn = get_conn()
    try:
        return conn.execute("SELECT value FROM app_settings WHERE key='telemetry_source_id'").fetchone()[0]
    finally:
        conn.close()


def export_events(after_id, limit):
    conn = get_conn()
    try:
        conn.row_factory = __import__('sqlite3').Row
        return [dict(row) for row in conn.execute('SELECT * FROM telemetry_events WHERE id>? ORDER BY id LIMIT ?', (after_id, limit))]
    finally:
        conn.close()


def write_batch(samples, events):
    if not samples and not events:
        return
    conn = get_conn()
    try:
        with conn:
            conn.executemany('''INSERT INTO measurements(ts,ot,it,wt,ht,ext,eqt,et,ft,gt,pr,state_json,raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                [(s['ts'], *[s['values'][k] for k in ('ot','it','wt','ht','ext','eqt','et','ft','gt','pr')],
                  json.dumps(s['state'], ensure_ascii=False), json.dumps(s['raw'], ensure_ascii=False)) for s in samples])
            conn.executemany('INSERT INTO telemetry_events(ts,level,code,message,details) VALUES (?,?,?,?,?)',
                             [(e['ts'], e['level'], e['code'], e['message'], json.dumps(e['details'], ensure_ascii=False)) for e in events])
    finally:
        conn.close()


class Collector:
    def __init__(self):
        self.samples, self.events, self.previous = [], [], {}
        self.last_sample = self.last_flush = None
        self.lock = asyncio.Lock()
        self.last_observed = None
        self.last_recorded_ts = None

    def observe(self, snapshot, now):
        state = snapshot['state']
        critical = False
        if not self.previous:
            self.events.append({'ts': snapshot['ts'], 'level': 'info', 'code': 'observation_started',
                                'message': 'Začiatok pozorovania; predchádzajúce trvanie stavov nie je známe.', 'details': {'state': state, 'power_percent':snapshot['values']['pr']}})
            # Persist an already-active fault/outage immediately, including after restart.
            critical = state.get('fault') is True or state.get('available.status') is False
            if critical:
                self.events.append({'ts':snapshot['ts'],'level':'error' if state.get('fault') else 'warning',
                    'code':'initial_fault_or_outage','message':'Chyba alebo výpadok už pri začiatku pozorovania.', 'details':{'state':state,'power_percent':snapshot['values']['pr']}})
        else:
            for key, value in state.items():
                if key not in self.previous or value == self.previous[key]:
                    continue
                is_fault = key == 'fault' or key.startswith('available.') or any(s in key.lower() for s in ('err', 'fault', 'alarm', 'warn'))
                critical |= is_fault
                level = 'error' if key == 'fault' and value is True else 'warning' if key.startswith('available.') and value is False else 'info'
                self.events.append({'ts': snapshot['ts'], 'level': level, 'code': 'state_changed',
                    'message': f'Zmena stavu {key}', 'details': {'field': key, 'before': self.previous[key], 'after': value, 'state': state, 'power_percent':snapshot['values']['pr']}})
        # Preserve the last known state through partial communication outages.
        self.previous.update(state)
        self.last_observed = snapshot
        if self.last_sample is None or now - self.last_sample >= SAMPLE_SECONDS:
            self.samples.append(snapshot)
            self.last_recorded_ts = snapshot['ts']
            self.last_sample = now
        return critical

    async def flush_locked(self):
        # Blocking SQLite commit runs off the ASGI event loop; retain on failure.
        task = asyncio.create_task(asyncio.to_thread(write_batch, self.samples[:], self.events[:]))
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            await task
            self.samples.clear(); self.events.clear()
            raise
        self.samples.clear(); self.events.clear()
        self.last_flush = time.monotonic()

    async def flush(self, include_latest=False):
        async with self.lock:
            if include_latest and self.last_observed and self.last_observed['ts'] != self.last_recorded_ts:
                self.samples.append(self.last_observed)
                self.last_recorded_ts = self.last_observed['ts']
            await self.flush_locked()

    async def run(self):
        try:
            while True:
                started = time.monotonic()
                if len(self.events) + len(self.samples) >= MAX_BUFFERED_EVENTS:
                    try:
                        await self.flush()
                    except Exception:
                        log.error('Telemetry storage unavailable; buffer full, observation paused')
                        await asyncio.sleep(FLUSH_SECONDS)
                        continue
                try:
                    snapshot = await asyncio.to_thread(fetch_snapshot)
                    async with self.lock:
                        critical = self.observe(snapshot, started)
                        due = self.last_flush is None or started - self.last_flush >= FLUSH_SECONDS
                        if critical or due or len(self.events) >= MAX_BUFFERED_EVENTS:
                            await self.flush_locked()
                except Exception:
                    log.exception('Telemetry observation/flush failed')
                await asyncio.sleep(max(1, POLL_SECONDS - (time.monotonic() - started)))
        finally:
            await self.flush()


collector = Collector()
