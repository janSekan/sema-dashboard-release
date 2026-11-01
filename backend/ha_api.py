"""Dedicated read-only HA API; never calls the pump or writes telemetry."""
import asyncio
import copy
import fcntl
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import secrets
import tempfile
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from auth import require_admin
from data.config.config import DEVICE_ID
from services.device_info import get_versions
from telemetry import collector, utc_now

TEMPERATURES = dict(outdoor_temp='ot', indoor_temp='it', water_temp='wt',
                    heat_temp='ht', equitherm_temp='eqt', exchanger_temp='ext',
                    e_temp='et', f_temp='ft', g_temp='gt')
STATUS_TEMPS = {'ot', 'it', 'wt', 'ht'}
STATES = ('heating', 'dhw', 'defrost', 'fault')
CAPABILITIES = [*(f'temperatures.{k}' for k in TEMPERATURES), 'power_percent',
                *(f'states.{k}' for k in STATES)]


class HAStore:
    """Persistent identity independent of history DB; atomic, serialized writes."""
    def __init__(self, path=None):
        self.path = Path(path or os.getenv('SEMA_HA_STORE_PATH',
                         str(Path.home() / '.config/sema/ha-api.json')))

    def update(self, action=None):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_fd = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(lock_fd, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.path.exists():
                data = json.loads(self.path.read_text())
                uuid.UUID(data['device_uid'])  # Fail closed; never silently replace identity.
            else:
                data = {'device_uid': str(uuid.uuid4()), 'token_hash': None, 'scope': 'read'}
            if action:
                action(data)
            if action or not self.path.exists():
                fd, name = tempfile.mkstemp(dir=self.path.parent, prefix='.ha-api-')
                try:
                    with os.fdopen(fd, 'w') as out:
                        json.dump(data, out)
                        out.flush()
                        os.fsync(out.fileno())
                    os.replace(name, self.path)
                finally:
                    if os.path.exists(name):
                        os.unlink(name)
            return data

    def read(self):
        # API reads do not create files or touch the telemetry DB.
        return json.loads(self.path.read_text())


store = HAStore()
router = APIRouter(prefix='/device-api')


def no_store(response: Response):
    response.headers['Cache-Control'] = 'no-store'


def require_ha(request: Request, response: Response):
    no_store(response)
    data = store.read()
    supplied = request.headers.get('Authorization', '')
    scheme, _, token = supplied.partition(' ')
    digest = hashlib.sha256(token.encode()).hexdigest()
    if (scheme.lower() != 'bearer' or not token or data.get('scope') != 'read'
            or not data.get('token_hash')
            or not hmac.compare_digest(digest, data['token_hash'])):
        raise HTTPException(401, 'Invalid HA token', headers={
            'WWW-Authenticate': 'Bearer', 'Cache-Control': 'no-store'})
    return data


@router.get('/integrations/home-assistant', dependencies=[Depends(require_admin)])
def integration_status(response: Response):
    no_store(response)
    data = store.read()
    return {'enabled': bool(data.get('token_hash')), 'device_uid': data['device_uid'], 'scope': 'read'}


@router.post('/integrations/home-assistant/token', dependencies=[Depends(require_admin)])
async def rotate_token(request: Request, response: Response):
    no_store(response)
    token = 'sema_ha_' + secrets.token_urlsafe(32)
    await asyncio.to_thread(store.update, lambda data: data.update(token_hash=hashlib.sha256(token.encode()).hexdigest(), scope='read'))
    if discovery := getattr(request.app.state, 'ha_discovery', None):
        discovery.notify()
    return {'token': token, 'scope': 'read'}


@router.delete('/integrations/home-assistant/token', dependencies=[Depends(require_admin)])
async def revoke_token(request: Request, response: Response):
    no_store(response)
    await asyncio.to_thread(store.update, lambda data: data.update(token_hash=None))
    if discovery := getattr(request.app.state, 'ha_discovery', None):
        discovery.notify()
    return {'enabled': False}


@router.get('/v1/info')
def info(identity=Depends(require_ha)):
    return {'api_version': 1, 'device_uid': identity['device_uid'],
            'device_id': DEVICE_ID, 'name': f'SEMA {DEVICE_ID or ""}'.strip(),
            'manufacturer': 'SEMA', 'model': 'SEMA',
            'firmware_version': get_versions().get('dashboard'),
            'capabilities': CAPABILITIES, 'recommended_poll_interval_seconds': 30,
            'max_age_seconds': 60}


def finite(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def state_payload(snapshot, uid):
    state = snapshot.get('state', {}) if snapshot else {}
    values = snapshot.get('values', {}) if snapshot else {}
    available = state.get('available.status') if snapshot else None
    available = available if type(available) is bool else None
    temps = {}
    for name, column in TEMPERATURES.items():
        source = 'status' if column in STATUS_TEMPS else 'temperatures'
        temps[name] = finite(values.get(column)) if available is True and state.get(f'available.{source}') is True else None
    flags = {name: state.get(name) if available is True and type(state.get(name)) is bool else None for name in STATES}
    return {'api_version': 1, 'device_uid': uid, 'generated_at': utc_now(),
            'observed_at': snapshot['ts'] if snapshot else None,
            'pump_available': available, 'temperatures': temps,
            'power_percent': finite(values.get('pr')) if available is True else None,
            'states': flags, 'errors': [{'code': 'general_fault', 'message': 'Čerpadlo hlási všeobecnú chybu.'}] if flags['fault'] is True else []}


@router.get('/v1/state')
async def state(identity=Depends(require_ha)):
    async with collector.lock:
        snapshot = copy.deepcopy(collector.last_observed)
    return state_payload(snapshot, identity['device_uid'])
