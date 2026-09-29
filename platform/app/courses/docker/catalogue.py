"""Parcours « Docker : conteneuriser la boutique ».

Chaque étudiant dispose de son propre moteur Docker, à l'intérieur de son conteneur
(runtime Sysbox en production). Les vérifications interrogent ce moteur : docker inspect,
appels HTTP aux services, reconstruction de l'image, relance des conteneurs…
"""

EXERCISES_VERSION = "2"

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
# npm_en_cache <projet> : après une modification de server.js, l'étape « RUN npm » doit être reprise du cache
npm_en_cache() {
  local t r n; t=$(mktemp -d); cp -a "$1/." "$t/"
  docker build --progress=plain -t lab-verif-cache:1 "$t" > "$t.1" 2>&1 || { echo "MSG:Le Dockerfile ne se construit pas."; rm -rf "$t" "$t.1"; return 1; }
  echo "// modification" >> "$t/server.js"
  docker build --progress=plain -t lab-verif-cache:2 "$t" > "$t.2" 2>&1; r=$?
  n=$(grep -oE "^#[0-9]+ \[[^]]*\] RUN +npm" "$t.2" | head -1 | cut -d" " -f1)
  docker rmi lab-verif-cache:1 lab-verif-cache:2 > /dev/null 2>&1
  [ "$r" = 0 ] && [ -n "$n" ] && grep -q "^$n CACHED" "$t.2"; r=$?
  rm -rf "$t" "$t.1" "$t.2"; return $r
}
# arret_propre <image> : docker stop doit arrêter le conteneur en moins de 3 s, avec le code 0 et le message « Arrêt propre »
arret_propre() {
  local d c l
  docker rm -f lab-verif-arret > /dev/null 2>&1
  docker run -d --name lab-verif-arret "$1" > /dev/null || return 1
  sleep 2; d=$(date +%s); docker stop -t 8 lab-verif-arret > /dev/null; d=$(( $(date +%s) - d ))
  c=$(insp lab-verif-arret "{{.State.ExitCode}}"); l=$(docker logs lab-verif-arret 2>&1)
  docker rm -f lab-verif-arret > /dev/null
  echo "MSG:docker stop : $d s, code de sortie $c"
  [ "$d" -le 3 ] && [ "$c" = 0 ] && echo "$l" | grep -q "Arrêt propre"
}
# version_api <image> : version annoncée par /health d'un conteneur lancé sans option
version_api() {
  local v
  docker rm -f lab-verif-version > /dev/null 2>&1
  docker run -d --name lab-verif-version -p 3997:3000 "$1" > /dev/null || return 1
  for _ in 1 2 3 4 5 6 7 8; do sleep 1; v=$(http 3997 /health | jq -r .version) && break; done
  docker rm -f lab-verif-version > /dev/null; echo "$v"
}
'''

INTRO = """<div class="scenario"><h3>Conteneuriser la boutique</h3><p>Cimes &amp; Sentiers veut en finir avec les « chez moi ça marche ». Léa vous confie la conteneurisation de la boutique : lancer et inspecter des conteneurs, publier le site, conserver les données (et éviter leurs pièges), écrire des Dockerfile rapides à construire, légers et sans secrets, puis assembler toute la pile avec <strong>docker compose</strong>.</p><p>Vous disposez de <strong>votre propre moteur Docker</strong> : tout ce que vous lancez reste dans votre environnement. Les images <code>alpine</code>, <code>nginx:alpine</code>, <code>node:20-alpine</code>, <code>redis:7-alpine</code> et <code>hello-world</code> sont déjà disponibles. Le projet est dans <code>~/projet</code>, modifiable dans l'éditeur.</p></div>"""

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
        "title": "Jour 5 — Volumes, bind mounts, tmpfs : les pièges",
        "description": "Ce que Docker fait vraiment des données. Compétences : volume pré-rempli, restauration, volumes anonymes, --read-only, --tmpfs.",
        "lesson": """<h3>Volume nommé ou bind mount : qui gagne ?</h3><p>Quand on monte quelque chose sur un dossier qui <strong>contient déjà des fichiers dans l'image</strong> (par exemple <code>/usr/share/nginx/html</code>), le résultat dépend du type de montage :</p><ul><li><strong>Bind mount</strong> (<code>-v /chemin/hote:/dossier</code>) : le dossier de l'hôte <strong>masque</strong> celui de l'image. Dossier vide ⇒ le conteneur voit un dossier vide (nginx répond 403).</li><li><strong>Volume nommé vide</strong> (<code>-v mon-volume:/dossier</code>) : au premier montage, Docker <strong>recopie</strong> le contenu de l'image dans le volume. Ensuite, le volume a sa vie propre : une nouvelle version de l'image ne le met plus à jour.</li></ul><pre>docker run -d -v html-vitrine:/usr/share/nginx/html nginx:alpine   # volume pré-rempli<br>docker cp promo.html conteneur:/usr/share/nginx/html/            # docker cp écrit aussi dans le volume</pre><h3>Restaurer une sauvegarde</h3><p>L'opération inverse de la sauvegarde du jour 4, <strong>avant</strong> de démarrer le service (sinon il travaille sur un volume vide, puis écrase ou ignore les fichiers restaurés) :</p><pre>docker volume create donnees-restaurees<br>docker run --rm -v donnees-restaurees:/data -v ~/sauvegardes:/backup alpine \\<br>  tar xzf /backup/archive.tar.gz -C /data<br>docker run -d --name ... -v donnees-restaurees:/data redis:7-alpine ...</pre><h3>Les volumes anonymes</h3><p>Certaines images déclarent un <code>VOLUME</code> dans leur Dockerfile (Redis : <code>VOLUME /data</code>). Sans <code>-v</code>, chaque <code>docker run</code> crée alors un <strong>volume anonyme</strong> (un nom de 64 caractères hexadécimaux)… qui <strong>survit</strong> à <code>docker rm</code>.</p><pre>docker image inspect -f '{{.Config.Volumes}}' redis:7-alpine<br>docker volume ls -f dangling=true      # volumes utilisés par aucun conteneur<br>docker rm -v conteneur                 # supprime le conteneur ET ses volumes anonymes<br>docker volume prune                    # supprime les volumes ANONYMES inutilisés<br>docker volume prune -a                 # … et aussi les volumes NOMMÉS inutilisés (danger)</pre><div class="tip"><code>docker run --rm</code> supprime aussi les volumes anonymes du conteneur ; jamais les volumes nommés.</div><h3>Un conteneur en lecture seule</h3><p><code>--read-only</code> interdit toute écriture dans le système de fichiers du conteneur : un attaquant ne peut plus déposer de fichier. Les dossiers où l'application doit vraiment écrire (cache, fichier PID…) reçoivent un <strong>tmpfs</strong> : un petit système de fichiers en mémoire, vidé à l'arrêt.</p><pre>docker run -d --read-only --tmpfs /tmp nginx:alpine<br>docker logs conteneur        # « Read-only file system » : quel dossier manque ?</pre><h3>Les trois types de montage</h3><pre>-v volume:/chemin          --mount type=volume,src=volume,dst=/chemin<br>-v /hote:/chemin:ro        --mount type=bind,src=/hote,dst=/chemin,readonly<br>--tmpfs /chemin            --mount type=tmpfs,dst=/chemin</pre>""",
        "setup": r'''
