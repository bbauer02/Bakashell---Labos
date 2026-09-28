# Images de base téléchargées à la construction (pas de dépendance à Docker Hub pendant les cours)
FROM gcr.io/go-containerregistry/crane:debug AS images
SHELL ["/busybox/sh", "-c"]
ARG TARGETARCH
RUN mkdir -p /images && \
    for image in hello-world:latest alpine:latest nginx:alpine node:20-alpine redis:7-alpine; do \
        crane pull --platform "linux/${TARGETARCH:-amd64}" "$image" "/images/$(echo "$image" | tr ':/' '__').tar"; \
    done

# Conteneur étudiant : un moteur Docker complet, dans le conteneur.
# En production, il tourne sous le runtime Sysbox (isolé, non privilégié).
FROM docker:27-dind

RUN apk add --no-cache bash bash-completion coreutils findutils grep sed curl jq nano vim less procps tree shadow ncurses

# etudiant : membre du groupe docker (pilote le moteur interne sans sudo)
RUN (getent group docker || addgroup -S docker) && \
    adduser -D -s /bin/bash etudiant && \
    addgroup etudiant docker

COPY --from=images /images /opt/docker-lab/images
COPY projet/ /opt/docker-lab/projet/
COPY incident/compose.yaml /opt/docker-lab/incident/compose.yaml
COPY incident/Dockerfile.app /opt/docker-lab/incident/app/Dockerfile
COPY projet/api/server.js projet/api/package.json projet/api/produits.json /opt/docker-lab/incident/app/
COPY start.sh /opt/docker-lab/start.sh
COPY banner.sh /etc/profile.d/lab-banner.sh
RUN chmod 755 /opt/docker-lab/start.sh && chmod -R a+rX /opt/docker-lab

# Moteur accessible uniquement par le socket local (pas de TLS ni de port réseau)
ENV DOCKER_TLS_CERTDIR=

WORKDIR /home/etudiant
ENTRYPOINT []
CMD ["/opt/docker-lab/start.sh"]
