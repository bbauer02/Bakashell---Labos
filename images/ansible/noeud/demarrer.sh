#!/bin/bash
# Démarrage d'un serveur géré : clés d'hôte propres à chaque serveur, services installés, puis sshd.
ssh-keygen -A >/dev/null
# Serveur neuf : cache APT vide, daté du passé (cache_valid_time juge sa fraîcheur sur la date de ce dossier,
# et la construction de l'image ne conserve pas les dates)
if [ -z "$(ls /var/lib/apt/lists | grep -v '^partial$')" ]; then touch -d '2000-01-01' /var/lib/apt/lists; fi
for s in nginx redis-server; do
    if [ -x /etc/init.d/$s ]; then service $s start >/dev/null 2>&1 || true; fi
done
exec /usr/sbin/sshd -D -e
