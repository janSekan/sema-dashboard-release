#!/bin/bash

AP_CONNECTION="sema-ap"
WIFI_DEVICE="wlan0"

SCRIPT_LOCK="/tmp/sema-wifi-watch.lock"
FAIL_FILE="/tmp/sema-wifi-fail-count"
LOCK_FILE="/tmp/sema-wifi-setup-active"
AP_LAST_RETRY_FILE="/tmp/sema-ap-last-retry"

FAIL_LIMIT=2
LOCK_TIMEOUT=300

# Ako dlho má nmcli čakať na úspešné pripojenie WiFi
CONNECT_TIMEOUT=30

# Ako často skúšať návrat z AP na uloženú WiFi
AP_RETRY_AFTER=600

now=$(date +%s)


# ---------------------------------------------------------
# Zabránenie súbežnému spusteniu viacerých watcherov
# ---------------------------------------------------------

exec 9>"$SCRIPT_LOCK"

if ! flock -n 9; then
    echo "Another wifi-watch instance is already running, exiting"
    exit 0
fi


# ---------------------------------------------------------
# Pomocné funkcie
# ---------------------------------------------------------

get_ap_uuid() {
    nmcli -g connection.uuid connection show "$AP_CONNECTION" 2>/dev/null | head -n 1
}


get_saved_wifi_uuids() {
    local ap_uuid

    ap_uuid=$(get_ap_uuid)

    nmcli -t -f UUID,TYPE connection show \
        | awk -F: -v ap="$ap_uuid" \
          '$2 == "802-11-wireless" && $1 != ap { print $1 }'
}


get_connection_name() {
    local uuid="$1"

    nmcli -g connection.id connection show uuid "$uuid" 2>/dev/null
}


saved_wifi_exists() {
    local uuid

    while IFS= read -r uuid; do
        [ -z "$uuid" ] && continue
        return 0
    done < <(get_saved_wifi_uuids)

    return 1
}


start_ap() {
    echo "Starting AP..."

    # AP sa nikdy nesmie automaticky spustiť po boote.
    # Zapína ho iba wifi-watch.
    nmcli connection modify "$AP_CONNECTION" connection.autoconnect no

    # NetworkManager si sám prepne wlan0 na AP.
    # Nie je potrebné robiť "nmcli device disconnect wlan0".
    if nmcli --wait 20 connection up "$AP_CONNECTION" ifname "$WIFI_DEVICE"; then
        echo "AP started successfully"
        return 0
    else
        echo "ERROR: Failed to start AP"
        return 1
    fi
}


try_saved_wifi() {
    local uuid
    local name

    while IFS= read -r uuid; do

        [ -z "$uuid" ] && continue

        name=$(get_connection_name "$uuid")

        echo "Trying saved WiFi profile: $name ($uuid)"

        # Uložená zákaznícka WiFi musí zostať schopná
        # automatického pripojenia aj po reštarte.
        nmcli connection modify uuid "$uuid" connection.autoconnect yes
        nmcli connection modify uuid "$uuid" connection.autoconnect-priority 10

        # AP sa nesmie automaticky vracať.
        nmcli connection modify "$AP_CONNECTION" connection.autoconnect no

        # Necháme NetworkManager dokončiť celý proces:
        # scan -> association -> authentication -> DHCP.
        #
        # Používame priamo --wait namiesto externého "timeout",
        # aby sme nmcli nezabili uprostred prebiehajúcej aktivácie.
        if nmcli --wait "$CONNECT_TIMEOUT" \
            connection up uuid "$uuid" ifname "$WIFI_DEVICE"; then

            # Overíme, že wlan0 je naozaj connected
            # a zároveň nejde o náš AP profil.
            if nmcli -t -f DEVICE,STATE device \
                    | grep -q "^${WIFI_DEVICE}:connected$" && \
               ! nmcli -t -f NAME,DEVICE connection show --active \
                    | grep -q "^${AP_CONNECTION}:${WIFI_DEVICE}$"; then

                echo "Connected to WiFi: $name"

                rm -f "$FAIL_FILE"
                rm -f "$AP_LAST_RETRY_FILE"

                return 0
            fi
        fi

        echo "Failed to connect to WiFi: $name"

    done < <(get_saved_wifi_uuids)

    return 1
}


# ---------------------------------------------------------
# Setup lock
#
# Python vytvorí:
# /tmp/sema-wifi-setup-active
#
# Počas nastavovania WiFi watcher nesmie zasahovať.
# ---------------------------------------------------------

