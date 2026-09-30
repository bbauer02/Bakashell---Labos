"""Projet final : épreuve de synthèse notée, qui enchaîne les cinq parcours sur un même projet, l'API de la boutique.

Mission 1 (Jest) : reproduire par un test le bug d'un ticket, puis le corriger ; mission 2 (Git) : livrer la
correction sur le dépôt partagé, avec le travail publié entre-temps par un collègue, et une étiquette de version ;
mission 3 (Docker) : l'image de l'API ; mission 4 (Ansible) : son déploiement sur web1 et web2 ; mission 5 (Linux) :
un incident en production sur web3.

Environnement (image projet-lab) : le poste de contrôle du parcours Ansible (ansible-core, sans sudo), avec Git, Node et
Jest. Son moteur Docker interne, réservé à root, fait tourner les serveurs Debian web1, web2, web3 (SSH, compte admin,
dépôt APT interne depot.cimes.lan qui fournit nodejs et nginx) et le serveur de construction ci1 (moteur Docker de
l'étudiant, joignable par DOCKER_HOST=tcp://ci1:2375 : l'étudiant construit ses images sans jamais accéder au moteur qui
héberge les serveurs, ni aux fichiers privés du poste de contrôle). Le dépôt partagé est un dépôt nu local.

Épreuve : aucun indice, aucune correction montrée (lignes « #? » absentes des corrigés). Les messages d'échec disent ce
qui ne va pas, sans la solution. Données tirées au sort une fois pour toutes (conservées dans le volume du moteur
Docker, /var/lib/docker/lab-projet) : bug et règles métier (P1.1), numéro de ticket, versions, port de l'API, produit de
Thomas, pannes de l'incident (P5.1). LAB_VARIANTE_<exercice> force une variante (tests du parcours).
Chaque mise en place prépare ce dont sa mission a besoin (dépôt, clone, serveurs, accès SSH) : une mission se prépare
même si la précédente n'est pas terminée, et aucune vérification ne dépend de la réussite d'une autre mission.
"""

EXERCISES_VERSION = "1"

MENTOR = "sophie"

SETUP_PRELUDE = r'''
set -e
unset DOCKER_HOST
H=/home/etudiant
B=$H/boutique
I=$H/infra
T=$H/tickets
R=/srv/git/boutique.git
L=/opt/projet-lab
ETAT=/var/lib/docker/lab-projet
CH=/var/lib/lab/chantier
export HOME=/root
emit() { echo "@$1=$2"; }
own() { chown -R etudiant:etudiant "$@"; }
corr() { node $L/correcteur.js "$@"; }
AS_ETU="runuser -u etudiant -- env HOME=$H"
MOTS=(marmotte bouquetin chamois edelweiss gentiane myrtille chocard lagopede genepi arnica)
mot() { echo "${MOTS[RANDOM % ${#MOTS[@]}]}"; }
# Attend le moteur Docker interne et l'image des serveurs (premier démarrage : environ 30 s)
for _ in $(seq 1 150); do [ -f /run/lab-ready ] && docker info >/dev/null 2>&1 && break; sleep 1; done
docker image inspect noeud-projet:1 >/dev/null 2>&1 || { echo "Les serveurs ne sont pas prêts" >&2; exit 1; }
mkdir -p $ETAT && chmod 700 $ETAT
# variante <exercice> <nombre> : tirée une fois (LAB_VARIANTE_<exercice> l'impose), conservée avec les données du moteur
variante() {
  local id=${1//./_} f v
  f=$ETAT/variante-$id; v=LAB_VARIANTE_$id
  if [ -n "${!v}" ]; then v=${!v}; elif [ -s $f ]; then v=$(cat $f); else v=$((RANDOM % $2)); fi
  echo "$v" > $f; echo "$v"
}
# donnee <CLE> <valeurs possibles…> : tirée au sort une fois pour toutes, puis conservée
donnee() { local f=$ETAT/$1; shift; if [ ! -s $f ]; then local t=("$@"); echo "${t[RANDOM % ${#t[@]}]}" > $f; fi; cat $f; }
# Commits des collègues
declare -A NOM=([thomas]="Thomas Leroy" [nadia]="Nadia Haddad")
declare -A MAIL=([thomas]=thomas.leroy [nadia]=nadia.haddad)
identite() {
  local d; d=$(date -d "@$(( $(date +%s) - $2 * 3600 ))" '+%Y-%m-%d %H:%M:%S')
  export GIT_AUTHOR_NAME="${NOM[$1]}" GIT_AUTHOR_EMAIL="${MAIL[$1]}@cimes-sentiers.fr" GIT_AUTHOR_DATE="$d" \
    GIT_COMMITTER_NAME="${NOM[$1]}" GIT_COMMITTER_EMAIL="${MAIL[$1]}@cimes-sentiers.fr" GIT_COMMITTER_DATE="$d"
}
commit() { ( identite "$1" "$2"; git add -A; git commit -q --allow-empty -m "$3" ); }
PRODUITS=("FRONTALE-RECH|Lampe frontale rechargeable 600 lm|39.9" "RECHAUD-GAZ|Réchaud à gaz compact|29.9"
  "COUTEAU-PLIANT|Couteau pliant de randonnée|24.5" "GUETRES|Guêtres imperméables|27")
# Dépôt partagé de l'équipe (dépôt nu, à l'étudiant) : historique de Thomas et Nadia, version W étiquetée
creer_depot() {
  rm -rf $CH; mkdir -p $CH/boutique
  corr livrer $CH/src
  cd $CH/boutique; git init -q -b main .
  cp -a $CH/src/server.js $CH/src/produits.json $CH/src/package.json $CH/src/package-lock.json $CH/src/.gitignore $CH/src/README.md .
  commit thomas 900 "API de la boutique : catalogue et état de santé"
  cp -a $CH/src/src $CH/src/tests .
  commit nadia 700 "Devis : remise par quantité et frais de port offerts"
  cp -a $CH/src/deploiement .
  commit thomas 500 "Script de service pour les serveurs Debian"
  cp -a $CH/src/CHANGELOG.md .
  commit nadia 300 "Version $W"
  ( identite nadia 300; git tag -a "v$W" -m "Version $W" )
  git rev-parse HEAD > $ETAT/BASE
  cd /; git clone -q --bare $CH/boutique $CH/boutique.git
  git --git-dir=$CH/boutique.git config --unset remote.origin.url || true
  chown -R etudiant:etudiant $CH/boutique.git; rm -rf $R; mv -T $CH/boutique.git $R
  rm -rf $CH
}
# initialiser : données de l'étudiant, dépôt partagé et clone ~/boutique (créés s'ils n'existent pas : le travail de
# l'étudiant n'est jamais écrasé)
initialiser() {
  variante P1.1 4 > $ETAT/BUG
  donnee SEUIL 48 54 60 66 72 >/dev/null; donnee FRAIS 4.9 5.9 6.5 7.9 >/dev/null
  donnee QTE 3 4 5 >/dev/null; donnee TAUX 5 10 15 >/dev/null
  TICKET=$(donnee TICKET $((300 + RANDOM % 600)))
  W=$(donnee W "$((1 + RANDOM % 3)).$((1 + RANDOM % 9)).0")
  X=${W%.0}.1
  PORT=$(donnee PORT $((3100 + RANDOM % 9 * 100)))
  mkdir -p $T; own $T
  [ -f $R/HEAD ] || creer_depot
  [ -e $B ] || $AS_ETU git clone -q $R $B
  if [ ! -e $B/node_modules ]; then ln -s $L/node_modules $B/node_modules; chown -h etudiant:etudiant $B/node_modules; fi
}
# point_de_depart : si la version X n'est pas encore publiée (mission 2 inachevée), consigne pour les missions suivantes
point_de_depart() {
  if $AS_ETU git --git-dir=$R rev-parse -q --verify "refs/tags/v$X" >/dev/null 2>&1; then rm -f $T/point-de-depart.txt; return 0; fi
  cat > $T/point-de-depart.txt <<EOF
Point de départ : la version $X n'a pas (encore) été publiée sur le dépôt partagé.
Pour les missions 3 et 4, partez de ~/boutique tel qu'il est : c'est son package.json qui fixe la version
annoncée par l'API. Il doit annoncer $X.
EOF
  own $T
}
# ─── Serveurs (moteur Docker interne, réservé à root) ───
declare -A IP=([web1]=11 [web2]=12 [web3]=13)
serveur() {
  local n=$1; shift
  if docker inspect "$n" >/dev/null 2>&1; then docker start "$n" >/dev/null
  else docker run -d --name "$n" --hostname "$n" --network cimes --ip "10.10.0.${IP[$n]}" --cap-add SYS_PTRACE \
         --add-host depot.cimes.lan:10.10.0.1 --restart unless-stopped --init "$@" noeud-projet:1 >/dev/null
  fi
  for _ in $(seq 1 40); do docker exec "$n" pgrep -x sshd >/dev/null 2>&1 && return 0; sleep 0.5; done
  echo "Le serveur $n ne démarre pas" >&2; return 1
}
neuf() { docker rm -f "$1" >/dev/null 2>&1 || true; serveur "$@"; }
sur() { docker exec "$1" bash -c "$2"; }
# acces <serveur>… : clé SSH de l'étudiant installée sur le compte admin, empreinte du serveur connue
acces() {
  [ -f $H/.ssh/id_ed25519 ] || $AS_ETU bash -c 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519'
  local s k; k=$(cat $H/.ssh/id_ed25519.pub)
  for s in "$@"; do
    sur $s "mkdir -p /home/admin/.ssh && touch /home/admin/.ssh/authorized_keys && { grep -qxF '$k' /home/admin/.ssh/authorized_keys || echo '$k' >> /home/admin/.ssh/authorized_keys; } && chown -R admin:admin /home/admin/.ssh && chmod 700 /home/admin/.ssh && chmod 600 /home/admin/.ssh/authorized_keys"
    $AS_ETU bash -c "ssh-keygen -q -R $s >/dev/null 2>&1; ssh-keygen -q -R 10.10.0.${IP[$s]} >/dev/null 2>&1; ssh-keyscan -q -t ed25519 $s 10.10.0.${IP[$s]} 2>/dev/null >> ~/.ssh/known_hosts" || true
  done
}
# Serveur de construction ci1 : moteur Docker de l'étudiant (réseau interne, tcp://ci1:2375), image node:24-alpine
ci_demarrer() {
  docker image inspect docker:27-dind >/dev/null 2>&1 || docker load -i $L/images/docker_27-dind.tar >/dev/null
  if docker inspect ci1 >/dev/null 2>&1; then docker start ci1 >/dev/null
  else docker run -d --name ci1 --hostname ci1 --privileged --network cimes --ip 10.10.0.30 -e DOCKER_TLS_CERTDIR= \
         -v ci1-docker:/var/lib/docker --restart unless-stopped docker:27-dind --tls=false >/dev/null
  fi
  for _ in $(seq 1 60); do docker -H tcp://10.10.0.30:2375 info >/dev/null 2>&1 && break; sleep 1; done
  docker -H tcp://10.10.0.30:2375 image inspect node:24-alpine >/dev/null 2>&1 || \
    docker -H tcp://10.10.0.30:2375 load -i $L/images/node_24-alpine.tar >/dev/null
}
'''

