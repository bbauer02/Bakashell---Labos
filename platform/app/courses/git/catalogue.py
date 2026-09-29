"""Parcours « Git : travailler en équipe ».

Chaque étudiant dispose d'un serveur avec Git et d'un dépôt partagé de l'équipe (dépôt nu local dans
/srv/git : pas besoin d'Internet). Les collègues y « poussent » leurs commits au fil des mises en place.
Sécurité : les dépôts de l'étudiant (et le dépôt partagé, qu'il peut modifier) ne sont jamais manipulés par git en
root, car leur configuration et leurs hooks pourraient exécuter du code. Les vérifications lancent git en tant
qu'etudiant ; les mises en place préparent les dépôts dans un dossier réservé à root, puis les livrent d'un bloc, et
passent par git-upload-pack / git-receive-pack exécutés en tant qu'etudiant pour échanger avec le dépôt partagé.
"""

EXERCISES_VERSION = "1"

MENTOR = "nadia"

SETUP_PRELUDE = r'''
set -e
H=/home/etudiant
R=/srv/git/boutique.git
E=/var/lib/lab/equipe/boutique
export HOME=/root
emit() { echo "@$1=$2"; }
own() { chown -R etudiant:etudiant "$@"; }
declare -A NOM=([thomas]="Thomas Leroy" [nadia]="Nadia Haddad" [lea]="Léa Nguyen" [sophie]="Sophie Marchand" [julien]="Julien Petit" [marc]="Marc Dumas")
declare -A MAIL=([thomas]=thomas.leroy [nadia]=nadia.haddad [lea]=lea.nguyen [sophie]=sophie.marchand [julien]=julien.petit [marc]=marc.dumas)
# commit <collègue> <il y a N heures> <message> : commite tout le dossier courant au nom d'un collègue
commit() {
  local d; d=$(date -d "-$2 hours" '+%Y-%m-%d %H:%M:%S')
  git add -A
  GIT_AUTHOR_NAME="${NOM[$1]}" GIT_AUTHOR_EMAIL="${MAIL[$1]}@cimes-sentiers.fr" GIT_AUTHOR_DATE="$d" \
  GIT_COMMITTER_NAME="${NOM[$1]}" GIT_COMMITTER_EMAIL="${MAIL[$1]}@cimes-sentiers.fr" GIT_COMMITTER_DATE="$d" \
    git commit -q -m "$3"
}
# chantier <dossier> : prépare un dossier à livrer dans un espace réservé à root, et s'y place
chantier() { DEST=$1; TMPD=/var/lib/lab/chantier/$(basename "$1"); rm -rf "$TMPD"; mkdir -p "$TMPD"; cd "$TMPD"; }
# nouveau_depot <dossier> : idem, avec un dépôt Git vide
nouveau_depot() { chantier "$1"; git init -q -b main .; }
# livre : remplace le dossier de l'étudiant par celui du chantier (pas de piège par lien symbolique)
livre() { cd /; chown -R etudiant:etudiant "$TMPD"; rm -rf "$DEST"; mv -T "$TMPD" "$DEST"; }
# Échanges avec le dépôt partagé : les programmes Git qui y lisent ou y écrivent tournent en tant qu'etudiant
AS_ETU="runuser -u etudiant -- env HOME=$H"
# Dépôt partagé de l'équipe (créé une seule fois : le travail poussé par l'étudiant est conservé)
depot_equipe() {
  [ -e $R ] && return 0
  nouveau_depot /var/lib/lab/equipe/init  # (préparé dans le chantier)
  printf '# Boutique Cimes & Sentiers\n\nSite de la boutique en ligne de matériel de randonnée.\n' > README.md
  commit thomas 900 "Premier commit : README"
  mkdir -p css
  cat > index.html <<'EOF'
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Cimes & Sentiers</title><link rel="stylesheet" href="css/style.css"></head>
<body>
  <h1>Cimes & Sentiers</h1>
  <p>Tout le matériel de Randonée, livré chez vous en 48 h.</p>
  <a href="tarifs.html">Nos tarifs</a>
</body>
</html>
EOF
  printf 'body { font-family: sans-serif; margin: 2rem; }\nh1 { color: #2d6a4f; }\n' > css/style.css
  commit thomas 850 "Page d'accueil et feuille de style"
  cat > tarifs.html <<'EOF'
<h2>Nos tarifs</h2>
<ul>
  <li>Bâtons de marche : 35 euros</li>
  <li>Sac 40 L : 79 euros</li>
  <li>Tente 2 places : 149 euros</li>
</ul>
EOF
  commit nadia 700 "Page des tarifs"
  printf "# L'équipe du site\n\n- Thomas Leroy (développement)\n- Nadia Haddad (lead dev)\n" > EQUIPE.md
  commit nadia 600 "Liste de l'équipe"
  cd /
  rm -rf /var/lib/lab/equipe/boutique.git
  git clone -q --bare "$TMPD" /var/lib/lab/equipe/boutique.git
  rm -rf "$TMPD"
  chown -R etudiant:etudiant /var/lib/lab/equipe/boutique.git
  mv -T /var/lib/lab/equipe/boutique.git $R
}
# equipe : clone de travail des collègues, à jour (invisible pour l'étudiant)
equipe() { depot_equipe; rm -rf $E; mkdir -p "$(dirname $E)"; git clone -q --no-local --upload-pack="$AS_ETU git-upload-pack" "$R" $E; cd $E; }
# pousse <branche> : publie sur le dépôt partagé
pousse() { git push -q --receive-pack="$AS_ETU git-receive-pack" origin "$1"; }
# trouve <message> : identifiant du commit (toutes branches) du dépôt partagé qui porte ce message
trouve() { $AS_ETU git --git-dir=$R log --all -1 --format=%H --grep="^$1\$"; }
'''

CHECK_PRELUDE = r'''
H=/home/etudiant
R=/srv/git/boutique.git
B=$H/boutique
# git en tant qu'etudiant (jamais en root dans ses dépôts), sans fsmonitor ni hooks, sans réécrire l'index
export GIT_OPTIONAL_LOCKS=0
etu_git() { runuser -u etudiant -- env HOME=$H git -c core.fsmonitor=false -c core.hooksPath=/dev/null "$@"; }
ans() { tr -d '[:space:]' < "$1" 2>/dev/null; }
gget() { etu_git config --global --get "$1"; }
g() { etu_git -C "$1" "${@:2}"; }
depot() { etu_git --git-dir=$R "$@"; }
# hashok <fichier> <hash> : le fichier contient ce hash, éventuellement abrégé (7 caractères au moins)
hashok() { local a; a=$(ans "$1" | tr 'A-F' 'a-f'); [ ${#a} -ge 7 ] && [ "${2#"$a"}" != "$2" ]; }
propre() { [ -z "$(g "$1" status --porcelain)" ]; }
'''

INTRO = """<div class="scenario"><h3>Travailler en équipe avec Git</h3><p>L'équipe web de Cimes &amp; Sentiers s'agrandit, et les « <code>index-final-v2-OK.html</code> » échangés par clé USB, c'est fini. Nadia, lead développeuse, vous confie la mise en place de <strong>Git</strong> : versionner les procédures, retrouver qui a cassé quoi dans les archives de Marc, travailler sur le dépôt partagé de l'équipe, gérer branches et conflits, et réparer les bêtises de Julien.</p><p>Le dépôt partagé de l'équipe est sur ce serveur : <code>/srv/git/boutique.git</code>. Vos collègues y publient leurs commits pendant que vous travaillez. Tout se passe dans le terminal ; l'éditeur par défaut est <code>nano</code> (<kbd>Ctrl</kbd>+<kbd>O</kbd> pour enregistrer, <kbd>Ctrl</kbd>+<kbd>X</kbd> pour quitter).</p></div>"""

