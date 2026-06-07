
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from device_service import get_dashboard_data, get_control_data, fetch_status_xml
from fastapi import FastAPI, Body, HTTPException, Depends
from db import init_db, log_temps, get_last_measurements, get_config, set_config, set_account, get_account
from fastapi.middleware.cors import CORSMiddleware
from services.wifi_service import is_setup_mode, scan_wifi_networks, connect_wifi
from services.device_info import get_device_info
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
from pydantic import BaseModel

from datetime import timedelta
from auth import (
    LoginRequest,
    TokenResponse,
    authenticate_user,
    create_access_token,
    get_current_user,
    require_admin,
    require_superadmin,
    get_account_by_role,
    password_hash,
)

from services.heat_curve_service import (
    load_heating_main_temp,
    set_heating_main_temp,
    set_heating_main_temp_reference,
)

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class ControlUpdate(BaseModel):
    powerMode: Optional[str] = None
    mode: Optional[str] = None
    season: Optional[str] = None

class SettingsUpdate(BaseModel):
    minIndoorCool: float
    maxIndoorHeat: float
    minWaterTemp: float
    maxWaterTemp: float
    constant: int
    limitWater: float
    limitHeat: float
    limitCool: float
    coolerTemp: float
    bivalentTemp: float
    timeLimitWater: int
    heatCurve: Dict[str, float]

class SetbackUpdate(BaseModel):
    heatOffset: float
    coolOffset: float
    schedule: Dict[str, List[dict]] = {}


class HeatingMainTempUpdate(BaseModel):
    value: float

class AccountUpdate(BaseModel):
    username: str
    password: Optional[str] = None

class WifiConnectRequest(BaseModel):
    ssid: str
    password: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(measurement_logger())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)


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

@app.get("/api/device/status")
def device_status():
    return fetch_status_xml()

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

@app.get("/")
def root():
    if APP_ENV == "production":
        index_file = FRONTEND_DIST / "index.html"

        if index_file.exists():
            return FileResponse(index_file)

    return {"status": "SEMA backend running"}


# @app.get("/api/dashboard")
# def get_dashboard():
#     data = {
#         "dashboard": get_dashboard_data(),
#         "control": get_control_data()
#     }
#     return data

