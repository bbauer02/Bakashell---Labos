"""Parcours « Docker : conteneuriser la boutique » (révision des bases).

Chaque étudiant dispose de son propre moteur Docker, à l'intérieur de son conteneur
(runtime Sysbox en production). Les vérifications interrogent ce moteur : docker inspect,
appels HTTP aux services, reconstruction de l'image, relance des conteneurs…
"""

EXERCISES_VERSION = "1"

MENTOR = "lea"

SETUP_PRELUDE = r'''
set -e
H=/home/etudiant
P=$H/projet
emit() { echo "@$1=$2"; }
own() { chown -R etudiant:etudiant "$@"; }
WORDS=(pingouin cactus volcan boussole lanterne marmotte horizon galaxie origami tambour)
rword() { echo "${WORDS[RANDOM % ${#WORDS[@]}]}-$((RANDOM % 900 + 100))"; }
# Attend que le moteur Docker interne soit prêt (premier démarrage : chargement des images)
for _ in $(seq 1 150); do [ -f /run/lab-ready ] && docker info >/dev/null 2>&1 && break; sleep 1; done
docker info >/dev/null 2>&1 || { echo "Le moteur Docker ne répond pas" >&2; exit 1; }
# Livre des éléments du projet (sans écraser le travail de l'étudiant)
livrer() { mkdir -p "$P"; for x in "$@"; do cp -rn "/opt/docker-lab/projet/$x" "$P/"; done; own "$P"; }
# Images de base : attend la fin du chargement initial, puis recharge celles qui auraient été supprimées
images_de_base() {
  for _ in $(seq 1 120); do [ -f /run/lab-images-all ] && break; sleep 1; done
  for img in hello-world:latest alpine:latest nginx:alpine node:20-alpine redis:7-alpine; do
    docker image inspect "$img" >/dev/null 2>&1 || docker load -i "/opt/docker-lab/images/$(echo "$img" | tr ':/' '__').tar" >/dev/null
  done
}
'''

CHECK_PRELUDE = r'''
H=/home/etudiant
P=$H/projet
ans() { tr -d '[:space:]' < "$1" 2>/dev/null; }
insp() { docker inspect -f "$2" "$1" 2>/dev/null; }
running() { [ "$(insp "$1" '{{.State.Running}}')" = true ]; }
http() { curl -fsS --max-time 5 "http://localhost:$1$2"; }
compose() { docker compose -f "$1" "${@:2}"; }
cfg() { docker compose -f "$1" config --format json 2>/dev/null | jq -e "$2" >/dev/null; }
'''

INTRO = """<div class="scenario"><h3>Conteneuriser la boutique</h3><p>Cimes &amp; Sentiers veut en finir avec les « chez moi ça marche ». Léa vous confie la conteneurisation de la boutique : lancer et inspecter des conteneurs, publier le site, conserver les données, écrire le Dockerfile de l'API, puis assembler toute la pile avec <strong>docker compose</strong>.</p><p>Vous disposez de <strong>votre propre moteur Docker</strong> : tout ce que vous lancez reste dans votre environnement. Les images <code>alpine</code>, <code>nginx:alpine</code>, <code>node:20-alpine</code>, <code>redis:7-alpine</code> et <code>hello-world</code> sont déjà disponibles. Le projet est dans <code>~/projet</code>, modifiable dans l'éditeur.</p></div>"""

