# Etape 5

## Les utilisateurs spéciaux

### Est-ce un avion ? Est-ce un oiseau ? Non, c'est superutilisateur

Il existe un utilisateur qui a tous les droits dans un système linux : `root`, le superutilisateur. 

`root` est tout puissant. Donc très dangereux, car de grand pouvoirs impliquent de grandes responsabilités.

### Créer un sidekick

On peut emprunter les pouvoir de `root` temporairement, pour une ou plusieurs commandes.

Il suffit de préfixer sa commande par la commande `sudo` (par exemple : `sudo mkdir truc`)

On ne peut utiliser `sudo` que si on fait partie du groupe `sudo` (et on devient un sudoer)

>Astuce : `sudo` == Superuser Do, Do as Superuser, exécuter en tant que superutilisateur

### Usurpation d'identité

On peut aussi devenir `root`. Ou devenir n'importe qui (sans faire n'importe quoi). 

Pour cela, il faut utiliser la commande `su`. `su` tout court permet de devenir le superutilisateur (si on connait son mot de passe).

On peut aussi utiliser `su <utilisateur>` pour devenir un autre utilisateur du système (mais toujours en connaissant son mot de passe, sinon ça ne marche pas)

Lorsqu'on est `root`, la ligne de commande change : 

```shell
root@machine:/home/user#
```

L'utilisateur est `root`, et le `$` de fin devient un `#`.

## Les processus

On peut lister tous les processus en cours sur le système en utilisant la commande `top`. Les processus et leur identifiant (PID) apparaissent alors, ainsi que leur consommation en mémoire et processeur.

On peut arrêter un processus avec la commande `kill <PID>`, ou en appuyant sur la touche `k` dans top, puis en tapant le PID du processus ciblé, et puis en tapant `kill`.

Vous pouvez passer à [l'étape suivante](https://github.com/Nat-Faeeria/tuto-cli-linux/tree/master/step-6)
