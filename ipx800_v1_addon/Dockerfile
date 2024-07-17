FROM python:3.9-slim

WORKDIR /app

COPY ipx800_v1_addon/ipx800_v1.py /app/ipx800_v1.py
COPY ipx800_v1_addon/ipx800_v1.py /app/ipx800_v1/ipx800_v1.py
COPY ipx800_v1_addon/run.sh /app/run.sh
COPY custom_components/ipx800_v1 /app/custom_components/ipx800_v1
COPY ipx800_v1_addon/requirements.txt /app/requirements.txt

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt
RUN pip list

# Rendre run.sh exécutable
RUN chmod +x /app/run.sh

# Commande pour exécuter l'application
CMD ["/app/run.sh"]
