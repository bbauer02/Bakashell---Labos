#!/bin/sh
# Résume un gros fichier de données brutes en trois lignes.
echo "Lignes : $(wc -l < "$1")"
echo "Octets : $(wc -c < "$1")"
echo "Empreinte : $(sha256sum "$1" | cut -c1-16)"
