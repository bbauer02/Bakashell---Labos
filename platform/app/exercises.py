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
'''



# ─── Scénario : l'étudiant est admin système junior chez une PME fictive ──────
# Les exercices peuvent prendre la forme d'un ticket envoyé par un personnage :
#   "ticket": {"from": "<clé de CHARACTERS>", "body": "<message HTML>"}
# « desc » décrit alors précisément le livrable attendu.

from .scenario import CHARACTERS, COMPANY  # noqa: F401  (personnages partagés entre parcours)

# Personnage qui « donne » les indices
MENTOR = "lea"

SCENARIO_INTRO = """<div class="scenario"><h3>Bienvenue chez Cimes &amp; Sentiers</h3><p>Vous rejoignez l'équipe informatique de <strong>Cimes &amp; Sentiers</strong>, une PME de 40 salariés qui vend du matériel de randonnée en ligne, comme <strong>admin système junior</strong>. Votre prédécesseur, Marc, est parti précipitamment en laissant derrière lui des notes éparpillées, des scripts obscurs et un serveur en désordre.</p><p>Les demandes de vos collègues arrivent sous forme de <strong>tickets</strong> (onglet <em>Exercices</em>). Ce cours est votre documentation : lisez-le, puis traitez les tickets dans le terminal.</p><ul class="cast"><li><strong>Sophie Marchand</strong> — DSI, votre responsable</li><li><strong>Léa Nguyen</strong> — admin système senior, votre mentore (c'est elle qui vous donne les indices)</li><li><strong>Thomas Leroy</strong> — développeur web</li><li><strong>Aminata Diallo</strong> — responsable comptabilité</li><li><strong>Julien Petit</strong> — stagiaire, souvent perdu</li></ul></div>"""


STEPS = {
    # ─────────────────────────────────────────────────────────────────────
    1: {
        "title": "Jour 1 — Prise en main du serveur",
        "description": "Premier jour chez Cimes & Sentiers. Compétences : cd, ls, cat, fichiers cachés, mkdir, touch.",
        "lesson": SCENARIO_INTRO + """<h3>Bienvenue en console !</h3><p>Le terminal affiche une invite :</p><pre>etudiant@linux-lab:~$</pre><p>Elle indique <strong>qui vous êtes</strong> (etudiant), <strong>sur quelle machine</strong> (linux-lab) et <strong>où vous êtes</strong> (<code>~</code>).</p><div class="tip"><code>~</code> est un raccourci vers votre dossier personnel : <code>/home/etudiant</code>.</div><h3>Commandes essentielles</h3><ul><li><code>whoami</code> — votre nom d'utilisateur</li><li><code>pwd</code> — le dossier courant (<em>Print Working Directory</em>)</li><li><code>cd &lt;dossier&gt;</code> — se déplacer ; <code>cd</code> seul ramène dans <code>~</code></li><li><code>ls</code> — lister ; <code>ls -a</code> montre aussi les fichiers <strong>cachés</strong> (nom commençant par <code>.</code>)</li><li><code>cat &lt;fichier&gt;</code> — afficher le contenu d'un fichier</li><li><code>mkdir &lt;dossier&gt;</code> — créer un dossier ; <code>touch &lt;fichier&gt;</code> — créer un fichier vide</li></ul><h3>Écrire une réponse dans un fichier</h3><pre>echo "ma réponse" &gt; ~/reponse.txt</pre><p>Le symbole <code>&gt;</code> envoie le texte dans le fichier (nous y reviendrons en détail).</p><h3>L'arborescence Linux</h3><ul><li><code>/</code> — la racine, tout part d'ici</li><li><code>/home</code> — dossiers personnels</li><li><code>/etc</code> — configuration</li><li><code>/opt</code> — logiciels et données additionnels</li><li><code>/usr</code> — programmes installés</li><li><code>/var</code> — données variables (logs, caches…)</li></ul><div class="tip">La touche <kbd>Tab</kbd> complète les noms de fichiers et de commandes : utilisez-la sans modération.</div>""",
        "setup": r'''
A=/opt/archives-marc
rm -rf $A
mkdir -p $A/2023/reseau/baie $A/2024/reseau/baie $A/2024/postes $A/divers
w=$(rword); old1=$(rword); old2=$(rword)
printf 'Note de Marc - baie réseau (PÉRIMÉ, ne plus utiliser)\nCODE=%s\n' "$old1" > $A/2023/reseau/baie/note.txt
printf 'Note de Marc - baie réseau (à jour)\nCODE=%s\n' "$w" > $A/2024/reseau/baie/note.txt
printf 'Note de Marc - postes de travail\nRien à signaler.\n' > $A/2024/postes/note.txt
printf 'Note de Marc - vieux code de la baie, PÉRIMÉ\nCODE=%s\n' "$old2" > $A/divers/note.txt
chmod -R a+rX $A
emit CODE "$w"
j=$(rword)
mkdir -p $H/passation
echo "Bienvenue ! J'ai laissé ici ce qu'il te faut. Certaines choses ne se voient pas au premier coup d'oeil... -- Marc" > $H/passation/lisez-moi.txt
echo "$j" > $H/passation/.jeton-vpn
own $H/passation
emit JETON "$j"
''',
        "exercises": [
            {"id": "1.1", "points": 3, "title": "Le code de la baie réseau",
             "ticket": {"from": "sophie", "body": "Bienvenue parmi nous ! Petit souci pour ton premier jour : Marc, ton prédécesseur, est parti sans nous donner le code du cadenas de la baie réseau. Il rangeait ses notes sous <code>/opt/archives-marc</code>, dans des fichiers <code>note.txt</code>… mais il ne jetait jamais les anciennes. Tu peux me retrouver le code <strong>à jour</strong> ?"},
             "desc": "Le code (sans le <code>CODE=</code>) dans <code>~/code-baie.txt</code>.",
             "hints": ["Explorez avec <code>ls /opt/archives-marc</code>, puis descendez dossier par dossier avec <code>cd</code> et <code>ls</code>.", "Lisez chaque note avec <code>cat</code> : la première ligne indique si elle est périmée. La bonne est dans le dossier de 2024."],
             "checks": [
                 ('test -f $H/code-baie.txt', "Le fichier ~/code-baie.txt n'existe pas."),
                 ('a=$(ans $H/code-baie.txt); [ "${a#CODE=}" = "$LAB_CODE" ]', "Ce n'est pas le code à jour : vérifiez que la note n'est pas marquée PÉRIMÉ."),
             ]},
            {"id": "1.2", "points": 3, "title": "Le jeton VPN de Marc",
             "ticket": {"from": "lea", "body": "Salut, je suis Léa, c'est moi qui vais t'accompagner. Marc t'a laissé un dossier <code>~/passation</code>. Il y cachait toujours son jeton VPN… littéralement : dans un fichier caché. Récupère-le, on en a besoin pour la connexion au datacenter."},
             "desc": "Le contenu du fichier caché dans <code>~/jeton-vpn.txt</code>.",
             "hints": ["Sous Linux, un fichier caché a un nom qui commence par un point : <code>ls</code> ne l'affiche pas par défaut.", "<code>ls -a ~/passation</code>"],
             "checks": [
                 ('[ "$(ans $H/jeton-vpn.txt)" = "$LAB_JETON" ]', "~/jeton-vpn.txt n'existe pas ou ne contient pas le jeton."),
             ]},
            {"id": "1.3", "points": 3, "title": "Ton espace de travail",
             "ticket": {"from": "sophie", "body": "Chez nous, chacun range ses documents et ses projets au même endroit, ça évite de chercher partout quand quelqu'un est absent. Prépare-toi un dossier pour chaque."},
             "desc": "Les dossiers <code>~/documents</code> et <code>~/projets</code>, créés sans <code>sudo</code>.",
             "hints": ["<code>mkdir</code> accepte plusieurs noms à la suite."],
             "checks": [
                 ('test -d $H/documents && test -d $H/projets', "Les dossiers ~/documents et ~/projets doivent exister."),
                 ('[ "$(owner $H/documents)" = etudiant ] && [ "$(owner $H/projets)" = etudiant ]', "Les dossiers appartiennent à root : créez-les sans sudo."),
             ]},
            {"id": "1.4", "points": 3, "title": "Journal de bord",
             "ticket": {"from": "lea", "body": "Conseil de vieille admin : note tout ce que tu fais sur un serveur. Le jour où ça casse, tu seras contente ou content d'avoir un historique. Commence par créer ton journal, vide pour l'instant."},
             "desc": "Un fichier vide <code>~/documents/journal.txt</code>.",
             "hints": ["La commande <code>touch</code> crée un fichier vide."],
             "checks": [
                 ('test -f $H/documents/journal.txt', "Le fichier ~/documents/journal.txt n'existe pas."),
                 ('[ "$(owner $H/documents/journal.txt)" = etudiant ]', "Le fichier doit vous appartenir (créez-le sans sudo)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Jour 2 — La doc et les chemins",
        "description": "Lire le manuel et ne plus se perdre dans l'arborescence. Compétences : man, chemins absolus et relatifs, . et ..",
        "lesson": """<h3>RTFM : Read The Manual !</h3><pre>man &lt;commande&gt;</pre><p>Dans le manuel : <kbd>/mot</kbd> recherche, <kbd>n</kbd> passe au résultat suivant, <kbd>q</kbd> quitte.</p><div class="tip"><strong>Conventions :</strong> <code>[PARAM]</code> = optionnel, <code>...</code> = répétable. Beaucoup de commandes acceptent aussi <code>--help</code>.</div><h3>Les options</h3><ul><li><code>ls -l</code> — format détaillé</li><li><code>ls -a</code> — fichiers cachés</li><li><code>ls -la</code> — les deux combinées</li></ul><h3>Chemins absolus vs relatifs</h3><table class="lesson-table"><tr><th>Absolu</th><th>Relatif</th></tr><tr><td>Commence par <code>/</code></td><td>Part du dossier courant</td></tr><tr><td><code>/home/etudiant/projets</code></td><td><code>projets</code> (depuis <code>~</code>)</td></tr><tr><td>Toujours valable</td><td>Dépend de l'endroit où l'on est</td></tr></table><div class="tip"><code>.</code> = dossier courant · <code>..</code> = dossier parent · <code>../..</code> = deux niveaux au-dessus</div><p><code>mkdir -p a/b/c</code> crée toute la chaîne de dossiers d'un coup.</p>""",
        "setup": r'''
P=$H/partage-marc
mkdir -p $P/clients/2024/devis $P/clients/2023 $P/fournisseurs
echo "Grille tarifaire clients 2025" > $P/clients/tarifs.txt
echo "Devis n°2024-017 - Club alpin de Grenoble" > $P/clients/2024/devis/devis-017.txt
own $P
''',
        "exercises": [
            {"id": "2.1", "points": 3, "title": "Le projet boutique",
             "ticket": {"from": "thomas", "body": "Hello ! Thomas, dev web. On lance la refonte de la boutique en ligne. Tu peux me préparer le dossier des sources ? Et fais-le en une seule commande avec le chemin complet, je vais le mettre dans la doc d'installation."},
             "desc": "Le dossier <code>/home/etudiant/projets/boutique/src</code>, créé avec un <strong>chemin absolu</strong> en une commande.",
             "hints": ["Une option de <code>mkdir</code> crée les dossiers parents manquants : cherchez-la dans <code>man mkdir</code>."],
             "checks": [
                 ('test -d $H/projets/boutique/src', "Le dossier ~/projets/boutique/src n'existe pas."),
             ]},
            {"id": "2.2", "points": 3, "title": "Question piège",
             "ticket": {"from": "lea", "body": "Petit test, comme en entretien d'embauche 😉 : quelle option de <code>ls</code> trie les fichiers <strong>par taille</strong> ? Interdit de chercher sur Internet, la réponse est dans le manuel."},
             "desc": "L'option (ex. <code>-x</code>) dans <code>~/reponse-man.txt</code>.",
             "hints": ["Dans <code>man ls</code>, tapez <code>/size</code> puis <kbd>n</kbd> pour parcourir les résultats.", "C'est une lettre majuscule."],
             "checks": [
                 ('a=$(ans $H/reponse-man.txt); [ "$a" = "-S" ] || [ "$a" = "S" ] || [ "$a" = "--sort=size" ]', "Ce n'est pas la bonne option (ou le fichier est absent)."),
             ]},
            {"id": "2.3", "points": 4, "title": "Le stagiaire est perdu",
             "ticket": {"from": "julien", "body": "Bonjour, désolé de déranger… Je suis dans <code>~/partage-marc/clients/2024/devis</code> et je dois ouvrir <code>tarifs.txt</code>, qui est dans le dossier <code>clients</code>. Mais je ne sais pas quel chemin taper sans repartir de la racine. Tu peux m'aider ?"},
             "desc": "Le <strong>chemin relatif</strong> vers <code>tarifs.txt</code> depuis <code>devis</code>, dans <code>~/chemin-relatif.txt</code>. Testez-le avec <code>cd ~/partage-marc/clients/2024/devis &amp;&amp; cat &lt;votre chemin&gt;</code>.",
             "hints": ["Chaque <code>..</code> remonte d'un dossier.", "De <code>devis</code>, il faut remonter deux fois pour arriver dans <code>clients</code>."],
             "checks": [
                 ('a=$(ans $H/chemin-relatif.txt); a=${a#./}; [ "$a" = "../../tarifs.txt" ]', "Ce chemin ne mène pas à tarifs.txt depuis le dossier devis (et il doit être relatif)."),
             ]},
            {"id": "2.4", "points": 3, "title": "Le script mystérieux de Marc",
             "ticket": {"from": "julien", "body": "Encore moi ! Un vieux script de Marc utilise le chemin <code>~/partage-marc/clients/2024/../..</code>. Je n'y comprends rien : il désigne quel dossier, en vrai ?"},
             "desc": "Le <strong>chemin absolu</strong> de ce dossier (sans <code>~</code>) dans <code>~/chemin-absolu.txt</code>.",
             "hints": ["Rendez-vous dans ce dossier avec <code>cd</code>, puis affichez où vous êtes avec <code>pwd</code>."],
             "checks": [
                 ('a=$(ans $H/chemin-absolu.txt); a=${a%/}; [ "$a" = "/home/etudiant/partage-marc" ]', "Ce n'est pas le bon chemin absolu (il doit commencer par /)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Jour 3 — Ranger l'héritage de Marc",
        "description": "Écrire, copier, renommer, supprimer sans casse. Compétences : > et >>, cp, mv, rm, jokers.",
        "lesson": """<h3>Écrire dans un fichier</h3><table class="lesson-table"><tr><th>Symbole</th><th>Effet</th><th>Exemple</th></tr><tr><td><code>&gt;</code></td><td><strong>Remplace</strong> le contenu</td><td><code>echo "Bonjour" &gt; f.txt</code></td></tr><tr><td><code>&gt;&gt;</code></td><td><strong>Ajoute</strong> à la fin</td><td><code>echo "Suite" &gt;&gt; f.txt</code></td></tr></table><p><code>cat fichier</code> affiche le contenu ; <code>wc -l fichier</code> compte ses lignes.</p><h3>Copier, déplacer, supprimer</h3><table class="lesson-table"><tr><th>Commande</th><th>Action</th><th>Note</th></tr><tr><td><code>cp src dest</code></td><td>Copier</td><td><code>-r</code> pour un dossier</td></tr><tr><td><code>mv src dest</code></td><td>Déplacer / renommer</td><td></td></tr><tr><td><code>rm fichier</code></td><td>Supprimer un fichier</td><td>Pas de corbeille !</td></tr><tr><td><code>rm -r dossier</code></td><td>Supprimer un dossier</td><td>Irréversible</td></tr></table><h3>Les jokers (globbing)</h3><ul><li><code>*</code> — n'importe quelle suite de caractères : <code>rm *.tmp</code></li><li><code>?</code> — un seul caractère : <code>ls fichier?.txt</code></li></ul><div class="tip">Avant un <code>rm</code> avec joker, testez le motif avec <code>ls</code> : <code>ls *.tmp</code>.</div>""",
        "setup": r'''
