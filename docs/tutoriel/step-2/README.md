# Etape 2

## Don't Panic, RTFM

Nous avions fini l'étape précédente avec la commande `ls`, qui permettait de lister les dossiers et fichiers du dossier courant. Mais est-ce que c'est vraiment la définition de la commande  `ls` ? Ne fonctionne-t-elle que comme cela ?

Pour le savoir, nous allons utiliser le grimoire indispensable à tous les sorciers de la ligne de commande : Le Manuel. Le Manuel contient la documentation relatives aux commandes disponibles sur votre système linux, si cette documentation existe. On l'invoque très simplement à l'aide de la commande `man <commande>`

Ici, nous souhaitons des renseignements sur `ls`, nous allons donc utiliser la commande `man ls`

Dans les résultats de cette commande, on identifie cette ligne : 
```shell
       ls [OPTION]... [FILE]...
```
Elle signifie que `ls` peut non seulement s'utiliser avec des options, mais aussi qu'elle peut avoir plusieurs arguments FILE. 
Quand on utilise `ls` seule, on applique `ls` au dossier courant, faute d'argument FILE. Mais on peut utiliser `ls` pour lister le contenu de dossiers distants. On peut par exemple écrire `ls /home`, ou `ls /home /usr`

>Astuce : `ls` seul correspond à la commande `ls .` Le symbole `.` cible le dossier courant

>A savoir : dans le Manuel, quand un paramètre est indiqué entre crochets ([PARAM]), c'est qu'il est optionnel

>A savoir : dans le Manuel, quand un paramètre est suivi de ..., c'est qu'on peut en passer plusieurs (ex. : [FILE]... indique que je peux passer plusieurs arguments FILE, ce qui me permet d'écrire `ls /home /usr`. Si le Manuel avait précisé [FILE] sans les ... ,  alors j'aurai du faire deux commandes : `ls /home` et `ls /usr`

>Point culture : RTFM == Read The Fucking Manuel, un acronyme classique sur les forums ou les channels d'aide linux quand un débutant pose une question dont la réponse est évidente dans le Manuel. En cas de doute, toujours consulter le Manuel puis Google avant de poser une question.

## Et la salade en option

Le Manuel pour `ls` indiquait qu'on pouvait lui passer des options. Les options sont un moyen de manipuler la commande qu'on utilise pour obtenir un résultat précis, ou pour réaliser une action spéciale.

Les options suivent toujours le format suivant `commande -option -option -option param `, ou parfois `commande -option1option2option3 param`.

Pour comprendre l'utilité des options, essayons quelques options de `ls` : 
  * `ls -l`
  * `ls -a`
  * `ls -la`
  * ...

Chaque option a son utilité (que je vous laisse chercher ;p ), qui est définie dans le Manuel. 

Les options sont très utiles, et sont souvent utilisées. Elles permettent parfois des changements majeurs dans le fonctionnement de la commande (par exemple les commande de `ping`, qui vont permettre d'envoyer des requêtes uniquement en IPv4 ou en IPv6, ou d'envoyer des types de requêtes particuliers)

>A retenir : les options vont souvent nous être utiles, il faut penser à lire le manuel pour savoir quelles options on peut utiliser avec chaque commande !

## Chacun sa route, chacun son chemin

On a vu qu'on pouvait utiliser `ls` sur des dossiers distants. Mais comment se réfère-t-on à ces dossiers ?

On passe par ce qu'on appelle un chemin : c'est une chaine de caractère qui identifie la position du dossier (le chemin à effectuer pour arriver au dossier). 

On trouve deux types de chemins : 
  * Les chemins absolus : ces chemins sont toujours vrais, peu importe l'endroit où on se situe dans le système. Ce sont des chemins qui partent de la racine (`/`), et donc qui peuvent être suivis de n'importe où pour arriver toujours au même résultat (on repart à chaque fois de `/`, du tout début, donc on suit toujours le même chemin complet, absolu)
  * Les chemins relatifs : ces chemins sont dépendants de notre emplacement dans le système. Ils omettent le début du chemin, qui est remplacé par l'emplacement actuel. Ils sont relatifs à l'emplacement au moment de la lecture du chemin.

Exemples : 
  * Absolus : /home/user, /usr/lib, /var/www, ...
  * Relatifs : step-1/README.md, ../dossier/fichier.txt, ...

Mettons que je sois dans le dossier `/home/user`, qui contient un dossier `Documents`. Je pourrais lister le contenu de `Documents` de deux manières : 
  * Absolue : `ls /home/user/Documents`
  * Relative : `ls Documents`
Mettons à présent que j'exécute la commande `cd /`, puis que je réessaie les deux commandes ci-dessus :
  * La commande avec le chemin absolu va-t-elle fonctionner ? Pourquoi ?
  * La commande avec le chemin relatif va-t-elle fonctionner ? Pourquoi ?

>Astuce : Le symbole `..` pointe vers le dossier précédent. `../..` pointe vers le dossier parent de mon dossier parent, `../../..` vers le dossier parent du dossier parent de mon dossier parent ...

>A retenir : les chemins absolus sont toujours vrais, mais volumineux/verbeux. Les chemins relatifs sont plus courts, mais laissent la possibilité d'une erreur suivant le contexte d'exécution.

Passez maintenant à [l'étape suivante](https://github.com/Nat-Faeeria/tuto-cli-linux/tree/master/step-3)

