from telemetry import collector, source_id, export_events
from services.software_info import software_info
from ha_api import router as ha_router, store as ha_store
from ha_discovery import HADiscovery
from contextlib import suppress

import os
from datetime import datetime, timezone
from data.config.config import DEVICE_ID
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from device_service import get_dashboard_data, get_control_data, fetch_status_xml
from fastapi import FastAPI, Body, HTTPException, Depends, Request, Query
from db import (
    init_db, 
    log_temps, 
    get_last_measurements, 
    get_measurements_after_id,
    get_config, 
    set_config, 
    )
from fastapi.middleware.cors import CORSMiddleware
from services.wifi_service import is_setup_mode, scan_wifi_networks, connect_wifi, touch_wifi_setup_lock
from services.device_info import get_device_info
from core.proxy_auth import (
    require_trusted_access, 
    is_trusted_access, 
    require_portal_sync,
    )
from data.config.config import LAN_ACCESS

from helpers import (
    parse_setback_param,
    parse_settings_params,
    parse_timer_params,
    extract_all_parameter_inputs,
    encode_temp_value,
    encode_heat_value,
    encode_cool_value,
    encode_bivalent_temp,
    encode_percentage_value,
    time_to_timer_slot,
    extract_all_timer_inputs
)
from heatpump_client import (
    fetch_parameters_html,
    fetch_timer_html,
    post_control_cmd,
    post_parameters_form,
    post_timer_form,
)

from data.config.config import CONFIG


import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from datetime import timedelta
from auth import (
    LoginRequest,
    TokenResponse,
    authenticate_user,
    create_access_token,
    get_current_user,
    require_admin,
    require_superadmin,
    require_pump_configurator,
    can_configure_pump,
    oauth2_scheme,
)

from services.heat_curve_service import (
    load_heating_main_temp,
    set_heating_main_temp,
    set_heating_main_temp_reference,
    load_heating_curve_coefficient,
    save_heating_curve_coefficient,
)

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

API_BASE = "/device-api"


class ControlUpdate(BaseModel):
    powerMode: Optional[str] = None
    mode: Optional[str] = None
    season: Optional[str] = None

class SettingsUpdate(BaseModel):
    minIndoorCool: float
    maxIndoorHeat: float
    minWaterTemp: float
    maxWaterTemp: float
    constant: Optional[int] = None
    limitWater: Optional[float] = None
    limitHeat: Optional[float] = None
    limitCool: Optional[float] = None
    coolerTemp: Optional[float] = None
    bivalentTemp: Optional[float] = None
    timeLimitWater: Optional[int] = None
    heatCurve: Optional[Dict[str, float]] = None


BASIC_SETTINGS = {"minIndoorCool", "maxIndoorHeat", "minWaterTemp", "maxWaterTemp"}

class SetbackUpdate(BaseModel):
    heatOffset: float
    coolOffset: float
    schedule: Dict[str, List[dict]] = {}


class HeatingMainTempUpdate(BaseModel):
    value: float = Field(allow_inf_nan=False)


class HeatingCurveCoefficientUpdate(BaseModel):
    value: float = Field(ge=0.1, multiple_of=0.1, allow_inf_nan=False)

class WifiConnectRequest(BaseModel):
    ssid: str
    password: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    software_info()
    init_db()
    await asyncio.to_thread(ha_store.update)
    app.state.ha_discovery = HADiscovery(ha_store)
    from ha_api import configuration_collector
    configuration_task = asyncio.create_task(configuration_collector.run())
    discovery_task = asyncio.create_task(app.state.ha_discovery.run())
    task = asyncio.create_task(collector.run())
    try:
        yield
    finally:
        task.cancel()
        discovery_task.cancel()
        configuration_task.cancel()
        try:
            with suppress(asyncio.CancelledError):
                await discovery_task
        finally:
            try:
                with suppress(asyncio.CancelledError):
                    await configuration_task
            finally:
                with suppress(asyncio.CancelledError):
                    await task

app = FastAPI(lifespan=lifespan)
from maintenance import router as maintenance_router
app.include_router(maintenance_router)
app.include_router(ha_router)


@app.middleware('http')
async def restrict_ha_credentials(request: Request, call_next):
    # Existing LAN endpoints may intentionally allow anonymous trusted access.
    # A dedicated HA credential must never be used for those or provisioning.
    scheme, _, credential = request.headers.get('Authorization', '').partition(' ')
    if (scheme.lower() == 'bearer' and credential.startswith('sema_ha_')
            and request.url.path not in ('/device-api/v1/info', '/device-api/v1/state')):
        return JSONResponse({'detail': 'HA token permits read-only v1 API only'},
                            status_code=403, headers={'Cache-Control': 'no-store'})
    return await call_next(request)