B=$H/bureau-marc
rm -rf $B; mkdir -p $B/vieux-projets/site-2019
for f in export brouillon sauvegarde cache; do echo "temporaire" > $B/$f.tmp; done
echo "Contrat de maintenance serveurs 2025-2027 - NE PAS SUPPRIMER" > $B/contrat-maintenance.txt
echo "<h1>Maquette 2019</h1>" > $B/vieux-projets/site-2019/index.html
own $B
''',
        "exercises": [
            {"id": "3.1", "points": 3, "title": "Classer la documentation",
             "ticket": {"from": "sophie", "body": "On va enfin avoir une vraie documentation. Dans tes documents, prépare un dossier pour les procédures et un autre pour les comptes rendus de réunion."},
             "desc": "Les dossiers <code>~/documents/procedures/</code> et <code>~/documents/comptes-rendus/</code>.",
             "hints": ["<code>mkdir -p</code> crée les parents manquants et accepte plusieurs chemins."],
             "checks": [
                 ('test -d $H/documents/procedures && test -d $H/documents/comptes-rendus', "Les deux dossiers doivent exister."),
             ]},
            {"id": "3.2", "points": 3, "title": "Première procédure",
             "ticket": {"from": "sophie", "body": "Première procédure à rédiger : l'arrivée d'un nouveau salarié. Commence par le titre, je veux exactement celui-ci : « Procédure arrivée nouveau salarié »."},
             "desc": "La <strong>première ligne</strong> de <code>~/documents/procedures/arrivee.txt</code> est exactement <code>Procédure arrivée nouveau salarié</code>.",
             "hints": ["<code>echo \"...\" &gt; fichier</code>"],
             "checks": [
                 ('test -f $H/documents/procedures/arrivee.txt', "Le fichier ~/documents/procedures/arrivee.txt n'existe pas."),
                 ('[ "$(head -n1 $H/documents/procedures/arrivee.txt)" = "Procédure arrivée nouveau salarié" ]', "La première ligne n'est pas exactement « Procédure arrivée nouveau salarié » (attention aux accents)."),
             ]},
            {"id": "3.3", "points": 3, "title": "Première étape",
             "ticket": {"from": "sophie", "body": "Ajoute la première étape sous le titre : « 1. Créer le compte utilisateur ». Et attention à ne pas écraser le titre, la dernière fois quelqu'un a perdu toute une procédure comme ça…"},
             "desc": "<code>arrivee.txt</code> contient exactement 2 lignes, la 2<sup>e</sup> étant <code>1. Créer le compte utilisateur</code>.",
             "hints": ["<code>&gt;</code> remplace, <code>&gt;&gt;</code> ajoute."],
             "checks": [
                 ('[ "$(sed -n 2p $H/documents/procedures/arrivee.txt)" = "1. Créer le compte utilisateur" ]', "La 2e ligne n'est pas « 1. Créer le compte utilisateur »."),
                 ('[ "$(wc -l < $H/documents/procedures/arrivee.txt)" -eq 2 ]', "Le fichier doit contenir exactement 2 lignes."),
             ]},
            {"id": "3.4", "points": 3, "title": "Copie pour relecture",
             "ticket": {"from": "sophie", "body": "Je relirai ta procédure ce soir. Dépose-m'en une copie dans les comptes rendus, sous le nom <code>arrivee-a-relire.txt</code>, et garde l'original là où il est."},
             "desc": "<code>~/documents/comptes-rendus/arrivee-a-relire.txt</code>, copie identique de <code>arrivee.txt</code> (qui reste en place).",
             "hints": ["<code>cp</code> accepte un nom de destination différent : <code>cp source dossier/nouveau-nom</code>."],
             "checks": [
                 ('test -f $H/documents/procedures/arrivee.txt', "L'original ~/documents/procedures/arrivee.txt a disparu : il fallait copier, pas déplacer."),
                 ('cmp -s $H/documents/procedures/arrivee.txt $H/documents/comptes-rendus/arrivee-a-relire.txt', "La copie est absente ou différente de l'original (refaites-la après l'ajout de la 2e ligne)."),
             ]},
            {"id": "3.5", "points": 4, "title": "Le bureau de Marc",
             "ticket": {"from": "sophie", "body": "Le dossier <code>~/bureau-marc</code> est un vrai bazar. Supprime tous les fichiers temporaires <code>.tmp</code> et le dossier <code>vieux-projets</code>. Par contre, <strong>surtout</strong> ne touche pas au contrat de maintenance, c'est le seul exemplaire !"},
             "desc": "Plus aucun <code>.tmp</code> ni <code>vieux-projets</code> dans <code>~/bureau-marc</code> ; <code>contrat-maintenance.txt</code> intact.",
             "hints": ["Le joker <code>*.tmp</code> désigne tous les fichiers qui finissent par .tmp. Testez d'abord avec <code>ls</code>.", "<code>rm -r</code> supprime un dossier non vide."],
             "checks": [
                 ('test -f $H/bureau-marc/contrat-maintenance.txt', "Le contrat de maintenance a été supprimé ! (bouton « Réinitialiser les fichiers de cette étape » pour recommencer)"),
                 ('! ls $H/bureau-marc/*.tmp', "Il reste des fichiers .tmp dans ~/bureau-marc."),
                 ('test ! -e $H/bureau-marc/vieux-projets', "Le dossier ~/bureau-marc/vieux-projets existe toujours."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Jour 4 — Sauvegardes et raccourcis",
        "description": "Comprendre ce qu'est vraiment un fichier. Compétences : inodes, liens durs, liens symboliques, liens cassés.",
        "lesson": """<h3>Le concept d'inode</h3><p>Chaque fichier est décrit par un <strong>inode</strong> (numéro unique). Un nom de fichier n'est qu'une étiquette qui pointe vers un inode.</p><pre>ls -i fichier.txt    # numéro d'inode<br>ls -l fichier.txt    # 2e colonne = nombre de liens durs</pre><h3>Lien dur</h3><pre>ln fichier.txt lien-dur.txt</pre><ul><li>Seconde étiquette vers le <strong>même inode</strong></li><li>Impossible vers un dossier ou une autre partition</li><li>Les données disparaissent quand le <em>dernier</em> lien est supprimé</li></ul><h3>Lien symbolique</h3><pre>ln -s /cible lien-sym</pre><ul><li>Fichier spécial qui contient un <strong>chemin</strong></li><li>Peut pointer vers un dossier, traverser les partitions</li><li><strong>Cassé</strong> si la cible disparaît</li></ul><pre>lrwxrwxrwx 1 etudiant etudiant 10 lien -&gt; /etc/hosts</pre><h3>Outils</h3><ul><li><code>readlink lien</code> — affiche la cible</li><li><code>find . -samefile f</code> — trouve tous les liens durs de <code>f</code></li><li><code>find . -xtype l</code> — trouve les liens symboliques cassés</li><li><code>ln -sfn nouvelle-cible lien</code> — remplace la cible d'un lien existant</li></ul>""",
        "setup": r'''
S=/opt/sauvegardes
rm -rf $S; mkdir -p $S/lundi $S/mardi/exports $S/mercredi
head -c 2048 /dev/urandom > $S/base-clients.db
dirs=(lundi lundi mardi/exports mercredi lundi mardi/exports)
n=$((RANDOM % 4 + 2))
for i in $(seq 1 $n); do ln $S/base-clients.db $S/${dirs[$i]}/export-$i.db; done
cp $S/base-clients.db $S/mercredi/base-clients-copie.db
chmod -R a+rX $S
emit NLINKS $((n + 1))
R=$H/raccourcis-marc
rm -rf $R; mkdir -p $R; cd $R
touch procedures.txt annuaire.txt planning.txt
targets=(procedures.txt annuaire.txt planning.txt)
names=(compta rh ventes direction)
broken=${names[RANDOM % 4]}
for nm in "${names[@]}"; do
  if [ "$nm" = "$broken" ]; then ln -s /mnt/ancien-nas/$nm "$nm"; else ln -s "${targets[RANDOM % 3]}" "$nm"; fi
