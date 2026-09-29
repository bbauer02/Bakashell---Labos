const PLAFOND = 1000;
const BONUS_ANNIVERSAIRE = 100;

/** Les dates 'AAAA-MM-JJ' sont interprétées en UTC : on compare donc les mois UTC (quel que soit le fuseau). */
function estMoisAnniversaire(anniversaire, dateAchat) {
  return new Date(anniversaire).getUTCMonth() === new Date(dateAchat).getUTCMonth();
}

/**
 * Points de fidélité gagnés pour un achat.
 * client = { statut: 'standard' | 'silver' | 'gold', anniversaire?: 'AAAA-MM-JJ', dateAchat: 'AAAA-MM-JJ' }
 */
function pointsFidelite(montantTTC, client) {
  if (montantTTC <= 0) {
    return 0;
  }
  let points = Math.floor(montantTTC);
  if (client.statut === 'gold') {
    points *= 2;
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
