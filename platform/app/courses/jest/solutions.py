"""Corrigé du parcours Jest : un script par étape, exécuté en tant qu'« etudiant » par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Les tests écrits passent sur le code de référence ET détectent tous les mutants du jeu correspondant.
"""

SOLUTIONS = {
    1: r'''
cd ~/boutique
#@ J1.1
sed -i 's/toBe(19.99 \* 1.2)/toBe(23.99)/' tests/prix.test.js
#@ J1.2
# npm test doit rendre la main ; --watch a besoin de git (~/boutique n'est pas un dépôt) : --watchAll
node -e '
const fs = require("fs");
const p = JSON.parse(fs.readFileSync("package.json", "utf8"));
p.scripts = { ...p.scripts, test: "jest", "test:watch": "jest --watchAll", "test:ci": "jest --ci" };
fs.writeFileSync("package.json", JSON.stringify(p, null, 2) + "\n");
'
#@ J1.3
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
cat > tests/panier-api.test.js <<'EOF'
const { Panier } = require('../src/panier');

// toEqual ignore les propriétés undefined et la classe des objets : seul toStrictEqual voit tout.
test('une ligne est exactement un objet simple { ref, libelle, prixHT, quantite }', () => {
  const panier = new Panier().ajouter({ ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5, poids: 0.3 }, 2);
  expect(panier.lignes()).toStrictEqual([{ ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5, quantite: 2 }]);
});
EOF
#@ J2.5
cat > tests/catalogue.test.js <<'EOF'
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

test('2 caractères suffisent, 1 ne suffit pas', () => {
  expect(rechercher(produits, 'la')).toEqual([lampe]);
  expect(rechercher(produits, 'e')).toEqual([]);
});
EOF
''',
    3: r'''
cd ~/boutique
#@ J3.1
cat > tests/livraison.test.js <<'EOF'
const { fraisLivraison, livraisonOfferte } = require('../src/livraison');

describe('fraisLivraison', () => {
  test.each([
    [0.5, 'FR', 4.9],
    [0.99, 'FR', 4.9],
    [1, 'FR', 8.9],
    [4.99, 'FR', 8.9],
    [5, 'FR', 14.9],
    [12, 'FR', 14.9],
    [1, 'BE', 11.9],
    [0.5, 'LU', 7.9],
    [2, 'DE', 16.9],
    [0.2, 'ES', 12.9],
    [6, 'IT', 22.9],
    [5, 'NL', 22.9],
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
    [59.99, 'FR', false],
    [60, 'FR', true],
    [60, 'DE', false],
    [99.99, 'BE', false],
    [100, 'BE', true],
  ])('%s € vers %s : %s', (total, pays, attendu) => {
    expect(livraisonOfferte(total, pays)).toBe(attendu);
  });
});
EOF
#@ J3.2
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
cat > tests/codesPromo.test.js <<'EOF'
const { validerCode } = require('../src/codesPromo');

const JOUR = new Date('2026-06-01T10:00:00');

test('un code valide renvoie sa remise en pourcentage', () => {
  expect(validerCode('RANDO10', JOUR)).toEqual({ valide: true, remise: 10 });
});

test('la casse est ignorée', () => {
  expect(validerCode('rando10', JOUR)).toEqual({ valide: true, remise: 10 });
});

test('les espaces autour sont ignorés', () => {
  expect(validerCode('  RANDO10 ', JOUR)).toEqual({ valide: true, remise: 10 });
});

test.each(['ABC', 'ABCDEFGHIJK', 'RANDO-10'])('le code « %s » est mal formé', (code) => {
  expect(validerCode(code, JOUR)).toEqual({ valide: false, raison: 'FORMAT' });
});

test.each(['ABCD', 'ABCDEFGHIJ'])('le code « %s », bien formé mais absent, est INCONNU', (code) => {
  expect(validerCode(code, JOUR)).toEqual({ valide: false, raison: 'INCONNU' });
});

test("un code est valable jusqu'au soir de son expiration", () => {
  expect(validerCode('ETE2026', new Date('2026-08-31T20:00:00'))).toEqual({ valide: true, remise: 15 });
});

test('un code est expiré le lendemain', () => {
  expect(validerCode('ETE2026', new Date('2026-09-01T08:00:00'))).toEqual({ valide: false, raison: 'EXPIRE' });
});

test('un code sans utilisations restantes est épuisé', () => {
  expect(validerCode('VIP30', JOUR)).toEqual({ valide: false, raison: 'EPUISE' });
});

test("l'expiration est prioritaire sur l'épuisement", () => {
  expect(validerCode('NOEL25', JOUR)).toEqual({ valide: false, raison: 'EXPIRE' });
});
EOF
#@ J4.2
cat > src/codesPromo.js <<'EOF'
const CODES = require('./data/codes');

const FORMAT = /^[A-Z0-9]{4,10}$/;

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
#@ J4.3
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
cat > tests/codes-minuit.test.js <<'EOF'
const { validerCode } = require('../src/codesPromo');

// ETE2026 expire le 31 août 2026, jour inclus, en heure locale.
// Le constructeur numérique est toujours en heure locale, quel que soit le fuseau (mois 7 = août).
test("le code est valable jusqu'à la dernière milliseconde du 31 août", () => {
  expect(validerCode('ETE2026', new Date(2026, 7, 31, 23, 59, 59, 999))).toEqual({ valide: true, remise: 15 });
});

test('le code est expiré à minuit pile le 1er septembre', () => {
  expect(validerCode('ETE2026', new Date(2026, 8, 1, 0, 0, 0, 0))).toEqual({ valide: false, raison: 'EXPIRE' });
});
EOF
''',
    5: r'''
cd ~/boutique
#@ J5.1
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
cat > tests/relance.test.js <<'EOF'
const { Panier } = require('../src/panier');
const { programmerRelance } = require('../src/relance');

const VINGT_QUATRE_HEURES = 24 * 60 * 60 * 1000;
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

test("rien n'est envoyé avant 24 h", () => {
  programmerRelance(panier, client, mailer);
  jest.advanceTimersByTime(VINGT_QUATRE_HEURES - 1);
  expect(mailer.envoyer).not.toHaveBeenCalled();
});

test('la relance part au bout de 24 h avec le nombre d’articles', () => {
  programmerRelance(panier, client, mailer);
  jest.advanceTimersByTime(VINGT_QUATRE_HEURES);
  expect(mailer.envoyer).toHaveBeenCalledWith(
    'bob@exemple.fr', 'Votre panier vous attend', 'Vous avez 3 article(s) dans votre panier.');
});

test('une seule relance, même trois jours plus tard', () => {
  programmerRelance(panier, client, mailer);
  jest.advanceTimersByTime(3 * VINGT_QUATRE_HEURES);
  expect(mailer.envoyer).toHaveBeenCalledTimes(1);
});

test('une relance annulée ne part jamais', () => {
  const relance = programmerRelance(panier, client, mailer);
  relance.annuler();
  jest.advanceTimersByTime(2 * VINGT_QUATRE_HEURES);
  expect(mailer.envoyer).not.toHaveBeenCalled();
});

test('un panier vidé entre-temps ne reçoit pas de relance', () => {
  programmerRelance(panier, client, mailer);
  panier.retirer('GOURDE');
  jest.advanceTimersByTime(2 * VINGT_QUATRE_HEURES);
  expect(mailer.envoyer).not.toHaveBeenCalled();
});
EOF
#@ J7.2
cat > tests/debit-patient.test.js <<'EOF'
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
test('attend 1 s avant la 2e tentative, puis 2 s avant la 3e', async () => {
  banque.debiter
    .mockRejectedValueOnce(new Error('ETIMEDOUT'))
    .mockRejectedValueOnce(new Error('ETIMEDOUT'))
    .mockResolvedValueOnce({ accepte: true, transaction: 'TX-3' });
  const resultat = debiterPatiemment(banque, '4970-1234', 60);
  expect(banque.debiter).toHaveBeenCalledTimes(1);
  await jest.advanceTimersByTimeAsync(999);
  expect(banque.debiter).toHaveBeenCalledTimes(1);
  await jest.advanceTimersByTimeAsync(1);
  expect(banque.debiter).toHaveBeenCalledTimes(2);
  await jest.advanceTimersByTimeAsync(1999);
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
cat > tests/fidelite.test.js <<'EOF'
const { pointsFidelite } = require('../src/fidelite');

const standard = { statut: 'standard', dateAchat: '2026-03-10' };

test.each([
  ['un achat nul', 0, standard, 0],
  ['un montant négatif', -5, standard, 0],
  ['un client standard (euros entiers)', 99.9, standard, 99],
  ['un client gold (x2)', 100, { ...standard, statut: 'gold' }, 200],
  ['un client silver (x1,5 arrondi inférieur)', 101, { ...standard, statut: 'silver' }, 151],
  ['un anniversaire dans le mois (+100)', 50, { ...standard, anniversaire: '1990-03-22' }, 150],
  ['un anniversaire un autre mois', 50, { ...standard, anniversaire: '1990-07-22' }, 50],
  ['le plafond de 1000 points', 800, { ...standard, statut: 'gold' }, 1000],
  ['un achat nul le mois de son anniversaire', 0, { ...standard, anniversaire: '1990-03-22' }, 0],
])('%s', (_cas, montant, client, attendu) => {
  expect(pointsFidelite(montant, client)).toBe(attendu);
});
EOF
#@ J8.3
cat >> tests/fidelite.test.js <<'EOF'

describe("ordre des règles : statut, puis bonus d'anniversaire, puis plafond", () => {
  test("le bonus d'anniversaire s'ajoute après le multiplicateur gold", () => {
    // 50 € -> 50 points, x2 = 100, +100 = 200 (et non (50 + 100) x 2 = 300)
    expect(pointsFidelite(50, { ...standard, statut: 'gold', anniversaire: '1990-03-22' })).toBe(200);
  });

  test("le plafond s'applique après le bonus d'anniversaire", () => {
    // 950 € -> 950 points, +100 = 1050, plafonnés à 1000 (et non 950 puis +100 = 1050)
    expect(pointsFidelite(950, { ...standard, anniversaire: '1990-03-22' })).toBe(1000);
  });
});
EOF
''',
    9: r'''
cd ~/boutique
#@ J9.1
cat > tests/facture.test.js <<'EOF'
const { Panier } = require('../src/panier');
const { genererFacture } = require('../src/facture');

test('bug #218 : le port est dû quand la remise fait passer sous le seuil', () => {
  // 55 € HT -> 66 € TTC (au-dessus de 60 €) -> -10 % = 59,40 € (en dessous) -> port 8,90 €
  const panier = new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 55 });
  expect(genererFacture(panier, { pays: 'FR', poidsKg: 2, remise: 10 })).toEqual({ produitsTTC: 59.4, port: 8.9, total: 68.3 });
});

test('au-dessus du seuil après remise, le port reste offert', () => {
  const panier = new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 100 });
  expect(genererFacture(panier, { pays: 'FR', poidsKg: 6, remise: 20 })).toEqual({ produitsTTC: 96, port: 0, total: 96 });
});
EOF
#@ J9.2
cat >> tests/facture.test.js <<'EOF'

test('bug #219 : le port suit le poids exact du colis', () => {
  // 40 € HT -> 48 € TTC (sous le seuil) ; 4,6 kg -> tranche « moins de 5 kg » : 8,90 €
  const panier = new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 40 });
  expect(genererFacture(panier, { pays: 'FR', poidsKg: 4.6 })).toEqual({ produitsTTC: 48, port: 8.9, total: 56.9 });
});
EOF
sed -i 's/livraisonOfferte(totalTTC, pays)/livraisonOfferte(produitsTTC, pays)/; s/fraisLivraison(Math.round(poidsKg), pays)/fraisLivraison(poidsKg, pays)/' src/facture.js
#@ J9.3
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
# Réactive tous les tests du brouillon, et corrige la valeur fausse qui n'avait jamais tourné (5 kg vers l'Espagne : 14,90 + 8 = 22,90 €)
sed -i 's/test\.only\.each(/test.each(/; s/test\.skip(/test(/; s/^  xit(/  test(/; s/^describe\.skip(/describe(/; s/toBe(16\.9)/toBe(22.9)/' tests/wip-thomas.test.js
#@ J10.2
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
# Le snapshot figeait deux bugs : « BE » au lieu de « BELGIQUE », et 2 lignes au lieu de 4 articles
sed -i 's/`Articles : ${panier.lignes().length}`/`Articles : ${panier.nombreArticles()}`/; s/^    client.pays,$/    PAYS[client.pays],/' src/etiquette.js
npx jest tests/etiquette -u >/dev/null 2>&1
''',
}