STEPS = {
    # ─────────────────────────────────────────────────────────────────────
    1: {
        "title": "Jour 1 — Premiers pas avec Git",
        "description": "Identité, premier dépôt, premiers commits. Compétences : git config, init, status, add, commit, .gitignore.",
        "lesson": INTRO + """<h3>Pourquoi Git ?</h3><p>Git enregistre des <strong>instantanés</strong> (des <em>commits</em>) de votre projet. Chaque commit a un auteur, une date, un message et un identifiant unique (le <em>hash</em>, par exemple <code>3f9c2a1</code>). On peut revenir à n'importe quel instantané, comparer, travailler à plusieurs.</p><h3>Se présenter (une fois par machine)</h3><pre>git config --global user.name "Prénom Nom"<br>git config --global user.email "prenom.nom@cimes-sentiers.fr"<br>git config --global init.defaultBranch main   # nom de la branche des nouveaux dépôts<br>git config --global --list                    # vérifier</pre><div class="tip">Chaque commit porte ce nom et cette adresse : configurez-les <strong>avant</strong> de commiter.</div><h3>Les trois zones</h3><ul><li>le <strong>répertoire de travail</strong> : vos fichiers, tels que vous les modifiez ;</li><li>l'<strong>index</strong> (<em>staging area</em>) : ce qui partira dans le prochain commit ;</li><li>le <strong>dépôt</strong> (dossier caché <code>.git</code>) : l'historique des commits.</li></ul><pre>git init                  # transforme le dossier courant en dépôt<br>git status                # que s'est-il passé depuis le dernier commit ?<br>git add fichier           # ajoute une modification à l'index<br>git add .                 # ajoute tout le dossier<br>git commit -m "Message"   # enregistre l'index dans un commit<br>git log --oneline         # historique, une ligne par commit</pre><h3>Ignorer des fichiers</h3><p>Un fichier <code>.gitignore</code> (versionné lui aussi) liste les fichiers que Git doit ignorer : brouillons, mots de passe, fichiers générés…</p><pre>brouillon-perso.txt<br>*.log<br>node_modules/</pre><p>Un fichier <strong>déjà suivi</strong> par Git n'est pas concerné par <code>.gitignore</code> : il faut d'abord le retirer de l'index, sans le supprimer du disque :</p><pre>git rm --cached fichier</pre><div class="tip">Un dépôt est créé avec la branche par défaut du moment. Pour renommer la branche courante : <code>git branch -m main</code>.</div>""",
        "setup": r'''
chantier $H/procedures
printf '# Sauvegardes\n\n1. Vérifier chaque lundi le rapport de sauvegarde.\n2. Tester une restauration par mois.\n' > sauvegarde.md
printf "# Comptes\n\nTout nouveau salarié reçoit un compte le jour de son arrivée.\n" > comptes.md
printf "# Imprimantes\n\nL'imprimante du 2e étage se relance en l'éteignant 30 secondes.\n" > imprimantes.md
printf 'Notes perso, à ne pas partager : penser à demander une augmentation.\n' > brouillon-perso.txt
livre
''',
        "exercises": [
            {"id": "G1.1", "points": 2, "title": "Se présenter à Git",
             "ticket": {"from": "sophie", "body": "Bienvenue dans l'équipe ! Avant toute chose, configure Git sur ce serveur : ton nom (« Prénom Nom ») et ton adresse professionnelle en <code>prenom.nom@cimes-sentiers.fr</code>. Chez nous, la branche principale s'appelle <strong>main</strong> : fais en sorte que tes nouveaux dépôts l'utilisent."},
             "desc": "Configuration globale : <code>user.name</code>, <code>user.email</code> (en <code>@cimes-sentiers.fr</code>) et <code>init.defaultBranch</code> = <code>main</code>.",
             "hints": ["<code>git config --global user.name \"Prénom Nom\"</code>, et de même pour <code>user.email</code>.", "<code>git config --global init.defaultBranch main</code> ; vérifiez avec <code>git config --global --list</code>."],
             "checks": [
                 ('n=$(gget user.name); [ -n "$n" ] && [ "$n" != etudiant ]', "Votre nom n'est pas configuré (git config --global user.name)."),
                 ('gget user.email | grep -qE "^[A-Za-z0-9._-]+@cimes-sentiers\\.fr$"', "Votre adresse doit être de la forme prenom.nom@cimes-sentiers.fr (git config --global user.email)."),
                 ('[ "$(gget init.defaultBranch)" = main ]', "Les nouveaux dépôts doivent utiliser la branche main (init.defaultBranch)."),
             ]},
            {"id": "G1.2", "points": 3, "title": "Versionner les procédures",
             "ticket": {"from": "lea", "body": "Mes procédures d'exploitation sont dans <code>~/procedures</code>, et je ne sais jamais qui a changé quoi. Mets ce dossier sous Git et fais un premier commit avec les trois procédures (<code>.md</code>)."},
             "desc": "<code>~/procedures</code> est un dépôt Git sur la branche <code>main</code>, dont un commit à votre nom contient <code>sauvegarde.md</code>, <code>comptes.md</code> et <code>imprimantes.md</code>.",
             "hints": ["<code>cd ~/procedures</code>, puis <code>git init</code>, <code>git add</code>, <code>git commit -m \"...\"</code>.", "Un commit fait avant de configurer votre identité ? <code>git commit --amend --reset-author</code>. Mauvaise branche ? <code>git branch -m main</code>."],
             "checks": [
                 ('[ -d $H/procedures/.git ]', "~/procedures n'est pas un dépôt Git (git init dans ce dossier)."),
                 ('g $H/procedures rev-parse -q --verify HEAD', "Le dépôt ne contient encore aucun commit."),
                 ('[ "$(g $H/procedures branch --show-current)" = main ]', "La branche doit s'appeler main (git branch -m main)."),
                 ('for f in sauvegarde.md comptes.md imprimantes.md; do g $H/procedures cat-file -e HEAD:$f || exit 1; done', "Les trois procédures (.md) doivent être dans le dernier commit."),
                 ('[ "$(g $H/procedures log -1 --format=%ae)" = "$(gget user.email)" ]', "Le commit n'est pas à votre nom : configurez votre identité, puis git commit --amend --reset-author."),
             ]},
            {"id": "G1.3", "points": 3, "title": "Ce qui ne regarde que moi",
             "ticket": {"from": "lea", "body": "Oups, j'avais oublié mon <code>brouillon-perso.txt</code> dans ce dossier. Il ne doit <strong>pas</strong> être dans le dépôt, ni maintenant ni plus tard, mais je veux garder le fichier sur le disque."},
             "desc": "<code>brouillon-perso.txt</code> existe toujours sur le disque, n'est pas dans le dernier commit et est ignoré grâce à un <code>.gitignore</code> commité ; <code>git status</code> n'affiche rien.",
             "hints": ["Un fichier <code>.gitignore</code> contenant <code>brouillon-perso.txt</code>, à ajouter et commiter.", "S'il a déjà été commité : <code>git rm --cached brouillon-perso.txt</code>, puis un commit."],
             "checks": [
                 ('[ -f $H/procedures/brouillon-perso.txt ]', "brouillon-perso.txt a disparu du disque : il fallait seulement le retirer du dépôt (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('! g $H/procedures cat-file -e HEAD:brouillon-perso.txt 2>/dev/null', "brouillon-perso.txt est encore dans le dernier commit (git rm --cached, puis commit)."),
                 ('g $H/procedures cat-file -e HEAD:.gitignore', "Le fichier .gitignore doit être commité."),
                 ('g $H/procedures check-ignore -q brouillon-perso.txt', "brouillon-perso.txt n'est pas ignoré par Git (.gitignore)."),
                 ('propre $H/procedures', "git status signale encore des fichiers modifiés ou non suivis : commitez-les."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Jour 2 — Enquête dans les archives de Marc",
        "description": "Explorer et corriger l'historique sans le réécrire. Compétences : log, show, diff, log -S, restore, revert.",
        "lesson": """<h3>Lire l'historique</h3><pre>git log                      # tous les commits, du plus récent au plus ancien<br>git log --oneline --graph    # compact, avec les branches<br>git log -p fichier           # l'historique d'un fichier, avec les modifications<br>git log --author=Marc<br>git log -S "texte"           # commits qui ont ajouté ou retiré ce texte (la « pioche »)<br>git log --diff-filter=D --name-only   # commits qui ont supprimé des fichiers</pre><h3>Examiner un commit</h3><pre>git show 3f9c2a1             # message et modifications d'un commit<br>git show 3f9c2a1:js/panier.js   # un fichier tel qu'il était dans ce commit<br>git diff                     # modifications pas encore indexées<br>git diff --staged            # modifications indexées<br>git diff a1b2c3d 3f9c2a1     # entre deux commits<br>git blame fichier            # qui a écrit chaque ligne ?</pre><p><code>HEAD</code> désigne le commit courant ; <code>HEAD~1</code> (ou <code>HEAD^</code>) son parent, <code>3f9c2a1^</code> le parent de <code>3f9c2a1</code>.</p><h3>Récupérer une ancienne version d'un fichier</h3><pre>git restore --source=3f9c2a1 chemin/fichier   # (ancienne syntaxe : git checkout 3f9c2a1 -- chemin/fichier)</pre><p>Le fichier revient dans le répertoire de travail : il reste à l'ajouter et à le commiter.</p><h3>Annuler un commit… sans réécrire l'histoire</h3><pre>git revert 3f9c2a1</pre><p><code>revert</code> crée un <strong>nouveau commit</strong> qui applique l'inverse du commit visé. L'historique reste intact : c'est la seule façon correcte d'annuler un commit déjà partagé avec l'équipe.</p><div class="tip"><code>git revert</code> ouvre l'éditeur pour le message : enregistrez et quittez (ou ajoutez <code>--no-edit</code>).</div>""",
        "setup": r'''
S=$H/archives-site
nouveau_depot $S
mkdir -p js data
printf '<h1>Cimes & Sentiers</h1>\n<p>Boutique de randonnée</p>\n' > index.html
cat > js/panier.js <<'EOF'
// Calcul du panier
const TVA = 0.20;

function prixTTC(prixHT) {
  return Math.round(prixHT * (1 + TVA) * 100) / 100;
}
EOF
printf 'fournisseur;telephone\nAltiSport;04 76 %02d %02d %02d\nTrekPro;04 76 %02d %02d %02d\n' \
  $((RANDOM%90+10)) $((RANDOM%90+10)) $((RANDOM%90+10)) $((RANDOM%90+10)) $((RANDOM%90+10)) $((RANDOM%90+10)) > data/fournisseurs.csv
commit marc 2000 "Import du site"
printf '<p>Mentions légales : Cimes & Sentiers SARL</p>\n' > mentions.html
commit marc 1900 "Ajout des mentions légales"
printf 'h1 { color: #2d6a4f; }\n' > style.css
commit marc 1800 "Un peu de couleur"
sed -i 's/const TVA = 0.20;/const TVA = 0.055;/' js/panier.js
commit marc 1700 "Optimisation du panier"
emit TVA "$(git rev-parse HEAD)"
printf '<p>Livraison offerte dès 60 euros</p>\n' >> index.html
commit marc 1600 "Livraison offerte"
emit AVANT "$(git rev-parse HEAD)"
git rm -q data/fournisseurs.csv
commit marc 1500 "Ménage"
printf 'p { line-height: 1.5; }\n' >> style.css
commit marc 1400 "Interlignage"
printf '<p>Contact : contact@cimes-sentiers.fr</p>\n' >> mentions.html
commit marc 1300 "Adresse de contact"
livre
''',
        "exercises": [
            {"id": "G2.1", "points": 3, "title": "Qui a cassé la TVA ?",
             "ticket": {"from": "diallo", "body": "Les factures du site appliquent une TVA de 5,5 % au lieu de 20 % ! Le site vient des archives de Marc (<code>~/archives-site</code>). Je dois savoir <strong>quel commit</strong> a introduit ce taux, pour dater le problème."},
             "desc": "L'identifiant (hash, abrégé ou complet) du commit qui a introduit <code>0.055</code> dans <code>js/panier.js</code>, dans <code>~/commit-tva.txt</code>.",
             "hints": ["<code>git log -p js/panier.js</code> montre chaque modification du fichier.", "Plus direct : <code>git log -S \"0.055\" --oneline</code>."],
             "checks": [
                 ('hashok $H/commit-tva.txt "$LAB_TVA"', "~/commit-tva.txt ne contient pas l'identifiant du commit qui a introduit le taux de 0.055 (7 caractères au moins)."),
             ]},
            {"id": "G2.2", "points": 4, "title": "Le fichier des fournisseurs",
             "ticket": {"from": "diallo", "body": "Et pendant que tu y es : le fichier <code>data/fournisseurs.csv</code> a disparu des archives. Marc l'a supprimé à un moment, mais j'en ai besoin ! Remets-le dans le dépôt tel qu'il était."},
             "desc": "<code>data/fournisseurs.csv</code> est de retour dans le dernier commit de <code>~/archives-site</code>, avec son contenu d'avant la suppression.",
             "hints": ["<code>git log --diff-filter=D --name-only</code> trouve le commit qui l'a supprimé.", "Le fichier existe encore dans le <strong>parent</strong> de ce commit : <code>git restore --source=&lt;hash&gt;^ data/fournisseurs.csv</code>, puis add et commit."],
             "checks": [
                 ('g $H/archives-site cat-file -e HEAD:data/fournisseurs.csv', "data/fournisseurs.csv n'est pas dans le dernier commit de ~/archives-site."),
                 ('[ "$(g $H/archives-site show HEAD:data/fournisseurs.csv)" = "$(g $H/archives-site show "$LAB_AVANT:data/fournisseurs.csv")" ]', "Le contenu de data/fournisseurs.csv n'est pas celui d'avant sa suppression."),
             ]},
            {"id": "G2.3", "points": 4, "title": "Annuler sans effacer",
             "ticket": {"from": "nadia", "body": "Maintenant qu'on a trouvé le commit fautif, annule-le. Attention : ces archives ont été partagées, alors <strong>on ne réécrit pas l'historique</strong>. Le commit de Marc doit rester visible, et son annulation aussi."},
             "desc": "Un nouveau commit de <code>~/archives-site</code> annule celui de la TVA (<code>git revert</code>) : <code>js/panier.js</code> revient à <code>TVA = 0.20</code> et le commit de Marc est toujours dans l'historique.",
             "hints": ["<code>git revert &lt;hash&gt;</code> (le hash trouvé dans le premier ticket)."],
             "checks": [
                 ('g $H/archives-site merge-base --is-ancestor "$LAB_TVA" HEAD', "Le commit de Marc a disparu de l'historique : il fallait l'annuler avec git revert (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('g $H/archives-site show HEAD:js/panier.js | grep -q "const TVA = 0.20;"', "Dans le dernier commit, js/panier.js n'a pas retrouvé TVA = 0.20."),
                 ('g $H/archives-site log --format=%s "$LAB_TVA..HEAD" | grep -q "^Revert"', "Aucun commit « Revert … » : utilisez git revert plutôt qu'une correction à la main."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Jour 3 — Le dépôt de l'équipe",
        "description": "Récupérer le dépôt partagé et y publier. Compétences : clone, remote, push.",
        "lesson": """<h3>Dépôt local, dépôt distant</h3><p>Chaque développeur a son <strong>propre dépôt complet</strong> (tout l'historique). L'équipe partage un dépôt <strong>distant</strong>, souvent sur GitHub ou GitLab ; ici il est sur le serveur : <code>/srv/git/boutique.git</code>. C'est un dépôt <em>nu</em> (<em>bare</em>) : il n'a que l'historique, pas de répertoire de travail.</p><pre>git clone /srv/git/boutique.git           # crée ~/boutique (si lancé depuis ~)<br>git clone https://github.com/org/projet   # même chose avec un dépôt en ligne<br>git remote -v                             # le distant s'appelle « origin »</pre><h3>Publier ses commits</h3><pre>git add index.html<br>git commit -m "Correction d'une faute"<br>git push                                  # envoie les commits de main vers origin/main<br>git log --oneline --graph --all           # origin/main = dernière position connue du distant</pre><div class="tip">Rien ne part sur le dépôt de l'équipe tant que vous n'avez pas fait <code>git push</code>. Un commit local reste local.</div><h3>Remplacer du texte dans un fichier</h3><p>Avec <code>nano</code> (<kbd>Ctrl</kbd>+<kbd>\\</kbd> pour rechercher et remplacer) ou avec <code>sed -i 's/ancien/nouveau/' fichier</code>.</p>""",
        "setup": r'''
depot_equipe
''',
        "exercises": [
            {"id": "G3.1", "points": 2, "title": "Rejoindre l'équipe",
             "ticket": {"from": "nadia", "body": "Le code de la boutique est dans notre dépôt partagé <code>/srv/git/boutique.git</code>. Récupère-le dans <code>~/boutique</code>."},
             "desc": "<code>~/boutique</code> est un clone du dépôt partagé (distant <code>origin</code> = <code>/srv/git/boutique.git</code>).",
             "hints": ["Depuis votre dossier personnel : <code>git clone /srv/git/boutique.git</code>."],
             "checks": [
                 ('[ -d $B/.git ]', "~/boutique n'est pas un dépôt Git (git clone depuis votre dossier personnel)."),
                 ('u=$(g $B remote get-url origin); u=${u#file://}; [ "${u%/}" = /srv/git/boutique.git ]', "Le distant origin de ~/boutique doit être /srv/git/boutique.git."),
                 ('g $B cat-file -e HEAD:EQUIPE.md', "~/boutique ne contient pas le code de l'équipe."),
             ]},
            {"id": "G3.2", "points": 4, "title": "Première contribution",
             "ticket": {"from": "thomas", "body": "Honte à moi : il y a une faute sur la page d'accueil depuis le premier jour (« Randonée »). Tu peux la corriger et la publier ? Un commit à ton nom, sur <code>main</code>."},
             "desc": "Sur la branche <code>main</code> du dépôt partagé, <code>index.html</code> contient « Randonnée » (et plus « Randonée »), corrigé par un commit à votre nom.",
             "hints": ["Corrigez <code>index.html</code>, puis <code>git add</code>, <code>git commit</code>.", "Le commit n'est publié qu'après <code>git push</code>."],
             "checks": [
                 ('! depot grep -q "Randonée" main -- index.html', "La faute est toujours dans index.html du dépôt partagé (commit, puis git push)."),
                 ('depot show main:index.html | grep -q "Randonnée"', "index.html doit contenir « Randonnée » correctement orthographié."),
                 ('[ "$(depot log -1 --format=%ae main -- index.html)" = "$(gget user.email)" ]', "La correction doit être un commit à votre nom."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Jour 4 — À plusieurs sur la même branche",
        "description": "Se synchroniser avec le travail des autres. Compétences : fetch, pull, pull --rebase, push refusé.",
        "lesson": """<h3>Le push refusé</h3><p>Si un collègue a publié entre-temps, votre <code>git push</code> est refusé :</p><pre> ! [rejected]        main -> main (fetch first)<br>error: failed to push some refs to '/srv/git/boutique.git'</pre><p>Git refuse d'écraser un travail que vous n'avez pas encore récupéré. Il faut d'abord <strong>intégrer</strong> les commits du distant.</p><h3>Récupérer</h3><pre>git fetch                 # télécharge les nouveaux commits (met à jour origin/main), sans toucher à votre travail<br>git log --oneline --graph --all<br>git pull                  # fetch + intégration dans votre branche</pre><h3>Fusion ou rebase ?</h3><p>Quand vous avez des commits locaux <strong>et</strong> que le distant a avancé, les deux historiques ont divergé. <code>git pull</code> peut :</p><ul><li><strong>fusionner</strong> (<code>git pull --no-rebase</code>) : crée un commit de fusion (« Merge branch 'main' of … ») ;</li><li><strong>rebaser</strong> (<code>git pull --rebase</code>) : rejoue vos commits locaux <em>après</em> ceux du distant. L'historique reste linéaire, sans commit de fusion inutile.</li></ul><pre>git config --global pull.rebase true   # rebase par défaut à chaque git pull</pre><div class="tip">Ne forcez jamais (<code>git push --force</code>) sur une branche partagée : vous effaceriez le travail de vos collègues.</div>""",
        "setup": r'''
equipe
if [ -z "$(trouve "Calcul des frais de livraison")" ]; then
  mkdir -p js
  cat > js/livraison.js <<'EOF'
// Livraison offerte à partir de 60 euros
function fraisLivraison(total) {
  return total >= 60 ? 0 : 5.9;
}
EOF
  commit nadia 2 "Calcul des frais de livraison"
  pousse main
fi
emit NADIA "$(trouve "Calcul des frais de livraison")"
''',
        "exercises": [
            {"id": "G4.1", "points": 2, "title": "La règle de l'équipe",
             "ticket": {"from": "nadia", "body": "Chez nous, on garde un historique linéaire : pas de commits « Merge branch 'main' » à chaque synchronisation. Configure Git pour que <code>git pull</code> <strong>rebase</strong> par défaut."},
             "desc": "Configuration globale <code>pull.rebase</code> = <code>true</code>.",
             "hints": ["<code>git config --global pull.rebase true</code>"],
             "checks": [
                 ('[ "$(gget pull.rebase)" = true ]', "git pull ne rebase pas par défaut (git config --global pull.rebase true)."),
             ]},
            {"id": "G4.2", "points": 5, "title": "Mon nom sur la liste",
             "ticket": {"from": "thomas", "body": "Ajoute-toi dans <code>EQUIPE.md</code> (une ligne à ton nom, comme nous) et publie-le. Attention, Nadia vient de pousser un commit : ne l'écrase surtout pas !"},
             "desc": "Sur le dépôt partagé, <code>EQUIPE.md</code> contient votre nom (<code>user.name</code>), le commit de Nadia est toujours là, et votre <code>main</code> local est à jour avec <code>origin/main</code>.",
             "hints": ["Faites votre commit, puis <code>git push</code> : lisez bien le message de refus.", "<code>git pull</code> (qui rebase désormais), puis de nouveau <code>git push</code>."],
             "checks": [
                 ('n=$(gget user.name); [ -n "$n" ] && depot show main:EQUIPE.md | grep -qF -- "$n"', "Votre nom (user.name) n'apparaît pas dans EQUIPE.md sur le dépôt partagé."),
                 ('depot merge-base --is-ancestor "$LAB_NADIA" main', "Le commit de Nadia a disparu du dépôt partagé : jamais de push --force sur une branche commune ! (bouton « Réinitialiser les fichiers de cette étape » pour le republier)"),
                 ('[ "$(g $B rev-parse main)" = "$(depot rev-parse main)" ]', "Votre branche main locale n'est pas identique à celle du dépôt partagé (git pull, git push)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Jour 5 — Les branches",
        "description": "Développer à côté de main, puis fusionner. Compétences : branch, switch, push -u, merge, suppression de branches.",
        "lesson": """<h3>Une branche, c'est une étiquette mobile</h3><p>Une branche n'est qu'un <strong>pointeur</strong> vers un commit, qui avance à chaque nouveau commit. On développe une fonctionnalité sur sa propre branche pour ne pas perturber <code>main</code>.</p><pre>git branch                       # branches locales (* = courante)<br>git branch -a                    # y compris celles du distant (remotes/origin/…)<br>git switch -c feature/promo      # crée la branche et s'y place (ancien : git checkout -b)<br>git switch main                  # revient sur main</pre><h3>Publier une branche</h3><pre>git push -u origin feature/promo # -u : mémorise le lien avec origin/feature/promo (upstream)<br>git push                         # ensuite, un simple push suffit</pre><h3>Récupérer la branche d'un collègue</h3><pre>git fetch<br>git switch feature/avis          # crée la branche locale qui suit origin/feature/avis</pre><h3>Fusionner</h3><pre>git switch main<br>git merge feature/avis</pre><ul><li>Si <code>main</code> n'a pas bougé : <em>fast-forward</em>, l'étiquette avance simplement.</li><li>Sinon, Git crée un <strong>commit de fusion</strong> à deux parents (l'éditeur s'ouvre pour son message).</li></ul><h3>Faire le ménage</h3><pre>git branch -d feature/avis              # supprime la branche locale (refuse si elle n'est pas fusionnée)<br>git push origin --delete feature/avis   # supprime la branche du dépôt distant<br>git fetch --prune                       # oublie les branches distantes supprimées</pre>""",
        "setup": r'''
equipe
if [ -z "$(trouve "Avis : note moyenne")" ]; then
  git switch -q -c feature/avis-clients
  printf '<h2>Avis clients</h2>\n<blockquote>Sac très confortable, même après 20 km. - Claire</blockquote>\n' > avis.html
  commit thomas 5 "Page des avis clients"
  printf '<p>Note moyenne : 4,7 / 5</p>\n' >> avis.html
  commit thomas 4 "Avis : note moyenne"
  pousse feature/avis-clients
fi
emit AVIS "$(trouve "Avis : note moyenne")"
''',
        "exercises": [
            {"id": "G5.1", "points": 4, "title": "La promo d'été",
             "ticket": {"from": "sophie", "body": "Le marketing prépare une promo d'été, mais rien ne doit apparaître sur le site avant validation. Travaille sur une branche <code>feature/promo-ete</code> : ajoute une page <code>promo.html</code> et publie la branche sur le dépôt partagé, pour que je puisse la relire."},
             "desc": "Sur le dépôt partagé, une branche <code>feature/promo-ete</code> dont le dernier commit (à votre nom) contient <code>promo.html</code> ; la branche locale suit <code>origin/feature/promo-ete</code>.",
             "hints": ["<code>git switch -c feature/promo-ete</code>, créez <code>promo.html</code>, add, commit.", "<code>git push -u origin feature/promo-ete</code>"],
             "checks": [
                 ('depot rev-parse -q --verify refs/heads/feature/promo-ete', "La branche feature/promo-ete n'existe pas sur le dépôt partagé (git push -u origin feature/promo-ete)."),
                 ('depot cat-file -e feature/promo-ete:promo.html', "La branche feature/promo-ete ne contient pas promo.html."),
                 ('[ "$(depot log -1 --format=%ae feature/promo-ete)" = "$(gget user.email)" ]', "Le dernier commit de feature/promo-ete doit être à votre nom."),
                 ('[ "$(g $B rev-parse --abbrev-ref "feature/promo-ete@{upstream}")" = origin/feature/promo-ete ]', "Votre branche locale feature/promo-ete ne suit pas origin/feature/promo-ete (option -u de git push)."),
             ]},
            {"id": "G5.2", "points": 4, "title": "Les avis clients en ligne",
             "ticket": {"from": "thomas", "body": "Ma branche <code>feature/avis-clients</code> est terminée et relue par Nadia. Tu peux la fusionner dans <code>main</code> et publier ? Je suis en déplacement."},
             "desc": "La branche <code>feature/avis-clients</code> est fusionnée dans <code>main</code> sur le dépôt partagé (<code>avis.html</code> est sur <code>main</code>).",
             "hints": ["<code>git fetch</code>, puis <code>git switch main</code> et <code>git merge origin/feature/avis-clients</code> (ou <code>git switch feature/avis-clients</code> d'abord).", "N'oubliez pas <code>git push</code>."],
             "checks": [
                 ('depot merge-base --is-ancestor "$LAB_AVIS" main', "La branche feature/avis-clients n'est pas fusionnée dans main sur le dépôt partagé (merge, puis push)."),
                 ('depot cat-file -e main:avis.html', "avis.html n'est pas sur la branche main du dépôt partagé."),
             ]},
            {"id": "G5.3", "points": 3, "title": "Branches mortes",
             "ticket": {"from": "nadia", "body": "Une branche fusionnée, c'est une branche à supprimer : sinon, dans six mois, on en a cinquante. Supprime <code>feature/avis-clients</code> partout : sur le dépôt partagé et chez toi."},
             "desc": "<code>feature/avis-clients</code> n'existe plus ni sur le dépôt partagé ni dans <code>~/boutique</code>, et son travail est bien dans <code>main</code>.",
             "hints": ["<code>git push origin --delete feature/avis-clients</code>", "<code>git branch -d feature/avis-clients</code> (si vous l'aviez créée localement)."],
             "checks": [
                 ('depot merge-base --is-ancestor "$LAB_AVIS" main', "Le travail de feature/avis-clients doit d'abord être fusionné dans main (ticket précédent)."),
                 ('! depot rev-parse -q --verify refs/heads/feature/avis-clients', "La branche existe toujours sur le dépôt partagé (git push origin --delete feature/avis-clients)."),
                 ('! g $B rev-parse -q --verify refs/heads/feature/avis-clients', "La branche locale feature/avis-clients existe toujours (git branch -d)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Jour 6 — Les conflits",
        "description": "Quand deux personnes modifient la même ligne. Compétences : conflit de fusion, marqueurs, résolution, merge --abort.",
        "lesson": """<h3>D'où vient un conflit ?</h3><p>Git fusionne seul les modifications de lignes différentes. Si <strong>la même ligne</strong> a été modifiée des deux côtés, il ne peut pas choisir : la fusion s'arrête sur un <strong>conflit</strong>.</p><pre>CONFLICT (content): Merge conflict in tarifs.html<br>Automatic merge failed; fix conflicts and then commit the result.</pre><h3>Lire les marqueurs</h3><pre>&lt;&lt;&lt;&lt;&lt;&lt;&lt; HEAD<br>  &lt;li&gt;version de votre branche&lt;/li&gt;<br>=======<br>  &lt;li&gt;version de la branche fusionnée&lt;/li&gt;<br>&gt;&gt;&gt;&gt;&gt;&gt;&gt; origin/feature/tarifs</pre><h3>Résoudre</h3><ol><li><code>git status</code> liste les fichiers en conflit (<em>both modified</em>).</li><li>Éditez chaque fichier : gardez le bon contenu (souvent un mélange des deux) et <strong>supprimez les trois marqueurs</strong>.</li><li><code>git add fichier</code> marque le conflit comme résolu.</li><li><code>git commit</code> termine la fusion (message déjà rempli).</li></ol><h3>Tout annuler</h3><pre>git merge --abort     # revient à l'état d'avant la fusion</pre><div class="tip">Avant de fusionner une branche dans <code>main</code>, mettez <code>main</code> à jour (<code>git pull</code>) : vous résolvez les conflits une fois, sur la dernière version.</div>""",
        "setup": r'''
equipe
if [ -z "$(trouve "Nouveau tarif du sac 40 L")" ]; then
  git switch -q -c feature/tarifs
  sed -i 's|<li>Sac 40 L : 79 euros</li>|<li>Sac 40 L : 89 euros</li>|' tarifs.html
  commit nadia 3 "Nouveau tarif du sac 40 L"
  pousse feature/tarifs
  git switch -q main
  sed -i 's|<li>Sac 40 L : 79 euros</li>|<li>Sac à dos 40 L : 79 euros</li>|' tarifs.html
  commit thomas 2 "Libellés plus clairs sur les tarifs"
  pousse main
fi
emit TARIF "$(trouve "Nouveau tarif du sac 40 L")"
emit LIBELLE "$(trouve "Libellés plus clairs sur les tarifs")"
J=$H/depot-julien
nouveau_depot $J
printf 'Planning de la semaine\nLundi : inventaire\nMardi : commandes\n' > planning.txt
commit julien 30 "Planning initial"
git switch -q -c version-lea
sed -i 's/Lundi : inventaire/Lundi : réunion équipe/' planning.txt
commit lea 20 "Réunion le lundi"
git switch -q main
sed -i 's/Lundi : inventaire/Lundi : livraison fournisseur/' planning.txt
commit julien 10 "Livraison le lundi"
emit JULIEN "$(git rev-parse HEAD)"
GIT_AUTHOR_NAME=x GIT_AUTHOR_EMAIL=x GIT_COMMITTER_NAME=x GIT_COMMITTER_EMAIL=x git merge -q version-lea >/dev/null 2>&1 || true
livre
''',
        "exercises": [
            {"id": "G6.1", "points": 6, "title": "Le prix du sac",
             "ticket": {"from": "nadia", "body": "J'ai poussé une branche <code>feature/tarifs</code> avec le nouveau prix du sac 40 L. Mais Thomas a modifié la même ligne sur <code>main</code> pour clarifier le libellé… Fusionne ma branche dans <code>main</code> et publie. Il faut garder <strong>le libellé de Thomas</strong> et <strong>mon prix</strong>."},
             "desc": "Sur le dépôt partagé, <code>main</code> contient le commit de Thomas et la branche <code>feature/tarifs</code>, <code>tarifs.html</code> contient exactement <code>&lt;li&gt;Sac à dos 40 L : 89 euros&lt;/li&gt;</code>, et aucun marqueur de conflit ne subsiste.",
             "hints": ["D'abord <code>git switch main</code> et <code>git pull</code> (Thomas a poussé), puis <code>git merge origin/feature/tarifs</code>.", "Dans <code>tarifs.html</code>, remplacez le bloc <code>&lt;&lt;&lt;&lt;&lt;&lt;&lt;</code> … <code>&gt;&gt;&gt;&gt;&gt;&gt;&gt;</code> par la bonne ligne, puis <code>git add tarifs.html</code>, <code>git commit</code> et <code>git push</code>."],
             "checks": [
                 ('depot merge-base --is-ancestor "$LAB_TARIF" main', "La branche feature/tarifs n'est pas fusionnée dans main sur le dépôt partagé."),
                 ('depot merge-base --is-ancestor "$LAB_LIBELLE" main', "Le commit de Thomas a disparu de main : jamais de push --force sur une branche commune !"),
                 ('! depot grep -qE "^(<<<<<<<|=======|>>>>>>>)" main', "Des marqueurs de conflit (<<<<<<<, =======, >>>>>>>) ont été commités."),
                 ('depot show main:tarifs.html | grep -qF "<li>Sac à dos 40 L : 89 euros</li>"', "tarifs.html doit contenir la ligne « Sac à dos 40 L : 89 euros » : le libellé de Thomas et le prix de Nadia."),
             ]},
            {"id": "G6.2", "points": 3, "title": "Julien est coincé",
             "ticket": {"from": "julien", "body": "Au secours ! J'ai lancé une fusion dans <code>~/depot-julien</code>, et maintenant Git me parle de conflit, et il y a des chevrons partout dans mon planning. Je ne veux pas de cette fusion, je veux juste revenir comme avant !"},
             "desc": "Dans <code>~/depot-julien</code>, la fusion est annulée : plus de fusion en cours, <code>main</code> est revenu sur son dernier commit et le répertoire de travail est propre.",
             "hints": ["<code>git status</code> explique la situation… et comment en sortir.", "<code>git merge --abort</code>"],
             "checks": [
                 ('[ ! -f $H/depot-julien/.git/MERGE_HEAD ]', "Une fusion est toujours en cours dans ~/depot-julien."),
                 ('[ "$(g $H/depot-julien rev-parse HEAD)" = "$LAB_JULIEN" ]', "La branche de Julien n'est plus sur son dernier commit : il fallait annuler la fusion, pas la terminer (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('propre $H/depot-julien', "Le répertoire de travail de ~/depot-julien n'est pas propre (git status)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    7: {
        "title": "Jour 7 — Réécrire son histoire locale",
        "description": "Mettre de côté, corriger le dernier commit, rebaser une branche. Compétences : stash, commit --amend, rebase.",
        "lesson": """<h3>Mettre son travail de côté</h3><pre>git stash            # range les modifications en cours et nettoie le répertoire de travail<br>git stash list<br>git stash pop        # réapplique les modifications rangées (et les retire de la liste)</pre><p>Utile quand une urgence tombe : on range, on change de branche, on corrige, on revient, on reprend.</p><h3>Corriger le dernier commit</h3><pre>git add fichier-oublie<br>git commit --amend -m "Nouveau message"   # remplace le dernier commit</pre><p><code>--amend</code> ne modifie pas le commit : il en crée un nouveau qui le <strong>remplace</strong> (nouveau hash). Sans <code>-m</code>, l'éditeur s'ouvre sur l'ancien message.</p><h3>Rebaser une branche</h3><p>Votre branche est partie d'un ancien <code>main</code>, qui a avancé depuis. Plutôt que de fusionner <code>main</code> dedans, on <strong>rejoue</strong> ses commits au-dessus du <code>main</code> actuel :</p><pre>git switch feature/filtres<br>git rebase main</pre><pre>avant :     A---B---C  main          après :   A---B---C  main<br>                 \\                                      \\<br>                  D---E  feature                         D'---E'  feature</pre><p>Les commits D et E sont recréés (D', E' : nouveaux hash). L'historique est linéaire, et la fusion dans <code>main</code> sera un simple <em>fast-forward</em>.</p><div class="tip">Règle d'or : on ne réécrit (amend, rebase) que des commits <strong>pas encore partagés</strong>. Réécrire des commits déjà poussés oblige tous les collègues à réparer leur dépôt.</div>""",
        "setup": r'''
A=$H/atelier
nouveau_depot $A
printf '<h1>Cimes & Sentiers</h1>\n' > index.html
printf '<p>Téléphone : 04 76 00 00 0</p>\n' > contact.html
commit thomas 50 "Site initial"
git switch -q -c feature/newsletter
printf "<form>Inscription à la newsletter</form>\n" > newsletter.html
commit thomas 5 "Début de la newsletter"
printf '<p>BROUILLON-NEWSLETTER : texte à faire relire par Sophie</p>\n' >> newsletter.html
livre
C=$H/corrections
nouveau_depot $C
mkdir -p js
printf 'function total(articles) {\n  return articles.reduce((s, a) => s + a.prix, 0);\n}\n' > js/panier.js
commit thomas 30 "Calcul du total du panier"
emit PARENT "$(git rev-parse HEAD)"
sed -i 's/s + a.prix/s + a.prix * a.quantite/' js/panier.js
commit julien 1 "corection du panié"
printf 'const REMISE_FIDELITE = 0.05;\n' > js/remise.js
livre
F=$H/filtres
nouveau_depot $F
printf '<h2>Catalogue</h2>\n' > catalogue.html
commit nadia 60 "Catalogue"
git switch -q -c feature/filtres
printf 'function filtrePrix(produits, max) { return produits.filter(p => p.prix <= max); }\n' > filtre-prix.js
commit thomas 40 "Filtre par prix"
printf 'function filtreMarque(produits, m) { return produits.filter(p => p.marque === m); }\n' > filtre-marque.js
commit thomas 39 "Filtre par marque"
git switch -q main
printf '<p>Promo : -20 %% sur les tentes</p>\n' > promo.html
commit nadia 20 "Bannière promo"
printf '<p>Mentions légales</p>\n' > mentions.html
commit nadia 19 "Mentions légales"
emit MAINF "$(git rev-parse main)"
git switch -q feature/filtres
livre
''',
        "exercises": [
            {"id": "G7.1", "points": 5, "title": "Urgence pendant la newsletter",
             "ticket": {"from": "sophie", "body": "Tu es sur la newsletter (<code>~/atelier</code>, branche <code>feature/newsletter</code>, travail pas terminé) ? Laisse tout de côté : le numéro de téléphone de <code>contact.html</code> est faux sur <code>main</code>, il manque un chiffre. Le bon, c'est <strong>04 76 00 00 00</strong>. Corrige-le sur <code>main</code>, puis reprends ta newsletter là où tu en étais, sans commiter ton brouillon."},
             "desc": "Dans <code>~/atelier</code> : <code>main</code> a un commit qui corrige le numéro (<code>04 76 00 00 00</code>) sans contenir le brouillon ; vous êtes revenu sur <code>feature/newsletter</code> avec le brouillon (non commité) restauré, et le stash est vide.",
             "hints": ["<code>git switch main</code> refuse de vous laisser partir avec le brouillon : <code>git stash</code> d'abord.", "Après la correction sur main : <code>git switch feature/newsletter</code> puis <code>git stash pop</code>."],
             "checks": [
                 ('g $H/atelier show main:contact.html | grep -q "04 76 00 00 00"', "Sur main, contact.html n'a pas le bon numéro (04 76 00 00 00) dans un commit."),
                 ('! g $H/atelier grep -q BROUILLON main --', "Le brouillon de la newsletter a été commité sur main."),
                 ('[ "$(g $H/atelier branch --show-current)" = feature/newsletter ]', "Vous devez être revenu sur la branche feature/newsletter."),
                 ('grep -q BROUILLON-NEWSLETTER $H/atelier/newsletter.html', "Le brouillon de newsletter.html n'est pas restauré dans le répertoire de travail (git stash pop)."),
                 ('! g $H/atelier grep -q BROUILLON feature/newsletter --', "Le brouillon ne doit pas être commité : il n'est pas relu."),
                 ('[ -z "$(g $H/atelier stash list)" ]', "Le stash n'est pas vide : utilisez git stash pop (et non apply), ou git stash drop."),
             ]},
            {"id": "G7.2", "points": 3, "title": "Un commit à rattraper",
             "ticket": {"from": "julien", "body": "J'ai commité dans <code>~/corrections</code> avec un message plein de fautes, et j'ai oublié le fichier <code>js/remise.js</code>… Je n'ai rien poussé. Tu peux arranger ça ? Le message doit être <strong>Correction du calcul du panier</strong>, et pas de commit en plus, Nadia déteste ça."},
             "desc": "Dans <code>~/corrections</code>, le dernier commit (qui remplace celui de Julien, même parent) a pour message <code>Correction du calcul du panier</code> et contient <code>js/remise.js</code> et la correction de <code>js/panier.js</code>.",
             "hints": ["<code>git add js/remise.js</code>, puis <code>git commit --amend</code>.", "<code>git commit --amend -m \"Correction du calcul du panier\"</code>"],
             "checks": [
                 ('[ "$(g $H/corrections log -1 --format=%s)" = "Correction du calcul du panier" ]', "Le message du dernier commit n'est pas « Correction du calcul du panier »."),
                 ('[ "$(g $H/corrections rev-parse HEAD^)" = "$LAB_PARENT" ]', "Le commit de Julien doit être remplacé, pas complété par un nouveau commit (git commit --amend)."),
                 ('g $H/corrections cat-file -e HEAD:js/remise.js', "js/remise.js n'est pas dans le dernier commit."),
                 ('g $H/corrections show HEAD:js/panier.js | grep -q "a.prix \\* a.quantite"', "La correction de js/panier.js a été perdue."),
             ]},
            {"id": "G7.3", "points": 5, "title": "Une histoire linéaire",
             "ticket": {"from": "nadia", "body": "La branche <code>feature/filtres</code> de Thomas (<code>~/filtres</code>) est partie d'un vieux <code>main</code>. Avant la relecture, rebase-la sur le <code>main</code> actuel : je veux ses deux commits au-dessus de <code>main</code>, sans commit de fusion. Et ne touche pas à <code>main</code>."},
             "desc": "Dans <code>~/filtres</code>, <code>main</code> n'a pas bougé et <code>feature/filtres</code> contient ses deux commits (« Filtre par prix », « Filtre par marque ») rejoués au-dessus de <code>main</code>, sans commit de fusion.",
             "hints": ["<code>git switch feature/filtres</code>, puis <code>git rebase main</code>.", "Vérifiez avec <code>git log --oneline --graph --all</code>."],
             "checks": [
                 ('[ "$(g $H/filtres rev-parse main)" = "$LAB_MAINF" ]', "main a été modifié : c'est feature/filtres qu'il faut rebaser (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('g $H/filtres merge-base --is-ancestor main feature/filtres', "feature/filtres n'est pas basée sur le main actuel (git rebase main)."),
                 ('[ -z "$(g $H/filtres rev-list --merges main..feature/filtres)" ]', "feature/filtres contient un commit de fusion : il fallait rebaser, pas fusionner."),
                 ('[ "$(g $H/filtres log --format=%s main..feature/filtres | sort | tr "\\n" "|")" = "Filtre par marque|Filtre par prix|" ]', "feature/filtres doit contenir exactement ses deux commits « Filtre par prix » et « Filtre par marque » au-dessus de main."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Jour 8 — Enquêtes et mise en production",
        "description": "Trouver un bug par dichotomie, étiqueter une version, récupérer un commit perdu. Compétences : bisect, tag, reflog.",
        "lesson": """<h3>Trouver le commit fautif par dichotomie</h3><p>Le code marchait il y a 40 commits, il ne marche plus. <code>git bisect</code> coupe l'intervalle en deux à chaque étape : au plus 6 tests pour 40 commits.</p><pre>git bisect start<br>git bisect bad                  # le commit courant est mauvais<br>git bisect good &lt;hash&gt;          # celui-ci était bon<br># Git se place au milieu : testez, puis dites-lui<br>git bisect good   # ou   git bisect bad<br># … jusqu'à « &lt;hash&gt; is the first bad commit »<br>git bisect reset                # revient où vous étiez</pre><p>Si un script dit si c'est bon (code de retour 0) ou mauvais (autre code), Git fait tout seul :</p><pre>git bisect run ./tests.sh</pre><h3>Étiqueter une version</h3><pre>git tag -a v1.0 -m "Première version en production"   # étiquette annotée (auteur, date, message)<br>git tag                                               # liste<br>git show v1.0<br>git push origin v1.0                                  # les étiquettes ne partent pas avec un simple git push</pre><p>Sans <code>-a</code>, l'étiquette est « légère » : un simple nom, sans auteur ni message. Pour une version livrée, on préfère une étiquette annotée.</p><h3>Rien n'est vraiment perdu</h3><p>Un <code>git reset --hard</code> malheureux a « effacé » des commits ? Ils existent encore : le <strong>reflog</strong> garde la trace de toutes les positions de <code>HEAD</code>.</p><pre>git reflog                       # HEAD@{0}, HEAD@{1}… avec les hash<br>git branch sauvetage &lt;hash&gt;      # une branche pour ne plus le perdre<br>git reset --hard &lt;hash&gt;          # ou remettre la branche courante dessus</pre>""",
        "setup": r'''
K=$H/calculs
nouveau_depot $K
cat > prix.sh <<'EOF'
#!/bin/bash
# Prix TTC d'un prix hors taxes (TVA à 20 %)
awk -v p="$1" 'BEGIN { printf "%.2f\n", p * 1.20 }'
EOF
cat > tests.sh <<'EOF'
#!/bin/bash
# Test du calcul : code de retour 0 si tout va bien
[ "$(./prix.sh 100)" = "120.00" ] && echo "OK" || { echo "ÉCHEC : ./prix.sh 100 donne $(./prix.sh 100)"; exit 1; }
EOF
chmod 755 prix.sh tests.sh
printf '# Historique\n' > CHANGELOG.md
commit marc 1000 "Calcul du prix TTC"
emit BON "$(git rev-parse HEAD)"
MSGS=("Mise à jour du changelog" "Nettoyage" "Commentaires" "Relecture" "Petites corrections" "Mise en forme" "Refonte légère")
bug=$((RANDOM % 22 + 8))
for i in $(seq 1 36); do
  echo "- modification $i" >> CHANGELOG.md
  if [ $i -eq $bug ]; then sed -i 's/p \* 1.20/p * 1.02/' prix.sh; fi
  sed -i "2s/.*/# Prix TTC d'un prix hors taxes (TVA à 20 %) - révision $i/" prix.sh
  commit marc $((1000 - i * 20)) "${MSGS[i % 7]}"
  if [ $i -eq $bug ]; then emit BUG "$(git rev-parse HEAD)"; fi
done
livre
P=$H/rapport
nouveau_depot $P
printf '# Rapport annuel\n' > rapport.md
commit julien 50 "Plan du rapport"
printf '\n## Chiffres\n\nChiffre d affaires : 2,4 M euros\n' >> rapport.md
commit julien 40 "Chiffres de l'année"
printf '\n## Conclusion\n\nUne très belle année.\n' >> rapport.md
commit julien 30 "Conclusion"
emit PERDU "$(git rev-parse HEAD)"
git reset -q --hard HEAD~2
livre
''',
        "exercises": [
            {"id": "G8.1", "points": 5, "title": "Le bug du prix TTC",
             "ticket": {"from": "diallo", "body": "Le script <code>prix.sh</code> de Marc (<code>~/calculs</code>) donne des prix TTC faux, alors qu'il était juste au premier commit. Il y a eu des dizaines de commits depuis, avec des messages qui ne veulent rien dire. Trouve celui qui a tout cassé. Le script <code>tests.sh</code> dit si le calcul est bon."},
             "desc": "L'identifiant du premier commit où <code>./tests.sh</code> échoue, dans <code>~/commit-fautif.txt</code>.",
             "hints": ["<code>git bisect start</code>, <code>git bisect bad</code>, puis <code>git bisect good</code> suivi du hash du premier commit (<code>git log --oneline | tail -1</code>).", "Laissez Git tester tout seul : <code>git bisect run ./tests.sh</code>. N'oubliez pas <code>git bisect reset</code> à la fin."],
             "checks": [
                 ('hashok $H/commit-fautif.txt "$LAB_BUG"', "~/commit-fautif.txt ne contient pas l'identifiant du commit qui a introduit le bug (7 caractères au moins)."),
             ]},
            {"id": "G8.2", "points": 3, "title": "Version 1.0",
             "ticket": {"from": "sophie", "body": "Le site part en production ! Pose une étiquette <strong>annotée</strong> <code>v1.0</code> sur le <code>main</code> actuel de la boutique (avec les tarifs corrigés) et publie-la, qu'on puisse toujours retrouver ce qui a été livré."},
             "desc": "Le dépôt partagé contient une étiquette annotée <code>v1.0</code> qui désigne un commit de <code>main</code> incluant la correction des tarifs.",
             "hints": ["Dans <code>~/boutique</code>, à jour sur main : <code>git tag -a v1.0 -m \"...\"</code>.", "<code>git push origin v1.0</code>"],
             "checks": [
                 ('depot rev-parse -q --verify refs/tags/v1.0', "L'étiquette v1.0 n'est pas sur le dépôt partagé (git push origin v1.0)."),
                 ('[ "$(depot cat-file -t v1.0)" = tag ]', "v1.0 est une étiquette légère : il faut une étiquette annotée (git tag -a)."),
                 ('depot merge-base --is-ancestor "v1.0^{commit}" main', "v1.0 doit désigner un commit de la branche main."),
                 ('depot show v1.0:tarifs.html | grep -qF "Sac à dos 40 L : 89 euros"', "v1.0 ne contient pas la correction des tarifs du jour 6 : étiquetez le main à jour."),
             ]},
            {"id": "G8.3", "points": 4, "title": "Le rapport disparu",
             "ticket": {"from": "julien", "body": "Catastrophe : j'ai tapé une commande trouvée sur Internet (<code>git reset --hard HEAD~2</code>) dans <code>~/rapport</code>, et mes deux derniers commits, dont la conclusion du rapport annuel, ont disparu ! Il faut le rendre demain…"},
             "desc": "Dans <code>~/rapport</code>, une branche <code>sauvetage</code> désigne le commit « Conclusion » disparu.",
             "hints": ["<code>git reflog</code> liste toutes les positions de HEAD, même « effacées ».", "<code>git branch sauvetage &lt;hash du commit Conclusion&gt;</code>"],
             "checks": [
                 ('g $H/rapport rev-parse -q --verify refs/heads/sauvetage', "Il n'y a pas de branche sauvetage dans ~/rapport."),
                 ('[ "$(g $H/rapport rev-parse sauvetage)" = "$LAB_PERDU" ]', "La branche sauvetage ne désigne pas le commit « Conclusion » disparu (git reflog)."),
             ]},
        ],
    },
}
