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
    && apt-get install -y --reinstall coreutils findutils grep sed tar gzip passwd procps util-linux \
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

COPY start.sh /opt/linux-lab/start.sh
COPY banner.sh /etc/profile.d/lab-banner.sh
RUN chmod 755 /opt/linux-lab/start.sh

WORKDIR /home/etudiant
CMD ["/opt/linux-lab/start.sh"]
