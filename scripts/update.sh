#!/bin/bash
set -e

cd /home/jan/sema

echo "Pulling latest release..."
git pull

echo "Restarting SEMA service..."
sudo systemctl restart sema

echo "Status:"
sudo systemctl status sema --no-pager