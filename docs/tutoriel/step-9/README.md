# Etape 9

## Recherche de fichiers et de contenu

Savoir retrouver un fichier ou une information dans un système Linux est une compétence fondamentale. On utilise principalement deux commandes : `find` pour chercher des fichiers, et `grep` pour chercher du contenu dans des fichiers.

### Chercher des fichiers avec find

La commande `find` permet de rechercher des fichiers et dossiers selon différents critères : nom, type, taille, date de modification, permissions, etc.

```shell
find <où chercher> <critères>
```

Exemples :
  * `find / -name "passwd"` — cherche un fichier nommé "passwd" dans tout le système
  * `find /home -name "*.txt"` — cherche tous les fichiers .txt dans /home
  * `find /var -type d -name "log"` — cherche un dossier nommé "log" dans /var
  * `find /home -type f -size +1M` — cherche les fichiers de plus de 1 Mo dans /home
  * `find /tmp -name "*.tmp" -mtime +7` — fichiers .tmp modifiés il y a plus de 7 jours

>Astuce : `-name` est sensible à la casse. Pour une recherche insensible, utilisez `-iname`

>Astuce : `-type f` cherche uniquement les fichiers, `-type d` uniquement les dossiers

### Chercher du contenu avec grep

La commande `grep` permet de chercher un motif (texte ou expression régulière) dans le contenu de fichiers.

```shell
grep <motif> <fichier(s)>
```

Exemples :
  * `grep "root" /etc/passwd` — cherche les lignes contenant "root" dans /etc/passwd
  * `grep -i "error" /var/log/syslog` — recherche insensible à la casse
  * `grep -r "TODO" /home/etudiant/` — recherche récursive dans un dossier
  * `grep -n "config" fichier.txt` — affiche les numéros de ligne
  * `grep -c "warning" fichier.log` — compte le nombre de lignes correspondantes

>Astuce : `-r` ou `-R` permet de chercher récursivement dans tous les fichiers d'un dossier

>Astuce : `-v` inverse la recherche (affiche les lignes qui ne contiennent PAS le motif)

### Compter avec wc

La commande `wc` (Word Count) permet de compter les lignes, mots et caractères :
  * `wc -l fichier.txt` — nombre de lignes
  * `wc -w fichier.txt` — nombre de mots
  * `wc -c fichier.txt` — nombre d'octets

On peut combiner `grep` et `wc` avec un pipe : `grep "error" log.txt | wc -l` compte le nombre de lignes contenant "error".

### Autres outils utiles

  * `which <commande>` — localise le binaire d'une commande
  * `locate <fichier>` — recherche rapide dans une base de données (plus rapide que find, mais nécessite `updatedb`)

Vous êtes prêts pour [l'étape suivante](../step-10/)
