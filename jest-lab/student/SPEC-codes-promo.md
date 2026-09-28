# Spécification : validation des codes promo

Fonction : `validerCode(code, maintenant = new Date())` dans `src/codesPromo.js`.

Le catalogue des codes est dans `src/data/codes.js` :
`{ code, remise (en %), expire ('AAAA-MM-JJ', jour inclus), restants (utilisations restantes) }`.

## Résultat

- Code accepté : `{ valide: true, remise: <pourcentage> }` (par exemple `{ valide: true, remise: 10 }`)
- Code refusé : `{ valide: false, raison: '<RAISON>' }`

## Règles, dans cet ordre

1. **Saisie** : les espaces autour du code sont ignorés, et la casse aussi (`" rando10 "` équivaut à `"RANDO10"`).
2. **FORMAT** : après normalisation, le code doit contenir **4 à 10** caractères, uniquement des lettres
   majuscules A-Z et des chiffres. Sinon : raison `FORMAT`.
3. **INCONNU** : un code bien formé mais absent du catalogue.
4. **EXPIRE** : le code est valable **jusqu'au jour d'expiration inclus** (jusqu'à 23:59:59.999, heure locale) ;
   au-delà, raison `EXPIRE`.
5. **EPUISE** : un code sans utilisations restantes (`restants` à 0).

Un code à la fois expiré et épuisé est donc signalé `EXPIRE`.

## Date

`maintenant` permet de fixer la date de référence (indispensable pour des tests reproductibles).
Sans ce paramètre, la date du jour est utilisée.
