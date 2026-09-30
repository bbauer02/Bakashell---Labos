const { calculerDevis, prixUnitaireTTC } = require('../src/devis');

// Catalogue de test (prix HT)
const catalogue = [
  { ref: 'CARTE', libelle: 'Carte IGN', prixHT: 10 },
  { ref: 'GOURDE', libelle: 'Gourde 1 L', prixHT: 20 },
  { ref: 'TENTE', libelle: 'Tente 2 places', prixHT: 100 },
  { ref: 'DUVET', libelle: 'Duvet léger', prixHT: {{SEUIL_HT}} },
  { ref: 'CHAUSSETTES', libelle: 'Chaussettes de randonnée', prixHT: {{V2_HT}} },
];

describe('prixUnitaireTTC', () => {
  test('ajoute 20 % de TVA', () => {
    expect(prixUnitaireTTC(10)).toBe(12);
  });
{{COMPLICE_PRIX}}});

describe('calculerDevis', () => {
  test('petite commande : les frais de port sont facturés', () => {
    const d = calculerDevis([{ ref: 'GOURDE', quantite: 1 }], catalogue);
    expect(d.produits).toBe(24);
    expect(d.port).toBe({{FRAIS}});
    expect(d.total).toBe({{TOTAL_PETITE}});
  });

  test('grande commande : le port est offert', () => {
    const d = calculerDevis([{ ref: 'TENTE', quantite: 1 }], catalogue);
    expect(d).toMatchObject({ produits: 120, port: 0, total: 120 });
  });

  test('un article inconnu est refusé', () => {
    expect(() => calculerDevis([{ ref: 'PIOLET', quantite: 1 }], catalogue)).toThrow('Article inconnu');
  });

  test('une quantité nulle est refusée', () => {
    expect(() => calculerDevis([{ ref: 'CARTE', quantite: 0 }], catalogue)).toThrow('Quantité invalide');
  });

  test('un devis vide est refusé', () => {
    expect(() => calculerDevis([], catalogue)).toThrow();
  });
{{COMPLICE_DEVIS}}});
