/**
 * Liste les lignes du panier dont le stock est insuffisant.
 * stockApi.quantiteDisponible(ref) renvoie une promesse du nombre d'articles en stock.
 */
async function verifierDisponibilite(panier, stockApi) {
  const manquants = [];
  for (const ligne of panier.lignes()) {
    const disponible = await stockApi.quantiteDisponible(ligne.ref);
    if (disponible < ligne.quantite) {
      manquants.push({ ref: ligne.ref, demande: ligne.quantite, disponible });
    }
  }
  return manquants;
}

module.exports = { verifierDisponibilite };
