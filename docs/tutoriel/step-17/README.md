# Etape 17

## Tâches planifiées avec cron

`cron` est le planificateur de tâches de Linux. Il permet d'exécuter automatiquement des commandes ou des scripts à des moments précis.

### Le démon cron

`cron` est un service (démon) qui tourne en permanence en arrière-plan. Chaque minute, il vérifie s'il y a des tâches à exécuter.

Pour vérifier si cron est actif : `service cron status`

### La crontab

Chaque utilisateur a sa propre **crontab** (cron table), un fichier contenant ses tâches planifiées.

```shell
crontab -l          # Lister les tâches planifiées
crontab -e          # Éditer la crontab
crontab -r          # Supprimer toute la crontab
```

### Syntaxe cron

Chaque ligne de la crontab suit ce format :

```
┌───────────── minute (0-59)
│ ┌───────────── heure (0-23)
│ │ ┌───────────── jour du mois (1-31)
│ │ │ ┌───────────── mois (1-12)
│ │ │ │ ┌───────────── jour de la semaine (0-7, 0 et 7 = dimanche)
│ │ │ │ │
* * * * * commande à exécuter
```

Exemples :
  * `0 8 * * * /home/user/backup.sh` — chaque jour à 8h00
  * `*/15 * * * * /home/user/check.sh` — toutes les 15 minutes
  * `0 0 * * 0 /home/user/weekly.sh` — chaque dimanche à minuit
  * `30 6 1 * * /home/user/monthly.sh` — le 1er de chaque mois à 6h30
  * `0 */2 * * * /home/user/bihourly.sh` — toutes les 2 heures

Caractères spéciaux :
  * `*` — toutes les valeurs
  * `*/n` — toutes les n unités
  * `1,15` — valeurs 1 et 15
  * `1-5` — de 1 à 5

### Les dossiers cron du système

En plus des crontabs utilisateur, le système a des dossiers prédéfinis :

```shell
/etc/cron.d/        # Tâches système personnalisées
/etc/cron.daily/    # Scripts exécutés chaque jour
/etc/cron.hourly/   # Scripts exécutés chaque heure
/etc/cron.weekly/   # Scripts exécutés chaque semaine
/etc/cron.monthly/  # Scripts exécutés chaque mois
```

Il suffit de placer un script exécutable dans un de ces dossiers pour qu'il soit lancé automatiquement.

### Bonnes pratiques

  * Toujours rediriger la sortie : `0 8 * * * /home/user/script.sh > /var/log/script.log 2>&1`
  * Utiliser des chemins absolus dans les scripts cron (le PATH est minimal)
  * Tester le script manuellement avant de le planifier
  * Utiliser `crontab -l` pour vérifier ses tâches

>A retenir : cron est indispensable pour les sauvegardes automatiques, la surveillance, le nettoyage de fichiers temporaires, etc.

Vous êtes prêts pour [l'étape suivante](../step-18/)
