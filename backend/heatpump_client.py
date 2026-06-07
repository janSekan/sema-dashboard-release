import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
from db import get_config

load_dotenv()


# DEVICE_USER get_auth())
DEVICE_USER = os.getenv("DEVICE_USER")
DEVICE_PASSWORD = os.getenv("DEVICE_PASSWORD")
APP_ENV = os.getenv("APP_ENV")

def get_device_base_url():
    if APP_ENV == "development":
        ip = os.getenv("DEVICE_IP_DEV", "192.168.33.30:8081")
    else:
        ip = get_config("device_ip", "192.168.69.2")

    return f"http://{ip}/"


def get_auth():
    return HTTPBasicAuth(DEVICE_USER, DEVICE_PASSWORD)


def get_device_url(path: str):
    return get_device_base_url() + path.lstrip("/")

# STATUS = DEVICE_URL + "status.xml"
# CONTROL_HTM = DEVICE_URL + "control.htm"
# PARAMETERS_URL = DEVICE_URL + "/parameters.htm"
# TIMER_URL = DEVICE_URL + "/timer.htm"

def fetch_parameters_html():
    response = requests.get(
        get_device_url("parameters.htm"),
        auth=get_auth(),
        timeout=10,
    )
    response.raise_for_status()
    return response.text

def fetch_timer_html():
    response = requests.get(
        get_device_url("timer.htm"),
        auth=get_auth(),
        timeout=10
    )
    response.raise_for_status()
    return response.text

def post_control_cmd(cmd: int):
    response = requests.post(
        get_device_url("control.htm"),
        auth=get_auth(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"cmd": str(cmd)},
        timeout=10,
    )
    response.raise_for_status()
    return True

def post_parameters_form(form_data: dict):
    response = requests.post(
        get_device_url("parameters.htm"),
        auth=get_auth(),
        data=form_data,
        timeout=10,
    )
    response.raise_for_status()
    return True

def post_timer_form(form_data: dict):
    response = requests.post(
        get_device_url("timer.htm"),
        auth=get_auth(),
        data=form_data,
        timeout=10,
    )
    response.raise_for_status()
    return True