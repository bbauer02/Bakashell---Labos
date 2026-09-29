#!/bin/sh
# Script de démarrage (Marc) : prépare la configuration, puis lance l'API.
echo "{\"redis\": \"${REDIS_HOST:-non configuré}\"}" > /tmp/config.json
echo "Configuration générée dans /tmp/config.json"
node server.js
