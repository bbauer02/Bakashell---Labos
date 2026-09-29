/**
 * Ligne du fichier d'export pour le logiciel de comptabilité : « date;numéro;montant TTC ».
 * Le montant s'écrit avec une virgule et toujours deux décimales : 59,40 ou 60,00.
 * Module maintenu par un prestataire : ne pas le modifier nous-mêmes.
 */
function ligneComptable({ date, numero, montantTTC }) {
  return `${date};${numero};${montantTTC.toFixed(2).replace('.', ',')}`;
}

module.exports = { ligneComptable };
