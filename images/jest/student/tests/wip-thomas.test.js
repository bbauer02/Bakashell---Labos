const { fraisLivraison, livraisonOfferte } = require('../src/livraison');

// Brouillon de Thomas : « je finis demain »
describe('fraisLivraison (WIP Thomas)', () => {
  test.only.each([
    [0.5, 'FR', {{LIV_WIP_FR}}],
    [2, 'BE', {{LIV_WIP_BE}}],
  ])('%s kg vers %s : %s €', (poids, pays, attendu) => {
    expect(fraisLivraison(poids, pays)).toBe(attendu);
  });

  test.skip('colis lourd en Italie', () => {
    expect(fraisLivraison(7, 'IT')).toBe({{LIV_WIP_IT}});
  });

  xit('colis de {{LIV_L2}} kg pile en Espagne', () => {
    expect(fraisLivraison({{LIV_L2}}, 'ES')).toBe({{LIV_WIP_ES_FAUX}});
  });
});

describe.skip('livraisonOfferte (WIP Thomas)', () => {
  test('offerte dès {{LIV_SAU}} € au Luxembourg', () => {
    expect(livraisonOfferte({{LIV_SAU}}, 'LU')).toBe(true);
  });
});
