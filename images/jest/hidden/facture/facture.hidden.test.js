// Tests cachés : comportement attendu de genererFacture
const { Panier } = require('../../src/panier');
const { genererFacture } = require('../../src/facture');

const panierDe = (prixHT, quantite = 1) =>
  new Panier().ajouter({ ref: 'SAC-40L', libelle: 'Sac à dos 40 L', prixHT }, quantite);

describe('genererFacture', () => {
  test('sans remise, en dessous du seuil, les frais de port sont facturés', () => {
    // 40 € HT -> 48 € TTC < 60 € -> port 8,90 € pour 2 kg en France
    expect(genererFacture(panierDe(40), { pays: 'FR', poidsKg: 2 })).toEqual({ produitsTTC: 48, port: 8.9, total: 56.9 });
  });

  test('au-dessus du seuil, la livraison est offerte', () => {
    // 50 € HT -> 60 € TTC -> port offert
    expect(genererFacture(panierDe(50), { pays: 'FR', poidsKg: 2 })).toEqual({ produitsTTC: 60, port: 0, total: 60 });
  });

  test('le seuil de livraison offerte est apprécié APRÈS remise (bug #218)', () => {
    // 55 € HT -> 66 € TTC -> -10 % = 59,40 € < 60 € -> le port reste dû
    expect(genererFacture(panierDe(55), { pays: 'FR', poidsKg: 2, remise: 10 })).toEqual({ produitsTTC: 59.4, port: 8.9, total: 68.3 });
  });

  test('une remise qui laisse le montant au-dessus du seuil garde la livraison offerte', () => {
    // 100 € HT -> 120 € TTC -> -20 % = 96 € -> offert en France
    expect(genererFacture(panierDe(100), { pays: 'FR', poidsKg: 6, remise: 20 })).toEqual({ produitsTTC: 96, port: 0, total: 96 });
  });

  test('hors de France, le seuil est de 100 € après remise', () => {
    // 90 € HT -> 108 € TTC -> -10 % = 97,20 € < 100 -> port Belgique 2 kg = 11,90 €
    expect(genererFacture(panierDe(90), { pays: 'BE', poidsKg: 2, remise: 10 })).toEqual({ produitsTTC: 97.2, port: 11.9, total: 109.1 });
  });

  test('les frais de port suivent le poids exact du colis (bug #219)', () => {
    // 40 € HT -> 48 € TTC < 60 € ; 4,6 kg -> tranche « moins de 5 kg » : 8,90 €
    expect(genererFacture(panierDe(40), { pays: 'FR', poidsKg: 4.6 })).toEqual({ produitsTTC: 48, port: 8.9, total: 56.9 });
    // 0,6 kg -> tranche « moins de 1 kg » : 4,90 €
    expect(genererFacture(panierDe(40), { pays: 'FR', poidsKg: 0.6 })).toEqual({ produitsTTC: 48, port: 4.9, total: 52.9 });
  });
});
