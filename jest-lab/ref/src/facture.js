const { calculerTTC, appliquerRemise, arrondir } = require('./prix');
const { fraisLivraison, livraisonOfferte } = require('./livraison');

/**
 * Facture d'une commande.
 * Le seuil de livraison offerte s'apprécie sur le montant des produits APRÈS remise.
 */
function genererFacture(panier, { pays, poidsKg, remise = 0 }) {
  const totalTTC = calculerTTC(panier.totalHT());
  const produitsTTC = appliquerRemise(totalTTC, remise);
  const port = livraisonOfferte(produitsTTC, pays) ? 0 : fraisLivraison(poidsKg, pays);
  return { produitsTTC, port, total: arrondir(produitsTTC + port) };
}

module.exports = { genererFacture };
