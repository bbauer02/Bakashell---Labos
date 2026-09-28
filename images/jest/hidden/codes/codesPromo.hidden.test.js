// Tests cachés : spécification complète des codes promo (SPEC-codes-promo.md)
const { validerCode } = require('../src/codesPromo');

const LE_1ER_JUIN_2026 = new Date('2026-06-01T10:00:00');

describe('Spécification des codes promo', () => {
  test('un code valide renvoie la remise en pourcentage', () => {
    expect(validerCode('RANDO10', LE_1ER_JUIN_2026)).toEqual({ valide: true, remise: 10 });
  });

  test('la saisie est insensible à la casse et aux espaces autour', () => {
    expect(validerCode('  rando10 ', LE_1ER_JUIN_2026)).toEqual({ valide: true, remise: 10 });
    expect(validerCode('Ete2026', LE_1ER_JUIN_2026)).toEqual({ valide: true, remise: 15 });
  });

  test.each(['', 'AB', 'ABC', 'TROPLONGCODE1', 'RANDO-10', 'RANDO 10', '€URO'])(
    "le code mal formé « %s » est refusé pour FORMAT",
    (code) => {
      expect(validerCode(code, LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'FORMAT' });
    },
  );

  test('4 et 10 caractères sont les longueurs limites acceptées', () => {
    expect(validerCode('ABCD', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'INCONNU' });
    expect(validerCode('ABCDEFGHIJ', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'INCONNU' });
  });

  test('un code bien formé mais absent du catalogue est INCONNU', () => {
    expect(validerCode('PROMO99', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'INCONNU' });
  });

  test("un code reste valable toute la journée de son expiration", () => {
    expect(validerCode('ETE2026', new Date('2026-08-31T23:59:00'))).toEqual({ valide: true, remise: 15 });
  });

  test('un code est EXPIRE le lendemain de sa date', () => {
    expect(validerCode('ETE2026', new Date('2026-09-01T00:00:01'))).toEqual({ valide: false, raison: 'EXPIRE' });
  });

  test('un code sans utilisations restantes est EPUISE', () => {
    expect(validerCode('VIP30', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'EPUISE' });
  });

  test('EXPIRE est prioritaire sur EPUISE', () => {
    expect(validerCode('NOEL25', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'EXPIRE' });
  });

  test('FORMAT est vérifié avant tout le reste', () => {
    expect(validerCode('noel-25', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'FORMAT' });
  });

  test("sans date fournie, la date du jour est utilisée", () => {
    jest.useFakeTimers({ now: new Date('2026-07-14T12:00:00') });
    try {
      expect(validerCode('ETE2026')).toEqual({ valide: true, remise: 15 });
      jest.setSystemTime(new Date('2026-12-25T12:00:00'));
      expect(validerCode('ETE2026')).toEqual({ valide: false, raison: 'EXPIRE' });
    } finally {
      jest.useRealTimers();
    }
  });
});
