import os
from dotenv import load_dotenv
load_dotenv()

CONFIG = {
    "deviceIp": {
        "db_key": "device_ip",
        "default": "192.168.69.2",
    },

    "subnetMask": {
        "db_key": "subnet_mask",
        "default": "255.255.255.0",
    },

    "heatingMainTemp": {
        "db_key": "heating_main_temp",
        "default": 20.0,
    },
}

PROXY_TOKEN = os.getenv("PROXY_TOKEN", "")