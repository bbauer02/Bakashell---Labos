#!/bin/bash
# Démarrage du conteneur étudiant du parcours Git.
rm -rf /run/lab-setup
mkdir -p /run/lab-setup /var/lib/lab/setup /var/lib/lab/equipe
chmod 700 /var/lib/lab
exec sleep infinity
