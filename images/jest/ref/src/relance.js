const DELAI_RELANCE_MS = 24 * 60 * 60 * 1000;

/**
 * Programme un e-mail de relance si le panier est toujours plein après le délai.
 * Retourne { annuler() } pour annuler la relance (par exemple si le client commande).
 */
function programmerRelance(panier, client, mailer, delai = DELAI_RELANCE_MS) {
  const minuteur = setTimeout(() => {
    if (!panier.estVide()) {
      mailer.envoyer(
        client.email,
        'Votre panier vous attend',
        `Vous avez ${panier.nombreArticles()} article(s) dans votre panier.`,
      );
    }
  }, delai);
  return { annuler: () => clearTimeout(minuteur) };
}

module.exports = { DELAI_RELANCE_MS, programmerRelance };
