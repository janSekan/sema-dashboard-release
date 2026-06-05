#!/bin/bash

echo "=== SEMA SERVICE ==="
systemctl status sema --no-pager

echo
echo "=== WIFI WATCH TIMER ==="
systemctl status sema-wifi-watch.timer --no-pager

echo
echo "=== NETWORK ==="
nmcli device

echo
echo "=== TAILSCALE ==="
tailscale status

echo
echo "=== IP ADDRESSES ==="
ip -4 addr