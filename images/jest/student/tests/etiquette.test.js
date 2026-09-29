const { Panier } = require('../src/panier');
const { etiquette } = require('../src/etiquette');

// Test écrit par Thomas : « j'ai figé l'étiquette dans un snapshot, comme ça plus de régression ! »
const gourde = { ref: 'GOURDE-1L', libelle: 'Gourde 1 L', prixHT: 12.5 };
const lampe = { ref: 'FRONTALE', libelle: 'Lampe frontale', prixHT: 25 };
const client = { nom: 'Chloé Dubois', adresse: '8 avenue Louise', codePostal: '1050', ville: 'Bruxelles', pays: 'BE' };

test("étiquette d'un colis pour la Belgique", () => {
  const panier = new Panier().ajouter(gourde, 3).ajouter(lampe);
  expect(etiquette(panier, client)).toMatchSnapshot();
});
