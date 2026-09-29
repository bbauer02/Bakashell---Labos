#!/bin/sh
# Tâche de nuit : le mode de traitement est lu dans /mode, déposé avant le démarrage.
echo "Démarrage de la tâche $(hostname)"
set -- $(cat /mode 2>/dev/null)
case "$1" in
    ok) echo "Traitement en cours…"; echo "Traitement terminé" ;;
    erreur) echo "Traitement en cours…"; exit "$2" ;;
    absent) echo "Traitement en cours…"; rapport-nuit --envoi ;;
    *) echo "Traitement en cours…"; sleep 3600 ;;
esac
