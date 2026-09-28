"""Parcours « Tests unitaires avec Jest » (niveau avancé).

Même format que le catalogue Linux (courses/linux/catalogue.py). Les vérifications s'appuient sur le correcteur de l'image
jest-lab (/opt/jest-lab/verifier.js) :
  - pass      : les tests de l'étudiant passent sur le code de référence (ou le sien) ;
  - kill      : ils échouent contre chaque mutant (version boguée) d'un jeu défini dans
                images/jest/mutants.json — c'est ce qui prouve qu'ils testent vraiment quelque chose ;
  - hidden    : des tests cachés valident le code écrit par l'étudiant (TDD) ;
  - reproduce : un test doit échouer sur la version boguée signalée ;
  - coverage / suite : couverture de code et suite complète.
Toutes les vérifications exécutent du code : elles sont « manuelles » (sur clic).
"""

EXERCISES_VERSION = "1"

MENTOR = "nadia"

SETUP_PRELUDE = r'''
set -e
H=/home/etudiant
P=$H/boutique
emit() { echo "@$1=$2"; }
livrer() { node /opt/jest-lab/verifier.js deliver "$@"; }
'''

CHECK_PRELUDE = r'''
H=/home/etudiant
P=$H/boutique
verif() { node /opt/jest-lab/verifier.js "$@"; }
has() { grep -qE -- "$2" "$P/$1" 2>/dev/null; }
pkg() { node -p "try { const p = require('$P/package.json'); String($1) } catch (e) { '' }" 2>/dev/null; }
'''

INTRO = """<div class="scenario"><h3>Nouvelle mission chez Cimes &amp; Sentiers</h3><p>La boutique en ligne grossit, et chaque mise en production casse quelque chose : un prix mal arrondi, une livraison offerte à tort, un code promo accepté la veille de son expiration… <strong>Nadia Haddad</strong>, lead développeuse, vous confie la qualité du code métier (<code>~/boutique</code>) : écrire des tests unitaires avec <strong>Jest</strong>, puis faire en sorte qu'aucune régression ne passe.</p><p><strong>Comment vos tests sont évalués</strong> : ils sont exécutés sur le code de référence (ils doivent passer), puis sur des <strong>versions volontairement boguées</strong> du même code (« mutants »), qu'ils doivent toutes détecter. Un test qui passe toujours ne protège de rien.</p><p>Éditez les fichiers dans l'éditeur (<kbd>Ctrl+S</kbd> pour enregistrer) et lancez <code>npx jest</code> dans le terminal. Les vérifications exécutent vos tests : cliquez sur <strong>Vérifier</strong> quand vous êtes prêt·e.</p></div>"""

