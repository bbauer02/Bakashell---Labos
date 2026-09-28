const { fraisLivraison } = require('../src/livraison');

// Brouillon de Thomas : « je finis demain »
describe('fraisLivraison (WIP Thomas)', () => {
  test.only('colis léger en France', () => {
    expect(fraisLivraison(0.5, 'FR')).toBe(4.9);
  });

  test.skip('colis lourd en Italie', () => {
    expect(fraisLivraison(7, 'IT')).toBe(22.9);
  });
});