@app.get("/api/dashboard")
def get_dashboard():
    try:
        return {
            "dashboard": get_dashboard_data(),
            "control": get_control_data(),
        }
    except Exception as e:
        print("DASHBOARD ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
def get_history(limit: int = 20):

    rows = get_last_measurements(limit)

    ts = []
    outdoor = []
    indoor = []
    water = []
    heat = []
    progress = []

    for r in rows:
        ts.append(r[0])
        outdoor.append(r[1])
        indoor.append(r[2])
        water.append(r[3])
        heat.append(r[4])
        progress.append(r[5])

    return {
        "ts": ts,
        "outdoor": outdoor,
        "indoor": indoor,
        "water": water,
        "heat": heat,
        "progress": progress
    }

@app.get("/api/heating-main-temp")
def get_heating_main_temp():
    return {
        "heatingMainTemp": load_heating_main_temp()
    }


@app.post("/api/heating-main-temp")
def post_heating_main_temp(data: HeatingMainTempUpdate):
    try:
        return set_heating_main_temp(data.value, build_parameters_payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/setback_params")
def get_parameters():
    try:
        html = fetch_parameters_html()
        data = parse_setback_param(html)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/system/setup-mode")
def get_setup_mode():
    return {
        "setupMode": is_setup_mode()
    }
    
@app.get("/api/wifi/scan")
def wifi_scan():
    return {
        "networks": scan_wifi_networks()
    }

@app.post("/api/wifi/connect")
def wifi_connect(data: WifiConnectRequest):
    result = connect_wifi(data.ssid, data.password)

    if not result.get("ok"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "WiFi connection failed"),
        )

    return result
@app.get("/api/settings")
def get_settings():
    try:
        html = fetch_parameters_html()
        return parse_settings_params(html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/setback")
def get_setback_schedule():
    try:
        html = fetch_timer_html()
        return parse_timer_params(html)
    except Exception as e:
        print("SetBack error:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/device/health")
def device_health():
    try:
        fetch_status_xml()
        return {"connected": True}
    except Exception:
        return {"connected": False}


@app.post("/api/control")
def update_control(data: ControlUpdate):
    try:
        print("CONTROL DATA:", data)

        cmd = map_control_to_cmd(data)
        print("CONTROL CMD:", cmd)

        post_control_cmd(cmd)

        return {"ok": True}
    except Exception as e:
        print("CONTROL ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/device-info")
def device_info(): 
    return get_device_info()
    

@app.post("/api/login", response_model=TokenResponse)
def login(data: LoginRequest):
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


@app.post("/api/heating-main-temp/reference")
def post_heating_main_temp_reference(
    data: HeatingMainTempUpdate,
    # current_user=Depends(require_admin),
):
    try:
        return set_heating_main_temp_reference(data.value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/me")
def me(current_user = Depends(get_current_user)):
    return current_user
    
@app.get("/api/account")
def get_my_account(current_user=Depends(get_current_user)):
    return {
        "username": current_user.username,
        "role": current_user.role,
    }




async def measurement_logger():
    while True:
        try:
            data = get_dashboard_data()

            log_temps(
                data["outdoorTemp"],
                data["indoorTemp"],
                data["waterTemp"],
                data["heatTemp"],
                data["progress"],
            )
        except Exception as e:
            print("Logging error:", e)

        await asyncio.sleep(300)  # 5 min


def build_parameters_payload(current_form: dict, data):
    def val(key):
        return data[key] if isinstance(data, dict) else getattr(data, key)

    form = current_form.copy()

    form["p3"] = str(encode_temp_value(val("minIndoorCool")))
    form["p4"] = str(encode_temp_value(val("maxIndoorHeat")))
    form["p5"] = str(int(val("constant")))

    heat_curve = val("heatCurve")

    form["p7"] = str(encode_temp_value(heat_curve["-20"]))
    form["p8"] = str(encode_temp_value(heat_curve["-12"]))
    form["p9"] = str(encode_temp_value(heat_curve["-4"]))
    form["p10"] = str(encode_temp_value(heat_curve["4"]))
    form["p11"] = str(encode_temp_value(heat_curve["12"]))
    form["p12"] = str(encode_temp_value(heat_curve["20"]))

    form["p13"] = str(encode_percentage_value(val("limitWater")))
    form["p14"] = str(encode_temp_value(val("minWaterTemp")))
    form["p15"] = str(encode_temp_value(val("maxWaterTemp")))
    form["p16"] = str(encode_percentage_value(val("limitHeat")))
    form["p17"] = str(encode_percentage_value(val("limitCool")))
    form["p18"] = str(encode_temp_value(val("coolerTemp")))
    form["p19"] = str(encode_bivalent_temp(val("bivalentTemp")))
    form["p22"] = str(int(val("timeLimitWater")))

    return form


@app.post("/api/settings")
def post_settings(data: SettingsUpdate):
    try:
        html = fetch_parameters_html()
        current_form = extract_all_parameter_inputs(html)
        payload = build_parameters_payload(current_form, data)

        post_parameters_form(payload)
        print(payload)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/setback")
def post_setback(data: SetbackUpdate):
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


@app.get("/api/config")
def load_config():

    result = {}

    for frontend_key, config in CONFIG.items():
        result[frontend_key] = get_config(
            config["db_key"],
            config["default"]
        )

    return result


@app.post("/api/config")
def save_config(payload: dict):

    for frontend_key, value in payload.items():

        config = CONFIG.get(frontend_key)

        if not config:
            continue

        set_config(
            config["db_key"],
            value
        )

    return {"ok": True}


@app.get("/api/accounts/{role}")
def get_account_info(
    role: str,
    current_user=Depends(get_current_user),
):
    valid_roles = ["user", "admin", "superadmin"]

    if role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid role",
        )

    if current_user.role == "user":
        allowed = ["user"]

    elif current_user.role == "admin":
        allowed = ["user", "admin"]

    elif current_user.role == "superadmin":
        allowed = ["user", "admin", "superadmin"]

    else:
        allowed = []

    if role not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    account = get_account_by_role(role)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return account


@app.post("/api/accounts/{role}")
def update_account(
    role: str,
    data: AccountUpdate,
    current_user=Depends(get_current_user),
):

    if current_user.role == "user":
        allowed = ["user"]

    elif current_user.role == "admin":
        allowed = ["user", "admin"]

    elif current_user.role == "superadmin":
        allowed = ["user", "admin", "superadmin"]

    else:
        allowed = []

    if role not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    current_account = get_account(role)

    if not current_account:
        raise HTTPException(status_code=404, detail="Account not found")

    password_hash_value = current_account["password_hash"]

    if data.password and data.password.strip():
        password_hash_value = password_hash.hash(data.password)

    set_account(
        role=role,
        username=data.username,
        password_hash=password_hash_value,
    )

    return {
        "ok": True,
        "role": role,
        "username": data.username,
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