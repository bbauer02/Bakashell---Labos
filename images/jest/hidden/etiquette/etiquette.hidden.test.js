// Tests cachés : étiquette conforme à la norme du transporteur
const { Panier } = require('../../src/panier');
const { etiquette } = require('../../src/etiquette');

const gourde = { ref: 'GOURDE-1L', libelle: 'Gourde 1 L', prixHT: 12.5 };
const lampe = { ref: 'FRONTALE', libelle: 'Lampe frontale', prixHT: 25 };

test('étiquette complète pour les Pays-Bas', () => {
  const panier = new Panier().ajouter(gourde, 2).ajouter(lampe, 3);
  const client = { nom: 'Jan de Vries', adresse: 'Keizersgracht 12', codePostal: '1015 CJ', ville: 'Amsterdam', pays: 'NL' };
  expect(etiquette(panier, client)).toBe('JAN DE VRIES\nKeizersgracht 12\n1015 CJ AMSTERDAM\nPAYS-BAS\nArticles : 5');
});

test('étiquette pour la France, un seul article', () => {
  const panier = new Panier().ajouter(lampe);
  const client = { nom: 'Léa Martin', adresse: '3 rue des Cimes', codePostal: '38000', ville: 'Grenoble', pays: 'FR' };
  expect(etiquette(panier, client)).toBe('LÉA MARTIN\n3 rue des Cimes\n38000 GRENOBLE\nFRANCE\nArticles : 1');
});
