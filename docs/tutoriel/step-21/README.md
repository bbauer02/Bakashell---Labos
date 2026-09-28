# Etape 21

## Expressions régulières

Les expressions régulières (ou **regex**) sont un langage de motifs permettant de décrire des chaînes de caractères. Elles sont utilisées dans `grep`, `sed`, `awk`, et dans la plupart des langages de programmation.

### Syntaxe de base

| Symbole | Signification | Exemple | Correspond à |
|---------|--------------|---------|--------------|
| `.` | N'importe quel caractère | `a.c` | abc, a1c, a-c |
| `^` | Début de ligne | `^Bonjour` | Lignes commençant par "Bonjour" |
| `$` | Fin de ligne | `fin$` | Lignes terminant par "fin" |
| `*` | 0 ou plus du précédent | `ab*c` | ac, abc, abbc, abbbc |
| `+` | 1 ou plus du précédent | `ab+c` | abc, abbc (pas ac) |
| `?` | 0 ou 1 du précédent | `colou?r` | color, colour |
| `\` | Échapper un caractère spécial | `\.` | Un point littéral |

>Attention : `+` et `?` nécessitent `grep -E` (extended regex) ou `egrep`

### Classes de caractères

| Syntaxe | Signification | Exemple |
|---------|--------------|---------|
| `[abc]` | a, b ou c | `[aeiou]` = une voyelle |
| `[a-z]` | Une minuscule | `[a-zA-Z]` = une lettre |
| `[0-9]` | Un chiffre | `[0-9]+` = un nombre |
| `[^abc]` | Tout sauf a, b, c | `[^0-9]` = pas un chiffre |

### Classes POSIX

| Classe | Équivalent | Signification |
|--------|-----------|---------------|
| `[:alpha:]` | `[a-zA-Z]` | Lettres |
| `[:digit:]` | `[0-9]` | Chiffres |
| `[:alnum:]` | `[a-zA-Z0-9]` | Lettres et chiffres |
| `[:space:]` | espace, tab, etc. | Espaces blancs |
| `[:upper:]` | `[A-Z]` | Majuscules |
| `[:lower:]` | `[a-z]` | Minuscules |

### Utilisation avec grep

```shell
# Lignes commençant par un commentaire
grep '^#' /etc/hosts

# Lignes contenant une adresse IP (simplifiée)
grep -E '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' /etc/hosts

# Lignes vides
grep '^$' fichier.txt

# Lignes NON vides
grep -v '^$' fichier.txt

# Mots commençant par une majuscule
grep -E '\b[A-Z][a-z]+' fichier.txt

# Lignes contenant "error" ou "warning" (insensible à la casse)
grep -iE '(error|warning)' log.txt
```

### Utilisation avec sed

```shell
# Supprimer les lignes vides
sed '/^$/d' fichier.txt

# Supprimer les commentaires (lignes commençant par #)
sed '/^#/d' fichier.txt

# Remplacer les adresses IP par [IP]
sed -E 's/[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[IP]/g' log.txt

# Extraire ce qui est entre guillemets
sed -E 's/.*"(.*)".*/\1/' fichier.txt
```

### Exemples pratiques

```shell
# Trouver les lignes contenant une adresse email
grep -E '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' fichier.txt

# Valider un format de date JJ/MM/AAAA
grep -E '^[0-3][0-9]/[01][0-9]/[0-9]{4}$' dates.txt

# Trouver les fichiers de log contenant des erreurs numérotées
grep -E 'error[[:space:]]+[0-9]+' /var/log/*.log
```

>A retenir : les regex sont un outil transversal. Maîtriser les bases (`.`, `^`, `$`, `[]`, `*`, `+`) couvre 90% des besoins quotidiens.

Vous êtes prêts pour [l'étape suivante](../step-22/)
