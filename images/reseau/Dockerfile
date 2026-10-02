# ─── Machines du réseau simulé (postes, imprimante, switch…) : Debian minimale et outils réseau ──────
# Leur système de fichiers est importé dans le moteur Docker de l'étudiant au premier démarrage.
FROM debian:bookworm-slim AS machine
RUN apt-get update && apt-get install -y --no-install-recommends \
        iproute2 iputils-ping iputils-arping ifupdown procps nano less bash-completion \
    && rm -rf /var/lib/apt/lists/*
COPY noeud/demarrer.sh /usr/local/sbin/demarrer-machine
COPY noeud/accueil.sh /etc/profile.d/lab-accueil.sh
RUN chmod 755 /usr/local/sbin/demarrer-machine && \
    echo 'export PS1="\[\e[1;31m\]root@\h\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]# "' >> /root/.bashrc

# ─── Console du technicien : moteur Docker interne qui fait tourner les machines, et leurs câbles ────
FROM docker:27-dind
RUN apk add --no-cache bash bash-completion coreutils findutils grep sed jq nano less ncurses procps \
        iproute2 iputils util-linux-misc sudo shadow
# etudiant n'est PAS dans le groupe docker : il n'atteint les machines que par « connexion » (sudo, liste fermée)
RUN adduser -D -s /bin/bash etudiant && \
    printf 'etudiant ALL=(root) NOPASSWD: /usr/local/sbin/lab-machine\n' > /etc/sudoers.d/machines && \
    chmod 440 /etc/sudoers.d/machines
COPY --from=machine / /opt/reseau-lab/machine/
COPY start.sh /opt/reseau-lab/start.sh
COPY banner.sh /etc/profile.d/lab-banner.sh
COPY sbin/ /usr/local/sbin/
COPY bin/ /usr/local/bin/
RUN chmod 755 /opt/reseau-lab/start.sh /usr/local/sbin/lab-machine /usr/local/sbin/lab-cablage \
        /usr/local/bin/connexion /usr/local/bin/redemarrer /usr/local/bin/plan
ENV DOCKER_TLS_CERTDIR=
WORKDIR /home/etudiant
ENTRYPOINT []
CMD ["/opt/reseau-lab/start.sh"]
