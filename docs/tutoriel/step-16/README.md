# Etape 16

## Introduction au scripting Bash

Un script bash est un fichier texte contenant une suite de commandes qui s'exécutent automatiquement. C'est le premier pas vers l'automatisation !

### Créer un script

Un script bash commence toujours par le **shebang** qui indique quel interpréteur utiliser :

```bash
#!/bin/bash
echo "Mon premier script !"
```

Pour exécuter un script :
  1. Rendez-le exécutable : `chmod +x mon_script.sh`
  2. Lancez-le : `./mon_script.sh`

Ou directement : `bash mon_script.sh`

>Astuce : `#!/bin/bash` s'appelle le shebang. C'est toujours la première ligne d'un script.

### Les variables

```bash
#!/bin/bash
NOM="Linux"
VERSION=22
echo "Bienvenue sur $NOM version $VERSION"
echo "Votre dossier personnel est : $HOME"
```

On peut aussi récupérer le résultat d'une commande :

```bash
DATE=$(date)
NB_USERS=$(wc -l < /etc/passwd)
echo "Date : $DATE"
echo "Nombre d'utilisateurs : $NB_USERS"
```

>Astuce : pas d'espaces autour du `=` lors de l'affectation ! `NOM = "Linux"` ne fonctionnera pas.

### Les conditions (if)

```bash
#!/bin/bash
FICHIER="/etc/passwd"

if [ -f "$FICHIER" ]; then
    echo "Le fichier $FICHIER existe"
else
    echo "Le fichier $FICHIER n'existe pas"
fi
```

Tests courants :
  * `-f fichier` — le fichier existe
  * `-d dossier` — le dossier existe
  * `-z "$var"` — la variable est vide
  * `-n "$var"` — la variable n'est pas vide
  * `"$a" = "$b"` — les chaînes sont égales
  * `"$a" -eq "$b"` — les nombres sont égaux
  * `"$a" -gt "$b"` — a est supérieur à b
  * `"$a" -lt "$b"` — a est inférieur à b

>Attention : les espaces autour des crochets `[ ]` sont obligatoires !

### Les boucles

#### Boucle for

```bash
#!/bin/bash
# Parcourir une liste
for FRUIT in pomme banane cerise; do
    echo "J'aime les $FRUIT"
done

# Parcourir des fichiers
for FICHIER in /etc/*.conf; do
    echo "Fichier de config : $FICHIER"
done

# Boucle numérique
for i in $(seq 1 5); do
    echo "Itération $i"
done
```

#### Boucle while

```bash
#!/bin/bash
COMPTEUR=1
while [ $COMPTEUR -le 5 ]; do
    echo "Compteur : $COMPTEUR"
    COMPTEUR=$((COMPTEUR + 1))
done
```

### Les arguments

Un script peut recevoir des arguments :

```bash
#!/bin/bash
echo "Nom du script : $0"
echo "Premier argument : $1"
echo "Deuxième argument : $2"
echo "Nombre d'arguments : $#"
echo "Tous les arguments : $@"
```

Usage : `./mon_script.sh arg1 arg2`

>A retenir : le scripting bash est essentiel pour automatiser les tâches répétitives en administration système.

Vous êtes prêts pour [l'étape suivante](../step-17/)
