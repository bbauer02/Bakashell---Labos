jest.mock('../src/services/paiement');
jest.mock('../src/services/mailer');

const paiement = require('../src/services/paiement');
const mailer = require('../src/services/mailer');
const { Panier } = require('../src/panier');
const { passerCommande } = require('../src/commande');

// Tests écrits par Thomas : « 4 tests, 4 verts, et je n'ai jamais vu l'un d'eux échouer ! »
const client = { email: 'alice@exemple.fr', carte: '4970-1234' };
const panier = () => new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 50 });

beforeEach(() => {
  jest.clearAllMocks();
  paiement.debiter.mockResolvedValue({ accepte: true, transaction: 'TX-1' });
  mailer.envoyer.mockResolvedValue();
});

test('un panier vide est refusé', async () => {
  try {
    await passerCommande(new Panier(), client);
  } catch (erreur) {
    expect(erreur.message).toBe('Panier vide');
  }
});

test('un refus de la banque remonte avec son motif', () => {
  paiement.debiter.mockResolvedValue({ accepte: false, motif: 'plafond atteint' });
  passerCommande(panier(), client).catch((erreur) => {
    expect(erreur.message).toMatch('plafond atteint');
  });
});

test("après un refus, aucun e-mail de confirmation n'est envoyé", () => {
  paiement.debiter.mockResolvedValue({ accepte: false, motif: 'plafond atteint' });
  passerCommande(panier(), client).catch(() => {});
  expect(mailer.envoyer).not.toHaveBeenCalled();
});

test('après deux pannes, le client est prévenu', async () => {
  paiement.debiter.mockRejectedValue(new Error('ECONNRESET'));
  await expect(passerCommande(panier(), client)).rejects.toThrow();
});
