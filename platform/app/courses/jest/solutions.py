"""Corrigé du parcours Jest : un script par étape, exécuté en tant qu'« etudiant » par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Les tests écrits passent sur le code de référence ET détectent tous les mutants du jeu correspondant.
"""

SOLUTIONS = {
    1: r'''
cd ~/boutique
#@ J1.1
#? La règle impose un prix TTC arrondi au centime : 19,99 × 1,2 = 23,988, donc le test doit attendre exactement `23.99`, une valeur calculée à la main.
#? `toBe(19.99 * 1.2)` recalculait le résultat avec la formule du code, sans arrondi : le test exigeait 23,988 et contredisait la règle.
#? Les mutants à détecter : un calcul sans arrondi (23,988), une troncature au centime inférieur (23,98) et une TVA à 19,6 %.
#? Piège : `toBeCloseTo(23.99, 2)` tolère un écart de 0,005 et laisserait donc passer le calcul non arrondi (23,988) ; ici, seule l'égalité exacte protège la règle.
#? Formes également valables : `calculerTTC(19.99, 0.2)`, `toEqual`/`toStrictEqual(23.99)`, ou un `test.each` des trois cas (l'article à 19,99 € doit y rester).
sed -i 's/toBe(19.99 \* 1.2)/toBe(23.99)/' tests/prix.test.js
#@ J1.2
#? `npm test` doit lancer la suite une seule fois et rendre la main : `--watchAll` dans ce script bloquait la CI indéfiniment.
#? `--watch` demande à git quels fichiers ont changé ; `~/boutique` n'étant pas un dépôt, il s'arrête aussitôt, alors que `--watchAll` relance toute la suite sans git.
#? `jest --ci` n'est jamais interactif et fait échouer un snapshot absent au lieu de l'écrire : c'est le comportement voulu en intégration continue.
#? Variantes également valables : garder `jest --watch` après avoir fait de `~/boutique` un dépôt git (`git init`) ; `npm test -- --ci` ou `CI=true jest` pour `test:ci`.
# npm test doit rendre la main ; --watch a besoin de git (~/boutique n'est pas un dépôt) : --watchAll
node -e '
const fs = require("fs");
const p = JSON.parse(fs.readFileSync("package.json", "utf8"));
p.scripts = { ...p.scripts, test: "jest", "test:watch": "jest --watchAll", "test:ci": "jest --ci" };
fs.writeFileSync("package.json", JSON.stringify(p, null, 2) + "\n");
'
#@ J1.3
#? Chaque cas démasque une erreur d'arrondi précise : 2,674 doit descendre, 2,678 monter, 2,671 ne pas monter, et un montant déjà rond ne doit pas bouger.
#? 1,005 est le piège des flottants : il est stocké 1,00499999…, et un simple `Math.round(montant * 100) / 100` donne 1,00 au lieu de 1,01.
#? Les mutants détectés : troncature (`Math.floor`), arrondi toujours vers le haut (`Math.ceil`), arrondi au dixième, absence d'arrondi et arrondi sans correction des flottants.
#? `test.each` évite de dupliquer six fois le même test, et son titre paramétré indique immédiatement quel cas échoue.
cat > tests/arrondir.test.js <<'EOF'
const { arrondir } = require('../src/prix');

describe('arrondir', () => {
  test.each([
    [2.674, 2.67],
    [2.671, 2.67],
    [2.678, 2.68],
    [1.005, 1.01],
    [12.5, 12.5],
    [7, 7],
  ])('arrondir(%s) vaut %s', (montant, attendu) => {
    expect(arrondir(montant)).toBe(attendu);
  });
});
EOF
#@ J1.4
#? Un test n'échoue que si un matcher est appelé et non satisfait, ou si une exception inattendue s'échappe : les quatre tests de Thomas ne pouvaient jamais échouer.
#? `expect(x)` sans matcher, une valeur attendue calculée avec le code testé, un appel sans `expect`, et `toThrow` sans parenthèses (la fonction n'est jamais appelée) : aucun ne vérifie rien.
#? Les valeurs attendues viennent de la règle (50 € − 10 % = 45 €) ; 19,99 × 0,85 = 16,9915 détecte en plus un prix remisé non arrondi.
#? Les mutants à détecter : renvoyer le montant de la remise au lieu du prix remisé, une remise dix fois trop petite, l'absence d'arrondi et une remise de 120 % acceptée.
cat > tests/remise.test.js <<'EOF'
const { appliquerRemise } = require('../src/prix');

// Valeurs attendues calculées à la main à partir de la règle, jamais avec le code testé.
describe('appliquerRemise', () => {
  test('applique une remise de 10 %', () => {
    expect(appliquerRemise(50, 10)).toBe(45);
  });

  test('arrondit le prix remisé au centime', () => {
    // 19,99 × 0,85 = 16,9915 -> 16,99
    expect(appliquerRemise(19.99, 15)).toBe(16.99);
  });

  test('applique une remise de 25 %', () => {
    expect(appliquerRemise(80, 25)).toBe(60);
  });

  test('refuse une remise de plus de 100 %', () => {
    expect(() => appliquerRemise(50, 120)).toThrow(RangeError);
  });
});
EOF
#@ J1.5
#? 1,005 ne prouve rien ici : les deux versions donnent 1,01. Il fallait chercher un montant sur lequel elles divergent.
#? Ajouter `Number.EPSILON` (2,2e-16) ne corrige l'erreur de représentation que près de 1 : au-delà de 2, l'écart entre deux flottants voisins dépasse EPSILON, et 10,075 (stocké 10,07499999…) reste arrondi à 10,07.
#? La valeur attendue, 10,08 €, se déduit de la règle « demi-centime vers le haut », pas de l'une ou l'autre implémentation.
#? Une boucle dans `node` comparant les deux versions sur tous les montants en x,xx5 est la bonne méthode pour trouver ces contre-exemples, au lieu de deviner.
cat > tests/arrondir-prestataire.test.js <<'EOF'
const { arrondir } = require('../src/prix');

// 10,075 est stocké 10,074999999999999289… : ajouter Number.EPSILON (2,2e-16) n'y change rien,
// car au-delà de 2 l'écart entre deux flottants voisins est plus grand qu'EPSILON.
// La version du prestataire donne donc 10,07 € au lieu de 10,08 €.
test.each([
  [1.005, 1.01],
  [10.075, 10.08],
  [2.135, 2.14],
])('arrondir(%s) vaut %s', (montant, attendu) => {
  expect(arrondir(montant)).toBe(attendu);
});
EOF
''',
    2: r'''
cd ~/boutique
#@ J2.1
#? Chaque méthode du panier porte une règle, et chaque test en vérifie une : vide, quantité par défaut, cumul, total HT, retrait.
#? Les quantités supérieures à 1 et les ajouts répétés d'une même référence sont indispensables : avec des quantités à 1, compter les lignes ou compter les articles donne le même résultat.
#? Les mutants à détecter : total qui ignore les quantités, pas de cumul (ou quantité remplacée au lieu d'être cumulée), `estVide` vrai pour une ligne, quantité par défaut à 2, `retirer` qui vide tout le panier.
#? `beforeEach` fournit un panier neuf à chaque test : aucun test ne dépend de ce qu'un autre a laissé.
cat > tests/panier.test.js <<'EOF'
const { Panier } = require('../src/panier');

const gourde = { ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5 };
const lampe = { ref: 'LAMPE', libelle: 'Lampe frontale', prixHT: 25 };

let panier;
beforeEach(() => {
  panier = new Panier();
});

test('un panier neuf est vide', () => {
  expect(panier.estVide()).toBe(true);
  expect(panier.nombreArticles()).toBe(0);
  expect(panier.totalHT()).toBe(0);
});

test("un panier d'une ligne n'est pas vide", () => {
  panier.ajouter(gourde);
  expect(panier.estVide()).toBe(false);
});

test('la quantité par défaut est 1', () => {
  panier.ajouter(gourde);
  expect(panier.nombreArticles()).toBe(1);
});

test("les quantités d'une même référence sont cumulées", () => {
  panier.ajouter(gourde, 2).ajouter(gourde, 3);
  expect(panier.lignes()).toHaveLength(1);
  expect(panier.nombreArticles()).toBe(5);
});

test('le total HT tient compte des quantités', () => {
  panier.ajouter(gourde, 2).ajouter(lampe);
  expect(panier.totalHT()).toBe(50);
  expect(panier.nombreArticles()).toBe(3);
});

test('retirer supprime seulement la référence demandée', () => {
  panier.ajouter(gourde, 2).ajouter(lampe);
  panier.retirer('GOURDE');
  expect(panier.lignes()).toEqual([{ ref: 'LAMPE', libelle: 'Lampe frontale', prixHT: 25, quantite: 1 }]);
});
EOF
#@ J2.2
#? Pour chaque validation, on cherche la frontière exacte : quantités de 0, de -1 et de 1,5 refusées ; remises de -1 % et de 101 % refusées, mais 0 % et 100 % acceptées.
#? `toThrow(RangeError)` vérifie le type : une `Error` générique n'est pas une `RangeError`, et ce mutant est détecté ; attention, `calculerTTC` lève une `TypeError`, pas une `RangeError`.
#? `toThrow('absent')` vérifie qu'une sous-chaîne figure dans le message (« Produit INCONNU absent du panier ») : un `retirer` silencieux est ainsi détecté.
#? Les mutants à détecter : validations trop laxistes (quantité nulle ou décimale, remise négative ou de plus de 100 %, prix négatif) mais aussi trop strictes (remise de 0 % ou de 100 % refusée).
cat > tests/erreurs.test.js <<'EOF'
const { Panier } = require('../src/panier');
const { appliquerRemise, calculerTTC } = require('../src/prix');

const gourde = { ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5 };

test.each([0, -1, 1.5])('une quantité de %s est refusée', (quantite) => {
  expect(() => new Panier().ajouter(gourde, quantite)).toThrow(RangeError);
});

test('retirer une référence absente lève une erreur', () => {
  expect(() => new Panier().retirer('INCONNU')).toThrow('absent');
});

test.each([-1, 101])('une remise de %s %% est refusée', (remise) => {
  expect(() => appliquerRemise(50, remise)).toThrow(RangeError);
});

test('les remises limites sont acceptées', () => {
  expect(appliquerRemise(50, 0)).toBe(50);
  expect(appliquerRemise(50, 100)).toBe(0);
});

test('un prix HT négatif est refusé', () => {
  expect(() => calculerTTC(-5)).toThrow(TypeError);
});
EOF
#@ J2.3
#? Une fuite peut se produire à deux niveaux : le tableau lui-même (`return this._lignes`) et les objets qu'il contient (`map((l) => l)` copie le tableau mais pas les lignes).
#? On modifie donc le tableau renvoyé puis une ligne renvoyée, et on relit l'état du panier par une autre méthode (`lignes()` à nouveau, `nombreArticles()`).
#? `toStrictEqual` sur une ligne complète détecte aussi une ligne mal construite : un libellé manquant ou une propriété `total` en trop.
cat > tests/panier-lignes.test.js <<'EOF'
const { Panier } = require('../src/panier');

const gourde = { ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5 };

let panier;
beforeEach(() => {
  panier = new Panier();
});

test('une ligne a la structure attendue', () => {
  panier.ajouter(gourde, 2);
  expect(panier.lignes()).toStrictEqual([{ ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5, quantite: 2 }]);
});

test('modifier le tableau renvoyé ne modifie pas le panier', () => {
  panier.ajouter(gourde);
  panier.lignes().push({ ref: 'INTRUS' });
  expect(panier.lignes()).toHaveLength(1);
});

test('modifier une ligne renvoyée ne modifie pas le panier', () => {
  panier.ajouter(gourde);
  panier.lignes()[0].quantite = 99;
  expect(panier.nombreArticles()).toBe(1);
});
EOF
#@ J2.4
#? `toEqual` ignore les propriétés qui valent `undefined` et la classe des objets : il restait vert avec `remise: undefined` et avec des instances d'une classe `Ligne`.
#? `toStrictEqual` tient compte des deux : c'est le seul matcher d'égalité qui garantit « exactement un objet simple ».
#? Le produit ajouté porte un champ `poids` supplémentaire : le test vérifie en même temps que la ligne ne recopie que `ref`, `libelle`, `prixHT` et `quantite`.
#? Variante également valable : vérifier `Object.keys(ligne)` et `Object.getPrototypeOf(ligne) === Object.prototype`, qui voient eux aussi la propriété `undefined` et la classe.
cat > tests/panier-api.test.js <<'EOF'
const { Panier } = require('../src/panier');

// toEqual ignore les propriétés undefined et la classe des objets : seul toStrictEqual voit tout.
test('une ligne est exactement un objet simple { ref, libelle, prixHT, quantite }', () => {
  const panier = new Panier().ajouter({ ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5, poids: 0.3 }, 2);
  expect(panier.lignes()).toStrictEqual([{ ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5, quantite: 2 }]);
});
EOF
#@ J2.5
#? La règle ne garantit pas l'ordre : on vérifie combien de résultats (`toHaveLength`) et lesquels (`toContainEqual`), jamais leur position.
#? Piège : `toEqual([gourde, gourdeInox])` serait trop strict et casserait sur les variantes correctes qui inversent ou trient les résultats par prix.
#? Chaque phrase du commentaire donne un cas : casse (« GOURDE »), milieu du libellé (« front »), espaces autour, et la longueur minimale du terme, testée des deux côtés.
#? La longueur minimale se lit dans le commentaire de `rechercher` (elle n'est pas la même dans tous les projets) : avec 3 caractères, par exemple, « lam » doit trouver la lampe et « la » ne rien trouver.
#? Chercher « GOURDE » alors que la lampe est le premier produit du catalogue détecte aussi le mutant qui renvoie toujours le premier produit ; `expect.arrayContaining` avec `toHaveLength` serait une variante également valable.
# Longueur minimale du terme, d'après le commentaire de rechercher
MIN=$(grep -oP 'un terme de moins de \K\d+' src/catalogue.js)
ASSEZ=$(echo lampe | cut -c1-$MIN)
TROP_COURT=$(echo lampe | cut -c1-$((MIN - 1)))
cat > tests/catalogue.test.js <<EOF
const { rechercher } = require('../src/catalogue');

const lampe = { ref: 'LAMPE', libelle: 'Lampe frontale', prixHT: 25 };
const gourde = { ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5 };
const gourdeInox = { ref: 'GOURDE-INOX', libelle: 'Petite gourde inox', prixHT: 19.9 };
const produits = [lampe, gourde, gourdeInox];

// L'ordre des résultats n'est pas garanti : on vérifie combien et lesquels, pas leur position.
test('trouve tous les produits dont le libellé contient le terme, sans tenir compte de la casse', () => {
  const resultats = rechercher(produits, 'GOURDE');
  expect(resultats).toHaveLength(2);
  expect(resultats).toContainEqual(gourde);
  expect(resultats).toContainEqual(gourdeInox);
});

test('le terme peut se trouver au milieu du libellé', () => {
  expect(rechercher(produits, 'front')).toEqual([lampe]);
});

test('les espaces autour du terme sont ignorés', () => {
  expect(rechercher(produits, '  lampe ')).toEqual([lampe]);
});

test('$MIN caractères suffisent, $((MIN - 1)) ne suffisent pas', () => {
  expect(rechercher(produits, '$ASSEZ')).toEqual([lampe]);
  expect(rechercher(produits, '$TROP_COURT')).toEqual([]);
});
EOF
''',
    3: r'''
cd ~/boutique
#@ J3.1
#? Les bugs se cachent aux frontières : chaque limite de poids est testée juste en dessous et pile dessus (0,99 / 1 kg si la première tranche s'arrête à 1 kg), et chaque pays au moins une fois.
#? Un `<` écrit `<=` ne se voit que sur la valeur limite exacte : sans un cas pile sur chaque limite, ces mutants survivent.
#? Pour `livraisonOfferte`, il faut chaque seuil pile, juste en dessous, et un pays étranger au seuil français, pour détecter une livraison offerte dès ce montant partout.
#? Les cas refusés font partie de la règle : un pays non desservi doit lever une erreur (pas coûter 0 €) et un poids nul doit être refusé.
#? Un `describe.each` par pays, un `test.each` en gabarit (`test.each` suivi d'un tableau entre accents graves) ou des lignes objets (`$poids`) conviennent tout autant.
#? La grille (tranches, tarifs, suppléments, seuils) n'est pas la même dans tous les projets : les valeurs attendues se calculent à partir des commentaires et de la table des suppléments de `src/livraison.js`, jamais en appelant le code testé. Ici, un petit script les calcule et écrit les lignes du `test.each`.
node - <<'EOF'
const fs = require('fs');
const src = fs.readFileSync('src/livraison.js', 'utf8');
const nombre = (t) => Number(t.replace(',', '.'));
const [l1, b1, l2, b2, b3] = src.match(/moins de (\d+) kg -> ([\d,]+) € ; moins de (\d+) kg -> ([\d,]+) € ; au-delà -> ([\d,]+) €/).slice(1).map(nombre);
const sup = Object.fromEntries([...src.matchAll(/^ {2}([A-Z]{2}): ([\d.]+),$/gm)].map((m) => [m[1], Number(m[2])]));
const [seuilFR, seuilAilleurs] = src.match(/offerte dès (\d+) € TTC en France, (\d+) € ailleurs/).slice(1).map(Number);

const centimes = (x) => Math.round(x * 100) / 100;
const frais = (poids, pays) => centimes((poids < l1 ? b1 : poids < l2 ? b2 : b3) + sup[pays]);
const cas = [
  [l1 / 2, 'FR'], [centimes(l1 - 0.01), 'FR'], [l1, 'FR'], [centimes(l2 - 0.01), 'FR'], [l2, 'FR'], [l2 + 7, 'FR'],
  [l1, 'BE'], [l1 / 2, 'LU'], [l1 + 1, 'DE'], [0.2, 'ES'], [l2 + 1, 'IT'], [l2, 'NL'],
];
const offerte = [
  [centimes(seuilFR - 0.01), 'FR', false], [seuilFR, 'FR', true], [seuilFR, 'DE', false],
  [centimes(seuilAilleurs - 0.01), 'BE', false], [seuilAilleurs, 'BE', true],
];
const lignes = (rows) => rows.map((r) => `    [${r.map((v) => JSON.stringify(v).replace(/"/g, "'")).join(', ')}],`).join('\n');

fs.writeFileSync('tests/livraison.test.js', `const { fraisLivraison, livraisonOfferte } = require('../src/livraison');

// Valeurs attendues calculées à partir de la grille décrite dans src/livraison.js
describe('fraisLivraison', () => {
  test.each([
${lignes(cas.map(([poids, pays]) => [poids, pays, frais(poids, pays)]))}
  ])('%s kg vers %s : %s €', (poids, pays, attendu) => {
    expect(fraisLivraison(poids, pays)).toBe(attendu);
  });

  test('un pays non desservi est refusé', () => {
    expect(() => fraisLivraison(1, 'US')).toThrow('Livraison impossible');
  });

  test.each([0, -2])('un poids de %s kg est refusé', (poids) => {
    expect(() => fraisLivraison(poids, 'FR')).toThrow(RangeError);
  });
});

describe('livraisonOfferte', () => {
  test.each([
${lignes(offerte)}
  ])('%s € vers %s : %s', (total, pays, attendu) => {
    expect(livraisonOfferte(total, pays)).toBe(attendu);
  });
});
`);
EOF
#@ J3.2
#? Le panier était créé une seule fois en haut du fichier : chaque test héritait de ce que les précédents y avaient mis, et l'ordre d'exécution décidait du résultat.
#? Avec `beforeEach`, chaque test part d'un panier neuf et prépare lui-même ce dont il a besoin (ajouter la gourde avant de vérifier le total, par exemple).
#? Piège : rendre les tests indépendants en supprimant leurs assertions ; les mutants (total sans les quantités, lignes comptées au lieu des articles, retrait qui vide tout) doivent rester détectés.
#? Le `beforeEach` est imposé par le ticket (règle de l'équipe) : créer un panier dans chaque test serait correct, mais refusé ; un `beforeEach` qui prépare déjà les gourdes, dans un `describe` imbriqué, est accepté.
cat > tests/panier-thomas.test.js <<'EOF'
const { Panier } = require('../src/panier');

const gourde = { ref: 'GOURDE-1L', libelle: 'Gourde 1 L', prixHT: 12.5 };
const lampe = { ref: 'FRONTALE', libelle: 'Lampe frontale', prixHT: 25 };

describe('Panier', () => {
  let panier;
  beforeEach(() => {
    panier = new Panier();
  });

  test('un panier neuf est vide', () => {
    expect(panier.estVide()).toBe(true);
  });

  test('on peut ajouter une gourde', () => {
    panier.ajouter(gourde, 2);
    expect(panier.nombreArticles()).toBe(2);
  });

  test('le total HT tient compte des quantités', () => {
    panier.ajouter(gourde, 2);
    expect(panier.totalHT()).toBe(25);
  });

  test('on peut ajouter une lampe', () => {
    panier.ajouter(gourde, 2).ajouter(lampe);
    expect(panier.nombreArticles()).toBe(3);
    expect(panier.totalHT()).toBe(50);
  });

  test('on peut retirer la gourde', () => {
    panier.ajouter(gourde, 2).ajouter(lampe);
    panier.retirer('GOURDE-1L');
    expect(panier.lignes()).toHaveLength(1);
  });
});
EOF
#@ J3.3
#? L'état partagé vit dans le module : `require` met `src/numerotation.js` en cache, et son compteur survit d'un test à l'autre.
#? `jest.resetModules()` vide le cache ; il faut ensuite refaire le `require` et réaffecter `prochainNumero`, sinon on garde la fonction de l'ancien module et son compteur.
#? Les parenthèses de `({ prochainNumero } = require(…))` sont obligatoires : sans elles, JavaScript lirait l'accolade comme le début d'un bloc.
#? Variante également valable : charger le module dans `jest.isolateModules(() => { … })` à l'intérieur de chaque test.
cat > tests/numerotation.test.js <<'EOF'
// Le compteur vit dans le module : chaque test recharge un module neuf.
describe('prochainNumero', () => {
  let prochainNumero;
  beforeEach(() => {
    jest.resetModules();
    ({ prochainNumero } = require('../src/numerotation'));
  });

  test('la première commande porte le numéro CMD-0001', () => {
    expect(prochainNumero()).toBe('CMD-0001');
  });

  test('les numéros se suivent', () => {
    expect(prochainNumero()).toBe('CMD-0001');
    expect(prochainNumero()).toBe('CMD-0002');
  });

  test('le numéro est toujours écrit sur 4 chiffres', () => {
    expect(prochainNumero()).toMatch(/^CMD-\d{4}$/);
  });
});
EOF
''',
    4: r'''
cd ~/boutique
#@ J4.1
#? Chaque test reçoit une date fixe (`JOUR`) : le résultat ne dépend plus du jour réel, et les tests passent même avec une horloge système déplacée dans le futur.
#? Les limites de format sont testées des deux côtés : une longueur de moins que le minimum et de plus que le maximum refusées pour `FORMAT`, les longueurs limites bien formées mais `INCONNU`, ce qui prouve qu'elles franchissent le contrôle de format.
#? Le code saisonnier (celui qui expire le premier) doit encore être valable le soir de son dernier jour : ce cas détecte une expiration calculée à minuit au début du jour.
#? Variante également valable : figer l'horloge avec `jest.useFakeTimers({ now })` et `jest.setSystemTime(…)` au lieu de passer la date à `validerCode`.
#? Le code à la fois expiré et épuisé vérifie la priorité entre les règles ; `toEqual` sur l'objet complet détecte aussi une remise renvoyée en fraction (0.1) au lieu d'un pourcentage (10).
#? Les codes et les longueurs autorisées ne sont pas les mêmes dans tous les projets : ils se lisent dans `src/data/codes.js` et dans la spécification. Ici, un petit script les lit et écrit les tests.
node - <<'EOF'
const fs = require('fs');
const codes = require('./src/data/codes');
const [min, max] = fs.readFileSync('SPEC-codes-promo.md', 'utf8').match(/\*\*(\d+) à (\d+)\*\*/).slice(1).map(Number);
const JOUR = '2026-06-01';
const disponibles = codes.filter((c) => c.restants > 0).sort((a, b) => a.expire.localeCompare(b.expire));
const saisonnier = disponibles[0];                                   // expire le premier
const valide = disponibles[disponibles.length - 1];
const epuise = codes.find((c) => c.restants <= 0 && c.expire > JOUR);
const expireEtEpuise = codes.find((c) => c.restants <= 0 && c.expire < JOUR);
const lendemain = new Date(`${saisonnier.expire}T12:00:00Z`);
lendemain.setUTCDate(lendemain.getUTCDate() + 1);
const lettres = 'ABCDEFGHIJKLMNOP';

fs.writeFileSync('tests/codesPromo.test.js', `const { validerCode } = require('../src/codesPromo');

const JOUR = new Date('${JOUR}T10:00:00');

test('un code valide renvoie sa remise en pourcentage', () => {
  expect(validerCode('${valide.code}', JOUR)).toEqual({ valide: true, remise: ${valide.remise} });
});

test('la casse est ignorée', () => {
  expect(validerCode('${valide.code.toLowerCase()}', JOUR)).toEqual({ valide: true, remise: ${valide.remise} });
});

test('les espaces autour sont ignorés', () => {
  expect(validerCode('  ${valide.code} ', JOUR)).toEqual({ valide: true, remise: ${valide.remise} });
});

test.each(['${lettres.slice(0, min - 1)}', '${lettres.slice(0, max + 1)}', 'AB-CD'])('le code « %s » est mal formé', (code) => {
  expect(validerCode(code, JOUR)).toEqual({ valide: false, raison: 'FORMAT' });
});

test.each(['${lettres.slice(0, min)}', '${lettres.slice(0, max)}'])('le code « %s », bien formé mais absent, est INCONNU', (code) => {
  expect(validerCode(code, JOUR)).toEqual({ valide: false, raison: 'INCONNU' });
});

test("un code est valable jusqu'au soir de son expiration", () => {
  expect(validerCode('${saisonnier.code}', new Date('${saisonnier.expire}T20:00:00'))).toEqual({ valide: true, remise: ${saisonnier.remise} });
});

test('un code est expiré le lendemain', () => {
  expect(validerCode('${saisonnier.code}', new Date('${lendemain.toISOString().slice(0, 10)}T08:00:00'))).toEqual({ valide: false, raison: 'EXPIRE' });
});

test('un code sans utilisations restantes est épuisé', () => {
  expect(validerCode('${epuise.code}', JOUR)).toEqual({ valide: false, raison: 'EPUISE' });
});

test("l'expiration est prioritaire sur l'épuisement", () => {
  expect(validerCode('${expireEtEpuise.code}', JOUR)).toEqual({ valide: false, raison: 'EXPIRE' });
});
`);
EOF
#@ J4.2
#? L'ordre des contrôles suit la spécification : format, existence, expiration, puis épuisement ; la première règle violée donne la raison.
#? La fin de validité est construite en heure locale avec une date-heure sans `Z` (`T23:59:59.999`) : le code reste valable toute la journée de son expiration.
#? Piège : `new Date(entree.expire)`, une date seule au format ISO, représente minuit UTC ; le code serait refusé le jour même, avec un résultat qui change selon le fuseau horaire.
#? Les longueurs autorisées viennent de la spécification du projet (elles ne sont pas les mêmes partout) ; le paramètre par défaut `maintenant = new Date()` garde la fonction utilisable en production tout en permettant aux tests d'injecter une date.
# Longueurs autorisées d'après la spécification (par exemple « 4 à 10 » -> {4,10})
LONGUEURS=$(grep -oP '\*\*\K\d+ à \d+(?=\*\*)' SPEC-codes-promo.md | sed 's/ à /,/')
cat > src/codesPromo.js <<'EOF'
const CODES = require('./data/codes');

const FORMAT = /^[A-Z0-9]{LONGUEURS}$/;

function validerCode(code, maintenant = new Date()) {
  const saisi = String(code).trim().toUpperCase();
  if (!FORMAT.test(saisi)) {
    return { valide: false, raison: 'FORMAT' };
  }
  const entree = CODES.find((c) => c.code === saisi);
  if (!entree) {
    return { valide: false, raison: 'INCONNU' };
  }
  if (maintenant > new Date(`${entree.expire}T23:59:59.999`)) {
    return { valide: false, raison: 'EXPIRE' };
  }
  if (entree.restants <= 0) {
    return { valide: false, raison: 'EPUISE' };
  }
  return { valide: true, remise: entree.remise };
}

module.exports = { validerCode };
EOF
sed -i "s/{LONGUEURS}/{$LONGUEURS}/" src/codesPromo.js
#@ J4.3
#? `String(null)` donne « null », puis « NULL » après `toUpperCase()` : bien formé mais absent du catalogue, d'où la réponse `INCONNU`.
#? En TDD, on complète d'abord la spécification, puis on écrit un test qui échoue sur l'ancien code (Red), avant de corriger le code (Green).
#? Le contrôle `typeof code !== 'string'` doit précéder toute normalisation : c'est la conversion en chaîne qui fabriquait un code plausible.
#? Piège : un contrôle limité à `null` et `undefined` laisserait passer un tableau, et `String([code])` redonne justement le code lui-même : un tableau contenant un code valide serait accepté !
cat >> SPEC-codes-promo.md <<'EOF'

## Saisie qui n'est pas une chaîne

Si `code` n'est pas une chaîne de caractères (`null`, `undefined`, un nombre, un objet…),
il est refusé pour `FORMAT`, avant toute autre vérification.
EOF
cat >> tests/codesPromo.test.js <<'EOF'

test.each([null, undefined, 1234, { code: 'RANDO10' }])('la saisie %p, qui n’est pas une chaîne, est refusée pour FORMAT', (saisie) => {
  expect(validerCode(saisie, JOUR)).toEqual({ valide: false, raison: 'FORMAT' });
});
EOF
sed -i "s/^  const saisi = String(code).trim().toUpperCase();/  if (typeof code !== 'string') {\n    return { valide: false, raison: 'FORMAT' };\n  }\n  const saisi = code.trim().toUpperCase();/" src/codesPromo.js
#@ J4.4
#? Le dernier instant valide est le jour d'expiration à 23:59:59.999 et le premier instant expiré le lendemain à 00:00:00.000, tous deux en heure locale.
#? Le constructeur numérique `new Date(2026, 7, 31, …)` est toujours en heure locale, quel que soit le fuseau ; attention, les mois commencent à 0 (7 = août).
#? Les mutants à détecter : la dernière seconde refusée (fin à 23:59:59 sans les millisecondes), une comparaison `>=` au lieu de `>`, et une fin de validité calculée en UTC, visible uniquement hors du fuseau UTC (à Montréal, par exemple).
#? Variante également valable : une chaîne date-heure sans `Z`, comme `new Date('2026-08-31T23:59:59.999')`, elle aussi interprétée en heure locale. Le code et sa date d'expiration se lisent dans `src/data/codes.js` (ils changent d'un projet à l'autre) : ici, un petit script écrit les tests pour le code qui expire le premier.
node - <<'EOF'
const fs = require('fs');
const codes = require('./src/data/codes');
const code = codes.filter((c) => c.restants > 0).sort((a, b) => a.expire.localeCompare(b.expire))[0];
const [a, m, j] = code.expire.split('-').map(Number);
const lendemain = new Date(Date.UTC(a, m - 1, j + 1));
const [a2, m2, j2] = [lendemain.getUTCFullYear(), lendemain.getUTCMonth() + 1, lendemain.getUTCDate()];

fs.writeFileSync('tests/codes-minuit.test.js', `const { validerCode } = require('../src/codesPromo');

// ${code.code} expire le ${code.expire}, jour inclus, en heure locale.
// Le constructeur numérique est toujours en heure locale, quel que soit le fuseau (mois numérotés à partir de 0).
test("le code est valable jusqu'à la dernière milliseconde de son dernier jour", () => {
  expect(validerCode('${code.code}', new Date(${a}, ${m - 1}, ${j}, 23, 59, 59, 999))).toEqual({ valide: true, remise: ${code.remise} });
});

test('le code est expiré à minuit pile le lendemain', () => {
  expect(validerCode('${code.code}', new Date(${a2}, ${m2 - 1}, ${j2}, 0, 0, 0, 0))).toEqual({ valide: false, raison: 'EXPIRE' });
});
`);
EOF
''',
    5: r'''
cd ~/boutique
#@ J5.1
#? La doublure respecte le contrat de la vraie API : `jest.fn(async …)` renvoie une promesse. Avec un simple nombre, le mutant qui oublie le `await` passerait inaperçu.
#? `toHaveBeenCalledWith('GOURDE')` est indispensable : avec le libellé au lieu de la référence, la doublure renvoie `undefined`, et `undefined < 2` est faux, donc aucun manque n'apparaît dans le résultat.
#? `toHaveBeenCalledTimes(2)` pour deux lignes détecte à la fois une ligne oubliée et une API interrogée deux fois par ligne (et facturée deux fois).
#? Le stock tout juste suffisant (2 demandés, 2 disponibles) détecte un `<=` à la place de `<`, et `toEqual` sur le manque complet vérifie que `disponible` est bien renseigné.
#? Variantes également valables : `jest.spyOn` sur une fausse API asynchrone, `mockResolvedValueOnce` en chaîne, `toHaveBeenNthCalledWith` ou `mock.calls`.
cat > tests/stock.test.js <<'EOF'
const { Panier } = require('../src/panier');
const { verifierDisponibilite } = require('../src/stock');

const gourde = { ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5 };
const lampe = { ref: 'LAMPE', libelle: 'Lampe frontale', prixHT: 25 };

// La vraie API renvoie une promesse : la doublure aussi.
const apiAvec = (stocks) => ({ quantiteDisponible: jest.fn(async (ref) => stocks[ref]) });

test('rien ne manque quand le stock est tout juste suffisant', async () => {
  const api = apiAvec({ GOURDE: 2 });
  const panier = new Panier().ajouter(gourde, 2);
  await expect(verifierDisponibilite(panier, api)).resolves.toEqual([]);
  expect(api.quantiteDisponible).toHaveBeenCalledWith('GOURDE');
});

test('chaque ligne est vérifiée une fois et les manques sont détaillés', async () => {
  const api = apiAvec({ GOURDE: 5, LAMPE: 0 });
  const panier = new Panier().ajouter(gourde, 3).ajouter(lampe, 1);
  expect(await verifierDisponibilite(panier, api)).toEqual([{ ref: 'LAMPE', demande: 1, disponible: 0 }]);
  expect(api.quantiteDisponible).toHaveBeenCalledTimes(2);
  expect(api.quantiteDisponible).toHaveBeenCalledWith('LAMPE');
});
EOF
#@ J5.2
#? Avec `jest.mock`, `paiement.debiter` et `mailer.envoyer` deviennent des `jest.fn()` qui renvoient `undefined` : il faut programmer un résultat (`mockResolvedValue`) pour que `passerCommande` aille au bout.
#? Le montant attendu se calcule à la main : 2 × 50 € HT = 100 € HT, soit 120 € TTC ; un débit du montant HT (100) est ainsi détecté, dans l'appel à la banque comme dans l'e-mail.
#? `toHaveBeenCalledTimes(1)` détecte un double débit, et l'e-mail est vérifié sur ses trois arguments : destinataire, sujet exact et montant dans le corps.
#? `jest.clearAllMocks()` dans `beforeEach` efface les appels enregistrés par le test précédent : sans lui, les compteurs d'appels s'additionneraient d'un test à l'autre.
cat > tests/commande.test.js <<'EOF'
jest.mock('../src/services/paiement');
jest.mock('../src/services/mailer');

const paiement = require('../src/services/paiement');
const mailer = require('../src/services/mailer');
const { Panier } = require('../src/panier');
const { passerCommande } = require('../src/commande');

const client = { email: 'alice@exemple.fr', carte: '4970-1234' };
const panier = () => new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 50 }, 2);

beforeEach(() => {
  jest.clearAllMocks();
  paiement.debiter.mockResolvedValue({ accepte: true, transaction: 'TX-42' });
  mailer.envoyer.mockResolvedValue();
});

test('débite une seule fois le montant TTC sur la carte du client', async () => {
  await passerCommande(panier(), client);
  expect(paiement.debiter).toHaveBeenCalledTimes(1);
  expect(paiement.debiter).toHaveBeenCalledWith('4970-1234', 120);
});

test('renvoie le numéro de transaction et le montant', async () => {
  await expect(passerCommande(panier(), client)).resolves.toEqual({ numero: 'TX-42', montant: 120 });
});

test('envoie la confirmation au client', async () => {
  await passerCommande(panier(), client);
  expect(mailer.envoyer).toHaveBeenCalledWith('alice@exemple.fr', 'Confirmation de commande', expect.stringContaining('120'));
});
EOF
#@ J5.3
#? `jest.spyOn(Math, 'random').mockReturnValue(…)` rend le tirage déterministe le temps d'un test ; `Math.random` renvoie une valeur de [0, 1[, d'où les deux extrêmes 0 et 0,999999.
#? Avec 0,999999, le dernier participant doit gagner : ce cas détecte un `Math.round` (index 3, hors de la liste) et une multiplication par `length - 1` (le dernier ne gagne jamais).
#? Avec 0, le premier doit gagner : ce cas détecte aussi un tirage figé au milieu de la liste ; la liste vide vérifie le message d'erreur.
#? `jest.restoreAllMocks()` dans `afterEach` remet le vrai `Math.random` en place ; un espion oublié fausserait tous les tests suivants du fichier. `espion.mockRestore()` serait une variante également valable.
cat > tests/concours.test.js <<'EOF'
const { tirerGagnant } = require('../src/concours');

const participants = ['Ana', 'Bruno', 'Chloé'];

afterEach(() => {
  jest.restoreAllMocks();
});

test('le premier participant gagne quand le hasard donne 0', () => {
  jest.spyOn(Math, 'random').mockReturnValue(0);
  expect(tirerGagnant(participants)).toBe('Ana');
});

test('le dernier participant gagne quand le hasard donne presque 1', () => {
  jest.spyOn(Math, 'random').mockReturnValue(0.999999);
  expect(tirerGagnant(participants)).toBe('Chloé');
});

test('une liste vide est refusée', () => {
  expect(() => tirerGagnant([])).toThrow('Aucun participant');
});
EOF
#@ J5.4
#? `clearAllMocks` n'efface que les appels enregistrés : les valeurs programmées (`mockResolvedValue`, et les « Once » non consommées) passaient d'un test à l'autre.
#? Le refus programmé par un test devenait la valeur par défaut des suivants, et le « Once » en trop du dernier test était consommé par le test d'après.
#? `jest.resetAllMocks()` efface aussi les implémentations ; la valeur par défaut doit alors être reprogrammée dans `beforeEach`, avant chaque test, et non une seule fois dans `beforeAll`.
#? Les tests restent forts : ils détectent toujours un débit HT, un e-mail oublié, un refus traité comme accepté et l'absence de nouvelle tentative.
cat > tests/commande-fuite.test.js <<'EOF'
jest.mock('../src/services/paiement');
jest.mock('../src/services/mailer');

const paiement = require('../src/services/paiement');
const mailer = require('../src/services/mailer');
const { Panier } = require('../src/panier');
const { passerCommande } = require('../src/commande');

const client = { email: 'alice@exemple.fr', carte: '4970-1234' };
const panier = () => new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 50 });

// clearAllMocks n'oublie que les appels : les valeurs « Once » non consommées et les
// mockResolvedValue d'un test passaient au suivant. resetAllMocks efface tout, puis on
// reprogramme la valeur par défaut avant CHAQUE test (et non une fois dans beforeAll).
beforeEach(() => {
  jest.resetAllMocks();
  paiement.debiter.mockResolvedValue({ accepte: true, transaction: 'TX-0' });
});

test('une panne passagère de la banque est rattrapée', async () => {
  paiement.debiter
    .mockRejectedValueOnce(new Error('Timeout'))
    .mockResolvedValueOnce({ accepte: true, transaction: 'TX-2' });
  await expect(passerCommande(panier(), client)).resolves.toEqual({ numero: 'TX-2', montant: 60 });
});

test('la confirmation part une seule fois', async () => {
  await passerCommande(panier(), client);
  expect(mailer.envoyer).toHaveBeenCalledTimes(1);
});

test('un refus de la banque est signalé au client', async () => {
  paiement.debiter.mockResolvedValue({ accepte: false, motif: 'carte expirée' });
  await expect(passerCommande(panier(), client)).rejects.toThrow('carte expirée');
  expect(mailer.envoyer).not.toHaveBeenCalled();
});

test('le numéro de transaction est renvoyé', async () => {
  paiement.debiter.mockResolvedValueOnce({ accepte: true, transaction: 'TX-1' });
  await expect(passerCommande(panier(), client)).resolves.toEqual({ numero: 'TX-1', montant: 60 });
});
EOF
#@ J5.5
#? Le destinataire et le sujet sont fixes, donc vérifiés exactement ; pour le corps, seul le montant fait partie de la règle, d'où `expect.stringContaining('120 €')`.
#? Piège : comparer le corps complet casserait à chaque reformulation du marketing ; c'est ce que vérifient les variantes correctes sur lesquelles le test doit rester vert.
#? Les mutants à détecter : sujet modifié, montant HT (100 €) au lieu du montant débité, montant absent du corps, e-mail envoyé à une mauvaise adresse.
#? Variante également valable : `expect.stringMatching(/120 €/)`, un autre matcher à trous, placé lui aussi en argument de `toHaveBeenCalledWith`.
cat > tests/commande-email.test.js <<'EOF'
jest.mock('../src/services/paiement');
jest.mock('../src/services/mailer');

const paiement = require('../src/services/paiement');
const mailer = require('../src/services/mailer');
const { Panier } = require('../src/panier');
const { passerCommande } = require('../src/commande');

const client = { email: 'alice@exemple.fr', carte: '4970-1234' };
// 2 × 50 € HT = 100 € HT, soit 120 € TTC débités
const panier = () => new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 50 }, 2);

beforeEach(() => {
  jest.resetAllMocks();
  paiement.debiter.mockResolvedValue({ accepte: true, transaction: 'TX-7' });
  mailer.envoyer.mockResolvedValue();
});

test('la confirmation part au client, avec le sujet exact et le montant débité dans le corps', async () => {
  await passerCommande(panier(), client);
  expect(mailer.envoyer).toHaveBeenCalledTimes(1);
  expect(mailer.envoyer).toHaveBeenCalledWith('alice@exemple.fr', 'Confirmation de commande', expect.stringContaining('120 €'));
});
EOF
''',
    6: r'''
cd ~/boutique
#@ J6.1
#? `await expect(…).rejects.toThrow(…)` attend la fin de la promesse et vérifie l'erreur ; le message complet (« Paiement refusé : fonds insuffisants ») détecte un motif perdu.
#? L'absence d'effets de bord se vérifie après la fin de l'opération : aucun e-mail après un refus, aucun débit pour un panier vide.
#? Ces vérifications détectent les mutants les plus sournois : l'e-mail envoyé avant le contrôle du paiement, ou le panier vide refusé seulement après le débit de la carte.
#? `rejects` est imposé par le ticket : un `try/catch` avec `expect.assertions` serait juste, mais refusé ici ; `return expect(…).rejects…` ou `rejects.toThrow(/motif/)` sont acceptés.
cat > tests/commande-erreurs.test.js <<'EOF'
jest.mock('../src/services/paiement');
jest.mock('../src/services/mailer');

const paiement = require('../src/services/paiement');
const mailer = require('../src/services/mailer');
const { Panier } = require('../src/panier');
const { passerCommande } = require('../src/commande');

const client = { email: 'alice@exemple.fr', carte: '4970-1234' };
const panier = () => new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 50 });

beforeEach(() => {
  jest.clearAllMocks();
  paiement.debiter.mockResolvedValue({ accepte: true, transaction: 'TX-1' });
  mailer.envoyer.mockResolvedValue();
});

test('un paiement refusé lève une erreur avec le motif, sans e-mail', async () => {
  paiement.debiter.mockResolvedValue({ accepte: false, motif: 'fonds insuffisants' });
  await expect(passerCommande(panier(), client)).rejects.toThrow('Paiement refusé : fonds insuffisants');
  expect(mailer.envoyer).not.toHaveBeenCalled();
});

test('un panier vide est refusé sans débit', async () => {
  await expect(passerCommande(new Panier(), client)).rejects.toThrow('Panier vide');
  expect(paiement.debiter).not.toHaveBeenCalled();
});
EOF
#@ J6.2
#? Une panne est une promesse rejetée (`mockRejectedValueOnce`), un refus est une réponse résolue avec `accepte: false` : les deux ne doivent pas être traités de la même façon.
#? On compte les appels à la banque dans chaque scénario : 2 après une panne passagère, 2 (et pas 3) après deux pannes, 1 seul après un refus.
#? Le message « Service de paiement indisponible » est vérifié explicitement : l'erreur technique brute ne doit jamais remonter au client.
#? `jest.resetAllMocks()` évite qu'une valeur « Once » non consommée dans un test ne fausse le suivant.
#? `mockRejectedValue(Once)` est imposé par le ticket : `mockImplementationOnce(() => Promise.reject(…))` serait équivalent, mais refusé.
cat > tests/commande-reprise.test.js <<'EOF'
jest.mock('../src/services/paiement');
jest.mock('../src/services/mailer');

const paiement = require('../src/services/paiement');
const mailer = require('../src/services/mailer');
const { Panier } = require('../src/panier');
const { passerCommande } = require('../src/commande');

const client = { email: 'alice@exemple.fr', carte: '4970-1234' };
const panier = () => new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 50 });

beforeEach(() => {
  jest.resetAllMocks();
  mailer.envoyer.mockResolvedValue();
});

test('une panne passagère est rattrapée par une seconde tentative', async () => {
  paiement.debiter
    .mockRejectedValueOnce(new Error('Timeout'))
    .mockResolvedValueOnce({ accepte: true, transaction: 'TX-9' });
  await expect(passerCommande(panier(), client)).resolves.toMatchObject({ numero: 'TX-9' });
  expect(paiement.debiter).toHaveBeenCalledTimes(2);
});

test('après deux pannes, le service est déclaré indisponible', async () => {
  paiement.debiter.mockRejectedValue(new Error('Timeout'));
  await expect(passerCommande(panier(), client)).rejects.toThrow('Service de paiement indisponible');
  expect(paiement.debiter).toHaveBeenCalledTimes(2);
});

test("un refus de la banque n'est jamais retenté", async () => {
  paiement.debiter.mockResolvedValue({ accepte: false, motif: 'fonds insuffisants' });
  await expect(passerCommande(panier(), client)).rejects.toThrow('Paiement refusé');
  expect(paiement.debiter).toHaveBeenCalledTimes(1);
});
EOF
#@ J6.3
#? Une assertion dans un `catch` ne s'exécute que si une erreur est levée : si le panier vide était accepté, le test restait vert. `rejects` échoue au contraire quand la promesse est résolue.
#? Une promesse ni attendue ni renvoyée laisse le test se terminer avant elle : toute assertion doit être précédée de `await` (ou renvoyée avec `return`).
#? `expect(mailer.envoyer).not.toHaveBeenCalled()` n'a de sens qu'après la fin de `passerCommande` : d'où le `await … .catch(() => {})` avant la vérification.
#? `toThrow()` sans argument accepte n'importe quelle erreur, y compris l'erreur technique brute ; variante également valable pour le premier test : garder le `try/catch` en ajoutant `expect.assertions(1)`.
cat > tests/commande-async.test.js <<'EOF'
jest.mock('../src/services/paiement');
jest.mock('../src/services/mailer');

const paiement = require('../src/services/paiement');
const mailer = require('../src/services/mailer');
const { Panier } = require('../src/panier');
const { passerCommande } = require('../src/commande');

const client = { email: 'alice@exemple.fr', carte: '4970-1234' };
const panier = () => new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 50 });

beforeEach(() => {
  jest.clearAllMocks();
  paiement.debiter.mockResolvedValue({ accepte: true, transaction: 'TX-1' });
  mailer.envoyer.mockResolvedValue();
});

// Avant : l'assertion dans le catch ne s'exécutait que si une erreur était levée.
test('un panier vide est refusé', async () => {
  await expect(passerCommande(new Panier(), client)).rejects.toThrow('Panier vide');
});

// Avant : la promesse n'était ni attendue ni renvoyée.
test('un refus de la banque remonte avec son motif', async () => {
  paiement.debiter.mockResolvedValue({ accepte: false, motif: 'plafond atteint' });
  await expect(passerCommande(panier(), client)).rejects.toThrow('plafond atteint');
});

// Avant : on vérifiait avant même que la commande ait eu le temps d'envoyer quoi que ce soit.
test("après un refus, aucun e-mail de confirmation n'est envoyé", async () => {
  paiement.debiter.mockResolvedValue({ accepte: false, motif: 'plafond atteint' });
  await passerCommande(panier(), client).catch(() => {});
  expect(mailer.envoyer).not.toHaveBeenCalled();
});

// Avant : toThrow() sans message acceptait n'importe quelle erreur, même l'erreur technique brute.
test('après deux pannes, le client est prévenu', async () => {
  paiement.debiter.mockRejectedValue(new Error('ECONNRESET'));
  await expect(passerCommande(panier(), client)).rejects.toThrow('Service de paiement indisponible');
});
EOF
''',
    7: r'''
cd ~/boutique
#@ J7.1
#? Les faux minuteurs font avancer une horloge virtuelle : plusieurs jours s'écoulent en quelques millisecondes, et `useRealTimers` dans `afterEach` rétablit les vrais minuteurs.
#? La limite exacte se teste des deux côtés : rien au délai moins 1 ms, l'e-mail pile au délai ; trois délais plus tard, toujours un seul envoi, ce qui détecte un `setInterval`.
#? Le délai (lu dans le commentaire de `programmerRelance`, il change d'un projet à l'autre) est écrit en dur dans le test : réutiliser `DELAI_RELANCE_MS`, exporté par le code testé, ferait suivre au test un délai erroné.
#? Un panier de 3 gourdes (une seule ligne) distingue le nombre d'articles du nombre de lignes dans le message ; l'annulation et le panier vidé entre-temps couvrent les deux cas où rien ne doit partir.
# Délai annoncé par le commentaire de programmerRelance, en heures
H=$(grep -oP 'envoyé une seule fois \K\d+(?= h)' src/relance.js)
cat > tests/relance.test.js <<EOF
const { Panier } = require('../src/panier');
const { programmerRelance } = require('../src/relance');

const DELAI = $H * 60 * 60 * 1000; // $H h, écrit en dur : jamais la constante du code testé
const client = { email: 'bob@exemple.fr' };
let mailer;
let panier;

beforeEach(() => {
  jest.useFakeTimers();
  mailer = { envoyer: jest.fn() };
  panier = new Panier().ajouter({ ref: 'GOURDE', libelle: 'Gourde', prixHT: 12.5 }, 3);
});

afterEach(() => {
  jest.useRealTimers();
});

test("rien n'est envoyé avant $H h", () => {
  programmerRelance(panier, client, mailer);
  jest.advanceTimersByTime(DELAI - 1);
  expect(mailer.envoyer).not.toHaveBeenCalled();
});

test('la relance part au bout de $H h avec le nombre d’articles', () => {
  programmerRelance(panier, client, mailer);
  jest.advanceTimersByTime(DELAI);
  expect(mailer.envoyer).toHaveBeenCalledWith(
    'bob@exemple.fr', 'Votre panier vous attend', 'Vous avez 3 article(s) dans votre panier.');
});

test('une seule relance, même trois délais plus tard', () => {
  programmerRelance(panier, client, mailer);
  jest.advanceTimersByTime(3 * DELAI);
  expect(mailer.envoyer).toHaveBeenCalledTimes(1);
});

test('une relance annulée ne part jamais', () => {
  const relance = programmerRelance(panier, client, mailer);
  relance.annuler();
  jest.advanceTimersByTime(2 * DELAI);
  expect(mailer.envoyer).not.toHaveBeenCalled();
});

test('un panier vidé entre-temps ne reçoit pas de relance', () => {
  programmerRelance(panier, client, mailer);
  panier.retirer('GOURDE');
  jest.advanceTimersByTime(2 * DELAI);
  expect(mailer.envoyer).not.toHaveBeenCalled();
});
EOF
#@ J7.2
#? `advanceTimersByTime` est synchrone : les promesses (`await`) n'avancent pas entre deux minuteurs. `advanceTimersByTimeAsync` les laisse se résoudre, et doit lui-même être attendu.
#? On compte les appels juste avant et pile à chaque échéance (1 ms avant, puis 1 ms plus tard) : des délais inversés, identiques ou absents sont ainsi détectés.
#? Les délais se lisent dans le commentaire de `debiterPatiemment` (ils changent d'un projet à l'autre) ; l'assertion `rejects` est créée avant de faire avancer le temps : la promesse rejetée a déjà un gestionnaire au moment où elle échoue.
#? Le second test vérifie à la fois le message final et le nombre exact de tentatives : ni 2, ni 4, mais 3.
#? Variantes également valables : `jest.runAllTimersAsync()` en notant `Date.now()` à chaque tentative, ou `jest.spyOn(global, 'setTimeout')` qui relève les délais demandés.
# Délais annoncés par le commentaire de debiterPatiemment (« On attend 1 s avant la 2e tentative, puis 2 s avant la 3e »), en millisecondes
read P1 P2 < <(grep -oP 'On attend \K[\d,]+ s avant la 2e tentative, puis [\d,]+(?= s avant la 3e)' src/debit-patient.js \
  | sed 's/ s avant la 2e tentative, puis / /; s/,/./g' | awk '{ print $1 * 1000, $2 * 1000 }')
cat > tests/debit-patient.test.js <<EOF
const { debiterPatiemment } = require('../src/debit-patient');

let banque;

beforeEach(() => {
  jest.useFakeTimers();
  banque = { debiter: jest.fn() };
});

afterEach(() => {
  jest.useRealTimers();
});

// advanceTimersByTime est synchrone : entre deux minuteurs, les promesses (await) n'avancent pas.
// Les variantes Async laissent les promesses se résoudre.
test('attend $P1 ms avant la 2e tentative, puis $P2 ms avant la 3e', async () => {
  banque.debiter
    .mockRejectedValueOnce(new Error('ETIMEDOUT'))
    .mockRejectedValueOnce(new Error('ETIMEDOUT'))
    .mockResolvedValueOnce({ accepte: true, transaction: 'TX-3' });
  const resultat = debiterPatiemment(banque, '4970-1234', 60);
  expect(banque.debiter).toHaveBeenCalledTimes(1);
  await jest.advanceTimersByTimeAsync($((P1 - 1)));
  expect(banque.debiter).toHaveBeenCalledTimes(1);
  await jest.advanceTimersByTimeAsync(1);
  expect(banque.debiter).toHaveBeenCalledTimes(2);
  await jest.advanceTimersByTimeAsync($((P2 - 1)));
  expect(banque.debiter).toHaveBeenCalledTimes(2);
  await jest.advanceTimersByTimeAsync(1);
  expect(banque.debiter).toHaveBeenCalledTimes(3);
  await expect(resultat).resolves.toEqual({ accepte: true, transaction: 'TX-3' });
  expect(banque.debiter).toHaveBeenCalledWith('4970-1234', 60);
});

test('abandonne après 3 échecs, sans 4e tentative', async () => {
  banque.debiter.mockRejectedValue(new Error('ETIMEDOUT'));
  const verification = expect(debiterPatiemment(banque, '4970-1234', 60)).rejects.toThrow('Service de paiement indisponible');
  await jest.advanceTimersByTimeAsync(60 * 1000);
  await verification;
  expect(banque.debiter).toHaveBeenCalledTimes(3);
});
EOF
''',
    8: r'''
cd ~/boutique
#@ J8.1
#? `collectCoverageFrom` mesure tous les fichiers de `src/`, y compris ceux qu'aucun test ne charge, qui comptent alors pour 0 %.
#? `coverageThreshold` accepte, à côté de `global`, des clés qui sont des chemins de fichiers, comme `./src/prix.js` ; si un seuil n'est pas atteint, `jest --coverage` échoue.
#? Piège : configurer Jest à la fois dans `package.json` et dans un `jest.config.js` ; Jest refuse alors de démarrer.
#? Variantes également valables : un `jest.config.js`, les globs `src/**` ou `./src/**/*.js`, un script `npm test -- --coverage` (mais pas `src/*.js`, qui oublie les sous-dossiers).
node -e '
const fs = require("fs");
const p = JSON.parse(fs.readFileSync("package.json", "utf8"));
p.scripts = { ...p.scripts, "test:coverage": "jest --coverage" };
p.jest = {
  collectCoverageFrom: ["src/**/*.js"],
  coverageThreshold: {
    global: { branches: 80, lines: 90 },
    "./src/prix.js": { branches: 100 },
  },
};
fs.writeFileSync("package.json", JSON.stringify(p, null, 2) + "\n");
'
#@ J8.2
#? Chaque cas du tableau exerce une branche et vérifie le nombre exact de points : couvrir une ligne ne suffit pas, il faut que le résultat distingue le bon calcul du mauvais.
#? Les montants sont choisis pour cela : 99,90 € donne 99 points (et non 100 avec `Math.round`), 101 € en silver donne 151 (et non 152 avec `Math.ceil`) ; avec 100 € en silver, les deux arrondis donneraient 150.
#? Un achat nul le mois de l'anniversaire doit rapporter 0 point : ce cas détecte un `< 0` à la place de `<= 0`, qui ajouterait le bonus.
#? Le multiplicateur gold, le bonus d'anniversaire et le plafond se lisent dans le commentaire de `pointsFidelite` (ils changent d'un projet à l'autre) : un achat égal au plafond, en gold, dépasse le plafond et doit y être ramené.
# Règles lues dans le commentaire de pointsFidelite
GOLD=$(grep -oP 'statut gold : ×\K\d+' src/fidelite.js)
BONUS=$(grep -oP '\+\K\d+(?= points le mois)' src/fidelite.js)
PLAFOND=$(grep -oP 'au plus \K\d+(?= points)' src/fidelite.js)
cat > tests/fidelite.test.js <<EOF
const { pointsFidelite } = require('../src/fidelite');

const standard = { statut: 'standard', dateAchat: '2026-03-10' };

test.each([
  ['un achat nul', 0, standard, 0],
  ['un montant négatif', -5, standard, 0],
  ['un client standard (euros entiers)', 99.9, standard, 99],
  ['un client gold (x$GOLD)', 100, { ...standard, statut: 'gold' }, $((100 * GOLD))],
  ['un client silver (x1,5 arrondi inférieur)', 101, { ...standard, statut: 'silver' }, 151],
  ['un anniversaire dans le mois (+$BONUS)', 50, { ...standard, anniversaire: '1990-03-22' }, $((50 + BONUS))],
  ['un anniversaire un autre mois', 50, { ...standard, anniversaire: '1990-07-22' }, 50],
  ['le plafond de $PLAFOND points', $PLAFOND, { ...standard, statut: 'gold' }, $PLAFOND],
  ['un achat nul le mois de son anniversaire', 0, { ...standard, anniversaire: '1990-03-22' }, 0],
])('%s', (_cas, montant, client, attendu) => {
  expect(pointsFidelite(montant, client)).toBe(attendu);
});
EOF
#@ J8.3
#? L'ordre entre deux règles ne se voit que sur un client concerné par les deux à la fois.
#? Gold et anniversaire : avec un multiplicateur de 2 et un bonus de 100, (50 × 2) + 100 = 200, alors qu'un bonus ajouté avant le multiplicateur donnerait (50 + 100) × 2 = 300.
#? Plafond et anniversaire : un achat juste sous le plafond (plafond moins la moitié du bonus) le dépasse une fois le bonus ajouté, et doit y être ramené ; un plafond appliqué avant le bonus le laisserait dépasser.
#? Variante également valable pour le premier cas : un client silver, car le bonus serait lui aussi multiplié par 1,5 s'il était ajouté trop tôt.
GOLD=$(grep -oP 'statut gold : ×\K\d+' src/fidelite.js)
BONUS=$(grep -oP '\+\K\d+(?= points le mois)' src/fidelite.js)
PLAFOND=$(grep -oP 'au plus \K\d+(?= points)' src/fidelite.js)
cat >> tests/fidelite.test.js <<EOF

describe("ordre des règles : statut, puis bonus d'anniversaire, puis plafond", () => {
  test("le bonus d'anniversaire s'ajoute après le multiplicateur gold", () => {
    // 50 € -> 50 points, x$GOLD = $((50 * GOLD)), +$BONUS = $((50 * GOLD + BONUS)) (et non (50 + $BONUS) x $GOLD = $(((50 + BONUS) * GOLD)))
    expect(pointsFidelite(50, { ...standard, statut: 'gold', anniversaire: '1990-03-22' })).toBe($((50 * GOLD + BONUS)));
  });

  test("le plafond s'applique après le bonus d'anniversaire", () => {
    // $((PLAFOND - BONUS / 2)) € -> $((PLAFOND - BONUS / 2)) points, +$BONUS = $((PLAFOND + BONUS / 2)), plafonnés à $PLAFOND
    expect(pointsFidelite($((PLAFOND - BONUS / 2)), { ...standard, anniversaire: '1990-03-22' })).toBe($PLAFOND);
  });
});
EOF
''',
    9: r'''
cd ~/boutique
#@ J9.1
#? Le test doit utiliser des valeurs qui distinguent les deux comportements : un article dont le prix TTC dépasse le seuil de livraison offerte avant la remise, mais plus après (avec un seuil de 60 € : 72 € TTC avant 20 % de remise, 57,60 € après).
#? Le résultat attendu est calculé à la main à partir de la règle : les frais de port restent dus, et la version boguée les offre.
#? Le second test, au-dessus du seuil même après remise, vérifie que la future correction ne tombera pas dans l'excès inverse.
#? Le seuil et la grille de livraison se lisent dans `src/livraison.js` (ils changent d'un projet à l'autre) : ici, un petit script en déduit les valeurs attendues et écrit les tests.
node - <<'EOF'
const fs = require('fs');
const src = fs.readFileSync('src/livraison.js', 'utf8');
const nombre = (t) => Number(t.replace(',', '.'));
const [l1, b1, l2, b2] = src.match(/moins de (\d+) kg -> ([\d,]+) € ; moins de (\d+) kg -> ([\d,]+) €/).slice(1).map(nombre);
const seuil = Number(src.match(/offerte dès (\d+) € TTC en France/)[1]);
const centimes = (x) => Math.round(Number((x * 100).toFixed(6))) / 100;
const port2kg = 2 < l1 ? b1 : b2; // colis de 2 kg, en France : pas de supplément

// Un article à « seuil » € HT : 1,2 × seuil TTC (au-dessus du seuil), puis 0,96 × seuil après 20 % de remise (en dessous)
const apresRemise = centimes(centimes(seuil * 1.2) * 0.8);
// Avec 10 % de remise seulement : 1,08 × seuil, toujours au-dessus
const offert = centimes(centimes(seuil * 1.2) * 0.9);

fs.writeFileSync('tests/facture.test.js', `const { Panier } = require('../src/panier');
const { genererFacture } = require('../src/facture');

test('bug #218 : le port est dû quand la remise fait passer sous le seuil', () => {
  // ${seuil} € HT -> ${centimes(seuil * 1.2)} € TTC (au-dessus de ${seuil} €) -> -20 % = ${apresRemise} € (en dessous) -> port ${port2kg} €
  const panier = new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: ${seuil} });
  expect(genererFacture(panier, { pays: 'FR', poidsKg: 2, remise: 20 })).toEqual({ produitsTTC: ${apresRemise}, port: ${port2kg}, total: ${centimes(apresRemise + port2kg)} });
});

test('au-dessus du seuil après remise, le port reste offert', () => {
  const panier = new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: ${seuil} });
  expect(genererFacture(panier, { pays: 'FR', poidsKg: 6, remise: 10 })).toEqual({ produitsTTC: ${offert}, port: 0, total: ${offert} });
});
`);
EOF
#@ J9.2
#? Les deux corrections : comparer le seuil à `produitsTTC` (après remise), et calculer le port sur `poidsKg` exact au lieu de `Math.round(poidsKg)`.
#? Pour #219, le poids doit franchir une tranche une fois arrondi : 0,4 kg sous la limite supérieure (4,6 kg si elle est de 5 kg) est arrondi à cette limite et payé au tarif supérieur, alors qu'un poids entier ne montrerait rien.
#? Chaque test de non-régression échoue sur son bug même si l'autre est corrigé : le test #218 utilise un poids entier, et le test #219 un panier sans remise sous le seuil.
node - <<'EOF'
const fs = require('fs');
const src = fs.readFileSync('src/livraison.js', 'utf8');
const nombre = (t) => Number(t.replace(',', '.'));
const [l2, b2] = src.match(/moins de (\d+) kg -> ([\d,]+) € ; au-delà/).slice(1).map(nombre);
const seuil = Number(src.match(/offerte dès (\d+) € TTC en France/)[1]);
const centimes = (x) => Math.round(Number((x * 100).toFixed(6))) / 100;
// Un article à seuil / 2 € HT : 0,6 × seuil TTC, sous le seuil ; un colis de 0,4 kg sous la limite supérieure
const produits = centimes(seuil / 2 * 1.2);
const poids = centimes(l2 - 0.4);

fs.appendFileSync('tests/facture.test.js', `
test('bug #219 : le port suit le poids exact du colis', () => {
  // ${seuil / 2} € HT -> ${produits} € TTC (sous le seuil) ; ${poids} kg -> tranche « moins de ${l2} kg » : ${b2} €
  const panier = new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: ${seuil / 2} });
  expect(genererFacture(panier, { pays: 'FR', poidsKg: ${poids} })).toEqual({ produitsTTC: ${produits}, port: ${b2}, total: ${centimes(produits + b2)} });
});
`);
EOF
sed -i 's/livraisonOfferte(totalTTC, pays)/livraisonOfferte(produitsTTC, pays)/; s/fraisLivraison(Math.round(poidsKg), pays)/fraisLivraison(poidsKg, pays)/' src/facture.js
#@ J9.3
#? `test.failing` est vert tant que son contenu échoue, et devient rouge dès qu'il passe : le jour du correctif, la suite rappelle d'en faire un test normal.
#? Piège : `test.skip` masquerait le bug, et il resterait désactivé pour toujours sans que personne ne le remarque.
#? `it.failing` convient aussi ; un test normal inversé (`.not.toBe('…59,40')`) est refusé : il ne dit pas ce que la compta attend, et le ticket demande un échec attendu.
#? Le montant doit rendre le bug visible : 59,4 s'écrit « 59,4 » avec `String`, alors que 12,35 s'écrit pareil avec ou sans le bug ; c'est pourquoi le second test, normal, passe dans les deux cas.
cat > tests/export-compta.test.js <<'EOF'
const { ligneComptable } = require('../src/export-compta');

// Bug #231 (correctif attendu du prestataire) : ce test deviendra rouge le jour où le bug sera
// corrigé. Il faudra alors remplacer test.failing par test.
test.failing('bug #231 : le montant a toujours deux décimales', () => {
  expect(ligneComptable({ date: '2026-09-29', numero: 'CMD-0042', montantTTC: 59.4 })).toBe('2026-09-29;CMD-0042;59,40');
});

test('un montant avec des centimes est exporté avec une virgule', () => {
  expect(ligneComptable({ date: '2026-09-29', numero: 'CMD-0043', montantTTC: 12.35 })).toBe('2026-09-29;CMD-0043;12,35');
});
EOF
''',
    10: r'''
cd ~/boutique
#@ J10.1
#? Les modificateurs se cachent sous plusieurs formes : `test.only.each`, `test.skip`, `xit`, `describe.skip`. Il faut toutes les chercher dans `tests/`.
#? Un test réactivé qui échoue n'est pas forcément un bug du code : le colis « pile » à la limite de la dernière tranche vers l'Espagne relève du tarif « au-delà », plus le supplément de l'Espagne (avec la grille 8,90 € / 14,90 € et 8 € de supplément : 22,90 €, et non 16,90 €). La valeur du brouillon, qui n'avait jamais tourné, était fausse.
#? Piège : `test.only` n'affecte que son fichier, et les tests ignorés n'apparaissent que comme « skipped » dans le résumé : ils passent facilement inaperçus.
# Valeur juste du colis pile à la limite vers l'Espagne : tarif « au-delà » + supplément de l'Espagne (grille de src/livraison.js)
JUSTE=$(node -e '
const src = require("fs").readFileSync("src/livraison.js", "utf8");
const auDela = Number(src.match(/au-delà -> ([\d,]+) €/)[1].replace(",", "."));
const espagne = Number(src.match(/^ {2}ES: ([\d.]+),$/m)[1]);
console.log(Math.round((auDela + espagne) * 100) / 100);
')
sed -i "s/test\.only\.each(/test.each(/; s/test\.skip(/test(/; s/^  xit(/  test(/; s/^describe\.skip(/describe(/; s/\(fraisLivraison([0-9.]*, 'ES'))\.toBe(\)[0-9.]*)/\1$JUSTE)/" tests/wip-thomas.test.js
#@ J10.2
#? `on: [push, pull_request]` déclenche le workflow sur les deux événements, et la matrice `node: [22, 24]` exécute le même job avec chaque version.
#? L'ordre des étapes compte : récupérer le code (`checkout`), installer Node, installer les dépendances, puis lancer les tests avec la couverture.
#? `npm ci` installe exactement les versions du `package-lock.json` : contrairement à `npm install`, il rend les résultats de la CI reproductibles.
#? Variantes également valables : lancer `npx jest --coverage` directement au lieu du script `test:coverage` ; un job par version de Node, ou une matrice `include`.
mkdir -p .github/workflows
cat > .github/workflows/tests.yml <<'EOF'
name: Tests
on: [push, pull_request]
jobs:
  tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [22, 24]
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-node@v5
        with:
          node-version: ${{ matrix.node }}
          cache: npm
      - run: npm ci
      - run: npm run test:coverage
EOF
#@ J10.3
#? La configuration est déplacée sans rien perdre, puis la clé `jest` est supprimée de `package.json` : avec deux configurations, Jest refuse de démarrer.
#? `resetMocks` efface appels, implémentations et valeurs programmées avant chaque test, et `restoreMocks` remet en place les méthodes espionnées : `clearMocks` n'aurait effacé que les appels.
#? Piège : avec `resetMocks`, une doublure programmée une seule fois dans un `beforeAll` est effacée par la remise à zéro automatique ; les fichiers de test la reprogramment donc dans `beforeEach`, qui s'exécute après elle.
#? Un `jest.config.js` écrit à la main, ou qui exporte une fonction renvoyant la configuration, convient aussi ; `clearMocks: true` en plus ne gêne pas.
node -e '
const fs = require("fs");
const p = JSON.parse(fs.readFileSync("package.json", "utf8"));
const config = { ...p.jest, resetMocks: true, restoreMocks: true };
delete p.jest;
fs.writeFileSync("package.json", JSON.stringify(p, null, 2) + "\n");
fs.writeFileSync("jest.config.js", "module.exports = " + JSON.stringify(config, null, 2) + ";\n");
'
''',
    11: r'''
cd ~/boutique
#@ J11.1
#? Un snapshot ne vérifie que ce que montrent les données : plusieurs produits pour l'ordre, des quantités, des centimes, une livraison payante et une offerte.
#? Avec un seul produit, l'ordre inversé passerait inaperçu, et avec une livraison offerte seulement, un total qui oublie les frais de port aussi.
#? Le premier `npx jest` enregistre le fichier `.snap`, qu'il faut relire et versionner : en mode `--ci`, un snapshot absent fait échouer le test au lieu d'être créé.
cat > tests/recapitulatif.test.js <<'EOF'
const { Panier } = require('../src/panier');
const { recapitulatif } = require('../src/recapitulatif');

const gourde = { ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.49 };
const lampe = { ref: 'LAMPE', libelle: 'Lampe frontale', prixHT: 25 };

test('plusieurs produits, des centimes, une livraison payante', () => {
  const panier = new Panier().ajouter(gourde, 3).ajouter(lampe);
  expect(recapitulatif(panier, { pays: 'BE', port: 11.9 })).toMatchSnapshot();
});

test('une livraison offerte', () => {
  const panier = new Panier().ajouter(lampe, 3);
  expect(recapitulatif(panier, { pays: 'FR', port: 0 })).toMatchSnapshot();
});
EOF
npx jest tests/recapitulatif >/dev/null 2>&1
#@ J11.2
#? Le snapshot avait figé deux bugs : le pays écrit « BE » au lieu de « BELGIQUE », et le nombre de lignes au lieu du nombre d'articles.
#? On corrige d'abord le code d'après la norme, puis on met à jour le snapshot avec `-u` seulement après avoir relu le nouveau contenu.
#? Piège : lancer `-u` sans relire, c'est valider un bug ; un snapshot enregistre le comportement du moment, bugs compris.
# Le snapshot figeait deux bugs : « BE » au lieu de « BELGIQUE », et 2 lignes au lieu de 4 articles
sed -i 's/`Articles : ${panier.lignes().length}`/`Articles : ${panier.nombreArticles()}`/; s/^    client.pays,$/    PAYS[client.pays],/' src/etiquette.js
npx jest tests/etiquette -u >/dev/null 2>&1
''',
}
