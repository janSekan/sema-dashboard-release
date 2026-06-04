import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"
SETBACK_FILE = DATA_DIR / "setback.json"

DATA_DIR.mkdir(exist_ok=True)

default_settings = {
    "minIndoorCool": 22,
    "maxIndoorHeat": 26,
    "minWaterTemp": 48,
    "maxWaterTemp": 52,
    "constant": 4,
    "heatCurve": {
        "-20": 29,
        "-12": 27,
        "-4": 25,
        "4": 23,
        "12": 21,
        "20": 19,
    },
}

default_setback = {
    "heatOffset": 2,
    "coolOffset": 2,
    "schedule": {
        "mon": [],
        "tue": [],
        "wed": [],
        "thu": [],
        "fri": [],
        "sat": [],
        "sun": [],
    },
}


def read_json(path: Path, default_data: dict):
    if not path.exists():
        write_json(path, default_data)
        return default_data

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)