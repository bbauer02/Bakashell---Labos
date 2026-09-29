#!/bin/bash
# Démarrage du poste de contrôle : moteur Docker interne, dépôt APT interne, noms des serveurs.
rm -rf /run/lab-setup /run/lab-ready
mkdir -p /run/lab-setup /var/lib/lab/setup
chmod 700 /var/lib/lab
rm -f /var/run/docker.pid /var/run/docker/containerd/containerd.pid

dockerd-entrypoint.sh dockerd --host=unix:///var/run/docker.sock > /var/log/dockerd.log 2>&1 &
for _ in $(seq 1 90); do
    docker info > /dev/null 2>&1 && break
    sleep 1
done

# Image des serveurs gérés (une seule fois : /var/lib/docker est un volume)
if ! docker image inspect noeud-cimes:1 > /dev/null 2>&1; then
    tar -C /opt/ansible-lab/noeud -c . | docker import \
        --change 'CMD ["/usr/local/sbin/demarrer-noeud"]' --change 'ENV LANG=C.UTF-8' - noeud-cimes:1 > /dev/null
fi
# Réseau des serveurs : adresses fixes, la passerelle 10.10.0.1 est ce poste
docker network inspect cimes > /dev/null 2>&1 || \
    docker network create --subnet 10.10.0.0/24 --gateway 10.10.0.1 cimes > /dev/null

# Noms des serveurs (le fichier /etc/hosts est recréé à chaque démarrage du conteneur)
cat >> /etc/hosts <<'HOSTS'
10.10.0.11  web1 web1.cimes.lan
10.10.0.12  web2 web2.cimes.lan
10.10.0.13  web3 web3.cimes.lan
10.10.0.21  db1 db1.cimes.lan
10.10.0.1   depot.cimes.lan
HOSTS

# Dépôt APT interne, pour les serveurs
(cd /opt/ansible-lab/depot && exec python3 -m http.server 8000 --bind 10.10.0.1 > /var/log/depot-apt.log 2>&1) &

touch /run/lab-ready
exec sleep infinity
