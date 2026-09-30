// API de la boutique Cimes & Sentiers : catalogue et devis.
// Aucune dépendance npm : uniquement les modules intégrés de Node.js (18 ou plus récent).
'use strict';
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { calculerDevis } = require('./src/devis');
const produits = require('./produits.json');
const { version } = require('./package.json');

const PORT = Number(process.env.PORT || 3000);
// Sur les serveurs de production : dossier des données (commandes, stock) et dossier des journaux d'accès.
// Sans ces variables (poste de développement, conteneur), l'API fonctionne sans données ni journal.
const DONNEES = process.env.API_DATA;
const JOURNAUX = process.env.API_JOURNAUX;

function journaliser(ligne) {
  if (JOURNAUX) fs.appendFileSync(path.join(JOURNAUX, 'acces.log'), `${new Date().toISOString()} ${ligne}\n`);
}

/** Au démarrage : les données doivent être lisibles, l'état et le journal doivent pouvoir être écrits. */
function verifierEnvironnement() {
  if (DONNEES) {
    for (const fichier of ['commandes.json', 'stock.json']) {
      JSON.parse(fs.readFileSync(path.join(DONNEES, fichier), 'utf8'));
    }
    const etat = { version, pid: process.pid, demarrage: new Date().toISOString() };
    fs.writeFileSync(path.join(DONNEES, 'etat.json'), `${JSON.stringify(etat)}\n`);
  }
  journaliser(`démarrage de l'API v${version}`);
}

function repondre(res, code, corps) {
  res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(corps));
}

/** /devis?SAC-40L=1&GOURDE-1L=3 : une ligne par référence, la valeur est la quantité. */
function devis(url, res) {
  const lignes = [...url.searchParams].map(([ref, q]) => ({ ref, quantite: Number(q) }));
  try {
    return repondre(res, 200, calculerDevis(lignes, produits));
  } catch (e) {
    return repondre(res, 400, { erreur: e.message });
  }
}

const serveur = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const chemin = url.pathname.replace(/^\/api(?=\/)/, '');
  journaliser(`${req.method} ${req.url}`);
  if (chemin === '/health') {
    return repondre(res, 200, { statut: 'ok', version, hote: os.hostname(), utilisateur: os.userInfo().username });
  }
  if (chemin === '/produits') return repondre(res, 200, produits);
  if (chemin === '/devis') return devis(url, res);
  return repondre(res, 404, { erreur: 'Ressource introuvable' });
});

try {
  verifierEnvironnement();
} catch (e) {
  console.error(`Démarrage impossible : ${e.message}`);
  process.exit(1);
}
serveur.on('error', (e) => {
  console.error(`Le port ${PORT} n'est pas disponible : ${e.code}`);
  process.exit(1);
});
serveur.listen(PORT, () => console.log(`API boutique v${version} à l'écoute sur le port ${PORT}`));
process.on('SIGTERM', () => serveur.close(() => process.exit(0)));