done
chown -hR etudiant:etudiant $R
emit BROKEN "$broken"
''',
        "exercises": [
            {"id": "4.1", "points": 3, "title": "Une grille, deux noms",
             "ticket": {"from": "diallo", "body": "Bonjour, Aminata Diallo, comptabilité. Mon tableur ouvre toujours <code>tarifs-courant.csv</code>, mais le fichier officiel s'appelle <code>tarifs-2025.csv</code>. Je ne veux pas de copie : la dernière fois, les deux versions avaient divergé et on a facturé les mauvais prix. Les deux noms doivent désigner <strong>le même fichier</strong>."},
             "desc": "<code>~/tarifs-2025.csv</code> contenant <code>produit;prix</code>, et un <strong>lien dur</strong> <code>~/tarifs-courant.csv</code> vers lui.",
             "hints": ["<code>ln cible nom-du-lien</code> (sans <code>-s</code>)."],
             "checks": [
                 ('grep -q "produit;prix" $H/tarifs-2025.csv', "~/tarifs-2025.csv n'existe pas ou ne contient pas « produit;prix »."),
                 ('test ! -L $H/tarifs-courant.csv && [ "$(stat -c %i $H/tarifs-2025.csv)" = "$(stat -c %i $H/tarifs-courant.csv)" ]', "~/tarifs-courant.csv n'est pas un lien dur vers tarifs-2025.csv (inodes différents ou lien symbolique)."),
             ]},
            {"id": "4.2", "points": 4, "title": "Combien de sauvegardes, vraiment ?",
             "ticket": {"from": "lea", "body": "Le script de sauvegarde de Marc crée des exports de <code>/opt/sauvegardes/base-clients.db</code> un peu partout. Je le soupçonne de faire des liens durs au lieu de vraies copies : si c'est le cas, on croit avoir plusieurs sauvegardes mais on n'en a qu'une ! Combien de noms désignent le même inode que <code>base-clients.db</code>, lui compris ?"},
             "desc": "Le nombre de liens durs dans <code>~/nb-liens.txt</code>. Une copie n'est pas un lien !",
             "hints": ["La 2e colonne de <code>ls -l</code> donne le nombre de liens durs.", "<code>find /opt/sauvegardes -samefile /opt/sauvegardes/base-clients.db</code> les liste tous."],
             "checks": [
                 ('[ "$(ans $H/nb-liens.txt)" = "$LAB_NLINKS" ]', "Ce n'est pas le bon nombre de liens durs."),
             ]},
            {"id": "4.3", "points": 3, "title": "Raccourci vers la configuration",
             "ticket": {"from": "thomas", "body": "Je passe mon temps dans <code>/etc</code>. Tu peux me faire un raccourci <code>conf-systeme</code> dans ton dossier personnel pour que je le montre aux autres devs ?"},
             "desc": "Un lien symbolique <code>~/conf-systeme</code> pointant vers <code>/etc</code>.",
             "hints": ["<code>ln -s cible nom-du-lien</code>"],
             "checks": [
                 ('test -L $H/conf-systeme', "~/conf-systeme n'existe pas ou n'est pas un lien symbolique."),
                 ('[ "$(readlink -f $H/conf-systeme)" = /etc ]', "~/conf-systeme ne pointe pas vers /etc."),
             ]},
            {"id": "4.4", "points": 3, "title": "Le raccourci qui ne mène nulle part",
             "ticket": {"from": "julien", "body": "Dans <code>~/raccourcis-marc</code>, il y a un raccourci par service. L'un d'eux me donne « No such file or directory ». Je crois qu'il pointe vers l'ancien NAS, qui a été débranché. Lequel c'est ?"},
             "desc": "Le nom du lien cassé dans <code>~/lien-casse.txt</code>.",
             "hints": ["<code>ls -l ~/raccourcis-marc</code> : regardez la cible de chaque lien.", "<code>find ~/raccourcis-marc -xtype l</code>"],
             "checks": [
                 ('[ "$(basename "$(ans $H/lien-casse.txt)")" = "$LAB_BROKEN" ]', "Ce n'est pas le lien cassé."),
             ]},
            {"id": "4.5", "points": 3, "title": "Réparer le raccourci",
             "ticket": {"from": "julien", "body": "Merci ! Sophie dit qu'en attendant le nouveau NAS, ce service doit simplement pointer vers l'annuaire. Tu peux réparer le raccourci, en gardant son nom ?"},
             "desc": "Le lien cassé garde son nom et pointe vers <code>annuaire.txt</code>.",
             "hints": ["<code>ln -sfn</code> remplace un lien existant."],
             "checks": [
                 ('test -L "$H/raccourcis-marc/$LAB_BROKEN"', "Le lien a disparu ou n'est plus un lien symbolique."),
                 ('[ "$(readlink -f "$H/raccourcis-marc/$LAB_BROKEN")" = "$H/raccourcis-marc/annuaire.txt" ]', "Le lien ne pointe pas vers annuaire.txt."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Jour 5 — Enquête dans les archives",
        "description": "Retrouver une information parmi des centaines de fichiers. Compétences : find, grep, wc.",
        "lesson": """<h3>Chercher des fichiers : find</h3><pre>find &lt;où&gt; &lt;critères&gt;</pre><ul><li><code>find /etc -name "*.conf"</code> — par nom (<code>-iname</code> : insensible à la casse)</li><li><code>find /var -type d</code> — dossiers uniquement (<code>-type f</code> : fichiers)</li><li><code>find / -size +5M</code> — plus de 5 Mo</li><li><code>find . -mtime -1</code> — modifiés depuis moins d'un jour</li></ul><h3>Chercher du contenu : grep</h3><ul><li><code>grep "root" /etc/passwd</code></li><li><code>grep -r "TODO" /srv</code> — récursif ; <code>-l</code> : n'affiche que les noms de fichiers</li><li><code>grep -i</code> — insensible à la casse ; <code>-c</code> — compte les lignes ; <code>-n</code> — numéros</li></ul><h3>Compter : wc</h3><p><code>wc -l</code> lignes · <code>wc -w</code> mots · <code>wc -c</code> octets. Combiné avec un pipe : <code>find ... | wc -l</code>.</p><div class="tip">Les erreurs « Permission denied » polluent l'affichage ? Ajoutez <code>2&gt;/dev/null</code>.</div>""",
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
bon=$A/${depts[RANDOM % 5]}/$((2022 + RANDOM % 3))/reclamation-$RANDOM.txt
echo "Réclamation client - geste commercial accordé" > $bon; echo "BON-$(rword)" >> $bon
emit BON_FILE "$bon"
big=$A/${depts[RANDOM % 5]}/2023/sauvegarde-$RANDOM.dat
head -c 6M /dev/zero > $big
emit BIG "$big"
words=(Erreur ERREUR erreur info ok succès avertissement)
for i in $(seq 1 60); do echo "facture $i : ${words[RANDOM % 7]} lors du traitement"; done > $A/rapport.txt
emit NERR "$(grep -ci erreur $A/rapport.txt)"
emit NLOG "$(find $A -name '*.log' | wc -l)"
chmod -R a+rX $A
''',
        "exercises": [
            {"id": "5.1", "points": 3, "title": "Préparer l'audit",
             "ticket": {"from": "lea", "body": "Un auditeur passe la semaine prochaine. Il veut la liste de tous les fichiers de configuration <code>.conf</code> sous <code>/etc</code>, avec leur chemin complet."},
             "desc": "La liste produite par <code>find</code> dans <code>~/audit-conf.txt</code>, chemins complets (comme les affiche <code>find /etc ...</code>).",
             "hints": ["<code>find /etc -name \"*.conf\"</code>", "Redirigez la sortie avec <code>&gt;</code> et les erreurs vers <code>/dev/null</code>."],
             "checks": [
                 ('test -s $H/audit-conf.txt', "~/audit-conf.txt est absent ou vide."),
                 ('''setcmp $H/audit-conf.txt "run_as etudiant \\"find /etc -name '*.conf' 2>/dev/null\\""''', "La liste ne correspond pas au résultat attendu (fichiers manquants ou en trop)."),
             ]},
            {"id": "5.2", "points": 4, "title": "Le bon de réduction",
             "ticket": {"from": "sophie", "body": "Un client affirme avoir reçu un bon de réduction et le service client ne retrouve pas le dossier. Le code commence par <code>BON-</code> et il est forcément quelque part dans <code>/srv/archives</code>. Il me faut le fichier exact."},
             "desc": "Le <strong>chemin complet</strong> du fichier qui contient le bon, dans <code>~/bon-reduction.txt</code>.",
             "hints": ["<code>grep -r</code> cherche dans tout un dossier.", "L'option <code>-l</code> de grep n'affiche que le nom des fichiers trouvés."],
             "checks": [
                 ('[ "$(ans $H/bon-reduction.txt)" = "$LAB_BON_FILE" ]', "Ce n'est pas le bon fichier (indiquez le chemin complet, commençant par /srv)."),
             ]},
            {"id": "5.3", "points": 3, "title": "Estimer le ménage",
             "ticket": {"from": "lea", "body": "Avant de faire le ménage dans les archives, j'aimerais savoir combien de journaux <code>.log</code> traînent sous <code>/srv/archives</code>, sous-dossiers compris."},
             "desc": "Le nombre dans <code>~/nb-logs.txt</code>.",
             "hints": ["<code>find ... | wc -l</code>"],
             "checks": [
                 ('[ "$(ans $H/nb-logs.txt)" = "$LAB_NLOG" ]', "Ce n'est pas le bon nombre."),
             ]},
            {"id": "5.4", "points": 3, "title": "Le fichier qui pèse lourd",
             "ticket": {"from": "sophie", "body": "L'espace disque des archives a explosé cette nuit. Un seul fichier dépasse 5 Mo : trouve-le-moi, je veux savoir qui l'a mis là."},
             "desc": "Son chemin complet dans <code>~/gros-fichier.txt</code>.",
             "hints": ["Regardez l'option <code>-size</code> dans <code>man find</code>."],
             "checks": [
                 ('[ "$(ans $H/gros-fichier.txt)" = "$LAB_BIG" ]', "Ce n'est pas le bon fichier."),
             ]},
            {"id": "5.5", "points": 3, "title": "Les erreurs de facturation",
             "ticket": {"from": "diallo", "body": "Le logiciel de facturation a produit <code>/srv/archives/rapport.txt</code>. J'ai besoin du nombre de lignes qui signalent une erreur. Attention, le logiciel écrit « Erreur », « ERREUR » ou « erreur » selon son humeur…"},
             "desc": "Le nombre de lignes contenant <em>erreur</em>, quelle que soit la casse, dans <code>~/nb-erreurs.txt</code>.",
             "hints": ["<code>grep</code> a une option pour ignorer la casse et une autre pour compter."],
             "checks": [
                 ('[ "$(ans $H/nb-erreurs.txt)" = "$LAB_NERR" ]', "Ce n'est pas le bon nombre (pensez à Erreur, ERREUR et erreur)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Redirections et pipes",
        "description": "Séparez sortie et erreurs, combinez les commandes avec les pipes.",
        "lesson": """<h3>Les trois flux</h3><table class="lesson-table"><tr><th>Flux</th><th>N°</th><th>Redirection</th></tr><tr><td>Entrée standard (stdin)</td><td>0</td><td><code>&lt; fichier</code></td></tr><tr><td>Sortie standard (stdout)</td><td>1</td><td><code>&gt; f</code>, <code>&gt;&gt; f</code></td></tr><tr><td>Erreurs (stderr)</td><td>2</td><td><code>2&gt; f</code>, <code>2&gt;&gt; f</code></td></tr></table><ul><li><code>2&gt;/dev/null</code> — jeter les erreurs</li><li><code>&gt; f 2&gt;&amp;1</code> — tout dans le même fichier</li></ul><h3>Le pipe |</h3><p>Branche la sortie d'une commande sur l'entrée de la suivante :</p><pre>cut -d: -f1 /etc/passwd | sort | head -5</pre><h3>tee</h3><p>Écrit dans un fichier <em>et</em> affiche : <code>ls | tee liste.txt</code></p><h3>Outils utiles</h3><ul><li><code>sort</code> (<code>-u</code> : sans doublons, <code>-n</code> : numérique, <code>-r</code> : inverse)</li><li><code>uniq</code>, <code>head</code>, <code>tail</code>, <code>cut</code>, <code>wc</code></li></ul>""",
        "setup": r'''
cat > /usr/local/bin/bavard <<'EOF'
#!/bin/bash
for i in 1 2 3 4 5; do echo "OK ligne $i"; done
for i in 1 2 3; do echo "ERR problème $i" >&2; done
EOF
chmod 755 /usr/local/bin/bavard
''',
        "exercises": [
            {"id": "6.1", "points": 3, "title": "Compter avec un pipe",
             "desc": "Combien d'entrées (fichiers et dossiers) affiche <code>ls /etc</code> ? Écrivez le nombre dans <code>~/nb-etc.txt</code> en une seule ligne de commande.",
             "hints": ["<code>ls /etc | wc -l</code>, puis redirigez."],
             "checks": [
                 ('[ "$(ans $H/nb-etc.txt)" = "$(ls /etc | wc -l)" ]', "Ce n'est pas le bon nombre."),
             ]},
            {"id": "6.2", "points": 3, "title": "Séparer les erreurs",
             "desc": "Lancez <code>find /root</code> (sans sudo) en envoyant la sortie normale dans <code>~/find-ok.txt</code> et les erreurs dans <code>~/erreurs.txt</code>.",
             "hints": ["<code>&gt;</code> pour stdout, <code>2&gt;</code> pour stderr, dans la même commande."],
             "checks": [
                 ('grep -qi "permission denied" $H/erreurs.txt', "~/erreurs.txt ne contient pas le message d'erreur de find."),
                 ('test -f $H/find-ok.txt && ! grep -qi "permission denied" $H/find-ok.txt', "~/find-ok.txt est absent ou contient des erreurs."),
             ]},
            {"id": "6.3", "points": 4, "title": "Le programme bavard",
             "desc": "La commande <code>bavard</code> écrit sur les deux flux. Envoyez sa sortie standard dans <code>~/sortie.txt</code> et ses erreurs dans <code>~/erreurs-bavard.txt</code>.",
             "hints": ["Même principe que l'exercice précédent."],
             "checks": [
                 ('[ "$(grep -c "^OK" $H/sortie.txt)" -eq 5 ] && ! grep -q "^ERR" $H/sortie.txt', "~/sortie.txt doit contenir les 5 lignes OK et aucune ligne ERR."),
                 ('[ "$(grep -c "^ERR" $H/erreurs-bavard.txt)" -eq 3 ] && ! grep -q "^OK" $H/erreurs-bavard.txt', "~/erreurs-bavard.txt doit contenir les 3 lignes ERR et aucune ligne OK."),
             ]},
            {"id": "6.4", "points": 3, "title": "Afficher et sauvegarder avec tee",
             "desc": "Avec <code>tee</code>, sauvegardez le résultat de <code>ls /usr/bin</code> dans <code>~/programmes.txt</code> tout en l'affichant.",
             "hints": ["<code>commande | tee fichier</code>"],
             "checks": [
                 ('test -f $H/programmes.txt && grep -qx bash $H/programmes.txt && [ "$(wc -l < $H/programmes.txt)" -gt 100 ]', "~/programmes.txt ne contient pas la liste de /usr/bin (un nom par ligne)."),
             ]},
            {"id": "6.5", "points": 4, "title": "Utilisateurs triés",
             "desc": "Extrayez les noms d'utilisateurs de <code>/etc/passwd</code> (1<sup>er</sup> champ), triés par ordre alphabétique et sans doublon, dans <code>~/users-sorted.txt</code>.",
             "hints": ["<code>cut -d: -f1</code> extrait le premier champ.", "<code>sort -u</code> trie et supprime les doublons."],
             "checks": [
                 ('linecmp $H/users-sorted.txt "cut -d: -f1 /etc/passwd | sort -u"', "Le contenu ne correspond pas à la liste triée des utilisateurs."),
             ]},
            {"id": "6.6", "points": 3, "title": "Silence les erreurs !",
             "desc": "Combien de <strong>fichiers</strong> (pas de dossiers) pouvez-vous voir sous <code>/etc</code>, sans sudo ? Écrivez le nombre dans <code>~/nb-fichiers-etc.txt</code>, sans qu'aucune erreur ne s'affiche à l'écran.",
             "hints": ["<code>find /etc -type f</code>, erreurs vers <code>/dev/null</code>, puis <code>wc -l</code>."],
             "checks": [
                 ('[ "$(ans $H/nb-fichiers-etc.txt)" = "$(run_as etudiant "find /etc -type f 2>/dev/null | wc -l")" ]', "Ce n'est pas le bon nombre (n'utilisez pas sudo)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    7: {
        "title": "Édition de texte en terminal",
        "description": "Modifiez des fichiers avec nano, vim et sed.",
        "lesson": """<h3>nano — l'éditeur simple</h3><p><code>nano fichier</code> · <kbd>Ctrl+O</kbd> enregistrer · <kbd>Ctrl+X</kbd> quitter · <kbd>Ctrl+W</kbd> rechercher · <kbd>Ctrl+K</kbd> couper une ligne.</p><h3>vim — l'éditeur puissant</h3><p>Trois modes : <strong>normal</strong> (défaut), <strong>insertion</strong> (<kbd>i</kbd>), <strong>commande</strong> (<kbd>:</kbd>).</p><ul><li><kbd>i</kbd> insérer · <kbd>Echap</kbd> revenir en mode normal</li><li><kbd>dd</kbd> supprimer la ligne · <kbd>G</kbd> aller à la fin · <kbd>o</kbd> nouvelle ligne en dessous</li><li><code>:w</code> enregistrer · <code>:q</code> quitter · <code>:wq</code> les deux · <code>:q!</code> quitter sans enregistrer</li></ul><div class="tip">Perdu dans vim ? <kbd>Echap</kbd> puis <code>:q!</code></div><h3>sed — l'éditeur de flux</h3><pre>sed 's/ancien/nouveau/' f       # 1re occurrence de chaque ligne<br>sed 's/ancien/nouveau/g' f      # toutes les occurrences<br>sed -i 's/ancien/nouveau/g' f   # modifie le fichier directement</pre>""",
        "setup": r'''
mkdir -p $H/config
n=$((RANDOM % 4 + 3))
{
  echo "# Configuration de l'application"
  for i in $(seq 1 $n); do echo "backend_$i=ancien-serveur:$((8000 + i))"; done
  echo "timeout=30"
  echo "log=/var/log/ancien-serveur.log"
} > $H/config/app.conf
emit NOLD $((n + 1))
cat > $H/config/poeme.txt <<'EOF'
Il pleure dans mon coeur
Comme il pleut sur la ville
INTRUS : cette ligne n'a rien à faire ici
Quelle est cette langueur
Qui pénètre mon coeur ?
EOF
own $H/config
''',
        "exercises": [
            {"id": "7.1", "points": 3, "title": "Éditer avec nano",
             "desc": "Avec <code>nano</code>, créez <code>~/config.txt</code> contenant exactement ces 3 lignes :<br><code>serveur=localhost</code><br><code>port=8080</code><br><code>debug=false</code>",
             "hints": ["<code>nano ~/config.txt</code>, tapez les lignes, <kbd>Ctrl+O</kbd>, <kbd>Entrée</kbd>, <kbd>Ctrl+X</kbd>."],
             "checks": [
                 ('[ "$(wc -l < $H/config.txt)" -eq 3 ]', "~/config.txt est absent ou ne fait pas exactement 3 lignes."),
                 ('[ "$(sed -n 1p $H/config.txt)" = serveur=localhost ] && [ "$(sed -n 2p $H/config.txt)" = port=8080 ] && sed -n 3p $H/config.txt | grep -qxE "debug=(false|true)"', "Le contenu ne correspond pas aux 3 lignes demandées (attention aux espaces)."),
             ]},
            {"id": "7.2", "points": 4, "title": "Éditer avec vim",
             "desc": "Avec <code>vim</code>, dans <code>~/config/poeme.txt</code> : supprimez la ligne qui contient <code>INTRUS</code> et ajoutez une dernière ligne <code>Fin</code>.",
             "hints": ["Placez le curseur sur la ligne, tapez <kbd>dd</kbd>.", "<kbd>G</kbd> puis <kbd>o</kbd> pour écrire sous la dernière ligne, <kbd>Echap</kbd> puis <code>:wq</code>."],
             "checks": [
                 ('! grep -q INTRUS $H/config/poeme.txt', "La ligne INTRUS est toujours là."),
                 ('[ "$(tail -n1 $H/config/poeme.txt)" = Fin ]', "La dernière ligne n'est pas « Fin »."),
                 ('[ "$(wc -l < $H/config/poeme.txt)" -eq 5 ] && [ "$(head -n1 $H/config/poeme.txt)" = "Il pleure dans mon coeur" ]', "Le reste du poème a été modifié : seules la ligne INTRUS et la ligne Fin devaient changer."),
             ]},
            {"id": "7.3", "points": 3, "title": "Remplacer avec sed",
             "desc": "Avec <code>sed -i</code>, remplacez <code>debug=false</code> par <code>debug=true</code> dans <code>~/config.txt</code> sans toucher aux autres lignes.",
             "hints": ["<code>sed -i 's/ancien/nouveau/' fichier</code>"],
             "checks": [
                 ('grep -qx debug=true $H/config.txt', "La ligne debug=true est absente."),
                 ('grep -qx serveur=localhost $H/config.txt && grep -qx port=8080 $H/config.txt && [ "$(wc -l < $H/config.txt)" -eq 3 ]', "Les autres lignes ont été modifiées."),
             ]},
            {"id": "7.4", "points": 4, "title": "Remplacement global",
             "desc": "Dans <code>~/config/app.conf</code>, remplacez <strong>toutes</strong> les occurrences de <code>ancien-serveur</code> par <code>nouveau-serveur</code>.",
             "hints": ["Le drapeau <code>g</code> à la fin de l'expression <code>s///</code> remplace toutes les occurrences."],
             "checks": [
                 ('! grep -q ancien-serveur $H/config/app.conf', "Il reste des occurrences de ancien-serveur."),
                 ('[ "$(grep -o nouveau-serveur $H/config/app.conf | wc -l)" -eq "$LAB_NOLD" ] && grep -qx timeout=30 $H/config/app.conf', "Le fichier a été abîmé : il manque des lignes."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Expressions régulières",
        "description": "Décrivez précisément ce que vous cherchez avec les regex.",
        "lesson": """<h3>Syntaxe de base</h3><table class="lesson-table"><tr><th>Motif</th><th>Signification</th></tr><tr><td><code>.</code></td><td>N'importe quel caractère</td></tr><tr><td><code>^</code> / <code>$</code></td><td>Début / fin de ligne</td></tr><tr><td><code>*</code></td><td>0 fois ou plus le précédent</td></tr><tr><td><code>+</code> / <code>?</code></td><td>1 fois ou plus / 0 ou 1 fois (avec <code>grep -E</code>)</td></tr><tr><td><code>{2}</code>, <code>{2,}</code></td><td>Exactement 2 / au moins 2 fois (avec <code>-E</code>)</td></tr><tr><td><code>[abc]</code> / <code>[^abc]</code></td><td>Un caractère parmi / hors de la liste</td></tr><tr><td><code>[a-z0-9]</code></td><td>Plages de caractères</td></tr><tr><td><code>\\s</code></td><td>Un espace ou une tabulation</td></tr><tr><td><code>\\.</code></td><td>Un vrai point</td></tr><tr><td><code>(a|b)</code></td><td>a ou b (avec <code>-E</code>)</td></tr></table><h3>Avec grep</h3><pre>grep '^#' f            # lignes de commentaire<br>grep -v '^$' f         # lignes non vides<br>grep -E '^\\s*(#|$)' f  # commentaires (même indentés) ou lignes blanches<br>grep -oE '[0-9]+' f    # -o : n'affiche que la partie qui correspond</pre><h3>Avec sed</h3><pre>sed 's/[0-9]/X/g' f    # chiffres -&gt; X<br>sed '/^$/d' f          # supprime les lignes vides</pre>""",
        "setup": r'''
mkdir -p $H/regex
prenoms=(alice bruno chloe david emma farid gael hugo ines jules)
doms=(exemple.fr societe.com univ-lyon.fr mail.org)
{
  echo "# Carnet de contacts - export du $(date +%d/%m/%Y)"
  for i in $(seq 1 8); do
    echo "Contact $i : ${prenoms[RANDOM % 10]}.$((RANDOM % 90 + 10))@${doms[RANDOM % 4]} - tel 0$((RANDOM % 5 + 1)) $((RANDOM % 90 + 10)) $((RANDOM % 90 + 10)) $((RANDOM % 90 + 10)) $((RANDOM % 90 + 10))"
  done
  echo "Contact 9 : jean@localhost - tel inconnu"
  echo "Contact 10 : @site.com - adresse incomplète"
  echo "Contact 11 : marie.dupont@@exemple.fr - faute de frappe"
  echo "Contact 12 : bob@ - à compléter"
  echo ""
  echo "Fin du carnet (12 contacts)"
} > $H/regex/contacts.txt
grep -oE '[a-z0-9._-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}' $H/regex/contacts.txt | sort -u > $REF/emails.txt
grep -oE '0[1-9]( [0-9]{2}){4}' $H/regex/contacts.txt | sort -u > $REF/telephones.txt
sed 's/[0-9]/X/g' $H/regex/contacts.txt > $REF/censure.txt
printf '%s\n' "# Fichier de configuration du serveur" "# Ne pas modifier sans autorisation" "" "port=8080" "   # port secondaire désactivé" "host=0.0.0.0" "" "workers=4" "    " "	# fin des réglages réseau" "log_level=info" > $H/regex/serveur.conf
grep -vE '^\s*(#|$)' $H/regex/serveur.conf > $REF/serveur-clean.txt
own $H/regex
''',
        "exercises": [
            {"id": "8.1", "points": 3, "title": "Début de ligne",
             "desc": "Extrayez les lignes de <code>/etc/passwd</code> qui commencent par <code>r</code> <strong>ou</strong> par <code>s</code> dans <code>~/regex/rs.txt</code>.",
             "hints": ["<code>^</code> ancre le motif en début de ligne ; <code>[rs]</code> = r ou s."],
             "checks": [
                 ('linecmp $H/regex/rs.txt "grep \'^[rs]\' /etc/passwd"', "Le contenu ne correspond pas (lignes manquantes ou en trop)."),
             ]},
            {"id": "8.2", "points": 5, "title": "Adresses e-mail valides",
             "desc": "<code>~/regex/contacts.txt</code> contient des adresses valides et des pièges. Extrayez <strong>uniquement</strong> les adresses valides (une par ligne) dans <code>~/regex/emails-valides.txt</code>.<br>Adresse valide : caractères <code>[a-z0-9._-]</code>, un seul <code>@</code>, puis un domaine contenant au moins un point et finissant par au moins 2 lettres.",
             "hints": ["<code>grep -oE</code> n'affiche que la partie reconnue par le motif.", "Structure : <code>[a-z0-9._-]+@[a-z0-9.-]+\\.[a-z]{2,}</code>"],
             "checks": [
                 ('test -s $H/regex/emails-valides.txt', "~/regex/emails-valides.txt est absent ou vide."),
                 ('setcmp $H/regex/emails-valides.txt "cat $REF/emails.txt"', "La liste ne correspond pas : il y a des adresses manquantes, des adresses invalides ou du texte en trop."),
             ]},
            {"id": "8.3", "points": 4, "title": "Configuration épurée",
             "desc": "Extrayez de <code>~/regex/serveur.conf</code> les lignes utiles — ni vides (ou blanches), ni commentaires (même précédés d'espaces) — dans <code>~/regex/serveur-clean.txt</code>, en gardant l'ordre.",
             "hints": ["<code>grep -v</code> inverse la sélection.", "<code>^\\s*#</code> reconnaît un commentaire indenté, <code>^\\s*$</code> une ligne blanche."],
             "checks": [
                 ('test -f $H/regex/serveur-clean.txt && diff -q $H/regex/serveur-clean.txt $REF/serveur-clean.txt', "Le résultat n'est pas le bon : vérifiez les commentaires indentés et les lignes ne contenant que des espaces."),
             ]},
            {"id": "8.4", "points": 3, "title": "Censure",
             "desc": "Avec <code>sed</code>, remplacez <strong>tous</strong> les chiffres de <code>~/regex/contacts.txt</code> par <code>X</code> et enregistrez le résultat dans <code>~/regex/censure.txt</code> (sans modifier l'original).",
             "hints": ["<code>sed 's/[0-9]/X/g' source &gt; destination</code>"],
             "checks": [
                 ('test -f $H/regex/censure.txt && ! grep -q "[0-9]" $H/regex/censure.txt', "Il reste des chiffres dans ~/regex/censure.txt (ou le fichier est absent)."),
                 ('diff -q $H/regex/censure.txt $REF/censure.txt', "Le texte a été modifié au-delà des chiffres."),
             ]},
            {"id": "8.5", "points": 4, "title": "Numéros de téléphone",
             "desc": "Extrayez les numéros de téléphone au format <code>0X XX XX XX XX</code> de <code>~/regex/contacts.txt</code> (un par ligne) dans <code>~/regex/telephones.txt</code>.",
             "hints": ["Un zéro, un chiffre de 1 à 9, puis 4 fois « espace + 2 chiffres ».", "<code>0[1-9]( [0-9]{2}){4}</code>"],
             "checks": [
                 ('setcmp $H/regex/telephones.txt "cat $REF/telephones.txt"', "La liste ne correspond pas aux numéros présents dans le carnet."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    9: {
        "title": "Filtrage et traitement de texte",
        "description": "Analysez des données avec sort, uniq, cut, awk et tr.",
        "lesson": """<h3>sort &amp; uniq</h3><pre>sort f                # trier<br>sort f | uniq -c      # compter les lignes identiques (entrée triée !)<br>sort -rn             # tri numérique décroissant</pre><h3>cut</h3><pre>cut -d: -f1 /etc/passwd     # 1er champ, séparateur :</pre><h3>awk</h3><p>awk découpe chaque ligne en champs <code>$1</code>, <code>$2</code>… (séparateur : espaces, ou <code>-F</code>).</p><pre>awk '{print $1}' access.log<br>awk -F: '$3 &gt;= 1000 {print $1, $3}' /etc/passwd<br>awk '$9 == 404' access.log       # filtre sur un champ précis</pre><h3>tr</h3><pre>echo "hello" | tr 'a-z' 'A-Z'</pre><h3>Le « top » classique</h3><pre>awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -3</pre><div class="tip">Format du journal d'accès : <code>IP - - [date] "GET /page HTTP/1.1" CODE TAILLE</code>. Le code HTTP est le 9<sup>e</sup> champ.</div>""",
        "setup": r'''
mkdir -p $H/logs $H/texte
ips=(); for i in $(seq 1 12); do ips+=("10.0.$i.$((RANDOM % 250 + 2))"); done
mapfile -t ord < <(printf '%s\n' "${ips[@]}" | shuf)
c1=$((RANDOM % 10 + 40)); c2=$((c1 - RANDOM % 4 - 3)); c3=$((c2 - RANDOM % 4 - 3))
counts=($c1 $c2 $c3)
for i in $(seq 4 12); do counts+=($((RANDOM % (c3 - 5) + 1))); done
urls=(/ /index.html /contact /produits /api/login /admin /images/logo.png /blog)
codes=(200 200 200 200 301 404 500 403)
tmp=$(mktemp)
for k in $(seq 0 11); do
  for j in $(seq 1 ${counts[$k]}); do
    printf '%s - - [12/Mar/2026:%02d:%02d:%02d +0100] "GET %s HTTP/1.1" %s %d\n' "${ord[$k]}" $((RANDOM % 24)) $((RANDOM % 60)) $((RANDOM % 60)) "${urls[RANDOM % 8]}" "${codes[RANDOM % 8]}" $((RANDOM % 5000 + 200)) >> $tmp
  done
done
shuf $tmp > $H/logs/access.log; rm -f $tmp
emit TOP3 "${ord[0]},${ord[1]},${ord[2]}"
emit N404 "$(awk '$9 == 404' $H/logs/access.log | wc -l)"
printf '%s\n' "le shell est un interprete de commandes" "linux est un systeme libre" "les pipes relient les commandes entre elles" > $H/texte/minuscules.txt
own $H/logs $H/texte
''',
        "exercises": [
            {"id": "9.1", "points": 3, "title": "Compter les shells",
             "desc": "Pour chaque shell de <code>/etc/passwd</code> (7<sup>e</sup> champ), comptez le nombre d'utilisateurs. Sauvegardez le résultat de <code>uniq -c</code>, trié du plus fréquent au moins fréquent, dans <code>~/shells-count.txt</code>.",
             "hints": ["<code>cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn</code>"],
             "checks": [
                 ('setcmp $H/shells-count.txt "cut -d: -f7 /etc/passwd | sort | uniq -c"', "Les comptes ne correspondent pas à /etc/passwd."),
                 ('[ "$(awk \'NF{print $1; exit}\' $H/shells-count.txt)" = "$(cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn | awk \'{print $1; exit}\')" ]', "Le fichier n'est pas trié du plus fréquent au moins fréquent."),
             ]},
            {"id": "9.2", "points": 5, "title": "Top 3 des visiteurs",
             "desc": "Dans <code>~/logs/access.log</code>, quelles sont les 3 adresses IP qui ont fait le plus de requêtes ? Écrivez-les dans <code>~/top-ip.txt</code>, de la plus active à la moins active.",
             "hints": ["L'IP est le premier champ : <code>awk '{print $1}'</code>.", "Puis <code>sort | uniq -c | sort -rn | head -3</code>."],
             "checks": [
                 ('[ "$(grep -oE "([0-9]{1,3}\\.){3}[0-9]{1,3}" $H/top-ip.txt | head -3 | paste -sd,)" = "$LAB_TOP3" ]', "Ce ne sont pas les 3 bonnes IP, ou elles ne sont pas dans le bon ordre."),
             ]},
            {"id": "9.3", "points": 4, "title": "Pages introuvables",
             "desc": "Combien de requêtes de <code>~/logs/access.log</code> ont reçu le code HTTP <code>404</code> ? Écrivez le nombre dans <code>~/nb-404.txt</code>.",
             "hints": ["Attention : « 404 » peut aussi apparaître dans la taille de la réponse (ex. 1404) ! Filtrez sur le bon champ.", "<code>awk '$9 == 404' ~/logs/access.log | wc -l</code>"],
             "checks": [
                 ('[ "$(ans $H/nb-404.txt)" = "$LAB_N404" ]', "Ce n'est pas le bon nombre. Un simple grep 404 compte-t-il trop de lignes ?"),
             ]},
            {"id": "9.4", "points": 4, "title": "Extraire avec awk",
             "desc": "Avec <code>awk</code>, listez les comptes « humains » de <code>/etc/passwd</code> (UID ≥ 1000 et &lt; 65534) sous la forme <code>nom UID</code> (séparés par un espace) dans <code>~/users-uid.txt</code>.",
             "hints": ["<code>-F:</code> choisit le séparateur, <code>$3</code> est l'UID.", "<code>awk -F: '$3 &gt;= 1000 &amp;&amp; $3 &lt; 65534 {print $1, $3}' /etc/passwd</code>"],
             "checks": [
                 ('setcmp $H/users-uid.txt "awk -F: \'\\$3 >= 1000 && \\$3 < 65534 {print \\$1, \\$3}\' /etc/passwd"', "La liste ne correspond pas aux comptes d'UID ≥ 1000."),
             ]},
            {"id": "9.5", "points": 3, "title": "Tout en majuscules",
             "desc": "Avec <code>tr</code>, convertissez <code>~/texte/minuscules.txt</code> en majuscules dans <code>~/texte/majuscules.txt</code>.",
             "hints": ["<code>tr</code> lit l'entrée standard : utilisez <code>&lt;</code> ou un pipe."],
             "checks": [
                 ('test -f $H/texte/majuscules.txt && diff -q $H/texte/majuscules.txt <(tr a-z A-Z < $H/texte/minuscules.txt)', "Le contenu ne correspond pas au texte converti en majuscules."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    10: {
        "title": "Utilisateurs, groupes et permissions",
        "description": "Créez comptes et groupes avec sudo, et contrôlez réellement qui accède à quoi.",
        "lesson": """<h3>sudo</h3><p>Vous êtes <code>etudiant</code>, un utilisateur normal. Les commandes d'administration se lancent avec <code>sudo</code> (mot de passe : <code>etudiant</code>) :</p><pre>sudo useradd -m -s /bin/bash alice</pre><h3>Utilisateurs</h3><table class="lesson-table"><tr><th>Commande</th><th>Action</th></tr><tr><td><code>useradd -m -s /bin/bash u</code></td><td>Créer (avec dossier personnel)</td></tr><tr><td><code>adduser u</code></td><td>Créer, version interactive (Debian/Ubuntu)</td></tr><tr><td><code>userdel -r u</code></td><td>Supprimer avec son dossier</td></tr><tr><td><code>id u</code></td><td>Voir UID et groupes</td></tr></table><h3>Groupes</h3><table class="lesson-table"><tr><th>Commande</th><th>Action</th></tr><tr><td><code>groupadd g</code></td><td>Créer un groupe</td></tr><tr><td><code>usermod -aG g u</code></td><td>Ajouter u au groupe g (<strong>-a</strong> sinon il perd ses autres groupes !)</td></tr></table><h3>Permissions</h3><p>3 triades : <strong>u</strong>tilisateur · <strong>g</strong>roupe · <strong>o</strong>thers. <code>r</code>=4, <code>w</code>=2, <code>x</code>=1.</p><ul><li><code>chmod 750 d</code> — octal ; <code>chmod u+x f</code>, <code>chmod o-rwx d</code> — symbolique</li><li><code>chown user:groupe f</code>, <code>chgrp groupe f</code></li></ul><div class="tip">Sur un <strong>dossier</strong> : <code>r</code> = lister, <code>w</code> = créer/supprimer dedans, <code>x</code> = entrer (<code>cd</code>).</div><h3>Le bit setgid sur un dossier</h3><p><code>chmod g+s dossier</code> (ou <code>2770</code>) : les fichiers créés dedans héritent du <strong>groupe du dossier</strong>. Indispensable pour un dossier partagé.</p><h3>Tester en tant qu'un autre utilisateur</h3><pre>sudo -u bob touch /home/partage/test</pre>""",
        "setup": r'''
mkuser intrus
mkdir -p $H/scripts
printf '#!/bin/bash\necho "Déploiement..."\n' > $H/scripts/deploy.sh
chmod 644 $H/scripts/deploy.sh
own $H/scripts
''',
        "exercises": [
            {"id": "10.1", "points": 3, "title": "Créer des utilisateurs",
             "desc": "Créez les utilisateurs <code>alice</code> et <code>bob</code>, <strong>avec</strong> leur dossier personnel.",
             "hints": ["<code>sudo useradd -m ...</code> : sans <code>-m</code>, pas de dossier personnel."],
             "checks": [
                 ('id alice && id bob', "alice et/ou bob n'existent pas."),
                 ('test -d /home/alice && test -d /home/bob', "Les dossiers personnels /home/alice et /home/bob n'existent pas (option -m de useradd)."),
             ]},
            {"id": "10.2", "points": 3, "title": "Créer un groupe",
             "desc": "Créez le groupe <code>equipe</code> et ajoutez-y <code>alice</code> et <code>bob</code>.",
             "hints": ["<code>sudo groupadd</code> puis <code>sudo usermod -aG</code>."],
             "checks": [
                 ('getent group equipe', "Le groupe equipe n'existe pas."),
                 ('id -nG alice | grep -qw equipe && id -nG bob | grep -qw equipe', "alice et bob doivent tous deux être membres du groupe equipe."),
             ]},
            {"id": "10.3", "points": 4, "title": "Dossier d'équipe",
             "desc": "Créez <code>/home/partage</code>. Les membres d'<code>equipe</code> doivent pouvoir y créer des fichiers ; les autres utilisateurs (comme <code>intrus</code>) ne doivent même pas pouvoir le lister.",
             "hints": ["Changez le groupe du dossier avec <code>chgrp</code>.", "Groupe : rwx, autres : --- → quel code octal ?"],
             "checks": [
                 ('test -d /home/partage', "/home/partage n'existe pas."),
                 ('[ "$(stat -c %G /home/partage)" = equipe ]', "/home/partage n'appartient pas au groupe equipe."),
                 ('run_as bob "touch /home/partage/.t-bob && rm -f /home/partage/.t-bob"', "bob (membre d'equipe) ne peut pas créer de fichier dans /home/partage."),
                 ('! run_as intrus "ls /home/partage"', "L'utilisateur intrus peut lister /home/partage."),
             ]},
            {"id": "10.4", "points": 4, "title": "Fichier confidentiel",
             "desc": "Créez <code>/home/partage/secret.txt</code> appartenant à <code>alice</code> et au groupe <code>equipe</code> : alice peut le modifier, les membres du groupe peuvent seulement le lire, les autres n'ont aucun droit.",
             "hints": ["<code>sudo chown alice:equipe fichier</code>", "rw- r-- --- = ?"],
             "checks": [
                 ('test -f /home/partage/secret.txt', "/home/partage/secret.txt n'existe pas."),
                 ('[ "$(stat -c %U:%G /home/partage/secret.txt)" = alice:equipe ]', "Le fichier doit appartenir à alice et au groupe equipe."),
                 ('run_as alice "test -w /home/partage/secret.txt"', "alice ne peut pas modifier le fichier."),
                 ('run_as bob "cat /home/partage/secret.txt" && ! run_as bob "test -w /home/partage/secret.txt"', "bob doit pouvoir lire le fichier mais pas le modifier."),
                 ('[ "$(others /home/partage/secret.txt)" = "---" ]', "Les autres utilisateurs ont encore des droits sur le fichier."),
             ]},
            {"id": "10.5", "points": 3, "title": "chmod symbolique",
             "desc": "Rendez <code>~/scripts/deploy.sh</code> exécutable <strong>par vous seul</strong>, sans modifier les autres droits. Utilisez la notation symbolique.",
             "hints": ["<code>u</code> = propriétaire, <code>+x</code> = ajouter l'exécution."],
             "checks": [
                 ('[ "$(perm $H/scripts/deploy.sh)" = 744 ]', "Les droits de deploy.sh devraient être rwxr--r-- (744)."),
             ]},
            {"id": "10.6", "points": 4, "title": "Héritage du groupe",
             "desc": "Faites en sorte que tout fichier créé dans <code>/home/partage</code> appartienne automatiquement au groupe <code>equipe</code>, quel que soit son créateur.",
             "hints": ["C'est le rôle du bit <strong>setgid</strong> sur un dossier.", "<code>sudo chmod g+s /home/partage</code>"],
             "checks": [
                 ('test -g /home/partage', "Le bit setgid n'est pas positionné sur /home/partage."),
                 ('run_as alice "touch /home/partage/.t-sgid" && [ "$(stat -c %G /home/partage/.t-sgid)" = equipe ]; r=$?; rm -f /home/partage/.t-sgid; exit $r', "Un fichier créé par alice n'hérite pas du groupe equipe."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    11: {
        "title": "Super-utilisateur et processus",
        "description": "Identifiez, priorisez, signalez et arrêtez des processus.",
        "lesson": """<h3>sudo et su</h3><ul><li><code>sudo commande</code> — exécuter en root (il faut être dans le groupe <code>sudo</code>)</li><li><code>sudo -u alice commande</code> — exécuter en tant qu'alice</li><li><code>sudo -i</code> — ouvrir un shell root (à éviter au quotidien)</li></ul><h3>Observer les processus</h3><pre>ps aux                   # instantané de tous les processus<br>ps -o pid,user,ni,cmd -C sleep<br>pgrep -a nom             # PID + commande<br>top                      # temps réel (q pour quitter)</pre><p>Colonnes utiles de <code>ps aux</code> : <code>USER</code>, <code>PID</code>, <code>%CPU</code>, <code>%MEM</code>, <code>COMMAND</code>.</p><h3>Signaux</h3><table class="lesson-table"><tr><th>Commande</th><th>Signal</th><th>Effet habituel</th></tr><tr><td><code>kill PID</code></td><td>TERM (15)</td><td>Arrêt propre</td></tr><tr><td><code>kill -9 PID</code></td><td>KILL (9)</td><td>Arrêt forcé (dernier recours)</td></tr><tr><td><code>kill -HUP PID</code></td><td>HUP (1)</td><td>Recharger la configuration (services)</td></tr></table><div class="tip">On ne peut envoyer un signal qu'à ses propres processus… sauf avec <code>sudo</code>.</div><h3>Arrière-plan et priorité</h3><ul><li><code>commande &amp;</code> — lancer en arrière-plan ; <code>jobs</code>, <code>fg</code>, <code>bg</code></li><li><code>nice -n 10 commande</code> — lancer avec une priorité plus basse (gentillesse 10)</li><li><code>renice</code> — modifier la priorité d'un processus existant</li></ul>""",
        "volatile": True,
        "setup": r'''
mkuser intrus
cat > /usr/local/bin/rogue-worker <<'EOF'
#!/bin/bash
while true; do sleep 5; done
EOF
chmod 755 /usr/local/bin/rogue-worker
pkill -x rogue-worker || true
su -s /bin/bash intrus -c 'setsid nohup /usr/local/bin/rogue-worker >/dev/null 2>&1 < /dev/null &'
cat > /usr/local/sbin/lab-service <<'EOF'
#!/bin/bash
trap 'echo "$(date +%T) configuration rechargée" >> /var/log/lab-service.log' HUP
echo "$(date +%T) démarrage" >> /var/log/lab-service.log
while true; do sleep 1 & wait $!; done
EOF
chmod 755 /usr/local/sbin/lab-service
: > /var/log/lab-service.log; chmod 644 /var/log/lab-service.log
pkill -x lab-service || true
# pas de nohup : un signal ignoré au démarrage ne peut plus être intercepté par trap
setsid /usr/local/sbin/lab-service >/dev/null 2>&1 < /dev/null &
sleep 1
emit PID "$(pgrep -x rogue-worker | head -n1)"
emit SVC_PID "$(pgrep -x lab-service | head -n1)"
''',
        "exercises": [
            {"id": "11.1", "points": 3, "title": "Créer un sudoer",
             "desc": "Créez l'utilisateur <code>stagiaire</code> et donnez-lui le droit d'utiliser <code>sudo</code>.",
             "hints": ["Sous Ubuntu, les membres du groupe <code>sudo</code> peuvent utiliser sudo."],
             "checks": [
                 ('id stagiaire', "L'utilisateur stagiaire n'existe pas."),
                 ('id -nG stagiaire | grep -qw sudo', "stagiaire n'est pas membre du groupe sudo."),
             ]},
            {"id": "11.2", "points": 3, "title": "Enquête",
             "desc": "Un processus nommé <code>rogue-worker</code> tourne sur la machine. Écrivez dans <code>~/rogue.txt</code> son <strong>PID</strong> et l'<strong>utilisateur</strong> qui l'a lancé (ex. <code>1234 bob</code>).",
             "hints": ["<code>ps aux | grep rogue</code> ou <code>ps -o pid,user,cmd -C rogue-worker</code>"],
             "checks": [
                 ('[ -n "$LAB_PID" ]', "Le processus de l'exercice n'a pas démarré : rechargez la page."),
                 ('grep -qw "$LAB_PID" $H/rogue.txt', "Le PID de rogue-worker n'est pas dans ~/rogue.txt."),
                 ('grep -qw intrus $H/rogue.txt', "Le propriétaire du processus n'est pas indiqué dans ~/rogue.txt."),
             ]},
            {"id": "11.3", "points": 4, "title": "Arrêter le processus",
             "desc": "Arrêtez <code>rogue-worker</code> proprement (signal TERM).",
             "hints": ["Ce processus appartient à un autre utilisateur : un simple <code>kill</code> sera refusé.", "<code>sudo kill &lt;PID&gt;</code>"],
             "checks": [
                 ('[ -n "$LAB_PID" ]', "Le processus de l'exercice n'a pas démarré : rechargez la page."),
                 ('! kill -0 "$LAB_PID" 2>/dev/null && ! pgrep -x rogue-worker', "rogue-worker tourne encore."),
             ]},
            {"id": "11.4", "points": 3, "title": "Processus gentil",
             "desc": "Lancez <code>sleep 1000</code> en arrière-plan avec une gentillesse (<em>niceness</em>) de <code>10</code>, et laissez-le tourner.",
             "hints": ["<code>nice -n 10 sleep 1000 &amp;</code>"],
             "checks": [
                 ('ps -o ni=,user=,args= -C sleep | awk \'$1 == 10 && $2 == "etudiant" && $4 == 1000\' | grep -q .', "Aucun « sleep 1000 » lancé par etudiant avec une niceness de 10 n'est en cours."),
             ]},
            {"id": "11.5", "points": 4, "title": "Recharger un service",
             "desc": "Le service <code>lab-service</code> (lancé par root) recharge sa configuration quand il reçoit le signal <code>HUP</code>. Faites-le recharger <strong>sans l'arrêter</strong>. Son journal est <code>/var/log/lab-service.log</code>.",
             "hints": ["<code>kill -HUP</code> ou <code>kill -1</code>", "Le processus appartient à root."],
             "checks": [
                 ('[ -n "$LAB_SVC_PID" ] && kill -0 "$LAB_SVC_PID"', "lab-service ne tourne plus : il fallait le recharger, pas l'arrêter (rechargez la page pour le relancer)."),
                 ('grep -q "rechargée" /var/log/lab-service.log', "Le journal n'indique aucun rechargement."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    12: {
        "title": "Cas pratique : système familial",
        "description": "Mettez en œuvre utilisateurs, groupes et permissions sur un cas concret.",
        "lesson": """<h3>Cas pratique</h3><p>Vous installez Linux pour une famille : <strong>papa</strong>, <strong>maman</strong>, <strong>fils</strong>, <strong>fille</strong>, et un compte <strong>invite</strong>.</p><ul><li>Chacun a un compte avec un dossier <code>Travail</code> et <code>Bazar</code> dans son dossier personnel, qui lui appartiennent.</li><li>Un dossier <code>/home/famille</code> partagé par les 4 membres.</li><li>Un dossier <code>/home/parents-only</code> réservé aux parents.</li><li>L'invité n'a accès à rien de tout ça, ni aux dossiers personnels.</li></ul><div class="tip">Ce sont les <strong>accès réels</strong> qui sont vérifiés (en se connectant en tant que chaque utilisateur), pas seulement les chiffres de <code>chmod</code>.</div><p>Rappels : <code>sudo -u papa mkdir ...</code> crée un dossier au nom de papa ; <code>chmod 750</code> interdit tout aux « autres ».</p>""",
        "exercises": [
            {"id": "12.1", "points": 4, "title": "La famille",
             "desc": "Créez <code>papa</code>, <code>maman</code>, <code>fils</code>, <code>fille</code>. Chacun a <code>~/Travail</code> et <code>~/Bazar</code>, qui lui appartiennent.",
             "hints": ["Une boucle <code>for u in papa maman fils fille; do ...; done</code> vous fera gagner du temps.", "<code>sudo -u $u mkdir /home/$u/Travail</code> crée le dossier directement au bon propriétaire."],
             "checks": [
                 ('for u in papa maman fils fille; do id $u || exit 1; done', "Les 4 utilisateurs doivent exister."),
                 ('for u in papa maman fils fille; do for d in Travail Bazar; do [ "$(owner /home/$u/$d)" = $u ] || exit 1; done; done', "Chaque utilisateur doit avoir Travail et Bazar dans son dossier, lui appartenant."),
             ]},
            {"id": "12.2", "points": 3, "title": "Les groupes",
             "desc": "Créez les groupes <code>parents</code> (papa, maman) et <code>enfants</code> (fils, fille).",
             "checks": [
                 ('getent group parents && getent group enfants', "Les groupes parents et enfants doivent exister."),
                 ('id -nG papa | grep -qw parents && id -nG maman | grep -qw parents && id -nG fils | grep -qw enfants && id -nG fille | grep -qw enfants', "Les membres des groupes ne sont pas corrects."),
             ]},
            {"id": "12.3", "points": 4, "title": "Espace commun",
             "desc": "Créez <code>/home/famille</code> (groupe <code>famille</code>) où les 4 membres peuvent créer des fichiers, et où les autres n'ont aucun droit.",
             "hints": ["Il faut un groupe qui rassemble les 4 membres."],
             "checks": [
                 ('getent group famille && [ "$(stat -c %G /home/famille)" = famille ]', "/home/famille doit exister et appartenir au groupe famille."),
                 ('for u in papa maman fils fille; do run_as $u "touch /home/famille/.t-$u && rm -f /home/famille/.t-$u" || exit 1; done', "Un des membres de la famille ne peut pas créer de fichier dans /home/famille."),
                 ('[ "$(others /home/famille)" = "---" ]', "Les autres utilisateurs ont encore des droits sur /home/famille."),
             ]},
            {"id": "12.4", "points": 4, "title": "Espace parents",
             "desc": "Créez <code>/home/parents-only</code> : papa et maman peuvent y écrire, les enfants ne peuvent même pas le lister.",
             "checks": [
                 ('run_as papa "touch /home/parents-only/.t && rm -f /home/parents-only/.t" && run_as maman "touch /home/parents-only/.t && rm -f /home/parents-only/.t"', "papa et maman doivent pouvoir écrire dans /home/parents-only."),
                 ('! run_as fils "ls /home/parents-only" && ! run_as fille "ls /home/parents-only"', "Les enfants peuvent lister /home/parents-only."),
             ]},
            {"id": "12.5", "points": 4, "title": "Compte invité",
             "desc": "Créez <code>invite</code>. Il ne doit pouvoir lister ni <code>/home/famille</code>, ni <code>/home/parents-only</code>, ni les dossiers personnels des membres de la famille.",
             "hints": ["Testez : <code>sudo -u invite ls /home/papa</code>", "Si un dossier personnel est lisible par tous, retirez les droits des « autres »."],
             "checks": [
                 ('id invite', "L'utilisateur invite n'existe pas."),
                 ('! run_as invite "ls /home/famille" && ! run_as invite "ls /home/parents-only"', "invite peut lister un dossier familial."),
                 ('for u in papa maman fils fille; do run_as invite "ls /home/$u" && exit 1; done; exit 0', "invite peut lister le dossier personnel d'un membre de la famille."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    13: {
        "title": "Installer des programmes",
        "description": "Gérez les paquets avec apt et dpkg, téléchargez avec wget.",
        "lesson": """<div class="tip">Ces exercices nécessitent un accès à Internet depuis le lab.</div><h3>apt : le gestionnaire de paquets</h3><table class="lesson-table"><tr><th>Commande</th><th>Action</th></tr><tr><td><code>sudo apt update</code></td><td>Mettre à jour la liste des paquets disponibles</td></tr><tr><td><code>apt search mot</code></td><td>Chercher un paquet</td></tr><tr><td><code>sudo apt install p</code></td><td>Installer</td></tr><tr><td><code>sudo apt remove p</code></td><td>Désinstaller (<code>purge</code> : avec la config)</td></tr></table><h3>dpkg : la base des paquets installés</h3><ul><li><code>dpkg -l</code> — lister les paquets installés</li><li><code>dpkg -L paquet</code> — fichiers installés par un paquet</li><li><code>dpkg -S /chemin/fichier</code> — quel paquet a installé ce fichier ?</li></ul><h3>Télécharger</h3><pre>wget -O fichier.html https://example.com<br>curl -o fichier.html https://example.com</pre><p>L'historique d'apt est dans <code>/var/log/apt/history.log</code>.</p>""",
        "exercises": [
            {"id": "13.1", "points": 3, "title": "Installer un programme",
             "desc": "Installez le programme <code>tree</code>, puis essayez <code>tree ~</code>.",
             "hints": ["Avant d'installer, mettez à jour la liste des paquets : <code>sudo apt update</code>."],
             "checks": [
                 ('command -v tree', "tree n'est pas installé."),
             ]},
            {"id": "13.2", "points": 3, "title": "D'où vient ce fichier ?",
             "desc": "Quel paquet a installé la commande <code>/usr/bin/pgrep</code> ? Écrivez son nom dans <code>~/paquet.txt</code>.",
             "hints": ["<code>dpkg -S</code>"],
             "checks": [
                 ('[ "$(ans $H/paquet.txt)" = "$(dpkg -S /usr/bin/pgrep | cut -d: -f1)" ]', "Ce n'est pas le bon paquet."),
             ]},
            {"id": "13.3", "points": 3, "title": "Télécharger une page",
             "desc": "Téléchargez <code>https://example.com</code> dans <code>~/telechargements/page.html</code>.",
             "hints": ["Créez d'abord le dossier.", "L'option <code>-O</code> de wget choisit le fichier de sortie."],
             "checks": [
                 ('grep -qi "example domain" $H/telechargements/page.html', "~/telechargements/page.html est absent ou ne contient pas la page d'example.com."),
             ]},
            {"id": "13.4", "points": 3, "title": "Installer puis désinstaller",
             "desc": "Installez le paquet <code>cowsay</code>, essayez <code>/usr/games/cowsay Bonjour</code>, puis désinstallez-le.",
             "checks": [
                 ('grep -q "cowsay" /var/log/apt/history.log', "L'historique apt ne montre aucune installation de cowsay."),
                 ('! dpkg -s cowsay 2>/dev/null | grep -q "^Status: install ok installed"', "cowsay est toujours installé."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    14: {
        "title": "Disques et systèmes de fichiers",
        "description": "Points de montage, occupation disque et /etc/fstab.",
        "lesson": """<h3>Périphériques et partitions</h3><ul><li><code>/dev/sda</code> — premier disque, <code>/dev/sda1</code> — sa première partition</li><li><code>lsblk</code> — arborescence des disques</li></ul><h3>Montage</h3><pre>sudo mount /dev/sdb1 /mnt/usb<br>sudo umount /mnt/usb<br>findmnt          # tout ce qui est monté<br>df -hT           # occupation + type de chaque système de fichiers</pre><h3>/etc/fstab</h3><p>Montages automatiques au démarrage, une ligne par montage, 6 champs :</p><pre># périphérique  point_de_montage  type  options   dump  pass<br>/dev/sdb1       /mnt/usb          ext4  defaults  0     2</pre><h3>Qui occupe la place ?</h3><pre>du -sh /srv/data/*      # taille de chaque sous-dossier<br>du -s /srv/data/* | sort -n<br>du -sm dossier          # taille en Mo</pre><div class="tip">Dans ce lab (un conteneur), la racine est un système de fichiers <code>overlay</code> et on ne peut pas monter de vrai disque : on s'entraîne sur les outils d'analyse et la syntaxe.</div>""",
        "setup": r'''
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
''',
        "exercises": [
            {"id": "14.1", "points": 3, "title": "Type de système de fichiers",
             "desc": "Quel est le <strong>type</strong> du système de fichiers monté sur <code>/</code> ? Écrivez-le dans <code>~/fs-racine.txt</code>.",
             "hints": ["<code>df -T /</code> ou <code>findmnt /</code>"],
             "checks": [
                 ('[ "$(ans $H/fs-racine.txt)" = "$(df -T / | awk \'NR==2{print $2}\')" ]', "Ce n'est pas le bon type."),
             ]},
            {"id": "14.2", "points": 4, "title": "Qui prend toute la place ?",
             "desc": "Quel sous-dossier de <code>/srv/data</code> occupe le plus d'espace disque ? Écrivez son nom dans <code>~/plus-gros.txt</code>.",
             "hints": ["<code>du -s /srv/data/* | sort -n</code>"],
             "checks": [
                 ('a=$(ans $H/plus-gros.txt); a=${a%/}; [ "$a" = "$LAB_BIGDIR" ] || [ "$a" = "/srv/data/$LAB_BIGDIR" ]', "Ce n'est pas le bon dossier."),
             ]},
            {"id": "14.3", "points": 3, "title": "Taille totale",
             "desc": "Quelle est la taille totale de <code>/srv/data</code> en mégaoctets, telle qu'affichée par <code>du -sm</code> ? Écrivez le nombre dans <code>~/taille-data.txt</code>.",
             "checks": [
                 ('[ "$(ans $H/taille-data.txt)" = "$(du -sm /srv/data | cut -f1)" ]', "Ce n'est pas la bonne taille."),
             ]},
            {"id": "14.4", "points": 4, "title": "Préparer un montage",
             "desc": "Créez le point de montage <code>/mnt/usb</code>, puis écrivez dans <code>~/fstab-usb.txt</code> la ligne fstab qui monterait <code>/dev/sdb1</code> (ext4) sur <code>/mnt/usb</code> avec les options par défaut, sans dump, vérifiée après la racine (pass 2).",
             "hints": ["Un point de montage est un simple dossier vide.", "6 champs : périphérique, point de montage, type, options, dump, pass."],
             "checks": [
                 ('test -d /mnt/usb', "Le dossier /mnt/usb n'existe pas."),
                 ('read -r a b c d e g < <(grep -vE "^\\s*(#|$)" $H/fstab-usb.txt | head -n1); [ "$a" = /dev/sdb1 ] && [ "$b" = /mnt/usb ] && [ "$c" = ext4 ] && [[ "$d" == *defaults* ]] && [ "$e" = 0 ] && [ "$g" = 2 ]', "La ligne fstab n'est pas correcte (vérifiez l'ordre et la valeur des 6 champs)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    15: {
        "title": "Variables d'environnement et shell",
        "description": "Variables, export, PATH, alias et ~/.bashrc.",
        "lesson": """<h3>Variables</h3><pre>echo $HOME $USER $PATH<br>env                        # variables d'environnement</pre><h3>Locale ou exportée ?</h3><pre>PROJET=demo           # visible seulement dans ce shell<br>export PROJET=demo    # transmise aux programmes lancés depuis ce shell</pre><p>Testez : <code>bash -c 'echo $PROJET'</code> n'affiche la valeur que si elle est exportée.</p><h3>Le PATH</h3><p>Liste des dossiers où le shell cherche les commandes, séparés par <code>:</code>.</p><pre>export PATH="$PATH:$HOME/outils"<br>command -v macommande     # où la commande est-elle trouvée ?</pre><h3>Les alias</h3><pre>alias ll='ls -la'</pre><h3>Rendre permanent</h3><p>Tout ce qui est tapé dans le terminal disparaît à la fermeture. Pour le rendre permanent, ajoutez-le à <code>~/.bashrc</code>, puis rechargez :</p><pre>source ~/.bashrc</pre>""",
        "exercises": [
            {"id": "15.1", "points": 4, "title": "Variable permanente",
             "desc": "Faites en sorte que la variable <code>PROJET</code> vaille <code>linux-lab</code> et soit <strong>exportée</strong> dans tous vos futurs terminaux.",
             "hints": ["Ajoutez la ligne dans <code>~/.bashrc</code>.", "Sans <code>export</code>, les programmes lancés ne la voient pas."],
             "checks": [
                 ('[ "$(etu_env \'printenv PROJET\')" = linux-lab ]', "Dans un nouveau terminal, PROJET n'est pas exportée avec la valeur linux-lab."),
             ]},
            {"id": "15.2", "points": 4, "title": "Mes propres commandes",
             "desc": "Créez un script exécutable <code>~/outils/bonjour</code> qui affiche <code>Bonjour !</code>, et ajoutez <code>~/outils</code> au <code>PATH</code> de façon permanente, pour pouvoir taper <code>bonjour</code> depuis n'importe quel dossier.",
             "hints": ["Le script commence par <code>#!/bin/bash</code> et doit être exécutable (<code>chmod +x</code>).", "<code>export PATH=\"$PATH:$HOME/outils\"</code> dans ~/.bashrc"],
             "checks": [
                 ('test -x $H/outils/bonjour', "~/outils/bonjour n'existe pas ou n'est pas exécutable."),
                 ('[ "$(etu_env \'command -v bonjour\')" = $H/outils/bonjour ]', "Dans un nouveau terminal, la commande bonjour n'est pas trouvée via le PATH."),
             ]},
            {"id": "15.3", "points": 3, "title": "Alias permanent",
             "desc": "Ubuntu définit déjà un alias <code>ll</code>. Redéfinissez-le de façon permanente en <code>ls -la</code>.",
             "hints": ["Ajoutez <code>alias ll='ls -la'</code> à la <strong>fin</strong> de ~/.bashrc (la dernière définition l'emporte)."],
             "checks": [
                 ('etu_env "alias ll" | grep -q "ls -la\'$"', "Dans un nouveau terminal, ll n'est pas un alias de « ls -la »."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    16: {
        "title": "Archivage et compression",
        "description": "tar, gzip et zip : créer, lister, extraire.",
        "lesson": """<h3>tar</h3><table class="lesson-table"><tr><th>Action</th><th>Commande</th></tr><tr><td>Créer (gzip)</td><td><code>tar -czf archive.tar.gz dossier/</code></td></tr><tr><td>Lister</td><td><code>tar -tzf archive.tar.gz</code></td></tr><tr><td>Extraire</td><td><code>tar -xzf archive.tar.gz -C /destination</code></td></tr></table><p>Mnémotechnique : <strong>c</strong>reate, e<strong>x</strong>tract, lis<strong>t</strong>, <strong>z</strong> = gzip, <strong>f</strong> = fichier.</p><h3>gzip</h3><pre>gzip f.txt        # remplace f.txt par f.txt.gz<br>gzip -k f.txt     # garde l'original<br>gunzip f.txt.gz<br>zcat f.txt.gz     # lire sans décompresser</pre><h3>zip</h3><pre>zip -r archive.zip dossier/<br>unzip -l archive.zip   # lister<br>unzip archive.zip</pre><div class="tip"><code>.tar.gz</code> = standard Linux · <code>.zip</code> = compatible Windows</div>""",
        "setup": r'''
code=$(rword)
tmp=$(mktemp -d); mkdir -p $tmp/paquet/docs
echo "Code de livraison : $code" > $tmp/paquet/docs/LISEZMOI.txt
echo "binaire" > $tmp/paquet/app.bin
mkdir -p /srv/livraison
tar -czf /srv/livraison/paquet.tar.gz -C $tmp paquet
rm -rf $tmp; chmod 644 /srv/livraison/paquet.tar.gz
emit CODE "$code"
''',
        "exercises": [
            {"id": "16.1", "points": 3, "title": "Créer une archive",
             "desc": "Créez <code>~/archive-test/</code> contenant <code>a.txt</code>, <code>b.txt</code> et <code>c.txt</code>, puis archivez ce dossier dans <code>~/archive-test.tar.gz</code>.",
             "hints": ["<code>tar -czf destination.tar.gz dossier/</code>"],
             "checks": [
                 ('gzip -t $H/archive-test.tar.gz', "~/archive-test.tar.gz est absent ou n'est pas compressé avec gzip."),
                 ('l=$(tar -tzf $H/archive-test.tar.gz); for f in a b c; do echo "$l" | grep -q "$f.txt$" || exit 1; done', "L'archive ne contient pas a.txt, b.txt et c.txt."),
             ]},
            {"id": "16.2", "points": 3, "title": "Extraire",
             "desc": "Extrayez <code>~/archive-test.tar.gz</code> dans le dossier <code>~/extraction/</code>.",
             "hints": ["Créez le dossier, puis utilisez l'option <code>-C</code> de tar."],
             "checks": [
                 ('find $H/extraction -name a.txt | grep -q .', "Aucun a.txt dans ~/extraction."),
             ]},
            {"id": "16.3", "points": 4, "title": "Colis reçu",
             "desc": "L'archive <code>/srv/livraison/paquet.tar.gz</code> contient un code de livraison. Trouvez-le et écrivez-le dans <code>~/code-livraison.txt</code>.",
             "hints": ["Listez d'abord son contenu avec <code>tar -tzf</code>.", "Vous ne pouvez pas écrire dans /srv/livraison : extrayez ailleurs (<code>-C</code>)."],
             "checks": [
                 ('grep -q "$LAB_CODE" $H/code-livraison.txt', "Ce n'est pas le bon code."),
             ]},
            {"id": "16.4", "points": 3, "title": "Compresser en gardant l'original",
             "desc": "Créez <code>~/compress-me.txt</code> (avec du contenu) puis compressez-le avec <code>gzip</code> en <strong>conservant</strong> l'original.",
             "hints": ["Cherchez l'option « keep » dans <code>man gzip</code>."],
             "checks": [
                 ('test -s $H/compress-me.txt', "~/compress-me.txt est absent ou vide : l'original doit être conservé."),
                 ('gzip -t $H/compress-me.txt.gz && zcat $H/compress-me.txt.gz | cmp -s - $H/compress-me.txt', "~/compress-me.txt.gz est absent ou ne correspond pas à l'original."),
             ]},
            {"id": "16.5", "points": 3, "title": "Archive zip",
             "desc": "Créez <code>~/backup.zip</code> contenant le dossier <code>archive-test</code> et ses fichiers.",
             "hints": ["<code>zip -r</code>, en vous plaçant dans ~ pour avoir des chemins courts."],
             "checks": [
                 ('unzip -l $H/backup.zip | grep -q "archive-test/a.txt"', "~/backup.zip est absent ou ne contient pas archive-test/a.txt."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    17: {
        "title": "Introduction au scripting Bash",
        "description": "Écrivez des scripts avec arguments, conditions et boucles.",
        "lesson": """<h3>Structure d'un script</h3><pre>#!/bin/bash<br># commentaire<br>echo "Mon script !"</pre><p>Rendre exécutable : <code>chmod +x script.sh</code> · lancer : <code>./script.sh</code></p><h3>Variables et arguments</h3><pre>NOM="Linux"             # pas d'espace autour du =<br>echo "Bonjour $NOM"<br>AUJOURDHUI=$(date +%F)  # résultat d'une commande<br>echo "1er argument : $1, nombre : $#"</pre><h3>Conditions</h3><pre>if [ -e "$1" ]; then<br>    echo "EXISTE"<br>else<br>    echo "ABSENT"<br>fi</pre><p>Tests utiles : <code>-e</code> existe, <code>-f</code> fichier, <code>-d</code> dossier, <code>-z "$x"</code> vide, <code>"$a" = "$b"</code>, <code>$n -gt 3</code>.</p><h3>Boucles</h3><pre>for i in 1 2 3; do echo "$i"; done<br>for i in $(seq 1 5); do ...; done<br>for f in *.txt; do ...; done</pre><h3>Code de retour</h3><p><code>exit 0</code> = succès, <code>exit 1</code> (ou autre) = erreur. Le code de la dernière commande est dans <code>$?</code>.</p><div class="tip">Ces exercices exécutent réellement vos scripts : cliquez sur <strong>Vérifier</strong> pour les tester.</div>""",
        "exercises": [
            {"id": "17.1", "points": 3, "title": "Premier script", "manual": True,
             "desc": "Créez <code>~/hello.sh</code>, exécutable, avec un shebang, qui affiche exactement <code>Bonjour depuis mon script !</code>.",
             "hints": ["Première ligne : <code>#!/bin/bash</code>", "<code>chmod +x ~/hello.sh</code>"],
             "checks": [
                 ('test -f $H/hello.sh', "~/hello.sh n'existe pas."),
                 ('head -n1 $H/hello.sh | grep -q "^#!"', "La première ligne doit être un shebang (#!/bin/bash)."),
                 ('test -x $H/hello.sh', "Le script n'est pas exécutable."),
                 ('[ "$(run_as etudiant "timeout 5 $H/hello.sh")" = "Bonjour depuis mon script !" ]', "Le script n'affiche pas exactement « Bonjour depuis mon script ! »."),
             ]},
            {"id": "17.2", "points": 3, "title": "Infos système", "manual": True,
             "desc": "Créez <code>~/info-system.sh</code> (exécutable) qui affiche, une par ligne : la date, votre nom d'utilisateur et le dossier courant <strong>au moment de l'exécution</strong>.",
             "hints": ["Utilisez les commandes <code>date</code>, <code>whoami</code> et <code>pwd</code>."],
             "checks": [
                 ('test -x $H/info-system.sh', "~/info-system.sh n'existe pas ou n'est pas exécutable."),
                 ('o=$(run_as etudiant "cd /tmp && timeout 5 $H/info-system.sh"); echo "$o" | grep -q "$(date +%Y)" && echo "$o" | grep -qx etudiant && echo "$o" | grep -qx /tmp', "Lancé depuis /tmp, le script doit afficher la date, « etudiant » et « /tmp » (chacun sur sa ligne)."),
             ]},
            {"id": "17.3", "points": 4, "title": "Tester un argument", "manual": True,
             "desc": "Créez <code>~/check-file.sh</code> : avec un chemin en argument, il affiche <code>EXISTE</code> ou <code>ABSENT</code>. Sans argument, il affiche un message contenant <code>Usage</code> et se termine avec un code d'erreur.",
             "hints": ["<code>$1</code> est le premier argument, <code>$#</code> le nombre d'arguments.", "<code>if [ $# -eq 0 ]; then echo \"Usage : $0 chemin\"; exit 1; fi</code>"],
             "checks": [
                 ('test -x $H/check-file.sh', "~/check-file.sh n'existe pas ou n'est pas exécutable."),
                 ('[ "$(run_as etudiant "timeout 5 $H/check-file.sh /etc/passwd")" = EXISTE ] && [ "$(run_as etudiant "timeout 5 $H/check-file.sh /inexistant")" = ABSENT ]', "Le script n'affiche pas EXISTE pour /etc/passwd et ABSENT pour /inexistant."),
                 ('! run_as etudiant "timeout 5 $H/check-file.sh" && run_as etudiant "timeout 5 $H/check-file.sh 2>&1; true" | grep -qi usage', "Sans argument, le script doit afficher « Usage ... » et renvoyer un code d'erreur (exit 1)."),
             ]},
            {"id": "17.4", "points": 4, "title": "Boucle", "manual": True,
             "desc": "Créez <code>~/create-users.sh</code> qui, avec une boucle <code>for</code>, crée <code>user1.txt</code> à <code>user5.txt</code> dans <code>~/users/</code> (le dossier est créé s'il n'existe pas).",
             "hints": ["<code>mkdir -p</code> ne râle pas si le dossier existe déjà.", "<code>for i in $(seq 1 5)</code> ou <code>for i in {1..5}</code>"],
             "checks": [
                 ('test -x $H/create-users.sh && grep -qw for $H/create-users.sh', "~/create-users.sh n'existe pas, n'est pas exécutable ou n'utilise pas de boucle for."),
                 ('touch /tmp/.lab-t && run_as etudiant "timeout 5 $H/create-users.sh" && [ "$(find $H/users -name "user[1-5].txt" -newer /tmp/.lab-t | wc -l)" -eq 5 ]', "En l'exécutant, le script ne crée (ou ne met à jour) pas les 5 fichiers ~/users/user1.txt à user5.txt."),
             ]},
            {"id": "17.5", "points": 5, "title": "Compteur", "manual": True,
             "desc": "Créez <code>~/compteur.sh</code> qui prend un dossier en argument et affiche le <strong>nombre de fichiers .txt</strong> qu'il contient (directement dedans, sans les sous-dossiers).",
             "hints": ["<code>ls \"$1\"/*.txt 2&gt;/dev/null | wc -l</code>", "ou <code>find \"$1\" -maxdepth 1 -name '*.txt' | wc -l</code>"],
             "checks": [
                 ('test -x $H/compteur.sh', "~/compteur.sh n'existe pas ou n'est pas exécutable."),
                 ('d=/tmp/lab-compteur; rm -rf $d; mkdir -p $d/sous; n=$((RANDOM % 6 + 2)); for i in $(seq $n); do touch $d/f$i.txt; done; touch $d/autre.log $d/sous/cache.txt; chmod -R a+rX $d; r=$(run_as etudiant "timeout 5 $H/compteur.sh $d" | tr -dc 0-9); rm -rf $d; [ "$r" = "$n" ]', "Testé sur un dossier inconnu, le script n'affiche pas le bon nombre de fichiers .txt."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    18: {
        "title": "Tâches planifiées (cron)",
        "description": "Automatisez avec crontab, /etc/cron.d et cron.daily.",
        "lesson": """<h3>crontab personnelle</h3><pre>crontab -l    # lister<br>crontab -e    # éditer</pre><h3>Syntaxe</h3><pre>┌─ minute (0-59)<br>│ ┌─ heure (0-23)<br>│ │ ┌─ jour du mois (1-31)<br>│ │ │ ┌─ mois (1-12)<br>│ │ │ │ ┌─ jour de la semaine (0-7, 0 et 7 = dimanche)<br>* * * * * commande</pre><ul><li><code>*/15 * * * *</code> — toutes les 15 minutes</li><li><code>0 8 * * 1-5</code> — 8h, du lundi au vendredi</li></ul><h3>/etc/cron.d/ : les tâches système</h3><p>Même syntaxe, avec un <strong>6<sup>e</sup> champ : l'utilisateur</strong> qui exécute la commande :</p><pre>0 2 * * * root /usr/local/bin/sauvegarde.sh</pre><div class="tip"><strong>Pièges classiques :</strong> cron n'a presque pas de PATH → utilisez des chemins absolus ; les fichiers de <code>/etc/cron.d</code> et <code>/etc/cron.daily</code> dont le nom contient un <strong>point</strong> sont ignorés ; le fichier doit appartenir à root.</div><h3>/etc/cron.daily/</h3><p>Scripts exécutés une fois par jour. <code>run-parts --test /etc/cron.daily</code> affiche ceux qui seront réellement lancés.</p>""",
        "exercises": [
            {"id": "18.1", "points": 4, "title": "Tic-tac",
             "desc": "Ajoutez à <strong>votre</strong> crontab une tâche qui ajoute la date à <code>~/tick.log</code> toutes les minutes. Attendez 2 minutes avant de valider.",
             "hints": ["<code>crontab -e</code>", "<code>* * * * * date &gt;&gt; /home/etudiant/tick.log</code>"],
             "checks": [
                 ('crontab -l -u etudiant 2>/dev/null | grep -v "^#" | grep -q tick.log', "Votre crontab ne contient pas de tâche écrivant dans tick.log."),
                 ('[ "$(sort -u $H/tick.log | wc -l)" -ge 2 ]', "~/tick.log ne contient pas encore 2 horodatages différents : patientez un peu."),
             ]},
            {"id": "18.2", "points": 3, "title": "Tâche système",
             "desc": "Créez <code>/etc/cron.d/backup-lab</code> qui exécute <code>/home/etudiant/hello.sh</code> en tant que <code>root</code>, tous les jours à 2h00.",
             "hints": ["N'oubliez pas le champ utilisateur entre l'horaire et la commande."],
             "checks": [
                 ('test -f /etc/cron.d/backup-lab', "/etc/cron.d/backup-lab n'existe pas."),
                 ('grep -qE "^0\\s+2\\s+\\*\\s+\\*\\s+\\*\\s+root\\s+/home/etudiant/hello\\.sh" /etc/cron.d/backup-lab', "La ligne n'est pas correcte : horaire 0 2 * * *, utilisateur root, chemin absolu du script."),
                 ('[ "$(owner /etc/cron.d/backup-lab)" = root ] && ! stat -c %A /etc/cron.d/backup-lab | cut -c6,9 | grep -q w', "Le fichier doit appartenir à root et ne pas être modifiable par le groupe ou les autres (cron l'ignorerait)."),
             ]},
            {"id": "18.3", "points": 4, "title": "Nettoyage quotidien", "manual": True,
             "desc": "Placez dans <code>/etc/cron.daily/</code> un script <code>nettoyage-tmp</code> qui supprime les fichiers <code>*.tmp</code> de <code>/tmp</code> (et seulement eux). Vérifiez avec <code>run-parts --test /etc/cron.daily</code> qu'il sera bien exécuté.",
             "hints": ["run-parts ignore les noms contenant un point : pas de <code>.sh</code> !", "Le script doit être exécutable."],
             "checks": [
                 ('run-parts --test /etc/cron.daily | grep -qx /etc/cron.daily/nettoyage-tmp', "run-parts ne lancera pas /etc/cron.daily/nettoyage-tmp (nom incorrect ou fichier non exécutable)."),
                 ('touch /tmp/lab-a.tmp /tmp/lab-b.txt && timeout 10 /etc/cron.daily/nettoyage-tmp; r=0; [ ! -e /tmp/lab-a.tmp ] || r=1; [ -e /tmp/lab-b.txt ] || r=1; rm -f /tmp/lab-a.tmp /tmp/lab-b.txt; exit $r', "Le script doit supprimer les .tmp de /tmp sans toucher aux autres fichiers."),
             ]},
            {"id": "18.4", "points": 3, "title": "Lire l'heure en cron",
             "desc": "Écrivez dans <code>~/cron-quiz.txt</code> les 5 champs cron correspondant à « <strong>tous les lundis à 8h30</strong> ».",
             "checks": [
                 ('a=$(tr -s " \\t" " " < $H/cron-quiz.txt | sed "s/^ //;s/ $//" | head -n1 | tr A-Z a-z); [ "$a" = "30 8 * * 1" ] || [ "$a" = "30 8 * * mon" ]', "Ce n'est pas la bonne expression."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    19: {
        "title": "Surveillance du système",
        "description": "Disque, mémoire, charge : repérez ce qui consomme les ressources.",
        "lesson": """<h3>Espace disque</h3><pre>df -h           # partitions<br>du -sh /var/*   # taille des sous-dossiers</pre><h3>Mémoire</h3><pre>free -h</pre><h3>Charge</h3><pre>uptime          # durée de fonctionnement + load average (1, 5, 15 min)</pre><h3>Processus gourmands</h3><pre>top                          # M : trier par mémoire, P : par CPU, q : quitter<br>ps aux --sort=-%mem | head   # les plus gros consommateurs de mémoire<br>ps aux --sort=-%cpu | head</pre><div class="tip">Un rapport de supervision n'est utile que s'il est horodaté : commencez-le par <code>date</code>.</div>""",
        "volatile": True,
        "setup": r'''
cat > /usr/local/bin/data-cruncher <<'EOF'
#!/bin/bash
x=$(head -c 30000000 /dev/zero | tr '\0' 'x')
while true; do sleep 5; done
EOF
chmod 755 /usr/local/bin/data-cruncher
pkill -x data-cruncher || true
setsid nohup /usr/local/bin/data-cruncher >/dev/null 2>&1 < /dev/null &
sleep 3
emit PID "$(pgrep -x data-cruncher | head -n1)"
''',
        "exercises": [
            {"id": "19.1", "points": 4, "title": "Rapport système", "manual": True,
             "desc": "Créez <code>~/rapport.sh</code> (exécutable) qui génère <code>~/rapport-systeme.txt</code> contenant la date, l'espace disque (<code>df -h</code>), la mémoire (<code>free -h</code>) et la charge (<code>uptime</code>). Chaque exécution remplace le rapport précédent.",
             "hints": ["Regroupez les commandes : <code>{ date; df -h; free -h; uptime; } &gt; fichier</code>"],
             "checks": [
                 ('test -x $H/rapport.sh', "~/rapport.sh n'existe pas ou n'est pas exécutable."),
                 ('touch /tmp/.lab-t && run_as etudiant "cd /tmp && timeout 10 $H/rapport.sh" && [ $H/rapport-systeme.txt -nt /tmp/.lab-t ]', "Le script ne (re)crée pas ~/rapport-systeme.txt (attention aux chemins relatifs : il est lancé depuis /tmp)."),
                 ('f=$H/rapport-systeme.txt; grep -q Mem $f && grep -qi filesystem $f && grep -q "load average" $f', "Le rapport doit contenir la sortie de df -h, free -h et uptime."),
             ]},
            {"id": "19.2", "points": 4, "title": "Le glouton",
             "desc": "Un processus consomme beaucoup plus de mémoire que les autres. Écrivez son <strong>PID</strong> dans <code>~/gourmand.txt</code>.",
             "hints": ["<code>ps aux --sort=-%mem | head</code> ou <code>top</code> puis <kbd>M</kbd>."],
             "checks": [
                 ('[ -n "$LAB_PID" ]', "Le processus de l'exercice n'a pas démarré : rechargez la page."),
                 ('[ "$(ans $H/gourmand.txt)" = "$LAB_PID" ]', "Ce n'est pas le PID du processus le plus gourmand en mémoire."),
             ]},
            {"id": "19.3", "points": 3, "title": "Le plus gros de /var",
             "desc": "Quel sous-dossier de <code>/var</code> est le plus volumineux ? Écrivez son chemin complet (ex. <code>/var/xxx</code>) dans <code>~/plus-gros-var.txt</code>.",
             "hints": ["<code>sudo du -s /var/* | sort -n | tail -1</code>"],
             "checks": [
                 ('a=$(ans $H/plus-gros-var.txt); a=${a%/}; [ "$a" = "$(du -s /var/* 2>/dev/null | sort -n | tail -n1 | cut -f2)" ] || [ "$a" = "$(run_as etudiant "du -s /var/* 2>/dev/null" | sort -n | tail -n1 | cut -f2)" ]', "Ce n'est pas le plus gros sous-dossier de /var."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    20: {
        "title": "Gestion des logs",
        "description": "Lisez, filtrez, analysez et faites tourner les journaux.",
        "lesson": """<h3>Où sont les logs ?</h3><pre>/var/log/syslog    — messages système (rsyslog)<br>/var/log/auth.log  — authentification (sudo, ssh…)<br>/var/log/apt/      — installations de paquets</pre><p>Beaucoup de logs ne sont lisibles que par root ou le groupe <code>adm</code> : utilisez <code>sudo</code>.</p><h3>Lire et filtrer</h3><pre>tail -n 20 /var/log/syslog<br>tail -f /var/log/syslog        # en temps réel (Ctrl+C pour sortir)<br>grep "\\[ERROR\\]" app.log        # les crochets doivent être échappés</pre><h3>Écrire dans syslog</h3><pre>logger "Mon message"</pre><h3>logrotate</h3><p>Fait « tourner » les logs pour qu'ils ne remplissent pas le disque. Une configuration dans <code>/etc/logrotate.d/</code> :</p><pre>/var/log/app/*.log {<br>    daily<br>    rotate 7<br>    compress<br>    missingok<br>}</pre><p><code>sudo logrotate -d /etc/logrotate.d/app-lab</code> teste la configuration sans rien modifier.</p>""",
        "setup": r'''
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
emit NERR "$(grep -c '\[ERROR\]' $f)"
''',
        "exercises": [
            {"id": "20.1", "points": 3, "title": "Écrire dans syslog",
             "desc": "Avec <code>logger</code>, envoyez le message <code>Mon premier log</code> dans le journal système, puis retrouvez-le dans <code>/var/log/syslog</code>.",
             "hints": ["<code>sudo tail /var/log/syslog</code>"],
             "checks": [
                 ('grep -q "Mon premier log" /var/log/syslog', "Le message « Mon premier log » n'apparaît pas dans /var/log/syslog."),
             ]},
            {"id": "20.2", "points": 4, "title": "Compter les erreurs",
             "desc": "Combien d'entrées de niveau <code>[ERROR]</code> contient <code>/var/log/app/app.log</code> ? Écrivez le nombre dans <code>~/error-count.txt</code>.",
             "hints": ["Le fichier n'est lisible qu'avec sudo (ou par le groupe adm).", "Attention : le mot ERROR apparaît aussi dans certains messages INFO ! Cherchez <code>\\[ERROR\\]</code>."],
             "checks": [
                 ('[ "$(ans $H/error-count.txt)" = "$LAB_NERR" ]', "Ce n'est pas le bon nombre. Avez-vous compté les lignes INFO qui contiennent le mot ERROR ?"),
             ]},
            {"id": "20.3", "points": 3, "title": "Les erreurs du 15 mars",
             "desc": "Extrayez toutes les lignes <code>[ERROR]</code> du <strong>15 mars 2026</strong> de <code>/var/log/app/app.log</code> dans <code>~/erreurs-15.txt</code>.",
             "hints": ["Les lignes commencent par la date au format <code>2026-03-15</code>.", "<code>grep '^2026-03-15.*\\[ERROR\\]'</code>"],
             "checks": [
                 ('test -s $H/erreurs-15.txt && diff -q $H/erreurs-15.txt <(grep "^2026-03-15 .*\\[ERROR\\]" /var/log/app/app.log)', "Le fichier ne contient pas exactement les erreurs du 15 mars."),
             ]},
            {"id": "20.4", "points": 5, "title": "Analyseur de logs", "manual": True,
             "desc": "Créez <code>~/log-analyzer.sh</code> qui prend un fichier de log en argument et affiche trois lignes <code>INFO: n</code>, <code>WARNING: n</code>, <code>ERROR: n</code> (nombre d'entrées de chaque niveau, repéré par <code>[NIVEAU]</code>).",
             "hints": ["<code>grep -c '\\[INFO\\]' \"$1\"</code>", "Il sera testé sur un autre fichier que app.log."],
             "checks": [
                 ('test -x $H/log-analyzer.sh', "~/log-analyzer.sh n'existe pas ou n'est pas exécutable."),
                 ('f=/tmp/lab-test.log; printf "%s\\n" "d [INFO] a" "d [INFO] b" "d [INFO] pas d\'ERROR ici" "d [WARNING] c" "d [WARNING] d" "d [ERROR] e" "d [ERROR] f" "d [ERROR] g" "d [ERROR] h" > $f; chmod 644 $f; o=$(run_as etudiant "timeout 5 $H/log-analyzer.sh $f"); rm -f $f; echo "$o" | grep -qE "INFO\\s*:\\s*3\\b" && echo "$o" | grep -qE "WARNING\\s*:\\s*2\\b" && echo "$o" | grep -qE "ERROR\\s*:\\s*4\\b"', "Sur un fichier de test (3 INFO, 2 WARNING, 4 ERROR), le script n'affiche pas les bons comptes."),
             ]},
            {"id": "20.5", "points": 4, "title": "Rotation des logs",
             "desc": "Créez <code>/etc/logrotate.d/app-lab</code> pour que <code>/var/log/app/*.log</code> tourne <strong>chaque jour</strong>, en gardant <strong>7</strong> archives <strong>compressées</strong>.",
             "hints": ["Inspirez-vous du modèle du cours, puis testez avec <code>sudo logrotate -d /etc/logrotate.d/app-lab</code>."],
             "checks": [
                 ('test -f /etc/logrotate.d/app-lab && logrotate -d /etc/logrotate.d/app-lab 2>&1 | grep -q "/var/log/app/"', "La configuration est absente ou logrotate ne la comprend pas."),
                 ('c=/etc/logrotate.d/app-lab; grep -qE "^\\s*daily\\b" $c && grep -qE "^\\s*rotate\\s+7\\b" $c && grep -qE "^\\s*compress\\b" $c', "La configuration doit contenir daily, rotate 7 et compress."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    21: {
        "title": "Réseau de base",
        "description": "Adresses, nom d'hôte, ports en écoute, résolution de noms.",
        "lesson": """<h3>Adresses et interfaces</h3><pre>ip a            # interfaces et adresses<br>hostname        # nom de la machine<br>hostname -I     # adresses IP</pre><h3>Connectivité</h3><pre>ping -c 4 example.com</pre><h3>Ports et connexions</h3><pre>ss -tuln        # ports TCP/UDP en écoute (-p avec sudo : quel programme)<br>ss -tan         # connexions TCP</pre><h3>Résolution de noms</h3><ul><li><code>/etc/hosts</code> — correspondances locales nom ↔ IP, prioritaires</li><li><code>/etc/resolv.conf</code> — serveurs DNS (<code>nameserver</code>)</li><li><code>getent hosts nom</code> — teste la résolution comme le système</li></ul><pre>192.168.1.10   serveur-web</pre>""",
        "volatile": True,
        "setup": r'''
port=$((RANDOM % 1000 + 4000))
cp /usr/bin/nc.openbsd /usr/local/bin/veilleur
pkill -x veilleur || true
setsid nohup /usr/local/bin/veilleur -lk $port >/dev/null 2>&1 < /dev/null &
sleep 1
emit PORT "$port"
''',
        "exercises": [
            {"id": "21.1", "points": 3, "title": "Mon adresse IP",
             "desc": "Écrivez l'adresse IPv4 de la machine (interface <code>eth0</code>, sans le masque) dans <code>~/mon-ip.txt</code>.",
             "hints": ["<code>ip a show eth0</code> ou <code>hostname -I</code>"],
             "checks": [
                 ('[ "$(ans $H/mon-ip.txt)" = "$(hostname -I | awk \'{print $1}\')" ]', "Ce n'est pas l'adresse IP de la machine (sans /16 ou /24)."),
             ]},
            {"id": "21.2", "points": 2, "title": "Nom d'hôte",
             "desc": "Écrivez le nom d'hôte de la machine dans <code>~/hostname.txt</code>.",
             "checks": [
                 ('[ "$(ans $H/hostname.txt)" = "$(hostname)" ]', "Ce n'est pas le nom d'hôte."),
             ]},
            {"id": "21.3", "points": 4, "title": "Le port mystère",
             "desc": "Un programme écoute sur un port TCP <strong>sur toutes les interfaces</strong> (adresse <code>0.0.0.0</code>). Écrivez ce numéro de port dans <code>~/port-mystere.txt</code>.",
             "hints": ["<code>ss -tln</code> : regardez la colonne « Local Address:Port ».", "Les ports liés à <code>127.0.0.x</code> ne sont joignables que depuis la machine elle-même (SSH du lab, DNS interne de Docker)."],
             "checks": [
                 ('[ -n "$LAB_PORT" ]', "Le programme de l'exercice n'a pas démarré : rechargez la page."),
                 ('[ "$(ans $H/port-mystere.txt)" = "$LAB_PORT" ]', "Ce n'est pas le bon port."),
             ]},
            {"id": "21.4", "points": 3, "title": "Résolution locale",
             "desc": "Faites en sorte que le nom <code>serveur-local</code> soit résolu en <code>192.168.1.100</code> sur cette machine.",
             "hints": ["Éditez <code>/etc/hosts</code> avec sudo.", "Testez avec <code>getent hosts serveur-local</code>."],
             "checks": [
                 ('timeout 5 getent ahostsv4 serveur-local | grep -q "^192\\.168\\.1\\.100\\b"', "serveur-local n'est pas résolu en 192.168.1.100."),
             ]},
            {"id": "21.5", "points": 3, "title": "Serveur DNS",
             "desc": "Quel est le serveur DNS utilisé par la machine ? Écrivez son adresse dans <code>~/dns.txt</code>.",
             "checks": [
                 ('[ "$(ans $H/dns.txt)" = "$(awk \'/^nameserver/{print $2; exit}\' /etc/resolv.conf)" ]', "Ce n'est pas l'adresse du serveur DNS."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    22: {
        "title": "SSH et accès distant",
        "description": "Clés, authentification sans mot de passe, config, scp et durcissement.",
        "lesson": """<h3>Connexion</h3><p>Un serveur SSH tourne sur cette machine. Un compte <code>deploy</code> (mot de passe <code>deploy123</code>) y est disponible : on s'entraîne sur <code>localhost</code> comme sur un serveur distant.</p><pre>ssh deploy@localhost</pre><h3>Authentification par clé</h3><pre>ssh-keygen -t ed25519                 # crée ~/.ssh/id_ed25519 (privée) et .pub (publique)<br>ssh-copy-id deploy@localhost          # copie la clé publique dans ~deploy/.ssh/authorized_keys</pre><div class="tip">La clé <strong>privée</strong> ne quitte jamais votre machine. Seule la clé publique est copiée sur les serveurs.</div><h3>Permissions exigées par sshd</h3><pre>~/.ssh               700<br>~/.ssh/id_ed25519    600<br>authorized_keys      600 (et appartenant à l'utilisateur)</pre><h3>~/.ssh/config</h3><pre>Host prod<br>    HostName localhost<br>    User deploy</pre><p>Puis simplement : <code>ssh prod</code></p><h3>Transférer des fichiers</h3><pre>scp fichier deploy@localhost:/home/deploy/<br>scp -r dossier prod:</pre><h3>Durcir le serveur</h3><p>Dans <code>/etc/ssh/sshd_config</code> :</p><pre>PasswordAuthentication no<br>PermitRootLogin no</pre><p>Puis <code>sudo sshd -t</code> (vérifie la syntaxe) et <code>sudo service ssh reload</code>.</p><div class="tip">Faites le durcissement <strong>en dernier</strong> : une fois les mots de passe désactivés, <code>ssh-copy-id</code> ne fonctionne plus !</div>""",
        "setup": r'''
mkuser deploy
echo 'deploy:deploy123' | chpasswd
mkdir -p $H/a-envoyer
echo "Livrable $(rword) du $(date +%F)" > $H/a-envoyer/livrable.txt
own $H/a-envoyer
''',
        "exercises": [
            {"id": "22.1", "points": 3, "title": "Générer une paire de clés",
             "desc": "Générez une paire de clés <code>ed25519</code> dans <code>~/.ssh/</code>, sans passphrase.",
             "hints": ["<code>ssh-keygen -t ed25519</code>, puis Entrée à chaque question."],
             "checks": [
                 ('test -f $H/.ssh/id_ed25519 && grep -q ssh-ed25519 $H/.ssh/id_ed25519.pub', "Les clés ~/.ssh/id_ed25519 et id_ed25519.pub n'existent pas."),
                 ('[ "$(owner $H/.ssh/id_ed25519)" = etudiant ] && [ "$(perm $H/.ssh/id_ed25519)" = 600 ]', "La clé privée doit vous appartenir et avoir les droits 600."),
             ]},
            {"id": "22.2", "points": 4, "title": "Connexion sans mot de passe",
             "desc": "Faites en sorte de pouvoir vous connecter en <code>deploy@localhost</code> <strong>par clé</strong>, sans taper de mot de passe.",
             "hints": ["<code>ssh-copy-id deploy@localhost</code> (mot de passe : deploy123)"],
             "checks": [
                 ('run_as etudiant "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 deploy@localhost true"', "La connexion par clé à deploy@localhost échoue."),
             ]},
            {"id": "22.3", "points": 3, "title": "Alias SSH",
             "desc": "Configurez <code>~/.ssh/config</code> pour que <code>ssh prod</code> vous connecte en <code>deploy</code> sur <code>localhost</code>.",
             "hints": ["Voir le bloc <code>Host</code> dans le cours."],
             "checks": [
                 ('c=$(run_as etudiant "ssh -G prod"); echo "$c" | grep -qxE "hostname (localhost|127\\.0\\.0\\.1)" && echo "$c" | grep -qx "user deploy"', "L'alias prod ne pointe pas vers deploy@localhost."),
                 ('run_as etudiant "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 prod true"', "ssh prod ne parvient pas à se connecter sans mot de passe."),
             ]},
            {"id": "22.4", "points": 3, "title": "Transfert scp",
             "desc": "Avec <code>scp</code>, copiez <code>~/a-envoyer/livrable.txt</code> dans le dossier personnel de <code>deploy</code>.",
             "hints": ["<code>scp fichier prod:</code> (le « : » final désigne le dossier personnel distant)."],
             "checks": [
                 ('cmp -s $H/a-envoyer/livrable.txt /home/deploy/livrable.txt', "/home/deploy/livrable.txt est absent ou différent de l'original."),
                 ('[ "$(owner /home/deploy/livrable.txt)" = deploy ]', "Le fichier doit appartenir à deploy (copiez-le avec scp, pas avec sudo cp)."),
             ]},
            {"id": "22.5", "points": 5, "title": "Durcir le serveur",
             "desc": "Configurez sshd pour <strong>refuser</strong> l'authentification par mot de passe et la connexion directe de root, puis rechargez le service. Votre connexion par clé doit continuer à fonctionner.",
             "hints": ["Éditez <code>/etc/ssh/sshd_config</code> avec sudo.", "Rechargez : <code>sudo service ssh reload</code>"],
             "checks": [
                 ('sshd -T 2>/dev/null | grep -qx "passwordauthentication no"', "La configuration de sshd autorise encore les mots de passe."),
                 ('sshd -T 2>/dev/null | grep -qx "permitrootlogin no"', "La configuration de sshd n'interdit pas la connexion de root (PermitRootLogin no)."),
                 ('! sshpass -p deploy123 ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 deploy@localhost true', "Le serveur accepte encore une connexion par mot de passe : avez-vous rechargé sshd ?"),
                 ('run_as etudiant "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 deploy@localhost true"', "La connexion par clé ne fonctionne plus !"),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    23: {
        "title": "Sécurité de base",
        "description": "Auditez la machine… et corrigez ce que vous trouvez.",
        "lesson": """<h3>Fichiers SUID</h3><p>Un exécutable <strong>SUID</strong> s'exécute avec les droits de son propriétaire (souvent root). Indispensable pour <code>passwd</code>, dangereux ailleurs.</p><pre>find / -perm -4000 -type f 2&gt;/dev/null<br>chmod u-s fichier            # retirer le bit SUID</pre><h3>Fichiers modifiables par tous</h3><pre>find /etc -type f -perm -o+w</pre><h3>Comptes</h3><pre>awk -F: '$3 == 0 {print $1}' /etc/passwd   # comptes d'UID 0 (= root !)<br>passwd -l user        # verrouiller le mot de passe<br>usermod -s /usr/sbin/nologin user   # interdire le shell<br>passwd -S user        # état (L = verrouillé, P = mot de passe actif)</pre><h3>Politique de mot de passe</h3><pre>chage -l user          # voir<br>chage -M 90 user       # expiration à 90 jours</pre><h3>Surveillance</h3><pre>last / lastb           # connexions réussies / échouées<br>ss -tulnp              # ports ouverts</pre><div class="tip">Sur un vrai serveur, on ajoute un pare-feu (<code>ufw</code>, <code>nftables</code>) — impossible à configurer dans ce conteneur.</div>""",
        "setup": r'''
cp /bin/cat /usr/local/bin/lecteur-root && chmod 4755 /usr/local/bin/lecteur-root
echo "db_password=Sup3rS3cret" > /etc/app-secret.conf && chmod 666 /etc/app-secret.conf
getent passwd toor >/dev/null || useradd -o -u 0 -g 0 -M -d /root -s /bin/bash toor
echo 'toor:toor' | chpasswd
mkuser securise
echo 'securise:Motdepasse1!' | chpasswd
''',
        "exercises": [
            {"id": "23.1", "points": 3, "title": "Inventaire SUID",
             "desc": "Listez tous les fichiers SUID du système (chemins complets) dans <code>~/suid-files.txt</code>.",
             "hints": ["<code>find / -perm -4000 -type f 2&gt;/dev/null</code>"],
             "checks": [
                 ('grep -qx /usr/bin/passwd $H/suid-files.txt', "La liste est incomplète (où est /usr/bin/passwd ?)."),
                 ('grep -qx /usr/local/bin/lecteur-root $H/suid-files.txt', "La liste est incomplète : un fichier SUID suspect manque."),
             ]},
            {"id": "23.2", "points": 4, "title": "Neutraliser le SUID suspect",
             "desc": "Un des fichiers SUID n'a rien à faire là : c'est une copie de <code>cat</code> qui permet à n'importe qui de lire n'importe quel fichier. Essayez <code>lecteur-root /etc/shadow</code>, puis retirez-lui son bit SUID.",
             "checks": [
                 ('test ! -u /usr/local/bin/lecteur-root', "/usr/local/bin/lecteur-root est toujours SUID."),
                 ('! run_as etudiant "/usr/local/bin/lecteur-root /etc/shadow"', "lecteur-root permet encore de lire /etc/shadow."),
             ]},
            {"id": "23.3", "points": 3, "title": "Secret exposé",
             "desc": "Un fichier de <code>/etc</code> contenant un mot de passe est modifiable par tout le monde. Trouvez-le et faites en sorte que seul root puisse le lire et le modifier.",
             "hints": ["<code>find /etc -type f -perm -o+w</code>", "Seul root : rw------- = ?"],
             "checks": [
                 ('test -f /etc/app-secret.conf', "Le fichier a été supprimé : il fallait corriger ses droits."),
                 ('[ -z "$(find /etc -xdev -type f -perm -o+w 2>/dev/null)" ]', "Il reste des fichiers modifiables par tous dans /etc."),
                 ('[ "$(perm /etc/app-secret.conf)" = 600 ] && [ "$(owner /etc/app-secret.conf)" = root ]', "Le fichier secret doit appartenir à root avec les droits 600."),
             ]},
            {"id": "23.4", "points": 5, "title": "Le faux root",
             "desc": "Listez dans <code>~/uid-zero.txt</code> les comptes d'UID 0. L'un d'eux n'est pas <code>root</code> : neutralisez-le (mot de passe verrouillé <strong>et</strong> shell <code>/usr/sbin/nologin</code>) ou supprimez-le.",
             "hints": ["<code>awk -F: '$3 == 0 {print $1}' /etc/passwd</code>", "<code>userdel</code> peut refuser car des processus tournent avec l'UID 0 : verrouillez plutôt avec <code>passwd -l</code> et <code>usermod -s</code>."],
             "checks": [
                 ('grep -qx root $H/uid-zero.txt && grep -qx toor $H/uid-zero.txt', "~/uid-zero.txt doit lister les comptes d'UID 0 (un nom par ligne)."),
                 ('! getent passwd toor || { [ "$(passwd -S toor | awk \'{print $2}\')" = L ] && getent passwd toor | cut -d: -f7 | grep -qE "(nologin|false)$"; }', "Le compte toor est encore utilisable (mot de passe non verrouillé ou shell actif)."),
             ]},
            {"id": "23.5", "points": 4, "title": "Politique de mot de passe",
             "desc": "Le compte <code>securise</code> doit changer de mot de passe au moins tous les 90 jours. Configurez-le, puis verrouillez le compte en attendant le retour de son propriétaire.",
             "hints": ["<code>chage -M</code>", "<code>passwd -l</code>"],
             "checks": [
                 ('chage -l securise | grep -i "^maximum" | grep -qE ":\\s*90$"', "L'expiration du mot de passe de securise n'est pas de 90 jours."),
                 ('[ "$(passwd -S securise | awk \'{print $2}\')" = L ]', "Le compte securise n'est pas verrouillé."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    24: {
        "title": "Dépannage",
        "description": "Des choses sont cassées sur ce serveur. Diagnostiquez et réparez.",
        "lesson": """<h3>La méthode</h3><ol><li><strong>Reproduire</strong> : lancez la commande qui échoue et lisez <em>vraiment</em> le message d'erreur.</li><li><strong>Observer</strong> : droits (<code>ls -l</code>, <code>namei -l chemin</code>), contenu (<code>cat -A</code> révèle les caractères invisibles), logs (<code>/var/log/</code>).</li><li><strong>Une hypothèse, une correction</strong> à la fois, puis on re-teste.</li></ol><h3>Boîte à outils</h3><ul><li><code>cat -A f</code> — affiche <code>^M</code> pour les fins de ligne Windows (CRLF)</li><li><code>sed -i 's/\\r$//' f</code> — convertit en fins de ligne Unix</li><li><code>file f</code> — type de fichier (« with CRLF line terminators »)</li><li><code>namei -l /chemin/complet</code> — droits de chaque dossier du chemin</li><li><code>du -ah /var/log | sort -h | tail</code> — les plus gros fichiers</li><li><code>truncate -s 0 f</code> ou <code>: &gt; f</code> — vider un fichier sans le supprimer</li><li><code>ssh -v</code> — connexion SSH verbeuse ; côté serveur : <code>/var/log/auth.log</code></li><li><code>run-parts --test /etc/cron.daily</code>, <code>grep CRON /var/log/syslog</code></li></ul><div class="tip">Supprimer un log ouvert par une application ne libère pas l'espace : l'application garde le fichier ouvert. On le <strong>vide</strong>.</div>""",
        "setup": r'''
mkdir -p $H/depannage
printf '#!/bin/bsh\r\necho "Déploiement en cours..."\r\necho "DEPLOY OK"\r\n' > $H/depannage/deploy.sh
chmod 644 $H/depannage/deploy.sh
mkdir -p /var/log/app-debug
for n in access audit worker; do head -c 200K /dev/urandom | base64 > /var/log/app-debug/$n.log; done
big=/var/log/app-debug/trace-$RANDOM.log
head -c 60M /dev/zero > $big
emit BIGLOG "$big"
mkuser ops
mkdir -p /home/ops/.ssh
rm -f $H/depannage/cle_ops $H/depannage/cle_ops.pub
ssh-keygen -q -t ed25519 -N '' -C cle-ops -f $H/depannage/cle_ops
cp $H/depannage/cle_ops.pub /home/ops/.ssh/authorized_keys
chmod 777 /home/ops /home/ops/.ssh; chmod 666 /home/ops/.ssh/authorized_keys
chown root:root /home/ops/.ssh/authorized_keys
own $H/depannage
cat > /usr/local/bin/rapport-cron.sh <<'EOF'
#!/bin/bash
echo "$(date '+%F %T') rapport généré" >> /var/log/rapport-cron.log
EOF
chmod 644 /usr/local/bin/rapport-cron.sh
printf '* * * * * rapport-cron.sh\n' > /etc/cron.d/rapport.cron
rm -f /var/log/rapport-cron.log
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
printf 'PORT=huit-mille-quatre-vingt\nLOG_DIR=/var/log/mon-service\n' > /etc/mon-service.conf
chmod 644 /etc/mon-service.conf
rm -rf /var/log/mon-service
''',
        "exercises": [
            {"id": "24.1", "points": 4, "title": "Le script qui ne démarre pas", "manual": True,
             "desc": "Un collègue a écrit <code>~/depannage/deploy.sh</code> sous Windows. Il doit afficher <code>DEPLOY OK</code> quand on lance <code>~/depannage/deploy.sh</code>. Réparez-le (il y a plusieurs problèmes).",
             "hints": ["Lancez-le et lisez l'erreur. Puis regardez-le avec <code>cat -A</code> : que sont ces <code>^M</code> ?", "Trois problèmes : droits, shebang, fins de ligne."],
             "checks": [
                 ('test -x $H/depannage/deploy.sh', "Le script n'est pas exécutable."),
                 ('head -n1 $H/depannage/deploy.sh | grep -qxE "#!/(usr/)?bin/(env )?(ba)?sh"', "Le shebang ne désigne pas un interpréteur valide."),
                 ('! grep -q $\'\\r\' $H/depannage/deploy.sh', "Le fichier contient encore des fins de ligne Windows (CRLF)."),
                 ('run_as etudiant "timeout 5 $H/depannage/deploy.sh" | grep -qx "DEPLOY OK"', "Le script ne produit pas la ligne « DEPLOY OK »."),
             ]},
            {"id": "24.2", "points": 4, "title": "Disque plein",
             "desc": "Un fichier de log énorme remplit <code>/var/log</code>. Trouvez-le, écrivez son chemin dans <code>~/gros-log.txt</code>, puis <strong>videz-le sans le supprimer</strong> (l'application le garde ouvert).",
             "hints": ["<code>sudo du -ah /var/log | sort -h | tail</code>", "<code>sudo truncate -s 0 fichier</code>"],
             "checks": [
                 ('[ "$(ans $H/gros-log.txt)" = "$LAB_BIGLOG" ]', "~/gros-log.txt ne désigne pas le bon fichier."),
                 ('test -f "$LAB_BIGLOG"', "Le fichier a été supprimé : il fallait le vider."),
                 ('[ "$(stat -c %s "$LAB_BIGLOG")" -lt 1048576 ]', "Le fichier fait encore plus de 1 Mo."),
             ]},
            {"id": "24.3", "points": 5, "title": "SSH refusé",
             "desc": "La commande <code>ssh -i ~/depannage/cle_ops ops@localhost</code> devrait fonctionner : la clé publique est bien dans <code>/home/ops/.ssh/authorized_keys</code>… mais sshd la refuse. Trouvez pourquoi et réparez.",
             "hints": ["sshd refuse les clés si les droits sont trop ouverts (StrictModes). Regardez <code>sudo tail /var/log/auth.log</code>.", "Vérifiez les droits et le propriétaire de /home/ops, de .ssh et de authorized_keys (<code>namei -l</code>)."],
             "checks": [
                 ('grep -qf $H/depannage/cle_ops.pub /home/ops/.ssh/authorized_keys', "La clé publique n'est plus dans authorized_keys."),
                 ('run_as etudiant "ssh -i $H/depannage/cle_ops -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 ops@localhost true"', "La connexion par clé en ops@localhost échoue toujours."),
             ]},
            {"id": "24.4", "points": 5, "title": "La tâche cron fantôme",
             "desc": "La tâche <code>/etc/cron.d/rapport.cron</code> devrait écrire chaque minute dans <code>/var/log/rapport-cron.log</code>, mais le fichier n'apparaît jamais. Réparez (plusieurs erreurs), puis attendez qu'il soit alimenté.",
             "hints": ["Relisez les « pièges classiques » de l'étape cron : nom du fichier, champ utilisateur, chemin absolu…", "…et le script lui-même est-il exécutable ?"],
             "checks": [
                 ('f=/var/log/rapport-cron.log; test -f $f && [ $(( $(date +%s) - $(stat -c %Y $f) )) -lt 150 ]', "/var/log/rapport-cron.log n'est pas alimenté (attendez 1 à 2 minutes après votre correction)."),
             ]},
            {"id": "24.5", "points": 4, "title": "Le service qui refuse de démarrer",
             "desc": "Le service <code>mon-service</code> tourne sous l'utilisateur <code>monsvc</code>. La commande <code>sudo -u monsvc mon-service --check</code> échoue : lisez les messages et corrigez jusqu'à obtenir <code>Configuration OK</code>. Le port attendu est <code>8080</code>.",
             "hints": ["La configuration est dans <code>/etc/mon-service.conf</code>.", "Le dossier de logs doit exister et appartenir à monsvc."],
             "checks": [
                 ('run_as monsvc "timeout 5 /usr/local/bin/mon-service --check"', "« sudo -u monsvc mon-service --check » échoue encore."),
                 ('grep -qx "PORT=8080" /etc/mon-service.conf', "Le port configuré n'est pas 8080."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    25: {
        "title": "Intégration finale : serveur web",
        "description": "Mobilisez tout le parcours pour préparer un serveur web.",
        "lesson": """<h3>Scénario</h3><p>Vous administrez le serveur qui héberge <em>monsite</em>. Vous devez :</p><ol><li>Créer l'utilisateur <code>webmaster</code> et le groupe <code>www</code></li><li>Préparer <code>/var/www/monsite/{html,logs,backup}</code> avec des droits de groupe</li><li>Écrire un script de sauvegarde horodatée avec rotation</li><li>Le planifier avec cron</li><li>Écrire un script de supervision avec seuil d'alerte</li><li>Donner un accès SSH par clé au webmaster</li></ol><div class="tip">Les scripts sont exécutés <strong>en tant que webmaster</strong> lors de la vérification : testez-les avec <code>sudo -u webmaster ...</code>.</div><h3>Rappels utiles</h3><pre>date +%Y%m%d-%H%M%S                    # horodatage pour les noms de fichiers<br>ls -1t site-*.tar.gz | tail -n +8      # tout sauf les 7 plus récents<br>df / | awk 'NR==2{print $5}' | tr -d %  # % d'occupation de /</pre>""",
        "setup": r'''
mkuser intrus
''',
        "exercises": [
            {"id": "25.1", "points": 5, "title": "Environnement web",
             "desc": "Créez <code>webmaster</code> (membre de <code>www</code>) et l'arborescence <code>/var/www/monsite/{html,logs,backup}</code> appartenant au groupe <code>www</code>. Les membres de <code>www</code> peuvent écrire partout dedans, les autres peuvent seulement lire, et les fichiers créés héritent du groupe <code>www</code>.",
             "hints": ["<code>sudo chgrp -R www</code>, <code>sudo chmod -R 2775</code>"],
             "checks": [
                 ('id -nG webmaster | grep -qw www', "webmaster n'existe pas ou n'est pas membre de www."),
                 ('for d in "" /html /logs /backup; do [ "$(stat -c %G /var/www/monsite$d)" = www ] && test -g /var/www/monsite$d || exit 1; done', "monsite et ses sous-dossiers doivent appartenir au groupe www avec le bit setgid."),
                 ('for d in html logs backup; do run_as webmaster "touch /var/www/monsite/$d/.t && rm -f /var/www/monsite/$d/.t" || exit 1; done', "webmaster ne peut pas écrire dans tous les sous-dossiers."),
                 ('run_as intrus "ls /var/www/monsite/html" && ! run_as intrus "touch /var/www/monsite/html/.t"', "Un utilisateur quelconque doit pouvoir lire mais pas écrire dans html/."),
             ]},
            {"id": "25.2", "points": 3, "title": "Contenu web",
             "desc": "En tant que <code>webmaster</code>, créez <code>html/index.html</code> contenant <code>&lt;h1&gt;Bienvenue&lt;/h1&gt;</code> et <code>logs/access.log</code> avec au moins 5 lignes.",
             "hints": ["<code>sudo -u webmaster bash</code> ouvre un shell en tant que webmaster."],
             "checks": [
                 ('grep -q "<h1>Bienvenue</h1>" /var/www/monsite/html/index.html', "index.html est absent ou ne contient pas <h1>Bienvenue</h1>."),
                 ('[ "$(owner /var/www/monsite/html/index.html)" = webmaster ]', "index.html doit appartenir à webmaster."),
                 ('[ "$(wc -l < /var/www/monsite/logs/access.log)" -ge 5 ]', "logs/access.log doit contenir au moins 5 lignes."),
             ]},
            {"id": "25.3", "points": 5, "title": "Sauvegarde horodatée", "manual": True,
             "desc": "Écrivez <code>/home/webmaster/backup.sh</code> (exécutable) qui : crée <code>/var/www/monsite/backup/site-AAAAMMJJ-HHMMSS.tar.gz</code> contenant le dossier <code>html</code>, et écrit la sortie de <code>df -h</code> dans <code>backup/disk-report.txt</code>.",
             "hints": ["<code>tar -czf /var/www/monsite/backup/site-$(date +%Y%m%d-%H%M%S).tar.gz -C /var/www/monsite html</code>"],
             "checks": [
                 ('test -x /home/webmaster/backup.sh', "/home/webmaster/backup.sh n'existe pas ou n'est pas exécutable."),
                 ('touch /tmp/.lab-t && sleep 1 && run_as webmaster "cd /tmp && timeout 20 /home/webmaster/backup.sh" && f=$(find /var/www/monsite/backup -name "site-$(date +%Y%m%d)-*.tar.gz" -newer /tmp/.lab-t | head -n1) && [ -n "$f" ] && tar -tzf "$f" | grep -q "index.html"', "Exécuté par webmaster, le script ne produit pas d'archive site-AAAAMMJJ-HHMMSS.tar.gz contenant index.html."),
                 ('[ /var/www/monsite/backup/disk-report.txt -nt /tmp/.lab-t ] && grep -qi filesystem /var/www/monsite/backup/disk-report.txt', "backup/disk-report.txt n'est pas (re)généré avec la sortie de df -h."),
             ]},
            {"id": "25.4", "points": 3, "title": "Planifier la sauvegarde",
             "desc": "Créez <code>/etc/cron.d/backup-web</code> pour que <code>webmaster</code> exécute <code>backup.sh</code> chaque jour à 3h00.",
             "checks": [
                 ('grep -qE "^0\\s+3\\s+\\*\\s+\\*\\s+\\*\\s+webmaster\\s+/home/webmaster/backup\\.sh" /etc/cron.d/backup-web', "La ligne cron n'est pas correcte (horaire, utilisateur webmaster, chemin absolu)."),
             ]},
            {"id": "25.5", "points": 5, "title": "Rotation des sauvegardes", "manual": True,
             "desc": "Complétez <code>backup.sh</code> pour qu'il ne conserve que les <strong>7 archives les plus récentes</strong> dans <code>backup/</code>.",
             "hints": ["<code>ls -1t .../site-*.tar.gz | tail -n +8 | xargs -r rm -f</code>"],
             "checks": [
                 ('b=/var/www/monsite/backup; for i in 0 1 2 3 4 5 6 7 8 9; do f=$b/site-2020010$i-000000.tar.gz; cp /dev/null $f; touch -d "$((20 - i)) days ago" $f; chgrp www $f; done; run_as webmaster "cd /tmp && timeout 20 /home/webmaster/backup.sh"; [ "$(ls $b/site-*.tar.gz | wc -l)" -le 7 ] && ls $b | grep -q "site-$(date +%Y%m%d)" && [ ! -e $b/site-20200100-000000.tar.gz ]', "Après ajout de 10 vieilles archives et exécution, il reste plus de 7 archives (ou la plus récente a disparu)."),
             ]},
            {"id": "25.6", "points": 5, "title": "Supervision avec seuil", "manual": True,
             "desc": "Écrivez <code>/home/webmaster/monitoring.sh SEUIL</code> : si le taux d'occupation de <code>/</code> (en %) dépasse <code>SEUIL</code>, il affiche une ligne contenant <code>ALERTE</code>, sinon une ligne contenant <code>OK</code>. Dans les deux cas, il ajoute cette ligne, horodatée, à <code>/var/www/monsite/logs/monitoring.txt</code>.",
             "hints": ["<code>u=$(df / | awk 'NR==2{print $5}' | tr -d %)</code>", "<code>if [ \"$u\" -gt \"$1\" ]; then ...</code>"],
             "checks": [
                 ('test -x /home/webmaster/monitoring.sh', "/home/webmaster/monitoring.sh n'existe pas ou n'est pas exécutable."),
                 ('run_as webmaster "timeout 10 /home/webmaster/monitoring.sh 0" | grep -q ALERTE && ! run_as webmaster "timeout 10 /home/webmaster/monitoring.sh 100" | grep -q ALERTE && run_as webmaster "timeout 10 /home/webmaster/monitoring.sh 100" | grep -q OK', "Avec un seuil de 0 il faut ALERTE, avec un seuil de 100 il faut OK."),
                 ('f=/var/www/monsite/logs/monitoring.txt; n=$(cat $f 2>/dev/null | wc -l); run_as webmaster "timeout 10 /home/webmaster/monitoring.sh 100" >/dev/null; [ "$(wc -l < $f)" -eq $((n + 1)) ] && tail -n1 $f | grep -q "$(date +%Y)"', "Chaque exécution doit ajouter une ligne horodatée à logs/monitoring.txt."),
             ]},
            {"id": "25.7", "points": 4, "title": "Accès SSH du webmaster",
             "desc": "Faites en sorte que vous (etudiant) puissiez vous connecter en <code>webmaster@localhost</code> avec votre clé SSH.",
             "hints": ["Si vous avez désactivé les mots de passe dans sshd, <code>ssh-copy-id</code> ne marchera pas : installez la clé à la main (avec sudo), en respectant les droits exigés par sshd."],
             "checks": [
                 ('run_as etudiant "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 webmaster@localhost true"', "La connexion par clé à webmaster@localhost échoue."),
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
