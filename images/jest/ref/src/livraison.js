/** Supplément par pays (en €), ajouté au tarif de base. */
const SUPPLEMENTS = {
  FR: 0,
  BE: 3,
  LU: 3,
  DE: 8,
  ES: 8,
  IT: 8,
  NL: 8,
};

/**
 * Frais de port TTC.
 * Tarif de base : moins de 1 kg -> 4,90 € ; moins de 5 kg -> 8,90 € ; au-delà -> 14,90 €.
 */
function fraisLivraison(poidsKg, pays) {
  if (!(pays in SUPPLEMENTS)) {
    throw new Error(`Livraison impossible vers ${pays}`);
  }
  if (typeof poidsKg !== 'number' || poidsKg <= 0) {
    throw new RangeError('Poids invalide');
  }
  let base;
  if (poidsKg < 1) {
    base = 4.9;
  } else if (poidsKg < 5) {
    base = 8.9;
  } else {
    base = 14.9;
  }
  return Math.round((base + SUPPLEMENTS[pays]) * 100) / 100;
}

/** Livraison offerte dès 60 € TTC en France, 100 € ailleurs. */
function livraisonOfferte(totalTTC, pays) {
  return pays === 'FR' ? totalTTC >= 60 : totalTTC >= 100;
}

module.exports = { fraisLivraison, livraisonOfferte };
