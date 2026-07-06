#!/bin/bash

AP_CONNECTION="sema-ap"
WIFI_DEVICE="wlan0"

SCRIPT_LOCK="/tmp/sema-wifi-watch.lock"
FAIL_FILE="/tmp/sema-wifi-fail-count"
LOCK_FILE="/tmp/sema-wifi-setup-active"
AP_LAST_RETRY_FILE="/tmp/sema-ap-last-retry"

FAIL_LIMIT=4
LOCK_TIMEOUT=300
CONNECT_TIMEOUT=15
AP_RETRY_AFTER=600

now=$(date +%s)

exec 9>"$SCRIPT_LOCK"
if ! flock -n 9; then
    echo "Another wifi-watch instance is already running, exiting"
    exit 0
fi

get_wifi_profiles() {
    nmcli -t -f NAME,TYPE connection show \
        | grep ":802-11-wireless$" \
        | cut -d: -f1
}

disable_saved_wifi_autoconnect() {
    profiles=$(get_wifi_profiles)

    for name in $profiles; do
        [ "$name" = "$AP_CONNECTION" ] && continue
        nmcli connection modify "$name" connection.autoconnect no
    done
}

enable_saved_wifi_autoconnect() {
    profiles=$(get_wifi_profiles)

    for name in $profiles; do
        [ "$name" = "$AP_CONNECTION" ] && continue
        nmcli connection modify "$name" connection.autoconnect yes
    done
}

start_ap() {
    echo "Starting AP..."

    disable_saved_wifi_autoconnect

    nmcli connection modify "$AP_CONNECTION" connection.autoconnect yes
    nmcli device disconnect "$WIFI_DEVICE"
    sleep 2
    nmcli connection up "$AP_CONNECTION"
}

try_saved_wifi() {
    profiles=$(get_wifi_profiles)

    for name in $profiles; do
        [ "$name" = "$AP_CONNECTION" ] && continue

        echo "Trying saved WiFi profile: $name"

        nmcli connection modify "$name" connection.autoconnect yes
        nmcli connection modify "$name" connection.autoconnect-priority 10

        nmcli connection modify "$AP_CONNECTION" connection.autoconnect no
        nmcli device disconnect "$WIFI_DEVICE"
        sleep 2

        timeout "$CONNECT_TIMEOUT" nmcli connection up "$name"

        if nmcli -t -f DEVICE,STATE device | grep -q "^${WIFI_DEVICE}:connected$" && \
           ! nmcli -t -f NAME,DEVICE connection show --active | grep -q "^${AP_CONNECTION}:${WIFI_DEVICE}$"; then
            echo "Connected to WiFi: $name"
            rm -f "$FAIL_FILE"
            rm -f "$AP_LAST_RETRY_FILE"
            return 0
        fi

        nmcli connection modify "$name" connection.autoconnect no
    done

    return 1
}

# Setup lock - počas ukladania WiFi nastavení nič nerob
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

    last_retry=0
    [ -f "$AP_LAST_RETRY_FILE" ] && last_retry=$(cat "$AP_LAST_RETRY_FILE")

    retry_age=$((now - last_retry))

    if [ "$retry_age" -lt "$AP_RETRY_AFTER" ]; then
        echo "Keeping AP running. Next WiFi retry in $((AP_RETRY_AFTER - retry_age))s"
        exit 0
    fi

    echo "$now" > "$AP_LAST_RETRY_FILE"
    echo "Trying to return from AP to saved WiFi..."

    if try_saved_wifi; then
        exit 0
    fi

    echo "Could not reconnect to saved WiFi. Returning to AP..."
    start_ap
    exit 0
fi

# Je pripojená normálna WiFi?
if nmcli -t -f DEVICE,STATE device | grep -q "^${WIFI_DEVICE}:connected$"; then
    echo "WiFi connected"

    nmcli connection modify "$AP_CONNECTION" connection.autoconnect no

    rm -f "$FAIL_FILE"
    rm -f "$AP_LAST_RETRY_FILE"
    exit 0
fi

# Nie je WiFi ani AP
fail_count=0
[ -f "$FAIL_FILE" ] && fail_count=$(cat "$FAIL_FILE")

fail_count=$((fail_count + 1))
echo "$fail_count" > "$FAIL_FILE"

echo "WiFi not connected. Fail count: $fail_count/$FAIL_LIMIT"

if try_saved_wifi; then
    exit 0
fi

if [ "$fail_count" -ge "$FAIL_LIMIT" ]; then
    rm -f "$FAIL_FILE"
    echo "$now" > "$AP_LAST_RETRY_FILE"
    start_ap
else
    echo "Waiting before starting AP..."
fi