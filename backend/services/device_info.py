# services/device_info.py

import json

import socket
import subprocess
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
VERSIONS_FILE = BASE_DIR.parent.parent / "versions.json"


def get_versions():
    try:
        with open(VERSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "dashboard": None,
            "semaos": None,
        }

def run_cmd(cmd: list[str]) -> str | None:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except Exception:
        return None


def get_hostname() -> str:
    return socket.gethostname()


def get_hostname_local() -> str:
    return f"{get_hostname()}.local"


def get_local_ip(interface: str = "wlan0") -> str | None:
    if os.getenv("APP_ENV") == "development":
        interface = "wlo1"
    output = run_cmd(["ip", "-4", "addr", "show", interface])

    if not output:
        return None

    for line in output.splitlines():
        line = line.strip()
        if line.startswith("inet "):
            return line.split()[1].split("/")[0]

    return None


def get_tailscale_ip() -> str | None:
    return run_cmd(["tailscale", "ip", "-4"])


def get_uptime() -> str | None:
    output = run_cmd(["uptime", "-p"])

    if not output:
        return None

    return output.replace("up ", "")


def get_rpi_model() -> str | None:
    path = Path("/proc/device-tree/model")

    try:
        return path.read_text().replace("\x00", "").strip()
    except Exception:
        return None






def get_device_info() -> dict:
    return {
        "deviceId": os.getenv("DEVICE_ID"),
        "hostname": get_hostname(),
        "localIp": get_local_ip("wlan0"),
        "tailscaleIp": get_tailscale_ip(),
        "uptime": get_uptime(),
        "semaOsVersion": get_versions()["semaos"],
        "dashboardVersion": get_versions()["dashboard"],

    }