"""Parcours « Git : travailler en équipe ».

Chaque étudiant dispose d'un serveur avec Git et d'un dépôt partagé de l'équipe (dépôt nu local dans
/srv/git : pas besoin d'Internet). Les collègues y « poussent » leurs commits au fil des mises en place.
Sécurité : les dépôts de l'étudiant (et le dépôt partagé, qu'il peut modifier) ne sont jamais manipulés par git en
root, car leur configuration et leurs hooks pourraient exécuter du code. Les vérifications lancent git en tant
qu'etudiant ; les mises en place préparent les dépôts dans un dossier réservé à root, puis les livrent d'un bloc, et
passent par git-upload-pack / git-receive-pack exécutés en tant qu'etudiant pour échanger avec le dépôt partagé.
Les exercices dont la réponse est écrite dans un fichier (identifiant, nombre, code) ou qui exécutent du code de
l'étudiant sont « manual » : sinon, la vérification automatique permettrait d'essayer toutes les réponses.
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
# identite <collègue> <il y a N heures> : auteur et committer des commandes Git qui suivent
identite() {
  local d; d=$(date -d "-$2 hours" '+%Y-%m-%d %H:%M:%S')
  export GIT_AUTHOR_NAME="${NOM[$1]}" GIT_AUTHOR_EMAIL="${MAIL[$1]}@cimes-sentiers.fr" GIT_AUTHOR_DATE="$d" \
    GIT_COMMITTER_NAME="${NOM[$1]}" GIT_COMMITTER_EMAIL="${MAIL[$1]}@cimes-sentiers.fr" GIT_COMMITTER_DATE="$d"
}
# commit <collègue> <il y a N heures> <message> : commite tout le dossier courant au nom d'un collègue
# (--allow-empty : une mise en place rejouée sur un dépôt déjà modifié ne doit pas échouer)
commit() { ( identite "$1" "$2"; git add -A; git commit -q --allow-empty -m "$3" ); }
# fusionne <collègue> <il y a N heures> <branche> <message> : vraie fusion (sans avance rapide) au nom d'un collègue
fusionne() { ( identite "$1" "$2"; git merge -q --no-ff -m "$4" "$3" ); }
# chantier <dossier> : prépare un dossier à livrer dans un espace réservé à root, et s'y place
chantier() { DEST=$1; TMPD=/var/lib/lab/chantier/$(basename "$1"); rm -rf "$TMPD"; mkdir -p "$TMPD"; cd "$TMPD"; }
# nouveau_depot <dossier> : idem, avec un dépôt Git vide
nouveau_depot() { chantier "$1"; git init -q -b main .; }
# livre : remplace le dossier de l'étudiant par celui du chantier (pas de piège par lien symbolique)
livre() { cd /; chown -R etudiant:etudiant "$TMPD"; rm -rf "$DEST"; mv -T "$TMPD" "$DEST"; }
# Échanges avec le dépôt partagé : les programmes Git qui y lisent ou y écrivent tournent en tant qu'etudiant
AS_ETU="runuser -u etudiant -- env HOME=$H"
# Phrase d'accroche de la page d'accueil (G3.2), tirée au sort à la création du dépôt partagé : avec ses deux
# fautes, et corrigée
ACC_FAUX=("Tout le matériel de Randonée, livré chez vous en 48 h." "Tout l'équipemment de Montagne, livré chez vous en 48 h."
  "Tout le matériel de Bivouac, livrée chez vous en 48 h." "Tout le matériel d'Escalade, livrer chez vous en 48 h.")
ACC_BON=("Tout le matériel de randonnée, livré chez vous en 48 h." "Tout l'équipement de montagne, livré chez vous en 48 h."
  "Tout le matériel de bivouac, livré chez vous en 48 h." "Tout le matériel d'escalade, livré chez vous en 48 h.")
# Dépôt partagé de l'équipe (créé une seule fois : le travail poussé par l'étudiant est conservé)
depot_equipe() {
  [ -e $R ] && return 0
  local v=${LAB_VARIANTE_G3_2:-$((RANDOM % 4))}
  nouveau_depot /var/lib/lab/equipe/init  # (préparé dans le chantier)
  printf '# Boutique Cimes & Sentiers\n\nSite de la boutique en ligne de matériel de randonnée.\n' > README.md
  commit thomas 900 "Premier commit : README"
  mkdir -p css
  cat > index.html <<EOF
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Cimes & Sentiers</title><link rel="stylesheet" href="css/style.css"></head>
<body>
  <h1>Cimes & Sentiers</h1>
  <p>${ACC_FAUX[v]}</p>
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
# pousse <branche ou étiquette> : publie sur le dépôt partagé
pousse() { git push -q --receive-pack="$AS_ETU git-receive-pack" origin "$1"; }
# trouve <message> : identifiant du commit (toutes branches) du dépôt partagé qui porte ce message ; le plus
# ancien, pour ne pas prendre une copie (rebase, cherry-pick) faite ensuite par l'étudiant
trouve() { $AS_ETU git --git-dir=$R log --all --format=%H --grep="^$1\$" | tail -n 1; }
# poste <dossier> : clone du dépôt partagé dans le chantier (le poste d'un collègue)
poste() {
  depot_equipe; chantier "$1"
  git clone -q --no-local --upload-pack="$AS_ETU git-upload-pack" "$R" .
  git config --unset remote.origin.uploadpack || true
}
# depot_nu <nom> : (re)crée un dépôt nu vide /srv/git/<nom>.git appartenant à l'étudiant
depot_nu() {
  local t=/var/lib/lab/chantier/$1.git
  rm -rf "$t"; git init -q --bare -b main "$t"; chown -R etudiant:etudiant "$t"
  rm -rf "/srv/git/$1.git"; mv -T "$t" "/srv/git/$1.git"
}
# publie_nu <nom> : (re)crée /srv/git/<nom>.git à partir du dépôt du chantier, qui devient son clone (origin)
publie_nu() {
  local t=/var/lib/lab/chantier/$1.git
  rm -rf "$t"; git clone -q --bare --no-local "$TMPD" "$t"; git --git-dir="$t" config --unset remote.origin.url || true
  chown -R etudiant:etudiant "$t"; rm -rf "/srv/git/$1.git"; mv -T "$t" "/srv/git/$1.git"
  git remote add origin "/srv/git/$1.git"; git update-ref refs/remotes/origin/main HEAD
  git config branch.main.remote origin; git config branch.main.merge refs/heads/main
}
# jeton : chaîne aléatoire impossible à deviner
jeton() { head -c 9 /dev/urandom | od -An -tx1 | tr -d ' \n'; }
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
# nu <nom> … : git dans le dépôt nu /srv/git/<nom>.git
nu() { etu_git --git-dir="/srv/git/$1.git" "${@:2}"; }
# hashok <fichier> <hash> : le premier mot du fichier est ce hash, éventuellement abrégé (7 caractères au moins) ;
# une ligne de git log --oneline (« 3f9c2a1 Message ») est donc acceptée
hashok() { local a; a=$(awk 'NF { print $1; exit }' "$1" 2>/dev/null | tr 'A-F' 'a-f'); [ ${#a} -ge 7 ] && [ "${2#"$a"}" != "$2" ]; }
propre() { [ -z "$(g "$1" status --porcelain)" ]; }
# origine <dépôt> <chemin> : le distant origin désigne ce dépôt (file://, barre finale et suffixe .git tolérés)
origine() { local u; u=$(g "$1" remote get-url origin) || return 1; u=${u#file://}; u=${u%/}; [ "${u%.git}" = "${2%.git}" ]; }
# marqueurs <dépôt> <commit> : vrai s'il reste des marqueurs de conflit dans ce commit
marqueurs() { g "$1" grep -qE '^(<<<<<<<|=======|>>>>>>>)' "$2" --; }
'''

INTRO = """<div class="scenario"><h3>Travailler en équipe avec Git</h3><p>L'équipe web de Cimes &amp; Sentiers s'agrandit, et les « <code>index-final-v2-OK.html</code> » échangés par clé USB, c'est fini. Nadia, lead développeuse, vous confie la mise en place de <strong>Git</strong> : versionner les procédures, retrouver qui a cassé quoi dans les archives de Marc, travailler sur le dépôt partagé de l'équipe, gérer branches et conflits, réparer les bêtises de Julien et protéger les secrets de l'entreprise.</p><p>Le dépôt partagé de l'équipe est sur ce serveur : <code>/srv/git/boutique.git</code>. Vos collègues y publient leurs commits pendant que vous travaillez. Tout se passe dans le terminal ; l'éditeur par défaut est <code>nano</code> (<kbd>Ctrl</kbd>+<kbd>O</kbd> pour enregistrer, <kbd>Ctrl</kbd>+<kbd>X</kbd> pour quitter).</p><p>Les descriptions disent <strong>ce qu'il faut obtenir</strong>, pas comment : à vous de lire l'état du dépôt (<code>git status</code>, <code>git log</code>, <code>git diff</code>) pour choisir la bonne commande. Chaque indice coûte un point.</p></div>"""

