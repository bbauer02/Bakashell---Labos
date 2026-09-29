// Import comptable : charge le fichier des écritures en mémoire (environ 70 Mo), puis l'intègre.
console.log('Import comptable : chargement du fichier des écritures…');
const blocs = [];
for (let i = 0; i < 14; i++) blocs.push(Buffer.alloc(5 * 1024 * 1024, i + 1));
console.log(`Import terminé : ${blocs.length * 5} Mo d'écritures intégrés`);
