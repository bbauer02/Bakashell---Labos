"""Définition des étapes, exercices, mises en place et vérifications.

Format d'une étape :
    title, description, lesson (HTML)
    setup     : script bash exécuté en root une fois par conteneur à l'ouverture de l'étape.
                Les lignes « @CLE=valeur » qu'il affiche sont mémorisées par la plateforme
                (jamais stockées dans le conteneur) et exposées aux vérifications via $LAB_CLE.
    volatile  : True si le setup lance des processus -> rejoué après redémarrage du conteneur.
    exercises : liste d'exercices.

Format d'un exercice :
    id, points, title, desc (HTML)
    hints   : indices débloqués un à un par l'étudiant (-1 pt chacun, minimum 1 pt).
    checks  : liste de (commande bash exécutée en root, message affiché si elle échoue).
              La première vérification en échec est renvoyée à l'étudiant.
    manual  : True si la vérification exécute du code de l'étudiant -> uniquement sur clic.

Les solutions de référence (utilisées par les tests) sont dans tests/solutions.py.
"""

# Changer cette valeur quand les identifiants d'exercices changent de sens :
# la progression existante est alors archivée au démarrage.
EXERCISES_VERSION = "2"

SETUP_PRELUDE = r'''
set -e
H=/home/etudiant
REF=/var/lib/lab/ref
mkdir -p "$REF"
emit() { echo "@$1=$2"; }
own() { chown -R etudiant:etudiant "$@"; }
mkuser() { id "$1" >/dev/null 2>&1 || useradd -m -s /bin/bash "$1"; }
WORDS=(pingouin cactus volcan boussole lanterne marmotte horizon galaxie origami tambour)
rword() { echo "${WORDS[RANDOM % ${#WORDS[@]}]}-$((RANDOM % 900 + 100))"; }
# Étapes volatiles (processus) : la mise en place complète n'est jouée qu'à la première ouverture de
# l'étape ou lors d'une réinitialisation demandée ; après un simple redémarrage du conteneur, on ne
# relance que les processus, sans défaire le travail de l'étudiant (first_run N ; done_once N).
first_run() { [ -e /run/lab-setup/step-$1 ] || [ ! -e $REF/once-$1 ]; }
done_once() { touch $REF/once-$1; }
# Valeur émise ET conservée pour être réémise après un redémarrage (kemit N CLE valeur ; reemit N)
kemit() { emit "$2" "$3"; echo "$2=$3" >> $REF/env-$1; }
reemit() { if [ -f $REF/env-$1 ]; then sed 's/^/@/' $REF/env-$1; fi; }
# Vrai si seul root peut modifier ce chemin : le fichier et chacun de ses dossiers (liens compris)
_ro_chain() { local p=$1; while :; do { [ -e "$p" ] || [ -L "$p" ]; } || return 1; [ "$(stat -c %u -- "$p")" = 0 ] || return 1; if [ ! -L "$p" ] && [ -n "$(find "$p" -maxdepth 0 -perm /022)" ]; then return 1; fi; [ "$p" = / ] && return 0; p=$(dirname -- "$p"); done; }
root_only() { case $1 in /*) ;; *) return 1 ;; esac; _ro_chain "$1" && _ro_chain "$(readlink -f -- "$1")"; }
# Copie d'un exécutable, même s'il est en cours d'exécution (évite « Text file busy » lors d'une réinitialisation)
putbin() { cp "$1" "$2.new" && mv -f "$2.new" "$2"; }
# Serveur SSH « de production » (port 2222) : clé d'hôte propre, (re)lancé à la demande
prod_sshd() {
  mkdir -p /etc/ssh/prod /run/sshd
  [ -f /etc/ssh/prod/ssh_host_ed25519_key ] || ssh-keygen -q -t ed25519 -N '' -C prod -f /etc/ssh/prod/ssh_host_ed25519_key
  local p; p=$(cat /run/sshd-prod.pid 2>/dev/null || true)
  if [ -n "$p" ] && tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q 'sshd -p 2222'; then kill "$p" 2>/dev/null || true; sleep 0.5; fi
  /usr/sbin/sshd -p 2222 -h /etc/ssh/prod/ssh_host_ed25519_key -o PidFile=/run/sshd-prod.pid
}
'''

CHECK_PRELUDE = r'''
H=/home/etudiant
REF=/var/lib/lab/ref
ans() { tr -d '[:space:]' < "$1" 2>/dev/null; }
run_as() { su -s /bin/bash "$1" -c "$2" </dev/null; }
etu_env() { su - etudiant -c "bash -ic '$1'" </dev/null 2>/dev/null | tail -n1; }
norm() { sed -e 's/[[:space:]]\+/ /g' -e 's/^ //' -e 's/ $//' | grep -v '^$' | sort -u; }
setcmp() { local f=$1; shift; [ -f "$f" ] && diff <(norm < "$f") <(eval "$*" | norm) >/dev/null; }
linecmp() { local f=$1; shift; [ -f "$f" ] && diff <(grep -v '^[[:space:]]*$' "$f") <(eval "$*" | grep -v '^[[:space:]]*$') >/dev/null; }
owner() { stat -c %U "$1" 2>/dev/null; }
perm() { stat -c %a "$1" 2>/dev/null; }
others() { stat -c %A "$1" 2>/dev/null | cut -c8-10; }
# Ni le groupe ni les autres ne peuvent écrire (fichier ou dossier)
no_gow() { [ -e "$1" ] && ! stat -c %A "$1" | cut -c6,9 | grep -q w; }
# Âge en secondes de la dernière modification d'un fichier
age() { echo $(( $(date +%s) - $(stat -c %Y "$1" 2>/dev/null || echo 0) )); }
# Vrai si seul root peut modifier ce chemin : le fichier et chacun de ses dossiers (liens compris)
_ro_chain() { local p=$1; while :; do { [ -e "$p" ] || [ -L "$p" ]; } || return 1; [ "$(stat -c %u -- "$p")" = 0 ] || return 1; if [ ! -L "$p" ] && [ -n "$(find "$p" -maxdepth 0 -perm /022)" ]; then return 1; fi; [ "$p" = / ] && return 0; p=$(dirname -- "$p"); done; }
root_only() { case $1 in /*) ;; *) return 1 ;; esac; _ro_chain "$1" && _ro_chain "$(readlink -f -- "$1")"; }
# Horaires cron : ensemble des valeurs d'un champ (*, a-b, a-b/n, */n, listes, noms de mois et de jours)
cron_set() {
  awk -v f="$1" -v lo="$2" -v hi="$3" -v k="${4:-}" 'BEGIN {
    f = tolower(f)
    if (k == "dow") { split("sun mon tue wed thu fri sat", N, " "); for (i = 1; i <= 7; i++) gsub(N[i], i - 1, f) }
    if (k == "mon") { split("jan feb mar apr may jun jul aug sep oct nov dec", N, " "); for (i = 1; i <= 12; i++) gsub(N[i], i, f) }
    n = split(f, P, ",")
    for (p = 1; p <= n; p++) {
      s = P[p]; st = 1; hs = 0
      if (index(s, "/")) { split(s, Q, "/"); s = Q[1]; if (Q[2] !~ /^[0-9]+$/ || Q[2] + 0 < 1) exit 1; st = Q[2] + 0; hs = 1 }
      if (s == "*") { a = lo; b = hi }
      else if (s ~ /^[0-9]+-[0-9]+$/) { split(s, R, "-"); a = R[1] + 0; b = R[2] + 0 }
      else if (s ~ /^[0-9]+$/) { a = s + 0; b = hs ? hi : a }
      else exit 1
      if (a < lo || b > hi || a > b) exit 1
      for (v = a; v <= b; v += st) { x = v; if (k == "dow" && x == 7) x = 0; S[x] = 1 }
    }
    for (v in S) print v
  }' | sort -n | tr '\n' ' '
}
# cron_is "ligne" m h jdm mois jds : les 5 premiers champs de la ligne désignent-ils les mêmes instants ?
cron_is() {
  local a; set -f; a=($1); set +f
  [ ${#a[@]} -ge 5 ] || return 1
  [ -n "$(cron_set "$2" 0 59)" ] && [ "$(cron_set "${a[0]}" 0 59)" = "$(cron_set "$2" 0 59)" ] \
    && [ "$(cron_set "${a[1]}" 0 23)" = "$(cron_set "$3" 0 23)" ] && [ "$(cron_set "${a[2]}" 1 31)" = "$(cron_set "$4" 1 31)" ] \
    && [ "$(cron_set "${a[3]}" 1 12 mon)" = "$(cron_set "$5" 1 12 mon)" ] && [ "$(cron_set "${a[4]}" 0 7 dow)" = "$(cron_set "$6" 0 7 dow)" ]
}
# Première ligne active d'un fichier cron (ni commentaire, ni ligne vide, ni affectation de variable)
cron_line() { grep -vE '^[[:space:]]*(#|$)' "$1" 2>/dev/null | grep -vE '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=' | head -n1; }
# Premier chemin exécuté par une ligne de /etc/cron.d (champs 7 et suivants, sans « bash »/« sh » devant)
cron_prog() { local a i; set -f; a=($1); set +f; for ((i = 6; i < ${#a[@]}; i++)); do case ${a[i]} in bash|sh|/bin/bash|/bin/sh|/usr/bin/bash) ;; *) echo "${a[i]}"; return ;; esac; done; }
# Le fichier se termine-t-il par un retour à la ligne ? (sinon cron ignore la dernière ligne)
eol_ok() { [ -s "$1" ] && [ -z "$(tail -c1 "$1")" ]; }
# cron_run UTILISATEUR FICHIER_OU_- MOTIF : exécute la 1re ligne active contenant MOTIF comme le ferait cron
# (/bin/sh, environnement minimal, variables définies dans le fichier, % non échappé = fin de la commande)
cron_run() {
  local u=$1 src=$2 pat=$3 hd t l cmd n v k=5
  if [ "$src" = - ]; then src=$(mktemp); crontab -l -u "$u" > "$src" 2>/dev/null; else k=6; cp "$src" /tmp/.lab-cron.$$ && src=/tmp/.lab-cron.$$; fi
  hd=$(getent passwd "$u" | cut -d: -f6); t=$(mktemp); chmod 755 "$t"
  echo 'cd "$HOME" || exit 1' > "$t"
  while IFS= read -r l; do
    [[ $l =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*)$ ]] || continue
    n=${BASH_REMATCH[1]}; v=${BASH_REMATCH[2]}; v=${v%"${v##*[![:space:]]}"}
    if [[ $v =~ ^\"(.*)\"$ || $v =~ ^\'(.*)\'$ ]]; then v=${BASH_REMATCH[1]}; fi
    printf "export %s='%s'\n" "$n" "${v//\'/\'\\\'\'}" >> "$t"
  done < <(grep -vE '^[[:space:]]*#' "$src")
  l=$(grep -vE '^[[:space:]]*(#|$)' "$src" | grep -vE '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=' | grep -F -- "$pat" | head -n1)
  rm -f "$src"
  [ -n "$l" ] || { rm -f "$t"; return 1; }
  cmd=$(echo "$l" | awk -v k=$k '{for (i = 1; i <= k; i++) sub(/^[[:space:]]*[^[:space:]]+/, ""); sub(/^[[:space:]]+/, ""); print}')
  printf '%s\n' "$cmd" | sed 's/\\%/\x01/g; s/%.*//; s/\x01/%/g' >> "$t"
  su -s /bin/sh "$u" -c "env -i HOME=$hd LOGNAME=$u USER=$u SHELL=/bin/sh PATH=/usr/bin:/bin /bin/sh $t" </dev/null >/dev/null 2>&1
  rm -f "$t"
}
SSHO="-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5"
'''



# ─── Scénario : l'étudiant est admin système junior chez une PME fictive ──────
# Les exercices peuvent prendre la forme d'un ticket envoyé par un personnage :
#   "ticket": {"from": "<clé de CHARACTERS>", "body": "<message HTML>"}
# « desc » décrit alors précisément le livrable attendu.

from ...scenario import CHARACTERS, COMPANY  # noqa: F401  (personnages partagés entre parcours)

# Personnage qui « donne » les indices
MENTOR = "lea"

SCENARIO_INTRO = """<div class="scenario"><h3>Bienvenue chez Cimes &amp; Sentiers</h3><p>Vous rejoignez l'équipe informatique de <strong>Cimes &amp; Sentiers</strong>, une PME de 40 salariés qui vend du matériel de randonnée en ligne, comme <strong>admin système junior</strong>. Votre prédécesseur, Marc, est parti précipitamment en laissant derrière lui des notes éparpillées, des scripts obscurs et un serveur en désordre.</p><p>Les demandes de vos collègues arrivent sous forme de <strong>tickets</strong> (onglet <em>Exercices</em>). Ce cours est votre documentation : lisez-le, puis traitez les tickets dans le terminal.</p><ul class="cast"><li><strong>Sophie Marchand</strong> — DSI, votre responsable</li><li><strong>Léa Nguyen</strong> — admin système senior, votre mentore (c'est elle qui vous donne les indices)</li><li><strong>Thomas Leroy</strong> — développeur web</li><li><strong>Aminata Diallo</strong> — responsable comptabilité</li><li><strong>Julien Petit</strong> — stagiaire, souvent perdu</li></ul></div>"""


STEPS = {
    # ─────────────────────────────────────────────────────────────────────
    1: {
        "title": "Jour 1 — Prise en main du serveur",
        "description": "Premier jour chez Cimes & Sentiers. Compétences : cd, ls, cat, fichiers cachés, noms à espaces, type d'un fichier, mkdir, touch.",
        "lesson": SCENARIO_INTRO + """<h3>Bienvenue en console !</h3><p>Le terminal affiche une invite :</p><pre>etudiant@linux-lab:~$</pre><p>Elle indique <strong>qui vous êtes</strong> (etudiant), <strong>sur quelle machine</strong> (linux-lab) et <strong>où vous êtes</strong> (<code>~</code>).</p><div class="tip"><code>~</code> est un raccourci vers votre dossier personnel : <code>/home/etudiant</code>.</div><h3>Commandes essentielles</h3><ul><li><code>whoami</code> — votre nom d'utilisateur</li><li><code>pwd</code> — le dossier courant (<em>Print Working Directory</em>)</li><li><code>cd /var/log</code> — se déplacer ; <code>cd ..</code> remonte d'un niveau ; <code>cd</code> seul ramène dans <code>~</code></li><li><code>ls</code> — lister le dossier courant ; <code>ls /etc</code> — lister un autre dossier ; <code>ls -a</code> montre aussi les fichiers <strong>cachés</strong>, dont le nom commence par <code>.</code></li><li><code>cat /etc/hostname</code> — afficher le contenu d'un fichier</li><li><code>mkdir photos</code> — créer un dossier ; <code>touch liste-courses.txt</code> — créer un fichier vide</li></ul><h3>Lire un ls -l</h3><pre>-rw-r--r-- 1 etudiant etudiant 1240 Mar 12 09:15 budget.txt<br>drwxr-xr-x 2 etudiant etudiant 4096 Mar 10 17:02 photos</pre><p>Dans l'ordre : le type (<code>-</code> fichier, <code>d</code> dossier, <code>l</code> lien) et les droits, le nombre de liens, le propriétaire, le groupe, la taille en octets, la date de dernière modification, le nom.</p><h3>Écrire une réponse dans un fichier</h3><pre>echo "ma réponse" &gt; ~/reponse.txt</pre><p>Le symbole <code>&gt;</code> envoie le texte dans le fichier (nous y reviendrons en détail).</p><h3>Noms de fichiers : attention aux espaces</h3><p>Le shell découpe la ligne de commande à chaque espace : <code>cat compte rendu.txt</code> cherche <strong>deux</strong> fichiers, <code>compte</code> et <code>rendu.txt</code>. Pour un nom qui contient des espaces, mettez-le entre guillemets (<code>cat "compte rendu.txt"</code>) ou laissez <kbd>Tab</kbd> le compléter pour vous.</p><h3>L'arborescence Linux</h3><ul><li><code>/</code> — la racine, tout part d'ici</li><li><code>/home</code> — dossiers personnels</li><li><code>/etc</code> — configuration</li><li><code>/opt</code> — logiciels et données additionnels</li><li><code>/usr</code> — programmes installés</li><li><code>/var</code> — données variables (journaux, caches…)</li></ul><div class="tip">La touche <kbd>Tab</kbd> complète les noms de fichiers et de commandes, <kbd>↑</kbd> rappelle les commandes précédentes et <kbd>Ctrl+C</kbd> interrompt une commande. Si l'affichage devient illisible (après un <code>cat</code> sur un fichier binaire, par exemple), tapez <code>reset</code>.</div>""",
        "setup": r'''
A=/opt/archives-marc
rm -rf $A
mkdir -p $A/2022 $A/2023 $A/2024 $A/2025
places=()
for y in 2022 2023 2024 2025; do for s in reseau/baie reseau/local-technique postes divers materiel; do places+=("$y/$s"); done; done
mapfile -t pl < <(printf '%s\n' "${places[@]}" | shuf -n 9)
w=$(rword)
mkdir -p "$A/${pl[0]}"
printf 'Note de Marc - cadenas de la baie réseau (à jour)\nCODE=%s\n' "$w" > "$A/${pl[0]}/note.txt"
for i in 1 2 3 4; do
  o=$(rword); while [ "$o" = "$w" ]; do o=$(rword); done
  mkdir -p "$A/${pl[i]}"
  printf 'Note de Marc - cadenas de la baie réseau (PÉRIMÉ, ne plus utiliser)\nCODE=%s\n' "$o" > "$A/${pl[i]}/note.txt"
done
sujets=("postes de travail : rien à signaler" "imprimantes : toner commandé" "onduleur : batterie changée" "climatisation : contrat à renouveler")
for i in 5 6 7 8; do mkdir -p "$A/${pl[i]}"; printf 'Note de Marc - %s\n' "${sujets[i - 5]}" > "$A/${pl[i]}/note.txt"; done
chmod -R a+rX $A
emit CODE "$w"
P=$H/passation
rm -rf $P; mkdir -p $P/boite $P/pieces
echo "Bienvenue ! J'ai laissé ici ce qu'il te faut. Certaines choses ne se voient pas au premier coup d'oeil... -- Marc" > $P/lisez-moi.txt
j=$(rword); v=$(rword); while [ "$v" = "$j" ]; do v=$(rword); done
echo "$j" > $P/.jeton-vpn
printf 'Ancien jeton, RÉVOQUÉ le 3 mars : %s\n' "$v" > $P/.jeton-vpn.ancien
emit JETON "$j"
# 1.5 : des noms de fichiers qui piègent le shell
m1=$(rword); m2=$(rword); while [ "$m2" = "$m1" ]; do m2=$(rword); done
printf 'Compte rendu de la réunion de lundi\nMOT=%s\n' "$m1" > "$P/boite/notes de réunion.txt"
printf 'À traiter en priorité !\nMOT=%s\n' "$m2" > "$P/boite/-urgent.txt"
emit M1 "$m1"
emit M2 "$m2"
# 1.6 : six fichiers sans extension, un seul script
mapfile -t pn < <(shuf -i 100-999 -n 6 | sed 's/^/piece-/')
printf '#!/bin/bash\n# Relance de la sauvegarde nocturne\ntar -czf /tmp/sauvegarde.tar.gz /srv/partage\n' > $P/pieces/${pn[0]}
cp /bin/true $P/pieces/${pn[1]}
printf 'À faire : relancer le script de sauvegarde avec bash après la coupure.\n' > $P/pieces/${pn[2]}
seq 1 300 | gzip -c > $P/pieces/${pn[3]}
tar -cf $P/pieces/${pn[4]} -C /etc hostname
: > $P/pieces/${pn[5]}
chmod 644 $P/pieces/*
own $P
emit SCRIPT "${pn[0]}"
''',
        "exercises": [
            {"id": "1.1", "points": 3, "title": "Le code de la baie réseau",
             "ticket": {"from": "sophie", "body": "Bienvenue parmi nous ! Petit souci pour ton premier jour : Marc, ton prédécesseur, est parti sans nous donner le code du cadenas de la baie réseau. Il rangeait ses notes sous <code>/opt/archives-marc</code>, dans des fichiers <code>note.txt</code>… mais il ne jetait jamais les anciennes, et il ne les rangeait pas toujours au bon endroit. Tu peux me retrouver le code <strong>à jour</strong> ?"},
             "desc": "Le code (sans le <code>CODE=</code>) dans <code>~/code-baie.txt</code>.",
             "hints": ["Descendez dans l'arborescence dossier par dossier depuis <code>/opt/archives-marc</code> : lister pour voir ce qu'il y a, entrer, remonter. Toutes les années peuvent contenir des notes.",
                       "Lisez chaque <code>note.txt</code> avec <code>cat</code> : la première ligne dit si la note est périmée. Une seule note est à jour, et ce n'est pas forcément dans l'année la plus récente."],
             "checks": [
                 ('test -f $H/code-baie.txt', "Le fichier ~/code-baie.txt n'existe pas."),
                 ('a=$(ans $H/code-baie.txt); [ "${a#CODE=}" = "$LAB_CODE" ]', "Ce n'est pas le code à jour : relisez la première ligne de la note d'où vous l'avez tiré."),
             ]},
            {"id": "1.2", "points": 3, "title": "Le jeton VPN de Marc",
             "ticket": {"from": "lea", "body": "Salut, je suis Léa, c'est moi qui vais t'accompagner. Marc t'a laissé un dossier <code>~/passation</code>. Il y cachait toujours son jeton VPN… littéralement : dans un fichier caché. Récupère le jeton <strong>valide</strong>, on en a besoin pour la connexion au datacenter."},
             "desc": "Le jeton en cours de validité (tel qu'il est écrit dans son fichier) dans <code>~/jeton-vpn.txt</code>.",
             "hints": ["Relisez dans le cours ce qui rend un fichier « caché », et l'option de <code>ls</code> qui les montre.",
                       "Il y a deux fichiers cachés : affichez-les tous les deux et gardez le jeton qui n'est pas révoqué."],
             "checks": [
                 ('[ "$(ans $H/jeton-vpn.txt)" = "$LAB_JETON" ]', "~/jeton-vpn.txt n'existe pas ou ne contient pas le jeton valide."),
             ]},
            {"id": "1.3", "points": 3, "title": "Ton espace de travail",
             "ticket": {"from": "sophie", "body": "Chez nous, chacun range ses documents et ses projets au même endroit, ça évite de chercher partout quand quelqu'un est absent. Prépare-toi un dossier pour chaque."},
             "desc": "Les dossiers <code>~/documents</code> et <code>~/projets</code>, créés sans <code>sudo</code>.",
             "hints": ["La commande qui crée un dossier est l'abréviation de <em>make directory</em>. Pas besoin de sudo : vous êtes chez vous.",
                       "Elle accepte plusieurs noms à la suite ; vérifiez ensuite avec <code>ls -l ~</code> que les deux dossiers vous appartiennent."],
             "checks": [
                 ('test -d $H/documents && test -d $H/projets', "Les dossiers ~/documents et ~/projets doivent exister."),
                 ('[ "$(owner $H/documents)" = etudiant ] && [ "$(owner $H/projets)" = etudiant ]', "Un des dossiers appartient à root (il a été créé avec sudo) : supprimez-le avec « sudo rmdir » suivi de son chemin, puis recréez-le sans sudo."),
             ]},
            {"id": "1.4", "points": 3, "title": "Journal de bord",
             "ticket": {"from": "lea", "body": "Conseil de vieille admin : note tout ce que tu fais sur un serveur. Le jour où ça casse, tu seras contente ou content d'avoir un historique. Commence par créer ton journal dans tes documents, vide pour l'instant."},
             "desc": "Un fichier <strong>vide</strong> <code>~/documents/journal.txt</code>, qui vous appartient.",
             "hints": ["Une commande du cours crée un fichier vide sans ouvrir d'éditeur.",
                       "Le dossier <code>~/documents</code> doit exister (exercice précédent) ; <code>ls -l ~/documents</code> doit ensuite montrer une taille de 0."],
             "checks": [
                 ('test -f $H/documents/journal.txt', "Le fichier ~/documents/journal.txt n'existe pas."),
                 ('[ "$(owner $H/documents/journal.txt)" = etudiant ]', "Le fichier doit vous appartenir (créez-le sans sudo)."),
                 ('! test -s $H/documents/journal.txt', "Le journal n'est pas vide : Léa le veut vide pour l'instant."),
             ]},
            {"id": "1.5", "points": 4, "title": "Des noms qui piègent",
             "ticket": {"from": "julien", "body": "Bonjour, Julien, le stagiaire. Marc a laissé deux fichiers dans <code>~/passation/boite</code>, et chaque fois que je fais <code>cat</code> dessus, j'ai des erreurs bizarres : « No such file or directory », puis « invalid option »… Il me faut les deux mots de passe qu'ils contiennent."},
             "desc": "Dans <code>~/mots.txt</code>, les deux valeurs <code>MOT=…</code> (sans <code>MOT=</code>), une par ligne : d'abord celle de <code>notes de réunion.txt</code>, puis celle de <code>-urgent.txt</code>.",
             "hints": ["Le shell découpe une ligne de commande aux espaces, et une commande prend pour une option tout argument qui commence par <code>-</code>.",
                       "Entourez le nom qui contient des espaces de guillemets. Pour le tiret, désignez le fichier par un chemin qui ne commence pas par <code>-</code> (en partant du dossier courant, par exemple), ou signalez la fin des options avec <code>--</code>."],
             "checks": [
                 ('test -f $H/mots.txt', "Le fichier ~/mots.txt n'existe pas."),
                 (r'''diff <(printf '%s\n' "$LAB_M1" "$LAB_M2") <(grep -v '^[[:space:]]*$' $H/mots.txt | sed 's/^[[:space:]]*MOT=//; s/[[:space:]]*$//')''', "Ce ne sont pas les deux bonnes valeurs, ou elles ne sont pas dans l'ordre demandé (une par ligne)."),
             ]},
            {"id": "1.6", "points": 4, "title": "Sans extension",
             "ticket": {"from": "lea", "body": "Dans <code>~/passation/pieces</code>, Marc a laissé six fichiers sans extension. L'un d'eux est un script shell qu'il faut relire avant de le lancer. Lequel ? Et évite de les afficher un par un avec <code>cat</code> : sur un binaire, ça met le terminal en vrac."},
             "desc": "Le nom du script (juste le nom, par exemple <code>piece-000</code>) dans <code>~/script-trouve.txt</code>.",
             "hints": ["Sous Linux, l'extension n'est qu'une convention. Une commande, dont le nom est le mot anglais pour « fichier », devine le type d'un fichier en examinant son contenu.",
                       "Donnez-lui tous les fichiers du dossier d'un coup avec le joker <code>*</code>, et cherchez celui qu'elle décrit comme un script."],
             "checks": [
                 ('a=$(ans $H/script-trouve.txt); [ -n "$a" ] && [ "$(basename "$a")" = "$LAB_SCRIPT" ]', "Ce n'est pas le script (ou ~/script-trouve.txt est absent)."),
             ]},
            {"id": "1.7", "points": 4, "title": "Le squelette du mini-site",
             "ticket": {"from": "thomas", "body": "Salut, moi c'est Thomas, développeur web. Pour le mini-site vitrine, il me faut exactement ce squelette dans tes projets : un dossier <code>vitrine</code> qui contient les dossiers <code>css</code>, <code>js</code> et <code>img</code>, un <code>index.html</code> vide, et un <code>style.css</code> vide dans <code>css</code>. Rien d'autre : mon outil de publication râle au moindre fichier en trop."},
             "desc": "Dans <code>~/projets/vitrine</code>, exactement : les dossiers <code>css</code>, <code>js</code> et <code>img</code>, le fichier vide <code>index.html</code>, et le fichier vide <code>css/style.css</code>. Tout vous appartient.",
             "hints": ["Placez-vous dans le dossier du projet une fois créé : les chemins relatifs seront plus courts, et <code>ls</code> vous montrera le résultat à chaque étape.",
                       "<code>mkdir</code> et <code>touch</code> acceptent plusieurs noms à la fois, et un nom peut contenir un chemin (<code>dossier/fichier</code>)."],
             "checks": [
                 ('test -d $H/projets/vitrine', "Le dossier ~/projets/vitrine n'existe pas."),
                 (r'''cd $H/projets/vitrine && diff <(find . | LC_ALL=C sort) <(printf '%s\n' . ./css ./css/style.css ./img ./index.html ./js | LC_ALL=C sort)''', "Le contenu de ~/projets/vitrine ne correspond pas exactement à la demande : un élément manque, est en trop ou est mal placé."),
                 ('cd $H/projets/vitrine && test -d css && test -d js && test -d img && test -f index.html && test -f css/style.css && ! test -s index.html && ! test -s css/style.css', "css, js et img doivent être des dossiers, index.html et css/style.css des fichiers vides."),
                 ('[ -z "$(find $H/projets/vitrine ! -user etudiant)" ]', "Certains éléments appartiennent à root : créez-les sans sudo."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Jour 2 — La doc et les chemins",
        "description": "Lire le manuel et ne plus se perdre dans l'arborescence. Compétences : man, commandes internes du shell, less, tri de ls, chemins absolus et relatifs, . et ..",
        "lesson": """<h3>RTFM : Read The Manual !</h3><pre>man &lt;commande&gt;</pre><p>Dans le manuel : <kbd>/mot</kbd> recherche, <kbd>n</kbd> passe au résultat suivant (<kbd>N</kbd> au précédent), <kbd>g</kbd> et <kbd>G</kbd> vont au début et à la fin, <kbd>q</kbd> quitte.</p><div class="tip"><strong>Conventions :</strong> <code>[PARAM]</code> = optionnel, <code>...</code> = répétable. Beaucoup de commandes acceptent aussi <code>--help</code>, une aide plus courte.</div><p>Le manuel est découpé en <strong>sections</strong> : 1 pour les commandes, 5 pour les formats de fichiers, 8 pour les commandes d'administration. <code>man -f crontab</code> liste les pages qui portent ce nom, et <code>man 5 crontab</code> ouvre celle de la section 5. <code>man -k mot</code> cherche un mot dans la description de toutes les pages.</p><h3>Lire un long fichier : less</h3><p><code>less fichier</code> affiche un fichier page par page, avec <strong>exactement les mêmes touches</strong> que <code>man</code> (c'est d'ailleurs lui qui affiche le manuel).</p><h3>Les options</h3><ul><li><code>ls -l</code> — format détaillé</li><li><code>ls -a</code> — fichiers cachés</li><li><code>ls -la</code> — les deux combinées ; l'ordre des lettres n'a pas d'importance</li></ul><h3>Chemins absolus vs relatifs</h3><table class="lesson-table"><tr><th>Absolu</th><th>Relatif</th></tr><tr><td>Commence par <code>/</code></td><td>Part du dossier courant</td></tr><tr><td><code>/home/etudiant/projets</code></td><td><code>projets</code> (depuis <code>~</code>)</td></tr><tr><td>Toujours valable</td><td>Dépend de l'endroit où l'on est</td></tr></table><div class="tip"><code>.</code> = dossier courant · <code>..</code> = dossier parent · <code>../..</code> = deux niveaux au-dessus. Depuis <code>/var/log/apt</code>, <code>../../lib</code> désigne <code>/var/lib</code>.</div>""",
        "setup": r'''
P=$H/partage-marc
mkdir -p $P/clients/2024/devis $P/clients/2023 $P/fournisseurs
# 2.3 : Marc n'a pas toujours rangé la grille tarifaire au même endroit (variante tirée au sort)
v=${LAB_VARIANTE_2_3:-$((RANDOM % 4))}
rm -f $P/tarifs.txt $P/clients/tarifs.txt $P/clients/2023/tarifs.txt $P/clients/2024/tarifs.txt
t=(clients/tarifs.txt clients/2024/tarifs.txt tarifs.txt clients/2023/tarifs.txt)
echo "Grille tarifaire clients 2025" > $P/${t[v]}
emit TARIFS "$P/${t[v]}"
echo "Devis n°2024-017 - Club alpin de Grenoble" > $P/clients/2024/devis/devis-017.txt
# 2.4 : le chemin du vieux script de Marc (variante tirée au sort)
v=${LAB_VARIANTE_2_4:-$((RANDOM % 4))}
cs=(clients/2024/../.. clients/2024/devis/../../2023 fournisseurs/../clients/./2024/.. clients/../fournisseurs/altitude-pro/..)
abs=($P $P/clients/2023 $P/clients $P/fournisseurs)
printf '#!/bin/bash\n# Sauvegarde des devis (script de Marc)\ncd ~/partage-marc/%s || exit 1\ntar -czf /tmp/sauvegarde-devis.tar.gz .\n' "${cs[v]}" > $P/vieux-script.sh
emit ABS "${abs[v]}"
# 2.2 : la question sur ls (variante tirée au sort)
v=${LAB_VARIANTE_2_2:-$((RANDOM % 4))}
qs=("les trie par taille, du plus gros au plus petit" "les trie par extension (ce qui suit le dernier point du nom)" "les trie par numéro de version (fichier-2 avant fichier-10)" "ne les trie pas du tout (ordre du dossier)")
opts=(S X v U); tris=(size extension version none)
printf 'Question de Léa : quelle option de ls, sans rien d'"'"'autre, affiche les fichiers d'"'"'un dossier mais %s ?\n' "${qs[v]}" > $H/question-man.txt
chown etudiant:etudiant $H/question-man.txt
emit OPT "${opts[v]}"
emit TRI "${tris[v]}"
# 2.5 : une commande interne du shell, sans page de manuel (variante tirée au sort)
v=${LAB_VARIANTE_2_5:-$((RANDOM % 4))}
cmds=(cd type export jobs); bopts=(-P -a -n -l)
qb=("de cd fait arriver dans le vrai dossier quand on passe par un raccourci (un lien symbolique), au lieu de garder le chemin du raccourci"
    "de type affiche toutes les définitions d'un nom (alias, fonctions, fichiers du PATH), et pas seulement celle qui sera utilisée"
    "de export retire une variable de l'environnement transmis aux programmes, sans la supprimer du shell"
    "de jobs affiche aussi le PID de chaque tâche lancée en arrière-plan")
printf 'man %s répond « No manual entry for %s ». Ma question : quelle option %s ?\n' "${cmds[v]}" "${cmds[v]}" "${qb[v]}" > $H/question-shell.txt
chown etudiant:etudiant $H/question-shell.txt
emit BCMD "${cmds[v]}"
emit BOPT "${bopts[v]}"
# 2.9 : le catalogue fournisseur à atteindre est tiré au sort
fr=(altitude-pro sentiers-diffusion montagne-equip)
for x in "${fr[@]}"; do mkdir -p $P/fournisseurs/$x; for j in 1 2 3 4; do echo "Catalogue $x n°$j" > $P/fournisseurs/$x/catalogue-$j.txt; done; done
cible=fournisseurs/${fr[RANDOM % 3]}/catalogue-$((RANDOM % 4 + 1)).txt
echo "Pour ce devis, prendre les prix du catalogue $cible (dans partage-marc)." > $P/clients/2024/devis/A-LIRE.txt
own $P
emit CIBLE "$P/$cible"
# 2.7 : des rapports aux noms trompeurs, datés au hasard
R=/opt/rapports-marc
rm -rf $R; mkdir -p $R
noms=(rapport-final.txt rapport-final-v2.txt synthese.txt bilan-trimestre.txt notes-reunion.txt point-hebdo.txt brouillon.txt compte-rendu.txt suivi-incidents.txt annexe-b.txt)
mapfile -t hs < <(shuf -i 5-2000 -n ${#noms[@]})
for i in "${!noms[@]}"; do printf 'Rapport de Marc (%s)\n' "${noms[i]}" > $R/${noms[i]}; touch -d "-${hs[i]} hours" $R/${noms[i]}; done
echo "Rapport annuel, version finale" > $R/rapport-2025-12-final.txt; touch -d "-3000 hours" $R/rapport-2025-12-final.txt
echo "NE PAS UTILISER" > $R/rapport-DEFINITIF.txt; touch -d "-2600 hours" $R/rapport-DEFINITIF.txt
chmod -R a+rX $R
emit RECENT "$(ls -t $R | head -n1)"
# 2.8 : un long journal, une seule vraie clôture
E=$H/exports
rm -rf $E; mkdir -p $E
n=$((RANDOM % 4000 + 3000)); lot=$((RANDOM % 90000 + 10000))
awk -v n=$n -v lot=$lot -v seed=$RANDOM 'BEGIN { srand(seed)
  for (i = 1; i <= 8000; i++) {
    if (i == n) { print "=== CLÔTURE ==="; print "Lot n° " lot }
    else if (i % 1500 == 0) { print "--- CLÔTURE partielle ---"; print "Lot n° " int(10000 + rand() * 89999) }
    else printf "%05d écriture comptable %d exportée\n", i, int(1000 + rand() * 9000)
  } }' > $E/journal-export.log
own $E
emit LOT "$lot"
''',
        "exercises": [
            {"id": "2.1", "points": 4, "title": "Le projet boutique",
             "ticket": {"from": "thomas", "body": "Hello ! On lance la refonte de la boutique en ligne. Tu peux me préparer le dossier des sources, <code>src</code>, dans un dossier <code>boutique</code> de tes projets ? Et note-moi la commande exacte dans <code>~/doc-install.txt</code> : je la copierai telle quelle dans la doc d'installation. Elle doit donc marcher depuis n'importe quel dossier, en une seule commande, même sur un poste où <code>boutique</code> n'existe pas encore."},
             "desc": "Le dossier <code>/home/etudiant/projets/boutique/src</code> existe et vous appartient. La première ligne de <code>~/doc-install.txt</code> est la commande unique qui le crée, avec un <strong>chemin absolu</strong> (sans <code>~</code>), et qui réussit même si <code>boutique</code> n'existe pas.",
             "hints": ["Une option de <code>mkdir</code> crée les dossiers parents manquants : cherchez-la dans <code>man mkdir</code> (le mot anglais est <em>parents</em>).",
                       "Un chemin absolu commence par <code>/</code>. Pour écrire la commande dans le fichier sans l'exécuter, mettez-la entre guillemets simples après <code>echo</code>, puis lancez-la une fois pour de bon."],
             "checks": [
                 ('test -d $H/projets/boutique/src', "Le dossier ~/projets/boutique/src n'existe pas."),
                 ('[ "$(owner $H/projets/boutique)" = etudiant ] && [ "$(owner $H/projets/boutique/src)" = etudiant ]', "Les dossiers boutique et src doivent vous appartenir : créez-les sans sudo."),
                 (r'''l=$(grep -v '^[[:space:]]*$' $H/doc-install.txt | head -n1); [[ $l =~ ^[[:space:]]*mkdir[[:space:]] ]]''', "La première ligne de ~/doc-install.txt n'est pas une commande mkdir (ou le fichier est absent)."),
                 (r'''l=$(grep -v '^[[:space:]]*$' $H/doc-install.txt | head -n1); [[ $l =~ [[:space:]]/home/etudiant/projets/boutique/src/?[[:space:]]*$ ]]''', "La commande ne se termine pas par le chemin absolu du dossier src (il commence par /home, sans ~)."),
                 (r'''l=$(grep -v '^[[:space:]]*$' $H/doc-install.txt | head -n1); [[ $l =~ [[:space:]](-[a-zA-Z]*p[a-zA-Z]*|--parents)([[:space:]]|$) ]]''', "Telle quelle, cette commande échouerait sur un poste où ~/projets/boutique n'existe pas encore."),
             ]},
            {"id": "2.2", "points": 3, "title": "Question piège",
             "ticket": {"from": "lea", "body": "Petit test, comme en entretien d'embauche 😉 : je t'ai laissé une question sur <code>ls</code> dans <code>~/question-man.txt</code>. Interdit de chercher sur Internet, la réponse est dans le manuel."},
             "desc": "L'option de <code>ls</code> demandée dans <code>~/question-man.txt</code> (ex. <code>-x</code>) dans <code>~/reponse-man.txt</code>.",
             "hints": ["Ouvrez le manuel de <code>ls</code> et utilisez sa recherche : <kbd>/</kbd> suivi d'un mot anglais de la question (<em>size</em>, <em>extension</em>, <em>version</em>, <em>sort</em>…), puis <kbd>n</kbd> pour l'occurrence suivante.",
                       "Chaque option est décrite en une ligne sous son nom. Attention à la casse : <code>-s</code> et <code>-S</code>, par exemple, ne font pas du tout la même chose."],
             "checks": [
                 ('a=$(ans $H/reponse-man.txt); [ -n "$LAB_OPT" ] && { [ "$a" = "-$LAB_OPT" ] || [ "$a" = "$LAB_OPT" ] || [ "$a" = "--sort=$LAB_TRI" ]; }', "Ce n'est pas l'option demandée dans ~/question-man.txt (ou ~/reponse-man.txt est absent)."),
             ]},
            {"id": "2.3", "points": 4, "title": "Le stagiaire est perdu",
             "ticket": {"from": "julien", "body": "Bonjour, désolé de déranger… Je suis dans <code>~/partage-marc/clients/2024/devis</code> et je dois ouvrir <code>tarifs.txt</code>, que Marc a rangé ailleurs dans <code>~/partage-marc</code>. Mais je ne sais pas quel chemin taper sans repartir de la racine. Tu peux m'aider ?"},
             "desc": "Le <strong>chemin relatif</strong> vers <code>tarifs.txt</code> (rangé quelque part dans <code>~/partage-marc</code>) depuis <code>devis</code>, dans <code>~/chemin-relatif.txt</code>. Testez-le avec <code>cd ~/partage-marc/clients/2024/devis &amp;&amp; cat &lt;votre chemin&gt;</code>.",
             "hints": ["Repérez d'abord où se trouve <code>tarifs.txt</code> (<code>ls -R ~/partage-marc</code>, ou <code>find</code> si vous le connaissez). Ensuite, chaque <code>..</code> remonte d'un dossier : comptez combien de niveaux il faut remonter depuis <code>devis</code>, puis redescendez si besoin.",
                       "Testez votre chemin avec <code>cat</code> depuis <code>devis</code> avant de l'écrire dans le fichier."],
             "checks": [
                 (r'''a=$(head -n1 $H/chemin-relatif.txt 2>/dev/null | tr -d '[:space:]'); [ -n "$a" ] && case $a in /*|"~"*) exit 1;; esac''', "Le chemin doit être relatif : il ne commence ni par / ni par ~ (ou le fichier est absent ou vide)."),
                 (r'''a=$(head -n1 $H/chemin-relatif.txt | tr -d '[:space:]'); cd $H/partage-marc/clients/2024/devis && [ -n "$LAB_TARIFS" ] && [ "$(readlink -f -- "$a")" = "$LAB_TARIFS" ]''', "Depuis le dossier devis, ce chemin ne mène pas à tarifs.txt."),
             ]},
            {"id": "2.4", "points": 3, "title": "Le script mystérieux de Marc",
             "ticket": {"from": "julien", "body": "Encore moi ! Un vieux script de Marc, <code>~/partage-marc/vieux-script.sh</code>, commence par un <code>cd</code> vers un chemin plein de <code>..</code>. Je n'y comprends rien : il désigne quel dossier, en vrai ?"},
             "desc": "Le <strong>chemin absolu</strong> (sans <code>~</code>) du dossier où mène le <code>cd</code> de <code>~/partage-marc/vieux-script.sh</code>, dans <code>~/chemin-absolu.txt</code>.",
             "hints": ["<code>..</code> désigne le dossier parent et <code>.</code> le dossier courant : lisez le chemin de gauche à droite, en remontant d'un cran à chaque <code>..</code>.",
                       "Ou laissez le shell faire le calcul : allez-y avec <code>cd</code> (le même chemin que dans le script), puis demandez-lui où vous êtes."],
             "checks": [
                 ('a=$(ans $H/chemin-absolu.txt); a=${a%/}; [ -n "$LAB_ABS" ] && [ "$a" = "$LAB_ABS" ]', "Ce n'est pas le chemin absolu du dossier où mène le cd du script (il doit commencer par /)."),
             ]},
            {"id": "2.5", "points": 5, "title": "« No manual entry »",
             "ticket": {"from": "julien", "body": "J'ai tapé <code>man</code> sur une commande et il me répond « No manual entry ». Cette commande n'a pas de doc ? J'ai noté ma question dans <code>~/question-shell.txt</code>."},
             "desc": "Dans <code>~/type-commande.txt</code>, la réponse du shell quand on lui demande ce qu'est la commande de la question ; dans <code>~/option-commande.txt</code>, l'option demandée (par exemple <code>-x</code>).",
             "hints": ["Toutes les commandes ne sont pas des programmes installés sur le disque : certaines font partie du shell lui-même et n'ont donc pas de page de manuel à leur nom. Cherchez dans <code>man bash</code> la section consacrée à ces commandes intégrées (<em>builtin</em>).",
                       "<code>type</code> suivi du nom de la commande dit ce qu'elle est ; <code>help</code> suivi du même nom affiche sa documentation."],
             "checks": [
                 ('grep -qi builtin $H/type-commande.txt && grep -qw -- "$LAB_BCMD" $H/type-commande.txt', "~/type-commande.txt ne contient pas la réponse du shell à la question « qu'est-ce que cette commande ? »."),
                 ('[ -n "$LAB_BOPT" ] && [ "$(ans $H/option-commande.txt)" = "$LAB_BOPT" ]', "~/option-commande.txt ne contient pas l'option demandée dans ~/question-shell.txt."),
             ]},
            {"id": "2.6", "points": 4, "title": "Le rapport le plus récent",
             "ticket": {"from": "sophie", "body": "Marc rendait ses rapports dans <code>/opt/rapports-marc</code>, mais ses noms de fichiers ne veulent rien dire : il y a même un « DEFINITIF » et un « final-v2 ». Je veux celui qu'il a modifié <strong>en dernier</strong>."},
             "desc": "Le nom du fichier de <code>/opt/rapports-marc</code> modifié le plus récemment, dans <code>~/dernier-rapport.txt</code>.",
             "hints": ["Ne vous fiez pas aux noms : la date de dernière modification est affichée par <code>ls -l</code>, et <code>ls</code> sait aussi trier sur ce critère (cherchez « time » dans son manuel).",
                       "Avec le bon tri, le plus récent s'affiche en premier."],
             "checks": [
                 ('a=$(ans $H/dernier-rapport.txt); [ -n "$a" ] && [ "$(basename "$a")" = "$LAB_RECENT" ]', "Ce n'est pas le rapport modifié le plus récemment (ou le fichier est absent)."),
             ]},
            {"id": "2.7", "points": 3, "title": "Le lot de clôture",
             "ticket": {"from": "diallo", "body": "Bonjour, Aminata Diallo, comptabilité. Le journal d'export comptable, <code>~/exports/journal-export.log</code>, fait 8 000 lignes. Il me faut le numéro de lot inscrit juste après la ligne <code>=== CLÔTURE ===</code>. Les clôtures partielles ne comptent pas."},
             "desc": "Le numéro du lot qui suit la ligne <code>=== CLÔTURE ===</code> (juste le nombre) dans <code>~/lot.txt</code>.",
             "hints": ["Ce fichier est trop long pour <code>cat</code>. Le cours cite un visionneur qui a exactement les mêmes touches que <code>man</code>, recherche comprise.",
                       "Ouvrez le fichier avec <code>less</code>, cherchez <code>=== CLÔTURE</code> avec <kbd>/</kbd>, et méfiez-vous des clôtures partielles."],
             "checks": [
                 ('[ "$(grep -oE "[0-9]+" $H/lot.txt | head -n1)" = "$LAB_LOT" ]', "Ce n'est pas le numéro du lot de la clôture (ou ~/lot.txt est absent)."),
             ]},
            {"id": "2.8", "points": 5, "title": "Vers le catalogue fournisseur",
             "ticket": {"from": "julien", "body": "Toujours dans <code>~/partage-marc/clients/2024/devis</code> ! Marc a noté dans <code>A-LIRE.txt</code> quel catalogue fournisseur utiliser pour ce devis. Il est dans une tout autre branche du partage… Tu me donnes le chemin relatif pour y aller d'ici ?"},
             "desc": "Le chemin <strong>relatif</strong>, depuis <code>~/partage-marc/clients/2024/devis</code>, du catalogue indiqué dans <code>A-LIRE.txt</code>, dans <code>~/chemin-fournisseur.txt</code>.",
             "hints": ["Remontez jusqu'au premier dossier commun aux deux chemins, puis redescendez vers la cible.",
                       "Depuis <code>devis</code>, remontez jusqu'à <code>partage-marc</code> (comptez les niveaux), puis descendez dans <code>fournisseurs</code>. Testez avec <code>cat</code> avant d'écrire la réponse."],
             "checks": [
                 (r'''a=$(head -n1 $H/chemin-fournisseur.txt 2>/dev/null | tr -d '[:space:]'); [ -n "$a" ] && case $a in /*|"~"*) exit 1;; esac''', "Le chemin doit être relatif : il ne commence ni par / ni par ~ (ou le fichier est absent ou vide)."),
                 (r'''a=$(head -n1 $H/chemin-fournisseur.txt | tr -d '[:space:]'); cd $H/partage-marc/clients/2024/devis && [ "$(readlink -f -- "$a")" = "$LAB_CIBLE" ]''', "Depuis le dossier devis, ce chemin ne mène pas au catalogue indiqué dans A-LIRE.txt."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Jour 3 — Ranger l'héritage de Marc",
        "description": "Écrire, copier, renommer, déplacer, supprimer sans casse. Compétences : > et >>, cp, mv, rm, jokers, accolades.",
        "lesson": """<h3>Écrire dans un fichier</h3><table class="lesson-table"><tr><th>Symbole</th><th>Effet</th><th>Exemple</th></tr><tr><td><code>&gt;</code></td><td><strong>Remplace</strong> le contenu</td><td><code>echo "Bonjour" &gt; f.txt</code></td></tr><tr><td><code>&gt;&gt;</code></td><td><strong>Ajoute</strong> à la fin</td><td><code>echo "Suite" &gt;&gt; f.txt</code></td></tr></table><p><code>cat fichier</code> affiche le contenu ; <code>wc -l fichier</code> compte ses lignes.</p><h3>Copier, déplacer, supprimer</h3><table class="lesson-table"><tr><th>Commande</th><th>Action</th><th>Note</th></tr><tr><td><code>cp src dest</code></td><td>Copier</td><td><code>-r</code> pour un dossier</td></tr><tr><td><code>mv src dest</code></td><td>Déplacer ou renommer</td><td>Pas de commande « rename » standard ici : renommer, c'est déplacer</td></tr><tr><td><code>rm fichier</code></td><td>Supprimer un fichier</td><td>Pas de corbeille !</td></tr><tr><td><code>rm -r dossier</code></td><td>Supprimer un dossier</td><td>Irréversible</td></tr></table><div class="tip"><code>cp</code> et <code>mv</code> <strong>écrasent la destination sans prévenir</strong> si elle existe déjà. <code>-i</code> demande confirmation, <code>-n</code> refuse d'écraser.</div><h3>Les jokers (globbing)</h3><p>C'est le shell qui remplace un motif par la liste des noms correspondants, avant de lancer la commande :</p><ul><li><code>*</code> — n'importe quelle suite de caractères : <code>ls *.jpg</code></li><li><code>?</code> — exactement un caractère : <code>ls photo?.jpg</code> (photo1.jpg, photoA.jpg, mais pas photo10.jpg)</li><li><code>[…]</code> — un caractère parmi une liste ou une plage : <code>ls scan-[a-c].pdf</code>, <code>ls img[0-9].png</code></li></ul><h3>Les accolades</h3><p>Le shell développe aussi une liste de variantes : <code>echo photo-{ete,hiver}.jpg</code> affiche <code>photo-ete.jpg photo-hiver.jpg</code>. Pratique pour créer plusieurs dossiers d'un coup.</p><div class="tip">Avant un <code>rm</code> ou un <code>mv</code> avec joker, testez le motif avec <code>ls</code> : il affiche exactement ce qui sera touché.</div>""",
        "setup": r'''
B=$H/bureau-marc
rm -rf $B; mkdir -p $B/vieux-projets/site-2019
for f in export brouillon sauvegarde cache; do echo "temporaire" > $B/$f.tmp; done
echo "Contrat de maintenance serveurs 2025-2027 - NE PAS SUPPRIMER" > $B/contrat-maintenance.txt
echo "<h1>Maquette 2019</h1>" > $B/vieux-projets/site-2019/index.html
# 3.9 : des .tmp cachés, et des fichiers à garder qui ressemblent à des .tmp
echo "temporaire" > "$B/.verrou-$((RANDOM % 900 + 100)).tmp"
echo "temporaire" > $B/.~session.tmp
echo "theme=sombre" > $B/.parametres
echo "Notes sur le ménage des fichiers temporaires" > $B/notes.tmp.txt
own $B
: > $REF/bureau-garder
for f in contrat-maintenance.txt .parametres notes.tmp.txt; do echo "$f $(stat -c %i $B/$f) $(md5sum < $B/$f | cut -c1-32)" >> $REF/bureau-garder; done
emit CONTRAT_INO "$(stat -c %i $B/contrat-maintenance.txt)"
emit CONTRAT_MD5 "$(md5sum < $B/contrat-maintenance.txt | cut -c1-32)"
# 3.6 : un brouillon à renommer, sans perdre l'ancien bilan
K=$H/bilans
rm -rf $K; mkdir -p $K
printf 'Bilan 2025 (version de Marc)\nTotal : %d €\n' $((RANDOM * 7)) > $K/bilan.txt
printf 'Bilan 2025 (version corrigée)\nTotal : %d €\n' $((RANDOM * 7 + 3)) > $K/brouillon-bilan.txt
own $K
emit MD5_ANCIEN "$(md5sum < $K/bilan.txt | cut -c1-32)"
emit MD5_NOUVEAU "$(md5sum < $K/brouillon-bilan.txt | cut -c1-32)"
# 3.7 : une boîte de réception à trier
F=$H/factures
rm -rf $F; mkdir -p $F/inbox $F/2024
mapfile -t nums < <(shuf -i 100-999 -n 30)
for k in "${!nums[@]}"; do
  case $((k % 5)) in 0|1) n=facture-2024-${nums[k]}.pdf;; 2) n=facture-2023-${nums[k]}.pdf;; 3) n=devis-2024-${nums[k]}.pdf;; 4) n=relance-facture-2024-${nums[k]}.pdf;; esac
  echo "$n" > $F/inbox/$n
done
own $F
ls $F/inbox | grep '^facture-2024-' | sort > $REF/factures-2024
ls $F/inbox | grep -v '^facture-2024-' | sort > $REF/factures-reste
# 3.8 : des rapports numérotés, et des noms voisins à garder
W=$H/rapports-hebdo
rm -rf $W; mkdir -p $W
N=$((RANDOM % 9 + 12))
for i in $(seq 1 $N); do echo "Rapport de la semaine $i" > $W/rapport$i.txt; done
echo "Synthèse de l'année" > $W/rapport-final.txt
echo "Annexe A" > $W/rapportA.txt
own $W
ls $W | grep -vE '^rapport[1-9]\.txt$' | sort > $REF/rapports-reste
''',
        "exercises": [
            {"id": "3.1", "points": 3, "title": "Classer la documentation",
             "ticket": {"from": "sophie", "body": "On va enfin avoir une vraie documentation. Dans tes documents, prépare un dossier pour les procédures et un autre pour les comptes rendus de réunion, et dans chacun un sous-dossier <code>archives</code> pour les vieilles versions."},
             "desc": "Les dossiers <code>~/documents/procedures/archives</code> et <code>~/documents/comptes-rendus/archives</code>, qui vous appartiennent.",
             "hints": ["Il faut créer des dossiers dont le dossier parent n'existe pas encore : l'option de <code>mkdir</code> découverte au jour 2 s'en charge.",
                       "<code>mkdir</code> accepte plusieurs chemins d'un coup, et les accolades du cours évitent de taper deux fois la même chose."],
             "checks": [
                 ('test -d $H/documents/procedures/archives && test -d $H/documents/comptes-rendus/archives', "Les dossiers procedures/archives et comptes-rendus/archives doivent exister dans ~/documents."),
                 ('[ -z "$(find $H/documents/procedures $H/documents/comptes-rendus -maxdepth 1 -type d ! -user etudiant)" ]', "Certains dossiers appartiennent à root : créez-les sans sudo."),
             ]},
            {"id": "3.2", "points": 3, "title": "Première procédure",
             "ticket": {"from": "sophie", "body": "Première procédure à rédiger : l'arrivée d'un nouveau salarié. Commence par le titre, je veux exactement celui-ci : « Procédure arrivée nouveau salarié »."},
             "desc": "La <strong>première ligne</strong> de <code>~/documents/procedures/arrivee.txt</code> est exactement <code>Procédure arrivée nouveau salarié</code>.",
             "hints": ["Le cours montre comment envoyer le texte d'<code>echo</code> dans un fichier.",
                       "Mettez le titre entre guillemets, accents compris, puis vérifiez avec <code>cat</code>."],
             "checks": [
                 ('test -f $H/documents/procedures/arrivee.txt', "Le fichier ~/documents/procedures/arrivee.txt n'existe pas."),
                 ('[ "$(head -n1 $H/documents/procedures/arrivee.txt)" = "Procédure arrivée nouveau salarié" ]', "La première ligne n'est pas exactement « Procédure arrivée nouveau salarié » (attention aux accents)."),
             ]},
            {"id": "3.3", "points": 3, "title": "Première étape",
             "ticket": {"from": "sophie", "body": "Ajoute la première étape sous le titre : « 1. Créer le compte utilisateur ». Et attention à ne pas écraser le titre, la dernière fois quelqu'un a perdu toute une procédure comme ça…"},
             "desc": "<code>arrivee.txt</code> contient exactement 2 lignes, la 2<sup>e</sup> étant <code>1. Créer le compte utilisateur</code>.",
             "hints": ["Des deux symboles de redirection, l'un remplace le contenu, l'autre ajoute à la fin : relisez le tableau du cours.",
                       "Si la ligne a été ajoutée deux fois, réécrivez le fichier : le titre avec un symbole, puis l'étape avec l'autre."],
             "checks": [
                 ('[ "$(sed -n 2p $H/documents/procedures/arrivee.txt)" = "1. Créer le compte utilisateur" ]', "La 2e ligne n'est pas « 1. Créer le compte utilisateur »."),
                 ('[ "$(wc -l < $H/documents/procedures/arrivee.txt)" -eq 2 ]', "Le fichier doit contenir exactement 2 lignes."),
             ]},
            {"id": "3.4", "points": 3, "title": "Copie pour relecture",
             "ticket": {"from": "sophie", "body": "Je relirai ta procédure ce soir. Dépose-m'en une copie dans les comptes rendus, sous le nom <code>arrivee-a-relire.txt</code>, et garde l'original là où il est."},
             "desc": "<code>~/documents/comptes-rendus/arrivee-a-relire.txt</code>, copie identique de <code>arrivee.txt</code> (qui reste en place).",
             "hints": ["La commande de copie accepte comme destination un chemin qui se termine par un nouveau nom.",
                       "Vérifiez avec <code>cat</code> que la copie contient bien les deux lignes."],
             "checks": [
                 ('test -f $H/documents/procedures/arrivee.txt', "L'original ~/documents/procedures/arrivee.txt a disparu : il fallait copier, pas déplacer."),
                 ('cmp -s $H/documents/procedures/arrivee.txt $H/documents/comptes-rendus/arrivee-a-relire.txt', "La copie est absente ou différente de l'original (refaites-la après l'ajout de la 2e ligne)."),
             ]},
            {"id": "3.5", "points": 4, "title": "Le bureau de Marc",
             "ticket": {"from": "sophie", "body": "Le dossier <code>~/bureau-marc</code> est un vrai bazar. Supprime tous les fichiers temporaires <code>.tmp</code> et le dossier <code>vieux-projets</code>. Par contre, <strong>surtout</strong> ne touche pas au contrat de maintenance, c'est le seul exemplaire !"},
             "desc": "Plus aucun fichier <code>.tmp</code> visible ni de <code>vieux-projets</code> dans <code>~/bureau-marc</code> ; <code>contrat-maintenance.txt</code> intact (le fichier d'origine, pas une copie).",
             "hints": ["Testez d'abord votre motif avec <code>ls</code> : il doit lister les <code>.tmp</code> et seulement eux.",
                       "<code>rm</code> refuse de supprimer un dossier non vide sans une option : relisez le tableau du cours."],
             "checks": [
                 ('[ "$(stat -c %i $H/bureau-marc/contrat-maintenance.txt 2>/dev/null)" = "$LAB_CONTRAT_INO" ] && [ "$(md5sum < $H/bureau-marc/contrat-maintenance.txt | cut -c1-32)" = "$LAB_CONTRAT_MD5" ]', "Le contrat de maintenance a été supprimé, modifié ou recréé : ce n'est plus l'exemplaire d'origine ! (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)"),
                 ('! ls $H/bureau-marc/*.tmp', "Il reste des fichiers .tmp dans ~/bureau-marc."),
                 ('test ! -e $H/bureau-marc/vieux-projets', "Le dossier ~/bureau-marc/vieux-projets existe toujours."),
             ]},
            {"id": "3.6", "points": 4, "title": "Renommer sans écraser",
             "ticket": {"from": "diallo", "body": "Dans <code>~/bilans</code>, le fichier <code>brouillon-bilan.txt</code> est la version corrigée : il doit devenir <code>bilan.txt</code>. Mais attention, un <code>bilan.txt</code> existe déjà (la version de Marc) et je veux la garder, sous le nom <code>bilan-ancien.txt</code>."},
             "desc": "Dans <code>~/bilans</code> : <code>bilan.txt</code> a le contenu de l'actuel <code>brouillon-bilan.txt</code>, l'ancien <code>bilan.txt</code> est conservé sous le nom <code>bilan-ancien.txt</code>, et <code>brouillon-bilan.txt</code> n'existe plus.",
             "hints": ["<code>mv</code> écrase la destination sans rien demander : l'ordre des opérations compte.",
                       "Mettez d'abord l'ancien de côté sous son nouveau nom, puis renommez le brouillon. L'option <code>-n</code> de <code>mv</code> refuse d'écraser un fichier existant : un bon filet de sécurité."],
             "checks": [
                 ('[ "$(md5sum < $H/bilans/bilan-ancien.txt | cut -c1-32)" = "$LAB_MD5_ANCIEN" ]', "~/bilans/bilan-ancien.txt n'existe pas ou ne contient pas le bilan de Marc. S'il a été écrasé, « Réinitialiser les fichiers de cette étape » remet les bilans en place."),
                 ('[ "$(md5sum < $H/bilans/bilan.txt | cut -c1-32)" = "$LAB_MD5_NOUVEAU" ]', "~/bilans/bilan.txt ne contient pas la version corrigée."),
                 ('test ! -e $H/bilans/brouillon-bilan.txt', "brouillon-bilan.txt existe toujours : il devait être renommé."),
             ]},
            {"id": "3.7", "points": 4, "title": "Classer les factures",
             "ticket": {"from": "diallo", "body": "Ma boîte <code>~/factures/inbox</code> déborde. Range toutes les <strong>factures 2024</strong> dans <code>~/factures/2024</code>. Laisse dans l'inbox tout le reste : les devis, les factures 2023 et les relances, je les traiterai à part."},
             "desc": "Tous les fichiers dont le nom commence par <code>facture-2024-</code> sont dans <code>~/factures/2024</code> ; tous les autres sont restés dans <code>~/factures/inbox</code>.",
             "hints": ["Un seul motif avec joker peut désigner toutes les factures d'une année : testez-le d'abord avec <code>ls</code>, et regardez bien ce qu'il attrape.",
                       "Le motif doit coller au <strong>début</strong> du nom : une étoile placée devant attraperait aussi les relances."],
             "checks": [
                 ('diff <(ls $H/factures/2024 | sort) $REF/factures-2024', "~/factures/2024 ne contient pas exactement les factures 2024 (il en manque, ou il y a des fichiers en trop)."),
                 ('diff <(ls $H/factures/inbox | sort) $REF/factures-reste', "~/factures/inbox ne contient plus exactement les autres documents (devis, factures 2023, relances)."),
             ]},
            {"id": "3.8", "points": 4, "title": "Les rapports numérotés",
             "ticket": {"from": "julien", "body": "Léa m'a demandé de supprimer les rapports hebdomadaires 1 à 9 de <code>~/rapports-hebdo</code> (<code>rapport1.txt</code> à <code>rapport9.txt</code>), mais de garder les suivants, la synthèse et l'annexe. Avec <code>rapport*.txt</code>, j'allais tout effacer… Tu peux le faire ?"},
             "desc": "Dans <code>~/rapports-hebdo</code>, <code>rapport1.txt</code> à <code>rapport9.txt</code> sont supprimés ; tous les autres fichiers sont toujours là.",
             "hints": ["<code>*</code> en prend trop. Le cours cite un joker qui vaut exactement un caractère… mais il accepte aussi une lettre.",
                       "Un crochet désigne un caractère parmi une plage, comme <code>[a-f]</code>. Testez avec <code>ls</code> avant <code>rm</code>."],
             "checks": [
                 ('diff <(ls $H/rapports-hebdo | sort) $REF/rapports-reste', "Le contenu de ~/rapports-hebdo n'est pas celui attendu : il reste des rapports 1 à 9, ou d'autres fichiers ont disparu (« Réinitialiser les fichiers de cette étape » pour recommencer)."),
             ]},
            {"id": "3.9", "points": 5, "title": "Des .tmp invisibles",
             "ticket": {"from": "sophie", "body": "L'outil de sauvegarde se plaint encore de fichiers <code>.tmp</code> dans <code>~/bureau-marc</code>. Tu m'avais dit que c'était fait ! Tous les <code>.tmp</code> doivent disparaître, sans exception, mais rien d'autre."},
             "desc": "Plus aucun fichier dont le nom se termine par <code>.tmp</code> dans <code>~/bureau-marc</code>, <strong>y compris les fichiers cachés</strong> ; les autres fichiers sont intacts.",
             "hints": ["<code>*</code> ne correspond jamais à un nom qui commence par un point : regardez ce qui reste avec <code>ls -a</code>.",
                       "Un motif qui commence lui-même par un point attrape les noms cachés. Testez-le avec <code>ls</code> avant <code>rm</code> : <code>notes.tmp.txt</code> et <code>.parametres</code> doivent rester."],
             "checks": [
                 ('[ -z "$(find $H/bureau-marc -maxdepth 1 -name \'*.tmp\')" ]', "L'outil de sauvegarde voit encore des fichiers .tmp dans ~/bureau-marc."),
                 ('while read -r n i m; do [ "$(stat -c %i "$H/bureau-marc/$n" 2>/dev/null)" = "$i" ] && [ "$(md5sum < "$H/bureau-marc/$n" | cut -c1-32)" = "$m" ] || exit 1; done < $REF/bureau-garder', "Un fichier qui n'était pas un .tmp a été supprimé ou modifié : seuls les .tmp devaient partir (« Réinitialiser les fichiers de cette étape » pour recommencer)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Jour 4 — Sauvegardes et raccourcis",
        "description": "Comprendre ce qu'est vraiment un fichier. Compétences : inodes, liens durs, liens symboliques relatifs et absolus, liens cassés, chaînes de liens.",
        "lesson": """<h3>Le concept d'inode</h3><p>Chaque fichier est décrit par un <strong>inode</strong> (numéro unique sur le système de fichiers). Un nom de fichier n'est qu'une étiquette qui pointe vers un inode.</p><pre>ls -i photo.jpg     # numéro d'inode<br>ls -l photo.jpg     # 2e colonne = nombre de liens durs</pre><h3>Lien dur</h3><pre>ln photo.jpg photo-bis.jpg</pre><ul><li>Seconde étiquette vers le <strong>même inode</strong> : aucune n'est « l'original »</li><li>Impossible vers un dossier ou une autre partition</li><li>Les données disparaissent quand le <em>dernier</em> nom est supprimé</li><li>Une <strong>copie</strong> (<code>cp</code>), elle, a son propre inode : modifier l'une ne change pas l'autre</li></ul><h3>Lien symbolique</h3><pre>ln -s /var/log ~/journaux</pre><ul><li>Petit fichier spécial qui contient un <strong>chemin</strong>, tel qu'on l'a écrit</li><li>Peut pointer vers un dossier, traverser les partitions</li><li><strong>Cassé</strong> si la cible disparaît</li><li>Un chemin <strong>relatif</strong> dans un lien est interprété à partir du dossier où se trouve le lien, pas du dossier où l'on était en le créant</li></ul><pre>lrwxrwxrwx 1 etudiant etudiant 8 journaux -&gt; /var/log</pre><h3>Outils</h3><ul><li><code>readlink lien</code> — affiche le chemin contenu dans le lien</li><li><code>find . -xtype l</code> — trouve les liens symboliques cassés</li><li><code>ln -sf nouvelle-cible lien</code> — <code>-f</code> remplace un lien qui existe déjà. Si ce lien pointe vers un <strong>dossier</strong>, lisez l'option <code>-n</code> dans <code>man ln</code> : sans elle, <code>ln</code> crée le nouveau lien <em>dans</em> le dossier.</li></ul>""",
        "setup": r'''
# 4.1 : la grille officielle existe déjà
rm -f $H/tarifs-2025.csv
printf 'produit;prix\n' > $H/tarifs-2025.csv
for p in gourde piolet lampe-frontale boussole bivouac; do echo "$p;$((RANDOM % 90 + 10)).$((RANDOM % 90 + 10))" >> $H/tarifs-2025.csv; done
chown etudiant:etudiant $H/tarifs-2025.csv
emit TARIFS_MD5 "$(md5sum < $H/tarifs-2025.csv | cut -c1-32)"
# 4.2 : liens durs et copies mélangés
S=/opt/sauvegardes
rm -rf $S; mkdir -p $S/lundi $S/mardi/exports $S/mercredi $S/jeudi
head -c 2048 /dev/urandom > $S/base-clients.db
dirs=(lundi mardi/exports mercredi jeudi)
n=$((RANDOM % 3 + 2))
for i in $(seq 1 $n); do ln $S/base-clients.db $S/${dirs[RANDOM % 4]}/export-$i.db; done
for i in $(seq $((n + 1)) $((n + 2))); do cp $S/base-clients.db $S/${dirs[RANDOM % 4]}/export-$i.db; done
cp $S/base-clients.db $S/mercredi/base-clients-copie.db
chmod -R a+rX $S
# 4.4 et 4.5 : un raccourci cassé parmi d'autres
R=$H/raccourcis-marc
rm -rf $R; mkdir -p $R; cd $R
touch procedures.txt annuaire.txt planning.txt
targets=(procedures.txt annuaire.txt planning.txt)
names=(compta rh ventes direction)
broken=${names[RANDOM % 4]}
for nm in "${names[@]}"; do
  if [ "$nm" = "$broken" ]; then ln -s /mnt/ancien-nas/$nm "$nm"; else ln -s "${targets[RANDOM % 3]}" "$nm"; fi
done
cd /
chown -hR etudiant:etudiant $R
emit BROKEN "$broken"
# 4.6 : un lien absolu qui cassera au déménagement
V=$H/site-v1
rm -rf $V; mkdir -p $V/releases
nr=$((RANDOM % 3 + 3)); act=r$((RANDOM % nr + 1))
for i in $(seq 1 $nr); do mkdir -p $V/releases/r$i; echo "<h1>Release $i</h1>" > $V/releases/r$i/index.html; done
ln -s $V/releases/$act $V/current
chown -hR etudiant:etudiant $V
emit REL "$act"
# 4.7 : la bascule ratée de Julien (ln -sf sur un lien vers un dossier) ; releases tirées au sort
v=${LAB_VARIANTE_4_7:-$((RANDOM % 4))}
anc=(r2 r3 r4 r1); nouv=(r3 r4 r1 r2)
D=$H/deploi
rm -rf $D; mkdir -p $D/releases/r1 $D/releases/r2 $D/releases/r3 $D/releases/r4
for i in 1 2 3 4; do echo "version $i" > $D/releases/r$i/VERSION; done
printf 'Release à mettre en production : %s\n' "${nouv[v]}" > $D/A-DEPLOYER
cd $D; ln -s releases/${anc[v]} current; ln -sf releases/${nouv[v]} current; cd /
chown -hR etudiant:etudiant $D
emit DEPLOI "${nouv[v]}"
# 4.8 : un fichier supprimé, mais un lien dur de secours caché quelque part
G=$H/grilles; C=$H/.cache/sauvegardes-auto
rm -rf $G $C; mkdir -p $G
printf 'tranche;taux\n' > $G/grille.csv
for t in A B C D E; do echo "$t;$((RANDOM % 30 + 5))" >> $G/grille.csv; done
d1=$C/$(rword); d2=$C/$(rword); mkdir -p $d1 $d2
ln $G/grille.csv $d1/$(rword).bak
cp $G/grille.csv $d2/grille.csv.bak
ino=$(stat -c %i $G/grille.csv)
rm $G/grille.csv
echo "grille.csv : inode $ino (noté par Marc le 2 septembre, au cas où)" > $G/LISEZ-MOI
chown -R etudiant:etudiant $H/.cache $G
emit INODE "$ino"
# 4.9 : une chaîne de raccourcis
Q=/srv/partages-anciens
rm -rf $Q
for d in compta rh direction; do mkdir -p $Q/$d; for f in budget planning inventaire; do echo "$d : $f" > $Q/$d/$f.ods; done; done
fin=$Q/$(shuf -n1 -e compta rh direction)/$(shuf -n1 -e budget planning inventaire).ods
chmod -R a+rX $Q
K=$H/raccourcis
rm -rf $K; mkdir -p $K/.relais
ln -s "$fin" $K/.relais/niveau3
ln -s .relais/niveau3 $K/niveau2
ln -s niveau2 $K/dernier
ln -s $Q/compta $K/compta
chown -hR etudiant:etudiant $K
emit FINAL "$fin"
''',
        "exercises": [
            {"id": "4.1", "points": 3, "title": "Une grille, deux noms",
             "ticket": {"from": "diallo", "body": "Mon tableur ouvre toujours <code>tarifs-courant.csv</code>, mais le fichier officiel, c'est <code>~/tarifs-2025.csv</code>. Je ne veux pas de copie : la dernière fois, les deux versions avaient divergé et on a facturé les mauvais prix. Les deux noms doivent désigner <strong>le même fichier</strong>."},
             "desc": "Un <strong>lien dur</strong> <code>~/tarifs-courant.csv</code> vers <code>~/tarifs-2025.csv</code>, dont le contenu ne change pas.",
             "hints": ["Relisez la différence entre lien dur et lien symbolique : Aminata veut deux noms pour le même inode, pas un raccourci.",
                       "<code>ln</code> prend d'abord le fichier existant, puis le nouveau nom ; vérifiez avec <code>ls -li</code> que les deux noms ont le même numéro d'inode."],
             "checks": [
                 ('[ "$(md5sum < $H/tarifs-2025.csv | cut -c1-32)" = "$LAB_TARIFS_MD5" ]', "~/tarifs-2025.csv a disparu ou a été modifié : c'est le fichier officiel, il ne fallait pas y toucher (« Réinitialiser les fichiers de cette étape » le remet en place)."),
                 ('test ! -L $H/tarifs-courant.csv && [ "$(stat -c %i $H/tarifs-2025.csv)" = "$(stat -c %i $H/tarifs-courant.csv 2>/dev/null)" ]', "~/tarifs-courant.csv n'est pas un lien dur vers tarifs-2025.csv (inodes différents, lien symbolique, ou fichier absent)."),
             ]},
            {"id": "4.2", "points": 4, "title": "Combien de sauvegardes, vraiment ?",
             "ticket": {"from": "lea", "body": "Le script de sauvegarde de Marc crée des exports de <code>/opt/sauvegardes/base-clients.db</code> un peu partout. Je le soupçonne de faire parfois des liens durs au lieu de vraies copies : si c'est le cas, on croit avoir plusieurs sauvegardes mais on n'en a qu'une ! Donne-moi tous les noms qui désignent en réalité le même fichier que <code>base-clients.db</code>."},
             "desc": "Dans <code>~/liens-base.txt</code>, un par ligne, les <strong>chemins complets</strong> de tous les noms qui désignent le même inode que <code>/opt/sauvegardes/base-clients.db</code>, lui compris. Une copie n'est pas un lien, même si son nom ressemble aux autres.",
             "hints": ["Un lien dur a le même numéro d'inode que l'original ; une copie en a un autre. <code>ls -li</code> sur chaque dossier permet de comparer.",
                       "<code>find</code> sait retrouver tous les noms d'un même fichier : cherchez « same » dans son manuel."],
             "checks": [
                 ('test -s $H/liens-base.txt', "~/liens-base.txt est absent ou vide."),
                 ('setcmp $H/liens-base.txt "find /opt/sauvegardes -samefile /opt/sauvegardes/base-clients.db"', "La liste ne correspond pas : il manque des noms, des copies s'y sont glissées, ou les chemins ne sont pas complets (ils commencent par /opt)."),
             ]},
            {"id": "4.3", "points": 3, "title": "Raccourci vers la configuration",
             "ticket": {"from": "thomas", "body": "Je passe mon temps dans <code>/etc</code>. Tu peux me faire un raccourci <code>conf-systeme</code> dans ton dossier personnel, pour que je le montre aux autres devs ?"},
             "desc": "Un lien symbolique <code>~/conf-systeme</code> pointant vers <code>/etc</code>.",
             "hints": ["Thomas veut un raccourci vers un <strong>dossier</strong> : un seul des deux types de liens le permet.",
                       "Avec l'option du lien symbolique, <code>ln</code> prend d'abord la cible, puis le nom du lien."],
             "checks": [
                 ('test -L $H/conf-systeme', "~/conf-systeme n'existe pas ou n'est pas un lien symbolique."),
                 ('[ "$(readlink -f $H/conf-systeme)" = /etc ]', "~/conf-systeme ne pointe pas vers /etc."),
             ]},
            {"id": "4.4", "points": 3, "title": "Le raccourci qui ne mène nulle part",
             "ticket": {"from": "julien", "body": "Dans <code>~/raccourcis-marc</code>, il y a un raccourci par service. L'un d'eux me donne « No such file or directory ». Je crois qu'il pointe vers l'ancien NAS, qui a été débranché. Lequel c'est ?"},
             "desc": "Le nom du lien cassé (et lui seul) dans <code>~/lien-casse.txt</code>.",
             "hints": ["Le format détaillé de <code>ls</code> affiche la cible de chaque lien : laquelle n'existe plus ?",
                       "Le cours donne une commande <code>find</code> qui ne liste que les liens cassés."],
             "checks": [
                 ('[ "$(grep -c "[^[:space:]]" $H/lien-casse.txt)" -eq 1 ]', "~/lien-casse.txt doit contenir une seule ligne : le nom du lien cassé."),
                 ('[ "$(basename "$(ans $H/lien-casse.txt)")" = "$LAB_BROKEN" ]', "Ce n'est pas le lien cassé."),
             ]},
            {"id": "4.5", "points": 3, "title": "Réparer le raccourci",
             "ticket": {"from": "julien", "body": "Merci ! Sophie dit qu'en attendant le nouveau NAS, ce service doit simplement pointer vers l'annuaire. Tu peux réparer le raccourci, en gardant son nom ?"},
             "desc": "Le lien cassé garde son nom et pointe vers <code>annuaire.txt</code> (dans le même dossier).",
             "hints": ["<code>ln</code> refuse de créer un lien si le nom existe déjà, sauf avec l'option qui force le remplacement.",
                       "Le lien est dans <code>~/raccourcis-marc</code>, comme <code>annuaire.txt</code> : une cible relative suffit, puisqu'elle est interprétée depuis le dossier du lien."],
             "checks": [
                 ('test -L "$H/raccourcis-marc/$LAB_BROKEN"', "Le lien a disparu ou n'est plus un lien symbolique."),
                 ('[ "$(readlink -f "$H/raccourcis-marc/$LAB_BROKEN")" = "$H/raccourcis-marc/annuaire.txt" ]', "Le lien ne pointe pas vers annuaire.txt."),
             ]},
            {"id": "4.6", "points": 5, "title": "Le lien qui cassera au déménagement",
             "ticket": {"from": "thomas", "body": "Le site va déménager de <code>~/site-v1</code> vers <code>/srv/site</code> la semaine prochaine. Léa dit que le lien <code>current</code>, qui désigne la release en production, cassera au déménagement. Tu peux le réparer <strong>avant</strong>, sans changer de release ?"},
             "desc": "<code>~/site-v1/current</code> est un lien symbolique qui désigne toujours la même release, et qui la désignera encore si le dossier <code>site-v1</code> est déplacé ou renommé.",
             "hints": ["Un lien symbolique ne contient qu'un texte : s'il commence par <code>/</code>, il désigne toujours le même endroit, où que le lien soit déplacé. Regardez ce qu'il contient avec <code>readlink</code>.",
                       "Recréez le lien avec un chemin relatif au dossier du lien : depuis <code>~/site-v1</code>, la release est dans <code>releases/</code>."],
             "checks": [
                 ('test -L $H/site-v1/current && [ "$(readlink -f $H/site-v1/current)" = "$H/site-v1/releases/$LAB_REL" ]', "~/site-v1/current n'est plus un lien symbolique vers la release en production."),
                 ('t=$(mktemp -d); cp -a $H/site-v1 $t/; [ "$(readlink -f $t/site-v1/current)" = "$t/site-v1/releases/$LAB_REL" ]; r=$?; rm -rf $t; exit $r', "Si le dossier site-v1 est déplacé, current ne mène plus à la release en production."),
             ]},
            {"id": "4.7", "points": 5, "title": "À quoi sert -n ?",
             "ticket": {"from": "lea", "body": "Julien a voulu basculer <code>~/deploi/current</code> sur la release notée dans <code>~/deploi/A-DEPLOYER</code>, avec <code>ln -sf releases/… current</code>. Résultat : <code>current</code> pointe toujours vers l'ancienne release, et un lien bizarre est apparu <strong>dans</strong> celle-ci. Bascule proprement et fais le ménage."},
             "desc": "<code>~/deploi/current</code> est un lien symbolique vers la release notée dans <code>~/deploi/A-DEPLOYER</code>, et aucun lien parasite ne traîne dans <code>~/deploi/releases</code>.",
             "hints": ["Quand le nom de destination est un lien vers un <strong>dossier</strong>, <code>ln</code> le traite comme ce dossier et crée le nouveau lien à l'intérieur. Une option de <code>ln</code> lui demande de traiter ce lien comme un simple fichier : cherchez-la dans <code>man ln</code>.",
                       "Ajoutez <code>-n</code> à <code>-sf</code> pour remplacer le lien lui-même, puis cherchez le lien parasite (<code>find ~/deploi/releases -type l</code>) et supprimez-le avec <code>rm</code> (sans <code>-r</code> : c'est un lien, pas un dossier)."],
             "checks": [
                 ('[ -n "$LAB_DEPLOI" ] && test -L $H/deploi/current && [ "$(readlink -f $H/deploi/current)" = "$H/deploi/releases/$LAB_DEPLOI" ]', "~/deploi/current ne pointe pas vers la release notée dans ~/deploi/A-DEPLOYER."),
                 ('[ -z "$(find $H/deploi/releases -type l)" ]', "Il reste un lien parasite dans ~/deploi/releases."),
                 ('for r in r1 r2 r3 r4; do test -d $H/deploi/releases/$r && test ! -L $H/deploi/releases/$r || exit 1; done', "Une des releases a disparu : seul le lien parasite devait partir."),
             ]},
            {"id": "4.8", "points": 5, "title": "Le fichier supprimé qui existe encore",
             "ticket": {"from": "diallo", "body": "J'ai supprimé <code>~/grilles/grille.csv</code> par erreur ! Léa dit que Marc faisait toujours un lien dur de secours, caché quelque part dans ton dossier personnel, et il avait noté le numéro d'inode dans <code>~/grilles/LISEZ-MOI</code>. Remets <code>grille.csv</code> en place, et surtout pas avec une copie : je veux le fichier d'origine."},
             "desc": "<code>~/grilles/grille.csv</code> existe de nouveau et désigne l'inode noté dans <code>LISEZ-MOI</code>.",
             "hints": ["Tant qu'un nom pointe vers un inode, ses données existent. <code>find</code> sait chercher un fichier par numéro d'inode (cherchez « inum » dans son manuel), y compris dans les dossiers cachés.",
                       "Une fois le nom de secours trouvé, créez un lien dur de ce fichier vers <code>~/grilles/grille.csv</code>. Méfiez-vous d'une copie au nom plus parlant : elle n'a pas le bon inode."],
             "checks": [
                 ('test ! -L $H/grilles/grille.csv && [ "$(stat -c %i $H/grilles/grille.csv 2>/dev/null)" = "$LAB_INODE" ]', "~/grilles/grille.csv n'existe pas, ou ce n'est pas l'inode d'origine (une copie ou un lien symbolique ne comptent pas)."),
             ]},
            {"id": "4.9", "points": 4, "title": "Chaîne de raccourcis",
             "ticket": {"from": "julien", "body": "Dans <code>~/raccourcis</code>, le raccourci <code>dernier</code> pointe vers un raccourci… qui pointe vers un autre raccourci. Je tourne en rond ! C'est quoi, le <strong>vrai</strong> fichier au bout ?"},
             "desc": "Le chemin absolu du vrai fichier au bout de la chaîne qui commence à <code>~/raccourcis/dernier</code>, dans <code>~/fichier-final.txt</code>.",
             "hints": ["<code>readlink</code> sans option n'affiche que la cible <em>immédiate</em> d'un lien, qui peut elle-même être un lien (parfois caché).",
                       "<code>readlink</code> a une option qui suit toute la chaîne jusqu'au bout (cherchez « canonicalize »), et la commande <code>realpath</code> fait de même."],
             "checks": [
                 ('a=$(ans $H/fichier-final.txt); [ "${a%/}" = "$LAB_FINAL" ]', "Ce n'est pas le chemin absolu du fichier au bout de la chaîne (ou ~/fichier-final.txt est absent)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Jour 5 — Enquête dans les archives",
        "description": "Retrouver une information parmi des centaines de fichiers. Compétences : find (nom, type, chemin, taille, date), grep (récursif, casse, mots, contexte), wc.",
        "lesson": """<h3>Chercher des fichiers : find</h3><pre>find &lt;où&gt; &lt;critères&gt;</pre><ul><li><code>find /var -name "*.log"</code> — par nom, jokers entre guillemets (<code>-iname</code> : sans tenir compte de la casse)</li><li><code>find /usr/share -type d</code> — dossiers uniquement (<code>-type f</code> : fichiers ordinaires, <code>-type l</code> : liens symboliques)</li><li><code>find /home -size +100k</code> — plus de 100 Kio ; unités : <code>c</code> (octets), <code>k</code>, <code>M</code>, <code>G</code></li><li><code>find /tmp -mtime -7</code> — modifiés il y a moins de 7 jours</li></ul><p>Plusieurs critères à la suite doivent être <strong>tous</strong> vrais : <code>find /var -type f -name "*.gz"</code>. Le manuel (<code>man find</code>) en décrit des dizaines d'autres.</p><h3>Chercher du contenu : grep</h3><ul><li><code>grep "root" /etc/passwd</code> — lignes qui contiennent « root »</li><li><code>grep -r "TODO" ~/projets</code> — récursif ; <code>-l</code> : n'affiche que les noms de fichiers</li><li><code>grep -i</code> — insensible à la casse ; <code>-c</code> — compte les lignes ; <code>-n</code> — numéros de ligne</li></ul><h3>Compter : wc</h3><p><code>wc -l</code> lignes · <code>wc -w</code> mots · <code>wc -c</code> octets. En avant-première du jour 6 : <code>commande | wc -l</code> compte les lignes affichées par une commande.</p><div class="tip">Les erreurs « Permission denied » polluent l'affichage ? Ajoutez <code>2&gt;/dev/null</code> à la fin de la commande (explications au jour 6).</div>""",
        "setup": r'''
A=/srv/archives
rm -rf $A; mkdir -p $A
depts=(compta rh info ventes direction)
for d in "${depts[@]}"; do for y in 2022 2023 2024; do mkdir -p $A/$d/$y; done; done
for i in $(seq 1 180); do
  d=${depts[RANDOM % 5]}; y=$((2022 + RANDOM % 3))
  case $((RANDOM % 4)) in 0) ext=log;; 1) ext=txt;; 2) ext=csv;; 3) ext=conf;; esac
  echo "Document $i du service $d" > $A/$d/$y/fichier-$i.$ext
done
# 5.3 : des journaux qui parlent de 2023 sans être rangés dans 2023
for d in compta info ventes; do echo "Bilan de l'année précédente" > $A/$d/2024/bilan-2023.log; done
bon=$A/${depts[RANDOM % 5]}/$((2022 + RANDOM % 3))/reclamation-$RANDOM.txt
echo "Réclamation client - geste commercial accordé" > $bon; echo "BON-$(rword)" >> $bon
emit BON_FILE "$bon"
big=$A/${depts[RANDOM % 5]}/2023/sauvegarde-$RANDOM.dat
head -c 6M /dev/zero > $big
emit BIG "$big"
words=(Erreur ERREUR erreur info ok succès avertissement)
for i in $(seq 1 60); do echo "facture $i : ${words[RANDOM % 7]} lors du traitement"; done > $A/rapport.txt
emit NERR "$(grep -ci erreur $A/rapport.txt)"
emit NLOG2023 "$(find $A -path '*/2023/*' -name '*.log' | wc -l)"
# 5.7 : le mot « erreur », pas les mots qui le contiennent
tpl=("erreur de TVA" "ERREUR de saisie" "Erreur, montant négatif" "3 erreurs corrigées" "la terreur des comptables" "traitement OK" "montant erroné" "Erreurs multiples")
{ for i in $(seq 1 60); do echo "facture $((i + 100)) : ${tpl[RANDOM % 8]}"; done
  echo "facture 997 : erreur d'arrondi"; echo "facture 998 : 2 erreurs de TVA"; echo "facture 999 : la terreur du service client"; } > $A/rapport2.txt
emit NMOT "$(grep -ciw erreur $A/rapport2.txt)"
# 5.6 : tout est ancien, sauf quelques fichiers modifiés après la dernière sauvegarde
find $A -type f | while read -r f; do touch -d "-$((RANDOM % 300 + 10)) days" "$f"; done
touch -d "-3 days" $A/.derniere-sauvegarde
find $A -type f ! -name 'reclamation-*' ! -name 'sauvegarde-*' ! -name '.derniere-sauvegarde' ! -name 'rapport*.txt' | shuf -n $((RANDOM % 4 + 3)) > $REF/archives-modifiees
while read -r f; do touch -d "-$((RANDOM % 48 + 1)) hours" "$f"; done < $REF/archives-modifiees
chmod -R a+rX $A
# 5.1 : un dossier dont le nom se termine par .conf
E=/etc/cimes-sentiers
rm -rf $E; mkdir -p $E/anciens.conf
echo "port=8443" > $E/boutique.conf
echo "passerelle=banque-populaire" > $E/paiement.conf
echo "Archives des anciennes configurations" > $E/anciens.conf/LISEZMOI.txt
# des modules ajoutés au fil du temps, et un raccourci en .conf (variante tirée au sort)
v=${LAB_VARIANTE_5_1:-$((RANDOM % 4))}
mods=(stock livraison fidelite newsletter)
for i in $(seq 0 $v); do echo "actif=oui" > $E/module-${mods[i]}.conf; done
if [ $((v % 2)) = 0 ]; then ln -s boutique.conf $E/actif.conf; else mkdir -p $E/modeles.conf; fi
chmod -R a+rX $E
# 5.8 : des médias de toutes les tailles, autour de 1 Mio
M=/srv/medias
rm -rf $M; mkdir -p $M/photos $M/sons
sizes=(0 120 480 900 1000 1023 1024 1500 3072)
mapfile -t ord < <(shuf -e affiche logo jingle bandeau miniature fond intro catalogue teaser)
: > $REF/petits-medias
for i in "${!sizes[@]}"; do
  if [ $((i % 2)) -eq 0 ]; then sub=photos; else sub=sons; fi
  f=$M/$sub/${ord[i]}.bin
  head -c ${sizes[i]}K /dev/zero > $f
  if [ ${sizes[i]} -lt 1024 ]; then echo "$f" >> $REF/petits-medias; fi
done
chmod -R a+rX $M
# 5.9 : une erreur fatale, et sa cause juste avant
L=$H/logs-app
rm -rf $L; mkdir -p $L
n=$((RANDOM % 2000 + 800))
cause="ERROR connexion à la base refusée (pool $(rword))"
awk -v n=$n -v cause="$cause" -v seed=$RANDOM 'BEGIN { srand(seed); split("INFO INFO INFO DEBUG WARN", lv, " ")
  for (i = 1; i <= 3000; i++) {
    t = sprintf("2026-03-12 %02d:%02d:%02d", int((i - 1) / 126), int(i / 3) % 60, i % 60)
    if (i == n - 1) print t, cause
    else if (i == n) print t, "FATAL arrêt du service boutique"
    else if (i % 97 == 0) print t, "WARN avertissement : erreur non fatale ignorée"
    else print t, lv[int(rand() * 5) + 1], "requête traitée en " int(rand() * 900 + 10) " ms"
  } }' > $L/app.log
own $L
sed -n "$((n - 1))p" $L/app.log > $REF/cause-fatale
''',
        "exercises": [
            {"id": "5.1", "points": 3, "title": "Préparer l'audit",
             "ticket": {"from": "lea", "body": "Un auditeur passe la semaine prochaine. Il veut la liste de tous les fichiers de configuration <code>.conf</code> sous <code>/etc</code>, avec leur chemin complet. Attention, il a précisé : des <strong>fichiers</strong>, pas des dossiers ni des raccourcis, même s'ils portent un nom en <code>.conf</code>."},
             "desc": "La liste des <strong>fichiers ordinaires</strong> (ni dossiers, ni liens symboliques) dont le nom se termine par <code>.conf</code> sous <code>/etc</code>, visibles sans sudo, chemins complets comme les affiche <code>find /etc ...</code>, dans <code>~/audit-conf.txt</code>.",
             "hints": ["<code>find</code> accepte plusieurs critères à la suite, qui doivent tous être vrais : un sur le nom, un sur le type.",
                       "Redirigez la liste vers le fichier avec <code>&gt;</code>, et les « Permission denied » vers <code>/dev/null</code>."],
             "checks": [
                 ('test -s $H/audit-conf.txt', "~/audit-conf.txt est absent ou vide."),
                 ('''setcmp $H/audit-conf.txt "run_as etudiant \\"find /etc -type f -name '*.conf' 2>/dev/null\\""''', "La liste ne correspond pas au résultat attendu (fichiers manquants, ou dossiers et liens en trop)."),
             ]},
            {"id": "5.2", "points": 4, "title": "Le bon de réduction",
             "ticket": {"from": "sophie", "body": "Un client affirme avoir reçu un bon de réduction et le service client ne retrouve pas le dossier. Le code commence par <code>BON-</code> et il est forcément quelque part dans <code>/srv/archives</code>. Il me faut le fichier exact."},
             "desc": "Le <strong>chemin complet</strong> du fichier qui contient le bon, dans <code>~/bon-reduction.txt</code>.",
             "hints": ["<code>grep</code> sait chercher dans tout un dossier, sous-dossiers compris : relisez ses options dans le cours.",
                       "Une option de <code>grep</code> n'affiche que le nom des fichiers trouvés, sans les lignes."],
             "checks": [
                 ('[ "$(ans $H/bon-reduction.txt)" = "$LAB_BON_FILE" ]', "Ce n'est pas le bon fichier (indiquez le chemin complet, commençant par /srv)."),
             ]},
            {"id": "5.3", "points": 4, "title": "Estimer le ménage",
             "ticket": {"from": "lea", "body": "Avant de faire le ménage dans les archives, j'aimerais savoir combien de journaux <code>.log</code> sont rangés dans les dossiers <strong>2023</strong> de <code>/srv/archives</code>, tous services confondus. Attention, certains journaux ont « 2023 » dans leur nom sans être rangés dans 2023."},
             "desc": "Le nombre de fichiers <code>.log</code> situés dans un dossier <code>2023</code> de <code>/srv/archives</code>, dans <code>~/nb-logs.txt</code>.",
             "hints": ["<code>find</code> sait filtrer sur le chemin complet d'un fichier, pas seulement sur son nom : cherchez « -path » dans son manuel.",
                       "Un motif de chemin comme <code>'*/2023/*'</code>, combiné au motif de nom, puis on compte les lignes obtenues."],
             "checks": [
                 ('[ "$(ans $H/nb-logs.txt)" = "$LAB_NLOG2023" ]', "Ce n'est pas le bon nombre : seuls comptent les .log rangés dans un dossier 2023."),
             ]},
            {"id": "5.4", "points": 3, "title": "Le fichier qui pèse lourd",
             "ticket": {"from": "sophie", "body": "L'espace disque des archives a explosé cette nuit. Un seul fichier dépasse 5 Mo : trouve-le-moi, qu'on sache ce que c'est."},
             "desc": "Son chemin complet dans <code>~/gros-fichier.txt</code>.",
             "hints": ["<code>find</code> sait filtrer sur la taille : le cours donne le critère et ses unités.",
                       "Le signe <code>+</code> devant la taille veut dire « plus de »."],
             "checks": [
                 ('[ "$(ans $H/gros-fichier.txt)" = "$LAB_BIG" ]', "Ce n'est pas le bon fichier."),
             ]},
            {"id": "5.5", "points": 3, "title": "Les erreurs de facturation",
             "ticket": {"from": "diallo", "body": "Le logiciel de facturation a produit <code>/srv/archives/rapport.txt</code>. J'ai besoin du nombre de lignes qui signalent une erreur. Attention, le logiciel écrit « Erreur », « ERREUR » ou « erreur » selon son humeur…"},
             "desc": "Le nombre de lignes contenant <em>erreur</em>, quelle que soit la casse, dans <code>~/nb-erreurs.txt</code>.",
             "hints": ["<code>grep</code> a une option pour ignorer la casse et une autre pour compter les lignes : cherchez-les dans le cours.",
                       "Les options se combinent : <code>-x -y</code> s'écrit aussi <code>-xy</code>."],
             "checks": [
                 ('[ "$(ans $H/nb-erreurs.txt)" = "$LAB_NERR" ]', "Ce n'est pas le bon nombre (pensez à Erreur, ERREUR et erreur)."),
             ]},
            {"id": "5.6", "points": 4, "title": "Qu'est-ce qui a bougé ?",
             "ticket": {"from": "sophie", "body": "Quelqu'un a touché aux archives depuis la dernière sauvegarde, et je veux savoir à quoi. La sauvegarde laisse un fichier repère, <code>/srv/archives/.derniere-sauvegarde</code>, daté de son passage."},
             "desc": "La liste des fichiers de <code>/srv/archives</code> modifiés <strong>après</strong> le fichier repère <code>.derniere-sauvegarde</code> (chemins complets, un par ligne), dans <code>~/modifies.txt</code>.",
             "hints": ["<code>find</code> sait comparer la date de modification de chaque fichier à celle d'un autre fichier : cherchez « newer » dans son manuel.",
                       "Ne gardez que les fichiers ordinaires ; <code>ls -l</code> sur quelques résultats permet de vérifier les dates."],
             "checks": [
                 ('test -s $H/modifies.txt', "~/modifies.txt est absent ou vide."),
                 ('setcmp $H/modifies.txt "cat $REF/archives-modifiees"', "La liste ne correspond pas aux fichiers modifiés depuis la dernière sauvegarde (chemins complets attendus)."),
             ]},
            {"id": "5.7", "points": 4, "title": "Le mot, pas la suite de lettres",
             "ticket": {"from": "diallo", "body": "Nouveau rapport, <code>/srv/archives/rapport2.txt</code>. Cette fois, je veux le nombre de lignes qui contiennent le <strong>mot</strong> « erreur », quelle que soit la casse. « erreurs » ou « terreur », ce n'est pas le même mot !"},
             "desc": "Le nombre de lignes de <code>/srv/archives/rapport2.txt</code> qui contiennent <em>erreur</em> en tant que mot entier, quelle que soit la casse, dans <code>~/nb-erreur-mot.txt</code>.",
             "hints": ["<code>grep</code> cherche une suite de caractères, pas un mot : « terreur » contient « erreur ». Une de ses options ne retient que les mots entiers (cherchez « word » dans son manuel).",
                       "Combinez-la avec les deux options de l'exercice « Les erreurs de facturation »."],
             "checks": [
                 ('[ "$(ans $H/nb-erreur-mot.txt)" = "$LAB_NMOT" ]', "Ce n'est pas le bon nombre : « erreurs » et « terreur » ne comptent pas, « Erreur » et « ERREUR » oui."),
             ]},
            {"id": "5.8", "points": 5, "title": "Le piège des unités",
             "ticket": {"from": "lea", "body": "Julien doit lister les fichiers de moins de 1 Mio de <code>/srv/medias</code>. Il a tapé <code>find /srv/medias -size -1M</code> et n'obtient presque rien, alors qu'il y en a plein. Donne-moi la bonne liste, et explique-lui son erreur."},
             "desc": "La liste des fichiers de <code>/srv/medias</code> qui font <strong>strictement moins de 1 Mio</strong> (1 048 576 octets), chemins complets, un par ligne, dans <code>~/petits-medias.txt</code>.",
             "hints": ["<code>find</code> arrondit la taille de chaque fichier à l'unité demandée <strong>avant</strong> de comparer : avec <code>M</code>, un fichier de 300 Kio compte pour 1 Mio. Relisez <code>-size</code> dans <code>man find</code>.",
                       "Exprimez la limite dans une unité plus petite (<code>k</code>, ou même <code>c</code> pour les octets), et vérifiez les tailles avec <code>ls -l</code>."],
             "checks": [
                 ('test -s $H/petits-medias.txt', "~/petits-medias.txt est absent ou vide."),
                 ('setcmp $H/petits-medias.txt "cat $REF/petits-medias"', "La liste ne correspond pas aux fichiers de moins de 1 Mio (il en manque, ou il y en a de trop gros)."),
             ]},
            {"id": "5.9", "points": 4, "title": "La cause de l'erreur fatale",
             "ticket": {"from": "thomas", "body": "La boutique a planté cette nuit. Dans <code>~/logs-app/app.log</code> (3 000 lignes), il y a une seule ligne <code>FATAL</code>, et d'expérience, la vraie cause est toujours sur la ligne <strong>juste avant</strong>. Tu me la retrouves ?"},
             "desc": "La ligne qui précède immédiatement la ligne <code>FATAL</code>, telle quelle, dans <code>~/cause.txt</code>.",
             "hints": ["<code>grep</code> peut afficher des lignes de contexte autour de chaque ligne trouvée : cherchez « context » dans son manuel. Attention, la casse compte : « non fatale » n'est pas une erreur FATAL.",
                       "L'option qui affiche les lignes d'<em>avant</em> (<em>before</em>) prend un nombre de lignes."],
             "checks": [
                 ('test -s $H/cause.txt', "~/cause.txt est absent ou vide."),
                 ('grep -qF -- "$(cat $REF/cause-fatale)" $H/cause.txt && [ "$(grep -c "[^[:space:]]" $H/cause.txt)" -le 2 ]', "~/cause.txt ne contient pas la ligne qui précède la ligne FATAL (ou contient trop de lignes)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Redirections et pipes",
        "description": "Séparer, fusionner et enchaîner les flux : >, 2>, 2>&1, |, tee, sort, uniq.",
        "lesson": """<h3>Les trois flux</h3><table class="lesson-table"><tr><th>Flux</th><th>N°</th><th>Redirection</th></tr><tr><td>Entrée standard (stdin)</td><td>0</td><td><code>&lt; fichier</code></td></tr><tr><td>Sortie standard (stdout)</td><td>1</td><td><code>&gt; f</code>, <code>&gt;&gt; f</code></td></tr><tr><td>Erreurs (stderr)</td><td>2</td><td><code>2&gt; f</code>, <code>2&gt;&gt; f</code></td></tr></table><ul><li><code>2&gt;/dev/null</code> — jeter les erreurs (<code>/dev/null</code> avale tout)</li><li><code>2&gt;&amp;1</code> — envoyer les erreurs <strong>là où va déjà</strong> la sortie standard, à cet instant</li></ul><div class="tip">Les redirections se lisent <strong>de gauche à droite</strong>. <code>ls /etc /inexistant &gt; tout.txt 2&gt;&amp;1</code> met tout dans le fichier ; <code>ls /etc /inexistant 2&gt;&amp;1 &gt; tout.txt</code> laisse les erreurs à l'écran, car au moment du <code>2&gt;&amp;1</code>, la sortie standard allait encore à l'écran.</div><h3>Le pipe |</h3><p>Branche la sortie standard d'une commande sur l'entrée de la suivante (les erreurs, elles, ne passent pas dans le pipe) :</p><pre>cut -d: -f1 /etc/group | sort | head -5</pre><h3>tee</h3><p>Écrit ce qu'il reçoit dans un fichier <em>et</em> le transmet à la suite : <code>df -h | tee disque.txt</code> affiche et enregistre. Placé au milieu d'un pipeline, il garde une copie d'une étape intermédiaire.</p><h3>Outils utiles</h3><ul><li><code>sort</code> — trier les lignes (options <code>-u</code>, <code>-n</code>, <code>-r</code> : voir <code>man sort</code>)</li><li><code>uniq</code> — regrouper les lignes identiques <strong>consécutives</strong></li><li><code>head -n 3</code>, <code>tail -n 3</code> — premières et dernières lignes</li><li><code>cut -d' ' -f2</code> — 2<sup>e</sup> champ, champs séparés par une espace</li><li><code>wc -l</code> — compter les lignes</li></ul>""",
        "setup": r'''
# 6.3 : bavard mélange sortie normale et erreurs, dans un ordre tiré au sort
mapfile -t ordre < <(printf '%s\n' O O O O O O E E E E | shuf)
{ echo '#!/bin/bash'; k=0; e=0
  for x in "${ordre[@]}"; do
    if [ "$x" = O ]; then k=$((k + 1)); echo "echo \"OK étape $k\""; else e=$((e + 1)); echo "echo \"ERR problème $e\" >&2"; fi
  done; } > /usr/local/bin/bavard
chmod 755 /usr/local/bin/bavard
/usr/local/bin/bavard > $REF/bavard-tout 2>&1
# 6.7 : compteur écrit sur les deux flux ; des lignes normales parlent d'erreurs
nerr=$((RANDOM % 8 + 5)); nok=$((RANDOM % 10 + 8))
mapfile -t ordre < <({ for i in $(seq 1 $nok); do echo O; done; for i in $(seq 1 $nerr); do echo E; done; } | shuf)
{ echo '#!/bin/bash'; i=0
  for x in "${ordre[@]}"; do
    i=$((i + 1))
    if [ "$x" = O ]; then
      case $((RANDOM % 3)) in 0) echo "echo 'synchro $i : OK (0 ERR)'";; 1) echo "echo 'bilan $i : aucune erreur'";; 2) echo "echo 'lot $i transféré'";; esac
    else
      case $((RANDOM % 3)) in 0) echo "echo 'échec de la synchro $i' >&2";; 1) echo "echo 'délai dépassé pour le lot $i' >&2";; 2) echo "echo 'ERR disque lent ($i)' >&2";; esac
    fi
  done; } > /usr/local/bin/compteur
chmod 755 /usr/local/bin/compteur
emit NERRC "$nerr"
# 6.1 : des marqueurs d'audit cachés dans /etc (leur nombre est tiré au sort)
rm -f /etc/.audit-cimes-*
v=${LAB_VARIANTE_6_1:-$((RANDOM % 4))}
for i in $(seq 0 $v); do echo "audit $i" > /etc/.audit-cimes-$i; chmod 644 /etc/.audit-cimes-$i; done
# 6.6 : des relevés d'audit sous /etc (leur nombre est tiré au sort)
rm -rf /etc/cimes-audit
v=${LAB_VARIANTE_6_6:-$((RANDOM % 4))}
mkdir -p /etc/cimes-audit
for i in $(seq 0 $((3 * v + 1))); do echo "relevé $i" > /etc/cimes-audit/releve-$i.txt; done
chmod -R a+rX /etc/cimes-audit
# 6.4 : les outils maison installés dans /usr/bin (leur nombre est tiré au sort)
rm -f /usr/bin/cimes-outil-*
v=${LAB_VARIANTE_6_4:-$((RANDOM % 4))}
for i in $(seq 0 $v); do printf '#!/bin/sh\necho "Outil maison %s de Cimes & Sentiers"\n' $i > /usr/bin/cimes-outil-$i; chmod 755 /usr/bin/cimes-outil-$i; done
mkdir -p $H/texte
# 6.5 et 6.9 : des badges, noms répétés dans le désordre
mapfile -t gens < <(shuf -n 8 -e alice.martin bruno.petit chloe.roux david.leroy emma.blanc farid.nasri gael.morin hugo.faure ines.garnier jules.moreau)
{ for k in 0 1 2 3 4; do for r in $(seq 1 $((RANDOM % 3 + 2))); do echo "${gens[k]}"; done; done; for k in 5 6 7; do echo "${gens[k]}"; done; } | shuf \
  | while read -r g; do printf '2026-03-12 %02d:%02d porte-%s %s\n' $((RANDOM % 11 + 7)) $((RANDOM % 60)) "$(shuf -n1 -e nord sud)" "$g"; done > $H/texte/badges.txt
cut -d' ' -f4 $H/texte/badges.txt | sort -u > $REF/badgeurs
cut -d' ' -f4 $H/texte/badges.txt | sort | uniq -d > $REF/badges-multiples
# 6.8 : des montants de longueurs différentes
{ for i in $(seq 1 25); do echo $((RANDOM % 9000 + 1)); done; echo 9876; echo 987; for i in 1 2 3; do echo $((RANDOM % 30000 + 10000)); done; } | shuf > $H/texte/ventes.txt
sort -rn $H/texte/ventes.txt | head -n3 > $REF/top-ventes
own $H/texte
''',
        "exercises": [
            {"id": "6.1", "points": 3, "title": "Compter avec un pipe",
             "ticket": {"from": "lea", "body": "Question de l'auditeur : combien d'entrées contient <code>/etc</code> sur ce serveur, <strong>fichiers cachés compris</strong> ? Il veut la réponse dans un fichier, et je veux voir que tu sais le faire en une seule ligne, sans compter à la main."},
             "desc": "Le nombre d'entrées (fichiers et dossiers) de <code>/etc</code>, entrées cachées comprises mais sans compter <code>.</code> ni <code>..</code>, dans <code>~/nb-etc.txt</code>.",
             "hints": ["Le pipe <code>|</code> envoie la liste produite par une commande à une autre, qui sait compter les lignes.",
                       "<code>ls -a</code> affiche aussi <code>.</code> et <code>..</code> : une autre option de <code>ls</code> montre les entrées cachées sans eux (cherchez « almost » dans son manuel)."],
             "checks": [
                 ('[ "$(ans $H/nb-etc.txt)" = "$(ls -A /etc | wc -l)" ]', "Ce n'est pas le bon nombre (entrées cachées comprises, sans . ni ..)."),
             ]},
            {"id": "6.2", "points": 3, "title": "Séparer les erreurs",
             "ticket": {"from": "lea", "body": "Julien a lancé un <code>find /root</code> et son écran s'est rempli de « Permission denied ». Montre-lui comment ranger les résultats d'un côté et les erreurs de l'autre, dans deux fichiers séparés."},
             "desc": "Lancez <code>find /root</code> (sans sudo) en envoyant la sortie normale dans <code>~/find-ok.txt</code> et les erreurs dans <code>~/erreurs.txt</code>.",
             "hints": ["Chaque flux a son numéro : la sortie normale est le 1, les erreurs le 2. On peut rediriger les deux dans la même commande.",
                       "Le tableau du cours donne le symbole de chaque redirection ; les deux se placent à la suite, après la commande."],
             "checks": [
                 ('grep -qi "permission denied" $H/erreurs.txt', "~/erreurs.txt ne contient pas le message d'erreur de find."),
                 ('grep -qx /root $H/find-ok.txt && ! grep -qi "permission denied" $H/find-ok.txt', "~/find-ok.txt doit contenir la sortie normale de find /root, et elle seule."),
             ]},
            {"id": "6.3", "points": 4, "title": "Le programme bavard",
             "ticket": {"from": "thomas", "body": "L'outil <code>bavard</code> de Marc mélange ses messages normaux et ses erreurs à l'écran. Pour comprendre à quel moment ça déraille, il me faut <strong>tout</strong> ce qu'il affiche dans un seul fichier, dans l'ordre exact où ça sort."},
             "desc": "Toutes les lignes de <code>bavard</code>, sortie normale et erreurs, dans l'ordre où il les écrit, dans <code>~/tout.txt</code>.",
             "hints": ["Les deux flux doivent aller dans le <strong>même</strong> fichier, ouvert une seule fois : deux redirections vers le même nom s'écrasent l'une l'autre.",
                       "Relisez l'encadré du cours sur <code>2&gt;&amp;1</code> : l'ordre des redirections compte."],
             "checks": [
                 ('test -f $H/tout.txt && diff -q $H/tout.txt $REF/bavard-tout', "~/tout.txt ne contient pas toutes les lignes de bavard, dans l'ordre (ou il est absent)."),
             ]},
            {"id": "6.4", "points": 4, "title": "Sauvegarder au passage avec tee",
             "ticket": {"from": "sophie", "body": "J'aimerais garder la liste des programmes de <code>/usr/bin</code>, et savoir combien il y en a. Léa dit qu'on peut faire les deux d'une seule commande, sans relire le fichier après coup. Tu me montres ?"},
             "desc": "En une seule ligne de commande : la liste produite par <code>ls /usr/bin</code> dans <code>~/programmes.txt</code>, et le nombre de lignes de cette liste dans <code>~/nb-programmes.txt</code>.",
             "hints": ["<code>tee</code> peut se placer au milieu d'un pipeline : il écrit dans un fichier et laisse passer le flux vers la commande suivante.",
                       "Le schéma : une commande qui liste, <code>tee</code> avec le premier fichier, une commande qui compte, redirigée vers le second fichier."],
             "checks": [
                 ('test -f $H/programmes.txt && linecmp $H/programmes.txt "ls /usr/bin"', "~/programmes.txt ne contient pas la liste de /usr/bin (un nom par ligne)."),
                 ('[ "$(ans $H/nb-programmes.txt)" = "$(ls /usr/bin | wc -l)" ]', "~/nb-programmes.txt ne contient pas le nombre de programmes de la liste."),
             ]},
            {"id": "6.5", "points": 4, "title": "Qui a badgé ?",
             "ticket": {"from": "sophie", "body": "Le système de badges a produit <code>~/texte/badges.txt</code> : une ligne par passage (date, heure, porte, personne). Pour la revue des accès, il me faut la liste des personnes qui sont passées, triée par ordre alphabétique, chacune une seule fois."},
             "desc": "La liste des personnes (4<sup>e</sup> champ) de <code>~/texte/badges.txt</code>, triée par ordre alphabétique et sans doublon, une par ligne, dans <code>~/badgeurs.txt</code>.",
             "hints": ["Isolez d'abord la colonne des noms (les champs sont séparés par une espace), puis triez.",
                       "<code>cut</code> choisit le séparateur et le champ ; <code>sort</code> a une option qui supprime les doublons au passage."],
             "checks": [
                 ('linecmp $H/badgeurs.txt "cat $REF/badgeurs"', "Le contenu ne correspond pas à la liste triée, sans doublon, des personnes qui ont badgé."),
             ]},
            {"id": "6.6", "points": 3, "title": "Silence les erreurs !",
             "ticket": {"from": "lea", "body": "Combien de <strong>fichiers</strong> un utilisateur ordinaire peut-il voir sous <code>/etc</code> ? Je veux le nombre, et je ne veux <strong>aucun</strong> message d'erreur à l'écran : les « Permission denied », on les fait disparaître."},
             "desc": "Combien de <strong>fichiers</strong> (pas de dossiers) pouvez-vous voir sous <code>/etc</code>, sans sudo ? Écrivez le nombre dans <code>~/nb-fichiers-etc.txt</code>, sans qu'aucune erreur ne s'affiche à l'écran.",
             "hints": ["Il faut compter des fichiers, pas des dossiers : <code>find</code> a un critère de type.",
                       "Les « Permission denied » passent par la sortie d'erreur : envoyez-la dans <code>/dev/null</code>, et comptez les lignes de la sortie normale."],
             "checks": [
                 ('[ "$(ans $H/nb-fichiers-etc.txt)" = "$(run_as etudiant "find /etc -type f 2>/dev/null | wc -l")" ]', "Ce n'est pas le bon nombre (n'utilisez pas sudo)."),
             ]},
            {"id": "6.7", "points": 5, "title": "Seulement les erreurs",
             "ticket": {"from": "thomas", "body": "L'outil <code>compteur</code> écrit sur sa sortie normale et sur sa sortie d'erreur. Combien de lignes d'<strong>erreur</strong> écrit-il ? Julien a essayé <code>compteur 2&gt;&amp;1 | grep -c ERR</code>, mais son résultat ne veut rien dire."},
             "desc": "Le nombre de lignes que <code>compteur</code> écrit sur sa <strong>sortie d'erreur</strong>, dans <code>~/nb-erreurs-compteur.txt</code>.",
             "hints": ["Les lignes d'erreur ne contiennent pas toutes le même mot, et certaines lignes normales parlent d'erreurs : il faut séparer les flux, pas chercher un mot.",
                       "Pour compter les erreurs dans un pipe : envoyez-les là où va la sortie standard (le pipe), <em>puis</em> jetez l'ancienne sortie standard dans <code>/dev/null</code>. Ou passez par un fichier intermédiaire."],
             "checks": [
                 ('[ "$(ans $H/nb-erreurs-compteur.txt)" = "$LAB_NERRC" ]', "Ce n'est pas le nombre de lignes que compteur écrit sur sa sortie d'erreur."),
             ]},
            {"id": "6.8", "points": 4, "title": "Les plus grosses ventes",
             "ticket": {"from": "diallo", "body": "Il me faut les 3 plus grosses ventes du mois, depuis <code>~/texte/ventes.txt</code> (un montant par ligne). Julien a trié le fichier et il trouve que 9876 est plus grand que 12000… je ne crois pas, non."},
             "desc": "Les 3 plus grands montants de <code>~/texte/ventes.txt</code>, du plus grand au plus petit, un par ligne, dans <code>~/top-ventes.txt</code>.",
             "hints": ["Par défaut, <code>sort</code> compare des caractères : « 9 » passe après « 1 », donc 9876 après 12000.",
                       "<code>sort</code> a une option de tri numérique et une autre pour inverser l'ordre ; <code>head</code> garde les premières lignes."],
             "checks": [
                 ('test -f $H/top-ventes.txt && diff <(grep -v "^[[:space:]]*$" $H/top-ventes.txt | tr -d "[:blank:]") $REF/top-ventes', "Ce ne sont pas les 3 plus grands montants, du plus grand au plus petit."),
             ]},
            {"id": "6.9", "points": 4, "title": "Badges en double",
             "ticket": {"from": "sophie", "body": "Toujours dans <code>~/texte/badges.txt</code> : certaines personnes sont passées plusieurs fois dans la journée. Je veux juste leur liste, triée, sans le détail."},
             "desc": "La liste triée des personnes qui apparaissent <strong>au moins deux fois</strong> dans <code>~/texte/badges.txt</code>, une par ligne, dans <code>~/badges-multiples.txt</code>.",
             "hints": ["<code>uniq</code> ne compare que des lignes voisines : il faut trier avant.",
                       "<code>uniq</code> a une option qui n'affiche que les lignes répétées (cherchez « duplicate » dans son manuel)."],
             "checks": [
                 ('linecmp $H/badges-multiples.txt "cat $REF/badges-multiples"', "La liste ne correspond pas aux personnes passées plusieurs fois (triée, une par ligne)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    7: {
        "title": "Édition de texte en terminal",
        "description": "Modifier des fichiers avec nano, vim et sed : remplacements ciblés, séparateurs, sauvegarde, suppression de lignes.",
        "lesson": """<h3>nano — l'éditeur simple</h3><p><code>nano fichier</code> · <kbd>Ctrl+O</kbd> enregistrer · <kbd>Ctrl+X</kbd> quitter · <kbd>Ctrl+W</kbd> rechercher · <kbd>Ctrl+K</kbd> couper une ligne. La barre du bas rappelle les raccourcis (<code>^</code> veut dire <kbd>Ctrl</kbd>).</p><h3>vim — l'éditeur puissant</h3><p>Trois modes : <strong>normal</strong> (défaut), <strong>insertion</strong> (<kbd>i</kbd>), <strong>commande</strong> (<kbd>:</kbd>).</p><ul><li><kbd>i</kbd> insérer · <kbd>Echap</kbd> revenir en mode normal</li><li><kbd>dd</kbd> supprimer la ligne · <kbd>G</kbd> aller à la fin · <kbd>o</kbd> nouvelle ligne en dessous · <kbd>u</kbd> annuler</li><li><code>:w</code> enregistrer · <code>:q</code> quitter · <code>:wq</code> les deux · <code>:q!</code> quitter sans enregistrer</li></ul><div class="tip">Perdu dans vim ? <kbd>Echap</kbd> puis <code>:q!</code></div><h3>sed — l'éditeur de flux</h3><pre>sed 's/chat/chien/' f        # 1re occurrence de chaque ligne<br>sed 's/chat/chien/g' f       # toutes les occurrences (g : global)<br>sed -i 's/chat/chien/g' f    # modifie le fichier au lieu d'afficher le résultat<br>sed '3s/chat/chien/' f       # seulement la ligne 3<br>sed '/brouillon/d' f         # supprime les lignes qui contiennent « brouillon »</pre><p>Dans un motif, <code>^</code> désigne le début de la ligne (<code>/^#/</code> : les lignes qui <em>commencent</em> par #) ; les expressions régulières sont le sujet du jour suivant.</p><div class="tip">Sans <code>-i</code>, <code>sed</code> ne touche pas au fichier : lancez-le d'abord ainsi pour vérifier le résultat, puis ajoutez <code>-i</code>. <code>man sed</code> décrit aussi comment garder une copie de l'original.</div>""",
        "setup": r'''
mkdir -p $H/config
n=$((RANDOM % 4 + 3))
{
  echo "# Configuration de l'application (ancien-serveur remplace ancien-serveur-test)"
  for i in $(seq 1 $n); do echo "backend_$i=ancien-serveur:$((8000 + i)),ancien-serveur:$((9000 + i))"; done
  echo "timeout=30"
  echo "log=/var/log/ancien-serveur.log"
} > $H/config/app.conf
emit NOLD "$(grep -o ancien-serveur $H/config/app.conf | wc -l)"
emit NLIGNES "$(wc -l < $H/config/app.conf)"
cat > $H/config/poeme.txt <<'EOF'
Il pleure dans mon coeur
Comme il pleut sur la ville
INTRUS : cette ligne n'a rien à faire ici
Quelle est cette langueur
Qui pénètre mon coeur ?
EOF
# 7.3 : la configuration de l'appli de développement
printf '# Application de développement\nserveur=localhost\nport=%d\ndebug=false\ncache=off\n' $((RANDOM % 900 + 3000)) > $H/config/dev.conf
sed 's/^debug=false$/debug=true/' $H/config/dev.conf > $REF/dev.conf
# 7.5 : des chemins pleins de /
{
  echo "# Chemins de l'application boutique"
  echo "journal=/var/log/boutique/app.log"
  echo "erreurs=/var/log/boutique/erreurs.log"
  echo "debug=/var/log/boutique/debug-$(rword).log"
  echo "archives=/var/log/boutique-old"
  echo "nginx=/var/log/nginx/boutique.log"
  echo "rotation=/var/log/boutique/app.log /var/log/boutique/erreurs.log"
} > $H/config/chemins.conf
sed 's|/var/log/boutique|/srv/logs/boutique|g' $H/config/chemins.conf > $REF/chemins.conf
# 7.6 : une configuration de production à modifier avec filet
rm -f $H/config/app-prod.conf.bak
printf '# Application en production\nmaintenance=on\nmessage=Retour dans 10 minutes\nworkers=%d\n' $((RANDOM % 8 + 2)) > $H/config/app-prod.conf
emit PROD_MD5 "$(md5sum < $H/config/app-prod.conf | cut -c1-32)"
sed 's/^maintenance=on$/maintenance=off/' $H/config/app-prod.conf > $REF/app-prod.conf
# 7.7 : trois sections, le même réglage dans chacune
mapfile -t secs < <(shuf -e web admin api)
{ echo "; services de la boutique"; for s in "${secs[@]}"; do echo "[$s]"; echo "host=127.0.0.1"; echo "port=8080"; echo "workers=$((RANDOM % 4 + 1))"; echo; done; } > $H/config/services.ini
awk '/^\[/ { sec = $0 } sec == "[admin]" && $0 == "port=8080" { $0 = "port=9090" } { print }' $H/config/services.ini > $REF/services.ini
# 7.8 : un journal bavard
{ for i in $(seq 1 40); do
    case $((RANDOM % 4)) in
      0) echo "DEBUG requête $i : cache consulté";;
      1) echo "INFO requête $i traitée";;
      2) echo "WARN requête $i lente (mode DEBUG désactivé)";;
      3) echo "INFO niveau DEBUG ignoré en production";;
    esac
  done; echo "DEBUG fin du traitement"; echo "INFO bilan : 0 DEBUG en attente"; } > $H/config/app.log
grep -v '^DEBUG' $H/config/app.log > $REF/app.log
own $H/config
''',
        "exercises": [
            {"id": "7.1", "points": 3, "title": "Éditer avec nano",
             "ticket": {"from": "thomas", "body": "Il me faut un petit fichier de configuration pour mes tests locaux. Tu peux me l'écrire avec <code>nano</code> ? Trois lignes, pas une de plus, pas une de moins."},
             "desc": "Avec <code>nano</code>, créez <code>~/config.txt</code> contenant exactement ces 3 lignes :<br><code>serveur=localhost</code><br><code>port=8080</code><br><code>debug=false</code>",
             "hints": ["Ouvrez le fichier avec nano (il sera créé à l'enregistrement), tapez les lignes, puis regardez la barre du bas : <code>^</code> veut dire <kbd>Ctrl</kbd>.",
                       "<kbd>Ctrl+O</kbd> puis <kbd>Entrée</kbd> pour enregistrer, <kbd>Ctrl+X</kbd> pour quitter ; vérifiez avec <code>cat</code>."],
             "checks": [
                 ('test -f $H/config.txt', "~/config.txt n'existe pas."),
                 (r'''diff <(awk '{ l[NR] = $0 } NF { n = NR } END { for (i = 1; i <= n; i++) print l[i] }' $H/config.txt) <(printf 'serveur=localhost\nport=8080\ndebug=false\n')''', "Le contenu ne correspond pas exactement aux 3 lignes demandées : vérifiez chaque ligne, les espaces et les valeurs."),
             ]},
            {"id": "7.2", "points": 4, "title": "Éditer avec vim",
             "ticket": {"from": "julien", "body": "Marc a laissé un poème dans <code>~/config/poeme.txt</code> (oui, vraiment). Quelqu'un y a glissé une ligne qui n'a rien à faire là. Léa dit que c'est l'occasion d'apprendre <code>vim</code>… tu peux t'en occuper ?"},
             "desc": "Avec <code>vim</code>, dans <code>~/config/poeme.txt</code> : supprimez la ligne qui contient <code>INTRUS</code> et ajoutez une dernière ligne <code>Fin</code>. Le reste du poème ne change pas.",
             "hints": ["En mode normal, deux frappes de la même touche suppriment la ligne du curseur ; <kbd>G</kbd> va à la dernière ligne.",
                       "<kbd>o</kbd> ouvre une ligne sous le curseur en mode insertion ; <kbd>Echap</kbd> puis <code>:wq</code> enregistre et quitte."],
             "checks": [
                 ('! grep -q INTRUS $H/config/poeme.txt', "La ligne INTRUS est toujours là."),
                 ('[ "$(grep -v "^[[:space:]]*$" $H/config/poeme.txt | tail -n1)" = Fin ]', "La dernière ligne n'est pas « Fin »."),
                 (r'''diff <(awk '{ l[NR] = $0 } NF { n = NR } END { for (i = 1; i <= n; i++) print l[i] }' $H/config/poeme.txt) <(printf 'Il pleure dans mon coeur\nComme il pleut sur la ville\nQuelle est cette langueur\nQui pénètre mon coeur ?\nFin\n')''', "Le reste du poème a été modifié : seules la ligne INTRUS et la ligne Fin devaient changer."),
             ]},
            {"id": "7.3", "points": 3, "title": "Remplacer avec sed",
             "ticket": {"from": "thomas", "body": "Je dois activer le mode debug de l'appli de développement, dont la configuration est dans <code>~/config/dev.conf</code>. Plutôt que d'ouvrir un éditeur, tu peux le faire d'une seule commande avec <code>sed</code> ?"},
             "desc": "Avec <code>sed -i</code>, remplacez <code>debug=false</code> par <code>debug=true</code> dans <code>~/config/dev.conf</code> sans toucher aux autres lignes.",
             "hints": ["La commande <code>s</code> de sed remplace un texte par un autre ; l'option <code>-i</code> écrit le résultat dans le fichier.",
                       "Lancez d'abord la commande sans <code>-i</code> pour voir le résultat, puis vérifiez avec <code>cat</code> que seule la ligne du debug a changé."],
             "checks": [
                 ('grep -qx debug=true $H/config/dev.conf', "La ligne debug=true est absente de ~/config/dev.conf."),
                 ('diff -q $H/config/dev.conf $REF/dev.conf', "Les autres lignes de ~/config/dev.conf ont été modifiées (« Réinitialiser les fichiers de cette étape » pour recommencer)."),
             ]},
            {"id": "7.4", "points": 4, "title": "Remplacement global",
             "ticket": {"from": "lea", "body": "On a migré vers le nouveau serveur, mais <code>~/config/app.conf</code> mentionne encore l'ancien <strong>partout</strong>, parfois plusieurs fois sur la même ligne. Corrige toutes les occurrences d'un coup."},
             "desc": "Dans <code>~/config/app.conf</code>, remplacez <strong>toutes</strong> les occurrences de <code>ancien-serveur</code> par <code>nouveau-serveur</code>, sans rien changer d'autre.",
             "hints": ["Sans rien de plus, la commande <code>s</code> ne remplace que la première occurrence de chaque ligne : regardez les lignes qui en contiennent plusieurs.",
                       "Une lettre placée après le dernier <code>/</code> de <code>s///</code> change ce comportement : le cours l'appelle « global »."],
             "checks": [
                 ('! grep -q ancien-serveur $H/config/app.conf', "Il reste des occurrences de ancien-serveur (certaines lignes en contiennent plusieurs)."),
                 ('[ "$(grep -o nouveau-serveur $H/config/app.conf | wc -l)" -eq "$LAB_NOLD" ] && grep -qx timeout=30 $H/config/app.conf && [ "$(wc -l < $H/config/app.conf)" -eq "$LAB_NLIGNES" ]', "Le fichier a été abîmé : il ne contient plus exactement les lignes d'origine, avec nouveau-serveur à la place de ancien-serveur."),
             ]},
            {"id": "7.5", "points": 5, "title": "Changer un chemin",
             "ticket": {"from": "thomas", "body": "Les journaux de la boutique déménagent de <code>/var/log/boutique</code> vers <code>/srv/logs/boutique</code>. Mets à jour <code>~/config/chemins.conf</code> : chaque <code>/var/log/boutique</code> devient <code>/srv/logs/boutique</code>, y compris dans <code>/var/log/boutique-old</code>. Les journaux de nginx, eux, ne bougent pas."},
             "desc": "Dans <code>~/config/chemins.conf</code>, toutes les occurrences de <code>/var/log/boutique</code> sont remplacées par <code>/srv/logs/boutique</code> ; rien d'autre ne change.",
             "hints": ["Les <code>/</code> du chemin se confondent avec ceux qui séparent les parties de <code>s///</code>. Deux solutions : les protéger un par un avec <code>\\</code>, ou changer de séparateur.",
                       "sed accepte presque n'importe quel caractère comme séparateur, pourvu qu'il suive immédiatement le <code>s</code> et qu'il soit le même trois fois (par exemple <code>|</code> ou <code>#</code>)."],
             "checks": [
                 ('test -f $H/config/chemins.conf && diff -q $H/config/chemins.conf $REF/chemins.conf', "~/config/chemins.conf ne correspond pas au résultat attendu : une occurrence n'a pas été remplacée, ou autre chose a changé (« Réinitialiser les fichiers de cette étape » pour recommencer)."),
             ]},
            {"id": "7.6", "points": 4, "title": "Filet de sécurité",
             "ticket": {"from": "lea", "body": "Passe <code>maintenance=on</code> à <code>off</code> dans <code>~/config/app-prod.conf</code>. C'est la production, alors je veux une copie de l'original à côté, <code>app-prod.conf.bak</code>, au cas où. Et fais-le avec <code>sed</code> : il sait faire les deux d'un coup."},
             "desc": "<code>~/config/app-prod.conf.bak</code> est une copie exacte de l'original ; dans <code>~/config/app-prod.conf</code>, <code>maintenance=on</code> est devenu <code>maintenance=off</code>, le reste est inchangé.",
             "hints": ["L'option <code>-i</code> de sed accepte un suffixe, collé à l'option : il garde alors une copie de l'original sous ce nom. Cherchez « SUFFIX » dans <code>man sed</code>.",
                       "Avec le suffixe <code>.bak</code>, sed crée <code>app-prod.conf.bak</code> avant de modifier <code>app-prod.conf</code>."],
             "checks": [
                 ('[ "$(md5sum < $H/config/app-prod.conf.bak | cut -c1-32)" = "$LAB_PROD_MD5" ]', "~/config/app-prod.conf.bak n'existe pas ou n'est pas une copie exacte de l'original (« Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('diff -q $H/config/app-prod.conf $REF/app-prod.conf', "~/config/app-prod.conf ne contient pas maintenance=off, ou autre chose a changé."),
             ]},
            {"id": "7.7", "points": 5, "title": "Une seule section",
             "ticket": {"from": "thomas", "body": "Dans <code>~/config/services.ini</code>, le port de l'interface d'administration doit passer de 8080 à 9090. Seulement dans la section <code>[admin]</code> : les autres sections gardent 8080, sinon plus rien ne marche."},
             "desc": "Dans <code>~/config/services.ini</code>, la ligne <code>port=8080</code> de la section <code>[admin]</code> devient <code>port=9090</code> ; rien d'autre ne change.",
             "hints": ["<code>sed</code> peut limiter une commande à certaines lignes : un numéro de ligne (voir le cours), ou une plage entre deux motifs. Un éditeur fait aussi l'affaire.",
                       "<code>grep -n</code> donne le numéro de chaque ligne <code>port=</code> : repérez celle qui suit <code>[admin]</code> et ne modifiez qu'elle."],
             "checks": [
                 ('test -f $H/config/services.ini && diff -q $H/config/services.ini $REF/services.ini', "~/config/services.ini ne correspond pas au résultat attendu : seul le port de la section [admin] devait passer à 9090."),
             ]},
            {"id": "7.8", "points": 4, "title": "Supprimer le bruit",
             "ticket": {"from": "thomas", "body": "<code>~/config/app.log</code> est noyé sous les messages de débogage. Supprime toutes les lignes qui <strong>commencent</strong> par <code>DEBUG</code>. Attention, certaines lignes parlent du mode DEBUG plus loin dans le texte : celles-là restent."},
             "desc": "Dans <code>~/config/app.log</code>, plus aucune ligne ne commence par <code>DEBUG</code> ; toutes les autres lignes sont conservées, dans l'ordre.",
             "hints": ["<code>sed</code> sait supprimer les lignes qui correspondent à un motif (le cours le montre) ; il faut que le motif ne corresponde qu'en début de ligne.",
                       "Le cours donne le symbole qui ancre un motif au début de la ligne ; testez sans <code>-i</code> avant de modifier le fichier."],
             "checks": [
                 ('test -f $H/config/app.log && diff -q $H/config/app.log $REF/app.log', "~/config/app.log ne correspond pas au résultat attendu : il reste des lignes qui commencent par DEBUG, ou d'autres lignes ont disparu (« Réinitialiser les fichiers de cette étape » pour recommencer)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Expressions régulières",
        "description": "Décrire précisément ce que l'on cherche : ancres, classes, répétitions, alternatives, captures.",
        "lesson": r"""<h3>Syntaxe</h3><table class="lesson-table"><tr><th>Motif</th><th>Signification</th></tr><tr><td><code>.</code></td><td>N'importe quel caractère (un seul)</td></tr><tr><td><code>^</code> / <code>$</code></td><td>Début / fin de ligne</td></tr><tr><td><code>*</code></td><td>0 fois ou plus l'élément précédent</td></tr><tr><td><code>+</code> / <code>?</code></td><td>1 fois ou plus / 0 ou 1 fois (syntaxe étendue : <code>grep -E</code>, <code>sed -E</code>)</td></tr><tr><td><code>{2}</code>, <code>{2,}</code>, <code>{2,5}</code></td><td>Exactement 2 / au moins 2 / de 2 à 5 fois (syntaxe étendue)</td></tr><tr><td><code>[abc]</code> / <code>[^abc]</code></td><td>Un caractère parmi / hors de la liste</td></tr><tr><td><code>[a-z0-9]</code></td><td>Plages de caractères</td></tr><tr><td><code>[[:space:]]</code></td><td>Un caractère blanc : espace, tabulation… (<code>\s</code> est un raccourci propre à GNU)</td></tr><tr><td><code>\.</code></td><td>Un vrai point</td></tr><tr><td><code>(a|b)</code></td><td>a ou b (syntaxe étendue)</td></tr></table><div class="tip">Sans <code>-E</code>, grep et sed utilisent la syntaxe « de base », où <code>+</code>, <code>?</code>, <code>{</code>, <code>(</code> et <code>|</code> sont des caractères ordinaires.</div><h3>Avec grep</h3><pre>grep '^#' f                  # lignes qui commencent par #<br>grep -v '^$' f               # lignes non vides (-v inverse la sélection)<br>grep -E '^[0-9]{5}$' f       # lignes qui ne sont qu'un code postal<br>grep -oE '[0-9]+' f          # -o : n'affiche que les morceaux qui correspondent</pre><h3>Avec sed</h3><pre>sed 's/[0-9]/#/g' f          # chaque chiffre devient #<br>sed '/^$/d' f                # supprime les lignes vides<br>sed -E 's/([a-z]+)@/\1 at /' f   # (…) capture, \1 réutilise ce qui a été capturé</pre>""",
        "setup": r'''
# 8.1 : des comptes de service propres à ce serveur (variante tirée au sort)
for u in rapports sonde relais stock supervision scanner reporting synchro; do userdel "$u" >/dev/null 2>&1 || true; done
v=${LAB_VARIANTE_8_1:-$((RANDOM % 4))}
case $v in 0) svc="rapports sonde" ;; 1) svc="relais stock supervision" ;; 2) svc="scanner" ;; 3) svc="reporting synchro" ;; esac
for u in $svc; do useradd -r -M -d /nonexistent -s /usr/sbin/nologin "$u"; done
mkdir -p $H/regex
prenoms=(alice bruno chloe david emma farid gael hugo ines jules)
doms=(exemple.fr societe.com univ-lyon.fr mail.org)
pieges_mail=("jean@localhost" "@site.com" "marie.dupont@@exemple.fr" "bob@" "paul.martin@exemple" "lea@exemple.c" "JULIE.ROUX@EXEMPLE.FR" "tom@exemple..fr")
pieges_tel=("00 12 34 56 78" "06.12.34.56.78" "01 23 45 67" "01 23 45 67 890" "+33 6 12 34 56 78" "101 22 33 44 55")
mapfile -t pm < <(shuf -n 4 -e "${pieges_mail[@]}")
mapfile -t pt < <(shuf -n 3 -e "${pieges_tel[@]}")
{
  echo "# Carnet de contacts - export du $(date +%d/%m/%Y)"
  for i in $(seq 1 8); do
    echo "Contact $i : ${prenoms[RANDOM % 10]}.$((RANDOM % 90 + 10))@${doms[RANDOM % 4]} - tel 0$((RANDOM % 5 + 1)) $((RANDOM % 90 + 10)) $((RANDOM % 90 + 10)) $((RANDOM % 90 + 10)) $((RANDOM % 90 + 10))"
  done
  i=9
  for m in "${pm[@]}"; do echo "Contact $i : $m - adresse à vérifier"; i=$((i + 1)); done
  for t in "${pt[@]}"; do echo "Contact $i : standard - tel $t (à vérifier)"; i=$((i + 1)); done
  echo ""
  echo "Fin du carnet ($((i - 1)) contacts)"
} > $H/regex/contacts.txt
cp $H/regex/contacts.txt $REF/contacts.orig
grep -oE '[a-z0-9._-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}' $H/regex/contacts.txt | sort -u > $REF/emails.txt
grep -owE '0[1-9]( [0-9]{2}){4}' $H/regex/contacts.txt | sort -u > $REF/telephones.txt
sed -E 's/\b0[1-9]( [0-9]{2}){4}\b/XX XX XX XX XX/g' $H/regex/contacts.txt > $REF/censure.txt
printf '%s\n' "# Fichier de configuration du serveur" "# Ne pas modifier sans autorisation" "" "port=8080" "   # port secondaire désactivé" "host=0.0.0.0" "password=ab#12" "" "workers=4" "    " "	# fin des réglages réseau" "url=http://intranet/#accueil" "log_level=info" > $H/regex/serveur.conf
grep -vE '^\s*(#|$)' $H/regex/serveur.conf > $REF/serveur-clean.txt
# 8.6 : des dates à convertir, et des leurres
{
  for i in $(seq 1 12); do
    printf 'Paiement de %d,%02d € reçu le %02d/%02d/2026 (facture F-2026-%d)\n' $((RANDOM % 900 + 100)) $((RANDOM % 100)) $((RANDOM % 28 + 1)) $((RANDOM % 12 + 1)) $((RANDOM % 900 + 100))
  done
  printf 'Relances envoyées le %02d/%02d/2025 et le %02d/%02d/2025\n' $((RANDOM % 28 + 1)) $((RANDOM % 12 + 1)) $((RANDOM % 28 + 1)) $((RANDOM % 12 + 1))
  echo "Échéancier : prochaine échéance 03/2026, puis le 1/4/2026"
} > $H/regex/paiements.txt
sed -E 's#([0-9]{2})/([0-9]{2})/([0-9]{4})#\3-\2-\1#g' $H/regex/paiements.txt > $REF/paiements-iso.txt
# 8.7 : des identifiants valides et invalides
{
  for i in 1 2 3 4 5 6; do rword; done
  printf '%s\n' j_doe abc Admin 9lives jo un-nom-beaucoup-trop-long "bob smith" "ok_user!" " espace" "zoe-" "Marc.Legrand"
} | shuf > $H/regex/demandes.txt
grep -xE '[a-z][a-z0-9_-]{2,15}' $H/regex/demandes.txt | sort -u > $REF/identifiants.txt
# 8.8 : un prix à changer, et des faux amis
{
  echo "ref;libelle;prix"
  echo "REF-9599;Gourde inox;9.99"
  echo "REF-1002;Lampe 9x99;19.99"
  echo "REF-9x99;Boussole;9.95"
  echo "REF-2044;Bâtons de marche;29.99"
  echo "REF-3001;Piles (lot de 4);9.99"
  for i in 1 2 3 4 5; do echo "REF-$((RANDOM % 9000 + 1000));Article $i;$(shuf -n1 -e 9.99 4.50 99.90 9.49 12.99)"; done
} > $H/regex/tarifs.csv
awk -F';' 'BEGIN { OFS = ";" } NR > 1 && $3 == "9.99" { $3 = "10.49" } { print }' $H/regex/tarifs.csv > $REF/tarifs.csv
own $H/regex
''',
        "exercises": [
            {"id": "8.1", "points": 3, "title": "Début de ligne",
             "ticket": {"from": "lea", "body": "Pour l'audit, j'ai besoin des comptes de <code>/etc/passwd</code> dont le nom commence par <code>r</code> ou par <code>s</code>. Une seule expression régulière devrait suffire."},
             "desc": "Extrayez les lignes de <code>/etc/passwd</code> qui commencent par <code>r</code> <strong>ou</strong> par <code>s</code> dans <code>~/regex/rs.txt</code>.",
             "hints": ["Il faut ancrer le motif au début de la ligne et accepter l'une ou l'autre lettre : deux notions du tableau du cours.",
                       "Des crochets désignent un caractère parmi une liste."],
             "checks": [
                 ('linecmp $H/regex/rs.txt "grep \'^[rs]\' /etc/passwd"', "Le contenu ne correspond pas (lignes manquantes ou en trop)."),
             ]},
            {"id": "8.2", "points": 5, "title": "Adresses e-mail valides",
             "ticket": {"from": "diallo", "body": "Notre fichier de contacts est plein d'adresses mal saisies et l'envoi des factures échoue. Tu peux m'extraire seulement les adresses <strong>valides</strong> ? Attention, il y a des pièges."},
             "desc": "<code>~/regex/contacts.txt</code> contient des adresses valides et des pièges. Extrayez <strong>uniquement</strong> les adresses valides (une par ligne) dans <code>~/regex/emails-valides.txt</code>.<br>Adresse valide, entièrement en minuscules : une partie locale faite de caractères <code>[a-z0-9._-]</code>, un seul <code>@</code>, puis un domaine fait de mots <code>[a-z0-9-]</code> séparés par des points simples, qui se termine par un point suivi d'au moins 2 lettres.",
             "hints": ["<code>grep -oE</code> n'affiche que la partie reconnue par le motif. Construisez le motif morceau par morceau et testez-le à chaque étape.",
                       "Structure : partie locale, <code>@</code>, un mot, puis zéro ou plusieurs fois « point + mot » (un groupe entre parenthèses suivi de <code>*</code>), puis « point + au moins 2 lettres » (<code>{2,}</code>). Et pas d'option <code>-i</code> !"],
             "checks": [
                 ('test -s $H/regex/emails-valides.txt', "~/regex/emails-valides.txt est absent ou vide."),
                 ('setcmp $H/regex/emails-valides.txt "cat $REF/emails.txt"', "La liste ne correspond pas : il y a des adresses manquantes, des adresses invalides ou du texte en trop."),
             ]},
            {"id": "8.3", "points": 4, "title": "Configuration épurée",
             "ticket": {"from": "lea", "body": "<code>~/regex/serveur.conf</code> est noyé sous les commentaires et les lignes vides. Sors-moi uniquement les lignes utiles, dans l'ordre, que je voie la vraie configuration."},
             "desc": "Extrayez de <code>~/regex/serveur.conf</code> les lignes utiles — ni vides (ou blanches), ni commentaires (même précédés d'espaces ou de tabulations) — dans <code>~/regex/serveur-clean.txt</code>, en gardant l'ordre. Un <code>#</code> au milieu d'une valeur n'est pas un commentaire.",
             "hints": ["Deux sortes de lignes à écarter : celles dont le premier caractère non blanc est <code>#</code>, et celles qui ne contiennent que des blancs. <code>grep -v</code> inverse la sélection.",
                       "Avec <code>-E</code>, <code>(a|b)</code> exprime une alternative ; <code>^</code>, <code>[[:space:]]*</code> et <code>$</code> décrivent « des blancs éventuels en début de ligne », « jusqu'à la fin de la ligne »."],
             "checks": [
                 ('test -f $H/regex/serveur-clean.txt && diff -q $H/regex/serveur-clean.txt $REF/serveur-clean.txt', "Le résultat n'est pas le bon : vérifiez les commentaires indentés, les lignes qui ne contiennent que des blancs, et les # au milieu d'une valeur."),
             ]},
            {"id": "8.4", "points": 5, "title": "Censure",
             "ticket": {"from": "sophie", "body": "Je dois transmettre la liste de contacts à un prestataire, mais sans aucun numéro de téléphone lisible, RGPD oblige. Masque-les, mais garde le reste tel quel (il a besoin des adresses et des numéros de contact), et ne touche pas à l'original."},
             "desc": "<code>~/regex/censure.txt</code> est une copie de <code>contacts.txt</code> où chaque numéro de téléphone (un <code>0</code>, un chiffre de 1 à 9, puis 4 groupes « espace + 2 chiffres », non collé à d'autres chiffres) est remplacé par <code>XX XX XX XX XX</code>. Tout le reste est identique, et <code>contacts.txt</code> n'est pas modifié.",
             "hints": ["Remplacer tous les chiffres masquerait aussi les adresses et les numéros de contact : il faut un motif qui décrit un numéro entier.",
                       "<code>sed -E</code> accepte les mêmes regex étendues que <code>grep -E</code>, et <code>\\b</code> y marque une frontière de mot : pratique pour ne pas mordre dans un nombre plus long."],
             "checks": [
                 ('cmp -s $H/regex/contacts.txt $REF/contacts.orig', "~/regex/contacts.txt a été modifié : il fallait écrire le résultat dans censure.txt (« Réinitialiser les fichiers de cette étape » remet l'original)."),
                 ('test -f $H/regex/censure.txt && diff -q $H/regex/censure.txt $REF/censure.txt', "~/regex/censure.txt ne correspond pas : un numéro n'est pas masqué, un faux numéro l'a été, ou autre chose a changé."),
             ]},
            {"id": "8.5", "points": 4, "title": "Numéros de téléphone",
             "ticket": {"from": "diallo", "body": "La relance téléphonique commence lundi. Il me faudrait tous les numéros de téléphone valides du fichier de contacts, un par ligne. Il y a des numéros mal saisis : ceux-là, on les laisse de côté."},
             "desc": "Extrayez les numéros au format <code>0X XX XX XX XX</code> (X de 1 à 9 pour le premier, non collés à d'autres chiffres) de <code>~/regex/contacts.txt</code>, un par ligne, dans <code>~/regex/telephones.txt</code>.",
             "hints": ["Un numéro : un zéro, un chiffre de 1 à 9, puis 4 fois « espace + 2 chiffres ». Des faux numéros traînent : trop longs, trop courts, avec des points…",
                       "<code>grep -o</code> n'affiche que la partie reconnue ; une option de grep ne retient une correspondance que si elle n'est pas collée à d'autres lettres ou chiffres."],
             "checks": [
                 ('setcmp $H/regex/telephones.txt "cat $REF/telephones.txt"', "La liste ne correspond pas aux numéros valides du carnet."),
             ]},
            {"id": "8.6", "points": 5, "title": "Dates au format ISO",
             "ticket": {"from": "diallo", "body": "Le nouveau logiciel comptable veut les dates au format AAAA-MM-JJ. Convertis toutes les dates JJ/MM/AAAA de <code>~/regex/paiements.txt</code> dans un nouveau fichier. Les échéances incomplètes (juste un mois, ou un jour sur un seul chiffre) restent telles quelles."},
             "desc": "<code>~/regex/paiements-iso.txt</code> : le contenu de <code>paiements.txt</code> où chaque date <code>JJ/MM/AAAA</code> (2, 2 et 4 chiffres) est devenue <code>AAAA-MM-JJ</code>. Le reste est identique.",
             "hints": ["Capturez les trois morceaux de la date entre parenthèses (avec <code>sed -E</code>), puis réutilisez-les dans le remplacement, dans l'ordre voulu.",
                       "Dans le remplacement, <code>\\1</code>, <code>\\2</code>, <code>\\3</code> désignent les morceaux capturés. Choisissez un séparateur de <code>s</code> autre que <code>/</code>, et n'oubliez pas les lignes qui contiennent deux dates."],
             "checks": [
                 ('test -f $H/regex/paiements-iso.txt && diff -q $H/regex/paiements-iso.txt $REF/paiements-iso.txt', "~/regex/paiements-iso.txt ne correspond pas : une date n'est pas convertie, un leurre l'a été, ou autre chose a changé."),
             ]},
            {"id": "8.7", "points": 5, "title": "Valider des identifiants",
             "ticket": {"from": "sophie", "body": "Les demandes de création de compte sont dans <code>~/regex/demandes.txt</code>, une par ligne. Garde uniquement les identifiants valides : une minuscule en premier, puis de 2 à 15 caractères parmi les minuscules, les chiffres, <code>_</code> et <code>-</code>. <strong>Rien d'autre sur la ligne</strong>, pas même une espace."},
             "desc": "Les lignes de <code>~/regex/demandes.txt</code> qui sont en entier un identifiant valide, dans <code>~/regex/identifiants.txt</code>.",
             "hints": ["Sans ancrage, une regex trouve un morceau valide au milieu d'une ligne invalide : il faut que la ligne <strong>entière</strong> corresponde.",
                       "Encadrez le motif par <code>^</code> et <code>$</code> (ou utilisez l'option <code>-x</code> de grep) ; <code>{2,15}</code> fixe le nombre de répétitions."],
             "checks": [
                 ('test -s $H/regex/identifiants.txt', "~/regex/identifiants.txt est absent ou vide."),
                 ('setcmp $H/regex/identifiants.txt "cat $REF/identifiants.txt"', "La liste ne correspond pas aux identifiants valides (il en manque, ou des lignes invalides s'y sont glissées)."),
             ]},
            {"id": "8.8", "points": 5, "title": "Le point qui n'en est pas un",
             "ticket": {"from": "diallo", "body": "Dans <code>~/regex/tarifs.csv</code>, tous les articles à 9.99 passent à 10.49. Ne touche surtout à rien d'autre : ni à la référence REF-9599, ni à la lampe 9x99, ni aux articles à 19.99 ou 29.99 !"},
             "desc": "Dans <code>~/regex/tarifs.csv</code>, chaque prix (3<sup>e</sup> colonne) égal à <code>9.99</code> devient <code>10.49</code> ; tout le reste est inchangé.",
             "hints": ["À gauche de <code>s///</code>, le point est un joker qui accepte n'importe quel caractère ; et « 9.99 » apparaît aussi à l'intérieur d'autres prix.",
                       "Échappez le point et ancrez le motif sur la colonne des prix : ici, entre le dernier <code>;</code> et la fin de la ligne."],
             "checks": [
                 ('test -f $H/regex/tarifs.csv && diff -q $H/regex/tarifs.csv $REF/tarifs.csv', "~/regex/tarifs.csv ne correspond pas : un prix à 9.99 n'a pas changé, ou autre chose a été modifié (« Réinitialiser les fichiers de cette étape » pour recommencer)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    9: {
        "title": "Filtrage et traitement de texte",
        "description": "Analyser des données avec sort, uniq, cut, awk et tr : filtres, comptages, sommes, agrégats.",
        "lesson": r"""<h3>sort &amp; uniq</h3><pre>sort f                 # trier<br>sort f | uniq -c       # compter les lignes identiques (entrée triée !)<br>sort -rn               # tri numérique décroissant<br>sort -t';' -k3 -n f    # trier sur le 3e champ, séparateur ;</pre><h3>cut</h3><pre>cut -d: -f1 /etc/group     # 1er champ, séparateur :<br>tail -n +2 f               # tout sauf la 1re ligne (un en-tête, par exemple)</pre><h3>awk</h3><p>awk découpe chaque ligne en champs <code>$1</code>, <code>$2</code>… (séparateur : les espaces, ou celui donné par <code>-F</code>). <code>NF</code> est le nombre de champs, <code>NR</code> le numéro de ligne.</p><pre>awk '{print $1}' f                       # 1re colonne<br>awk -F: '$4 == 0 {print $1}' /etc/passwd # condition sur un champ, puis action<br>awk '$2 &gt; 100 &amp;&amp; $3 != "OK"' f          # conditions combinées (sans action : affiche la ligne)<br>awk '$1 ~ /^srv/' f                      # ~ : le champ correspond à une regex (!~ : ne correspond pas)</pre><p>awk sait aussi calculer : une variable s'additionne ligne après ligne (<code>s += $2</code>), et le bloc <code>END { … }</code> s'exécute après la dernière ligne. Un tableau peut être indexé par un texte : <code>n[$1]++</code> compte les lignes pour chaque valeur du 1<sup>er</sup> champ.</p><h3>tr</h3><pre>echo "bonjour" | tr 'a-z' 'A-Z'    # remplace caractère par caractère<br>tr -d ',' &lt; f                      # supprime des caractères</pre><h3>Le « top » classique</h3><pre>awk '{print $7}' access.log | sort | uniq -c | sort -rn | head -3    # les 3 pages les plus demandées</pre><div class="tip">Format du journal d'accès : <code>IP - - [jour/mois/année:heure:min:s +0100] "GET /page HTTP/1.1" CODE TAILLE</code>. Avec le séparateur par défaut, l'IP est le 1<sup>er</sup> champ, la page le 7<sup>e</sup>, le code HTTP le 9<sup>e</sup> et la taille le 10<sup>e</sup>.</div>""",
        "setup": r'''
# 9.1 : des comptes de bornes et d'impression, avec des shells variés (variante tirée au sort)
for u in imprim kiosque borne1 borne2 borne3 ftpdepot mailrelay; do userdel "$u" >/dev/null 2>&1 || true; done
v=${LAB_VARIANTE_9_1:-$((RANDOM % 4))}
case $v in
  0) cpt="imprim:/bin/sh" ;;
  1) cpt="ftpdepot:/bin/false mailrelay:/bin/false" ;;
  2) cpt="kiosque:/bin/dash" ;;
  3) cpt="borne1:/bin/sh borne2:/usr/sbin/nologin borne3:/bin/sh" ;;
esac
for c in $cpt; do useradd -r -M -d /nonexistent -s "${c#*:}" "${c%%:*}"; done
mkdir -p $H/logs $H/texte
ips=(); for i in $(seq 1 12); do ips+=("10.0.$i.$((RANDOM % 250 + 2))"); done
mapfile -t ord < <(printf '%s\n' "${ips[@]}" | shuf)
cible="10.0.20.$((RANDOM % 9 + 1))"; leurre="${cible}$((RANDOM % 9 + 1))"
e1=$((RANDOM % 4 + 22)); e2=$((e1 - RANDOM % 3 - 3)); e3=$((e2 - RANDOM % 3 - 3))
urls=(/ /index.html /contact /produits /api/login /panier /images/logo.png /blog)
okc=(200 200 200 301 304); erc=(404 404 404 500 403 503)
hot=$((RANDOM % 24))
tmp=$(mktemp)
ligne() {
  local h=$((RANDOM % 24))
  if [ $((RANDOM % 4)) -eq 0 ]; then h=$hot; fi
  printf '%s - - [12/Mar/2026:%02d:%02d:%02d +0100] "GET %s HTTP/1.1" %s %d\n' "$1" $h $((RANDOM % 60)) $((RANDOM % 60)) "${urls[RANDOM % 8]}" "$2" $((RANDOM % 5000 + 200)) >> $tmp
}
serie() { local j; for ((j = 0; j < $2; j++)); do ligne $1 ${okc[RANDOM % 5]}; done; for ((j = 0; j < $3; j++)); do ligne $1 ${erc[RANDOM % 6]}; done; }
# les 3 IP qui cumulent le plus d'erreurs ne sont pas celles qui font le plus de requêtes
serie ${ord[0]} $((RANDOM % 5 + 2)) $e1
serie ${ord[1]} $((RANDOM % 5 + 2)) $e2
serie ${ord[2]} $((RANDOM % 5 + 2)) $e3
for k in 3 4 5; do serie ${ord[k]} $((RANDOM % 16 + 60)) $((RANDOM % 3)); done
for k in $(seq 6 11); do serie ${ord[k]} $((RANDOM % 20 + 5)) $((RANDOM % (e3 - 4))); done
serie $cible $((RANDOM % 10 + 8)) $((RANDOM % 3))
serie $leurre $((RANDOM % 10 + 8)) $((RANDOM % 3))
# pièges pour « grep 404 » : une page et des tailles qui contiennent 404
printf '%s - - [12/Mar/2026:10:%02d:00 +0100] "GET /produits/404-sac-randonnee HTTP/1.1" 200 %d\n' ${ord[4]} $((RANDOM % 60)) $((RANDOM % 3000 + 500)) >> $tmp
for s in 1404 4040; do printf '%s - - [12/Mar/2026:11:%02d:00 +0100] "GET /blog HTTP/1.1" 200 %d\n' ${ord[5]} $((RANDOM % 60)) $s >> $tmp; done
shuf $tmp > $H/logs/access.log; rm -f $tmp
echo "Client à surveiller (facture de bande passante) : $cible" > $H/logs/LISEZ-MOI
emit TOP3 "${ord[0]},${ord[1]},${ord[2]}"
emit N404 "$(awk '$9 == 404' $H/logs/access.log | wc -l)"
emit OCTETS "$(awk -v ip=$cible '$1 == ip { s += $10 } END { print s }' $H/logs/access.log)"
emit HOT "$(awk -F: '{ print $2 }' $H/logs/access.log | sort | uniq -c | sort -rn | awk 'NR == 1 { print $2 }')"
# 9.4 : un fichier de comptes d'un autre serveur, avec des pièges
u=($(shuf -i 1000-1999 -n 6))
{
  echo "root:x:0:0:root:/root:/bin/bash"
  { echo "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin"
    echo "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin"
    echo "sauvegarde:x:999:999:compte de service:/var/backups:/bin/bash"
    echo "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin"
    echo "ancien:x:${u[0]}:${u[0]}:ancien salarié:/home/ancien:/usr/sbin/nologin"
    echo "prestataire:x:${u[1]}:${u[1]}:accès coupé:/home/prestataire:/bin/false"
    echo "admin:x:1000:1000:Admin:/home/admin:/bin/bash"
    echo "claire:x:${u[2]}:${u[2]}:Claire:/home/claire:/bin/bash"
    echo "karim:x:${u[3]}:${u[3]}:Karim:/home/karim:/bin/zsh"
    echo "lucie:x:${u[4]}:${u[4]}:Lucie:/home/lucie:/bin/sh"
    echo "mathis:x:${u[5]}:${u[5]}:Mathis:/home/mathis:/bin/bash"; } | shuf
} > $H/texte/passwd-serveur
awk -F: '$3 >= 1000 && $3 < 65534 && $7 !~ /(nologin|false)$/ { print $1, $3 }' $H/texte/passwd-serveur | sort > $REF/humains.txt
printf '%s\n' "le shell est un interprete de commandes" "linux est un systeme libre" "les pipes relient les commandes entre elles" > $H/texte/minuscules.txt
# 9.7 : des ventes où un même produit revient sur plusieurs lignes
prods=(gourde piolet lampe tente duvet boussole corde gants)
for essai in $(seq 1 40); do
  { echo "produit;quantite;prix_unitaire"
    for i in $(seq 1 30); do echo "${prods[RANDOM % 8]};$((RANDOM % 9 + 1));$((RANDOM % 80 + 5)).$((RANDOM % 9))0"; done; } > $H/texte/ventes.csv
  totaux=$(awk -F';' 'NR > 1 { t[$1] += $2 * $3 } END { for (p in t) printf "%.2f %s\n", t[p], p }' $H/texte/ventes.csv | sort -rn)
  agg=$(echo "$totaux" | head -n3 | awk '{ print $2 }' | paste -sd,)
  naif=$(awk -F';' 'NR > 1 { printf "%.2f %s\n", $2 * $3, $1 }' $H/texte/ventes.csv | sort -rn | awk '!vu[$2]++ { print $2 }' | head -n3 | paste -sd,)
  distincts=$(echo "$totaux" | head -n4 | awk '{ print $1 }' | sort -u | wc -l)
  if [ "$agg" != "$naif" ] && [ "$distincts" -eq 4 ]; then break; fi
done
emit TOPPROD "$agg"
printf '%s\n' "élève à l'école" "où est la clé ?" "façade ensoleillée" "noël au château" "très bientôt réouvert" > $H/texte/accents.txt
sed 's/.*/\U&/' $H/texte/accents.txt > $REF/accents-maj.txt
own $H/logs $H/texte
''',
        "exercises": [
            {"id": "9.1", "points": 3, "title": "Compter les shells",
             "ticket": {"from": "lea", "body": "Combien de comptes utilisent chaque shell sur ce serveur ? Donne-moi le décompte trié du plus fréquent au moins fréquent : c'est souvent comme ça qu'on repère un compte bizarre."},
             "desc": "Pour chaque shell de <code>/etc/passwd</code> (7<sup>e</sup> champ), comptez le nombre d'utilisateurs. Sauvegardez le résultat de <code>uniq -c</code>, trié du plus fréquent au moins fréquent, dans <code>~/shells-count.txt</code>.",
             "hints": ["Isolez le 7<sup>e</sup> champ, puis regroupez les valeurs identiques en les comptant. <code>uniq</code> ne regroupe que des lignes voisines.",
                       "Quatre étapes : extraire le champ, trier, compter, puis trier à nouveau sur le nombre, dans l'ordre décroissant."],
             "checks": [
                 ('setcmp $H/shells-count.txt "cut -d: -f7 /etc/passwd | sort | uniq -c"', "Les comptes ne correspondent pas à /etc/passwd."),
                 ('[ "$(awk \'NF{print $1; exit}\' $H/shells-count.txt)" = "$(cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn | awk \'{print $1; exit}\')" ]', "Le fichier n'est pas trié du plus fréquent au moins fréquent."),
             ]},
            {"id": "9.2", "points": 5, "title": "Top 3 des fauteurs d'erreurs",
             "ticket": {"from": "thomas", "body": "La boutique a ramé toute la nuit et le journal est plein d'erreurs. Je ne cherche pas les clients les plus actifs, mais ceux qui provoquent le plus d'<strong>erreurs</strong> (code HTTP 400 ou plus) : je soupçonne des robots mal réglés. Tu me trouves les 3 adresses IP concernées ?"},
             "desc": "Dans <code>~/logs/access.log</code>, les 3 adresses IP qui cumulent le plus de requêtes en erreur (code HTTP ≥ 400), de la plus fautive à la moins fautive, dans <code>~/top-ip.txt</code>.",
             "hints": ["Filtrez d'abord les lignes en erreur avec une condition awk sur le bon champ (relisez le format du journal dans le cours), puis appliquez le « top » classique à l'IP.",
                       "<code>awk '$9 &gt;= 400 {print $1}'</code> donne l'IP de chaque requête en erreur ; il reste à compter, trier et garder les 3 premières."],
             "checks": [
                 ('[ "$(grep -oE "([0-9]{1,3}\\.){3}[0-9]{1,3}" $H/top-ip.txt | head -3 | paste -sd,)" = "$LAB_TOP3" ]', "Ce ne sont pas les 3 IP qui cumulent le plus d'erreurs, ou elles ne sont pas dans le bon ordre."),
             ]},
            {"id": "9.3", "points": 4, "title": "Pages introuvables",
             "ticket": {"from": "thomas", "body": "Le référencement de la boutique baisse, et je pense que c'est à cause des pages introuvables. Combien de requêtes ont reçu une erreur 404 ?"},
             "desc": "Combien de requêtes de <code>~/logs/access.log</code> ont reçu le code HTTP <code>404</code> ? Écrivez le nombre dans <code>~/nb-404.txt</code>.",
             "hints": ["« 404 » peut apparaître ailleurs que dans le code HTTP : dans une taille de réponse, dans une adresse de page… Filtrez sur le bon champ.",
                       "awk peut n'afficher que les lignes dont un champ précis vaut une valeur donnée ; il reste à les compter."],
             "checks": [
                 ('[ "$(ans $H/nb-404.txt)" = "$LAB_N404" ]', "Ce n'est pas le bon nombre. Un simple grep 404 compte-t-il trop de lignes ?"),
             ]},
            {"id": "9.4", "points": 4, "title": "Les vrais comptes humains",
             "ticket": {"from": "sophie", "body": "Pour la revue des accès du serveur de l'agence de Chambéry, j'ai récupéré son fichier de comptes : <code>~/texte/passwd-serveur</code>. Je ne veux que les comptes de vraies personnes qui peuvent encore se connecter : pas les comptes système, ni ceux dont le shell interdit la connexion."},
             "desc": "Avec <code>awk</code>, listez les comptes de <code>~/texte/passwd-serveur</code> dont l'UID est ≥ 1000 et &lt; 65534 <strong>et</strong> dont le shell ne se termine ni par <code>nologin</code> ni par <code>false</code>, sous la forme <code>nom UID</code> (séparés par une espace), dans <code>~/users-uid.txt</code>.",
             "hints": ["Avec <code>-F:</code>, <code>$3</code> est l'UID et <code>$7</code> le shell. Une condition awk peut combiner plusieurs tests avec <code>&amp;&amp;</code>.",
                       "<code>~</code> teste si un champ correspond à une regex, <code>!~</code> le contraire : <code>$7 !~ /nologin/</code>. Les bornes comptent : 1000 est inclus, 65534 exclu."],
             "checks": [
                 ('test -s $H/users-uid.txt', "~/users-uid.txt est absent ou vide."),
                 ('setcmp $H/users-uid.txt "cat $REF/humains.txt"', "La liste ne correspond pas aux comptes humains qui peuvent se connecter (vérifiez les bornes d'UID et les shells)."),
             ]},
            {"id": "9.5", "points": 3, "title": "Tout en majuscules",
             "ticket": {"from": "julien", "body": "Le vieux logiciel de caisse n'accepte que des textes en MAJUSCULES. Tu peux convertir <code>~/texte/minuscules.txt</code> pour moi ?"},
             "desc": "Avec <code>tr</code>, convertissez <code>~/texte/minuscules.txt</code> en majuscules dans <code>~/texte/majuscules.txt</code>.",
             "hints": ["<code>tr</code> ne prend pas de nom de fichier : il lit l'entrée standard, qu'on alimente avec <code>&lt;</code> ou un pipe.",
                       "<code>tr</code> prend deux ensembles de caractères, par exemple deux plages : chaque caractère du premier est remplacé par celui qui est à la même place dans le second."],
             "checks": [
                 ('test -f $H/texte/majuscules.txt && diff -q $H/texte/majuscules.txt <(tr a-z A-Z < $H/texte/minuscules.txt)', "Le contenu ne correspond pas au texte converti en majuscules."),
             ]},
            {"id": "9.6", "points": 4, "title": "La facture de bande passante",
             "ticket": {"from": "thomas", "body": "Un client nous coûte cher en bande passante : son adresse est notée dans <code>~/logs/LISEZ-MOI</code>. Combien d'octets lui avons-nous envoyés au total, d'après le journal ?"},
             "desc": "La somme des tailles de réponse (10<sup>e</sup> champ) de toutes les requêtes de l'adresse indiquée dans <code>~/logs/LISEZ-MOI</code>, dans <code>~/octets-ip.txt</code>.",
             "hints": ["awk peut accumuler une valeur ligne après ligne dans une variable, et l'afficher à la fin, dans le bloc <code>END</code>.",
                       "Filtrez sur le 1<sup>er</sup> champ avec une égalité exacte (<code>==</code>) : un <code>grep</code> sur l'adresse attraperait aussi une adresse plus longue qui commence pareil."],
             "checks": [
                 ('[ "$(ans $H/octets-ip.txt)" = "$LAB_OCTETS" ]', "Ce n'est pas le bon total pour cette adresse (avez-vous compté des lignes d'une autre adresse ?)."),
             ]},
            {"id": "9.7", "points": 5, "title": "Chiffre d'affaires par produit",
             "ticket": {"from": "diallo", "body": "Dans <code>~/texte/ventes.csv</code> (<code>produit;quantite;prix_unitaire</code>, avec une ligne d'en-tête), un même produit apparaît sur plusieurs lignes. Il me faut les 3 produits qui ont rapporté le plus au total, du plus gros au plus petit."},
             "desc": "Les 3 produits au plus gros chiffre d'affaires total (somme des quantité × prix de toutes leurs lignes), un par ligne, du plus gros au plus petit, dans <code>~/top-produits.txt</code>.",
             "hints": ["Il faut additionner les montants de chaque produit <strong>avant</strong> de classer : la plus grosse ligne n'est pas forcément le plus gros produit. Un tableau awk indexé par le nom du produit fait ça très bien.",
                       "Sautez l'en-tête (<code>NR &gt; 1</code>), accumulez <code>t[$1] += $2 * $3</code>, affichez chaque total dans le bloc <code>END</code> avec une boucle <code>for (p in t)</code>, puis triez numériquement."],
             "checks": [
                 ('[ "$(grep -v "^[[:space:]]*$" $H/top-produits.txt | awk \'{ for (i = 1; i <= NF; i++) if ($i !~ /^[0-9.,]+$/) { print $i; break } }\' | head -n3 | paste -sd,)" = "$LAB_TOPPROD" ]', "Ce ne sont pas les 3 produits au plus gros chiffre d'affaires total, dans l'ordre (ou le fichier est absent)."),
             ]},
            {"id": "9.8", "points": 5, "title": "Majuscules accentuées",
             "ticket": {"from": "julien", "body": "La nouvelle caisse accepte enfin les accents ! Mais quand je convertis <code>~/texte/accents.txt</code> avec <code>tr</code>, les « é » restent en minuscules. Il me le faut entièrement en majuscules, accents compris."},
             "desc": "<code>~/texte/accents-maj.txt</code> : le texte de <code>~/texte/accents.txt</code> entièrement en majuscules, lettres accentuées comprises (É, À, Ç…).",
             "hints": ["<code>tr</code> travaille octet par octet ; en UTF-8, « é » occupe deux octets, que <code>tr</code> ne sait pas convertir comme une seule lettre. Il faut un outil qui comprend les caractères.",
                       "Dans la partie remplacement de <code>s///</code>, GNU sed accepte <code>\\U</code>, qui passe en majuscules tout ce qui suit (et <code>&amp;</code> désigne tout le texte trouvé) ; awk a aussi une fonction <code>toupper()</code>."],
             "checks": [
                 ('test -f $H/texte/accents-maj.txt && diff -q $H/texte/accents-maj.txt $REF/accents-maj.txt', "~/texte/accents-maj.txt n'est pas le texte entièrement en majuscules, accents compris."),
             ]},
            {"id": "9.9", "points": 4, "title": "L'heure de pointe",
             "ticket": {"from": "thomas", "body": "Pour planifier la maintenance, j'ai besoin de savoir à quelle heure de la journée la boutique reçoit le plus de requêtes, d'après <code>~/logs/access.log</code>."},
             "desc": "L'heure (de 00 à 23) qui compte le plus de requêtes dans <code>~/logs/access.log</code>, dans <code>~/heure-pointe.txt</code>.",
             "hints": ["L'heure est entre le premier et le deuxième « : » de la date : avec un autre séparateur de champs que l'espace, elle devient un champ à part entière.",
                       "<code>awk -F:</code> découpe aux deux-points ; appliquez ensuite le « top » classique au bon champ."],
             "checks": [
                 ('a=$(ans $H/heure-pointe.txt); [[ $a =~ ^[0-9]{1,2}$ ]] && [ "$((10#$a))" = "$((10#$LAB_HOT))" ]', "Ce n'est pas l'heure qui compte le plus de requêtes (un nombre de 00 à 23 est attendu)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    10: {
        "title": "Utilisateurs, groupes et permissions",
        "description": "Créer comptes et groupes avec sudo, régler les droits, et contrôler réellement qui accède à quoi.",
        "lesson": """<h3>sudo</h3><p>Vous êtes <code>etudiant</code>, un utilisateur normal. Les commandes d'administration se lancent avec <code>sudo</code> (mot de passe : <code>etudiant</code>) :</p><pre>sudo useradd -m -s /bin/bash carla</pre><h3>Utilisateurs</h3><table class="lesson-table"><tr><th>Commande</th><th>Action</th></tr><tr><td><code>useradd -m -s /bin/bash u</code></td><td>Créer (avec dossier personnel et shell bash)</td></tr><tr><td><code>adduser u</code></td><td>Créer, version interactive (Debian/Ubuntu)</td></tr><tr><td><code>userdel -r u</code></td><td>Supprimer avec son dossier</td></tr><tr><td><code>id u</code></td><td>Voir UID et groupes</td></tr></table><h3>Groupes</h3><table class="lesson-table"><tr><th>Commande</th><th>Action</th></tr><tr><td><code>groupadd g</code></td><td>Créer un groupe</td></tr><tr><td><code>usermod -aG g u</code></td><td>Ajouter u au groupe g. <strong>Sans -a</strong>, la liste des groupes secondaires de u est <strong>remplacée</strong> : il perd tous les autres !</td></tr></table><h3>Permissions</h3><p>3 triades : <strong>u</strong>tilisateur propriétaire · <strong>g</strong>roupe · <strong>o</strong>thers (les autres). <code>r</code>=4, <code>w</code>=2, <code>x</code>=1 ; on additionne dans chaque triade.</p><ul><li><code>chmod 750 dossier</code> — octal : fixe tous les droits d'un coup</li><li><code>chmod g+w,o-rwx f</code> — symbolique : ajoute ou retire des droits sans toucher aux autres</li><li><code>chown carla:compta f</code>, <code>chgrp compta f</code> — changer le propriétaire et le groupe</li></ul><div class="tip">Sur un <strong>dossier</strong> : <code>r</code> = lister, <code>w</code> = créer ou supprimer dedans, <code>x</code> = entrer et traverser.</div><h3>Le bit setgid sur un dossier</h3><p><code>chmod g+s dossier</code> (ou le chiffre 2 devant l'octal, comme dans <code>2770</code>) : les fichiers créés dedans héritent du <strong>groupe du dossier</strong>, au lieu du groupe principal de leur créateur.</p><h3>umask</h3><p>La <strong>umask</strong> retire des droits à chaque fichier créé : avec 022, un nouveau fichier est en 644 (<code>rw-r--r--</code>), sans écriture pour le groupe ; avec 002, il est en 664. Le setgid règle le groupe d'un nouveau fichier, pas ses droits.</p><h3>Écrire dans un fichier qui appartient à root</h3><p>Dans <code>sudo commande &gt; fichier</code>, c'est <strong>votre</strong> shell, pas root, qui ouvre le fichier : seule la commande tourne en root. Pour faire écrire un fichier par root, il faut que ce soit une commande lancée avec sudo qui l'ouvre elle-même.</p><h3>Tester en tant qu'un autre utilisateur</h3><pre>sudo -u carla touch /srv/compta/test</pre>""",
        "setup": r'''
mkuser intrus
mkdir -p $H/scripts
printf '#!/bin/bash\necho "Déploiement..."\n' > $H/scripts/deploy.sh
modes=(640 604 664 660 644 600 620)
m=${modes[RANDOM % 7]}
chmod $m $H/scripts/deploy.sh
own $H/scripts
emit DEPLOY_MODE "$(printf '%o' $((8#$m | 8#100)))"
# 10.7 : un compte déjà membre de plusieurs groupes
groupadd -f catalogue; groupadd -f boutique
mkuser webdev
orig=$(shuf -n 3 -e adm www-data catalogue users | sort | paste -sd,)
usermod -G "$orig" webdev
mkdir -p $H/rh
echo "Groupes secondaires de webdev (relevé du 1er septembre) : ${orig//,/, }" > $H/rh/webdev.txt
own $H/rh
emit WEBDEV_GROUPS "$orig"
# 10.8 : un fichier de configuration qui appartient à root
printf '# Environnement de la boutique\nBOUTIQUE_DB=%s\nBOUTIQUE_PORT=%d\n' "$(rword)" $((RANDOM % 1000 + 8000)) > /etc/boutique.env
chown root:root /etc/boutique.env; chmod 644 /etc/boutique.env
emit ENV_MD5 "$(md5sum < /etc/boutique.env | cut -c1-32)"
emit ENV_N "$(wc -l < /etc/boutique.env)"
# 10.9 : des droits à reproduire, tirés au sort
D=$H/droits
rm -rf $D; mkdir -p $D
mapfile -t cibles < <(shuf -n 3 -e 751 640 400 754 705 620 711 600 750 604 700 741)
fics=(rapport.txt lancer.sh archives.tar)
: > $D/CONSIGNE
for i in 0 1 2; do
  echo "contenu de ${fics[i]}" > $D/${fics[i]}
  chmod ${cibles[i]} $D/${fics[i]}
  printf '%-14s %s\n' "${fics[i]}" "$(stat -c %A $D/${fics[i]})" >> $D/CONSIGNE
  chmod 666 $D/${fics[i]}
  emit DROIT$i "${cibles[i]}"
done
own $D
''',
        "exercises": [
            {"id": "10.1", "points": 3, "title": "Créer des utilisateurs",
             "ticket": {"from": "sophie", "body": "Deux nouvelles recrues arrivent lundi au service marketing : Alice et Bob. Crée-leur un compte, avec leur dossier personnel bien sûr."},
             "desc": "Les utilisateurs <code>alice</code> et <code>bob</code> existent, chacun <strong>avec</strong> son dossier personnel, qui lui appartient.",
             "hints": ["Créer un compte est une tâche d'administration : il faut sudo, et la commande dont le nom veut dire « ajouter un utilisateur ».",
                       "Sans l'option <code>-m</code>, <code>useradd</code> ne crée pas le dossier personnel ; <code>-s</code> choisit le shell."],
             "checks": [
                 ('id alice && id bob', "alice et/ou bob n'existent pas."),
                 ('test -d /home/alice && test -d /home/bob', "Les dossiers personnels /home/alice et /home/bob n'existent pas (une option de useradd les crée)."),
                 ('[ "$(owner /home/alice)" = alice ] && [ "$(owner /home/bob)" = bob ]', "Les dossiers personnels doivent appartenir à leur utilisateur : laissez useradd les créer."),
             ]},
            {"id": "10.2", "points": 3, "title": "Créer un groupe",
             "ticket": {"from": "sophie", "body": "Alice et Bob vont travailler ensemble sur la prochaine campagne. Regroupe-les dans un groupe <code>equipe</code>."},
             "desc": "Créez le groupe <code>equipe</code> et ajoutez-y <code>alice</code> et <code>bob</code>.",
             "hints": ["Deux temps : créer le groupe, puis y ajouter chaque utilisateur, sans lui retirer ses autres groupes.",
                       "Le cours donne les deux commandes ; vérifiez le résultat avec <code>id alice</code>."],
             "checks": [
                 ('getent group equipe', "Le groupe equipe n'existe pas."),
                 ('id -nG alice | grep -qw equipe && id -nG bob | grep -qw equipe', "alice et bob doivent tous deux être membres du groupe equipe."),
             ]},
            {"id": "10.3", "points": 4, "title": "Dossier d'équipe",
             "ticket": {"from": "sophie", "body": "L'équipe marketing a besoin d'un dossier partagé. Tout le monde dans l'équipe doit pouvoir y déposer des fichiers et voir ce qu'il contient, et personne d'autre ne doit pouvoir y entrer."},
             "desc": "Créez <code>/home/partage</code>. Les membres d'<code>equipe</code> peuvent y créer des fichiers et le lister ; les autres utilisateurs (comme <code>intrus</code>) n'ont <strong>aucun</strong> droit dessus.",
             "hints": ["Trois réglages : le groupe du dossier, les droits du groupe (lister, créer, entrer), et aucun droit pour les autres.",
                       "<code>chgrp</code> change le groupe ; en octal, <code>rwx</code> = 7 et <code>---</code> = 0."],
             "checks": [
                 ('test -d /home/partage', "/home/partage n'existe pas."),
                 ('[ "$(stat -c %G /home/partage)" = equipe ]', "/home/partage n'appartient pas au groupe equipe."),
                 ('run_as bob "touch /home/partage/.t-bob && rm -f /home/partage/.t-bob" && run_as alice "ls /home/partage"', "Un membre d'equipe ne peut pas créer de fichier dans /home/partage, ou ne peut pas le lister."),
                 ('! run_as intrus "ls /home/partage" && [ "$(others /home/partage)" = "---" ]', "Les autres utilisateurs (comme intrus) ont encore des droits sur /home/partage."),
             ]},
            {"id": "10.4", "points": 4, "title": "Fichier confidentiel",
             "ticket": {"from": "sophie", "body": "Alice va rédiger le plan de la campagne, qui est confidentiel. Elle seule peut le modifier, le reste de l'équipe peut le lire, et les autres n'y ont aucun accès."},
             "desc": "Créez <code>/home/partage/secret.txt</code> appartenant à <code>alice</code> et au groupe <code>equipe</code> : alice peut le modifier, les membres du groupe peuvent seulement le lire, les autres n'ont aucun droit.",
             "hints": ["Deux choses à régler : le propriétaire et le groupe (<code>chown</code> sait faire les deux, avec <code>:</code>), puis les droits.",
                       "Propriétaire <code>rw-</code>, groupe <code>r--</code>, autres <code>---</code> : traduisez chaque triade en chiffre."],
             "checks": [
                 ('test -f /home/partage/secret.txt', "/home/partage/secret.txt n'existe pas."),
                 ('[ "$(stat -c %U:%G /home/partage/secret.txt)" = alice:equipe ]', "Le fichier doit appartenir à alice et au groupe equipe."),
                 ('run_as alice "test -w /home/partage/secret.txt"', "alice ne peut pas modifier le fichier."),
                 ('run_as bob "cat /home/partage/secret.txt" && ! run_as bob "test -w /home/partage/secret.txt"', "bob doit pouvoir lire le fichier mais pas le modifier."),
                 ('[ "$(others /home/partage/secret.txt)" = "---" ]', "Les autres utilisateurs ont encore des droits sur le fichier."),
             ]},
            {"id": "10.5", "points": 3, "title": "chmod symbolique",
             "ticket": {"from": "lea", "body": "Le script <code>~/scripts/deploy.sh</code> doit devenir exécutable, mais par toi seul. Et fais-le en notation symbolique, sans toucher aux autres droits : c'est un réflexe à prendre, d'autant que ses droits actuels sont un peu particuliers."},
             "desc": "<code>~/scripts/deploy.sh</code> est exécutable <strong>par vous seul</strong> ; tous ses autres droits sont restés ceux de départ.",
             "hints": ["La notation symbolique modifie un droit sans toucher aux autres : <em>qui</em> (u, g, o), <em>quoi</em> (+ ou -), <em>quel droit</em> (r, w, x).",
                       "Regardez les droits avec <code>ls -l</code> avant et après : seul un <code>x</code> doit être apparu, dans la première triade."],
             "checks": [
                 ('[ "$(perm $H/scripts/deploy.sh)" = "$LAB_DEPLOY_MODE" ]', "Les droits de deploy.sh ne sont pas ceux de départ avec seulement l'exécution en plus pour vous (« Réinitialiser les fichiers de cette étape » remet les droits d'origine)."),
             ]},
            {"id": "10.6", "points": 4, "title": "Héritage du groupe",
             "ticket": {"from": "lea", "body": "Bob se plaint : les fichiers qu'il dépose dans le dossier partagé appartiennent à son groupe personnel, <code>bob</code>. Du coup, Alice peut les lire (grâce aux droits des « autres »… on en reparlera), mais elle ne peut pas les <strong>modifier</strong>. Fais en sorte que tout nouveau fichier du dossier appartienne automatiquement au groupe de l'équipe."},
             "desc": "Tout fichier créé dans <code>/home/partage</code> appartient automatiquement au groupe <code>equipe</code>, quel que soit son créateur.",
             "hints": ["Un bit spécial, posé sur un dossier, fait hériter aux nouveaux fichiers le groupe du dossier au lieu du groupe principal de leur créateur : relisez le cours.",
                       "C'est le bit setgid ; il se pose avec <code>chmod</code>, en symbolique (<code>g+…</code>) ou en octal."],
             "checks": [
                 ('test -g /home/partage', "Le bit setgid n'est pas positionné sur /home/partage."),
                 ('run_as alice "touch /home/partage/.t-sgid" && [ "$(stat -c %G /home/partage/.t-sgid)" = equipe ]; r=$?; rm -f /home/partage/.t-sgid; exit $r', "Un fichier créé par alice n'hérite pas du groupe equipe."),
             ]},
            {"id": "10.7", "points": 4, "title": "Ne pas perdre ses groupes",
             "ticket": {"from": "lea", "body": "Ajoute le compte <code>webdev</code> au groupe <code>boutique</code>. Attention : il est déjà membre d'autres groupes (le relevé est dans <code>~/rh/webdev.txt</code>), et il doit tous les garder, sinon le déploiement du site casse."},
             "desc": "<code>webdev</code> est membre du groupe <code>boutique</code> <strong>et</strong> de tous ses groupes secondaires d'origine.",
             "hints": ["Regardez d'abord ses groupes actuels avec <code>id</code>. Relisez l'avertissement du cours sur <code>usermod -G</code> : sans une option de plus, il <strong>remplace</strong> la liste des groupes.",
                       "L'option <code>-a</code> (<em>append</em>) ajoute sans rien retirer ; elle s'utilise avec <code>-G</code>. Si des groupes ont déjà été perdus, rajoutez-les de la même façon."],
             "checks": [
                 ('getent group boutique >/dev/null && id -nG webdev | tr " " "\\n" | grep -qx boutique', "webdev n'est pas membre du groupe boutique."),
                 ('g=" $(id -nG webdev) "; for x in ${LAB_WEBDEV_GROUPS//,/ }; do [[ $g == *" $x "* ]] || exit 1; done', "webdev a perdu au moins un de ses groupes d'origine (notés dans ~/rh/webdev.txt) : rajoutez-le."),
             ]},
            {"id": "10.8", "points": 4, "title": "sudo n'y peut rien ?",
             "ticket": {"from": "thomas", "body": "J'ai tapé <code>sudo echo \"BOUTIQUE_ENV=prod\" &gt;&gt; /etc/boutique.env</code> et on me répond « Permission denied », alors que j'utilise sudo ! Tu peux ajouter cette ligne à la fin du fichier ? Et sans bricoler les droits du fichier, hein."},
             "desc": "La ligne <code>BOUTIQUE_ENV=prod</code> est ajoutée à la fin de <code>/etc/boutique.env</code> ; le contenu d'origine est intact ; le fichier appartient toujours à root, avec ses droits d'origine (644).",
             "hints": ["Relisez la partie du cours sur l'écriture dans un fichier de root : la redirection <code>&gt;&gt;</code> est faite par votre shell, qui n'est pas root, avant même que sudo ne démarre.",
                       "Faites ouvrir le fichier par une commande lancée avec sudo : <code>tee</code> recopie son entrée dans un fichier, et une de ses options ajoute à la fin au lieu d'écraser."],
             "checks": [
                 ('[ "$(owner /etc/boutique.env)" = root ] && [ "$(perm /etc/boutique.env)" = 644 ]', "/etc/boutique.env doit toujours appartenir à root, avec ses droits d'origine (644) : pas de chmod ni de chown pour contourner."),
                 ('[ "$(head -n "$LAB_ENV_N" /etc/boutique.env | md5sum | cut -c1-32)" = "$LAB_ENV_MD5" ]', "Le contenu d'origine de /etc/boutique.env a été modifié ou écrasé : il fallait ajouter à la fin (« Réinitialiser les fichiers de cette étape » le remet en place)."),
                 ('[ "$(grep -v "^[[:space:]]*$" /etc/boutique.env | tail -n1)" = "BOUTIQUE_ENV=prod" ]', "La dernière ligne de /etc/boutique.env n'est pas BOUTIQUE_ENV=prod."),
             ]},
            {"id": "10.9", "points": 4, "title": "Droits à la carte",
             "ticket": {"from": "julien", "body": "Léa m'a laissé une consigne dans <code>~/droits/CONSIGNE</code> : chaque fichier du dossier doit avoir exactement les droits indiqués, tels que <code>ls -l</code> les affiche. Moi, les <code>rwx</code>, je m'y perds…"},
             "desc": "Chaque fichier de <code>~/droits</code> a exactement les droits indiqués dans <code>~/droits/CONSIGNE</code>.",
             "hints": ["Traduisez chaque triade (propriétaire, groupe, autres) en un chiffre : r vaut 4, w 2, x 1, et on additionne.",
                       "Un <code>chmod</code> en octal par fichier ; vérifiez ensuite avec <code>ls -l</code> que l'affichage correspond caractère pour caractère à la consigne."],
             "checks": [
                 ('[ "$(perm $H/droits/rapport.txt)" = "$LAB_DROIT0" ]', "Les droits de rapport.txt ne correspondent pas à la consigne."),
                 ('[ "$(perm $H/droits/lancer.sh)" = "$LAB_DROIT1" ]', "Les droits de lancer.sh ne correspondent pas à la consigne."),
                 ('[ "$(perm $H/droits/archives.tar)" = "$LAB_DROIT2" ]', "Les droits de archives.tar ne correspondent pas à la consigne."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    11: {
        "title": "Super-utilisateur et processus",
        "description": "Déléguer les droits d'administration, puis identifier, signaler, mettre en pause et arrêter des processus.",
        "lesson": """<h3>sudo et su</h3><ul><li><code>sudo commande</code> — exécuter en root ; sous Ubuntu, les membres du groupe <code>sudo</code> y ont droit, et sudo demande <strong>leur propre</strong> mot de passe</li><li><code>sudo -u carla commande</code> — exécuter en tant que carla</li><li><code>sudo -i</code> — ouvrir un shell root (à éviter au quotidien)</li><li><code>su - carla</code> — ouvrir une session sous l'identité de carla ; <code>su</code> demande le mot de passe de <strong>carla</strong> (sauf pour root : <code>sudo su - carla</code>)</li><li><code>sudo -l</code> — ce que vous avez le droit de lancer ; <code>sudo -l -U carla</code> — ce qu'a le droit de lancer carla</li></ul><h3>Les règles de sudo</h3><p>Elles sont dans <code>/etc/sudoers</code> et dans les fichiers de <code>/etc/sudoers.d/</code>, une règle par ligne :</p><pre>%compta   ALL=(root) /usr/bin/lpq            # le groupe compta peut lancer lpq en root<br>carla     ALL=(ALL:ALL) ALL                  # carla peut tout faire</pre><div class="tip">Une erreur de syntaxe dans ces fichiers peut bloquer <strong>tout</strong> sudo. On les modifie toujours avec <code>sudo visudo</code> (ou <code>sudo visudo -f /etc/sudoers.d/fichier</code>), qui vérifie la syntaxe avant d'enregistrer.</div><h3>Observer les processus</h3><pre>ps aux                         # instantané de tous les processus<br>ps -o pid,user,ni,cmd -C sleep  # colonnes choisies, pour un nom de commande<br>pgrep -a nom                   # PID + commande<br>top                            # temps réel (q pour quitter)</pre><p>Colonnes utiles de <code>ps aux</code> : <code>USER</code>, <code>PID</code>, <code>%CPU</code>, <code>%MEM</code>, <code>STAT</code> (état : <code>S</code> endormi, <code>R</code> en cours, <code>T</code> arrêté…), <code>COMMAND</code>. Chaque processus a aussi un <strong>parent</strong>, celui qui l'a lancé : son PID est le <code>PPID</code>.</p><h3>Signaux</h3><table class="lesson-table"><tr><th>Commande</th><th>Signal</th><th>Effet par défaut</th></tr><tr><td><code>kill PID</code></td><td>TERM (15)</td><td>Demande d'arrêt : le programme peut faire le ménage avant de s'arrêter</td></tr><tr><td><code>kill -9 PID</code></td><td>KILL (9)</td><td>Arrêt immédiat, sans ménage possible (dernier recours)</td></tr><tr><td><code>kill -HUP PID</code></td><td>HUP (1)</td><td>Arrêt… sauf si le programme l'intercepte : par convention, beaucoup de services le traitent comme « relis ta configuration »</td></tr></table><p><code>kill -l</code> liste tous les signaux. On ne peut envoyer un signal qu'à ses propres processus… sauf avec <code>sudo</code>.</p><h3>Arrière-plan et priorité</h3><ul><li><code>commande &amp;</code> — lancer en arrière-plan ; <code>jobs</code>, <code>fg</code>, <code>bg</code> pour les tâches du terminal</li><li><code>nice -n 15 commande</code> — lancer avec une priorité plus basse (gentillesse 15, de -20 à 19)</li><li><code>renice -n 5 -p PID</code> — changer la gentillesse d'un processus déjà lancé ; un utilisateur ordinaire peut l'augmenter, pas la baisser</li></ul>""",
        "volatile": True,
        "setup": r'''
mkuser intrus
# Variantes tirées à la première ouverture ou à la réinitialisation, conservées après un redémarrage du conteneur
if first_run 11 || [ ! -f $REF/var-11 ]; then
  { echo "v2=${LAB_VARIANTE_11_2:-$((RANDOM % 4))}"; echo "v5=${LAB_VARIANTE_11_5:-$((RANDOM % 3))}"; echo "v6=${LAB_VARIANTE_11_6:-$((RANDOM % 3))}"; } > $REF/var-11
  done_once 11
fi
. $REF/var-11
# 11.2 : le compte qui a lancé rogue-worker
ru=(intrus prestataire webdev ancien-admin); ru=${ru[v2]}
mkuser "$ru"
cat > /usr/local/bin/rogue-worker <<'EOF'
#!/bin/bash
trap 'echo "$(date +%T) arrêt propre (signal TERM reçu)" >> /var/log/rogue.log; exit 0' TERM
while true; do sleep 5 & wait $!; done
EOF
chmod 755 /usr/local/bin/rogue-worker
pkill -KILL -x rogue-worker || true
: > /var/log/rogue.log; chown "$ru:$ru" /var/log/rogue.log; chmod 644 /var/log/rogue.log
su -s /bin/bash "$ru" -c 'setsid /usr/local/bin/rogue-worker >/dev/null 2>&1 < /dev/null &'
# 11.5 : le signal de rechargement, documenté par le service lui-même
sig=(HUP USR1 USR2); sig=${sig[v5]}
cat > /usr/local/sbin/lab-service <<EOF
#!/bin/bash
# lab-service : service de démonstration de Cimes & Sentiers.
# « lab-service --aide » affiche la documentation.
if [ "\${1:-}" = --aide ]; then
    echo "lab-service : service de démonstration de Cimes & Sentiers."
    echo "Configuration : /etc/lab-service.conf, relue à chaud à la réception du signal $sig."
    echo "Tout autre signal l'arrête."
    exit 0
fi
trap 'echo "\$(date +%T) configuration rechargée" >> /var/log/lab-service.log' $sig
echo "\$(date +%T) démarrage" >> /var/log/lab-service.log
while true; do sleep 1 & wait \$!; done
EOF
chmod 755 /usr/local/sbin/lab-service
echo "clients_max=200" > /etc/lab-service.conf
: > /var/log/lab-service.log; chmod 644 /var/log/lab-service.log
pkill -x lab-service || true
# pas de nohup : un signal ignoré au démarrage ne peut plus être intercepté par trap
setsid /usr/local/sbin/lab-service >/dev/null 2>&1 < /dev/null &
# 11.6 : mineur, relancé en boucle par un parent (au nom tiré au sort), par une chaîne de deux processus,
# ou par une boucle anonyme (variante)
cat > /usr/local/bin/mineur <<'EOF'
#!/bin/bash
while true; do sleep 5 & wait $!; done
EOF
chmod 755 /usr/local/bin/mineur
pkill -KILL -x 'veille-[0-9]{4}' || true
pkill -KILL -x 'relais-[0-9]{4}' || true
pkill -KILL -f '^bash -c while true; do /usr/local/bin/mineur' || true
pkill -KILL -x mineur || true
rm -f /usr/local/bin/veille-* /usr/local/bin/relais-*
sup=veille-$((RANDOM % 9000 + 1000)); rel=relais-$((RANDOM % 9000 + 1000))
case $v6 in
  0) printf '#!/bin/bash\nwhile true; do /usr/local/bin/mineur; sleep 2; done\n' > /usr/local/bin/$sup ;;
  1) printf '#!/bin/bash\nwhile true; do /usr/local/bin/mineur; sleep 2; done\n' > /usr/local/bin/$rel
     printf '#!/bin/bash\nwhile true; do /usr/local/bin/%s; sleep 2; done\n' $rel > /usr/local/bin/$sup ;;
esac
chmod 755 /usr/local/bin/veille-* /usr/local/bin/relais-* 2>/dev/null || true
if [ "$v6" = 2 ]; then
  su -s /bin/bash intrus -c "setsid bash -c 'while true; do /usr/local/bin/mineur; sleep 2; done' >/dev/null 2>&1 < /dev/null &"
else
  su -s /bin/bash intrus -c "setsid /usr/local/bin/$sup >/dev/null 2>&1 < /dev/null &"
fi
# 11.7 : un export à mettre en pause (attente sans processus enfant)
cat > /usr/local/bin/export-nuit <<'EOF'
#!/bin/bash
f=/tmp/.export-nuit.$$; mkfifo "$f"; exec 9<> "$f"; rm -f "$f"
while true; do read -t 3 -u 9 || true; done
EOF
chmod 755 /usr/local/bin/export-nuit
pkill -KILL -x export-nuit || true
su -s /bin/bash etudiant -c 'setsid /usr/local/bin/export-nuit >/dev/null 2>&1 < /dev/null &'
# 11.8 : un script que thomas devra pouvoir lancer en root
mkuser thomas
cat > /usr/local/sbin/relance-boutique <<'EOF'
#!/bin/bash
echo "$(date +%T) relance de la boutique demandée par ${SUDO_USER:-$USER}" >> /var/log/relance-boutique.log
echo "Boutique relancée."
EOF
chown root:root /usr/local/sbin/relance-boutique; chmod 755 /usr/local/sbin/relance-boutique
# une règle invalide bloquerait tout sudo : on la retire (le bouton de réinitialisation sert de secours)
if [ -e /etc/sudoers.d/thomas ] && ! visudo -cqf /etc/sudoers.d/thomas; then rm -f /etc/sudoers.d/thomas; fi
sleep 1
emit PID "$(pgrep -x rogue-worker | head -n1)"
emit ROGUE_USER "$ru"
emit SVC_PID "$(pgrep -x lab-service | head -n1)"
# 11.6 : les processus qui relancent mineur (parent, grand-parent ou boucle anonyme)
emit SUP_PIDS "$({ pgrep -x "$sup"; pgrep -x "$rel"; pgrep -f '^bash -c while true; do /usr/local/bin/mineur'; } | sort -u | paste -sd' ')"
emit EXPORT_PID "$(pgrep -x export-nuit | head -n1)"
''',
        "exercises": [
            {"id": "11.1", "points": 4, "title": "Créer un sudoer",
             "ticket": {"from": "sophie", "body": "On accueille un stagiaire en administration système. Crée-lui un compte <code>stagiaire</code>, avec son dossier personnel, et donne-lui les droits d'administration : Léa le surveillera de près. Et pense qu'il devra pouvoir répondre à la question de sudo…"},
             "desc": "Le compte <code>stagiaire</code> existe avec son dossier personnel, peut lancer n'importe quelle commande avec <code>sudo</code>, et a un mot de passe.",
             "hints": ["Sous Ubuntu, être membre d'un certain groupe suffit pour utiliser sudo : regardez les groupes de votre propre compte avec <code>id</code>. Un compte créé par <code>useradd</code> n'a pas de mot de passe utilisable.",
                       "<code>usermod -aG</code> pour le groupe ; <code>sudo passwd stagiaire</code> pour lui définir un mot de passe. Vérifiez avec <code>sudo -l -U stagiaire</code>."],
             "checks": [
                 ('id stagiaire', "L'utilisateur stagiaire n'existe pas."),
                 ('test -d /home/stagiaire', "stagiaire n'a pas de dossier personnel."),
                 (r'''sudo -l -U stagiaire 2>/dev/null | grep -qE '\(ALL( : ALL)?\) (NOPASSWD: )?ALL' ''', "stagiaire n'a pas le droit de lancer toutes les commandes avec sudo."),
                 (r'''[ "$(passwd -S stagiaire | awk '{print $2}')" = P ]''', "stagiaire n'a pas de mot de passe utilisable : sans lui, il ne pourra jamais répondre à la question de sudo."),
             ]},
            {"id": "11.2", "points": 3, "title": "Enquête",
             "ticket": {"from": "lea", "body": "Le serveur est lent depuis ce matin et un processus <code>rogue-worker</code> que je ne connais pas tourne dessus. Trouve-moi son PID et qui l'a lancé, avant qu'on décide quoi en faire."},
             "desc": "Dans <code>~/rogue.txt</code>, une seule ligne : le <strong>PID</strong> de <code>rogue-worker</code> puis l'<strong>utilisateur</strong> qui l'a lancé (ex. <code>1234 bob</code>).",
             "hints": ["<code>ps</code> affiche tous les processus avec leur propriétaire ; il reste à trouver la bonne ligne.",
                       "Dans <code>ps aux</code>, USER est la 1<sup>re</sup> colonne et PID la 2<sup>e</sup> ; <code>pgrep</code> donne directement le PID d'un nom. N'écrivez que les deux mots demandés."],
             "checks": [
                 ('[ -n "$LAB_PID" ]', "Le processus de l'exercice n'a pas démarré : rechargez la page."),
                 (r'''[ "$(grep -c '[^[:space:]]' $H/rogue.txt)" -eq 1 ] && [ "$(wc -w < $H/rogue.txt)" -eq 2 ]''', "~/rogue.txt doit contenir une seule ligne de deux mots : le PID, puis l'utilisateur (ex. 1234 bob)."),
                 (r'''read -r p u < <(grep '[^[:space:]]' $H/rogue.txt); [ "$p" = "$LAB_PID" ]''', "Le PID indiqué n'est pas celui de rogue-worker (s'il a redémarré entre-temps, vérifiez son PID actuel)."),
                 (r'''read -r p u < <(grep '[^[:space:]]' $H/rogue.txt); [ -n "$LAB_ROGUE_USER" ] && [ "$u" = "$LAB_ROGUE_USER" ]''', "L'utilisateur indiqué n'est pas celui qui a lancé rogue-worker."),
             ]},
            {"id": "11.3", "points": 4, "title": "Arrêter le processus",
             "ticket": {"from": "lea", "body": "Pas de doute, ce <code>rogue-worker</code> n'a rien à faire là. Arrête-le, mais proprement : on lui laisse une chance de se terminer correctement, pas de <code>kill -9</code>."},
             "desc": "<code>rogue-worker</code> ne tourne plus, et il a pu se terminer proprement (son journal <code>/var/log/rogue.log</code> le confirme).",
             "hints": ["Ce processus appartient à un autre utilisateur : il faut les droits d'administration pour lui envoyer un signal.",
                       "Relisez le tableau des signaux : sans option, <code>kill</code> envoie le signal qui laisse au programme le temps de faire le ménage ; <code>-9</code> ne lui laisse aucune chance."],
             "checks": [
                 ('[ -n "$LAB_PID" ]', "Le processus de l'exercice n'a pas démarré : rechargez la page."),
                 ('! pgrep -x rogue-worker >/dev/null', "rogue-worker tourne encore."),
                 ('grep -q "arrêt propre" /var/log/rogue.log', "rogue-worker a été arrêté brutalement, sans pouvoir se terminer proprement (son journal ne mentionne aucun arrêt propre). Relancez-le avec « Réinitialiser les fichiers de cette étape », puis recommencez avec le bon signal."),
             ]},
            {"id": "11.4", "points": 3, "title": "Processus gentil",
             "ticket": {"from": "thomas", "body": "Je dois lancer un long calcul en tâche de fond sans ralentir la boutique. Tu peux me montrer comment le démarrer avec une priorité réduite ? On va tester avec un <code>sleep 1000</code>."},
             "desc": "Lancez <code>sleep 1000</code> en arrière-plan avec une gentillesse (<em>niceness</em>) de <code>10</code>, et laissez-le tourner.",
             "hints": ["La commande qui lance un programme avec une priorité réduite porte un nom anglais qui veut dire « gentil » ; <code>&amp;</code> met la commande en arrière-plan.",
                       "Elle prend l'option <code>-n</code> suivie de la gentillesse, puis la commande à lancer. Vérifiez avec <code>ps -o pid,ni,cmd -C sleep</code>."],
             "checks": [
                 ('ps -o ni=,user=,args= -C sleep | awk \'$1 == 10 && $2 == "etudiant" && $4 == 1000\' | grep -q .', "Aucun « sleep 1000 » lancé par etudiant avec une niceness de 10 n'est en cours."),
             ]},
            {"id": "11.5", "points": 4, "title": "Recharger un service",
             "ticket": {"from": "thomas", "body": "J'ai modifié la configuration de <code>lab-service</code>. Il faut qu'il la relise, mais surtout pas de redémarrage : il sert des clients en ce moment même."},
             "desc": "Le service <code>lab-service</code> (lancé par root) relit sa configuration à chaud quand il reçoit un signal précis : sa documentation (<code>lab-service --aide</code>) dit lequel. Faites-le recharger <strong>sans l'arrêter</strong>. Son journal est <code>/var/log/lab-service.log</code>.",
             "hints": ["Tous les services ne suivent pas la convention du cours : lisez d'abord la documentation du service. Un signal qu'il n'intercepte pas l'arrêterait.",
                       "<code>kill</code> accepte le nom du signal en option (<code>kill -l</code> les liste tous) ; le processus appartient à root, et <code>pgrep</code> donne son PID."],
             "checks": [
                 ('[ -n "$LAB_SVC_PID" ] && kill -0 "$LAB_SVC_PID"', "lab-service ne tourne plus : il fallait le recharger, pas l'arrêter (rechargez la page pour le relancer)."),
                 ('grep -q "rechargée" /var/log/lab-service.log', "Le journal n'indique aucun rechargement."),
             ]},
            {"id": "11.6", "points": 5, "title": "Le processus qui renaît",
             "ticket": {"from": "lea", "body": "Un processus <code>mineur</code> lancé par intrus mange nos ressources. J'ai beau le tuer, il revient quelques secondes plus tard avec un autre PID ! Débarrasse-nous-en pour de bon."},
             "desc": "Plus aucun processus <code>mineur</code>, ni rien qui le relance ; et cela doit durer.",
             "hints": ["Si un processus revient avec un nouveau PID, c'est que quelqu'un le relance : regardez son processus parent (la colonne PPID de <code>ps</code>, ou l'arbre de <code>pstree -p</code>).",
                       "<code>ps -o pid,ppid,user,cmd -C mineur</code>, puis <code>ps -o pid,ppid,user,args -p</code> sur le PPID, et ainsi de suite en remontant (le parent peut lui-même être relancé par un autre processus, ou ne pas avoir de nom parlant). Arrêtez tous ceux qui relancent, puis mineur, avec sudo : ils appartiennent à intrus."],
             "checks": [
                 ('[ -n "$LAB_SUP_PIDS" ]', "Les processus de l'exercice n'ont pas démarré : rechargez la page."),
                 ('pgrep -x mineur >/dev/null && exit 1; for p in $LAB_SUP_PIDS; do kill -0 "$p" 2>/dev/null && exit 1; done; exit 0', "mineur tourne encore, ou ce qui le relance est toujours là."),
                 ('sleep 3; ! pgrep -x mineur >/dev/null', "mineur est revenu quelques secondes plus tard : quelque chose le relance encore."),
             ]},
            {"id": "11.7", "points": 4, "title": "Mettre en pause",
             "ticket": {"from": "thomas", "body": "Le traitement <code>export-nuit</code> a démarré en pleine journée et ralentit la boutique. Ne le tue surtout pas, il a déjà fait la moitié du travail : <strong>mets-le en pause</strong>, je le relancerai ce soir."},
             "desc": "<code>export-nuit</code> est suspendu : il n'est pas arrêté, le même processus doit pouvoir reprendre plus tard.",
             "hints": ["Il existe un signal qui gèle un processus sans le terminer, et un autre qui le fait repartir : <code>kill -l</code> les liste tous (cherchez STOP et CONT).",
                       "<code>kill</code> avec le signal de pause, sur le PID d'export-nuit ; la colonne STAT de <code>ps</code> affiche alors <code>T</code>."],
             "checks": [
                 ('[ -n "$LAB_EXPORT_PID" ]', "Le processus de l'exercice n'a pas démarré : rechargez la page."),
                 ('kill -0 "$LAB_EXPORT_PID" 2>/dev/null', "export-nuit ne tourne plus : il fallait le mettre en pause, pas l'arrêter (« Réinitialiser les fichiers de cette étape » le relance)."),
                 ('ps -o stat= -p "$LAB_EXPORT_PID" | grep -q "^T"', "export-nuit tourne toujours : il n'est pas en pause."),
             ]},
            {"id": "11.8", "points": 5, "title": "Déléguer un seul droit",
             "ticket": {"from": "sophie", "body": "Thomas doit pouvoir relancer la boutique avec <code>/usr/local/sbin/relance-boutique</code>, qui doit tourner en root. Mais je ne veux pas lui donner tous les droits : cette commande-là, et <strong>rien d'autre</strong>. Et sans lui demander de mot de passe, c'est pour les astreintes."},
             "desc": "<code>thomas</code> peut lancer <code>/usr/local/sbin/relance-boutique</code> avec <code>sudo</code>, sans mot de passe ; il ne peut lancer aucune autre commande avec sudo ; la configuration de sudo reste valide.",
             "hints": ["Une règle sudo peut viser une seule commande, par son chemin absolu, et dispenser de mot de passe. On l'écrit dans un fichier de <code>/etc/sudoers.d</code> avec <code>visudo</code>, qui vérifie la syntaxe (relisez le cours).",
                       "<code>sudo visudo -f /etc/sudoers.d/thomas</code> ; format : <code>utilisateur machine=(compte cible) NOPASSWD: /chemin/commande</code>. Vérifiez avec <code>sudo -l -U thomas</code>."],
             "checks": [
                 ("! visudo -c 2>&1 | grep -qiE 'syntax error|parse error'", "La configuration de sudo contient une erreur de syntaxe : corrigez-la avec sudo visudo -f (si sudo ne répond plus, « Réinitialiser les fichiers de cette étape » retire /etc/sudoers.d/thomas)."),
                 ("! visudo -c 2>&1 | grep -q 'bad permissions'", "Un fichier de /etc/sudoers.d n'a pas les droits attendus (0440) : sudo visudo -c le signale."),
                 ('run_as thomas "sudo -n /usr/local/sbin/relance-boutique" >/dev/null', "thomas ne peut pas lancer /usr/local/sbin/relance-boutique avec sudo sans mot de passe."),
                 ('! run_as thomas "sudo -n /usr/bin/id" >/dev/null 2>&1 && ! run_as thomas "sudo -n /bin/bash -c true" >/dev/null 2>&1', "thomas peut lancer d'autres commandes que relance-boutique avec sudo."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    12: {
        "title": "Cas pratique : système familial",
        "description": "Mettre en œuvre utilisateurs, groupes et permissions sur un cas concret, et enquêter sur des droits trop ouverts.",
        "lesson": """<h3>Cas pratique</h3><p>Vous installez Linux pour une famille : <strong>papa</strong>, <strong>maman</strong>, <strong>fils</strong>, <strong>fille</strong>, et un compte <strong>invite</strong>.</p><ul><li>Chacun a un compte avec un dossier <code>Travail</code> et <code>Bazar</code> dans son dossier personnel, qui lui appartiennent.</li><li>Un dossier <code>/home/famille</code> partagé par les 4 membres.</li><li>Un dossier <code>/home/parents-only</code> réservé aux parents.</li><li>L'invité n'a accès à rien de tout ça, ni aux dossiers personnels.</li></ul><div class="tip">Ce sont les <strong>accès réels</strong> qui sont vérifiés (en se connectant en tant que chaque utilisateur), pas seulement les chiffres de <code>chmod</code>.</div><h3>Rappels utiles</h3><ul><li><code>sudo -u carla mkdir /home/carla/Photos</code> crée un dossier au nom de carla ; <code>sudo -u carla ls /srv</code> teste ce que carla peut voir.</li><li>Les droits d'un <strong>nouveau</strong> dossier personnel ne sont pas fixés par <code>useradd</code> lui-même, mais par un réglage de <code>/etc/login.defs</code> : ils dépendent donc de la distribution… et de ce qu'en a fait l'administrateur précédent.</li><li>Pour atteindre un dossier, il faut le droit <code>x</code> sur chaque dossier du chemin ; <code>r</code> ne sert qu'à lister. Un dossier en <code>710</code> se traverse pour les membres de son groupe, sans qu'ils puissent voir ce qu'il contient.</li><li><code>find</code> sait tester les droits avec <code>-perm</code> (voir <code>man find</code>).</li></ul><div class="tip"><strong>Recette</strong> (les boucles seront expliquées au jour 17) : pour répéter une commande sur plusieurs comptes, <code>for u in carla david; do sudo useradd -m -s /bin/bash $u; done</code>.</div>""",
        "setup": r'''
# Marc avait « ouvert » les dossiers personnels des nouveaux comptes, d'une façon tirée au sort
# (une seule fois : on ne défait pas une correction)
if [ ! -e $REF/homemode-12 ]; then
  v=${LAB_VARIANTE_12_5:-$((RANDOM % 3))}
  case $v in
    0) sed -i 's/^HOME_MODE.*/HOME_MODE\t0755/' /etc/login.defs ;;
    # sans HOME_MODE, useradd applique la UMASK (022) : dossiers en 755
    1) sed -i 's/^HOME_MODE.*/#HOME_MODE\t0750   # désactivé par Marc (trop restrictif pour le support)/' /etc/login.defs ;;
    # une « surcouche » de useradd, placée avant le vrai dans le PATH de root
    2) cat > /usr/local/sbin/useradd <<'EOF'
#!/bin/bash
# Surcouche de useradd (Marc) : dossiers personnels ouverts, « plus pratique pour le support »
/usr/sbin/useradd "$@" || exit
for a; do :; done
h=$(getent passwd "$a" | cut -d: -f6)
case $h in /home/?*) [ -d "$h" ] && chmod 755 "$h" ;; esac
exit 0
EOF
       chmod 755 /usr/local/sbin/useradd ;;
  esac
  touch $REF/homemode-12
fi
# 12.7 : la copie de l'ancien PC de la famille, avec des droits disparates
V=/srv/ancien-pc
rm -rf $V; mkdir -p $V/photos $V/papiers $V/jeux
fics=(photos/ete-2024.jpg photos/noel.jpg photos/anniversaire.png papiers/impots-2025.pdf papiers/banque.csv papiers/assurance.pdf jeux/sauvegarde.dat jeux/scores.txt)
modes=(600 640 644 604 660 664 400 444)
mapfile -t ms < <(shuf -e "${modes[@]}")
for i in "${!fics[@]}"; do echo "${fics[i]}" > $V/${fics[i]}; chmod ${ms[i]} $V/${fics[i]}; done
chmod 755 $V $V/photos $V/papiers $V/jeux
find $V -type f -perm -o=r | sort > $REF/ancien-pc-ouverts
''',
        "exercises": [
            {"id": "12.1", "points": 4, "title": "La famille",
             "ticket": {"from": "sophie", "body": "Un petit service perso, si tu as cinq minutes : j'installe un vieux PC pour la maison. Tu peux créer un compte pour chacun de nous quatre ? Chacun avec un dossier <code>Travail</code> et un dossier <code>Bazar</code>, les enfants insistent pour le deuxième."},
             "desc": "Créez <code>papa</code>, <code>maman</code>, <code>fils</code>, <code>fille</code>, avec leur dossier personnel. Chacun a <code>~/Travail</code> et <code>~/Bazar</code>, qui lui appartiennent.",
             "hints": ["Même méthode qu'au jour 10 pour chaque compte. Pour que Travail et Bazar appartiennent à chacun, créez-les en son nom (ou changez leur propriétaire après coup).",
                       "<code>sudo -u papa mkdir /home/papa/Travail</code> crée le dossier au nom de papa ; la recette du cours évite de tout taper quatre fois."],
             "checks": [
                 ('for u in papa maman fils fille; do id $u || exit 1; done', "Les 4 utilisateurs doivent exister."),
                 ('for u in papa maman fils fille; do for d in Travail Bazar; do [ "$(owner /home/$u/$d)" = $u ] || exit 1; done; done', "Chaque utilisateur doit avoir Travail et Bazar dans son dossier, lui appartenant."),
             ]},
            {"id": "12.2", "points": 3, "title": "Les groupes",
             "ticket": {"from": "sophie", "body": "Pour s'y retrouver, il faudrait un groupe pour les parents et un groupe pour les enfants. Évidemment, pas de mélange !"},
             "desc": "Les groupes <code>parents</code> (papa et maman seulement) et <code>enfants</code> (fils et fille seulement).",
             "hints": ["Même méthode qu'au jour 10 : créer le groupe, puis y ajouter chaque membre sans lui retirer ses autres groupes.",
                       "Vérifiez avec <code>getent group parents</code> et <code>getent group enfants</code> : chaque membre ne doit apparaître que dans le bon groupe."],
             "checks": [
                 ('getent group parents && getent group enfants', "Les groupes parents et enfants doivent exister."),
                 ('id -nG papa | grep -qw parents && id -nG maman | grep -qw parents && id -nG fils | grep -qw enfants && id -nG fille | grep -qw enfants', "Un membre de la famille n'est pas dans son groupe."),
                 ('! id -nG fils | grep -qw parents && ! id -nG fille | grep -qw parents && ! id -nG papa | grep -qw enfants && ! id -nG maman | grep -qw enfants', "Un enfant est dans le groupe parents, ou un parent dans le groupe enfants."),
             ]},
            {"id": "12.3", "points": 4, "title": "Espace commun",
             "ticket": {"from": "sophie", "body": "Il nous faut un dossier commun pour les photos de vacances : toute la famille peut y déposer des fichiers, et personne d'autre."},
             "desc": "Créez <code>/home/famille</code> (groupe <code>famille</code>) où les 4 membres peuvent créer des fichiers, et où les autres n'ont aucun droit.",
             "hints": ["Il faut un groupe qui rassemble les 4 membres, puis les mêmes réglages que pour le dossier d'équipe du jour 10.",
                       "Groupe propriétaire, droits complets pour le groupe, rien pour les autres ; le setgid rendra service pour les fichiers créés ensuite."],
             "checks": [
                 ('getent group famille && [ "$(stat -c %G /home/famille)" = famille ]', "/home/famille doit exister et appartenir au groupe famille."),
                 ('for u in papa maman fils fille; do run_as $u "touch /home/famille/.t-$u && rm -f /home/famille/.t-$u" || exit 1; done', "Un des membres de la famille ne peut pas créer de fichier dans /home/famille."),
                 ('[ "$(others /home/famille)" = "---" ]', "Les autres utilisateurs ont encore des droits sur /home/famille."),
             ]},
            {"id": "12.4", "points": 4, "title": "Espace parents",
             "ticket": {"from": "sophie", "body": "Et un dossier réservé aux parents, pour les papiers administratifs… et les idées de cadeaux de Noël. Les enfants ne doivent même pas pouvoir voir ce qu'il y a dedans."},
             "desc": "Créez <code>/home/parents-only</code> : papa et maman peuvent y écrire, les enfants ne peuvent même pas le lister, et les autres utilisateurs n'ont aucun droit.",
             "hints": ["Un groupe existe déjà pour les parents : c'est lui qui doit posséder le dossier.",
                       "Même schéma que l'espace commun, avec un autre groupe. Testez avec <code>sudo -u fils ls /home/parents-only</code>."],
             "checks": [
                 ('run_as papa "touch /home/parents-only/.t && rm -f /home/parents-only/.t" && run_as maman "touch /home/parents-only/.t && rm -f /home/parents-only/.t"', "papa et maman doivent pouvoir écrire dans /home/parents-only."),
                 ('! run_as fils "ls /home/parents-only" && ! run_as fille "ls /home/parents-only"', "Les enfants peuvent lister /home/parents-only."),
                 ('[ "$(others /home/parents-only)" = "---" ]', "Les autres utilisateurs ont encore des droits sur /home/parents-only."),
             ]},
            {"id": "12.5", "points": 5, "title": "Compte invité",
             "ticket": {"from": "sophie", "body": "Dernière chose : un compte invité pour la baby-sitter. Il ne doit avoir accès à aucun de nos dossiers, ni communs, ni personnels. Et si je crée d'autres comptes plus tard, je ne veux pas avoir à y repenser à chaque fois."},
             "desc": "Créez <code>invite</code>. Il ne doit pouvoir lister ni <code>/home/famille</code>, ni <code>/home/parents-only</code>, ni le dossier personnel d'aucun membre de la famille. Les comptes créés à l'avenir ne doivent plus avoir un dossier personnel accessible à tous.",
             "hints": ["Testez en vous mettant à la place d'invite : <code>sudo -u invite ls /home/papa</code>. Puis regardez les droits des dossiers personnels avec <code>ls -l /home</code> : ceux de la famille sont-ils comme ceux d'alice ou de bob ?",
                       "Les droits des nouveaux dossiers personnels viennent du réglage <code>HOME_MODE</code> de <code>/etc/login.defs</code> (ou, s'il est absent, de sa <code>UMASK</code>)… à condition que <code>sudo useradd</code> lance bien le vrai useradd (<code>sudo sh -c 'command -v useradd'</code>). Marc a touché à l'un de ces maillons : corrigez-le, puis fermez les dossiers déjà créés."],
             "checks": [
                 ('id invite', "L'utilisateur invite n'existe pas."),
                 ('! run_as invite "ls /home/famille" && ! run_as invite "ls /home/parents-only"', "invite peut lister un dossier familial."),
                 ('for u in papa maman fils fille; do run_as invite "ls /home/$u" && exit 1; done; exit 0', "invite peut lister le dossier personnel d'un membre de la famille."),
                 (r'''u=lab-verif-$RANDOM; useradd -m -s /bin/bash "$u" >/dev/null 2>&1; m=$(stat -c %a "/home/$u" 2>/dev/null); userdel -r "$u" >/dev/null 2>&1; [ -n "$m" ] && (( (8#$m & 7) == 0 ))''', "Un compte créé maintenant avec useradd -m aurait encore un dossier personnel ouvert aux autres utilisateurs : trouvez ce qui fixe les droits des nouveaux dossiers personnels."),
             ]},
            {"id": "12.6", "points": 5, "title": "Le Bazar du frère et de la sœur",
             "ticket": {"from": "sophie", "body": "Nouvelle demande des enfants : le fils veut pouvoir fouiller dans le <code>Bazar</code> de sa sœur (elle est d'accord, c'est leur coin à jeux). Mais seulement le Bazar : le reste du dossier de la fille reste privé, et les parents comme l'invitée n'ont pas à y mettre le nez."},
             "desc": "<code>fils</code> peut lister <code>/home/fille/Bazar</code>, mais pas <code>/home/fille</code> ; ni les parents ni <code>invite</code> ne peuvent lister <code>/home/fille/Bazar</code> ; <code>fille</code> reste propriétaire de son Bazar et peut toujours y écrire.",
             "hints": ["Pour atteindre <code>Bazar</code>, le fils doit pouvoir <strong>traverser</strong> <code>/home/fille</code> (droit <code>x</code>) sans pouvoir le lister (droit <code>r</code>). Un groupe existant rassemble exactement le frère et la sœur.",
                       "Donnez au groupe des enfants le droit de traverser <code>/home/fille</code> (et rien de plus), et le droit de lister et traverser <code>Bazar</code>. Testez avec <code>sudo -u fils ls /home/fille/Bazar</code> et <code>sudo -u papa ls /home/fille/Bazar</code>."],
             "checks": [
                 ('run_as fils "ls /home/fille/Bazar"', "fils ne peut pas lister /home/fille/Bazar."),
                 ('! run_as fils "ls /home/fille"', "fils peut lister tout le dossier personnel de sa sœur : seul Bazar doit lui être accessible."),
                 ('! run_as papa "ls /home/fille/Bazar" && ! run_as maman "ls /home/fille/Bazar"', "Les parents peuvent lister /home/fille/Bazar."),
                 ('! run_as invite "ls /home/fille/Bazar"', "invite peut lister /home/fille/Bazar."),
                 ('[ "$(owner /home/fille/Bazar)" = fille ] && run_as fille "touch /home/fille/Bazar/.t && rm -f /home/fille/Bazar/.t"', "fille doit rester propriétaire de son Bazar et pouvoir y écrire."),
             ]},
            {"id": "12.7", "points": 4, "title": "Les fichiers trop ouverts",
             "ticket": {"from": "lea", "body": "Sophie a recopié les fichiers de son ancien PC dans <code>/srv/ancien-pc</code>. Avant de tout remettre sur la nouvelle machine, je voudrais savoir lesquels sont lisibles par <strong>n'importe qui</strong>. Il y a des papiers de banque là-dedans…"},
             "desc": "La liste des fichiers de <code>/srv/ancien-pc</code> dont les « autres » ont le droit de lecture, chemins complets, un par ligne, dans <code>~/fichiers-ouverts.txt</code>.",
             "hints": ["<code>find</code> sait tester les bits de permission avec <code>-perm</code> ; attention, <code>-perm 644</code> ne trouve que les fichiers dont les droits sont <strong>exactement</strong> 644.",
                       "Avec un tiret devant, <code>-perm</code> veut dire « au moins ces bits-là » : il suffit de tester le bit de lecture des autres (4 dans la dernière triade, ou <code>o=r</code>)."],
             "checks": [
                 ('test -s $H/fichiers-ouverts.txt', "~/fichiers-ouverts.txt est absent ou vide."),
                 ('setcmp $H/fichiers-ouverts.txt "cat $REF/ancien-pc-ouverts"', "La liste ne correspond pas aux fichiers lisibles par les autres (il en manque, ou il y en a en trop)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    13: {
        "title": "Installer des programmes",
        "description": "Gérer les paquets avec apt et dpkg : installer, interroger, vérifier, désinstaller, y compris des paquets livrés hors dépôt.",
        "lesson": """<div class="tip">Les exercices marqués « Internet » ont besoin d'un accès à Internet depuis le lab ; les autres utilisent des paquets livrés dans <code>/srv/paquets</code> et fonctionnent sans réseau.</div><h3>apt : le gestionnaire de paquets</h3><table class="lesson-table"><tr><th>Commande</th><th>Action</th></tr><tr><td><code>sudo apt update</code></td><td>Télécharger la liste des paquets disponibles (vide au départ dans ce lab)</td></tr><tr><td><code>apt search mot</code></td><td>Chercher un paquet</td></tr><tr><td><code>sudo apt install p</code></td><td>Installer, avec ses dépendances</td></tr><tr><td><code>sudo apt remove p</code></td><td>Désinstaller le programme</td></tr><tr><td><code>sudo apt purge p</code></td><td>Désinstaller le programme <strong>et</strong> ses fichiers de configuration</td></tr><tr><td><code>sudo apt autoremove</code></td><td>Retirer les dépendances installées automatiquement dont plus rien n'a besoin</td></tr></table><h3>dpkg : la base des paquets installés</h3><ul><li><code>dpkg -l</code> — lister les paquets connus, avec leur état : <code>ii</code> installé, <code>rc</code> retiré mais configuration conservée</li><li><code>dpkg -s paquet</code> — état et informations d'un paquet</li><li><code>dpkg -L paquet</code> — fichiers installés par un paquet</li><li><code>dpkg -S /chemin/fichier</code> — quel paquet a installé ce fichier ?</li><li><code>sudo dpkg -i fichier.deb</code> — installer un paquet livré sous forme de fichier. Contrairement à apt, dpkg ne va <strong>pas</strong> chercher les dépendances : si elles manquent, le paquet reste à moitié installé.</li></ul><p><code>man dpkg</code> décrit bien d'autres actions : lire le contenu d'un <code>.deb</code> avant de l'installer, vérifier l'intégrité des fichiers installés…</p><div class="tip">Sur Ubuntu récent, <code>/bin</code> est un lien vers <code>/usr/bin</code> : un même programme a donc deux chemins.</div><h3>Télécharger</h3><pre>wget -O fichier.html https://exemple.org<br>curl -o fichier.html https://exemple.org</pre><p>L'historique d'apt est dans <code>/var/log/apt/history.log</code>.</p>""",
        "setup": r'''
PK=/srv/paquets
rm -rf $PK; mkdir -p $PK $H/paquets
B=$(mktemp -d)
# mkdeb NOM VERSION DÉPENDANCES : construit $PK/NOM_VERSION_all.deb à partir de $B/NOM (fichiers déjà en place)
mkdeb() {
  local d=$B/$1
  mkdir -p $d/DEBIAN
  { echo "Package: $1"; echo "Version: $2"; echo "Architecture: all"; echo "Maintainer: Prestataire CS <support@cs-outils.example>"
    if [ -n "$3" ]; then echo "Depends: $3"; fi
    echo "Description: outils du prestataire ($1)"; } > $d/DEBIAN/control
  if [ -d $d/etc ]; then find $d/etc -type f | sed "s|^$d||" > $d/DEBIAN/conffiles; fi
  dpkg-deb --build --root-owner-group $d $PK/${1}_${2}_all.deb >/dev/null
  rm -rf $d
}
dpkg -P cs-outils cs-rapport cs-base cs-commun cs-ancien cs-supervision >/dev/null 2>&1 || true
# 13.5 : un paquet à inspecter avant de l'installer
bin=cs-$(shuf -n1 -e inventaire etiquettes synchro releves)
mkdir -p $B/cs-outils/usr/bin $B/cs-outils/etc
printf '#!/bin/sh\necho "Outil %s du prestataire"\n' "$bin" > $B/cs-outils/usr/bin/$bin; chmod 755 $B/cs-outils/usr/bin/$bin
echo "serveur=cs.example" > $B/cs-outils/etc/cs-outils.conf
mkdeb cs-outils 1.$((RANDOM % 8 + 2)) ""
emit BIN "/usr/bin/$bin"
# 13.6 : une dépendance livrée en plusieurs versions (dépendance et versions tirées au sort)
v=${LAB_VARIANTE_13_6:-$((RANDOM % 3))}
case $v in
  0) dep=cs-base; min=1.2; livr="cs-base:1.0 cs-base:1.3" ;;
  1) dep=cs-base; min=2.0; livr="cs-base:1.3 cs-base:2.1" ;;
  2) dep=cs-commun; min=1.1; livr="cs-commun:1.0 cs-commun:1.4 cs-base:1.3" ;;
esac
for l in $livr; do p=${l%%:*}; ver=${l#*:}; mkdir -p $B/$p/usr/share/$p; echo "$p $ver" > $B/$p/usr/share/$p/VERSION; mkdeb $p $ver ""; done
mkdir -p $B/cs-rapport/usr/bin; printf '#!/bin/sh\necho "Rapport du prestataire"\n' > $B/cs-rapport/usr/bin/cs-rapport; chmod 755 $B/cs-rapport/usr/bin/cs-rapport
mkdeb cs-rapport 2.0 "$dep (>= $min)"
emit DEP "$dep"
emit DEPMIN "$min"
# 13.7 : un vieux paquet installé, avec sa configuration
mkdir -p $B/cs-ancien/usr/bin $B/cs-ancien/etc
printf '#!/bin/sh\necho "Ancien outil"\n' > $B/cs-ancien/usr/bin/cs-ancien; chmod 755 $B/cs-ancien/usr/bin/cs-ancien
echo "licence=expiree" > $B/cs-ancien/etc/cs-ancien.conf
mkdeb cs-ancien 0.9 ""
dpkg -i $PK/cs-ancien_0.9_all.deb >/dev/null
rm -f $PK/cs-ancien_0.9_all.deb
# 13.9 : un paquet installé dont un fichier a été retouché à la main
mkdir -p $B/cs-supervision/usr/bin $B/cs-supervision/usr/share/cs-supervision
for f in cs-sonde cs-alerte cs-bilan; do printf '#!/bin/sh\necho "%s"\n' "$f" > $B/cs-supervision/usr/bin/$f; chmod 755 $B/cs-supervision/usr/bin/$f; done
echo "seuil=90" > $B/cs-supervision/usr/share/cs-supervision/seuils.txt
mkdeb cs-supervision 1.0 ""
dpkg -i $PK/cs-supervision_1.0_all.deb >/dev/null
modif=$(shuf -n1 -e /usr/bin/cs-sonde /usr/bin/cs-alerte /usr/bin/cs-bilan /usr/share/cs-supervision/seuils.txt)
echo "# modifié à la main" >> $modif
emit MODIF "$modif"
rm -rf $B
chmod -R a+rX $PK
# 13.2 : une commande installée, tirée au sort
q=$(shuf -n1 -e /usr/bin/pgrep /usr/bin/namei /usr/bin/lsof /usr/bin/pstree /usr/bin/xxd /usr/bin/less)
echo "De quel paquet vient $q ?" > $H/paquets/question.txt
emit PKG "$(dpkg -S $q | cut -d: -f1)"
# 13.8 : une commande que dpkg ne connaît que sous son chemin d'origine, dans /bin
cands=()
for c in ps kill ls cat ping ss ip netstat fuser zcat dmesg; do
  if ! dpkg -S /usr/bin/$c >/dev/null 2>&1 && p=$(dpkg -S /bin/$c 2>/dev/null | cut -d: -f1) && [ -n "$p" ] && [ "$p" != "$c" ]; then cands+=("$c:$p"); fi
done
x=${cands[RANDOM % ${#cands[@]}]}
echo "De quel paquet vient la commande ${x%%:*} ? (dpkg -S \$(which ${x%%:*}) répond « no path found »)" > $H/paquets/question-bin.txt
own $H/paquets
emit PKGBIN "${x#*:}"
''',
        "exercises": [
            {"id": "13.1", "points": 3, "title": "Installer un programme",
             "ticket": {"from": "julien", "body": "Léa affiche toujours l'arborescence des dossiers avec une jolie commande <code>tree</code>, mais chez moi elle n'existe pas. Tu peux l'installer ?"},
             "desc": "(Internet) Installez le programme <code>tree</code>, puis essayez <code>tree ~</code>.",
             "hints": ["Dans ce lab, la liste des paquets disponibles est vide au départ : apt doit d'abord la télécharger avant de pouvoir installer quoi que ce soit.",
                       "Mettez à jour la liste des paquets, puis installez, les deux avec sudo (voir le tableau du cours)."],
             "checks": [
                 ('command -v tree', "tree n'est pas installé."),
             ]},
            {"id": "13.2", "points": 3, "title": "D'où vient ce fichier ?",
             "ticket": {"from": "lea", "body": "On prépare la mise à jour du serveur, et je veux savoir de quel paquet vient la commande notée dans <code>~/paquets/question.txt</code>, pour vérifier qu'elle ne sera pas supprimée par erreur."},
             "desc": "Le nom du paquet qui a installé le fichier indiqué dans <code>~/paquets/question.txt</code>, dans <code>~/paquet.txt</code>.",
             "hints": ["<code>dpkg</code> tient la liste de tous les fichiers installés par chaque paquet, et sait faire la recherche dans l'autre sens.",
                       "L'option de recherche de dpkg est dans le cours ; le nom du paquet est avant les deux-points."],
             "checks": [
                 ('[ "$(ans $H/paquet.txt)" = "$LAB_PKG" ]', "Ce n'est pas le bon paquet."),
             ]},
            {"id": "13.3", "points": 3, "title": "Télécharger une page",
             "ticket": {"from": "thomas", "body": "J'ai besoin d'une copie de la page d'accueil de <code>example.com</code> pour mes tests d'intégration. Tu peux la télécharger depuis le serveur ?"},
             "desc": "(Internet) Téléchargez <code>https://example.com</code> dans <code>~/telechargements/page.html</code>.",
             "hints": ["Le dossier de destination doit exister avant le téléchargement.",
                       "<code>wget</code> et <code>curl</code> ont chacun une option pour choisir le fichier de sortie (voir le cours)."],
             "checks": [
                 ('grep -qi "example domain" $H/telechargements/page.html', "~/telechargements/page.html est absent ou ne contient pas la page d'example.com."),
             ]},
            {"id": "13.4", "points": 3, "title": "Installer puis désinstaller",
             "ticket": {"from": "julien", "body": "Quelqu'un m'a parlé d'une vache qui parle dans le terminal ! Tu peux me montrer ? Mais Léa veut qu'on la désinstalle juste après : pas de gadgets sur un serveur."},
             "desc": "(Internet) Installez le paquet <code>cowsay</code>, essayez <code>/usr/games/cowsay Bonjour</code>, puis désinstallez-le.",
             "hints": ["Installez-le comme <code>tree</code>, puis cherchez dans le tableau du cours la commande apt qui désinstalle.",
                       "L'historique d'apt garde la trace de l'installation ; <code>dpkg -s cowsay</code> dit s'il est encore installé."],
             "checks": [
                 ('grep -q "cowsay" /var/log/apt/history.log', "L'historique apt ne montre aucune installation de cowsay."),
                 ('! dpkg -s cowsay 2>/dev/null | grep -q "^Status: install ok installed"', "cowsay est toujours installé."),
             ]},
            {"id": "13.5", "points": 4, "title": "Le paquet du prestataire",
             "ticket": {"from": "thomas", "body": "Le prestataire nous a livré son outil sous forme de paquet : <code>/srv/paquets/cs-outils_*.deb</code>. Avant de l'installer, Léa veut savoir quel programme il va déposer dans <code>/usr/bin</code>. Ensuite, installe-le."},
             "desc": "Dans <code>~/contenu-deb.txt</code>, le chemin complet du programme que <code>cs-outils</code> installe dans <code>/usr/bin</code> (lu dans le paquet) ; puis le paquet <code>cs-outils</code> installé.",
             "hints": ["<code>dpkg</code> sait lire un fichier <code>.deb</code> sans l'installer : lister son contenu (<em>contents</em>) ou afficher ses informations. Cherchez dans <code>man dpkg-deb</code>.",
                       "<code>dpkg -c</code> liste les fichiers d'un <code>.deb</code> ; <code>sudo dpkg -i</code> installe un paquet local."],
             "checks": [
                 ('[ "/$(grep -oE "usr/bin/[A-Za-z0-9._-]+" $H/contenu-deb.txt | head -n1)" = "$LAB_BIN" ]', "~/contenu-deb.txt ne contient pas le chemin du programme que cs-outils installe dans /usr/bin."),
                 ('dpkg-query -W -f="\\${Status}" cs-outils 2>/dev/null | grep -q "install ok installed"', "Le paquet cs-outils n'est pas installé."),
             ]},
            {"id": "13.6", "points": 5, "title": "Dépendance manquante",
             "ticket": {"from": "lea", "body": "Le prestataire a aussi livré <code>cs-rapport</code>, dans <code>/srv/paquets</code>. Quand on l'installe avec <code>dpkg</code>, ça échoue. Fais aboutir l'installation. Attention, il a livré plusieurs versions de certaines choses…"},
             "desc": "Les paquets <code>cs-rapport</code> et sa dépendance sont complètement installés (état <code>ii</code> dans <code>dpkg -l</code>), dans une version qui satisfait la dépendance.",
             "hints": ["Lisez le message d'erreur de dpkg : il nomme ce qui manque, et la version exigée. <code>dpkg -I</code> affiche aussi les dépendances d'un <code>.deb</code>.",
                       "Installez la bonne version de la dépendance, puis terminez la configuration de cs-rapport (en le réinstallant, ou avec <code>sudo dpkg --configure -a</code>)."],
             "checks": [
                 ('[ -n "$LAB_DEP" ] && dpkg-query -W -f="\\${Status}" "$LAB_DEP" 2>/dev/null | grep -q "install ok installed" && dpkg --compare-versions "$(dpkg-query -W -f="\\${Version}" "$LAB_DEP")" ge "$LAB_DEPMIN"', "La dépendance de cs-rapport n'est pas installée dans une version qui la satisfait : relisez ce qu'exige cs-rapport (dpkg -I)."),
                 ('dpkg-query -W -f="\\${Status}" cs-rapport 2>/dev/null | grep -q "install ok installed"', "cs-rapport n'est pas complètement installé : relisez le message de dpkg et son état dans dpkg -l."),
             ]},
            {"id": "13.7", "points": 4, "title": "Désinstaller complètement",
             "ticket": {"from": "lea", "body": "Le vieux paquet <code>cs-ancien</code> n'a plus de licence. Désinstalle-le <strong>complètement</strong> : je ne veux plus en voir aucune trace, configuration comprise."},
             "desc": "<code>cs-ancien</code> n'est plus installé, sa configuration (<code>/etc/cs-ancien.conf</code>) a disparu, et <code>dpkg</code> n'en garde plus aucune trace.",
             "hints": ["Après une simple désinstallation, <code>dpkg -l</code> affiche encore le paquet avec l'état <code>rc</code> : programme retiré, configuration conservée.",
                       "Le cours cite la commande apt qui retire aussi la configuration ; <code>dpkg</code> a une option équivalente."],
             "checks": [
                 ('! dpkg-query -W -f="\\${Status}" cs-ancien 2>/dev/null | grep -q " installed$"', "cs-ancien est toujours installé."),
                 ('! dpkg-query -W -f="\\${Status}" cs-ancien 2>/dev/null | grep -q "config-files"', "cs-ancien est désinstallé, mais dpkg garde encore sa configuration (état rc dans dpkg -l)."),
                 ('test ! -e /etc/cs-ancien.conf', "/etc/cs-ancien.conf existe encore."),
             ]},
            {"id": "13.8", "points": 5, "title": "« no path found »",
             "ticket": {"from": "lea", "body": "Je voulais savoir de quel paquet vient la commande notée dans <code>~/paquets/question-bin.txt</code>, mais <code>dpkg -S $(which …)</code> me répond « no path found ». Elle n'a été installée par aucun paquet ? Ça m'étonnerait…"},
             "desc": "Le nom du paquet qui a installé la commande indiquée dans <code>~/paquets/question-bin.txt</code>, dans <code>~/paquet-bin.txt</code>.",
             "hints": ["Relisez l'encadré du cours sur <code>/bin</code> : un même programme a deux chemins, mais dpkg ne connaît que celui sous lequel le paquet l'a installé.",
                       "Essayez <code>dpkg -S</code> avec le chemin sous <code>/bin</code>, ou avec un simple motif comme <code>bin/nom</code>."],
             "checks": [
                 ('[ "$(ans $H/paquet-bin.txt)" = "$LAB_PKGBIN" ]', "Ce n'est pas le paquet qui a installé cette commande."),
             ]},
            {"id": "13.9", "points": 5, "title": "Un fichier retouché ?",
             "ticket": {"from": "lea", "body": "Quelqu'un a modifié à la main un des fichiers installés par le paquet <code>cs-supervision</code>. Lequel ? Note-le-moi, puis remets le paquet d'aplomb (son <code>.deb</code> est dans <code>/srv/paquets</code>)."},
             "desc": "Le chemin complet du fichier modifié dans <code>~/fichier-modifie.txt</code> ; puis <code>cs-supervision</code> réinstallé, sans plus aucune différence avec ce que le paquet a livré.",
             "hints": ["<code>dpkg</code> garde une empreinte de chaque fichier qu'il installe et sait comparer les fichiers présents à ces empreintes : cherchez « verify » dans <code>man dpkg</code>.",
                       "<code>dpkg -V cs-supervision</code> signale les fichiers dont le contenu a changé (un <code>5</code> dans la 3<sup>e</sup> colonne) ; réinstallez ensuite le même <code>.deb</code> avec <code>sudo dpkg -i</code>."],
             "checks": [
                 ('[ "$(ans $H/fichier-modifie.txt)" = "$LAB_MODIF" ]', "~/fichier-modifie.txt ne contient pas le chemin complet du fichier modifié."),
                 ('dpkg-query -W -f="\\${Status}" cs-supervision 2>/dev/null | grep -q "install ok installed" && [ -z "$(dpkg -V cs-supervision 2>&1)" ]', "cs-supervision n'est pas remis d'aplomb : dpkg -V signale encore une différence."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    14: {
        "title": "Disques et systèmes de fichiers",
        "description": "Points de montage, /etc/fstab, occupation disque et ses pièges (fichiers cachés, creux, petits fichiers).",
        "lesson": r"""<h3>Disques et partitions</h3><ul><li>Chaque disque est un fichier de <code>/dev</code> : <code>/dev/sda</code> (SATA ou SCSI), <code>/dev/nvme0n1</code> (SSD NVMe), <code>/dev/vda</code> (disque de machine virtuelle). Les partitions ajoutent un numéro : <code>/dev/sda1</code>, <code>/dev/nvme0n1p2</code>.</li><li><code>lsblk</code> affiche l'arborescence des disques et partitions ; <code>blkid</code> affiche le <strong>type</strong> et l'identifiant unique (<strong>UUID</strong>) de chaque système de fichiers, y compris dans un fichier image.</li></ul><h3>Monter</h3><p>Un système de fichiers n'est accessible qu'une fois <strong>monté</strong> sur un dossier, le point de montage :</p><pre>sudo mount /dev/sdc1 /mnt/archives<br>sudo umount /mnt/archives<br>findmnt          # arbre de tout ce qui est monté, avec les options<br>df -h            # occupation de chaque système de fichiers</pre><p>Chaque montage a des <strong>options</strong> : <code>rw</code> ou <code>ro</code> (lecture seule), <code>noexec</code>, <code>nosuid</code>… <code>df</code>, <code>findmnt</code> et <code>mount</code> savent aussi afficher le <strong>type</strong> de chaque système de fichiers (ext4, xfs, vfat, tmpfs…) : cherchez l'option dans leur manuel.</p><h3>/etc/fstab</h3><p>Les montages automatiques au démarrage, un par ligne, en 6 champs :</p><pre># source                                    point      type  options           dump  pass<br>UUID=3f1c9a2e-8b7d-4c1e-9f0a-5d6e7b8c9d01   /srv/web   xfs   defaults,noatime  0     2<br>LABEL=ARCHIVES                              /archives  ext4  defaults          0     2</pre><ul><li><strong>source</strong> : préférez <code>UUID=</code> ou <code>LABEL=</code> (lus par <code>blkid</code>) à <code>/dev/sdb1</code> : le nom <code>sdX</code> dépend de l'ordre de détection des disques et peut changer d'un démarrage à l'autre.</li><li><strong>dump</strong> : presque toujours 0 ; <strong>pass</strong> : ordre de vérification au démarrage (1 pour la racine, 2 pour les autres, 0 pour jamais).</li><li>Un disque <strong>amovible</strong> absent au démarrage bloque le serveur en mode de secours… sauf si une option indique que son absence n'est pas grave : cherchez-la dans <code>man 5 fstab</code>.</li></ul><div class="tip">Avant de redémarrer, testez : <code>sudo findmnt --verify</code> analyse fstab, <code>sudo mount -a</code> monte tout ce qui ne l'est pas encore. Une erreur dans fstab peut empêcher le serveur de démarrer.</div><h3>Qui occupe la place ?</h3><pre>du -sh /home/*                # taille de chaque dossier personnel<br>du -h -d 1 /var | sort -h     # un seul niveau de profondeur, trié<br>du -x …                       # sans descendre dans les autres systèmes de fichiers</pre><ul><li><code>du</code> compte les <strong>blocs réellement occupés</strong> ; <code>ls -l</code> affiche la <strong>taille apparente</strong>. Un fichier <em>creux</em> (<em>sparse</em>, typique des images de machines virtuelles) peut annoncer 50 Go et n'occuper presque rien : comparez avec <code>du --apparent-size</code>.</li><li>Le joker <code>*</code> ignore les noms qui commencent par un point : <code>du -sh dossier/*</code> ne voit pas les dossiers cachés.</li><li>Les unités de <code>du -m</code> et <code>du -h</code> sont des mébioctets (Mio, 1 048 576 octets), arrondis au supérieur.</li><li><code>df -i</code> compte les <strong>inodes</strong> : chaque fichier en consomme un, même vide. Un disque peut être « plein » de petits fichiers alors qu'il lui reste des octets libres.</li></ul><div class="tip">Dans ce lab (un conteneur), on ne peut pas monter de vrai disque, et <code>lsblk</code> montre les disques de la machine hôte : on s'entraîne sur les outils d'analyse et sur la syntaxe de fstab.</div>""",
        "setup": r'''
# 14.1 : le point de montage à inventorier (variante tirée au sort)
v=${LAB_VARIANTE_14_1:-$((RANDOM % 4))}
pm=(/ /dev/shm /proc /dev/pts)
printf 'Inventaire du serveur - point de montage à relever : %s\n' "${pm[v]}" > $H/inventaire-montage.txt
chown etudiant:etudiant $H/inventaire-montage.txt
emit POINT "${pm[v]}"
D=/srv/data
rm -rf $D; mkdir -p $D
names=(photos videos musique documents backup projets)
big=${names[RANDOM % 6]}
for n in "${names[@]}"; do
  mkdir -p $D/$n; k=$((RANDOM % 5 + 1))
  for i in $(seq 1 $((RANDOM % 5 + 3))); do head -c $((k * 100))K /dev/urandom > $D/$n/f$i.bin; done
done
for i in $(seq 1 12); do head -c 400K /dev/urandom > $D/$big/extra$i.bin; done
chmod -R a+rX $D
emit BIGDIR "$big"
# 14.4 : image du disque USB de sauvegarde (système de fichiers ext4 à l'UUID aléatoire)
mkdir -p /srv/disques
img=/srv/disques/usb-sauvegarde.img
u=$(cat /proc/sys/kernel/random/uuid)
rm -f $img; truncate -s 8M $img
mkfs.ext4 -q -F -U "$u" $img >/dev/null 2>&1
chmod 644 $img
emit UUID "$u"
# 14.5 : un dossier caché occupe plus que tous les autres réunis
S=/srv/stockage
rm -rf $S; mkdir -p $S
for n in clients fournisseurs catalogue photos-produits factures; do
  mkdir -p $S/$n; head -c $(( (RANDOM % 4 + 2) * 1024 ))K /dev/urandom > $S/$n/donnees.bin
done
hid=".cache-$(rword)"
mkdir -p "$S/$hid"
for i in 1 2 3; do head -c 12M /dev/urandom > "$S/$hid/bloc$i.bin"; done
chmod -R a+rX $S
emit HIDDEN "$hid"
# 14.6 : images de machines virtuelles, dont deux fichiers creux
V=/srv/vm
rm -rf $V; mkdir -p $V
vms=(web-01.img bdd-01.raw cache-01.qcow2 ci-runner.img mail-01.raw)
vms=($(printf '%s\n' "${vms[@]}" | shuf))
truncate -s 4G $V/${vms[0]}; head -c 1M /dev/urandom | dd of=$V/${vms[0]} conv=notrunc status=none
truncate -s 2G $V/${vms[1]}; head -c 1M /dev/urandom | dd of=$V/${vms[1]} conv=notrunc status=none
sizes=($(shuf -i 6-14 -n 3))
for i in 0 1 2; do head -c ${sizes[i]}M /dev/urandom > $V/${vms[i + 2]}; done
real=$(for i in 0 1 2; do echo "${sizes[i]} ${vms[i + 2]}"; done | sort -n | tail -n1 | cut -d' ' -f2)
chmod -R a+rX $V
emit VMREAL "$real"
# 14.7 : un dossier de sessions rempli de petits fichiers
T=/srv/sessions
rm -rf $T; mkdir -p $T
apps=(boutique api-mobile intranet newsletter paiement)
apps=($(printf '%s\n' "${apps[@]}" | shuf))
mkdir -p $T/${apps[0]} && (cd $T/${apps[0]} && seq -f 'sess_%05g' 1 8000 | xargs touch)
mkdir -p $T/${apps[1]} && for i in 1 2 3; do head -c 3M /dev/urandom > $T/${apps[1]}/export-$i.dump; done
for a in "${apps[@]:2}"; do mkdir -p $T/$a && (cd $T/$a && seq -f 'sess_%05g' 1 $((RANDOM % 400 + 100)) | xargs touch); done
chmod -R a+rX $T
emit MANYFILES "${apps[0]}"
''',
        "exercises": [
            {"id": "14.1", "points": 3, "title": "Type de système de fichiers",
             "ticket": {"from": "lea", "body": "Pour l'inventaire du serveur, j'ai besoin du type de système de fichiers monté sur le point de montage que j'ai noté dans <code>~/inventaire-montage.txt</code>. Pas de devinette : je veux la valeur lue sur la machine."},
             "desc": "Écrivez le <strong>type</strong> du système de fichiers monté sur le point de montage indiqué dans <code>~/inventaire-montage.txt</code> dans <code>~/fs-type.txt</code>.",
             "hints": ["Plusieurs commandes de la partie « Monter » du cours savent afficher le type d'un système de fichiers : cherchez l'option dans leur manuel.", "<code>df -T</code> suivi du point de montage, ou <code>findmnt -n -o FSTYPE</code> suivi du point de montage."],
             "checks": [
                 ('[ -n "$LAB_POINT" ] && [ "$(ans $H/fs-type.txt)" = "$(df -T "$LAB_POINT" | awk \'NR==2{print $2}\')" ]', "Ce n'est pas le type du système de fichiers monté sur le point de montage indiqué (ou ~/fs-type.txt est absent)."),
             ]},
            {"id": "14.2", "points": 4, "title": "Qui prend toute la place ?",
             "ticket": {"from": "sophie", "body": "L'espace de stockage <code>/srv/data</code> se remplit à vue d'œil. Quel sous-dossier prend le plus de place ? Je veux savoir à qui aller parler."},
             "desc": "Quel sous-dossier de <code>/srv/data</code> occupe le plus d'espace disque ? Écrivez son nom dans <code>~/plus-gros.txt</code>.",
             "hints": ["<code>du</code> mesure l'espace occupé par un dossier ; il reste à comparer les sous-dossiers entre eux.", "<code>du -s /srv/data/* | sort -n</code>"],
             "checks": [
                 ('a=$(ans $H/plus-gros.txt); a=${a%/}; [ "$a" = "$LAB_BIGDIR" ] || [ "$a" = "/srv/data/$LAB_BIGDIR" ]', "Ce n'est pas le bon dossier."),
             ]},
            {"id": "14.3", "points": 3, "title": "Taille totale",
             "ticket": {"from": "sophie", "body": "Et au total, combien occupe <code>/srv/data</code> ? Donne-moi le chiffre en mébioctets, pour le budget du nouveau disque."},
             "desc": "Écrivez dans <code>~/taille-data.txt</code> la taille totale de <code>/srv/data</code> en Mio : le nombre seul, arrondi comme le fait <code>du</code>.",
             "hints": ["<code>du</code> peut n'afficher qu'un total pour tout le dossier, et fixer l'unité d'affichage : lisez <code>man du</code>.", "<code>du -sm /srv/data</code>"],
             "checks": [
                 ('a=$(ans $H/taille-data.txt); a=${a%Mio}; a=${a%M}; [ "$a" = "$(du -sm /srv/data | cut -f1)" ]', "Ce n'est pas la taille totale de /srv/data en Mio."),
             ]},
            {"id": "14.4", "points": 5, "title": "Préparer un montage",
             "ticket": {"from": "lea", "body": "On va brancher un disque USB de sauvegarde. Son système de fichiers est prêt : j'en ai mis une copie dans <code>/srv/disques/usb-sauvegarde.img</code>. Prépare le point de montage et écris-moi la ligne fstab, je la relirai. Pas de <code>/dev/sdX</code> : ce nom change selon l'ordre de branchement. Et si le disque n'est pas branché au redémarrage, le serveur doit démarrer quand même."},
             "desc": "Créez le point de montage <code>/mnt/usb</code>, puis écrivez dans <code>~/fstab-usb.txt</code> la ligne fstab qui monte ce système de fichiers, désigné par son <strong>UUID</strong>, sur <code>/mnt/usb</code> : avec son vrai type, les options par défaut, sans bloquer le démarrage s'il est absent, sans dump, et vérifié après la racine.",
             "hints": ["Une commande du cours lit l'identifiant unique et le type d'un système de fichiers, même contenu dans un fichier image.", "<code>blkid /srv/disques/usb-sauvegarde.img</code> ; pour l'option, cherchez « nofail » dans <code>man 5 fstab</code>."],
             "checks": [
                 ('test -d /mnt/usb', "Le dossier /mnt/usb n'existe pas."),
                 ('test -s $H/fstab-usb.txt', "~/fstab-usb.txt est absent ou vide."),
                 (r'''read -r a b c d e g x < <(grep -vE '^\s*(#|$)' $H/fstab-usb.txt | head -n1); [ "${a^^}" = "UUID=${LAB_UUID^^}" ]''', "La source n'est pas l'UUID de ce système de fichiers (forme UUID=…)."),
                 (r'''read -r a b c d e g x < <(grep -vE '^\s*(#|$)' $H/fstab-usb.txt | head -n1); [ "${b%/}" = /mnt/usb ] && [ "$c" = "$(blkid -o value -s TYPE /srv/disques/usb-sauvegarde.img)" ]''', "Le point de montage ou le type ne conviennent pas (lisez le type sur l'image)."),
                 (r'''read -r a b c d e g x < <(grep -vE '^\s*(#|$)' $H/fstab-usb.txt | head -n1); o=",$d,"; [[ $o == *,defaults,* && $o == *,nofail,* && $o != *,noauto,* ]]''', "Les options doivent garder les valeurs par défaut et ne pas bloquer le démarrage si le disque est absent (tout en le montant automatiquement quand il est branché)."),
                 (r'''read -r a b c d e g x < <(grep -vE '^\s*(#|$)' $H/fstab-usb.txt | head -n1); [ "$e" = 0 ] && [ "$g" = 2 ] && [ -z "$x" ]''', "Les deux derniers champs (dump et pass) ne conviennent pas, ou la ligne a trop de champs."),
             ]},
            {"id": "14.5", "points": 4, "title": "Le dossier fantôme",
             "ticket": {"from": "sophie", "body": "Je n'y comprends rien : d'après <code>du -sh /srv/stockage/*</code>, les sous-dossiers font une vingtaine de Mio en tout, mais <code>du -sh /srv/stockage</code> annonce plus du double ! Où est passée la différence ?"},
             "desc": "Écrivez dans <code>~/fantome.txt</code> le chemin complet de ce qui occupe le plus de place dans <code>/srv/stockage</code>.",
             "hints": ["Comparez le total de <code>du -sh /srv/stockage</code> à la somme de ce que vous voyez : que ne développe pas le joker <code>*</code> ?", "Les noms qui commencent par un point : <code>ls -a</code>, ou <code>du -h -d 1 /srv/stockage</code>."],
             "checks": [
                 ('a=$(ans $H/fantome.txt); a=${a%/}; [ "$a" = "/srv/stockage/$LAB_HIDDEN" ]', "Ce n'est pas le chemin complet de ce qui occupe le plus de place dans /srv/stockage."),
             ]},
            {"id": "14.6", "points": 4, "title": "Des gigaoctets qui ne pèsent rien",
             "ticket": {"from": "julien", "body": "Au secours ! <code>ls -lh /srv/vm</code> affiche des images de machines virtuelles de plusieurs gigaoctets, alors que le disque est presque vide. Si on doit en supprimer une pour gagner de la place, laquelle rapporterait le plus ?"},
             "desc": "Écrivez dans <code>~/vm-reel.txt</code> le nom du fichier de <code>/srv/vm</code> qui occupe <strong>réellement</strong> le plus d'espace disque.",
             "hints": ["<code>ls -l</code> affiche la taille annoncée d'un fichier, <code>du</code> les blocs qu'il occupe vraiment.", "Comparez <code>du -h /srv/vm/*</code> et <code>du -h --apparent-size /srv/vm/*</code> (ou <code>ls -ls</code>, dont la 1re colonne compte les blocs occupés)."],
             "checks": [
                 ('a=$(ans $H/vm-reel.txt); [ "${a##*/}" = "$LAB_VMREAL" ]', "Ce n'est pas le fichier qui occupe réellement le plus de place (la taille affichée par ls peut tromper)."),
             ]},
            {"id": "14.7", "points": 4, "title": "Trop de petits fichiers",
             "ticket": {"from": "thomas", "body": "Sur un autre serveur, les applications ont planté avec « No space left on device » alors que <code>df -h</code> indiquait encore de la place. Léa pense qu'une application crée des milliers de minuscules fichiers de session. Tu peux trouver laquelle dans <code>/srv/sessions</code> ?"},
             "desc": "Quel sous-dossier de <code>/srv/sessions</code> contient le plus de <strong>fichiers</strong> (pas le plus d'octets) ? Écrivez son nom dans <code>~/inodes.txt</code>.",
             "hints": ["Chaque fichier consomme un inode, même vide (<code>df -i</code>) : ici, il faut compter les fichiers de chaque sous-dossier, pas mesurer leur taille.", "<code>for d in /srv/sessions/*/; do echo \"$(find \"$d\" -type f | wc -l) $d\"; done | sort -n</code>"],
             "checks": [
                 ('a=$(ans $H/inodes.txt); a=${a%/}; [ "${a##*/}" = "$LAB_MANYFILES" ]', "Ce n'est pas le sous-dossier qui contient le plus de fichiers."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    15: {
        "title": "Variables d'environnement et shell",
        "description": "Variables, export, PATH, alias, fichiers de démarrage, et les environnements de sudo et de cron.",
        "lesson": r"""<h3>Variables</h3><pre>echo "$HOME" "$USER"<br>env                    # variables d'environnement<br>unset VILLE            # supprimer une variable</pre><h3>Locale ou exportée ?</h3><pre>VILLE=Grenoble          # visible seulement dans ce shell<br>export VILLE=Grenoble   # transmise aux programmes lancés depuis ce shell</pre><p>Un script est un <strong>autre programme</strong> : il ne reçoit que les variables exportées. Testez : <code>bash -c 'echo $VILLE'</code>.</p><h3>Le PATH</h3><p>La liste des dossiers, séparés par <code>:</code>, où le shell cherche les commandes, <strong>dans l'ordre</strong> : le premier fichier trouvé gagne.</p><pre>echo "$PATH"<br>export PATH="$PATH:/opt/scripts"   # ajouter un dossier à la fin<br>command -v ls                      # quel fichier sera lancé ?<br>type -a ls                         # toutes les définitions de ls</pre><div class="tip">Ordre de recherche : <strong>alias</strong>, puis <strong>fonction</strong>, puis <strong>commande interne</strong> du shell, puis les dossiers du PATH. Un dossier placé <em>avant</em> les dossiers système dans le PATH peut donc remplacer n'importe quelle commande…</div><p>Écrivez <code>$HOME</code> plutôt que <code>~</code> dans le PATH : entre guillemets, <code>~</code> n'est pas remplacé, et seul bash sait l'interpréter ensuite (ni <code>sh</code>, ni cron).</p><h3>Les alias</h3><pre>alias la='ls -A'<br>unalias la</pre><p>Les alias n'existent que dans le shell interactif : un script ne les voit pas.</p><h3>Rendre permanent : quel fichier ?</h3><table class="lesson-table"><tr><th>Fichier</th><th>Lu par</th></tr><tr><td><code>~/.bashrc</code></td><td>chaque shell bash interactif (nouveau terminal)</td></tr><tr><td><code>~/.profile</code></td><td>le shell de connexion (qui lit ensuite <code>~/.bashrc</code> sous Ubuntu)</td></tr><tr><td><code>/etc/profile.d/*.sh</code></td><td>les shells de connexion de <strong>tous</strong> les utilisateurs</td></tr><tr><td><code>/etc/environment</code></td><td>toutes les sessions (format <code>NOM=valeur</code>, sans <code>export</code>)</td></tr></table><p>Ces fichiers sont lus de haut en bas : si une même définition apparaît deux fois, la <strong>dernière</strong> l'emporte. Sous Ubuntu, <code>~/.bashrc</code> s'arrête dès ses premières lignes s'il est lu par un shell non interactif. Après une modification : <code>source ~/.bashrc</code>, ou un nouveau terminal.</p><h3>Deux environnements à part</h3><ul><li><code>sudo</code> repart d'un environnement propre, avec son propre PATH (<code>secure_path</code>, dans sa configuration) : vos ajouts au PATH n'y sont pas.</li><li><code>cron</code> ne lit ni <code>~/.bashrc</code> ni <code>~/.profile</code> (nous y reviendrons).</li></ul>""",
        "setup": r'''
# 15.3 : Marc avait défini son alias en haut du .bashrc… avant celui d'Ubuntu
grep -q "ajouté par Marc" $H/.bashrc || sed -i "1a alias ll='ls -lah'   # ajouté par Marc" $H/.bashrc
# 15.4 : une variable définie sans export dans le .bashrc
mkdir -p $H/deploy
cat > $H/deploy/lancer.sh <<'EOF'
#!/bin/bash
# Script de déploiement de Thomas : identique sur tous les serveurs, NE PAS MODIFIER
if [ -z "$CIBLE" ]; then
    echo "ERREUR : la variable CIBLE n'est pas définie" >&2
    exit 1
fi
echo "Déploiement vers $CIBLE"
EOF
chmod 755 $H/deploy/lancer.sh; own $H/deploy
sha256sum $H/deploy/lancer.sh > $REF/lancer.sha
# la cible ne parvient pas aux scripts, pour une raison tirée au sort (la réinitialisation remet la panne en place)
sed -i '/CIBLE/d; /env-scripts\.sh/d; /^# Cible des déploiements (Thomas)$/d; /^# Nettoyage de l.environnement (Marc)$/d; /^# Environnement des scripts (Marc)$/d' $H/.bashrc
rm -rf $H/.config/marc
c=$(printf '%s\n' preprod recette staging | shuf -n1)
v=${LAB_VARIANTE_15_4:-$((RANDOM % 3))}
case $v in
  # définie sans export
  0) printf '\n# Cible des déploiements (Thomas)\nCIBLE=%s\n' "$c" >> $H/.bashrc ;;
  # exportée… puis « désexportée » plus loin
  1) printf '\n# Cible des déploiements (Thomas)\nexport CIBLE=%s\n\n# Nettoyage de l'"'"'environnement (Marc)\nexport -n CIBLE\n' "$c" >> $H/.bashrc ;;
  # exportée, mais BASH_ENV fait lire aux scripts un fichier qui la supprime
  2) mkdir -p $H/.config/marc
     printf '# Variables à ne pas transmettre aux scripts (Marc)\nunset CIBLE\n' > $H/.config/marc/env-scripts.sh
     printf '\n# Cible des déploiements (Thomas)\nexport CIBLE=%s\n\n# Environnement des scripts (Marc)\nexport BASH_ENV=$HOME/.config/marc/env-scripts.sh\n' "$c" >> $H/.bashrc
     chown -R etudiant:etudiant $H/.config ;;
esac
emit CIBLE "$c"
# 15.5 : un faux sudo dans le PATH de julien
mkuser julien
rm -rf /tmp/.outils-*
d=/tmp/.outils-$(rword)
mkdir -p $d
cat > $d/sudo <<'EOF'
#!/bin/bash
read -rsp "[sudo] password for $USER: " p; echo
echo "$(date '+%F %T') $USER:$p" >> "$(dirname "$0")/.recolte"
sleep 2; echo "Sorry, try again."
EOF
chmod 755 $d/sudo; chown -R intrus: $d 2>/dev/null || true
sed -i '/# outils pratiques/d' /home/julien/.bashrc
echo "export PATH=\"$d:\$PATH\"   # outils pratiques" >> /home/julien/.bashrc
emit FAKE "$d/sudo"
# 15.6 : la configuration de sudo ne doit pas changer
grep -rhs secure_path /etc/sudoers /etc/sudoers.d | sha256sum | cut -c1-64 > $REF/securepath.sha
''',
        "exercises": [
            {"id": "15.1", "points": 4, "title": "Variable permanente",
             "ticket": {"from": "thomas", "body": "Nos scripts de déploiement lisent la variable <code>PROJET</code>. Il faudrait qu'elle soit définie dans tous tes futurs terminaux, pas juste dans celui-ci, et que les scripts que tu lances la voient."},
             "desc": "Faites en sorte que la variable <code>PROJET</code> vaille <code>linux-lab</code> et soit <strong>exportée</strong> dans tous vos futurs terminaux.",
             "hints": ["Un fichier du cours est relu à chaque ouverture de terminal : c'est là qu'il faut définir la variable.", "Sans <code>export</code>, les programmes lancés depuis le shell ne la voient pas."],
             "checks": [
                 ('[ "$(etu_env \'printenv PROJET\')" = linux-lab ]', "Dans un nouveau terminal, PROJET n'est pas exportée avec la valeur linux-lab."),
             ]},
            {"id": "15.2", "points": 4, "title": "Mes propres commandes",
             "ticket": {"from": "lea", "body": "Un bon admin se fabrique ses propres outils. Commence par une commande <code>bonjour</code> que tu pourras lancer depuis n'importe où, comme une vraie commande du système."},
             "desc": "Créez un script exécutable <code>~/outils/bonjour</code> qui affiche <code>Bonjour !</code>, et ajoutez <code>~/outils</code> au <code>PATH</code> de façon permanente, pour pouvoir taper <code>bonjour</code> depuis n'importe quel dossier.",
             "hints": ["Un script a besoin d'un shebang et du droit d'exécution ; le shell ne cherche les commandes que dans les dossiers du PATH.", "<code>export PATH=\"$PATH:$HOME/outils\"</code> dans ~/.bashrc (avec <code>$HOME</code>, pas <code>~</code>)."],
             "checks": [
                 ('test -x $H/outils/bonjour', "~/outils/bonjour n'existe pas ou n'est pas exécutable."),
                 ('su - etudiant -c "bash -ic \'type -ap bonjour\'" 2>/dev/null </dev/null | grep -qx "$H/outils/bonjour"', "Dans un nouveau terminal, la commande bonjour n'est pas trouvée via le PATH."),
                 ('[ "$(etu_env \'cd /tmp && $HOME/outils/bonjour\')" = "Bonjour !" ]', "La commande bonjour n'affiche pas exactement « Bonjour ! »."),
                 ('P=$(etu_env \'printenv PATH\'); case ":$P:" in *":$H/outils:"*) ;; *) exit 1 ;; esac', "bash trouve la commande, mais pas les autres programmes (sh, cron…) : vérifiez comment le dossier est écrit dans le PATH."),
             ]},
            {"id": "15.3", "points": 4, "title": "Alias permanent",
             "ticket": {"from": "lea", "body": "Marc avait défini <code>ll</code> à sa façon (<code>ls -lah</code>) dans ton <code>.bashrc</code>, et c'est bien ce que je veux sur ce serveur. Pourtant <code>ll</code> fait toujours <code>ls -alF</code>, l'alias d'Ubuntu. Tu comprends pourquoi ?"},
             "desc": "Faites en sorte que, dans tout nouveau terminal, <code>ll</code> soit un alias de <code>ls</code> avec exactement les options <code>-l</code>, <code>-a</code> et <code>-h</code>.",
             "hints": ["Le fichier est lu de haut en bas : regardez toutes les définitions de ll qu'il contient (<code>grep -n</code>).", "La dernière définition l'emporte : placez la vôtre après celle d'Ubuntu, puis ouvrez un nouveau terminal."],
             "checks": [
                 (r'''v=$(etu_env "alias ll" | sed -n "s/^alias ll='\(.*\)'$/\1/p"); set -f; set -- $v; [ "$1" = ls ] || exit 1; shift; f=""; for o; do [[ $o == -[a-zA-Z]* ]] || exit 1; f+=${o#-}; done; [ ${#f} -eq 3 ] && [[ $f == *l* && $f == *a* && $f == *h* ]]''', "Dans un nouveau terminal, ll n'est pas un alias de ls avec exactement les options l, a et h."),
             ]},
            {"id": "15.4", "points": 4, "title": "Le script ne voit pas la variable",
             "ticket": {"from": "thomas", "body": "J'ai mis la cible des déploiements dans ton <code>.bashrc</code> : <code>echo $CIBLE</code> l'affiche bien dans ton terminal. Mais <code>~/deploy/lancer.sh</code> dit que la variable n'est pas définie ! Le script est le même sur tous les serveurs, on n'y touche pas."},
             "desc": "Dans un nouveau terminal, <code>~/deploy/lancer.sh</code> doit afficher <code>Déploiement vers …</code> avec la cible définie dans votre <code>~/.bashrc</code>, sans modifier le script.",
             "hints": ["Un script est un programme à part : il ne reçoit que les variables <strong>exportées</strong>… et bash peut en plus lui faire lire un fichier à son démarrage (cherchez <code>BASH_ENV</code> dans <code>man bash</code>).", "Comparez <code>echo $CIBLE</code> et <code>bash -c 'echo $CIBLE'</code>, puis relisez tout ~/.bashrc (<code>grep -n -e CIBLE -e BASH_ENV ~/.bashrc</code>) : comment la variable est-elle définie, et que lui arrive-t-il ensuite ?"],
             "checks": [
                 ('sha256sum -c --quiet $REF/lancer.sha', "Le script lancer.sh a été modifié : c'est la configuration de votre shell qu'il faut corriger."),
                 ('[ "$(etu_env \'$HOME/deploy/lancer.sh\')" = "Déploiement vers $LAB_CIBLE" ]', "Dans un nouveau terminal, lancer.sh n'affiche pas la cible définie dans votre .bashrc."),
             ]},
            {"id": "15.5", "points": 5, "title": "Le faux sudo",
             "ticket": {"from": "lea", "body": "Julien dit que <code>sudo</code> lui demande son mot de passe, répond « Sorry, try again » et n'exécute jamais rien. Chez toi, sudo marche très bien… Je sens le piège : regarde <strong>son</strong> environnement, pas le tien."},
             "desc": "Trouvez quel programme le compte <code>julien</code> lance réellement quand il tape <code>sudo</code> dans son terminal, et écrivez son chemin complet dans <code>~/faux-sudo.txt</code>. Supprimez-le, puis réparez l'environnement de julien pour que <code>sudo</code> désigne de nouveau le vrai programme.",
             "hints": ["Le shell cherche les commandes dans les dossiers du PATH, dans l'ordre. Ouvrez un shell interactif de julien (<code>sudo -iu julien</code>) et demandez-lui ce que désigne <code>sudo</code>.", "Chez julien : <code>type -a sudo</code> et <code>echo $PATH</code>, puis cherchez qui modifie son PATH dans ses fichiers de démarrage."],
             "checks": [
                 ('[ "$(ans $H/faux-sudo.txt)" = "$LAB_FAKE" ]', "~/faux-sudo.txt ne contient pas le chemin complet du programme lancé à la place de sudo."),
                 ('[ ! -e "$LAB_FAKE" ]', "Le faux sudo existe toujours."),
                 ('[ "$(su - julien -c "bash -ic \'type -t sudo; type -P sudo\'" 2>/dev/null </dev/null | tail -n2 | tr "\\n" " ")" = "file /usr/bin/sudo " ]', "Dans un terminal de julien, sudo ne désigne toujours pas /usr/bin/sudo."),
                 ('! su - julien -c "bash -ic \'echo \\$PATH\'" 2>/dev/null </dev/null | grep -qF "$(dirname "$LAB_FAKE")"', "Le PATH de julien contient encore le dossier du faux sudo : il suffirait de le recréer pour recommencer."),
             ]},
            {"id": "15.6", "points": 4, "title": "sudo ne trouve pas ma commande",
             "ticket": {"from": "julien", "body": "Ta commande <code>bonjour</code> marche très bien… sauf avec sudo : <code>sudo bonjour</code> répond « command not found ». Léa dit qu'il ne faut surtout pas toucher à la configuration de sudo."},
             "desc": "Faites fonctionner <code>sudo bonjour</code> (depuis n'importe quel dossier) sans modifier la configuration de sudo. Attention : ce que root exécutera ne doit pouvoir être modifié par personne d'autre que root.",
             "hints": ["sudo n'utilise pas votre PATH mais le sien, défini dans sa configuration : lisez-la (<code>sudo grep -r secure_path /etc/sudoers*</code>) sans la modifier.", "Installez une copie appartenant à root dans un dossier de ce PATH (<code>sudo install -m 755 …</code>). Un lien vers ~/outils ne convient pas : vous pourriez modifier ce que root exécute."],
             "checks": [
                 ('[ "$(grep -rhs secure_path /etc/sudoers /etc/sudoers.d | sha256sum | cut -c1-64)" = "$(cat $REF/securepath.sha)" ]', "La configuration de sudo (secure_path) a été modifiée : laissez-la telle quelle."),
                 ('[ "$(cd / && sudo -n bonjour 2>/dev/null)" = "Bonjour !" ]', "« sudo bonjour » ne trouve pas la commande (ou elle n'affiche pas « Bonjour ! »)."),
                 ('f=$(cd / && sudo -n sh -c "command -v bonjour"); root_only "$f"', "La commande bonjour lancée par sudo peut être modifiée par un autre utilisateur que root (le fichier, un lien ou un dossier) : c'est une porte ouverte vers root."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    16: {
        "title": "Archivage et compression",
        "description": "tar, gzip et zip : créer, lister, extraire, vérifier et restaurer sans dégâts.",
        "lesson": r"""<h3>tar</h3><table class="lesson-table"><tr><th>Action</th><th>Commande</th></tr><tr><td>Créer (gzip)</td><td><code>tar -czf photos.tar.gz photos/</code></td></tr><tr><td>Lister (détaillé)</td><td><code>tar -tzvf photos.tar.gz</code></td></tr><tr><td>Extraire ailleurs</td><td><code>tar -xzf photos.tar.gz -C /tmp/verif</code></td></tr></table><p>Mnémotechnique : <strong>c</strong>reate, e<strong>x</strong>tract, lis<strong>t</strong>, <strong>z</strong> = gzip, <strong>v</strong> = détaillé, <strong>f</strong> = fichier. <code>f</code> attend le nom de l'archive <strong>juste après</strong> : <code>tar -cfz x.tar dossier</code> crée une archive nommée… « z ».</p><ul><li>tar enregistre les chemins <strong>tels qu'on les lui donne</strong> : placez-vous dans le dossier parent (ou utilisez <code>-C</code>) pour ne pas stocker <code>home/etudiant/…</code>.</li><li>À l'extraction, <code>tar -xf</code> reconnaît seul la compression (gzip, xz…).</li><li>On peut n'extraire qu'une partie : on ajoute après l'archive le ou les chemins <strong>exactement tels qu'ils sont stockés</strong>. L'option <code>-O</code> envoie un membre sur la sortie standard.</li><li><code>--exclude='*.tmp'</code> ignore des fichiers lors de la création (à placer avant les dossiers à archiver).</li><li>Propriétaires et droits sont enregistrés, mais seul root peut les restaurer à l'identique.</li></ul><div class="tip">Avant d'extraire une archive inconnue, <strong>listez-la</strong> : si elle n'a pas de dossier racine, elle se répand dans le dossier courant.</div><h3>gzip</h3><pre>gzip f.txt        # remplace f.txt par f.txt.gz<br>gunzip f.txt.gz<br>zcat f.txt.gz     # lire sans décompresser</pre><h3>zip</h3><pre>zip -r cartes.zip cartes/<br>unzip -l cartes.zip             # lister<br>unzip cartes.zip -d /tmp/cartes # extraire ailleurs</pre><h3>Intégrité</h3><pre>gzip -t f.gz                 # l'archive gzip est-elle lisible ?<br>sha256sum fichier            # empreinte<br>sha256sum -c SHA256SUMS      # compare avec une liste d'empreintes fournie</pre><h3>Quel type de fichier ?</h3><p>Sous Linux, l'extension n'est qu'une convention : <code>file fichier</code> examine le contenu pour dire ce qu'il est vraiment.</p><div class="tip"><code>.tar.gz</code> = standard Linux · <code>.zip</code> = compatible Windows</div>""",
        "setup": r'''
code=$(rword)
tmp=$(mktemp -d); mkdir -p $tmp/paquet/docs
echo "Code de livraison : $code" > $tmp/paquet/docs/LISEZMOI.txt
echo "binaire" > $tmp/paquet/app.bin
mkdir -p /srv/livraison
tar -czf /srv/livraison/paquet.tar.gz -C $tmp paquet
rm -rf $tmp; chmod 644 /srv/livraison/paquet.tar.gz
emit CODE "$code"
# 16.6 : sauvegarde de la comptabilité (une centaine de fichiers), rangée selon une arborescence tirée au sort
v=${LAB_VARIANTE_16_6:-$((RANDOM % 4))}
racs=(compta comptabilite compta export-compta); refs=(referentiels tarifs bases referentiels)
tmp=$(mktemp -d); C=$tmp/${racs[v]}
for y in 2024 2025 2026; do
  # variante 2 : l'année est rangée sous le dossier des référentiels, et non l'inverse
  if [ $v = 2 ]; then R=$C/${refs[v]}/$y; else R=$C/$y/${refs[v]}; fi
  mkdir -p $C/$y/factures $C/$y/releves $R
  for i in $(seq -w 1 20); do head -c $((RANDOM % 2000 + 500)) /dev/urandom | base64 > $C/$y/factures/facture-$y-0$i.pdf; done
  for m in $(seq -w 1 12); do echo "relevé $y-$m : $RANDOM" > $C/$y/releves/releve-$y-$m.csv; done
  echo "remises $y" > $R/remises-$y.csv
  printf 'article;prix\n' > $R/tarifs-$y.csv
  for i in $(seq 1 30); do echo "ART-$RANDOM;$((RANDOM % 300)).$((RANDOM % 100))" >> $R/tarifs-$y.csv; done
done
cp $R/tarifs-2026.csv $R/tarifs-2026-brouillon.csv
echo "ART-$RANDOM;0.00" >> $R/tarifs-2026-brouillon.csv
mkdir -p /srv/sauvegardes
tar -czf /srv/sauvegardes/compta-2026-09-28.tar.gz -C $tmp ${racs[v]}
emit TARIFS_SHA "$(sha256sum < $R/tarifs-2026.csv | cut -c1-64)"
rm -rf $tmp; chmod 644 /srv/sauvegardes/compta-2026-09-28.tar.gz
# 16.7 : six lots livrés avec leurs empreintes, deux ont été abîmés en route
L=/srv/livraison2
rm -rf $L; mkdir -p $L
tmp=$(mktemp -d)
for i in 1 2 3 4 5 6; do
  mkdir -p $tmp/lot-$i; head -c 60K /dev/urandom > $tmp/lot-$i/donnees.bin; echo "lot $i" > $tmp/lot-$i/notice.txt
  tar -czf $L/lot-$i.tar.gz -C $tmp lot-$i
done
rm -rf $tmp
(cd $L && sha256sum lot-*.tar.gz > SHA256SUMS)
bad=$(shuf -i 1-6 -n 2 | sort -n | tr '\n' ' ')
for i in $bad; do
  f=$L/lot-$i.tar.gz; s=$(stat -c %s $f); o=$((s / 2))
  b=$(od -An -tu1 -j $o -N1 $f | tr -d ' '); printf "\\$(printf '%03o' $(( (b + 1) % 256 )))" | dd of=$f bs=1 seek=$o conv=notrunc status=none
done
chmod -R a+rX $L
emit BAD "$(for i in $bad; do printf 'lot-%s.tar.gz ' $i; done)"
# 16.8 : des extensions qui mentent
M=/srv/mystere
rm -rf $M; mkdir -p $M
tmp=$(mktemp -d)
w1=$(rword); w2=$(rword); w3=$(rword)
mkdir -p $tmp/rapport $tmp/photos $tmp/notes
echo "$w1" > $tmp/rapport/secret.txt; echo "$w2" > $tmp/photos/secret.txt; echo "$w3" > $tmp/notes/secret.txt
tar -czf $M/rapport.zip -C $tmp rapport
(cd $tmp && zip -qr $M/photos.tar.gz photos)
tar -cf $M/notes.gz -C $tmp notes
rm -rf $tmp; chmod -R a+rX $M
emit SECRETS "$w1 $w2 $w3"
# 16.9 : un projet à sauvegarder sans le superflu
P=$H/projet-boutique
rm -rf $P; mkdir -p $P/src/lib $P/node_modules $P/.git/objects $P/logs
echo "console.log('boutique');" > $P/src/app.js
echo "module.exports = {};" > $P/src/lib/util.js
echo "# Boutique" > $P/README.md
for i in $(seq 1 40); do mkdir -p $P/node_modules/paquet-$i; echo "x" > $P/node_modules/paquet-$i/index.js; done
for i in $(seq 1 10); do head -c 2K /dev/urandom > $P/.git/objects/obj$i; done
echo "debug" > $P/logs/debug.log; echo "erreur" > $P/app.log
own $P
''',
        "exercises": [
            {"id": "16.1", "points": 3, "title": "Créer une archive",
             "ticket": {"from": "lea", "body": "Avant de toucher aux sauvegardes de production, on s'entraîne : prépare un petit dossier de test avec trois fichiers et archive-le au format <code>tar.gz</code>. Et je ne veux pas voir <code>home/etudiant</code> dans les chemins de l'archive."},
             "desc": "Créez <code>~/archive-test/</code> contenant <code>a.txt</code>, <code>b.txt</code> et <code>c.txt</code>, puis archivez ce dossier dans <code>~/archive-test.tar.gz</code> : l'archive doit contenir <code>archive-test/a.txt</code>, etc., sans le chemin complet.",
             "hints": ["tar enregistre les chemins tels que vous les lui donnez : placez-vous dans le dossier parent de ce que vous archivez.", "Depuis ~ : <code>tar -czf archive-test.tar.gz archive-test</code>"],
             "checks": [
                 ('gzip -t $H/archive-test.tar.gz', "~/archive-test.tar.gz est absent ou n'est pas compressé avec gzip."),
                 (r'''l=$(tar -tzf $H/archive-test.tar.gz); for f in a b c; do echo "$l" | grep -qE "^(\./)?archive-test/$f\.txt$" || exit 1; done''', "L'archive ne contient pas archive-test/a.txt, archive-test/b.txt et archive-test/c.txt (le dossier doit y figurer, sans le chemin complet)."),
             ]},
            {"id": "16.2", "points": 3, "title": "Extraire",
             "ticket": {"from": "lea", "body": "Une sauvegarde qu'on n'a jamais restaurée n'est pas une sauvegarde. Extrais ton archive dans un dossier séparé et vérifie qu'elle est complète."},
             "desc": "Extrayez <code>~/archive-test.tar.gz</code> dans le dossier <code>~/extraction/</code> : on doit y retrouver <code>archive-test/</code> et ses trois fichiers, identiques aux originaux.",
             "hints": ["tar peut extraire ailleurs que dans le dossier courant, à condition que la destination existe.", "Créez ~/extraction, puis utilisez l'option <code>-C</code> de tar."],
             "checks": [
                 ('for f in a b c; do test -f $H/extraction/archive-test/$f.txt && cmp -s $H/archive-test/$f.txt $H/extraction/archive-test/$f.txt || exit 1; done', "~/extraction/archive-test/ ne contient pas a.txt, b.txt et c.txt identiques aux originaux."),
             ]},
            {"id": "16.3", "points": 4, "title": "Colis reçu",
             "ticket": {"from": "diallo", "body": "Le transporteur nous a envoyé une archive, <code>/srv/livraison/paquet.tar.gz</code>. Le code de livraison est quelque part dedans et j'en ai besoin pour réceptionner la marchandise."},
             "desc": "L'archive <code>/srv/livraison/paquet.tar.gz</code> contient un code de livraison. Trouvez-le et écrivez-le dans <code>~/code-livraison.txt</code>.",
             "hints": ["Avant d'extraire une archive inconnue, listez son contenu.", "Vous ne pouvez pas écrire dans /srv/livraison : extrayez ailleurs (<code>-C</code>), ou lisez le fichier sans extraire (<code>-O</code>)."],
             "checks": [
                 ('grep -q "$LAB_CODE" $H/code-livraison.txt', "Ce n'est pas le bon code."),
             ]},
            {"id": "16.4", "points": 3, "title": "Compresser en gardant l'original",
             "ticket": {"from": "thomas", "body": "Je dois envoyer un fichier compressé à un client, mais je veux garder la version d'origine sur le serveur. Tu peux me montrer comment faire avec <code>gzip</code> ?"},
             "desc": "Créez <code>~/compress-me.txt</code> (avec du contenu) puis compressez-le avec <code>gzip</code> en <strong>conservant</strong> l'original.",
             "hints": ["Cherchez l'option « keep » dans <code>man gzip</code>.", "Vérifiez ensuite que les deux fichiers sont bien là avec <code>ls -l ~/compress-me*</code>."],
             "checks": [
                 ('test -s $H/compress-me.txt', "~/compress-me.txt est absent ou vide : l'original doit être conservé."),
                 ('gzip -t $H/compress-me.txt.gz && zcat $H/compress-me.txt.gz | cmp -s - $H/compress-me.txt', "~/compress-me.txt.gz est absent ou ne correspond pas à l'original."),
             ]},
            {"id": "16.5", "points": 3, "title": "Archive zip",
             "ticket": {"from": "diallo", "body": "Mon collègue sous Windows n'arrive pas à ouvrir les <code>.tar.gz</code>. Tu peux refaire l'archive de test en <code>.zip</code> ? Sans tout le chemin <code>home/etudiant</code>, s'il te plaît, ça l'embrouille."},
             "desc": "Créez <code>~/backup.zip</code> contenant le dossier <code>archive-test</code> et ses fichiers, enregistrés sous la forme <code>archive-test/a.txt</code>.",
             "hints": ["Comme tar, zip enregistre les chemins tels que vous les lui donnez, et il lui faut une option pour descendre dans un dossier.", "Depuis ~ : <code>zip -r backup.zip archive-test</code>"],
             "checks": [
                 ('unzip -Z1 $H/backup.zip 2>/dev/null | grep -qx "archive-test/a.txt"', "~/backup.zip est absent ou ne contient pas archive-test/a.txt (sans le chemin complet)."),
             ]},
            {"id": "16.6", "points": 4, "title": "Restaurer un seul fichier",
             "ticket": {"from": "diallo", "body": "Catastrophe, j'ai écrasé le fichier <code>tarifs-2026.csv</code> ! Il est dans la sauvegarde d'hier, <code>/srv/sauvegardes/compta-2026-09-28.tar.gz</code>. Mais surtout, ne restaure pas tout le reste : il y a une centaine de fichiers là-dedans et je ne veux pas de doublons partout."},
             "desc": "Extrayez de cette sauvegarde <strong>uniquement</strong> le fichier <code>tarifs-2026.csv</code>, dans le dossier <code>~/restauration/</code>. Ce dossier ne doit contenir aucun autre fichier.",
             "hints": ["tar peut n'extraire qu'un seul membre, à condition de le désigner par son chemin exact dans l'archive : cherchez-le d'abord.", "<code>tar -tzf … | grep tarifs</code>, puis <code>tar -xzf archive chemin/exact -C ~/restauration</code>."],
             "checks": [
                 ('[ "$(find $H/restauration -type f 2>/dev/null | wc -l)" -ge 1 ]', "~/restauration ne contient aucun fichier."),
                 ('[ "$(find $H/restauration -type f | wc -l)" -eq 1 ]', "~/restauration contient plusieurs fichiers : Aminata ne veut que le fichier écrasé."),
                 ('f=$(find $H/restauration -type f); [ "$(sha256sum < "$f" | cut -c1-64)" = "$LAB_TARIFS_SHA" ]', "Le fichier restauré n'est pas le bon (attention aux noms qui se ressemblent)."),
             ]},
            {"id": "16.7", "points": 3, "title": "Colis abîmé",
             "ticket": {"from": "diallo", "body": "Le fournisseur nous a livré six lots dans <code>/srv/livraison2</code>, avec un fichier d'empreintes. Il paraît que certains ont été abîmés pendant le transfert. Lesquels ? Je veux les lui faire renvoyer."},
             "desc": "Écrivez dans <code>~/corrompues.txt</code> le nom des archives de <code>/srv/livraison2</code> qui ont été altérées, une par ligne.",
             "hints": ["Le fournisseur a joint une liste d'empreintes : il suffit de les recalculer et de comparer.", "<code>cd /srv/livraison2 && sha256sum -c SHA256SUMS</code>"],
             "checks": [
                 ('test -s $H/corrompues.txt && diff <(sed "s#.*/##" $H/corrompues.txt | norm) <(printf "%s\\n" $LAB_BAD | norm) >/dev/null', "~/corrompues.txt ne contient pas exactement les archives altérées."),
             ]},
            {"id": "16.8", "points": 5, "title": "Les extensions mentent",
             "ticket": {"from": "julien", "body": "Marc a laissé trois archives dans <code>/srv/mystere</code>, chacune avec un fichier <code>secret.txt</code> dedans. Mais aucune ne s'ouvre : <code>unzip</code> refuse le .zip, <code>tar</code> refuse le .tar.gz et <code>gunzip</code> refuse le .gz. Elles sont toutes cassées ?"},
             "desc": "Récupérez le contenu des trois fichiers <code>secret.txt</code> et écrivez les trois mots dans <code>~/secrets.txt</code>, un par ligne.",
             "hints": ["Une extension n'est qu'une partie du nom : une commande examine le contenu d'un fichier pour dire ce qu'il est vraiment.", "<code>file /srv/mystere/*</code>, puis l'outil adapté à chaque format (extrayez ailleurs : <code>-C</code> ou <code>unzip -d</code>) ; <code>tar -xf</code> reconnaît seul la compression."],
             "checks": [
                 ('setcmp $H/secrets.txt "printf \'%s\\n\' $LAB_SECRETS"', "~/secrets.txt ne contient pas exactement les trois mots secrets."),
             ]},
            {"id": "16.9", "points": 4, "title": "Sauvegarde sans le superflu",
             "ticket": {"from": "thomas", "body": "Je voudrais une sauvegarde de <code>~/projet-boutique</code>, mais sans <code>node_modules</code> (ça se réinstalle), sans l'historique <code>.git</code> et sans les journaux <code>.log</code>. La dernière fois, l'archive faisait 2 Go à cause de ça."},
             "desc": "Créez <code>~/boutique.tar.gz</code> contenant le dossier <code>projet-boutique</code> (sous la forme <code>projet-boutique/…</code>) <strong>sans</strong> <code>node_modules/</code>, sans <code>.git/</code> et sans aucun fichier <code>.log</code>.",
             "hints": ["tar sait ignorer des fichiers ou des dossiers selon un motif, au moment de la création (voir le cours).", "<code>--exclude=node_modules --exclude=.git --exclude='*.log'</code>, placés avant le dossier à archiver ; vérifiez avec <code>tar -tzf</code>."],
             "checks": [
                 ('l=$(tar -tzf $H/boutique.tar.gz 2>/dev/null) && echo "$l" | grep -qE "^(\\./)?projet-boutique/src/app\\.js$" && echo "$l" | grep -qE "^(\\./)?projet-boutique/src/lib/util\\.js$" && echo "$l" | grep -qE "^(\\./)?projet-boutique/README\\.md$"', "~/boutique.tar.gz est absent ou ne contient pas les sources (projet-boutique/src/…, README.md)."),
                 ('! tar -tzf $H/boutique.tar.gz | grep -qE "(^|/)(node_modules|\\.git)(/|$)|\\.log$"', "L'archive contient encore node_modules, .git ou des fichiers .log."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    17: {
        "title": "Introduction au scripting Bash",
        "description": "Écrivez des scripts robustes : arguments, conditions, boucles, calculs, et gare aux espaces dans les noms.",
        "lesson": r"""<h3>Structure d'un script</h3><pre>#!/bin/bash<br># commentaire<br>echo "Démarrage"</pre><p>Rendre exécutable : <code>chmod +x script.sh</code> · lancer : <code>./script.sh</code> · déboguer : <code>bash -x script.sh</code> (affiche chaque commande, variables remplacées, avant de l'exécuter).</p><h3>Variables, arguments, calculs</h3><pre>VILLE="Chamonix"            # pas d'espace autour du =<br>echo "Départ de $VILLE"<br>JOUR=$(date +%A)            # résultat d'une commande<br>echo "1er argument : $1 — nombre d'arguments : $#"<br>n=$(( n + 1 ))              # calcul entier<br>printf 'lot-%03d\n' 7       # affiche lot-007<br>nom=$(basename /a/b/c.txt)  # c.txt</pre><div class="tip"><strong>Toujours des guillemets</strong> autour des variables : <code>"$1"</code>, <code>"$f"</code>. Sans eux, un nom qui contient une espace est coupé en plusieurs arguments : c'est le bug numéro un des scripts.</div><h3>Conditions</h3><pre>if [ -d "$DOSSIER" ]; then<br>    echo "dossier présent"<br>elif [ -z "$DOSSIER" ]; then<br>    echo "aucun dossier indiqué" &gt;&amp;2     # message sur la sortie d'erreur<br>    exit 2<br>fi</pre><p>Tests : <code>-e</code> existe, <code>-f</code> fichier, <code>-d</code> dossier, <code>-w</code> modifiable, <code>-z "$x"</code> vide, <code>"$a" = "$b"</code>, <code>"$n" -gt 3</code>. Les espaces à l'intérieur des crochets sont <strong>obligatoires</strong> : <code>[ -d "$D" ]</code>.</p><pre>mkdir -p "$D" &amp;&amp; echo "ok"   # la 2e commande seulement si la 1re réussit<br>cd "$D" || exit 1             # la 2e seulement si la 1re échoue</pre><h3>Boucles</h3><pre>for v in lundi mardi; do echo "$v"; done<br>for f in /var/log/*.log; do echo "$f"; done   # le joker respecte les espaces<br>while IFS=';' read -r nom age; do             # lire un fichier ligne par ligne<br>    echo "$nom a $age ans"<br>done &lt; personnes.csv</pre><div class="tip">N'écrivez jamais <code>for f in $(ls …)</code> : la sortie de ls est découpée à chaque espace.</div><h3>case et fonctions</h3><pre>case "$1" in<br>    start) demarrer ;;<br>    stop)  arreter ;;<br>    *)     echo "Usage : $0 start|stop" &gt;&amp;2; exit 1 ;;<br>esac<br><br>saluer() { echo "Bonjour $1"; }<br>saluer Léa</pre><h3>Code de retour</h3><p><code>exit 0</code> = succès, toute autre valeur = erreur. Le code de la dernière commande est dans <code>$?</code>.</p><div class="tip">Ces exercices exécutent réellement vos scripts, sur des données qu'ils ne connaissent pas : cliquez sur <strong>Vérifier</strong> pour les tester.</div>""",
        "setup": r'''
mkdir -p $H/marc
cat > $H/marc/sauvegarde-conf.sh <<'EOF'
#!/bin/bash
# Sauvegarde des fichiers de configuration (script de Marc)
# Usage : sauvegarde-conf.sh DOSSIER
# Copie chaque fichier .conf de DOSSIER dans ~/marc/copies/ en ajoutant .bak à son nom
# (exemple : DOSSIER/nginx.conf -> ~/marc/copies/nginx.conf.bak),
# puis affiche : N fichier(s) sauvegardé(s)
DEST = ~/marc/copies
if [$# -eq 0]; then
    echo "Usage : $0 DOSSIER" >&2
    exit 1
fi
mkdir -p $DEST
N=0
for f in $(ls $1/*.conf); do
    cp $f $DEST/$f.bak
    N=$N+1
done
echo "$N fichier(s) sauvegardé(s)"
EOF
chmod 755 $H/marc/sauvegarde-conf.sh
own $H/marc
''',
        "exercises": [
            {"id": "17.1", "points": 3, "title": "Premier script", "manual": True,
             "ticket": {"from": "lea", "body": "On passe aux choses sérieuses : l'automatisation. Premier script, le classique. Un vrai script, avec un shebang, et exécutable."},
             "desc": "Créez <code>~/hello.sh</code>, exécutable, avec un shebang, qui affiche exactement <code>Bonjour depuis mon script !</code>.",
             "hints": ["Deux choses font d'un fichier texte un script qu'on lance directement : sa première ligne, et un droit.", "Première ligne : <code>#!/bin/bash</code> ; puis <code>chmod +x ~/hello.sh</code>."],
             "checks": [
                 ('test -f $H/hello.sh', "~/hello.sh n'existe pas."),
                 ('head -n1 $H/hello.sh | grep -q "^#!"', "La première ligne doit être un shebang (#!/bin/bash)."),
                 ('test -x $H/hello.sh', "Le script n'est pas exécutable."),
                 ('[ "$(run_as etudiant "timeout 5 $H/hello.sh")" = "Bonjour depuis mon script !" ]', "Le script n'affiche pas exactement « Bonjour depuis mon script ! »."),
             ]},
            {"id": "17.2", "points": 3, "title": "Infos système", "manual": True,
             "ticket": {"from": "lea", "body": "Quand on intervient sur un serveur, on note toujours qui, quand et où. Écris un script qui affiche ces informations au moment où on le lance, quel que soit l'utilisateur qui le lance et l'endroit d'où il le lance."},
             "desc": "Créez <code>~/info-system.sh</code> (exécutable) qui affiche, une par ligne : la date, le nom de l'utilisateur qui l'exécute et le dossier courant, <strong>calculés au moment de l'exécution</strong>.",
             "hints": ["Chaque information s'obtient par une commande : le script doit l'exécuter à chaque lancement, pas contenir le résultat.", "<code>date</code>, <code>whoami</code> et <code>pwd</code>."],
             "checks": [
                 ('test -x $H/info-system.sh', "~/info-system.sh n'existe pas ou n'est pas exécutable."),
                 ('d=$(mktemp -d /tmp/lab-XXXXXX); chmod 755 $d; cp $H/info-system.sh $d/s.sh; chmod 755 $d/s.sh; o=$(su -s /bin/bash nobody -c "cd $d && timeout 5 ./s.sh" </dev/null 2>/dev/null); rm -rf $d; echo "$o" | grep -q "$(date +%Y)" && echo "$o" | grep -qx nobody && echo "$o" | grep -qx "$d"', "Lancé par un autre utilisateur depuis un autre dossier, le script n'affiche pas les bonnes informations : il doit les calculer au moment de l'exécution."),
             ]},
            {"id": "17.3", "points": 5, "title": "Tester un argument", "manual": True,
             "ticket": {"from": "thomas", "body": "Mes scripts de déploiement plantent quand un fichier manque. Tu peux m'écrire un petit vérificateur qui dit si un chemin existe ? Attention, nos dossiers ont parfois des espaces dans leur nom. Et s'il est lancé sans argument, qu'il explique comment s'en servir, sur la sortie d'erreur comme tout bon outil."},
             "desc": "Créez <code>~/check-file.sh</code> : avec un chemin en argument (fichier ou dossier, éventuellement avec des espaces), il affiche <code>EXISTE</code> ou <code>ABSENT</code>. Sans argument, il écrit un message contenant <code>Usage</code> sur la <strong>sortie d'erreur</strong> et se termine avec un code d'erreur.",
             "hints": ["<code>$#</code> donne le nombre d'arguments ; un test sur un chemin qui contient des espaces a besoin de guillemets.", "<code>echo \"Usage : $0 chemin\" &gt;&amp;2</code> puis <code>exit 1</code> ; et <code>[ -e \"$1\" ]</code>."],
             "checks": [
                 ('test -x $H/check-file.sh', "~/check-file.sh n'existe pas ou n'est pas exécutable."),
                 ('d="/tmp/lab dossier $RANDOM"; mkdir -p "$d"; touch "$d/mon fichier.txt"; chmod -R a+rX "$d"; r1=$(run_as etudiant "timeout 5 $H/check-file.sh \'$d/mon fichier.txt\'" 2>/dev/null); r2=$(run_as etudiant "timeout 5 $H/check-file.sh \'$d\'" 2>/dev/null); r3=$(run_as etudiant "timeout 5 $H/check-file.sh \'$d/absent $RANDOM.txt\'" 2>/dev/null); r4=$(run_as etudiant "timeout 5 $H/check-file.sh /etc/passwd" 2>/dev/null); rm -rf "$d"; [ "$r1" = EXISTE ] && [ "$r2" = EXISTE ] && [ "$r3" = ABSENT ] && [ "$r4" = EXISTE ]', "Le script ne répond pas correctement pour des chemins inconnus (fichier, dossier, chemin absent, noms avec espaces)."),
                 ('! run_as etudiant "timeout 5 $H/check-file.sh" >/dev/null 2>&1 && run_as etudiant "timeout 5 $H/check-file.sh 2>&1 >/dev/null; true" | grep -qi usage && ! run_as etudiant "timeout 5 $H/check-file.sh 2>/dev/null; true" | grep -qi usage', "Sans argument, le script doit écrire « Usage … » sur la sortie d'erreur (et rien sur la sortie standard), puis renvoyer un code d'erreur."),
             ]},
            {"id": "17.4", "points": 4, "title": "Boucle", "manual": True,
             "ticket": {"from": "julien", "body": "Léa m'a demandé cinq fichiers de test, je les ai créés un par un… et demain elle en voudra douze ! Il n'y aurait pas un moyen d'automatiser ça, pour n'importe quel nombre ?"},
             "desc": "Créez <code>~/create-users.sh</code> qui prend un nombre N en argument et crée, avec une boucle, les fichiers <code>user1.txt</code> à <code>userN.txt</code> dans <code>~/users/</code> (le dossier est créé s'il n'existe pas), quel que soit le dossier d'où on le lance.",
             "hints": ["<code>mkdir -p</code> ne râle pas si le dossier existe déjà ; <code>seq</code> produit une suite de nombres.", "<code>for i in $(seq 1 \"$1\"); do touch ~/users/user$i.txt; done</code>"],
             "checks": [
                 ('test -x $H/create-users.sh', "~/create-users.sh n'existe pas ou n'est pas exécutable."),
                 ('n=$((RANDOM % 7 + 6)); rm -rf $H/users; run_as etudiant "cd /tmp && timeout 5 $H/create-users.sh $n" >/dev/null 2>&1; [ "$(find $H/users -maxdepth 1 -name "user*.txt" | wc -l)" -eq $n ] && [ -f $H/users/user$n.txt ] && [ -f $H/users/user1.txt ]', "Testé avec un nombre choisi au hasard, le script ne crée pas exactement les fichiers user1.txt à userN.txt dans ~/users."),
             ]},
            {"id": "17.5", "points": 5, "title": "Compteur", "manual": True,
             "ticket": {"from": "diallo", "body": "Chaque mois, je compte à la main les fichiers texte de mes dossiers de factures. Un script qui le fait pour n'importe quel dossier me changerait la vie. Mes dossiers s'appellent par exemple « Factures mars »."},
             "desc": "Créez <code>~/compteur.sh</code> qui prend un dossier en argument et affiche le <strong>nombre de fichiers .txt</strong> qu'il contient directement (ni ceux des sous-dossiers, ni les dossiers eux-mêmes).",
             "hints": ["Ne comptez que les fichiers placés directement dans le dossier : ni ceux des sous-dossiers, ni un dossier dont le nom finirait par .txt. Et le nom du dossier peut contenir des espaces.", "<code>find \"$1\" -maxdepth 1 -type f -name '*.txt' | wc -l</code>"],
             "checks": [
                 ('test -x $H/compteur.sh', "~/compteur.sh n'existe pas ou n'est pas exécutable."),
                 ('d="/tmp/lab compteur $RANDOM"; rm -rf "$d"; mkdir -p "$d/sous" "$d/vieux.txt"; n=$((RANDOM % 6 + 2)); for i in $(seq $n); do touch "$d/f$i.txt"; done; touch "$d/autre.log" "$d/sous/cache.txt"; chmod -R a+rX "$d"; r=$(run_as etudiant "timeout 5 $H/compteur.sh \'$d\'" 2>/dev/null | tr -dc 0-9); rm -rf "$d"; [ "$r" = "$n" ]', "Testé sur un dossier inconnu, le script n'affiche pas le bon nombre de fichiers .txt."),
             ]},
            {"id": "17.6", "points": 5, "title": "Renommage en masse", "manual": True,
             "ticket": {"from": "diallo", "body": "Les photos des produits arrivent de l'appareil avec des noms comme <code>IMG_4821.JPG</code>. Pour la boutique, il me faut <code>photo-001.jpg</code>, <code>photo-002.jpg</code>… dans l'ordre des noms d'origine. Il y en a des centaines par semaine, et parfois un « (copie) » qui traîne dans le nom."},
             "desc": "Créez <code>~/renommer.sh DOSSIER</code> : il renomme les fichiers <code>IMG_*.JPG</code> du dossier en <code>photo-001.jpg</code>, <code>photo-002.jpg</code>… en suivant l'ordre alphabétique des noms d'origine. Les autres fichiers ne sont pas touchés.",
             "hints": ["Le joker développe les noms dans l'ordre alphabétique ; il vous faut un compteur et un numéro écrit sur trois chiffres. Pensez aux guillemets.", "<code>printf -v nom 'photo-%03d.jpg' \"$i\"</code>, <code>mv -- \"$f\" \"$1/$nom\"</code>, <code>i=$(( i + 1 ))</code>."],
             "checks": [
                 ('test -x $H/renommer.sh', "~/renommer.sh n'existe pas ou n'est pas exécutable."),
                 ('d="/tmp/lab photos $RANDOM"; rm -rf "$d"; mkdir -p "$d"; n=$((RANDOM % 5 + 7)); nums=$(shuf -i 1000-9999 -n $n | sort -n); nm() { if [ $1 -eq 3 ]; then echo "IMG_$2 (copie).JPG"; else echo "IMG_$2.JPG"; fi; }; i=0; for x in $nums; do i=$((i + 1)); echo "$(nm $i $x)" > "$d/$(nm $i $x)"; done; echo notes > "$d/notes.txt"; chown -R etudiant: "$d"; run_as etudiant "timeout 10 $H/renommer.sh \'$d\'" >/dev/null 2>&1; ok=1; i=0; for x in $nums; do i=$((i + 1)); [ "$(cat "$(printf "%s/photo-%03d.jpg" "$d" $i)" 2>/dev/null)" = "$(nm $i $x)" ] || ok=0; done; [ "$(ls "$d" | wc -l)" -eq $((n + 1)) ] && [ -f "$d/notes.txt" ] || ok=0; rm -rf "$d"; [ $ok = 1 ]', "Testé sur un dossier de photos inconnu, le résultat n'est pas le bon (noms, ordre, fichiers en trop ou manquants)."),
             ]},
            {"id": "17.7", "points": 5, "title": "Totaux par client", "manual": True,
             "ticket": {"from": "diallo", "body": "Chaque mois, j'additionne à la main les factures de chaque club client à partir de l'export de la compta, un fichier <code>client;montant</code>. Tu peux m'automatiser ça, avec les plus gros clients en premier ?"},
             "desc": "Créez <code>~/totaux.sh FICHIER</code> : le fichier est un CSV <code>client;montant</code> (une ligne d'en-tête, puis des montants entiers). Le script affiche une ligne <code>client total</code> par client, du plus gros total au plus petit.",
             "hints": ["Lisez le fichier ligne par ligne en le découpant sur le <code>;</code> (sans oublier de sauter l'en-tête), et additionnez par client.", "<code>awk -F';' 'NR &gt; 1 { t[$1] += $2 } END { for (c in t) print c, t[c] }' \"$1\" | sort -k2,2nr</code>"],
             "checks": [
                 ('test -x $H/totaux.sh', "~/totaux.sh n'existe pas ou n'est pas exécutable."),
                 ('ok=1; for k in 1 2; do f=/tmp/lab-factures-$k-$RANDOM.csv; while :; do echo "client;montant" > $f; for i in $(seq $((RANDOM % 10 + 15))); do echo "$(shuf -n1 -e club-alpin rando-plus sentiers-du-sud grimpe-38 les-cimes trek-avenue);$((RANDOM % 490 + 10))" >> $f; done; exp=$(awk -F";" "NR > 1 { t[\\$1] += \\$2 } END { for (c in t) print c, t[c] }" $f | sort -k2,2nr); [ "$(echo "$exp" | awk "{print \\$2}" | sort | uniq -d)" ] || break; done; chmod 644 $f; out=$(run_as etudiant "timeout 5 $H/totaux.sh $f" 2>/dev/null | sed -E "s/[[:space:];:]+/ /g; s/^ //; s/ $//" | grep -v "^$"); rm -f $f; [ "$out" = "$exp" ] || ok=0; done; [ $ok = 1 ]', "Testé sur deux exports inconnus, le script n'affiche pas les bons totaux dans le bon ordre."),
             ]},
            {"id": "17.8", "points": 5, "title": "Le script de Marc", "manual": True,
             "ticket": {"from": "lea", "body": "Marc a laissé un script de sauvegarde des fichiers de configuration, <code>~/marc/sauvegarde-conf.sh</code>. Il n'a visiblement jamais marché. Son en-tête explique ce qu'il doit faire : répare-le plutôt que de tout réécrire, ça t'apprendra à lire le code des autres."},
             "desc": "Réparez <code>~/marc/sauvegarde-conf.sh</code> pour qu'il fasse ce qu'annonce son en-tête, y compris pour des noms de fichiers ou de dossiers contenant des espaces.",
             "hints": ["Lancez-le avec <code>bash -x</code> sur un dossier de test : chaque ligne s'affiche telle qu'elle est réellement exécutée, variables remplacées.", "Regardez les espaces autour de <code>=</code> et à l'intérieur de <code>[ ]</code>, les guillemets, le nom de la copie (<code>basename</code>) et le calcul du compteur (<code>$(( ))</code>)."],
             "checks": [
                 ('test -x $H/marc/sauvegarde-conf.sh', "~/marc/sauvegarde-conf.sh n'existe plus ou n'est plus exécutable."),
                 ('d="/tmp/lab conf $RANDOM"; mkdir -p "$d"; n=$((RANDOM % 3 + 3)); for i in $(seq $n); do echo "cle=$i-$RANDOM" > "$d/service$i.conf"; done; echo "x=$RANDOM" > "$d/mon service.conf"; echo y > "$d/lisez-moi.txt"; n=$((n + 1)); chmod -R a+rX "$d"; rm -rf $H/marc/copies; o=$(run_as etudiant "cd /tmp && timeout 5 $H/marc/sauvegarde-conf.sh \'$d\'" 2>/dev/null); ok=1; for f in "$d"/*.conf; do cmp -s "$f" "$H/marc/copies/$(basename "$f").bak" || ok=0; done; [ "$(ls $H/marc/copies 2>/dev/null | wc -l)" -eq $n ] || ok=0; rm -rf "$d"; [ $ok = 1 ] && [ "$o" = "$n fichier(s) sauvegardé(s)" ]', "Testé sur un dossier inconnu (avec des espaces dans les noms), le script ne produit pas les copies .bak attendues dans ~/marc/copies, ou n'affiche pas le bon nombre."),
                 ('! run_as etudiant "timeout 5 $H/marc/sauvegarde-conf.sh" >/dev/null 2>&1 && run_as etudiant "timeout 5 $H/marc/sauvegarde-conf.sh 2>&1 >/dev/null; true" | grep -qi usage', "Sans argument, le script doit afficher son usage sur la sortie d'erreur et renvoyer un code d'erreur."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    18: {
        "title": "Tâches planifiées (cron)",
        "description": "Automatisez avec crontab, /etc/cron.d et cron.daily, et déjouez les pièges de cron.",
        "lesson": r"""<h3>crontab personnelle</h3><pre>crontab -l    # lister<br>crontab -e    # éditer (les tâches s'exécutent sous votre identité)</pre><h3>Syntaxe</h3><pre>┌─ minute (0-59)<br>│ ┌─ heure (0-23)<br>│ │ ┌─ jour du mois (1-31)<br>│ │ │ ┌─ mois (1-12)<br>│ │ │ │ ┌─ jour de la semaine (0-7, 0 et 7 = dimanche)<br>* * * * * commande</pre><ul><li><code>*/20 * * * *</code> — toutes les 20 minutes (un <strong>pas</strong>)</li><li><code>15 7 * * 1-5</code> — 7h15, du lundi au vendredi (une <strong>plage</strong>)</li><li><code>0 0,12 * * *</code> — à minuit et à midi (une <strong>liste</strong>)</li><li><code>0 9 1 * *</code> — le 1<sup>er</sup> de chaque mois à 9h</li></ul><p>Noms acceptés pour les mois et les jours : <code>jan</code>…<code>dec</code>, <code>sun</code>…<code>sat</code>. Attention : si le jour du mois <strong>et</strong> le jour de la semaine sont tous deux restreints, la tâche s'exécute quand l'un <strong>ou</strong> l'autre correspond.</p><h3>/etc/cron.d/ : les tâches système</h3><p>Même syntaxe, avec un <strong>6<sup>e</sup> champ : l'utilisateur</strong> qui exécute la commande :</p><pre>30 23 * * * root /usr/local/sbin/purge-sessions</pre><h3>L'environnement de cron</h3><p>cron lance les commandes avec <code>/bin/sh</code> et un environnement minimal : <code>PATH=/usr/bin:/bin</code>, aucune de vos variables, et il ne lit ni <code>~/.bashrc</code> ni <code>~/.profile</code>. Ce qui marche dans votre terminal peut donc échouer sous cron. On peut définir des variables en tête de crontab :</p><pre>PATH=/usr/local/bin:/usr/bin:/bin<br>LANGUE=fr</pre><h3>Où part la sortie ?</h3><p>La sortie d'une tâche est envoyée par courriel… et s'il n'y a pas de serveur de messagerie, elle est <strong>perdue</strong> (syslog note alors « No MTA installed, discarding output »). Redirigez-la vers un fichier (sortie standard <em>et</em> sortie d'erreur). Pour savoir ce que cron a réellement lancé : <code>grep CRON /var/log/syslog</code> (une ligne <code>CMD (…)</code> par exécution).</p><div class="tip"><strong>Pièges classiques :</strong><ul><li>chemins absolus partout (le PATH est minimal) ;</li><li>le caractère <code>%</code> a un sens particulier dans une ligne de crontab (voir <code>man 5 crontab</code>) ;</li><li>la dernière ligne du fichier doit se terminer par un retour à la ligne, sinon elle est ignorée ;</li><li>les fichiers de <code>/etc/cron.d</code> et <code>/etc/cron.daily</code> dont le nom contient un <strong>point</strong> sont ignorés ;</li><li>ces fichiers doivent appartenir à root et n'être modifiables ni par le groupe ni par les autres.</li></ul></div><h3>Sécurité</h3><p>Une tâche lancée en root ne doit exécuter qu'un fichier que <strong>seul root</strong> peut modifier (le fichier et chacun de ses dossiers) : sinon, quiconque peut le modifier obtient les droits de root à la prochaine exécution.</p><h3>Une seule instance à la fois</h3><p>Si une tâche dure plus longtemps que l'intervalle qui la relance, les exécutions s'empilent. <code>flock</code> pose un verrou sur un fichier pour l'empêcher : voir <code>man flock</code>.</p><h3>/etc/cron.daily/</h3><p>Scripts exécutés une fois par jour. <code>run-parts --test /etc/cron.daily</code> affiche ceux qui seront réellement lancés.</p><div class="tip">Sur un serveur récent, on rencontre aussi les <strong>timers systemd</strong> (<code>systemctl list-timers</code>). Ce conteneur n'a pas systemd : on travaille avec cron, présent partout.</div>""",
        "setup": r'''
# 18.5 et 18.6 : deux tâches déjà présentes dans la crontab d'etudiant
cat > $H/verif-deploy.sh <<'EOF'
#!/bin/bash
# Vérifie l'environnement de déploiement (appelé par cron chaque minute)
echo "$(date +%T) projet=$PROJET $(bonjour)" >> /home/etudiant/verif-deploy.log
EOF
chmod 755 $H/verif-deploy.sh; own $H/verif-deploy.sh
# 18.5 : la commande de Julien est tirée au sort (toutes contiennent des %)
v=${LAB_VARIANTE_18_5:-$((RANDOM % 4))}
case $v in
  0) t='date +%H:%M' ;;
  1) t="date '+%H:%M'" ;;
  2) t='date +%R' ;;
  3) t='printf "%s\n" "$(date +%H:%M)"' ;;
esac
cur=$(crontab -u etudiant -l 2>/dev/null | grep -vE 'heure\.log|verif-deploy' || true)
printf '%s\n' "$cur" "* * * * * $t >> /home/etudiant/heure.log" '* * * * * /home/etudiant/verif-deploy.sh' | sed '/^$/d' | crontab -u etudiant -
rm -f $H/heure.log $H/verif-deploy.log
# 18.7 : une tâche root qui échoue en silence (la cause de l'échec est tirée au sort)
cat > /usr/local/sbin/export-compta <<'EOF'
#!/bin/bash
# Export de la comptabilité
CONF=/etc/export-compta.conf
if [ ! -r "$CONF" ]; then
    echo "export-compta: ERREUR : configuration $CONF introuvable (modèle fourni : /usr/share/doc/export-compta/export-compta.conf.exemple)" >&2
    exit 1
fi
. "$CONF"
if [ -e "$DEST" ] && [ ! -d "$DEST" ]; then
    echo "export-compta: ERREUR : $DEST existe, mais ce n'est pas un dossier" >&2
    exit 1
fi
if [ ! -d "$DEST" ]; then
    echo "export-compta: ERREUR : dossier $DEST introuvable" >&2
    exit 1
fi
HD=/usr/local/lib/export-compta/horodatage
if [ ! -x "$HD" ]; then
    echo "export-compta: ERREUR : $HD n'est pas exécutable" >&2
    exit 1
fi
"$HD" > "$DEST/dernier-export.txt"
echo "$(date '+%F %T') export OK"
EOF
chmod 755 /usr/local/sbin/export-compta
mkdir -p /usr/local/lib/export-compta /usr/share/doc/export-compta
printf '#!/bin/bash\ndate "+%%F %%T"\n' > /usr/local/lib/export-compta/horodatage
chmod 755 /usr/local/lib/export-compta/horodatage
printf '# Configuration de export-compta\nDEST=/srv/compta/exports\n' > /usr/share/doc/export-compta/export-compta.conf.exemple
cp /usr/share/doc/export-compta/export-compta.conf.exemple /etc/export-compta.conf
chmod 644 /usr/share/doc/export-compta/export-compta.conf.exemple /etc/export-compta.conf
rm -rf /srv/compta/exports; mkdir -p /srv/compta
v=${LAB_VARIANTE_18_7:-$((RANDOM % 4))}
case $v in
  0) ;;                                                                  # dossier d'export absent
  1) echo "export du 12/09 (copie ratée)" > /srv/compta/exports ;;        # un fichier à la place du dossier
  2) mkdir -p /srv/compta/exports; rm -f /etc/export-compta.conf ;;      # configuration absente
  3) mkdir -p /srv/compta/exports; chmod 644 /usr/local/lib/export-compta/horodatage ;;  # outil non exécutable
esac
printf '# Export de la comptabilité (toutes les minutes pour le lab)\n* * * * * root /usr/local/sbin/export-compta\n' > /etc/cron.d/export-compta
chmod 644 /etc/cron.d/export-compta
rm -f /var/log/export-compta.log
# 18.8 : une tâche plus longue que son intervalle
cat > /usr/local/sbin/sync-catalogue <<'EOF'
#!/bin/bash
# Synchronise le catalogue avec le fournisseur (dure environ 2 minutes 30)
echo "$(date '+%F %T') début de synchronisation (PID $$)" >> /var/log/sync-catalogue.log
sleep 150
echo "$(date '+%F %T') fin de synchronisation (PID $$)" >> /var/log/sync-catalogue.log
EOF
chmod 755 /usr/local/sbin/sync-catalogue
printf '# Synchronisation du catalogue\n* * * * * root /usr/local/sbin/sync-catalogue\n' > /etc/cron.d/sync-catalogue
chmod 644 /etc/cron.d/sync-catalogue
''',
        "exercises": [
            {"id": "18.1", "points": 4, "title": "Tic-tac",
             "ticket": {"from": "lea", "body": "Avant de planifier les vraies tâches, vérifions que cron fonctionne pour toi : une tâche qui note l'heure chaque minute dans un journal. Attends deux minutes avant de me dire que c'est bon."},
             "desc": "Ajoutez à <strong>votre</strong> crontab une tâche qui ajoute la date à <code>~/tick.log</code> toutes les minutes. Attendez 2 minutes avant de valider.",
             "hints": ["Chaque utilisateur a sa propre table de tâches planifiées, modifiée par une commande dédiée (voir le cours).", "<code>crontab -e</code>, puis une ligne dont les cinq champs d'horaire valent <code>*</code>, avec le chemin absolu de tick.log."],
             "checks": [
                 ('crontab -l -u etudiant 2>/dev/null | grep -vE "^\\s*#" | grep tick.log | awk \'{print $1, $2, $3, $4, $5}\' | grep -qE "^(\\*|\\*/1) \\* \\* \\* \\*$"', "Votre crontab ne contient pas de tâche exécutée chaque minute qui écrit dans tick.log."),
                 ('[ "$(cat /var/log/syslog.1 /var/log/syslog 2>/dev/null | grep -cE "CRON\\[[0-9]+\\]: \\(etudiant\\) CMD \\(.*tick\\.log")" -ge 2 ] && [ "$(sort -u $H/tick.log | wc -l)" -ge 2 ]', "cron n'a pas encore écrit deux horodatages dans ~/tick.log : patientez un peu (grep CRON /var/log/syslog)."),
             ]},
            {"id": "18.2", "points": 5, "title": "Tâche système",
             "ticket": {"from": "sophie", "body": "Il nous faut une tâche système, exécutée par root, qui lance ton script <code>hello.sh</code> chaque nuit à 2 heures, quand personne ne travaille. Léa insiste sur un point : root ne doit jamais exécuter un fichier que quelqu'un d'autre peut modifier."},
             "desc": "Créez <code>/etc/cron.d/backup-lab</code> qui exécute chaque jour à 2h00, en tant que root, une copie de <code>~/hello.sh</code> que seul root peut modifier (ni le fichier, ni aucun de ses dossiers ne doivent être modifiables par un autre utilisateur).",
             "hints": ["Qui peut modifier <code>/home/etudiant/hello.sh</code> ? Si ce n'est pas seulement root, planifiez une copie placée dans un dossier système.", "<code>sudo install -m 755 ~/hello.sh /usr/local/sbin/hello</code>, puis la ligne cron : horaire, utilisateur, chemin absolu."],
             "checks": [
                 ('test -f /etc/cron.d/backup-lab', "/etc/cron.d/backup-lab n'existe pas."),
                 ('[ "$(owner /etc/cron.d/backup-lab)" = root ] && no_gow /etc/cron.d/backup-lab && eol_ok /etc/cron.d/backup-lab', "Le fichier doit appartenir à root, n'être modifiable ni par le groupe ni par les autres, et se terminer par un retour à la ligne (sinon cron ignore la dernière ligne)."),
                 ('l=$(cron_line /etc/cron.d/backup-lab); cron_is "$l" 0 2 "*" "*" "*" && [ "$(echo "$l" | awk \'{print $6}\')" = root ]', "L'horaire ou l'utilisateur ne conviennent pas : tous les jours à 2h00, en root."),
                 ('p=$(cron_prog "$(cron_line /etc/cron.d/backup-lab)"); [[ $p == /* ]] && [ -f "$p" ] && cmp -s "$p" $H/hello.sh', "La commande planifiée n'est pas le chemin absolu d'une copie de ~/hello.sh."),
                 ('p=$(cron_prog "$(cron_line /etc/cron.d/backup-lab)"); root_only "$p"', "Le script planifié, ou l'un de ses dossiers, peut être modifié par un autre utilisateur que root : il pourrait faire exécuter n'importe quoi à root."),
             ]},
            {"id": "18.3", "points": 4, "title": "Nettoyage quotidien", "manual": True,
             "ticket": {"from": "lea", "body": "<code>/tmp</code> se remplit de fichiers <code>.tmp</code> oubliés. Mets en place un nettoyage quotidien, mais qui ne supprime <strong>que</strong> ceux-là : certaines applications gardent d'autres fichiers dans <code>/tmp</code>."},
             "desc": "Placez dans <code>/etc/cron.daily/</code> un script <code>nettoyage-tmp</code> qui supprime les fichiers <code>*.tmp</code> de <code>/tmp</code> (et seulement eux). Vérifiez avec <code>run-parts --test /etc/cron.daily</code> qu'il sera bien exécuté.",
             "hints": ["Après avoir créé le script, vérifiez avec <code>run-parts --test</code> : s'il n'apparaît pas, relisez les pièges du cours (nom et droits).", "Pas d'extension <code>.sh</code> ; le script doit être exécutable."],
             "checks": [
                 ('run-parts --test /etc/cron.daily | grep -qx /etc/cron.daily/nettoyage-tmp', "run-parts ne lancera pas /etc/cron.daily/nettoyage-tmp (nom incorrect ou fichier non exécutable)."),
                 ('touch /tmp/lab-a.tmp /tmp/lab-b.txt && timeout 10 /etc/cron.daily/nettoyage-tmp; r=0; [ ! -e /tmp/lab-a.tmp ] || r=1; [ -e /tmp/lab-b.txt ] || r=1; rm -f /tmp/lab-a.tmp /tmp/lab-b.txt; exit $r', "Le script doit supprimer les .tmp de /tmp sans toucher aux autres fichiers."),
             ]},
            {"id": "18.4", "points": 4, "title": "Lire l'heure en cron",
             "ticket": {"from": "julien", "body": "Je dois planifier quatre tâches et je m'emmêle complètement dans les champs… Tu peux m'écrire les horaires ?"},
             "desc": "Écrivez dans <code>~/cron-quiz.txt</code> une ligne par horaire, les 5 champs seulement, dans cet ordre :<ol><li>toutes les 10 minutes, du lundi au vendredi, de 8h00 à 18h50 ;</li><li>le 1<sup>er</sup> et le 15 de chaque mois, à 23h45 ;</li><li>chaque dimanche à minuit ;</li><li>à 6h00 le premier jour de chaque trimestre (1<sup>er</sup> janvier, avril, juillet et octobre).</li></ol>",
             "hints": ["Une plage s'écrit <code>a-b</code>, une liste <code>a,b</code>, un pas <code>*/n</code> ; les jours de la semaine vont de 0 (dimanche) à 6.", "Ligne 1 : le pas porte sur le champ des minutes, la plage d'heures sur celui des heures. Ligne 4 : une liste de mois."],
             "checks": [
                 ('test -s $H/cron-quiz.txt', "~/cron-quiz.txt est absent ou vide."),
                 ('cron_is "$(grep -vE "^\\s*(#|$)" $H/cron-quiz.txt | sed -n 1p)" "*/10" 8-18 "*" "*" 1-5', "La ligne 1 (toutes les 10 minutes en semaine) ne correspond pas."),
                 ('cron_is "$(grep -vE "^\\s*(#|$)" $H/cron-quiz.txt | sed -n 2p)" 45 23 1,15 "*" "*"', "La ligne 2 (le 1er et le 15 du mois) ne correspond pas."),
                 ('cron_is "$(grep -vE "^\\s*(#|$)" $H/cron-quiz.txt | sed -n 3p)" 0 0 "*" "*" 0', "La ligne 3 (chaque dimanche à minuit) ne correspond pas."),
                 ('cron_is "$(grep -vE "^\\s*(#|$)" $H/cron-quiz.txt | sed -n 4p)" 0 6 1 1,4,7,10 "*"', "La ligne 4 (chaque trimestre) ne correspond pas."),
             ]},
            {"id": "18.5", "points": 4, "title": "Le pourcentage maudit", "manual": True,
             "ticket": {"from": "julien", "body": "J'ai ajouté dans ta crontab une tâche qui note l'heure dans <code>~/heure.log</code> chaque minute. Dans le terminal, la commande marche parfaitement… mais le fichier reste désespérément vide ! Je n'y comprends rien."},
             "desc": "Réparez la tâche de Julien : <code>~/heure.log</code> doit recevoir chaque minute une ligne au format <code>HH:MM</code>.",
             "hints": ["Regardez ce que cron a réellement lancé : <code>grep CRON /var/log/syslog</code>. La commande est-elle complète ?", "Dans une ligne de crontab, <code>%</code> a un sens particulier (<code>man 5 crontab</code>) : il faut l'échapper."],
             "checks": [
                 ('crontab -l -u etudiant 2>/dev/null | grep -vE "^\\s*#" | grep -q heure.log', "La tâche de Julien n'est plus dans votre crontab."),
                 ('f=$H/heure.log; a=$(grep -cE "^[0-9]{2}:[0-9]{2}$" $f 2>/dev/null); cron_run etudiant - heure.log; b=$(grep -cE "^[0-9]{2}:[0-9]{2}$" $f 2>/dev/null); [ "$b" -eq $((a + 1)) ] && tail -n1 $f | grep -qE "^[0-9]{2}:[0-9]{2}$"', "Exécutée exactement comme le fait cron, la tâche n'ajoute pas une ligne HH:MM à ~/heure.log."),
             ]},
            {"id": "18.6", "points": 5, "title": "Ça marche dans mon terminal", "manual": True,
             "ticket": {"from": "thomas", "body": "Mon script <code>~/verif-deploy.sh</code> marche parfaitement quand je le lance dans mon terminal. Mais lancé par cron chaque minute, il écrit des lignes à moitié vides dans <code>~/verif-deploy.log</code>. Ça me rend fou."},
             "desc": "Faites en sorte que, lancé par cron, <code>verif-deploy.sh</code> écrive des lignes qui se terminent par <code>projet=linux-lab Bonjour !</code>. Il utilise la variable <code>PROJET</code> et la commande <code>bonjour</code> de l'étape 15.",
             "hints": ["Quel environnement a une tâche cron ? Comparez <code>env</code> dans votre terminal et dans une tâche (<code>* * * * * env &gt; /tmp/env-cron.txt</code>).", "cron ne lit pas ~/.bashrc : définissez PROJET et un PATH complet en tête de crontab, ou dans le script (chemin absolu de bonjour)."],
             "checks": [
                 ('crontab -l -u etudiant 2>/dev/null | grep -vE "^\\s*#" | grep -q verif-deploy.sh', "La tâche qui lance verif-deploy.sh n'est plus dans votre crontab."),
                 ('cron_run etudiant - verif-deploy.sh; tail -n1 $H/verif-deploy.log 2>/dev/null | grep -q "projet=linux-lab Bonjour !$"', "Exécuté exactement comme le fait cron (environnement minimal, sans ~/.bashrc), verif-deploy.sh n'écrit pas une ligne complète."),
             ]},
            {"id": "18.7", "points": 5, "title": "Où sont passées les erreurs ?", "manual": True,
             "ticket": {"from": "lea", "body": "Aminata ne reçoit plus l'export de la comptabilité, et la tâche <code>/etc/cron.d/export-compta</code> ne laisse aucune trace : ni fichier, ni message. Commence par faire en sorte qu'on voie ce qu'elle raconte. Ensuite seulement, on répare."},
             "desc": "Modifiez la tâche pour que sa sortie <strong>et ses erreurs</strong> s'ajoutent à <code>/var/log/export-compta.log</code>. Laissez-la s'exécuter, lisez l'erreur, puis corrigez sa cause pour que la tâche réussisse.",
             "hints": ["Sans serveur de messagerie, cron jette la sortie des tâches (voyez <code>grep CRON /var/log/syslog</code>). Il faut rediriger deux flux : la sortie standard et la sortie d'erreur.", "<code>… &gt;&gt; /var/log/export-compta.log 2&gt;&amp;1</code> à la fin de la ligne ; attendez une minute, puis lisez le journal."],
             "checks": [
                 ('l=$(cron_line /etc/cron.d/export-compta); [[ $l == *export-compta*">>"*/var/log/export-compta.log* && $l == *"2>&1"* ]] && [ "$(echo "$l" | awk \'{print $6}\')" = root ]', "La tâche (toujours en root) n'ajoute pas sa sortie et ses erreurs à /var/log/export-compta.log."),
                 ('grep -q "ERREUR" /var/log/export-compta.log 2>/dev/null', "Le journal ne contient pas encore l'erreur de la tâche : laissez cron l'exécuter au moins une fois avant de corriger quoi que ce soit."),
                 ('cron_run root /etc/cron.d/export-compta export-compta; tail -n1 /var/log/export-compta.log | grep -q "export OK"', "Exécutée exactement comme le fait cron, la tâche ne réussit pas encore : lisez l'erreur capturée et corrigez sa cause."),
             ]},
            {"id": "18.8", "points": 5, "title": "Tâches qui s'empilent", "manual": True,
             "ticket": {"from": "lea", "body": "La synchronisation du catalogue dure deux minutes et demie, et cron la relance chaque minute : plusieurs synchronisations tournent en même temps et se marchent dessus (regarde <code>/var/log/sync-catalogue.log</code>). Il ne doit jamais y en avoir plus d'une à la fois."},
             "desc": "Modifiez <code>/etc/cron.d/sync-catalogue</code> pour qu'une nouvelle exécution abandonne immédiatement si la précédente n'est pas terminée. La tâche doit toujours s'exécuter en root.",
             "hints": ["Il faut un verrou : une instance le prend en démarrant ; si le verrou est déjà pris, la suivante abandonne aussitôt.", "<code>flock -n /run/lock/sync-catalogue.lock /usr/local/sbin/sync-catalogue</code> dans la ligne cron (<code>man flock</code>)."],
             "checks": [
                 ('l=$(cron_line /etc/cron.d/sync-catalogue); [[ $l == *sync-catalogue* ]] && [ "$(echo "$l" | awk \'{print $6}\')" = root ]', "La tâche de synchronisation n'est plus planifiée en root dans /etc/cron.d/sync-catalogue."),
                 ('cmd=$(cron_line /etc/cron.d/sync-catalogue | awk \'{for (i = 7; i <= NF; i++) printf "%s ", $i}\');L=/var/log/sync-catalogue.log; pkill -f "sbin/sync-catalogu[e]"; pkill -f "^sleep 150$"; sleep 0.5; touch $L; b=$(grep -c début $L); (setsid sh -c "$cmd" >/dev/null 2>&1 </dev/null &); sleep 1.5; timeout 5 sh -c "$cmd" >/dev/null 2>&1 </dev/null; rc=$?; sleep 0.5; a=$(grep -c début $L); pkill -f "sbin/sync-catalogu[e]"; pkill -f "^sleep 150$"; [ $((a - b)) -eq 1 ] && [ $rc -ne 124 ]', "Lancée deux fois de suite, la tâche démarre deux synchronisations en parallèle, n'en démarre aucune, ou la seconde attend au lieu d'abandonner : une seule instance doit tourner, et la suivante doit renoncer aussitôt."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    19: {
        "title": "Surveillance du système",
        "description": "Disque, mémoire, processeur, processus : repérez ce qui consomme les ressources, et les pièges du conteneur.",
        "lesson": r"""<h3>Espace disque</h3><pre>df -h           # partitions<br>du -sh /var/*   # taille des sous-dossiers<br>find /var -size +100M     # fichiers de plus de 100 Mio</pre><h3>Mémoire et charge</h3><pre>free -h         # mémoire : totale, utilisée, disponible, swap<br>uptime          # durée de fonctionnement + charge moyenne (1, 5, 15 min)<br>nproc           # nombre de processeurs<br>vmstat 1 5      # 5 mesures, une par seconde</pre><p>La <strong>charge</strong> (load average) est le nombre moyen de processus qui réclament le processeur : à comparer au nombre de cœurs (<code>nproc</code>). Une charge de 4 sur 8 cœurs est confortable ; sur 1 cœur, c'est une file d'attente.</p><div class="tip"><strong>Piège du conteneur :</strong> <code>free</code>, <code>top</code> et <code>uptime</code> lisent <code>/proc</code>, qui décrit la machine <strong>hôte</strong> tout entière. Les limites propres au conteneur (mémoire, processeur) sont appliquées par le noyau grâce aux <strong>cgroups</strong>, et se lisent sous <code>/sys/fs/cgroup/</code>. Quand la limite de mémoire est atteinte, le noyau tue un processus (l'<em>OOM killer</em>).</div><h3>Processus gourmands</h3><pre>top                          # M : trier par mémoire, P : par processeur, q : quitter<br>ps aux --sort=-%cpu | head   # ps sait trier sur n'importe quelle colonne<br>ps -o pid,ni,%cpu,rss,cmd -p 1234</pre><p><code>%MEM</code> est calculé par rapport à la mémoire de l'hôte ; <code>RSS</code> donne la mémoire réellement occupée, en Kio.</p><h3>États des processus</h3><p>Colonne <code>STAT</code> de <code>ps</code> : <code>R</code> en cours d'exécution, <code>S</code> endormi, <code>D</code> en attente d'une entrée-sortie, <code>T</code> arrêté, <code>Z</code> <strong>zombie</strong> : terminé, mais son parent n'a pas encore lu son code de retour. <code>ps -eo pid,ppid,stat,cmd</code> affiche le parent de chaque processus (PPID).</p><h3>Priorité</h3><p><code>renice -n 10 -p PID</code> change la gentillesse d'un processus déjà lancé (de -20, le plus prioritaire, à 19). Seul root peut la baisser ou toucher aux processus des autres.</p><h3>Fichiers ouverts</h3><pre>lsof -p PID          # fichiers ouverts par un processus<br>lsof /chemin         # qui a ouvert ce fichier ?</pre><p>Un fichier supprimé alors qu'un programme l'a encore ouvert continue d'occuper le disque jusqu'à sa fermeture : <code>df</code> ne baisse pas. <code>lsof</code> sait lister ces fichiers (cherchez « link count » dans son manuel), et <code>/proc/PID/fd/</code> contient un lien vers chaque fichier ouvert par un processus.</p><div class="tip">Sur un vrai serveur, <code>systemctl status service</code> affiche en plus la mémoire et les processus d'un service. Ce conteneur n'a pas systemd.</div>""",
        "volatile": True,
        "setup": r'''
if first_run 19; then
  rm -f $REF/env-19
  # 19.3 : un gros fichier oublié sous /var
  rm -rf /var/cache/catalogue; mkdir -p /var/cache/catalogue
  f=/var/cache/catalogue/export-$(rword).bak
  head -c 45M /dev/zero > $f
  done_once 19
fi
reemit 19
cat > /usr/local/bin/data-cruncher <<'EOF'
#!/bin/bash
x=$(head -c 30000000 /dev/zero | tr '\0' 'x')
while true; do sleep 5; done
EOF
chmod 755 /usr/local/bin/data-cruncher
pkill -x data-cruncher || true
setsid nohup /usr/local/bin/data-cruncher >/dev/null 2>&1 < /dev/null &
# 19.5 : un processus qui accapare le processeur (nom tiré au hasard, conservé après redémarrage)
cpu=$(sed -n 's/^CPUNAME=//p' $REF/env-19 2>/dev/null || true)
if [ -z "$cpu" ]; then cpu=$(printf '%s\n' indexeur-photos calcul-stats vignettes-gen reindex-cat | shuf -n1); echo "CPUNAME=$cpu" >> $REF/env-19; emit CPUNAME "$cpu"; fi
cat > /usr/local/bin/$cpu <<'EOF'
#!/bin/bash
# Traitement gourmand (il s'arrête de lui-même au bout de deux heures)
while [ $SECONDS -lt 7200 ]; do for ((i = 0; i < 2000; i++)); do :; done; sleep 0.08; done
EOF
chmod 755 /usr/local/bin/$cpu
for n in indexeur-photos calcul-stats vignettes-gen reindex-cat; do pkill -x $n || true; done
setsid /usr/local/bin/$cpu >/dev/null 2>&1 < /dev/null &
# 19.6 : un fichier supprimé mais toujours ouvert
cat > /usr/local/bin/cache-vignettes <<'EOF'
#!/bin/bash
exec 3>/var/tmp/cache-vignettes.bin
head -c 40M /dev/zero >&3
rm -f /var/tmp/cache-vignettes.bin
while true; do sleep 60 3>&-; done
EOF
chmod 755 /usr/local/bin/cache-vignettes
pkill -x cache-vignettes || true
setsid /usr/local/bin/cache-vignettes >/dev/null 2>&1 < /dev/null &
# 19.7 : un parent qui ne récupère jamais la fin de ses enfants
mkdir -p /usr/local/lib/lab; putbin /bin/sleep /usr/local/lib/lab/collect-stats
pkill -x collect-stats || true
setsid bash -c 'for i in 1 2 3 4 5; do /bin/sleep 0.2 & done; exec /usr/local/lib/lab/collect-stats infinity' >/dev/null 2>&1 < /dev/null &
sleep 3
emit PID "$(pgrep -x data-cruncher | head -n1)"
emit CPUPID "$(pgrep -x "$cpu" | head -n1)"
emit CACHEPID "$(pgrep -x cache-vignettes | head -n1)"
emit ZPARENT "$(pgrep -x collect-stats | head -n1)"
''',
        "exercises": [
            {"id": "19.1", "points": 4, "title": "Rapport système", "manual": True,
             "ticket": {"from": "sophie", "body": "J'aimerais un rapport sur l'état du serveur que je puisse consulter quand je veux : date, espace disque, mémoire et charge. Un script qui le régénère à chaque lancement, sans empiler les anciens rapports, serait parfait."},
             "desc": "Créez <code>~/rapport.sh</code> (exécutable) qui génère <code>~/rapport-systeme.txt</code> contenant la date, l'espace disque (<code>df -h</code>), la mémoire (<code>free -h</code>) et la charge (<code>uptime</code>). Chaque exécution <strong>remplace</strong> le rapport précédent, quel que soit le dossier d'où on lance le script.",
             "hints": ["Un bloc <code>{ cmd1; cmd2; }</code> redirige la sortie de plusieurs commandes d'un coup ; <code>&gt;</code> remplace le fichier, <code>&gt;&gt;</code> ajoute à la fin.", "Utilisez un chemin absolu (ou <code>$HOME</code>) : le script est lancé depuis un autre dossier."],
             "checks": [
                 ('test -x $H/rapport.sh', "~/rapport.sh n'existe pas ou n'est pas exécutable."),
                 ('touch /tmp/.lab-t && run_as etudiant "cd /tmp && timeout 10 $H/rapport.sh" && [ $H/rapport-systeme.txt -nt /tmp/.lab-t ]', "Le script ne (re)crée pas ~/rapport-systeme.txt (attention aux chemins relatifs : il est lancé depuis /tmp)."),
                 ('f=$H/rapport-systeme.txt; grep -q "$(date +%Y)" $f && grep -q Mem $f && grep -qi filesystem $f && grep -q "load average" $f', "Le rapport doit contenir la date, et la sortie de df -h, free -h et uptime."),
                 ('f=$H/rapport-systeme.txt; n1=$(wc -l < $f); run_as etudiant "cd /tmp && timeout 10 $H/rapport.sh"; n2=$(wc -l < $f); [ "$n1" -eq "$n2" ] && [ "$(grep -c "load average" $f)" -eq 1 ]', "Deux exécutions successives s'accumulent dans le rapport : chaque exécution doit remplacer le rapport précédent."),
             ]},
            {"id": "19.2", "points": 3, "title": "Le glouton",
             "ticket": {"from": "thomas", "body": "La boutique est lente et je pense qu'un processus consomme bien plus de mémoire qu'il ne devrait. Tu peux trouver lequel ? Donne-moi son PID."},
             "desc": "Un processus consomme beaucoup plus de mémoire que les autres. Écrivez son <strong>PID</strong> dans <code>~/gourmand.txt</code>.",
             "hints": ["ps sait trier sa sortie selon n'importe quelle colonne ; RSS (ou %MEM) mesure la mémoire occupée.", "<code>ps aux --sort=-rss | head</code>, ou <code>top</code> puis <kbd>M</kbd>."],
             "checks": [
                 ('[ -n "$LAB_PID" ]', "Le processus de l'exercice n'a pas démarré : rechargez la page."),
                 ('[ "$(ans $H/gourmand.txt)" = "$LAB_PID" ]', "Ce n'est pas le PID du processus le plus gourmand en mémoire."),
             ]},
            {"id": "19.3", "points": 4, "title": "Le plus gros de /var",
             "ticket": {"from": "lea", "body": "<code>/var</code> grossit anormalement. Trouve-moi le plus gros <strong>fichier</strong> qui s'y cache : c'est par lui qu'on commencera l'enquête."},
             "desc": "Quel est le plus gros fichier sous <code>/var</code> ? Écrivez son chemin complet dans <code>~/plus-gros-var.txt</code>.",
             "hints": ["find sait sélectionner des fichiers selon leur taille (<code>-size</code>) ; certains dossiers ne sont lisibles qu'avec sudo.", "<code>sudo find /var -type f -size +10M</code>, ou <code>sudo du -ah /var | sort -h | tail</code>."],
             "checks": [
                 ('[ "$(ans $H/plus-gros-var.txt)" = "$(find /var -xdev -type f -printf "%s %p\\n" 2>/dev/null | sort -n | tail -n1 | cut -d" " -f2-)" ]', "Ce n'est pas le chemin complet du plus gros fichier de /var."),
             ]},
            {"id": "19.4", "points": 4, "title": "Le vrai plafond",
             "ticket": {"from": "lea", "body": "<code>free -h</code> annonce des gigaoctets de mémoire libre, mais l'hébergeur affirme que ce serveur n'a droit qu'à une petite fraction de la machine. Qui ment ? Trouve la vraie limite."},
             "desc": "Écrivez dans <code>~/limite-memoire.txt</code> la limite de mémoire réellement imposée à ce serveur, en Mio (le nombre seul).",
             "hints": ["Ce serveur est un conteneur : sa limite est appliquée par le noyau (les cgroups), et free ne la voit pas.", "Cherchez sous <code>/sys/fs/cgroup</code> un fichier <code>memory.max</code> (cgroup v2) ou <code>memory/memory.limit_in_bytes</code> (cgroup v1), puis divisez par 1 048 576."],
             "checks": [
                 ('f=/sys/fs/cgroup/memory.max; [ -r $f ] || f=/sys/fs/cgroup/memory/memory.limit_in_bytes; v=$(cat $f); [[ $v =~ ^[0-9]+$ ]] && a=$(ans $H/limite-memoire.txt) && a=${a%Mio} && a=${a%Mi} && a=${a%M} && [ "$a" = "$((v / 1048576))" ]', "Ce n'est pas la limite de mémoire imposée au conteneur (en Mio)."),
             ]},
            {"id": "19.5", "points": 4, "title": "Le mangeur de processeur",
             "ticket": {"from": "thomas", "body": "Un traitement accapare le processeur et la boutique rame. On ne peut pas l'arrêter, il doit finir sa tâche, mais il faut qu'il passe après tout le reste."},
             "desc": "Un processus consomme bien plus de processeur que les autres. Sans l'arrêter, donnez-lui une gentillesse (<em>niceness</em>) de <code>15</code>, et écrivez son nom dans <code>~/cpu.txt</code>.",
             "hints": ["<code>top</code> trie par consommation de processeur ; sa colonne NI affiche la gentillesse de chaque processus.", "<code>sudo renice -n 15 -p PID</code> (le processus appartient à root)."],
             "checks": [
                 ('[ -n "$LAB_CPUPID" ]', "Le processus de l'exercice n'a pas démarré : rechargez la page."),
                 ('[ "$(ans $H/cpu.txt)" = "$LAB_CPUNAME" ]', "Ce n'est pas le nom du processus qui consomme le plus de processeur."),
                 ('kill -0 "$LAB_CPUPID"', "Le processus a été arrêté : il fallait seulement baisser sa priorité (rechargez la page pour le relancer)."),
                 ('[ "$(ps -o ni= -p "$LAB_CPUPID" | tr -d " ")" = 15 ]', "La gentillesse du processus n'est pas de 15."),
             ]},
            {"id": "19.6", "points": 5, "title": "L'espace qui ne revient pas",
             "ticket": {"from": "sophie", "body": "J'ai supprimé l'énorme fichier de cache des vignettes dans <code>/var/tmp</code>, et <code>df</code> affiche exactement la même place occupée ! Explique-moi… et récupère cette place, mais sans arrêter le programme qui l'utilise : il tourne pour la boutique."},
             "desc": "Écrivez dans <code>~/cache-pid.txt</code> le PID du processus qui retient l'espace du fichier supprimé, puis libérez cet espace <strong>sans arrêter ce processus</strong>.",
             "hints": ["Un fichier supprimé mais encore ouvert existe toujours pour le processus qui le tient : lsof sait lister les fichiers dont le nombre de liens est tombé à 0.", "<code>sudo lsof +L1</code> ; le fichier reste accessible par <code>/proc/PID/fd/N</code> : on peut le vider (<code>sudo truncate -s 0 …</code>)."],
             "checks": [
                 ('[ -n "$LAB_CACHEPID" ]', "Le processus de l'exercice n'a pas démarré : rechargez la page."),
                 ('[ "$(ans $H/cache-pid.txt)" = "$LAB_CACHEPID" ]', "Ce n'est pas le PID du processus qui retient le fichier supprimé."),
                 ('kill -0 "$LAB_CACHEPID"', "Le processus a été arrêté : il fallait libérer l'espace sans l'interrompre (rechargez la page pour le relancer)."),
                 ('s=$(stat -L -c %s /proc/$LAB_CACHEPID/fd/3 2>/dev/null); [ -n "$s" ] && [ "$s" -lt 1048576 ]', "Le fichier supprimé occupe toujours de la place : il est encore ouvert, et toujours aussi gros."),
             ]},
            {"id": "19.7", "points": 4, "title": "Les zombies",
             "ticket": {"from": "lea", "body": "<code>top</code> signale des processus « zombie ». J'ai essayé de les tuer avec <code>kill -9</code> : rien à faire, ils sont toujours là. Tu sais comment on s'en débarrasse ?"},
             "desc": "Écrivez dans <code>~/parent-zombies.txt</code> le PID du processus <strong>parent</strong> des zombies, puis faites disparaître les zombies.",
             "hints": ["Un zombie est déjà mort : aucun signal ne peut le tuer. C'est son parent qui aurait dû « récupérer » sa fin.", "<code>ps -eo pid,ppid,stat,cmd</code> (état Z), puis agissez sur le processus parent : quand il disparaît, le processus n° 1 récupère ses zombies."],
             "checks": [
                 ('[ -n "$LAB_ZPARENT" ]', "Le processus de l'exercice n'a pas démarré : rechargez la page."),
                 ('[ "$(ans $H/parent-zombies.txt)" = "$LAB_ZPARENT" ]', "Ce n'est pas le PID du parent des zombies."),
                 ('sleep 1; ! ps -eo stat=,comm= | grep -qE "^Z\\S*\\s+sleep"', "Des processus zombies sont toujours présents."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    20: {
        "title": "Gestion des logs",
        "description": "Lisez, filtrez, analysez et faites tourner les journaux, y compris ceux d'un service qui les garde ouverts.",
        "lesson": r"""<h3>Où sont les logs ?</h3><pre>/var/log/syslog    — messages système (rsyslog)<br>/var/log/auth.log  — authentification (sudo, ssh, su…)<br>/var/log/apt/      — installations de paquets</pre><p>Beaucoup de journaux ne sont lisibles que par root ou le groupe <code>adm</code> : utilisez <code>sudo</code>.</p><div class="tip"><strong>Sur un vrai serveur Ubuntu</strong>, la plupart des services écrivent aussi (ou seulement) dans le journal de <strong>systemd</strong>, qu'on lit avec <code>journalctl</code> : <code>journalctl -u ssh</code> (un service), <code>journalctl -p err --since today</code> (les erreurs du jour), <code>journalctl -f</code> (en direct). Ce conteneur n'a pas systemd : ici, rsyslog écrit tout dans des fichiers de <code>/var/log</code>, et les techniques de filtrage sont les mêmes.</div><h3>Lire et filtrer</h3><pre>tail -n 20 /var/log/syslog<br>tail -f /var/log/syslog          # en temps réel (Ctrl+C pour sortir)<br>less +F /var/log/syslog          # idem, mais on peut remonter (Ctrl+C, puis q)<br>grep "\[CRIT\]" autre.log         # les crochets doivent être échappés…<br>grep -F "[CRIT]" autre.log       # … ou recherche littérale avec -F<br>grep -oE 'user=[a-z]+' f         # n'affiche que la partie qui correspond</pre><h3>Journaux tournés</h3><p>Après rotation, les anciens journaux s'appellent <code>app.log.1</code>, <code>app.log.2.gz</code>… <code>zcat</code>, <code>zgrep</code> et <code>zless</code> lisent les fichiers compressés sans les décompresser sur le disque.</p><h3>Écrire dans syslog</h3><pre>logger "Message"<br>logger -p user.warning "Attention"</pre><p>Chaque message porte une <strong>étiquette</strong> (par défaut, votre nom d'utilisateur), une <strong>facility</strong> (auth, cron, user, local0 à local7…) et un <strong>niveau</strong> (debug, info, notice, warning, err, crit…). rsyslog range les messages selon des règles <code>facility.niveau destination</code>, dans <code>/etc/rsyslog.conf</code> et <code>/etc/rsyslog.d/*.conf</code>. Après une modification, rsyslog doit être <strong>redémarré</strong> (un simple signal HUP ne relit pas les règles) : <code>sudo systemctl restart rsyslog</code> sur un vrai serveur ; dans ce conteneur sans systemd, <code>sudo pkill -x rsyslogd; sudo rsyslogd</code>.</p><h3>auth.log</h3><p>On y trouve les connexions SSH, sudo, su… Chaque tentative de connexion peut y laisser plusieurs lignes (utilisateur invalide, échec PAM, échec du mot de passe, fermeture) : pour compter des tentatives, choisissez <strong>un seul</strong> type de ligne.</p><h3>logrotate</h3><p>Fait « tourner » les journaux pour qu'ils ne remplissent pas le disque. Une configuration dans <code>/etc/logrotate.d/</code> :</p><pre>/var/log/exemple/*.log {<br>    weekly          # fréquence (daily, weekly, monthly)<br>    rotate 4        # nombre d'archives conservées<br>    missingok       # pas d'erreur si le fichier manque<br>    notifempty      # ne pas faire tourner un fichier vide<br>}</pre><p>Autres directives : <code>compress</code> et <code>delaycompress</code>, <code>create 0640 root adm</code> (droits du nouveau fichier), <code>copytruncate</code> (copier puis vider le journal au lieu de le renommer), <code>postrotate … endscript</code> (commandes lancées après la rotation), <code>su utilisateur groupe</code>.</p><div class="tip">Un programme qui garde son journal ouvert continue d'écrire dans l'ancien fichier, même renommé en <code>.1</code> : il faut soit ne pas renommer le fichier, soit demander au programme de rouvrir son journal après la rotation.</div><p><code>sudo logrotate -d /etc/logrotate.d/exemple</code> teste une configuration sans rien modifier ; <code>-f</code> force une rotation immédiate.</p>""",
        "volatile": True,
        "setup": r'''
demo=0
if first_run 20; then
  rm -f $REF/env-20
  mkdir -p /var/log/app
  f=/var/log/app/app.log; : > $f
  for d in 13 14 15 16; do
    for i in $(seq 1 $((RANDOM % 20 + 25))); do
      r=$((RANDOM % 10))
      if [ $r -lt 6 ]; then lvl=INFO; elif [ $r -lt 8 ]; then lvl=WARNING; else lvl=ERROR; fi
      printf '2026-03-%s %02d:%02d:%02d [%s] requête %d traitée\n' $d $((RANDOM % 24)) $((RANDOM % 60)) $((RANDOM % 60)) $lvl $RANDOM >> $f
    done
    printf '2026-03-%s 23:59:59 [INFO] bilan : aucune ERROR bloquante\n' $d >> $f
  done
  sort -o $f $f
  chown root:adm $f; chmod 640 $f
  kemit 20 NERR "$(grep -c '\[ERROR\]' $f)"
  grep '^2026-03-15 .*\[ERROR\]' $f > $REF/s20-erreurs15
  # 20.6 : une nuit d'attaque par force brute sur SSH
  mkdir -p /var/log/lab; A=/var/log/lab/auth.log; tmp=$(mktemp)
  ts() { printf '%02d:%02d:%02d' $((RANDOM % 6)) $((RANDOM % 60)) $((RANDOM % 60)); }
  fail() { # fail IP COMPTE
    local p=$((RANDOM % 50000 + 10000)) s=$((RANDOM % 9000 + 1000)) t=$(ts) u=$2 w=$2
    case $2 in root|deploy|ubuntu) ;; *) w="invalid user $2"; echo "Sep 28 $t linux-lab sshd[$s]: Invalid user $2 from $1 port $p" >> $tmp ;; esac
    [ $((RANDOM % 3)) = 0 ] && echo "Sep 28 $t linux-lab sshd[$s]: pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=$1  user=$u" >> $tmp
    echo "Sep 28 $t linux-lab sshd[$s]: Failed password for $w from $1 port $p ssh2" >> $tmp
    [ $((RANDOM % 2)) = 0 ] && echo "Sep 28 $t linux-lab sshd[$s]: Connection closed by authenticating user $u $1 port $p [preauth]" >> $tmp
    return 0
  }
  comptes=(root admin test oracle postgres ubuntu git deploy guest ftp)
  atk="203.0.113.$((RANDOM % 200 + 20))"; nat=$((RANDOM % 30 + 60))
  vis=($(printf '%s\n' "${comptes[@]}" | shuf -n $((RANDOM % 3 + 4))))
  : > $REF/s20-comptes
  for i in $(seq $nat); do u=${vis[RANDOM % ${#vis[@]}]}; echo "$u" >> $REF/s20-comptes; fail $atk $u; done
  sort -u -o $REF/s20-comptes $REF/s20-comptes
  for j in 1 2 3 4 5; do ip="198.51.100.$((RANDOM % 200 + 20))"; for i in $(seq $((RANDOM % 20 + 10))); do fail $ip ${comptes[RANDOM % 10]}; done; done
  for i in $(seq 12); do echo "Sep 28 $(ts) linux-lab sshd[$((RANDOM % 9000 + 1000))]: Accepted publickey for deploy from 192.0.2.10 port $((RANDOM % 50000 + 10000)) ssh2: ED25519 SHA256:q8Hf2kPzV1dXw4" >> $tmp; done
  sort -k3,3 $tmp > $A; rm -f $tmp; chown root:adm $A; chmod 640 $A
  kemit 20 ATK_IP "$atk"
  kemit 20 ATK_N "$(grep -c "Failed password .* from $atk port" $A)"
  # 20.7 : les journaux de la boutique ont tourné plusieurs fois
  B=/var/log/boutique; rm -rf $B; mkdir -p $B; tmp=$(mktemp -d)
  for d in 12 13 14 15 16; do
    for i in $(seq $((RANDOM % 25 + 30))); do
      r=$((RANDOM % 10)); if [ $r -lt 6 ]; then lvl=INFO; elif [ $r -lt 8 ]; then lvl=WARNING; else lvl=ERROR; fi
      printf '2026-03-%s %02d:%02d:%02d [%s] commande %d\n' $d $((RANDOM % 24)) $((RANDOM % 60)) $((RANDOM % 60)) $lvl $RANDOM
    done > $tmp/d$d
    printf '2026-03-%s 11:30:00 [INFO] reprise après une ERROR réseau\n' $d >> $tmp/d$d
    sort -o $tmp/d$d $tmp/d$d
  done
  cp $tmp/d12 $B/shop.log.3
  { cat $tmp/d13; awk '$2 < "12"' $tmp/d14; } > $B/shop.log.2
  { awk '$2 >= "12"' $tmp/d14; cat $tmp/d15; } > $B/shop.log.1
  cp $tmp/d16 $B/shop.log
  kemit 20 N14 "$(grep -c '^2026-03-14 .*\[ERROR\]' $tmp/d14)"
  gzip -f $B/shop.log.3 $B/shop.log.2
  rm -rf $tmp; chown -R root:adm $B; chmod 755 $B; chmod 640 $B/*
  # 20.8 : le journal de la caisse
  rm -rf /var/log/caisse; mkdir -p /var/log/caisse
  rm -f /etc/logrotate.d/caisse
  demo=1
  # 20.9 : la facility du module de paiement est tirée au sort
  rm -f /var/log/paiement.log
  v=${LAB_VARIANTE_20_9:-$((RANDOM % 4))}
  fac=(local0 local3 local5 local6); fac=${fac[v]}
  mkdir -p /etc/paiement
  printf '# Module de paiement : journalisation\nSYSLOG_TAG=paiement\nSYSLOG_FACILITY=%s\n' "$fac" > /etc/paiement/module.conf
  chmod 644 /etc/paiement/module.conf
  kemit 20 FACILITE "$fac"
  done_once 20
fi
reemit 20
cat > /usr/local/sbin/journal-caisse <<'EOF'
#!/bin/bash
# Service de caisse : enregistre les ventes dans son journal, qu'il garde ouvert.
# Sur le signal HUP, il ferme puis rouvre son journal (utile après une rotation).
L=/var/log/caisse/caisse.log
echo $$ > /run/journal-caisse.pid
exec 3>>"$L"
trap 'exec 3>&-; exec 3>>"$L"; echo "$(date "+%F %T") journal rouvert" >&3' HUP
while true; do echo "$(date '+%F %T') vente enregistrée n°$RANDOM" >&3; sleep 1 3>&- & wait $!; done
EOF
chmod 755 /usr/local/sbin/journal-caisse
pkill -x journal-caisse || true
setsid /usr/local/sbin/journal-caisse >/dev/null 2>&1 < /dev/null &
sleep 2
if [ $demo = 1 ]; then mv -f /var/log/caisse/caisse.log /var/log/caisse/caisse.log.1; fi
emit CAISSE_PID "$(pgrep -x journal-caisse | head -n1)"
''',
        "exercises": [
            {"id": "20.1", "points": 3, "title": "Écrire dans syslog",
             "ticket": {"from": "lea", "body": "Nos scripts de sauvegarde vont écrire dans le journal système. Pour qu'on retrouve leurs messages d'un coup d'œil, ils porteront tous l'étiquette <code>cimes-backup</code>. Fais un essai, et vérifie qu'il est bien arrivé."},
             "desc": "Envoyez dans le journal système le message <code>Test de journalisation</code> avec l'étiquette <code>cimes-backup</code>, puis retrouvez-le dans <code>/var/log/syslog</code>.",
             "hints": ["Une commande du cours envoie un message au journal système ; son manuel explique comment choisir l'étiquette (<em>tag</em>).", "<code>logger -t …</code>, puis <code>sudo grep cimes-backup /var/log/syslog</code>."],
             "checks": [
                 (r'''grep -qE '[[:space:]]cimes-backup(\[[0-9]+\])?: Test de journalisation$' /var/log/syslog''', "Le message « Test de journalisation » avec l'étiquette cimes-backup n'apparaît pas dans /var/log/syslog."),
             ]},
            {"id": "20.2", "points": 4, "title": "Compter les erreurs",
             "ticket": {"from": "thomas", "body": "L'application a eu une mauvaise semaine. Combien d'erreurs contient son journal <code>/var/log/app/app.log</code> ?"},
             "desc": "Combien d'entrées de niveau <code>[ERROR]</code> contient <code>/var/log/app/app.log</code> ? Écrivez le nombre dans <code>~/error-count.txt</code>.",
             "hints": ["Le fichier n'est lisible qu'avec sudo (ou par le groupe adm).", "Relisez quelques lignes : le mot ERROR apparaît-il uniquement comme niveau ? Comptez les niveaux, pas les mots."],
             "checks": [
                 ('[ "$(ans $H/error-count.txt)" = "$LAB_NERR" ]', "Ce n'est pas le bon nombre d'entrées de niveau [ERROR]."),
             ]},
            {"id": "20.3", "points": 3, "title": "Les erreurs du 15 mars",
             "ticket": {"from": "thomas", "body": "Un client s'est plaint d'un bug le 15 mars. Sors-moi toutes les erreurs de ce jour-là, que je les analyse."},
             "desc": "Extrayez toutes les lignes <code>[ERROR]</code> du <strong>15 mars 2026</strong> de <code>/var/log/app/app.log</code> dans <code>~/erreurs-15.txt</code>.",
             "hints": ["Chaque ligne commence par la date : un motif ancré au début de la ligne (<code>^</code>) évite les faux positifs.", "Un seul motif pour la date et le niveau, avec <code>.*</code> entre les deux (et des crochets échappés)."],
             "checks": [
                 ('test -s $H/erreurs-15.txt && diff -q $H/erreurs-15.txt $REF/s20-erreurs15', "Le fichier ne contient pas exactement les lignes d'erreur du 15 mars."),
             ]},
            {"id": "20.4", "points": 5, "title": "Analyseur de logs", "manual": True,
             "ticket": {"from": "lea", "body": "Je passe mon temps à compter les niveaux de gravité dans les journaux. Un script qui fait ce décompte pour n'importe quel fichier de log nous ferait gagner un temps fou."},
             "desc": "Créez <code>~/log-analyzer.sh</code> qui prend un fichier de log en argument et affiche trois lignes <code>INFO: n</code>, <code>WARNING: n</code> et <code>ERROR: n</code> : le nombre d'entrées de chaque niveau, repéré par <code>[NIVEAU]</code> en majuscules.",
             "hints": ["Pour chaque niveau, comptez les lignes qui contiennent le niveau entre crochets ; le fichier à analyser est le premier argument du script.", "<code>grep -c '\\[INFO\\]' \"$1\"</code> ; une boucle <code>for</code> sur les trois niveaux évite de répéter le code."],
             "checks": [
                 ('test -x $H/log-analyzer.sh', "~/log-analyzer.sh n'existe pas ou n'est pas exécutable."),
                 (r'''ok=1; for k in 1 2; do f=/tmp/lab-analyse-$k-$RANDOM.log; { for i in $(seq $((RANDOM % 9))); do echo "2026-04-0$k 10:00:0$i [INFO] requête $RANDOM"; done; [ $k = 1 ] && for i in $(seq $((RANDOM % 6 + 1))); do echo "2026-04-0$k 11:00:0$i [WARNING] lenteur"; done; for i in $(seq $((RANDOM % 7 + 1))); do echo "2026-04-0$k 12:00:0$i [ERROR] échec"; done; echo "2026-04-0$k 13:00:00 [INFO] reprise après une ERROR"; echo "2026-04-0$k 14:00:00 [DEBUG] WARNING ignoré"; echo "2026-04-0$k 15:00:00 [error] en minuscules, ne compte pas"; } | shuf > $f; chmod 644 $f; o=$(run_as etudiant "timeout 5 $H/log-analyzer.sh $f" 2>/dev/null); for l in INFO WARNING ERROR; do n=$(grep -c "\[$l\]" $f); echo "$o" | grep -qE "^$l\s*:\s*$n\s*$" || ok=0; done; rm -f $f; done; [ $ok = 1 ]''', "Testé sur deux journaux générés au hasard, le script n'affiche pas les bons comptes (trois lignes INFO: n, WARNING: n, ERROR: n)."),
             ]},
            {"id": "20.5", "points": 4, "title": "Rotation des logs",
             "ticket": {"from": "lea", "body": "Les journaux de l'application ne sont jamais archivés et vont finir par remplir le disque. Mets en place une rotation quotidienne : on garde une semaine d'archives, compressées."},
             "desc": "Créez <code>/etc/logrotate.d/app-lab</code> pour que <code>/var/log/app/*.log</code> tourne <strong>chaque jour</strong>, en gardant <strong>7</strong> archives <strong>compressées</strong>.",
             "hints": ["Un bloc de configuration commence par le motif des fichiers visés, puis contient une directive par ligne entre accolades : cherchez dans <code>man logrotate</code> celles qui fixent la fréquence, le nombre d'archives et la compression.", "Testez à blanc avec <code>sudo logrotate -d /etc/logrotate.d/app-lab</code>."],
             "checks": [
                 ('test -f /etc/logrotate.d/app-lab && logrotate -d /etc/logrotate.d/app-lab 2>&1 | grep -q "/var/log/app/"', "La configuration est absente, ou logrotate ne la comprend pas."),
                 (r'''grep -qE "^\s*daily\b" /etc/logrotate.d/app-lab''', "La rotation doit être quotidienne."),
                 (r'''d=$(mktemp -d /tmp/lab-rot-XXXXXX); sed "s#/var/log/app/#$d/#g" /etc/logrotate.d/app-lab > $d/conf; echo debut > $d/app.log; for i in $(seq 9); do logrotate -f -s $d/state $d/conf >/dev/null 2>&1; echo "passage $i" > $d/app.log; done; ok=1; for i in 2 3 4 5 6 7; do [ -f $d/app.log.$i.gz ] || ok=0; done; { [ -f $d/app.log.1.gz ] || [ -f $d/app.log.1 ]; } || ok=0; [ -e $d/app.log.8.gz ] || [ -e $d/app.log.8 ] && ok=0; rm -rf $d; [ $ok = 1 ]''', "En faisant tourner votre configuration plusieurs fois sur un journal de test, on n'obtient pas exactement 7 archives compressées."),
             ]},
            {"id": "20.6", "points": 5, "title": "Force brute",
             "ticket": {"from": "sophie", "body": "L'assureur pense qu'on a subi une attaque par force brute sur SSH la nuit dernière. Il veut savoir d'où elle venait, son ampleur, et quels comptes étaient visés. Le journal est dans <code>/var/log/lab/auth.log</code>."},
             "desc": "Dans <code>~/attaquant.txt</code>, écrivez l'adresse IP qui a fait le plus de tentatives de mot de passe <strong>échouées</strong>, suivie de ce nombre (ex. <code>10.1.2.3 42</code>). Dans <code>~/comptes-vises.txt</code>, la liste des comptes visés par cette adresse, un par ligne, sans doublon.",
             "hints": ["Repérez la forme exacte des lignes d'échec de mot de passe, puis isolez le champ de l'adresse. D'autres lignes contiennent aussi l'adresse de l'attaquant : ne les comptez pas.", "<code>sudo grep 'Failed password' … | grep -oE 'from [0-9.]+' | sort | uniq -c | sort -rn</code> ; pour les comptes, « invalid user » décale les champs : prenez le mot qui précède « from »."],
             "checks": [
                 ('read -r ip n x < $H/attaquant.txt; [ "$ip" = "$LAB_ATK_IP" ]', "Ce n'est pas l'adresse qui a le plus souvent échoué."),
                 ('read -r ip n x < $H/attaquant.txt; [ "$n" = "$LAB_ATK_N" ]', "L'adresse est la bonne, mais pas le nombre de tentatives de mot de passe échouées."),
                 ('setcmp $H/comptes-vises.txt "cat $REF/s20-comptes"', "La liste des comptes visés par cette adresse n'est pas exacte."),
             ]},
            {"id": "20.7", "points": 4, "title": "Journaux tournés",
             "ticket": {"from": "thomas", "body": "Un client a eu des soucis le 14 mars. Depuis, le journal de la boutique a tourné plusieurs fois… Combien d'erreurs en tout ce jour-là ?"},
             "desc": "Les journaux de la boutique sont dans <code>/var/log/boutique/</code> : <code>shop.log</code> et ses versions tournées, dont certaines compressées. Écrivez dans <code>~/erreurs-14.txt</code> le nombre total d'entrées <code>[ERROR]</code> du 14 mars 2026.",
             "hints": ["Un journal tourné puis compressé se lit sans le décompresser sur le disque ; les erreurs du 14 peuvent être réparties dans plusieurs fichiers.", "<code>sudo zgrep</code> (ou <code>zcat -f</code>, qui lit aussi les fichiers non compressés) sur <code>shop.log*</code>, puis comptez."],
             "checks": [
                 ('[ "$(ans $H/erreurs-14.txt)" = "$LAB_N14" ]', "Ce n'est pas le bon total : toutes les versions du journal ont-elles été lues, compressées comprises ?"),
             ]},
            {"id": "20.8", "points": 5, "title": "Rotation d'un journal ouvert", "manual": True,
             "ticket": {"from": "lea", "body": "On a testé une rotation à la main de <code>/var/log/caisse/caisse.log</code>, et depuis, le service de caisse écrit dans <code>caisse.log.1</code> ! Il faut une configuration logrotate qui marche avec ce service, sans jamais l'arrêter. Bonne nouvelle : il rouvre son journal quand il reçoit le signal HUP (son PID est dans <code>/run/journal-caisse.pid</code>)."},
             "desc": "Écrivez <code>/etc/logrotate.d/caisse</code> : rotation quotidienne de <code>/var/log/caisse/caisse.log</code> avec 5 archives, et, après chaque rotation, les nouvelles lignes du service doivent arriver dans <code>caisse.log</code>, sans redémarrer le service.",
             "hints": ["Le service garde son fichier ouvert : après un renommage, il écrit toujours dans le même fichier… qui s'appelle maintenant .1. Deux solutions : ne pas renommer (copier puis vider), ou demander au service de rouvrir son journal.", "<code>copytruncate</code>, ou un bloc <code>postrotate</code> … <code>endscript</code> qui envoie HUP au PID lu dans /run/journal-caisse.pid."],
             "checks": [
                 ('[ -n "$LAB_CAISSE_PID" ] && kill -0 "$LAB_CAISSE_PID"', "Le service de caisse ne tourne plus : rechargez la page pour le relancer."),
                 ('test -f /etc/logrotate.d/caisse && logrotate -d /etc/logrotate.d/caisse 2>&1 | grep -q /var/log/caisse/caisse.log', "La configuration est absente, ou ne concerne pas /var/log/caisse/caisse.log."),
                 (r'''c=/etc/logrotate.d/caisse; grep -qE '^\s*daily\b' $c && grep -qE '^\s*rotate\s+5\b' $c''', "La rotation doit être quotidienne et garder 5 archives."),
                 ('f=/var/log/caisse/caisse.log; kill -HUP "$LAB_CAISSE_PID"; sleep 1.5; t=$(date +%s); logrotate -f -s /tmp/lab-caisse.state /etc/logrotate.d/caisse >/dev/null 2>&1; sleep 3; rm -f /tmp/lab-caisse.state; test -s $f && { [ -e $f.1 ] || [ -e $f.1.gz ]; } && [ "$(stat -c %Y $f)" -ge "$t" ]', "Après une rotation forcée, les nouvelles lignes du service n'arrivent pas dans caisse.log."),
                 ('kill -0 "$LAB_CAISSE_PID"', "Le service de caisse a été arrêté pendant la rotation : il doit continuer à tourner (rechargez la page pour le relancer)."),
             ]},
            {"id": "20.9", "points": 4, "title": "Un journal dédié", "manual": True,
             "ticket": {"from": "thomas", "body": "Le module de paiement écrit ses messages dans syslog, avec la facility indiquée dans sa configuration, <code>/etc/paiement/module.conf</code>. Noyés au milieu du reste, on ne les retrouve jamais. Il me faudrait un fichier rien que pour eux."},
             "desc": "Faites en sorte que tous les messages de la facility du module de paiement (voir <code>/etc/paiement/module.conf</code>) arrivent dans <code>/var/log/paiement.log</code>, et seulement eux.",
             "hints": ["rsyslog lit des règles « facility.niveau destination » dans /etc/rsyslog.d/*.conf ; après une modification, il faut le redémarrer (voir le cours pour ce conteneur).", "Une ligne <code>FACILITY.* /var/log/paiement.log</code> (avec la facility lue dans la configuration du module) dans un fichier .conf de /etc/rsyslog.d, puis testez avec <code>logger -p FACILITY.info essai</code>."],
             "checks": [
                 ('[ -n "$LAB_FACILITE" ] && m="verif-$RANDOM$RANDOM" && logger -p "$LAB_FACILITE.notice" -t paiement "$m" && sleep 1.5 && grep -q "$m" /var/log/paiement.log 2>/dev/null', "Un message envoyé avec la facility du module de paiement n'arrive pas dans /var/log/paiement.log (la facility est-elle la bonne ? rsyslog a-t-il été redémarré ?)."),
                 ('for f in local0 local3 local5 local6 user; do [ "$f" = "$LAB_FACILITE" ] && continue; m="autre-$RANDOM$RANDOM"; logger -p "$f.notice" -t autre "$m"; sleep 0.3; grep -q "$m" /var/log/paiement.log 2>/dev/null && exit 1; done; exit 0', "Des messages d'autres facilities arrivent aussi dans /var/log/paiement.log : seuls ceux du module de paiement sont attendus."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    21: {
        "title": "Réseau de base",
        "description": "Adresses, réseau et passerelle, ports en écoute et connexions, résolution de noms : diagnostiquer ce qui cloche.",
        "lesson": r"""<h3>Adresses et interfaces</h3><pre>ip a            # interfaces et adresses (ip -4 a : IPv4 seulement)<br>ip route        # table de routage<br>hostname        # nom de la machine<br>hostname -I     # adresses IP</pre><h3>Adresse, masque et réseau</h3><p>Une adresse s'écrit avec la longueur de son <strong>préfixe</strong> : <code>10.8.3.25/16</code>. Les 16 premiers bits (<code>10.8</code>) désignent le <strong>réseau</strong>, les autres la machine. Masque équivalent : <code>255.255.0.0</code>. L'adresse du réseau s'obtient en mettant à 0 les bits de la machine : <code>10.8.0.0/16</code>. Autre exemple : <code>192.168.50.130/24</code> appartient au réseau <code>192.168.50.0/24</code>.</p><p>Plages <strong>privées</strong>, non routées sur Internet : <code>10.0.0.0/8</code>, <code>172.16.0.0/12</code>, <code>192.168.0.0/16</code>. <code>127.0.0.0/8</code> est la boucle locale : la machine elle-même. <code>192.0.2.0/24</code> est réservée aux exemples de documentation.</p><h3>Passerelle</h3><p>Pour joindre une adresse hors de ses réseaux, la machine envoie les paquets à sa <strong>passerelle</strong>, indiquée par la route par défaut de sa table de routage.</p><h3>Ports et connexions</h3><pre>ss -tln           # ports TCP en écoute (t = TCP, u = UDP, l = écoute, n = numérique)<br>sudo ss -tlnp     # … avec le programme (p) : il faut root pour voir ceux des autres<br>ss -tlne          # … avec l'utilisateur propriétaire de chaque socket (uid)<br>ss -tn            # connexions TCP établies (adresse locale et adresse distante)<br>sudo lsof -i :443 # qui utilise ce port ?<br>ps -u alice -o pid,args   # les processus d'un utilisateur, avec leurs arguments</pre><div class="tip"><strong>Dans ce conteneur</strong>, root lui-même ne peut pas examiner les fichiers ouverts par les processus des autres utilisateurs (il lui manque une capacité du noyau, CAP_SYS_PTRACE) : <code>ss -p</code> et <code>lsof</code> n'affichent donc que les processus de root. Sur un vrai serveur, <code>sudo ss -tlnp</code> montre tout.</div><p>L'adresse d'écoute compte : <code>127.0.0.1:5432</code> n'est joignable que depuis la machine elle-même ; <code>0.0.0.0:5432</code> (ou <code>*:5432</code>) l'est depuis toutes ses interfaces, donc potentiellement depuis le réseau.</p><h3>Tester un port</h3><pre>nc -zv 10.0.0.5 22                # la connexion TCP aboutit-elle ? (sans rien envoyer)<br>curl -s http://10.0.0.5:8080/     # interroger un service web</pre><p>« Connection refused » : rien n'écoute à cette adresse sur ce port. Pas de réponse du tout : un pare-feu filtre, ou la machine est injoignable.</p><h3>Résolution de noms</h3><ul><li><code>/etc/nsswitch.conf</code> (ligne <code>hosts:</code>) fixe l'ordre : d'abord <code>files</code> (<code>/etc/hosts</code>), puis <code>dns</code>.</li><li><code>/etc/hosts</code> : correspondances locales, une par ligne (<code>10.0.0.12   intranet</code>). Si un nom y figure deux fois, les programmes obtiennent les deux adresses, et la première est en général utilisée.</li><li><code>/etc/resolv.conf</code> : serveurs DNS (lignes <code>nameserver</code>), interrogés dans l'ordre ; un premier serveur injoignable ralentit chaque résolution de plusieurs secondes.</li><li><code>getent hosts nom</code> (ou <code>getent ahostsv4 nom</code>) teste la résolution comme le font les programmes.</li></ul><div class="tip"><strong>Spécificités du conteneur :</strong> <code>/etc/hosts</code> et <code>/etc/resolv.conf</code> sont fournis par Docker, qui les régénère au redémarrage ; <code>sed -i</code> échoue sur ces fichiers (« Device or resource busy ») : modifiez-les avec un éditeur (<code>sudo nano</code>). Sur un vrai Ubuntu, <code>resolv.conf</code> pointe vers <code>127.0.0.53</code>, le résolveur local de systemd, et <code>resolvectl status</code> montre les vrais serveurs DNS.</div><p>Pas d'accès à Internet ici : on diagnostique ce qui se passe sur la machine.</p>""",
        "volatile": True,
        "setup": r'''
mkuser intrus
fr=0
if first_run 21; then
  fr=1
  rm -f $REF/env-21
  # 21.5 : un serveur DNS injoignable (adresse tirée au sort) en tête de liste
  v=${LAB_VARIANTE_21_5:-$((RANDOM % 4))}
  morts=(192.0.2.53 198.51.100.53 203.0.113.53 192.0.2.254); mort=${morts[v]}
  c=$(grep -vE '^nameserver (192\.0\.2|198\.51\.100|203\.0\.113)\.|^# Serveur DNS de secours \(Marc\)' /etc/resolv.conf || true)
  dns=$(printf '%s\n' "$c" | awk '/^nameserver/ {print $2; exit}')
  kemit 21 DNS "$dns"
  kemit 21 DNS_MORT "$mort"
  { echo "# Serveur DNS de secours (Marc)"; echo "nameserver $mort"; printf '%s\n' "$c"; } > /etc/resolv.conf
  # 21.4 : pourquoi serveur-local ne désigne-t-il pas la bonne machine ? (variante et ancienne adresse tirées au sort)
  v=${LAB_VARIANTE_21_4:-$((RANDOM % 4))}
  vieille="10.$((RANDOM % 200 + 20)).$((RANDOM % 250 + 1)).$((RANDOM % 250 + 2))"
  case $v in
    0) printf '%s     serveur-local   # ancien serveur de test\n192.168.1.100   serveur-local\n' "$vieille" ;;
    1) printf '%s     test-ancien serveur-local\n192.168.1.100   serveur-local\n' "$vieille" ;;
    2) printf '%s     serveur-local   # ancien serveur de test\n#192.168.1.100  serveur-local   # ajouté par Thomas\n' "$vieille" ;;
    3) printf '%s     serveur-local   # ancien serveur de test\n192.168.1.100   serveur-locale\n' "$vieille" ;;
  esac > $REF/s21-local
  # 21.6 : le programme qui squatte le port de la caisse, et son propriétaire (tirés au sort)
  v=${LAB_VARIANTE_21_6:-$((RANDOM % 4))}
  sq=(vieux-proxy:intrus relais-test:julien ancien-cache:webdev proxy-marc:prestataire)
  printf 'SQ_PROG=%s\nSQ_USER=%s\n' "${sq[v]%%:*}" "${sq[v]#*:}" > $REF/s21-squat
  # 21.7 : ce qui limite mini-web à la boucle locale (tiré au sort)
  v=${LAB_VARIANTE_21_7:-$((RANDOM % 3))}
  rm -rf /etc/mini-web.d /etc/default/mini-web
  case $v in
    0) printf '# Configuration de mini-web\nBIND=127.0.0.1\nPORT=8088\n' > /etc/mini-web.conf ;;
    1) printf '# Configuration de mini-web\nBIND=0.0.0.0\nPORT=8088\n' > /etc/mini-web.conf
       mkdir -p /etc/mini-web.d
       printf '# Surcharge locale (Marc, pour ses tests)\nBIND=127.0.0.1\n' > /etc/mini-web.d/90-local.conf ;;
    2) printf '# Configuration de mini-web\nBIND=0.0.0.0\nPORT=8088\n' > /etc/mini-web.conf
       mkdir -p /etc/default
       printf '# Options de démarrage de mini-web (Marc)\nMINIWEB_BIND=127.0.0.1\n' > /etc/default/mini-web ;;
  esac
  # 21.8 : cinq noms de bases de données, une seule répond sur 5432
  ips=($(printf '127.0.0.%s\n' 2 3 4 6 7 | shuf))
  : > $REF/s21-hosts
  for i in 1 2 3 4 5; do echo "${ips[i - 1]}   bdd-$i" >> $REF/s21-hosts; done
  k=$((RANDOM % 5 + 1)); kemit 21 BDD "bdd-$k"
  o=$(( k % 5 + 1 )); p=$(( (k + 1) % 5 + 1 ))
  printf 'PG_IP=%s\nPG5433_IP=%s\nBOUNCER_IP=%s\n' "${ips[k - 1]}" "${ips[o - 1]}" "${ips[p - 1]}" > $REF/s21-bdd
  done_once 21
fi
reemit 21
# /etc/hosts est régénéré par Docker au redémarrage : on remet les entrées de l'exercice
if [ $fr = 1 ] || ! grep -q serveur-loca /etc/hosts; then
  h=$(grep -v serveur-loca /etc/hosts || true); printf '%s\n' "$h" > /etc/hosts
  cat $REF/s21-local >> /etc/hosts
fi
if [ $fr = 1 ] || ! grep -q 'bdd-1' /etc/hosts; then
  h=$(grep -v ' bdd-[0-9]' /etc/hosts || true); printf '%s\n' "$h" > /etc/hosts; cat $REF/s21-hosts >> /etc/hosts
fi
. $REF/s21-bdd
# 21.3 : un port ouvert sur toutes les interfaces
port=$((RANDOM % 1000 + 4000))
putbin /usr/bin/nc.openbsd /usr/local/bin/veilleur
pkill -x veilleur || true
setsid nohup /usr/local/bin/veilleur -lk $port >/dev/null 2>&1 < /dev/null &
# 21.6 : un programme occupe le port de l'appli de caisse
. $REF/s21-squat
mkuser "$SQ_USER"
for x in vieux-proxy relais-test ancien-cache proxy-marc; do pkill -x $x || true; rm -f /usr/local/bin/$x; done
putbin /usr/bin/nc.openbsd /usr/local/bin/$SQ_PROG
cat > /usr/local/bin/appli-caisse <<'EOF'
#!/bin/bash
# Application de caisse : doit écouter sur 127.0.0.1:8081
if ss -Htln 'sport = :8081' | grep -q .; then
    echo "appli-caisse: ERREUR : bind 127.0.0.1:8081 : Address already in use" >&2
    exit 1
fi
echo "appli-caisse : le port 8081 est libre, l'application peut démarrer."
EOF
chmod 755 /usr/local/bin/appli-caisse
su -s /bin/bash "$SQ_USER" -c "setsid /usr/local/bin/$SQ_PROG -lk 127.0.0.1 8081 >/dev/null 2>&1 < /dev/null &"
# 21.7 : mini-web, un petit service HTTP et son script de contrôle
cat > /usr/local/sbin/mini-web <<'EOF'
#!/bin/bash
# mini-web : répond « mini-web OK » en HTTP
# Configuration : /etc/mini-web.conf, puis les surcharges de /etc/mini-web.d/*.conf,
# puis les options de démarrage de /etc/default/mini-web (MINIWEB_BIND remplace BIND)
. /etc/mini-web.conf
for f in /etc/mini-web.d/*.conf; do [ -r "$f" ] && . "$f"; done
[ -r /etc/default/mini-web ] && . /etc/default/mini-web
BIND=${MINIWEB_BIND:-$BIND}
echo $$ > /run/mini-web.pid
while true; do
    printf 'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nmini-web OK\n' | nc -N -l "$BIND" "$PORT" >/dev/null 2>&1 || sleep 1
done
EOF
cat > /usr/local/sbin/mini-web-ctl <<'EOF'
#!/bin/bash
# Contrôle de mini-web : start | stop | restart | status
P=/run/mini-web.pid
arreter() {
    local p; p=$(cat $P 2>/dev/null)
    if [ -n "$p" ] && tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q mini-web; then kill -- -"$p" 2>/dev/null; sleep 0.5; fi
    rm -f $P
}
demarrer() { setsid /usr/local/sbin/mini-web >/dev/null 2>&1 < /dev/null & sleep 0.5; }
case "$1" in
    start)   demarrer; echo "mini-web démarré" ;;
    stop)    arreter; echo "mini-web arrêté" ;;
    restart) arreter; demarrer; echo "mini-web redémarré" ;;
    status)  if [ -f $P ] && kill -0 "$(cat $P)" 2>/dev/null; then echo "mini-web tourne (PID $(cat $P))"; else echo "mini-web est arrêté"; fi ;;
    *)       echo "Usage : $0 start|stop|restart|status" >&2; exit 1 ;;
esac
EOF
chmod 755 /usr/local/sbin/mini-web /usr/local/sbin/mini-web-ctl
/usr/local/sbin/mini-web-ctl restart >/dev/null
# 21.8 : les serveurs de base de données
putbin /usr/bin/nc.openbsd /usr/local/bin/pg-serveur
pkill -x pg-serveur || true
for spec in "$PG_IP 5432" "$PG5433_IP 5433" "$BOUNCER_IP 6432"; do setsid /usr/local/bin/pg-serveur -lk $spec >/dev/null 2>&1 < /dev/null & done
# 21.9 : une connexion sortante permanente vers le port 4444
putbin /usr/bin/nc.openbsd /usr/local/bin/relais-distant
putbin /usr/bin/nc.openbsd /usr/local/bin/maj-auto
pkill -x maj-auto || true; pkill -x relais-distant || true
setsid /usr/local/bin/relais-distant -lk 127.0.0.5 4444 >/dev/null 2>&1 < /dev/null &
sleep 0.5
setsid sh -c "sleep 1000000 | /usr/local/bin/maj-auto 127.0.0.5 4444 >/dev/null 2>&1" >/dev/null 2>&1 < /dev/null &
sleep 1
emit PORT "$port"
emit MAJ_PID "$(pgrep -x maj-auto | head -n1)"
emit SQ_PROG "$SQ_PROG"
emit SQ_USER "$SQ_USER"
''',
        "exercises": [
            {"id": "21.1", "points": 4, "title": "Mon adresse IP",
             "ticket": {"from": "sophie", "body": "Le prestataire qui installe le nouveau pare-feu me demande l'adresse IP du serveur, et le réseau sur lequel il se trouve (adresse du réseau et longueur du préfixe)."},
             "desc": "Écrivez l'adresse IPv4 de l'interface <code>eth0</code>, sans le préfixe, dans <code>~/mon-ip.txt</code>, et l'adresse de son réseau suivie de la longueur du préfixe (ex. <code>10.8.0.0/16</code>) dans <code>~/reseau.txt</code>.",
             "hints": ["L'adresse s'affiche avec la longueur de son préfixe (/xx) : elle indique combien de bits, en partant de la gauche, désignent le réseau.", "<code>ip -4 addr show eth0</code> ; l'adresse du réseau garde ces bits et met les autres à 0 (la table de routage affiche aussi le réseau local)."],
             "checks": [
                 ('[ "$(ans $H/mon-ip.txt)" = "$(ip -4 -o addr show eth0 | awk \'{print $4}\' | cut -d/ -f1)" ]', "Ce n'est pas l'adresse IPv4 de eth0 (sans le /xx)."),
                 ('c=$(ip -4 -o addr show eth0 | awk \'{print $4}\'); p=${c#*/}; IFS=. read -r a b x y <<< "${c%/*}"; n=$(( (a << 24) | (b << 16) | (x << 8) | y )); m=$(( p == 0 ? 0 : (0xFFFFFFFF << (32 - p)) & 0xFFFFFFFF )); n=$(( n & m )); [ "$(ans $H/reseau.txt)" = "$((n >> 24 & 255)).$((n >> 16 & 255)).$((n >> 8 & 255)).$((n & 255))/$p" ]', "Ce n'est pas l'adresse du réseau de eth0 suivie de la longueur de son préfixe."),
             ]},
            {"id": "21.2", "points": 2, "title": "Passerelle par défaut",
             "ticket": {"from": "sophie", "body": "Il lui faut aussi l'adresse du routeur par lequel le serveur sort de son réseau."},
             "desc": "Écrivez l'adresse de la passerelle par défaut du serveur dans <code>~/passerelle.txt</code>.",
             "hints": ["Pour joindre une adresse hors de ses réseaux, la machine passe par sa route par défaut : affichez sa table de routage.", "<code>ip route</code> : la ligne <code>default via …</code>"],
             "checks": [
                 ('[ "$(ans $H/passerelle.txt)" = "$(ip route | awk \'/^default/ {print $3; exit}\')" ]', "Ce n'est pas l'adresse de la passerelle par défaut."),
             ]},
            {"id": "21.3", "points": 4, "title": "Le port mystère",
             "ticket": {"from": "lea", "body": "Un programme écoute sur toutes les interfaces réseau du serveur alors qu'on n'a rien ouvert de tel. Sur quel port ? C'est peut-être une porte d'entrée pour un attaquant."},
             "desc": "Un programme écoute sur un port TCP <strong>sur toutes les interfaces</strong> (adresse <code>0.0.0.0</code>). Écrivez ce numéro de port dans <code>~/port-mystere.txt</code>.",
             "hints": ["Listez les ports TCP en écoute avec leur adresse : seules certaines adresses signifient « toutes les interfaces ».", "Un port lié à <code>127.0.0.x</code> n'est joignable que depuis la machine elle-même ; cherchez <code>0.0.0.0</code> (ou <code>*</code>)."],
             "checks": [
                 ('[ -n "$LAB_PORT" ]', "Le programme de l'exercice n'a pas démarré : rechargez la page."),
                 ('[ "$(ans $H/port-mystere.txt)" = "$LAB_PORT" ]', "Ce n'est pas le bon port."),
             ]},
            {"id": "21.4", "points": 4, "title": "Résolution locale",
             "ticket": {"from": "thomas", "body": "Pour mes tests, <code>serveur-local</code> doit désigner <code>192.168.1.100</code> sur cette machine. J'ai ajouté une ligne dans <code>/etc/hosts</code>, mais mes programmes continuent de se connecter à une autre adresse !"},
             "desc": "Faites en sorte que <code>serveur-local</code> soit résolu en <code>192.168.1.100</code> sur cette machine, et <strong>uniquement</strong> en cette adresse.",
             "hints": ["Testez ce que le système obtient : <code>getent hosts serveur-local</code>. Puis relisez /etc/hosts en entier, caractère par caractère : quelles lignes mentionnent ce nom (même comme deuxième nom d'une adresse), et la ligne de Thomas est-elle vraiment prise en compte ?", "Corrigez avec un éditeur (<code>sudo nano /etc/hosts</code>) : dans ce conteneur, <code>sed -i</code> échoue sur ce fichier. Il doit rester une seule correspondance pour ce nom, la bonne."],
             "checks": [
                 ('[ "$(timeout 5 getent ahostsv4 serveur-local | awk \'{print $1}\' | sort -u)" = 192.168.1.100 ]', "serveur-local n'est pas résolu uniquement en 192.168.1.100."),
             ]},
            {"id": "21.5", "points": 4, "title": "Le DNS qui ne répond pas",
             "ticket": {"from": "lea", "body": "Depuis que Marc a « amélioré » la configuration DNS, chaque résolution d'un nom absent de <code>/etc/hosts</code> met plusieurs secondes. Trouve le serveur DNS qui ne répond pas, et débarrasse-nous-en, sans toucher à celui qui fonctionne."},
             "desc": "Écrivez dans <code>~/dns-injoignable.txt</code> l'adresse du serveur DNS qui ne peut pas répondre, puis retirez-le de la configuration, en gardant celui qui fonctionne.",
             "hints": ["Les serveurs DNS sont interrogés dans l'ordre où ils sont déclarés, et chaque requête attend le premier avant de passer au suivant.", "Regardez <code>/etc/resolv.conf</code> : les plages 192.0.2.0/24, 198.51.100.0/24 et 203.0.113.0/24 sont réservées à la documentation, jamais routées. Retirez la ligne fautive avec un éditeur (<code>sudo nano</code>)."],
             "checks": [
                 ('[ -n "$LAB_DNS_MORT" ] && [ "$(ans $H/dns-injoignable.txt)" = "$LAB_DNS_MORT" ]', "Ce n'est pas l'adresse du serveur DNS qui ne peut pas répondre."),
                 ('! grep -qE "^\\s*nameserver\\s+${LAB_DNS_MORT//./\\.}\\s*$" /etc/resolv.conf && grep -qE "^\\s*nameserver\\s+$LAB_DNS\\s*$" /etc/resolv.conf', "La configuration DNS contient encore le serveur injoignable, ou ne contient plus le bon serveur."),
             ]},
            {"id": "21.6", "points": 4, "title": "Qui squatte le port ?",
             "ticket": {"from": "thomas", "body": "L'appli de caisse refuse de démarrer : <code>appli-caisse</code> dit « Address already in use » sur le port 8081. Quelqu'un occupe notre port ! Qui ?"},
             "desc": "Écrivez dans <code>~/squatteur.txt</code> le nom du programme qui occupe le port 8081 et l'utilisateur qui l'a lancé (ex. <code>programme utilisateur</code>), puis arrêtez-le pour que <code>appli-caisse</code> puisse démarrer.",
             "hints": ["Dans ce conteneur, <code>ss -p</code> ne montre que les processus de root (voir le cours) ; mais ss sait aussi afficher l'utilisateur propriétaire de chaque socket.", "<code>ss -tlne 'sport = :8081'</code> donne l'uid ; <code>getent passwd UID</code>, puis <code>ps -u utilisateur -o pid,args</code> pour trouver le programme, et <code>sudo kill PID</code>."],
             "checks": [
                 ('[ -n "$LAB_SQ_PROG" ] && grep -qw -- "$LAB_SQ_PROG" $H/squatteur.txt && grep -qw -- "$LAB_SQ_USER" $H/squatteur.txt', "~/squatteur.txt ne contient pas le nom du programme qui occupe le port 8081 et l'utilisateur qui l'a lancé."),
                 ('! ss -Htln "sport = :8081" | grep -q .', "Le port 8081 est toujours occupé."),
             ]},
            {"id": "21.7", "points": 5, "title": "Joignable seulement de l'intérieur",
             "ticket": {"from": "thomas", "body": "Mon service <code>mini-web</code> répond bien quand je fais <code>curl http://127.0.0.1:8088</code> sur le serveur. Mais en utilisant l'adresse IP du serveur, comme le fera le répartiteur de charge : « connection refused ». Pourtant il tourne !"},
             "desc": "Faites en sorte que <code>mini-web</code> réponde aussi sur l'adresse IP de <code>eth0</code>, port 8088 (testez avec <code>curl http://ADRESSE:8088</code>). Sa configuration principale est <code>/etc/mini-web.conf</code>, mais l'en-tête du script <code>/usr/local/sbin/mini-web</code> indique tous les fichiers qu'il lit ; il se pilote avec <code>sudo mini-web-ctl start|stop|restart|status</code>.",
             "hints": ["Comparez l'adresse sur laquelle le service écoute (<code>ss -tln</code>) avec celle que vous interrogez, puis cherchez d'où vient cette adresse : le script mini-web charge plusieurs fichiers dans un ordre précis, et le dernier qui fixe une valeur l'emporte.", "<code>0.0.0.0</code> signifie « toutes les interfaces » (on peut aussi indiquer l'adresse de eth0) : corrigez la valeur là où elle est réellement fixée, puis <code>sudo mini-web-ctl restart</code>."],
             "checks": [
                 ('ip=$(ip -4 -o addr show eth0 | awk \'{print $4}\' | cut -d/ -f1); curl -s --max-time 3 "http://$ip:8088/" | grep -q "mini-web OK"', "mini-web ne répond pas sur l'adresse IP de eth0, port 8088."),
             ]},
            {"id": "21.8", "points": 4, "title": "Quelle base répond ?",
             "ticket": {"from": "lea", "body": "L'application doit se connecter à la base PostgreSQL (port 5432), mais Marc a laissé cinq noms dans <code>/etc/hosts</code> : <code>bdd-1</code> à <code>bdd-5</code>. Un seul serveur accepte vraiment les connexions sur ce port. Lequel ?"},
             "desc": "Écrivez dans <code>~/bdd-active.txt</code> le nom (<code>bdd-1</code> à <code>bdd-5</code>) de la machine qui accepte les connexions TCP sur le port 5432.",
             "hints": ["Tentez une connexion TCP vers chaque nom sur le port 5432, sans rien envoyer (une option de nc). Ou comparez les adresses en écoute avec /etc/hosts.", "<code>for h in bdd-1 bdd-2 bdd-3 bdd-4 bdd-5; do nc -zv -w1 $h 5432; done</code>"],
             "checks": [
                 ('[ "$(ans $H/bdd-active.txt)" = "$LAB_BDD" ]', "Ce n'est pas la machine qui accepte les connexions sur le port 5432."),
             ]},
            {"id": "21.9", "points": 5, "title": "Connexion suspecte",
             "ticket": {"from": "sophie", "body": "La supervision signale une connexion permanente depuis ce serveur vers le port 4444 d'une autre machine — un port classique des outils de piratage. Trouve quel programme l'a ouverte, et coupe-la."},
             "desc": "Écrivez dans <code>~/connexion.txt</code> le PID et le nom du programme local qui a établi une connexion vers le port 4444 d'une autre adresse (ex. <code>1234 programme</code>), puis arrêtez ce programme. Dans ce lab, la « machine distante » est simulée par l'adresse <code>127.0.0.5</code>.",
             "hints": ["ss affiche aussi les connexions établies, pas seulement les ports en écoute ; avec root, il indique le programme de chacune. Repérez celle dont l'adresse <em>distante</em> se termine par <code>:4444</code>.", "<code>sudo ss -tnp</code> : la colonne « Peer Address:Port » donne l'adresse distante, <code>users:((…))</code> le programme et son PID."],
             "checks": [
                 ('[ -n "$LAB_MAJ_PID" ]', "Le programme de l'exercice n'a pas démarré : rechargez la page."),
                 ('grep -qw "$LAB_MAJ_PID" $H/connexion.txt && grep -qw maj-auto $H/connexion.txt', "~/connexion.txt ne contient pas le PID et le nom du programme qui a ouvert la connexion."),
                 ('! kill -0 "$LAB_MAJ_PID" 2>/dev/null', "Le programme qui a ouvert la connexion tourne toujours."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    22: {
        "title": "SSH et accès distant",
        "description": "Clés, authentification sans mot de passe, configuration du client, restrictions et durcissement du serveur.",
        "lesson": r"""<h3>Connexion</h3><p>Un serveur SSH tourne sur cette machine. Un compte <code>deploy</code> (mot de passe <code>deploy123</code>) y est disponible : on s'entraîne sur <code>localhost</code> comme sur un serveur distant. Un second serveur SSH, qui joue le rôle du serveur de <strong>production</strong>, écoute sur le port 2222.</p><pre>ssh deploy@localhost<br>ssh -p 2222 deploy@localhost</pre><h3>Authentification par clé</h3><pre>ssh-keygen -t ed25519                 # crée ~/.ssh/id_ed25519 (privée) et id_ed25519.pub (publique)<br>ssh-copy-id deploy@localhost          # ajoute la clé publique au authorized_keys du compte distant<br>ssh -i ~/.ssh/autre_cle deploy@localhost   # utiliser une clé précise</pre><div class="tip">La clé <strong>privée</strong> ne quitte jamais votre machine. Une <strong>passphrase</strong> la chiffre sur le disque ; <code>ssh-agent</code> la garde ensuite déverrouillée le temps de la session. Pour des tâches automatiques, on utilise une clé sans passphrase… mais strictement restreinte.</div><h3>Qui exige quels droits ?</h3><ul><li>Le <strong>client</strong> <code>ssh</code> refuse d'utiliser une clé privée lisible par d'autres (« UNPROTECTED PRIVATE KEY FILE ») : <code>600</code> (ou <code>400</code>).</li><li>Le <strong>serveur</strong> <code>sshd</code> (option <code>StrictModes</code>, activée par défaut) ignore <code>authorized_keys</code> si ce fichier, le dossier <code>~/.ssh</code> <strong>ou le dossier personnel</strong> sont modifiables par le groupe ou par les autres. Recommandé : <code>~/.ssh</code> en <code>700</code> et <code>authorized_keys</code> en <code>600</code>.</li><li>Côté serveur, les refus sont expliqués dans <code>/var/log/auth.log</code> ; côté client, avec <code>ssh -v</code>.</li></ul><h3>~/.ssh/config</h3><pre>Host sauvegarde<br>    HostName 10.0.0.42<br>    User backup<br>    Port 2200<br>    IdentityFile ~/.ssh/cle_sauvegarde</pre><p>Puis simplement : <code>ssh sauvegarde</code>. <code>ssh -G sauvegarde</code> affiche la configuration finale.</p><h3>Transférer des fichiers</h3><pre>scp rapport.pdf backup@10.0.0.42:/srv/depot/<br>scp -r dossier sauvegarde:</pre><h3>Empreinte du serveur</h3><p>À la première connexion, ssh mémorise la clé du serveur dans <code>~/.ssh/known_hosts</code>. Si elle change ensuite, il refuse de se connecter (« REMOTE HOST IDENTIFICATION HAS CHANGED ») : c'est peut-être une attaque… ou une réinstallation. On compare alors l'empreinte annoncée à celle de la vraie clé (<code>ssh-keygen -lf fichier.pub</code>) avant d'oublier l'ancienne (<code>ssh-keygen -R hôte</code>). On ne désactive jamais la vérification.</p><h3>Restreindre une clé</h3><p>Dans <code>authorized_keys</code>, des options peuvent précéder une clé : <code>from="10.0.0.0/8"</code> (d'où elle peut servir), <code>command="…"</code> (commande imposée), <code>no-pty</code>, <code>no-port-forwarding</code>… Voir la section AUTHORIZED_KEYS FILE FORMAT de <code>man sshd</code>.</p><h3>Durcir le serveur</h3><p>Dans <code>/etc/ssh/sshd_config</code>, par exemple :</p><pre>PasswordAuthentication no<br>PermitRootLogin no<br>MaxAuthTries 3</pre><p>sshd sait aussi refuser des comptes nommément, ou n'accepter qu'une liste de comptes (<code>man sshd_config</code>). Puis : <code>sudo sshd -t</code> (vérifie la syntaxe), <code>sudo sshd -T</code> (affiche la configuration <strong>effective</strong>) et rechargement : <code>sudo service ssh reload</code> dans ce conteneur, <code>sudo systemctl reload ssh</code> sur un vrai serveur.</p><div class="tip"><code>sshd_config</code> commence par <code>Include /etc/ssh/sshd_config.d/*.conf</code> : ces fichiers sont lus <strong>en premier</strong>, et pour la plupart des options, c'est la <strong>première valeur lue</strong> qui l'emporte.</div><div class="tip">Faites le durcissement <strong>en dernier</strong> : une fois les mots de passe désactivés, <code>ssh-copy-id</code> ne fonctionne plus !</div>""",
        "volatile": True,
        "setup": r'''
if first_run 22; then
  rm -f $REF/env-22
  mkuser deploy
  echo 'deploy:deploy123' | chpasswd
  mkdir -p $H/a-envoyer
  echo "Livrable $(rword) du $(date +%F)" > $H/a-envoyer/livrable.txt
  own $H/a-envoyer
  # 22.6 : la seule commande autorisée au serveur d'intégration continue
  cat > /usr/local/bin/deploy-only <<'EOF'
#!/bin/bash
echo "deploy-only : déploiement de la boutique lancé (commande demandée : ${SSH_ORIGINAL_COMMAND:-aucune})"
EOF
  chmod 755 /usr/local/bin/deploy-only
  # 22.7 : une clé fournie avec de mauvais droits
  mkuser sauvegarde
  mkdir -p $H/cles; rm -f $H/cles/sauvegarde_key $H/cles/sauvegarde_key.pub
  ssh-keygen -q -t ed25519 -N '' -C cle-sauvegarde -f $H/cles/sauvegarde_key
  install -d -m 700 -o sauvegarde -g sauvegarde /home/sauvegarde/.ssh
  install -m 600 -o sauvegarde -g sauvegarde $H/cles/sauvegarde_key.pub /home/sauvegarde/.ssh/authorized_keys
  own $H/cles; chmod 600 $H/cles/sauvegarde_key
  sha256sum /home/sauvegarde/.ssh/authorized_keys > $REF/s22-sauvegarde.sha
  # ce qui empêche ssh d'utiliser la clé est tiré au sort
  v=${LAB_VARIANTE_22_7:-$((RANDOM % 3))}
  case $v in
    0) chmod 644 $H/cles/sauvegarde_key ;;                         # lisible par tous
    1) chown root:root $H/cles/sauvegarde_key ;;                   # illisible pour vous
    2) sed -i 's/$/\r/' $H/cles/sauvegarde_key ;;                   # fins de ligne Windows
  esac
  # 22.8 : intrus a une clé autorisée
  mkuser intrus
  rm -f $REF/intrus_key $REF/intrus_key.pub
  ssh-keygen -q -t ed25519 -N '' -C cle-intrus -f $REF/intrus_key
  install -d -m 700 -o intrus -g intrus /home/intrus/.ssh
  install -m 600 -o intrus -g intrus $REF/intrus_key.pub /home/intrus/.ssh/authorized_keys
  done_once 22
fi
reemit 22
prod_sshd
''',
        "exercises": [
            {"id": "22.1", "points": 3, "title": "Générer une paire de clés",
             "ticket": {"from": "lea", "body": "On va arrêter les mots de passe pour les connexions entre serveurs. Première étape : génère ta paire de clés, en <code>ed25519</code>, c'est le standard aujourd'hui. Sans passphrase pour l'instant : les exercices suivants se connecteront automatiquement."},
             "desc": "Générez une paire de clés <code>ed25519</code> dans <code>~/.ssh/</code> (emplacement par défaut), sans passphrase.",
             "hints": ["ssh-keygen choisit le type de clé avec une option ; aux questions, l'emplacement par défaut convient et la passphrase doit rester vide.", "<code>ssh-keygen -t ed25519</code>, puis Entrée à chaque question."],
             "checks": [
                 ('test -f $H/.ssh/id_ed25519 && grep -q ssh-ed25519 $H/.ssh/id_ed25519.pub', "Les clés ~/.ssh/id_ed25519 et id_ed25519.pub n'existent pas."),
                 ('[ "$(owner $H/.ssh/id_ed25519)" = etudiant ] && [ "$(perm $H/.ssh/id_ed25519)" = 600 ]', "La clé privée doit vous appartenir et avoir les droits 600."),
                 ("ssh-keygen -y -P '' -f $H/.ssh/id_ed25519 >/dev/null 2>&1", "La clé privée est protégée par une passphrase : pour ce lab, il la faut sans (les connexions automatiques des exercices suivants échoueraient)."),
             ]},
            {"id": "22.2", "points": 4, "title": "Connexion sans mot de passe",
             "ticket": {"from": "thomas", "body": "Le compte <code>deploy</code> sert à déployer la boutique. Ce serait pratique que tu puisses t'y connecter par clé, sans taper de mot de passe à chaque fois."},
             "desc": "Faites en sorte de pouvoir vous connecter en <code>deploy@localhost</code> <strong>par clé</strong>, sans taper de mot de passe.",
             "hints": ["Une commande installe votre clé publique dans le authorized_keys du compte distant ; elle vous demandera une dernière fois le mot de passe de deploy.", "<code>ssh-copy-id deploy@localhost</code> (mot de passe : deploy123)"],
             "checks": [
                 ('run_as etudiant "ssh $SSHO deploy@localhost true"', "La connexion par clé à deploy@localhost échoue."),
             ]},
            {"id": "22.3", "points": 4, "title": "Alias SSH",
             "ticket": {"from": "thomas", "body": "Le serveur de production écoute sur le port 2222 (sur <code>localhost</code> dans ce lab). Taper <code>ssh -p 2222 deploy@localhost</code> à longueur de journée, c'est pénible : configure-moi un raccourci pour que <code>ssh prod</code> suffise."},
             "desc": "Configurez <code>~/.ssh/config</code> pour que <code>ssh prod</code> vous connecte, par clé, en <code>deploy</code> sur le serveur de production (<code>localhost</code>, port 2222).",
             "hints": ["Un bloc <code>Host</code> de ~/.ssh/config regroupe les réglages d'un alias : nom de la machine, utilisateur, port…", "<code>Host prod</code>, puis <code>HostName</code>, <code>User</code> et <code>Port</code> ; vérifiez avec <code>ssh -G prod</code>."],
             "checks": [
                 ('c=$(run_as etudiant "ssh -G prod" 2>/dev/null); echo "$c" | grep -qxE "hostname (localhost|127\\.0\\.0\\.1|::1)" && echo "$c" | grep -qx "user deploy" && echo "$c" | grep -qx "port 2222"', "L'alias prod ne désigne pas deploy sur localhost, port 2222."),
                 ('run_as etudiant "ssh $SSHO prod true"', "ssh prod ne parvient pas à se connecter sans mot de passe."),
             ]},
            {"id": "22.4", "points": 3, "title": "Transfert scp",
             "ticket": {"from": "thomas", "body": "Le livrable de la version est prêt dans <code>~/a-envoyer</code>. Copie-le chez <code>deploy</code> avec <code>scp</code>, c'est comme ça qu'on le fera sur les vrais serveurs."},
             "desc": "Avec <code>scp</code>, copiez <code>~/a-envoyer/livrable.txt</code> dans le dossier personnel de <code>deploy</code>.",
             "hints": ["scp s'utilise comme cp, mais l'une des deux extrémités est de la forme <code>hôte:chemin</code> ; votre alias fonctionne aussi avec scp.", "Un « : » sans chemin après l'hôte désigne le dossier personnel distant."],
             "checks": [
                 ('cmp -s $H/a-envoyer/livrable.txt /home/deploy/livrable.txt', "/home/deploy/livrable.txt est absent ou différent de l'original."),
                 ('[ "$(owner /home/deploy/livrable.txt)" = deploy ]', "Le fichier doit appartenir à deploy (copiez-le avec scp, pas avec sudo cp)."),
             ]},
            {"id": "22.5", "points": 5, "title": "Durcir le serveur",
             "ticket": {"from": "sophie", "body": "L'assureur exige qu'on durcisse SSH : plus de connexion par mot de passe, et plus de connexion directe en root. Attention à ne pas te couper l'accès : ta clé doit continuer à fonctionner !"},
             "desc": "Configurez sshd pour <strong>refuser</strong> l'authentification par mot de passe et la connexion directe de root, puis rechargez le service. Votre connexion par clé doit continuer à fonctionner.",
             "hints": ["Les deux réglages se font dans /etc/ssh/sshd_config (avec sudo) ; vérifiez la syntaxe avant de recharger le service.", "<code>sudo sshd -t</code>, <code>sudo sshd -T | grep -i -e password -e rootlogin</code>, puis <code>sudo service ssh reload</code>."],
             "checks": [
                 ('sshd -t', "La configuration de sshd contient une erreur (sudo sshd -t l'affiche) : le service ne pourrait pas redémarrer."),
                 ('sshd -T 2>/dev/null | grep -qx "passwordauthentication no"', "La configuration de sshd autorise encore les mots de passe."),
                 ('sshd -T 2>/dev/null | grep -qx "permitrootlogin no"', "La configuration de sshd n'interdit pas la connexion de root (PermitRootLogin)."),
                 ('! sshpass -p deploy123 ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 deploy@localhost true', "Le serveur accepte encore une connexion par mot de passe : avez-vous rechargé sshd ?"),
                 ('run_as etudiant "ssh $SSHO deploy@localhost true"', "La connexion par clé ne fonctionne plus !"),
             ]},
            {"id": "22.6", "points": 5, "title": "Clé à usage unique",
             "ticket": {"from": "thomas", "body": "Le serveur d'intégration continue va se connecter en <code>deploy</code> pour lancer les déploiements. Je ne veux pas qu'avec sa clé, il puisse faire autre chose que lancer <code>/usr/local/bin/deploy-only</code>, quelle que soit la commande qu'il demande."},
             "desc": "Créez une paire de clés <code>~/.ssh/ci_key</code> (sans passphrase) et autorisez-la sur le compte <code>deploy</code> de sorte qu'une connexion avec cette clé exécute <strong>uniquement</strong> <code>/usr/local/bin/deploy-only</code>, quoi qu'on demande. Votre clé personnelle doit garder un accès normal.",
             "hints": ["Chaque ligne de authorized_keys peut commencer par des options qui restreignent ce que la clé permet de faire.", "<code>man sshd</code>, section AUTHORIZED_KEYS FILE FORMAT : <code>command=\"/usr/local/bin/deploy-only\"</code> (avec <code>no-pty</code>, <code>no-port-forwarding</code>…) devant la clé publique."],
             "checks": [
                 ('test -f $H/.ssh/ci_key && test -f $H/.ssh/ci_key.pub', "La paire de clés ~/.ssh/ci_key n'existe pas."),
                 ('o=$(run_as etudiant "ssh -i $H/.ssh/ci_key -o IdentitiesOnly=yes $SSHO deploy@localhost whoami" 2>/dev/null); echo "$o" | grep -q "deploy-only" && ! echo "$o" | grep -qx deploy', "Avec ci_key, la connexion n'exécute pas uniquement deploy-only (ou elle échoue)."),
                 ('[ "$(run_as etudiant "ssh $SSHO deploy@localhost whoami" 2>/dev/null)" = deploy ]', "Votre clé personnelle n'a plus un accès normal au compte deploy."),
             ]},
            {"id": "22.7", "points": 3, "title": "Clé trop bavarde",
             "ticket": {"from": "julien", "body": "On m'a donné la clé <code>~/cles/sauvegarde_key</code> pour me connecter au compte <code>sauvegarde</code>, mais ssh refuse de s'en servir et me demande un mot de passe que je n'ai pas. La clé est pourtant la bonne, c'est promis !"},
             "desc": "Faites en sorte que <code>ssh -i ~/cles/sauvegarde_key sauvegarde@localhost</code> fonctionne, avec cette clé, sans toucher au compte <code>sauvegarde</code>.",
             "hints": ["Lisez le message d'erreur en entier, depuis le début : ssh explique pourquoi il ignore la clé (<code>ssh -v</code> en dit encore plus).", "Selon le message : « UNPROTECTED PRIVATE KEY FILE » (droits trop ouverts), « Permission denied » en chargeant la clé (elle ne vous est pas lisible : à qui appartient-elle ?), ou une erreur de format (<code>cat -A</code> et <code>file</code> révèlent des fins de ligne Windows)."],
             "checks": [
                 ('sha256sum -c --quiet $REF/s22-sauvegarde.sha', "Le compte sauvegarde a été modifié : c'est la clé fournie qui doit fonctionner, sans toucher au compte."),
                 ('p=$(perm $H/cles/sauvegarde_key); [ "$(owner $H/cles/sauvegarde_key)" = etudiant ] && { [ "$p" = 600 ] || [ "$p" = 400 ]; }', "La clé privée doit vous appartenir et n'être lisible que par vous."),
                 ('run_as etudiant "ssh -i $H/cles/sauvegarde_key -o IdentitiesOnly=yes $SSHO sauvegarde@localhost true"', "La connexion avec ~/cles/sauvegarde_key échoue toujours."),
             ]},
            {"id": "22.8", "points": 4, "title": "Qui a le droit d'entrer",
             "ticket": {"from": "sophie", "body": "Les comptes <code>intrus</code> et <code>toor</code> (un compte que l'auditeur nous a signalé) ne doivent jamais pouvoir se connecter en SSH, quelle que soit la méthode. Les autres comptes, y compris ceux qu'on créera plus tard, ne doivent pas être gênés."},
             "desc": "Configurez sshd pour refuser toute connexion SSH aux comptes <code>intrus</code> et <code>toor</code>, sans restreindre les autres comptes (actuels ou futurs), puis rechargez le service.",
             "hints": ["sshd sait refuser des comptes nommément (liste noire) ou n'accepter qu'une liste (liste blanche) : laquelle ne gênera pas les comptes créés plus tard ?", "<code>DenyUsers</code> dans sshd_config, puis <code>sudo sshd -t</code> et <code>sudo service ssh reload</code>."],
             "checks": [
                 ('sshd -t', "La configuration de sshd contient une erreur (sudo sshd -t l'affiche)."),
                 ('d=$(sshd -T 2>/dev/null | awk \'$1 == "denyusers" {print $2}\'); echo "$d" | grep -qx intrus && echo "$d" | grep -qx toor', "La configuration effective de sshd ne refuse pas intrus et toor."),
                 ('! sshd -T 2>/dev/null | grep -qiE "^(allowusers|allowgroups) "', "N'utilisez pas de liste blanche : les comptes créés plus tard seraient refusés."),
                 ('! ssh -i $REF/intrus_key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 intrus@localhost true 2>/dev/null', "intrus peut encore se connecter avec sa clé : avez-vous rechargé sshd ?"),
                 ('run_as etudiant "ssh $SSHO deploy@localhost true"', "Votre connexion par clé au compte deploy ne fonctionne plus."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    23: {
        "title": "Sécurité de base",
        "description": "Auditez la machine… et corrigez ce que vous trouvez : SUID, droits, comptes, umask, cron, clés SSH.",
        "lesson": r"""<h3>Fichiers SUID</h3><p>Un exécutable <strong>SUID</strong> s'exécute avec les droits de son propriétaire, souvent root. Indispensable pour <code>passwd</code> ; catastrophique sur un programme capable de lire ou d'écrire des fichiers, ou de lancer d'autres commandes (<code>cat</code>, <code>find</code>, un éditeur, un shell…).</p><pre>find /usr -perm -2000 -type f 2&gt;/dev/null   # ici, les fichiers SETGID (bit 2000)<br>chmod u-s fichier                           # retirer le bit SUID<br>dpkg -S /chemin/du/fichier                  # quel paquet l'a installé ?</pre><p>Un binaire SUID qui n'appartient à <strong>aucun paquet</strong> mérite une enquête. Attention : sous Ubuntu, <code>/bin</code>, <code>/sbin</code> et <code>/lib</code> sont des liens vers leurs équivalents de <code>/usr</code>, et dpkg connaît certains fichiers sous leur ancien chemin (<code>/bin/mount</code> plutôt que <code>/usr/bin/mount</code>) : avant de conclure, essayez les deux.</p><h3>Fichiers modifiables par tous</h3><pre>find /srv -type f -perm -o+w</pre><h3>Le bit sticky</h3><p>Dans un dossier modifiable par tous, n'importe qui peut supprimer ou renommer les fichiers des autres… sauf si le dossier porte le <strong>bit sticky</strong> : un <code>t</code> à la fin des droits, comme pour <code>/tmp</code> (<code>drwxrwxrwt</code>). Il se pose avec <code>chmod +t</code>, ou en octal avec un 1 en tête (<code>1xxx</code>).</p><h3>umask</h3><p>La <strong>umask</strong> retire des droits aux fichiers et aux dossiers au moment de leur création : avec <code>umask 022</code>, un fichier est créé en <code>644</code> (666 moins 022) et un dossier en <code>755</code> ; avec <code>027</code>, les autres n'ont plus aucun droit. <code>umask</code> seul affiche la valeur en cours. Elle est fixée à l'ouverture de session (PAM et <code>/etc/login.defs</code>, puis <code>/etc/profile</code>, <code>/etc/profile.d/*.sh</code>, <code>~/.profile</code>…) et un script peut la changer pour lui-même. Sous Ubuntu, un utilisateur dont le groupe principal porte son nom reçoit <code>002</code> : son groupe ne contient que lui.</p><h3>Comptes</h3><pre>awk -F: '$3 &gt;= 1000 {print $1}' /etc/passwd   # comptes « humains » (UID ≥ 1000)<br>sudo awk -F: '$2 == ""' /etc/shadow         # mots de passe vides<br>passwd -S user                              # état du mot de passe (L = verrouillé, P = actif)</pre><p>Un compte d'UID 0, quel que soit son nom, <strong>est</strong> root.</p><table class="lesson-table"><tr><th>Commande</th><th>Effet réel</th></tr><tr><td><code>passwd -l user</code></td><td>verrouille le <strong>mot de passe</strong> seulement : la connexion par clé SSH reste possible</td></tr><tr><td><code>usermod -s /usr/sbin/nologin user</code></td><td>interdit le shell, mais pas, par exemple, un tunnel SSH</td></tr><tr><td><code>chage -E 0 user</code> (ou <code>usermod -e 1</code>)</td><td>fait <strong>expirer le compte</strong> : plus aucune connexion, quelle que soit la méthode</td></tr><tr><td><code>chage -E -1 user</code></td><td>annule l'expiration</td></tr></table><h3>Politique de mot de passe</h3><pre>chage -l user          # voir<br>chage -M 60 user       # changement obligatoire au moins tous les 60 jours<br>chage -d 0 user        # changement forcé à la prochaine connexion</pre><h3>Tâches planifiées et clés SSH</h3><ul><li>Une tâche lancée en root ne doit exécuter que des fichiers que <strong>seul root</strong> peut modifier : vérifiez le fichier et chacun de ses dossiers (<code>namei -l</code>), car on peut remplacer un fichier dans un dossier où l'on a le droit d'écrire.</li><li>Chaque compte, root compris, peut avoir un <code>~/.ssh/authorized_keys</code> : une clé oubliée est une porte d'entrée permanente. C'est la clé elle-même (la longue suite de caractères) qui compte, pas le commentaire en fin de ligne, que chacun écrit comme il veut.</li></ul><h3>Surveillance</h3><pre>last / lastb           # connexions réussies / échouées (si les journaux wtmp et btmp existent)<br>sudo ss -tulnp         # ports ouverts</pre><div class="tip">Sur un vrai serveur, on ajoute un pare-feu (<code>ufw</code>, <code>nftables</code>) — impossible à configurer dans ce conteneur.</div>""",
        "setup": r'''
# 23.1 et 23.2 : deux binaires SUID installés hors paquet, noms et emplacements tirés au sort
suids="/usr/local/bin/lecteur-root /usr/sbin/pam-diag /usr/local/sbin/sauve-conf /usr/local/bin/lire-journaux /usr/lib/cimes/diag-reseau /usr/sbin/suivi-log /opt/support/bin/aide-support /usr/local/sbin/pam-verif"
rm -f $suids
v=${LAB_VARIANTE_23_1:-$((RANDOM % 4))}
case $v in
  0) lect=/usr/local/bin/lecteur-root; autre=/usr/sbin/pam-diag; src=/usr/bin/find ;;
  1) lect=/usr/local/bin/lire-journaux; autre=/usr/local/sbin/sauve-conf; src=/bin/cp ;;
  2) lect=/usr/lib/cimes/diag-reseau; autre=/usr/sbin/suivi-log; src=/usr/bin/tail ;;
  3) lect=/opt/support/bin/aide-support; autre=/usr/local/sbin/pam-verif; src=/usr/bin/find ;;
esac
mkdir -p "$(dirname $lect)" "$(dirname $autre)"
putbin /bin/cat $lect && chmod 4755 $lect
putbin $src $autre && chmod 4755 $autre
emit SUSPECTS "$lect $autre"
emit LECTEUR "$lect"
# 23.3 : un secret modifiable par tous, quelque part dans /etc (emplacement tiré au sort)
secrets="/etc/app-secret.conf /etc/boutique/bdd.ini /etc/cimes/paiement.env /etc/opt/crm/connexion.conf"
rm -f $secrets
v=${LAB_VARIANTE_23_3:-$((RANDOM % 4))}
sf=$(echo $secrets | cut -d' ' -f$((v + 1)))
mdp="$(rword | tr -d -)$((RANDOM % 90 + 10))!"
mkdir -p "$(dirname $sf)"
printf '# Accès à la base de données\ndb_user=boutique\ndb_password=%s\n' "$mdp" > $sf && chmod 666 $sf
emit SECRET_FILE "$sf"
emit SECRET_MDP "$mdp"
# 23.4 : un second compte d'UID 0, au nom tiré au sort
for u in toor sysmaint rescue admin0; do sed -i "/^$u:/d" /etc/passwd /etc/shadow; done
v=${LAB_VARIANTE_23_4:-$((RANDOM % 4))}
fr=(toor sysmaint rescue admin0); fr=${fr[v]}
useradd -o -u 0 -g 0 -M -d /root -s /bin/bash $fr
echo "$fr:$fr" | chpasswd
emit FAUX_ROOT "$fr"
# 23.5 : securise a aussi une clé SSH
mkuser securise
echo 'securise:Motdepasse1!' | chpasswd
chage -E -1 -M 99999 securise; passwd -u securise >/dev/null 2>&1 || true
rm -f $REF/securise_key $REF/securise_key.pub
ssh-keygen -q -t ed25519 -N '' -C cle-test-securise -f $REF/securise_key
install -d -m 700 -o securise -g securise /home/securise/.ssh
install -m 600 -o securise -g securise $REF/securise_key.pub /home/securise/.ssh/authorized_keys
mkdir -p $H/cles-test; cp $REF/securise_key $H/cles-test/securise_key; own $H/cles-test; chmod 600 $H/cles-test/securise_key
# 23.6 : un dépôt ouvert à tous
mkuser alice; mkuser bob
rm -rf /srv/depot; mkdir -p /srv/depot; chmod 777 /srv/depot
su -s /bin/bash alice -c 'echo "note d alice" > /srv/depot/note-alice.txt'
su -s /bin/bash bob -c 'echo "devis de bob" > /srv/depot/devis-bob.txt'
# 23.7 : des réglages « de confort » un peu trop généreux, rangés à un endroit tiré au sort
rm -f /etc/profile.d/zz-confort.sh
for f in /etc/profile /etc/bash.bashrc; do sed -i '/^# Réglages de confort pour tous les utilisateurs (Marc)$/,/^# Fin des réglages de confort$/d' $f; done
v=${LAB_VARIANTE_23_7:-$((RANDOM % 3))}
cf=(/etc/profile.d/zz-confort.sh /etc/bash.bashrc /etc/profile); cf=${cf[v]}
cat >> $cf <<'EOF'
# Réglages de confort pour tous les utilisateurs (Marc)
export HISTTIMEFORMAT="%F %T "
umask 000
alias ..='cd ..'
# Fin des réglages de confort
EOF
chmod 644 $cf
# 23.8 : des tâches root qui exécutent des fichiers modifiables par d'autres
groupadd -f equipe
mkdir -p /opt/scripts; chown root:root /opt/scripts; chmod 755 /opt/scripts
printf '#!/bin/bash\n# Purge du cache applicatif\nfind /var/cache/catalogue -name "*.tmp" -mtime +7 -delete\n' > /opt/scripts/purge-cache.sh
chown root:root /opt/scripts/purge-cache.sh; chmod 755 /opt/scripts/purge-cache.sh
mkdir -p /srv/outils; chown root:root /srv/outils; chmod 755 /srv/outils
printf '#!/bin/bash\n# Rotation des exports\nfind /srv/compta -name "*.csv" -mtime +30 -delete\n' > /srv/outils/rotation-exports.sh
chown root:root /srv/outils/rotation-exports.sh; chmod 755 /srv/outils/rotation-exports.sh
printf '#!/bin/bash\n# Statistiques de ventes\necho "$(date +%%F) statistiques calculées" >> /var/log/stats-ventes.log\n' > /usr/local/sbin/stats-ventes
chown root:root /usr/local/sbin/stats-ventes; chmod 755 /usr/local/sbin/stats-ventes
# Ce qui rend chaque script détournable est tiré au sort : fichier modifiable par tous (F), dossier modifiable
# par le groupe equipe (D), fichier appartenant à un autre compte que root (O), ou rien (sain)
mkuser intrus
v=${LAB_VARIANTE_23_8:-$((RANDOM % 4))}
case $v in 0) risques="F D -" ;; 1) risques="- F O" ;; 2) risques="D O -" ;; 3) risques="O - F" ;; esac
set -- $risques
for spec in "/opt/scripts/purge-cache.sh $1" "/srv/outils/rotation-exports.sh $2" "/usr/local/sbin/stats-ventes $3"; do
  p=${spec% *}
  case ${spec##* } in
    F) chmod 777 $p ;;
    D) chown root:equipe $(dirname $p); chmod 2775 $(dirname $p) ;;
    O) chown intrus:intrus $p ;;
  esac
done
printf '30 3 * * * root /opt/scripts/purge-cache.sh\n' > /etc/cron.d/purge-cache
printf '0 4 * * * root /srv/outils/rotation-exports.sh\n' > /etc/cron.d/rotation-exports
printf '0 5 * * * root /usr/local/sbin/stats-ventes\n' > /etc/cron.d/stats-ventes
chmod 644 /etc/cron.d/purge-cache /etc/cron.d/rotation-exports /etc/cron.d/stats-ventes
: > $REF/s23-cron-risque
for f in /etc/cron.d/*; do
  case ${f##*/} in *.*) continue ;; esac
  while read -r l; do
    set -f; a=($l); set +f
    if [ "${a[5]:-}" != root ]; then continue; fi
    p=""; for ((i = 6; i < ${#a[@]}; i++)); do case ${a[i]} in bash|sh|/bin/bash|/bin/sh|/usr/bin/bash) ;; *) p=${a[i]}; break ;; esac; done
    if [[ $p == /* ]] && [ -e "$p" ] && ! root_only "$p"; then echo "$p" >> $REF/s23-cron-risque; fi
  done < <(grep -vE '^[[:space:]]*(#|$)' "$f" | grep -vE '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=' || true)
done
sort -u -o $REF/s23-cron-risque $REF/s23-cron-risque
# 23.9 : la même clé de Marc, cachée sous trois comptes (les deux comptes autres que root sont tirés au sort)
for u in deploy sauvegarde alice bob julien; do mkuser $u; done
# on retire d'abord les clés de Marc d'une mise en place précédente
if [ -s $REF/s23-marc-blobs ]; then
  for u in root deploy sauvegarde alice bob julien; do
    k=$(getent passwd $u | cut -d: -f6)/.ssh/authorized_keys
    if [ -f $k ]; then grep -vF -f $REF/s23-marc-blobs $k > $k.tmp || true; cat $k.tmp > $k; rm -f $k.tmp; fi
  done
fi
rm -f $REF/marc_key $REF/marc_key.pub
ssh-keygen -q -t ed25519 -N '' -C marc@portable -f $REF/marc_key
b=$(awk '{print $2}' $REF/marc_key.pub)
v=${LAB_VARIANTE_23_9:-$((RANDOM % 4))}
case $v in
  0) caches="deploy:cle-deploiement sauvegarde:sauvegarde-auto" ;;
  1) caches="alice:alice@poste-compta julien:outil-synchro" ;;
  2) caches="bob:bob@poste-12 deploy:ci-runner" ;;
  3) caches="sauvegarde:backup-nas alice:support-distant" ;;
esac
for spec in root:marc@portable $caches; do
  u=${spec%%:*}; c=${spec#*:}; hd=$(getent passwd $u | cut -d: -f6)
  install -d -m 700 -o $u -g $(id -gn $u) $hd/.ssh
  k=$hd/.ssh/authorized_keys; touch $k
  echo "ssh-ed25519 $b $c" >> $k; chown $u: $k; chmod 600 $k
done
echo "$b" > $REF/s23-marc-blobs
''',
        "exercises": [
            {"id": "23.1", "points": 4, "title": "Inventaire SUID",
             "ticket": {"from": "sophie", "body": "L'audit de sécurité commence. Première demande de l'auditeur : la liste complète des fichiers SUID du système, et, parmi eux, ceux qui ne viennent d'aucun paquet officiel."},
             "desc": "Listez dans <code>~/suid-files.txt</code> tous les fichiers SUID du système (chemins complets, un par ligne), puis, dans <code>~/suid-suspects.txt</code>, ceux qui n'ont été installés par <strong>aucun paquet</strong>.",
             "hints": ["find sait sélectionner les fichiers selon leurs droits ; le bit SUID vaut 4000. Les erreurs « Permission denied » peuvent être jetées.", "<code>sudo find / -perm -4000 -type f 2&gt;/dev/null</code>, puis <code>dpkg -S</code> sur chaque chemin (une boucle <code>for</code>). « no path found » ? Réessayez avec l'ancien chemin (<code>/bin/…</code> au lieu de <code>/usr/bin/…</code>) avant de conclure à un intrus."],
             "checks": [
                 ('test -s $H/suid-files.txt', "~/suid-files.txt est absent ou vide."),
                 ('s=" $LAB_SUSPECTS "; find / -xdev -perm -4000 -type f 2>/dev/null | while read -r f; do [[ $s == *" $f "* ]] && continue; grep -qxF "$f" $H/suid-files.txt || exit 1; done', "La liste est incomplète : il manque des fichiers SUID du système."),
                 ('f=$H/suid-suspects.txt; s=" $LAB_SUSPECTS "; test -s $f && [ -n "$LAB_SUSPECTS" ] && while read -r l; do l=$(echo $l); [ -z "$l" ] || [[ $s == *" $l "* ]] || exit 1; done < $f && for x in $LAB_SUSPECTS; do test ! -u $x || grep -qxF $x $f || exit 1; done', "~/suid-suspects.txt ne contient pas exactement les fichiers SUID qu'aucun paquet n'a installés."),
             ]},
            {"id": "23.2", "points": 4, "title": "Neutraliser les SUID suspects",
             "ticket": {"from": "lea", "body": "Les SUID qui ne viennent d'aucun paquet me font peur. Essaie de lire <code>/etc/shadow</code> en simple utilisateur avec chacun d'eux (l'un se comporte comme <code>cat</code>)… Si ça marche, c'est une faille béante. Neutralise-les tous, mais sans les supprimer : l'auditeur veut les examiner."},
             "desc": "Retirez le bit SUID de tous les fichiers SUID qu'aucun paquet n'a installés, sans les supprimer, puis vérifiez qu'aucun ne permet plus de lire <code>/etc/shadow</code>.",
             "hints": ["Le bit SUID se retire avec chmod, en notation symbolique ; faites-le pour chaque fichier suspect de votre inventaire (<code>~/suid-suspects.txt</code>).", "<code>sudo chmod u-s fichier</code>, puis testez à nouveau en simple utilisateur."],
             "checks": [
                 ('[ -n "$LAB_SUSPECTS" ] && for x in $LAB_SUSPECTS; do test -f $x || exit 1; done', "Un des fichiers suspects a été supprimé : l'auditeur veut les examiner, il fallait seulement retirer leur bit SUID."),
                 ('for x in $LAB_SUSPECTS; do test ! -u $x || exit 1; done', "Un fichier SUID installé par aucun paquet est toujours actif."),
                 ('! run_as etudiant "$LAB_LECTEUR /etc/shadow"', "Un des fichiers suspects permet encore de lire /etc/shadow."),
             ]},
            {"id": "23.3", "points": 4, "title": "Secret exposé",
             "ticket": {"from": "lea", "body": "L'auditeur a trouvé dans <code>/etc</code> un fichier qui contient un mot de passe et que n'importe qui peut modifier. Trouve-le avant qu'il ne l'écrive dans son rapport, et verrouille-le. Et comme n'importe qui a pu le lire, ce mot de passe est grillé : change-le."},
             "desc": "Un fichier de <code>/etc</code> contenant un mot de passe est modifiable par tout le monde. Trouvez-le, faites en sorte que seul root puisse le lire et le modifier, et remplacez le mot de passe exposé par une nouvelle valeur (la ligne <code>db_password=</code> doit rester).",
             "hints": ["find sait chercher des fichiers selon leurs droits : ici, ceux que les « autres » peuvent modifier.", "<code>find /etc -type f -perm -o+w</code> ; seul root : <code>rw-------</code> ; puis modifiez la valeur avec <code>sudo nano</code>."],
             "checks": [
                 ('[ -n "$LAB_SECRET_FILE" ] && test -f "$LAB_SECRET_FILE"', "Le fichier a été supprimé : il fallait corriger ses droits."),
                 ('[ -z "$(find /etc -xdev -type f -perm -o+w 2>/dev/null)" ]', "Il reste des fichiers modifiables par tous dans /etc."),
                 ('[ "$(perm "$LAB_SECRET_FILE")" = 600 ] && [ "$(owner "$LAB_SECRET_FILE")" = root ]', "Le fichier secret doit appartenir à root avec les droits 600."),
                 ('grep -qE "^db_password=.+" "$LAB_SECRET_FILE" && ! grep -qF -- "$LAB_SECRET_MDP" "$LAB_SECRET_FILE"', "Le mot de passe exposé n'a pas été remplacé (la ligne db_password= doit rester, avec une nouvelle valeur)."),
             ]},
            {"id": "23.4", "points": 5, "title": "Le faux root",
             "ticket": {"from": "sophie", "body": "Alerte de l'auditeur : il y aurait plusieurs comptes avec l'UID 0, donc plusieurs root ! Liste-les, et neutralise celui qui ne devrait pas exister."},
             "desc": "Listez dans <code>~/uid-zero.txt</code> les comptes d'UID 0 (un nom par ligne). L'un d'eux n'est pas <code>root</code> : neutralisez-le (mot de passe inutilisable <strong>et</strong> shell <code>/usr/sbin/nologin</code>), changez son UID, ou supprimez-le.",
             "hints": ["awk sait filtrer les lignes de /etc/passwd selon la valeur d'un champ : l'UID est le 3e.", "<code>userdel</code> peut refuser (des processus tournent avec l'UID 0) : verrouillez plutôt son mot de passe et retirez-lui son shell (<code>usermod -s</code>)."],
             "checks": [
                 ('f=$H/uid-zero.txt; x=$LAB_FAUX_ROOT; [ -n "$x" ] && grep -qx root $f && [ -z "$(grep -vxE "\\s*(root|$x)?\\s*" $f)" ] && { grep -qx "$x" $f || ! awk -F: \'$3 == 0\' /etc/passwd | grep -q "^$x:"; }', "~/uid-zero.txt doit lister exactement les comptes d'UID 0 (un nom par ligne)."),
                 ('x=$LAB_FAUX_ROOT; ! getent passwd "$x" >/dev/null || [ "$(id -u "$x")" != 0 ] || { { [ "$(passwd -S "$x" | awk \'{print $2}\')" = L ] || [ "$(getent shadow "$x" | cut -d: -f8)" = 0 ]; } && getent passwd "$x" | cut -d: -f7 | grep -qE "(nologin|false)$"; }', "Le compte d'UID 0 qui n'est pas root est encore utilisable (mot de passe actif ou shell de connexion)."),
             ]},
            {"id": "23.5", "points": 5, "title": "Vraiment verrouillé",
             "ticket": {"from": "sophie", "body": "Le propriétaire du compte <code>securise</code> part six mois en congé. D'ici son retour, plus personne ne doit pouvoir se connecter avec ce compte, par aucun moyen, mais on ne supprime rien. À son retour, la politique de l'entreprise s'appliquera : changement de mot de passe au moins tous les 90 jours."},
             "desc": "Faites en sorte qu'aucune connexion au compte <code>securise</code> ne soit plus possible, ni par mot de passe, ni par clé SSH (sa clé de test est dans <code>~/cles-test/securise_key</code>), sans supprimer le compte ni ses fichiers. Configurez aussi l'expiration de son mot de passe à 90 jours.",
             "hints": ["Verrouiller le mot de passe ne suffit pas : essayez ensuite de vous connecter avec sa clé de test (<code>ssh -i ~/cles-test/securise_key securise@localhost</code>), et même avec <code>ssh -N</code>.", "Un compte peut expirer : relisez le tableau du cours ; et <code>chage -M</code> pour la politique."],
             "checks": [
                 ('chage -l securise | grep -i "^maximum" | grep -qE ":\\s*90$"', "L'expiration du mot de passe de securise n'est pas de 90 jours."),
                 ('id securise && test -d /home/securise && grep -qF "$(awk \'{print $2}\' $REF/securise_key.pub)" /home/securise/.ssh/authorized_keys', "Le compte, son dossier ou sa clé autorisée ont été supprimés : il fallait bloquer les connexions sans rien supprimer."),
                 ('timeout 8 ssh -N -i $REF/securise_key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 securise@localhost 2>/dev/null; [ $? = 255 ]', "Une connexion SSH par clé au compte securise est encore acceptée (essayez ssh -N : interdire le shell ne suffit pas)."),
                 ('[ "$(passwd -S securise | awk \'{print $2}\')" = L ] || { e=$(getent shadow securise | cut -d: -f8); [ -n "$e" ] && [ "$e" -le $(( $(date +%s) / 86400 )) ]; }', "Le mot de passe de securise permet encore de se connecter."),
             ]},
            {"id": "23.6", "points": 3, "title": "Le dépôt où tout le monde efface tout",
             "ticket": {"from": "diallo", "body": "Tout le monde dépose ses documents dans <code>/srv/depot</code>, c'est pratique. Mais ce matin, tous mes fichiers avaient disparu : quelqu'un les a supprimés ! Chacun doit pouvoir continuer à y déposer des fichiers, mais ne supprimer que les siens."},
             "desc": "Faites en sorte que <code>/srv/depot</code> reste ouvert en écriture à tous les utilisateurs, mais que chacun ne puisse supprimer ou renommer que ses propres fichiers.",
             "hints": ["C'est exactement le fonctionnement de /tmp : comparez <code>ls -ld /tmp</code> et <code>ls -ld /srv/depot</code>.", "Le bit sticky (voir le cours)."],
             "checks": [
                 ('run_as bob "touch /srv/depot/.t-bob && rm -f /srv/depot/.t-bob" && run_as intrus "touch /srv/depot/.t-i && rm -f /srv/depot/.t-i"', "Tous les utilisateurs doivent pouvoir déposer (et supprimer) leurs propres fichiers dans /srv/depot."),
                 ('run_as alice "touch /srv/depot/.t-alice" && run_as bob "rm -f /srv/depot/.t-alice" 2>/dev/null; test -e /srv/depot/.t-alice; r=$?; rm -f /srv/depot/.t-alice; exit $r', "bob peut encore supprimer un fichier déposé par alice."),
             ]},
            {"id": "23.7", "points": 4, "title": "Des fichiers ouverts à tous",
             "ticket": {"from": "lea", "body": "Les fichiers que créent les utilisateurs sont modifiables par tout le monde ! Crée un fichier et regarde ses droits… Trouve pourquoi et corrige, mais garde les autres réglages de confort que Marc avait mis au même endroit."},
             "desc": "Faites en sorte que les fichiers créés par les utilisateurs dans leurs sessions ne soient plus modifiables par les autres, sans perdre les autres réglages du fichier fautif.",
             "hints": ["Créez un fichier en simple utilisateur et regardez ses droits : un réglage du shell décide des droits retirés à la création. Qui le fixe à l'ouverture de session ?", "<code>umask</code>, puis <code>grep -r umask /etc/profile /etc/profile.d /etc/bash.bashrc</code>."],
             "checks": [
                 ('for u in alice bob; do for c in umask "bash -ic umask"; do m=$(su - $u -c "$c" 2>/dev/null </dev/null | tail -n1); [[ $m =~ ^[0-7]+$ ]] && (( (8#$m & 2) == 2 )) || exit 1; done; done', "Dans une session, la umask d'alice ou de bob laisse encore les autres modifier les nouveaux fichiers."),
                 ('[ -n "$(su - alice -c "bash -ic \'echo \\$HISTTIMEFORMAT\'" 2>/dev/null </dev/null | tail -n1)" ]', "Les autres réglages de Marc (comme HISTTIMEFORMAT) ont disparu : ne corrigez que la ligne fautive."),
             ]},
            {"id": "23.8", "points": 5, "title": "Tâches cron détournables",
             "ticket": {"from": "lea", "body": "Les tâches planifiées de root sont une cible de choix : si quelqu'un peut modifier ce qu'elles exécutent, il devient root à la prochaine exécution. Passe en revue toutes les tâches de <code>/etc/cron.d</code> lancées en root."},
             "desc": "Écrivez dans <code>~/cron-risque.txt</code> le chemin de chaque script lancé en root par <code>/etc/cron.d</code> qu'un autre utilisateur que root peut modifier ou remplacer (par le fichier lui-même ou par l'un de ses dossiers), un par ligne. Corrigez ensuite les droits pour que seul root puisse les modifier, sans les supprimer, les déplacer ni les empêcher de s'exécuter.",
             "hints": ["Pour chaque ligne lancée en root, demandez-vous qui peut modifier le fichier… et chacun de ses dossiers : on peut remplacer un fichier dans un dossier où l'on a le droit d'écrire.", "<code>grep -h root /etc/cron.d/*</code>, puis <code>namei -l</code> sur chaque chemin ; corrigez avec <code>chmod go-w</code> et <code>chown root:root</code>."],
             "checks": [
                 ('setcmp $H/cron-risque.txt "cat $REF/s23-cron-risque"', "La liste des scripts détournables n'est pas exacte (ni oubli, ni fausse alerte)."),
                 ('while read -r p; do [ -f "$p" ] && [ -x "$p" ] && root_only "$p" || exit 1; done < $REF/s23-cron-risque', "Un des scripts détournables peut encore être modifié ou remplacé par un autre utilisateur que root (ou il n'est plus exécutable)."),
             ]},
            {"id": "23.9", "points": 5, "title": "Porte dérobée SSH",
             "ticket": {"from": "sophie", "body": "Marc est parti, mais je ne suis pas sûre qu'il ait perdu ses accès : il avait l'habitude de semer sa clé SSH un peu partout, et pas toujours sous son nom. Fais le ménage, sans couper les accès légitimes."},
             "desc": "Retirez la clé de Marc de tous les fichiers <code>authorized_keys</code> du système, quel que soit le commentaire qui l'accompagne, sans toucher aux autres clés : votre accès par clé au compte <code>deploy</code> doit continuer à fonctionner.",
             "hints": ["Chaque compte, root compris, peut avoir son propre authorized_keys : cherchez-les tous. Le commentaire d'une clé ne prouve rien, c'est la clé elle-même qu'il faut comparer.", "<code>sudo find / -xdev -name authorized_keys</code>, repérez la clé de <code>marc@portable</code>, puis cherchez la même suite de caractères ailleurs (<code>sudo grep -rl</code>)."],
             "checks": [
                 ('[ -z "$(find / -xdev -name "authorized_keys*" -type f 2>/dev/null | xargs -r grep -lF -f $REF/s23-marc-blobs)" ]', "La clé de Marc est encore autorisée sur au moins un compte."),
                 ('run_as etudiant "ssh $SSHO deploy@localhost true"', "Votre accès par clé au compte deploy ne fonctionne plus."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    24: {
        "title": "Dépannage",
        "description": "Des choses sont cassées sur ce serveur. Diagnostiquez, puis réparez sans casser autre chose.",
        "lesson": r"""<h3>La méthode</h3><ol><li><strong>Reproduire</strong> : lancez la commande qui échoue et lisez <em>vraiment</em> le message d'erreur, en entier.</li><li><strong>Observer</strong> : droits (<code>ls -l</code>, <code>namei -l chemin</code>), contenu (<code>cat -A</code> révèle les caractères invisibles), journaux (<code>/var/log/</code>).</li><li><strong>Une hypothèse, une correction</strong> à la fois, puis on reteste.</li><li><strong>Réparer sans affaiblir</strong> : désactiver une sécurité (droits 777, <code>StrictModes no</code>, vérification des clés d'hôte…) fait disparaître le symptôme, pas le problème.</li></ol><h3>Boîte à outils</h3><ul><li><code>cat -A f</code> — affiche <code>^M</code> pour les fins de ligne Windows (CRLF) ; <code>file f</code> le signale aussi</li><li><code>sed -i 's/\r$//' f</code> — convertit en fins de ligne Unix</li><li><code>bash -x script</code> — exécute pas à pas en affichant chaque commande</li><li><code>namei -l /chemin/complet</code> — droits de chaque dossier du chemin (pour atteindre un fichier, il faut pouvoir <strong>traverser</strong> chaque dossier : droit <code>x</code>)</li><li><code>du -ah /var/log | sort -h | tail</code> — les plus gros fichiers</li><li><code>truncate -s 0 f</code> ou <code>: &gt; f</code> — vider un fichier sans le supprimer</li><li><code>sudo lsof +L1</code> — fichiers supprimés mais encore ouverts</li><li><code>sudo ss -tlnp</code>, <code>sudo lsof -i :PORT</code> — qui écoute sur ce port ?</li><li><code>ssh -v</code> — connexion SSH bavarde ; côté serveur : <code>/var/log/auth.log</code> et <code>sudo sshd -T</code> (configuration effective)</li><li><code>ssh-keygen -lf cle.pub</code> — empreinte d'une clé ; <code>ssh-keygen -R hôte</code> — oublier une clé d'hôte</li><li><code>chage -l user</code>, <code>passwd -S user</code> — état d'un compte</li><li><code>run-parts --test /etc/cron.daily</code>, <code>grep CRON /var/log/syslog</code></li></ul><div class="tip">Supprimer un journal ouvert par une application ne libère pas l'espace : l'application garde le fichier ouvert. On le <strong>vide</strong>.</div><div class="tip">Sur un vrai serveur, les services sont gérés par systemd : <code>systemctl status service</code> (état et dernières lignes du journal), <code>journalctl -u service -e</code>, <code>systemctl restart service</code>. Ce conteneur n'a pas systemd : les services du lab se lancent à la main ou par de petits scripts de contrôle, mais la démarche de diagnostic est la même.</div>""",
        "volatile": True,
        "setup": r'''
if first_run 24; then
  rm -f $REF/env-24
  mkdir -p $H/depannage
  # 24.1 : ce que Windows a fait au script est tiré au sort
  v=${LAB_VARIANTE_24_1:-$((RANDOM % 3))}
  case $v in
    # fins de ligne CRLF, shebang erroné, pas exécutable
    0) printf '#!/bin/bsh\r\necho "Déploiement en cours..."\r\necho "DEPLOY OK"\r\n' > $H/depannage/deploy.sh
       chmod 644 $H/depannage/deploy.sh ;;
    # enregistré en UTF-16 (« Unicode » du Bloc-notes), fins de ligne CRLF, pas exécutable
    1) printf '#!/bin/bash\r\necho "Déploiement en cours..."\r\necho "DEPLOY OK"\r\n' | iconv -f UTF-8 -t UTF-16 > $H/depannage/deploy.sh
       chmod 644 $H/depannage/deploy.sh ;;
    # marque d'ordre des octets (BOM) UTF-8 devant le shebang, fins de ligne CRLF
    2) printf '\xef\xbb\xbf#!/bin/bash\r\necho "Déploiement en cours..."\r\necho "DEPLOY OK"\r\n' > $H/depannage/deploy.sh
       chmod 755 $H/depannage/deploy.sh ;;
  esac
  rm -rf /var/log/app-debug; mkdir -p /var/log/app-debug
  for n in access audit worker; do head -c 200K /dev/urandom | base64 > /var/log/app-debug/$n.log; done
  big=/var/log/app-debug/trace-$RANDOM.log
  head -c 60M /dev/zero > $big
  kemit 24 BIGLOG "$big"
  kemit 24 BIGINO "$(stat -c %i $big)"
  # 24.3 : ce qui fait refuser la clé de l'équipe ops est tiré au sort
  mkuser ops
  usermod -s /bin/bash ops; chage -E -1 ops
  mkdir -p /home/ops/.ssh
  rm -f $H/depannage/cle_ops $H/depannage/cle_ops.pub
  ssh-keygen -q -t ed25519 -N '' -C cle-ops -f $H/depannage/cle_ops
  cp $H/depannage/cle_ops.pub /home/ops/.ssh/authorized_keys
  chown -R ops:ops /home/ops/.ssh; chmod 755 /home/ops; chmod 700 /home/ops/.ssh; chmod 600 /home/ops/.ssh/authorized_keys
  v=${LAB_VARIANTE_24_3:-$((RANDOM % 4))}
  case $v in
    # droits trop ouverts (StrictModes)
    0) chmod 777 /home/ops /home/ops/.ssh; chmod 666 /home/ops/.ssh/authorized_keys
       chown root:root /home/ops/.ssh/authorized_keys ;;
    # clé restreinte à un réseau d'où l'on ne vient pas
    1) sed -i 's/^/from="10.0.0.0\/8" /' /home/ops/.ssh/authorized_keys ;;
    # compte expiré
    2) chage -E 1 ops ;;
    # shell qui refuse toute session
    3) usermod -s /usr/sbin/nologin ops ;;
  esac
  own $H/depannage
  # 24.4 : la tâche cron de Marc, avec des erreurs tirées au sort (dans le fichier cron et dans le script)
  rm -f /etc/cron.d/rapport /etc/cron.d/rapport.cron /etc/cron.d/rapport-quotidien /var/log/rapport-cron.log
  v=${LAB_VARIANTE_24_4:-$((RANDOM % 3))}
  case $v in
    # nom avec un point, pas d'utilisateur, chemin relatif ; script non exécutable
    0) printf '#!/bin/bash\necho "$(date '"'"'+%%F %%T'"'"') rapport généré" >> /var/log/rapport-cron.log\n' > /usr/local/bin/rapport-cron.sh
       chmod 644 /usr/local/bin/rapport-cron.sh
       printf '* * * * * rapport-cron.sh\n' > /etc/cron.d/rapport.cron ;;
    # fichier modifiable par le groupe et sans retour à la ligne final ; script aux fins de ligne Windows
    1) printf '#!/bin/bash\r\necho "$(date '"'"'+%%F %%T'"'"') rapport généré" >> /var/log/rapport-cron.log\r\n' > /usr/local/bin/rapport-cron.sh
       chmod 755 /usr/local/bin/rapport-cron.sh
       printf '# Rapport de Marc\n* * * * * root /usr/local/bin/rapport-cron.sh' > /etc/cron.d/rapport
       chmod 664 /etc/cron.d/rapport ;;
    # fichier qui n'appartient pas à root, mauvais dossier du script ; shebang erroné
    2) printf '#!/bin/bsh\necho "$(date '"'"'+%%F %%T'"'"') rapport généré" >> /var/log/rapport-cron.log\n' > /usr/local/bin/rapport-cron.sh
       chmod 755 /usr/local/bin/rapport-cron.sh
       printf '# Rapport de Marc\n* * * * * root /usr/local/sbin/rapport-cron.sh\n' > /etc/cron.d/rapport-quotidien
       chown etudiant:etudiant /etc/cron.d/rapport-quotidien; chmod 644 /etc/cron.d/rapport-quotidien ;;
  esac
  mkuser monsvc
  cat > /usr/local/bin/mon-service <<'EOF'
#!/bin/bash
CONF=/etc/mon-service.conf
[ -r "$CONF" ] || { echo "ERREUR: configuration $CONF illisible" >&2; exit 1; }
. "$CONF"
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
  echo "ERREUR: PORT='$PORT' invalide (nombre entre 1024 et 65535 attendu)" >&2; exit 2
fi
[ -d "$LOG_DIR" ] || { echo "ERREUR: LOG_DIR=$LOG_DIR n'existe pas" >&2; exit 3; }
touch "$LOG_DIR/mon-service.log" 2>/dev/null || { echo "ERREUR: $(id -un) ne peut pas écrire dans $LOG_DIR" >&2; exit 4; }
if [ "$1" = "--check" ]; then echo "Configuration OK (port $PORT)"; exit 0; fi
echo "$(date '+%F %T') démarrage sur le port $PORT" >> "$LOG_DIR/mon-service.log"
exec nc -lk "$PORT"
EOF
  chmod 755 /usr/local/bin/mon-service
  # 24.5 : les erreurs de configuration sont tirées au sort
  rm -rf /var/log/mon-service /var/log/mon-servce
  v=${LAB_VARIANTE_24_5:-$((RANDOM % 3))}
  case $v in
    # port écrit en toutes lettres, dossier des journaux absent
    0) printf 'PORT=huit-mille-quatre-vingt\nLOG_DIR=/var/log/mon-service\n' > /etc/mon-service.conf
       chmod 644 /etc/mon-service.conf ;;
    # fichier aux fins de ligne Windows, port réservé
    1) printf 'PORT=80\r\nLOG_DIR=/var/log/mon-service\r\n' > /etc/mon-service.conf
       chmod 644 /etc/mon-service.conf
       mkdir -p /var/log/mon-service; chown monsvc:monsvc /var/log/mon-service; chmod 755 /var/log/mon-service ;;
    # configuration illisible pour monsvc, faute de frappe dans le dossier des journaux
    2) printf 'PORT=8080\nLOG_DIR=/var/log/mon-servce\n' > /etc/mon-service.conf
       chmod 600 /etc/mon-service.conf ;;
  esac
  chown root:root /etc/mon-service.conf
  # 24.6 : un dossier intraversable (lequel est tiré au sort)
  mkuser webapp
  rm -rf /srv/app; mkdir -p /srv/app/public /srv/app/secrets
  echo "<h1>Catalogue Cimes &amp; Sentiers</h1>" > /srv/app/public/index.html
  echo "db_password=$(rword)" > /srv/app/secrets/db.conf
  chown -R root:root /srv/app; chmod 644 /srv/app/public/index.html
  chmod 700 /srv/app/secrets; chmod 600 /srv/app/secrets/db.conf
  v=${LAB_VARIANTE_24_6:-$((RANDOM % 3))}
  case $v in
    0) chmod 700 /srv/app; chmod 755 /srv/app/public ;;   # /srv/app ne se traverse pas
    1) chmod 711 /srv/app; chmod 700 /srv/app/public ;;   # public est fermé aux autres
    2) chmod 711 /srv/app; chmod 744 /srv/app/public ;;   # public se liste, mais ne se traverse pas
  esac
  # 24.7 : l'hébergeur a « préparé » sshd, d'une façon tirée au sort
  if ! id deploy >/dev/null 2>&1; then mkuser deploy; echo 'deploy:deploy123' | chpasswd; fi
  sed -i -E 's/^#?PasswordAuthentication .*/PasswordAuthentication no/; s/^#?KbdInteractiveAuthentication .*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
  grep -q '^PasswordAuthentication no' /etc/ssh/sshd_config || echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config
  sed -i '/^# Accès de secours de l.hébergeur$/,$d' /etc/ssh/sshd_config
  rm -f /etc/ssh/sshd_config.d/50-cloud-init.conf /etc/ssh/sshd_config.d/05-migration.conf
  v=${LAB_VARIANTE_24_7:-$((RANDOM % 4))}
  case $v in
    0) printf '# Préparé par l'"'"'hébergeur pour la migration\nPasswordAuthentication yes\n' > /etc/ssh/sshd_config.d/50-cloud-init.conf ;;
    1) printf '# Migration des comptes (hébergeur)\nPasswordAuthentication yes\n' > /etc/ssh/sshd_config.d/05-migration.conf ;;
    2) printf '\n# Accès de secours de l'"'"'hébergeur\nMatch Address 127.0.0.1,::1\n    PasswordAuthentication yes\n' >> /etc/ssh/sshd_config ;;
    3) printf '# Préparé par l'"'"'hébergeur pour la migration\nKbdInteractiveAuthentication yes\n' > /etc/ssh/sshd_config.d/50-cloud-init.conf ;;
  esac
  if [ -f /run/sshd.pid ]; then kill -HUP "$(cat /run/sshd.pid)" 2>/dev/null || true; fi
  # 24.8 : un script qui casse sur les espaces
  cat > /usr/local/bin/archiver-factures <<'EOF'
#!/bin/bash
# Archive les factures : copie chaque facture de SOURCE dans DEST, puis affiche le nombre copié
# Usage : archiver-factures [SOURCE] [DEST]   (par défaut /srv/factures et /srv/archives-factures)
SRC=${1:-/srv/factures}
DEST=${2:-/srv/archives-factures}
mkdir -p $DEST
n=0
for f in $(ls $SRC); do
    cp $SRC/$f $DEST/ && n=$((n + 1))
done
echo "$n facture(s) archivée(s)"
EOF
  chmod 755 /usr/local/bin/archiver-factures
  rm -rf /srv/factures /srv/archives-factures; mkdir -p /srv/factures
  for nm in "facture-001.pdf" "facture mars.pdf" "avoir client 12.pdf" "facture-002.pdf"; do echo "$nm" > "/srv/factures/$nm"; done
  # 24.9 : le serveur de production a été « réinstallé » (nouvelle clé d'hôte)
  rm -f /etc/ssh/prod/ssh_host_ed25519_key /etc/ssh/prod/ssh_host_ed25519_key.pub
  done_once 24
fi
reemit 24
prod_sshd
# 24.2 : l'application garde son journal ouvert
big=$(sed -n 's/^BIGLOG=//p' $REF/env-24)
cat > /usr/local/bin/trace-boutique <<'EOF'
#!/bin/bash
exec 3>>"$1"
while true; do echo "$(date '+%F %T') trace" >&3; sleep 5 3>&-; done
EOF
chmod 755 /usr/local/bin/trace-boutique
pkill -x trace-boutique || true
setsid /usr/local/bin/trace-boutique "$big" >/dev/null 2>&1 < /dev/null &
sleep 1
emit WRITER "$(pgrep -x trace-boutique | head -n1)"
''',
        "exercises": [
            {"id": "24.1", "points": 4, "title": "Le script qui ne démarre pas", "manual": True,
             "ticket": {"from": "thomas", "body": "J'ai écrit <code>deploy.sh</code> sur mon PC Windows et il refuse de démarrer sur le serveur. J'ai tout vérifié, je ne comprends pas… Tu peux jeter un œil ?"},
             "desc": "Un collègue a écrit <code>~/depannage/deploy.sh</code> sous Windows. Il doit afficher <code>DEPLOY OK</code> quand on lance <code>~/depannage/deploy.sh</code>. Réparez-le (il y a plusieurs problèmes).",
             "hints": ["Lancez-le et lisez l'erreur. Puis examinez-le : <code>file</code> indique son encodage et ses fins de ligne, <code>cat -A</code> montre les caractères invisibles (<code>^M</code>, octets en tête de fichier…).", "Il y a plusieurs problèmes : corrigez-en un, relancez, lisez le nouveau message, et recommencez (droits, première ligne, fins de ligne, encodage : <code>iconv</code> convertit un fichier d'un encodage à un autre)."],
             "checks": [
                 ('test -x $H/depannage/deploy.sh', "Le script n'est pas exécutable."),
                 ('head -n1 $H/depannage/deploy.sh | grep -qxE "#! ?/(usr/)?bin/(env )?(ba)?sh"', "Le shebang ne désigne pas un interpréteur valide."),
                 ('! grep -q $\'\\r\' $H/depannage/deploy.sh', "Le fichier contient encore des fins de ligne Windows (CRLF)."),
                 ('run_as etudiant "timeout 5 $H/depannage/deploy.sh" | grep -qx "DEPLOY OK"', "Le script ne produit pas la ligne « DEPLOY OK »."),
             ]},
            {"id": "24.2", "points": 5, "title": "Disque plein",
             "ticket": {"from": "sophie", "body": "URGENT : le disque est plein et la boutique ne peut plus enregistrer les commandes ! Un journal a dû exploser dans <code>/var/log</code>. Attention, l'application qui l'écrit tourne toujours et le garde ouvert."},
             "desc": "Un fichier de log énorme remplit <code>/var/log</code>. Trouvez-le, écrivez son chemin dans <code>~/gros-log.txt</code>, puis libérez réellement l'espace <strong>sans arrêter l'application</strong> qui l'écrit.",
             "hints": ["Cherchez les plus gros fichiers de /var/log (du ou find, avec sudo).", "Que devient l'espace d'un fichier supprimé qu'un programme garde ouvert ? Videz-le plutôt que de le supprimer (voir la boîte à outils)."],
             "checks": [
                 ('[ "$(ans $H/gros-log.txt)" = "$LAB_BIGLOG" ]', "~/gros-log.txt ne désigne pas le bon fichier."),
                 ('test -f "$LAB_BIGLOG" && [ "$(stat -c %i "$LAB_BIGLOG")" = "$LAB_BIGINO" ]', "Le fichier a été supprimé (puis peut-être recréé) : l'application écrit toujours dans l'ancien, et l'espace n'est pas libéré."),
                 ('[ "$(stat -c %s "$LAB_BIGLOG")" -lt 1048576 ]', "Le fichier fait encore plus de 1 Mo."),
                 ('[ -n "$LAB_WRITER" ] && kill -0 "$LAB_WRITER"', "L'application qui écrit ce journal a été arrêtée : il fallait la laisser tourner (rechargez la page pour la relancer)."),
             ]},
            {"id": "24.3", "points": 5, "title": "SSH refusé",
             "ticket": {"from": "lea", "body": "L'équipe ops n'arrive plus à se connecter avec sa clé. La clé publique est pourtant bien dans <code>authorized_keys</code>… sshd est très pointilleux : cherche ce qui le gêne, et répare sans baisser la garde."},
             "desc": "La commande <code>ssh -i ~/depannage/cle_ops ops@localhost</code> devrait fonctionner : la clé publique est bien dans <code>/home/ops/.ssh/authorized_keys</code>… mais la connexion échoue. Trouvez pourquoi et réparez, sans désactiver les vérifications de sshd ni retirer la clé.",
             "hints": ["Lisez ce que répond ssh, puis ce que sshd explique dans <code>/var/log/auth.log</code> (avec sudo) : droits trop ouverts, clé refusée pour l'adresse d'origine, compte expiré ou shell qui refuse la session… chaque cause laisse un message différent.", "Selon le message : <code>namei -l /home/ops/.ssh/authorized_keys</code> (aucun élément modifiable par le groupe ou les autres), les options placées devant la clé dans authorized_keys, <code>sudo chage -l ops</code>, ou le shell de ops dans <code>/etc/passwd</code>."],
             "checks": [
                 ('grep -qf $H/depannage/cle_ops.pub /home/ops/.ssh/authorized_keys', "La clé publique n'est plus dans authorized_keys."),
                 ('sshd -T 2>/dev/null | grep -qx "strictmodes yes"', "La vérification des droits par sshd (StrictModes) a été désactivée : réactivez-la et corrigez plutôt les droits."),
                 ('for p in /home/ops /home/ops/.ssh /home/ops/.ssh/authorized_keys; do no_gow $p || exit 1; done', "Le dossier personnel de ops, son .ssh ou authorized_keys est encore modifiable par le groupe ou par les autres."),
                 ('run_as etudiant "ssh -i $H/depannage/cle_ops -o IdentitiesOnly=yes $SSHO ops@localhost true"', "La connexion par clé en ops@localhost échoue toujours."),
             ]},
            {"id": "24.4", "points": 5, "title": "La tâche cron fantôme",
             "ticket": {"from": "diallo", "body": "Le rapport qui devait arriver chaque minute dans <code>/var/log/rapport-cron.log</code> n'est jamais apparu. Marc avait configuré ça juste avant de partir… Tu peux regarder ?"},
             "desc": "La tâche que Marc a déposée dans <code>/etc/cron.d</code> (son fichier mentionne <code>rapport-cron</code>) devrait écrire chaque minute dans <code>/var/log/rapport-cron.log</code> en exécutant <code>/usr/local/bin/rapport-cron.sh</code> en root, mais le fichier n'apparaît jamais. Réparez (plusieurs erreurs, dans la tâche et dans le script), puis attendez que <strong>cron</strong> l'alimente.",
             "hints": ["Comparez le fichier et sa ligne aux pièges classiques de l'étape cron ; <code>grep CRON /var/log/syslog</code> montre ce que cron exécute réellement… et les fichiers qu'il refuse, avec la raison.", "Nom de fichier sans point, propriétaire et droits, retour à la ligne final, 6<sup>e</sup> champ pour l'utilisateur, chemin absolu du script. Puis lancez le script vous-même (<code>sudo /usr/local/bin/rapport-cron.sh</code>) : est-il exécutable, et son interpréteur existe-t-il ?"],
             "checks": [
                 ('for f in /etc/cron.d/*; do case ${f##*/} in *.*) continue ;; esac; grep -vE "^\\s*#" "$f" | grep -q "/usr/local/bin/rapport-cron.sh" && exit 0; done; exit 1', "Aucune tâche prise en compte par cron dans /etc/cron.d ne lance /usr/local/bin/rapport-cron.sh (cron ignore certains noms de fichiers)."),
                 ('grep -qE "CRON\\[[0-9]+\\]: \\(root\\) CMD \\(.*rapport-cron" /var/log/syslog', "cron n'a pas encore lancé la tâche en root (grep CRON /var/log/syslog) : attendez une minute après votre correction."),
                 ('f=/var/log/rapport-cron.log; [ "$(grep -c "rapport généré" $f 2>/dev/null)" -ge 2 ] && [ "$(age $f)" -lt 90 ] && t1=$(date -d "$(grep "rapport généré" $f | tail -n2 | head -n1 | cut -c1-19)" +%s) && t2=$(date -d "$(grep "rapport généré" $f | tail -n1 | cut -c1-19)" +%s) && [ $((t2 - t1)) -ge 50 ]', "/var/log/rapport-cron.log n'est pas encore alimenté par cron chaque minute : attendez deux exécutions après votre correction."),
             ]},
            {"id": "24.5", "points": 4, "title": "Le service qui refuse de démarrer",
             "ticket": {"from": "thomas", "body": "<code>mon-service</code> refuse de démarrer depuis la mise à jour. Son mode <code>--check</code> affiche des messages, mais je n'y comprends rien. Le port attendu est 8080."},
             "desc": "Le service <code>mon-service</code> tourne sous l'utilisateur <code>monsvc</code>. La commande <code>sudo -u monsvc mon-service --check</code> échoue : lisez les messages et corrigez jusqu'à obtenir <code>Configuration OK</code> sur le port 8080. Les journaux du service doivent rester dans <code>/var/log/mon-service</code>.",
             "hints": ["Lisez chaque message : il désigne précisément la ligne de /etc/mon-service.conf ou le dossier en cause. Corrigez, relancez, recommencez. Un message qui semble absurde cache parfois des caractères invisibles : <code>sudo cat -A /etc/mon-service.conf</code>.", "La configuration doit être lisible par monsvc ; PORT doit être un nombre entre 1024 et 65535 ; le dossier des journaux doit être /var/log/mon-service, exister et appartenir à monsvc (pas de chmod 777)."],
             "checks": [
                 ('run_as monsvc "timeout 5 /usr/local/bin/mon-service --check" 2>/dev/null | grep -q "Configuration OK (port 8080)"', "« sudo -u monsvc mon-service --check » n'affiche pas une configuration valide sur le port 8080."),
                 ('L=$(bash -c ". /etc/mon-service.conf; echo \\"\\$LOG_DIR\\""); [ "${L%/}" = /var/log/mon-service ]', "Les journaux du service doivent rester dans /var/log/mon-service."),
                 ('[ "$(owner /var/log/mon-service)" = monsvc ] && ! stat -c %A /var/log/mon-service | cut -c9 | grep -q w', "Le dossier des journaux doit appartenir à monsvc et ne pas être modifiable par les autres."),
             ]},
            {"id": "24.6", "points": 4, "title": "Permission refusée quelque part",
             "ticket": {"from": "thomas", "body": "L'application web tourne sous le compte <code>webapp</code> et affiche « Permission denied » en lisant <code>/srv/app/public/index.html</code>. Pourtant ce fichier est lisible par tout le monde, j'ai vérifié ! Attention : le reste de <code>/srv/app</code> contient des secrets."},
             "desc": "Faites en sorte que <code>webapp</code> puisse lire <code>/srv/app/public/index.html</code>, sans pouvoir lister le contenu de <code>/srv/app</code> ni accéder à <code>/srv/app/secrets</code>.",
             "hints": ["Pour atteindre un fichier, il faut pouvoir traverser chacun des dossiers du chemin : lequel bloque webapp ? Ce n'est pas forcément le premier.", "<code>namei -l /srv/app/public/index.html</code> ; sur un dossier, <code>x</code> sans <code>r</code> permet de le traverser sans pouvoir le lister, et <code>r</code> sans <code>x</code> ne permet pas d'y entrer."],
             "checks": [
                 ('run_as webapp "cat /srv/app/public/index.html" >/dev/null 2>&1', "webapp ne peut toujours pas lire /srv/app/public/index.html."),
                 ('! run_as webapp "ls /srv/app" >/dev/null 2>&1', "webapp peut lister le contenu de /srv/app."),
                 ('! run_as webapp "ls /srv/app/secrets" >/dev/null 2>&1 && ! run_as webapp "cat /srv/app/secrets/db.conf" >/dev/null 2>&1', "webapp peut accéder à /srv/app/secrets."),
                 ('no_gow /srv/app && no_gow /srv/app/public', "/srv/app ou /srv/app/public est modifiable par le groupe ou par les autres."),
             ]},
            {"id": "24.7", "points": 5, "title": "Le durcissement sans effet",
             "ticket": {"from": "sophie", "body": "L'auditeur est revenu : il arrive encore à se connecter au compte <code>deploy</code> avec un mot de passe ! Pourtant <code>/etc/ssh/sshd_config</code> dit bien <code>PasswordAuthentication no</code>, j'ai vérifié. Il paraît que l'hébergeur a « préparé » le serveur…"},
             "desc": "Faites en sorte que sshd refuse réellement toute authentification par mot de passe, quelle que soit la méthode (vérifiez sa configuration <strong>effective</strong>, y compris pour une connexion venant de la machine elle-même), puis rechargez-le. Votre connexion par clé doit continuer à fonctionner.",
             "hints": ["Demandez à sshd la configuration qu'il applique réellement, pas celle d'un seul fichier : <code>sudo sshd -T</code>, et <code>sudo sshd -T -C user=deploy,host=localhost,addr=127.0.0.1</code> pour une connexion précise (les blocs <code>Match</code> en dépendent).", "Regardez la ligne Include en tête de sshd_config (ces fichiers sont lus d'abord, et la première valeur lue l'emporte), les blocs <code>Match</code> en fin de fichier, et aussi <code>KbdInteractiveAuthentication</code> : avec PAM, cette méthode demande elle aussi le mot de passe."],
             "checks": [
                 ('sshd -t', "La configuration de sshd contient une erreur (sudo sshd -t l'affiche)."),
                 ('sshd -T 2>/dev/null | grep -qx "passwordauthentication no" && sshd -T -C user=deploy,host=localhost,addr=127.0.0.1 2>/dev/null | grep -qx "passwordauthentication no"', "La configuration effective de sshd autorise encore les mots de passe (au moins pour certaines connexions)."),
                 ('sshd -T -C user=deploy,host=localhost,addr=127.0.0.1 2>/dev/null | grep -qx "kbdinteractiveauthentication no"', "La configuration effective de sshd accepte encore le mot de passe par une autre méthode d'authentification."),
                 ('! sshpass -p deploy123 ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 deploy@localhost true', "Le serveur accepte encore une connexion par mot de passe : avez-vous rechargé sshd ?"),
                 ('run_as etudiant "ssh $SSHO deploy@localhost true"', "Votre connexion par clé au compte deploy ne fonctionne plus."),
             ]},
            {"id": "24.8", "points": 5, "title": "Le script qui casse sur les espaces", "manual": True,
             "ticket": {"from": "diallo", "body": "Le script d'archivage des factures en oublie ! Il affiche des erreurs bizarres pour <code>facture mars.pdf</code> et quelques autres… Tu peux le réparer ? Il est dans <code>/usr/local/bin/archiver-factures</code>."},
             "desc": "Réparez <code>/usr/local/bin/archiver-factures</code> pour qu'il archive toutes les factures, quels que soient leurs noms (espaces compris), et affiche le bon nombre. Il doit rester utilisable avec ses arguments facultatifs SOURCE et DEST, qui peuvent eux aussi contenir des espaces.",
             "hints": ["Lancez-le avec <code>sudo bash -x /usr/local/bin/archiver-factures</code> : combien d'éléments la boucle voit-elle pour « facture mars.pdf » ?", "Parcourez les fichiers avec un joker (<code>\"$SRC\"/*</code>) plutôt qu'avec ls, et mettez des guillemets autour de chaque variable."],
             "checks": [
                 ('s="/tmp/lab factures $RANDOM"; d="/tmp/lab archives $RANDOM"; mkdir -p "$s"; n=$((RANDOM % 4 + 4)); for i in $(seq $n); do echo "f$i-$RANDOM" > "$s/facture $i du mois.pdf"; done; echo x > "$s/facture-simple.pdf"; n=$((n + 1)); o=$(timeout 10 /usr/local/bin/archiver-factures "$s" "$d" 2>/dev/null); ok=1; for f in "$s"/*; do cmp -s "$f" "$d/$(basename "$f")" || ok=0; done; rm -rf "$s" "$d"; [ $ok = 1 ] && [ "$o" = "$n facture(s) archivée(s)" ]', "Testé sur des dossiers inconnus (noms avec espaces), le script n'archive pas toutes les factures, ou n'affiche pas le bon nombre."),
             ]},
            {"id": "24.9", "points": 5, "title": "Hôte usurpé ?",
             "ticket": {"from": "lea", "body": "Le serveur de production a été réinstallé ce week-end. Depuis, <code>ssh prod</code> hurle « REMOTE HOST IDENTIFICATION HAS CHANGED » et refuse de se connecter. Surtout, ne désactive pas la vérification : on vérifie d'abord que c'est bien notre serveur, ensuite seulement on met à jour."},
             "desc": "Écrivez dans <code>~/empreinte.txt</code> l'empreinte SHA256 de la nouvelle clé d'hôte du serveur de production (sa clé publique est <code>/etc/ssh/prod/ssh_host_ed25519_key.pub</code>) et vérifiez qu'elle correspond à celle qu'annonce ssh. Puis rétablissez la connexion à <code>deploy@localhost</code> sur le port 2222, avec la vérification des clés d'hôte toujours active.",
             "hints": ["L'empreinte d'une clé publique se calcule avec ssh-keygen ; comparez-la à celle qu'affiche ssh dans son avertissement.", "<code>ssh-keygen -lf /etc/ssh/prod/ssh_host_ed25519_key.pub</code>, puis <code>ssh-keygen -R '[localhost]:2222'</code>, et reconnectez-vous en acceptant la nouvelle clé."],
             "checks": [
                 ('fp=$(ssh-keygen -lf /etc/ssh/prod/ssh_host_ed25519_key.pub | awk \'{print $2}\'); grep -qF "${fp#SHA256:}" $H/empreinte.txt 2>/dev/null', "~/empreinte.txt ne contient pas l'empreinte SHA256 de la nouvelle clé du serveur de production."),
                 ('run_as etudiant "ssh -p 2222 -o StrictHostKeyChecking=yes -o BatchMode=yes -o ConnectTimeout=5 deploy@localhost true"', "La connexion au serveur de production (port 2222) échoue encore quand la vérification des clés d'hôte est active."),
                 ('c=$(run_as etudiant "ssh -G prod; ssh -G -p 2222 localhost" 2>/dev/null); ! echo "$c" | grep -qiE "^stricthostkeychecking (false|no|off)$" && ! echo "$c" | grep -qi "^userknownhostsfile /dev/null"', "Votre configuration SSH désactive la vérification des clés d'hôte : c'est exactement ce qu'il ne fallait pas faire."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    25: {
        "title": "Intégration finale : serveur web",
        "description": "Mobilisez tout le parcours pour héberger le site vitrine : comptes, droits, sauvegardes, supervision, SSH, service HTTP et revue de sécurité.",
        "lesson": r"""<h3>Scénario</h3><p>Vous administrez le serveur qui héberge <em>monsite</em>, le site vitrine de Cimes &amp; Sentiers. Vous devez :</p><ol><li>Créer l'utilisateur <code>webmaster</code> et le groupe <code>www</code></li><li>Préparer <code>/var/www/monsite/{html,logs,backup}</code> avec des droits de groupe</li><li>Écrire un script de sauvegarde horodatée avec rotation, et le planifier</li><li>Écrire un script de supervision avec seuil d'alerte</li><li>Donner un accès SSH par clé au webmaster</li><li>Mettre le site en ligne avec un petit serveur HTTP</li><li>Passer la revue de sécurité</li></ol><div class="tip">Les scripts sont exécutés <strong>en tant que webmaster</strong> lors de la vérification : testez-les avec <code>sudo -u webmaster …</code>. Attention : dans <code>sudo -u webmaster echo x &gt; fichier</code>, c'est <strong>votre</strong> shell qui ouvre <code>fichier</code>, pas webmaster. Préférez <code>sudo -u webmaster bash -c '…'</code>, ou <code>… | sudo -u webmaster tee fichier</code>.</div><h3>Rappels utiles</h3><pre>date +%d%m%Y              # 29092026 : à adapter pour nommer vos fichiers<br>ls -1t /var/backups/*.gz  # du plus récent au plus ancien<br>tail -n +4                # tout à partir de la 4e ligne<br>df -P /home               # une ligne par système de fichiers, format stable</pre><p><code>xargs</code> transforme des lignes en arguments : <code>find /tmp -name '*.old' | xargs -r rm -f</code> (<code>-r</code> : ne rien lancer si la liste est vide).</p><h3>Servir une page en HTTP avec nc</h3><p>Une réponse HTTP minimale, c'est une ligne de statut, des en-têtes, une ligne vide, puis le contenu :</p><pre>HTTP/1.0 200 OK<br>Content-Type: text/html<br><br>&lt;h1&gt;…&lt;/h1&gt;</pre><p><code>nc -l 127.0.0.1 PORT</code> attend une connexion et envoie au client ce qu'il reçoit sur son entrée standard ; avec <code>-N</code>, il ferme la connexion à la fin de cette entrée. Il sert une seule connexion : il faut le relancer en boucle. Un processus lancé avec <code>setsid</code> (ou <code>nohup</code>) survit à la fermeture du terminal.</p><div class="tip">En production, on utilise un vrai serveur web (nginx, Apache) géré par systemd ; le principe reste le même : un processus qui écoute sur un port, sous un compte sans privilèges.</div><h3>umask dans un script</h3><p>Un script peut fixer sa propre umask en tête (<code>umask 077</code>, par exemple) : tous les fichiers qu'il crée ensuite en tiennent compte, quelle que soit la umask de la session qui l'a lancé.</p>""",
        "setup": r'''
mkuser intrus
''',
        "exercises": [
            {"id": "25.1", "points": 5, "title": "Environnement web",
             "ticket": {"from": "sophie", "body": "Grand projet : on héberge nous-mêmes le nouveau site vitrine ! Prépare un compte <code>webmaster</code> et l'arborescence du site. L'équipe web doit pouvoir travailler partout dedans, et le reste du monde seulement lire."},
             "desc": "Créez <code>webmaster</code> (membre de <code>www</code>) et l'arborescence <code>/var/www/monsite/{html,logs,backup}</code> appartenant au groupe <code>www</code>. Les membres de <code>www</code> peuvent écrire partout dedans, les autres ne peuvent écrire nulle part mais peuvent lire <code>html/</code>, et les fichiers créés héritent du groupe <code>www</code>.",
             "hints": ["Il faut un groupe propriétaire, le droit d'écriture pour ce groupe, et le bit qui fait hériter le groupe aux nouveaux fichiers (étape 10).", "<code>sudo chgrp -R www …</code>, <code>sudo chmod -R 2775 …</code>"],
             "checks": [
                 ('id -nG webmaster | grep -qw www', "webmaster n'existe pas ou n'est pas membre de www."),
                 ('for d in "" /html /logs /backup; do [ "$(stat -c %G /var/www/monsite$d)" = www ] && test -g /var/www/monsite$d || exit 1; done', "monsite et ses sous-dossiers doivent appartenir au groupe www avec le bit setgid."),
                 ('for d in html logs backup; do run_as webmaster "touch /var/www/monsite/$d/.t && rm -f /var/www/monsite/$d/.t" || exit 1; done', "webmaster ne peut pas écrire dans tous les sous-dossiers."),
                 ('run_as intrus "ls /var/www/monsite/html" >/dev/null 2>&1', "Un utilisateur quelconque doit pouvoir lire le contenu de html/."),
                 ('for d in "" /html /logs /backup; do run_as intrus "touch /var/www/monsite$d/.t-intrus" 2>/dev/null && { rm -f /var/www/monsite$d/.t-intrus; exit 1; }; done; exit 0', "Un utilisateur quelconque peut écrire dans monsite ou dans l'un de ses sous-dossiers."),
             ]},
            {"id": "25.2", "points": 3, "title": "Contenu web",
             "ticket": {"from": "thomas", "body": "Pour tester l'hébergement, mets une première page d'accueil et quelques lignes de journal d'accès. Fais-le en tant que <code>webmaster</code>, pour vérifier que ses droits sont bons."},
             "desc": "En tant que <code>webmaster</code>, créez <code>html/index.html</code> contenant <code>&lt;h1&gt;Bienvenue&lt;/h1&gt;</code> et <code>logs/access.log</code> avec au moins 5 lignes.",
             "hints": ["Pour agir en tant que webmaster, ouvrez un shell à son nom ; attention, avec <code>sudo -u webmaster echo … &gt; fichier</code>, la redirection est faite par votre shell à vous.", "<code>sudo -u webmaster bash</code>, puis vos commandes (<code>exit</code> pour revenir)."],
             "checks": [
                 ('grep -q "<h1>Bienvenue</h1>" /var/www/monsite/html/index.html', "index.html est absent ou ne contient pas <h1>Bienvenue</h1>."),
                 ('[ "$(owner /var/www/monsite/html/index.html)" = webmaster ]', "index.html doit appartenir à webmaster."),
                 ('[ "$(wc -l < /var/www/monsite/logs/access.log)" -ge 5 ]', "logs/access.log doit contenir au moins 5 lignes."),
             ]},
            {"id": "25.3", "points": 5, "title": "Sauvegarde horodatée", "manual": True,
             "ticket": {"from": "sophie", "body": "Le site doit être sauvegardé. Il me faut un script qui crée une archive horodatée du site, avec un état de l'espace disque à côté."},
             "desc": "Écrivez <code>/home/webmaster/backup.sh</code> (exécutable) qui crée <code>/var/www/monsite/backup/site-AAAAMMJJ-HHMMSS.tar.gz</code> contenant le dossier <code>html</code> (sans le chemin complet), et écrit la sortie de <code>df -h</code> dans <code>backup/disk-report.txt</code>.",
             "hints": ["date sait produire n'importe quel format ; l'option <code>-C</code> de tar évite de stocker le chemin complet /var/www/monsite.", "<code>tar -czf \"$B/site-$(date +%Y%m%d-%H%M%S).tar.gz\" -C /var/www/monsite html</code>, puis <code>df -h &gt; …/disk-report.txt</code>."],
             "checks": [
                 ('test -x /home/webmaster/backup.sh', "/home/webmaster/backup.sh n'existe pas ou n'est pas exécutable."),
                 ('touch /tmp/.lab-t && sleep 1 && run_as webmaster "cd /tmp && timeout 20 /home/webmaster/backup.sh" >/dev/null 2>&1; f=$(find /var/www/monsite/backup -regextype posix-extended -regex ".*/site-$(date +%Y%m%d)-[0-9]{6}\\.tar\\.gz" -newer /tmp/.lab-t | head -n1); [ -n "$f" ] && tar -tzf "$f" | grep -qE "^(\\./)?html/index\\.html$"', "Exécuté par webmaster, le script ne produit pas d'archive site-AAAAMMJJ-HHMMSS.tar.gz contenant html/index.html."),
                 ('[ /var/www/monsite/backup/disk-report.txt -nt /tmp/.lab-t ] && grep -qi filesystem /var/www/monsite/backup/disk-report.txt', "backup/disk-report.txt n'est pas (re)généré avec la sortie de df -h."),
             ]},
            {"id": "25.4", "points": 4, "title": "Planifier la sauvegarde",
             "ticket": {"from": "sophie", "body": "Et cette sauvegarde doit tourner toute seule, chaque nuit à 3 heures, sous le compte <code>webmaster</code>."},
             "desc": "Créez <code>/etc/cron.d/backup-web</code> pour que <code>webmaster</code> exécute <code>/home/webmaster/backup.sh</code> chaque jour à 3h00.",
             "hints": ["Même format que les tâches système de l'étape cron : 6<sup>e</sup> champ pour l'utilisateur, chemin absolu, et gare aux pièges de fichier.", "Le fichier appartient à root, n'est modifiable ni par le groupe ni par les autres, et se termine par un retour à la ligne."],
             "checks": [
                 ('f=/etc/cron.d/backup-web; test -f $f && [ "$(owner $f)" = root ] && no_gow $f && eol_ok $f', "/etc/cron.d/backup-web est absent, n'appartient pas à root, est modifiable par d'autres, ou ne se termine pas par un retour à la ligne."),
                 ('l=$(cron_line /etc/cron.d/backup-web); cron_is "$l" 0 3 "*" "*" "*" && [ "$(echo "$l" | awk \'{print $6}\')" = webmaster ] && [ "$(cron_prog "$l")" = /home/webmaster/backup.sh ]', "La ligne cron ne convient pas (horaire, utilisateur webmaster, chemin absolu du script)."),
             ]},
            {"id": "25.5", "points": 5, "title": "Rotation des sauvegardes", "manual": True,
             "ticket": {"from": "lea", "body": "Attention, à une archive par nuit, le disque sera plein dans quelques mois. Fais en sorte que la sauvegarde ne garde que les 7 plus récentes. Et surtout, ne jette pas les bonnes : une sauvegarde qui supprime les sauvegardes, j'en ai déjà vu…"},
             "desc": "Complétez <code>backup.sh</code> pour qu'après chaque sauvegarde, il ne reste que les <strong>7 archives les plus récentes</strong> dans <code>backup/</code>.",
             "hints": ["ls sait trier par date ; il reste à ignorer les 7 premières lignes et à supprimer les suivantes.", "<code>ls -1t … | tail -n +8 | xargs -r rm -f</code> (voir xargs dans le cours)."],
             "checks": [
                 ('b=/var/www/monsite/backup; rm -f $b/site-2020*; for i in 0 1 2 3 4 5 6 7 8 9; do f=$b/site-2020010$i-000000.tar.gz; cp /dev/null $f; touch -d "$((20 - i)) days ago" $f; chown webmaster:www $f; done; keep=$(ls -1t $b/site-*.tar.gz | head -n 6); touch /tmp/.lab-t5; sleep 1; run_as webmaster "cd /tmp && timeout 20 /home/webmaster/backup.sh" >/dev/null 2>&1; [ "$(ls $b/site-*.tar.gz | wc -l)" -eq 7 ] && [ -n "$(find $b -name "site-$(date +%Y%m%d)-*.tar.gz" -newer /tmp/.lab-t5)" ] && for k in $keep; do [ -e "$k" ] || exit 1; done', "Après l'ajout de 10 vieilles archives et une exécution, il ne reste pas exactement les 7 archives les plus récentes (dont celle du jour)."),
             ]},
            {"id": "25.6", "points": 5, "title": "Supervision avec seuil", "manual": True,
             "ticket": {"from": "lea", "body": "Dernière brique : la supervision. Un script qui lève une alerte quand le disque dépasse un seuil donné, et qui garde un historique de ses contrôles."},
             "desc": "Écrivez <code>/home/webmaster/monitoring.sh SEUIL</code> : si le taux d'occupation de <code>/</code> (en %) <strong>dépasse</strong> <code>SEUIL</code>, il affiche une ligne contenant <code>ALERTE</code>, sinon une ligne contenant <code>OK</code>. Dans les deux cas, il ajoute cette ligne, horodatée, à <code>/var/www/monsite/logs/monitoring.txt</code>. Sans argument, il affiche un message d'usage et renvoie un code d'erreur.",
             "hints": ["df affiche le taux d'occupation : n'en gardez que le nombre, puis comparez-le à l'argument (« dépasse » = strictement supérieur).", "<code>u=$(df -P / | awk 'NR==2 {print $5}' | tr -d %)</code> ; <code>if [ \"$u\" -gt \"$1\" ]; then …</code>"],
             "checks": [
                 ('test -x /home/webmaster/monitoring.sh', "/home/webmaster/monitoring.sh n'existe pas ou n'est pas exécutable."),
                 ('u=$(df -P / | awk \'NR==2 {print $5}\' | tr -d %); r() { run_as webmaster "timeout 10 /home/webmaster/monitoring.sh $1" 2>/dev/null; }; r $((u - 1)) | grep -q ALERTE && ! r $u | grep -q ALERTE && r $u | grep -q OK && r $((u + 1)) | grep -q OK && ! r $((u + 1)) | grep -q ALERTE', "Testé avec des seuils juste au-dessous, égal et juste au-dessus de l'occupation réelle, le script ne répond pas ALERTE seulement quand l'occupation dépasse le seuil."),
                 ('f=/var/www/monsite/logs/monitoring.txt; n=$(cat $f 2>/dev/null | wc -l); run_as webmaster "timeout 10 /home/webmaster/monitoring.sh 100" >/dev/null 2>&1; [ "$(wc -l < $f)" -eq $((n + 1)) ] && tail -n1 $f | grep -q "$(date +%Y)"', "Chaque exécution doit ajouter une ligne horodatée à logs/monitoring.txt."),
                 ('! run_as webmaster "timeout 10 /home/webmaster/monitoring.sh" >/dev/null 2>&1', "Sans argument, le script doit s'arrêter avec un code d'erreur."),
             ]},
            {"id": "25.7", "points": 4, "title": "Accès SSH du webmaster",
             "ticket": {"from": "sophie", "body": "Tu dois pouvoir intervenir sur le compte <code>webmaster</code> avec ta clé SSH, comme sur les autres comptes."},
             "desc": "Faites en sorte que vous (etudiant) puissiez vous connecter en <code>webmaster@localhost</code> avec votre clé SSH.",
             "hints": ["webmaster n'a pas de mot de passe (compte créé sans) : ssh-copy-id ne peut donc pas s'y connecter. Installez la clé vous-même, avec sudo.", "Le dossier ~/.ssh de webmaster et son authorized_keys doivent lui appartenir, sans droits d'écriture pour le groupe ni les autres (700 et 600)."],
             "checks": [
                 ('run_as etudiant "ssh $SSHO webmaster@localhost true"', "La connexion par clé à webmaster@localhost échoue."),
             ]},
            {"id": "25.8", "points": 5, "title": "Mettre le site en ligne",
             "ticket": {"from": "thomas", "body": "Le site est prêt, il ne manque plus… qu'un serveur web ! En attendant le vrai (nginx, au prochain trimestre), on se contente d'un petit serveur maison : il suffit qu'il réponde avec la page d'accueil et qu'il note chaque visite."},
             "desc": "Écrivez <code>/home/webmaster/serveur.sh</code>, qui sert <code>html/index.html</code> en HTTP sur <code>127.0.0.1:8000</code> (une réponse par connexion, en boucle) et ajoute une ligne à <code>logs/access.log</code> à chaque requête. Lancez-le en tant que <code>webmaster</code>, en arrière-plan, de façon qu'il survive à la fermeture du terminal.",
             "hints": ["nc sait attendre une connexion : donnez-lui à envoyer un en-tête HTTP puis le fichier, et relancez-le en boucle après chaque requête (voir le cours).", "<code>while true; do { printf 'HTTP/1.0 200 OK\\r\\nContent-Type: text/html\\r\\n\\r\\n'; cat …/index.html; } | nc -N -l 127.0.0.1 8000 &gt; /dev/null; echo \"$(date) GET /\" &gt;&gt; …/access.log; done</code>, lancé avec <code>sudo -u webmaster setsid …</code>."],
             "checks": [
                 ('curl -s --max-time 3 http://127.0.0.1:8000/ | grep -q Bienvenue', "http://127.0.0.1:8000/ ne renvoie pas la page d'accueil du site."),
                 ('sleep 1; u=$(ss -Htlne "sport = :8000" | grep -o "uid:[0-9]*" | head -n1 | cut -d: -f2); [ -n "$u" ] && [ "$u" = "$(id -u webmaster)" ]', "Le serveur qui écoute sur le port 8000 ne tourne pas sous le compte webmaster."),
                 ('f=/var/www/monsite/logs/access.log; a=$(wc -l < $f); curl -s --max-time 3 http://127.0.0.1:8000/ >/dev/null; sleep 1; curl -s --max-time 3 http://127.0.0.1:8000/ >/dev/null; sleep 1; b=$(wc -l < $f); [ $((b - a)) -ge 2 ]', "Chaque requête doit ajouter une ligne à logs/access.log."),
             ]},
            {"id": "25.9", "points": 5, "title": "Revue de sécurité finale", "manual": True,
             "ticket": {"from": "sophie", "body": "L'auditeur a jeté un œil à l'hébergement du site : « n'importe quel compte du serveur peut lire vos sauvegardes, qui contiendront bientôt la configuration de la base de données ». Corrige ça pour de bon, y compris pour les sauvegardes des prochaines nuits, sans gêner l'équipe web."},
             "desc": "Faites en sorte que les comptes extérieurs au groupe <code>www</code> ne puissent plus rien lire dans <code>backup/</code>, et que chaque nouvelle archive créée par <code>backup.sh</code> ne soit lisible que par webmaster et le groupe <code>www</code>. Enfin, <code>backup.sh</code> ne doit être modifiable que par webmaster.",
             "hints": ["Deux choses : les droits du dossier backup/, et les droits des archives que le script créera chaque nuit (quel réglage décide des droits d'un fichier à sa création ?).", "<code>sudo chmod o-rwx /var/www/monsite/backup</code> ; <code>umask 027</code> au début de backup.sh."],
             "checks": [
                 ('! run_as intrus "ls /var/www/monsite/backup" >/dev/null 2>&1 && ! run_as intrus "cat /var/www/monsite/backup/disk-report.txt" >/dev/null 2>&1', "Un compte extérieur à www peut encore lire le contenu de backup/."),
                 ('run_as webmaster "ls /var/www/monsite/backup" >/dev/null 2>&1', "webmaster ne peut plus lire backup/ : l'équipe web ne doit pas être gênée."),
                 ('[ "$(owner /home/webmaster/backup.sh)" = webmaster ] && no_gow /home/webmaster/backup.sh', "backup.sh doit appartenir à webmaster et n'être modifiable ni par le groupe ni par les autres."),
                 ('touch /tmp/.lab-t9; sleep 1; run_as webmaster "cd /tmp && umask 002 && timeout 20 /home/webmaster/backup.sh" >/dev/null 2>&1; f=$(find /var/www/monsite/backup -name "site-*.tar.gz" -newer /tmp/.lab-t9 | head -n1); [ -n "$f" ] && [ "$(others "$f")" = "---" ] && stat -c %A "$f" | cut -c5 | grep -q r', "Une archive fraîchement créée par backup.sh est encore lisible par les autres (ou illisible pour le groupe www)."),
             ]},
        ],
    },
}


def get_exercise(exercise_id: str):
    """Retourne (étape, exercice) pour un identifiant comme '4.2'."""
    try:
        step_num = int(exercise_id.split(".")[0])
    except ValueError:
        return None, None
    step = STEPS.get(step_num)
    if not step:
        return None, None
    for ex in step["exercises"]:
        if ex["id"] == exercise_id:
            return step_num, ex
    return None, None


MAX_SCORE = sum(ex["points"] for s in STEPS.values() for ex in s["exercises"])
TOTAL_EXERCISES = sum(len(s["exercises"]) for s in STEPS.values())