images_de_base
# Le site « disparu » de Thomas : un dossier vide monté par-dessus celui de nginx
mkdir -p $P/vide
own $P
docker rm -f vitrine-vide >/dev/null 2>&1 || true
docker run -d --name vitrine-vide -p 8085:80 -v $P/vide:/usr/share/nginx/html nginx:alpine >/dev/null
# Sauvegarde du cache faite avant la migration (clé promo aléatoire)
promo=$(rword | tr 'a-z-' 'A-Z_')
mkdir -p $H/sauvegardes
docker rm -f lab-prep-cache >/dev/null 2>&1 || true
docker volume rm lab-prep-cache >/dev/null 2>&1 || true
docker run -d --name lab-prep-cache -v lab-prep-cache:/data redis:7-alpine redis-server --appendonly yes >/dev/null
for _ in $(seq 1 30); do docker exec lab-prep-cache redis-cli ping 2>/dev/null | grep -q PONG && break; sleep 0.5; done
docker exec lab-prep-cache redis-cli set promo "$promo" >/dev/null
docker exec lab-prep-cache redis-cli save >/dev/null
docker rm -f lab-prep-cache >/dev/null
docker run --rm -v lab-prep-cache:/data -v $H/sauvegardes:/backup alpine tar czf /backup/cache-avant-migration.tar.gz -C /data .
docker volume rm lab-prep-cache >/dev/null
own $H/sauvegardes
# Volumes anonymes laissés par des conteneurs Redis supprimés, et un volume nommé inutilisé mais précieux
docker volume create archives-2023 >/dev/null
docker run --rm -v archives-2023:/archives alpine sh -c 'echo "Grand livre 2023" > /archives/grand-livre-2023.txt'
for _ in 1 2 3 4; do docker rm "$(docker create redis:7-alpine)" >/dev/null; done
emit PROMO "$promo"
''',
        "exercises": [
            {"id": "D5.1", "points": 4, "title": "Le site a disparu",
             "ticket": {"from": "thomas", "body": "Je ne comprends pas : j'ai lancé <code>vitrine-vide</code> en montant un dossier vide sur <code>/usr/share/nginx/html</code>, et nginx répond 403 (<code>curl localhost:8085</code>) ! Je voulais garder la page d'accueil de nginx et juste y ajouter une page. Fais-moi une <code>vitrine-pleine</code> sur le port <strong>8082</strong> dont les pages sont dans un <strong>volume</strong> <code>html-vitrine</code> qui garde la page de nginx, et ajoutes-y <code>promo.html</code> avec « Soldes d'été »."},
             "desc": "Le conteneur <code>vitrine-pleine</code> (nginx:alpine) monte le volume <code>html-vitrine</code> sur <code>/usr/share/nginx/html</code>, sert la page d'accueil de nginx sur le port 8082, ainsi que <code>/promo.html</code> contenant « Soldes ».",
             "hints": ["Un volume nommé <strong>vide</strong> monté sur un dossier de l'image reçoit une copie de son contenu ; un bind mount le masque.", "<code>docker run -d --name vitrine-pleine -p 8082:80 -v html-vitrine:/usr/share/nginx/html nginx:alpine</code>, puis <code>docker cp promo.html vitrine-pleine:/usr/share/nginx/html/</code>."],
             "checks": [
                 ('docker volume inspect html-vitrine', "Le volume html-vitrine n'existe pas."),
                 ('running vitrine-pleine', "Le conteneur vitrine-pleine ne tourne pas."),
                 ('insp vitrine-pleine "{{range .Mounts}}{{.Type}} {{.Name}} {{.Destination}}{{println}}{{end}}" | grep -qx "volume html-vitrine /usr/share/nginx/html"', "Le volume html-vitrine doit être monté sur /usr/share/nginx/html dans vitrine-pleine."),
                 ('http 8082 / | grep -q "Welcome to nginx"', "http://localhost:8082 ne sert pas la page d'accueil de nginx : le volume était-il vide au premier montage ?"),
                 ('http 8082 /promo.html | grep -q "Soldes"', "http://localhost:8082/promo.html ne contient pas « Soldes »."),
             ]},
            {"id": "D5.2", "points": 4, "title": "Restaurer le cache",
             "ticket": {"from": "sophie", "body": "Avant la migration, Léa a sauvegardé le cache Redis dans <code>~/sauvegardes/cache-avant-migration.tar.gz</code>. Restaure-le dans un nouveau volume <code>donnees-restaurees</code>, et démarre dessus un Redis nommé <code>cache-restaure</code>. Je veux retrouver la clé <code>promo</code> telle qu'elle était."},
             "desc": "Le conteneur <code>cache-restaure</code> (redis:7-alpine) monte le volume <code>donnees-restaurees</code> sur <code>/data</code>, et la clé <code>promo</code> a la valeur de la sauvegarde.",
             "hints": ["Un conteneur jetable qui monte le volume et <code>~/sauvegardes</code>, et lance <code>tar xzf … -C /data</code>.", "Restaurez <strong>avant</strong> de démarrer Redis : il ne lit ses fichiers qu'au démarrage. Sinon : <code>docker rm -f cache-restaure</code>, restauration, puis nouveau <code>docker run</code>."],
             "checks": [
                 ('running cache-restaure', "Le conteneur cache-restaure ne tourne pas."),
                 ('insp cache-restaure "{{range .Mounts}}{{.Type}} {{.Name}} {{.Destination}}{{println}}{{end}}" | grep -qx "volume donnees-restaurees /data"', "Le volume donnees-restaurees doit être monté sur /data dans cache-restaure."),
                 ('[ "$(docker exec cache-restaure redis-cli get promo)" = "$LAB_PROMO" ]', "La clé promo de cache-restaure n'a pas la valeur de la sauvegarde (archive extraite dans le volume avant le démarrage de Redis ?)."),
             ]},
            {"id": "D5.3", "points": 3, "title": "Des volumes fantômes",
             "ticket": {"from": "lea", "body": "<code>docker volume ls</code> est plein de volumes aux noms illisibles : des volumes <strong>anonymes</strong> laissés par des conteneurs Redis supprimés. Fais le ménage. Attention : <code>archives-2023</code> ne sert à aucun conteneur, mais il contient le grand livre comptable. Il doit rester !"},
             "desc": "Plus aucun volume anonyme inutilisé ; le volume <code>archives-2023</code> existe toujours.",
             "hints": ["<code>docker volume ls -f dangling=true</code> : les volumes qu'aucun conteneur n'utilise.", "<code>docker volume prune</code> ne supprime que les volumes anonymes ; avec <code>-a</code>, il supprime aussi les volumes nommés."],
             "checks": [
                 ('docker volume inspect archives-2023', "Le volume archives-2023 a été supprimé ! (docker volume prune -a supprime aussi les volumes nommés inutilisés ; bouton « Réinitialiser les fichiers de cette étape » pour le recréer)"),
                 ('[ -z "$(docker volume ls -q -f dangling=true | grep -E "^[0-9a-f]{64}$")" ]', "Il reste des volumes anonymes inutilisés (docker volume ls -f dangling=true)."),
             ]},
            {"id": "D5.4", "points": 4, "title": "Une vitrine en lecture seule",
             "ticket": {"from": "sophie", "body": "Suite à l'audit de sécurité : si quelqu'un pénètre dans le serveur web, il ne doit pouvoir <strong>rien écrire</strong> dans le conteneur. Lance <code>vitrine-ro</code> (nginx:alpine, port <strong>8083</strong>) avec un système de fichiers en lecture seule. Et il doit quand même fonctionner…"},
             "desc": "Le conteneur <code>vitrine-ro</code> a un système de fichiers en lecture seule (<code>--read-only</code>), répond sur <code>http://localhost:8083</code>, et on ne peut pas écrire dans <code>/usr/share/nginx/html</code>.",
             "hints": ["Essayez d'abord avec <code>--read-only</code> seul, puis lisez <code>docker logs vitrine-ro</code> : quel dossier nginx veut-il écrire ?", "nginx écrit dans <code>/var/cache/nginx</code> et son fichier PID dans <code>/run</code> : <code>--tmpfs /var/cache/nginx --tmpfs /run</code>."],
             "checks": [
                 ('running vitrine-ro', "Le conteneur vitrine-ro ne tourne pas (docker logs vitrine-ro)."),
                 ('[ "$(insp vitrine-ro "{{.HostConfig.ReadonlyRootfs}}")" = true ]', "Le système de fichiers de vitrine-ro doit être en lecture seule (--read-only)."),
                 ('http 8083 / | grep -q "Welcome to nginx"', "vitrine-ro ne sert pas la page de nginx sur http://localhost:8083."),
                 ('! docker exec vitrine-ro touch /usr/share/nginx/html/pirate.html 2>/dev/null', "On peut encore écrire dans /usr/share/nginx/html de vitrine-ro."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Jour 6 — Le Dockerfile de l'API",
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
            {"id": "D6.1", "points": 5, "title": "L'image de l'API", "manual": True,
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
            {"id": "D6.2", "points": 3, "title": "L'API en service",
             "ticket": {"from": "sophie", "body": "Mets l'API en service : un conteneur <code>api</code> sur le port 3000 de la machine, qui redémarre tout seul s'il plante ou si le serveur redémarre (sauf si on l'arrête volontairement)."},
             "desc": "Un conteneur <code>api</code> issu de <code>boutique-api:1.0</code>, publié sur le port 3000, avec la politique de redémarrage <code>unless-stopped</code>.",
             "hints": ["<code>--restart unless-stopped</code>"],
             "checks": [
                 ('running api', "Le conteneur api ne tourne pas."),
                 ('[ "$(insp api "{{.Config.Image}}")" = boutique-api:1.0 ]', "Le conteneur api doit être créé depuis l'image boutique-api:1.0."),
                 ('http 3000 /produits | grep -q "SAC-40L"', "http://localhost:3000/produits ne renvoie pas le catalogue."),
                 ('[ "$(insp api "{{.HostConfig.RestartPolicy.Name}}")" = unless-stopped ]', "La politique de redémarrage doit être unless-stopped."),
             ]},
            {"id": "D6.3", "points": 5, "title": "Une image propre", "manual": True,
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
    7: {
        "title": "Jour 7 — Dockerfile : cache, démarrage et arguments",
        "description": "Les subtilités du Dockerfile. Compétences : ordre des couches et cache, forme exec et PID 1, ENTRYPOINT et CMD, ARG, ENV et LABEL.",
        "lesson": """<h3>Le cache de construction</h3><p>Pour chaque instruction, Docker réutilise la couche du cache si l'instruction <strong>et tout ce qui la précède</strong> sont inchangés. Pour <code>COPY</code>, « inchangé » veut dire : mêmes fichiers, même contenu. Dès qu'une couche change, <strong>toutes les suivantes</strong> sont reconstruites.</p><pre>FROM node:20-alpine<br>WORKDIR /app<br>COPY package.json package-lock.json ./   # change rarement<br>RUN npm ci --omit=dev --no-audit        # long : reste en cache tant que les deux fichiers ne changent pas<br>COPY . .                                # change à chaque modification du code</pre><p>Avec <code>COPY . .</code> <em>avant</em> <code>npm ci</code>, la moindre virgule modifiée dans <code>server.js</code> relance l'installation des dépendances. <code>docker build --progress=plain</code> affiche <code>CACHED</code> pour chaque étape réutilisée.</p><div class="tip"><code>npm ci</code> installe exactement les versions de <code>package-lock.json</code> (constructions reproductibles) ; <code>--omit=dev</code> laisse de côté les outils de développement.</div><h3>Forme exec, forme shell, et PID 1</h3><pre>CMD ["node", "server.js"]   # forme exec : node est le processus n°1 du conteneur<br>CMD node server.js          # forme shell : /bin/sh -c "node server.js"</pre><p><code>docker stop</code> envoie <strong>SIGTERM au PID 1</strong>, attend 10 s, puis tue tout (SIGKILL, code de sortie 137). Si le PID 1 est un <strong>shell</strong> (forme shell, ou script de démarrage), il ne transmet pas le signal à l'application : elle est tuée sans avoir pu s'arrêter proprement.</p><ul><li>Forme exec pour <code>CMD</code> et <code>ENTRYPOINT</code>.</li><li>Dans un script de démarrage, lancez l'application avec <code>exec</code> : le shell est <strong>remplacé</strong> par l'application, qui devient le PID 1.</li></ul><pre>docker top conteneur          # qui est le PID 1 ?<br>time docker stop conteneur    # 10 s = le signal n'a pas été entendu<br>docker inspect -f '{{.State.ExitCode}}' conteneur   # 137 = tué par SIGKILL</pre><h3>ENTRYPOINT et CMD</h3><ul><li><code>ENTRYPOINT</code> : le programme, toujours exécuté.</li><li><code>CMD</code> : ses arguments <strong>par défaut</strong>, remplacés par ce que l'on écrit après le nom de l'image dans <code>docker run</code>.</li></ul><pre>ENTRYPOINT ["node", "export.js"]<br>CMD ["--format", "texte"]<br><br>docker run --rm export-produits:1.0                  # node export.js --format texte<br>docker run --rm export-produits:1.0 --format csv     # node export.js --format csv</pre><p>Sans ENTRYPOINT, les arguments de <code>docker run</code> remplacent toute la commande. <code>docker run --entrypoint sh …</code> remplace l'ENTRYPOINT, pour déboguer.</p><h3>ARG, ENV et LABEL</h3><pre>ARG APP_VERSION=dev                          # variable de CONSTRUCTION (valeur par défaut : dev)<br>ENV APP_VERSION=$APP_VERSION                 # variable d'ENVIRONNEMENT, présente à l'exécution<br>LABEL org.opencontainers.image.version=$APP_VERSION   # métadonnée de l'image<br><br>docker build --build-arg APP_VERSION=1.1 -t boutique-api:1.1 .<br>docker image inspect -f '{{json .Config.Labels}}' boutique-api:1.1</pre><ul><li>Un <code>ARG</code> n'existe que pendant la construction ; pour que l'application le voie, il faut le recopier dans un <code>ENV</code>.</li><li>Un ARG qui change invalide le cache à partir de l'endroit où il est utilisé : placez-le <strong>le plus bas possible</strong>, après <code>npm ci</code>.</li><li><code>-e</code> au lancement (ou <code>environment:</code> dans compose) reste prioritaire sur l'ENV de l'image.</li></ul>""",
        "setup": r'''
