# Etape 24

## Sécurité de base

La sécurité est une responsabilité fondamentale de l'administrateur système. Cette étape couvre les bonnes pratiques essentielles pour sécuriser un serveur Linux.

### Politique de mots de passe

Les mots de passe sont stockés de façon chiffrée dans `/etc/shadow` (et non dans `/etc/passwd` comme le nom le laisse penser).

```shell
# Voir la politique de mot de passe d'un utilisateur
chage -l utilisateur

# Forcer un changement de mot de passe à la prochaine connexion
chage -d 0 utilisateur

# Définir un âge maximum (90 jours)
chage -M 90 utilisateur

# Verrouiller un compte
passwd -l utilisateur

# Déverrouiller
passwd -u utilisateur
```

>A retenir : ne jamais stocker de mots de passe en clair dans des fichiers ou des scripts !

### Permissions sensibles

Certains fichiers nécessitent des permissions strictes :

```shell
# Fichiers critiques du système
chmod 644 /etc/passwd       # Lisible par tous (pas de mots de passe dedans)
chmod 640 /etc/shadow        # Lisible uniquement par root et le groupe shadow
chmod 600 ~/.ssh/id_*        # Clés SSH privées
chmod 700 ~/.ssh             # Dossier SSH
```

#### Le bit SUID et SGID

  * **SUID** (Set User ID) : un programme s'exécute avec les droits de son propriétaire
  * **SGID** (Set Group ID) : un programme s'exécute avec les droits de son groupe

```shell
# Trouver les fichiers SUID (potentiel risque de sécurité)
find / -perm -4000 -type f 2>/dev/null

# Trouver les fichiers SGID
find / -perm -2000 -type f 2>/dev/null

# Trouver les fichiers world-writable (modifiables par tous)
find / -perm -o+w -type f 2>/dev/null
```

>Astuce : les fichiers SUID sont des cibles privilégiées pour les attaquants. Auditez-les régulièrement.

### Pare-feu avec UFW

UFW (Uncomplicated Firewall) est l'interface simplifiée d'`iptables` :

```shell
# Statut du pare-feu
ufw status

# Activer/désactiver
ufw enable
ufw disable

# Règles de base
ufw default deny incoming     # Bloquer tout en entrée par défaut
ufw default allow outgoing    # Autoriser tout en sortie

# Autoriser un port
ufw allow 22                  # SSH
ufw allow 80                  # HTTP
ufw allow 443                 # HTTPS
ufw allow 22/tcp              # Spécifier le protocole

# Autoriser depuis une IP spécifique
ufw allow from 192.168.1.0/24 to any port 22

# Bloquer une IP
ufw deny from 10.0.0.5

# Supprimer une règle
ufw delete allow 80

# Voir les règles numérotées
ufw status numbered
```

### Bonnes pratiques SSH

Fichier de configuration : `/etc/ssh/sshd_config`

```shell
# Désactiver la connexion root directe
PermitRootLogin no

# Utiliser uniquement l'authentification par clé
PasswordAuthentication no

# Changer le port par défaut (sécurité par obscurité)
Port 2222

# Limiter les utilisateurs autorisés
AllowUsers admin webmaster

# Timeout de session
ClientAliveInterval 300
ClientAliveCountMax 2
```

Après modification, redémarrer SSH : `systemctl restart sshd`

### Surveiller les tentatives d'intrusion

```shell
# Dernières connexions réussies
last

# Dernières tentatives de connexion échouées
lastb

# Tentatives SSH échouées
grep "Failed password" /var/log/auth.log | tail -20

# Compter les tentatives par IP
grep "Failed password" /var/log/auth.log | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | sort | uniq -c | sort -rn | head -10
```

### Auditer le système

```shell
# Vérifier les ports ouverts
ss -tuln

# Vérifier les processus en écoute
ss -tulnp

# Trouver les fichiers modifiés récemment (dernières 24h)
find /etc -mtime -1 -type f

# Vérifier les utilisateurs avec UID 0 (droits root)
awk -F: '$3 == 0 {print $1}' /etc/passwd

# Vérifier les comptes sans mot de passe
awk -F: '$2 == "" {print $1}' /etc/shadow
```

### Checklist de sécurité minimale

  1. Mots de passe forts + politique d'expiration
  2. SSH par clé uniquement, pas de root SSH
  3. Pare-feu activé, seuls les ports nécessaires ouverts
  4. Mises à jour régulières (`apt-get update && apt-get upgrade`)
  5. Permissions correctes sur les fichiers sensibles
  6. Surveillance des logs d'authentification
  7. Pas de services inutiles en écoute

>A retenir : la sécurité est un processus continu, pas un état. Auditez, mettez à jour, surveillez.

Félicitations, vous avez terminé le tutoriel complet ! 🎉
