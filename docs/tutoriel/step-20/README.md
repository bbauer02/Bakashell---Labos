# Etape 20

## Liens symboliques et liens durs

Sous Linux, les fichiers sont identifiés en interne par un numéro appelé **inode**. Les noms de fichiers ne sont que des étiquettes qui pointent vers ces inodes. Il est possible de créer plusieurs étiquettes pour un même fichier : ce sont les **liens**.

### Le concept d'inode

Chaque fichier sur le disque est associé à un inode unique. L'inode stocke les métadonnées (permissions, propriétaire, taille, dates) et pointe vers les données sur le disque.

Pour voir l'inode d'un fichier : `ls -i fichier.txt`

```shell
$ ls -i fichier.txt
1234567 fichier.txt
```

### Liens durs (hard links)

Un lien dur est une seconde étiquette qui pointe vers le **même inode**. Les deux noms sont strictement équivalents : modifier l'un modifie l'autre.

```shell
ln fichier-original.txt lien-dur.txt
```

Caractéristiques :
  * Le fichier n'est supprimé que quand **tous** les liens durs sont supprimés
  * Même inode, même contenu, mêmes permissions
  * Ne peut **pas** traverser les systèmes de fichiers (partitions)
  * Ne peut **pas** pointer vers un dossier
  * `ls -l` montre le nombre de liens durs (2ème colonne)

```shell
$ ls -li
1234567 -rw-r--r-- 2 user user 100 mars 30 fichier-original.txt
1234567 -rw-r--r-- 2 user user 100 mars 30 lien-dur.txt
```

Le `2` indique qu'il y a 2 liens durs vers cet inode.

### Liens symboliques (symlinks)

Un lien symbolique est un **raccourci** qui pointe vers un chemin. C'est un fichier séparé qui contient le chemin vers sa cible.

```shell
ln -s /chemin/vers/cible lien-symbolique
```

Caractéristiques :
  * Fichier séparé avec son propre inode
  * Peut pointer vers un dossier
  * Peut traverser les systèmes de fichiers
  * Si la cible est supprimée, le lien devient **cassé** (dangling symlink)
  * `ls -l` affiche une flèche vers la cible

```shell
$ ls -l
lrwxrwxrwx 1 user user 15 mars 30 mon-lien -> /etc/hosts
```

Le `l` au début indique un lien symbolique.

### Exemples courants dans le système

Les liens symboliques sont omniprésents :

```shell
$ ls -l /usr/bin/python3
lrwxrwxrwx 1 root root 9 /usr/bin/python3 -> python3.8

$ ls -l /etc/alternatives/
# Tout ce dossier utilise des symlinks pour gérer les versions
```

### Comparer liens durs et symboliques

| | Lien dur | Lien symbolique |
|---|---------|-----------------|
| Commande | `ln` | `ln -s` |
| Inode | Même que la cible | Inode différent |
| Dossiers | Non | Oui |
| Cross-partition | Non | Oui |
| Cible supprimée | Données préservées | Lien cassé |
| Taille | Identique à la cible | Taille du chemin |

>A retenir : les liens symboliques sont les plus utilisés. On les crée avec `ln -s cible nom_du_lien`. Pensez à eux comme des raccourcis Windows, mais en plus puissant.

Vous êtes prêts pour [l'étape suivante](../step-21/)
