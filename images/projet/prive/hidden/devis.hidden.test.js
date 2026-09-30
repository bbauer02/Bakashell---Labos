// Tests de validation (cachés) : toutes les règles de src/devis.js, pour la variante de l'étudiant.
// Les valeurs attendues sont calculées ici, en centimes entiers, à partir des règles métier.
const { calculerDevis, prixUnitaireTTC } = require('../../src/devis');

const QTE = {{QTE}};
const TAUX = {{TAUX}};
const FRAIS = Math.round({{FRAIS}} * 100);
const SEUIL = {{SEUIL}} * 100;

const cts = (x) => Math.round(Number((x * 100).toFixed(6)));
const pourcent = (montant, taux) => Math.round((montant * taux) / 100);

/** Devis attendu (en euros), calculé en centimes. */
function attendu(lignes, catalogue) {
  const details = lignes.map(({ ref, quantite }) => {
    const unite = cts(catalogue.find((p) => p.ref === ref).prixHT * 1.2);
    const brut = unite * quantite;
    const remise = quantite >= QTE ? pourcent(brut, TAUX) : 0;
    return { ref, quantite, brut: brut / 100, remise: remise / 100, net: (brut - remise) / 100 };
  });
  const brut = details.reduce((s, l) => s + Math.round(l.brut * 100), 0);
  const remises = details.reduce((s, l) => s + Math.round(l.remise * 100), 0);
  const produits = brut - remises;
  const port = produits >= SEUIL ? 0 : FRAIS;
  return { lignes: details, brut: brut / 100, remises: remises / 100, produits: produits / 100, port: port / 100, total: (produits + port) / 100 };
}

const catalogue = [
  { ref: 'CARTE', prixHT: 10.01 },
  { ref: 'GOURDE', prixHT: 19.99 },
  { ref: 'TENTE', prixHT: 100 },
  { ref: 'PILE', prixHT: {{SEUIL_HT}} },
  { ref: 'SOUS', prixHT: {{SOUS_HT}} },
  { ref: 'PAIRE', prixHT: {{V2_HT}} },
  { ref: 'MINI', prixHT: 0.99 },
];

const cas = {
  'une seule ligne, sans remise': [{ ref: 'GOURDE', quantite: 1 }],
  'exactement au seuil': [{ ref: 'PILE', quantite: 1 }],
  'juste sous le seuil': [{ ref: 'SOUS', quantite: 1 }],
  'remise à partir du seuil de quantité': [{ ref: 'CARTE', quantite: QTE }],
  'pas de remise juste en dessous': [{ ref: 'CARTE', quantite: QTE - 1 }],
  'remise limitée à la ligne concernée': [{ ref: 'CARTE', quantite: QTE }, { ref: 'TENTE', quantite: 1 }],
  'remise sur plusieurs lignes': [{ ref: 'MINI', quantite: QTE + 2 }, { ref: 'CARTE', quantite: QTE }],
  'le seuil s\'apprécie remises déduites': [{ ref: 'PAIRE', quantite: QTE }],
  'arrondi du prix unitaire avant la quantité': [{ ref: 'GOURDE', quantite: 3 }],
  'arrondi vers le bas': [{ ref: 'CARTE', quantite: 1 }, { ref: 'MINI', quantite: 2 }],
  'grosse commande': [{ ref: 'TENTE', quantite: 2 }, { ref: 'GOURDE', quantite: QTE + 1 }],
};

describe('calculerDevis (validation)', () => {
  test.each(Object.entries(cas))('%s', (_nom, lignes) => {
    expect(calculerDevis(lignes, catalogue)).toEqual(attendu(lignes, catalogue));
  });

  test('prix unitaires TTC arrondis au centime', () => {
    expect(prixUnitaireTTC(19.99)).toBe(23.99);
    expect(prixUnitaireTTC(10.01)).toBe(12.01);
    expect(prixUnitaireTTC(0.99)).toBe(1.19);
    expect(prixUnitaireTTC(10)).toBe(12);
  });

  test('les erreurs restent signalées', () => {
    expect(() => calculerDevis([], catalogue)).toThrow();
    expect(() => calculerDevis([{ ref: 'PIOLET', quantite: 1 }], catalogue)).toThrow('Article inconnu');
    expect(() => calculerDevis([{ ref: 'CARTE', quantite: 0 }], catalogue)).toThrow('Quantité invalide');
    expect(() => calculerDevis([{ ref: 'CARTE', quantite: 1.5 }], catalogue)).toThrow('Quantité invalide');
  });
});
