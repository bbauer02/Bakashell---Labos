/** Supplément par pays (en €), ajouté au tarif de base. */
const SUPPLEMENTS = {
  FR: 0,
  BE: {{LIV_SP}},
  LU: {{LIV_SP}},
  DE: {{LIV_SL}},
  ES: {{LIV_SL}},
  IT: {{LIV_SL}},
  NL: {{LIV_SL}},
};

/**
 * Frais de port TTC.
 * Tarif de base : moins de {{LIV_L1}} kg -> {{LIV_B1_TXT}} € ; moins de {{LIV_L2}} kg -> {{LIV_B2_TXT}} € ; au-delà -> {{LIV_B3_TXT}} €.
 */
function fraisLivraison(poidsKg, pays) {
  if (!(pays in SUPPLEMENTS)) {
    throw new Error(`Livraison impossible vers ${pays}`);
  }
  if (typeof poidsKg !== 'number' || poidsKg <= 0) {
    throw new RangeError('Poids invalide');
  }
  let base;
  if (poidsKg < {{LIV_L1}}) {
    base = {{LIV_B1}};
  } else if (poidsKg < {{LIV_L2}}) {
    base = {{LIV_B2}};
  } else {
    base = {{LIV_B3}};
  }
  return Math.round((base + SUPPLEMENTS[pays]) * 100) / 100;
}

/** Livraison offerte dès {{LIV_SFR}} € TTC en France, {{LIV_SAU}} € ailleurs. */
function livraisonOfferte(totalTTC, pays) {
  return pays === 'FR' ? totalTTC >= {{LIV_SFR}} : totalTTC >= {{LIV_SAU}};
}

module.exports = { fraisLivraison, livraisonOfferte };
