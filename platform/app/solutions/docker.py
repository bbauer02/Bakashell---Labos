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
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
EOF
docker build -t boutique-api:1.0 .
#@ D5.2
docker run -d --name api -p 3000:3000 --restart unless-stopped boutique-api:1.0
#@ D5.3
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
    6: r'''
#@ D6.1
docker network create reseau-boutique
docker run -d --name redis --network reseau-boutique redis:7-alpine
docker rm -f api
docker run -d --name api --network reseau-boutique -p 3000:3000 -e REDIS_HOST=redis --restart unless-stopped boutique-api:1.0
sleep 2
''',
    7: r'''
#@ D7.1
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
#@ D7.2
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
#@ D7.3
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
#@ D7.4
echo "APP_VERSION=2.0" > .env
# Dans compose.yaml, service api : ajout de la variable, lue dans .env
sed -i 's/      REDIS_HOST: redis/      REDIS_HOST: redis\n      APP_VERSION: ${APP_VERSION}/' compose.yaml
docker compose up -d
sleep 8
''',
    8: r'''
#@ D8.1
cd ~/incident
sed -i 's/"3000:8090"/"8090:3000"/; s/REDIS_HOTE/REDIS_HOST/' compose.yaml
sed -i 's/serveur\.js/server.js/' app/Dockerfile
docker compose up -d --build
sleep 5
#@ D8.2
docker image prune -f
''',
}
