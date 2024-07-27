FROM python:3.9-slim

WORKDIR /app

# Copier le fichier ipx800_v1.py
COPY ipx800_v1_addon/ipx800_v1.py /app/ipx800_v1.py

# Copier le script run.sh
COPY ipx800_v1_addon/run.sh /app/run.sh

# Copier le dossier custom_components/ipx800_v1
COPY custom_components/ipx800_v1 /app/custom_components/ipx800_v1

# Copier le requirements.txt
COPY ipx800_v1_addon/requirements.txt /app/requirements.txt

COPY ipx800_v1_addon/websocket_server.py /app/websocket_server.py

# Modifier les permissions des fichiers
RUN chmod -R 755 /app/ipx800_v1.py /app/run.sh /app/custom_components/ipx800_v1
RUN chmod -R 755 /app/websocket_server.py

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt
RUN pip list

RUN pip show flask-cors && pip list

# Rendre run.sh exécutable
RUN chmod +x /app/run.sh

# Commande pour exécuter l'application
CMD ["/app/run.sh"]