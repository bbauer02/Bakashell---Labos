#!/bin/sh
# Installe l'outil de stock : vérifie le jeton du fournisseur.
# Usage : ./installer.sh [fichier du jeton]   (par défaut : /root/.jeton)
set -e
jeton=${1:-/root/.jeton}
[ -s "$jeton" ] || { echo "Jeton introuvable : $jeton" >&2; exit 1; }
# Seule l'empreinte du jeton est conservée
sha256sum "$jeton" | cut -c1-16 > /opt/stock/installe
echo "Outil installé (empreinte $(cat /opt/stock/installe))"