def build_setback_parameters_payload(current_form: dict, data: SetbackUpdate):
    form = current_form.copy()

    form["p20"] = str(encode_heat_value(data.heatOffset))
    form["p21"] = str(encode_cool_value(data.coolOffset))

    return form



def map_control_to_cmd(data: ControlUpdate) -> int:
    if data.powerMode is not None:
        if data.powerMode == "Zapnuté":
            return 2
        if data.powerMode == "Vypnuté":
            return 1

    if data.mode is not None:
        if data.mode == "Kúrenie":
            return 4
        if data.mode == "Chladenie":
            return 3

    if data.season is not None:
        if data.season == "Leto":
            return 6
        if data.season == "Zima":
            return 5

    raise ValueError("Invalid control payload")


origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_ENV = os.getenv("APP_ENV", "development")
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

@app.get("/device-api/access-mode")
def access_mode(request: Request):
    return {
        "trusted": is_trusted_access(request),
        "lan_access": LAN_ACCESS,
    }

@app.get(f"{API_BASE}/system/setup-mode")
def get_setup_mode():
    return {
        "setupMode": is_setup_mode()
    }
    
def require_wifi_access(request: Request, token=Depends(oauth2_scheme)):
    # First-boot provisioning remains possible before connecting to the portal.
    if not is_setup_mode():
        return require_admin(get_current_user(request, token))


@app.get(f"{API_BASE}/wifi/scan")
def wifi_scan(access=Depends(require_wifi_access)):
    touch_wifi_setup_lock()
    return {
        "networks": scan_wifi_networks()
    }

@app.post(f"{API_BASE}/wifi/connect")
def wifi_connect(data: WifiConnectRequest, access=Depends(require_wifi_access)):
    touch_wifi_setup_lock()
    result = connect_wifi(data.ssid, data.password)

    if not result.get("ok"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "WiFi connection failed"),
        )

    return result

@app.get(f"{API_BASE}/device/status")
def device_status():
    return fetch_status_xml()


@app.get("/")
def root():
    if APP_ENV == "production":
        index_file = FRONTEND_DIST / "index.html"

        if index_file.exists():
            return FileResponse(index_file)

    return {"status": "SEMA backend running"}



@app.get(f"{API_BASE}/dashboard")
def get_dashboard(
    trusted=Depends(require_trusted_access),
):
    try:
        return {
            "dashboard": get_dashboard_data(),
            "control": get_control_data(),
        }
    except Exception as e:
        print("DASHBOARD ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/device-api/proxy-test")
def proxy_test(request: Request):
    return {
        "user": request.headers.get("X-SEMA-Proxy-User"),
        "role": request.headers.get("X-SEMA-Proxy-Role"),
    }

@app.get(f"{API_BASE}/history")
def get_history(limit: int = 20, trusted=Depends(require_trusted_access),):

    rows = get_last_measurements(limit)

    ts = []
    outdoor = []
    indoor = []
    water = []
    heat = []
    exchanger = []
    equiterm = []
    e = []
    f = []
    g = []
    progress = []


    for r in rows:
        ts.append(r[0])
        outdoor.append(r[1])
        indoor.append(r[2])
        water.append(r[3])
        heat.append(r[4])
        exchanger.append(r[5])
        equiterm.append(r[6])
        e.append(r[7])
        f.append(r[8])
        g.append(r[9])
        progress.append(r[10])

    return {
        "ts": ts,
        "outdoor": outdoor,
        "indoor": indoor,
        "water": water,
        "heat": heat,
        "exchanger": exchanger,
        "equiterm": equiterm,
        "eTemp": e,
        "fTemp": f,
        "gTemp": g,
        "progress": progress
    }

@app.get(f"{API_BASE}/heating-main-temp")
def get_heating_main_temp(trusted=Depends(require_trusted_access),):
    return {
        "heatingMainTemp": load_heating_main_temp()
    }


@app.get(f"{API_BASE}/heating-main-temp/coefficient")
def get_heating_curve_coefficient(current_user=Depends(require_pump_configurator),
                                 trusted=Depends(require_trusted_access)):
    return {"coefficient": load_heating_curve_coefficient()}