images_de_base
livrer api pointeuse export
''',
        "exercises": [
            {"id": "D7.1", "points": 5, "title": "Des constructions qui traînent", "manual": True,
             "ticket": {"from": "nadia", "body": "À chaque modification de <code>server.js</code>, la construction de l'API refait tout depuis le début. Sur notre vrai projet, avec des centaines de dépendances, ce sont des minutes perdues à chaque fois. Le projet a maintenant un <code>package-lock.json</code> : installe les dépendances avec <code>npm ci</code>, et organise le Dockerfile pour que cette étape reste <strong>en cache</strong> quand seul le code change."},
             "desc": "Le Dockerfile de <code>~/projet/api</code> installe les dépendances avec <code>RUN npm ci</code> ; après une modification de <code>server.js</code>, cette étape est reprise du cache.",
             "hints": ["Copiez d'abord <code>package.json</code> et <code>package-lock.json</code>, lancez <code>npm ci</code>, et seulement ensuite <code>COPY . .</code>.", "Vérifiez : modifiez <code>server.js</code>, puis <code>docker build --progress=plain -t boutique-api:1.0 .</code> : l'étape <code>RUN npm ci</code> doit afficher <code>CACHED</code>."],
             "checks": [
                 ('test -f $P/api/Dockerfile', "~/projet/api/Dockerfile n'existe pas (voir le jour 6)."),
                 ('grep -qiE "^RUN +npm +(ci|install)" $P/api/Dockerfile', "Le Dockerfile de l'API doit installer les dépendances (RUN npm ci)."),
                 ('npm_en_cache $P/api', "Après une modification de server.js, l'étape RUN npm est rejouée au lieu d'être reprise du cache : dans quel ordre sont les COPY ?"),
             ]},
            {"id": "D7.2", "points": 5, "title": "La pointeuse perd des passages", "manual": True,
             "ticket": {"from": "thomas", "body": "La pointeuse de l'entrepôt (<code>~/projet/pointeuse</code>) enregistre les passages quand elle s'arrête… en théorie. En pratique, <code>docker stop</code> met 10 secondes et on perd tout : le message « Arrêt propre » n'apparaît jamais dans les logs. Trouve pourquoi, corrige, et construis <code>pointeuse:1.0</code>."},
             "desc": "L'image <code>pointeuse:1.0</code>, construite depuis <code>~/projet/pointeuse</code>, s'arrête en moins de 3 secondes avec <code>docker stop</code>, avec le code de sortie 0 et le message « Arrêt propre ».",
             "hints": ["Construisez l'image, lancez un conteneur, puis <code>docker top</code> : quel est le processus n°1 ? Est-ce lui qui reçoit SIGTERM ?", "Deux corrections : <code>exec node pointeuse.js</code> dans <code>demarrer.sh</code>, et la forme exec <code>CMD [\"./demarrer.sh\"]</code> dans le Dockerfile."],
             "checks": [
                 ('docker build -q -t lab-verif-pointeuse $P/pointeuse', "Le Dockerfile de ~/projet/pointeuse ne se construit pas."),
                 ('arret_propre lab-verif-pointeuse; r=$?; docker rmi lab-verif-pointeuse >/dev/null 2>&1; [ $r = 0 ]', "docker stop n'arrête pas proprement la pointeuse : SIGTERM n'atteint pas node (qui est le PID 1 ?)."),
                 ('docker image inspect pointeuse:1.0 >/dev/null && arret_propre pointeuse:1.0', "L'image pointeuse:1.0 est absente ou n'a pas été reconstruite après la correction."),
             ]},
            {"id": "D7.3", "points": 4, "title": "Un outil qui accepte des options", "manual": True,
             "ticket": {"from": "diallo", "body": "Pour nos partenaires, j'utilise <code>~/projet/export</code> (<code>node export.js --format texte|csv|json</code>). Je voudrais une image <code>export-produits:1.0</code> qui s'utilise comme une commande : <code>docker run --rm export-produits:1.0</code> me donne le catalogue en texte, et <code>docker run --rm export-produits:1.0 --format csv</code> en CSV."},
             "desc": "Avec <code>export-produits:1.0</code> : sans argument, le catalogue au format texte ; avec <code>--format csv</code> ou <code>--format json</code>, le format demandé.",
             "hints": ["<code>ENTRYPOINT</code> : le programme, toujours lancé ; <code>CMD</code> : ses arguments par défaut, remplacés par ceux de <code>docker run</code>.", "<code>ENTRYPOINT [\"node\", \"export.js\"]</code> et <code>CMD [\"--format\", \"texte\"]</code>"],
             "checks": [
                 ('test -f $P/export/Dockerfile', "~/projet/export/Dockerfile n'existe pas."),
                 ('docker image inspect export-produits:1.0', "L'image export-produits:1.0 n'existe pas."),
                 ('docker run --rm export-produits:1.0 | grep -q "SAC-40L .*€ HT"', "Sans argument, docker run --rm export-produits:1.0 doit afficher le catalogue au format texte."),
                 ('[ "$(docker run --rm export-produits:1.0 --format csv | head -1)" = "ref;libelle;prixHT" ]', "docker run --rm export-produits:1.0 --format csv ne produit pas le CSV : les arguments de docker run doivent compléter le programme (ENTRYPOINT), pas le remplacer."),
                 ('docker run --rm export-produits:1.0 --format json | jq -e "length == 4"', "docker run --rm export-produits:1.0 --format json ne produit pas le catalogue en JSON."),
             ]},
            {"id": "D7.4", "points": 4, "title": "Une version gravée dans l'image", "manual": True,
             "ticket": {"from": "sophie", "body": "En production, on ne sait jamais quelle version de l'API tourne. Je veux que la version soit <strong>gravée dans l'image</strong> au moment de la construction : l'image <code>boutique-api:1.1</code> doit s'annoncer en 1.1 dans <code>/health</code> sans aucun <code>-e</code>, et porter le label standard <code>org.opencontainers.image.version</code>. Pas de version écrite en dur dans le Dockerfile : elle est passée à la construction."},
             "desc": "<code>boutique-api:1.1</code> est construite avec <code>--build-arg APP_VERSION=1.1</code> : elle porte le label <code>org.opencontainers.image.version=1.1</code> et s'annonce en 1.1 ; sans <code>--build-arg</code>, le même Dockerfile donne une autre version.",
             "hints": ["<code>ARG APP_VERSION=dev</code>, puis <code>ENV APP_VERSION=$APP_VERSION</code> (l'ARG disparaît après la construction) et <code>LABEL org.opencontainers.image.version=$APP_VERSION</code>.", "Placez ces lignes après <code>npm ci</code> pour ne pas casser le cache. Puis <code>docker build --build-arg APP_VERSION=1.1 -t boutique-api:1.1 .</code>"],
             "checks": [
                 ('docker image inspect boutique-api:1.1', "L'image boutique-api:1.1 n'existe pas."),
                 ('[ "$(insp boutique-api:1.1 "{{index .Config.Labels \\"org.opencontainers.image.version\\"}}")" = 1.1 ]', "L'image boutique-api:1.1 doit porter le label org.opencontainers.image.version=1.1."),
                 ('[ "$(version_api boutique-api:1.1)" = 1.1 ]', "Un conteneur lancé depuis boutique-api:1.1 (sans -e) ne s'annonce pas en version 1.1 dans /health (ARG recopié dans un ENV ?)."),
                 ('docker build -q -t lab-verif-version $P/api >/dev/null && v=$(version_api lab-verif-version); docker rmi lab-verif-version >/dev/null 2>&1; [ -n "$v" ] && [ "$v" != 1.1 ]', "Construit sans --build-arg, le Dockerfile de l'API donne encore la version 1.1 : elle doit venir d'un ARG, pas être écrite en dur."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Jour 8 — Des images légères et sans secrets",
        "description": "Construction en plusieurs étapes et gestion des secrets. Compétences : multi-stage, docker history, docker save, couches, RUN --mount=type=secret.",
        "lesson": """<h3>Construction en plusieurs étapes (multi-stage)</h3><p>Les outils nécessaires pour <strong>construire</strong> (compilateur, Node, npm…) sont inutiles pour <strong>exécuter</strong>. Un Dockerfile peut enchaîner plusieurs étapes ; seule la dernière forme l'image finale :</p><pre>FROM node:20-alpine AS construction      # étape 1 : on génère<br>WORKDIR /src<br>COPY . .<br>RUN node generer.js                      # produit /src/dist<br><br>FROM nginx:alpine                        # étape 2 : l'image finale<br>COPY --from=construction /src/dist/ /usr/share/nginx/html/</pre><p>L'image finale ne contient que nginx et le site : pas de Node, pas de sources. Plus légère, et moins de logiciels à mettre à jour ou à attaquer.</p><h3>Une image garde toutes ses couches</h3><p>Chaque instruction ajoute une couche, et une image est l'empilement de <strong>toutes</strong> ses couches. Supprimer un fichier dans une instruction suivante ne fait que le <strong>masquer</strong> : il reste dans la couche où il a été ajouté.</p><pre>docker history ancienne-api:0.9                # les instructions et la taille de chaque couche<br>docker history --no-trunc ancienne-api:0.9     # les commandes complètes… avec la valeur des ARG !<br>docker save ancienne-api:0.9 -o image.tar       # l'image complète : un tar de couches (elles-mêmes des tar)<br>tar -xf image.tar ; ls blobs/sha256/<br>tar -tf blobs/sha256/&lt;empreinte&gt;               # contenu d'une couche</pre><div class="tip">Une image se partage : registre, sauvegarde, collègue… Tout ce qui est passé dans un <code>ARG</code> ou copié dans une couche doit être considéré comme <strong>publié</strong>.</div><h3>Les secrets de construction</h3><p>BuildKit peut fournir un secret à <strong>une seule instruction RUN</strong>, sans l'écrire dans aucune couche ni dans l'historique :</p><pre>RUN --mount=type=secret,id=licence ./activer.sh /run/secrets/licence<br><br>docker build --secret id=licence,src=$HOME/licences/reassort.txt -t outil-reassort:1.0 .</pre><p>Le fichier est monté dans <code>/run/secrets/&lt;id&gt;</code> le temps du RUN, puis disparaît. Gardez aussi les secrets <strong>hors du contexte</strong> de construction (ou dans <code>.dockerignore</code>) : un <code>COPY . .</code> les embarquerait.</p>""",
        "setup": r'''
