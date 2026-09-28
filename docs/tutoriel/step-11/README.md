# Etape 11

## Édition de texte en terminal

Modifier un fichier de configuration est une tâche quotidienne pour un administrateur Linux. Il faut maîtriser au moins un éditeur de texte en ligne de commande.

### nano — l'éditeur simple

`nano` est l'éditeur le plus accessible pour les débutants. Il affiche les raccourcis en bas de l'écran.

```shell
nano fichier.txt
```

Raccourcis essentiels (le symbole `^` signifie la touche Ctrl) :
  * `Ctrl+O` — sauvegarder (Write Out)
  * `Ctrl+X` — quitter
  * `Ctrl+K` — couper la ligne
  * `Ctrl+U` — coller la ligne
  * `Ctrl+W` — rechercher
  * `Ctrl+G` — aide

>Astuce : pour sauvegarder et quitter rapidement : `Ctrl+O`, `Entrée`, `Ctrl+X`

### vim — l'éditeur puissant

`vim` est beaucoup plus puissant mais a une courbe d'apprentissage plus raide. Le concept clé : vim a des **modes**.

  * **Mode normal** : pour naviguer et exécuter des commandes (mode par défaut)
  * **Mode insertion** : pour taper du texte (appuyez sur `i` pour entrer)
  * **Mode commande** : pour sauvegarder, quitter, etc. (appuyez sur `:`)

```shell
vim fichier.txt
```

Commandes essentielles :
  * `i` — passer en mode insertion
  * `Echap` — revenir en mode normal
  * `:w` — sauvegarder
  * `:q` — quitter
  * `:wq` — sauvegarder et quitter
  * `:q!` — quitter sans sauvegarder
  * `dd` — supprimer une ligne (en mode normal)
  * `yy` — copier une ligne
  * `p` — coller

>Astuce : si vous êtes perdu dans vim, appuyez sur `Echap` plusieurs fois puis tapez `:q!` pour quitter sans rien casser

### sed — l'éditeur de flux

`sed` (Stream Editor) permet de modifier du texte sans ouvrir de fichier interactivement. Très utile dans les scripts :

```shell
sed 's/ancien/nouveau/' fichier.txt         # Remplace la 1ère occurrence par ligne
sed 's/ancien/nouveau/g' fichier.txt        # Remplace toutes les occurrences
sed -i 's/ancien/nouveau/g' fichier.txt     # Modifie le fichier directement (-i = in-place)
sed -n '5,10p' fichier.txt                  # Affiche les lignes 5 à 10
sed '/motif/d' fichier.txt                  # Supprime les lignes contenant le motif
```

>Astuce : sans `-i`, `sed` affiche le résultat sans modifier le fichier original. C'est plus sûr pour tester !

>A retenir : `nano` pour les modifications rapides, `vim` quand on veut être efficace, `sed` pour les modifications automatisées dans les scripts.

Vous êtes prêts pour [l'étape suivante](../step-12/)
