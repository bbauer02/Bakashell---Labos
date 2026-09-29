"""Corrigé du parcours Docker : un script par étape, exécuté en tant qu'« etudiant » (groupe docker) par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
"""

SOLUTIONS = {
    1: r'''
#@ D1.1
# "$(cat …)" insère le contenu du fichier tel quel : ni le « $ » ni l'apostrophe ne sont interprétés
docker run --name premier alpine echo "$(cat ~/message.txt)"
#@ D1.2
docker run -d --name dormeur alpine sleep 3600
# Vu de l'hôte : un processus comme un autre, avec son PID
docker inspect -f '{{.State.Pid}}' dormeur > ~/pid-dormeur.txt
# Vu de l'intérieur : sleep est le processus n°1 du conteneur
docker exec dormeur ps
echo 1 > ~/pid-interne.txt
#@ D1.3
# Deux filtres différents se combinent en ET, deux valeurs de status en OU : on vérifie avant de supprimer
docker ps -a --filter label=equipe=marketing --filter status=exited --filter status=created
docker rm $(docker ps -aq --filter label=equipe=marketing --filter status=exited --filter status=created)
#@ D1.4
docker ps -a --filter name=tache- --format '{{.Names}} {{.Status}}'
# 137 = 128 + 9 : tuée par SIGKILL ; 127 : commande introuvable
docker ps -a --filter name=tache- --format '{{.Names}} {{.Status}}' | grep '(137)' | cut -d' ' -f1 > ~/tuee.txt
docker ps -a --filter name=tache- --format '{{.Names}} {{.Status}}' | grep '(127)' | cut -d' ' -f1 > ~/introuvable.txt
#@ D1.5
for p in poste-1 poste-2 poste-3; do echo "== $p"; docker diff $p; done
# Bruit commun aux trois postes : /root (historique), /tmp, /var/log. L'intrus est ailleurs.
for p in poste-1 poste-2 poste-3; do
  f=$(docker diff $p | awk '$1 == "A" {print $2}' | grep -vE '^/(tmp|root|var/log)/')
  if [ -n "$f" ]; then echo "$p" > ~/poste-compromis.txt; echo "$f" > ~/fichier-depose.txt; fi
done
''',
    2: r'''
#@ D2.1
# Les erreurs sont écrites sur la sortie d'erreur : 2>&1 les fait passer dans le tube
docker logs paiements 2>&1 | grep -c ERREUR > ~/nb-erreurs.txt
docker logs paiements 2>&1 | grep ERREUR | tail -1 | grep -o 'TX-[0-9a-f]*' > ~/derniere-erreur.txt
#@ D2.2
# 10 s d'attente : le shell en PID 1 ignore SIGTERM, il finit tué (code 137)
docker stop traitement-nuit
docker inspect -f '{{.State.ExitCode}}' traitement-nuit > ~/code-sortie.txt
#@ D2.3
# Le conteneur tourne sous l'utilisateur guest, qui n'a pas le droit de lire /secret
docker exec coffre id
docker exec -u root coffre cat /secret/cle.txt > ~/cle-coffre.txt
#@ D2.4
# L'image dit « production », mais le -e du lancement l'emporte : on interroge le conteneur
docker exec coffre printenv ENVIRONNEMENT > ~/env-coffre.txt
#@ D2.5
docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' worker-a worker-b worker-c worker-d
docker stats --no-stream --format '{{.MemPerc}} {{.Name}}' worker-a worker-b worker-c worker-d | sort -rn | head -1 | cut -d' ' -f2 > ~/gourmand.txt
#@ D2.6
# Mémoire ET mémoire + swap (même valeur : pas de swap), et un demi-CPU, à chaud
docker update --memory 128m --memory-swap 128m --cpus 0.5 "$(cat ~/gourmand.txt)"
#@ D2.7
# En salle : docker attach caisse, taper CLOTURE puis Entrée, et se détacher avec Ctrl+P Ctrl+Q.
# Ici, « script » simule le terminal : il envoie CLOTURE, Entrée, puis Ctrl+P Ctrl+Q.
(sleep 1; printf 'CLOTURE\r'; sleep 2; printf '\020\021'; sleep 1) | script -q -c "docker attach caisse" /dev/null > /dev/null
docker logs caisse
#@ D2.8
# Le conteneur est arrêté : pas d'exec, mais diff et cp fonctionnent
docker diff generateur-factures
mkdir -p ~/factures
docker cp generateur-factures:/factures/. ~/factures/
''',
    3: r'''
#@ D3.1
docker run -d --name vitrine -p 8080:80 nginx:alpine
#@ D3.2
docker run -d --name vitrine-site -p 8081:80 -v ~/projet/site:/usr/share/nginx/html:ro nginx:alpine
sleep 2
#@ D3.3
nom=$(docker ps --filter publish=8086 --format '{{.Names}}')
# La page a été déposée dans la couche inscriptible : on la sauve avant de recréer le conteneur
docker diff "$nom"
docker cp "$nom":/usr/share/nginx/html/index.html /tmp/page-flash.html
docker rm -f "$nom"
docker run -d --name "$nom" -p 8087:80 nginx:alpine
docker cp /tmp/page-flash.html "$nom":/usr/share/nginx/html/index.html
docker run -d --name vitrine-promo -p 8086:80 -v ~/projet/site:/usr/share/nginx/html:ro nginx:alpine
sleep 2
#@ D3.4
# Publié sur 127.0.0.1 seulement : injoignable depuis le réseau
docker run -d --name admin-console -p 127.0.0.1:8088:80 nginx:alpine
docker port admin-console
sleep 1
#@ D3.5
# Le conteneur voit encore l'ancien fichier : un bind mount de fichier suit l'inode d'origine, et sed -i en a créé un nouveau
ls -i ~/projet/maintenance/default.conf
docker exec maintenance cat /etc/nginx/conf.d/default.conf
# On monte le DOSSIER : les fichiers remplacés y sont bien visibles
docker rm -f maintenance
docker run -d --name maintenance -p 8089:80 -v ~/projet/maintenance:/etc/nginx/conf.d:ro nginx:alpine
sleep 2
#@ D3.6
docker logs intranet 2>&1 | tail -3
docker top intranet
ls -ln ~/projet/intranet
# Les processus de travail de nginx (uid 101) relèvent des droits des « autres » : lecture et traversée
chmod 755 ~/projet/intranet
chmod 644 ~/projet/intranet/index.html
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
#@ D4.3
# Propriétaire 999 (l'utilisateur redis de l'image), droits 700 : on passe par le moteur, qui est root
ls -ld ~/redis-local
docker run --rm -v ~/redis-local:/d alpine chown -R "$(id -u):$(id -g)" /d
ls -l ~/redis-local
#@ D4.4
# Un volume ne se renomme pas : on copie son contenu dans un nouveau, avec un conteneur jetable
docker volume create stock-archive
docker run --rm -v stock-2024:/de -v stock-archive:/vers alpine cp -a /de/. /vers/
docker run -d --name stock -v stock-archive:/data redis:7-alpine
docker volume rm stock-2024
sleep 2
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
#@ D5.5
# Le conteneur est bien sur la v2… mais un volume rempli par la v1 masque le site de l'image
docker inspect -f '{{.Config.Image}}' vitrine-maison
docker inspect -f '{{range .Mounts}}{{.Name}} -> {{.Destination}}{{end}}' vitrine-maison
docker rm -f vitrine-maison
docker volume rm html-maison
# Le site est livré par l'image : on ne monte rien par-dessus
docker run -d --name vitrine-maison -p 8092:80 vitrine-maison:2
sleep 1
#@ D5.6
# Les tmpfs sont montés « noexec » par défaut
docker run --rm --read-only --tmpfs /work compilateur:1 mount | grep /work || true
docker run --name compilateur --read-only --tmpfs /work:exec compilateur:1
#@ D5.7
docker volume ls -f dangling=true
docker volume ls -f dangling=true -f label=conserver=oui
# Volumes nommés inutilisés, sauf ceux étiquetés conserver=oui
docker volume prune -a -f --filter 'label!=conserver=oui'
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
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY . .
# L'application ne tourne pas en root
USER node
EXPOSE 3000
CMD ["node", "server.js"]
EOF
# Le contexte de construction exclut les dépendances locales et les secrets
printf 'node_modules\n.env\n' > .dockerignore
docker build -t boutique-api:1.0 .
# Un conteneur garde son image : on recrée « api » sur la nouvelle
docker rm -f api
docker run -d --name api -p 3000:3000 --restart unless-stopped boutique-api:1.0
sleep 2
#@ D6.4
# « Restarting (3) » : le programme sort avec le code 3, faute de configuration
docker logs synchro 2>&1 | tail -2
docker rm -f synchro
docker run -d --name synchro --restart on-failure:5 -v ~/projet/synchro:/config:ro synchro-stock:1.0
sleep 2
#@ D6.5
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY . .
USER node
EXPOSE 3000
# wget (BusyBox) est dans l'image, curl non
HEALTHCHECK --interval=10s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "server.js"]
EOF
docker build -t boutique-api:1.0 .
docker rm -f api
docker run -d --name api -p 3000:3000 --restart unless-stopped boutique-api:1.0
sleep 2
#@ D6.6
# Ce que Marc a modifié par rapport à l'image alpine
docker diff bricolage-marc
cd ~/projet/rapport
docker cp bricolage-marc:/usr/local/bin/rapport.sh .
docker cp bricolage-marc:/etc/rapport.conf .
cat > Dockerfile <<'EOF'
FROM alpine
COPY rapport.conf /etc/rapport.conf
COPY rapport.sh /usr/local/bin/rapport.sh
CMD ["rapport.sh"]
EOF
docker build -t rapport:1.0 .
docker run --rm rapport:1.0
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
HEALTHCHECK --interval=10s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "server.js"]
EOF
docker build -t boutique-api:1.0 .
#@ D7.2
cd ~/projet/pointeuse
# exec : le shell est remplacé par node, qui devient le PID 1 et reçoit SIGTERM (c'est la correction essentielle)
sed -i 's/^node pointeuse.js/exec node pointeuse.js/' demarrer.sh
# Forme exec : on ne compte pas sur le shell pour lancer le script
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
HEALTHCHECK --interval=10s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "server.js"]
EOF
docker build --build-arg APP_VERSION=1.1 -t boutique-api:1.1 .
#@ D7.5
cd ~/projet/entree
# Le script prépare la configuration, puis se fait REMPLACER par la commande reçue (le CMD par défaut)
sed -i 's/^node server.js$/exec "$@"/' demarrage.sh
echo 'CMD ["node", "server.js"]' >> Dockerfile
docker build -t api-entree:1.0 .
docker run --rm -e REDIS_HOST=essai api-entree:1.0 cat /tmp/config.json
#@ D7.6
# node en PID 1 sans gestionnaire de SIGTERM ignore le signal : un mini-init (tini) le lui transmet
docker rm -f rapports-nuit
docker run -d --name rapports-nuit --init rapports-nuit:1.0
#@ D7.7
docker images etiqueteuse
docker tag etiqueteuse:1.5 etiqueteuse:latest
docker tag etiqueteuse:1.5 etiqueteuse:1
# Le conteneur garde l'ancienne image : on le recrée
docker rm -f etiqueteuse
docker run -d --name etiqueteuse etiqueteuse:latest
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
#@ D8.5
cd ~/projet/outil-stock
# Le jeton est dans une couche : le RUN le recopie dans /root/.jeton
docker save outil-stock:1.0 | grep -ac "$(cat ~/licences/stock.txt)" || true
sed -i 's|cp /run/secrets/jeton /root/.jeton && ./installer.sh$|./installer.sh /run/secrets/jeton|' Dockerfile
docker build --secret id=jeton,src=$HOME/licences/stock.txt -t outil-stock:1.0 .
#@ D8.6
cd ~/projet/rapport-compact
docker history rapport-compact:1.0
cat > Dockerfile <<'EOF'
FROM alpine
WORKDIR /opt/rapport
COPY compacter.sh .
# Création, utilisation et suppression du fichier brut dans le MÊME RUN : aucune couche ne le contient
RUN yes "Cimes & Sentiers : ventes du jour" | head -c 50000000 > /tmp/brut \
 && ./compacter.sh /tmp/brut > resultat.txt \
 && rm /tmp/brut
CMD ["cat", "resultat.txt"]
EOF
docker build -t rapport-compact:1.0 .
#@ D8.7
# docker save : l'image complète (couches, configuration, tag), et non les seuls fichiers d'un conteneur
mkdir -p ~/livraison
docker save catalogue-web:1.0 | gzip > ~/livraison/catalogue-web.tar.gz
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
#@ D9.3
# Redis seulement sur un réseau interne ; l'API sur un réseau ordinaire (pour publier son port) ET sur l'interne
docker network create --internal reseau-donnees
docker network create reseau-front
docker run -d --name redis-sec --network reseau-donnees redis:7-alpine
docker run -d --name api-sec --network reseau-front -p 3002:3000 -e REDIS_HOST=redis-sec boutique-api:1.0
docker network connect reseau-donnees api-sec
sleep 2
#@ D9.4
# L'API cherche « redis-cache », un nom qui n'existe pas, sur un réseau où Redis n'est pas
docker exec api-diag env | grep REDIS_HOST
docker exec api-diag nslookup redis-cache || true
cache=$(docker ps --format '{{.Names}}' | grep -E '^cache-[a-z]+-[0-9]+$')
reseau=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' api-diag)
# Redis rejoint le réseau de l'API, à chaud, sous le nom attendu
docker network connect --alias redis-cache "$reseau" "$cache"
sleep 1
#@ D9.5
docker run -d --name vitrine-a --network reseau-boutique --network-alias vitrine-interne nginx:alpine
docker run -d --name vitrine-b --network reseau-boutique --network-alias vitrine-interne nginx:alpine
docker run --rm --network reseau-boutique alpine nslookup vitrine-interne
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
docker compose exec -T api wget -qO- http://localhost:3000/visites
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
    # nginx résout « api » à son démarrage : l'API doit exister avant lui
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
docker compose config | grep APP_VERSION
docker compose up -d
sleep 8
#@ D10.5
# Service rattaché à un profil : ignoré par « docker compose up », lancé à la demande
sed -i 's/^volumes:$/  outils:\n    image: redis:7-alpine\n    profiles: [outils]\n\nvolumes:/' compose.yaml
docker compose up -d
docker compose --profile outils run --rm -T outils redis-cli -h redis ping
#@ D10.6
cd ~/stock
# Avec « - /data », chaque nouveau conteneur reçoit un volume anonyme neuf : on nomme le volume
cat > compose.yaml <<'EOF'
# Pile du stock (Diallo) : Redis garde les quantités en stock.
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - stock:/data

volumes:
  stock:
EOF
docker compose up -d
''',
    11: r'''
#@ D11.1
cd ~/incident
sed -i 's/"3000:8090"/"8090:3000"/; s/REDIS_HOTE/REDIS_HOST/' compose.yaml
sed -i 's/serveur\.js/server.js/' app/Dockerfile
docker compose up -d --build
sleep 5
#@ D11.2
docker images -f dangling=true
docker image prune -f
# Une ancienne version résiste : elle est utilisée par un conteneur arrêté
for i in $(docker images -qf dangling=true); do docker ps -a --filter ancestor=$i; done
docker rm brouillon-test
docker image prune -f
#@ D11.3
# Code 137 (SIGKILL) et OOMKilled=true : tué par le noyau, limite mémoire dépassée
docker inspect -f '{{.State.ExitCode}} {{.State.OOMKilled}} {{.HostConfig.Memory}}' import-compta
echo "Tué par le noyau (OOM) : la limite mémoire de 64 Mo est trop basse pour l'import" > ~/cause.txt
docker update --memory 128m --memory-swap 128m import-compta
docker start -a import-compta
#@ D11.4
# Politiques modifiées à chaud, sans recréer les conteneurs
docker update --restart unless-stopped badgeuse supervision
docker update --restart no outil-ponctuel
''',
}
