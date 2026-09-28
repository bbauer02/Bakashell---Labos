const { Panier } = require('../src/panier');

// Tests écrits par Thomas : « ils passent chez moi ! »
const panier = new Panier();
const gourde = { ref: 'GOURDE-1L', libelle: 'Gourde 1 L', prixHT: 12.5 };
const lampe = { ref: 'FRONTALE', libelle: 'Lampe frontale', prixHT: 25 };

describe('Panier', () => {
  test('un panier neuf est vide', () => {
    expect(panier.estVide()).toBe(true);
  });

  test('on peut ajouter une gourde', () => {
    panier.ajouter(gourde, 2);
    expect(panier.nombreArticles()).toBe(2);
  });

  test('le total HT tient compte des quantités', () => {
    expect(panier.totalHT()).toBe(25);
  });

  test('on peut ajouter une lampe', () => {
    panier.ajouter(lampe);
    expect(panier.nombreArticles()).toBe(3);
    expect(panier.totalHT()).toBe(50);
  });

  test('on peut retirer la gourde', () => {
    panier.retirer('GOURDE-1L');
    expect(panier.lignes()).toHaveLength(1);
  });
});
