const { calculerTTC, arrondir } = require('./prix');

const euros = (montant) => `${montant.toFixed(2).replace('.', ',')} €`;

/**
 * Récapitulatif envoyé au client avant le paiement (texte brut).
 * Une ligne par produit, dans l'ordre du panier, avec son prix TTC ; puis la livraison
 * (« offerte » quand le port vaut 0) et le total TTC.
 */
function recapitulatif(panier, { pays, port }) {
  const lignes = panier.lignes().map((l) => `${l.quantite} × ${l.libelle} : ${euros(calculerTTC(l.prixHT * l.quantite))}`);
  const produits = calculerTTC(panier.totalHT());
  return [
    'Votre commande Cimes & Sentiers',
    ...lignes,
    `Livraison (${pays}) : ${port === 0 ? 'offerte' : euros(port)}`,
    `Total TTC : ${euros(arrondir(produits + port))}`,
  ].join('\n');
}

module.exports = { recapitulatif };
