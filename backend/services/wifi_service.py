import subprocess
import re

def is_wifi_connected() -> bool:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,STATE", "device"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        return "wlan0:connected" in result.stdout

    except Exception:
        return False


def is_setup_mode() -> bool:

    force_setup = os.getenv(
        "FORCE_SETUP_MODE",
        "false"
    ).lower() == "true"

    if force_setup:
        return True

    return not is_wifi_connected()


def scan_wifi_networks():
    try:
        result = subprocess.run(
            [
                "nmcli",
                "-t",
                "-f",
                "SSID,SIGNAL,SECURITY",
                "dev",
                "wifi",
                "list",
                "ifname",
                "wlan0",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        networks = []

        for line in result.stdout.splitlines():
            if not line.strip():
                continue

            parts = line.split(":")

            ssid = parts[0].strip()
            signal = parts[1].strip() if len(parts) > 1 else ""
            security = parts[2].strip() if len(parts) > 2 else ""

            if not ssid:
                continue

            networks.append({
                "ssid": ssid,
                "signal": int(signal) if signal.isdigit() else 0,
                "security": security,
            })

        # odstránenie duplicít podľa SSID
        unique = {}
        for network in networks:
            ssid = network["ssid"]
            if ssid not in unique or network["signal"] > unique[ssid]["signal"]:
                unique[ssid] = network

        return sorted(
            unique.values(),
            key=lambda x: x["signal"],
            reverse=True,
        )

    except Exception:
        return []
    
def connect_wifi(ssid: str, password: str) -> dict:
    try:
        result = subprocess.run(
            [
                "sudo",
                "nmcli",
                "dev",
                "wifi",
                "connect",
                ssid,
                "password",
                password,
                "ifname",
                "wlan0",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {
                "ok": False,
                "error": result.stderr.strip() or result.stdout.strip(),
            }

        return {
            "ok": True,
            "message": "WiFi pripojenie bolo úspešné",
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }

