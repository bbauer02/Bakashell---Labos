jest.mock('../src/services/paiement');
jest.mock('../src/services/mailer');

const paiement = require('../src/services/paiement');
const mailer = require('../src/services/mailer');
const { Panier } = require('../src/panier');
const { passerCommande } = require('../src/commande');

// Tests écrits par Thomas : « verts chez moi, rouges une fois sur deux dans la CI (jest --randomize) »
const client = { email: 'alice@exemple.fr', carte: '4970-1234' };
const panier = () => new Panier().ajouter({ ref: 'SAC', libelle: 'Sac 40 L', prixHT: 50 });

beforeAll(() => {
  paiement.debiter.mockResolvedValue({ accepte: true, transaction: 'TX-0' });
});

beforeEach(() => {
  jest.clearAllMocks();
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
  paiement.debiter
    .mockResolvedValueOnce({ accepte: true, transaction: 'TX-1' })
    .mockResolvedValueOnce({ accepte: true, transaction: 'TX-1' });
  await expect(passerCommande(panier(), client)).resolves.toEqual({ numero: 'TX-1', montant: 60 });
});
