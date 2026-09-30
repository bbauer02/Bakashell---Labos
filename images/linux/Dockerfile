FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV TERM=xterm-256color

# L'image ubuntu est "minimisée" : sans ceci, `man` n'affiche rien.
RUN rm -f /etc/dpkg/dpkg.cfg.d/excludes && \
    if [ "$(dpkg-divert --truename /usr/bin/man)" = "/usr/bin/man.REAL" ]; then \
        rm -f /usr/bin/man && dpkg-divert --quiet --remove --rename /usr/bin/man; \
    fi

RUN apt-get update && apt-get install -y \
    bash \
    man-db \
    manpages \
    less \
    nano \
    vim \
    wget \
    curl \
    tar \
    sudo \
    procps \
    psmisc \
    lsof \
    file \
    jq \
    findutils \
    gawk \
    sed \
    iproute2 \
    iputils-ping \
    net-tools \
    netcat-openbsd \
    gzip \
    zip \
    unzip \
    cron \
    rsyslog \
    logrotate \
    openssh-client \
    openssh-server \
    sshpass \
    && apt-get install -y --reinstall coreutils findutils grep sed tar gzip passwd procps util-linux mount e2fsprogs \
       bash dpkg apt adduser debianutils login \
    && rm -rf /var/lib/apt/lists/*

# Utilisateur étudiant : sudoer avec mot de passe (on apprend à utiliser sudo)
RUN useradd -m -s /bin/bash -G sudo etudiant && \
    echo "etudiant:etudiant" | chpasswd && \
    echo 'Defaults timestamp_timeout=60' > /etc/sudoers.d/lab && \
    chmod 440 /etc/sudoers.d/lab

# rsyslog sans accès au noyau (impossible en conteneur)
RUN sed -i '/imklog/s/^/#/' /etc/rsyslog.conf

# sshd n'écoute que sur la boucle locale : les conteneurs ne sont pas joignables entre eux
RUN mkdir -p /run/sshd && \
    printf 'ListenAddress 127.0.0.1\nListenAddress ::1\n' > /etc/ssh/sshd_config.d/00-lab.conf

# Miroir APT interne et intranet de l'entreprise, servis sur la boucle locale par busybox httpd :
# les exercices sur apt et sur wget/curl fonctionnent sans accès à Internet. Les paquets proposés
# aux étudiants, et celles de leurs dépendances qui manquent à l'image, sont téléchargés ici, à la
# construction ; les sources Ubuntu sont ensuite remplacées par ce miroir.
COPY depot/ /opt/linux-lab/depot/
RUN set -e; \
    P="tree cowsay figlet sl ncdu htop"; \
    D=/srv/depot/ubuntu; A=$(dpkg --print-architecture); \
    apt-get update; \
    apt-get install -y busybox apt-utils; \
    maj=$(apt-get install -s $P | awk '/^Inst [^ ]+ \[/ {print $2}'); \
    if [ -n "$maj" ]; then apt-get install -y --only-upgrade $maj; fi; \
    # Dépendances que cowsay installe et qu'apt autoremove retirera (apt garde les paquets de priorité « required »)
    for p in $(apt-get install -s cowsay | awk '/^Inst/ && $2 != "cowsay" {print $2}'); do \
        apt-cache show "$p" | grep -qE '^Priority: (required|important)' || echo "$p"; \
    done > /opt/linux-lab/depot/dependances-cowsay; \
    test -s /opt/linux-lab/depot/dependances-cowsay; \
    mkdir -p $D/pool/main $D/dists/jammy/main/binary-$A /tmp/debs/partial; \
    apt-get install -y --download-only -o Dir::Cache::Archives=/tmp/debs $P; \
    mv /tmp/debs/*.deb $D/pool/main/; \
    cd $D; \
    apt-ftparchive packages pool > dists/jammy/main/binary-$A/Packages; \
    gzip -9kn dists/jammy/main/binary-$A/Packages; \
    apt-ftparchive -o APT::FTPArchive::Release::Origin="Cimes et Sentiers" \
        -o APT::FTPArchive::Release::Label="Miroir interne" -o APT::FTPArchive::Release::Suite=jammy \
        -o APT::FTPArchive::Release::Codename=jammy -o APT::FTPArchive::Release::Architectures=$A \
        -o APT::FTPArchive::Release::Components=main release dists/jammy > dists/jammy/Release; \
    apt-get purge -y apt-utils; \
    mv /etc/apt/sources.list /opt/linux-lab/depot/sources.list.ubuntu; \
    cp /opt/linux-lab/depot/sources.list /etc/apt/sources.list; \
    mkdir -p /srv/depot/cgi-bin; \
    cp /opt/linux-lab/depot/index.cgi /srv/depot/cgi-bin/index.cgi; \
    sed -i 's/\r$//' /opt/linux-lab/depot/*.sh /srv/depot/cgi-bin/index.cgi; \
    chmod 755 /opt/linux-lab/depot/demarrer.sh /srv/depot/cgi-bin/index.cgi; \
    chmod -R a+rX /srv/depot; \
    rm -rf /var/lib/apt/lists/* /tmp/debs; \
    apt-get clean

COPY start.sh /opt/linux-lab/start.sh
COPY banner.sh /etc/profile.d/lab-banner.sh
RUN chmod 755 /opt/linux-lab/start.sh

WORKDIR /home/etudiant
CMD ["/opt/linux-lab/start.sh"]
