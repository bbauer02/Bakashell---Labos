# API de la boutique Cimes & Sentiers

Catalogue et devis de la boutique en ligne.

```sh
npm test          # tests unitaires (Jest)
npm start         # lance l'API sur le port 3000 (variable PORT pour en changer)
curl localhost:3000/health
curl "localhost:3000/devis?GOURDE-1L=3&TENTE-2P=1"
```

- `src/devis.js` : calcul des devis (règles du service commercial en tête du fichier) ;
- `tests/` : tests unitaires ;
- `deploiement/` : installation sur les serveurs Debian.
