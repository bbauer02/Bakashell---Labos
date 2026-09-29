/** Tire au sort le gagnant du jeu-concours : chaque participant a exactement la même chance. */
function tirerGagnant(participants) {
  if (participants.length === 0) {
    throw new Error('Aucun participant');
  }
  return participants[Math.floor(Math.random() * participants.length)];
}

module.exports = { tirerGagnant };
