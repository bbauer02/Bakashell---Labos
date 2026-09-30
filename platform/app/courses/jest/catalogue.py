"""Parcours « Tests unitaires avec Jest » (niveau avancé).

Même format que le catalogue Linux (courses/linux/catalogue.py). Les vérifications s'appuient sur le correcteur de l'image
jest-lab (/opt/jest-lab/verifier.js) :
  - pass      : les tests de l'étudiant passent sur le code de référence (ou le sien, ou une version boguée),
                éventuellement dans plusieurs ordres, chacun isolément, dans un autre fuseau horaire… ;
  - kill      : ils échouent contre chaque mutant (version boguée) d'un jeu défini dans
                images/jest/mutants.json — c'est ce qui prouve qu'ils testent vraiment quelque chose ;
  - survive   : ils passent sur des variantes CORRECTES du code (ils n'exigent pas plus que la règle) ;
  - hidden    : des tests cachés valident le code écrit par l'étudiant (TDD, corrections de bugs) ;
  - reproduce : un test doit échouer sur la version boguée signalée (ou sur la version corrigée) ;
  - coverage / suite / config / workflow : couverture, suite complète, configuration Jest, CI.
Toutes les vérifications exécutent du code : elles sont « manuelles » (sur clic).

Exercices non transmissibles : certaines données métier (longueur minimale de recherche, grille de livraison,
codes promo, délais de relance et d'attente, règles de fidélité) sont tirées au sort à la mise en place
(`tirer`, variantes décrites dans images/jest/variantes.json). Le code de référence, les mutants et les tests
cachés suivent la variante de l'étudiant : un fichier de tests copié chez un voisin échoue.
"""

EXERCISES_VERSION = "1"

MENTOR = "nadia"

SETUP_PRELUDE = r'''
set -e
H=/home/etudiant
P=$H/boutique
emit() { echo "@$1=$2"; }
livrer() { node /opt/jest-lab/verifier.js deliver "$@"; }
# tirer CLE N fichier… : variante des données métier de l'étudiant (tirée une fois pour toutes, puis conservée ;
# LAB_VARIANTE_<CLE> l'impose, pour les tests du parcours). À appeler avant de livrer les fichiers concernés.
tirer() { local f="LAB_VARIANTE_$1"; node /opt/jest-lab/verifier.js variante "$1" "${!f:-$((RANDOM % $2))}" "${@:3}" ${!f:+--force}; }
'''

CHECK_PRELUDE = r'''
H=/home/etudiant
P=$H/boutique
# Le correcteur reçoit les variantes de l'étudiant enregistrées par la plateforme (LAB_VARIANTE_<CLE>)
_variantes() { local v; for v in ${!LAB_VARIANTE_@}; do printf '%s=%s,' "${v#LAB_VARIANTE_}" "${!v}"; done; }
verif() { node /opt/jest-lab/verifier.js "$@" --variantes "$(_variantes)"; }
# Recherche dans un fichier du projet (commentaires exclus pour les fichiers .js)
has() { node /opt/jest-lab/verifier.js grep "$1" "$2"; }
pkg() { node -p "try { const p = require('$P/package.json'); String($1) } catch (e) { '' }" 2>/dev/null; }
'''

# Tests focalisés ou désactivés : test.only, describe.skip.each, test.concurrent.only, fit, xit…
FOCUS_SKIP = r"(^|[^\w$.])(fit|fdescribe|xit|xtest|xdescribe)\s*\(|\b(test|it|describe)(\.\w+)*\.(only|skip)\b"

INTRO = """<div class="scenario"><h3>Nouvelle mission chez Cimes &amp; Sentiers</h3><p>La boutique en ligne grossit, et chaque mise en production casse quelque chose : un prix mal arrondi, une livraison offerte à tort, un code promo accepté la veille de son expiration… <strong>Nadia Haddad</strong>, lead développeuse, vous confie la qualité du code métier (<code>~/boutique</code>) : écrire des tests unitaires avec <strong>Jest</strong>, puis faire en sorte qu'aucune régression ne passe.</p><p><strong>Comment vos tests sont évalués</strong> : ils sont exécutés sur le code de référence (ils doivent passer), puis sur des <strong>versions volontairement boguées</strong> du même code (« mutants »), qu'ils doivent toutes détecter. Un test qui passe toujours ne protège de rien. Parfois, ils sont aussi exécutés sur des versions <strong>correctes mais différentes</strong> du code : un test trop exigeant, qui casse sans raison, est un mauvais test.</p><p>Quand des défauts échappent à vos tests, la vérification indique combien ; elle en décrit un à partir de la 3<sup>e</sup> vérification ratée. Cherchez d'abord par vous-même : c'est tout l'exercice.</p><p>Certaines données métier (tarifs, seuils, codes promo, délais…) diffèrent d'un projet à l'autre : les valeurs attendues se déduisent de <strong>votre</strong> code et de ses commentaires, et les tests d'un voisin ne passeront pas chez vous.</p><p>Éditez les fichiers dans l'éditeur (<kbd>Ctrl+S</kbd> pour enregistrer) et lancez <code>npx jest</code> dans le terminal. Les vérifications exécutent vos tests : cliquez sur <strong>Vérifier</strong> quand vous êtes prêt·e.</p></div>"""

