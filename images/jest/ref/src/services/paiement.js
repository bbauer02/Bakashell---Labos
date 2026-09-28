/**
 * Client de la banque. En production, appelle l'API de paiement.
 * debiter(carte, montant) -> Promise<{ accepte: boolean, transaction?: string, motif?: string }>
 */
async function debiter(carte, montant) {
  throw new Error(`Appel réseau interdit : la banque ne doit jamais être appelée depuis les tests (débit de ${montant} €)`);
}

module.exports = { debiter };
