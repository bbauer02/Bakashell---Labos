const attendre = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Débit avec patience : jusqu'à 3 tentatives en cas d'erreur technique de la banque.
 * On attend {{ATT_P1_TXT}} avant la 2e tentative, puis {{ATT_P2_TXT}} avant la 3e. Après 3 échecs :
 * erreur « Service de paiement indisponible ».
 * banque.debiter(carte, montant) -> Promise<{ accepte, transaction?, motif? }>
 */
async function debiterPatiemment(banque, carte, montant) {
  const pauses = [{{ATT_P1}}, {{ATT_P2}}];
  for (let tentative = 0; ; tentative += 1) {
    try {
      return await banque.debiter(carte, montant);
    } catch (erreur) {
      if (tentative >= pauses.length) {
        throw new Error('Service de paiement indisponible');
      }
      await attendre(pauses[tentative]);
    }
  }
}

module.exports = { debiterPatiemment };
