#!/bin/bash
# Miroir APT interne et intranet de Cimes & Sentiers, servis sur la boucle locale par busybox httpd.
# Idempotent : appelé au démarrage du conteneur et par la mise en place de l'étape sur les paquets.

# /etc/hosts est régénéré par Docker à chaque démarrage : on y remet les noms des deux sites
if ! grep -q 'depot\.cimes\.lan' /etc/hosts; then
    echo '127.0.0.1   depot.cimes.lan intranet.cimes.lan' >> /etc/hosts
fi

# Journal des pages servies par l'intranet (empreinte de chaque réponse)
mkdir -p /var/lib/depot-intranet
chown www-data:www-data /var/lib/depot-intranet
chmod 700 /var/lib/depot-intranet

if ! pgrep -f '^busybox httpd -p 127\.0\.0\.1:80 ' >/dev/null; then
    busybox httpd -p 127.0.0.1:80 -h /srv/depot -u www-data
fi
