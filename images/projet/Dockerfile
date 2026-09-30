# Projet final (épreuve de synthèse) : poste de contrôle du parcours Ansible, enrichi de Git, Node + Jest et d'un
# serveur de construction Docker. Tout ce qui sert pendant l'épreuve est intégré à l'image : elle se déroule sans
# Internet.

# ─── Serveurs gérés (web1, web2, web3) : Debian minimale avec SSH, Python et sudo (comme le parcours Ansible) ─────
FROM debian:bookworm-slim AS noeud
RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server python3 python3-apt sudo procps curl ca-certificates less nano iproute2 psmisc lsof \
    && rm -rf /var/lib/apt/lists/*
# Compte d'administration des serveurs : mot de passe pour le premier contact, sudo sans mot de passe
RUN useradd -m -s /bin/bash admin && echo 'admin:cimes' | chpasswd && \
    echo 'admin ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/admin && chmod 440 /etc/sudoers.d/admin && \
    rm -f /etc/ssh/ssh_host_* && mkdir -p /run/sshd
# Journal de sudo : les vérifications y distinguent ce qu'Ansible a fait (« BECOME-SUCCESS ») d'une commande tapée
# à la main en SSH
RUN printf 'Defaults logfile=/var/log/sudo.log\nDefaults loglinelen=0\n' > /etc/sudoers.d/journal && \
    chmod 440 /etc/sudoers.d/journal && visudo -c >/dev/null
COPY noeud/demarrer.sh /usr/local/sbin/demarrer-noeud
COPY noeud/services-au-demarrage.sh /usr/local/sbin/services-au-demarrage
RUN chmod 755 /usr/local/sbin/demarrer-noeud /usr/local/sbin/services-au-demarrage

# ─── Dépôt APT interne (depot.cimes.lan) : Node.js, nginx et leurs dépendances ────────────────────────────────
FROM noeud AS depot
RUN apt-get update && mkdir -p /depot && \
    apt-get install -y --download-only nodejs nginx && \
    mv /var/cache/apt/archives/*.deb /depot/ && \
    apt-get install -y --no-install-recommends dpkg-dev && \
    cd /depot && dpkg-scanpackages --multiversion . > Packages && gzip -k Packages

# Les serveurs n'utilisent que le dépôt interne. Cache APT vide, comme sur un serveur neuf.
FROM noeud AS noeud-final
RUN rm -f /etc/apt/sources.list.d/* && \
    echo 'deb [trusted=yes] http://depot.cimes.lan:8000 ./' > /etc/apt/sources.list && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*.bin

# ─── Images Docker intégrées : le moteur du serveur de construction ci1, et l'image de base de l'API ─────────
FROM gcr.io/go-containerregistry/crane:debug AS images
SHELL ["/busybox/sh", "-c"]
ARG TARGETARCH
RUN mkdir -p /images && \
    for image in docker:27-dind node:24-alpine; do \
        crane pull --platform "linux/${TARGETARCH:-amd64}" "$image" "/images/$(echo "$image" | tr ':/' '__').tar"; \
    done

# ─── Projet de l'API : verrou npm (package-lock.json) et Jest, préparés ici avec accès à Internet ────────────
FROM node:24-alpine AS boutique
WORKDIR /boutique
COPY boutique/package.json ./
RUN sed -i 's/{{VERSION}}/0.0.0/' package.json && \
    npm install --package-lock-only --no-audit --no-fund && npm ci --no-audit --no-fund

# ─── Poste de contrôle de l'étudiant ─────────────────────────────────────────────────────────────────────────
FROM docker:27-dind
RUN apk add --no-cache bash bash-completion coreutils findutils grep sed curl jq nano vim less procps tree \
        shadow ncurses openssh-client sshpass python3 py3-yaml 'ansible-core~2.18' git nodejs npm runuser
# etudiant n'est PAS dans le groupe docker : les serveurs de l'entreprise sont pour lui des machines distantes.
# Son moteur Docker est celui du serveur de construction ci1 (variable DOCKER_HOST).
# correcteur : exécute les tests Jest de l'étudiant pendant les vérifications, dans un bac à sable.
RUN adduser -D -s /bin/bash etudiant && \
    adduser -S -D -H -h /var/lib/correcteur -s /sbin/nologin correcteur && addgroup -S correcteur && \
    adduser correcteur correcteur && mkdir -p /var/lib/correcteur && \
    chown correcteur:correcteur /var/lib/correcteur && chmod 700 /var/lib/correcteur && \
    mkdir -p /srv/git && chown etudiant:etudiant /srv/git
COPY --from=noeud-final / /opt/projet-lab/noeud/
COPY --from=depot /depot /opt/projet-lab/depot/
COPY --from=images /images /opt/projet-lab/images/
# Jest (lisible par tous) ; modèle du projet, variantes, tests cachés et correcteur (root uniquement)
COPY --from=boutique /boutique/node_modules /opt/projet-lab/node_modules/
COPY boutique/ /opt/projet-lab/prive/boutique/
COPY --from=boutique /boutique/package-lock.json /opt/projet-lab/prive/boutique/package-lock.json
COPY prive/ /opt/projet-lab/prive/
COPY correcteur.js /opt/projet-lab/correcteur.js
COPY start.sh /opt/projet-lab/start.sh
COPY banner.sh /etc/profile.d/lab-banner.sh
RUN chmod -R a+rX /opt/projet-lab/node_modules && chmod 755 /opt/projet-lab /opt/projet-lab/start.sh && \
    chown -R root:root /opt/projet-lab/prive /opt/projet-lab/correcteur.js && \
    chmod -R go-rwx /opt/projet-lab/prive /opt/projet-lab/correcteur.js && \
    chmod 755 /opt/projet-lab/prive/boutique/deploiement/api-boutique && \
    printf 'export ANSIBLE_PYTHON_INTERPRETER=auto_silent\nexport DOCKER_HOST=tcp://ci1:2375\n' > /etc/profile.d/projet.sh
ENV ANSIBLE_PYTHON_INTERPRETER=auto_silent
ENV DOCKER_HOST=tcp://ci1:2375
ENV DOCKER_TLS_CERTDIR=
WORKDIR /home/etudiant
ENTRYPOINT []
CMD ["/opt/projet-lab/start.sh"]