STEPS = {
    # ─────────────────────────────────────────────────────────────────────
    1: {
        "title": "Jour 1 — Un conteneur, c'est quoi ?",
        "description": "Image, conteneur, processus isolé. Compétences : docker run, ps -a, images, rm, inspect.",
        "lesson": INTRO + """<h3>Image et conteneur</h3><ul><li>Une <strong>image</strong> est un modèle en lecture seule : un système de fichiers (Alpine, Node…) et une commande par défaut.</li><li>Un <strong>conteneur</strong> est une instance de l'image : un <strong>processus</strong> de la machine hôte, isolé (système de fichiers, réseau, processus visibles…), avec une couche inscriptible.</li></ul><div class="tip">Contrairement à une machine virtuelle, un conteneur n'embarque pas de noyau : il partage celui de l'hôte. Il démarre en une fraction de seconde.</div><h3>Commandes essentielles</h3><pre>docker run alpine echo "Bonjour"          # crée ET démarre un conteneur<br>docker run --name premier alpine ...    # lui donne un nom<br>docker run -d alpine sleep 3600         # en arrière-plan (detached)<br>docker ps                               # conteneurs en cours<br>docker ps -a                            # tous, y compris arrêtés<br>docker images                           # images disponibles<br>docker rm nom                           # supprime un conteneur arrêté<br>docker rm -f nom                        # l'arrête et le supprime</pre><h3>Cycle de vie</h3><p>Un conteneur vit tant que son processus principal tourne. <code>echo</code> se termine aussitôt : le conteneur passe à l'état <em>Exited</em> (avec un code de sortie), mais il existe toujours jusqu'à son <code>rm</code>.</p><h3>Voir le processus depuis l'hôte</h3><pre>docker top dormeur                      # processus du conteneur, vus de l'hôte<br>docker inspect -f '{{.State.Pid}}' dormeur<br>ps aux | grep sleep</pre><p>Filtrer : <code>docker ps -a --filter name=ancien-</code> ; <code>-q</code> n'affiche que les identifiants.</p>""",
        "setup": r'''
docker rm -f ancien-1 ancien-2 ancien-3 ancien-4 ancien-5 ne-pas-toucher >/dev/null 2>&1 || true
# Conteneurs jamais démarrés (état « Created ») : instantanés à créer, et bien listés par docker ps -a
for i in 1 2 3 4 5; do docker create --name ancien-$i alpine true >/dev/null & done
docker run -d --name ne-pas-toucher alpine sleep infinity >/dev/null &
wait
''',
        "exercises": [
            {"id": "D1.1", "points": 3, "title": "Premier conteneur",
             "ticket": {"from": "julien", "body": "Paraît qu'avec Docker, une seule commande suffit pour lancer un système complet ? Tu peux me montrer ? Lance un conteneur Alpine qui dit bonjour à toute l'équipe."},
             "desc": "Un conteneur nommé <code>premier</code>, créé depuis l'image <code>alpine</code>, qui a affiché <code>Bonjour Cimes &amp; Sentiers</code> puis s'est terminé normalement.",
             "hints": ["<code>docker run --name ... image commande arguments</code>", 'Mettez le message entre guillemets : <code>echo "Bonjour Cimes &amp; Sentiers"</code>.'],
             "checks": [
                 ('docker inspect premier', "Aucun conteneur nommé premier (option --name)."),
                 ('i=$(insp premier "{{.Config.Image}}"); [ "$i" = alpine ] || [ "$i" = alpine:latest ]', "Le conteneur premier doit être créé depuis l'image alpine."),
                 ('docker logs premier 2>&1 | grep -q "Bonjour Cimes & Sentiers"', "Le conteneur n'a pas affiché « Bonjour Cimes & Sentiers »."),
                 ('[ "$(insp premier "{{.State.Status}}")" = exited ] && [ "$(insp premier "{{.State.ExitCode}}")" = 0 ]', "Le conteneur doit s'être terminé normalement (état exited, code 0)."),
             ]},
            {"id": "D1.2", "points": 4, "title": "Un conteneur n'est qu'un processus",
             "ticket": {"from": "lea", "body": "Première leçon que je donne toujours : un conteneur n'est pas une petite VM, c'est un <strong>processus</strong> de l'hôte, isolé. Lance en arrière-plan un conteneur <code>dormeur</code> (Alpine, <code>sleep 3600</code>), puis retrouve le PID de son processus <code>sleep</code>… vu depuis l'hôte."},
             "desc": "Le conteneur <code>dormeur</code> tourne, et <code>~/pid-dormeur.txt</code> contient le PID (sur l'hôte) de son processus.",
             "hints": ["<code>docker run -d --name dormeur alpine sleep 3600</code>", "<code>docker top dormeur</code> ou <code>docker inspect -f '{{.State.Pid}}' dormeur</code>. Vérifiez avec <code>ps -p &lt;PID&gt;</code>."],
             "checks": [
                 ('running dormeur', "Le conteneur dormeur ne tourne pas."),
                 ('[ "$(ans $H/pid-dormeur.txt)" = "$(insp dormeur "{{.State.Pid}}")" ]', "~/pid-dormeur.txt ne contient pas le PID du processus du conteneur."),
                 ('[ "$(ps -o comm= -p "$(insp dormeur "{{.State.Pid}}")")" = sleep ]', "Le processus trouvé n'est pas le sleep du conteneur."),
             ]},
            {"id": "D1.3", "points": 3, "title": "Le grand ménage",
             "ticket": {"from": "sophie", "body": "Marc a laissé traîner des conteneurs <code>ancien-1</code> à <code>ancien-5</code>, qui ne tournent pas. Supprime-les. Par contre <code>ne-pas-toucher</code> porte bien son nom : il doit continuer à tourner."},
             "desc": "Plus aucun conteneur <code>ancien-*</code> ; <code>ne-pas-toucher</code> tourne toujours.",
             "hints": ["<code>docker ps -a --filter name=ancien-</code>", "<code>docker rm $(docker ps -aq --filter name=ancien-)</code>"],
             "checks": [
                 ('running ne-pas-toucher', "Le conteneur ne-pas-toucher a été arrêté ou supprimé ! (bouton « Réinitialiser les fichiers de cette étape » pour le recréer)"),
                 ('[ -z "$(docker ps -aq --filter name=ancien-)" ]', "Il reste des conteneurs ancien-*."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Jour 2 — Enquête sur les conteneurs de Marc",
        "description": "Observer et piloter des conteneurs. Compétences : logs, stop, exec, inspect.",
        "lesson": """<h3>Observer</h3><pre>docker logs nom            # sortie du processus principal<br>docker logs -f nom         # en continu (Ctrl+C pour quitter)<br>docker logs --tail 20 nom<br>docker stats               # CPU / mémoire en direct<br>docker inspect nom         # toute la configuration, en JSON</pre><p><code>docker inspect</code> accepte un modèle Go pour extraire une valeur :</p><pre>docker inspect -f '{{.State.Status}}' nom<br>docker inspect -f '{{.Config.Env}}' nom<br>docker inspect -f '{{.NetworkSettings.IPAddress}}' nom</pre><h3>Agir</h3><pre>docker stop nom            # arrêt propre (SIGTERM, puis SIGKILL après 10 s)<br>docker start nom           # redémarre un conteneur arrêté<br>docker restart nom<br>docker exec nom commande   # exécute une commande DANS le conteneur<br>docker exec -it nom sh     # ouvre un shell interactif dedans<br>docker cp nom:/chemin ./   # copie un fichier du conteneur vers l'hôte</pre><div class="tip">Un conteneur arrêté conserve ses journaux et ses fichiers : on peut encore faire <code>docker logs</code> ou <code>docker cp</code>. Ils ne disparaissent qu'avec <code>docker rm</code>.</div>""",
        "setup": r'''
code=$(rword); cle=$(rword); env="preprod-$((RANDOM % 90 + 10))"
docker rm -f traitement-nuit coffre >/dev/null 2>&1 || true
docker run -d --name traitement-nuit alpine sh -c "echo 'Démarrage du traitement de nuit'; echo 'Connexion à la base…'; echo 'CODE-ACCES=$code'; echo 'Traitement en cours'; while true; do sleep 5; done" >/dev/null
docker run -d --name coffre -e ENVIRONNEMENT=$env -e TZ=Europe/Paris alpine sh -c "mkdir -p /secret && echo $cle > /secret/cle.txt && sleep infinity" >/dev/null
emit CODE "$code"
emit CLE "$cle"
emit ENV "$env"
''',
        "exercises": [
            {"id": "D2.1", "points": 3, "title": "Que dit le traitement de nuit ?",
             "ticket": {"from": "lea", "body": "Un conteneur <code>traitement-nuit</code> tourne depuis des semaines. D'après la doc (introuvable), il affiche un code d'accès au démarrage. Retrouve-le."},
             "desc": "Le code (la valeur après <code>CODE-ACCES=</code>) dans <code>~/code-acces.txt</code>.",
             "hints": ["Tout ce que le processus principal écrit est dans <code>docker logs</code>."],
             "checks": [
                 ('a=$(ans $H/code-acces.txt); [ "${a#CODE-ACCES=}" = "$LAB_CODE" ]', "Ce n'est pas le code d'accès affiché par traitement-nuit."),
             ]},
            {"id": "D2.2", "points": 3, "title": "Arrêter sans effacer",
             "ticket": {"from": "sophie", "body": "Ce traitement de nuit ne sert plus à rien. Arrête-le, mais <strong>ne le supprime pas</strong> : l'auditeur voudra lire ses journaux."},
             "desc": "<code>traitement-nuit</code> est arrêté mais existe toujours.",
             "hints": ["<code>docker stop</code> (et pas <code>docker rm</code>)."],
             "checks": [
                 ('docker inspect traitement-nuit', "traitement-nuit a été supprimé : il fallait seulement l'arrêter (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('[ "$(insp traitement-nuit "{{.State.Running}}")" = false ]', "traitement-nuit tourne encore."),
             ]},
            {"id": "D2.3", "points": 3, "title": "Le coffre",
             "ticket": {"from": "lea", "body": "Le conteneur <code>coffre</code> contient une clé de chiffrement dans <code>/secret/cle.txt</code>. Récupère-la sans l'arrêter."},
             "desc": "Le contenu de <code>/secret/cle.txt</code> du conteneur <code>coffre</code> dans <code>~/cle-coffre.txt</code>.",
             "hints": ["<code>docker exec coffre cat /secret/cle.txt</code>, puis redirigez vers le fichier."],
             "checks": [
                 ('running coffre', "Le conteneur coffre ne tourne plus."),
                 ('[ "$(ans $H/cle-coffre.txt)" = "$LAB_CLE" ]', "Ce n'est pas la clé contenue dans le coffre."),
             ]},
            {"id": "D2.4", "points": 3, "title": "Quel environnement ?",
             "ticket": {"from": "thomas", "body": "Le <code>coffre</code> tourne avec une variable d'environnement <code>ENVIRONNEMENT</code>. On ne sait plus si c'est la préprod ou la prod… Tu peux vérifier sa valeur ?"},
             "desc": "La valeur de la variable <code>ENVIRONNEMENT</code> du conteneur <code>coffre</code> dans <code>~/env-coffre.txt</code>.",
             "hints": ["<code>docker inspect -f '{{.Config.Env}}' coffre</code> ou <code>docker exec coffre env</code>."],
             "checks": [
                 ('a=$(ans $H/env-coffre.txt); [ "${a#ENVIRONNEMENT=}" = "$LAB_ENV" ]', "Ce n'est pas la valeur de ENVIRONNEMENT."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Jour 3 — La vitrine en ligne",
        "description": "Rendre un service accessible et lui donner des fichiers. Compétences : -p, bind mount, lecture seule.",
        "lesson": """<h3>Publier un port</h3><p>Un conteneur a son propre réseau : son port 80 n'est pas joignable depuis l'hôte… sauf si on le <strong>publie</strong>.</p><pre>docker run -d --name vitrine -p 8080:80 nginx:alpine<br>#                              hôte:conteneur<br>curl http://localhost:8080</pre><div class="tip">Deux conteneurs ne peuvent pas publier le même port de l'hôte : « port is already allocated ».</div><h3>Monter un dossier de l'hôte (bind mount)</h3><pre>docker run -d -p 8081:80 \\<br>  -v ~/projet/site:/usr/share/nginx/html:ro \\<br>  nginx:alpine</pre><ul><li>Le dossier de l'hôte est <strong>partagé</strong> avec le conteneur : une modification est visible immédiatement, sans reconstruire quoi que ce soit.</li><li><code>:ro</code> (<em>read-only</em>) : le conteneur ne peut pas modifier les fichiers.</li><li>Le chemin de l'hôte doit être <strong>absolu</strong> (<code>~</code> est remplacé par le shell, <code>$(pwd)</code> aussi).</li></ul><p>Syntaxe longue équivalente : <code>--mount type=bind,src=/home/etudiant/projet/site,dst=/usr/share/nginx/html,readonly</code></p>""",
        "setup": r'''
images_de_base
livrer site
''',
        "exercises": [
            {"id": "D3.1", "points": 3, "title": "Un serveur web en 10 secondes",
             "ticket": {"from": "thomas", "body": "Il me faut un serveur web vite fait pour une démo : un nginx, accessible sur le port <strong>8080</strong> de la machine, nommé <code>vitrine</code>."},
             "desc": "Un conteneur <code>vitrine</code> (image <code>nginx:alpine</code>) qui répond sur <code>http://localhost:8080</code>.",
             "hints": ["<code>-p port_hôte:port_conteneur</code> ; nginx écoute sur le port 80 dans le conteneur."],
             "checks": [
                 ('running vitrine', "Le conteneur vitrine ne tourne pas."),
                 ('insp vitrine "{{.Config.Image}}" | grep -q "^nginx"', "vitrine doit utiliser l'image nginx:alpine."),
                 ('http 8080 / | grep -qi nginx', "Rien ne répond sur http://localhost:8080 (port publié ?)."),
             ]},
            {"id": "D3.2", "points": 5, "title": "Le vrai site",
             "ticket": {"from": "sophie", "body": "Le site vitrine est dans <code>~/projet/site</code>. Sers-le sur le port <strong>8081</strong> avec un conteneur <code>vitrine-site</code>. Thomas doit pouvoir modifier le HTML sans rien reconstruire, et le serveur web ne doit surtout pas pouvoir modifier les fichiers."},
             "desc": "<code>vitrine-site</code> sert <code>~/projet/site</code> sur le port 8081 grâce à un <strong>bind mount en lecture seule</strong> sur <code>/usr/share/nginx/html</code>.",
             "hints": ["<code>-v /chemin/absolu/hote:/usr/share/nginx/html:ro</code>", "Testez : modifiez <code>index.html</code>, rechargez <code>curl localhost:8081</code>."],
             "checks": [
                 ('running vitrine-site', "Le conteneur vitrine-site ne tourne pas."),
                 ('http 8081 / | grep -q "Cimes"', "http://localhost:8081 ne sert pas le site de la boutique."),
                 ('insp vitrine-site "{{range .Mounts}}{{.Type}} {{.Source}} {{.Destination}} {{.RW}}{{println}}{{end}}" | grep -qx "bind /home/etudiant/projet/site /usr/share/nginx/html false"', "Le dossier ~/projet/site doit être monté (bind) en lecture seule sur /usr/share/nginx/html."),
                 ('t=$RANDOM$RANDOM; echo "$t" > $P/site/.verif.html; r=$(http 8081 /.verif.html); rm -f $P/site/.verif.html; [ "$r" = "$t" ]', "Une modification du dossier n'est pas visible immédiatement dans le conteneur."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Jour 4 — Des données qui survivent",
        "description": "Volumes nommés et sauvegarde. Compétences : docker volume, -v volume:/chemin, conteneurs jetables.",
        "lesson": """<h3>Le problème</h3><p>Tout ce qu'un conteneur écrit dans sa couche inscriptible disparaît avec <code>docker rm</code>. Une base de données doit donc écrire ailleurs.</p><h3>Les volumes</h3><pre>docker volume create donnees-boutique<br>docker volume ls<br>docker run -d --name cache -v donnees-boutique:/data redis:7-alpine redis-server --appendonly yes</pre><ul><li>Un <strong>volume</strong> est géré par Docker (dans <code>/var/lib/docker/volumes</code>), indépendant de tout conteneur.</li><li>On peut supprimer le conteneur, en recréer un autre sur le même volume : les données sont là.</li><li><code>--appendonly yes</code> : Redis écrit chaque modification sur disque.</li></ul><pre>docker exec cache redis-cli set promo RANDO10<br>docker exec cache redis-cli get promo</pre><h3>Sauvegarder un volume</h3><p>Avec un conteneur <strong>jetable</strong> qui monte le volume et un dossier de l'hôte :</p><pre>docker run --rm -v donnees-boutique:/data -v ~/sauvegardes:/backup alpine \\<br>  tar czf /backup/donnees-boutique.tar.gz -C /data .</pre><div class="tip"><code>--rm</code> supprime le conteneur dès qu'il se termine : parfait pour une tâche ponctuelle.</div>""",
        "setup": r'''
images_de_base
''',
        "exercises": [
            {"id": "D4.1", "points": 5, "title": "Un cache persistant",
             "ticket": {"from": "thomas", "body": "On veut un Redis pour la boutique, mais la dernière fois tout a été perdu à la mise à jour. Crée un volume <code>donnees-boutique</code>, lance un conteneur <code>cache</code> (redis:7-alpine) qui y stocke ses données (<code>/data</code>) avec la persistance activée, puis enregistre la clé <code>promo</code> = <code>RANDO10</code>."},
             "desc": "Volume <code>donnees-boutique</code> monté sur <code>/data</code> du conteneur <code>cache</code> ; la clé <code>promo</code> vaut <code>RANDO10</code> et est écrite sur le volume.",
             "hints": ["<code>docker run -d --name cache -v donnees-boutique:/data redis:7-alpine redis-server --appendonly yes</code>", "<code>docker exec cache redis-cli set promo RANDO10</code>"],
             "checks": [
                 ('docker volume inspect donnees-boutique', "Le volume donnees-boutique n'existe pas."),
                 ('running cache', "Le conteneur cache ne tourne pas."),
                 ('insp cache "{{range .Mounts}}{{.Type}} {{.Name}} {{.Destination}}{{println}}{{end}}" | grep -qx "volume donnees-boutique /data"', "Le volume donnees-boutique doit être monté sur /data dans le conteneur cache."),
                 ('[ "$(docker exec cache redis-cli get promo)" = RANDO10 ]', "La clé promo ne vaut pas RANDO10 dans Redis."),
                 ('docker run --rm -v donnees-boutique:/data alpine grep -rqs RANDO10 /data', "La donnée n'est pas encore écrite sur le volume : activez la persistance (--appendonly yes)."),
             ]},
            {"id": "D4.2", "points": 3, "title": "Sauvegarde du volume",
             "ticket": {"from": "sophie", "body": "Règle d'or : pas de données sans sauvegarde. Archive le contenu du volume <code>donnees-boutique</code> dans <code>~/sauvegardes/donnees-boutique.tar.gz</code>."},
             "desc": "<code>~/sauvegardes/donnees-boutique.tar.gz</code> contient les fichiers du volume (dont les données Redis).",
             "hints": ["Un conteneur jetable (<code>--rm</code>) qui monte le volume ET le dossier ~/sauvegardes, et lance <code>tar</code>.", "<code>docker run --rm -v donnees-boutique:/data -v ~/sauvegardes:/backup alpine tar czf /backup/donnees-boutique.tar.gz -C /data .</code>"],
             "checks": [
                 ('gzip -t $H/sauvegardes/donnees-boutique.tar.gz', "~/sauvegardes/donnees-boutique.tar.gz est absent ou n'est pas une archive gzip."),
                 ('tar -tzf $H/sauvegardes/donnees-boutique.tar.gz | grep -qE "appendonly|dump\\.rdb"', "L'archive ne contient pas les données Redis du volume."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Jour 5 — Le Dockerfile de l'API",
        "description": "Construire sa propre image. Compétences : FROM, WORKDIR, COPY, EXPOSE, CMD, USER, .dockerignore, docker build.",
        "lesson": """<h3>Un Dockerfile</h3><pre>FROM node:20-alpine        # image de départ<br>WORKDIR /app              # dossier de travail (créé si besoin)<br>COPY . .                  # copie le projet dans l'image<br>USER node                 # n'exécute pas l'application en root<br>EXPOSE 3000               # documente le port écouté<br>CMD ["node", "server.js"] # commande lancée au démarrage</pre><pre>docker build -t boutique-api:1.0 ~/projet/api   # construit l'image (le dernier argument = contexte)<br>docker run -d --name api -p 3000:3000 boutique-api:1.0<br>docker history boutique-api:1.0                 # les couches de l'image</pre><h3>Couches et cache</h3><p>Chaque instruction crée une <strong>couche</strong>. Si rien n'a changé, Docker réutilise la couche du cache : placez en premier ce qui change rarement.</p><h3>.dockerignore</h3><p>Tout le <strong>contexte</strong> (le dossier) est envoyé au moteur, et <code>COPY . .</code> copie tout. Un <code>.dockerignore</code> exclut ce qui n'a rien à faire dans l'image :</p><pre>node_modules<br>.env<br>.git</pre><div class="tip">Un secret copié dans une image est lisible par quiconque récupère l'image, même si on le supprime dans une couche suivante.</div><h3>Politique de redémarrage</h3><p><code>--restart unless-stopped</code> : le conteneur redémarre s'il plante ou si la machine redémarre, sauf s'il a été arrêté volontairement.</p>""",
        "setup": r'''
images_de_base
livrer api
secret="sk_live_$(rword | tr -d '-')$RANDOM"
printf 'STRIPE_SECRET_KEY=%s\nDB_PASSWORD=Sup3rS3cret!\n' "$secret" > $P/api/.env
mkdir -p $P/api/node_modules/module-lourd
[ -f $P/api/node_modules/module-lourd/blob.bin ] || head -c 25M /dev/urandom > $P/api/node_modules/module-lourd/blob.bin
own $P/api
emit SECRET "$secret"
''',
        "exercises": [
            {"id": "D5.1", "points": 5, "title": "L'image de l'API", "manual": True,
             "ticket": {"from": "thomas", "body": "L'API de la boutique (<code>~/projet/api</code>, Node 20, point d'entrée <code>server.js</code>, port 3000) doit tourner partout pareil. Écris son <code>Dockerfile</code> et construis l'image <code>boutique-api:1.0</code>."},
             "desc": "<code>~/projet/api/Dockerfile</code> construit une image <code>boutique-api:1.0</code> basée sur <code>node:20-alpine</code>, qui expose le port 3000 et dont l'API répond sur <code>/health</code>.",
             "hints": ["Instructions nécessaires : <code>FROM</code>, <code>WORKDIR</code>, <code>COPY</code>, <code>EXPOSE</code>, <code>CMD</code>.", "<code>docker build -t boutique-api:1.0 ~/projet/api</code>"],
             "checks": [
                 ('test -f $P/api/Dockerfile', "~/projet/api/Dockerfile n'existe pas."),
                 ('docker build -q -t lab-verif-api $P/api && docker rmi lab-verif-api', "Le Dockerfile ne se construit pas : lancez docker build pour voir l'erreur."),
                 ('docker image inspect boutique-api:1.0', "L'image boutique-api:1.0 n'existe pas (option -t de docker build)."),
                 ('insp boutique-api:1.0 "{{json .Config.ExposedPorts}}" | grep -q "3000/tcp"', "L'image doit exposer le port 3000 (EXPOSE)."),
                 ('docker rm -f lab-verif >/dev/null 2>&1; docker run -d --name lab-verif -p 3999:3000 boutique-api:1.0 && for i in 1 2 3 4 5 6; do sleep 1; http 3999 /health | grep -q ok && ok=1 && break; done; docker rm -f lab-verif >/dev/null; [ "$ok" = 1 ]', "Un conteneur lancé depuis boutique-api:1.0 ne répond pas sur /health (vérifiez CMD et le port)."),
             ]},
            {"id": "D5.2", "points": 3, "title": "L'API en service",
             "ticket": {"from": "sophie", "body": "Mets l'API en service : un conteneur <code>api</code> sur le port 3000 de la machine, qui redémarre tout seul s'il plante ou si le serveur redémarre (sauf si on l'arrête volontairement)."},
             "desc": "Un conteneur <code>api</code> issu de <code>boutique-api:1.0</code>, publié sur le port 3000, avec la politique de redémarrage <code>unless-stopped</code>.",
             "hints": ["<code>--restart unless-stopped</code>"],
             "checks": [
                 ('running api', "Le conteneur api ne tourne pas."),
                 ('[ "$(insp api "{{.Config.Image}}")" = boutique-api:1.0 ]', "Le conteneur api doit être créé depuis l'image boutique-api:1.0."),
                 ('http 3000 /produits | grep -q "SAC-40L"', "http://localhost:3000/produits ne renvoie pas le catalogue."),
                 ('[ "$(insp api "{{.HostConfig.RestartPolicy.Name}}")" = unless-stopped ]', "La politique de redémarrage doit être unless-stopped."),
             ]},
            {"id": "D5.3", "points": 5, "title": "Une image propre", "manual": True,
             "ticket": {"from": "nadia", "body": "Revue de ton image : elle embarque <code>node_modules</code> (25 Mo inutiles) et… le fichier <code>.env</code> avec la clé Stripe de production ! En plus, l'API tourne en <code>root</code>. Corrige le Dockerfile, ajoute un <code>.dockerignore</code>, et reconstruis <code>boutique-api:1.0</code>."},
             "desc": "L'image <code>boutique-api:1.0</code> reconstruite ne contient ni <code>.env</code> ni <code>node_modules</code>, et l'application ne s'exécute pas en root.",
             "hints": ["Un fichier <code>.dockerignore</code> à côté du Dockerfile, une entrée par ligne.", "L'image node fournit l'utilisateur <code>node</code> : <code>USER node</code>. Pensez à recréer le conteneur <code>api</code> avec la nouvelle image."],
             "checks": [
                 ('grep -qE "^/?node_modules/?$" $P/api/.dockerignore && grep -qE "^/?\\.env$" $P/api/.dockerignore', "~/projet/api/.dockerignore doit exclure node_modules et .env."),
                 ('docker run --rm --entrypoint sh boutique-api:1.0 -c "test -z \\"\\$(find / -xdev \\( -name .env -o -name blob.bin \\) 2>/dev/null)\\""', "L'image boutique-api:1.0 contient encore .env ou node_modules : reconstruisez-la."),
                 ('[ "$(docker run --rm --entrypoint whoami boutique-api:1.0)" != root ]', "L'application s'exécute encore en root (instruction USER)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Jour 6 — Faire dialoguer les conteneurs",
        "description": "Réseaux utilisateur et résolution par nom. Compétences : docker network, --network, variables d'environnement.",
        "lesson": """<h3>Réseaux</h3><pre>docker network create reseau-boutique<br>docker run -d --name redis --network reseau-boutique redis:7-alpine<br>docker run -d --name api --network reseau-boutique -e REDIS_HOST=redis ... boutique-api:1.0</pre><ul><li>Sur un réseau <strong>créé par vous</strong>, les conteneurs se joignent <strong>par leur nom</strong> (DNS intégré de Docker) : l'API contacte <code>redis:6379</code>.</li><li>Sur le réseau par défaut (<code>bridge</code>), pas de résolution par nom.</li><li>Un service qui n'est utilisé que par d'autres conteneurs n'a <strong>pas</strong> besoin de <code>-p</code> : ne publiez que ce qui doit être joignable de l'extérieur.</li></ul><pre>docker network ls<br>docker network inspect reseau-boutique<br>docker network connect reseau-boutique conteneur   # brancher un conteneur existant</pre><h3>Variables d'environnement</h3><p><code>-e NOM=valeur</code> configure l'application sans reconstruire l'image. Pour changer la configuration d'un conteneur existant, on le <strong>recrée</strong> (<code>docker rm -f</code> puis <code>docker run</code>).</p>""",
        "setup": r'''
images_de_base
''',
        "exercises": [
            {"id": "D6.1", "points": 6, "title": "Compter les visites",
             "ticket": {"from": "thomas", "body": "L'API sait compter les visites (<code>/visites</code>) dans Redis, si on lui donne l'hôte Redis dans <code>REDIS_HOST</code>. Crée un réseau <code>reseau-boutique</code>, un conteneur <code>redis</code> dessus (surtout pas exposé à l'extérieur), et recrée l'<code>api</code> sur ce réseau, toujours sur le port 3000."},
             "desc": "<code>redis</code> et <code>api</code> sur le réseau <code>reseau-boutique</code> ; <code>redis</code> ne publie aucun port ; <code>http://localhost:3000/visites</code> compte les visites.",
             "hints": ["<code>docker network create reseau-boutique</code> puis <code>--network reseau-boutique</code> sur les deux conteneurs.", "L'API trouve Redis par son nom : <code>-e REDIS_HOST=redis</code>."],
             "checks": [
                 ('docker network inspect reseau-boutique', "Le réseau reseau-boutique n'existe pas."),
                 ('running redis && running api', "Les conteneurs redis et api doivent tourner."),
                 ('n=$(docker network inspect -f "{{range .Containers}}{{.Name}} {{end}}" reseau-boutique); echo "$n" | grep -qw redis && echo "$n" | grep -qw api', "redis et api doivent tous deux être connectés à reseau-boutique."),
                 ('[ -z "$(docker port redis)" ]', "redis ne doit publier aucun port sur la machine."),
                 ('a=$(http 3000 /visites | jq -e .visites) && b=$(http 3000 /visites | jq -e .visites) && [ "$b" -gt "$a" ]', "http://localhost:3000/visites ne compte pas les visites (REDIS_HOST ?)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    7: {
        "title": "Jour 7 — Toute la pile avec docker compose",
        "description": "Décrire et lancer une application multi-conteneurs. Compétences : compose.yaml, build, ports, volumes, depends_on, healthcheck, .env.",
        "lesson": """<h3>Un fichier au lieu de dix commandes</h3><pre>services:<br>  api:<br>    build: ./api                 # construit l'image depuis ./api/Dockerfile<br>    environment:<br>      REDIS_HOST: redis<br>    depends_on:<br>      - redis<br>  redis:<br>    image: redis:7-alpine<br>    volumes:<br>      - donnees:/data<br>volumes:<br>  donnees:</pre><pre>docker compose up -d --build     # construit et démarre tout<br>docker compose ps                # état des services<br>docker compose logs -f api<br>docker compose exec api sh       # shell dans un service<br>docker compose down              # arrête et supprime les conteneurs (pas les volumes)</pre><ul><li>Compose crée un réseau pour le projet : les services se joignent par leur <strong>nom de service</strong>.</li><li>Le nom du projet vient du dossier (<code>projet</code>) : conteneurs <code>projet-api-1</code>, volume <code>projet_donnees</code>…</li></ul><h3>Attendre qu'un service soit prêt</h3><pre>  redis:<br>    healthcheck:<br>      test: ["CMD", "redis-cli", "ping"]<br>      interval: 5s<br>  api:<br>    depends_on:<br>      redis:<br>        condition: service_healthy</pre><h3>Variables</h3><p>Compose lit le fichier <code>.env</code> du dossier du projet : <code>${APP_VERSION}</code> dans <code>compose.yaml</code> est remplacé par sa valeur. <code>docker compose config</code> affiche le résultat.</p><div class="tip">Les ports de l'hôte sont partagés : arrêtez d'abord les conteneurs lancés à la main (<code>docker rm -f api redis vitrine …</code>).</div>""",
        "setup": r'''
images_de_base
livrer api site nginx
''',
        "exercises": [
            {"id": "D7.1", "points": 6, "title": "La pile en un fichier",
             "ticket": {"from": "lea", "body": "Tes commandes <code>docker run</code> à rallonge, personne ne pourra les rejouer. Décris la pile dans <code>~/projet/compose.yaml</code> : un service <code>api</code> construit depuis <code>./api</code>, un service <code>redis</code> dont les données sont dans un volume nommé, l'API configurée pour joindre Redis. Puis supprime les conteneurs lancés à la main et démarre la pile."},
             "desc": "<code>~/projet/compose.yaml</code> valide, avec les services <code>api</code> (<code>build: ./api</code>) et <code>redis</code> (volume nommé sur <code>/data</code>), démarrés ; l'API compte les visites.",
             "hints": ["Reprenez l'exemple du cours ; le nom d'hôte Redis est le nom du service.", "<code>docker compose up -d --build</code> depuis <code>~/projet</code>, puis <code>docker compose exec api wget -qO- localhost:3000/visites</code>."],
             "checks": [
                 ('compose $P/compose.yaml config -q', "~/projet/compose.yaml est absent ou invalide (docker compose config pour voir l'erreur)."),
                 ('cfg $P/compose.yaml \'.services.api.build.context | endswith("/api")\'', "Le service api doit être construit depuis ./api (build)."),
                 ('cfg $P/compose.yaml \'.services.redis.volumes[]? | select(.type == "volume" and .target == "/data")\'', "Le service redis doit stocker /data dans un volume nommé."),
                 ('s=$(compose $P/compose.yaml ps --status running --services); echo "$s" | grep -qx api && echo "$s" | grep -qx redis', "Les services api et redis ne tournent pas (docker compose up -d)."),
                 ('compose $P/compose.yaml exec -T api wget -qO- http://localhost:3000/visites | jq -e ".visites >= 1"', "Dans la pile, l'API ne parvient pas à compter les visites (REDIS_HOST ?)."),
             ]},
            {"id": "D7.2", "points": 5, "title": "Un seul point d'entrée",
             "ticket": {"from": "sophie", "body": "Pour la sécurité, une seule porte d'entrée : ajoute un service <code>web</code> (nginx:alpine) publié sur le port <strong>8080</strong>, qui sert le site (<code>./site</code>) et relaie <code>/api/</code> vers l'API grâce à <code>./nginx/default.conf</code>. L'API ne doit plus être publiée directement."},
             "desc": "Le service <code>web</code> publie 8080, sert le site et relaie <code>/api/</code> ; le service <code>api</code> ne publie aucun port.",
             "hints": ["Montez <code>./nginx/default.conf</code> sur <code>/etc/nginx/conf.d/default.conf</code> et <code>./site</code> sur <code>/usr/share/nginx/html</code>, en lecture seule.", "Le port 8080 est peut-être encore pris par le conteneur <code>vitrine</code> du jour 3."],
             "checks": [
                 ('http 8080 / | grep -q "Cimes"', "http://localhost:8080 ne sert pas le site de la boutique."),
                 ('http 8080 /api/health | jq -e ".statut == \\"ok\\""', "http://localhost:8080/api/health ne répond pas : le proxy vers l'API ne fonctionne pas."),
                 ('cfg $P/compose.yaml \'(.services.api.ports // []) | length == 0\'', "Le service api ne doit plus publier de port : tout passe par web."),
             ]},
            {"id": "D7.3", "points": 4, "title": "Démarrer dans le bon ordre",
             "ticket": {"from": "nadia", "body": "Au démarrage, l'API renvoie parfois des erreurs parce que Redis n'est pas encore prêt. Ajoute un <strong>healthcheck</strong> à Redis, et fais attendre l'API jusqu'à ce que Redis soit <em>en bonne santé</em>."},
             "desc": "<code>redis</code> a un healthcheck (<code>redis-cli ping</code>) et est <em>healthy</em> ; <code>api</code> en dépend avec <code>condition: service_healthy</code>.",
             "hints": ['<code>healthcheck: test: ["CMD", "redis-cli", "ping"]</code>', "<code>depends_on: redis: condition: service_healthy</code>"],
             "checks": [
                 ('cfg $P/compose.yaml \'.services.redis.healthcheck.test | tostring | test("ping")\'', "Le service redis n'a pas de healthcheck basé sur redis-cli ping."),
                 ('cfg $P/compose.yaml \'.services.api.depends_on.redis.condition == "service_healthy"\'', "Le service api doit dépendre de redis avec condition: service_healthy."),
                 ('[ "$(insp "$(compose $P/compose.yaml ps -q redis)" "{{.State.Health.Status}}")" = healthy ]', "Le conteneur redis n'est pas (encore) healthy : relancez docker compose up -d."),
             ]},
            {"id": "D7.4", "points": 4, "title": "Une version configurable",
             "ticket": {"from": "thomas", "body": "L'API affiche sa version dans <code>/health</code> (variable <code>APP_VERSION</code>). Je ne veux plus modifier <code>compose.yaml</code> à chaque livraison : la version doit venir d'un fichier <code>.env</code>. On livre la <strong>2.0</strong>."},
             "desc": "<code>~/projet/.env</code> définit <code>APP_VERSION=2.0</code>, <code>compose.yaml</code> l'utilise via <code>${APP_VERSION}</code>, et <code>/api/health</code> affiche la version 2.0.",
             "hints": ["Dans compose.yaml : <code>APP_VERSION: ${APP_VERSION}</code> dans l'environnement du service api.", "Après modification : <code>docker compose up -d</code> recrée les conteneurs concernés."],
             "checks": [
                 ('grep -qx "APP_VERSION=2.0" $P/.env', "~/projet/.env doit contenir APP_VERSION=2.0."),
                 ('grep -q "\\${APP_VERSION" $P/compose.yaml', "compose.yaml doit utiliser la variable ${APP_VERSION} (et non une valeur écrite en dur)."),
                 ('http 8080 /api/health | jq -e ".version == \\"2.0\\""', "L'API ne s'annonce pas en version 2.0 (conteneur recréé ?)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Jour 8 — Incident en production",
        "description": "Diagnostiquer une pile qui ne fonctionne pas, et garder un moteur propre. Compétences : ps, logs, port, config, image prune.",
        "lesson": """<h3>Méthode de diagnostic</h3><ol><li><code>docker compose ps</code> — quels services tournent ? Lequel redémarre en boucle (<em>Restarting</em>) ?</li><li><code>docker compose logs api</code> — le message d'erreur du processus.</li><li><code>docker compose config</code> — la configuration réellement appliquée (variables, ports).</li><li><code>docker port conteneur</code> — quels ports sont publiés, et vers quoi.</li><li><code>docker compose exec api env</code> — les variables vues par l'application.</li></ol><div class="tip">Dans <code>ports:</code>, l'ordre est toujours <strong>hôte:conteneur</strong>. Le port du conteneur est celui sur lequel l'application écoute vraiment.</div><h3>Faire de la place</h3><pre>docker system df              # espace utilisé par les images, conteneurs, volumes<br>docker image prune            # supprime les images « pendantes » (&lt;none&gt;)<br>docker image prune -a         # supprime TOUTES les images non utilisées par un conteneur (attention !)<br>docker container prune        # supprime les conteneurs arrêtés</pre><p>Une image <em>pendante</em> (<em>dangling</em>) est une ancienne version qui a perdu son tag après un nouveau <code>docker build -t</code>.</p>""",
        "setup": r'''
images_de_base
mkdir -p $H/incident
cp -rn /opt/docker-lab/incident/. $H/incident/
own $H/incident
(cd $H/incident && docker compose up -d --build >/dev/null 2>&1) || true
for v in 1 2 3; do printf 'FROM alpine\nRUN echo "brouillon %s" > /version\n' "$v" | docker build -q -t brouillon-marc - >/dev/null; done
''',
        "exercises": [
            {"id": "D8.1", "points": 8, "title": "La pile de Marc",
             "ticket": {"from": "sophie", "body": "Alerte ! La pile <code>~/incident</code> déployée par Marc juste avant son départ ne fonctionne pas : l'API devrait répondre sur <code>http://localhost:8090/visites</code>. Je n'ai pas le temps de t'en dire plus, mais je parie qu'il y a <strong>plusieurs</strong> erreurs."},
             "desc": "Après correction de <code>~/incident</code> (fichiers compose et Dockerfile), <code>http://localhost:8090/visites</code> compte les visites.",
             "hints": ["Commencez par <code>docker compose ps</code> et <code>docker compose logs api</code> dans <code>~/incident</code>.", "Trois erreurs : la commande de démarrage de l'image, le sens de la redirection de port, et le nom d'une variable d'environnement attendue par l'API (voir <code>server.js</code>)."],
             "checks": [
                 ('http 8090 /visites | jq -e ".visites >= 1"', "http://localhost:8090/visites ne compte pas les visites."),
                 ('compose $H/incident/compose.yaml ps --status running --services | grep -qx api', "Le service api de la pile incident ne tourne pas."),
             ]},
            {"id": "D8.2", "points": 3, "title": "Le disque se remplit",
             "ticket": {"from": "lea", "body": "Le disque du serveur se remplit : Marc a reconstruit plusieurs fois son image <code>brouillon-marc</code>, et les anciennes versions traînent sans nom (<code>&lt;none&gt;</code>). Supprime ces images pendantes. Attention, les images de base (node, nginx, redis…) doivent rester, on n'a pas Internet dans la salle serveur."},
             "desc": "Plus aucune image pendante ; <code>node:20-alpine</code>, <code>nginx:alpine</code>, <code>redis:7-alpine</code> et <code>alpine</code> sont toujours présentes.",
             "hints": ["<code>docker images -f dangling=true</code> pour les voir.", "<code>docker image prune</code> — sans <code>-a</code> !"],
             "checks": [
                 ('for i in node:20-alpine nginx:alpine redis:7-alpine alpine:latest; do docker image inspect $i >/dev/null 2>&1 || exit 1; done', "Des images de base ont été supprimées ! (docker image prune -a supprime toutes les images inutilisées)"),
                 ('[ -z "$(docker images -q -f dangling=true)" ]', "Il reste des images pendantes (<none>)."),
             ]},
        ],
    },
}