if [ -f "$LOCK_FILE" ]; then

    lock_time=$(stat -c %Y "$LOCK_FILE" 2>/dev/null)

    if [ -n "$lock_time" ]; then

        lock_age=$((now - lock_time))

        if [ "$lock_age" -lt "$LOCK_TIMEOUT" ]; then
            echo "WiFi setup active, skipping"
            exit 0
        else
            echo "WiFi setup lock expired, removing stale lock"
            rm -f "$LOCK_FILE"
        fi

    else
        echo "Could not read setup lock timestamp, removing lock"
        rm -f "$LOCK_FILE"
    fi
fi


# ---------------------------------------------------------
# Je aktívny AP?
# ---------------------------------------------------------

if nmcli -t -f NAME,DEVICE connection show --active \
        | grep -q "^${AP_CONNECTION}:${WIFI_DEVICE}$"; then

    echo "AP mode active"

    last_retry=0

    if [ -f "$AP_LAST_RETRY_FILE" ]; then
        last_retry=$(cat "$AP_LAST_RETRY_FILE" 2>/dev/null)

        # Ochrana proti poškodenému obsahu súboru
        if ! [[ "$last_retry" =~ ^[0-9]+$ ]]; then
            last_retry=0
        fi
    fi

    retry_age=$((now - last_retry))

    if [ "$retry_age" -lt "$AP_RETRY_AFTER" ]; then

        echo "Keeping AP running. Next WiFi retry in $((AP_RETRY_AFTER - retry_age))s"
        exit 0
    fi


    # Ak ešte neexistuje žiadna zákaznícka WiFi,
    # nemá význam AP vôbec zhadzovať.
    if ! saved_wifi_exists; then

        echo "No saved WiFi profiles. Keeping AP running."

        echo "$now" > "$AP_LAST_RETRY_FILE"

        exit 0
    fi


    echo "$now" > "$AP_LAST_RETRY_FILE"

    echo "Trying to return from AP to saved WiFi..."


    if try_saved_wifi; then

        echo "Successfully returned from AP to WiFi"
        exit 0
    fi


    echo "Saved WiFi unavailable. Returning to AP..."

    start_ap

    exit 0
fi


# ---------------------------------------------------------
# Je už pripojená normálna WiFi?
# ---------------------------------------------------------

if nmcli -t -f DEVICE,STATE device \
        | grep -q "^${WIFI_DEVICE}:connected$"; then

    echo "WiFi connected"

    # AP sa po prípadnom reštarte nesmie automaticky zapnúť.
    nmcli connection modify "$AP_CONNECTION" connection.autoconnect no

    rm -f "$FAIL_FILE"
    rm -f "$AP_LAST_RETRY_FILE"

    exit 0
fi


# ---------------------------------------------------------
# Nie je WiFi ani AP
# ---------------------------------------------------------


# Ak neexistuje žiadna uložená zákaznícka WiFi,
# ide napríklad o úplne prvé spustenie zariadenia.
#
# AP preto zapneme okamžite.
if ! saved_wifi_exists; then

    echo "No saved WiFi profiles found. Starting AP immediately."

    rm -f "$FAIL_FILE"

    echo "$now" > "$AP_LAST_RETRY_FILE"

    start_ap

    exit 0
fi


# ---------------------------------------------------------
# Existuje uložená WiFi, ale momentálne nie sme pripojení.
# ---------------------------------------------------------

fail_count=0

if [ -f "$FAIL_FILE" ]; then

    fail_count=$(cat "$FAIL_FILE" 2>/dev/null)

    if ! [[ "$fail_count" =~ ^[0-9]+$ ]]; then
        fail_count=0
    fi
fi


fail_count=$((fail_count + 1))

echo "$fail_count" > "$FAIL_FILE"

echo "WiFi not connected. Fail count: $fail_count/$FAIL_LIMIT"


# Skús uložené siete
if try_saved_wifi; then
    exit 0
fi


# Po dosiahnutí limitu prejdeme do AP režimu
if [ "$fail_count" -ge "$FAIL_LIMIT" ]; then

    echo "WiFi connection failed $FAIL_LIMIT times. Starting AP."

    rm -f "$FAIL_FILE"

    echo "$now" > "$AP_LAST_RETRY_FILE"

    start_ap

else

    echo "Waiting before starting AP..."

fi