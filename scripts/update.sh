#!/bin/bash
set -e

cd /home/jan/sema

echo "Fetching latest release..."
git fetch origin

echo "Resetting to origin/main..."
git reset --hard origin/main

echo "Restarting SEMA service..."
sudo systemctl restart sema

echo "Status:"
sudo systemctl status sema --no-pager