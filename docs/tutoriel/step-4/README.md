# Etape 4

## Les utilisateurs

On peut créer plusieurs utilisateurs sur un même système Linux. 

Lorsqu'on crée un utilisateur, un dossier personnel lui est automatiquement créé dans `/home`.

Pour créer un utilisateur, on utilise la commande `adduser <utilisateur>`

On peut aussi supprimer un utilisateur avec la commande `deluser <utilisateur>`. Mais si on utilise cette commande sans options, les fichiers de l'utilisateur supprimé ne sont pas détruits ! Il faudra utiliser l'option `--remove-home` pour supprimer son dossier personnel, ou `--remove-all-files` pour supprimer tous les fichiers dont il est le propriétaires (fichiers créés en dehors du dossier personnel par exemple)

Créez un utilisateur `peon`, puis vérifiez que son dossier personnel a été créé dans `/home`

Affichez le contenu du fichier `/etc/passwd`. Ce fichier liste tous les utilisateurs du système (et non pas leurs mots de passe, c'est un piège ! ). Vérifiez que le nouvel utilisateur y est.

>Astuce : quand on veut afficher le contenu d'un fichier long, on peut choisir de n'afficher que le début avec la commande `head`, ou que la fin avec la commande `tail`. On peut utiliser l'option `-n` avec ces deux commandes pour préciser le nombre de lignes à afficher. Par exemple, `tail -n20 f1.txt` affichera les 20 dernières lignes du fichier f1.txt

## Les groupes

Quand on crée un utilisateur, un groupe portant le même nom que cet utilisateur est automatiquement créé. On l'appelle le groupe nominal, ou groupe primaire.

Un groupe est un ensemble d'utilisateur/une liste d'utilisateur, tout simplement. Les groupes sont listés dans le fichier `/etc/group`.

Les groupes sont utiles pour la gestion des droits sur les fichiers ou dossiers : on peut donner des droits de lecture, écriture et exécution sur un fichier ou un dossier à un groupe, donc à un ensemble d'utilisateur. Par exemple, je vais donner accès au dossier `docs-administratifs` au groupe `administration`.

Voici les diverses opérations réalisables avec les groupes : 
  * Créer un groupe : `addgroup <groupe>`
  * Supprimer un groupe : `delgroup <groupe>` ou `deluser --group <groupe>`
  * Ajouter un utilisateur dans un groupe : `adduser <user> <group>`
  * Supprimer un utilisateur d'un groupe : `deluser <user> <group>`

## Gestion des droits

Vous vous souvenez de l'option `-l` de `ls` ? le résultat ressemblait à ça : 

```shell
drwxr-xr-x  4 user group   4096 févr. 15 00:33 Images
-rw-r--r--  1 user group   2406 févr. 15 00:34 lettre.txt
```
On distingue plusieurs parties/colonnes dans ces lignes. On va s'intéresser aux suivantes : 
  1. `d` ou `-` : indique si c'est un dossier ou un fichier
  2. `r`,`w`,`x` ou `-` 9 fois (3 groupes de 3 caractères) : ce sont les permissions (droits) du fichier/dossier
  4. L'utilisateur propriétaire du fichier
  5. Le groupe propriétaire du fichier

### Permissions en chaine de caractères
  
Les permissions sont aux nombre de 3 :
  * `r` pour readable, lecture/lisible
  * `w` pour writable, écriture
  * `x` pour executable

Pour un fichier : 
  * `r` signifie qu'on peut afficher son contenu (`cat` ou `nano` ou autre)
  * `w` signifie qu'on peut modifier son contenu (`nano`, `vim`, `>` ou autre)
  * `x` signifie que le fichier est exécutable (pour un programme ou un script par exemple)

Pour un dossier : 
  * `r` signifie qu'on peut `ls` le dossier
  * `w` signifie qu'on peut ajouter du contenu dans le dossier
  * `x` signifie qu'on peut `cd` dans le dossier (mais pas `ls`, sauf si `r` est activé)

Ces permissions sont organisées en 3 triades : 
  * La première triade correspond aux permissions pour l'utilisateur possédant le fichier/dossier
  * la deuxième triade correspond aux permissions pour le groupe possédant le fichier/dossier
  * la troisième triade correspond aux permissions pour tous les utilisateurs n'étant pas possesseurs du fichier et n'appartenant pas au groupe possesseur du fichier

Si on prend les permissions pour le dossier `Images` comme exemple, on distingue : 
  * la première triade `rwx`, qui signifie que l'utilisateur possédant le dossier a tous les droits sur ce dossier
  * la deuxième triade `r-x` qui signifie que les utilisateurs du groupe possédant le dossier n'ont que les droits de lecture et exécution sur ce dossier (ils peuvent `ls` et `cd` dans ce dossier, mais pas `mkdir`, `touch`, `cp` ou `mv` par exemple)
  * la troisième triad `r-x` qui signifie que tous les autres utilisateurs n'ont que les droits de lecture et exécution sur ce dossier
La chaine de permissions obtenue est donc `rwxr-xr-x`


### Permissions en octal

On peut aussi écrire les permissions sous forme de trois bits octaux : 
  * le `x` vaut 1
  * le `w` vaut 2
  * le `r` vaut 4

On va ensuite calculer la valeur de chaque bit de permission. En reprenant l'exemple d'`Images` : 
  * `rwx` == 4+2+1 == 7
  * `r-x` == 4+1 == 5 
  * `r-x` == 4+1 == 5

On obtient 3 bits de permissions : 755

Calculez les 3 bits de permissions pour les permissions suivantes : 
  * `r---w---x`
  * `rwxrwxrwx`
  * `rw-r-x-wx`

### Changer les permissions

Les permissions sont aussi appelées des modes, ou modes de permissions. 

Pour changer les permissions d'un fichier, on va donc utiliser la commande `chmod`.

On peut l'utiliser avec les modes chaînés ou octaux : 
  * En modes chaînés, on a quatre lettres-clés qui permettent de changer les modes : 
    ** `u` pour user
    ** `g` pour group
    ** `o` pour others
    ** `a` pour all
    On les utilise de la façon suivante : je souhaite avoir `r` pour l'utilisateur, `w` pour le groupe et `x` pour les autres : `chmod u=r,g=w,o=x fichier.txt`
    On peut utiliser : 
    ** `=` pour changer la valeur : si j'ai `rwxrwxrwx` et que je fais `chmod u=r`, j'obtiens `r--rwxrw`
    ** `+` pour rajouter une permission : si j'ai `r--rwxrwx` et que je fais `chmod u+w`, j'obtiens `rw-rwxrwx`
    ** `-` pour supprimer une permission : si j'ai `rw-rwxrwx` et que je fais `chmod g-wx,o-wx` j'obtiens `rw-r--r--`
  * En modes octaux : `chmod <valeur octale> <fichier>`. Par exemple, `chmod 421 fichier.txt` == `chmod u=r,g=w,o=x fichier.txt`

>Astuce : `chmod` == Change Modes

##  Expropriation

Il est intéressant de changer les droits, mais parfois on aimerait aussi changer le propriétaire ou le groupe propriétaire d'un fichier. 

Pour ce faire, on utilisera les commandes suivantes : 
  * `chown` pour changer de propriétaire
  * `chgrp` pour changer de groupe propriétaire

>Astuce : `chown` == Change Owner, changer de propriétaire

>Astuce : `chgrp` == Change Group, changer de groupe

Vous êtes prêts pour [l'étape suivante](https://github.com/Nat-Faeeria/tuto-cli-linux/tree/master/step-5)
