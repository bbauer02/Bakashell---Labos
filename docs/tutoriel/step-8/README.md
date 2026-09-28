# Etape 8

## Monter un système de fichiers

On rentre dans les trucs tricky ! 

Quand vous branchez une clé usb ou un autre périphérique à votre ordinateur, ce périphérique se retrouve sous forme de fichier dans /dev.

Les disques durs, par exemple, sont généralement listés en /dev/sdX (sda, sdb, etc. Chaque partition se retrouve aussi : /dev/sda1, /dev/sda2, etc.)

Si votre périphérique contient un système de fichiers, vous aimeriez y avoir accès. Il va donc falloir monter ce périphérique, c'est à dire donner accès au système de fichiers dans un dossier de votre système.

Généralement, le système monte automatiquement les périphériques. Mais parfois ça ne fonctionne pas ... 

  * Branchez une clé usb à votre système. Vérifiez qu'elle est bien apparue dans `/dev` (listez `/dev` avant et après avoir inséré la clé)
  * Trouvez quel est le fichier de `/dev` correspondant à votre clé
  * Créez un dossier accessible dans `/media` ou `/mnt`
  * Utilisez la commande `mount <chemin de `/dev`> <chemin de `/media`||`/mnt`>`
  * Listez le contenu du dossier que vous avez créé dans `/media`||`/mnt` : il devrait contenir le système de fichier de votre clé usb !

## Installer un nouveau système

Créez une nouvelle machine virtuelle et installez une version `16.04` d'Ubuntu. A l'installation, créez 3 partitions : 
  * une partition avec `/` comme point de montage
  * une partition avec `/home` comme point de montage
  * une partition de swap

Créez quelques dossiers et fichiers dans votre dossier personnel.

Une fois que vous avez fini, essayez d'installer une version `17.10` d'Ubuntu sur la même machine. Lors du partitionnement, n'effacez pas le disque, mais précisez que vous voulez faire les choses de manière custom.

Précisez que vous souhaitez installer le système sur la partition qui a `/` comme point de montage, en effaçant les données. Précisez aussi que vous utiliserez la partition avec `/home` comme point de montage comme partition avec `/home` comme point de montage, mais n'effacez PAS les données ! 

Une fois l'installation terminée, relancez le système. Vous devriez vous connecter à un système `17.10` et ... vos données du `/home` de la version `16.04` seront toujours là ! :D

Voilà, c'est la fin de ce tutoriel pour le moment ;) A bientôt pour de prochains updates !

