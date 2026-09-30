#!/bin/bash
# Démarrage du conteneur étudiant : services utilisés par les exercices.

# Les mises en place "volatiles" (processus lancés par un exercice) sont
# rejouées après chaque redémarrage du conteneur.
rm -rf /run/lab-setup
mkdir -p /run/lab-setup /var/lib/lab/setup /var/lib/lab/ref
chmod 700 /var/lib/lab

rm -f /run/rsyslogd.pid /run/crond.pid /run/sshd.pid
ssh-keygen -A >/dev/null 2>&1
mkdir -p /run/sshd
/usr/sbin/sshd
rsyslogd
cron
# Miroir APT interne et intranet (sans Internet)
/opt/linux-lab/depot/demarrer.sh

exec sleep infinity