STEPS = {
    # ─────────────────────────────────────────────────────────────────────
    1: {
        "title": "Jour 1 — Premiers pas avec Git",
        "description": "Identité, premier dépôt, premiers commits. Compétences : git config, init, status, diff, add (y compris partiel), commit, restore, .gitignore.",
        "lesson": INTRO + """<h3>Pourquoi Git ?</h3><p>Git enregistre des <strong>instantanés</strong> (des <em>commits</em>) de votre projet. Chaque commit a un auteur, une date, un message et un identifiant unique (le <em>hash</em>, par exemple <code>3f9c2a1</code>). On peut revenir à n'importe quel instantané, comparer, travailler à plusieurs.</p><h3>Se présenter (une fois par machine)</h3><p>Les réglages de Git se lisent et s'écrivent avec <code>git config</code>. Avec <code>--global</code>, ils valent pour tous vos dépôts (fichier <code>~/.gitconfig</code>) :</p><pre>git config --global &lt;clé&gt; "&lt;valeur&gt;"   # écrire un réglage<br>git config --global --get &lt;clé&gt;         # le relire<br>git config --global --list              # tout afficher</pre><ul><li><code>user.name</code> : votre nom, tel qu'il apparaîtra dans l'historique (« Prénom Nom ») ;</li><li><code>user.email</code> : votre adresse ;</li><li><code>init.defaultBranch</code> : le nom de la branche créée par <code>git init</code>. Sans ce réglage, Git 2.39 crée <code>master</code> (et affiche un long conseil).</li></ul><div class="tip">Chaque commit porte ce nom et cette adresse : configurez-les <strong>avant</strong> de commiter.</div><h3>Les trois zones</h3><ul><li>le <strong>répertoire de travail</strong> : vos fichiers, tels que vous les modifiez ;</li><li>l'<strong>index</strong> (<em>staging area</em>) : ce qui partira dans le prochain commit ;</li><li>le <strong>dépôt</strong> (dossier caché <code>.git</code>) : l'historique des commits.</li></ul><pre>git init                  # transforme le dossier courant en dépôt<br>git status                # que s'est-il passé depuis le dernier commit ?<br>git add fichier           # ajoute une modification à l'index<br>git add .                 # ajoute TOUT le dossier (attention à ce qui traîne !)<br>git commit -m "Message"   # enregistre l'index dans un commit<br>git log --oneline         # historique, une ligne par commit</pre><h3>Regarder avant d'indexer</h3><pre>git diff                  # répertoire de travail ↔ index : ce qui n'est pas encore indexé<br>git diff --staged         # index ↔ dernier commit : ce qui partira au prochain commit<br>git diff HEAD             # tout ce qui a changé depuis le dernier commit</pre><p>Les lignes qui commencent par <code>-</code> sont retirées, celles qui commencent par <code>+</code> sont ajoutées. Un bon réflexe : <code>git status</code> puis <code>git diff</code> avant chaque <code>git add</code>.</p><h3>Défaire avant de commiter</h3><pre>git restore fichier            # jette les modifications non indexées (retour à la version indexée)<br>git restore --staged fichier   # retire le fichier de l'index, sans toucher à vos modifications</pre><div class="tip"><code>git restore fichier</code> est définitif : les modifications jetées ne sont enregistrées nulle part.</div><h3>Indexer une partie d'un fichier</h3><p>Un fichier contient deux modifications sans rapport ? <code>git add -p fichier</code> (<em>patch</em>) présente chaque morceau (<em>hunk</em>) et demande s'il faut l'indexer : <kbd>y</kbd> oui, <kbd>n</kbd> non, <kbd>s</kbd> découper le morceau, <kbd>q</kbd> quitter, <kbd>?</kbd> aide. Vérifiez ensuite avec <code>git diff --staged</code> (ce qui sera commité) et <code>git diff</code> (ce qui restera).</p><h3>Ignorer des fichiers</h3><p>Un fichier <code>.gitignore</code> (versionné lui aussi) liste les fichiers que Git doit ignorer : brouillons, mots de passe, fichiers générés…</p><pre>notes.txt<br>*.log<br>node_modules/</pre><p>Un fichier <strong>déjà suivi</strong> par Git n'est pas concerné par <code>.gitignore</code> : il faut d'abord le retirer de l'index, sans le supprimer du disque :</p><pre>git rm --cached fichier</pre><p><code>git check-ignore -v fichier</code> dit quelle règle (fichier et ligne) ignore un fichier. Les règles peuvent aussi venir de votre configuration personnelle, mais seules celles du <code>.gitignore</code> commité valent pour toute l'équipe.</p><div class="tip">Pour renommer la branche courante : <code>git branch -m nouveau-nom</code>.</div>""",
        "setup": r'''
chantier $H/procedures
printf '# Sauvegardes\n\n1. Vérifier chaque lundi le rapport de sauvegarde.\n2. Tester une restauration par mois.\n' > sauvegarde.md
printf "# Comptes\n\nTout nouveau salarié reçoit un compte le jour de son arrivée.\n" > comptes.md
printf "# Imprimantes\n\nL'imprimante du 2e étage se relance en l'éteignant 30 secondes.\n" > imprimantes.md
printf 'Notes perso, à ne pas partager : penser à demander une augmentation.\n' > brouillon-perso.txt
livre
# Inventaire de Léa : une modification à commiter, un essai de Julien à jeter
nouveau_depot $H/inventaire
printf 'article;quantite\nbatons;12\nsacs;8\ntentes;5\nrechauds;9\n' > stock.csv
printf '# Inventaire\n\nInventaire mensuel de la réserve du magasin.\n' > README.md
printf 'fournisseur;delai\nAltiSport;5 jours\nTrekPro;8 jours\n' > fournisseurs.csv
printf '# Rayons\n\n- Rayon A : sacs et bâtons\n- Rayon B : tentes et réchauds\n' > rayons.md
printf 'date;article;quantite\n2024-09-02;sacs;10\n' > commandes.csv
commit lea 48 "Inventaire de septembre"
emit INV_BASE "$(git rev-parse HEAD)"
Q=$((RANDOM % 80 + 20)); T=ESSAI-$RANDOM$RANDOM
sed -i "s/^sacs;8$/sacs;$Q/" stock.csv
# L'essai de Julien : dans un fichier suivi tiré au sort (variante)
v=${LAB_VARIANTE_G1_4:-$((RANDOM % 4))}
case $v in
  0) printf '\n%s : essai de Julien, à ne pas garder\n' "$T" >> README.md ;;
  1) printf 'EssaiJulien;%s\n' "$T" >> fournisseurs.csv ;;
  2) printf -- '- Rayon C : %s (essai de Julien, à ne pas garder)\n' "$T" >> rayons.md ;;
  *) printf '2024-10-01;%s;0\n' "$T" >> commandes.csv ;;
esac
emit INV_Q "$Q"
emit INV_TOK "$T"
livre
# Boutique de Thomas : une correction et une ligne de debug dans le même fichier
nouveau_depot $H/boutique-js
mkdir -p js
# Variante : ordre des fonctions et place de la ligne de debug, donc ordre des morceaux de git add -p (et
# parfois un seul morceau, à découper)
v=${LAB_VARIANTE_G1_5:-$((RANDOM % 4))}
fonction() {
  case $1 in
    P) printf 'function prixAffiche(prix) {\n  return prix.toFixed(0) + " €";\n}\n' ;;
    N) printf 'function nomProduit(p) {\n  return p.marque + " " + p.modele;\n}\n' ;;
    B) printf 'function badgeStock(p) {\n  if (p.stock === 0) return "Rupture";\n  if (p.stock < 5) return "Plus que " + p.stock;\n  return "En stock";\n}\n' ;;
    L) printf 'function lienProduit(p) {\n  return "/produits/" + p.id;\n}\n' ;;
    A) printf 'function afficherPanier(panier) {\n  const lignes = panier.map(l => nomProduit(l.produit) + " : " + prixAffiche(l.total));\n  return lignes.join(", ");\n}\n' ;;
  esac
}
case $v in
  0) ordre="P N B L A"; apres="const lignes"; vue=lignes ;;
  1) ordre="N B L A P"; apres="function nomProduit"; vue=p ;;
  2) ordre="P N B L A"; apres="function nomProduit"; vue=p ;;
  *) ordre="N P B L A"; apres="function nomProduit"; vue=p ;;
esac
{ echo "// Fonctions d'affichage de la boutique"; for f in $ordre; do echo; fonction $f; done; } > js/app.js
commit thomas 30 "Fonctions d'affichage"
emit BJ_BASE "$(git rev-parse HEAD)"
T=$RANDOM$RANDOM
sed -i 's/prix.toFixed(0)/prix.toFixed(2)/' js/app.js
awk -v t="$T" -v a="$apres" -v x="$vue" '{ print } index($0, a) { print "  console.log(\"DEBUG-" t "\", " x ");" }' js/app.js > js/app.tmp
mv js/app.tmp js/app.js
emit BJ_TOK "$T"
livre
''',
        "exercises": [
            {"id": "G1.1", "points": 2, "title": "Se présenter à Git",
             "ticket": {"from": "sophie", "body": "Bienvenue dans l'équipe ! Avant toute chose, configure Git sur ce serveur : ton nom (« Prénom Nom ») et ton adresse professionnelle en <code>prenom.nom@cimes-sentiers.fr</code>. Chez nous, la branche principale s'appelle <strong>main</strong> : fais en sorte que tes nouveaux dépôts l'utilisent."},
             "desc": "Votre identité Git vaut pour tous vos dépôts : un nom « Prénom Nom », une adresse en <code>@cimes-sentiers.fr</code>, et les dépôts que vous créerez démarreront sur la branche <code>main</code>.",
             "hints": ["Ces réglages doivent valoir pour tous vos dépôts : le cours présente l'option de <code>git config</code> qui les enregistre dans votre dossier personnel, et les trois clés concernées.", "<code>git config --global user.name \"Prénom Nom\"</code>, de même pour <code>user.email</code> et <code>init.defaultBranch</code> ; vérifiez avec <code>git config --global --list</code>."],
             "checks": [
                 ('n=$(gget user.name); [ -n "$n" ] && [ "$n" != etudiant ]', "Votre nom n'est pas configuré pour tous vos dépôts (git config --global)."),
                 ('n=$(gget user.name); [[ "$n" == *[![:space:]]" "*[![:space:]]* ]]', "Votre nom doit être de la forme « Prénom Nom » (deux mots au moins)."),
                 ('gget user.email | grep -qE "^[A-Za-z0-9._-]+@cimes-sentiers\\.fr$"', "Votre adresse doit être de la forme prenom.nom@cimes-sentiers.fr."),
                 ('[ "$(gget init.defaultBranch)" = main ]', "Les nouveaux dépôts ne démarrent pas sur la branche main (réglage init.defaultBranch)."),
             ]},
            {"id": "G1.2", "points": 3, "title": "Versionner les procédures",
             "ticket": {"from": "lea", "body": "Mes procédures d'exploitation sont dans <code>~/procedures</code>, et je ne sais jamais qui a changé quoi. Mets ce dossier sous Git et fais un premier commit avec les trois procédures (<code>.md</code>)."},
             "desc": "<code>~/procedures</code> est un dépôt Git sur la branche <code>main</code>, dont un commit à votre nom contient <code>sauvegarde.md</code>, <code>comptes.md</code> et <code>imprimantes.md</code>.",
             "hints": ["Un dossier ordinaire devient un dépôt en une commande ; ensuite, on choisit ce qui part dans l'instantané, puis on l'enregistre. <code>git status</code> vous guide à chaque étape.", "<code>git init</code>, <code>git add</code> des trois fichiers <code>.md</code>, <code>git commit -m \"...\"</code>. Commit fait avant de configurer votre identité ? <code>git commit --amend --reset-author --no-edit</code> (vu au jour 7). Branche <code>master</code> ? <code>git branch -m main</code>."],
             "checks": [
                 ('[ -d $H/procedures/.git ]', "~/procedures n'est pas un dépôt Git."),
                 ('g $H/procedures rev-parse -q --verify HEAD', "Le dépôt ne contient encore aucun commit."),
                 ('[ "$(g $H/procedures branch --show-current)" = main ]', "La branche doit s'appeler main (git branch -m main)."),
                 ('for f in sauvegarde.md comptes.md imprimantes.md; do g $H/procedures cat-file -e HEAD:$f || exit 1; done', "Les trois procédures (.md) doivent être dans le dernier commit."),
                 ('[ "$(g $H/procedures log -1 --format=%ae)" = "$(gget user.email)" ]', "Le commit n'est pas à votre nom : configurez votre identité, puis git commit --amend --reset-author --no-edit."),
             ]},
            {"id": "G1.3", "points": 3, "title": "Ce qui ne regarde que moi",
             "ticket": {"from": "lea", "body": "Oups, j'avais oublié mon <code>brouillon-perso.txt</code> dans ce dossier. Il ne doit <strong>pas</strong> être dans le dépôt, ni maintenant ni plus tard (même si quelqu'un fait un jour <code>git add .</code>), mais je veux garder le fichier sur le disque. S'il est déjà parti dans un commit, tant pis pour cette fois : ce n'est qu'un brouillon (on verra au jour 9 ce qu'on fait quand c'est un vrai secret)."},
             "desc": "<code>brouillon-perso.txt</code> existe toujours sur le disque, n'est pas dans le dernier commit et est ignoré grâce à une règle du <code>.gitignore</code> du dépôt, commité ; <code>git status</code> n'affiche rien.",
             "hints": ["La règle doit voyager avec le dépôt (donc être dans un fichier commité)… et une règle d'ignorance n'a aucun effet sur un fichier que Git suit déjà.", "Un <code>.gitignore</code> contenant <code>brouillon-perso.txt</code>, ajouté et commité ; si le brouillon a déjà été commité : <code>git rm --cached brouillon-perso.txt</code>, puis un commit."],
             "checks": [
                 ('[ -f $H/procedures/brouillon-perso.txt ]', "brouillon-perso.txt a disparu du disque : il fallait seulement le retirer du dépôt (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('! g $H/procedures cat-file -e HEAD:brouillon-perso.txt 2>/dev/null', "brouillon-perso.txt est encore dans le dernier commit : .gitignore ne concerne pas un fichier déjà suivi."),
                 ('g $H/procedures cat-file -e HEAD:.gitignore', "Le fichier .gitignore doit être commité."),
                 ('g $H/procedures check-ignore -v brouillon-perso.txt | grep -q "^\\.gitignore:"', "brouillon-perso.txt n'est pas ignoré par le .gitignore du dépôt (une règle dans votre configuration personnelle ne suffit pas : elle ne voyage pas avec le dépôt)."),
                 ('propre $H/procedures', "git status signale encore des fichiers modifiés ou non suivis : commitez-les."),
             ]},
            {"id": "G1.4", "points": 4, "title": "Le bon fichier au bon moment",
             "ticket": {"from": "lea", "body": "J'ai mis à jour le stock des sacs dans <code>~/inventaire</code>. Julien a aussi fait un essai dans ce dossier, je ne sais plus où. Commite <strong>uniquement</strong> mon inventaire, avec le message « Inventaire d'octobre », et jette l'essai de Julien : il ne doit rester nulle part."},
             "desc": "Dans <code>~/inventaire</code>, un seul nouveau commit « Inventaire d'octobre », à votre nom, avec le nouveau stock des sacs et sans l'essai de Julien ; l'essai a disparu du répertoire de travail et <code>git status</code> n'affiche plus rien.",
             "hints": ["Avant d'indexer quoi que ce soit, comparez le répertoire de travail au dernier commit : quels fichiers ont changé, et quelles lignes ?", "<code>git status</code> et <code>git diff</code> montrent dans quel fichier est l'essai ; <code>git add stock.csv</code>, <code>git commit -m \"Inventaire d'octobre\"</code>, puis <code>git restore &lt;fichier de l'essai&gt;</code> pour revenir à la version du dernier commit."],
             "checks": [
                 ('g $H/inventaire show HEAD:stock.csv | grep -qx "sacs;$LAB_INV_Q"', "Le dernier commit de ~/inventaire ne contient pas le nouveau stock des sacs de Léa."),
                 ('! g $H/inventaire grep -qF "$LAB_INV_TOK" HEAD --', "L'essai de Julien est parti dans le commit : seul l'inventaire devait être commité (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('[ "$(g $H/inventaire rev-parse HEAD^)" = "$LAB_INV_BASE" ]', "Il faut exactement un nouveau commit après « Inventaire de septembre »."),
                 ("[ \"$(g $H/inventaire log -1 --format=%s)\" = \"Inventaire d'octobre\" ]", "Le message du commit doit être « Inventaire d'octobre »."),
                 ('[ "$(g $H/inventaire log -1 --format=%ae)" = "$(gget user.email)" ]', "Le commit n'est pas à votre nom."),
                 ('propre $H/inventaire', "L'essai de Julien traîne encore dans le répertoire de travail (git status) : il fallait le jeter, pas seulement éviter de le commiter."),
             ]},
            {"id": "G1.5", "points": 5, "title": "Juste la correction",
             "ticket": {"from": "thomas", "body": "Dans <code>~/boutique-js</code>, <code>js/app.js</code> contient ma correction de l'affichage des prix (les centimes) <strong>et</strong> une ligne de debug que je garde encore un peu pour mes essais. Commite seulement la correction (message libre) ; la ligne de debug doit rester dans mon fichier, sans être commitée."},
             "desc": "Un seul nouveau commit dans <code>~/boutique-js</code>, à votre nom : il contient la correction des centimes mais pas la ligne de debug ; celle-ci est toujours dans <code>js/app.js</code>, non indexée, et rien d'autre n'est modifié.",
             "hints": ["Les deux modifications sont dans le même fichier : Git sait n'indexer qu'une partie d'un fichier, morceau par morceau, et même découper un morceau qui en contient deux. Contrôlez ensuite ce qui est indexé et ce qui ne l'est pas.", "<code>git add -p js/app.js</code> : <kbd>y</kbd> pour le morceau des centimes, <kbd>n</kbd> pour celui du debug, dans l'ordre où Git les présente (<kbd>s</kbd> d'abord si un seul morceau contient les deux) ; <code>git diff --staged</code> pour contrôler, puis <code>git commit</code>."],
             "checks": [
                 ('g $H/boutique-js show HEAD:js/app.js | grep -qF "toFixed(2)"', "Le dernier commit ne contient pas la correction des centimes."),
                 ('! g $H/boutique-js show HEAD:js/app.js | grep -qF "DEBUG-$LAB_BJ_TOK"', "La ligne de debug est partie dans le commit : seule la correction devait l'être (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('[ "$(g $H/boutique-js rev-parse HEAD^)" = "$LAB_BJ_BASE" ]', "Il faut exactement un nouveau commit après celui de Thomas."),
                 ('[ "$(g $H/boutique-js log -1 --format=%ae)" = "$(gget user.email)" ]', "Le commit n'est pas à votre nom."),
                 ('g $H/boutique-js diff --cached --quiet', "Des modifications sont encore indexées sans être commitées : la ligne de debug ne doit pas être indexée."),
                 (r'''[ "$(g $H/boutique-js diff --numstat)" = "$(printf '1\t0\tjs/app.js')" ] && g $H/boutique-js diff | grep -qF "DEBUG-$LAB_BJ_TOK"''', "La ligne de debug doit rester dans js/app.js (non commitée), et rien d'autre ne doit être modifié."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Jour 2 — Enquête dans les archives de Marc",
        "description": "Explorer et corriger l'historique sans le réécrire. Compétences : log, show, diff, log -S, blame, restore, revert (y compris avec conflit).",
        "lesson": """<h3>Lire l'historique</h3><pre>git log                      # tous les commits, du plus récent au plus ancien<br>git log --oneline --graph    # compact, avec les branches<br>git log -p fichier           # l'historique d'un fichier, avec les modifications<br>git log --author=Marc<br>git log -S "texte"           # la « pioche » : commits qui changent le nombre d'occurrences de ce texte<br>git log -G "regex"           # commits dont une ligne ajoutée ou retirée correspond à l'expression<br>git log --diff-filter=D --name-only   # commits qui ont supprimé des fichiers<br>git log ... -- chemin        # (à la fin) limiter la recherche à un fichier ou un dossier</pre><div class="tip"><code>-S</code> ne voit pas un texte simplement déplacé (le nombre d'occurrences ne change pas) ; <code>-G</code> le voit. Et un texte peut apparaître légitimement à plusieurs endroits : regardez <em>quel fichier</em> chaque commit a modifié.</div><h3>Examiner un commit</h3><pre>git show 3f9c2a1             # message et modifications d'un commit<br>git show 3f9c2a1:js/app.js   # un fichier tel qu'il était dans ce commit<br>git diff a1b2c3d 3f9c2a1     # différences entre deux commits</pre><p><code>HEAD</code> désigne le commit courant ; <code>HEAD~1</code> (ou <code>HEAD^</code>) son parent, <code>3f9c2a1^</code> le parent de <code>3f9c2a1</code>.</p><h3>Qui a écrit cette ligne ?</h3><pre>git blame fichier            # pour chaque ligne : le dernier commit qui l'a modifiée, son auteur, sa date<br>git blame -L 10,20 fichier   # seulement les lignes 10 à 20<br>git log -L 10,20:fichier     # toute l'histoire de ces lignes, commit par commit</pre><p><code>blame</code> montre le <strong>dernier</strong> commit qui a touché la ligne… y compris un commit qui n'a changé que l'indentation. Lisez <code>git help blame</code> : des options permettent d'ignorer ce genre de modification.</p><h3>Récupérer une ancienne version d'un fichier</h3><pre>git restore --source=3f9c2a1 chemin/fichier   # (ancienne syntaxe : git checkout 3f9c2a1 -- chemin/fichier)</pre><p>Le fichier revient dans le répertoire de travail : il reste à l'ajouter et à le commiter. Attention : <code>git checkout 3f9c2a1</code> <strong>sans</strong> nom de fichier déplace tout le dépôt sur ce commit (« tête détachée ») : ce n'est pas une restauration.</p><h3>Annuler un commit… sans réécrire l'histoire</h3><pre>git revert 3f9c2a1</pre><p><code>revert</code> crée un <strong>nouveau commit</strong> qui applique l'inverse du commit visé, avec le message « Revert … » et la mention « This reverts commit … ». L'historique reste intact : c'est la seule façon d'annuler un commit déjà partagé sans réécrire l'histoire commune.</p><div class="tip"><code>git revert</code> ouvre l'éditeur pour le message : enregistrez et quittez (ou ajoutez <code>--no-edit</code>).</div><h3>Quand l'annulation bute sur la suite</h3><p>Annuler un vieux commit, c'est appliquer son inverse sur la version <em>actuelle</em>. Si les mêmes lignes ont été modifiées depuis, Git ne peut pas décider seul : le revert s'arrête sur un <strong>conflit</strong>, avec des marqueurs dans le fichier (voir le jour 6).</p><pre>git status                 # fichiers en conflit, et la marche à suivre<br># éditez, gardez le bon contenu, supprimez les marqueurs &lt;&lt;&lt;&lt;&lt;&lt;&lt; ======= &gt;&gt;&gt;&gt;&gt;&gt;&gt;<br>git add fichier<br>git revert --continue      # termine l'annulation (ou : git revert --abort pour tout abandonner)</pre>""",
        "setup": r'''
S=$H/archives-site
# Variantes tirées au sort : G2.1 (et G2.3) le commit qui casse la TVA, G2.4 le commit qui fixe les frais
# standard actuels, G2.5 les seuils et commentaires de la livraison offerte
v1=${LAB_VARIANTE_G2_1:-$((RANDOM % 4))}
v4=${LAB_VARIANTE_G2_4:-$((RANDOM % 4))}
v5=${LAB_VARIANTE_G2_5:-$((RANDOM % 4))}
case $v1 in
  0) TVA_H=1850; TVA_M="Optimisation du panier" ;;
  1) TVA_H=1780; TVA_M="Simplification du calcul" ;;
  2) TVA_H=1920; TVA_M="Nettoyage du panier" ;;
  *) TVA_H=1680; TVA_M="Refactorisation du panier" ;;
esac
case $v4 in
  0) PORT_H=1450; PORT_M="Mise à jour des tarifs d'expédition" ;;
  1) PORT_H=1320; PORT_M="Nouveau contrat avec le transporteur" ;;
  2) PORT_H=1520; PORT_M="Révision des frais de port" ;;
  *) PORT_H=1280; PORT_M="Tarifs de livraison de la rentrée" ;;
esac
case $v5 in
  0) SEUIL_A=60; SEUIL_B=100; COM_A="livraison offerte dès ce montant"; COM_B="livraison offerte à partir de ce montant (TTC)" ;;
  1) SEUIL_A=50; SEUIL_B=80; COM_A="frais de port offerts à partir de ce montant"; COM_B="frais de port offerts à partir de ce montant, hors promotions" ;;
  2) SEUIL_A=75; SEUIL_B=120; COM_A="seuil de gratuité"; COM_B="seuil de gratuité de la livraison, en euros TTC" ;;
  *) SEUIL_A=45; SEUIL_B=90; COM_A="livraison gratuite au-delà"; COM_B="livraison gratuite au-delà de ce montant (France métropolitaine)" ;;
esac
tva() { sed -i 's/const TVA = 0.20;/const TVA = 0.055;/' js/panier.js; commit marc $TVA_H "$TVA_M"; emit TVA "$(git rev-parse HEAD)"; }
frais() {
  local f; f=$(shuf -n 1 -e 5.20 5.60 5.80 6.10 6.30 6.50 6.90)
  sed -i "s/standard: 5.40/standard: $f/" js/port.js
  commit "$(shuf -n 1 -e nadia sophie thomas)" $PORT_H "$PORT_M"
  emit PORT "$(git rev-parse HEAD)"
}
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
commit marc 1950 "Ajout des mentions légales"
if [ $TVA_H = 1920 ]; then tva; fi
printf 'h1 { color: #2d6a4f; }\n' > style.css
commit marc 1900 "Un peu de couleur"
if [ $TVA_H = 1850 ]; then tva; fi
# Leurre : 0.055 est aussi (légitimement) le taux des livres
printf '// Cartes et topoguides : taux réduit de TVA des livres\nconst TVA_LIVRES = 0.055;\n' > js/livres.js
commit thomas 1800 "Rayon librairie : cartes et topoguides"
emit LIVRES "$(git rev-parse HEAD)"
if [ $TVA_H = 1780 ]; then tva; fi
printf '\nfunction arrondi(x) {\n  return Math.round(x * 100) / 100;\n}\n' >> js/panier.js
commit marc 1750 "Petites retouches du panier"
printf '// Frais de port (euros)\nconst FRAIS = {\n\tstandard: 4.90,\n\tmontagne: 7.90,\n};\n' > js/port.js
commit thomas 1700 "Frais de port"
if [ $TVA_H = 1680 ]; then tva; fi
printf '// Livraison\nconst SEUIL_LIVRAISON = %s; // %s\n' "$SEUIL_A" "$COM_A" > js/livraison.js
printf '<p>Livraison offerte dès %s euros</p>\n' "$SEUIL_A" >> index.html
commit marc 1650 "Livraison offerte"
emit AVANT "$(git rev-parse HEAD)"
git rm -q data/fournisseurs.csv
commit marc 1600 "Ménage"
sed -i 's/standard: 4.90/standard: 5.40/' js/port.js
commit lea 1550 "Frais de port 2024"
emit PORT0 "$(git rev-parse HEAD)"
if [ $PORT_H = 1520 ]; then frais; fi
printf 'p { line-height: 1.5; }\n' >> style.css
commit marc 1500 "Interlignage"
if [ $PORT_H = 1450 ]; then frais; fi
sed -i 's/montagne: 7.90/montagne: 8.90/' js/port.js
commit lea 1400 "Frais de port en montagne"
sed -i "s/SEUIL_LIVRAISON = $SEUIL_A;/SEUIL_LIVRAISON = $SEUIL_B;/" js/livraison.js
commit marc 1350 "Seuil de livraison relevé"
emit SEUIL "$(git rev-parse HEAD)"
if [ $PORT_H = 1320 ]; then frais; fi
printf '<p>Contact : contact@cimes-sentiers.fr</p>\n' >> mentions.html
commit marc 1300 "Adresse de contact"
if [ $PORT_H = 1280 ]; then frais; fi
sed -i "s|// $COM_A\$|// $COM_B|" js/livraison.js
commit marc 1250 "Précision sur le seuil"
emit SEUIL2 "$(git rev-parse HEAD)"
emit SEUIL_LIGNE "const SEUIL_LIVRAISON = $SEUIL_A; // $COM_B"
sed -i 's/^\t/  /' js/port.js
commit julien 1200 "Mise en forme du code"
emit FIN "$(git rev-parse HEAD)"
livre
''',
        "exercises": [
            {"id": "G2.1", "points": 4, "title": "Qui a cassé la TVA ?", "manual": True,
             "ticket": {"from": "diallo", "body": "Les factures du site appliquent une TVA de 5,5 % au lieu de 20 % ! Le site vient des archives de Marc (<code>~/archives-site</code>). Je dois savoir <strong>quel commit</strong> a introduit ce taux dans le calcul du panier, pour dater le problème."},
             "desc": "L'identifiant (hash, abrégé ou complet) du commit qui a introduit le taux de 5,5 % dans le calcul du panier, seul sur la première ligne de <code>~/commit-tva.txt</code>.",
             "hints": ["Chercher le texte <code>0.055</code> dans les modifications, plutôt que de lire tous les commits… mais ce taux est parfaitement légal ailleurs dans le site : c'est le panier qui compte.", "<code>git log -S \"0.055\" --oneline -- js/panier.js</code>, puis <code>git show</code> pour confirmer."],
             "checks": [
                 ('[ -s $H/commit-tva.txt ]', "~/commit-tva.txt est vide ou absent."),
                 ('! hashok $H/commit-tva.txt "$LAB_LIVRES"', "Ce commit introduit bien 0.055… mais dans js/livres.js, où c'est le taux légal des livres. Cherchez celui qui l'a mis dans le calcul du panier."),
                 ('hashok $H/commit-tva.txt "$LAB_TVA"', "~/commit-tva.txt ne contient pas l'identifiant du commit qui a introduit le taux de 0.055 dans le panier (7 caractères au moins)."),
             ]},
            {"id": "G2.2", "points": 4, "title": "Le fichier des fournisseurs",
             "ticket": {"from": "diallo", "body": "Et pendant que tu y es : le fichier <code>data/fournisseurs.csv</code> a disparu des archives. Marc l'a supprimé à un moment, mais j'en ai besoin ! Remets-le dans le dépôt tel qu'il était, sans défaire le travail qui a suivi."},
             "desc": "<code>data/fournisseurs.csv</code> est de retour, avec son contenu d'avant la suppression, dans un nouveau commit de la branche <code>main</code> de <code>~/archives-site</code> ; tous les commits de Marc sont toujours là.",
             "hints": ["Retrouvez d'abord le commit qui a supprimé le fichier : le fichier existe encore dans l'état qui précède ce commit. On restaure <strong>un fichier</strong>, pas tout le dépôt.", "<code>git log --diff-filter=D --name-only</code>, puis <code>git restore --source=&lt;hash&gt;^ data/fournisseurs.csv</code>, <code>git add</code> et <code>git commit</code>."],
             "checks": [
                 ('[ "$(g $H/archives-site branch --show-current)" = main ]', "~/archives-site n'est pas sur la branche main (tête détachée ?) : git checkout &lt;commit&gt; sans nom de fichier déplace tout le dépôt. Revenez avec git switch main."),
                 ('g $H/archives-site merge-base --is-ancestor "$LAB_FIN" HEAD', "Des commits de Marc ont disparu de l'historique : il fallait restaurer un fichier, pas revenir en arrière (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('g $H/archives-site cat-file -e HEAD:data/fournisseurs.csv', "data/fournisseurs.csv n'est pas dans le dernier commit de ~/archives-site."),
                 ('[ "$(g $H/archives-site show HEAD:data/fournisseurs.csv)" = "$(g $H/archives-site show "$LAB_AVANT:data/fournisseurs.csv")" ]', "Le contenu de data/fournisseurs.csv n'est pas celui d'avant sa suppression."),
             ]},
            {"id": "G2.3", "points": 4, "title": "Annuler sans effacer",
             "ticket": {"from": "nadia", "body": "Maintenant qu'on a trouvé le commit fautif, annule-le. Attention : ces archives ont été partagées, alors <strong>on ne réécrit pas l'historique</strong>. Le commit de Marc doit rester visible, et son annulation aussi."},
             "desc": "Un nouveau commit de <code>~/archives-site</code> annule le commit de la TVA : <code>js/panier.js</code> revient à <code>TVA = 0.20</code>, et le commit de Marc comme son annulation restent visibles dans l'historique.",
             "hints": ["Git sait fabriquer lui-même le commit « inverse » d'un commit donné, avec un message qui dit ce qu'il annule.", "<code>git revert &lt;hash&gt;</code> (le hash trouvé pour Aminata)."],
             "checks": [
                 ('[ "$(g $H/archives-site branch --show-current)" = main ]', "~/archives-site n'est pas sur la branche main (git switch main)."),
                 ('g $H/archives-site merge-base --is-ancestor "$LAB_FIN" HEAD', "Des commits ont disparu de l'historique : il fallait annuler avec un nouveau commit (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('g $H/archives-site show HEAD:js/panier.js | grep -q "const TVA = 0.20;"', "Dans le dernier commit, js/panier.js n'a pas retrouvé TVA = 0.20."),
                 ('g $H/archives-site log --format=%B "$LAB_TVA..HEAD" | grep -qF "This reverts commit $LAB_TVA"', "Aucun commit n'annule celui de la TVA (« This reverts commit … ») : utilisez git revert sur ce commit-là, plutôt qu'une correction à la main."),
             ]},
            {"id": "G2.4", "points": 4, "title": "Qui a fixé les frais de port ?", "manual": True,
             "ticket": {"from": "diallo", "body": "Un client demande pourquoi nos frais de port standard ont augmenté. Retrouve dans <code>~/archives-site</code> le commit qui a fixé le montant <strong>actuel</strong> des frais standard (<code>js/port.js</code>) : j'irai voir son auteur. Mets son identifiant dans <code>~/commit-frais.txt</code>."},
             "desc": "L'identifiant du commit qui a donné aux frais de port standard leur valeur actuelle, seul sur la première ligne de <code>~/commit-frais.txt</code>.",
             "hints": ["Annoter chaque ligne avec le dernier commit qui l'a touchée est la bonne idée… mais un commit qui n'a changé que la mise en forme peut masquer le vrai auteur d'une ligne.", "<code>git blame -w js/port.js</code> (<code>-w</code> ignore les changements d'espaces), ou <code>git log -L '/standard/,+1:js/port.js'</code>."],
             "checks": [
                 ('[ -s $H/commit-frais.txt ]', "~/commit-frais.txt est vide ou absent."),
                 ('! hashok $H/commit-frais.txt "$LAB_FIN"', "C'est le commit de mise en forme de Julien : il n'a changé que des espaces. Qui a vraiment fixé le montant actuel ?"),
                 ('! hashok $H/commit-frais.txt "$LAB_PORT0"', "Ce commit a bien modifié les frais standard… mais ce n'est pas le montant actuel."),
                 ('hashok $H/commit-frais.txt "$LAB_PORT"', "~/commit-frais.txt ne contient pas l'identifiant du commit qui a fixé le montant actuel des frais standard (7 caractères au moins)."),
             ]},
            {"id": "G2.5", "points": 6, "title": "Annuler malgré la suite",
             "ticket": {"from": "nadia", "body": "Marc avait relevé le seuil de livraison gratuite (commit « Seuil de livraison relevé »), sans l'accord de la direction : on revient à l'ancien seuil. Annule ce commit proprement, comme pour la TVA. Attention, il a retouché la même ligne ensuite pour préciser le commentaire : cette précision-là, on la garde."},
             "desc": "Un nouveau commit de <code>~/archives-site</code> annule « Seuil de livraison relevé » : le seuil de <code>js/livraison.js</code> retrouve sa valeur d'avant ce commit, avec le commentaire précisé ensuite par Marc ; l'historique est intact et aucun marqueur de conflit ne subsiste.",
             "hints": ["Annuler un vieux commit, c'est appliquer son inverse sur la version actuelle : si la même ligne a changé depuis, Git s'arrête sur un conflit, comme pour une fusion. <code>git status</code> dit comment terminer.", "<code>git revert &lt;hash&gt;</code> ; dans <code>js/livraison.js</code>, gardez l'ancienne valeur <strong>et</strong> le nouveau commentaire sur une seule ligne, supprimez les marqueurs, puis <code>git add js/livraison.js</code> et <code>git revert --continue</code>."],
             "checks": [
                 ('[ ! -e $H/archives-site/.git/REVERT_HEAD ]', "Une annulation (revert) est encore en cours : résolvez le conflit, git add, puis git revert --continue."),
                 ('[ "$(g $H/archives-site branch --show-current)" = main ] && g $H/archives-site merge-base --is-ancestor "$LAB_FIN" HEAD', "L'historique de main a été réécrit ou vous n'êtes plus sur main : il fallait annuler par un nouveau commit (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('g $H/archives-site log --format=%B "$LAB_SEUIL..HEAD" | grep -qF "This reverts commit $LAB_SEUIL"', "Aucun commit n'annule « Seuil de livraison relevé » (« This reverts commit … ») : utilisez git revert sur ce commit."),
                 ('! marqueurs $H/archives-site HEAD', "Des marqueurs de conflit (<<<<<<<, =======, >>>>>>>) ont été commités."),
                 ('[ "$(g $H/archives-site show HEAD:js/livraison.js | grep SEUIL_LIVRAISON)" = "$LAB_SEUIL_LIGNE" ]', "js/livraison.js doit contenir une seule ligne de seuil : la valeur d'avant « Seuil de livraison relevé », avec le commentaire tel que Marc l'a précisé ensuite."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Jour 3 — Le dépôt de l'équipe",
        "description": "Récupérer le dépôt partagé, y publier, relier un dépôt local à son distant. Compétences : clone, remote, push, push -u.",
        "lesson": """<h3>Dépôt local, dépôt distant</h3><p>Chaque développeur a son <strong>propre dépôt complet</strong> (tout l'historique). L'équipe partage un dépôt <strong>distant</strong>, souvent sur GitHub ou GitLab ; ici il est sur le serveur, dans <code>/srv/git</code>. C'est un dépôt <em>nu</em> (<em>bare</em>) : il n'a que l'historique, pas de répertoire de travail.</p><pre>git clone &lt;url ou chemin&gt;                 # crée un dossier du nom du dépôt, dans le dossier courant<br>git clone https://github.com/org/projet   # même chose avec un dépôt en ligne<br>git remote -v                             # les distants connus ; le distant d'origine s'appelle « origin »</pre><h3>Publier ses commits</h3><pre>git add index.html<br>git commit -m "Correction d'une faute"<br>git push                                  # met à jour la branche main du dépôt origin avec vos commits<br>git log --oneline --graph --all           # origin/main : dernière position connue de main sur origin</pre><p><code>origin/main</code> n'est pas une branche sur laquelle on travaille : c'est une <strong>référence de suivi</strong>, la mémoire locale de l'état du distant, mise à jour à chaque échange (<code>push</code>, <code>fetch</code>, <code>pull</code>).</p><div class="tip">Rien ne part sur le dépôt de l'équipe tant que vous n'avez pas fait <code>git push</code>. Un commit local reste local.</div><h3>Relier un dépôt existant à un distant</h3><pre>git remote add origin &lt;url&gt;         # déclarer un distant<br>git remote set-url origin &lt;url&gt;     # corriger l'adresse d'un distant existant<br>git remote remove origin            # l'oublier<br>git push -u origin main             # publier main ; -u mémorise que main suit origin/main (upstream)<br>git branch -vv                      # quelle branche distante chaque branche locale suit</pre><p>Après un <code>push -u</code>, un simple <code>git push</code> ou <code>git pull</code> sait où aller. Sans lien de suivi, Git répond « has no upstream branch ».</p><h3>Remplacer du texte dans un fichier</h3><p>Avec <code>nano</code> (<kbd>Ctrl</kbd>+<kbd>\\</kbd> pour rechercher et remplacer) ou avec <code>sed -i 's/ancien/nouveau/' fichier</code>. Relisez ensuite <code>git diff</code> avant de commiter.</p>""",
        "setup": r'''
depot_equipe
ACCUEIL=$(trouve "Page d'accueil et feuille de style")
emit ACCUEIL "$ACCUEIL"
# Variante de la phrase d'accroche (G3.2) : retrouvée dans le dépôt partagé, tirée au sort à sa création
L=$($AS_ETU git --git-dir=$R show "$ACCUEIL:index.html" | sed -n 's|^  <p>\(.*\)</p>$|\1|p')
for i in 0 1 2 3; do
  if [ "$L" = "${ACC_FAUX[i]}" ]; then emit ACC_FAUX "${ACC_FAUX[i]}"; emit ACC_BON "${ACC_BON[i]}"; fi
done
# La vitrine de Julien : un dépôt local dont le distant est mal orthographié
depot_nu vitrine
nouveau_depot $H/vitrine
printf '<h1>Cimes & Sentiers : le magasin</h1>\n' > index.html
commit julien 30 "Page d'accueil de la vitrine"
printf '<p>12 rue des Alpes, Grenoble</p>\n' > adresse.html
commit julien 28 "Adresse du magasin"
printf '<p>Ouvert du mardi au samedi, de 9 h 30 à 19 h.</p>\n' > horaires.html
commit julien 26 "Horaires d'ouverture"
git remote add origin /srv/git/vitrin.git
emit VITRINE "$(git rev-parse HEAD)"
livre
''',
        "exercises": [
            {"id": "G3.1", "points": 2, "title": "Rejoindre l'équipe",
             "ticket": {"from": "nadia", "body": "Le code de la boutique est dans notre dépôt partagé <code>/srv/git/boutique.git</code>. Récupère-le dans <code>~/boutique</code>."},
             "desc": "<code>~/boutique</code> est une copie de travail du dépôt partagé, qui le connaît comme distant <code>origin</code>.",
             "hints": ["Il ne s'agit pas de créer un dépôt vide, mais de récupérer une copie complète d'un dépôt existant, depuis votre dossier personnel.", "<code>cd ~</code> puis <code>git clone /srv/git/boutique.git</code>."],
             "checks": [
                 ('[ -d $B/.git ]', "~/boutique n'est pas un dépôt Git (la copie doit être faite depuis votre dossier personnel)."),
                 ('origine $B /srv/git/boutique.git', "Le distant origin de ~/boutique doit être /srv/git/boutique.git."),
                 ('g $B cat-file -e HEAD:EQUIPE.md', "~/boutique ne contient pas le code de l'équipe."),
             ]},
            {"id": "G3.2", "points": 4, "title": "Première contribution",
             "ticket": {"from": "thomas", "body": "Honte à moi : la phrase d'accroche de la page d'accueil contient <strong>deux fautes</strong> depuis le premier jour. Tu peux les corriger et publier la correction ? Un commit à ton nom, sur <code>main</code>, et ne touche à rien d'autre."},
             "desc": "Sur la branche <code>main</code> du dépôt partagé, la phrase d'accroche d'<code>index.html</code> est correcte, le reste du fichier est inchangé, et la correction est un commit à votre nom.",
             "hints": ["Relisez la phrase mot à mot : une faute d'orthographe, et une autre qu'un correcteur ne verrait pas. Relisez <code>git diff</code> avant de commiter.", "Un mot mal écrit, et une majuscule qui n'a rien à faire au milieu de la phrase ; corrigez les deux, puis <code>git add</code>, <code>git commit</code> et <code>git push</code>."],
             "checks": [
                 ('! depot show main:index.html | grep -qxF "  <p>$LAB_ACC_FAUX</p>"', "La phrase d'accroche d'index.html n'a pas changé sur le dépôt partagé (commit, puis git push)."),
                 ('depot show main:index.html | grep -qxF "  <p>$LAB_ACC_BON</p>"', "La phrase d'accroche d'index.html n'est pas encore correcte sur le dépôt partagé : il reste une faute (relisez chaque mot, majuscules comprises), ou vous avez changé autre chose dans la phrase."),
                 ('[ "$(depot show "$LAB_ACCUEIL:index.html" | grep -v "^  <p>")" = "$(depot show main:index.html | grep -v "^  <p>")" ]', "Le reste d'index.html a changé : ne corrigez que la phrase d'accroche."),
                 ('[ "$(depot log -1 --format=%ae main -- index.html)" = "$(gget user.email)" ]', "La correction doit être un commit à votre nom."),
             ]},
            {"id": "G3.3", "points": 5, "title": "Le dépôt de Julien ne part pas",
             "ticket": {"from": "julien", "body": "J'ai créé le dépôt <code>~/vitrine</code> (la future vitrine du magasin) et Nadia m'a préparé un dépôt partagé vide, <code>/srv/git/vitrine.git</code>. Mais <code>git push</code> me répond « does not appear to be a git repository » ! Tu peux publier ma branche <code>main</code> là-bas ? Et que je puisse faire un simple <code>git push</code> la prochaine fois."},
             "desc": "Le distant <code>origin</code> de <code>~/vitrine</code> désigne le dépôt préparé par Nadia, dont la branche <code>main</code> est identique à celle de Julien ; la branche <code>main</code> locale suit <code>origin/main</code>.",
             "hints": ["Comparez le chemin cité dans le message d'erreur avec celui du dépôt préparé par Nadia : où Git croit-il que se trouve <code>origin</code> ? On corrige l'adresse plutôt que de créer un nouveau dépôt.", "<code>git remote -v</code>, puis <code>git remote set-url origin /srv/git/vitrine.git</code> et <code>git push -u origin main</code>."],
             "checks": [
                 ('origine $H/vitrine /srv/git/vitrine.git', "Le distant origin de ~/vitrine ne désigne pas le dépôt préparé par Nadia (/srv/git/vitrine.git) : comparez avec git remote -v."),
                 ('nu vitrine rev-parse -q --verify refs/heads/main', "Rien n'a été publié sur la branche main de /srv/git/vitrine.git."),
                 ('[ "$(nu vitrine rev-parse main)" = "$(g $H/vitrine rev-parse main)" ] && g $H/vitrine merge-base --is-ancestor "$LAB_VITRINE" main', "La branche main de /srv/git/vitrine.git n'est pas identique à celle de ~/vitrine (avec les commits de Julien)."),
                 ('[ "$(g $H/vitrine rev-parse --abbrev-ref "main@{upstream}")" = origin/main ]', "La branche main de ~/vitrine ne suit pas origin/main : un simple git push ne saurait pas où publier."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Jour 4 — À plusieurs sur la même branche",
        "description": "Se synchroniser avec le travail des autres. Compétences : fetch, pull, pull --rebase, autostash, push refusé, conflit pendant un rebase.",
        "lesson": """<h3>Le push refusé</h3><p>Si un collègue a publié entre-temps, votre <code>git push</code> est refusé :</p><pre> ! [rejected]        main -> main (fetch first)<br>error: failed to push some refs to '/srv/git/boutique.git'</pre><p>Git refuse d'écraser un travail que vous n'avez pas encore récupéré. Il faut d'abord <strong>intégrer</strong> les commits du distant.</p><h3>Télécharger, puis intégrer</h3><pre>git fetch                 # télécharge les nouveaux commits (met à jour origin/main), sans toucher à votre branche<br>git status                # « Your branch is behind 'origin/main' by 3 commits »<br>git log --oneline main..origin/main   # commits de origin/main absents de main<br>git pull                  # fetch + intégration dans la branche courante</pre><p>La notation <code>A..B</code> désigne les commits accessibles depuis <code>B</code> mais pas depuis <code>A</code> ; <code>git rev-list --count A..B</code> les compte.</p><h3>Fusion ou rebase ?</h3><p>Quand vous avez des commits locaux <strong>et</strong> que le distant a avancé, les deux historiques ont divergé. Avec Git 2.39, un <code>git pull</code> sans réglage s'arrête alors :</p><pre>hint: You have divergent branches and need to specify how to reconcile them.<br>fatal: Need to specify how to reconcile divergent branches.</pre><p>Il faut choisir :</p><ul><li><strong>fusionner</strong> (<code>git pull --no-rebase</code>) : crée un commit de fusion (« Merge branch 'main' of … ») ;</li><li><strong>rebaser</strong> (<code>git pull --rebase</code>) : rejoue vos commits locaux <em>après</em> ceux du distant. L'historique reste linéaire, sans commit de fusion inutile.</li></ul><p>Ce choix peut devenir le comportement par défaut grâce au réglage <code>pull.rebase</code> (<code>true</code> : rebaser). Un rebase refuse de démarrer si vous avez des modifications non commitées ; l'option <code>--autostash</code> les met de côté le temps de l'opération puis les remet en place, et elle existe aussi sous forme de réglage (cherchez-la dans <code>git help config</code>).</p><h3>Un conflit pendant le rebase</h3><p>Si l'un de vos commits modifie les mêmes lignes qu'un commit du distant, le rebase s'arrête sur ce commit :</p><pre>CONFLICT (content): Merge conflict in css/style.css<br>error: could not apply 1a2b3c4... Mon commit</pre><ol><li>éditez le fichier, gardez le bon contenu, supprimez les marqueurs (voir le jour 6) ;</li><li><code>git add fichier</code> ;</li><li><code>git rebase --continue</code> (et <strong>pas</strong> <code>git commit</code>) : Git passe au commit suivant.</li></ol><p><code>git rebase --abort</code> abandonne tout et revient à l'état d'avant le rebase. Pendant un rebase, vous êtes sur une « tête détachée » : c'est normal, <code>git status</code> indique où vous en êtes.</p><div class="tip">Ne forcez jamais (<code>git push --force</code>) sur une branche partagée : vous effaceriez le travail de vos collègues. Si vous devez vraiment forcer (branche à vous seul), préférez <code>git push --force-with-lease</code>, qui refuse si le distant contient des commits que vous n'avez pas vus.</div>""",
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
  commit nadia 3 "Calcul des frais de livraison"
fi
if [ -z "$(trouve "Titre plus grand")" ]; then
  sed -i 's/^h1 { color: #2d6a4f; }$/h1 { color: #2d6a4f; font-size: 2rem; }/' css/style.css
  commit nadia 2 "Titre plus grand"
  # Nombre de commits publiés ensuite tiré au sort (G4.3 : le nombre à trouver diffère d'un étudiant à l'autre)
  n=${LAB_VARIANTE_G4_3:-$((RANDOM % 6))}
  printf '<p>Service client : du lundi au vendredi, de 9 h à 18 h.</p>\n' > horaires.html
  commit lea 2 "Horaires du service client"
  if [ $n -ge 1 ]; then printf 'User-agent: *\nAllow: /\n' > robots.txt; commit thomas 1 "Ajout du robots.txt"; fi
  if [ $n -ge 2 ]; then printf '<p>Garantie de deux ans sur tout le matériel.</p>\n' > garanties.html; commit lea 1 "Page des garanties"; fi
  if [ $n -ge 3 ]; then printf '<h2>Questions fréquentes</h2>\n' > faq.html; commit thomas 1 "Page FAQ"; fi
  if [ $n -ge 4 ]; then printf '<p>Paiement sécurisé par carte bancaire.</p>\n' > paiement.html; commit lea 1 "Page paiement sécurisé"; fi
  if [ $n -ge 5 ]; then printf '<ul><li>Accueil</li><li>Tarifs</li></ul>\n' > plan.html; commit thomas 1 "Plan du site"; fi
fi
pousse main
NADIA=$(trouve "Calcul des frais de livraison")
CSS=$(trouve "Titre plus grand")
emit NADIA "$NADIA"
emit CSS "$CSS"
# Le vieux clone de Sophie, resté avant les publications de Nadia
poste $H/poste-sophie
OLD=$(git rev-parse "$NADIA^")
git reset -q --hard "$OLD"
git update-ref refs/remotes/origin/main "$OLD"
emit OLD "$OLD"
livre
# Le poste de Thomas : un commit local non poussé, sur la ligne que Nadia a modifiée ensuite. La couleur change à
# chaque réinitialisation (jamais celle déjà publiée) : après une erreur publiée, on peut toujours recommencer.
poste $H/poste-thomas
BASE=$(git rev-parse "$CSS^")
git reset -q --hard "$BASE"
git update-ref refs/remotes/origin/main "$BASE"
ACT=$($AS_ETU git --git-dir=$R show main:css/style.css | sed -n 's/^h1 { color: \(#[0-9a-f]*\);.*/\1/p')
COUL=$(printf '%s\n' '#1b4332' '#40916c' '#2b9348' '#1d3557' '#264653' '#2a9d8f' '#344e41' '#3a5a40' | grep -vxF -- "${ACT:-aucune}" | shuf -n 1)
emit COUL "$COUL"
sed -i "s/color: #2d6a4f;/color: $COUL;/" css/style.css
commit thomas 14 "Couleur du titre conforme à la charte"
livre
''',
        "exercises": [
            {"id": "G4.1", "points": 2, "title": "La règle de l'équipe",
             "ticket": {"from": "nadia", "body": "Chez nous, on garde un historique linéaire : pas de commits « Merge branch 'main' of … » à chaque synchronisation. Configure Git pour que <code>git pull</code> rejoue tes commits au-dessus de ceux de l'équipe. Et comme tu oublieras forcément un jour de commiter avant de synchroniser, fais en sorte que tes modifications en cours soient mises de côté puis remises en place automatiquement pendant l'opération."},
             "desc": "Deux réglages globaux : <code>git pull</code> rebase par défaut, et les modifications non commitées sont mises de côté automatiquement le temps d'un rebase.",
             "hints": ["Le premier réglage est expliqué dans le cours. Le second appartient à la section <code>rebase</code> de la configuration : <code>git help config</code>, puis cherchez « autostash » avec <kbd>/</kbd>.", "<code>git config --global pull.rebase true</code> et <code>git config --global rebase.autoStash true</code>."],
             "checks": [
                 ('[ "$(gget pull.rebase)" = true ]', "git pull ne rebase pas par défaut (réglage global pull.rebase)."),
                 ('[ "$(gget rebase.autoStash)" = true ]', "Les modifications en cours ne sont pas mises de côté automatiquement pendant un rebase (cherchez « autostash » dans git help config, section rebase)."),
             ]},
            {"id": "G4.2", "points": 5, "title": "Mon nom sur la liste",
             "ticket": {"from": "thomas", "body": "Ajoute-toi dans <code>EQUIPE.md</code> de <code>~/boutique</code> (une ligne à ton nom, comme nous) et publie-le. Attention, Nadia et d'autres viennent de pousser des commits : ne les écrase surtout pas !"},
             "desc": "Sur le dépôt partagé, un commit à votre nom ajoute votre nom (<code>user.name</code>) dans <code>EQUIPE.md</code>, les commits publiés par l'équipe sont toujours là, sans commit « Merge branch 'main' of … », et votre <code>main</code> local est synchronisé avec celui du dépôt partagé.",
             "hints": ["Faites votre commit, puis publiez : lisez bien le message de refus, il dit ce qui manque.", "<code>git pull</code> (qui rebase grâce au réglage précédent), puis de nouveau <code>git push</code>."],
             "checks": [
                 ('n=$(gget user.name); [ -n "$n" ] && depot show main:EQUIPE.md | grep -qF -- "$n"', "Votre nom (user.name) n'apparaît pas dans EQUIPE.md sur le dépôt partagé."),
                 ('depot log --format=%ae "$LAB_NADIA^..main" -- EQUIPE.md | grep -qxF "$(gget user.email)"', "Aucun commit à votre nom ne modifie EQUIPE.md sur le dépôt partagé : ajoutez vous-même votre ligne."),
                 ('depot merge-base --is-ancestor "$LAB_CSS" main', "Des commits de l'équipe ont disparu du dépôt partagé : jamais de push --force sur une branche commune ! (bouton « Réinitialiser les fichiers de cette étape » pour les republier)"),
                 ('e=$(gget user.email); c=$(depot log --format="%H %ae" "$LAB_NADIA^..main" -- EQUIPE.md | awk -v m="$e" \'$2 == m { print $1; exit }\'); [ -n "$c" ] && depot merge-base --is-ancestor "$LAB_CSS" "$c"', "Votre commit sur EQUIPE.md n'a pas été rejoué au-dessus des commits de l'équipe (fusion au lieu d'un rebase ?) : la règle est un historique linéaire. Refaites une petite modification d'EQUIPE.md après un git pull --rebase, et publiez-la."),
                 ('m=$(g $B rev-parse main) && depot merge-base --is-ancestor "$m" main && g $B merge-base --is-ancestor "$LAB_CSS" main', "Votre branche main locale n'est pas synchronisée avec le dépôt partagé : elle doit contenir les commits publiés par l'équipe, et tous vos commits doivent être publiés."),
             ]},
            {"id": "G4.3", "points": 4, "title": "Qu'est-ce qui a bougé ?", "manual": True,
             "ticket": {"from": "sophie", "body": "Je reprends mon vieux clone du dépôt de la boutique (<code>~/poste-sophie</code>) après trois semaines de congés. Avant de mélanger quoi que ce soit, je veux savoir <strong>combien de commits</strong> ont été publiés sur <code>main</code> depuis ma dernière synchronisation. Ne touche surtout pas à ma branche : écris juste le nombre dans <code>~/nouveaux-commits.txt</code>."},
             "desc": "Le poste de Sophie connaît les derniers commits du dépôt partagé sans que sa branche <code>main</code> ait bougé, et <code>~/nouveaux-commits.txt</code> contient le nombre de commits de <code>origin/main</code> absents de son <code>main</code>.",
             "hints": ["<code>git pull</code> ferait deux choses : télécharger, puis intégrer. Vous ne voulez que la première. Ensuite, comparez les deux branches.", "<code>git fetch</code>, puis <code>git status</code> ou <code>git rev-list --count main..origin/main</code>."],
             "checks": [
                 ('[ "$(g $H/poste-sophie rev-parse main)" = "$LAB_OLD" ]', "La branche main du poste de Sophie a bougé : il ne fallait rien intégrer (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('g $H/poste-sophie merge-base --is-ancestor "$LAB_CSS" origin/main', "Le poste de Sophie ne connaît pas encore les nouveaux commits du dépôt partagé : il faut les télécharger (sans les intégrer)."),
                 ('[ "$(ans $H/nouveaux-commits.txt)" = "$(g $H/poste-sophie rev-list --count main..origin/main)" ]', "~/nouveaux-commits.txt ne contient pas le nombre de commits de origin/main absents de main (juste le nombre)."),
             ]},
            {"id": "G4.4", "points": 6, "title": "Conflit pendant la synchronisation",
             "ticket": {"from": "thomas", "body": "Hier soir, sur mon poste (<code>~/poste-thomas</code>), j'ai commité la nouvelle couleur du titre (celle de la charte), mais j'ai oublié de la pousser. Ce matin, Nadia a publié un changement sur la même ligne. Publie mon commit sans perdre son travail : le titre doit avoir <strong>ma couleur et sa taille</strong>. Et pas de commit de fusion, tu connais la règle."},
             "desc": "Sur le dépôt partagé, <code>main</code> contient le commit de Nadia et celui de Thomas (« Couleur du titre conforme à la charte »), sans commit de fusion, et l'unique règle <code>h1</code> de <code>css/style.css</code> combine la couleur de Thomas et la taille de Nadia, sans marqueur de conflit.",
             "hints": ["Le push sera refusé : il faut d'abord rejouer le commit de Thomas au-dessus du travail publié. Pendant un rebase, <code>git status</code> dit comment continuer… et ce n'est pas <code>git commit</code>.", "<code>git pull --rebase</code> ; dans <code>css/style.css</code>, gardez une seule ligne <code>h1 { color: &lt;couleur de Thomas&gt;; font-size: 2rem; }</code>, puis <code>git add css/style.css</code>, <code>git rebase --continue</code> et <code>git push</code>."],
             "checks": [
                 ('depot log --format="%an|%s" main | grep -qxF "Thomas Leroy|Couleur du titre conforme à la charte"', "Le commit de Thomas (« Couleur du titre conforme à la charte ») n'est pas sur la branche main du dépôt partagé."),
                 ('depot merge-base --is-ancestor "$LAB_CSS" main', "Le commit de Nadia (« Titre plus grand ») a disparu du dépôt partagé : jamais de push --force sur une branche commune !"),
                 ('! marqueurs "$R" main', "Des marqueurs de conflit (<<<<<<<, =======, >>>>>>>) ont été publiés."),
                 ('[ "$(depot show main:css/style.css | grep "^h1")" = "h1 { color: $LAB_COUL; font-size: 2rem; }" ]', "Dans css/style.css (dépôt partagé), il doit rester une seule règle h1, avec la couleur choisie par Thomas et la taille de Nadia (2rem)."),
                 ('t=$(depot log -1 --format=%H --author="Thomas Leroy" --grep="^Couleur du titre conforme à la charte$" main); depot merge-base --is-ancestor "$LAB_CSS" "$t"', "Le commit de Thomas n'a pas été rejoué au-dessus de celui de Nadia (fusion au lieu d'un rebase) : la règle est un historique linéaire. Bouton « Réinitialiser les fichiers de cette étape » pour retrouver le poste de Thomas, puis recommencez avec un rebase."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Jour 5 — Les branches",
        "description": "Développer à côté de main, suivre les branches des collègues, déplacer et copier des commits. Compétences : branch, switch, push -u, merge, suivi de branche, reset --hard, cherry-pick.",
        "lesson": """<h3>Une branche, c'est une étiquette mobile</h3><p>Une branche n'est qu'un <strong>pointeur</strong> vers un commit, qui avance à chaque nouveau commit. On développe une fonctionnalité sur sa propre branche pour ne pas perturber <code>main</code>.</p><pre>git branch                       # branches locales (* = courante)<br>git branch -a                    # y compris celles du distant (remotes/origin/…)<br>git branch -vv                   # avec la branche distante suivie par chacune<br>git switch -c ma-branche         # crée la branche et s'y place (ancien : git checkout -b)<br>git switch main                  # revient sur main</pre><h3>Publier une branche</h3><pre>git push -u origin ma-branche    # -u : mémorise le lien avec origin/ma-branche (upstream)<br>git push                         # ensuite, un simple push suffit</pre><h3>Récupérer la branche d'un collègue</h3><pre>git fetch                        # rapatrie origin/sa-branche<br>git branch -r                    # branches distantes connues<br>git switch sa-branche            # crée la branche locale qui suit origin/sa-branche</pre><p>Attention : <code>git switch origin/sa-branche</code> refuse, et <code>git checkout origin/sa-branche</code> vous place sur une tête détachée, sans branche locale. <code>git branch -u origin/sa-branche</code> établit le suivi après coup.</p><h3>Fusionner</h3><pre>git switch main<br>git pull                         # d'abord mettre main à jour<br>git merge sa-branche</pre><ul><li>Si <code>main</code> n'a pas bougé depuis la création de la branche : <em>fast-forward</em>, l'étiquette avance simplement.</li><li>Sinon, Git crée un <strong>commit de fusion</strong> à deux parents (l'éditeur s'ouvre pour son message).</li></ul><div class="tip">Avec <code>pull.rebase=true</code>, un <code>git pull</code> fait <em>après</em> une fusion locale non publiée rejoue les commits et fait disparaître la fusion : mettez <code>main</code> à jour <strong>avant</strong> de fusionner.</div><h3>Déplacer une étiquette</h3><pre>git branch nouvelle [commit]     # pose une nouvelle branche (ici, ou sur le commit indiqué), sans s'y placer<br>git reset --hard &lt;commit&gt;        # déplace la branche COURANTE sur ce commit et aligne les fichiers</pre><p>Les commits que plus aucune branche ne désigne ne sont pas détruits tout de suite (voir le reflog, jour 8), mais <code>reset --hard</code> jette définitivement les modifications <strong>non commitées</strong>. On ne déplace ainsi que des commits non publiés.</p><h3>Copier un commit d'une branche à l'autre</h3><pre>git cherry-pick &lt;commit&gt;         # rejoue ce commit (et lui seul) sur la branche courante<br>git cherry-pick -x &lt;commit&gt;      # ajoute « (cherry picked from commit …) » au message</pre><p>La copie a un nouvel identifiant ; l'original reste sur sa branche.</p><h3>Faire le ménage</h3><pre>git branch -d ma-branche                # supprime la branche locale (refuse si son travail n'est pas intégré)<br>git push origin --delete ma-branche     # supprime la branche du dépôt distant<br>git fetch --prune                       # oublie les branches distantes supprimées par d'autres</pre><p><code>branch -d</code> vérifie que la branche est fusionnée dans sa branche distante suivie si elle en a une, sinon dans la branche courante ; <code>-D</code> force la suppression.</p>""",
        "setup": r'''
equipe
if [ -z "$(trouve "Avis : note moyenne")" ]; then
  git switch -q -c feature/avis-clients
  printf '<h2>Avis clients</h2>\n<blockquote>Sac très confortable, même après 20 km. - Claire</blockquote>\n' > avis.html
  commit thomas 5 "Page des avis clients"
  printf '<p>Note moyenne : 4,7 / 5</p>\n' >> avis.html
  commit thomas 4 "Avis : note moyenne"
  pousse feature/avis-clients
  git switch -q main
fi
# main avance pendant que Thomas travaille : sa fusion sera un vrai commit de fusion
if [ -z "$(trouve "Page livraison et retours")" ]; then
  printf '<h2>Livraison et retours</h2>\n<p>Retours gratuits pendant 30 jours.</p>\n' > livraison.html
  commit lea 3 "Page livraison et retours"
  pousse main
fi
emit AVIS "$(trouve "Avis : note moyenne")"
# La branche du code promo de Léa (nom et code imprévisibles)
BR=$($AS_ETU git --git-dir=$R for-each-ref --format='%(refname:strip=2)' 'refs/heads/feature/code-promo-*' | head -n 1)
if [ -z "$BR" ]; then
  BR=feature/code-promo-$((RANDOM % 9000 + 1000))
  git switch -q -c "$BR"
  printf 'const CODE_PROMO = "RANDO%s";\nconst REMISE = 0.1;\n' "$RANDOM$RANDOM" > code-promo.js
  commit lea 6 "Code promo de la rentrée"
  pousse "$BR"
  git switch -q main
fi
emit BR "$BR"
emit CODE "$($AS_ETU git --git-dir=$R show "$BR:code-promo.js" | sed -n 's/^const CODE_PROMO = "\(.*\)";$/\1/p')"
# Julien a commité sur main au lieu d'une branche
nouveau_depot $H/panier-julien
printf '<h1>Panier</h1>\n<div id="panier"></div>\n' > panier.html
commit julien 100 "Page panier"
printf 'function total(lignes) {\n  return lignes.reduce((s, l) => s + l.prix, 0);\n}\n' > panier.js
commit julien 90 "Script du panier"
PJ_BASE=$(git rev-parse HEAD)
emit PJ_BASE "$PJ_BASE"
# Variante : deux, trois ou quatre commits du panier v2 sur main
v=${LAB_VARIANTE_G5_5:-$((RANDOM % 3))}
printf 'export class PanierV2 {\n  constructor() { this.lignes = []; }\n}\n' > panier-v2.js
commit julien 4 "Panier v2 : structure"
if [ $v -ge 1 ]; then printf '.panier-v2 { display: grid; gap: 1rem; }\n' > panier-v2.css; commit julien 3 "Panier v2 : styles"; fi
printf 'export function afficher(p) {\n  return p.lignes.length + " article(s)";\n}\n' >> panier-v2.js
sed -i 's|<div id="panier"></div>|<div id="panier" data-version="2"></div>|' panier.html
commit julien 2 "Panier v2 : affichage"
if [ $v -ge 2 ]; then printf 'import { PanierV2 } from "./panier-v2.js";\ntest("panier vide", () => expect(new PanierV2().lignes.length).toBe(0));\n' > panier-v2.test.js; commit julien 1 "Panier v2 : tests"; fi
emit PJ_TREE "$(git rev-parse 'HEAD^{tree}')"
emit PJ_MSGS "$(git log --format=%s "$PJ_BASE..HEAD" | tr '\n' '|')"
livre
# La refonte de Thomas, avec un correctif de sécurité noyé au milieu
nouveau_depot $H/refonte
mkdir -p js css
printf '<h1>Cimes & Sentiers</h1>\n<form id="contact"></form>\n' > index.html
printf 'function afficherMessage(zone, texte) {\n  zone.innerHTML = texte;\n}\n' > js/formulaire.js
printf 'body { font-family: serif; }\n' > css/site.css
commit thomas 200 "Site de base"
emit RF_MAIN "$(git rev-parse HEAD)"
git switch -q -c feature/refonte
# Variante : message du correctif ; sa place dans la refonte est tirée au sort, et la dernière étape de la refonte
# parle aussi du formulaire (sans toucher à js/formulaire.js)
v=${LAB_VARIANTE_G5_6:-$((RANDOM % 4))}
FIXMSG=("Échappement des champs du formulaire" "Formulaire : textContent au lieu de innerHTML"
  "Correction de la faille XSS du formulaire" "Affichage sûr des messages du formulaire")
pos=$((RANDOM % 4 + 2))
for i in 1 2 3 4 5 6; do
  if [ $i -eq $pos ]; then
    sed -i 's/zone.innerHTML = texte;/zone.textContent = texte;/' js/formulaire.js
    commit thomas $((150 - i)) "${FIXMSG[v]}"
    emit RF_FIX "$(git rev-parse HEAD)"
  else
    printf '/* refonte, étape %s */\n.bloc-%s { margin: %srem; }\n' $i $i $i >> css/site.css
    [ $i -eq 3 ] && sed -i 's/<h1>/<h1 class="titre">/' index.html
    if [ $i -eq 6 ]; then commit thomas $((150 - i)) "Refonte : styles du formulaire"; else commit thomas $((150 - i)) "Refonte : étape $i"; fi
  fi
done
emit RF_REF "$(git rev-parse HEAD)"
git switch -q main
livre
''',
        "exercises": [
            {"id": "G5.1", "points": 4, "title": "La promo d'été",
             "ticket": {"from": "sophie", "body": "Le marketing prépare une promo d'été, mais rien ne doit apparaître sur le site avant validation. Travaille sur une branche <code>feature/promo-ete</code> : ajoute une page <code>promo.html</code> et publie la branche sur le dépôt partagé, pour que je puisse la relire."},
             "desc": "Sur le dépôt partagé, une branche <code>feature/promo-ete</code> dont le dernier commit (à votre nom) contient <code>promo.html</code> ; la branche locale suit sa branche distante.",
             "hints": ["Créez la branche avant de commiter, puis publiez-la en demandant à Git de retenir le lien avec la branche distante.", "<code>git switch -c feature/promo-ete</code>, créez <code>promo.html</code>, <code>git add</code>, <code>git commit</code>, puis <code>git push -u origin feature/promo-ete</code>."],
             "checks": [
                 ('depot rev-parse -q --verify refs/heads/feature/promo-ete', "La branche feature/promo-ete n'existe pas sur le dépôt partagé."),
                 ('depot cat-file -e feature/promo-ete:promo.html', "La branche feature/promo-ete ne contient pas promo.html."),
                 ('[ "$(depot log -1 --format=%ae feature/promo-ete)" = "$(gget user.email)" ]', "Le dernier commit de feature/promo-ete doit être à votre nom."),
                 ('[ "$(g $B rev-parse --abbrev-ref "feature/promo-ete@{upstream}")" = origin/feature/promo-ete ]', "Votre branche locale feature/promo-ete ne suit pas origin/feature/promo-ete."),
             ]},
            {"id": "G5.2", "points": 4, "title": "Les avis clients en ligne",
             "ticket": {"from": "thomas", "body": "Ma branche <code>feature/avis-clients</code> est terminée et relue par Nadia. Tu peux la fusionner dans <code>main</code> et publier ? Je suis en déplacement. Léa a publié sur <code>main</code> pendant ce temps."},
             "desc": "La branche <code>feature/avis-clients</code> est fusionnée dans <code>main</code> sur le dépôt partagé (<code>avis.html</code> y est), avec le travail publié par Léa.",
             "hints": ["<code>main</code> a bougé depuis que Thomas a créé sa branche : mettez-le à jour <strong>avant</strong> de fusionner, et attendez-vous à un vrai commit de fusion.", "<code>git switch main</code>, <code>git pull</code>, <code>git merge origin/feature/avis-clients</code> (enregistrez le message proposé), puis <code>git push</code>."],
             "checks": [
                 ('depot merge-base --is-ancestor "$LAB_AVIS" main', "La branche feature/avis-clients n'est pas fusionnée dans main sur le dépôt partagé. Si un git pull a « aplati » votre fusion en rejouant les commits de Thomas (copies), repartez de origin/main (git reset --hard origin/main) et refusionnez."),
                 ('depot cat-file -e main:avis.html', "avis.html n'est pas sur la branche main du dépôt partagé."),
             ]},
            {"id": "G5.3", "points": 3, "title": "Branches mortes",
             "ticket": {"from": "nadia", "body": "Une branche fusionnée, c'est une branche à supprimer : sinon, dans six mois, on en a cinquante. Supprime <code>feature/avis-clients</code> partout : sur le dépôt partagé et chez toi."},
             "desc": "<code>feature/avis-clients</code> n'existe plus ni sur le dépôt partagé ni dans <code>~/boutique</code> (ni comme branche locale, ni comme branche distante connue), et son travail est bien dans <code>main</code>.",
             "hints": ["Une branche existe à deux endroits : sur le dépôt partagé et (peut-être) chez vous. Chacune se supprime avec sa propre commande.", "<code>git push origin --delete feature/avis-clients</code>, puis <code>git branch -d feature/avis-clients</code> si vous l'aviez créée."],
             "checks": [
                 ('depot merge-base --is-ancestor "$LAB_AVIS" main', "Le travail de feature/avis-clients doit d'abord être fusionné dans main (ticket précédent)."),
                 ('! depot rev-parse -q --verify refs/heads/feature/avis-clients', "La branche existe toujours sur le dépôt partagé."),
                 ('! g $B rev-parse -q --verify refs/heads/feature/avis-clients', "La branche locale feature/avis-clients existe toujours."),
                 ('! g $B rev-parse -q --verify refs/remotes/origin/feature/avis-clients', "~/boutique affiche encore origin/feature/avis-clients : oubliez les branches distantes supprimées (git fetch --prune)."),
             ]},
            {"id": "G5.4", "points": 4, "title": "Le code promo de Léa", "manual": True,
             "ticket": {"from": "sophie", "body": "Léa a publié une branche dont le nom commence par <code>feature/code-promo</code>, avec le code promo de la rentrée. Récupère-la dans <code>~/boutique</code> comme une vraie branche locale (je veux que tu puisses y travailler et pousser sans rien préciser), et donne-moi le code promo qu'elle définit dans <code>~/code-promo.txt</code>."},
             "desc": "<code>~/boutique</code> a une branche locale du même nom que celle de Léa, qui suit sa branche distante, et <code>~/code-promo.txt</code> contient le code promo (le code seul).",
             "hints": ["Commencez par découvrir quelles branches existent sur le dépôt partagé ; une branche locale créée à partir de la branche distante la suit automatiquement.", "<code>git fetch</code>, <code>git branch -r</code>, puis <code>git switch feature/code-promo-…</code> (le nom exact, sans <code>origin/</code>) ; le code est dans <code>code-promo.js</code>."],
             "checks": [
                 ('g $B rev-parse -q --verify "refs/heads/$LAB_BR"', "~/boutique n'a pas de branche locale portant le nom de la branche de Léa."),
                 ('[ "$(g $B rev-parse --abbrev-ref "$LAB_BR@{upstream}")" = "origin/$LAB_BR" ]', "Votre branche locale ne suit pas la branche distante de Léa (git branch -vv)."),
                 ('[ "$(ans $H/code-promo.txt)" = "$LAB_CODE" ]', "~/code-promo.txt ne contient pas le code promo défini par Léa (le code seul, sans guillemets)."),
             ]},
            {"id": "G5.5", "points": 5, "title": "Commits sur la mauvaise branche",
             "ticket": {"from": "julien", "body": "J'ai fait tous mes commits du panier v2 directement sur <code>main</code> dans <code>~/panier-julien</code>, au lieu d'une branche <code>feature/panier-v2</code> (rien n'est poussé). Nadia va me tuer. <code>main</code> doit revenir comme avant mes commits, et mes commits doivent se retrouver sur la branche, intacts."},
             "desc": "Dans <code>~/panier-julien</code>, <code>main</code> est revenu sur « Script du panier » et <code>feature/panier-v2</code> porte tous les commits du panier v2 juste au-dessus ; le répertoire de travail est propre.",
             "hints": ["Une branche n'est qu'une étiquette sur un commit : posez-en une nouvelle là où sont les commits de Julien, puis déplacez l'étiquette <code>main</code>. Comptez bien les commits de Julien.", "Sur <code>main</code> : <code>git branch feature/panier-v2</code>, puis <code>git reset --hard &lt;hash de « Script du panier »&gt;</code> (ou <code>HEAD~n</code>, n étant le nombre de commits du panier v2) ; vérifiez avec <code>git log --oneline --graph --all</code>."],
             "checks": [
                 ('g $H/panier-julien rev-parse -q --verify refs/heads/feature/panier-v2', "Il n'y a pas de branche feature/panier-v2 dans ~/panier-julien."),
                 ('[ "$(g $H/panier-julien rev-parse "feature/panier-v2^{tree}")" = "$LAB_PJ_TREE" ]', "feature/panier-v2 ne contient pas exactement le travail de Julien (panier v2 terminé)."),
                 ('[ "$(g $H/panier-julien log --format=%s main..feature/panier-v2 | tr "\\n" "|")" = "$LAB_PJ_MSGS" ]', "feature/panier-v2 doit porter exactement les commits du panier v2 de Julien, tous, au-dessus de main."),
                 ('[ "$(g $H/panier-julien rev-parse main)" = "$LAB_PJ_BASE" ]', "main n'est pas revenu sur « Script du panier » : l'étiquette main doit reculer, pas recevoir un commit d'annulation."),
                 ('propre $H/panier-julien', "Le répertoire de travail de ~/panier-julien n'est pas propre (git status)."),
             ]},
            {"id": "G5.6", "points": 6, "title": "Juste le correctif de sécurité",
             "ticket": {"from": "nadia", "body": "Dans <code>~/refonte</code>, Thomas a glissé le correctif de la faille du formulaire au milieu de sa refonte, qui ne sera pas prête avant un mois. Mets <strong>uniquement</strong> ce correctif sur <code>main</code>, et je veux que le commit indique de quel commit il vient, pour la traçabilité. Ne touche pas à sa branche."},
             "desc": "<code>main</code> a exactement un nouveau commit : la copie du correctif du formulaire, dont le message mentionne le commit d'origine ; rien d'autre de la refonte, et <code>feature/refonte</code> est inchangée.",
             "hints": ["Retrouvez le commit du correctif (son message peut tromper : le fichier qu'il modifie est plus sûr), puis rejouez ce commit-là, seul, sur <code>main</code> ; une option ajoute la mention de l'origine au message.", "<code>git log --oneline feature/refonte -- js/formulaire.js</code>, <code>git switch main</code>, <code>git cherry-pick -x &lt;hash&gt;</code>."],
             "checks": [
                 ('[ "$(g $H/refonte rev-parse feature/refonte)" = "$LAB_RF_REF" ]', "feature/refonte a été modifiée : la branche de Thomas ne devait pas bouger (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('[ "$(g $H/refonte rev-parse main:js/formulaire.js)" = "$(g $H/refonte rev-parse "$LAB_RF_FIX:js/formulaire.js")" ]', "main ne contient pas le correctif du formulaire."),
                 ('[ "$(g $H/refonte diff --name-only "$LAB_RF_MAIN" main)" = js/formulaire.js ]', "main contient d'autres modifications de la refonte : seul le correctif devait y aller."),
                 ('[ "$(g $H/refonte rev-parse "main^")" = "$LAB_RF_MAIN" ]', "main doit avoir exactement un nouveau commit : la copie du correctif."),
                 ('g $H/refonte log -1 --format=%B main | grep -qF "(cherry picked from commit $LAB_RF_FIX)"', "Le commit ne mentionne pas son origine : Nadia veut la trace « (cherry picked from commit …) » (une option de la commande l'ajoute)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Jour 6 — Les conflits",
        "description": "Quand deux personnes modifient la même ligne, et comment défaire une fusion. Compétences : conflit de fusion, marqueurs, résolution, --ours / --theirs, merge --abort, revert d'une fusion.",
        "lesson": """<h3>D'où vient un conflit ?</h3><p>Git fusionne seul les modifications de lignes différentes. Si <strong>la même ligne</strong> (ou deux lignes voisines) a été modifiée des deux côtés, il ne peut pas choisir : la fusion s'arrête sur un <strong>conflit</strong>.</p><pre>CONFLICT (content): Merge conflict in page.html<br>Automatic merge failed; fix conflicts and then commit the result.</pre><h3>Lire les marqueurs</h3><pre>&lt;&lt;&lt;&lt;&lt;&lt;&lt; HEAD<br>  &lt;li&gt;version de votre branche&lt;/li&gt;<br>=======<br>  &lt;li&gt;version de la branche fusionnée&lt;/li&gt;<br>&gt;&gt;&gt;&gt;&gt;&gt;&gt; nom-de-la-branche</pre><p>Avec <code>git config --global merge.conflictStyle zdiff3</code>, Git affiche aussi, entre <code>|||||||</code> et <code>=======</code>, la version d'<strong>origine</strong> : on voit ce que chaque côté a changé.</p><h3>Résoudre</h3><ol><li><code>git status</code> liste les fichiers en conflit (<em>both modified</em>).</li><li>Éditez chaque fichier : gardez le bon contenu (souvent un mélange des deux) et <strong>supprimez les trois marqueurs</strong>.</li><li><code>git add fichier</code> marque le conflit comme résolu.</li><li><code>git commit</code> (ou <code>git merge --continue</code>) termine la fusion, avec un message déjà rempli.</li></ol><h3>Prendre une version entière</h3><p>Pour un fichier qu'on ne fusionne pas à la main (fichier généré, binaire…), on choisit un côté pour <strong>tout le fichier</strong> :</p><pre>git checkout --ours fichier     # la version de la branche courante<br>git checkout --theirs fichier   # la version de la branche fusionnée<br>git add fichier</pre><div class="tip">À ne pas confondre avec <code>git merge -X ours</code> / <code>-X theirs</code>, qui ne tranchent que les <em>zones en conflit</em> : le reste du fichier reste fusionné.</div><h3>Tout annuler</h3><pre>git merge --abort     # revient à l'état d'avant la fusion</pre><div class="tip">Avant de fusionner une branche dans <code>main</code>, mettez <code>main</code> à jour (<code>git pull</code>) : vous résolvez les conflits une fois, sur la dernière version. Et pour intégrer une branche <strong>publiée</strong>, utilisez <code>git merge origin/la-branche</code> : avec <code>pull.rebase=true</code>, un <code>git pull origin la-branche</code> rebaserait votre <code>main</code> au-dessus d'elle.</div><h3>Annuler une fusion déjà publiée</h3><p>Un commit de fusion a <strong>deux parents</strong> : le parent 1 est la branche où l'on a fusionné (en général <code>main</code>), le parent 2 la branche fusionnée. Pour l'annuler sans réécrire l'histoire, on indique à <code>revert</code> le parent de référence (<em>mainline</em>) :</p><pre>git log --oneline --graph              # repérer la fusion<br>git revert -m &lt;numéro du parent&gt; &lt;fusion&gt;</pre><p>Le nouveau commit ramène le contenu à celui du parent choisi, en gardant tout ce qui a été commité après la fusion. Attention : pour Git, les commits de la branche restent « déjà fusionnés » ; pour les réintégrer plus tard, il faudra annuler l'annulation.</p>""",
        "setup": r'''
equipe
# G6.1 : l'article dont Nadia (prix) et Thomas (libellé) modifient la même ligne. La variante est tirée au sort une
# fois, puis retrouvée d'après les commits déjà publiés sur le dépôt partagé.
TF_NADIA=("Nouveau tarif du sac 40 L" "Nouveau tarif des bâtons de marche" "Nouveau tarif de la tente 2 places" "Sac 40 L : prix revu à la baisse")
TF_AVANT=("Sac 40 L : 79 euros" "Bâtons de marche : 35 euros" "Tente 2 places : 149 euros" "Sac 40 L : 79 euros")
TF_PRIX=("Sac 40 L : 89 euros" "Bâtons de marche : 39 euros" "Tente 2 places : 139 euros" "Sac 40 L : 75 euros")
TF_LIBELLE=("Sac à dos 40 L : 79 euros" "Paire de bâtons de marche : 35 euros" "Tente légère 2 places : 149 euros" "Sac de randonnée 40 L : 79 euros")
TF_FINAL=("Sac à dos 40 L : 89 euros" "Paire de bâtons de marche : 39 euros" "Tente légère 2 places : 139 euros" "Sac de randonnée 40 L : 75 euros")
TF_MOT=("40 L" "de marche" "2 places" "40 L")
v=
for i in 0 1 2 3; do
  if [ -n "$(trouve "${TF_NADIA[i]}")" ]; then v=$i; fi
done
LIB=$(trouve "Libellés plus clairs sur les tarifs")
if [ -z "$v" ] && [ -n "$LIB" ]; then
  for i in 0 1 2 3; do
    if $AS_ETU git --git-dir=$R show "$LIB:tarifs.html" | grep -qF "<li>${TF_LIBELLE[i]}</li>"; then v=$i; fi
  done
fi
v=${v:-${LAB_VARIANTE_G6_1:-$((RANDOM % 4))}}
# Un contrôle par commit : si l'un disparaît (push --force), la réinitialisation le republie
if [ -z "$(trouve "${TF_NADIA[v]}")" ]; then
  git switch -q -c feature/tarifs
  sed -i "s|<li>${TF_AVANT[v]}</li>|<li>${TF_PRIX[v]}</li>|" tarifs.html
  commit nadia 3 "${TF_NADIA[v]}"
  pousse feature/tarifs
  git switch -q main
fi
if [ -z "$LIB" ]; then
  sed -i "s|<li>${TF_AVANT[v]}</li>|<li>${TF_LIBELLE[v]}</li>|" tarifs.html
  commit thomas 2 "Libellés plus clairs sur les tarifs"
  pousse main
fi
emit TARIF "$(trouve "${TF_NADIA[v]}")"
emit LIBELLE "$(trouve "Libellés plus clairs sur les tarifs")"
emit TF_FINAL "${TF_FINAL[v]}"
emit TF_MOT "${TF_MOT[v]}"
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
# Boutique en production : une fusion publiée à annuler. Variante : Sophie a fusionné le paiement dans main
# (main = parent 1), ou main dans la branche du paiement avant d'avancer main dessus (main = parent 2) ; avec ou
# sans page CGV sur main avant la fusion
v=${LAB_VARIANTE_G6_3:-$((RANDOM % 4))}
nouveau_depot $H/boutique-prod
printf '<h1>Cimes & Sentiers</h1>\n<nav>Accueil | Catalogue</nav>\n<p>Bienvenue sur la boutique.</p>\n' > index.html
commit sophie 300 "Site en production"
git switch -q -c feature/paiement
printf 'function payer(montant) {\n  return banque.debiter(montant);\n}\n' > paiement.js
commit thomas 200 "Module de paiement"
sed -i 's/Accueil | Catalogue/Accueil | Catalogue | Paiement/' index.html
commit thomas 190 "Lien vers le paiement"
git switch -q main
printf '<p>Livraison en 48 h partout en France.</p>\n' > livraison.html
commit lea 180 "Page livraison"
if [ $v -ge 2 ]; then printf '<h2>Conditions générales de vente</h2>\n' > cgv.html; commit lea 175 "Conditions générales de vente"; fi
emit PX_IDX "$(git rev-parse HEAD:index.html)"
if [ $((v % 2)) -eq 0 ]; then
  fusionne sophie 170 feature/paiement "Fusion du nouveau paiement"
else
  git switch -q feature/paiement
  fusionne sophie 170 main "Fusion du nouveau paiement"
  git switch -q main
  git merge -q --ff-only feature/paiement
fi
emit PX_M "$(git rev-parse HEAD)"
printf '<p>Mentions légales : Cimes & Sentiers SARL</p>\n' > mentions.html
commit sophie 100 "Mentions légales"
emit PX_Z "$(git rev-parse HEAD)"
livre
# La réserve : un fichier généré en conflit
nouveau_depot $H/reserve
cat > stock.json <<'EOF'
{
  "batons": 12,
  "sacs": 8,
  "tentes": 5,
  "rechauds": 9,
  "gourdes": 30,
  "lampes": 14,
  "cartes": 40,
  "boussoles": 7,
  "duvets": 6
}
EOF
printf '# Réserve\n\nStock de la réserve du magasin.\n' > README.md
commit thomas 100 "Outil de stock"
git switch -q -c maj-stock
sed -i -e "s/\"sacs\": 8,/\"sacs\": $((RANDOM % 40 + 10)),/" -e "s/\"tentes\": 5,/\"tentes\": $((RANDOM % 20 + 6)),/" \
  -e "s/\"duvets\": 6/\"duvets\": $((RANDOM % 20 + 7))/" stock.json
printf 'Dernière synchronisation : automatique (outil de la réserve).\n' >> README.md
commit thomas 20 "Synchronisation du stock"
emit RS_BR "$(git rev-parse HEAD)"
emit RS_BLOB "$(git rev-parse HEAD:stock.json)"
git switch -q main
sed -i -e 's/"sacs": 8,/"sacs": 7,/' -e 's/"lampes": 14,/"lampes": 15,/' stock.json
sed -i '1s/.*/# Réserve (responsable : Julien Petit)/' README.md
commit julien 10 "Corrections manuelles du stock"
emit RS_MAIN "$(git rev-parse HEAD)"
livre
''',
        "exercises": [
            {"id": "G6.1", "points": 6, "title": "Le nouveau prix",
             "ticket": {"from": "nadia", "body": "J'ai poussé une branche <code>feature/tarifs</code> avec le nouveau prix d'un de nos articles. Mais Thomas a modifié la même ligne sur <code>main</code> pour clarifier le libellé… Fusionne ma branche dans <code>main</code> et publie. Il faut garder <strong>le libellé de Thomas</strong> et <strong>mon prix</strong>."},
             "desc": "Sur le dépôt partagé, <code>main</code> contient le commit de Thomas et le commit de Nadia (sa branche fusionnée, pas réécrite), <code>tarifs.html</code> contient une seule ligne pour l'article concerné, avec le libellé de Thomas et le prix de Nadia, et aucun marqueur de conflit ne subsiste.",
             "hints": ["Mettez d'abord <code>main</code> à jour, puis fusionnez la branche <strong>publiée</strong> de Nadia (sans la réécrire). Le conflit se règle en choisissant le contenu ligne par ligne.", "<code>git switch main</code>, <code>git pull</code>, <code>git merge origin/feature/tarifs</code> ; dans <code>tarifs.html</code>, remplacez le bloc <code>&lt;&lt;&lt;&lt;&lt;&lt;&lt;</code> … <code>&gt;&gt;&gt;&gt;&gt;&gt;&gt;</code> par la bonne ligne, puis <code>git add</code>, <code>git commit</code> et <code>git push</code>."],
             "checks": [
                 ('! depot rev-parse -q --verify refs/heads/feature/tarifs || depot merge-base --is-ancestor "$LAB_TARIF" feature/tarifs', "La branche feature/tarifs de Nadia a été réécrite sur le dépôt partagé : une branche publiée se fusionne, elle ne se rebase pas."),
                 ('depot merge-base --is-ancestor "$LAB_TARIF" main', "Le commit de Nadia (son nouveau tarif) n'est pas dans main du dépôt partagé : fusionnez origin/feature/tarifs (une copie rebasée de son commit ne compte pas), puis poussez."),
                 ('depot merge-base --is-ancestor "$LAB_LIBELLE" main', "Le commit de Thomas a disparu de main : jamais de push --force sur une branche commune !"),
                 ('! marqueurs "$R" main', "Des marqueurs de conflit (<<<<<<<, =======, >>>>>>>) ont été commités."),
                 ('depot show main:tarifs.html | grep -qxF "  <li>$LAB_TF_FINAL</li>" && [ "$(depot show main:tarifs.html | grep -c -- "$LAB_TF_MOT")" -eq 1 ]', "tarifs.html doit contenir une seule ligne pour l'article en conflit, qui réunit le libellé de Thomas et le prix de Nadia (relisez les deux côtés du conflit)."),
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
            {"id": "G6.3", "points": 6, "title": "Annuler une fusion publiée",
             "ticket": {"from": "sophie", "body": "Catastrophe : le nouveau module de paiement, fusionné dans <code>main</code> de <code>~/boutique-prod</code> et déjà publié, débite les clients deux fois ! Annule <strong>toute</strong> la fusion, sans réécrire l'historique et sans perdre ce qui a été commité après (les mentions légales)."},
             "desc": "Un nouveau commit de <code>main</code> annule la fusion « Fusion du nouveau paiement » : plus de <code>paiement.js</code>, <code>index.html</code> revient à son état d'avant la fusion, et tout le reste (pages ajoutées sur <code>main</code>, mentions légales) est conservé ; l'historique n'est pas réécrit.",
             "hints": ["Annuler une fusion, c'est retirer ce que la branche a apporté ; mais une fusion a deux parents, et Git doit savoir lequel représente la ligne principale.", "<code>git log --oneline --graph</code> pour repérer la fusion, <code>git show &lt;hash de la fusion&gt;</code> pour lire ses parents dans l'ordre (ligne « Merge: »), puis <code>git revert -m &lt;numéro du parent qui était main&gt; &lt;hash de la fusion&gt;</code> : c'est le parent sans le paiement."],
             "checks": [
                 ('g $H/boutique-prod merge-base --is-ancestor "$LAB_PX_Z" main', "L'historique publié de main a été réécrit (« Mentions légales » ou la fusion ont disparu) : il fallait annuler par un nouveau commit (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('[ -n "$(g $H/boutique-prod log --format=%H --grep="This reverts commit $LAB_PX_M" main)" ]', "Aucun commit de main n'annule la fusion « Fusion du nouveau paiement » (git revert de la fusion elle-même)."),
                 ('r=$(g $H/boutique-prod log --format=%H --grep="This reverts commit $LAB_PX_M" main | tail -n 1); ! g $H/boutique-prod cat-file -e "$r:paiement.js"', "Le commit d'annulation garde paiement.js : c'est ce que la branche feature/paiement a apporté qui doit disparaître (quel parent de la fusion est main ?)."),
                 ('r=$(g $H/boutique-prod log --format=%H --grep="This reverts commit $LAB_PX_M" main | tail -n 1); [ "$(g $H/boutique-prod rev-parse "$r:index.html")" = "$LAB_PX_IDX" ]', "Après l'annulation, index.html n'est pas revenu à son état d'avant la fusion (lien vers le paiement)."),
                 ('r=$(g $H/boutique-prod log --format=%H --grep="This reverts commit $LAB_PX_M" main | tail -n 1); g $H/boutique-prod cat-file -e "$r:mentions.html" && g $H/boutique-prod cat-file -e "$r:livraison.html" && { ! g $H/boutique-prod cat-file -e "$LAB_PX_Z:cgv.html" 2>/dev/null || g $H/boutique-prod cat-file -e "$r:cgv.html"; }', "Le commit d'annulation a perdu du travail qui n'appartenait pas à la branche du paiement (pages ajoutées sur main ou mentions légales)."),
             ]},
            {"id": "G6.4", "points": 5, "title": "Le fichier généré",
             "ticket": {"from": "thomas", "body": "Fusionne la branche <code>maj-stock</code> dans <code>main</code> (<code>~/reserve</code>). <code>stock.json</code> est généré par l'outil de la réserve : on prend <strong>entièrement</strong> la version de la branche, les retouches à la main de Julien sur <code>main</code> ne comptent pas. Pour les autres fichiers, on garde bien le travail des deux côtés."},
             "desc": "<code>maj-stock</code> est fusionnée dans <code>main</code> par un commit de fusion ; <code>stock.json</code> de <code>main</code> est exactement celui de la branche, et <code>README.md</code> garde les ajouts des deux côtés.",
             "hints": ["Un fichier généré ne se résout pas ligne par ligne : on prend une version entière. Attention, toutes les options qui « favorisent un côté » ne le font pas pour tout le fichier.", "<code>git merge maj-stock</code>, puis <code>git checkout --theirs stock.json</code>, <code>git add stock.json</code> et <code>git commit</code>."],
             "checks": [
                 ('[ ! -f $H/reserve/.git/MERGE_HEAD ]', "Une fusion est encore en cours dans ~/reserve : terminez-la (git add, puis git commit)."),
                 ('g $H/reserve merge-base --is-ancestor "$LAB_RS_BR" main && g $H/reserve merge-base --is-ancestor "$LAB_RS_MAIN" main', "maj-stock n'est pas fusionnée dans main (ou main a perdu les commits de Julien)."),
                 ('[ -n "$(g $H/reserve rev-list --merges "$LAB_RS_MAIN..main")" ]', "main ne contient pas de commit de fusion : il fallait fusionner la branche maj-stock."),
                 ('[ "$(g $H/reserve rev-parse main:stock.json)" = "$LAB_RS_BLOB" ]', "stock.json de main n'est pas exactement celui de maj-stock : pour un fichier généré, on prend la version entière de la branche (-X theirs ne tranche que les zones en conflit)."),
                 ('g $H/reserve show main:README.md | grep -qF "responsable : Julien Petit" && g $H/reserve show main:README.md | grep -qF "Dernière synchronisation : automatique"', "README.md de main doit garder les ajouts des deux côtés (le responsable et la synchronisation automatique)."),
                 ('propre $H/reserve', "Le répertoire de travail de ~/reserve n'est pas propre (git status)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    7: {
        "title": "Jour 7 — Réécrire son histoire locale",
        "description": "Mettre de côté, corriger, réorganiser et défaire des commits non publiés. Compétences : stash (-u), commit --amend, rebase, rebase interactif, reset --soft / --mixed / --hard.",
        "lesson": """<h3>Mettre son travail de côté</h3><pre>git stash                  # range les modifications des fichiers suivis et nettoie le répertoire de travail<br>git stash -u               # idem, fichiers non suivis compris (--include-untracked)<br>git stash list             # stash@{0}, stash@{1}… avec leur message<br>git stash show -p stash@{1}   # voir le contenu d'un stash<br>git stash pop [stash@{n}]  # réapplique un stash (le dernier par défaut) et le retire de la liste<br>git stash drop stash@{n}   # supprime un stash</pre><p>Utile quand une urgence tombe : on range, on change de branche, on corrige, on revient, on reprend. Par défaut, un fichier <strong>jamais ajouté</strong> à Git n'est pas rangé.</p><h3>Corriger le dernier commit</h3><pre>git add fichier-oublie<br>git commit --amend -m "Nouveau message"   # remplace le dernier commit</pre><p><code>--amend</code> ne modifie pas le commit : il en crée un nouveau qui le <strong>remplace</strong> (nouveau hash). Sans <code>-m</code>, l'éditeur s'ouvre sur l'ancien message.</p><h3>Reculer une branche : reset</h3><p><code>git reset &lt;commit&gt;</code> déplace l'étiquette de la branche courante. Les commits « enlevés » ne sont plus dans la branche ; ce qui change, c'est le sort de leurs modifications :</p><ul><li><code>--soft</code> : elles restent <strong>indexées</strong>, prêtes à être recommitées ;</li><li><code>--mixed</code> (par défaut) : elles restent dans le répertoire de travail, <strong>non indexées</strong> ;</li><li><code>--hard</code> : elles sont <strong>jetées</strong>, fichiers compris.</li></ul><pre>git reset --soft HEAD~3    # fondre les 3 derniers commits en un seul, à recommiter</pre><h3>Rebaser une branche</h3><p>Votre branche est partie d'un ancien <code>main</code>, qui a avancé depuis. Plutôt que de fusionner <code>main</code> dedans, on <strong>rejoue</strong> ses commits au-dessus du <code>main</code> actuel :</p><pre>git switch ma-branche<br>git rebase main</pre><pre>avant :     A---B---C  main          après :   A---B---C  main<br>                 \\                                      \\<br>                  D---E  ma-branche                      D'---E'  ma-branche</pre><p>Les commits D et E sont recréés (D', E' : nouveaux hash). L'historique est linéaire, et la fusion dans <code>main</code> sera un simple <em>fast-forward</em>.</p><h3>Le rebase interactif</h3><pre>git rebase -i main      # ou : git rebase -i HEAD~4</pre><p>Git ouvre l'éditeur avec la liste des commits à rejouer, <strong>du plus ancien au plus récent</strong>, une ligne par commit :</p><pre>pick 1a2b3c4 Premier commit<br>pick 5d6e7f8 Deuxième commit</pre><ul><li>déplacer une ligne change l'ordre des commits ;</li><li><code>reword</code> : garder le commit, changer son message ;</li><li><code>squash</code> : fondre dans le commit <em>précédent</em> et combiner les messages ;</li><li><code>fixup</code> : fondre dans le précédent en gardant seulement le message du précédent ;</li><li><code>drop</code> (ou supprimer la ligne) : retirer le commit ; <code>edit</code> : s'arrêter dessus pour le modifier.</li></ul><p>On enregistre, on quitte, et Git rejoue la liste. En cas de conflit : résoudre, <code>git add</code>, <code>git rebase --continue</code> ; <code>git rebase --abort</code> pour tout annuler.</p><div class="tip">Règle d'or : on ne réécrit (amend, reset, rebase) que des commits <strong>pas encore partagés</strong>. Réécrire des commits déjà poussés oblige tous les collègues à réparer leur dépôt.</div>""",
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
# La branche du formulaire de contact : cinq commits à ranger en deux
nouveau_depot $H/contact
printf '<h1>Cimes & Sentiers</h1>\n' > index.html
commit nadia 100 "Site"
emit CT_MAIN "$(git rev-parse HEAD)"
git switch -q -c feature/contact
printf '<form id="contact">\n  <input name="nom">\n  <textarea name="mesage"></textarea>\n</form>\n' > contact.html
commit nadia 10 "Ajout du formulaire de contact"
# Variante : l'ordre des retouches et le fichier que chacune modifie
c_email() { sed -i 's|  <input name="nom">|  <input name="nom">\n  <input name="email">|' contact.html; }
c_faute() { sed -i 's/mesage/message/' contact.html; }
c_bouton() { sed -i 's|</form>|  <button>Envoyer</button>\n</form>|' contact.html; }
v_creer() { printf 'function valider(f) {\n  return f.nom.value !== "" && f.%s.value.includes("@");\n}\n' "${1:-email}" > validation.js; }
v_faute() { sed -i 's/f\.emial/f.email/' validation.js; }
v_plus() { printf 'function messageValide(f) {\n  return f.message.value.length >= 10;\n}\n' >> validation.js; }
etape() { "$1" "${@:4}"; commit nadia $2 "$3"; }
VAL="Validation des champs du formulaire"
v=${LAB_VARIANTE_G7_4:-$((RANDOM % 4))}
case $v in
  0) etape c_email 9 "wip"; etape c_faute 8 "faute de frappe"; etape v_creer 7 "$VAL"; etape c_bouton 6 "oups oubli" ;;
  1) etape v_creer 9 "$VAL"; etape c_email 8 "wip"; etape v_plus 7 "oups oubli"; etape c_faute 6 "faute de frappe" ;;
  2) etape c_faute 9 "faute de frappe"; etape v_creer 8 "$VAL"; etape v_plus 7 "wip"; etape c_bouton 6 "oups oubli" ;;
  *) etape v_creer 9 "$VAL" emial; etape c_email 8 "wip"; etape v_faute 7 "faute de frappe"; etape c_bouton 6 "oups oubli" ;;
esac
emit CT_TREE "$(git rev-parse 'HEAD^{tree}')"
livre
# Les deux commits ratés de Julien
nouveau_depot $H/faq-julien
printf '<h1>Cimes & Sentiers</h1>\n' > index.html
commit julien 100 "Site"
emit FQ_BASE "$(git rev-parse HEAD)"
printf '<h2>Questions fréquentes</h2>\n<h3>Livraison</h3>\n<p>48 h en France métropolitaine.</p>\n' > faq.html
N=NOTE-$RANDOM$RANDOM
# Variante : deux, trois ou quatre commits ratés
v=${LAB_VARIANTE_G7_5:-$((RANDOM % 3))}
notes() { printf 'Notes de Julien (%s) : demander à Nadia comment on range des commits.\n' "$N" > notes-perso.txt; }
suite() { printf '<h3>Retours</h3>\n<p>Retours gratuits pendant 30 jours.</p>\n' >> faq.html; }
case $v in
  0) notes; commit julien 3 "faq"; suite; echo "Penser à relire la FAQ." >> notes-perso.txt; commit julien 2 "suite + notes" ;;
  1) commit julien 4 "faq"; notes; commit julien 3 "notes"; suite; echo "Penser à relire la FAQ." >> notes-perso.txt; commit julien 2 "suite" ;;
  *) commit julien 5 "faq"; notes; commit julien 4 "wip"; suite; commit julien 3 "suite"
     echo "Penser à relire la FAQ." >> notes-perso.txt; commit julien 2 "fin" ;;
esac
emit FQ_BLOB "$(git rev-parse HEAD:faq.html)"
emit FQ_NOTE "$N"
livre
# Le bandeau de Sophie : un fichier modifié et un fichier tout neuf, non suivi
nouveau_depot $H/bandeau
printf '<h1>Cimes & Sentiers</h1>\n<p>Bienvenue</p>\n' > index.html
printf '<p>Écrivez-nous : contact@cimes-sentier.fr</p>\n' > contact.html
commit sophie 100 "Site"
git switch -q -c feature/bandeau
mkdir -p css
printf '.bandeau { background: #2d6a4f; }\n' > css/bandeau.css
commit sophie 50 "Préparation du bandeau"
git switch -q main
printf '<div class="bandeau">Soldes : -30 %%</div>\n' > bandeau.html
commit lea 40 "Ancien bandeau des soldes"
emit BD_BLOB "$(git rev-parse HEAD:bandeau.html)"
git switch -q feature/bandeau
T1=IDX-$RANDOM$RANDOM; T2=BAN-$RANDOM$RANDOM
printf '<!-- %s -->\n<div class="bandeau">Nouveau bandeau en préparation</div>\n' "$T1" >> index.html
printf '<div class="bandeau">Nouvelle collection %s</div>\n' "$T2" > bandeau.html
emit BD_T1 "$T1"
emit BD_T2 "$T2"
livre
''',
        "exercises": [
            {"id": "G7.1", "points": 5, "title": "Urgence pendant la newsletter",
             "ticket": {"from": "sophie", "body": "Tu es sur la newsletter (<code>~/atelier</code>, branche <code>feature/newsletter</code>, travail pas terminé) ? Laisse tout de côté : le numéro de téléphone de <code>contact.html</code> est faux sur <code>main</code>, il manque un chiffre. Le bon, c'est <strong>04 76 00 00 00</strong>. Corrige-le sur <code>main</code>, puis reprends ta newsletter là où tu en étais, sans commiter ton brouillon."},
             "desc": "Dans <code>~/atelier</code> : <code>main</code> a un commit qui corrige le numéro (<code>04 76 00 00 00</code>) sans contenir le brouillon ; vous êtes revenu sur <code>feature/newsletter</code> avec le brouillon (non commité) restauré, et le stash est vide.",
             "hints": ["Git refuse de changer de branche tant que votre brouillon risque d'être écrasé : mettez-le de côté sans le commiter, et pensez à le reprendre ensuite.", "<code>git stash</code>, <code>git switch main</code>, corrigez et commitez, <code>git switch feature/newsletter</code>, puis <code>git stash pop</code>."],
             "checks": [
                 ('g $H/atelier show main:contact.html | grep -qF "04 76 00 00 00<"', "Sur main, contact.html n'a pas exactement le bon numéro (04 76 00 00 00) dans un commit."),
                 ('! g $H/atelier grep -q BROUILLON main --', "Le brouillon de la newsletter a été commité sur main."),
                 ('[ "$(g $H/atelier branch --show-current)" = feature/newsletter ]', "Vous devez être revenu sur la branche feature/newsletter."),
                 ('grep -q BROUILLON-NEWSLETTER $H/atelier/newsletter.html', "Le brouillon de newsletter.html n'est pas restauré dans le répertoire de travail."),
                 ('! g $H/atelier grep -q BROUILLON feature/newsletter --', "Le brouillon ne doit pas être commité : il n'est pas relu."),
                 ('[ -z "$(g $H/atelier stash list)" ]', "Le stash n'est pas vide : reprenez le travail rangé avec git stash pop (et non apply), ou supprimez l'entrée restante."),
             ]},
            {"id": "G7.2", "points": 3, "title": "Un commit à rattraper",
             "ticket": {"from": "julien", "body": "J'ai commité dans <code>~/corrections</code> avec un message plein de fautes, et j'ai oublié le fichier <code>js/remise.js</code>… Je n'ai rien poussé. Tu peux arranger ça ? Le message doit être <strong>Correction du calcul du panier</strong>, et pas de commit en plus, Nadia déteste ça."},
             "desc": "Dans <code>~/corrections</code>, le dernier commit (qui remplace celui de Julien, même parent) a pour message <code>Correction du calcul du panier</code> et contient <code>js/remise.js</code> et la correction de <code>js/panier.js</code>.",
             "hints": ["On ne crée pas de nouveau commit : on remplace le dernier, en y ajoutant le fichier oublié et en changeant son message.", "<code>git add js/remise.js</code>, puis <code>git commit --amend -m \"Correction du calcul du panier\"</code>."],
             "checks": [
                 ('[ "$(g $H/corrections log -1 --format=%s)" = "Correction du calcul du panier" ]', "Le message du dernier commit n'est pas « Correction du calcul du panier »."),
                 ('[ "$(g $H/corrections rev-parse HEAD^)" = "$LAB_PARENT" ]', "Le commit de Julien doit être remplacé, pas complété par un nouveau commit."),
                 ('g $H/corrections cat-file -e HEAD:js/remise.js', "js/remise.js n'est pas dans le dernier commit."),
                 ('g $H/corrections show HEAD:js/panier.js | grep -q "a.prix \\* a.quantite"', "La correction de js/panier.js a été perdue."),
             ]},
            {"id": "G7.3", "points": 5, "title": "Une histoire linéaire",
             "ticket": {"from": "nadia", "body": "La branche <code>feature/filtres</code> de Thomas (<code>~/filtres</code>) est partie d'un vieux <code>main</code>. Avant la relecture, rebase-la sur le <code>main</code> actuel : je veux ses deux commits au-dessus de <code>main</code>, sans commit de fusion, avec tout son travail. Et ne touche pas à <code>main</code>."},
             "desc": "Dans <code>~/filtres</code>, <code>main</code> n'a pas bougé et <code>feature/filtres</code> contient ses deux commits (« Filtre par prix », « Filtre par marque ») rejoués au-dessus de <code>main</code>, sans commit de fusion, avec les deux fichiers de filtres.",
             "hints": ["On ne fusionne pas <code>main</code> dans la branche : on rejoue les commits de la branche au-dessus du <code>main</code> actuel, depuis la branche elle-même.", "<code>git switch feature/filtres</code>, puis <code>git rebase main</code> ; vérifiez avec <code>git log --oneline --graph --all</code>."],
             "checks": [
                 ('[ "$(g $H/filtres rev-parse main)" = "$LAB_MAINF" ]', "main a été modifié : c'est feature/filtres qu'il faut rebaser (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('g $H/filtres merge-base --is-ancestor main feature/filtres', "feature/filtres n'est pas basée sur le main actuel."),
                 ('[ -z "$(g $H/filtres rev-list --merges main..feature/filtres)" ]', "feature/filtres contient un commit de fusion : il fallait rebaser, pas fusionner."),
                 ('[ "$(g $H/filtres log --format=%s main..feature/filtres | sort | tr "\\n" "|")" = "Filtre par marque|Filtre par prix|" ]', "feature/filtres doit contenir exactement ses deux commits « Filtre par prix » et « Filtre par marque » au-dessus de main."),
                 ('[ "$(g $H/filtres diff --name-only main feature/filtres | sort | tr "\\n" " ")" = "filtre-marque.js filtre-prix.js " ]', "Par rapport à main, feature/filtres doit apporter exactement filtre-prix.js et filtre-marque.js : du travail de Thomas a été perdu, ou du travail de main défait."),
             ]},
            {"id": "G7.4", "points": 6, "title": "Deux commits propres",
             "ticket": {"from": "nadia", "body": "Ta branche <code>feature/contact</code> (<code>~/contact</code>, rien de poussé) a cinq commits dont « wip », « faute de frappe » et « oups oubli » : illisible en relecture. Je veux <strong>exactement deux commits</strong> : « Ajout du formulaire de contact » (tout le travail sur <code>contact.html</code>) puis « Validation des champs du formulaire » (<code>validation.js</code>). Le contenu final ne doit pas changer d'un octet."},
             "desc": "<code>feature/contact</code> a exactement deux commits au-dessus de <code>main</code> : « Ajout du formulaire de contact » (seulement <code>contact.html</code>, dans sa version finale) puis « Validation des champs du formulaire » (seulement <code>validation.js</code>), avec le même contenu final qu'avant ; <code>main</code> n'a pas bougé.",
             "hints": ["Le rebase interactif permet de réordonner des commits (en déplaçant leurs lignes) et de fondre un commit dans le précédent sans garder son message. Regardez d'abord quel fichier modifie chaque retouche (<code>git show --stat &lt;hash&gt;</code>) : elle doit rejoindre le commit principal de ce fichier.", "<code>git rebase -i main</code> : placez chaque retouche juste sous le commit principal du même fichier, remplacez <code>pick</code> par <code>fixup</code> pour « wip », « faute de frappe » et « oups oubli », enregistrez et quittez."],
             "checks": [
                 ('[ ! -d $H/contact/.git/rebase-merge ] && [ ! -d $H/contact/.git/rebase-apply ]', "Un rebase est encore en cours dans ~/contact (git status) : terminez-le (git rebase --continue) ou annulez-le (git rebase --abort)."),
                 ('[ "$(g $H/contact rev-parse main)" = "$LAB_CT_MAIN" ]', "main a bougé : seule la branche feature/contact devait être réorganisée."),
                 ('[ "$(g $H/contact rev-parse "feature/contact^{tree}")" = "$LAB_CT_TREE" ]', "Le contenu final de feature/contact a changé : la réorganisation ne doit rien perdre ni rien ajouter (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('g $H/contact merge-base --is-ancestor main feature/contact && [ "$(g $H/contact log --format=%s main..feature/contact | tr "\\n" "|")" = "Validation des champs du formulaire|Ajout du formulaire de contact|" ]', "feature/contact doit contenir exactement deux commits au-dessus de main : « Ajout du formulaire de contact » puis « Validation des champs du formulaire »."),
                 ('[ "$(g $H/contact diff --name-only feature/contact~1 feature/contact)" = validation.js ] && [ "$(g $H/contact diff --name-only main feature/contact~1)" = contact.html ]', "Chaque commit doit avoir un seul sujet : le premier ne touche que contact.html (dans sa version finale, toutes ses retouches comprises), le second ne touche que validation.js (lui aussi avec ses retouches)."),
             ]},
            {"id": "G7.5", "points": 5, "title": "Défaire sans perdre",
             "ticket": {"from": "julien", "body": "Dans <code>~/faq-julien</code>, tous mes commits après « Site » (rien n'est poussé) sont ratés : messages nuls, et j'y ai mis <code>notes-perso.txt</code> par erreur. Remplace-les par <strong>un seul</strong> commit « Page FAQ » qui contient la version finale de <code>faq.html</code>. Mes notes doivent rester sur le disque, mais dans aucun commit."},
             "desc": "Dans <code>~/faq-julien</code>, un seul commit « Page FAQ », juste après « Site », remplace tous les commits de Julien avec la version finale de <code>faq.html</code> et sans <code>notes-perso.txt</code> ; les notes sont toujours sur le disque, non suivies (ou ignorées).",
             "hints": ["Il existe un moyen de reculer l'étiquette de la branche jusqu'à « Site » en <strong>gardant</strong> les modifications des commits retirés dans le répertoire de travail ; ensuite, on recommite seulement ce qu'on veut. Comptez bien les commits de Julien.", "<code>git reset &lt;hash de « Site »&gt;</code> ou <code>git reset HEAD~n</code>, n étant le nombre de commits de Julien (ou <code>--soft</code>, puis <code>git restore --staged notes-perso.txt</code>), <code>git add faq.html</code>, <code>git commit -m \"Page FAQ\"</code>. Surtout pas <code>--hard</code>."],
             "checks": [
                 ('grep -qF "$LAB_FQ_NOTE" $H/faq-julien/notes-perso.txt', "notes-perso.txt a disparu ou a perdu son contenu : Julien veut garder ses notes sur le disque (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('[ "$(g $H/faq-julien rev-parse HEAD^)" = "$LAB_FQ_BASE" ]', "Il faut exactement un commit après « Site », à la place de tous les commits de Julien."),
                 ('[ "$(g $H/faq-julien log -1 --format=%s)" = "Page FAQ" ]', "Le message du commit doit être « Page FAQ »."),
                 ('[ "$(g $H/faq-julien rev-parse HEAD:faq.html)" = "$LAB_FQ_BLOB" ]', "faq.html du commit n'est pas la version finale de Julien."),
                 ('! g $H/faq-julien cat-file -e HEAD:notes-perso.txt', "notes-perso.txt est encore dans le commit."),
                 ('s=$(g $H/faq-julien status --porcelain); [ "$s" = "?? notes-perso.txt" ] || { [ -z "$s" ] && g $H/faq-julien check-ignore -q notes-perso.txt; }', "git status doit seulement montrer notes-perso.txt non suivi (ou rien, s'il est ignoré)."),
             ]},
            {"id": "G7.6", "points": 5, "title": "Urgence avec un fichier tout neuf",
             "ticket": {"from": "sophie", "body": "Tu travailles sur le nouveau bandeau (<code>~/bandeau</code>, branche <code>feature/bandeau</code>) : <code>index.html</code> modifié et un tout nouveau <code>bandeau.html</code>, rien de commité. Urgence : sur <code>main</code>, l'adresse de <code>contact.html</code> est fausse, c'est <strong>contact@cimes-sentiers.fr</strong>. Corrige-la sur <code>main</code>, puis reprends ton travail exactement où tu en étais, sans rien commiter de ton brouillon."},
             "desc": "Sur <code>main</code> de <code>~/bandeau</code>, un commit corrige l'adresse de <code>contact.html</code> sans toucher au <code>bandeau.html</code> de <code>main</code> ; vous êtes revenu sur <code>feature/bandeau</code> avec vos deux fichiers en cours intacts et non commités, et le stash est vide.",
             "hints": ["Essayez, et lisez le refus : par défaut, la mise de côté ignore une catégorie de fichiers… justement celle qui bloque le changement de branche.", "<code>git stash -u</code>, <code>git switch main</code>, corrigez et commitez, <code>git switch feature/bandeau</code>, puis <code>git stash pop</code>."],
             "checks": [
                 ('g $H/bandeau show main:contact.html | grep -qF "contact@cimes-sentiers.fr"', "Sur main, contact.html n'a pas la bonne adresse (contact@cimes-sentiers.fr) dans un commit."),
                 ('[ "$(g $H/bandeau rev-parse main:bandeau.html)" = "$LAB_BD_BLOB" ]', "Le bandeau.html de main a changé : votre nouveau bandeau n'est pas prêt, il ne devait pas y aller."),
                 ('! g $H/bandeau grep -q -e "$LAB_BD_T1" -e "$LAB_BD_T2" main feature/bandeau --', "Votre travail en cours (index.html ou bandeau.html) a été commité : il fallait le mettre de côté."),
                 ('[ "$(g $H/bandeau branch --show-current)" = feature/bandeau ]', "Vous devez être revenu sur la branche feature/bandeau."),
                 ('grep -qF "$LAB_BD_T1" $H/bandeau/index.html && grep -qF "$LAB_BD_T2" $H/bandeau/bandeau.html', "Votre travail en cours n'est pas restauré : index.html et bandeau.html doivent contenir vos modifications (bouton « Réinitialiser les fichiers de cette étape » s'ils sont perdus)."),
                 ('[ -z "$(g $H/bandeau stash list)" ]', "Le stash n'est pas vide : reprenez votre travail avec git stash pop (ou supprimez l'entrée restante)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Jour 8 — Enquêtes et mise en production",
        "description": "Trouver un bug par dichotomie, étiqueter une version, récupérer un commit perdu. Compétences : bisect, tag (et son remplacement), reflog.",
        "lesson": """<h3>Trouver le commit fautif par dichotomie</h3><p>Le code marchait il y a 40 commits, il ne marche plus. <code>git bisect</code> coupe l'intervalle en deux à chaque étape : au plus 6 tests pour 40 commits.</p><pre>git bisect start<br>git bisect bad                  # le commit courant est mauvais<br>git bisect good &lt;hash&gt;          # celui-ci était bon<br># Git se place au milieu : testez, puis dites-lui<br>git bisect good   # ou   git bisect bad   (ou git bisect skip si ce commit est impossible à tester)<br># … jusqu'à « &lt;hash&gt; is the first bad commit »<br>git bisect log                  # le journal de la recherche<br>git bisect reset                # revient où vous étiez (et termine la recherche)</pre><p>Si un script dit si c'est bon ou mauvais, Git fait tout seul :</p><pre>git bisect run ./tests.sh</pre><p>Code de retour du script : <code>0</code> = bon ; <code>125</code> = impossible à tester (commit sauté) ; de 1 à 127 (sauf 125) = mauvais ; 128 ou plus = arrêt de la recherche.</p><h3>Étiqueter une version</h3><pre>git tag -a v1.0 -m "Première version en production"   # étiquette annotée (auteur, date, message)<br>git tag v1.0-test                                     # étiquette légère : un simple nom sur un commit<br>git tag                                               # liste<br>git show v1.0<br>git push origin v1.0                                  # les étiquettes ne partent pas avec un simple git push</pre><p>Une étiquette est annotée si on la crée avec <code>-a</code>, <code>-m</code> ou <code>-s</code> ; sinon elle est légère. Pour une version livrée, on préfère une étiquette annotée.</p><h3>Déplacer une étiquette publiée</h3><p>Une étiquette est censée ne jamais bouger : Git ne la remplace pas sans qu'on le lui demande.</p><pre>git tag -d v1.0                      # supprime l'étiquette locale<br>git push origin --delete v1.0        # supprime l'étiquette du dépôt distant<br>git push --force origin v1.0         # ou : remplace l'étiquette distante par la vôtre</pre><div class="tip">Un <code>git fetch</code> ne remplace jamais une étiquette que vous avez déjà (« would clobber existing tag ») : chaque clone qui a récupéré l'ancienne doit la supprimer (ou faire <code>git fetch --tags --force</code>).</div><h3>Rien n'est vraiment perdu</h3><p>Un <code>git reset --hard</code> malheureux a « effacé » des commits ? Ils existent encore : le <strong>reflog</strong> garde la trace de toutes les positions de <code>HEAD</code> (environ 90 jours).</p><pre>git reflog                       # HEAD@{0}, HEAD@{1}… avec les hash<br>git branch &lt;nom&gt; &lt;hash&gt;         # une branche pour ne plus le perdre<br>git reset --hard &lt;hash&gt;          # ou remettre la branche courante dessus</pre>""",
        "setup": r'''
K=$H/calculs
nouveau_depot $K
# ecrire_prix <expression> : réécrit prix.sh ; l'expression change de forme à chaque commit (la « pioche » ne
# désigne donc pas le commit fautif : il faut tester)
ecrire_prix() {
cat > prix.sh <<EOF
#!/bin/bash
# Prix TTC d'un prix hors taxes (TVA à 20 %)
awk -v p="\$1" 'BEGIN { printf "%.2f\\n", $1 }'
EOF
}
ecrire_prix "p * 1.20"
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
BONS=("p * 1.20" "p * 1.2" "p * 6 / 5" "p * (1 + 0.20)" "p * 12 / 10" "p * 120 / 100" "p * (1 + 20 / 100)")
FAUX=("p * 1.02" "p * (1 + 0.02)" "p * 102 / 100" "p * 51 / 50" "p * (1 + 2 / 100)")
bug=$((RANDOM % 22 + 8))
for i in $(seq 1 36); do
  echo "- modification $i" >> CHANGELOG.md
  if [ $i -lt $bug ]; then ecrire_prix "${BONS[i % 7]}"; else ecrire_prix "${FAUX[i % 5]}"; fi
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
# Variante : ce que Julien a fait après avoir perdu ses commits (la conclusion n'est pas toujours HEAD@{1})
v=${LAB_VARIANTE_G8_3:-$((RANDOM % 4))}
case $v in
  0) git reset -q --hard HEAD~2 ;;
  1) git reset -q --hard HEAD~2
     printf '\n## Introduction\n\nÀ rédiger.\n' >> rapport.md; commit julien 20 "Introduction"
     printf "\n## Remerciements\n\nMerci à toute l'équipe.\n" >> rapport.md; commit julien 10 "Remerciements" ;;
  2) git reset -q --hard HEAD~1; git reset -q --hard HEAD~1 ;;
  *) git reset -q --hard HEAD~2; git switch -q -c essai
     printf '\n<!-- essai de mise en page -->\n' >> rapport.md; commit julien 20 "Essai de mise en page"
     git switch -q main ;;
esac
livre
# Mise en production : Julien a déjà posé (et publié) une étiquette légère v1.0 sur un vieux commit
equipe
if [ -z "$(trouve "Préparation de la mise en production")" ]; then
  printf 'version=1.0\n' > VERSION
  commit sophie 5 "Préparation de la mise en production"
  pousse main
fi
if ! $AS_ETU git --git-dir=$R rev-parse -q --verify refs/tags/v1.0 >/dev/null; then
  git tag v1.0 "$(trouve "Page des tarifs")"
  pousse v1.0
fi
emit PREP "$(trouve "Préparation de la mise en production")"
''',
        "exercises": [
            {"id": "G8.1", "points": 6, "title": "Le bug du prix TTC", "manual": True,
             "ticket": {"from": "diallo", "body": "Le script <code>prix.sh</code> de Marc (<code>~/calculs</code>) donne des prix TTC faux, alors qu'il était juste au premier commit. Il y a eu des dizaines de commits depuis, avec des messages qui ne veulent rien dire, et Marc réécrivait la formule à chaque fois. Trouve celui qui a tout cassé. Le script <code>tests.sh</code> dit si le calcul est bon. Pour l'audit, je veux aussi le journal de ta recherche."},
             "desc": "L'identifiant du premier commit où <code>./tests.sh</code> échoue, seul sur la première ligne de <code>~/commit-fautif.txt</code>, et dans <code>~/bisect.log</code> le journal de votre recherche par dichotomie, tel que Git l'enregistre.",
             "hints": ["Tester 36 commits un par un serait long : partez d'un commit bon et d'un commit mauvais, et coupez l'intervalle en deux à chaque fois. Git peut même lancer le test tout seul. Le journal s'affiche avant la fin de la recherche.", "<code>git bisect start</code>, <code>git bisect bad</code>, <code>git bisect good &lt;premier commit&gt;</code>, <code>git bisect run ./tests.sh</code>, puis <code>git bisect log &gt; ~/bisect.log</code> avant <code>git bisect reset</code>."],
             "checks": [
                 ('hashok $H/commit-fautif.txt "$LAB_BUG"', "~/commit-fautif.txt ne contient pas l'identifiant du commit qui a introduit le bug (7 caractères au moins)."),
                 ('grep -qF "# first bad commit: [$LAB_BUG]" $H/bisect.log && grep -q "^git bisect good" $H/bisect.log', "~/bisect.log n'est pas le journal d'une recherche par dichotomie qui a abouti sur ce commit (à enregistrer avant de terminer la recherche)."),
             ]},
            {"id": "G8.2", "points": 5, "title": "Version 1.0",
             "ticket": {"from": "sophie", "body": "Le site part en production ! Julien a voulu bien faire : il a posé et publié une étiquette <code>v1.0</code>… légère, et sur un vieux commit. Il faut une étiquette <strong>annotée</strong> <code>v1.0</code> sur le <code>main</code> actuel de la boutique (avec le commit « Préparation de la mise en production »), sur le dépôt partagé <strong>et</strong> dans ton <code>~/boutique</code>."},
             "desc": "Sur le dépôt partagé et dans <code>~/boutique</code>, <code>v1.0</code> est une étiquette annotée qui désigne le même commit de <code>main</code>, lequel inclut « Préparation de la mise en production ».",
             "hints": ["Une étiquette publiée ne se déplace pas toute seule : il faut la remplacer des deux côtés. Et un fetch ne remplace jamais une étiquette que vous avez déjà.", "Dans <code>~/boutique</code> à jour sur main : <code>git tag -d v1.0</code>, <code>git tag -a v1.0 -m \"...\"</code>, puis <code>git push --force origin v1.0</code> (ou <code>git push origin --delete v1.0</code> puis <code>git push origin v1.0</code>)."],
             "checks": [
                 ('depot rev-parse -q --verify refs/tags/v1.0', "L'étiquette v1.0 n'est pas sur le dépôt partagé."),
                 ('[ "$(depot cat-file -t v1.0)" = tag ]', "v1.0 est toujours une étiquette légère sur le dépôt partagé : il faut une étiquette annotée (auteur, date, message)."),
                 ('depot merge-base --is-ancestor "$LAB_PREP" "v1.0^{commit}"', "v1.0 ne désigne pas le main actuel : elle doit inclure le commit « Préparation de la mise en production »."),
                 ('depot merge-base --is-ancestor "v1.0^{commit}" main', "v1.0 doit désigner un commit de la branche main."),
                 ('[ "$(g $B rev-parse -q --verify "v1.0^{commit}")" = "$(depot rev-parse "v1.0^{commit}")" ]', "Dans ~/boutique, l'étiquette v1.0 ne désigne pas le même commit que sur le dépôt partagé (un fetch ne remplace jamais une étiquette existante)."),
             ]},
            {"id": "G8.3", "points": 4, "title": "Le rapport disparu",
             "ticket": {"from": "julien", "body": "Catastrophe : j'ai tapé des commandes trouvées sur Internet (des <code>git reset --hard</code>…) dans <code>~/rapport</code>, et mes deux derniers commits, dont la conclusion du rapport annuel, ont disparu ! Il faut le rendre demain… Mets-les à l'abri sur une branche <code>sauvetage</code>."},
             "desc": "Dans <code>~/rapport</code>, une branche <code>sauvetage</code> désigne le commit « Conclusion » disparu.",
             "hints": ["Git tient un journal de toutes les positions successives de HEAD, même celles qu'aucune branche ne désigne plus.", "<code>git reflog</code>, puis <code>git branch sauvetage &lt;hash du commit Conclusion&gt;</code>."],
             "checks": [
                 ('g $H/rapport rev-parse -q --verify refs/heads/sauvetage', "Il n'y a pas de branche sauvetage dans ~/rapport."),
                 ('[ "$(g $H/rapport rev-parse sauvetage)" = "$LAB_PERDU" ]', "La branche sauvetage ne désigne pas le commit « Conclusion » disparu."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    9: {
        "title": "Jour 9 — Secrets et garde-fous",
        "description": "Ne plus laisser fuir de secrets : fichiers suivis par erreur, règles d'ignorance piégeuses, secret dans l'historique, hook de contrôle. Compétences : rm --cached, .gitignore avancé, check-ignore, filter-repo / filter-branch, push --force, hooks.",
        "lesson": """<h3>Un secret commité est un secret publié</h3><p>Mots de passe, clés d'API, fichiers <code>.env</code> : une fois commités et poussés, ils sont copiés dans chaque clone. Les supprimer dans un nouveau commit ne suffit pas : ils restent dans les commits précédents, que tout le monde peut consulter (<code>git log -p</code>).</p><div class="tip">Le premier geste est toujours de <strong>révoquer</strong> le secret (changer le mot de passe, régénérer la clé). Nettoyer l'historique vient ensuite, et ne protège jamais les clones déjà faits.</div><h3>Ne plus suivre un fichier</h3><pre>git rm --cached fichier       # retire le fichier de l'index (il reste sur le disque)<br>git commit -m "Ne plus suivre fichier"</pre><p>Ajouter le fichier au <code>.gitignore</code> ne suffit pas s'il est déjà suivi : Git continue de suivre ses modifications. (<code>git update-index --assume-unchanged</code> ne fait que masquer ces modifications : le fichier reste dans les commits.)</p><h3>Les règles de .gitignore</h3><ul><li>un motif sans barre oblique s'applique à tous les niveaux : <code>*.log</code>, <code>local.ini</code> ;</li><li>un motif qui contient une barre oblique (au début ou au milieu) est relatif à l'emplacement du <code>.gitignore</code> : <code>/local.ini</code>, <code>docs/brouillon.md</code> ;</li><li>une barre finale ne vise que les dossiers : <code>cache/</code> ;</li><li><code>**</code> traverse les dossiers : <code>docs/**/*.pdf</code> ;</li><li><code>!motif</code> ré-inclut ce qu'une règle précédente excluait… <strong>sauf</strong> si un dossier parent est lui-même exclu : Git n'entre jamais dans un dossier exclu. On exclut alors le <em>contenu</em> du dossier (<code>dossier/*</code>) plutôt que le dossier.</li></ul><pre>git check-ignore -v chemin              # quelle règle (fichier:ligne) ignore ce chemin ?<br>git check-ignore -v --no-index chemin   # idem, même pour un fichier déjà suivi<br>git status --ignored                    # voir aussi les fichiers ignorés</pre><h3>Effacer un fichier de tout l'historique</h3><p>Il faut <strong>réécrire</strong> chaque commit qui contient le fichier. Deux outils :</p><pre>git filter-repo --invert-paths --path chemin/secret.env   # l'outil recommandé (installé ici)<br>git filter-branch --index-filter 'git rm -q --cached --ignore-unmatch chemin/secret.env' -- main   # l'ancien, intégré à Git</pre><ul><li><code>filter-repo</code> refuse de travailler ailleurs que dans un clone tout frais (option <code>--force</code> pour passer outre) et, par sécurité, <strong>retire le distant</strong> <code>origin</code> : il faut le redéclarer avant de publier.</li><li><code>filter-branch</code> garde une sauvegarde de l'ancienne histoire dans <code>refs/original/</code> : tant qu'elle existe, le secret aussi (<code>git update-ref -d refs/original/refs/heads/main</code>).</li><li>Pour un ou deux commits récents, un rebase interactif avec <code>edit</code> suffit aussi.</li></ul><p>Ensuite, la nouvelle histoire remplace l'ancienne sur le dépôt partagé : <code>git push --force</code>, exceptionnellement, en prévenant l'équipe (chacun devra recloner ou réaligner sa copie). Vérifiez avec <code>git log --all -p | grep &lt;secret&gt;</code> : <code>--all</code> parcourt toutes les références, branches distantes, sauvegardes et stash compris.</p><h3>Les hooks : des garde-fous automatiques</h3><p>Git exécute des scripts à certains moments, s'ils sont placés dans <code>.git/hooks/</code>, portent le nom de l'événement et sont <strong>exécutables</strong> :</p><ul><li><code>pre-commit</code> : avant chaque commit ; un code de retour non nul l'annule ;</li><li><code>commit-msg</code> : peut vérifier (ou refuser) le message ;</li><li><code>pre-push</code> : avant chaque push.</li></ul><p>Dans <code>.git/hooks/</code>, Git fournit des exemples (<code>*.sample</code>). Un hook ne voyage pas avec le dépôt : pour le partager, on le versionne dans un dossier (par exemple <code>.githooks/</code>) et chacun active <code>git config core.hooksPath .githooks</code>. <code>git commit --no-verify</code> contourne <code>pre-commit</code> : un hook est un garde-fou, pas une sécurité absolue.</p><div class="tip">Pour examiner ce qui va partir dans le commit, un hook regarde l'<strong>index</strong> (<code>git diff --cached</code>), pas les fichiers du disque.</div>""",
        "setup": r'''
# L'API météo de Thomas : .env ignoré… mais déjà suivi
nouveau_depot $H/api-meteo
printf 'API_KEY=%s\n' "$(jeton)" > .env
printf 'const cle = process.env.API_KEY;\nconsole.log("API météo prête");\n' > app.js
commit thomas 50 "Première version de l'API météo"
printf '.env\n' > .gitignore
commit thomas 40 "Ignorer le fichier .env"
K2=$(jeton)
printf 'API_KEY=%s\n' "$K2" > .env
emit K2 "$K2"
livre
# Le catalogue de Nadia : un git status illisible
nouveau_depot $H/catalogue-web
mkdir -p src docs outils
printf 'console.log("catalogue");\n' > src/app.js
printf '# Catalogue web\n' > README.md
commit nadia 30 "Squelette du catalogue"
R1=$RANDOM; R2=$RANDOM; R3=$RANDOM
mkdir -p logs build/css node_modules/lodash outils/node_modules/leftpad config
echo "démarrage" > logs/app-$R1.log
echo "Les journaux de l'application sont dans ce dossier." > logs/LISEZMOI.log
echo "trace" > src/debug-$R2.log
echo "minifié" > build/app-$R3.min.js
echo "body{}" > build/css/site.css
: > build/.gitkeep
echo "module.exports = {};" > node_modules/lodash/index.js
echo "module.exports = {};" > outils/node_modules/leftpad/index.js
printf '[bdd]\nmot_de_passe = %s\n' "$(jeton)" > config/local.ini
printf '[bdd]\nhote = localhost\n' > config/defaut.ini
printf '[cache]\nactif = oui\n' > src/local.ini
printf '# Construire le catalogue\n' > docs/build.md
printf '#!/bin/sh\necho déploiement\n' > outils/deploiement.sh
emit IGN "logs/app-$R1.log src/debug-$R2.log build/app-$R3.min.js build/css/site.css node_modules/lodash/index.js outils/node_modules/leftpad/index.js config/local.ini"
emit GARDE "logs/LISEZMOI.log build/.gitkeep config/defaut.ini src/local.ini docs/build.md outils/deploiement.sh src/app.js"
livre
# La météo des sommets : une clé commitée puis « supprimée », publiée sur un dépôt partagé
nouveau_depot $H/meteo
printf 'const villes = ["Grenoble", "Chamonix"];\nconsole.log("Météo des sommets");\n' > app.js
printf '# Météo des sommets\n' > README.md
commit sophie 100 "Squelette de la météo"
KEY=$(jeton)
mkdir -p config
printf 'API_KEY=%s\n' "$KEY" > config/api.env
printf 'const config = lireConfig("config/api.env");\n' >> app.js
commit julien 90 "Configuration de l'API"
printf 'function prevision(ville, jours) {\n  return api.get(ville, jours);\n}\n' > previsions.js
commit thomas 80 "Prévisions à 3 jours"
git rm -q config/api.env
commit julien 70 "Suppression de la clé"
printf '\nfunction afficher(p) {\n  return p.ville + " : " + p.temperature + " °C";\n}\n' >> previsions.js
commit thomas 60 "Mise en forme des prévisions"
emit KEY "$KEY"
emit MT_FILES "$(git ls-tree -r HEAD | awk '{ printf "%s:%s ", $4, $3 }')"
publie_nu meteo
livre
''',
        "exercises": [
            {"id": "G9.1", "points": 4, "title": "Le .env qui ne veut pas partir",
             "ticket": {"from": "thomas", "body": "Dans <code>~/api-meteo</code>, j'ai mis <code>.env</code> dans le <code>.gitignore</code>, mais <code>git status</code> me montre toujours les modifications de mon <code>.env</code> (j'ai une nouvelle clé), et j'ai peur de la pousser par erreur. Arrange ça sans perdre ma nouvelle clé : le fichier doit rester sur mon disque."},
             "desc": "Dans <code>~/api-meteo</code>, <code>.env</code> n'est plus dans le dernier commit, il est ignoré par le <code>.gitignore</code> du dépôt, il contient toujours la nouvelle clé de Thomas, et <code>git status</code> n'affiche rien.",
             "hints": ["Relisez ce que le cours du jour 1 dit de <code>.gitignore</code> et des fichiers <strong>déjà suivis</strong>. Il faut que Git arrête de suivre le fichier, sans le supprimer du disque.", "<code>git rm --cached .env</code>, puis un commit."],
             "checks": [
                 ('grep -qF "$LAB_K2" $H/api-meteo/.env', "Le fichier .env a disparu ou a perdu la nouvelle clé de Thomas : il devait rester sur le disque (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)."),
                 ('! g $H/api-meteo cat-file -e HEAD:.env', ".env est toujours suivi par Git (il est dans le dernier commit) : masquer ses modifications ne suffit pas, le prochain commit de .env partirait avec le reste."),
                 ('g $H/api-meteo check-ignore -v .env | grep -q "^\\.gitignore:"', ".env n'est pas ignoré par le .gitignore du dépôt."),
                 ('g $H/api-meteo cat-file -e HEAD:app.js && g $H/api-meteo cat-file -e HEAD:.gitignore', "app.js ou .gitignore a disparu du dernier commit."),
                 ('propre $H/api-meteo', "git status signale encore des modifications : commitez-les."),
             ]},
            {"id": "G9.2", "points": 6, "title": "Le .gitignore du catalogue",
             "ticket": {"from": "nadia", "body": "Dans <code>~/catalogue-web</code>, <code>git status</code> est illisible. Écris et commite un <code>.gitignore</code> qui ignore :<ul><li>tous les <code>.log</code>, où qu'ils soient, <strong>sauf</strong> <code>logs/LISEZMOI.log</code> ;</li><li>tout le contenu du dossier <code>build/</code> de la racine, <strong>sauf</strong> <code>build/.gitkeep</code> (qui garde le dossier dans le dépôt) ;</li><li>tous les dossiers <code>node_modules/</code>, à n'importe quel niveau ;</li><li><code>config/local.ini</code>, qui contient un mot de passe, mais pas les autres <code>local.ini</code> ni <code>config/defaut.ini</code>.</li></ul>Commite ensuite tout ce qui doit l'être : <code>git status</code> doit être vide."},
             "desc": "Le <code>.gitignore</code> commité de <code>~/catalogue-web</code> ignore exactement ce que Nadia demande, les fichiers à garder sont tous commités et <code>git status</code> n'affiche rien.",
             "hints": ["Deux pièges : une exception (<code>!motif</code>) ne peut pas ré-inclure un fichier dont le <strong>dossier parent</strong> est exclu, et un motif sans barre oblique s'applique à tous les niveaux. <code>git check-ignore -v chemin</code> dit quelle règle s'applique.", "<code>*.log</code>, <code>!logs/LISEZMOI.log</code>, <code>/build/*</code>, <code>!/build/.gitkeep</code>, <code>node_modules/</code>, <code>/config/local.ini</code> ; puis <code>git add .</code> et <code>git commit</code>."],
             "checks": [
                 ('g $H/catalogue-web cat-file -e HEAD:.gitignore', "Le .gitignore n'est pas commité dans ~/catalogue-web."),
                 ('for p in $LAB_IGN; do g $H/catalogue-web check-ignore -q --no-index "$p" || { echo "MSG:$p n\'est pas ignoré."; exit 1; }; done', "Le .gitignore n'ignore pas tout ce que Nadia demande."),
                 ('for p in $LAB_GARDE; do ! g $H/catalogue-web check-ignore -q --no-index "$p" || { echo "MSG:$p est ignoré alors qu\'il doit être gardé."; exit 1; }; done', "Le .gitignore ignore des fichiers qui doivent être gardés."),
                 ('for p in $LAB_GARDE; do g $H/catalogue-web cat-file -e "HEAD:$p" || { echo "MSG:$p n\'est pas commité."; exit 1; }; done', "Des fichiers à garder ne sont pas dans le dernier commit."),
                 ('propre $H/catalogue-web', "git status n'est pas vide dans ~/catalogue-web."),
             ]},
            {"id": "G9.3", "points": 6, "title": "La clé dans l'historique",
             "ticket": {"from": "sophie", "body": "Mauvaise nouvelle : Julien a commité la clé de l'API météo dans <code>config/api.env</code>, puis l'a « supprimée »… dans le commit suivant. Elle est donc toujours dans l'historique de <code>~/meteo</code> et du dépôt partagé <code>/srv/git/meteo.git</code>. Je l'ai révoquée, mais je veux qu'elle n'apparaisse plus <strong>nulle part</strong> dans l'historique, ni chez toi ni sur le dépôt partagé, sans perdre le reste du travail. Et ce fichier doit être ignoré à l'avenir."},
             "desc": "La clé n'apparaît plus dans aucun commit de <code>~/meteo</code> ni de <code>/srv/git/meteo.git</code> (toutes références confondues) ; les autres commits et les fichiers de l'application sont conservés à l'identique ; un <code>.gitignore</code> commité et publié ignore <code>config/api.env</code>, et <code>main</code> est identique des deux côtés.",
             "hints": ["Supprimer le fichier aujourd'hui ne l'efface pas des commits d'hier : il faut réécrire toute l'histoire concernée (un outil dédié le fait pour tous les commits d'un coup), vérifier qu'aucune référence ne garde l'ancienne histoire, puis republier, exceptionnellement de force.", "<code>git filter-repo --force --invert-paths --path config/api.env</code> puis <code>git remote add origin /srv/git/meteo.git</code> ; ou <code>git filter-branch --index-filter 'git rm -q --cached --ignore-unmatch config/api.env' -- main</code> puis <code>git update-ref -d refs/original/refs/heads/main</code>. Ensuite le <code>.gitignore</code>, et <code>git push --force origin main</code>."],
             "checks": [
                 ('! nu meteo log --all -p | grep -qF "$LAB_KEY"', "La clé apparaît encore dans l'historique du dépôt partagé /srv/git/meteo.git : réécrivez l'historique, puis publiez-le (de force, exceptionnellement)."),
                 ('! g $H/meteo log --all -p | grep -qF "$LAB_KEY"', "La clé apparaît encore dans l'historique de ~/meteo (toutes références : branches, origin/main, sauvegarde refs/original de filter-branch, stash…)."),
                 ('for m in "Squelette de la météo" "Prévisions à 3 jours" "Mise en forme des prévisions"; do nu meteo log --format=%s main | grep -qxF "$m" || { echo "MSG:Le commit « $m » a disparu."; exit 1; }; done', "Des commits ont disparu de main sur le dépôt partagé : seule la clé devait être retirée de l'historique."),
                 ('for f in $LAB_MT_FILES; do [ "$(nu meteo rev-parse "main:${f%%:*}")" = "${f#*:}" ] || { echo "MSG:${f%%:*} a changé."; exit 1; }; done', "Les fichiers de l'application ne sont plus identiques sur main du dépôt partagé."),
                 ('[ "$(g $H/meteo rev-parse main)" = "$(nu meteo rev-parse main)" ]', "La branche main de ~/meteo et celle du dépôt partagé diffèrent."),
                 ('nu meteo cat-file -e main:.gitignore && g $H/meteo check-ignore -q --no-index config/api.env && propre $H/meteo', "config/api.env doit être ignoré par un .gitignore commité et publié (et git status doit être vide)."),
             ]},
            {"id": "G9.4", "points": 5, "title": "Un garde-fou avant chaque commit", "manual": True,
             "ticket": {"from": "nadia", "body": "Pour que ça n'arrive plus, installe dans <code>~/meteo</code> un contrôle automatique qui <strong>refuse tout commit</strong> dont les modifications indexées ajoutent une ligne contenant <code>API_KEY=</code> ou <code>PASSWORD=</code> (par exemple <code>DB_PASSWORD=…</code>). Les autres commits doivent passer normalement, même s'il traîne un fichier secret non indexé dans le dossier."},
             "desc": "<code>~/meteo</code> a un hook exécutable qui, avant chaque commit, refuse ceux dont les modifications indexées ajoutent <code>API_KEY=</code> ou <code>PASSWORD=</code>, et accepte les autres. La vérification rejoue votre hook dans un dépôt de test.",
             "hints": ["Git exécute les scripts placés dans un dossier précis du dépôt s'ils portent le nom de l'événement et sont exécutables ; pour celui qui intervient avant le commit, un code de retour non nul annule le commit. Examinez ce qui est indexé, pas les fichiers du disque.", "<code>.git/hooks/pre-commit</code> : <code>#!/bin/sh</code>, puis <code>if git diff --cached | grep -qE '^\\+.*(API_KEY|PASSWORD)='; then echo \"Secret détecté\" &gt;&amp;2; exit 1; fi</code> ; et <code>chmod +x .git/hooks/pre-commit</code>."],
             "checks": [
                 ('hp=$(g $H/meteo config --local --get core.hooksPath || echo .git/hooks); case $hp in /*) ;; *) hp=$H/meteo/$hp ;; esac; [ -f "$hp/pre-commit" ] && [ -x "$hp/pre-commit" ]', "Aucun hook pre-commit exécutable dans ~/meteo (dossier .git/hooks, nom exact, chmod +x)."),
                 (r'''hp=$(g $H/meteo config --local --get core.hooksPath || echo .git/hooks); case $hp in /*) ;; *) hp=$H/meteo/$hp ;; esac
runuser -u etudiant -- env HOME=$H HOOK="$hp/pre-commit" timeout 20 bash -s <<'TEST'
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT
cd "$T" || exit 1
git init -q . && git config user.name Test && git config user.email test@cimes-sentiers.fr && git config core.hooksPath .git/hooks || exit 1
cat "$HOOK" > .git/hooks/pre-commit && chmod 700 .git/hooks/pre-commit || exit 1
echo "Premier fichier" > lisezmoi.txt; git add lisezmoi.txt
git commit -q --no-verify -m init </dev/null >/dev/null 2>&1 || exit 1
echo "Deuxième ligne" >> lisezmoi.txt; git add lisezmoi.txt
git commit -q -m normal </dev/null >/dev/null 2>&1 || { echo "MSG:Un commit sans secret a été refusé par votre hook."; exit 1; }
echo "API_KEY=abc123" > cle.env; git add cle.env
git commit -q -m cle </dev/null >/dev/null 2>&1 && { echo "MSG:Un commit qui ajoute une ligne API_KEY= a été accepté."; exit 1; }
git rm -q --cached cle.env
echo "DB_PASSWORD=secret" >> lisezmoi.txt; git add lisezmoi.txt
git commit -q -m mdp </dev/null >/dev/null 2>&1 && { echo "MSG:Un commit qui ajoute une ligne DB_PASSWORD= a été accepté."; exit 1; }
git checkout -q HEAD -- lisezmoi.txt
echo "Troisième ligne" >> lisezmoi.txt; git add lisezmoi.txt
git commit -q -m suite </dev/null >/dev/null 2>&1 || { echo "MSG:Un commit sans secret a été refusé parce qu'un fichier secret non indexé (cle.env) traînait dans le dossier : seules les modifications indexées comptent."; exit 1; }
exit 0
TEST''', "Votre hook ne se comporte pas comme demandé (testé dans un dépôt temporaire) :"),
             ]},
        ],
    },
}
