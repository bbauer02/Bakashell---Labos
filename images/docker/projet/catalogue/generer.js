// Génère le site du catalogue (dossier dist/) à partir de produits.json.
// À exécuter avec Node : node generer.js
const fs = require('fs');
const produits = require('./produits.json');

const lignes = produits
  .map((p) => `      <tr><td>${p.ref}</td><td>${p.libelle}</td><td>${p.prixHT.toFixed(2)} € HT</td></tr>`)
  .join('\n');

const page = `<!doctype html>
<html lang="fr">
  <head><meta charset="utf-8"><title>Catalogue Cimes &amp; Sentiers</title></head>
  <body>
    <h1>Catalogue Cimes &amp; Sentiers</h1>
    <table>
${lignes}
    </table>
    <p><small>Page générée par generer.js le ${new Date().toISOString()}</small></p>
  </body>
</html>
`;

fs.mkdirSync('dist', { recursive: true });
fs.writeFileSync('dist/index.html', page);
console.log(`dist/index.html : ${produits.length} produits`);
