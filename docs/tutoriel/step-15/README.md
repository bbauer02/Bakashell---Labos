# Etape 15

## Filtrage et traitement de texte

Linux dispose d'outils puissants pour manipuler et transformer du texte. Ces outils, combinés avec les pipes, permettent de traiter des données efficacement.

### sort — trier les lignes

```shell
sort fichier.txt              # Tri alphabétique
sort -n fichier.txt           # Tri numérique
sort -r fichier.txt           # Tri inversé
sort -t: -k3 -n /etc/passwd   # Tri par le 3ème champ (séparateur :)
sort -u fichier.txt           # Tri + suppression des doublons
```

### uniq — supprimer les doublons

`uniq` ne détecte que les doublons **consécutifs**. Il faut donc trier avant :

```shell
sort fichier.txt | uniq       # Supprime les doublons
sort fichier.txt | uniq -c    # Compte les occurrences
sort fichier.txt | uniq -d    # Affiche seulement les doublons
```

### cut — découper les lignes

`cut` extrait des colonnes ou des champs d'un texte :

```shell
cut -d: -f1 /etc/passwd       # Extrait le 1er champ (séparateur :)
cut -d: -f1,3 /etc/passwd     # Extrait les champs 1 et 3
cut -c1-10 fichier.txt        # Extrait les caractères 1 à 10
```

### awk — traitement avancé

`awk` est un langage de traitement de texte très puissant. L'usage basique :

```shell
awk '{print $1}' fichier.txt           # Affiche la 1ère colonne
awk '{print $1, $3}' fichier.txt       # Affiche les colonnes 1 et 3
awk -F: '{print $1}' /etc/passwd       # Séparateur personnalisé
awk '$3 > 1000' /etc/passwd            # Filtre par condition
awk '{print NR, $0}' fichier.txt       # Numérote les lignes
```

>Astuce : `$0` = la ligne entière, `$1` = 1er champ, `$2` = 2ème champ, etc. `NR` = numéro de ligne

### tr — transformer les caractères

```shell
echo "HELLO" | tr 'A-Z' 'a-z'         # Convertit en minuscules
echo "hello" | tr 'a-z' 'A-Z'         # Convertit en majuscules
echo "hello   world" | tr -s ' '      # Supprime les espaces en double
cat fichier.txt | tr -d '\r'           # Supprime les retours chariot Windows
```

### Exemples pratiques combinés

```shell
# Lister les shells utilisés par les utilisateurs, triés par fréquence
cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn

# Trouver les 5 plus gros fichiers dans un dossier
ls -lS /var/log | head -6

# Extraire les noms d'utilisateurs ayant un UID > 1000
awk -F: '$3 >= 1000 {print $1}' /etc/passwd
```

>A retenir : la puissance de Linux vient de la combinaison de ces petits outils simples via les pipes.

Vous êtes prêts pour [l'étape suivante](../step-16/)
