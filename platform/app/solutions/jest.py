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
node -e '
const fs = require("fs");
const p = JSON.parse(fs.readFileSync("package.json", "utf8"));
p.scripts = { test: "jest", "test:watch": "jest --watch", "test:coverage": "jest --coverage" };
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
    [6, 'IT', 22.9],
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

test.each(['ABC', 'TROPLONGCODE1', 'RANDO-10'])('le code « %s » est mal formé', (code) => {
  expect(validerCode(code, JOUR)).toEqual({ valide: false, raison: 'FORMAT' });
});

test('un code de 4 caractères bien formé mais absent est INCONNU', () => {
  expect(validerCode('ABCD', JOUR)).toEqual({ valide: false, raison: 'INCONNU' });
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
''',
    5: r'''
cd ~/boutique
#@ J5.1
cat > tests/stock.test.js <<'EOF'
const { Panier } = require('../src/panier');
const { verifierDisponibilite } = require('../src/stock');

const gourde = { ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 12.5 };
const lampe = { ref: 'LAMPE', libelle: 'Lampe frontale', prixHT: 25 };

const apiAvec = (stocks) => ({ quantiteDisponible: jest.fn(async (ref) => stocks[ref]) });

test('rien ne manque quand le stock est tout juste suffisant', async () => {
  const api = apiAvec({ GOURDE: 2 });
  const panier = new Panier().ajouter(gourde, 2);
  await expect(verifierDisponibilite(panier, api)).resolves.toEqual([]);
  expect(api.quantiteDisponible).toHaveBeenCalledWith('GOURDE');
});

test('chaque ligne est vérifiée et les manques sont détaillés', async () => {
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

test('débite le montant TTC sur la carte du client', async () => {
  await passerCommande(panier(), client);
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
  jest.clearAllMocks();
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

test('une relance annulée ne part jamais', () => {
  const relance = programmerRelance(panier, client, mailer);
  relance.annuler();
  jest.advanceTimersByTime(2 * VINGT_QUATRE_HEURES);
  expect(mailer.envoyer).not.toHaveBeenCalled();
});

test('un panier vidé entre-temps ne reçoit pas de relance', () => {
  programmerRelance(panier, client, mailer);
  panier.retirer('GOURDE');
  jest.runAllTimers();
  expect(mailer.envoyer).not.toHaveBeenCalled();
});
EOF
''',
    8: r'''
cd ~/boutique
#@ J8.1
node -e '
const fs = require("fs");
const p = JSON.parse(fs.readFileSync("package.json", "utf8"));
p.jest = { collectCoverageFrom: ["src/**/*.js"], coverageThreshold: { global: { branches: 80, lines: 90 } } };
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
''',
    9: r'''
cd ~/boutique
#@ J9.1
cat > tests/facture.test.js <<'EOF'
const { Panier } = require('../src/panier');
const { genererFacture } = require('../src/facture');

test('bug #218 : le port est dû quand la remise fait passer sous le seuil', () => {
  const panier = new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 55 });
  expect(genererFacture(panier, { pays: 'FR', poidsKg: 2, remise: 10 })).toEqual({ produitsTTC: 59.4, port: 8.9, total: 68.3 });
});

test('au-dessus du seuil après remise, le port reste offert', () => {
  const panier = new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 100 });
  expect(genererFacture(panier, { pays: 'FR', poidsKg: 6, remise: 20 })).toEqual({ produitsTTC: 96, port: 0, total: 96 });
});
EOF
#@ J9.2
sed -i 's/livraisonOfferte(totalTTC, pays)/livraisonOfferte(produitsTTC, pays)/' src/facture.js
''',
    10: r'''
cd ~/boutique
#@ J10.1
sed -i 's/test\.only(/test(/; s/test\.skip(/test(/' tests/wip-thomas.test.js
#@ J10.2
mkdir -p .github/workflows
cat > .github/workflows/tests.yml <<'EOF'
name: Tests
on: [push, pull_request]
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm test -- --coverage
EOF
''',
}
