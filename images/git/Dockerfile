FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV TERM=xterm-256color
ENV EDITOR=nano
ENV VISUAL=nano
# git filter-branch (jour 9) : pas d'attente de 10 s avant de commencer (son avertissement reste dans le cours)
ENV FILTER_BRANCH_SQUELCH_WARNING=1

# git-filter-repo : l'outil recommandé pour purger un fichier de tout l'historique (jour 9)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash bash-completion git git-filter-repo nano vim-tiny less tree procps ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Invite qui affiche la branche courante (et * / + s'il y a des modifications)
RUN cat >> /etc/skel/.bashrc <<'RC'

# Parcours Git : branche courante dans l'invite
if [ -f /usr/lib/git-core/git-sh-prompt ]; then
    . /usr/lib/git-core/git-sh-prompt
    GIT_PS1_SHOWDIRTYSTATE=1
    PS1='\[\e[1;32m\]\u@\h\[\e[0m\]:\[\e[1;34m\]\w\[\e[0;33m\]$(__git_ps1 " (%s)")\[\e[0m\]\$ '
fi
RC

# etudiant : travaille dans le terminal et l'éditeur, sans sudo.
# Son identité Git (user.name, user.email) n'est PAS configurée : c'est le premier exercice.
RUN useradd -m -s /bin/bash etudiant

# Configuration système : nano comme éditeur, couleurs. Pas de safe.directory : root ne doit jamais utiliser git dans
# les dépôts de l'étudiant (leurs hooks et leur configuration pourraient exécuter du code en root).
RUN git config --system core.editor nano && \
    git config --system color.ui auto

# Dépôts « distants » de l'équipe : des dépôts nus locaux (pas besoin d'Internet), créés par les mises en place
RUN mkdir -p /srv/git && chown etudiant:etudiant /srv/git

COPY start.sh /opt/git-lab/start.sh
COPY banner.sh /etc/profile.d/lab-banner.sh
RUN chmod 755 /opt/git-lab/start.sh

WORKDIR /home/etudiant
CMD ["/opt/git-lab/start.sh"]
