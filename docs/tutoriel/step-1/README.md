# Etape 1

## Premiers pas en console

Bienvenue dans ce tutoriel ! 

Vous allez apprendre à utiliser l'interface en ligne de commande (ou CLI) de Linux, en commençant par la base et en finissant par des manipulations complexes. Bon voyage ! 

Tout d'abord, connectez-vous à votre système linux, puis ouvrez un terminal de commande (application Terminal, ou Ctrl+Alt+t avec Ubuntu ou Debian)
Un terminal apparait, et contient normalement une ligne comme celle-ci :

```shell
user@machine:~$
```

Cette ligne apparaîtra systématiquement au début de la zone d'entrée des commandes. Elle vous permet d'identifier rapidement avec quel utilisateur vous êtes connecté, sur quelle machine, et où vous vous situez.
Vous pouvez aussi récupérer ces informations avec les commandes `whoami` et `pwd`. Entrez ces commandes dans le terminal, et regardez le résultat.
`whoami` affiche qui vous êtes, `pwd` affiche le dossier courant. 

>Détail intéressant : sur la ligne, vous voyez apparaître ~, tandis que `pwd` affiche le chemin `/home/user`. C'est parce que ces deux chemins sont équivalents : le symbole `~` pointe vers le dossier personnel de l'utilisateur connecté. C'est un raccourci à retenir.

## Petite balade

Maintenant que vous savez qui vous êtes et où vous êtes, apprenons à nous déplacer.

Pour se déplacer de dossier en dossier, il faut utiliser la commande `cd`

Essayons cette commande tout de suite en nous déplaçant vers le dossier `/etc` : `cd /etc`

Le début de notre ligne a maintenant changé : 
```shell
user@machine:/etc$
```
Vous pouvez le vérifier avec la commande vue précedemment ... `pwd`

Déplacez vous maintenant vers le dossier /var, puis /usr. 

>Astuce : `cd` == Change Directory, ou Changer de Dossier

## Retour aux origines

Nous allons maintenant remonter à l'origine de tous les systèmes Unix : `/`

Il suffit d'un petit `cd /` et ... nous y voilà. Mais ça à l'air bien vide et inutile ... Il serait intéressant de voir ce qui se cache dans `/`

Nous allons donc lister les dossiers contenus dans `/` . On va pour cela utiliser la commande `ls`

Le résultat de cette commande est d'afficher tous les dossiers et fichiers contenus dans le dossier courant. On découvre ainsi : 
  * `/home`, le dossier contenant tous les dossiers personnels des utilisateurs
  * `/etc`, le dossier contenant les fichiers de configuration des programmes
  * `/root`, le dossier personnel du superutilisateur
  * `/usr`, qui contient tous les fichiers binaires (programmes) installés par l'utilisateur
  * `/opt`, qui sert à contenir les logiciels tiers (directement téléchargés par l'utilisateur)
  * `/proc`, qui contient des fichiers "temporaires" pendant l'exécution, relatifs à chacun des processus lancés par le système
  * `/dev`, qui contient les informations sur le matériel et les périphériques (devices)
  * ...

>Astuce : `ls` == Lister

Vous êtes prêts pour [l'étape suivante](https://github.com/Nat-Faeeria/tuto-cli-linux/tree/master/step-2)
