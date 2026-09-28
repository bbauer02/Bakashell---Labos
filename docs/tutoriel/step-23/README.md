# Etape 23

## Gestion des logs

Les logs (journaux) sont les fichiers dans lesquels le système et les applications enregistrent leurs événements. Savoir les lire et les analyser est **la** compétence clé pour diagnostiquer un problème.

### Où sont les logs ?

Les logs système se trouvent dans `/var/log/` :

```shell
ls /var/log/
```

Fichiers importants :
  * `/var/log/syslog` ou `/var/log/messages` — logs système généraux
  * `/var/log/auth.log` — connexions, tentatives d'authentification
  * `/var/log/kern.log` — messages du noyau
  * `/var/log/dpkg.log` — historique des installations de paquets
  * `/var/log/apt/` — logs du gestionnaire de paquets
  * `/var/log/cron.log` — exécutions des tâches cron

Les applications ajoutent souvent leurs propres logs :
  * `/var/log/apache2/` — serveur web Apache
  * `/var/log/nginx/` — serveur web Nginx
  * `/var/log/mysql/` — base de données MySQL

### Lire les logs

#### Commandes essentielles

```shell
# Voir les dernières lignes
tail -20 /var/log/syslog

# Suivre en temps réel (très utile pour le debug !)
tail -f /var/log/syslog

# Suivre plusieurs fichiers
tail -f /var/log/syslog /var/log/auth.log

# Voir le début
head -50 /var/log/dpkg.log

# Afficher tout (attention aux gros fichiers)
less /var/log/syslog    # Navigation avec les flèches, q pour quitter
```

>Astuce : `tail -f` est votre meilleur ami pour le dépannage en temps réel. Ouvrez un terminal avec `tail -f` et reproduisez le problème dans un autre.

#### Filtrer les logs

```shell
# Chercher les erreurs
grep -i "error" /var/log/syslog

# Chercher les événements d'aujourd'hui
grep "Mar 30" /var/log/syslog

# Chercher les connexions échouées
grep "Failed" /var/log/auth.log

# Compter les occurrences d'erreur par type
grep -i "error" /var/log/syslog | awk '{print $5}' | sort | uniq -c | sort -rn

# Extraire les IP qui tentent des connexions SSH
grep "sshd" /var/log/auth.log | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | sort | uniq -c | sort -rn
```

### dmesg — messages du noyau

`dmesg` affiche les messages du noyau Linux (matériel, drivers, erreurs critiques) :

```shell
dmesg                       # Tous les messages
dmesg | tail -30            # Les plus récents
dmesg --level=err           # Uniquement les erreurs
dmesg -T                    # Avec horodatage lisible
dmesg | grep -i "usb"       # Messages liés à l'USB
dmesg | grep -i "error"     # Erreurs du noyau
```

### Rotation des logs

Les logs grossissent avec le temps. `logrotate` gère automatiquement :
  * La **rotation** (ancien log renommé, nouveau créé)
  * La **compression** des vieux logs
  * La **suppression** après un certain temps

Configuration : `/etc/logrotate.conf` et `/etc/logrotate.d/`

```shell
# Voir la configuration de rotation pour syslog
cat /etc/logrotate.d/rsyslog
```

Exemple de configuration :
```
/var/log/syslog {
    daily           # Rotation quotidienne
    rotate 7        # Garder 7 fichiers
    compress        # Compresser les anciens
    missingok       # Pas d'erreur si absent
    notifempty      # Ignorer si vide
}
```

### Créer ses propres logs

Dans un script, redirigez la sortie vers un fichier de log :

```bash
#!/bin/bash
LOG="/var/log/mon-script.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Début du script" >> $LOG
echo "$(date '+%Y-%m-%d %H:%M:%S') - Opération X terminée" >> $LOG
```

On peut aussi utiliser `logger` pour écrire dans syslog :

```shell
logger "Mon message de log"
logger -t mon-script "Sauvegarde terminée"
```

>A retenir : les logs sont votre boîte noire. Quand quelque chose ne marche pas, la réponse est presque toujours dans les logs.

Vous êtes prêts pour [l'étape suivante](../step-24/)
