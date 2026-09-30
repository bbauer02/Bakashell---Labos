// Tests cachés : tout ce qui n'est pas une chaîne est refusé pour FORMAT (ticket du front)
const { validerCode } = require('../../src/codesPromo');

const LE_1ER_JUIN_2026 = new Date('2026-06-01T10:00:00');

describe('Saisies qui ne sont pas des chaînes', () => {
  test.each([
    ['null', null],
    ['undefined', undefined],
    ['un nombre', 1234],
    ['un objet', { code: '{{CODE_A}}' }],
    ['un tableau', ['{{CODE_A}}']],
  ])('%s est refusé pour FORMAT', (_cas, saisie) => {
    expect(validerCode(saisie, LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'FORMAT' });
  });

  test('une chaîne valide reste acceptée', () => {
    expect(validerCode(' {{CODE_A_MIN}} ', LE_1ER_JUIN_2026)).toEqual({ valide: true, remise: {{REMISE_A}} });
  });

  test("un code inconnu reste INCONNU", () => {
    expect(validerCode('NULL', LE_1ER_JUIN_2026)).toEqual({ valide: false, raison: 'INCONNU' });
  });
});
