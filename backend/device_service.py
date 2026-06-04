import requests
import xml.etree.ElementTree as ET
import os
from dotenv import load_dotenv
from heatpump_client import get_device_base_url, get_device_url, get_auth

load_dotenv()
DEVICE_USER = os.getenv("DEVICE_USER")
DEVICE_PASSWORD = os.getenv("DEVICE_PASSWORD")
# DEVICE_URL = get_device_base_url()
# STATUS = DEVICE_URL + "status.xml"
# CONTROL = DEVICE_URL + "control.xml"


def parse_temp(value: str) -> float:
    return float(value.replace("°C", "").strip())


def parse_percent(value: str) -> int:
    return int(value.replace("%", "").strip())


def fetch_status_xml():
    response = requests.get(
        get_device_url("status.xml"),
        auth=get_auth(),
        timeout=5,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)

    return {
        "rtcc": root.findtext("rtcc", default="").strip(),
        "tep2": parse_temp(root.findtext("tep2", default="0")),
        "tep3": parse_temp(root.findtext("tep3", default="0")),
        "tep4": parse_temp(root.findtext("tep4", default="0")),
        "tep8": parse_temp(root.findtext("tep8", default="0")),
        "pwr": parse_percent(root.findtext("pwr", default="0")),
        "st1": int(root.findtext("st1", default="0")),
        "st2": int(root.findtext("st2", default="0")),
        "st3": int(root.findtext("st3", default="0")),
        "st4": int(root.findtext("st4", default="0")),
        "st5": int(root.findtext("st5", default="0")),
    }

def fetch_control_xml():
    response = requests.get(
        get_device_url("control.xml"),
        auth=get_auth(),
        timeout=5,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)

    return {
        "st1": int(root.findtext("st1", default="0")),
        "st2": int(root.findtext("st2", default="0")),
        "st3": int(root.findtext("st3", default="0")),
    }


def get_dashboard_data():
    raw = fetch_status_xml()

    season_map = {
        1: "Kúrenie",
        2: "Chladenie",
        3: "Vypnuté",
        4: "Defrost",
        5: "Chyba",
    }

    heat_stage_map = {
        1: "Kompresor",
        2: "Bivalent 1",
        3: "Bivalent 2",
        4: "Letný režim",
    }

    dhw_map = {
        1: "Ohrev TUV",
        2: "E Ohrev TUV",
    }

    return {
        "indoorTemp": raw["tep2"],
        "outdoorTemp": raw["tep8"],
        "waterTemp": raw["tep4"],
        "heatTemp": raw["tep3"],
        "power": str(raw["pwr"]),
        "mode": dhw_map.get(raw["st3"], "Standby"),
        "heatCool": season_map.get(raw["st1"], "Neznáme"),
        "season": heat_stage_map.get(raw["st2"], ""),
        "defrost": raw["st1"] == 4,
        "error": raw["st1"] == 5,
        "setbackActive": raw["st4"] == 1,
        "highTariff": raw["st5"] == 1,
        "progress": str(raw["pwr"]),
        "notConnected":0,
    }

def get_control_data():
    raw = fetch_control_xml()

    power_map = {
    0: "Neznámy stav",
    1: "Zapnuté",
    2: "Vypnuté",
    }

    mode_map = {
        0: "Neznámy stav",
        1: "Kúrenie",
        2: "Chladenie",
    }

    season_map = {
        0: "Neznámy stav",
        1: "Leto",
        2: "Zima",

    }

    return {
        "powerMode": power_map.get(raw.get("st1"), "Neznámy stav"),
        "mode": mode_map.get(raw.get("st2"), "Neznámy stav"),
        "season": season_map.get(raw.get("st3"), "Neznámy stav"),
    }