STEPS = {
    # ─────────────────────────────────────────────────────────────────────
    1: {
        "title": "Jour 1 — La CI est rouge",
        "description": "Prise en main de Jest. Compétences : test, expect, describe, toBe, toBeCloseTo, flottants, scripts npm.",
        "lesson": INTRO + """<h3>Anatomie d'un test</h3><pre>const { calculerTTC } = require('../src/prix');<br><br>describe('calculerTTC', () =&gt; {<br>  test('ajoute 20 % de TVA', () =&gt; {<br>    expect(calculerTTC(100)).toBe(120);<br>  });<br>});</pre><p>Jest trouve seul les fichiers <code>*.test.js</code>. Un test échoue dans deux cas seulement : un <strong>matcher</strong> (<code>toBe</code>, <code>toEqual</code>…) est appelé et n'est pas satisfait, ou une exception non attendue s'échappe du test. Tout le reste est vert.</p><div class="tip">Un test que vous n'avez jamais vu échouer ne prouve rien. Cassez volontairement le code (ou la valeur attendue) : le test doit devenir rouge. Et une valeur attendue se calcule <strong>à partir de la règle métier</strong>, jamais avec le code que l'on teste.</div><h3>Égalité et nombres à virgule</h3><ul><li><code>toBe</code> — égalité stricte (<code>Object.is</code>) : parfait pour les primitives</li><li><code>toEqual</code> / <code>toStrictEqual</code> — égalité de structure (objets, tableaux)</li><li><code>toBeCloseTo(x, chiffres)</code> — tolérance pour les flottants (2 chiffres par défaut : écart &lt; 0,005)</li></ul><p>Les nombres sont stockés en binaire sur 64 bits : la plupart des décimaux n'ont pas de représentation exacte. <code>0.1 + 0.2</code> vaut <code>0.30000000000000004</code>, et <code>(1.005).toPrecision(20)</code> révèle que 1,005 est en réalité stocké comme 1,00499999999999989…</p><div class="tip">Si la règle métier dit « arrondi au centime », le test doit vérifier <strong>la valeur arrondie exacte</strong>. Une tolérance trop large laisserait passer un code qui n'arrondit pas.</div><h3>Lancer les tests</h3><pre>npx jest                    # toute la suite<br>npx jest tests/prix         # les fichiers dont le chemin correspond à l'expression « tests/prix »<br>npx jest -t "TVA"           # les tests dont le nom contient « TVA »</pre><table class="lesson-table"><tr><th>Option</th><th>Effet</th></tr><tr><td><code>--watchAll</code></td><td>relance toute la suite à chaque sauvegarde (interactif : <kbd>q</kbd> pour quitter)</td></tr><tr><td><code>--watch</code></td><td>relance seulement les tests concernés par les fichiers modifiés depuis le dernier commit : Jest le demande à git</td></tr><tr><td><code>--ci</code></td><td>mode intégration continue : jamais interactif, et un snapshot absent fait échouer au lieu d'être créé</td></tr><tr><td><code>--coverage</code></td><td>mesure la couverture de code (jour 8)</td></tr></table><h3>Scripts npm</h3><p>Dans <code>package.json</code>, la section <code>scripts</code> standardise les commandes de l'équipe :</p><pre>"scripts": {<br>  "start": "node src/serveur.js",<br>  "lint": "eslint src"<br>}</pre><p>Puis <code>npm start</code>, <code>npm test</code> (raccourcis) ou <code>npm run lint</code>. Tout ce qui suit <code>--</code> est transmis au script : <code>npm test -- -t TVA</code>.</p>""",
        "setup": r'''
livrer package.json package-lock.json .gitignore README.md src/prix.js tests/prix.test.js tests/remise.test.js
''',
        "exercises": [
            {"id": "J1.1", "points": 4, "title": "Le test qui ment", "manual": True,
             "ticket": {"from": "thomas", "body": "La CI est rouge depuis ce matin sur <code>tests/prix.test.js</code>. Je te jure que <code>calculerTTC</code> est juste : la règle, c'est un prix TTC <strong>arrondi au centime</strong>. C'est mon test qui est faux… tu peux le corriger ? Sans toucher au code, et sans supprimer le test, hein 😅"},
             "desc": "<code>tests/prix.test.js</code> passe, garde ses 3 tests (dont celui de l'article à 19,99 € HT) et détecte un calcul de TTC mal arrondi.",
             "hints": ["Lancez <code>npx jest tests/prix</code> et lisez la différence entre <em>Expected</em> et <em>Received</em> : lequel des deux respecte la règle ?", "Quel arrondi la règle impose-t-elle ? Faites le calcul à la main, sans passer par JavaScript : c'est cette valeur que le test doit attendre."],
             "checks": [
                 ('has tests/prix.test.js "(^|[^0-9.])19\\.99([^0-9]|$)"', "Le test de l'article à 19,99 € HT a disparu : il fallait le corriger, pas le supprimer."),
                 ('verif pass --tests tests/prix.test.js --min 3', "tests/prix.test.js ne passe pas avec le code de référence."),
                 ('verif kill --tests tests/prix.test.js --set prix-ttc', "Le test corrigé est trop permissif."),
             ]},
            {"id": "J1.2", "points": 2, "title": "Des commandes pour toute l'équipe", "manual": True,
             "ticket": {"from": "thomas", "body": "J'ai ajouté des scripts npm dans <code>package.json</code>, mais rien ne marche : dans la CI, <code>npm test</code> ne rend jamais la main (le job est tué au bout d'une heure), et chez moi <code>npm run test:watch</code> s'arrête aussitôt avec un message bizarre. Nadia veut aussi un script <code>test:ci</code> pour l'intégration continue. Tu regardes ?"},
             "desc": "Dans <code>package.json</code> : <code>npm test</code> lance la suite une seule fois et rend la main ; <code>npm run test:watch</code> relance les tests à chaque sauvegarde et fonctionne dans <code>~/boutique</code> ; <code>npm run test:ci</code> lance la suite en mode intégration continue.",
             "hints": ["Lancez chaque script et lisez ce qu'il affiche. Quelle option de Jest rend la main, laquelle attend vos sauvegardes ?", "Relisez le tableau des options du cours : de quoi <code>--watch</code> a-t-il besoin pour savoir ce qui a changé ? <code>~/boutique</code> l'a-t-il ?"],
             "checks": [
                 ('node -e "require(\'$P/package.json\')"', "package.json n'est plus un JSON valide."),
                 ('t="$(pkg \'p.scripts.test\')"; echo "$t" | grep -qE "^(CI=(true|1) )?(npx )?jest( |$)" && ! echo "$t" | grep -qE -- "--watch(All)?(=true)?( |$)"', "Le script « test » doit lancer jest une seule fois, sans mode surveillance : dans la CI, npm test doit rendre la main."),
                 ('w="$(pkg \'p.scripts["test:watch"]\')"; echo "$w" | grep -qE -- "--watchAll( |$)" || { echo "$w" | grep -qE -- "--watch( |$)" && [ -d $P/.git ]; }', "Le script « test:watch » ne fonctionne pas dans ~/boutique : lancez npm run test:watch et lisez le message d'erreur."),
                 ('c="$(pkg \'p.scripts["test:ci"]\')"; echo "$c" | grep -qE "^((CI=(true|1) )?(npx )?jest|npm (run )?test --)( |$)" && echo "$c" | grep -qE -- "(^CI=(true|1) |--ci( |$))" && ! echo "$c" | grep -qE -- "--watch(All)?(=true)?( |$)"', "Le script « test:ci » doit lancer jest en mode intégration continue (option --ci)."),
             ]},
            {"id": "J1.3", "points": 5, "title": "Arrondi commercial", "manual": True,
             "ticket": {"from": "diallo", "body": "Bonjour, ici la compta. La fonction <code>arrondir</code> de <code>src/prix.js</code> sert pour toutes nos factures. Je veux la garantie qu'elle arrondit <strong>au centime le plus proche</strong>, les demi-centimes vers le haut, y compris dans les cas piégeux : 1,005 € doit donner 1,01 € (le précédent logiciel donnait 1,00 € et on a eu un contrôle fiscal)."},
             "desc": "Un fichier <code>tests/arrondir.test.js</code> (au moins 3 tests) qui passe et détecte toutes les variantes d'arrondi erronées.",
             "hints": ["Quelles erreurs un développeur pressé pourrait-il commettre en écrivant un arrondi ? Chacune mérite un cas qui la démasque.", "Un cas qui doit arrondir vers le bas, un autre vers le haut, le piège 1,005… et un montant qui ne doit pas bouger du tout."],
             "checks": [
                 ('verif pass --tests tests/arrondir.test.js --min 3', "tests/arrondir.test.js est absent, ne passe pas ou contient moins de 3 tests."),
                 ('verif kill --tests tests/arrondir.test.js --set arrondir', "Vos tests ne détectent pas toutes les erreurs d'arrondi."),
             ]},
            {"id": "J1.4", "points": 5, "title": "Des tests qui ne testent rien", "manual": True,
             "ticket": {"from": "thomas", "body": "J'ai écrit <code>tests/remise.test.js</code> pour <code>appliquerRemise</code> : 4 tests, tout est vert, 100 % de couverture. Nadia l'a relu et m'a juste répondu « aucun de ces tests ne peut échouer ». Hein ?! Tu peux regarder ? Garde mes 4 tests, mais fais-en de vrais tests."},
             "desc": "<code>tests/remise.test.js</code> garde au moins ses 4 tests, passe, et détecte toute erreur de calcul, d'arrondi ou de validation dans <code>appliquerRemise</code>.",
             "hints": ["Pour chaque test, demandez-vous : si <code>appliquerRemise</code> renvoyait n'importe quoi, ce test deviendrait-il rouge ? Essayez : cassez le code et relancez.", "Relisez dans le cours les deux seules façons dont un test peut échouer, et d'où doit venir une valeur attendue."],
             "checks": [
                 ('verif pass --tests tests/remise.test.js --min 4', "tests/remise.test.js ne passe pas, ou contient moins de 4 tests : il fallait réparer ceux de Thomas, pas les supprimer."),
                 ('verif kill --tests tests/remise.test.js --set remise', "Certains tests ne peuvent toujours pas échouer."),
             ]},
            {"id": "J1.5", "points": 6, "title": "Le contrôle fiscal revient", "manual": True,
             "ticket": {"from": "diallo", "body": "Notre prestataire veut remplacer <code>arrondir</code> par « sa » version, qu'il dit éprouvée : <code>Math.round((montant + Number.EPSILON) * 100) / 100</code>. Il jure qu'elle gère 1,005 €, et c'est vrai. Mais je n'ai pas confiance : j'ai déjà payé une amende. Avant de lui dire non, il me faut une <strong>preuve</strong> : un test qui passe avec notre fonction actuelle et qui échoue avec la sienne."},
             "desc": "<code>tests/arrondir-prestataire.test.js</code> passe avec le code actuel et échoue avec la version proposée par le prestataire.",
             "hints": ["Pourquoi ajouter <code>Number.EPSILON</code> suffit-il pour 1,005 ? Cet ajout aurait-il le même effet sur un montant de 10 € que sur un montant de 1 € ?", "Inutile de deviner : dans <code>node</code>, comparez les deux versions sur tous les montants en x,xx5 entre 0 et 100 € avec une boucle. La valeur attendue, elle, se déduit de la règle."],
             "checks": [
                 ('verif pass --tests tests/arrondir-prestataire.test.js', "tests/arrondir-prestataire.test.js est absent ou ne passe pas avec la fonction actuelle."),
                 ('verif kill --tests tests/arrondir-prestataire.test.js --set arrondir-epsilon --no-hint', "Votre test passe aussi avec la version du prestataire : ce n'est pas encore une preuve."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Jour 2 — Le panier",
        "description": "Choisir le bon matcher. Compétences : toEqual, toStrictEqual, toMatchObject, toContainEqual, toHaveLength, toThrow, tests ni trop laxistes ni trop stricts.",
        "lesson": """<h3>Matchers de structure</h3><table class="lesson-table"><tr><th>Matcher</th><th>Usage</th></tr><tr><td><code>toEqual(obj)</code></td><td>Même structure, récursivement. Ignore les propriétés valant <code>undefined</code> et la classe des objets</td></tr><tr><td><code>toStrictEqual(obj)</code></td><td>Même structure, en tenant compte aussi des propriétés <code>undefined</code>, de la classe des objets et des trous dans les tableaux</td></tr><tr><td><code>toMatchObject(partiel)</code></td><td>Contient au moins ces propriétés (les autres sont ignorées)</td></tr><tr><td><code>toContainEqual(item)</code></td><td>Un tableau contient un élément de cette structure</td></tr><tr><td><code>toHaveLength(n)</code></td><td>Longueur d'un tableau ou d'une chaîne</td></tr><tr><td><code>not</code></td><td>Inverse : <code>expect(x).not.toBe(y)</code></td></tr></table><h3>Tester une exception</h3><pre>expect(() =&gt; panier.ajouter(gourde, 0)).toThrow(RangeError);<br>expect(() =&gt; panier.ajouter(gourde, 0)).toThrow('Quantité invalide');</pre><div class="tip">On passe une <strong>fonction</strong> à <code>expect</code>. <code>expect(panier.ajouter(gourde, 0))</code> lèverait l'exception avant même que Jest puisse l'attraper.</div><h3>Encapsulation</h3><p>Une méthode qui renvoie des données internes doit renvoyer une <strong>copie</strong> (copie défensive) : un appelant ne doit pas pouvoir modifier l'état d'un objet sans passer par ses méthodes.</p><h3>Ni trop laxiste, ni trop strict</h3><p>Un bon test échoue quand la règle est violée… <strong>et seulement dans ce cas</strong>. Un test trop laxiste laisse passer des bugs ; un test trop strict casse sur une implémentation correcte (il fige un détail que la règle ne garantit pas : un ordre, une formulation, une structure interne) et finit désactivé.</p><pre>expect(resultats).toHaveLength(2);<br>expect(resultats).toContainEqual({ ref: 'A', libelle: 'Gourde' });<br>expect(resultats).toEqual(expect.arrayContaining([...]));</pre><h3>Bonnes pratiques</h3><ul><li>Un test = un comportement, avec un nom qui le décrit (« cumule les quantités d'une même référence »).</li><li>Structure <em>Arrange / Act / Assert</em> : préparer, agir, vérifier.</li><li>Testez aussi les cas limites et les erreurs, pas seulement le cas nominal.</li></ul>""",
        "setup": r'''
v=$(tirer J2_5 3 src/catalogue.js)
emit VARIANTE_J2_5 "$v"
livrer src/panier.js src/catalogue.js
''',
        "exercises": [
            {"id": "J2.1", "points": 5, "title": "Le panier sous contrôle", "manual": True,
             "ticket": {"from": "nadia", "body": "<code>src/panier.js</code> n'a aucun test et tout le tunnel de commande repose dessus. Couvre son comportement : ajout, cumul d'une même référence, quantité par défaut, retrait, nombre d'articles, total HT, panier vide."},
             "desc": "<code>tests/panier.test.js</code> (au moins 5 tests) qui passe et détecte les régressions du panier.",
             "hints": ["Lisez attentivement <code>src/panier.js</code> : chaque méthode porte une règle à vérifier.", "Utilisez au moins deux produits différents, des quantités supérieures à 1, et ajoutez plusieurs fois la même référence."],
             "checks": [
                 ('verif pass --tests tests/panier.test.js --min 5', "tests/panier.test.js est absent, ne passe pas ou contient moins de 5 tests."),
                 ('verif kill --tests tests/panier.test.js --set panier-base', "Vos tests ne détectent pas toutes les régressions du panier."),
             ]},
            {"id": "J2.2", "points": 5, "title": "Les cas d'erreur", "manual": True,
             "ticket": {"from": "thomas", "body": "Hier, un client a commandé 0 sac à dos, et un autre 1,5 lampe frontale. Il nous faut des tests sur <strong>toutes les erreurs</strong> : quantités invalides, retrait d'un produit absent, remises hors de 0–100 %, prix HT négatif. Et vérifie le <strong>type</strong> d'erreur, avec <code>toThrow</code> : le front affiche un message différent pour une <code>RangeError</code>. Attention quand même : une remise de 0 % ou de 100 %, c'est permis."},
             "desc": "<code>tests/erreurs.test.js</code>, utilisant <code>toThrow</code>, qui passe et détecte chaque validation manquante, trop stricte ou mal typée.",
             "hints": ["Pour chaque validation, cherchez la frontière exacte entre accepté et refusé, et testez des deux côtés.", "Le type d'erreur se lit dans le code : ne supposez pas qu'il est le même partout."],
             "checks": [
                 ('has tests/erreurs.test.js "toThrow"', "tests/erreurs.test.js doit utiliser toThrow."),
                 ('verif pass --tests tests/erreurs.test.js', "tests/erreurs.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/erreurs.test.js --set panier-erreurs', "Vos tests ne détectent pas toutes les validations manquantes ou erronées."),
             ]},
            {"id": "J2.3", "points": 4, "title": "Fuite de données", "manual": True,
             "ticket": {"from": "nadia", "body": "Un bug vicieux en production : un composant du front modifiait les lignes renvoyées par <code>panier.lignes()</code>… et ça modifiait le vrai panier. C'est corrigé, mais je veux un test qui l'empêche de revenir. Vérifie aussi la structure exacte d'une ligne, avec <code>toEqual</code> ou <code>toStrictEqual</code>."},
             "desc": "<code>tests/panier-lignes.test.js</code>, utilisant <code>toEqual</code> ou <code>toStrictEqual</code>, qui détecte toute fuite de l'état interne et toute ligne mal construite.",
             "hints": ["Qu'est-ce qu'un appelant pourrait modifier dans ce qui lui est renvoyé ? Il y a deux niveaux.", "Après la modification, relisez l'état du panier par une autre méthode : a-t-il bougé ?"],
             "checks": [
                 ('has tests/panier-lignes.test.js "to(Strict)?Equal"', "tests/panier-lignes.test.js doit utiliser toEqual ou toStrictEqual."),
                 ('verif pass --tests tests/panier-lignes.test.js', "tests/panier-lignes.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/panier-lignes.test.js --set panier-lignes', "Vos tests ne détectent pas toutes les fuites de l'état interne."),
             ]},
            {"id": "J2.4", "points": 4, "title": "Une colonne « undefined »", "manual": True,
             "ticket": {"from": "thomas", "body": "L'appli mobile a affiché une colonne « undefined » dans le panier pendant deux jours, et le module d'export plantait sur des lignes qui « n'étaient pas des objets simples ». C'est réparé. Le pire ? Notre test de structure des lignes est resté vert pendant tout ce temps. Il me faut un test qui aurait vu ces deux problèmes."},
             "desc": "<code>tests/panier-api.test.js</code> passe et garantit qu'une ligne du panier est exactement un objet simple <code>{ ref, libelle, prixHT, quantite }</code>, sans aucune propriété de plus.",
             "hints": ["Relisez dans le cours ce que chaque matcher d'égalité <strong>ignore</strong>.", "Un seul matcher d'égalité tient compte des propriétés qui valent <code>undefined</code> et de la classe d'un objet."],
             "checks": [
                 ('verif pass --tests tests/panier-api.test.js', "tests/panier-api.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/panier-api.test.js --set panier-strict', "Votre test ne voit pas tous les écarts de structure."),
             ]},
            {"id": "J2.5", "points": 6, "title": "Recherche dans le catalogue", "manual": True,
             "ticket": {"from": "sophie", "body": "La recherche du site (<code>rechercher</code>, dans <code>src/catalogue.js</code>) va être branchée sur un moteur externe le mois prochain : il renverra les mêmes produits, mais <strong>pas forcément dans le même ordre</strong>. Écris dès maintenant des tests qui attrapent toute erreur de filtrage… et qui resteront verts le jour de la bascule."},
             "desc": "<code>tests/catalogue.test.js</code> (au moins 4 tests) passe, détecte les erreurs de filtrage de <code>rechercher</code>, et passe aussi sur toute implémentation correcte qui renvoie les résultats dans un autre ordre.",
             "hints": ["Relisez le commentaire de <code>rechercher</code> : chaque phrase est une règle, et chaque règle a ses cas limites.", "L'ordre fait-il partie de la règle ? Vérifiez <em>combien</em> de résultats et <em>lesquels</em>, sans imposer leur position."],
             "checks": [
                 ('verif pass --tests tests/catalogue.test.js --min 4', "tests/catalogue.test.js est absent, ne passe pas ou contient moins de 4 tests."),
                 ('verif kill --tests tests/catalogue.test.js --set catalogue', "Vos tests ne détectent pas toutes les erreurs de filtrage."),
                 ('verif survive --tests tests/catalogue.test.js --set catalogue-ordre', "Vos tests cassent sur une implémentation correcte."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Jour 3 — Livraison : les cas limites",
        "description": "Tests paramétrés et isolation. Compétences : test.each, describe.each, valeurs limites, beforeEach, --randomize, état d'un module.",
        "lesson": """<h3>Tests paramétrés</h3><pre>test.each([<br>  [100, 120],<br>  [0, 0],<br>])('calculerTTC(%s) vaut %s', (prixHT, attendu) =&gt; {<br>  expect(calculerTTC(prixHT)).toBe(attendu);<br>});</pre><p>Variante avec des objets et des noms lisibles :</p><pre>test.each([<br>  { prixHT: 10, taux: 0.055, attendu: 10.55 },<br>])('$prixHT € HT à $taux', ({ prixHT, taux, attendu }) =&gt; { ... });</pre><p><code>describe.each</code> accepte le même tableau et génère un <strong>bloc</strong> de tests par ligne (par exemple un bloc par pays, contenant plusieurs tests).</p><h3>Analyse des valeurs limites</h3><p>Les bugs se cachent aux frontières : pour une règle « moins de 1 kg », testez <strong>juste en dessous, pile sur la limite, juste au-dessus</strong> (0,99 · 1 · 1,01). Une règle <code>&lt;</code> écrite <code>&lt;=</code> par erreur ne se voit que sur la limite exacte.</p><h3>Isolation des tests</h3><p>Chaque test doit pouvoir s'exécuter <strong>seul</strong> (<code>npx jest -t "nom du test"</code>) et dans n'importe quel ordre. Un état partagé entre tests (une variable créée une seule fois en haut du fichier) crée des dépendances cachées.</p><pre>let panier;<br>beforeEach(() =&gt; {<br>  panier = new Panier();<br>});</pre><p>Autres hooks : <code>afterEach</code>, <code>beforeAll</code>, <code>afterAll</code>.</p><div class="tip">Par défaut, Jest exécute les tests d'un fichier dans l'ordre où ils sont écrits. <code>npx jest --randomize</code> les mélange (la graine utilisée est affichée) : idéal pour débusquer les tests dépendants. <code>npx jest --randomize --seed=42</code> rejoue exactement le même ordre.</div><h3>L'état caché dans un module</h3><p><code>require</code> met les modules en cache : une variable déclarée au niveau d'un module (un compteur, un cache…) est partagée par tous les tests d'un même fichier, et survit de l'un à l'autre. Jest sait repartir d'un registre de modules neuf :</p><ul><li><code>jest.resetModules()</code> vide le cache : les <code>require</code> <em>suivants</em> rechargent les modules ;</li><li><code>jest.isolateModules(fn)</code> charge, le temps de <code>fn</code>, les modules dans un registre à part.</li></ul>""",
        "setup": r'''
v=$(tirer J3_1 4 src/livraison.js)
emit VARIANTE_J3_1 "$v"
livrer src/livraison.js tests/panier-thomas.test.js src/numerotation.js tests/numerotation.test.js
''',
        "exercises": [
            {"id": "J3.1", "points": 6, "title": "La grille tarifaire", "manual": True,
             "ticket": {"from": "sophie", "body": "Le transporteur a changé ses tarifs et <code>src/livraison.js</code> a été réécrit en urgence. Avant la mise en ligne, je veux la grille <strong>entièrement</strong> vérifiée : chaque tranche de poids, chaque pays, les seuils de livraison offerte, et les cas refusés, en tests paramétrés (<code>test.each</code> ou <code>describe.each</code>), pas en 40 copier-coller. Les commentaires du fichier font foi."},
             "desc": "<code>tests/livraison.test.js</code> utilisant <code>test.each</code> (ou <code>describe.each</code>), qui passe et détecte toutes les erreurs de grille, de limites et de seuils.",
             "hints": ["Faites la liste des limites de la grille (poids et montants) et des pays : chaque élément de la liste mérite au moins un cas.", "N'oubliez pas les cas refusés, ni la seconde fonction du module."],
             "checks": [
                 ('has tests/livraison.test.js "\\.each"', "tests/livraison.test.js doit utiliser test.each (ou it.each / describe.each)."),
                 ('verif pass --tests tests/livraison.test.js --min 8', "tests/livraison.test.js est absent, ne passe pas ou contient moins de 8 tests."),
                 ('verif kill --tests tests/livraison.test.js --set livraison', "Vos tests ne détectent pas toutes les erreurs de la grille tarifaire."),
             ]},
            {"id": "J3.2", "points": 4, "title": "« Ils passent chez moi »", "manual": True,
             "ticket": {"from": "thomas", "body": "La CI lance maintenant les tests avec <code>jest --randomize</code>, et <code>tests/panier-thomas.test.js</code> y échoue une fois sur deux, alors que chez moi tout est vert ! Nadia dit que mes tests « dépendent de leur ordre ». Tu peux les réparer, sans en supprimer et sans les affaiblir ? Règle de l'équipe : un <code>beforeEach</code> fournit à chaque test un panier neuf."},
             "desc": "<code>tests/panier-thomas.test.js</code> garde au moins 5 tests qui vérifient toujours le panier, utilise <code>beforeEach</code>, et chaque test passe seul comme dans n'importe quel ordre.",
             "hints": ["Lancez <code>npx jest tests/panier-thomas --randomize</code> plusieurs fois, puis chaque test seul avec <code>-t</code>. Qu'est-ce qu'un test suppose sans le préparer lui-même ?", "Chaque test doit partir d'un panier neuf et préparer lui-même ce dont il a besoin, sans perdre ses vérifications."],
             "checks": [
                 ('has tests/panier-thomas.test.js "beforeEach"', "tests/panier-thomas.test.js doit utiliser beforeEach."),
                 ('verif pass --tests tests/panier-thomas.test.js --min 5 --isolate', "Les tests ne passent pas, ne passent pas chacun seul, ou il en reste moins de 5."),
                 ('verif pass --tests tests/panier-thomas.test.js --seeds 1,2,3,4', "Les tests échouent quand on change leur ordre d'exécution."),
                 ('verif kill --tests tests/panier-thomas.test.js --set panier-thomas', "Les tests ne vérifient plus tout ce qu'ils vérifiaient : il fallait les réparer, pas les vider."),
             ]},
            {"id": "J3.3", "points": 6, "title": "Le compteur partagé", "manual": True,
             "ticket": {"from": "sophie", "body": "Les numéros de commande viennent de <code>src/numerotation.js</code>. Thomas a écrit <code>tests/numerotation.test.js</code>, vert dans l'ordre… mais impossible de lancer un test seul, et la CI (<code>--randomize</code>) est rouge une fois sur deux. Interdiction d'ajouter au module une fonction de remise à zéro « pour les tests » : le module est très bien comme il est. Répare les tests."},
             "desc": "<code>tests/numerotation.test.js</code> garde au moins 3 tests ; chacun passe seul et dans n'importe quel ordre, sans modifier <code>src/numerotation.js</code>, et les tests détectent toute erreur de numérotation.",
             "hints": ["Où vit l'état qui passe d'un test à l'autre ? Pas dans le fichier de test : dans le module testé.", "Relisez la fin du cours : comment obtenir, pour chaque test, un module tout neuf ? Attention à ce que référence <code>prochainNumero</code> après coup."],
             "checks": [
                 ('verif pass --tests tests/numerotation.test.js --min 3 --isolate', "Les tests ne passent pas, ne passent pas chacun seul, ou il en reste moins de 3."),
                 ('verif pass --tests tests/numerotation.test.js --seeds 1,2,3,4', "Les tests échouent quand on change leur ordre d'exécution."),
                 ('verif kill --tests tests/numerotation.test.js --set numerotation', "Vos tests ne détectent pas toutes les erreurs de numérotation."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Jour 4 — TDD : les codes promo",
        "description": "Développement piloté par les tests. Compétences : tests d'après une spécification, maîtrise des dates et des fuseaux horaires, Red-Green-Refactor.",
        "lesson": """<h3>Le cycle TDD</h3><ol><li><strong>Red</strong> : écrire un test qui échoue, pour un comportement pas encore codé.</li><li><strong>Green</strong> : écrire le code le plus simple qui le fait passer.</li><li><strong>Refactor</strong> : améliorer le code, les tests restant verts.</li></ol><p>On avance à petits pas : un comportement à la fois, puis on recommence. Les tests deviennent la spécification exécutable du module ; quand la spécification change, on commence par les tests.</p><h3>Des tests indépendants de la date</h3><p>Un test qui utilise la date du jour passe aujourd'hui… et échoue le jour où un code expire. Deux solutions :</p><ul><li><strong>Injecter la date</strong> : <code>validerCode('RANDO10', new Date('2026-06-01T10:00:00'))</code>.</li><li><strong>Figer l'horloge</strong> :<pre>jest.useFakeTimers({ now: new Date('2026-06-01T10:00:00') });<br>// ... puis<br>jest.useRealTimers();</pre></li></ul><div class="tip">Vos tests seront aussi exécutés avec une horloge système déplacée dans le futur : s'ils dépendent du jour réel, ils échoueront.</div><h3>Les pièges des dates</h3><table class="lesson-table"><tr><th>Écriture</th><th>Instant représenté</th></tr><tr><td><code>new Date('2026-08-31')</code></td><td>minuit <strong>UTC</strong> (date seule au format ISO)</td></tr><tr><td><code>new Date('2026-08-31T00:00:00')</code></td><td>minuit <strong>heure locale</strong></td></tr><tr><td><code>new Date('2026-08-31T00:00:00Z')</code></td><td>minuit UTC (le <code>Z</code> l'impose)</td></tr><tr><td><code>new Date(2026, 7, 31, 23, 59)</code></td><td>heure locale ; attention, les mois sont numérotés <strong>à partir de 0</strong> (7 = août)</td></tr></table><p>Sur un serveur réglé sur UTC, les deux premières lignes coïncident… mais pas sur le poste d'un collègue à Montréal. Pour lancer les tests comme sur une machine d'un autre fuseau : <code>TZ=America/Toronto npx jest</code>.</p><h3>Couvrir une spécification</h3><ul><li>Un test par règle, et un par raison de refus.</li><li>Les limites : longueur minimale et maximale, dernier instant de validité, premier instant d'expiration.</li><li>Les priorités entre règles (que se passe-t-il si deux règles s'appliquent ?).</li><li>Les entrées inattendues : que doit faire la fonction si on ne lui passe pas ce qu'elle attend ?</li></ul>""",
        "setup": r'''
v=$(tirer J4_1 4 src/data/codes.js SPEC-codes-promo.md)
emit VARIANTE_J4_1 "$v"
livrer src/data/codes.js src/codesPromo.js SPEC-codes-promo.md
''',
        "exercises": [
            {"id": "J4.1", "points": 6, "title": "Red : la spécification en tests", "manual": True,
             "ticket": {"from": "nadia", "body": "Le marketing veut des codes promo pour lundi. On fait ça en TDD : lis <code>SPEC-codes-promo.md</code> et écris d'abord les tests. Je les ferai tourner sur mon implémentation de référence : ils doivent passer, et attraper toutes les erreurs classiques. Et pas de test qui dépend de la date du jour, on s'est déjà fait avoir."},
             "desc": "<code>tests/codesPromo.test.js</code> (au moins 6 tests), indépendant de la date réelle, qui passe sur l'implémentation de référence et détecte ses variantes erronées.",
             "hints": ["Relisez chaque règle de la spécification : chacune mérite au moins un test, et chaque limite aussi (des deux côtés).", "Passez toujours une date aux fonctions, ou figez l'horloge. Et relisez la fin de la spécification : que se passe-t-il quand deux raisons de refus s'appliquent au même code ?"],
             "checks": [
                 ('verif pass --tests tests/codesPromo.test.js --min 6', "tests/codesPromo.test.js est absent, ne passe pas sur l'implémentation de référence ou contient moins de 6 tests."),
                 ('verif pass --tests tests/codesPromo.test.js --fake-date', "Vos tests dépendent de la date du jour."),
                 ('verif kill --tests tests/codesPromo.test.js --set codes', "Vos tests ne couvrent pas toute la spécification."),
             ]},
            {"id": "J4.2", "points": 6, "title": "Green : l'implémentation", "manual": True,
             "ticket": {"from": "nadia", "body": "Tes tests sont prêts, à toi d'écrire <code>validerCode</code> dans <code>src/codesPromo.js</code>. Quand tout est vert chez toi, je lance ma propre batterie de validation."},
             "desc": "<code>src/codesPromo.js</code> implémente la spécification : vos tests et les tests de validation de Nadia passent.",
             "hints": ["Suivez l'ordre des règles de la spécification, et faites passer vos tests un par un.", "« Jour inclus » : jusqu'à quel instant exactement ? Construisez cet instant en heure locale, pas en UTC."],
             "checks": [
                 ('verif pass --tests tests/codesPromo.test.js --src student', "Vos propres tests ne passent pas avec votre implémentation."),
                 ('verif hidden --set codes', "Votre implémentation ne respecte pas toute la spécification."),
             ]},
            {"id": "J4.3", "points": 6, "title": "La spécification a un trou", "manual": True,
             "ticket": {"from": "nadia", "body": "Le front a appelé <code>validerCode(null)</code> quand le champ était vide… et on a répondu <code>INCONNU</code>. Le client a cru que son code n'existait pas. Décision de l'équipe : <strong>tout ce qui n'est pas une chaîne de caractères</strong> est refusé pour <code>FORMAT</code>. En TDD, bien sûr : complète la spécification, puis les tests, puis le code."},
             "desc": "<code>SPEC-codes-promo.md</code> mentionne la nouvelle règle ; <code>tests/codesPromo.test.js</code> la vérifie (il échoue sur l'ancien comportement) ; <code>src/codesPromo.js</code> la respecte, ainsi que tout le reste de la spécification.",
             "hints": ["Suivez pas à pas ce que devient <code>null</code> dans votre fonction : pourquoi la réponse est-elle <code>INCONNU</code> ?", "Quelles autres valeurs qui ne sont pas des chaînes le front pourrait-il envoyer ? Testez-en plusieurs, et vérifiez le type avant toute normalisation."],
             "checks": [
                 ('verif grep SPEC-codes-promo.md "null|undefined|cha[iî]ne|string|type|texte" --i',"SPEC-codes-promo.md ne mentionne pas la nouvelle règle."),
                 ('verif pass --tests tests/codesPromo.test.js', "tests/codesPromo.test.js ne passe pas sur l'implémentation de référence."),
                 ('verif reproduce --tests tests/codesPromo.test.js --set bug-null', "Vos tests passent encore sur l'ancien comportement : ils ne vérifient pas la nouvelle règle."),
                 ('verif pass --tests tests/codesPromo.test.js --src student', "Vos tests ne passent pas avec votre implémentation."),
                 ('verif hidden --set codes,codes-null', "Votre implémentation ne respecte pas toute la spécification, nouvelle règle comprise."),
             ]},
            {"id": "J4.4", "points": 6, "title": "Minuit pile", "manual": True,
             "ticket": {"from": "sophie", "body": "Deux réclamations sur le même code : une cliente l'a saisi le dernier jour de sa validité, à 23 h 59 min 59 s passées : refusé (alors que la spécification dit « jour inclus ») ; et l'équipe de notre prestataire, à Montréal, obtient d'autres résultats que nous en lançant les mêmes tests. Je veux des tests qui verrouillent la fin de validité <strong>à la milliseconde près</strong>, et qui disent la même chose sur toutes les machines."},
             "desc": "<code>tests/codes-minuit.test.js</code> vérifie le dernier instant de validité et le premier instant d'expiration d'un code, passe quel que soit le fuseau horaire de la machine et quelle que soit la date du jour, et détecte toute fin de validité mal calculée.",
             "hints": ["Quels sont exactement le dernier instant valide et le premier instant expiré ? Écrivez-les de façon à ce qu'ils ne puissent pas être compris autrement.", "Relisez le tableau des pièges des dates, puis lancez vos tests avec <code>TZ=America/Toronto npx jest</code> et <code>TZ=Asia/Tokyo npx jest</code>."],
             "checks": [
                 ('verif pass --tests tests/codes-minuit.test.js --min 2', "tests/codes-minuit.test.js est absent, ne passe pas ou contient moins de 2 tests."),
                 ('verif pass --tests tests/codes-minuit.test.js --tz America/Toronto', "Vos tests ne passent pas sur une machine réglée sur l'heure de Montréal."),
                 ('verif pass --tests tests/codes-minuit.test.js --tz Asia/Tokyo --fake-date', "Vos tests ne passent pas sur une machine réglée sur l'heure de Tokyo, ou dépendent de la date du jour."),
                 ('verif kill --tests tests/codes-minuit.test.js --set codes-minuit --tz America/Toronto', "Vos tests ne détectent pas toutes les erreurs de fin de validité."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Jour 5 — Doublures de test",
        "description": "Isoler le code de ses dépendances. Compétences : jest.fn, jest.mock, jest.spyOn, clear / reset / restore, matchers asymétriques.",
        "lesson": """<h3>Pourquoi des doublures ?</h3><p>Un test unitaire ne doit appeler ni la banque, ni le serveur de mails, ni l'API de stock : c'est lent, instable, et parfois coûteux. On remplace ces dépendances par des <strong>doublures</strong> contrôlées.</p><h3>jest.fn() : une fonction espionne</h3><pre>const api = { lire: jest.fn() };<br>api.lire.mockReturnValue(3);                 // renvoie toujours 3<br>api.lire.mockResolvedValue(3);               // renvoie une promesse de 3<br>api.lire.mockResolvedValueOnce(0);           // 0 au prochain appel seulement<br>api.lire.mockImplementation(async (ref) =&gt; stocks[ref]);</pre><p>Vérifier les appels :</p><pre>expect(api.lire).toHaveBeenCalledTimes(2);<br>expect(api.lire).toHaveBeenCalledWith('GOURDE-1L');<br>expect(api.lire).not.toHaveBeenCalled();</pre><div class="tip">Une doublure doit respecter le <strong>contrat</strong> de ce qu'elle remplace : si la vraie fonction renvoie une promesse, la doublure aussi.</div><h3>jest.mock() : remplacer un module entier</h3><p>Quand le code fait lui-même <code>require('./services/paiement')</code>, on ne peut pas lui passer de doublure. On demande à Jest de remplacer le module :</p><pre>jest.mock('../src/services/paiement');<br>const paiement = require('../src/services/paiement');</pre><p>Toutes les fonctions exportées deviennent des <code>jest.fn()</code> <strong>qui renvoient <code>undefined</code></strong>, même si l'originale était <code>async</code> : c'est au test de programmer leur résultat. Les appels à <code>jest.mock</code> sont remontés en haut du fichier par Jest : ils s'appliquent avant les <code>require</code>.</p><h3>jest.spyOn() : espionner une méthode existante</h3><pre>const espion = jest.spyOn(objet, 'methode');        // garde le vrai comportement<br>espion.mockReturnValue(42);                        // ... ou le remplace<br>espion.mockRestore();                              // remet la vraie méthode en place</pre><h3>Remettre les doublures à zéro</h3><table class="lesson-table"><tr><th>Sur une doublure</th><th>Sur toutes</th><th>Configuration</th><th>Effet</th></tr><tr><td><code>mockClear()</code></td><td><code>jest.clearAllMocks()</code></td><td><code>clearMocks</code></td><td>oublie les appels enregistrés (garde les valeurs programmées)</td></tr><tr><td><code>mockReset()</code></td><td><code>jest.resetAllMocks()</code></td><td><code>resetMocks</code></td><td>oublie aussi les implémentations et les valeurs programmées, y compris les « Once » pas encore consommées</td></tr><tr><td><code>mockRestore()</code></td><td><code>jest.restoreAllMocks()</code></td><td><code>restoreMocks</code></td><td>remet en place la vraie méthode espionnée par <code>spyOn</code></td></tr></table><h3>Matchers à trous (asymétriques)</h3><p>Pour vérifier un argument sans figer ce qui n'a pas d'importance :</p><pre>expect.any(Number)                 expect.stringContaining('texte')<br>expect.stringMatching(/^CMD-\\d+$/) expect.objectContaining({ ref: 'A' })<br>expect.arrayContaining([1, 2])</pre><p>Ils s'utilisent partout où l'on attend une valeur, par exemple dans <code>toHaveBeenCalledWith</code> ou <code>toEqual</code>.</p><h3>Asynchrone</h3><p>Un test peut être <code>async</code> : <code>const r = await verifierDisponibilite(panier, api);</code>. Sans <code>await</code> (ou <code>return</code>), Jest termine le test avant la fin de la promesse (voir le jour 6).</p>""",
        "setup": r'''
livrer src/stock.js src/commande.js src/services/paiement.js src/services/mailer.js src/concours.js tests/commande-fuite.test.js
''',
        "exercises": [
            {"id": "J5.1", "points": 5, "title": "Rupture de stock", "manual": True,
             "ticket": {"from": "thomas", "body": "<code>verifierDisponibilite</code> (dans <code>src/stock.js</code>) interroge l'API de l'entrepôt pour chaque ligne du panier. Évidemment, pas question d'appeler l'entrepôt depuis les tests : l'API est passée en paramètre, fais-en une doublure Jest (<code>jest.fn</code> ou <code>jest.spyOn</code>). Vérifie ce qu'elle renvoie <strong>et</strong> comment l'API est appelée (l'entrepôt facture chaque appel !)."},
             "desc": "<code>tests/stock.test.js</code>, avec une doublure Jest (<code>jest.fn()</code> ou <code>jest.spyOn</code>) dont les appels sont vérifiés (<code>toHaveBeenCalledWith</code>…), qui passe et détecte les régressions.",
             "hints": ["La doublure est un simple objet dont la méthode <code>quantiteDisponible</code> est un <code>jest.fn()</code>. Que renvoie la vraie API : un nombre, ou une promesse ?", "Testez un stock insuffisant, un stock tout juste suffisant, et un panier de plusieurs lignes ; comptez aussi les appels."],
             "checks": [
                 ('has tests/stock.test.js "jest\\.(fn|spyOn)\\b"', "tests/stock.test.js doit remplacer l'API par une doublure Jest (jest.fn() ou jest.spyOn)."),
                 ('has tests/stock.test.js "to(HaveBeen|Be)(Nth|Last)?CalledWith|(nth|last)CalledWith|\\.mock\\.calls"', "tests/stock.test.js doit vérifier les arguments des appels (toHaveBeenCalledWith, toHaveBeenNthCalledWith…)."),
                 ('verif pass --tests tests/stock.test.js', "tests/stock.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/stock.test.js --set stock', "Vos tests ne détectent pas toutes les régressions."),
             ]},
            {"id": "J5.2", "points": 6, "title": "Passer commande sans débiter personne", "manual": True,
             "ticket": {"from": "sophie", "body": "Incident de la semaine dernière : un test a débité pour de vrai la carte de test… de notre PDG. Désormais <code>src/services/paiement.js</code> et <code>mailer.js</code> refusent de fonctionner dans les tests. Écris les tests du <strong>cas nominal</strong> de <code>passerCommande</code> (<code>src/commande.js</code>) en remplaçant ces deux modules avec <code>jest.mock</code>."},
             "desc": "<code>tests/commande.test.js</code>, avec <code>jest.mock</code> des services de paiement et de mail, qui vérifie le débit (montant, carte, nombre), l'e-mail de confirmation et le résultat renvoyé.",
             "hints": ["Une fois le module remplacé par <code>jest.mock</code>, que renvoie <code>paiement.debiter</code> ? Que doit-il renvoyer pour que <code>passerCommande</code> aille au bout ?", "Le montant débité est le total <strong>TTC</strong> du panier. Un débit, c'est un seul appel à la banque, et un e-mail a un destinataire, un sujet et un corps."],
             "checks": [
                 ('has tests/commande.test.js "jest\\.mock\\([\'\\"]\\.\\./src/services/paiement"', "tests/commande.test.js doit remplacer le module de paiement avec jest.mock('../src/services/paiement')."),
                 ('verif pass --tests tests/commande.test.js', "tests/commande.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/commande.test.js --set commande-ok', "Vos tests ne détectent pas toutes les régressions du cas nominal."),
             ]},
            {"id": "J5.3", "points": 6, "title": "Le tirage au sort", "manual": True,
             "ticket": {"from": "sophie", "body": "Le marketing organise un jeu-concours : <code>tirerGagnant</code> (<code>src/concours.js</code>) désigne un gagnant au hasard. Un huissier va contrôler le tirage : chaque participant, <strong>premier et dernier compris</strong>, doit pouvoir gagner, et une liste vide doit être refusée. Écris des tests qui donnent toujours le même résultat, sans toucher au module : espionne <code>Math.random</code> avec <code>jest.spyOn</code>, et remets la vraie fonction en place après usage."},
             "desc": "<code>tests/concours.test.js</code> passe à chaque exécution, espionne <code>Math.random</code> avec <code>jest.spyOn</code>, remet la vraie fonction en place, et détecte tout tirage biaisé ou mal protégé.",
             "hints": ["On ne peut pas prévoir le hasard… mais on peut décider de ce que renvoie <code>Math.random</code>, le temps d'un test. Quelles valeurs extrêmes peut-il renvoyer ?", "Relisez la section <code>jest.spyOn</code> du cours, et le tableau de remise à zéro : un espion oublié fausse tous les tests suivants du fichier."],
             "checks": [
                 ('has tests/concours.test.js "spyOn\\(\\s*((global|globalThis)\\s*\\.\\s*)?Math\\s*,"', "tests/concours.test.js doit espionner Math.random avec jest.spyOn."),
                 ('has tests/concours.test.js "mockRestore|restoreAllMocks"', "L'espion de Math.random doit être retiré après usage (mockRestore ou jest.restoreAllMocks)."),
                 ('verif pass --tests tests/concours.test.js --seeds 1,2,3', "tests/concours.test.js est absent, ne passe pas, ou ne donne pas toujours le même résultat."),
                 ('verif kill --tests tests/concours.test.js --set concours', "Vos tests ne détectent pas tous les tirages biaisés."),
             ]},
            {"id": "J5.4", "points": 6, "title": "Le mock qui fuit", "manual": True,
             "ticket": {"from": "nadia", "body": "<code>tests/commande-fuite.test.js</code>, de Thomas, est vert dans l'ordre d'écriture, rouge une fois sur deux avec <code>--randomize</code>. Pourtant il y a bien un <code>jest.clearAllMocks()</code> avant chaque test ! Trouve ce qui passe d'un test à l'autre et corrige, sans supprimer de test."},
             "desc": "<code>tests/commande-fuite.test.js</code> garde au moins 4 tests ; ils passent dans n'importe quel ordre et chacun seul, et détectent toujours les régressions de <code>passerCommande</code>.",
             "hints": ["Lancez les tests dans plusieurs ordres, repérez celui qui échoue, et demandez-vous ce que le test précédent a laissé derrière lui.", "Qu'efface exactement <code>clearAllMocks</code> ? Relisez le tableau du cours… et où sont programmées les valeurs par défaut."],
             "checks": [
                 ('verif pass --tests tests/commande-fuite.test.js --min 4 --isolate', "Les tests ne passent pas, ne passent pas chacun seul, ou il en reste moins de 4."),
                 ('verif pass --tests tests/commande-fuite.test.js --seeds 1,2,3,4,5,6', "Les tests échouent quand on change leur ordre d'exécution."),
                 ('verif kill --tests tests/commande-fuite.test.js --set commande-fuite', "Les tests ne détectent plus toutes les régressions de passerCommande."),
             ]},
            {"id": "J5.5", "points": 5, "title": "Le marketing réécrit les e-mails", "manual": True,
             "ticket": {"from": "sophie", "body": "Le marketing va réécrire le texte des e-mails de confirmation chaque semaine (tests A/B). Ce qui ne doit <strong>jamais</strong> changer : le destinataire, le sujet exact, et le montant débité, qui doit figurer dans le corps. Je veux des tests qui protègent ça… sans casser à chaque nouvelle formulation. Comme d'habitude, le module d'envoi est remplacé avec <code>jest.mock</code>."},
             "desc": "<code>tests/commande-email.test.js</code> passe, détecte tout e-mail de confirmation mal adressé, mal intitulé ou sans le bon montant, et reste vert quelle que soit la formulation du corps.",
             "hints": ["Pour le corps, qu'est-ce qui fait partie de la règle, et qu'est-ce qui n'en fait pas partie ?", "Relisez la section du cours sur les matchers à trous : ils s'utilisent aussi comme arguments de <code>toHaveBeenCalledWith</code>."],
             "checks": [
                 ('has tests/commande-email.test.js "jest\\.mock\\([\'\\"]\\.\\./src/services/mailer"', "tests/commande-email.test.js doit remplacer le module d'envoi d'e-mails avec jest.mock('../src/services/mailer')."),
                 ('verif pass --tests tests/commande-email.test.js', "tests/commande-email.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/commande-email.test.js --set commande-email', "Vos tests ne détectent pas tous les e-mails de confirmation erronés."),
                 ('verif survive --tests tests/commande-email.test.js --set commande-email-variantes', "Vos tests cassent quand le marketing reformule l'e-mail."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Jour 6 — Quand tout va mal",
        "description": "Tester les chemins d'erreur asynchrones. Compétences : rejects, mockRejectedValueOnce, toHaveBeenCalledTimes, expect.assertions.",
        "lesson": """<h3>Promesses rejetées</h3><pre>await expect(passerCommande(panier, client)).rejects.toThrow('Paiement refusé');</pre><div class="tip">Une assertion sur une promesse doit être attendue (<code>await</code>) ou renvoyée (<code>return</code>). Sinon le test se termine avant elle : selon les cas, l'échec passe inaperçu, apparaît dans un autre test, ou fait s'arrêter brutalement toute l'exécution.</div><h3>Des assertions qui ne s'exécutent jamais</h3><p>Une assertion placée dans un <code>catch</code>, un <code>.then</code> ou un <code>if</code> n'est exécutée que si le programme y passe. Si le code ne lève plus l'erreur attendue, le test reste vert… sans avoir rien vérifié.</p><ul><li><code>expect.assertions(n)</code> en début de test : le test échoue si exactement <code>n</code> assertions n'ont pas été exécutées ;</li><li><code>expect.hasAssertions()</code> : au moins une.</li></ul><h3>Simuler des pannes</h3><pre>paiement.debiter<br>  .mockRejectedValueOnce(new Error('Timeout'))            // 1er appel : panne<br>  .mockResolvedValueOnce({ accepte: true, transaction: 'TX-9' }); // 2e : succès</pre><h3>Vérifier ce qui ne doit PAS arriver</h3><pre>expect(mailer.envoyer).not.toHaveBeenCalled();<br>expect(paiement.debiter).toHaveBeenCalledTimes(2);</pre><p>Dans un chemin d'erreur, vérifiez à la fois l'erreur levée et l'absence d'effets de bord (pas d'e-mail de confirmation, pas de second débit…). Et vérifiez-les <strong>après</strong> la fin de l'opération.</p>""",
        "setup": r'''
livrer tests/commande-async.test.js
''',
        "exercises": [
            {"id": "J6.1", "points": 6, "title": "Paiement refusé", "manual": True,
             "ticket": {"from": "diallo", "body": "Un client a reçu un e-mail « commande confirmée » alors que sa banque avait refusé le paiement ! Et un autre a vu sa carte sollicitée pour un panier vide. Il nous faut des tests sur les <strong>échecs</strong> de <code>passerCommande</code> : paiement refusé (avec le motif de la banque dans le message), panier vide… et aucun effet de bord dans ces cas-là. Vérifie les promesses rejetées avec <code>rejects</code>."},
             "desc": "<code>tests/commande-erreurs.test.js</code>, utilisant <code>rejects</code>, qui passe et détecte chaque chemin d'erreur mal géré.",
             "hints": ["Le client doit comprendre pourquoi sa commande échoue : que doit contenir le message d'erreur ?", "Dans chaque chemin d'erreur, quels appels ne doivent <em>jamais</em> avoir lieu ? Vérifiez-les une fois l'opération terminée."],
             "checks": [
                 ('has tests/commande-erreurs.test.js "rejects"', "tests/commande-erreurs.test.js doit utiliser .rejects."),
                 ('verif pass --tests tests/commande-erreurs.test.js', "tests/commande-erreurs.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/commande-erreurs.test.js --set commande-erreurs', "Vos tests ne détectent pas tous les chemins d'erreur mal gérés."),
             ]},
            {"id": "J6.2", "points": 5, "title": "La banque qui tousse", "manual": True,
             "ticket": {"from": "nadia", "body": "L'API de la banque a des micro-coupures. <code>passerCommande</code> retente <strong>une seule fois</strong> après une erreur technique, puis abandonne avec « Service de paiement indisponible » (on ne montre jamais l'erreur technique brute au client). Un refus de la banque, lui, n'est pas une panne : on ne redemande jamais. Verrouille ce comportement, en simulant les pannes avec <code>mockRejectedValue</code> (ou <code>mockRejectedValueOnce</code>)."},
             "desc": "<code>tests/commande-reprise.test.js</code>, simulant des pannes avec <code>mockRejectedValueOnce</code> ou <code>mockRejectedValue</code>, qui détecte toute erreur dans la logique de reprise.",
             "hints": ["Faites la liste des scénarios : que peut répondre la banque au premier appel ? Et au second ?", "Comptez les tentatives dans chaque scénario, et distinguez une promesse rejetée (panne) d'une réponse négative (refus)."],
             "checks": [
                 ('has tests/commande-reprise.test.js "mockRejectedValue(Once)?"', "tests/commande-reprise.test.js doit simuler des pannes avec mockRejectedValue ou mockRejectedValueOnce."),
                 ('verif pass --tests tests/commande-reprise.test.js', "tests/commande-reprise.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/commande-reprise.test.js --set commande-reprise', "Vos tests ne détectent pas toutes les erreurs de la logique de reprise."),
             ]},
            {"id": "J6.3", "points": 6, "title": "Des tests qui ne peuvent pas échouer", "manual": True,
             "ticket": {"from": "nadia", "body": "Revue de code de <code>tests/commande-async.test.js</code>, écrit par Thomas : 4 tests, 4 verts. J'ai glissé exprès des bugs dans <code>passerCommande</code> sur ma machine : ses tests sont restés verts à chaque fois. Répare-les, sans en supprimer : chacun doit pouvoir échouer quand le comportement qu'il décrit est cassé."},
             "desc": "<code>tests/commande-async.test.js</code> garde au moins 4 tests, passe, et chacun détecte la régression qu'annonce son nom.",
             "hints": ["Pour chaque test : à quel moment l'assertion s'exécute-t-elle ? Et s'exécute-t-elle seulement, quand le code ne se comporte plus comme prévu ?", "Relisez la section « Des assertions qui ne s'exécutent jamais » du cours, et vérifiez chaque message d'erreur que le client est censé voir."],
             "checks": [
                 ('verif pass --tests tests/commande-async.test.js --min 4', "tests/commande-async.test.js ne passe pas, ou contient moins de 4 tests."),
                 ('verif kill --tests tests/commande-async.test.js --set commande-async', "Certains tests ne peuvent toujours pas échouer."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    7: {
        "title": "Jour 7 — Le temps qui passe",
        "description": "Tester du code qui dépend du temps sans attendre. Compétences : jest.useFakeTimers, advanceTimersByTime, minuteurs et promesses.",
        "lesson": """<h3>Le problème</h3><p><code>programmerRelance</code> envoie un e-mail un ou plusieurs jours après l'abandon d'un panier. Un test ne peut évidemment pas attendre aussi longtemps (et Jest l'arrête au bout de 5 s).</p><h3>Les faux minuteurs</h3><pre>beforeEach(() =&gt; jest.useFakeTimers());<br>afterEach(() =&gt; jest.useRealTimers());<br><br>test('le livreur est rappelé au bout de 30 min', () =&gt; {<br>  const rappel = jest.fn();<br>  setTimeout(rappel, 30 * 60 * 1000);<br>  jest.advanceTimersByTime(30 * 60 * 1000);<br>  expect(rappel).toHaveBeenCalledTimes(1);<br>});</pre><ul><li><code>jest.advanceTimersByTime(ms)</code> — avance l'horloge virtuelle et exécute les minuteurs arrivés à échéance</li><li><code>jest.runOnlyPendingTimers()</code> — exécute les minuteurs en attente (pas ceux qu'ils créent)</li><li><code>jest.runAllTimers()</code> — exécute tout, jusqu'à ce qu'il ne reste rien (boucle sans fin avec un <code>setInterval</code> !)</li><li><code>jest.getTimerCount()</code> — nombre de minuteurs en attente</li></ul><div class="tip">Testez la limite exacte : <strong>juste avant</strong> le délai rien ne doit se passer, <strong>au moment du délai</strong> l'action a lieu. Et regardez aussi ce qui se passe <strong>longtemps après</strong>.</div><h3>Minuteurs et promesses</h3><p><code>advanceTimersByTime</code> est synchrone : il exécute les minuteurs, mais ne laisse pas aux promesses le temps de se résoudre entre deux. Un code qui enchaîne <code>await</code> et <code>setTimeout</code> (attendre, puis réessayer, puis attendre encore…) n'avance donc pas. Jest (depuis la version 29.5) propose des variantes asynchrones, à attendre :</p><pre>await jest.advanceTimersByTimeAsync(1000);<br>await jest.runAllTimersAsync();</pre>""",
        "setup": r'''
v=$(tirer J7_1 4 src/relance.js)
emit VARIANTE_J7_1 "$v"
v=$(tirer J7_2 4 src/debit-patient.js)
emit VARIANTE_J7_2 "$v"
livrer src/relance.js src/debit-patient.js
''',
        "exercises": [
            {"id": "J7.1", "points": 6, "title": "Relance des paniers abandonnés", "manual": True,
             "ticket": {"from": "thomas", "body": "Le marketing a lancé les relances de paniers abandonnés (<code>src/relance.js</code>). Premier jour : des clients relancés au bout d'une heure, d'autres relancés alors qu'ils avaient déjà commandé, et un client qui se plaint de recevoir la relance <strong>tous les jours</strong>… Écris des tests qui garantissent une relance unique au bout du délai fixé par le marketing (il est indiqué dans <code>src/relance.js</code>), l'annulation, le destinataire et le contenu du message. Sans attendre pour de vrai, évidemment : avec les faux minuteurs de Jest (<code>jest.useFakeTimers</code>)."},
             "desc": "<code>tests/relance.test.js</code>, avec <code>jest.useFakeTimers</code>, rapide (moins de 5 s), qui détecte toute régression de la relance.",
             "hints": ["Le <code>mailer</code> est passé en paramètre. Scénarios : délai exact (juste avant / pile), annulation, panier vidé entre-temps, message avec plusieurs articles… et bien après le délai.", "Écrivez le délai attendu en dur, tel que l'annonce le commentaire : si vous réutilisez la constante exportée par le code testé, un délai faux passera inaperçu."],
             "checks": [
                 ('has tests/relance.test.js "useFakeTimers"', "tests/relance.test.js doit utiliser jest.useFakeTimers()."),
                 ('verif pass --tests tests/relance.test.js --max-ms 5000', "tests/relance.test.js est absent, ne passe pas ou est trop lent."),
                 ('verif kill --tests tests/relance.test.js --set relance', "Vos tests ne détectent pas toutes les régressions de la relance."),
             ]},
            {"id": "J7.2", "points": 6, "title": "La banque fait patienter", "manual": True,
             "ticket": {"from": "nadia", "body": "Nouvelle règle de la banque : après une erreur technique, on doit <strong>patienter</strong> avant de réessayer, un peu avant la 2<sup>e</sup> tentative, plus longtemps avant la 3<sup>e</sup>, et pas plus de 3 tentatives. C'est <code>debiterPatiemment</code> (<code>src/debit-patient.js</code>), dont le commentaire donne les délais exacts. Teste les délais au plus près, mais je refuse une suite qui attend pour de vrai."},
             "desc": "<code>tests/debit-patient.test.js</code> passe en moins de 2,5 s et détecte toute erreur sur le nombre de tentatives, les délais d'attente ou l'erreur finale.",
             "hints": ["Avec des faux minuteurs, faites avancer le temps juste avant, puis juste au moment de chaque nouvelle tentative, et comptez les appels à la banque.", "Si rien ne bouge alors que le temps avance, relisez la section « Minuteurs et promesses » du cours."],
             "checks": [
                 ('has tests/debit-patient.test.js "useFakeTimers|spyOn\\(\\s*(global|globalThis)\\s*,\\s*[\'\\"]setTimeout[\'\\"]"', "tests/debit-patient.test.js doit simuler le temps (jest.useFakeTimers(), ou setTimeout espionné) au lieu d'attendre."),
                 ('verif pass --tests tests/debit-patient.test.js --max-ms 2500', "tests/debit-patient.test.js est absent, ne passe pas ou attend de vrais délais."),
                 ('verif kill --tests tests/debit-patient.test.js --set attente', "Vos tests ne détectent pas toutes les erreurs de la logique d'attente."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Jour 8 — Couverture de code",
        "description": "Mesurer ce que les tests exercent. Compétences : --coverage, branches, coverageThreshold, combinaisons de règles.",
        "lesson": """<h3>Mesurer la couverture</h3><pre>npx jest --coverage</pre><table class="lesson-table"><tr><th>Mesure</th><th>Signification</th></tr><tr><td>Statements / Lines</td><td>Instructions / lignes exécutées au moins une fois</td></tr><tr><td>Functions</td><td>Fonctions appelées au moins une fois</td></tr><tr><td>Branches</td><td>Chaque sortie de chaque <code>if</code>, <code>? :</code>, <code>&amp;&amp;</code>… empruntée au moins une fois</td></tr></table><p>Le rapport HTML détaillé est dans <code>coverage/lcov-report/index.html</code> ; la colonne <em>Uncovered Line #s</em> du terminal indique les lignes jamais exécutées.</p><h3>Configurer Jest</h3><p>La configuration va soit dans <code>package.json</code>, sous une clé <code>"jest"</code>, soit dans un fichier <code>jest.config.js</code> (<code>module.exports = { ... }</code>) — jamais les deux à la fois : Jest refuse de démarrer.</p><pre>"jest": {<br>  "collectCoverageFrom": ["src/**/*.js"],<br>  "coverageThreshold": {<br>    "global": { "statements": 85 }<br>  }<br>}</pre><p>Si un seuil n'est pas atteint, <code>jest --coverage</code> échoue : la CI bloque la fusion. En plus de <code>global</code>, des seuils peuvent être fixés pour certains fichiers ou dossiers (voir la documentation de <code>coverageThreshold</code>).</p><div class="tip">100 % de couverture ne prouve pas que le code est juste : un test sans <code>expect</code> « couvre » tout. La couverture montre ce qui n'est <strong>pas</strong> testé ; les mutants montrent si ce qui est exécuté est vraiment vérifié.</div><h3>Au-delà des branches : les combinaisons</h3><p>Une fois chaque branche couverte, il reste les <strong>interactions entre règles</strong> : l'ordre dans lequel elles s'appliquent ne se voit que sur un cas concerné par plusieurs règles à la fois.</p>""",
        "setup": r'''
v=$(tirer J8_2 4 src/fidelite.js)
emit VARIANTE_J8_2 "$v"
livrer src/fidelite.js
''',
        "exercises": [
            {"id": "J8.1", "points": 3, "title": "Des seuils dans la CI", "manual": True,
             "ticket": {"from": "nadia", "body": "À partir d'aujourd'hui, la couverture fait partie de la définition de « terminé ». Configure Jest : couverture mesurée sur tout <code>src/</code>, échec si on passe sous <strong>80 % de branches</strong> ou <strong>90 % de lignes</strong> sur l'ensemble du projet, et <strong>100 % de branches</strong> exigées sur <code>src/prix.js</code>, qui calcule toutes nos factures. Ajoute aussi un script <code>test:coverage</code>."},
             "desc": "La configuration de Jest mesure la couverture de <code>src/**/*.js</code>, exige au moins 80 % de branches et 90 % de lignes au global et 100 % de branches sur <code>src/prix.js</code> ; <code>npm run test:coverage</code> lance les tests avec la couverture.",
             "hints": ["Relisez dans le cours les deux endroits où peut vivre la configuration de Jest. Vérifiez votre travail avec <code>npm run test:coverage</code> : les seuils sont-ils affichés quand ils ne sont pas atteints ?", "À côté de <code>global</code>, <code>coverageThreshold</code> accepte des clés qui sont des chemins de fichiers (<code>./src/…</code>)."],
             "checks": [
                 ('node -e "require(\'$P/package.json\')"', "package.json n'est plus un JSON valide."),
                 ('pkg \'p.scripts["test:coverage"]\' | grep -qE -- "^((npx )?jest|npm (run )?test --)( .*)? --(coverage|collectCoverage)(=true)?( |$)"', "Le script « test:coverage » doit lancer jest avec --coverage."),
                 ('verif config --expr \'couvreSrc()\'', "collectCoverageFrom doit mesurer tous les fichiers .js de src/ (par exemple « src/**/*.js »)."),
                 ('verif config --expr \'c.coverageThreshold && c.coverageThreshold.global && c.coverageThreshold.global.branches >= 80 && c.coverageThreshold.global.lines >= 90\'', "coverageThreshold.global doit exiger au moins 80 % de branches et 90 % de lignes."),
                 ('verif config --expr \'Object.entries(c.coverageThreshold || {}).some(([k, v]) => k !== "global" && /(^|\\/)src\\/prix\\.js$/.test(k) && v && v.branches >= 100)\'', "Aucun seuil n'exige 100 % de branches sur src/prix.js."),
             ]},
            {"id": "J8.2", "points": 6, "title": "Le programme de fidélité", "manual": True,
             "ticket": {"from": "diallo", "body": "Le calcul des points de fidélité (<code>src/fidelite.js</code>) a des règles dans tous les sens : statuts, bonus d'anniversaire, plafond… et zéro test. Je veux que <strong>toutes les branches</strong> soient testées, et que les tests vérifient vraiment les montants de points."},
             "desc": "<code>tests/fidelite.test.js</code> : 100 % des branches et des lignes de <code>src/fidelite.js</code>, et détection de toutes les erreurs de calcul.",
             "hints": ["<code>npx jest tests/fidelite --coverage --collectCoverageFrom=src/fidelite.js</code> montre les lignes non couvertes.", "Chaque branche couverte doit aussi être vérifiée : choisissez des montants qui distinguent un arrondi d'un autre."],
             "checks": [
                 ('verif pass --tests tests/fidelite.test.js', "tests/fidelite.test.js est absent ou ne passe pas."),
                 ('verif coverage --tests tests/fidelite.test.js --file src/fidelite.js --branches 100 --lines 100', "La couverture de src/fidelite.js n'est pas complète."),
                 ('verif kill --tests tests/fidelite.test.js --set fidelite', "Vos tests exécutent tout le code mais ne vérifient pas tous les calculs."),
             ]},
            {"id": "J8.3", "points": 6, "title": "Dans quel ordre, les points ?", "manual": True,
             "ticket": {"from": "diallo", "body": "La direction a tranché : on part des euros entiers dépensés, on applique le multiplicateur du statut, puis on ajoute le bonus d'anniversaire, et on applique le plafond <strong>en dernier</strong>. Un prestataire va réécrire le module le trimestre prochain. Ta couverture est à 100 %, mais je veux que tes tests refusent toute version qui appliquerait ces étapes dans un autre ordre."},
             "desc": "<code>tests/fidelite.test.js</code> passe et détecte toute version de <code>pointsFidelite</code> qui n'applique pas les règles dans l'ordre : statut, bonus d'anniversaire, plafond.",
             "hints": ["Pour qu'un changement d'ordre se voie, il faut un client concerné par deux règles à la fois.", "Quels statuts rendent visible l'ordre « statut puis bonus » ? Quel montant rend le plafond sensible au bonus ?"],
             "checks": [
                 ('verif pass --tests tests/fidelite.test.js', "tests/fidelite.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/fidelite.test.js --set fidelite-ordre', "Vos tests ne détectent pas toutes les erreurs d'ordre entre les règles."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    9: {
        "title": "Jour 9 — Les bugs de la facture",
        "description": "Corriger un bug en commençant par le reproduire. Compétences : test de non-régression, débogage, test.failing.",
        "lesson": """<h3>Corriger un bug, dans le bon ordre</h3><ol><li><strong>Reproduire</strong> : écrire un test qui échoue et qui montre le bug. Ce test prouve que vous avez compris le problème.</li><li><strong>Corriger</strong> le code : le test passe.</li><li><strong>Garder</strong> le test : c'est un <em>test de non-régression</em>, le bug ne pourra pas revenir sans que la CI le voie.</li></ol><h3>Outils de débogage</h3><ul><li><code>npx jest -t "nom du test"</code> — ne lancer qu'un test</li><li><code>console.log</code> dans le code ou le test (Jest affiche la sortie avec le nom du fichier)</li><li>Calculez à la main le résultat attendu à partir de la règle métier, avant de regarder ce que renvoie le code.</li></ul><div class="tip">Un test de reproduction doit utiliser des valeurs qui <strong>distinguent</strong> le bon comportement du mauvais : sur beaucoup de valeurs, les deux donnent le même résultat.</div><h3>Un bug connu, pas encore corrigé</h3><p>Parfois, on ne peut pas corriger tout de suite (code d'un prestataire, correctif prévu plus tard). Plutôt que de désactiver le test avec <code>.skip</code>, on le marque comme « échec attendu » :</p><pre>test.failing('bug #999 : ...', () =&gt; {<br>  expect(resultat).toBe(valeurCorrecte);<br>});</pre><p>Un test <code>.failing</code> est vert tant que son contenu échoue, et devient <strong>rouge dès qu'il passe</strong> : le jour où le bug est corrigé, la suite vous prévient qu'il est temps d'en faire un test normal.</p>""",
        "setup": r'''
# La facture dépend de la grille de livraison de l'étudiant (tirée au jour 3)
v=$(tirer J3_1 4 src/livraison.js)
emit VARIANTE_J3_1 "$v"
livrer --set bug-facture src/facture.js
livrer --set bug-export src/export-compta.js
''',
        "exercises": [
            {"id": "J9.1", "points": 5, "title": "Reproduire le bug", "manual": True,
             "ticket": {"from": "sophie", "body": "Ticket #218, remonté par la compta : un client a bénéficié de la livraison offerte alors que, remise déduite, ses produits coûtaient moins que le seuil. Or le commentaire de <code>src/facture.js</code> est clair : le seuil de livraison offerte (voir <code>src/livraison.js</code>) s'apprécie <strong>après</strong> remise. Avant toute correction, je veux un test qui reproduise le problème."},
             "desc": "<code>tests/facture.test.js</code> échoue sur la version boguée actuelle et passe sur une version corrigée.",
             "hints": ["À quel montant le seuil est-il comparé dans le code ? Et d'après le commentaire ?", "Il vous faut un panier au-dessus du seuil avant la remise, et en dessous après. Calculez à la main la facture attendue."],
             "checks": [
                 ('verif pass --tests tests/facture.test.js', "tests/facture.test.js est absent, ou ne passe pas sur une version corrigée du code (vos valeurs attendues sont-elles justes ?)."),
                 ('verif reproduce --tests tests/facture.test.js --set bug-facture', "Votre test ne reproduit pas le bug #218."),
             ]},
            {"id": "J9.2", "points": 4, "title": "Corriger les bugs", "manual": True,
             "ticket": {"from": "sophie", "body": "Parfait, le bug #218 est prouvé. Mauvaise nouvelle : la compta en a trouvé un second dans les factures, ticket #219 : un randonneur a payé le tarif de la tranche de poids supérieure pour un colis trop léger pour en faire partie. Corrige les deux dans <code>src/facture.js</code>, avec un test de non-régression <strong>pour chacun</strong>."},
             "desc": "<code>src/facture.js</code> est corrigé et passe les tests de validation ; <code>tests/facture.test.js</code> passe avec votre code et contient, pour chacun des deux bugs, un test qui échoue quand ce bug revient.",
             "hints": ["Pour #219, suivez le poids du colis depuis les paramètres de <code>genererFacture</code> jusqu'au calcul du port.", "Un test de non-régression par bug : chacun doit échouer quand <em>son</em> bug est présent, même si l'autre est corrigé. Quel poids distingue le bon calcul du mauvais ?"],
             "checks": [
                 ('verif pass --tests tests/facture.test.js --src student', "Votre test de facture ne passe pas avec votre code."),
                 ('verif hidden --set facture', "La facturation n'est pas encore correcte."),
                 ('verif reproduce --tests tests/facture.test.js --set bug-facture --each', "Il manque un test de non-régression."),
             ]},
            {"id": "J9.3", "points": 5, "title": "Un bug assumé", "manual": True,
             "ticket": {"from": "sophie", "body": "Ticket #231 : le logiciel de comptabilité rejette certaines lignes de l'export (<code>src/export-compta.js</code>). Ce module appartient au prestataire, qui livrera le correctif le mois prochain : on n'y touche pas. Mais je veux que le bug soit documenté dans notre suite : un test qui dit ce que la compta attend, qui reste vert tant que le bug existe… et qui passe au rouge le jour où le correctif arrive, pour qu'on pense à le transformer en test normal. Un test marqué comme échec attendu, donc, ni désactivé ni inversé."},
             "desc": "<code>tests/export-compta.test.js</code> décrit le résultat attendu par la compta, passe avec le code actuel (bogué), et échoue dès que le bug #231 est corrigé.",
             "hints": ["Écrivez d'abord le test normal, avec la valeur exacte que la compta attend d'après le commentaire du module : il est rouge. Comment annoncer cet échec comme connu, sans désactiver le test ?", "Relisez la fin du cours du jour."],
             "checks": [
                 ('has tests/export-compta.test.js "\\.failing\\b"', "Le bug connu doit être documenté par un test marqué comme échec attendu."),
                 ('verif pass --tests tests/export-compta.test.js --bug bug-export', "tests/export-compta.test.js est absent ou ne passe pas avec le code actuel (bogué)."),
                 ('verif reproduce --tests tests/export-compta.test.js --ref', "Votre suite reste verte quand le bug est corrigé : votre test attend-il la bonne valeur ?"),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    10: {
        "title": "Jour 10 — Mise en production",
        "description": "Une suite fiable, exécutée automatiquement. Compétences : .only/.skip, jest.config.js, suite complète, intégration continue (GitHub Actions).",
        "lesson": """<h3>Les pièges qui passent en revue de code</h3><ul><li><code>test.only</code> / <code>describe.only</code> / <code>fit</code> : dans le <strong>fichier</strong> qui les contient, seuls ces tests s'exécutent ; les autres tests du fichier sont comptés comme <em>skipped</em> dans le résumé, et passent facilement inaperçus. Les autres fichiers, eux, s'exécutent normalement.</li><li><code>test.skip</code> / <code>xit</code> / <code>xdescribe</code> : test désactivé, souvent « temporairement »… pour toujours.</li><li>Ces modificateurs se combinent : <code>test.only.each</code>, <code>describe.skip.each</code>, <code>test.concurrent.only</code>…</li></ul><h3>Un fichier de configuration</h3><pre>// jest.config.js<br>module.exports = {<br>  testEnvironment: 'node',<br>  collectCoverageFrom: ['src/**/*.js'],<br>};</pre><p>Une seule configuration à la fois : clé <code>"jest"</code> de <code>package.json</code> <strong>ou</strong> <code>jest.config.js</code>. Les options <code>clearMocks</code>, <code>resetMocks</code> et <code>restoreMocks</code> (jour 5) y automatisent la remise à zéro des doublures avant chaque test.</p><h3>Intégration continue avec GitHub Actions</h3><p>Un fichier <code>.github/workflows/*.yml</code> décrit quand et comment lancer des commandes sur les serveurs de GitHub. Exemple, pour une analyse du code à chaque push :</p><pre>name: Lint<br>on: push<br>jobs:<br>  lint:<br>    runs-on: ubuntu-latest<br>    steps:<br>      - uses: actions/checkout@v5<br>      - uses: actions/setup-node@v5<br>        with:<br>          node-version: 24<br>      - run: npm ci<br>      - run: npm run lint</pre><p>Plusieurs événements : <code>on: [push, pull_request]</code>. Pour exécuter le même job dans plusieurs configurations, une <strong>matrice</strong> :</p><pre>    strategy:<br>      matrix:<br>        os: [ubuntu-latest, windows-latest]<br>    runs-on: ${{ matrix.os }}</pre><div class="tip"><code>npm ci</code> installe exactement les versions du <code>package-lock.json</code> (il échoue s'il est absent ou désynchronisé de <code>package.json</code>) : les résultats de la CI sont reproductibles. Ce fichier se versionne ; <code>node_modules</code>, jamais (<code>.gitignore</code>).</div>""",
        "setup": r'''
if [ -f $P/tests/wip-thomas.test.js ]; then emit WIP_MIN 2; else emit WIP_MIN 5; fi
# Le brouillon de Thomas suit la grille de livraison de l'étudiant (tirée au jour 3)
v=$(tirer J3_1 4 src/livraison.js)
emit VARIANTE_J3_1 "$v"
livrer tests/wip-thomas.test.js package-lock.json .gitignore
''',
        "exercises": [
            {"id": "J10.1", "points": 5, "title": "Feu vert", "manual": True,
             "ticket": {"from": "nadia", "body": "Dernière ligne droite avant la mise en production. Thomas a laissé un brouillon <code>tests/wip-thomas.test.js</code>… plein de tests focalisés et désactivés. Nettoie tout ça : aucun test focalisé ou désactivé dans <code>tests/</code>, les tests du brouillon réactivés (et justes : certains n'ont jamais tourné…), et <strong>toute la suite</strong> doit passer avec ton code et tes seuils de couverture."},
             "desc": "Aucun test focalisé ou désactivé dans <code>tests/</code> ; tous les tests du brouillon de Thomas sont conservés, réactivés et passent ; <code>jest --coverage</code> réussit sur l'ensemble du projet, seuils compris (les exercices précédents, dont J4.2 et J9.2, doivent être terminés).",
             "hints": ["Cherchez les tests focalisés ou désactivés dans tout <code>tests/</code>, sous toutes leurs formes (relisez le cours).", "Un test réactivé qui échoue : est-ce le code ou la valeur attendue qui est faux ? Recalculez-la à partir de la grille de <code>src/livraison.js</code> (commentaires et table des suppléments). Puis lancez <code>npm run test:coverage</code>."],
             "checks": [
                 ('for f in $(cd $P && find tests -name "*.js" -not -path "*/node_modules/*" 2>/dev/null); do verif grep "$f" \'' + FOCUS_SKIP + '\' && exit 1; done; exit 0', "Il reste des tests focalisés (.only, fit…) ou désactivés (.skip, xit…) dans tests/."),
                 ('verif pass --tests tests/wip-thomas.test.js --min ${LAB_WIP_MIN:-2}', "Les tests du brouillon de Thomas doivent tous être conservés, réactivés et passer."),
                 ('verif suite', "La suite complète n'est pas au vert."),
             ]},
            {"id": "J10.2", "points": 5, "title": "L'intégration continue", "manual": True,
             "ticket": {"from": "sophie", "body": "Dernière demande : je ne veux plus jamais entendre « ça passait chez moi ». Mets en place un workflow <strong>GitHub Actions</strong> qui lance la suite de tests, avec la couverture, à chaque push et à chaque pull request, sur les <strong>deux versions LTS de Node encore maintenues</strong> (22 et 24), avec des dépendances installées exactement comme sur nos postes."},
             "desc": "<code>.github/workflows/tests.yml</code> : un workflow valide, déclenché sur <code>push</code> et <code>pull_request</code>, qui récupère le code, installe Node 22 et Node 24, installe les dépendances de façon reproductible et lance les tests avec la couverture.",
             "hints": ["Faites la liste : quels événements, quel environnement, quelles étapes, dans quel ordre ? Le cours donne la forme d'un workflow et celle d'une matrice.", "Pour vérifier votre YAML : <code>node -e \"console.log(JSON.stringify(require('js-yaml').load(require('fs').readFileSync('.github/workflows/tests.yml', 'utf8')), null, 2))\"</code>."],
             "checks": [
                 ('test -f $P/.github/workflows/tests.yml', "Le fichier .github/workflows/tests.yml n'existe pas."),
                 ('verif workflow .github/workflows/tests.yml', "Le workflow ne fait pas tout ce qui est demandé."),
             ]},
            {"id": "J10.3", "points": 5, "title": "Une configuration à part", "manual": True,
             "ticket": {"from": "nadia", "body": "<code>package.json</code> devient illisible : déplace toute la configuration de Jest dans un <code>jest.config.js</code>, sans rien perdre. Et profites-en : on a eu assez de doublures qui fuient d'un test à l'autre. Active la remise à zéro <strong>complète</strong> de toutes les doublures avant chaque test (appels, valeurs programmées, implémentations) et la restauration automatique des espions. La suite doit rester verte."},
             "desc": "La configuration de Jest est dans <code>jest.config.js</code> (plus aucune clé <code>jest</code> dans <code>package.json</code>), garde la couverture et les seuils du jour 8, remet à zéro toutes les doublures et restaure les espions avant chaque test, et la suite complète passe.",
             "hints": ["Relisez le tableau de remise à zéro du jour 5 : quelle option correspond à chaque demande de Nadia ? Une seule ne suffit pas.", "Si la suite casse après le changement, cherchez les doublures programmées une seule fois pour tout un fichier."],
             "checks": [
                 ('[ "$(pkg \'p.jest === undefined\')" = true ]', "package.json contient encore une clé « jest »."),
                 ('verif config --expr \'where === "jest.config.js"\'', "La configuration de Jest doit être dans jest.config.js."),
                 ('verif config --expr \'couvreSrc() && c.coverageThreshold && c.coverageThreshold.global && c.coverageThreshold.global.branches >= 80 && c.coverageThreshold.global.lines >= 90 && Object.entries(c.coverageThreshold).some(([k, v]) => /(^|\\/)src\\/prix\\.js$/.test(k) && v && v.branches >= 100)\'', "La configuration de la couverture et ses seuils (jour 8) ont été perdus en route."),
                 ('verif config --expr \'c.resetMocks === true && c.restoreMocks === true\'', "La remise à zéro complète des doublures et la restauration des espions ne sont pas toutes les deux activées."),
                 ('verif suite', "La suite complète n'est pas au vert."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    11: {
        "title": "Jour 11 — Instantanés (snapshots)",
        "description": "Figer une sortie complexe, et la relire. Compétences : toMatchSnapshot, fichiers .snap, mise à jour avec -u, relecture critique.",
        "lesson": """<h3>Le principe</h3><p>Pour une sortie longue (un texte, un gros objet), écrire la valeur attendue à la main est fastidieux. Un <strong>snapshot</strong> l'enregistre à la première exécution, puis la compare aux suivantes :</p><pre>test('récapitulatif simple', () =&gt; {<br>  expect(recapitulatif(panier, { pays: 'FR', port: 0 })).toMatchSnapshot();<br>});</pre><ul><li>Premier lancement (hors CI) : Jest écrit <code>tests/__snapshots__/recapitulatif.test.js.snap</code>.</li><li>Lancements suivants : toute différence fait échouer le test, avec un diff lisible.</li><li>Changement voulu : <code>npx jest -u</code> réécrit les snapshots… <strong>après</strong> avoir lu le diff.</li><li>Avec <code>--ci</code>, un snapshot absent fait échouer le test au lieu d'être créé.</li></ul><div class="tip">Le fichier <code>.snap</code> fait partie du code : on le versionne et on le <strong>relit</strong> en revue. Un snapshot enregistre le comportement du moment, bugs compris. Mettre à jour sans lire, c'est valider un bug.</div><h3>Bonnes pratiques</h3><ul><li>Des snapshots petits et ciblés, un par situation significative (et pas un seul énorme).</li><li>Des données de test qui rendent chaque règle visible dans le résultat.</li><li>Pour une valeur qui change à chaque exécution (date, identifiant aléatoire), des matchers à trous : <code>toMatchSnapshot({ date: expect.any(Date) })</code>.</li></ul><p><code>toMatchInlineSnapshot()</code> écrit le snapshot directement dans le fichier de test, mais nécessite l'outil Prettier, absent de ce projet.</p>""",
        "setup": r'''
livrer src/recapitulatif.js tests/etiquette.test.js tests/__snapshots__/etiquette.test.js.snap
livrer --set etiquette-bugs src/etiquette.js
''',
        "exercises": [
            {"id": "J11.1", "points": 5, "title": "Le récapitulatif de commande", "manual": True,
             "ticket": {"from": "sophie", "body": "Avant de payer, le client reçoit un récapitulatif texte de sa commande (<code>recapitulatif</code>, dans <code>src/recapitulatif.js</code>). Il a été validé ligne à ligne par le juridique : je veux qu'aucun caractère ne change sans qu'on le voie. Fige-le dans des snapshots, en couvrant les situations qui comptent."},
             "desc": "<code>tests/recapitulatif.test.js</code> utilise des snapshots enregistrés, passe (y compris en mode CI) et détecte toute modification du récapitulatif.",
             "hints": ["Un snapshot ne vérifie que ce que montrent vos données : quelles situations font apparaître chaque règle décrite dans le commentaire de la fonction ?", "Plusieurs produits, des quantités, des prix qui donnent des centimes, une livraison payante et une offerte… Lancez <code>npx jest tests/recapitulatif</code> pour enregistrer, puis relisez le fichier <code>.snap</code>."],
             "checks": [
                 ('has tests/recapitulatif.test.js "toMatchSnapshot"', "tests/recapitulatif.test.js doit utiliser toMatchSnapshot."),
                 ('verif pass --tests tests/recapitulatif.test.js', "tests/recapitulatif.test.js est absent ou ne passe pas en mode CI (les snapshots ont-ils été enregistrés ?)."),
                 ('verif kill --tests tests/recapitulatif.test.js --set recap', "Vos snapshots ne détectent pas toutes les modifications du récapitulatif."),
             ]},
            {"id": "J11.2", "points": 6, "title": "Le snapshot qui fige un bug", "manual": True,
             "ticket": {"from": "thomas", "body": "Le transporteur nous renvoie des colis pour la Belgique : « étiquette non conforme ». Pourtant <code>tests/etiquette.test.js</code> est vert, j'ai même un snapshot ! Tu peux regarder <code>src/etiquette.js</code> ? La norme du transporteur est dans son commentaire."},
             "desc": "<code>src/etiquette.js</code> respecte la norme du transporteur ; le snapshot de <code>tests/etiquette.test.js</code> contient l'étiquette correcte et détecte toute étiquette non conforme.",
             "hints": ["Relisez le fichier <code>.snap</code> ligne par ligne, en face du commentaire de la fonction et des données du test : que devrait-il contenir ?", "Corrigez le code, puis mettez à jour le snapshot… en vérifiant le nouveau contenu avant de l'accepter."],
             "checks": [
                 ('has tests/etiquette.test.js "toMatchSnapshot"', "tests/etiquette.test.js doit garder son snapshot."),
                 ('verif pass --tests tests/etiquette.test.js', "Le snapshot de tests/etiquette.test.js ne correspond pas à une étiquette conforme (ou le test est absent)."),
                 ('verif kill --tests tests/etiquette.test.js --set etiquette-bugs', "Le snapshot ne détecte pas toutes les étiquettes non conformes."),
                 ('verif hidden --set etiquette', "src/etiquette.js ne respecte pas encore la norme du transporteur."),
                 ('verif pass --tests tests/etiquette.test.js --src student', "tests/etiquette.test.js ne passe pas avec votre code."),
             ]},
        ],
    },
}
