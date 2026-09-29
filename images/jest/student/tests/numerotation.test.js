const { prochainNumero } = require('../src/numerotation');

// Tests écrits par Thomas : « verts chez moi… sauf quand je lance un test tout seul »
describe('prochainNumero', () => {
  test('la première commande porte le numéro CMD-0001', () => {
    expect(prochainNumero()).toBe('CMD-0001');
  });

  test('les numéros se suivent', () => {
    expect(prochainNumero()).toBe('CMD-0002');
    expect(prochainNumero()).toBe('CMD-0003');
  });

  test('le numéro est toujours écrit sur 4 chiffres', () => {
    expect(prochainNumero()).toMatch(/^CMD-\d{4}$/);
  });
});
