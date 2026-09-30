// Tests cachés : spécification complète des codes promo (SPEC-codes-promo.md)
// Les codes et les longueurs autorisées dépendent de la variante de l'étudiant (marqueurs {{…}}).
const { validerCode } = require('../../src/codesPromo');

const LE_1ER_JUIN_2026 = new Date('2026-06-01T10:00:00');

/** Instant local : le jour « AAAA-MM-JJ » à l'heure indiquée, décalé de « jours » jours. */
function le(jour, heure, jours = 0) {
  const [a, m, j] = jour.split('-').map(Number);
  const [h, min, s, ms] = heure;
  return new Date(a, m - 1, j + jours, h, min, s, ms);
}

describe('Spécification des codes promo', () => {
  test('un code valide renvoie la remise en pourcentage', () => {
    expect(validerCode('{{CODE_A}}', LE_1ER_JUIN_2026)).toEqual({ valide: true, remise: {{REMISE_A}} });
  });

  test('la saisie est insensible à la casse et aux espaces autour', () => {
    expect(validerCode('  {{CODE_A_MIN}} ', LE_1ER_JUIN_2026)).toEqual({ valide: true, remise: {{REMISE_A}} });
    expect(validerCode('{{CODE_B_MIXTE}}', LE_1ER_JUIN_2026)).toEqual({ valide: true, remise: {{REMISE_B}} });
  });

  test.each(['', 'A', '{{CODE_TROP_COURT}}', '{{CODE_TROP_LONG}}', 'TROPLONGCODE1', 'RANDO-10', 'RANDO 10', '€URO'])(
    "le code mal formé « %s » est refusé pour FORMAT",
    (code) => {
      expect(validerCode(code, LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'FORMAT' });
    },
  );

  test('{{CODES_MIN}} et {{CODES_MAX}} caractères sont les longueurs limites acceptées', () => {
    expect(validerCode('{{CODE_LIM_MIN}}', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'INCONNU' });
    expect(validerCode('{{CODE_LIM_MAX}}', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'INCONNU' });
  });

  test('un code bien formé mais absent du catalogue est INCONNU', () => {
    expect(validerCode('PROMO99', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'INCONNU' });
  });

  test("un code reste valable toute la journée de son expiration", () => {
    expect(validerCode('{{CODE_B}}', le('{{EXPIRE_B}}', [23, 59, 0, 0]))).toEqual({ valide: true, remise: {{REMISE_B}} });
  });

  test('un code est EXPIRE le lendemain de sa date', () => {
    expect(validerCode('{{CODE_B}}', le('{{EXPIRE_B}}', [0, 0, 1, 0], 1))).toEqual({ valide: false, raison: 'EXPIRE' });
  });

  test('un code sans utilisations restantes est EPUISE', () => {
    expect(validerCode('{{CODE_C}}', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'EPUISE' });
  });

  test('EXPIRE est prioritaire sur EPUISE', () => {
    expect(validerCode('{{CODE_D}}', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'EXPIRE' });
  });

  test('FORMAT est vérifié avant tout le reste', () => {
    expect(validerCode('{{CODE_D_TIRET}}', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'FORMAT' });
  });

  test("sans date fournie, la date du jour est utilisée", () => {
    jest.useFakeTimers({ now: new Date('2026-07-14T12:00:00') });
    try {
      expect(validerCode('{{CODE_B}}')).toEqual({ valide: true, remise: {{REMISE_B}} });
      jest.setSystemTime(new Date('2026-12-25T12:00:00'));
      expect(validerCode('{{CODE_B}}')).toEqual({ valide: false, raison: 'EXPIRE' });
    } finally {
      jest.useRealTimers();
    }
  });
});