CHECK_PRELUDE = r'''
unset DOCKER_HOST
H=/home/etudiant
B=$H/boutique
I=$H/infra
R=/srv/git/boutique.git
CI=tcp://10.10.0.30:2375
export GIT_OPTIONAL_LOCKS=0
ans() { tr -d '[:space:]' < "$1" 2>/dev/null; }
corr() { node /opt/projet-lab/correcteur.js "$@"; }
# ─── Git : toujours en tant qu'etudiant, sans hooks ni fsmonitor (jamais git en root dans ses dépôts) ───
etu_git() { runuser -u etudiant -- env HOME=$H git -c core.fsmonitor=false -c core.hooksPath=/dev/null "$@"; }
depot() { etu_git --git-dir=$R "$@"; }
COLLEGUES='^(Thomas Leroy|Nadia Haddad|Léa Nguyen|Sophie Marchand|Julien Petit|Aminata Diallo|root|etudiant)?$'
# de_letudiant <nom> <e-mail> : une identité Git configurée par l'étudiant (pas celle d'un collègue)
de_letudiant() { ! grep -qxE "$COLLEGUES" <<<"$1" && [[ "$2" == ?*@?* ]] && [[ "$2" != *"(none)"* ]]; }
# commits_ticket <plage> : commits de l'étudiant, dans la plage, dont le message cite le ticket (#numéro)
commits_ticket() {
  local c
  for c in $(depot rev-list "$1" 2>/dev/null); do
    de_letudiant "$(depot log -1 --format=%an $c)" "$(depot log -1 --format=%ae $c)" && \
      depot log -1 --format=%B $c | grep -qE "#$LAB_TICKET([^0-9]|$)" && echo $c
  done
}
# correctif_dans <révision> : la révision contient le test du ticket et une modification de src/devis.js
correctif_dans() { depot cat-file -e "$1:tests/ticket-$LAB_TICKET.test.js" 2>/dev/null && ! depot diff --quiet "$LAB_BASE" "$1" -- src/devis.js; }
# ─── Docker : serveur de construction ci1 ───
dk() { docker -H $CI "$@"; }
ci_pret() {
  [ "$(docker inspect -f '{{.State.Running}}' ci1 2>/dev/null)" = true ] || docker start ci1 >/dev/null 2>&1
  for _ in $(seq 1 40); do dk info >/dev/null 2>&1 && return 0; sleep 1; done
  echo "MSG:le serveur de construction ci1 ne répond pas"; return 1
}
# construit <image> [dossier] : construit l'image depuis le Dockerfile de ~/boutique, EN TANT QU'etudiant (le contexte
# est lu avec ses droits), sur ci1 ; en cas d'échec, les dernières lignes de la construction
construit() {
  ci_pret || return 1
  runuser -u etudiant -- env HOME=$H DOCKER_HOST=$CI docker build -q -t "$1" "${2:-$B}" > /tmp/lab-construction.txt 2>&1 && return 0
  grep -vE '^\s*$' /tmp/lab-construction.txt | tail -n 2 | cut -c1-180 | sed 's/^/MSG:/'; return 1
}
verif() { dk rm -f "$@" >/dev/null 2>&1; true; }
# sante <conteneur> : réponse de /health, interrogée depuis l'intérieur du conteneur (8 s au plus)
sante() { local i; for i in 1 2 3 4 5 6 7 8; do dk exec "$1" wget -qO- http://localhost:3000/health 2>/dev/null && return 0; sleep 1; done; return 1; }
couches() { dk image inspect -f '{{range .RootFS.Layers}}{{println .}}{{end}}' "$1" 2>/dev/null; }
# base_alpine <image> : l'image commence par toutes les couches de node:24-alpine
base_alpine() { local b i; b=$(couches node:24-alpine); i=$(couches "$1"); [ -n "$b" ] && [ "$(echo "$i" | head -n "$(echo "$b" | wc -l)")" = "$b" ]; }
# superflu <image> : ce que l'image contient et qui ne sert pas à exécuter l'API (dépôt Git, tests, Jest, lien vers
# les modules du poste de développement)
superflu() {
  dk run --rm --entrypoint sh "$1" -c 'find / -xdev \( -name .git -o -name "*.test.js" -o -name coverage -o -path "*/node_modules/jest" -o \( -type l -name node_modules \) \) -not -path "/usr/local/lib/node_modules/*" -not -path "/proc/*" 2>/dev/null | head -n 3'
}
etape_npm() { grep -oE '^#[0-9]+ \[[^]]*\] RUN .*npm"?[ ,"]+(ci|install)' "$1" | head -1 | cut -d' ' -f1; }
# npm_en_cache : l'étape npm est reprise du cache quand seul server.js change, et rejouée quand package-lock.json change
npm_en_cache() {
  local t r=1 n u i
  ci_pret || return 1
  t=$(mktemp -d); chown etudiant:etudiant $t
  runuser -u etudiant -- cp -a $B/. $t/ || { rm -rf $t; return 1; }
  bld() { runuser -u etudiant -- env HOME=$H DOCKER_HOST=$CI docker build --progress=plain -t "$1" $t > "$2" 2>&1; }
  if bld lab-verif-cache:1 $t.1; then
    runuser -u etudiant -- sh -c "echo '// modification' >> $t/server.js"
    bld lab-verif-cache:2 $t.2 && n=$(etape_npm $t.2) && [ -n "$n" ] && grep -q "^$n CACHED" $t.2 && r=0
    [ $r = 0 ] || echo "MSG:Après une modification de server.js, l'étape npm est rejouée au lieu d'être reprise du cache (ou il n'y a pas d'étape npm)."
    if [ $r = 0 ]; then
      # Blancs propres à cette vérification (JSON toujours valide) : un contenu déjà vu serait repris du cache
      u=$(date +%s%N)$RANDOM; i=0; while [ $i -lt ${#u} ]; do printf "%$(( ${u:$i:1} + 1 ))s\n" ""; i=$((i + 1)); done > $t.blancs
      runuser -u etudiant -- sh -c "cat $t.blancs >> $t/package-lock.json"; r=1
      bld lab-verif-cache:3 $t.3 && n=$(etape_npm $t.3) && [ -n "$n" ] && ! grep -q "^$n CACHED" $t.3 && r=0
      [ $r = 0 ] || echo "MSG:Après une modification de package-lock.json, l'étape npm reste en cache : elle ne dépend donc pas de ce fichier."
    fi
  else echo "MSG:Le Dockerfile ne se construit pas."; fi
  dk rmi lab-verif-cache:1 lab-verif-cache:2 lab-verif-cache:3 >/dev/null 2>&1; rm -rf $t $t.1 $t.2 $t.3 $t.blancs; return $r
}
# ─── Serveurs (web1, web2, web3) ───
sur() { docker exec "$1" bash -c "$2" 2>/dev/null; }
# etu <commande> : exécutée par l'étudiant, depuis ~/infra (sa configuration Ansible s'applique)
etu() { su - etudiant -c "cd $I && ANSIBLE_NOCOLOR=1 ANSIBLE_PYTHON_INTERPRETER=auto_silent $1" </dev/null 2>/dev/null; }
yjson() { python3 -c 'import sys, yaml, json; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))' "$1" 2>/dev/null; }
# joue <playbook> [options] : lance le playbook de l'étudiant ; échoue si un serveur est en échec ou injoignable
joue() { etu "ansible-playbook $* 2>&1" > /tmp/lab-jeu.txt; grep -qE "^[a-z0-9]+ +: ok=" /tmp/lab-jeu.txt && ! grep -qE "failed=[1-9]|unreachable=[1-9]" /tmp/lab-jeu.txt; }
rien_change() { ! grep -qE "changed=[1-9]" /tmp/lab-jeu.txt; }
recap() {
  grep -E "^[a-z0-9]+ +: ok=|ERROR!|fatal:" /tmp/lab-jeu.txt | head -3 | cut -c1-160 | sed 's/^/MSG:/'
  grep -qiE "no hosts matched|Could not match supplied host pattern" /tmp/lab-jeu.txt && echo "MSG:aucun serveur visé : « hosts » ne correspond à aucun serveur de l'inventaire"
  return 1
}
paquet() { sur "$1" "dpkg-query -W -f='\${Status}' $2 2>/dev/null" | grep -q "install ok installed"; }
somme() { sur "$1" "sha256sum < '$2' 2>/dev/null" | cut -c1-64; }
# api <serveur> <port> <version> [compte] : /health répond avec cette version, sous ce compte (api par défaut)
api() {
  local j c; j=$(curl -fsS --max-time 5 "http://$1:$2/health" 2>/dev/null) || {
    c=$(curl -s -o /dev/null --max-time 5 -w '%{http_code}' "http://$1:$2/health" 2>/dev/null)
    if [ "${c:-000}" = 000 ]; then echo "MSG:$1 : rien ne répond sur le port $2"; else echo "MSG:$1 : le port $2 répond (HTTP $c), mais ce n'est pas l'API"; fi
    return 1; }
  [ "$(jq -r .version <<<"$j")" = "$3" ] && [ "$(jq -r .utilisateur <<<"$j")" = "${4:-api}" ] || \
    { echo "MSG:$1 : version $(jq -r .version <<<"$j"), exécutée par $(jq -r .utilisateur <<<"$j")"; return 1; }
}
attendre_api() { local i; for i in $(seq 1 "${5:-15}"); do api "$@" >/dev/null && return 0; sleep 1; done; api "$@"; }
# par_le_service <serveur> <port> : le processus qui écoute sur ce port est celui du service (/run/api-boutique.pid)
par_le_service() { sur "$1" "p=\$(cat /run/api-boutique.pid 2>/dev/null); [ -n \"\$p\" ] && ss -ltnpH 'sport = :$2' | grep -q \"pid=\$p,\""; }
# reconstruit <serveur> : serveur réinstallé à neuf, avec ses clés d'hôte et la clé d'admin déjà installée
# (comme une image de l'hébergeur) : tout ce qui n'est pas décrit par le code est perdu
reconstruit() {
  local d=/tmp/lab-rec-$1 ip
  ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$1") || return 1
  rm -rf $d && mkdir -p $d && docker cp "$1":/etc/ssh $d/ssh && docker cp "$1":/home/admin/.ssh $d/cles || return 1
  docker rm -f "$1" >/dev/null
  docker create --name "$1" --hostname "$1" --network cimes --ip "$ip" --cap-add SYS_PTRACE \
    --add-host depot.cimes.lan:10.10.0.1 --restart unless-stopped --init noeud-projet:1 >/dev/null || return 1
  docker cp $d/ssh/. "$1":/etc/ssh/ && docker cp $d/cles "$1":/home/admin/.ssh && docker start "$1" >/dev/null || return 1
  rm -rf $d
  for _ in $(seq 1 40); do docker exec "$1" pgrep -x sshd >/dev/null 2>&1 && break; sleep 0.5; done
  docker exec "$1" chown -R admin:admin /home/admin/.ssh
}
# redemarre_web3 : comme un redémarrage du serveur (processus arrêtés, services activés relancés), sans vider /var/log
redemarre_web3() {
  sur web3 "pkill -9 -x node; pkill -9 -x python3; nginx -s stop >/dev/null 2>&1; sleep 1; pkill -9 -x nginx; rm -f /run/*.pid; /usr/local/sbin/services-au-demarrage"
  true
}
'''

