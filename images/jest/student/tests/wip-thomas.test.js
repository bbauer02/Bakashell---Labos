const { fraisLivraison, livraisonOfferte } = require('../src/livraison');

// Brouillon de Thomas : « je finis demain »
describe('fraisLivraison (WIP Thomas)', () => {
  test.only.each([
    [0.5, 'FR', 4.9],
    [2, 'BE', 11.9],
  ])('%s kg vers %s : %s €', (poids, pays, attendu) => {
    expect(fraisLivraison(poids, pays)).toBe(attendu);
  });

  test.skip('colis lourd en Italie', () => {
    expect(fraisLivraison(7, 'IT')).toBe(22.9);
  });

  xit('colis de 5 kg pile en Espagne', () => {
    expect(fraisLivraison(5, 'ES')).toBe(16.9);
  });
});

describe.skip('livraisonOfferte (WIP Thomas)', () => {
  test('offerte dès 100 € au Luxembourg', () => {
    expect(livraisonOfferte(100, 'LU')).toBe(true);
  });
});