images_de_base
livrer catalogue prive
# Licence du fournisseur de l'outil de réassort, hors du projet
mkdir -p $H/licences
licence="LIC-$(rword | tr 'a-z-' 'A-Z_')-$RANDOM$RANDOM"
echo "$licence" > $H/licences/reassort.txt
chmod 600 $H/licences/reassort.txt
own $H/licences
activ=$(sha256sum $H/licences/reassort.txt | cut -c1-16)
# L'ancienne image de Marc : un mot de passe passé en ARG, et un fichier « supprimé » dans une couche suivante
dbpw="$(rword)_$RANDOM"; mdp="$(rword)_$RANDOM"
t=$(mktemp -d); mkdir -p $t/config
echo "motdepasse=$mdp" > $t/config/identifiants.txt
echo "base=boutique" > $t/config/app.conf
cat > $t/Dockerfile <<'EOF'
FROM alpine
ARG DB_PASSWORD
COPY config/ /config/
RUN echo "Initialisation de la base avec $DB_PASSWORD" > /dev/null && rm /config/identifiants.txt
CMD ["cat", "/config/app.conf"]
EOF
docker rmi -f ancienne-api:0.9 >/dev/null 2>&1 || true
docker build -q --build-arg DB_PASSWORD="$dbpw" -t ancienne-api:0.9 $t >/dev/null
rm -rf $t
emit DBPW "$dbpw"
emit COUCHE "$mdp"
emit LICENCE "$licence"
emit ACTIV "$activ"
''',
        "exercises": [
            {"id": "D8.1", "points": 5, "title": "Le catalogue sans Node",
             "ticket": {"from": "nadia", "body": "Le catalogue en ligne (<code>~/projet/catalogue</code>) est une page statique <strong>générée</strong> par <code>node generer.js</code> (dans <code>dist/</code>). Il faut Node pour la générer, mais surtout pas pour la servir. Écris un Dockerfile en deux étapes qui produit l'image <code>catalogue-web:1.0</code> (nginx, sans Node), et lance-la dans un conteneur <code>catalogue</code> sur le port <strong>8084</strong>."},
             "desc": "<code>~/projet/catalogue/Dockerfile</code> a deux étapes ; l'image <code>catalogue-web:1.0</code> ne contient pas Node ; le conteneur <code>catalogue</code> qui en est issu sert la page générée sur <code>http://localhost:8084</code>.",
             "hints": ["Étape 1 : <code>FROM node:20-alpine AS construction</code>, copie du projet, <code>RUN node generer.js</code>. Étape 2 : <code>FROM nginx:alpine</code>.", "<code>COPY --from=construction /src/dist/ /usr/share/nginx/html/</code> (adaptez le chemin à votre WORKDIR)."],
             "checks": [
                 ('test -f $P/catalogue/Dockerfile', "~/projet/catalogue/Dockerfile n'existe pas."),
                 ('[ "$(grep -ciE "^FROM " $P/catalogue/Dockerfile)" -ge 2 ]', "Le Dockerfile doit comporter deux étapes (deux FROM) : la génération, puis l'image finale."),
                 ('docker image inspect catalogue-web:1.0', "L'image catalogue-web:1.0 n'existe pas."),
                 ('docker run --rm --entrypoint sh catalogue-web:1.0 -c "! command -v node"', "L'image catalogue-web:1.0 contient Node : seul le résultat (dist/) doit être copié dans l'image finale."),
                 ('running catalogue && [ "$(insp catalogue "{{.Config.Image}}")" = catalogue-web:1.0 ]', "Le conteneur catalogue, issu de catalogue-web:1.0, ne tourne pas."),
                 ('http 8084 / | grep -q "Page générée par generer.js"', "http://localhost:8084 ne sert pas la page générée par generer.js."),
             ]},
            {"id": "D8.2", "points": 3, "title": "Un ARG n'est pas un coffre",
             "ticket": {"from": "sophie", "body": "Audit de l'ancienne image de Marc, <code>ancienne-api:0.9</code> (on n'a plus ses sources). Il paraît qu'il a passé le mot de passe de la base à la construction, avec un <code>--build-arg</code>. Si c'est vrai, n'importe qui peut le lire… Prouve-le : retrouve ce mot de passe."},
             "desc": "La valeur de <code>DB_PASSWORD</code> utilisée pour construire <code>ancienne-api:0.9</code> dans <code>~/mdp-build.txt</code>.",
             "hints": ["L'historique d'une image garde chaque instruction… et la valeur des ARG utilisés par un RUN.", "<code>docker history --no-trunc ancienne-api:0.9</code>"],
             "checks": [
                 ('a=$(ans $H/mdp-build.txt); [ "${a#DB_PASSWORD=}" = "$LAB_DBPW" ]', "Ce n'est pas le mot de passe passé à la construction de ancienne-api:0.9."),
             ]},
            {"id": "D8.3", "points": 4, "title": "Supprimé… vraiment ?",
             "ticket": {"from": "sophie", "body": "Deuxième trouvaille : dans <code>ancienne-api:0.9</code>, Marc a copié un fichier <code>/config/identifiants.txt</code>, puis l'a supprimé « par sécurité ». Un conteneur ne le voit plus, c'est vrai. Mais je parie qu'il est toujours dans l'image. Retrouve le mot de passe qu'il contient."},
             "desc": "Le mot de passe du fichier <code>/config/identifiants.txt</code> (la valeur après <code>motdepasse=</code>) dans <code>~/mdp-couche.txt</code>.",
             "hints": ["<code>docker save ancienne-api:0.9 -o image.tar</code>, puis <code>tar -xf image.tar</code> dans un dossier vide : chaque fichier de <code>blobs/sha256/</code> est une couche (ou un fichier de description).", "<code>for c in blobs/sha256/*; do tar -tf $c 2&gt;/dev/null | grep -q identifiants && echo $c; done</code>, puis <code>tar -xOf &lt;couche&gt; config/identifiants.txt</code>"],
             "checks": [
                 ('a=$(ans $H/mdp-couche.txt); [ "${a#motdepasse=}" = "$LAB_COUCHE" ]', "Ce n'est pas le mot de passe de /config/identifiants.txt."),
             ]},
            {"id": "D8.4", "points": 5, "title": "Une licence qui ne fuit pas", "manual": True,
             "ticket": {"from": "nadia", "body": "L'outil de réassort (<code>~/projet/prive</code>) doit être activé <strong>à la construction</strong> avec la licence du fournisseur, rangée dans <code>~/licences/reassort.txt</code>. Le Dockerfile de Marc la copie dans l'image (tu as vu ce que ça donne) et ne se construit même plus. Ne la copie surtout pas dans le projet : passe-la en <strong>secret de construction</strong>, et construis <code>outil-reassort:1.0</code>."},
             "desc": "<code>outil-reassort:1.0</code> est activée avec la licence de <code>~/licences/reassort.txt</code>, reçue par <code>RUN --mount=type=secret</code> ; la licence n'apparaît ni dans les couches ni dans l'historique de l'image.",
             "hints": ["Dans le Dockerfile : plus de <code>COPY licence.txt</code>, mais <code>RUN --mount=type=secret,id=licence ./activer.sh /run/secrets/licence</code>.", "<code>docker build --secret id=licence,src=$HOME/licences/reassort.txt -t outil-reassort:1.0 ~/projet/prive</code>"],
             "checks": [
                 ('grep -q "type=secret" $P/prive/Dockerfile', "Le Dockerfile doit recevoir la licence par un secret de construction (RUN --mount=type=secret…)."),
                 ('docker image inspect outil-reassort:1.0', "L'image outil-reassort:1.0 n'existe pas."),
                 ('[ "$(docker run --rm outil-reassort:1.0 cat /opt/reassort/activation)" = "$LAB_ACTIV" ]', "outil-reassort:1.0 n'est pas activée avec la licence de ~/licences/reassort.txt."),
                 ('! docker history --no-trunc outil-reassort:1.0 | grep -qF "$LAB_LICENCE"', "La licence apparaît dans l'historique de l'image (ARG ?)."),
                 ('! docker save outil-reassort:1.0 | grep -aqF "$LAB_LICENCE"', "La licence est encore présente dans une couche de l'image."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    9: {
        "title": "Jour 9 — Faire dialoguer les conteneurs",
        "description": "Réseaux utilisateur et résolution par nom. Compétences : docker network, --network, variables d'environnement.",
        "lesson": """<h3>Réseaux</h3><pre>docker network create reseau-boutique<br>docker run -d --name redis --network reseau-boutique redis:7-alpine<br>docker run -d --name api --network reseau-boutique -e REDIS_HOST=redis ... boutique-api:1.0</pre><ul><li>Sur un réseau <strong>créé par vous</strong>, les conteneurs se joignent <strong>par leur nom</strong> (DNS intégré de Docker) : l'API contacte <code>redis:6379</code>.</li><li>Sur le réseau par défaut (<code>bridge</code>), pas de résolution par nom.</li><li>Un service qui n'est utilisé que par d'autres conteneurs n'a <strong>pas</strong> besoin de <code>-p</code> : ne publiez que ce qui doit être joignable de l'extérieur.</li></ul><pre>docker network ls<br>docker network inspect reseau-boutique<br>docker network connect reseau-boutique conteneur   # brancher un conteneur existant</pre><h3>Le réseau par défaut</h3><p>Un conteneur lancé sans <code>--network</code> arrive sur le réseau <code>bridge</code> par défaut : il a une adresse IP, mais <strong>aucun nom</strong> n'y est résolu. Adresses qui changent à chaque redémarrage, noms qui ne marchent pas : c'est pour cela qu'on crée toujours ses propres réseaux.</p><p>Un conteneur peut être branché sur <strong>plusieurs</strong> réseaux, à chaud, sans le recréer :</p><pre>docker network connect reseau conteneur<br>docker network disconnect reseau conteneur<br>docker inspect -f '{{json .NetworkSettings.Networks}}' conteneur</pre><h3>Variables d'environnement</h3><p><code>-e NOM=valeur</code> configure l'application sans reconstruire l'image. Pour changer la configuration d'un conteneur existant, on le <strong>recrée</strong> (<code>docker rm -f</code> puis <code>docker run</code>).</p>""",
        "setup": r'''
