# Etape 3

## Création

Placez-vous dans le dossier `/home/<votre user>`. Nous allons apprendre à créer des dossiers et des fichiers.

Pour créer un dossier, on utilise la commande `mkdir` : `mkdir dossier-inutile`

Pour créer un fichier, on utilise la commande `touch` : `cd dossier-inutile && touch fichier-inutile.txt`

>Astuce : Le symbole `&&` permet d'enchainer plusieurs commandes à la suite
>Astuce : `mkdir` == MaKe Directory

## Ecriture

C'est bien d'avoir créé un fichier, encore faut-il pouvoir écrire dedans. On a deux moyens pour le faire : 
  * Utiliser un éditeur de texte en ligne de commande, comme `vi`, `vim`, `emacs` ou `nano`
  * Coller du texte directement en contenu de fichier ou en fin de fichier en redirigeant la sortie d'une commande vers le fichier

### Editeurs de texte

Les éditeurs de texte en ligne de commande sont plus ou moins puissants selon l'éditeur, et sont à l'origine de nombreuses guerres et controverses pour savoir lequel est le plus efficace.

`vim` est souvent cité comme le plus puissant et le plus utilisé, mais les défenseurs d'`emacs` ne sont pas d'accord. 

Tout le monde est plutôt d'accord pour dire que `nano` n'est "pas un vrai éditeur de texte" ou "est pour les noobs". Cependant, tout le monde utilise `nano` assez souvent parce qu'il est simple et efficace, même s'il n'est pas très développé.

On utilise ces commandes de la façon suivant `editeur-de-texte fichier`. Par exemple : `nano fichier-inutile.txt`. On entre ensuite dans l'éditeur de texte. Il faudra apprendre les raccourcis claviers permettant de sauvegarder du texte, de fermer l'éditeur, etc.

### Redirection de flux

La commande `echo` permet d'afficher du texte dans la ligne de commande. Essayez par exemple `echo "Hello World ! "`

En fait, la chaine de caractère "Hello World ! " est passée à la commande `echo`, qui l'écrit dans la sortie standard (stdout)

On peut récupérer le flux de la commande `echo`, et le rediriger vers le fichier dans lequel on veut écrire quelquechose. Pour ce faire, on utilise le symbole `>`

Essayez `echo "Inutile" > fichier-inutile.txt`, puis affichez le contenu du fichier à l'aide de la commande `cat` : `cat fichier-inutile.txt`

Le flux de la commande `echo` a bien été redirigé vers le fichier pour remplacer son contenu ! 

Il existe aussi le symbole `>>`. Ce symbole fonctionne comme `>`, mais écrit le flux à la fin du fichier au lieu de remplacer tout le contenu.

Essayez `echo "Ajout" >> fichier-inutile.txt && cat fichier-inutile.txt`, puis `echo "Remplacement du contenu" > fichier-inutile.txt && cat fichier-inutile.txt`

Comprenez vous la différence entre `>` et `>>` ?

>A retenir : `echo` écrit du texte dans un flux, qui peut être redirigé

>A retenir : `cat` affiche le contenu d'un fichier

>A retenir : `>` détourne un flux et remplace le contenu de sa cible par ce flux

>A retenir : `>>` détourne un flux et l'écrit à la suite du contenu de sa cible

## Démultiplication

On veut faire des modifications à notre fichier `fichier-inutile.txt`. Dans le doute, on décide de d'abord en faire une copie.

On utilise la commande `¢p` : `cp fichier-inutile.txt copie-fichier-inutile.txt`

On veut aussi faire une copie de `dossier-inutile`. Il faut utiliser `cp`, mais avec une option particulière ... laquelle ? (`man cp`)

## Mon nom est Personne

On trouve que le nom `copie-fichier-inutile.txt` est trop long. On décide de renommer ce fichier en `cp-fi.txt`.

On utilise la commande `mv` : `mv copie-fichier-inutile.txt cp-fi.txt`

La commande `mv` sert en fait à déplacer des fichiers ou des dossiers. Lors du déplacement, on peut les renommer. Comme il n'existe pas de commande rename, on renomme un fichier ou un dossier en le déplaçant à son emplacement actuel, mais en changeant son nom ^^

Créez un dossier `backup` dans `/home/user`, et déplacez-y `cp-fi.txt`

## Destruction

Le fichier que nous avons créé est inutile. Le dossier aussi, comme le nom l'indique. Nous allons donc les supprimer, pour nettoyer un peu.

Pour supprimer un fichier, on utilise la commande `rm` : `rm fichier-inutile.txt`

Pour supprimer un dossier, on a deux choix : 
  * Le dossier est vide : on utilise la commande `rmdir` : `rmdir dossier-inutile`
  * Le dossier a du contenu : si on utilise `rmdir`, on va obtenir une erreur. Il faut utiliser la commande `rm` avec l'option `R` : `rm -R dossier-inutile`

>Pourquoi l'option `R` ? A vous de chercher ... ;)

Vous êtes prêts à passer à [l'étape suivante](https://github.com/Nat-Faeeria/tuto-cli-linux/tree/master/step-4)
