#!/bin/bash

echo "Listing of /app/custom_components/ipx800_v1:"
ls -la /app/custom_components/ipx800_v1

echo "Creating directory /config/custom_components/ipx800_v1"
mkdir -p /config/custom_components/ipx800_v1

echo "Checking source files in /app/custom_components/ipx800_v1"
if [ "$(ls -A /app/custom_components/ipx800_v1)" ]; then
    echo "Source files exist, copying..."
    cp -r /app/custom_components/ipx800_v1/* /config/custom_components/ipx800_v1/
    echo "Files copied successfully."
else
    echo "No source files found to copy."
fi

echo "Starting WebSocket server on port 6789"
python /app/ipx800_v1.py &

sleep 5

echo "Installation terminée. Veuillez redémarrer Home Assistant pour terminer la configuration."

wait