images_de_base
# Deux conteneurs de l'ancienne application, sur le réseau par défaut
docker rm -f legacy-web legacy-db >/dev/null 2>&1 || true
docker network rm reseau-legacy >/dev/null 2>&1 || true
docker run -d --name legacy-db alpine sleep infinity >/dev/null
docker run -d --name legacy-web alpine sleep infinity >/dev/null
emit WEBID "$(docker inspect -f '{{.Id}}' legacy-web)"
emit DBID "$(docker inspect -f '{{.Id}}' legacy-db)"
''',
        "exercises": [
            {"id": "D9.1", "points": 6, "title": "Compter les visites",
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
            {"id": "D9.2", "points": 4, "title": "Brancher sans redémarrer",
             "ticket": {"from": "lea", "body": "L'ancienne application tourne dans deux conteneurs, <code>legacy-web</code> et <code>legacy-db</code>, lancés sans réseau particulier. <code>legacy-web</code> n'arrive pas à joindre <code>legacy-db</code> par son nom (<code>docker exec legacy-web ping -c1 legacy-db</code>). Règle ça <strong>sans arrêter ni recréer</strong> les conteneurs : ils sont en production."},
             "desc": "<code>legacy-web</code> joint <code>legacy-db</code> par son nom ; les deux conteneurs d'origine n'ont été ni recréés ni arrêtés.",
             "hints": ["Sur le réseau <code>bridge</code> par défaut, aucun nom n'est résolu. Créez un réseau (par exemple <code>reseau-legacy</code>).", "<code>docker network connect reseau-legacy legacy-web</code>, et de même pour <code>legacy-db</code>."],
             "checks": [
                 ('[ "$(insp legacy-web "{{.Id}}")" = "$LAB_WEBID" ] && [ "$(insp legacy-db "{{.Id}}")" = "$LAB_DBID" ]', "legacy-web ou legacy-db a été recréé : il fallait les brancher sans les recréer (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('running legacy-web && running legacy-db', "legacy-web et legacy-db doivent tourner."),
                 ('docker exec legacy-web ping -c1 -W2 legacy-db', "legacy-web ne joint toujours pas legacy-db par son nom."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    10: {
        "title": "Jour 10 — Toute la pile avec docker compose",
        "description": "Décrire et lancer une application multi-conteneurs. Compétences : compose.yaml, build, ports, volumes, depends_on, healthcheck, .env.",
        "lesson": """<h3>Un fichier au lieu de dix commandes</h3><pre>services:<br>  api:<br>    build: ./api                 # construit l'image depuis ./api/Dockerfile<br>    environment:<br>      REDIS_HOST: redis<br>    depends_on:<br>      - redis<br>  redis:<br>    image: redis:7-alpine<br>    volumes:<br>      - donnees:/data<br>volumes:<br>  donnees:</pre><pre>docker compose up -d --build     # construit et démarre tout<br>docker compose ps                # état des services<br>docker compose logs -f api<br>docker compose exec api sh       # shell dans un service<br>docker compose down              # arrête et supprime les conteneurs (pas les volumes)</pre><ul><li>Compose crée un réseau pour le projet : les services se joignent par leur <strong>nom de service</strong>.</li><li>Le nom du projet vient du dossier (<code>projet</code>) : conteneurs <code>projet-api-1</code>, volume <code>projet_donnees</code>…</li></ul><h3>Attendre qu'un service soit prêt</h3><pre>  redis:<br>    healthcheck:<br>      test: ["CMD", "redis-cli", "ping"]<br>      interval: 5s<br>  api:<br>    depends_on:<br>      redis:<br>        condition: service_healthy</pre><h3>Variables</h3><p>Compose lit le fichier <code>.env</code> du dossier du projet : <code>${APP_VERSION}</code> dans <code>compose.yaml</code> est remplacé par sa valeur. <code>docker compose config</code> affiche le résultat.</p><div class="tip">Les ports de l'hôte sont partagés : arrêtez d'abord les conteneurs lancés à la main (<code>docker rm -f api redis vitrine …</code>).</div>""",
        "setup": r'''
