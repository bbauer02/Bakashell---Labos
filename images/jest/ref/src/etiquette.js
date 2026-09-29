const PAYS = {
  FR: 'FRANCE',
  BE: 'BELGIQUE',
  LU: 'LUXEMBOURG',
  DE: 'ALLEMAGNE',
  ES: 'ESPAGNE',
  IT: 'ITALIE',
  NL: 'PAYS-BAS',
};

/**
 * Étiquette collée sur le colis (norme du transporteur) :
 * nom en majuscules, adresse, code postal et ville en majuscules, pays EN TOUTES LETTRES
 * et en majuscules, puis le nombre total d'ARTICLES du colis (pas le nombre de lignes du panier).
 */
function etiquette(panier, client) {
  return [
    client.nom.toUpperCase(),
    client.adresse,
    `${client.codePostal} ${client.ville.toUpperCase()}`,
    PAYS[client.pays],
    `Articles : ${panier.nombreArticles()}`,
  ].join('\n');
}

module.exports = { etiquette };
