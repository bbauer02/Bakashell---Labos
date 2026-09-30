/**
 * Recherche de produits par mot-clé dans le libellé.
 * - la casse est ignorée, ainsi que les espaces autour du terme saisi ;
 * - un terme de moins de {{CAT_MIN}} caractères ne renvoie aucun résultat ;
 * - l'ORDRE des résultats n'est pas garanti : le futur moteur de recherche les classera à sa façon.
 */
function rechercher(produits, terme) {
  const t = String(terme).trim().toLowerCase();
  if (t.length < {{CAT_MIN}}) {
    return [];
  }
  return produits.filter((p) => p.libelle.toLowerCase().includes(t));
}

module.exports = { rechercher };
