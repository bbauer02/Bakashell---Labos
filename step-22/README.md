# Etape 22

## SSH et accès distant

SSH (Secure Shell) est le protocole standard pour se connecter à distance à une machine Linux de manière sécurisée. C'est l'outil quotidien de tout administrateur système.

### Se connecter en SSH

```shell
ssh utilisateur@adresse-ip
ssh utilisateur@nom-de-machine
ssh -p 2222 utilisateur@serveur    # Port personnalisé
```

Lors de la première connexion, SSH demande de vérifier l'empreinte du serveur. Cette empreinte est stockée dans `~/.ssh/known_hosts`.

### Authentification par clé

L'authentification par mot de passe est simple mais moins sécurisée. La méthode recommandée est l'**authentification par clé** :

#### 1. Générer une paire de clés

```shell
ssh-keygen -t ed25519 -C "mon-email@exemple.com"
```

Cela crée deux fichiers dans `~/.ssh/` :
  * `id_ed25519` — la clé **privée** (à ne JAMAIS partager)
  * `id_ed25519.pub` — la clé **publique** (à copier sur les serveurs)

>Astuce : `-t ed25519` utilise l'algorithme le plus moderne et sécurisé. Avant, on utilisait `-t rsa -b 4096`.

#### 2. Copier la clé sur un serveur

```shell
ssh-copy-id utilisateur@serveur
```

Ou manuellement :
```shell
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
```

La clé publique est ajoutée au fichier `~/.ssh/authorized_keys` du serveur. À la prochaine connexion, plus besoin de mot de passe !

### Transférer des fichiers

#### scp — copie sécurisée

```shell
# Local → Serveur
scp fichier.txt utilisateur@serveur:/chemin/destination/

# Serveur → Local
scp utilisateur@serveur:/chemin/fichier.txt ./

# Copier un dossier entier
scp -r dossier/ utilisateur@serveur:/chemin/
```

#### sftp — transfert interactif

```shell
sftp utilisateur@serveur
sftp> ls                    # Lister les fichiers distants
sftp> get fichier.txt       # Télécharger
sftp> put fichier.txt       # Uploader
sftp> quit
```

### Configuration SSH

Le fichier `~/.ssh/config` permet de créer des raccourcis :

```
Host mon-serveur
    HostName 192.168.1.100
    User admin
    Port 22
    IdentityFile ~/.ssh/id_ed25519
```

Ensuite : `ssh mon-serveur` suffit !

### Permissions du dossier .ssh

Les permissions sont **critiques** pour SSH :

```shell
chmod 700 ~/.ssh                  # Dossier
chmod 600 ~/.ssh/id_ed25519       # Clé privée
chmod 644 ~/.ssh/id_ed25519.pub   # Clé publique
chmod 600 ~/.ssh/authorized_keys  # Clés autorisées
chmod 644 ~/.ssh/known_hosts      # Serveurs connus
chmod 644 ~/.ssh/config           # Configuration
```

>A retenir : si les permissions sont trop ouvertes, SSH refusera de fonctionner ! C'est une mesure de sécurité.

### Exécuter une commande à distance

On peut exécuter une commande sans ouvrir de session interactive :

```shell
ssh utilisateur@serveur "df -h"
ssh utilisateur@serveur "cat /etc/hostname"
ssh utilisateur@serveur "tar -czf - /var/log" > logs.tar.gz
```

>A retenir : SSH est la porte d'entrée de l'administration distante. Clés > mots de passe. Protégez votre clé privée comme un mot de passe.

Vous êtes prêts pour [l'étape suivante](../step-23/)
