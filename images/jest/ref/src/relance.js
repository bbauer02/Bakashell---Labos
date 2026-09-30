const DELAI_RELANCE_MS = {{RELANCE_H}} * 60 * 60 * 1000;

/**
 * Programme un e-mail de relance, envoyé une seule fois {{RELANCE_H}} h après l'abandon du panier (délai fixé
 * par le marketing), si le panier est toujours plein à ce moment-là.
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
