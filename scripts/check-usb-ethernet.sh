#!/bin/bash

ADAPTER_IDS=(
    "1a86:e396"
    "0fe6:9702"
    # "abcd:1234"
)

COUNT_FILE="/var/tmp/sema-usb-eth-reboot-count"
MAX_REBOOTS=3

sleep 20

for adapter_id in "${ADAPTER_IDS[@]}"; do
    if lsusb | grep -qi "$adapter_id"; then
        logger "SEMA: USB Ethernet found: $adapter_id"
        rm -f "$COUNT_FILE"
        exit 0
    fi
done

count=0

if [ -f "$COUNT_FILE" ]; then
    count=$(cat "$COUNT_FILE")
fi

count=$((count + 1))
echo "$count" > "$COUNT_FILE"

logger "SEMA: USB Ethernet missing. Reboot attempt $count/$MAX_REBOOTS"

if [ "$count" -le "$MAX_REBOOTS" ]; then
    reboot
else
    logger "SEMA: USB Ethernet still missing after $MAX_REBOOTS attempts. Giving up."
    exit 1
fi