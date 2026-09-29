#!/bin/sh
# Active l'outil de réassort avec la licence du fournisseur (fichier passé en argument).
set -e
[ -s "$1" ] || { echo "Licence introuvable : $1" >&2; exit 1; }
grep -q '^LIC-' "$1" || { echo "Licence invalide" >&2; exit 1; }
# Seule l'empreinte de la licence est conservée dans l'image
sha256sum "$1" | cut -c1-16 > /opt/reassort/activation
echo "Outil activé (empreinte $(cat /opt/reassort/activation))"
