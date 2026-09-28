# Etape 18

## Surveillance du système

Un administrateur doit pouvoir vérifier rapidement l'état de santé d'un système : espace disque, mémoire, charge processeur, temps de fonctionnement.

### Espace disque

```shell
df -h               # Affiche l'espace disque de toutes les partitions (-h = human readable)
df -h /             # Espace disque de la partition racine
df -h /home         # Espace disque de /home
```

`du` (Disk Usage) montre l'espace utilisé par les fichiers et dossiers :

```shell
du -h /var/log              # Taille de chaque sous-dossier
du -sh /var/log             # Taille totale (-s = summary)
du -sh /home/*              # Taille de chaque dossier utilisateur
du -h --max-depth=1 /       # Taille des dossiers au premier niveau
```

>Astuce : `df` montre l'espace des partitions, `du` montre l'espace des fichiers/dossiers

### Mémoire

```shell
free -h             # Affiche la mémoire RAM et swap (-h = human readable)
free -m             # En mégaoctets
```

Colonnes importantes :
  * **total** — mémoire totale
  * **used** — mémoire utilisée
  * **free** — mémoire libre
  * **available** — mémoire disponible (inclut les caches récupérables)

### Charge système et uptime

```shell
uptime              # Depuis quand le système est allumé + charge moyenne
```

Résultat typique : `10:30:00 up 5 days, 3:45, 2 users, load average: 0.15, 0.10, 0.05`

Les 3 nombres de **load average** représentent la charge moyenne sur 1, 5 et 15 minutes.

>Astuce : sur un système avec 4 cœurs, un load average de 4.0 signifie que les cœurs sont utilisés à 100%

### Processus et ressources

```shell
top                 # Vue en temps réel (quitter avec q)
ps aux              # Snapshot de tous les processus
ps aux --sort=-%mem # Triés par consommation mémoire
ps aux --sort=-%cpu # Triés par consommation CPU
```

Dans `top`, raccourcis utiles :
  * `q` — quitter
  * `M` — trier par mémoire
  * `P` — trier par CPU
  * `k` — tuer un processus

### Logs système

```shell
dmesg                       # Messages du noyau (démarrage, matériel)
dmesg | tail -20            # Les 20 derniers messages
cat /var/log/syslog         # Logs système généraux
tail -f /var/log/syslog     # Suivre les logs en temps réel
```

>Astuce : `tail -f` est très utile pour surveiller un fichier de log en direct. `Ctrl+C` pour arrêter.

### Résumé des commandes

| Commande | Information |
|----------|-------------|
| `df -h` | Espace disque |
| `du -sh` | Taille d'un dossier |
| `free -h` | Mémoire RAM |
| `uptime` | Durée + charge |
| `top` | Processus en temps réel |
| `dmesg` | Messages noyau |

Vous êtes prêts pour [l'étape suivante](../step-19/)