EPREUVE = """<div class="scenario"><h3>Projet final — épreuve notée</h3><p>Une journée ordinaire chez Cimes &amp; Sentiers : un bug signalé sur l'API de la boutique, à corriger, livrer, conteneuriser, déployer… et un incident en production. Cinq missions, sur le même projet, qui mobilisent les cinq parcours (Jest, Git, Docker, Ansible, Linux).</p><ul><li><strong>Épreuve notée</strong> : pas d'indice, pas de correction. Une vérification en échec dit ce qui ne va pas, jamais comment le corriger.</li><li>Vos données sont personnelles (bug, versions, ports, pannes) : le travail d'un voisin ne passera pas chez vous.</li><li>Les missions s'enchaînent, mais chacune peut être commencée même si la précédente n'est pas terminée (voir <code>~/tickets/point-de-depart.txt</code> s'il existe).</li><li>Les vérifications observent le résultat réel (tests exécutés, dépôt partagé, images, serveurs), pas la façon de l'obtenir.</li></ul><table class="lesson-table"><tr><th>Où</th><th>Quoi</th></tr><tr><td><code>~/tickets/</code></td><td>les tickets qui vous concernent (données propres à votre épreuve)</td></tr><tr><td><code>~/boutique</code></td><td>l'API de la boutique (clone du dépôt partagé <code>/srv/git/boutique.git</code>)</td></tr><tr><td><code>ci1</code></td><td>serveur de construction : la commande <code>docker</code> l'utilise déjà</td></tr><tr><td><code>~/infra</code></td><td>projet Ansible (inventaire et configuration prêts)</td></tr><tr><td><code>web1</code>, <code>web2</code>, <code>web3</code></td><td>serveurs Debian, en SSH avec le compte <code>admin</code> (sudo)</td></tr></table></div>"""

