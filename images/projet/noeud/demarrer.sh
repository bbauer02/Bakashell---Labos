#!/bin/bash
# Démarrage d'un serveur géré : clés d'hôte propres à chaque serveur, services activés au démarrage, puis sshd.
ssh-keygen -A >/dev/null
# Serveur neuf : cache APT vide, daté du passé (cache_valid_time juge sa fraîcheur sur la date de ce dossier)
if [ -z "$(ls /var/lib/apt/lists | grep -v '^partial$')" ]; then touch -d '2000-01-01' /var/lib/apt/lists; fi
/usr/local/sbin/services-au-demarrage
exec /usr/sbin/sshd -D -e
