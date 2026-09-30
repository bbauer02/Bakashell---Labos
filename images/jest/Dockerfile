# Node 24 : version LTS maintenue (Node 20 est en fin de vie depuis avril 2026)
FROM node:24-bookworm-slim

ENV LANG=C.UTF-8
ENV TERM=xterm-256color

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash nano vim less procps ca-certificates git tree \
    && rm -rf /var/lib/apt/lists/*

# L'image node fournit l'utilisateur « node » (uid 1000) : on crée les nôtres à côté.
# etudiant : travaille dans le terminal et l'éditeur, sans sudo.
# correcteur : exécute les tests pendant les vérifications, dans un bac à sable.
RUN useradd -m -s /bin/bash etudiant && \
    useradd -r -m -d /var/lib/correcteur -s /usr/sbin/nologin correcteur && \
    chmod 700 /var/lib/correcteur

# Jest installé une fois pour toutes (pas besoin d'Internet en cours), versions figées par package-lock.json
WORKDIR /opt/jest-lab
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund && npm cache clean --force && chmod -R a+rX /opt/jest-lab

# Fichiers privés : code de référence, mutants, variantes, tests cachés, correcteur (root uniquement)
COPY ref/ private/ref/
COPY student/ private/student/
COPY hidden/ private/hidden/
COPY mutants.json private/mutants.json
COPY variantes.json private/variantes.json
COPY verifier.js verifier.js
RUN chown -R root:root private verifier.js && chmod -R go-rwx private verifier.js

COPY start.sh /opt/jest-lab/start.sh
COPY banner.sh /etc/profile.d/lab-banner.sh
RUN chmod 755 /opt/jest-lab/start.sh

WORKDIR /home/etudiant
CMD ["/opt/jest-lab/start.sh"]
