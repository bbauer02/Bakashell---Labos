const PLAFOND = {{FID_PLAFOND}};
const BONUS_ANNIVERSAIRE = {{FID_BONUS}};

/** Les dates 'AAAA-MM-JJ' sont interprétées en UTC : on compare donc les mois UTC (quel que soit le fuseau). */
function estMoisAnniversaire(anniversaire, dateAchat) {
  return new Date(anniversaire).getUTCMonth() === new Date(dateAchat).getUTCMonth();
}

/**
 * Points de fidélité gagnés pour un achat : 1 point par euro entier dépensé ; statut gold : ×{{FID_GOLD}},
 * silver : ×1,5 (arrondi à l'inférieur) ; +{{FID_BONUS}} points le mois de l'anniversaire ; au plus {{FID_PLAFOND}} points.
 * client = { statut: 'standard' | 'silver' | 'gold', anniversaire?: 'AAAA-MM-JJ', dateAchat: 'AAAA-MM-JJ' }
 */
function pointsFidelite(montantTTC, client) {
  if (montantTTC <= 0) {
    return 0;
  }
  let points = Math.floor(montantTTC);
  if (client.statut === 'gold') {
    points *= {{FID_GOLD}};
  } else if (client.statut === 'silver') {
    points = Math.floor(points * 1.5);
  }
  if (client.anniversaire && estMoisAnniversaire(client.anniversaire, client.dateAchat)) {
    points += BONUS_ANNIVERSAIRE;
  }
  if (points > PLAFOND) {
    points = PLAFOND;
  }
  return points;
}

module.exports = { pointsFidelite };
