const TVA_NORMALE = 0.2;

/**
 * Arrondi commercial au centime le plus proche, les demi-centimes vers le haut (1,005 € -> 1,01 €).
 * Le montant en centimes est d'abord ramené à 6 décimales : on efface ainsi l'erreur de représentation
 * binaire (1.005 * 100 vaut 100.49999999999999) avant d'arrondir.
 */
function arrondir(montant) {
  return Math.round(Number((montant * 100).toFixed(6))) / 100;
}

/** Prix TTC arrondi au centime. */
function calculerTTC(prixHT, taux = TVA_NORMALE) {
  if (typeof prixHT !== 'number' || Number.isNaN(prixHT) || prixHT < 0) {
    throw new TypeError('Prix HT invalide');
  }
  return arrondir(prixHT * (1 + taux));
}

/** Applique une remise en pourcentage (0 à 100). */
function appliquerRemise(prix, pourcentage) {
  if (pourcentage < 0 || pourcentage > 100) {
    throw new RangeError('Remise invalide');
  }
  return arrondir(prix * (1 - pourcentage / 100));
}

module.exports = { TVA_NORMALE, arrondir, calculerTTC, appliquerRemise };
