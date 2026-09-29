# Boutique Cimes & Sentiers — code métier

- `src/` : modules métier (prix, panier, livraison, commande…)
- `tests/` : tests Jest (`*.test.js`)

Lancer les tests :

```bash
npx jest                 # toute la suite
npx jest tests/prix      # les fichiers dont le chemin correspond à « tests/prix »
npx jest -t "TVA"        # les tests dont le nom contient « TVA »
npx jest --watchAll      # relance toute la suite à chaque modification
npx jest --coverage      # avec la couverture de code
```
