#!/bin/bash

# Créez le répertoire si nécessaire
mkdir -p /config/custom_components/ipx800_v1

# Copiez le composant personnalisé dans le répertoire custom_components de Home Assistant
cp -r /app/custom_components/ipx800_v1/* /config/custom_components/ipx800_v1/


# Start the cron job for updating prices
python3 /app/ipx800_v1.py &


# Afficher un message à l'utilisateur pour redémarrer Home Assistant
echo "L'installation est terminée. Veuillez redémarrer Home Assistant pour terminer la configuration."

# Continuer à exécuter Gunicorn en premier plan
wait