STEPS = {
    # ─────────────────────────────────────────────────────────────────────
    1: {
        "title": "Jour 1 — La CI est rouge",
        "description": "Prise en main de Jest. Compétences : test, expect, describe, toBe, toBeCloseTo, scripts npm.",
        "lesson": INTRO + """<h3>Anatomie d'un test</h3><pre>const { calculerTTC } = require('../src/prix');<br><br>describe('calculerTTC', () =&gt; {<br>  test('ajoute 20 % de TVA', () =&gt; {<br>    expect(calculerTTC(100)).toBe(120);<br>  });<br>});</pre><p>Jest trouve seul les fichiers <code>*.test.js</code>. Un test échoue dès qu'un <code>expect</code> n'est pas satisfait ou qu'une exception non attendue est levée.</p><h3>Égalité et nombres à virgule</h3><ul><li><code>toBe</code> — égalité stricte (<code>Object.is</code>) : parfait pour les primitives</li><li><code>toEqual</code> / <code>toStrictEqual</code> — égalité de structure (objets, tableaux)</li><li><code>toBeCloseTo(x, chiffres)</code> — tolérance pour les flottants (2 chiffres par défaut : écart &lt; 0,005)</li></ul><div class="tip"><code>0.1 + 0.2 === 0.30000000000000004</code>. Mais attention : si la règle métier dit « arrondi au centime », le test doit vérifier <strong>la valeur arrondie exacte</strong>. Une tolérance trop large laisserait passer un code qui n'arrondit pas.</div><h3>Lancer les tests</h3><pre>npx jest                    # toute la suite<br>npx jest tests/prix         # les fichiers dont le chemin contient « tests/prix »<br>npx jest -t "TVA"           # les tests dont le nom contient « TVA »<br>npx jest --watch            # relance à chaque sauvegarde</pre><h3>Scripts npm</h3><p>Dans <code>package.json</code>, la section <code>scripts</code> standardise les commandes de l'équipe :</p><pre>"scripts": {<br>  "test": "jest",<br>  "test:watch": "jest --watch"<br>}</pre><p>Puis <code>npm test</code>, ou <code>npm run test:watch</code>.</p>""",
        "setup": r'''
livrer package.json README.md src/prix.js tests/prix.test.js
''',
        "exercises": [
            {"id": "J1.1", "points": 4, "title": "Le test qui ment", "manual": True,
             "ticket": {"from": "thomas", "body": "La CI est rouge depuis ce matin sur <code>tests/prix.test.js</code>. Je te jure que <code>calculerTTC</code> est juste : la règle, c'est un prix TTC <strong>arrondi au centime</strong>. C'est mon test qui est faux… tu peux le corriger ? Sans toucher au code, et sans supprimer le test, hein 😅"},
             "desc": "<code>tests/prix.test.js</code> passe, garde ses 3 tests (dont celui à 19,99 €) et détecte un calcul non arrondi.",
             "hints": ["Lancez <code>npx jest tests/prix</code> et lisez la différence entre <em>Expected</em> et <em>Received</em>.", "Quel est le prix TTC de 19,99 € HT, arrondi au centime ? Écrivez cette valeur exacte avec <code>toBe</code> : <code>toBeCloseTo</code> accepterait aussi 23,988."],
             "checks": [
                 ('has tests/prix.test.js "19[.,]99"', "Le test de l'article à 19,99 € a disparu : il fallait le corriger, pas le supprimer."),
                 ('verif pass --tests tests/prix.test.js --min 3', "tests/prix.test.js ne passe pas avec le code de référence."),
                 ('verif kill --tests tests/prix.test.js --set prix-ttc', "Le test corrigé est trop permissif."),
             ]},
            {"id": "J1.2", "points": 2, "title": "Des commandes pour toute l'équipe", "manual": True,
             "ticket": {"from": "nadia", "body": "Bienvenue ! Première règle de l'équipe : tout le monde lance les tests de la même façon. Ajoute au <code>package.json</code> les scripts <code>test</code>, <code>test:watch</code> et <code>test:coverage</code>."},
             "desc": "Dans <code>package.json</code> : <code>test</code> lance <code>jest</code>, <code>test:watch</code> le mode <code>--watch</code>, <code>test:coverage</code> l'option <code>--coverage</code>.",
             "hints": ["Le fichier doit rester un JSON valide : attention aux virgules et aux guillemets doubles.", '<code>"scripts": { "test": "jest", "test:watch": "jest --watch", "test:coverage": "jest --coverage" }</code>'],
             "checks": [
                 ('node -e "require(\'$P/package.json\')"', "package.json n'est plus un JSON valide."),
                 ('[ "$(pkg \'p.scripts.test\')" = jest ]', "Le script « test » doit valoir exactement « jest »."),
                 ('pkg \'p.scripts["test:watch"]\' | grep -q -- "jest.*--watch"', "Le script « test:watch » doit lancer jest avec --watch."),
                 ('pkg \'p.scripts["test:coverage"]\' | grep -q -- "jest.*--coverage"', "Le script « test:coverage » doit lancer jest avec --coverage."),
             ]},
            {"id": "J1.3", "points": 5, "title": "Arrondi commercial", "manual": True,
             "ticket": {"from": "diallo", "body": "Bonjour, ici la compta. La fonction <code>arrondir</code> de <code>src/prix.js</code> sert pour toutes nos factures. Je veux la garantie qu'elle arrondit <strong>au centime le plus proche</strong>, y compris dans les cas piégeux : 1,005 € doit donner 1,01 € (le précédent logiciel donnait 1,00 € et on a eu un contrôle fiscal)."},
             "desc": "Un fichier <code>tests/arrondir.test.js</code> (au moins 3 tests) qui passe et détecte toutes les variantes d'arrondi erronées.",
             "hints": ["Pensez à un cas qui doit arrondir vers le bas, un autre vers le haut, et au piège 1,005.", "Un montant déjà rond (ex. 12,5) ou un entier doivent rester inchangés."],
             "checks": [
                 ('verif pass --tests tests/arrondir.test.js --min 3', "tests/arrondir.test.js est absent, ne passe pas ou contient moins de 3 tests."),
                 ('verif kill --tests tests/arrondir.test.js --set arrondir', "Vos tests ne détectent pas toutes les erreurs d'arrondi."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Jour 2 — Le panier",
        "description": "Choisir le bon matcher. Compétences : toEqual, toStrictEqual, toMatchObject, toContainEqual, toHaveLength, toThrow.",
        "lesson": """<h3>Matchers de structure</h3><table class="lesson-table"><tr><th>Matcher</th><th>Usage</th></tr><tr><td><code>toEqual(obj)</code></td><td>Même structure (ignore les propriétés <code>undefined</code>)</td></tr><tr><td><code>toStrictEqual(obj)</code></td><td>Même structure, plus stricte (<code>undefined</code>, classes)</td></tr><tr><td><code>toMatchObject(partiel)</code></td><td>Contient au moins ces propriétés</td></tr><tr><td><code>toContainEqual(item)</code></td><td>Un tableau contient un élément de cette structure</td></tr><tr><td><code>toHaveLength(n)</code></td><td>Longueur d'un tableau ou d'une chaîne</td></tr><tr><td><code>not</code></td><td>Inverse : <code>expect(x).not.toBe(y)</code></td></tr></table><h3>Tester une exception</h3><pre>expect(() =&gt; panier.ajouter(gourde, 0)).toThrow(RangeError);<br>expect(() =&gt; panier.ajouter(gourde, 0)).toThrow('Quantité invalide');</pre><div class="tip">On passe une <strong>fonction</strong> à <code>expect</code>. <code>expect(panier.ajouter(gourde, 0))</code> lèverait l'exception avant même que Jest puisse l'attraper.</div><h3>Tester l'encapsulation</h3><p>Une méthode qui renvoie des données internes doit renvoyer une <strong>copie</strong>. Pour le vérifier : modifiez ce qui est renvoyé, puis constatez que l'objet d'origine n'a pas bougé.</p><h3>Bonnes pratiques</h3><ul><li>Un test = un comportement, avec un nom qui le décrit (« cumule les quantités d'une même référence »).</li><li>Structure <em>Arrange / Act / Assert</em> : préparer, agir, vérifier.</li><li>Testez aussi les cas limites et les erreurs, pas seulement le cas nominal.</li></ul>""",
        "setup": r'''
livrer src/panier.js
''',
        "exercises": [
            {"id": "J2.1", "points": 5, "title": "Le panier sous contrôle", "manual": True,
             "ticket": {"from": "nadia", "body": "<code>src/panier.js</code> n'a aucun test et tout le tunnel de commande repose dessus. Couvre son comportement : ajout, cumul d'une même référence, quantité par défaut, retrait, nombre d'articles, total HT, panier vide."},
             "desc": "<code>tests/panier.test.js</code> (au moins 5 tests) qui passe et détecte les régressions du panier.",
             "hints": ["Lisez attentivement <code>src/panier.js</code> : chaque méthode porte une règle à vérifier.", "Utilisez au moins deux produits différents, et des quantités supérieures à 1."],
             "checks": [
                 ('verif pass --tests tests/panier.test.js --min 5', "tests/panier.test.js est absent, ne passe pas ou contient moins de 5 tests."),
                 ('verif kill --tests tests/panier.test.js --set panier-base', "Vos tests ne détectent pas toutes les régressions du panier."),
             ]},
            {"id": "J2.2", "points": 5, "title": "Les cas d'erreur", "manual": True,
             "ticket": {"from": "thomas", "body": "Hier, un client a commandé 0 sac à dos, et un autre 1,5 lampe frontale. Il nous faut des tests sur <strong>toutes les erreurs</strong> : quantités invalides, retrait d'un produit absent, remises hors de 0–100 %, prix HT négatif. Et vérifie le <strong>type</strong> d'erreur : le front affiche un message différent pour une <code>RangeError</code>."},
             "desc": "<code>tests/erreurs.test.js</code>, utilisant <code>toThrow</code>, qui passe et détecte chaque validation manquante ou mal typée.",
             "hints": ["<code>expect(() =&gt; appliquerRemise(50, 120)).toThrow(RangeError)</code>", "Chaque règle de validation a ses deux bornes : testez juste à côté (0, -1, 101…)."],
             "checks": [
                 ('has tests/erreurs.test.js "toThrow"', "tests/erreurs.test.js doit utiliser toThrow."),
                 ('verif pass --tests tests/erreurs.test.js', "tests/erreurs.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/erreurs.test.js --set panier-erreurs', "Vos tests ne détectent pas toutes les validations manquantes."),
             ]},
            {"id": "J2.3", "points": 4, "title": "Fuite de données", "manual": True,
             "ticket": {"from": "nadia", "body": "Un bug vicieux en production : un composant du front modifiait les lignes renvoyées par <code>panier.lignes()</code>… et ça modifiait le vrai panier. C'est corrigé, mais je veux un test qui l'empêche de revenir. Vérifie aussi la structure exacte d'une ligne."},
             "desc": "<code>tests/panier-lignes.test.js</code>, utilisant <code>toEqual</code> ou <code>toStrictEqual</code>, qui détecte toute fuite de l'état interne.",
             "hints": ["Modifiez le tableau renvoyé (<code>push</code>)… et une ligne renvoyée (<code>quantite = 99</code>), puis relisez le panier.", "La structure d'une ligne : <code>{ ref, libelle, prixHT, quantite }</code>."],
             "checks": [
                 ('has tests/panier-lignes.test.js "to(Strict)?Equal"', "tests/panier-lignes.test.js doit utiliser toEqual ou toStrictEqual."),
                 ('verif pass --tests tests/panier-lignes.test.js', "tests/panier-lignes.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/panier-lignes.test.js --set panier-lignes', "Vos tests ne détectent pas toutes les fuites de l'état interne."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Jour 3 — Livraison : les cas limites",
        "description": "Tests paramétrés et isolation. Compétences : test.each, valeurs limites, beforeEach, --randomize.",
        "lesson": """<h3>Tests paramétrés</h3><pre>test.each([<br>  [0.5, 'FR', 4.9],<br>  [1, 'FR', 8.9],<br>])('%s kg vers %s coûte %s €', (poids, pays, attendu) =&gt; {<br>  expect(fraisLivraison(poids, pays)).toBe(attendu);<br>});</pre><p>Variante avec des objets et des noms lisibles :</p><pre>test.each([<br>  { poids: 1, pays: 'BE', attendu: 11.9 },<br>])('$poids kg vers $pays', ({ poids, pays, attendu }) =&gt; { ... });</pre><h3>Analyse des valeurs limites</h3><p>Les bugs se cachent aux frontières : pour une règle « moins de 1 kg », testez <strong>juste en dessous, pile sur la limite, juste au-dessus</strong> (0,99 · 1 · 1,01). Une règle <code>&lt;</code> écrite <code>&lt;=</code> par erreur ne se voit que sur la limite exacte.</p><h3>Isolation des tests</h3><p>Chaque test doit pouvoir s'exécuter seul et dans n'importe quel ordre. Un état partagé entre tests (une variable créée une seule fois en haut du fichier) crée des dépendances cachées.</p><pre>let panier;<br>beforeEach(() =&gt; {<br>  panier = new Panier();<br>});</pre><p>Autres hooks : <code>afterEach</code>, <code>beforeAll</code>, <code>afterAll</code>.</p><div class="tip"><code>npx jest --randomize</code> exécute les tests dans un ordre aléatoire (affiché sous forme de <em>seed</em>) : idéal pour débusquer les tests dépendants. <code>--seed=42</code> rejoue un ordre précis.</div>""",
        "setup": r'''
livrer src/livraison.js tests/panier-thomas.test.js
''',
        "exercises": [
            {"id": "J3.1", "points": 6, "title": "La grille tarifaire", "manual": True,
             "ticket": {"from": "sophie", "body": "Le transporteur a changé ses tarifs et <code>src/livraison.js</code> a été réécrit en urgence. Avant la mise en ligne, je veux la grille <strong>entièrement</strong> vérifiée : chaque tranche de poids, chaque pays, les seuils de livraison offerte, et les cas refusés. Les commentaires du fichier font foi."},
             "desc": "<code>tests/livraison.test.js</code> utilisant <code>test.each</code> (au moins 8 tests), qui passe et détecte toutes les erreurs de grille, de limites et de seuils.",
             "hints": ["Pour chaque limite (1 kg, 5 kg, 60 €, 100 €) : juste en dessous, pile dessus.", "Pensez aux cas refusés : pays non desservi, poids nul. Et testez les deux fonctions du module."],
             "checks": [
                 ('has tests/livraison.test.js "\\.each"', "tests/livraison.test.js doit utiliser test.each (ou it.each / describe.each)."),
                 ('verif pass --tests tests/livraison.test.js --min 8', "tests/livraison.test.js est absent, ne passe pas ou contient moins de 8 tests."),
                 ('verif kill --tests tests/livraison.test.js --set livraison', "Vos tests ne détectent pas toutes les erreurs de la grille tarifaire."),
             ]},
            {"id": "J3.2", "points": 4, "title": "« Ils passent chez moi »", "manual": True,
             "ticket": {"from": "thomas", "body": "La CI échoue une fois sur trois sur <code>tests/panier-thomas.test.js</code>, alors que chez moi tout est vert ! Nadia dit que mes tests « dépendent de leur ordre ». Tu peux les réparer, sans en supprimer ?"},
             "desc": "<code>tests/panier-thomas.test.js</code> garde au moins 5 tests, utilise <code>beforeEach</code> et passe dans n'importe quel ordre (<code>--randomize</code>).",
             "hints": ["Lancez <code>npx jest tests/panier-thomas --randomize</code> plusieurs fois.", "Chaque test doit partir d'un panier neuf créé dans <code>beforeEach</code>, et préparer lui-même ce dont il a besoin."],
             "checks": [
                 ('has tests/panier-thomas.test.js "beforeEach"', "tests/panier-thomas.test.js doit utiliser beforeEach."),
                 ('verif pass --tests tests/panier-thomas.test.js --min 5', "Les tests ne passent pas (ou il en reste moins de 5)."),
                 ('verif pass --tests tests/panier-thomas.test.js --seeds 1,2,3,4,5,6', "Les tests échouent quand on change leur ordre d'exécution."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Jour 4 — TDD : les codes promo",
        "description": "Développement piloté par les tests. Compétences : tests d'après une spécification, maîtrise du temps, Red-Green-Refactor.",
        "lesson": """<h3>Le cycle TDD</h3><ol><li><strong>Red</strong> : écrire un test qui échoue, pour un comportement pas encore codé.</li><li><strong>Green</strong> : écrire le code le plus simple qui le fait passer.</li><li><strong>Refactor</strong> : améliorer le code, les tests restant verts.</li></ol><p>Les tests deviennent la spécification exécutable du module.</p><h3>Des tests indépendants de la date</h3><p>Un test qui utilise la date du jour passe aujourd'hui… et échoue le jour où un code expire. Deux solutions :</p><ul><li><strong>Injecter la date</strong> : <code>validerCode('RANDO10', new Date('2026-06-01'))</code>.</li><li><strong>Figer l'horloge</strong> :<pre>jest.useFakeTimers({ now: new Date('2026-06-01') });<br>// ... puis<br>jest.useRealTimers();</pre></li></ul><div class="tip">Vos tests seront aussi exécutés avec une horloge système déplacée dans le futur : s'ils dépendent du jour réel, ils échoueront.</div><h3>Couvrir une spécification</h3><ul><li>Un test par règle, et un par raison de refus.</li><li>Les limites : longueur minimale et maximale, dernier jour de validité, premier jour d'expiration.</li><li>Les priorités entre règles (que se passe-t-il si deux règles s'appliquent ?).</li></ul>""",
        "setup": r'''
livrer src/data/codes.js src/codesPromo.js SPEC-codes-promo.md
''',
        "exercises": [
            {"id": "J4.1", "points": 6, "title": "Red : la spécification en tests", "manual": True,
             "ticket": {"from": "nadia", "body": "Le marketing veut des codes promo pour lundi. On fait ça en TDD : lis <code>SPEC-codes-promo.md</code> et écris d'abord les tests. Je les ferai tourner sur mon implémentation de référence : ils doivent passer, et attraper toutes les erreurs classiques. Et pas de test qui dépend de la date du jour, on s'est déjà fait avoir."},
             "desc": "<code>tests/codesPromo.test.js</code> (au moins 6 tests), indépendant de la date réelle, qui passe sur l'implémentation de référence et détecte ses variantes erronées.",
             "hints": ["Relisez chaque règle de la spécification : chacune mérite au moins un test, et chaque limite aussi.", "Passez toujours le 2e argument <code>maintenant</code>, ou figez l'horloge avec <code>jest.useFakeTimers({ now })</code>. Le code NOEL25 est à la fois expiré et épuisé."],
             "checks": [
                 ('verif pass --tests tests/codesPromo.test.js --min 6', "tests/codesPromo.test.js est absent, ne passe pas sur l'implémentation de référence ou contient moins de 6 tests."),
                 ('verif pass --tests tests/codesPromo.test.js --fake-date', "Vos tests dépendent de la date du jour."),
                 ('verif kill --tests tests/codesPromo.test.js --set codes', "Vos tests ne couvrent pas toute la spécification."),
             ]},
            {"id": "J4.2", "points": 6, "title": "Green : l'implémentation", "manual": True,
             "ticket": {"from": "nadia", "body": "Tes tests sont prêts, à toi d'écrire <code>validerCode</code> dans <code>src/codesPromo.js</code>. Quand tout est vert chez toi, je lance ma propre batterie de validation."},
             "desc": "<code>src/codesPromo.js</code> implémente la spécification : vos tests et les tests de validation de Nadia passent.",
             "hints": ["Normalisez la saisie avec <code>trim()</code> et <code>toUpperCase()</code> avant tout.", "Le dernier jour est inclus : comparez à <code>new Date(`${expire}T23:59:59.999`)</code>."],
             "checks": [
                 ('verif pass --tests tests/codesPromo.test.js --src student', "Vos propres tests ne passent pas avec votre implémentation."),
                 ('verif hidden --set codes', "Votre implémentation ne respecte pas toute la spécification."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Jour 5 — Doublures de test",
        "description": "Isoler le code de ses dépendances. Compétences : jest.fn, mockResolvedValue, toHaveBeenCalledWith, jest.mock.",
        "lesson": """<h3>Pourquoi des doublures ?</h3><p>Un test unitaire ne doit appeler ni la banque, ni le serveur de mails, ni l'API de stock : c'est lent, instable, et parfois coûteux. On remplace ces dépendances par des <strong>doublures</strong> contrôlées.</p><h3>jest.fn() : une fonction espionne</h3><pre>const stockApi = { quantiteDisponible: jest.fn() };<br>stockApi.quantiteDisponible.mockResolvedValue(3);          // toujours 3<br>stockApi.quantiteDisponible.mockResolvedValueOnce(0);      // 0 au prochain appel<br>stockApi.quantiteDisponible.mockImplementation(async (ref) =&gt; stocks[ref]);</pre><p>Vérifier les appels :</p><pre>expect(stockApi.quantiteDisponible).toHaveBeenCalledTimes(2);<br>expect(stockApi.quantiteDisponible).toHaveBeenCalledWith('GOURDE-1L');<br>expect(mailer.envoyer).not.toHaveBeenCalled();</pre><h3>jest.mock() : remplacer un module entier</h3><p>Quand le code fait lui-même <code>require('./services/paiement')</code>, on ne peut pas lui passer de doublure. On demande à Jest de remplacer le module :</p><pre>jest.mock('../src/services/paiement');<br>const paiement = require('../src/services/paiement');<br><br>paiement.debiter.mockResolvedValue({ accepte: true, transaction: 'TX-1' });</pre><p>Toutes les fonctions exportées deviennent des <code>jest.fn()</code>.</p><div class="tip">Remettez les doublures à zéro entre les tests : <code>beforeEach(() =&gt; jest.clearAllMocks())</code>, ou <code>"clearMocks": true</code> dans la configuration.</div><h3>Asynchrone</h3><p>Un test peut être <code>async</code> : <code>const r = await verifierDisponibilite(panier, api);</code>. Sans <code>await</code> (ou <code>return</code>), Jest termine le test avant la promesse… et il passe toujours.</p>""",
        "setup": r'''
livrer src/stock.js src/commande.js src/services/paiement.js src/services/mailer.js
''',
        "exercises": [
            {"id": "J5.1", "points": 5, "title": "Rupture de stock", "manual": True,
             "ticket": {"from": "thomas", "body": "<code>verifierDisponibilite</code> (dans <code>src/stock.js</code>) interroge l'API de l'entrepôt pour chaque ligne du panier. Évidemment, pas question d'appeler l'entrepôt depuis les tests : l'API est passée en paramètre, fais-en une doublure. Vérifie ce qu'elle renvoie <strong>et</strong> comment l'API est appelée."},
             "desc": "<code>tests/stock.test.js</code>, avec <code>jest.fn()</code> et <code>toHaveBeenCalledWith</code>, qui passe et détecte les régressions.",
             "hints": ["<code>const api = { quantiteDisponible: jest.fn(async (ref) =&gt; stocks[ref]) }</code>", "Testez un stock insuffisant, un stock tout juste suffisant, et un panier de plusieurs lignes."],
             "checks": [
                 ('has tests/stock.test.js "jest\\.fn"', "tests/stock.test.js doit utiliser jest.fn()."),
                 ('has tests/stock.test.js "toHaveBeenCalledWith"', "tests/stock.test.js doit vérifier les appels avec toHaveBeenCalledWith."),
                 ('verif pass --tests tests/stock.test.js', "tests/stock.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/stock.test.js --set stock', "Vos tests ne détectent pas toutes les régressions."),
             ]},
            {"id": "J5.2", "points": 6, "title": "Passer commande sans débiter personne", "manual": True,
             "ticket": {"from": "sophie", "body": "Incident de la semaine dernière : un test a débité pour de vrai la carte de test… de notre PDG. Désormais <code>src/services/paiement.js</code> et <code>mailer.js</code> refusent de fonctionner dans les tests. Écris les tests du <strong>cas nominal</strong> de <code>passerCommande</code> (<code>src/commande.js</code>) en remplaçant ces deux modules."},
             "desc": "<code>tests/commande.test.js</code>, avec <code>jest.mock</code> des services de paiement et de mail, qui vérifie le montant débité, la carte, l'e-mail et le résultat renvoyé.",
             "hints": ["<code>jest.mock('../src/services/paiement')</code> puis <code>paiement.debiter.mockResolvedValue({ accepte: true, transaction: 'TX-42' })</code>.", "Le montant débité est le total <strong>TTC</strong> du panier : vérifiez-le avec <code>toHaveBeenCalledWith(carte, montant)</code>."],
             "checks": [
                 ('has tests/commande.test.js "jest\\.mock\\([\'\\"]\\.\\./src/services/paiement"', "tests/commande.test.js doit remplacer le module de paiement avec jest.mock('../src/services/paiement')."),
                 ('verif pass --tests tests/commande.test.js', "tests/commande.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/commande.test.js --set commande-ok', "Vos tests ne détectent pas toutes les régressions du cas nominal."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Jour 6 — Quand tout va mal",
        "description": "Tester les chemins d'erreur asynchrones. Compétences : rejects, mockRejectedValueOnce, toHaveBeenCalledTimes.",
        "lesson": """<h3>Promesses rejetées</h3><pre>await expect(passerCommande(panier, client)).rejects.toThrow('Paiement refusé');</pre><div class="tip">Sans <code>await</code> devant <code>expect(...).rejects</code>, le test se termine avant la vérification : il passe toujours, même si le code est faux.</div><p>Alternative : <code>expect.assertions(1)</code> en début de test oblige Jest à vérifier qu'une assertion a bien été exécutée (utile avec <code>try/catch</code>).</p><h3>Simuler des pannes</h3><pre>paiement.debiter<br>  .mockRejectedValueOnce(new Error('Timeout'))            // 1er appel : panne<br>  .mockResolvedValueOnce({ accepte: true, transaction: 'TX-9' }); // 2e : succès</pre><h3>Vérifier ce qui ne doit PAS arriver</h3><pre>expect(mailer.envoyer).not.toHaveBeenCalled();<br>expect(paiement.debiter).toHaveBeenCalledTimes(2);</pre><p>Dans un chemin d'erreur, vérifiez à la fois l'erreur levée et l'absence d'effets de bord (pas d'e-mail de confirmation, pas de second débit…).</p>""",
        "exercises": [
            {"id": "J6.1", "points": 6, "title": "Paiement refusé", "manual": True,
             "ticket": {"from": "diallo", "body": "Un client a reçu un e-mail « commande confirmée » alors que sa banque avait refusé le paiement ! Il nous faut des tests sur les <strong>échecs</strong> de <code>passerCommande</code> : paiement refusé (avec le motif de la banque dans le message), panier vide… et aucun e-mail de confirmation dans ces cas-là."},
             "desc": "<code>tests/commande-erreurs.test.js</code>, utilisant <code>rejects</code>, qui passe et détecte chaque chemin d'erreur mal géré.",
             "hints": ["<code>await expect(passerCommande(...)).rejects.toThrow('Paiement refusé : fonds insuffisants')</code>", "Après un refus : <code>expect(mailer.envoyer).not.toHaveBeenCalled()</code>. Pensez à <code>jest.clearAllMocks()</code> entre les tests."],
             "checks": [
                 ('has tests/commande-erreurs.test.js "rejects"', "tests/commande-erreurs.test.js doit utiliser .rejects."),
                 ('verif pass --tests tests/commande-erreurs.test.js', "tests/commande-erreurs.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/commande-erreurs.test.js --set commande-erreurs', "Vos tests ne détectent pas tous les chemins d'erreur mal gérés."),
             ]},
            {"id": "J6.2", "points": 5, "title": "La banque qui tousse", "manual": True,
             "ticket": {"from": "nadia", "body": "L'API de la banque a des micro-coupures. <code>passerCommande</code> retente <strong>une seule fois</strong> après une erreur technique, puis abandonne avec « Service de paiement indisponible » (on ne montre jamais l'erreur technique brute au client). Verrouille ce comportement."},
             "desc": "<code>tests/commande-reprise.test.js</code>, simulant des pannes avec <code>mockRejectedValueOnce</code> ou <code>mockRejectedValue</code>, qui détecte toute erreur dans la logique de reprise.",
             "hints": ["Deux scénarios : une panne puis un succès, et deux pannes de suite.", "Comptez les tentatives avec <code>toHaveBeenCalledTimes</code>."],
             "checks": [
                 ('has tests/commande-reprise.test.js "mockRejectedValue(Once)?"', "tests/commande-reprise.test.js doit simuler des pannes avec mockRejectedValue ou mockRejectedValueOnce."),
                 ('verif pass --tests tests/commande-reprise.test.js', "tests/commande-reprise.test.js est absent ou ne passe pas."),
                 ('verif kill --tests tests/commande-reprise.test.js --set commande-reprise', "Vos tests ne détectent pas toutes les erreurs de la logique de reprise."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    7: {
        "title": "Jour 7 — Le temps qui passe",
        "description": "Tester du code qui dépend du temps sans attendre. Compétences : jest.useFakeTimers, advanceTimersByTime.",
        "lesson": """<h3>Le problème</h3><p><code>programmerRelance</code> envoie un e-mail 24 h après l'abandon d'un panier. Un test ne peut évidemment pas attendre 24 h (et Jest l'arrête au bout de 5 s).</p><h3>Les faux minuteurs</h3><pre>beforeEach(() =&gt; jest.useFakeTimers());<br>afterEach(() =&gt; jest.useRealTimers());<br><br>test('relance après 24 h', () =&gt; {<br>  programmerRelance(panier, client, mailer);<br>  jest.advanceTimersByTime(24 * 60 * 60 * 1000 - 1);<br>  expect(mailer.envoyer).not.toHaveBeenCalled();<br>  jest.advanceTimersByTime(1);<br>  expect(mailer.envoyer).toHaveBeenCalledTimes(1);<br>});</pre><ul><li><code>jest.advanceTimersByTime(ms)</code> — avance l'horloge virtuelle</li><li><code>jest.runAllTimers()</code> — exécute tous les minuteurs en attente</li><li><code>jest.getTimerCount()</code> — nombre de minuteurs en attente</li></ul><div class="tip">Testez la limite exacte : <strong>juste avant</strong> le délai rien ne doit se passer, <strong>au moment du délai</strong> l'action a lieu.</div>""",
        "setup": r'''
livrer src/relance.js
''',
        "exercises": [
            {"id": "J7.1", "points": 6, "title": "Relance des paniers abandonnés", "manual": True,
             "ticket": {"from": "thomas", "body": "Le marketing a lancé les relances de paniers abandonnés (<code>src/relance.js</code>). Premier jour : des clients relancés au bout d'une heure, d'autres relancés alors qu'ils avaient déjà commandé… Écris des tests qui garantissent le délai de 24 h, l'annulation, et le contenu du message. Sans attendre 24 h, évidemment."},
             "desc": "<code>tests/relance.test.js</code>, avec <code>jest.useFakeTimers</code>, rapide (moins de 5 s), qui détecte toute régression de la relance.",
             "hints": ["Le <code>mailer</code> est passé en paramètre : <code>const mailer = { envoyer: jest.fn() }</code>.", "Scénarios : délai exact (juste avant / pile), annulation, panier vidé entre-temps, texte du message avec plusieurs articles.", "Écrivez le délai attendu en dur (24 h) : si vous réutilisez la constante exportée par le code testé, un délai faux passera inaperçu."],
             "checks": [
                 ('has tests/relance.test.js "useFakeTimers"', "tests/relance.test.js doit utiliser jest.useFakeTimers()."),
                 ('verif pass --tests tests/relance.test.js --max-ms 5000', "tests/relance.test.js est absent, ne passe pas ou est trop lent."),
                 ('verif kill --tests tests/relance.test.js --set relance', "Vos tests ne détectent pas toutes les régressions de la relance."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Jour 8 — Couverture de code",
        "description": "Mesurer ce que les tests exercent. Compétences : --coverage, branches, coverageThreshold.",
        "lesson": """<h3>Mesurer la couverture</h3><pre>npx jest --coverage</pre><table class="lesson-table"><tr><th>Mesure</th><th>Signification</th></tr><tr><td>Statements / Lines</td><td>Instructions / lignes exécutées au moins une fois</td></tr><tr><td>Functions</td><td>Fonctions appelées au moins une fois</td></tr><tr><td>Branches</td><td>Chaque sortie de chaque <code>if</code>, <code>? :</code>, <code>&amp;&amp;</code>… empruntée au moins une fois</td></tr></table><p>Le rapport HTML détaillé est dans <code>coverage/lcov-report/index.html</code> ; la colonne <em>Uncovered Line #s</em> du terminal indique les lignes jamais exécutées.</p><h3>Configurer Jest</h3><p>Dans <code>package.json</code>, clé <code>"jest"</code> :</p><pre>"jest": {<br>  "collectCoverageFrom": ["src/**/*.js"],<br>  "coverageThreshold": {<br>    "global": { "branches": 80, "lines": 90 }<br>  }<br>}</pre><p>Si un seuil n'est pas atteint, <code>jest --coverage</code> échoue : la CI bloque la fusion.</p><div class="tip">100 % de couverture ne prouve pas que le code est juste : un test sans <code>expect</code> « couvre » tout. La couverture montre ce qui n'est <strong>pas</strong> testé ; les mutants montrent si ce qui est exécuté est vraiment vérifié.</div>""",
        "setup": r'''
livrer src/fidelite.js
''',
        "exercises": [
            {"id": "J8.1", "points": 3, "title": "Des seuils dans la CI", "manual": True,
             "ticket": {"from": "nadia", "body": "À partir d'aujourd'hui, la couverture fait partie de la définition de « terminé ». Configure Jest dans <code>package.json</code> : couverture mesurée sur tout <code>src/</code>, et échec si on passe sous <strong>80 % de branches</strong> ou <strong>90 % de lignes</strong>."},
             "desc": "Dans <code>package.json</code> : <code>jest.collectCoverageFrom</code> inclut <code>src/**/*.js</code> et <code>jest.coverageThreshold.global</code> exige au moins 80 % de branches et 90 % de lignes.",
             "hints": ["La configuration va sous une clé <code>\"jest\"</code> au même niveau que <code>\"scripts\"</code>.", "Vérifiez avec <code>npm run test:coverage</code>."],
             "checks": [
                 ('node -e "require(\'$P/package.json\')"', "package.json n'est plus un JSON valide."),
                 ('pkg \'(p.jest.collectCoverageFrom || []).join(" ")\' | grep -qF "src/**/*.js"', "jest.collectCoverageFrom doit inclure « src/**/*.js »."),
                 ('[ "$(pkg \'p.jest.coverageThreshold.global.branches >= 80 && p.jest.coverageThreshold.global.lines >= 90\')" = true ]', "jest.coverageThreshold.global doit exiger au moins 80 % de branches et 90 % de lignes."),
             ]},
            {"id": "J8.2", "points": 6, "title": "Le programme de fidélité", "manual": True,
             "ticket": {"from": "diallo", "body": "Le calcul des points de fidélité (<code>src/fidelite.js</code>) a des règles dans tous les sens : statuts, bonus d'anniversaire, plafond… et zéro test. Je veux que <strong>toutes les branches</strong> soient testées, et que les tests vérifient vraiment les montants de points."},
             "desc": "<code>tests/fidelite.test.js</code> : 100 % des branches et des lignes de <code>src/fidelite.js</code>, et détection de toutes les erreurs de calcul.",
             "hints": ["<code>npx jest tests/fidelite --coverage --collectCoverageFrom=src/fidelite.js</code> montre les lignes non couvertes.", "Branches à couvrir : montant nul, chaque statut, anniversaire présent ou non (et dans le mois ou non), plafond atteint ou non."],
             "checks": [
                 ('verif pass --tests tests/fidelite.test.js', "tests/fidelite.test.js est absent ou ne passe pas."),
                 ('verif coverage --tests tests/fidelite.test.js --file src/fidelite.js --branches 100 --lines 100', "La couverture de src/fidelite.js n'est pas complète."),
                 ('verif kill --tests tests/fidelite.test.js --set fidelite', "Vos tests exécutent tout le code mais ne vérifient pas tous les calculs."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    9: {
        "title": "Jour 9 — Le bug #218",
        "description": "Corriger un bug en commençant par le reproduire. Compétences : test de non-régression, débogage.",
        "lesson": """<h3>Corriger un bug, dans le bon ordre</h3><ol><li><strong>Reproduire</strong> : écrire un test qui échoue et qui montre le bug. Ce test prouve que vous avez compris le problème.</li><li><strong>Corriger</strong> le code : le test passe.</li><li><strong>Garder</strong> le test : c'est un <em>test de non-régression</em>, le bug ne pourra pas revenir sans que la CI le voie.</li></ol><h3>Outils de débogage</h3><ul><li><code>npx jest -t "nom du test"</code> — ne lancer qu'un test</li><li><code>console.log</code> dans le code ou le test (Jest affiche la sortie avec le nom du fichier)</li><li>Calculez à la main le résultat attendu à partir de la règle métier, avant de regarder ce que renvoie le code.</li></ul><div class="tip">Un test de reproduction doit utiliser des valeurs qui <strong>distinguent</strong> le bon comportement du mauvais. Ici, cherchez un panier dont le montant passe sous le seuil <em>à cause de la remise</em>.</div>""",
        "setup": r'''
livrer --set bug-facture src/facture.js
''',
        "exercises": [
            {"id": "J9.1", "points": 5, "title": "Reproduire le bug", "manual": True,
             "ticket": {"from": "sophie", "body": "Ticket #218, remonté par la compta : un client a payé 59,40 € de produits après sa remise de 10 %… et n'a pas payé de frais de port ! Or le commentaire de <code>src/facture.js</code> est clair : le seuil de livraison offerte (60 € en France) s'apprécie <strong>après</strong> remise. Avant toute correction, je veux un test qui reproduise le problème."},
             "desc": "<code>tests/facture.test.js</code> échoue sur la version boguée actuelle et passe sur une version corrigée.",
             "hints": ["55 € HT → 66 € TTC → −10 % = 59,40 € : sous le seuil, donc les frais de port sont dus.", "Comparez tout l'objet renvoyé : <code>{ produitsTTC, port, total }</code>."],
             "checks": [
                 ('verif pass --tests tests/facture.test.js', "tests/facture.test.js est absent, ou ne passe pas sur une version corrigée du code (vos valeurs attendues sont-elles justes ?)."),
                 ('verif reproduce --tests tests/facture.test.js --set bug-facture', "Votre test ne reproduit pas le bug."),
             ]},
            {"id": "J9.2", "points": 4, "title": "Corriger le bug", "manual": True,
             "ticket": {"from": "sophie", "body": "Parfait, le bug est prouvé. Corrige maintenant <code>src/facture.js</code>, et garde ton test : il protégera la facturation."},
             "desc": "<code>src/facture.js</code> corrigé : votre test de facture et les tests de validation passent.",
             "hints": ["Quel montant est passé à <code>livraisonOfferte</code> ? Celui d'avant ou d'après remise ?"],
             "checks": [
                 ('verif pass --tests tests/facture.test.js --src student', "Votre test de facture ne passe pas avec votre code."),
                 ('verif hidden --set facture', "La facturation n'est pas encore correcte."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    10: {
        "title": "Jour 10 — Mise en production",
        "description": "Une suite fiable, exécutée automatiquement. Compétences : .only/.skip, suite complète, intégration continue (GitHub Actions).",
        "lesson": """<h3>Les pièges qui passent en revue de code</h3><ul><li><code>test.only</code> / <code>describe.only</code> / <code>fit</code> : seuls ces tests s'exécutent, les autres sont ignorés en silence.</li><li><code>test.skip</code> / <code>xit</code> : test désactivé, souvent « temporairement »… pour toujours.</li></ul><pre>grep -rnE "\\.(only|skip)\\(|\\b(fit|xit|xtest)\\(" tests/</pre><h3>Intégration continue avec GitHub Actions</h3><p>Un fichier <code>.github/workflows/tests.yml</code> lance les tests à chaque push et pull request :</p><pre>name: Tests<br>on: [push, pull_request]<br>jobs:<br>  tests:<br>    runs-on: ubuntu-latest<br>    steps:<br>      - uses: actions/checkout@v4<br>      - uses: actions/setup-node@v4<br>        with:<br>          node-version: 20<br>      - run: npm ci<br>      - run: npm test -- --coverage</pre><div class="tip"><code>npm ci</code> installe exactement les versions du <code>package-lock.json</code> : les résultats de la CI sont reproductibles.</div>""",
        "setup": r'''
livrer tests/wip-thomas.test.js
''',
        "exercises": [
            {"id": "J10.1", "points": 5, "title": "Feu vert", "manual": True,
             "ticket": {"from": "nadia", "body": "Dernière ligne droite avant la mise en production. Thomas a laissé un brouillon <code>tests/wip-thomas.test.js</code>… avec un <code>.only</code> qui fait ignorer des tests. Nettoie tout ça : aucun test focalisé ou désactivé dans <code>tests/</code>, et <strong>toute la suite</strong> doit passer avec ton code et tes seuils de couverture."},
             "desc": "Aucun <code>.only</code>, <code>.skip</code>, <code>fit</code>, <code>xit</code>… dans <code>tests/</code>, et <code>jest --coverage</code> réussit sur l'ensemble du projet (seuils compris).",
             "hints": ["Cherchez les tests focalisés ou désactivés avec <code>grep -rn</code>.", "Lancez <code>npm run test:coverage</code> : tous les tests doivent passer et les seuils de votre configuration être atteints."],
             "checks": [
                 ('! grep -rEn "\\.(only|skip)\\(|\\b(fit|fdescribe|xit|xtest|xdescribe)\\(" $P/tests', "Il reste des tests focalisés (.only, fit) ou désactivés (.skip, xit) dans tests/."),
                 ('verif suite', "La suite complète n'est pas au vert."),
             ]},
            {"id": "J10.2", "points": 5, "title": "L'intégration continue", "manual": True,
             "ticket": {"from": "sophie", "body": "Dernière demande : je ne veux plus jamais entendre « ça passait chez moi ». Mets en place un workflow <strong>GitHub Actions</strong> qui lance la suite de tests, avec la couverture, à chaque push et à chaque pull request, sur Node 20."},
             "desc": "<code>.github/workflows/tests.yml</code> : déclenché sur <code>push</code> et <code>pull_request</code>, qui récupère le code, installe Node 20, installe les dépendances et lance les tests avec la couverture.",
             "hints": ["Inspirez-vous du modèle du cours.", "Étapes attendues : <code>actions/checkout</code>, <code>actions/setup-node</code> (<code>node-version: 20</code>), <code>npm ci</code>, puis les tests avec <code>--coverage</code> (ou <code>npm run test:coverage</code>)."],
             "checks": [
                 ('test -f $P/.github/workflows/tests.yml', "Le fichier .github/workflows/tests.yml n'existe pas."),
                 ('f=$P/.github/workflows/tests.yml; grep -q "push" $f && grep -q "pull_request" $f', "Le workflow doit se déclencher sur push et sur pull_request."),
                 ('f=$P/.github/workflows/tests.yml; grep -q "actions/checkout" $f && grep -q "actions/setup-node" $f && grep -qE "node-version: *[\'\\"]?20" $f', "Le workflow doit utiliser actions/checkout et actions/setup-node avec node-version 20."),
                 ('f=$P/.github/workflows/tests.yml; grep -qE "npm (ci|install)" $f && grep -qE "(npm (run )?test.*--coverage|npm run test:coverage|jest.*--coverage)" $f', "Le workflow doit installer les dépendances (npm ci) puis lancer les tests avec la couverture."),
             ]},
        ],
    },
}
