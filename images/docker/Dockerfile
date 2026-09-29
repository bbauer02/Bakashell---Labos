# Images de base téléchargées à la construction (pas de dépendance à Docker Hub pendant les cours)
FROM gcr.io/go-containerregistry/crane:debug AS images
SHELL ["/busybox/sh", "-c"]
ARG TARGETARCH
RUN mkdir -p /images && \
    for image in hello-world:latest alpine:latest node:20-alpine redis:7-alpine; do \
        crane pull --platform "linux/${TARGETARCH:-amd64}" "$image" "/images/$(echo "$image" | tr ':/' '__').tar"; \
    done
# nginx:alpine lance un processus de travail par cœur VISIBLE (des dizaines sur un serveur), même quand le
# conteneur étudiant est limité à 1 CPU : on fixe 2 processus, pour tenir à 25 conteneurs dans 1,5 Go.
RUN mkdir -p /couche/etc/nginx && \
    crane export --platform "linux/${TARGETARCH:-amd64}" nginx:alpine - | tar -xO etc/nginx/nginx.conf \
      | sed 's/^worker_processes .*/# Salle de TP (mémoire limitée) : 2 processus de travail, et non un par cœur\nworker_processes  2;/' \
      > /couche/etc/nginx/nginx.conf && \
    grep -q '^worker_processes  2;' /couche/etc/nginx/nginx.conf && \
    tar -cf /couche.tar -C /couche etc && \
    crane append --platform "linux/${TARGETARCH:-amd64}" -b nginx:alpine -f /couche.tar -t nginx:alpine -o /images/nginx_alpine.tar

# Conteneur étudiant : un moteur Docker complet, dans le conteneur.
# En production, il tourne sous le runtime Sysbox (isolé, non privilégié).
FROM docker:27-dind

# util-linux-misc : « script », qui permet au banc de test de simuler un terminal pour docker attach
RUN apk add --no-cache bash bash-completion coreutils findutils grep sed curl jq nano vim less procps tree shadow ncurses util-linux-misc

# etudiant : membre du groupe docker (pilote le moteur interne sans sudo)
RUN (getent group docker || addgroup -S docker) && \
    adduser -D -s /bin/bash etudiant && \
    addgroup etudiant docker

COPY --from=images /images /opt/docker-lab/images
COPY projet/ /opt/docker-lab/projet/
COPY fabrique/ /opt/docker-lab/fabrique/
COPY incident/compose.yaml /opt/docker-lab/incident/compose.yaml
COPY incident/Dockerfile.app /opt/docker-lab/incident/app/Dockerfile
COPY projet/api/server.js projet/api/package.json projet/api/produits.json /opt/docker-lab/incident/app/
COPY start.sh /opt/docker-lab/start.sh
COPY banner.sh /etc/profile.d/lab-banner.sh
RUN chmod 755 /opt/docker-lab/start.sh && chmod -R a+rX /opt/docker-lab && \
    find /opt/docker-lab -name '*.sh' -exec chmod 755 {} +

# Moteur accessible uniquement par le socket local (pas de TLS ni de port réseau)
ENV DOCKER_TLS_CERTDIR=

WORKDIR /home/etudiant
ENTRYPOINT []
CMD ["/opt/docker-lab/start.sh"]
