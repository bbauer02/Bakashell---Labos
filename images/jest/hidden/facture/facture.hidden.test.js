// Tests cachés : comportement attendu de genererFacture
// La grille de livraison dépend de la variante de l'étudiant : les valeurs attendues sont calculées
// ici, à partir de la grille (règle métier), sans utiliser le code de l'étudiant.
const { Panier } = require('../../src/panier');
const { genererFacture } = require('../../src/facture');

const GRILLE = {
  limites: [{{LIV_L1}}, {{LIV_L2}}],
  bases: [{{LIV_B1}}, {{LIV_B2}}, {{LIV_B3}}],
  supplements: { FR: 0, BE: {{LIV_SP}}, DE: {{LIV_SL}} },
  seuils: { FR: {{LIV_SFR}}, ailleurs: {{LIV_SAU}} },
};

const centimes = (x) => Math.round(Number((x * 100).toFixed(6))) / 100;

function port(poids, pays) {
  const [l1, l2] = GRILLE.limites;
  const base = poids < l1 ? GRILLE.bases[0] : poids < l2 ? GRILLE.bases[1] : GRILLE.bases[2];
  return centimes(base + GRILLE.supplements[pays]);
}

/** Facture attendue, pour un article de prixHT (TVA 20 %). */
function attendue(prixHT, { pays, poidsKg, remise = 0 }) {
  const produitsTTC = centimes(centimes(prixHT * 1.2) * (1 - remise / 100));
  const seuil = pays === 'FR' ? GRILLE.seuils.FR : GRILLE.seuils.ailleurs;
  const frais = produitsTTC >= seuil ? 0 : port(poidsKg, pays);
  return { produitsTTC, port: frais, total: centimes(produitsTTC + frais) };
}

const panierDe = (prixHT) => new Panier().ajouter({ ref: 'SAC-40L', libelle: 'Sac à dos 40 L', prixHT });

const cas = (prixHT, options) => expect(genererFacture(panierDe(prixHT), options)).toEqual(attendue(prixHT, options));

describe('genererFacture', () => {
  const S = GRILLE.seuils.FR;
  const A = GRILLE.seuils.ailleurs;

  test('sans remise, en dessous du seuil, les frais de port sont facturés', () => {
    cas(S / 2, { pays: 'FR', poidsKg: 2 });
    expect(attendue(S / 2, { pays: 'FR', poidsKg: 2 }).port).toBeGreaterThan(0);
  });

  test('au-dessus du seuil, la livraison est offerte', () => {
    cas(S, { pays: 'FR', poidsKg: 2 });
    expect(attendue(S, { pays: 'FR', poidsKg: 2 }).port).toBe(0);
  });

  test('le seuil de livraison offerte est apprécié APRÈS remise (bug #218)', () => {
    // 1,2 × S TTC avant remise (au-dessus du seuil), 0,96 × S après 20 % (en dessous) : le port reste dû
    cas(S, { pays: 'FR', poidsKg: 2, remise: 20 });
    expect(attendue(S, { pays: 'FR', poidsKg: 2, remise: 20 }).port).toBeGreaterThan(0);
  });

  test('une remise qui laisse le montant au-dessus du seuil garde la livraison offerte', () => {
    cas(S, { pays: 'FR', poidsKg: 6, remise: 10 });
  });

  test('hors de France, le seuil ne concerne que le montant après remise', () => {
    cas(A, { pays: 'BE', poidsKg: 2, remise: 20 });
    cas(A, { pays: 'DE', poidsKg: 2, remise: 10 });
  });

  test('les frais de port suivent le poids exact du colis (bug #219)', () => {
    const [l1, l2] = GRILLE.limites;
    // Un poids qui franchirait une tranche s'il était arrondi au kilo
    cas(S / 2, { pays: 'FR', poidsKg: l2 - 0.4 });
    cas(S / 2, { pays: 'FR', poidsKg: l1 - 0.4 });
    cas(S / 2, { pays: 'FR', poidsKg: l1 + 0.4 });
  });
});
