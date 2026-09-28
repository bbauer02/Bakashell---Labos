# Etape 10

## Redirections et Pipes

Vous avez déjà vu `>` et `>>` à l'étape 3. Allons plus loin avec les redirections et découvrons le concept de **pipe**, un des mécanismes les plus puissants de Linux.

### Rappel des redirections

  * `>` — redirige la sortie standard (stdout) vers un fichier, en écrasant le contenu
  * `>>` — redirige la sortie standard vers un fichier, en ajoutant à la fin

### Redirection des erreurs

Chaque programme a trois flux :
  * **stdin** (entrée standard) — flux 0
  * **stdout** (sortie standard) — flux 1
  * **stderr** (sortie d'erreur) — flux 2

On peut rediriger les erreurs séparément :
  * `commande 2> erreurs.txt` — redirige les erreurs dans un fichier
  * `commande > sortie.txt 2> erreurs.txt` — sépare sortie et erreurs
  * `commande > tout.txt 2>&1` — combine sortie et erreurs dans un seul fichier
  * `commande 2>/dev/null` — supprime les erreurs (les envoie dans le "trou noir")

>/dev/null est un fichier spécial qui détruit tout ce qu'on y écrit. Très pratique pour ignorer les erreurs ou la sortie d'une commande.

### Le pipe |

Le **pipe** (`|`) connecte la sortie d'une commande à l'entrée de la suivante. C'est comme une tuyauterie :

```shell
commande1 | commande2 | commande3
```

La sortie de `commande1` devient l'entrée de `commande2`, dont la sortie devient l'entrée de `commande3`.

Exemples pratiques :
  * `ls -l /etc | head -20` — affiche les 20 premières lignes du listing de /etc
  * `cat /etc/passwd | grep "bash"` — filtre les utilisateurs utilisant bash
  * `ps aux | grep "sleep"` — cherche un processus spécifique
  * `cat fichier.txt | sort` — trie les lignes alphabétiquement
  * `cat fichier.txt | sort | uniq` — trie et supprime les doublons
  * `ls /etc | wc -l` — compte le nombre de fichiers dans /etc

### La commande tee

`tee` est une commande spéciale : elle lit l'entrée standard, l'écrit dans un fichier ET l'affiche aussi en sortie standard. C'est un "T" dans la tuyauterie :

```shell
ls -l /etc | tee listing.txt | head -5
```

Cette commande liste /etc, sauvegarde le résultat dans `listing.txt`, et affiche les 5 premières lignes.

### Commandes utiles avec les pipes

  * `sort` — trie les lignes
  * `uniq` — supprime les doublons consécutifs (utiliser après sort)
  * `head -n N` — affiche les N premières lignes
  * `tail -n N` — affiche les N dernières lignes
  * `cut -d: -f1` — découpe les lignes (ici par ":" et prend le 1er champ)
  * `tr 'a-z' 'A-Z'` — transforme les caractères (ici minuscules en majuscules)

>Astuce : on peut enchaîner autant de pipes qu'on veut. C'est la philosophie Unix : des outils simples qui font une chose bien, combinés ensemble.

Vous êtes prêts pour [l'étape suivante](../step-11/)
