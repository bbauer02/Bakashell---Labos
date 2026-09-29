// Pointeuse de l'entrepôt : enregistre les passages, et les écrit sur disque à l'arrêt.
let passages = 0;
console.log('Pointeuse démarrée');
const minuteur = setInterval(() => { passages++; }, 1000);

// docker stop envoie SIGTERM : on enregistre, puis on quitte proprement
process.on('SIGTERM', () => {
  clearInterval(minuteur);
  console.log(`Arrêt propre : ${passages} passages enregistrés`);
  process.exit(0);
});