@app.post(f"{API_BASE}/heating-main-temp/coefficient")
def post_heating_curve_coefficient(data: HeatingCurveCoefficientUpdate,
                                  current_user=Depends(require_pump_configurator),
                                  trusted=Depends(require_trusted_access)):
    return save_heating_curve_coefficient(data.value)


@app.post(f"{API_BASE}/heating-main-temp")
def post_heating_main_temp(data: HeatingMainTempUpdate, current_user=Depends(get_current_user),
                           trusted=Depends(require_trusted_access)):
    try:
        return set_heating_main_temp(data.value, build_parameters_payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{API_BASE}/setback_params")
def get_parameters(trusted=Depends(require_trusted_access),):
    try:
        html = fetch_parameters_html()
        data = parse_setback_param(html)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get(f"{API_BASE}/settings")
def get_settings(current_user=Depends(get_current_user), trusted=Depends(require_trusted_access)):
    try:
        html = fetch_parameters_html()
        data = parse_settings_params(html)
        return data if can_configure_pump(current_user.role) else {
            key: value for key, value in data.items() if key in BASIC_SETTINGS
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{API_BASE}/setback")
def get_setback_schedule(trusted=Depends(require_trusted_access),):
    try:
        html = fetch_timer_html()
        return parse_timer_params(html)
    except Exception as e:
        print("SetBack error:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get(f"{API_BASE}/health")
def health():
    return {"ok": True}


@app.get(f"{API_BASE}/device/health")
def device_health():
    try:
        fetch_status_xml()
        return {"connected": True}
    except Exception:
        return {"connected": False}


@app.post(f"{API_BASE}/control")
def update_control(data: ControlUpdate, current_user=Depends(get_current_user), trusted=Depends(require_trusted_access)):
    try:
        print("CONTROL DATA:", data)

        cmd = map_control_to_cmd(data)
        print("CONTROL CMD:", cmd)

        post_control_cmd(cmd)

        return {"ok": True}
    except Exception as e:
        print("CONTROL ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get(f"{API_BASE}/device-info")
def device_info(trusted=Depends(require_trusted_access),): 
    return get_device_info()
    

@app.post(f"{API_BASE}/login", response_model=TokenResponse)
def login(data: LoginRequest, trusted=Depends(require_trusted_access),):
    user = authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Nesprávne meno alebo heslo")

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
    }


@app.post(f"{API_BASE}/heating-main-temp/reference")
def post_heating_main_temp_reference(
    data: HeatingMainTempUpdate,
    trusted=Depends(require_trusted_access),
    current_user=Depends(require_pump_configurator),
):
    try:
        return set_heating_main_temp_reference(data.value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(f"{API_BASE}/me")
def me(current_user = Depends(get_current_user),trusted=Depends(require_trusted_access),):
    return current_user
    
@app.get(f"{API_BASE}/account")
def get_my_account(current_user=Depends(get_current_user),trusted=Depends(require_trusted_access),):
    return {
        "username": current_user.username,
        "role": current_user.role,
    }





def build_parameters_payload(current_form: dict, data):
    form = current_form.copy()
    values = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
    mappings = {
        "minIndoorCool": ("p3", encode_temp_value), "maxIndoorHeat": ("p4", encode_temp_value),
        "constant": ("p5", int), "limitWater": ("p13", encode_percentage_value),
        "minWaterTemp": ("p14", encode_temp_value), "maxWaterTemp": ("p15", encode_temp_value),
        "limitHeat": ("p16", encode_percentage_value), "limitCool": ("p17", encode_percentage_value),
        "coolerTemp": ("p18", encode_temp_value), "bivalentTemp": ("p19", encode_bivalent_temp),
        "timeLimitWater": ("p22", int),
    }
    for name, (key, encode) in mappings.items():
        if name in values and values[name] is not None:
            form[key] = str(encode(values[name]))
    if values.get("heatCurve") is not None:
        for point, key in zip(("-20", "-12", "-4", "4", "12", "20"), range(7, 13)):
            form[f"p{key}"] = str(encode_temp_value(values["heatCurve"][point]))
    return form


@app.post(f"{API_BASE}/settings")
def post_settings(data: SettingsUpdate, current_user=Depends(get_current_user),
                  trusted=Depends(require_trusted_access)):
    supplied = data.model_fields_set
    if not can_configure_pump(current_user.role) and supplied - BASIC_SETTINGS:
        raise HTTPException(403, "Technical pump settings access required")
    try:
        html = fetch_parameters_html()
        current_form = extract_all_parameter_inputs(html)
        payload = build_parameters_payload(current_form, data)

        post_parameters_form(payload)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post(f"{API_BASE}/setback")
def post_setback(data: SetbackUpdate, current_user=Depends(get_current_user), trusted=Depends(require_trusted_access)):
    try:
        # 1. uloženie offsetov do parameters.htm
        params_html = fetch_parameters_html()
        current_params_form = extract_all_parameter_inputs(params_html)
        params_payload = build_setback_parameters_payload(current_params_form, data)
        post_parameters_form(params_payload)

        # 2. uloženie schedule do timer.htm
        timer_html = fetch_timer_html()
        current_timer_form = extract_all_timer_inputs(timer_html)
        timer_payload = build_timer_payload(current_timer_form, data.schedule)
        post_timer_form(timer_payload)

        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

def build_timer_payload(current_form: dict, schedule: dict):

    form = current_form.copy()

    for day_idx, day_key in enumerate(DAY_KEYS):
        base = day_idx * 8
        intervals = schedule.get(day_key, [])

        # vymaž celý deň
        for i in range(8):
            form[f"p{base + i}"] = "255"

        # zapíš max 4 intervaly
        for interval_idx, interval in enumerate(intervals[:4]):
            from_index = base + interval_idx * 2
            to_index = from_index + 1

            form[f"p{from_index}"] = str(interval["from"])
            form[f"p{to_index}"] = str(interval["to"])

    return form


@app.get(f"{API_BASE}/config")
def load_config(current_user=Depends(require_admin), trusted=Depends(require_trusted_access)):

    result = {}

    for frontend_key, config in CONFIG.items():
        result[frontend_key] = get_config(
            config["db_key"],
            config["default"]
        )

    return result


@app.post(f"{API_BASE}/config")
def save_config(payload: dict, current_user=Depends(require_admin), trusted=Depends(require_trusted_access)):

    for frontend_key, value in payload.items():

        config = CONFIG.get(frontend_key)

        if not config:
            continue

        set_config(
            config["db_key"],
            value
        )

    return {"ok": True}


# Local credential management is retired; existing SQLite logins are preserved.
@app.api_route(API_BASE + "/accounts/{role}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def retired_account_management(role: str):
    raise HTTPException(410, "Správa účtov prebieha výhradne cez SEMA Portal.")


@app.get(f"{API_BASE}/sync/measurements")
def sync_measurements(
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=1000),
    trusted=Depends(require_portal_sync),
):
    measurements = get_measurements_after_id(
        after_id=after_id,
        limit=limit,
    )

    last_id = (
        measurements[-1]["id"]
        if measurements
        else after_id
    )

    return {
        "device_id": DEVICE_ID,
        "source_db_id": source_id(),
        "measurements": measurements,
        "count": len(measurements),
        "last_id": last_id,
    }

@app.get(f"{API_BASE}/sync/metadata")
def sync_metadata(trusted=Depends(require_portal_sync)):
    return {"device_id": DEVICE_ID, "source_db_id": source_id(), "version": 2}


@app.get(f"{API_BASE}/sync/events")
def sync_events(after_id: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=1000), trusted=Depends(require_portal_sync)):
    events = export_events(after_id, limit)
    return {"device_id": DEVICE_ID, "source_db_id": source_id(), "events": events,
            "last_id": events[-1]['id'] if events else after_id}


@app.post(f"{API_BASE}/sync/flush")
async def sync_flush(trusted=Depends(require_portal_sync)):
    await collector.flush(include_latest=True)
    return {"ok": True, "device_id": DEVICE_ID}


@app.get(f"{API_BASE}/sync/status")
def sync_status(
    trusted=Depends(require_portal_sync),
):
    return {
        "status": "online",
        "software": software_info(),
        "device_id": DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "errors": ([{"code": "general_fault", "message": "Čerpadlo hlási všeobecnú chybu."}]
                   if collector.previous.get('fault') else []),
        "pump_available": collector.previous.get('available.status'),
        "observed_at": collector.last_observed['ts'] if collector.last_observed else None,
    }


if APP_ENV == "production":

    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}")
    def serve_react_app(full_path: str):
        index_file = FRONTEND_DIST / "index.html"

        if index_file.exists():
            return FileResponse(index_file)

        raise HTTPException(
            status_code=404,
            detail="Frontend build not found",
        )
    
