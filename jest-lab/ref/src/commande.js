const paiement = require('./services/paiement');
const mailer = require('./services/mailer');
const { calculerTTC } = require('./prix');

/** Débite la carte ; en cas d'erreur technique, une seule nouvelle tentative. */
async function debiterAvecReprise(carte, montant) {
  try {
    return await paiement.debiter(carte, montant);
  } catch (premiereErreur) {
    try {
      return await paiement.debiter(carte, montant);
    } catch (secondeErreur) {
      throw new Error('Service de paiement indisponible');
    }
  }
}

/**
 * Passe la commande : débit du montant TTC, puis e-mail de confirmation.
 * client = { email, carte }
 */
async function passerCommande(panier, client) {
  if (panier.estVide()) {
    throw new Error('Panier vide');
  }
  const montant = calculerTTC(panier.totalHT());
  const resultat = await debiterAvecReprise(client.carte, montant);
  if (!resultat.accepte) {
    throw new Error(`Paiement refusé : ${resultat.motif}`);
  }
  await mailer.envoyer(client.email, 'Confirmation de commande', `Montant débité : ${montant} €`);
  return { numero: resultat.transaction, montant };
}

module.exports = { passerCommande };
