/**
 * Envoi d'e-mails. En production, passe par le serveur SMTP.
 * envoyer(destinataire, sujet, corps) -> Promise<void>
 */
async function envoyer(destinataire, sujet, corps) {
  throw new Error(`Appel réseau interdit : aucun e-mail ne doit partir depuis les tests (${destinataire})`);
}

module.exports = { envoyer };
