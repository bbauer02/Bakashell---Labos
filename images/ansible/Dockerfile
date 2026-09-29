# ─── Serveurs gérés (web1, web2, db1…) : Debian minimale avec SSH, Python et sudo ────────────────
# Leur système de fichiers est importé dans le moteur Docker de l'étudiant au premier démarrage.
FROM debian:bookworm-slim AS noeud
RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server python3 python3-apt sudo procps curl ca-certificates less nano iproute2 \
    && rm -rf /var/lib/apt/lists/*
# Compte d'administration des serveurs : mot de passe pour le premier contact, sudo sans mot de passe
RUN useradd -m -s /bin/bash admin && echo 'admin:cimes' | chpasswd && \
    echo 'admin ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/admin && chmod 440 /etc/sudoers.d/admin && \
    rm -f /etc/ssh/ssh_host_* && mkdir -p /run/sshd
# Journal de sudo (horodaté, une ligne par commande) : les vérifications y distinguent ce qu'Ansible a fait
# (« BECOME-SUCCESS ») d'une commande tapée à la main en SSH
RUN printf 'Defaults logfile=/var/log/sudo.log\nDefaults loglinelen=0\n' > /etc/sudoers.d/journal && \
    chmod 440 /etc/sudoers.d/journal && visudo -c >/dev/null
COPY noeud/demarrer.sh /usr/local/sbin/demarrer-noeud
RUN chmod 755 /usr/local/sbin/demarrer-noeud

# ─── Dépôt APT interne (depot.cimes.lan) : les paquets du parcours et leurs dépendances ──────────
FROM noeud AS depot
RUN apt-get update && mkdir -p /depot && \
    apt-get install -y --download-only nginx redis-server tree htop rsync unzip && \
    mv /var/cache/apt/archives/*.deb /depot/ && \
    apt-get install -y --no-install-recommends dpkg-dev && \
    cd /depot && dpkg-scanpackages --multiversion . > Packages && gzip -k Packages

# Les serveurs n'utilisent que le dépôt interne : le parcours fonctionne sans Internet.
# Cache APT vide, comme sur un serveur neuf : le premier « apt » doit rafraîchir la liste (update_cache).
FROM noeud AS noeud-final
RUN rm -f /etc/apt/sources.list.d/* && \
    echo 'deb [trusted=yes] http://depot.cimes.lan:8000 ./' > /etc/apt/sources.list && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*.bin

# ─── Poste de contrôle de l'étudiant : Ansible + moteur Docker interne qui fait tourner les serveurs ─
FROM docker:27-dind
RUN apk add --no-cache bash bash-completion coreutils findutils grep sed curl jq nano vim less procps tree \
        shadow ncurses openssh-client sshpass python3 py3-yaml 'ansible-core~2.18'
# ansible-core est figé en 2.18 : la 2.19 change l'évaluation des conditions (when) et des modèles, et le parcours
# (notamment le piège des booléens du jour 6) est écrit et vérifié pour cette version.
# etudiant n'est PAS dans le groupe docker : pour lui, web1, web2… sont de vrais serveurs, joignables en SSH
RUN adduser -D -s /bin/bash etudiant
COPY --from=noeud-final / /opt/ansible-lab/noeud/
COPY --from=depot /depot /opt/ansible-lab/depot/
COPY start.sh /opt/ansible-lab/start.sh
COPY banner.sh /etc/profile.d/lab-banner.sh
# Python des serveurs trouvé automatiquement, sans avertissement à chaque commande (aussi après « su - »)
RUN chmod 755 /opt/ansible-lab/start.sh && \
    echo 'export ANSIBLE_PYTHON_INTERPRETER=auto_silent' > /etc/profile.d/ansible.sh
ENV ANSIBLE_PYTHON_INTERPRETER=auto_silent
ENV DOCKER_TLS_CERTDIR=
WORKDIR /home/etudiant
ENTRYPOINT []
CMD ["/opt/ansible-lab/start.sh"]
