// API de la boutique Cimes & Sentiers — aucune dépendance npm (modules Node intégrés uniquement)
const http = require('http');
const net = require('net');
const os = require('os');
const produits = require('./produits.json');

const PORT = Number(process.env.PORT || 3000);
const REDIS_HOST = process.env.REDIS_HOST;
const VERSION = process.env.APP_VERSION || '1.0';

/** Incrémente un compteur dans Redis (protocole RESP minimal). */
function incrementer(cle) {
  return new Promise((resolve, reject) => {
    const socket = net.createConnection({ host: REDIS_HOST, port: 6379 }, () => {
      socket.write(`*2\r\n$4\r\nINCR\r\n$${Buffer.byteLength(cle)}\r\n${cle}\r\n`);
    });
    socket.setTimeout(2000, () => {
      socket.destroy();
      reject(new Error(`Redis (${REDIS_HOST}) ne répond pas`));
    });
    socket.on('data', (donnees) => {
      socket.end();
      const reponse = donnees.toString();
      if (reponse.startsWith(':')) resolve(Number(reponse.slice(1)));
      else reject(new Error(reponse.trim()));
    });
    socket.on('error', (e) => reject(new Error(`Redis (${REDIS_HOST}) injoignable : ${e.code || e.message}`)));
  });
}

function repondre(res, code, corps) {
  res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(corps));
}

const serveur = http.createServer(async (req, res) => {
  const chemin = req.url.replace(/^\/api(?=\/)/, '');
  console.log(`${new Date().toISOString()} ${req.method} ${req.url}`);
  if (chemin === '/health') {
    return repondre(res, 200, { statut: 'ok', version: VERSION, hote: os.hostname(), utilisateur: os.userInfo().username });
  }
  if (chemin === '/produits') {
    return repondre(res, 200, produits);
  }
  if (chemin === '/visites') {
    if (!REDIS_HOST) return repondre(res, 503, { erreur: 'Variable REDIS_HOST non configurée' });
    try {
      return repondre(res, 200, { visites: await incrementer('visites') });
    } catch (e) {
      return repondre(res, 503, { erreur: e.message });
    }
  }
  return repondre(res, 404, { erreur: 'Ressource introuvable' });
});

serveur.listen(PORT, () => console.log(`API boutique v${VERSION} à l'écoute sur le port ${PORT}`));
process.on('SIGTERM', () => serveur.close(() => process.exit(0)));
