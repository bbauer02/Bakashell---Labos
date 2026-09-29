// Export du catalogue pour les partenaires : node export.js --format texte|csv|json
const produits = require('./produits.json');

const i = process.argv.indexOf('--format');
const format = i === -1 ? undefined : process.argv[i + 1];

if (format === 'json') {
  console.log(JSON.stringify(produits, null, 2));
} else if (format === 'csv') {
  console.log('ref;libelle;prixHT');
  for (const p of produits) console.log(`${p.ref};${p.libelle};${p.prixHT.toFixed(2)}`);
} else if (format === 'texte') {
  console.log('Catalogue Cimes & Sentiers');
  for (const p of produits) console.log(`  ${p.ref.padEnd(10)} ${p.libelle.padEnd(28)} ${p.prixHT.toFixed(2).padStart(7)} € HT`);
} else {
  console.error('Usage : node export.js --format texte|csv|json');
  process.exit(2);
}
