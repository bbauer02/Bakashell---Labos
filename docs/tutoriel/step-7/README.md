# Etape 7

## Installation de programmes

Il y a plusieurs façons d'installer des programmes dans Linux : par programmes compilés ou par paquets.

Pour bien comprendre, un petit apparté avant d'expliciter chacune des façons : 

>Les fichiers dans Linux : dans Linux, tout est fichier. Votre disque dur est un fichier (dans /dev), qui contient un système de fichiers (arborescence de dossiers et de fichiers. Un dossier est un fichier, de type dossier. Un programme exécutable est un fichier exécutable. Installer quelque chose, c'est mettre les bons fichiers aux bons endroits, de façon à ce que les chemins soient justes, et rendre les bons fichiers exécutables.

### Installation de programme compilés

On peut installer un programme en téléchargeant sa version compilée sur le net, puis en le plaçant à un endroit accessible. On va utiliser un exemple pratique pour comprendre : 

  * Utilisez la commande `wget` pour télécharger la base de données mongodb : `wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu1604-3.6.2.tgz`
  * Dézippez l'archive récupérée : `tar -zxf mongodb-linux-x86_64-ubuntu1604-3.6.2.tgz`
  * Déplacez cette archive dans un endroit accessible : `sudo mv mongodb-linux-x86_64-ubuntu1604-3.6.2.tgz /opt/mongo`
  * Listez le contenu de `/opt/mongo`. Il y a un dossier bin : il contient les binaries (fichiers binaires compilés et exécutables) de la base de données. Vérifiez qu'ils soient exécutables
  * Créez un dossier `/data/db' (utilisez l'option `-p` pour le faire en une seule commande)
  * Ajoutez le chemin vers le programme `mongod` dans la liste des chemins vers les programmes du système : `PATH=$PATH:/opt/mongo/bin && export $PATH`
  * Essayez d'exécuter le programme `mongod` en tapant simplement son nom comme une commande

>Apparté - exécuter un programme : pour exécuter un programme, il suffit de taper son nom, comme une commande, à condition qu'il soit accessible ! Si je rentre le chemin absolu du programme (ex.: `/opt/mongo/bin/mongod`), il s'exécute. Si je suis dans le dossier où est le programme, je peux l'exécuter avec un chemin relatif (ex.: je suis dans /opt/mongo/bin, je tape la commande `./mongod`)

>Apparté - le PATH : pour pouvoir exécuter un programme de n'importe où dans le système, il faut que le chemin absolu vers ce programme soit référencé quelquepart. Il existe une variable d'environnement pour le système, nommée PATH, qui contient tous les chemins menant vers des programmes du système. Quand on ajoute un programme quelque part, il faut rajouter son chemin dans $PATH pour pouvoir le lancer de n'importe où. Pour écrire dans PATH, on utilise la commande `PATH=$PATH:<chemin` pour dire que PATH est égal à sa valeur précédente plus un nouveau chemin concaténé. Puis on exporte la variable PATH pour que les modifications soient prises en compte : `export $PATH`. 

Il y a d'autres moyens : télécharger des sources et les compiler soi-même, télécharger un programme avec un script d'installation qui place les éléments automatiquement aux bons endroits, etc.

### Installation de programmes par paquets

Les paquets sont un ensemble de fichiers et de scripts permettant l'installation d'un programme. Généralement un programme est dépendant de plusieurs paquets (des librairies), qui vont être partagés par tout le système.

L'installation par paquets peut se faire graphiquement avec le gestionnaire de paquets Synaptic, ou en ligne de commande avec d'autres gestionnaires de paquets.

Chaque "famille" de distribution linux à son type de paquets : 
  * Red Hat (et Fedora) ont le gestionnaire `yum`
  * Archlinux a `pacman`
  * Debian (et Ubuntu) ont le gestionnaire `apt` et les paquets en .deb
  * ...

Avec Debian ou Ubuntu, on peut utiliser le gestionnaire de paquets de base, `apt`, ou installer une surcouche plus simple, `aptitude`.


Pour installer un paquet avec `apt` : 
  * On commence par mettre à jour la liste des paquets : `apt-get update`
  * Puis on cherche le nom du paquet qu'on veut installer (pour apache par exemple : `apt-cache search apache`, dans la liste des réponses on trouvera le paquet `apache2`)
  * On demande l'installation du paquet `apt-get install <paquet>`

Et c'est bon ! On peut taper le nom de la commande, et le programme s'exécutera sans avoir besoin de plus de configurations ! 

Avec `apt`, on peut aussi mettre à jour les paquets, avec `apt-get upgrade`

Ou supprimer des paquets : 
  * `apt-get remove <paquet>` : supprime le paquet seul
  * `apt-get purge` : supprime le paquet et ses fichiers de configuration
  * `apt-get autoremove --purge` : supprime le paquet, les paquets dépendants non-utilisés par d'autres paquets et les fichiers de configuration

Vous pouvez passer à [l'étape suivante](https://github.com/Nat-Faeeria/tuto-cli-linux/tree/master/step-8)
