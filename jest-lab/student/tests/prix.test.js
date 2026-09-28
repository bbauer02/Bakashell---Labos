const { calculerTTC } = require('../src/prix');

// Tests écrits par Thomas
describe('calculerTTC', () => {
  test('ajoute 20 % de TVA par défaut', () => {
    expect(calculerTTC(100)).toBe(120);
  });

  test('accepte un autre taux de TVA', () => {
    expect(calculerTTC(10, 0.25)).toBe(12.5);
  });

  test("calcule le prix TTC d'un article à 19,99 € HT", () => {
    expect(calculerTTC(19.99)).toBe(19.99 * 1.2);
  });
});
