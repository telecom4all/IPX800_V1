#!/bin/bash

# Affichage des répertoires pour le débogage
echo "Listing of /app/custom_components/ipx800_v1:"
ls -la /app/custom_components/ipx800_v1

# Créez le répertoire si nécessaire
echo "Creating directory /config/custom_components/ipx800_v1"
mkdir -p /config/custom_components/ipx800_v1

# Vérification de l'existence des fichiers sources
echo "Checking source files in /app/custom_components/ipx800_v1"
if [ "$(ls -A /app/custom_components/ipx800_v1)" ]; then
    echo "Source files exist, copying..."
    cp -r /app/custom_components/ipx800_v1/* /config/custom_components/ipx800_v1/
    echo "Files copied successfully."
else
    echo "No source files found to copy."
fi

# Start the main script
echo "Starting the IPX800 script"
python3 /app/ipx800_v1.py &

# Afficher un message à l'utilisateur pour redémarrer Home Assistant
echo "Installation is complete. Please restart Home Assistant to complete the setup."

# Keep the script running
wait
