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

# Créer le fichier de configuration de Gunicorn
GUNICORN_CONF="/app/gunicorn.conf.py"

cat <<EOL > $GUNICORN_CONF
import logging
import logging.config

# Configuration de la journalisation avec horodatage
logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s:%(name)s:%(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

def on_starting(server):
    logging.config.dictConfig(logging_config)

def post_fork(server, worker):
    logging.config.dictConfig(logging_config)
EOL

# Démarrer l'application Flask avec Gunicorn
echo "Starting Flask with Gunicorn"
gunicorn --config $GUNICORN_CONF --bind 0.0.0.0:5213 ipx800_v1:app &

# Attendre que l'application Flask démarre correctement
sleep 5

# Afficher un message à l'utilisateur pour redémarrer Home Assistant
echo "L'installation est terminée. Veuillez redémarrer Home Assistant pour terminer la configuration."

# Continuer à exécuter Gunicorn en premier plan
wait

