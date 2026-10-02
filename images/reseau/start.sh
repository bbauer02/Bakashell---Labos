#!/bin/bash
# Démarrage de la console : moteur Docker interne, machines du réseau simulé et leurs câbles.
rm -rf /run/lab-setup /run/lab-ready
mkdir -p /run/lab-setup /var/lib/lab/setup /etc/reseau
chmod 700 /var/lib/lab
touch /etc/reseau/machines /etc/reseau/cables /etc/reseau/plan.txt
chmod 644 /etc/reseau/*
rm -f /var/run/docker.pid /var/run/docker/containerd/containerd.pid

dockerd-entrypoint.sh dockerd --host=unix:///var/run/docker.sock > /var/log/dockerd.log 2>&1 &
for _ in $(seq 1 90); do
    docker info > /dev/null 2>&1 && break
    sleep 1
done

# Image des machines (une seule fois : /var/lib/docker est un volume). Changer l'étiquette si son contenu change.
if ! docker image inspect machine-reseau:4 > /dev/null 2>&1; then
    tar -C /opt/reseau-lab/machine -c . | docker import \
        --change 'CMD ["/usr/local/sbin/demarrer-machine"]' --change 'ENV LANG=C.UTF-8' - machine-reseau:4 > /dev/null
fi

# Les machines redémarrent avec le moteur (restart unless-stopped), sans câble : on attend qu'elles tournent,
# puis on rebranche tout
for _ in $(seq 1 30); do
    attendues=$(grep -c . /etc/reseau/machines)
    lancees=$(docker ps -q --filter label=reseau-lab | wc -l)
    [ "$lancees" -ge "$attendues" ] && break
    sleep 1
done
/usr/local/sbin/lab-cablage

touch /run/lab-ready
exec sleep infinity
