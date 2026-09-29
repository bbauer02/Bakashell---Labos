#!/bin/sh
# Synchronisation du stock avec l'entrepôt : lit sa configuration dans /config/stock.conf.
if [ ! -f /config/stock.conf ]; then
    echo "Erreur : /config/stock.conf introuvable" >&2
    exit 3
fi
echo "Synchro OK : $(cat /config/stock.conf)"
exec sleep infinity
