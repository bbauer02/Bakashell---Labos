#!/bin/bash
# Démarrage du conteneur étudiant du parcours Docker : lance le moteur Docker interne.
rm -rf /run/lab-setup /run/lab-ready /run/lab-images-all
mkdir -p /run/lab-setup /var/lib/lab/setup
chmod 700 /var/lib/lab
rm -f /var/run/docker.pid /var/run/docker/containerd/containerd.pid

dockerd-entrypoint.sh dockerd --host=unix:///var/run/docker.sock --group=docker > /var/log/dockerd.log 2>&1 &

for _ in $(seq 1 90); do
    docker info > /dev/null 2>&1 && break
    sleep 1
done

charger() {
    docker image inspect "$1" > /dev/null 2>&1 || docker load -i "/opt/docker-lab/images/$(echo "$1" | tr ':/' '__').tar" > /dev/null
}

# Images de base préchargées. /var/lib/docker est un volume : après le premier démarrage, rien à faire.
if [ -f /var/lib/docker/.lab-images ]; then
    touch /run/lab-ready /run/lab-images-all
else
    # Le jour 1 n'a besoin que d'alpine : l'étudiant peut commencer tout de suite…
    charger alpine:latest
    charger hello-world:latest
    touch /run/lab-ready
    # … pendant que les autres images se chargent en arrière-plan, en priorité basse
    (
        renice -n 19 -p $BASHPID > /dev/null 2>&1
        charger redis:7-alpine
        charger nginx:alpine
        charger node:20-alpine
        touch /var/lib/docker/.lab-images /run/lab-images-all
    ) &
fi

exec sleep infinity
