# Etape 12

## Variables d'environnement et configuration du shell

Les variables d'environnement sont des valeurs stockées en mémoire par le système, accessibles par tous les programmes. Elles configurent le comportement du shell et des applications.

### Afficher les variables

  * `env` ou `printenv` — affiche toutes les variables d'environnement
  * `echo $VARIABLE` — affiche la valeur d'une variable spécifique
  * `echo $HOME` — votre dossier personnel
  * `echo $USER` — votre nom d'utilisateur
  * `echo $PATH` — les chemins vers les programmes exécutables
  * `echo $SHELL` — votre shell actuel

>Astuce : le symbole `$` devant le nom permet d'accéder à la valeur de la variable

### Créer et modifier des variables

```shell
# Variable locale (disponible uniquement dans le shell courant)
MA_VARIABLE="Bonjour"
echo $MA_VARIABLE

# Variable d'environnement (disponible pour les processus enfants)
export MA_VARIABLE="Bonjour"
```

La différence est importante : sans `export`, la variable n'est pas transmise aux sous-processus (scripts lancés depuis le shell, par exemple).

Pour supprimer une variable : `unset MA_VARIABLE`

### Le PATH

Le `PATH` est la variable la plus importante pour un administrateur. Elle contient la liste des dossiers où le système cherche les programmes exécutables, séparés par `:`.

```shell
echo $PATH
# /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Ajouter un dossier au PATH
export PATH=$PATH:/mon/nouveau/chemin
```

>Astuce : quand vous tapez une commande (ex: `ls`), le système parcourt chaque dossier du PATH dans l'ordre jusqu'à trouver le programme

### Les alias

Un alias est un raccourci pour une commande longue :

```shell
alias ll='ls -la'
alias ..='cd ..'
alias update='apt-get update && apt-get upgrade'
```

Pour voir tous les alias : `alias`
Pour supprimer un alias : `unalias ll`

### Fichiers de configuration du shell

Les alias et variables définis dans le terminal sont perdus à la fermeture. Pour les rendre permanents, on les écrit dans des fichiers de configuration :

  * `~/.bashrc` — exécuté à chaque ouverture de terminal (bash)
  * `~/.bash_profile` ou `~/.profile` — exécuté à la connexion

```shell
# Ajouter un alias permanent
echo "alias ll='ls -la'" >> ~/.bashrc

# Recharger la configuration sans fermer le terminal
source ~/.bashrc
```

>A retenir : les modifications dans `.bashrc` ne prennent effet qu'après `source ~/.bashrc` ou à la prochaine ouverture de terminal

Vous êtes prêts pour [l'étape suivante](../step-13/)
