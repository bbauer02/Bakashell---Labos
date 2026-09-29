"""Corrigé du parcours Docker : un script par étape, exécuté en tant qu'« etudiant » (groupe docker) par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
"""

SOLUTIONS = {
    1: r'''
#@ D1.1
docker run --name premier alpine echo "Bonjour Cimes & Sentiers"
#@ D1.2
docker run -d --name dormeur alpine sleep 3600
docker inspect -f '{{.State.Pid}}' dormeur > ~/pid-dormeur.txt
#@ D1.3
docker rm $(docker ps -aq --filter name=ancien-)
''',
    2: r'''
#@ D2.1
docker logs traitement-nuit | grep CODE-ACCES | cut -d= -f2 > ~/code-acces.txt
#@ D2.2
docker stop -t 2 traitement-nuit
#@ D2.3
docker exec coffre cat /secret/cle.txt > ~/cle-coffre.txt
#@ D2.4
docker exec coffre printenv ENVIRONNEMENT > ~/env-coffre.txt
''',
    3: r'''
#@ D3.1
docker run -d --name vitrine -p 8080:80 nginx:alpine
#@ D3.2
docker run -d --name vitrine-site -p 8081:80 -v ~/projet/site:/usr/share/nginx/html:ro nginx:alpine
sleep 2
''',
    4: r'''
#@ D4.1
docker volume create donnees-boutique
docker run -d --name cache -v donnees-boutique:/data redis:7-alpine redis-server --appendonly yes
sleep 2
docker exec cache redis-cli set promo RANDO10
sleep 1
#@ D4.2
mkdir -p ~/sauvegardes
docker run --rm -v donnees-boutique:/data -v ~/sauvegardes:/backup alpine tar czf /backup/donnees-boutique.tar.gz -C /data .
''',
    5: r'''
#@ D5.1
docker volume create html-vitrine
docker run -d --name vitrine-pleine -p 8082:80 -v html-vitrine:/usr/share/nginx/html nginx:alpine
echo "<h1>Soldes d'été : -20 % sur les sacs</h1>" > /tmp/promo.html
docker cp /tmp/promo.html vitrine-pleine:/usr/share/nginx/html/promo.html
sleep 1
#@ D5.2
docker volume create donnees-restaurees
# Restauration AVANT le démarrage de Redis
docker run --rm -v donnees-restaurees:/data -v ~/sauvegardes:/backup alpine tar xzf /backup/cache-avant-migration.tar.gz -C /data
docker run -d --name cache-restaure -v donnees-restaurees:/data redis:7-alpine redis-server --appendonly yes
sleep 2
#@ D5.3
docker volume ls -f dangling=true
# Sans -a : seuls les volumes anonymes inutilisés sont supprimés
docker volume prune -f
#@ D5.4
# docker logs montre ce que nginx doit écrire : son cache et son fichier PID
docker run -d --name vitrine-ro -p 8083:80 --read-only --tmpfs /var/cache/nginx --tmpfs /run nginx:alpine
sleep 2
''',
    6: r'''
#@ D6.1
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
EOF
docker build -t boutique-api:1.0 .
#@ D6.2
docker run -d --name api -p 3000:3000 --restart unless-stopped boutique-api:1.0
#@ D6.3
# Dockerfile corrigé : utilisateur non-root (et copie de package.json d'abord, pour profiter du cache)
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY package.json ./
COPY . .
USER node
EXPOSE 3000
CMD ["node", "server.js"]
EOF
printf 'node_modules\n.env\n' > .dockerignore
docker build -t boutique-api:1.0 .
# Le conteneur « api » doit être recréé pour utiliser la nouvelle image
docker rm -f api
docker run -d --name api -p 3000:3000 --restart unless-stopped boutique-api:1.0
sleep 2
''',
    7: r'''
#@ D7.1
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
# Les dépendances d'abord : cette couche reste en cache tant que package*.json ne changent pas
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
# Le code ensuite : il change souvent
COPY . .
USER node
EXPOSE 3000
CMD ["node", "server.js"]
EOF
docker build -t boutique-api:1.0 .
#@ D7.2
cd ~/projet/pointeuse
# exec : le shell est remplacé par node, qui devient le PID 1 et reçoit SIGTERM
sed -i 's/^node pointeuse.js/exec node pointeuse.js/' demarrer.sh
# Forme exec : pas de « /bin/sh -c » intermédiaire
sed -i 's|^CMD ./demarrer.sh|CMD ["./demarrer.sh"]|' Dockerfile
docker build -t pointeuse:1.0 .
#@ D7.3
cd ~/projet/export
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY . .
USER node
# Le programme, toujours lancé, et ses arguments par défaut (remplacés par ceux de docker run)
ENTRYPOINT ["node", "export.js"]
CMD ["--format", "texte"]
EOF
docker build -t export-produits:1.0 .
#@ D7.4
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
COPY . .
# Version passée à la construction, placée après npm ci pour ne pas invalider le cache
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
LABEL org.opencontainers.image.version=$APP_VERSION
USER node
EXPOSE 3000
CMD ["node", "server.js"]
EOF
docker build --build-arg APP_VERSION=1.1 -t boutique-api:1.1 .
''',
    8: r'''
#@ D8.1
cd ~/projet/catalogue
cat > Dockerfile <<'EOF'
# Étape 1 : génération du site avec Node
FROM node:20-alpine AS construction
WORKDIR /src
COPY . .
RUN node generer.js

# Étape 2 : l'image finale ne contient que nginx et le résultat
FROM nginx:alpine
COPY --from=construction /src/dist/ /usr/share/nginx/html/
EOF
docker build -t catalogue-web:1.0 .
docker run -d --name catalogue -p 8084:80 catalogue-web:1.0
sleep 1
#@ D8.2
docker history --no-trunc ancienne-api:0.9 | grep -o 'DB_PASSWORD=[^ ]*' | head -1 | cut -d= -f2 > ~/mdp-build.txt
#@ D8.3
mkdir -p /tmp/ancienne-api && cd /tmp/ancienne-api
docker save ancienne-api:0.9 -o image.tar
tar -xf image.tar
# La couche du COPY contient encore le fichier ; celle du RUN ne fait que le masquer
for couche in blobs/sha256/*; do
  tar -xOf "$couche" config/identifiants.txt 2>/dev/null
done | cut -d= -f2 > ~/mdp-couche.txt
#@ D8.4
cd ~/projet/prive
cat > Dockerfile <<'EOF'
FROM alpine
WORKDIR /opt/reassort
COPY activer.sh reassort.sh ./
# La licence n'est montée que pendant ce RUN : elle n'est écrite dans aucune couche
RUN --mount=type=secret,id=licence ./activer.sh /run/secrets/licence
CMD ["./reassort.sh"]
EOF
docker build --secret id=licence,src=$HOME/licences/reassort.txt -t outil-reassort:1.0 .
''',
    9: r'''
#@ D9.1
docker network create reseau-boutique
docker run -d --name redis --network reseau-boutique redis:7-alpine
docker rm -f api
docker run -d --name api --network reseau-boutique -p 3000:3000 -e REDIS_HOST=redis --restart unless-stopped boutique-api:1.0
sleep 2
#@ D9.2
docker network create reseau-legacy
docker network connect reseau-legacy legacy-web
docker network connect reseau-legacy legacy-db
''',
    10: r'''
#@ D10.1
cd ~/projet
# Les conteneurs lancés à la main occupent les noms et les ports : on les supprime
docker rm -f api redis vitrine vitrine-site cache > /dev/null
cat > compose.yaml <<'EOF'
services:
  api:
    build: ./api
    ports:
      - "3000:3000"
    environment:
      REDIS_HOST: redis
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - donnees:/data

volumes:
  donnees:
EOF
docker compose up -d --build
sleep 3
docker compose exec api wget -qO- http://localhost:3000/visites
#@ D10.2
# Ajout du service web ; l'API n'est plus publiée (plus de « ports » sur api)
cat > compose.yaml <<'EOF'
services:
  api:
    build: ./api
    environment:
      REDIS_HOST: redis
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - donnees:/data

  web:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./site:/usr/share/nginx/html:ro
    depends_on:
      - api

volumes:
  donnees:
EOF
docker compose up -d
#@ D10.3
# Healthcheck sur redis, et l'API attend que redis soit « healthy »
cat > compose.yaml <<'EOF'
services:
  api:
    build: ./api
    environment:
      REDIS_HOST: redis
    depends_on:
      redis:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - donnees:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  web:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./site:/usr/share/nginx/html:ro
    depends_on:
      - api

volumes:
  donnees:
EOF
docker compose up -d
#@ D10.4
echo "APP_VERSION=2.0" > .env
# Dans compose.yaml, service api : ajout de la variable, lue dans .env
sed -i 's/      REDIS_HOST: redis/      REDIS_HOST: redis\n      APP_VERSION: ${APP_VERSION}/' compose.yaml
docker compose up -d
sleep 8
''',
    11: r'''
#@ D11.1
cd ~/incident
sed -i 's/"3000:8090"/"8090:3000"/; s/REDIS_HOTE/REDIS_HOST/' compose.yaml
sed -i 's/serveur\.js/server.js/' app/Dockerfile
docker compose up -d --build
sleep 5
#@ D11.2
docker image prune -f
''',
}
