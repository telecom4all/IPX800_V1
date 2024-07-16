FROM python:3.9-slim

RUN pip install requests

WORKDIR /app



COPY ipx800-v1-addon/ipx800_v1.py /app/ipx800_v1.py
COPY ipx800-v1-addon/run.sh /app/run.sh
COPY custom_components/ipx800_v1 /app/custom_components/ipx800_v1


# Rendre run.sh exécutable
RUN chmod +x /app/run.sh


# Commande pour exécuter l'application
CMD ["/app/run.sh"]