images_de_base
livrer api site nginx
''',
        "exercises": [
            {"id": "D10.1", "points": 6, "title": "La pile en un fichier",
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
            {"id": "D10.2", "points": 5, "title": "Un seul point d'entrée",
             "ticket": {"from": "sophie", "body": "Pour la sécurité, une seule porte d'entrée : ajoute un service <code>web</code> (nginx:alpine) publié sur le port <strong>8080</strong>, qui sert le site (<code>./site</code>) et relaie <code>/api/</code> vers l'API grâce à <code>./nginx/default.conf</code>. L'API ne doit plus être publiée directement."},
             "desc": "Le service <code>web</code> publie 8080, sert le site et relaie <code>/api/</code> ; le service <code>api</code> ne publie aucun port.",
             "hints": ["Montez <code>./nginx/default.conf</code> sur <code>/etc/nginx/conf.d/default.conf</code> et <code>./site</code> sur <code>/usr/share/nginx/html</code>, en lecture seule.", "Le port 8080 est peut-être encore pris par le conteneur <code>vitrine</code> du jour 3."],
             "checks": [
                 ('http 8080 / | grep -q "Cimes"', "http://localhost:8080 ne sert pas le site de la boutique."),
                 ('http 8080 /api/health | jq -e ".statut == \\"ok\\""', "http://localhost:8080/api/health ne répond pas : le proxy vers l'API ne fonctionne pas."),
                 ('cfg $P/compose.yaml \'(.services.api.ports // []) | length == 0\'', "Le service api ne doit plus publier de port : tout passe par web."),
             ]},
            {"id": "D10.3", "points": 4, "title": "Démarrer dans le bon ordre",
             "ticket": {"from": "nadia", "body": "Au démarrage, l'API renvoie parfois des erreurs parce que Redis n'est pas encore prêt. Ajoute un <strong>healthcheck</strong> à Redis, et fais attendre l'API jusqu'à ce que Redis soit <em>en bonne santé</em>."},
             "desc": "<code>redis</code> a un healthcheck (<code>redis-cli ping</code>) et est <em>healthy</em> ; <code>api</code> en dépend avec <code>condition: service_healthy</code>.",
             "hints": ['<code>healthcheck: test: ["CMD", "redis-cli", "ping"]</code>', "<code>depends_on: redis: condition: service_healthy</code>"],
             "checks": [
                 ('cfg $P/compose.yaml \'.services.redis.healthcheck.test | tostring | test("ping")\'', "Le service redis n'a pas de healthcheck basé sur redis-cli ping."),
                 ('cfg $P/compose.yaml \'.services.api.depends_on.redis.condition == "service_healthy"\'', "Le service api doit dépendre de redis avec condition: service_healthy."),
                 ('[ "$(insp "$(compose $P/compose.yaml ps -q redis)" "{{.State.Health.Status}}")" = healthy ]', "Le conteneur redis n'est pas (encore) healthy : relancez docker compose up -d."),
             ]},
            {"id": "D10.4", "points": 4, "title": "Une version configurable",
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
    11: {
        "title": "Jour 11 — Incident en production",
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
            {"id": "D11.1", "points": 8, "title": "La pile de Marc",
             "ticket": {"from": "sophie", "body": "Alerte ! La pile <code>~/incident</code> déployée par Marc juste avant son départ ne fonctionne pas : l'API devrait répondre sur <code>http://localhost:8090/visites</code>. Je n'ai pas le temps de t'en dire plus, mais je parie qu'il y a <strong>plusieurs</strong> erreurs."},
             "desc": "Après correction de <code>~/incident</code> (fichiers compose et Dockerfile), <code>http://localhost:8090/visites</code> compte les visites.",
             "hints": ["Commencez par <code>docker compose ps</code> et <code>docker compose logs api</code> dans <code>~/incident</code>.", "Trois erreurs : la commande de démarrage de l'image, le sens de la redirection de port, et le nom d'une variable d'environnement attendue par l'API (voir <code>server.js</code>)."],
             "checks": [
                 ('http 8090 /visites | jq -e ".visites >= 1"', "http://localhost:8090/visites ne compte pas les visites."),
                 ('compose $H/incident/compose.yaml ps --status running --services | grep -qx api', "Le service api de la pile incident ne tourne pas."),
             ]},
            {"id": "D11.2", "points": 3, "title": "Le disque se remplit",
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
