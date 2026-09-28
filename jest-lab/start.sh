#!/bin/bash
# Démarrage du conteneur étudiant du parcours Jest.
rm -rf /run/lab-setup
mkdir -p /run/lab-setup /var/lib/lab/setup
chmod 700 /var/lib/lab
rm -rf /var/lib/correcteur/run-* /var/lib/correcteur/resultat-*
exec sleep infinity
