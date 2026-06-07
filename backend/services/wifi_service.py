import subprocess
import re
import os
from dotenv import load_dotenv

load_dotenv()

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
    if (os.getenv("APP_ENV")=="development"):
        return False
    force_setup_raw = os.getenv("FORCE_SETUP_MODE", "false")
    force_setup = force_setup_raw.strip().lower() == "true"

    print("FORCE_SETUP_MODE raw:", force_setup_raw)
    print("force_setup:", force_setup)

    if force_setup:
        print("SETUP MODE: forced by env")
        return True

    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,DEVICE,TYPE", "connection", "show", "--active"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        print("nmcli active:")
        print(result.stdout)

        for line in result.stdout.splitlines():
            parts = line.split(":")

            if len(parts) >= 3:
                name = parts[0]
                device = parts[1]
                conn_type = parts[2]

                print("connection:", name, device, conn_type)

                if name == "sema-ap" and device == "wlan0":
                    print("SETUP MODE: sema-ap active")
                    return True

    except Exception as e:
        print("setup mode nmcli error:", e)

    wifi_connected = is_wifi_connected()
    print("wifi_connected:", wifi_connected)

    result = not wifi_connected
    print("SETUP MODE result:", result)

    return result

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
        # ak je AP aktívny, vypni ho
        subprocess.run(
            ["sudo", "nmcli", "connection", "down", "sema-ap"],
            capture_output=True,
            text=True,
            timeout=10,
        )

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
            # ak sa pripojenie nepodarí, znova zapni AP
            subprocess.run(
                ["sudo", "nmcli", "connection", "up", "sema-ap"],
                capture_output=True,
                text=True,
                timeout=10,
            )

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