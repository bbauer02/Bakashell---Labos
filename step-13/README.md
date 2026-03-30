# Etape 13

## Réseau de base

Un administrateur système doit savoir diagnostiquer les problèmes réseau et vérifier la configuration réseau d'une machine Linux.

### Informations réseau de la machine

La commande `ip` (remplaçante de l'ancienne commande `ifconfig`) permet d'afficher et configurer les interfaces réseau :

```shell
ip a                    # Affiche toutes les interfaces et adresses IP
ip addr show            # Identique à ip a
ip link show            # Affiche l'état des interfaces (up/down)
ip route show           # Affiche la table de routage
```

Autres commandes utiles :
  * `hostname` — affiche le nom de la machine
  * `hostname -I` — affiche l'adresse IP de la machine (sans les détails)
  * `cat /etc/hostname` — le fichier contenant le nom de la machine
  * `cat /etc/hosts` — le fichier de résolution locale (association nom ↔ IP)

### Tester la connectivité

La commande `ping` envoie des paquets ICMP pour vérifier qu'une machine est accessible :

```shell
ping google.com         # Ping continu (Ctrl+C pour arrêter)
ping -c 4 google.com    # Envoie 4 pings seulement
ping -c 2 8.8.8.8       # Ping l'IP directement (DNS Google)
```

>Astuce : si `ping nom-de-domaine` échoue mais `ping IP` fonctionne, c'est probablement un problème DNS

### Ports et connexions

Pour voir les ports ouverts et les connexions réseau :

```shell
ss -tuln                # Affiche les ports en écoute (TCP et UDP)
ss -tunap               # Avec les noms de processus
netstat -tuln           # Ancienne commande (similaire à ss)
```

Options de `ss` :
  * `-t` — TCP
  * `-u` — UDP
  * `-l` — ports en écoute (listening)
  * `-n` — affiche les numéros de port au lieu des noms
  * `-p` — affiche le processus associé

### Télécharger et communiquer

`curl` est un outil puissant pour communiquer avec des serveurs web :

```shell
curl http://example.com                 # Affiche le contenu de la page
curl -o fichier.html http://example.com # Sauvegarde dans un fichier
curl -I http://example.com              # Affiche seulement les en-têtes HTTP
curl -s http://example.com              # Mode silencieux (pas de barre de progression)
```

>Astuce : `curl` est l'outil indispensable pour tester des API et des services web depuis le terminal

### Le fichier /etc/hosts

Ce fichier permet de définir des résolutions DNS locales :

```
127.0.0.1   localhost
127.0.1.1   ma-machine
192.168.1.10 serveur-web
```

Quand vous accédez à "serveur-web", le système vérifie d'abord `/etc/hosts` avant de consulter un serveur DNS.

Vous êtes prêts pour [l'étape suivante](../step-14/)
