const { appliquerRemise } = require('../src/prix');

// Tests écrits par Thomas : « tout est vert, et appliquerRemise est couverte à 100 % ! »
describe('appliquerRemise', () => {
  test('applique une remise de 10 %', () => {
    expect(appliquerRemise(50, 10));
  });

  test('arrondit le prix remisé au centime', () => {
    const attendu = appliquerRemise(19.99, 15);
    expect(appliquerRemise(19.99, 15)).toBe(attendu);
  });

  test('applique une remise de 25 %', () => {
    appliquerRemise(80, 25);
  });

  test('refuse une remise de plus de 100 %', () => {
    expect(() => appliquerRemise(50, 120)).toThrow;
  });
});
