#!/bin/bash

sleep 20

if ! lsusb | grep -q "1a86:e396"; then
    logger "SEMA: USB Ethernet missing, rebooting"
    reboot
fi