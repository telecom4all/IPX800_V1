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

GUNICORN_CONF="/app/gunicorn.conf.py"

cat <<EOL > $GUNICORN_CONF
import logging
import logging.config

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

echo "Starting Flask with Gunicorn"
gunicorn --config $GUNICORN_CONF --bind 0.0.0.0:5213 ipx800_v1:app &

sleep 5

echo "Installation terminée. Veuillez redémarrer Home Assistant pour terminer la configuration."

wait
