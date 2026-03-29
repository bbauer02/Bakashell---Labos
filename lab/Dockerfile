FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV TERM=xterm-256color

RUN apt-get update && apt-get install -y \
    bash \
    man-db \
    manpages \
    nano \
    vim \
    wget \
    curl \
    tar \
    sudo \
    procps \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Validation scripts
RUN mkdir -p /opt/linux-lab/exercises
COPY exercises/ /opt/linux-lab/exercises/
COPY utils.sh /opt/linux-lab/utils.sh
COPY engine.sh /opt/linux-lab/engine.sh

RUN chmod +x /opt/linux-lab/engine.sh /opt/linux-lab/utils.sh /opt/linux-lab/exercises/*.sh && \
    ln -s /opt/linux-lab/engine.sh /usr/local/bin/check

WORKDIR /home
CMD ["sleep", "infinity"]
