# Etape 14

## Archivage et compression

Archiver et compresser des fichiers est essentiel pour les sauvegardes, le transfert de données et la gestion de l'espace disque.

### La différence entre archivage et compression

  * **Archivage** : regrouper plusieurs fichiers/dossiers en un seul fichier (sans réduire la taille)
  * **Compression** : réduire la taille d'un fichier

En Linux, on fait souvent les deux en même temps avec `tar` + un algorithme de compression.

### tar — l'outil d'archivage

`tar` (Tape Archive) est l'outil standard pour créer des archives :

```shell
# Créer une archive
tar -cf archive.tar dossier/           # Crée une archive (sans compression)
tar -czf archive.tar.gz dossier/       # Crée une archive compressée (gzip)
tar -cjf archive.tar.bz2 dossier/      # Crée une archive compressée (bzip2)

# Lister le contenu d'une archive
tar -tf archive.tar.gz                  # Liste les fichiers de l'archive
tar -tzf archive.tar.gz                 # Liste avec décompression gzip

# Extraire une archive
tar -xf archive.tar                     # Extrait
tar -xzf archive.tar.gz                 # Extrait une archive gzip
tar -xjf archive.tar.bz2                # Extrait une archive bzip2
tar -xzf archive.tar.gz -C /destination # Extrait dans un dossier spécifique
```

Options essentielles :
  * `-c` — create (créer)
  * `-x` — extract (extraire)
  * `-t` — list (lister)
  * `-f` — file (spécifier le nom du fichier)
  * `-z` — gzip (compression)
  * `-j` — bzip2 (compression)
  * `-v` — verbose (afficher les détails)

>Astuce : les extensions .tar.gz (ou .tgz) et .tar.bz2 sont les plus courantes en Linux

### gzip et gunzip

`gzip` compresse un fichier individuel (et remplace l'original) :

```shell
gzip fichier.txt            # Crée fichier.txt.gz (supprime l'original)
gzip -k fichier.txt         # Garde l'original (-k = keep)
gunzip fichier.txt.gz       # Décompresse
gzip -l fichier.txt.gz      # Affiche les infos de compression
```

### zip et unzip

`zip` est le format universel (compatible Windows) :

```shell
zip archive.zip fichier1 fichier2       # Crée un zip
zip -r archive.zip dossier/             # Zip récursif d'un dossier
unzip archive.zip                        # Décompresse
unzip -l archive.zip                     # Liste le contenu
unzip archive.zip -d /destination        # Décompresse dans un dossier
```

>A retenir : `tar.gz` est le format standard Linux, `zip` pour l'échange avec Windows

Vous êtes prêts pour [l'étape suivante](../step-15/)
