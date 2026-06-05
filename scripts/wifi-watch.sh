#!/bin/bash

AP_CONNECTION="sema-ap"
WIFI_DEVICE="wlan0"

if nmcli -t -f NAME,DEVICE connection show --active | grep -q "^${AP_CONNECTION}:${WIFI_DEVICE}$"; then
    echo "AP mode active"
    exit 0
fi

if nmcli -t -f DEVICE,STATE device | grep -q "^${WIFI_DEVICE}:connected$"; then
    echo "WiFi connected"
    exit 0
fi

echo "WiFi not connected, starting AP..."
nmcli connection up "$AP_CONNECTION"