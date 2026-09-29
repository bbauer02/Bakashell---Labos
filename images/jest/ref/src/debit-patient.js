const attendre = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Débit avec patience : jusqu'à 3 tentatives en cas d'erreur technique de la banque.
 * On attend 1 s avant la 2e tentative, puis 2 s avant la 3e. Après 3 échecs :
 * erreur « Service de paiement indisponible ».
 * banque.debiter(carte, montant) -> Promise<{ accepte, transaction?, motif? }>
 */
async function debiterPatiemment(banque, carte, montant) {
  const pauses = [1000, 2000];
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
