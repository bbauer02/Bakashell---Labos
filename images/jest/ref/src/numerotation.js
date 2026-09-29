// Compteur partagé par toute l'application : il vit aussi longtemps que le module.
let dernier = 0;

/** Numéro de la commande suivante : CMD-0001, CMD-0002… */
function prochainNumero() {
  dernier += 1;
  return `CMD-${String(dernier).padStart(4, '0')}`;
}

module.exports = { prochainNumero };
