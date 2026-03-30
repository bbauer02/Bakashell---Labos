FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# Create restricted user with known password
RUN useradd -m -s /bin/bash etudiant && \
    echo "etudiant:etudiant" | chpasswd

# SSH directory setup
RUN mkdir /run/sshd

# Custom sshd config
COPY sshd_config /etc/ssh/sshd_config

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
