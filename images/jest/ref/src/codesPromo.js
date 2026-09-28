const CODES = require('./data/codes');

const FORMAT = /^[A-Z0-9]{4,10}$/;

/**
 * Vérifie un code promo.
 * Retourne { valide: true, remise } ou { valide: false, raison }.
 * Ordre des vérifications : FORMAT, INCONNU, EXPIRE, EPUISE.
 */
function validerCode(code, maintenant = new Date()) {
  const saisi = String(code).trim().toUpperCase();
  if (!FORMAT.test(saisi)) {
    return { valide: false, raison: 'FORMAT' };
  }
  const entree = CODES.find((c) => c.code === saisi);
  if (!entree) {
    return { valide: false, raison: 'INCONNU' };
  }
  const finValidite = new Date(`${entree.expire}T23:59:59.999`);
  if (maintenant > finValidite) {
    return { valide: false, raison: 'EXPIRE' };
  }
  if (entree.restants <= 0) {
    return { valide: false, raison: 'EPUISE' };
  }
  return { valide: true, remise: entree.remise };
}

module.exports = { validerCode };
