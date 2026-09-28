# Boutique Cimes & Sentiers — code métier

- `src/` : modules métier (prix, panier, livraison, commande…)
- `tests/` : tests Jest (`*.test.js`)

Lancer les tests :

```bash
npx jest                 # toute la suite
npx jest tests/prix      # un seul fichier
npx jest --watch         # relance à chaque modification
npx jest --coverage      # avec la couverture de code
```
