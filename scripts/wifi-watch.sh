#!/bin/bash

AP_CONNECTION="sema-ap"
WIFI_DEVICE="wlan0"

FAIL_FILE="/tmp/sema-wifi-fail-count"
LOCK_FILE="/tmp/sema-wifi-setup-active"

FAIL_LIMIT=4
LOCK_TIMEOUT=300
CONNECT_TIMEOUT=15

now=$(date +%s)

# Setup lock
if [ -f "$LOCK_FILE" ]; then
    lock_time=$(stat -c %Y "$LOCK_FILE")
    lock_age=$((now - lock_time))

    if [ "$lock_age" -lt "$LOCK_TIMEOUT" ]; then
        echo "WiFi setup active, skipping"
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi

# Je aktívny AP?
if nmcli -t -f NAME,DEVICE connection show --active | grep -q "^${AP_CONNECTION}:${WIFI_DEVICE}$"; then
    echo "AP mode active"

    # Skús návrat na uloženú WiFi
    profiles=$(nmcli -t -f NAME,TYPE connection show | grep ":802-11-wireless$" | cut -d: -f1)

    for name in $profiles; do
        [ "$name" = "$AP_CONNECTION" ] && continue

        echo "Trying saved WiFi profile: $name"
        timeout "$CONNECT_TIMEOUT" nmcli connection up "$name"

        if nmcli -t -f DEVICE,STATE device | grep -q "^${WIFI_DEVICE}:connected$" && \
           ! nmcli -t -f NAME,DEVICE connection show --active | grep -q "^${AP_CONNECTION}:${WIFI_DEVICE}$"; then
            echo "Reconnected to WiFi: $name"
            rm -f "$FAIL_FILE"
            exit 0
        fi
    done

    echo "Still in AP mode"
    exit 0
fi

# Je pripojená normálna WiFi?
if nmcli -t -f DEVICE,STATE device | grep -q "^${WIFI_DEVICE}:connected$"; then
    echo "WiFi connected"
    rm -f "$FAIL_FILE"
    exit 0
fi

# Nie je WiFi ani AP
fail_count=0
[ -f "$FAIL_FILE" ] && fail_count=$(cat "$FAIL_FILE")

fail_count=$((fail_count + 1))
echo "$fail_count" > "$FAIL_FILE"

echo "WiFi not connected. Fail count: $fail_count/$FAIL_LIMIT"

# Skús uložené WiFi profily
profiles=$(nmcli -t -f NAME,TYPE connection show | grep ":802-11-wireless$" | cut -d: -f1)

for name in $profiles; do
    [ "$name" = "$AP_CONNECTION" ] && continue

    echo "Trying saved WiFi profile: $name"
    timeout "$CONNECT_TIMEOUT" nmcli connection up "$name"

    if nmcli -t -f DEVICE,STATE device | grep -q "^${WIFI_DEVICE}:connected$"; then
        echo "Connected to WiFi: $name"
        rm -f "$FAIL_FILE"
        exit 0
    fi
done

# AP až po viacerých zlyhaniach
if [ "$fail_count" -ge "$FAIL_LIMIT" ]; then
    echo "Starting AP..."
    rm -f "$FAIL_FILE"
    nmcli connection up "$AP_CONNECTION"
else
    echo "Waiting before starting AP..."
fi