STEPS = {
    # ─────────────────────────────────────────────────────────────────────
    1: {
        "title": "Mission 1 — Le bug du devis (Jest)",
        "description": "Reproduire un bug signalé par un test, le corriger sans casser le reste, et laisser une suite de tests qui protège vraiment le calcul des devis.",
        "lesson": EPREUVE + """<h3>Mission 1 : le bug du devis</h3><p>Un bug du calcul des devis (<code>~/boutique/src/devis.js</code>) a été signalé : le ticket est dans <code>~/tickets/</code>. Les règles du service commercial sont écrites en tête de <code>src/devis.js</code> : c'est la référence, pas le comportement actuel du code.</p><h3>Consignes</h3><ul><li>Le test qui reproduit le bug va dans <code>tests/ticket-&lt;numéro du ticket&gt;.test.js</code>.</li><li>Vos tests sont exécutés sur une version corrigée du code (ils doivent passer), puis sur des versions boguées (ils doivent échouer). Un test qui passe toujours ne protège de rien.</li><li>Aucun test existant ne doit être supprimé ni désactivé.</li><li>Lancez les tests avec <code>npx jest</code> dans <code>~/boutique</code>. Les vérifications exécutent votre code : cliquez sur <strong>Vérifier</strong> quand vous êtes prêt·e.</li></ul>""",
        "setup": r'''
initialiser
corr ticket > $T/ticket-$TICKET.txt
own $T
emit TICKET "$TICKET"
''',
        "exercises": [
            {"id": "P1.1", "points": 5, "title": "Reproduire le bug", "manual": True,
             "ticket": {"from": "diallo", "body": "Un ticket du support est arrivé ce matin sur les devis de la boutique (vous le trouverez dans <code>~/tickets</code>). Avant que quiconque touche au code, je veux la preuve du problème : un test automatique qui le montre, dans le fichier que le ticket désigne."},
             "desc": "<code>tests/ticket-&lt;numéro&gt;.test.js</code> passe sur une version corrigée du calcul et échoue sur le code d'origine, qui contient le bug du ticket.",
             "checks": [
                 ('test -f $B/tests/ticket-$LAB_TICKET.test.js', "Le fichier de test du ticket n'existe pas dans ~/boutique/tests (son nom contient le numéro du ticket)."),
                 ('corr pass --tests tests/ticket-$LAB_TICKET.test.js --src ref', "Votre test ne passe pas sur une version corrigée du code : la valeur attendue doit venir des règles du service commercial."),
                 ('corr reproduit --tests tests/ticket-$LAB_TICKET.test.js', "Votre test ne reproduit pas le bug du ticket : il passe aussi sur le code d'origine."),
             ]},
            {"id": "P1.2", "points": 6, "title": "Corriger le calcul", "manual": True,
             "ticket": {"from": "nadia", "body": "Le bug est prouvé, à toi de le corriger dans <code>src/devis.js</code>. Attention, ce module calcule tous les devis de la boutique : la correction ne doit rien changer d'autre que ce qui est faux."},
             "desc": "<code>src/devis.js</code> respecte toutes les règles écrites en tête du fichier (tests de validation cachés), et votre test du ticket passe avec votre code.",
             "checks": [
                 ('test -f $B/tests/ticket-$LAB_TICKET.test.js && test -f $B/src/devis.js', "Il manque src/devis.js ou le test du ticket."),
                 ('corr valide', "Le calcul des devis n'est pas encore conforme aux règles du service commercial."),
                 ('corr pass --tests tests/ticket-$LAB_TICKET.test.js --src etudiant', "Votre test du ticket échoue avec votre code."),
             ]},
            {"id": "P1.3", "points": 3, "title": "La CI au vert", "manual": True,
             "ticket": {"from": "thomas", "body": "La CI lance <code>npx jest</code> sur tout le projet à chaque livraison. Elle doit être verte avec ta correction, sans qu'on ait perdu un seul test en route (et pas de <code>.skip</code> pour faire passer, hein)."},
             "desc": "Toute la suite de <code>~/boutique</code> (tests existants et test du ticket) passe avec votre code, sans test supprimé, désactivé ou isolé.",
             "checks": [
                 ('test -f $B/tests/ticket-$LAB_TICKET.test.js', "Le test du ticket n'existe pas."),
                 ('corr suite', "La suite complète du projet n'est pas verte avec votre code."),
             ]},
            {"id": "P1.4", "points": 6, "title": "Des tests qui protègent vraiment", "manual": True,
             "ticket": {"from": "nadia", "body": "Un bug corrigé qui revient six mois plus tard, c'est un test qui manquait. Je veux que notre suite détecte ce bug-là, mais aussi les erreurs voisines qu'on pourrait commettre en retouchant ce calcul. On passera tes tests sur plusieurs versions boguées plausibles du module."},
             "desc": "Toute la suite passe sur une version corrigée du calcul et échoue contre chacune des versions boguées plausibles du voisinage du bug.",
             "checks": [
                 ('test -f $B/tests/ticket-$LAB_TICKET.test.js', "Le test du ticket n'existe pas."),
                 ('corr pass --tests tout --src ref', "Votre suite ne passe pas sur une version corrigée du code."),
                 ('corr tue', "Votre suite ne détecte pas toutes les erreurs plausibles autour du bug."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Mission 2 — Livrer la correction (Git)",
        "description": "Livrer proprement la correction sur le dépôt partagé : branche, commits identifiés, intégration du travail d'un collègue, version et étiquette annotée.",
        "lesson": EPREUVE + """<h3>Mission 2 : livrer la correction</h3><p>La correction de la mission 1 est dans votre copie de travail <code>~/boutique</code> (un clone du dépôt partagé <code>/srv/git/boutique.git</code>). Pendant que vous travailliez, l'équipe a continué à publier sur le dépôt partagé.</p><h3>Consignes</h3><ul><li>Vos commits portent <strong>votre</strong> identité Git (nom et e-mail), et leur message cite le ticket (<code>#numéro</code>).</li><li>Le travail des collègues ne doit jamais être perdu ni réécrit sur le dépôt partagé.</li><li>La version corrective suit la version actuelle : <code>x.y.z</code> devient <code>x.y.(z+1)</code>.</li><li>Les vérifications lisent le dépôt partagé : ce qui n'est pas poussé n'existe pas.</li></ul>""",
        "setup": r'''
initialiser
# Thomas publie son travail sur main pendant que l'étudiant corrige le bug (une seule fois)
if ! { [ -s $ETAT/THOMAS ] && $AS_ETU git --git-dir=$R cat-file -e "$(cat $ETAT/THOMAS)^{commit}" 2>/dev/null; }; then
  IFS='|' read -r ref libelle prix <<<"${PRODUITS[$(donnee PRODUIT 0 1 2 3)]}"
  rm -rf $CH; mkdir -p $CH
  git clone -q --no-local --upload-pack="$AS_ETU git-upload-pack" $R $CH/thomas
  cd $CH/thomas
  python3 - "$ref" "$libelle" "$prix" <<'PY'
import sys
ref, libelle, prix = sys.argv[1:4]
lignes = open("produits.json", encoding="utf-8").read().rstrip("\n").split("\n")
fin = len(lignes) - 1
while fin > 0 and lignes[fin].strip() != "]":
    fin -= 1
lignes[fin - 1] = lignes[fin - 1].rstrip(",") + ","
lignes.insert(fin, f'  {{ "ref": "{ref}", "libelle": "{libelle}", "prixHT": {prix} }}')
open("produits.json", "w", encoding="utf-8").write("\n".join(lignes) + "\n")
journal = open("CHANGELOG.md", encoding="utf-8").read()
ligne = f"- Catalogue : {libelle.lower()} (Thomas)"
if "## [Non publié]" in journal:
    journal = journal.replace("## [Non publié]\n", f"## [Non publié]\n\n{ligne}\n", 1)
else:
    journal += f"\n## [Non publié]\n\n{ligne}\n"
open("CHANGELOG.md", "w", encoding="utf-8").write(journal)
PY
  commit thomas 1 "Catalogue : $libelle"
  git push -q --receive-pack="$AS_ETU git-receive-pack" origin HEAD:main
  git rev-parse HEAD > $ETAT/THOMAS
  cd /; rm -rf $CH
fi
IFS='|' read -r ref libelle prix <<<"${PRODUITS[$(cat $ETAT/PRODUIT)]}"
emit TICKET "$TICKET"
emit VERSION "$X"
emit W "$W"
emit BASE "$(cat $ETAT/BASE)"
emit THOMAS "$(cat $ETAT/THOMAS)"
emit PRODUIT "$ref"
emit LIGNE_THOMAS "- Catalogue : ${libelle,,} (Thomas)"
''',
        "exercises": [
            {"id": "P2.1", "points": 5, "title": "Une branche pour le correctif",
             "ticket": {"from": "nadia", "body": "Chez nous, rien ne part directement sur <code>main</code> : la correction passe par une branche <code>correctif-&lt;numéro du ticket&gt;</code>, publiée sur le dépôt partagé pour la relecture. Des commits à ton nom, qui citent le ticket, et rien qui n'a sa place dans un dépôt."},
             "desc": "Sur le dépôt partagé, la branche <code>correctif-&lt;numéro&gt;</code> contient au moins un commit de votre identité dont le message cite le ticket ; elle contient la correction de <code>src/devis.js</code> et le test du ticket, et aucun fichier généré (<code>node_modules</code>, <code>coverage</code>).",
             "checks": [
                 ('depot rev-parse -q --verify refs/heads/correctif-$LAB_TICKET >/dev/null', "La branche du correctif n'est pas sur le dépôt partagé (nom attendu : correctif- suivi du numéro du ticket)."),
                 ('[ -n "$(commits_ticket $LAB_BASE..refs/heads/correctif-$LAB_TICKET)" ]', "Aucun commit de la branche n'est à la fois de votre identité Git (nom, e-mail) et cite le ticket (#numéro) dans son message."),
                 ('correctif_dans refs/heads/correctif-$LAB_TICKET', "La branche ne contient pas à la fois le test du ticket et la correction de src/devis.js."),
                 ("! depot ls-tree -r --name-only refs/heads/correctif-$LAB_TICKET | grep -qE '^(node_modules|coverage)(/|$)'", "Des fichiers qui n'ont rien à faire dans le dépôt (node_modules, coverage) ont été commités."),
             ]},
            {"id": "P2.2", "points": 7, "title": "Intégrer sans rien perdre",
             "ticket": {"from": "thomas", "body": "J'ai publié sur <code>main</code> pendant que tu corrigeais (le catalogue et le journal des modifications). Intègre ta correction à <code>main</code> sur le dépôt partagé, sans écraser mon travail : je le vérifierai."},
             "desc": "Le <code>main</code> du dépôt partagé contient le commit de Thomas (intact), votre correction (commit cité, test du ticket, <code>src/devis.js</code>) et le travail de Thomas dans les fichiers ; aucun marqueur de conflit, fichiers JSON valides.",
             "checks": [
                 ('depot merge-base --is-ancestor $LAB_THOMAS refs/heads/main', "Le commit de Thomas n'est plus dans l'historique de main sur le dépôt partagé : son travail a été écrasé ou réécrit."),
                 ('[ -n "$(commits_ticket $LAB_BASE..refs/heads/main)" ] && correctif_dans refs/heads/main', "Le main du dépôt partagé ne contient pas encore votre correction (commit de votre identité qui cite le ticket, test du ticket, src/devis.js)."),
                 ("! depot grep -qE '^(<<<<<<<|=======|>>>>>>>)( |$)' refs/heads/main --", "Il reste des marqueurs de conflit dans les fichiers de main."),
                 ('depot show main:produits.json | jq -e . >/dev/null && depot show main:package.json | jq -e . >/dev/null', "Un fichier JSON de main (produits.json ou package.json) n'est plus valide."),
                 ('depot show main:produits.json | grep -qF "\\"$LAB_PRODUIT\\"" && depot show main:CHANGELOG.md | grep -qxF -- "$LAB_LIGNE_THOMAS"', "Le travail de Thomas a disparu des fichiers de main (produit du catalogue ou ligne du journal des modifications)."),
             ]},
            {"id": "P2.3", "points": 6, "title": "La version corrective",
             "ticket": {"from": "sophie", "body": "On livre ce soir : une version corrective, numérotée à la suite de la version actuelle, avec son entrée dans le journal des modifications (le ticket y figure), et une étiquette <strong>annotée</strong> <code>v&lt;version&gt;</code> sur le dépôt partagé. L'étiquette de la version précédente ne bouge pas."},
             "desc": "Sur le dépôt partagé, <code>v&lt;version corrective&gt;</code> est une étiquette annotée par vous, sur un commit de <code>main</code> qui contient le travail de Thomas et votre correction ; dans ce commit, <code>package.json</code> annonce la nouvelle version et <code>CHANGELOG.md</code> la présente avec le numéro du ticket ; l'étiquette de la version précédente est inchangée.",
             "checks": [
                 ('[ "$(depot cat-file -t v$LAB_VERSION 2>/dev/null)" = tag ]', "L'étiquette de la version corrective n'existe pas sur le dépôt partagé, ou ce n'est pas une étiquette annotée."),
                 ('de_letudiant "$(depot for-each-ref --format="%(taggername)" refs/tags/v$LAB_VERSION)" "$(depot for-each-ref --format="%(taggeremail)" refs/tags/v$LAB_VERSION | tr -d "<>")"', "L'étiquette doit être annotée avec votre identité Git."),
                 ('c=$(depot rev-parse v$LAB_VERSION^{commit}) && depot merge-base --is-ancestor $c refs/heads/main && depot merge-base --is-ancestor $LAB_THOMAS $c && correctif_dans $c', "L'étiquette doit désigner un commit de main qui contient le travail de Thomas et votre correction."),
                 ('[ "$(depot show v$LAB_VERSION:package.json | jq -r .version)" = "$LAB_VERSION" ]', "Dans le commit étiqueté, package.json n'annonce pas la version corrective."),
                 ('j=$(depot show v$LAB_VERSION:CHANGELOG.md) && grep -qF "$LAB_VERSION" <<<"$j" && grep -qE "#$LAB_TICKET([^0-9]|$)" <<<"$j" && grep -qxF -- "$LAB_LIGNE_THOMAS" <<<"$j"', "Dans le commit étiqueté, CHANGELOG.md ne présente pas la nouvelle version avec le ticket corrigé (sans perdre la ligne de Thomas)."),
                 ('[ "$(depot rev-parse v$LAB_W^{commit} 2>/dev/null)" = "$LAB_BASE" ]', "L'étiquette de la version précédente a été supprimée ou déplacée."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Mission 3 — L'image de l'API (Docker)",
        "description": "Écrire le Dockerfile de l'API : image légère, exécutée sans root, qui tire parti du cache et surveille sa propre santé ; construire l'image de la version livrée.",
        "lesson": EPREUVE + """<h3>Mission 3 : l'image de l'API</h3><p>L'API doit tourner partout de la même façon. Le <code>Dockerfile</code> est à écrire à la racine de <code>~/boutique</code> (le dossier est le contexte de construction).</p><h3>Consignes</h3><ul><li>Votre moteur Docker est celui du serveur de construction <code>ci1</code> : les commandes <code>docker</code> du poste de contrôle l'utilisent déjà. Un port publié s'interroge sur <code>ci1</code> (par exemple <code>curl ci1:3000/health</code>).</li><li>Image de base imposée : <code>node:24-alpine</code> (déjà présente sur <code>ci1</code>) ; le serveur de construction n'a pas accès à Internet.</li><li>L'API écoute sur le port 3000 ; <code>/health</code> donne sa version et le compte qui l'exécute.</li><li>Les vérifications reconstruisent l'image depuis votre <code>Dockerfile</code>, avec vos droits.</li></ul>""",
        "setup": r'''
initialiser
ci_demarrer
point_de_depart
emit VERSION "$X"
''',
        "exercises": [
            {"id": "P3.1", "points": 5, "title": "Le Dockerfile de l'API", "manual": True,
             "ticket": {"from": "thomas", "body": "Il faut conteneuriser l'API : un <code>Dockerfile</code> à la racine de <code>~/boutique</code>, à partir de <code>node:24-alpine</code>. Et pas question qu'elle tourne en <code>root</code> dans le conteneur."},
             "desc": "<code>~/boutique/Dockerfile</code> construit une image basée sur <code>node:24-alpine</code> dont un conteneur, lancé sans option, répond sur <code>/health</code> (port 3000) avec la version de <code>~/boutique/package.json</code>, sous un autre compte que <code>root</code>.",
             "checks": [
                 ('test -f $B/Dockerfile', "~/boutique/Dockerfile n'existe pas."),
                 ('construit lab-verif-api', "Le Dockerfile ne se construit pas (lancez docker build pour voir l'erreur complète)."),
                 ('r=0; base_alpine lab-verif-api || r=1; [ $r = 0 ] || dk rmi lab-verif-api >/dev/null 2>&1; [ $r = 0 ]', "L'image doit partir de node:24-alpine."),
                 ('verif lab-verif; dk run -d --name lab-verif lab-verif-api >/dev/null && j=$(sante lab-verif); r=$?; verif lab-verif; v=$(runuser -u etudiant -- jq -r .version "$B/package.json" 2>/dev/null); echo "MSG:réponse de /health : ${j:-aucune}"; [ $r = 0 ] && [ "$(jq -r .version <<<"$j")" = "$v" ]', "Un conteneur lancé depuis l'image ne répond pas sur /health avec la version de ~/boutique/package.json."),
                 ('verif lab-verif; dk run -d --name lab-verif lab-verif-api >/dev/null && j=$(sante lab-verif); verif lab-verif; dk rmi lab-verif-api >/dev/null 2>&1; u=$(jq -r .utilisateur <<<"$j" 2>/dev/null); [ -n "$u" ] && [ "$u" != root ] && [ "$u" != null ]', "L'API s'exécute en root dans le conteneur."),
             ]},
            {"id": "P3.2", "points": 4, "title": "Une image légère", "manual": True,
             "ticket": {"from": "nadia", "body": "L'image part en production : elle ne doit contenir que ce qui sert à <em>exécuter</em> l'API. Pas notre historique Git, pas nos tests, pas Jest ni aucun outil de développement. Qu'elle ne pèse guère plus que l'image de base."},
             "desc": "Construite depuis <code>~/boutique</code>, l'image ne contient ni dépôt Git, ni tests, ni Jest, ni lien vers les modules du poste de développement, et pèse moins de 3 Mo de plus que <code>node:24-alpine</code>.",
             "checks": [
                 ('construit lab-verif-leger', "Le Dockerfile ne se construit pas."),
                 ('f=$(superflu lab-verif-leger); [ -z "$f" ] || { echo "MSG:par exemple : $(echo $f | cut -c1-120)"; dk rmi lab-verif-leger >/dev/null 2>&1; exit 1; }', "L'image contient des fichiers qui ne servent pas à exécuter l'API (dépôt Git, tests, Jest, lien node_modules du poste de développement)."),
                 ('s=$(dk image inspect -f "{{.Size}}" lab-verif-leger); b=$(dk image inspect -f "{{.Size}}" node:24-alpine); dk rmi lab-verif-leger >/dev/null 2>&1; echo "MSG:$(( (s - b) / 1000 )) ko de plus que node:24-alpine"; [ -n "$s" ] && [ $((s - b)) -lt 3000000 ]', "L'image pèse plus de 3 Mo de plus que l'image de base."),
             ]},
            {"id": "P3.3", "points": 4, "title": "Un cache bien utilisé", "manual": True,
             "ticket": {"from": "thomas", "body": "La CI reconstruit l'image à chaque commit. L'installation des dépendances (<code>npm ci</code>) ne doit être rejouée que quand les dépendances changent, pas à chaque modification du code."},
             "desc": "Construite depuis <code>~/boutique</code>, l'image installe les dépendances de production avec npm ; cette étape est reprise du cache quand seul <code>server.js</code> change, et rejouée quand <code>package-lock.json</code> change.",
             "checks": [
                 ('npm_en_cache', "L'étape d'installation des dépendances n'utilise pas le cache comme demandé."),
             ]},
            {"id": "P3.4", "points": 4, "title": "La santé dans l'image", "manual": True,
             "ticket": {"from": "nadia", "body": "Je veux que <code>docker ps</code> montre l'état de santé de l'API partout où elle tourne, sans rien ajouter au lancement : la surveillance doit être dans l'image. Une API qui ne répond plus sur <code>/health</code> doit apparaître <em>unhealthy</em>."},
             "desc": "Construite depuis <code>~/boutique</code>, l'image a un HEALTHCHECK : un conteneur de l'API devient <em>healthy</em>, un conteneur dont l'API ne répond pas devient <em>unhealthy</em>.",
             "checks": [
                 ('construit lab-verif-sante', "Le Dockerfile ne se construit pas."),
                 ('h=$(dk image inspect -f "{{json .Config.Healthcheck}}" lab-verif-sante); [ -n "$h" ] && [ "$h" != null ] || { dk rmi lab-verif-sante >/dev/null 2>&1; exit 1; }', "L'image n'a pas de HEALTHCHECK."),
                 ('verif lab-verif-s; dk run -d --name lab-verif-s --health-interval 1s lab-verif-sante >/dev/null && for i in $(seq 1 20); do sleep 1; s=$(dk inspect -f "{{.State.Health.Status}}" lab-verif-s); [ "$s" = healthy ] && break; done; verif lab-verif-s; echo "MSG:état après le lancement : $s"; [ "$s" = healthy ] || { dk rmi lab-verif-sante >/dev/null 2>&1; exit 1; }', "Un conteneur de l'API ne devient pas healthy : la commande de surveillance existe-t-elle dans l'image, interroge-t-elle le bon port ?"),
                 ('verif lab-verif-s; dk run -d --name lab-verif-s --health-interval 1s --health-retries 1 --health-start-period 1s --entrypoint sleep lab-verif-sante 60 >/dev/null && for i in $(seq 1 20); do sleep 1; s=$(dk inspect -f "{{.State.Health.Status}}" lab-verif-s); [ "$s" = unhealthy ] && break; done; verif lab-verif-s; dk rmi lab-verif-sante >/dev/null 2>&1; [ "$s" = unhealthy ]', "Quand l'API ne répond pas, le conteneur ne devient pas unhealthy : la surveillance vérifie-t-elle vraiment /health ?"),
             ]},
            {"id": "P3.5", "points": 3, "title": "L'image de la version livrée", "manual": True,
             "ticket": {"from": "sophie", "body": "L'image de la version corrective doit être disponible sur <code>ci1</code> sous le nom <code>boutique-api:&lt;version&gt;</code> (le numéro de la version corrective, sans le « v »), prête pour la production : même exigences que pour ton Dockerfile."},
             "desc": "L'image <code>boutique-api:&lt;version corrective&gt;</code> existe sur <code>ci1</code> ; son API annonce cette version sur <code>/health</code>, sans tourner en <code>root</code>, avec un HEALTHCHECK et sans fichier superflu.",
             "checks": [
                 ('ci_pret && dk image inspect boutique-api:$LAB_VERSION >/dev/null 2>&1', "L'image boutique-api de la version corrective n'existe pas sur ci1 (nom : boutique-api, étiquette : le numéro de version)."),
                 ('verif lab-verif-l; dk run -d --name lab-verif-l boutique-api:$LAB_VERSION >/dev/null && j=$(sante lab-verif-l); verif lab-verif-l; echo "MSG:réponse de /health : ${j:-aucune}"; [ "$(jq -r .version <<<"$j" 2>/dev/null)" = "$LAB_VERSION" ] && u=$(jq -r .utilisateur <<<"$j") && [ "$u" != root ]', "Un conteneur de cette image n'annonce pas la version corrective sur /health, ou s'exécute en root."),
                 ('h=$(dk image inspect -f "{{json .Config.Healthcheck}}" boutique-api:$LAB_VERSION); [ -n "$h" ] && [ "$h" != null ] && [ -z "$(superflu boutique-api:$LAB_VERSION)" ]', "Cette image n'a pas de HEALTHCHECK ou contient des fichiers superflus : reconstruisez-la depuis votre Dockerfile."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Mission 4 — Déployer l'API (Ansible)",
        "description": "Déployer la version corrective de l'API sur web1 et web2 avec un rôle Ansible : variables, modèle, handler, service activé, idempotence.",
        "lesson": EPREUVE + """<h3>Mission 4 : déployer l'API</h3><p>L'API doit tourner sur les serveurs web <code>web1</code> et <code>web2</code> (Debian, sans systemd), comme un service. Le dossier <code>deploiement/</code> de <code>~/boutique</code> explique comment l'installer sur un serveur ; le projet Ansible <code>~/infra</code> est prêt (inventaire, accès SSH). Le ticket de déploiement est dans <code>~/tickets/deploiement.txt</code>.</p><h3>Consignes</h3><ul><li>Tout se fait avec Ansible : les vérifications <strong>réinstallent les serveurs à neuf</strong> avant de rejouer votre playbook. Une modification faite à la main en SSH n'est donc jamais prise en compte.</li><li>Le playbook se lance depuis <code>~/infra</code> : <code>ansible-playbook deploiement.yml</code>.</li><li>Les serveurs n'ont accès qu'au dépôt APT interne de l'entreprise.</li></ul>""",
        "setup": r'''
initialiser
for s in web1 web2; do serveur $s; done
acces web1 web2
mkdir -p $I/roles
[ -f $I/ansible.cfg ] || printf '[defaults]\ninventory = inventaire.ini\nremote_user = admin\n' > $I/ansible.cfg
[ -f $I/inventaire.ini ] || printf '# Serveurs de l'"'"'entreprise\n\n[web]\nweb1\nweb2\n' > $I/inventaire.ini
own $I
cat > $T/deploiement.txt <<EOF
Déploiement de l'API de la boutique — demandé par Léa Nguyen

Serveurs      : groupe web de l'inventaire (web1, web2)
Version       : $X (la version corrective)
Port          : $PORT (variable Ansible api_port, surchargeable)
Compte        : api (compte système, jamais root)
Code          : /opt/api-boutique (uniquement ce qui sert à exécuter l'API)
Service       : api-boutique, démarré et activé au démarrage du serveur
EOF
own $T
point_de_depart
emit VERSION "$X"
emit PORT "$PORT"
emit PORT2 "$((PORT + 1))"
''',
        "exercises": [
            {"id": "P4.1", "points": 4, "title": "Un rôle api",
             "ticket": {"from": "lea", "body": "Je veux du code réutilisable : un rôle <code>api</code> (<code>~/infra/roles/api</code>) avec ses tâches, ses handlers et ses modèles, et un playbook <code>deploiement.yml</code> qui l'applique au groupe <code>web</code>. Le port est la variable <code>api_port</code>, avec une valeur par défaut que chacun peut surcharger."},
             "desc": "<code>roles/api</code> contient des tâches, des handlers et au moins un modèle qui utilise <code>api_port</code> ; <code>deploiement.yml</code> applique le rôle au groupe <code>web</code> sans tâches propres ; <code>api_port</code> a une valeur par défaut dans <code>defaults</code> et n'est pas figée dans <code>vars</code>.",
             "checks": [
                 ('test -f $I/deploiement.yml', "~/infra/deploiement.yml n'existe pas."),
                 ('ls -d $I/roles/api/tasks/main.yml $I/roles/api/tasks/main.yaml 2>/dev/null | grep -q . && ls -d $I/roles/api/handlers/main.yml $I/roles/api/handlers/main.yaml 2>/dev/null | grep -q .', "Le rôle api doit avoir ses tâches et ses handlers (roles/api/tasks/main.yml, roles/api/handlers/main.yml)."),
                 ("yjson $I/deploiement.yml | jq -e 'any(.[]; ([.hosts] | flatten) == [\"web\"] and ((.roles // []) | map(if type == \"string\" then . else (.role // .name) end) | index(\"api\"))) and all(.[]; ((.tasks // []) + (.pre_tasks // []) + (.post_tasks // [])) | length == 0)' >/dev/null", "deploiement.yml doit appliquer le rôle api au groupe web, sans tâches propres."),
                 ("f=$(ls $I/roles/api/defaults/main.y*ml 2>/dev/null | head -1); [ -n \"$f\" ] && yjson $f | jq -e '.api_port' >/dev/null && ! grep -rqsE '^[[:space:]]*api_port[[:space:]]*:' $I/roles/api/vars/", "api_port doit avoir sa valeur par défaut dans roles/api/defaults/main.yml (et pas dans vars, qui l'empêcherait d'être surchargée)."),
                 ('grep -rqsE "\\{\\{[^}]*api_port" $I/roles/api/templates/', "Aucun modèle du rôle (roles/api/templates) n'utilise api_port."),
             ]},
            {"id": "P4.2", "points": 8, "title": "L'API en production", "manual": True,
             "ticket": {"from": "lea", "body": "Déploie l'API sur <code>web1</code> et <code>web2</code> d'après le ticket <code>~/tickets/deploiement.txt</code>. Je vérifierai sur des serveurs réinstallés à neuf : tout doit venir du playbook."},
             "desc": "Sur des serveurs réinstallés à neuf, <code>ansible-playbook deploiement.yml</code> réussit ; ensuite, sur <code>web1</code> et <code>web2</code>, l'API de la version corrective répond sur le port du ticket, exécutée par le compte système <code>api</code> et lancée par le service <code>api-boutique</code> ; Node.js vient du dépôt interne ; <code>/opt/api-boutique</code> ne contient ni tests ni modules de développement.",
             "checks": [
                 ('test -f $I/deploiement.yml', "~/infra/deploiement.yml n'existe pas."),
                 ('reconstruit web1 && reconstruit web2 && joue deploiement.yml || recap', "Sur des serveurs réinstallés à neuf, ansible-playbook deploiement.yml échoue (voir le récapitulatif)."),
                 ('for s in web1 web2; do attendre_api $s $LAB_PORT $LAB_VERSION api 10 || exit 1; done', "L'API ne répond pas sur le port du ticket avec la version corrective, exécutée par le compte api, sur les deux serveurs."),
                 ('for s in web1 web2; do u=$(sur $s "id -u api"); [ -n "$u" ] && [ "$u" -lt 1000 ] && [ "$u" -gt 0 ] || { echo "MSG:$s"; exit 1; }; done', "Le compte api doit être un compte système (ni root, ni compte d'utilisateur)."),
                 ('for s in web1 web2; do par_le_service $s $LAB_PORT && paquet $s nodejs || { echo "MSG:$s"; exit 1; }; done', "L'API doit être lancée par le service api-boutique (script de service et son fichier PID), avec le Node.js du paquet nodejs."),
                 ('for s in web1 web2; do sur $s "test -f /opt/api-boutique/server.js && ! test -e /opt/api-boutique/tests && ! test -e /opt/api-boutique/node_modules/jest" || { echo "MSG:$s"; exit 1; }; done', "/opt/api-boutique doit contenir le code de l'API, sans les tests ni les modules de développement."),
             ]},
            {"id": "P4.3", "points": 4, "title": "Rejouable et redémarrable", "manual": True,
             "ticket": {"from": "lea", "body": "Deux règles d'exploitation : on doit pouvoir rejouer le playbook n'importe quand sans rien changer ni rien couper, et un serveur qui redémarre doit relancer l'API tout seul."},
             "desc": "Rejoué, <code>deploiement.yml</code> ne change rien ; après un redémarrage de <code>web2</code>, l'API y répond à nouveau, sans intervention.",
             "checks": [
                 ('test -f $I/deploiement.yml', "~/infra/deploiement.yml n'existe pas."),
                 ('joue deploiement.yml || recap', "ansible-playbook deploiement.yml échoue (voir le récapitulatif)."),
                 ('joue deploiement.yml && rien_change || recap', "Rejoué, deploiement.yml modifie encore quelque chose : il n'est pas idempotent."),
                 ('attendre_api web2 $LAB_PORT $LAB_VERSION api 5 && docker restart -t 2 web2 >/dev/null && attendre_api web2 $LAB_PORT $LAB_VERSION api 20', "Après un redémarrage de web2, l'API n'y répond plus : le service n'est pas activé au démarrage (ou l'API n'était pas déployée)."),
             ]},
            {"id": "P4.4", "points": 6, "title": "Un changement, un redémarrage", "manual": True,
             "ticket": {"from": "lea", "body": "Le jour où on change le port, ou quand quelqu'un « bricole » le code sur un serveur, un passage du playbook doit suffire à tout remettre d'aplomb : fichiers à jour <em>et</em> API redémarrée pour en tenir compte. Mais seulement quand quelque chose a changé."},
             "desc": "Avec <code>-e api_port=&lt;autre port&gt;</code>, l'API passe sur ce port sur les deux serveurs (et quitte l'ancien) ; après une modification du code faite à la main sur <code>web1</code>, un passage normal du playbook y rétablit le port et le code de la version corrective, API redémarrée.",
             "checks": [
                 ('test -f $I/deploiement.yml', "~/infra/deploiement.yml n'existe pas."),
                 ('joue deploiement.yml -e api_port=$LAB_PORT2 || recap', "ansible-playbook deploiement.yml -e api_port=… échoue (voir le récapitulatif)."),
                 ('for s in web1 web2; do attendre_api $s $LAB_PORT2 $LAB_VERSION api 10 || exit 1; ! curl -fsS --max-time 3 http://$s:$LAB_PORT/health >/dev/null 2>&1 || { echo "MSG:$s répond encore sur l\'ancien port"; exit 1; }; done', "Avec api_port surchargée, l'API n'a pas changé de port sur les deux serveurs : le modèle utilise-t-il api_port, et l'API est-elle redémarrée quand ses réglages changent ?"),
                 (r'''sur web1 "sed -i 's/\"version\": *\"[^\"]*\"/\"version\": \"0.0.0-bricolage\"/' /opt/api-boutique/package.json && service api-boutique restart" >/dev/null; joue deploiement.yml || recap''', "Après une modification manuelle du code sur web1, ansible-playbook deploiement.yml échoue."),
                 ('for s in web1 web2; do attendre_api $s $LAB_PORT $LAB_VERSION api 10 || exit 1; done', "Après un passage normal du playbook, les serveurs ne sont pas revenus au port du ticket avec la version corrective (le vérificateur avait modifié le code de web1 à la main) : le code est-il redéployé, et l'API redémarrée quand il change ?"),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Mission 5 — Incident en production (Linux)",
        "description": "Diagnostiquer et réparer, en SSH, l'API des magasins sur web3, sans rien casser d'autre, de façon durable, puis rendre compte.",
        "volatile": True,
        "lesson": EPREUVE + """<h3>Mission 5 : incident en production</h3><p>Le serveur <code>web3</code> sert l'API aux caisses des magasins (version actuellement en production), et la vitrine des magasins (nginx, port 80). Ce matin, les caisses n'obtiennent plus de devis. Le ticket est dans <code>~/tickets/incident.txt</code>.</p><h3>Consignes</h3><ul><li>Connectez-vous en SSH : <code>ssh admin@web3</code> (sudo sans mot de passe). Ce serveur n'est pas géré par Ansible.</li><li>Il peut y avoir <strong>plusieurs causes</strong>. Réparez les causes, pas les symptômes : la réparation doit tenir après un redémarrage du serveur.</li><li>On ne supprime ni données, ni journaux d'accès (ce sont des preuves comptables), ni comptes ; on ne donne pas de droits plus larges que nécessaire ; on ne modifie ni le code ni les réglages de l'API au-delà de ce qui est cassé.</li><li>« Réinitialiser » cette mission recrée le serveur dans l'état de l'incident.</li></ul>""",
        "setup": r'''
initialiser
# Deux causes : A (disque plein, droits ou réglage) et B (port occupé par la maquette de Julien ou par une ancienne
# version) ; LAB_VARIANTE_P5_1_A impose aussi le fichier ou le réglage en cause (tests du parcours)
v=$(variante P5.1 6)
CA=$((v % 3)); CB=$((v / 3))
O="${W%%.*}.$(( $(echo $W | cut -d. -f2) - 1 )).0"
# web3 neuf : partition des journaux de l'API (8 Mo), paquets du dépôt interne
neuf web3 --tmpfs /var/log/api-boutique:size=8m,mode=0755
acces web3
sur web3 "apt-get update -qq >/dev/null 2>&1 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs nginx >/dev/null 2>&1"
rm -rf $CH; mkdir -p $CH; corr livrer $CH/w3
tar -C $CH/w3 -c server.js package.json produits.json src | docker exec -i web3 bash -c 'mkdir -p /opt/api-boutique && tar -C /opt/api-boutique -x --no-same-owner && chmod -R a+rX,go-w /opt/api-boutique'
docker cp $CH/w3/deploiement/api-boutique web3:/etc/init.d/api-boutique
sur web3 "chown root:root /etc/init.d/api-boutique && chmod 755 /etc/init.d/api-boutique && useradd -r -s /usr/sbin/nologin -d /var/lib/api-boutique api && useradd -m -s /bin/bash julien"
cat > $CH/default <<EOF
# Réglages de l'API de la boutique (serveur des magasins)
API_USER=api
API_DIR=/opt/api-boutique
API_PORT=$PORT
API_DATA=/var/lib/api-boutique
API_JOURNAUX=/var/log/api-boutique
EOF
docker cp $CH/default web3:/etc/default/api-boutique
# Données des magasins
python3 - $CH/donnees <<'PY'
import json, os, random, sys
d = sys.argv[1]; os.makedirs(d, exist_ok=True)
refs = ["SAC-40L", "GOURDE-1L", "FRONTALE", "BATONS", "CARTE-IGN", "TENTE-2P"]
commandes = [{"numero": f"MAG-{random.randint(10000, 99999)}", "magasin": random.choice(["Annecy", "Chamonix", "Grenoble", "Briançon"]),
              "lignes": [{"ref": random.choice(refs), "quantite": random.randint(1, 4)} for _ in range(random.randint(1, 3))]}
             for _ in range(random.randint(12, 30))]
json.dump(commandes, open(os.path.join(d, "commandes.json"), "w"), ensure_ascii=False, indent=1)
json.dump({r: random.randint(0, 80) for r in refs}, open(os.path.join(d, "stock.json"), "w"), indent=1)
PY
tar -C $CH/donnees -c . | docker exec -i web3 bash -c 'mkdir -p /var/lib/api-boutique && tar -C /var/lib/api-boutique -x --no-same-owner'
sur web3 "chown -R api:api /var/lib/api-boutique /var/log/api-boutique && chmod 750 /var/lib/api-boutique && chmod 640 /var/lib/api-boutique/*.json"
VITRINE="Vitrine des magasins Cimes & Sentiers — édition $(mot)-$((RANDOM % 900 + 100))"
sur web3 "sed -i 's/^worker_processes .*/worker_processes 2;/' /etc/nginx/nginx.conf"
sur web3 "echo '<!DOCTYPE html><html lang=\"fr\"><meta charset=\"utf-8\"><title>Magasins</title><h1>$VITRINE</h1></html>' > /var/www/html/index.html; update-rc.d nginx defaults >/dev/null 2>&1; service nginx restart >/dev/null 2>&1"
sur web3 "update-rc.d api-boutique defaults >/dev/null 2>&1; service api-boutique start >/dev/null 2>&1; sleep 1; curl -fsS http://localhost:$PORT/health >/dev/null; service api-boutique stop"
# Journaux d'accès : deux fichiers archivés et le journal courant (taille multiple de 4 Kio : la moindre ligne de
# plus demande un nouveau bloc à la partition)
python3 - $CH/journaux "$W" <<'PY'
import datetime, os, random, sys
d, version = sys.argv[1], sys.argv[2]; os.makedirs(d, exist_ok=True)
t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)
def ligne():
    global t
    t += datetime.timedelta(seconds=random.randint(20, 400))
    return f"{t.isoformat(timespec='milliseconds').replace('+00:00', 'Z')} GET /devis?{random.choice(['GOURDE-1L', 'SAC-40L', 'FRONTALE', 'BATONS'])}={random.randint(1, 5)}\n"
for nom in ("acces.log.2", "acces.log.1"):
    open(os.path.join(d, nom), "w").write(f"{t.isoformat(timespec='milliseconds').replace('+00:00', 'Z')} démarrage de l'API v{version}\n" + "".join(ligne() for _ in range(random.randint(40, 90))))
entete = f"{t.isoformat(timespec='milliseconds').replace('+00:00', 'Z')} démarrage de l'API v{version} (caisse {random.randint(1000, 9999)})\n"
texte = entete + "".join(ligne() for _ in range(random.randint(30, 60)))
reste = 4096 - len(texte.encode()) % 4096
while not 80 <= reste < 150:
    texte += ligne(); reste = 4096 - len(texte.encode()) % 4096
debut = f"{t.isoformat(timespec='milliseconds').replace('+00:00', 'Z')} GET /produits?session="
texte += debut + "".join(random.choice("0123456789abcdef") for _ in range(reste - 1 - len(debut.encode()))) + "\n"
assert len(texte.encode()) % 4096 == 0
open(os.path.join(d, "acces.log"), "w").write(texte)
PY
# (docker cp n'écrit pas dans une partition tmpfs : copie par tar)
tar -C $CH/journaux -c . | docker exec -i web3 tar -C /var/log/api-boutique -x --no-same-owner
sur web3 "chown api:api /var/log/api-boutique/acces.log* && chmod 640 /var/log/api-boutique/acces.log*"
# ─── Cause A : disque plein, droits, ou réglage erroné ───
case $CA in
  0) JA="trace-$(mot)-$((RANDOM % 9000 + 1000)).dump"
     sur web3 "dd if=/dev/urandom of=/var/log/api-boutique/$JA bs=64k >/dev/null 2>&1; true" ;;
  1) JA=$(echo commandes.json stock.json etat.json | cut -d' ' -f$((${LAB_VARIANTE_P5_1_A:-$((RANDOM % 3))} + 1)))
     if [ "$JA" = etat.json ]; then sur web3 "chown root:root /var/lib/api-boutique/etat.json && chmod 644 /var/lib/api-boutique/etat.json"
     else sur web3 "chown root:root /var/lib/api-boutique/$JA && chmod 600 /var/lib/api-boutique/$JA"; fi ;;
  *) case ${LAB_VARIANTE_P5_1_A:-$((RANDOM % 3))} in
       0) JA=API_USER; sur web3 "sed -i 's/^API_USER=api$/API_USER=api-boutique/' /etc/default/api-boutique" ;;
       1) JA=API_DIR; sur web3 "sed -i 's|^API_DIR=/opt/api-boutique$|API_DIR=/opt/api_boutique|' /etc/default/api-boutique" ;;
       *) JA=API_DATA; sur web3 "sed -i 's|^API_DATA=/var/lib/api-boutique$|API_DATA=/var/lib/api-boutiques|' /etc/default/api-boutique" ;;
     esac ;;
esac
# ─── Cause B : le port de l'API pris par la maquette de Julien, ou par une ancienne version lancée en root ───
if [ $CB = 0 ]; then
  JB="maquette-$(mot)"
  sur web3 "mkdir -p /home/julien/$JB && echo '<h1>Maquette de la future vitrine (Julien)</h1>' > /home/julien/$JB/index.html && chown -R julien:julien /home/julien/$JB"
  cat > $CH/maquette <<EOF
#!/bin/sh
### BEGIN INIT INFO
# Provides:          $JB
# Required-Start:    \$remote_fs \$network
# Required-Stop:     \$remote_fs \$network
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Maquette de Julien (test)
### END INIT INFO
# « Pour montrer la maquette aux magasins, sur le même port que l'API, c'est plus simple » (Julien)
case "\$1" in
  start) start-stop-daemon --start --quiet --background --make-pidfile --pidfile /run/$JB.pid --chuid julien \\
           --chdir /home/julien/$JB --exec /usr/bin/python3 -- -m http.server $PORT; sleep 1 ;;
  stop) start-stop-daemon --stop --quiet --pidfile /run/$JB.pid --remove-pidfile ;;
  status) start-stop-daemon --status --pidfile /run/$JB.pid ;;
  restart) "\$0" stop; "\$0" start ;;
esac
exit 0
EOF
  docker cp $CH/maquette web3:/etc/init.d/$JB
  sur web3 "chmod 755 /etc/init.d/$JB && ln -sf ../init.d/$JB /etc/rc2.d/S00$JB && service $JB start && sleep 1"
else
  JB="api-boutique-$O"
  sur web3 "cp -a /opt/api-boutique /opt/$JB && sed -i 's/\"version\": *\"[^\"]*\"/\"version\": \"$O\"/' /opt/$JB/package.json"
  cat > $CH/ancienne <<EOF
#!/bin/sh
### BEGIN INIT INFO
# Provides:          api-ancienne
# Required-Start:    \$remote_fs \$network
# Required-Stop:     \$remote_fs \$network
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: API de la boutique (version $O)
### END INIT INFO
case "\$1" in
  start) PORT=$PORT start-stop-daemon --start --quiet --background --make-pidfile --pidfile /run/api-ancienne.pid \\
           --chdir /opt/$JB --exec /usr/bin/node -- server.js; sleep 1 ;;
  stop) start-stop-daemon --stop --quiet --pidfile /run/api-ancienne.pid --remove-pidfile ;;
  status) start-stop-daemon --status --pidfile /run/api-ancienne.pid ;;
  restart) "\$0" stop; "\$0" start ;;
esac
exit 0
EOF
  docker cp $CH/ancienne web3:/etc/init.d/api-ancienne
  sur web3 "chmod 755 /etc/init.d/api-ancienne && update-rc.d api-ancienne defaults >/dev/null 2>&1 && service api-ancienne start && sleep 1"
fi
sur web3 "service api-boutique start >/dev/null 2>&1 || true"
mkdir -p $H/incident; own $H/incident
cat > $T/incident.txt <<EOF
Incident — ouvert par Sophie Marchand

Serveur : web3 (ssh admin@web3)
Symptôme : les caisses des magasins n'obtiennent plus de devis de l'API (port $PORT).
Attendu : l'API de la version en production ($W) répond sur le port $PORT, lancée par son service
          (api-boutique), sous le compte api ; la vitrine (nginx, port 80) continue de fonctionner.

Rapport d'incident à rédiger dans ~/incident/rapport.txt : pour chaque cause trouvée, l'élément en
cause (fichier, réglage, programme ou dossier, avec son nom exact) et ce que vous avez fait.
EOF
own $T
emit W "$W"
emit PORT "$PORT"
emit CAUSES "$CA$CB"
emit JETON_A "$JA"
emit JETON_B "$JB"
emit VITRINE "$VITRINE"
emit SOMME_SERVER "$(sur web3 'sha256sum < /opt/api-boutique/server.js' | cut -c1-64)"
emit SOMME_PKG "$(sur web3 'sha256sum < /opt/api-boutique/package.json' | cut -c1-64)"
emit SOMME_DEVIS "$(sur web3 'sha256sum < /opt/api-boutique/src/devis.js' | cut -c1-64)"
emit SOMME_COMMANDES "$(sur web3 'sha256sum < /var/lib/api-boutique/commandes.json' | cut -c1-64)"
emit SOMME_STOCK "$(sur web3 'sha256sum < /var/lib/api-boutique/stock.json' | cut -c1-64)"
emit SOMME_J1 "$(sur web3 'sha256sum < /var/log/api-boutique/acces.log.1' | cut -c1-64)"
emit SOMME_J2 "$(sur web3 'sha256sum < /var/log/api-boutique/acces.log.2' | cut -c1-64)"
emit JOURNAL_DEBUT "$(sur web3 'head -n 1 /var/log/api-boutique/acces.log')"
emit SOMME_REGLAGES "$(grep -vE '^\s*(#|$)' $CH/default | sed 's/[[:space:]]//g' | sort | sha256sum | cut -c1-64)"
rm -rf $CH
''',
        "exercises": [
            {"id": "P5.1", "points": 7, "title": "Les caisses fonctionnent",
             "ticket": {"from": "sophie", "body": "Les caisses des magasins sont bloquées : plus aucun devis ! Remets l'API de <code>web3</code> en service, dans les conditions normales de production (le détail est dans <code>~/tickets/incident.txt</code>)."},
             "desc": "Sur <code>web3</code>, l'API de la version en production répond sur son port, exécutée par le compte <code>api</code> et lancée par son service <code>api-boutique</code>.",
             "checks": [
                 ('api web3 $LAB_PORT $LAB_W api', "L'API de web3 ne répond pas comme en production (bonne version, sous le compte api) sur son port."),
                 ('par_le_service web3 $LAB_PORT', "L'API répond, mais elle n'a pas été lancée par son service api-boutique."),
             ]},
            {"id": "P5.2", "points": 5, "title": "Réparé sans rien casser",
             "ticket": {"from": "lea", "body": "Une réparation qui casse autre chose n'en est pas une. Je vérifierai que les données, les journaux d'accès, la vitrine, les comptes, le code et les réglages de l'API sont intacts, et qu'aucun droit trop large n'a été donné pour « faire marcher »."},
             "desc": "L'API fonctionne, et sur <code>web3</code> : code, réglages (hors réparation), données et journaux d'accès sont intacts ; rien n'est modifiable par tous dans les dossiers de l'API ; la vitrine répond ; le compte de Julien existe toujours ; <code>admin</code> garde sudo.",
             "checks": [
                 ('api web3 $LAB_PORT $LAB_W api', "L'API de web3 ne fonctionne pas encore normalement."),
                 ('[ "$(somme web3 /opt/api-boutique/server.js)" = "$LAB_SOMME_SERVER" ] && [ "$(somme web3 /opt/api-boutique/package.json)" = "$LAB_SOMME_PKG" ] && [ "$(somme web3 /opt/api-boutique/src/devis.js)" = "$LAB_SOMME_DEVIS" ]', "Le code de l'API a été modifié : ce n'était pas la cause de la panne."),
                 ('[ "$(sur web3 "grep -vE \'^\\s*(#|$)\' /etc/default/api-boutique" | sed "s/[[:space:]]//g" | sort | sha256sum | cut -c1-64)" = "$LAB_SOMME_REGLAGES" ]', "Les réglages de l'API (/etc/default/api-boutique) ne sont pas ceux de la production : seule une erreur éventuelle devait y être corrigée."),
                 ('[ "$(somme web3 /var/lib/api-boutique/commandes.json)" = "$LAB_SOMME_COMMANDES" ] && [ "$(somme web3 /var/lib/api-boutique/stock.json)" = "$LAB_SOMME_STOCK" ]', "Les données des magasins (commandes, stock) ont été modifiées ou supprimées."),
                 ('[ "$(somme web3 /var/log/api-boutique/acces.log.1)" = "$LAB_SOMME_J1" ] && [ "$(somme web3 /var/log/api-boutique/acces.log.2)" = "$LAB_SOMME_J2" ] && [ "$(sur web3 "head -n 1 /var/log/api-boutique/acces.log")" = "$LAB_JOURNAL_DEBUT" ]', "Des journaux d'accès (preuves comptables) ont été supprimés, vidés ou modifiés."),
                 ('[ -z "$(sur web3 "find /var/lib/api-boutique /var/log/api-boutique /opt/api-boutique /etc/default/api-boutique -perm -o+w ! -type l" | head -1)" ] && [ -z "$(sur web3 "find /var/lib/api-boutique ! -user api" | head -1)" ]', "Des droits trop larges ont été donnés (fichier ou dossier modifiable par tous), ou des données de l'API n'appartiennent pas à son compte."),
                 ('curl -fsS --max-time 5 http://web3/ | grep -qF "$LAB_VITRINE"', "La vitrine des magasins (nginx, port 80) ne répond plus sur web3."),
                 ('sur web3 "id julien && test -d /home/julien && sudo -u admin sudo -n true"', "Un compte a été touché : le compte de Julien (ou son dossier personnel) a disparu, ou admin a perdu sudo."),
             ]},
            {"id": "P5.3", "points": 4, "title": "Et après un redémarrage ?", "manual": True,
             "ticket": {"from": "lea", "body": "Dernière chose avant de clore : je redémarre <code>web3</code>. Si la panne revient, c'est qu'on a soigné un symptôme, pas la cause."},
             "desc": "Après un redémarrage de <code>web3</code>, l'API de la version en production répond à nouveau sur son port, lancée par son service sous le compte <code>api</code>, et la vitrine fonctionne.",
             "checks": [
                 ('api web3 $LAB_PORT $LAB_W api', "L'API de web3 ne fonctionne pas encore normalement (avant même le redémarrage)."),
                 ('redemarre_web3; attendre_api web3 $LAB_PORT $LAB_W api 15 && par_le_service web3 $LAB_PORT', "Après un redémarrage de web3, l'API ne fonctionne plus normalement : une cause de la panne est toujours là."),
                 ('curl -fsS --max-time 5 http://web3/ | grep -qF "$LAB_VITRINE"', "Après un redémarrage de web3, la vitrine ne répond plus."),
             ]},
            {"id": "P5.4", "points": 4, "title": "Le rapport d'incident", "manual": True,
             "ticket": {"from": "sophie", "body": "La direction veut comprendre ce qui s'est passé. Rédige le rapport dans <code>~/incident/rapport.txt</code> : chaque cause, avec le nom exact de l'élément en cause, et ce que tu as fait."},
             "desc": "<code>~/incident/rapport.txt</code> nomme précisément l'élément en cause (fichier, réglage, programme ou dossier) de chacune des causes de l'incident.",
             "checks": [
                 ('test -s $H/incident/rapport.txt', "~/incident/rapport.txt n'existe pas ou est vide."),
                 ('grep -qF -- "$LAB_JETON_A" $H/incident/rapport.txt && grep -qF -- "$LAB_JETON_B" $H/incident/rapport.txt', "Le rapport ne nomme pas exactement l'élément en cause de chaque cause de l'incident."),
             ]},
        ],
    },
}
