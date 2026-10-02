"""Mémo du parcours Réseau : une fiche par commande ou notion, débloquée par un exercice.

Les exemples visent volontairement un autre réseau (le magasin de Chamonix, 172.16.5.0/24) : une fiche rappelle une
syntaxe, elle ne donne jamais la réponse d'un exercice.
"""
from ..linux.memo import C

BASE, OBSERVE, CONFIG, TEST, ROUTE = ("Prise en main", "Observer", "Configurer", "Tester", "Routage")

CARDS = [
    C("invite", "L'invite", BASE, "Elle dit qui vous êtes, sur quelle machine et dans quel dossier ; # pour root, $ pour un compte ordinaire.",
      ["<compte>@<machine>:<dossier>$", "<compte>@<machine>:<dossier>#"],
      [("etudiant@console:~$", "la console, dossier personnel"), ("root@vitrine:~#", "administrateur de la machine vitrine")], ["R0.1"]),
    C("machines", "Changer de machine", BASE, "Un onglet par machine au-dessus du terminal ; ou, depuis la console, la commande connexion.",
      ["connexion <machine>", "connexion <machine> <commande>", "exit", "plan", "redemarrer <machine>"],
      [("connexion vitrine", "un terminal sur vitrine"), ("connexion vitrine ip a", "une seule commande, sans ouvrir de terminal"),
       ("exit", "refermer la session de la machine")], ["R0.1", "R0.4"]),
    C("fichiers", "ls, cat, echo", BASE, "Lister les fichiers, afficher un fichier, écrire un texte dans un fichier.",
      ["ls", "cat <fichier>", 'echo "<texte>" > <fichier>'],
      [("ls", "les fichiers du dossier courant"), ("cat notes.txt", "afficher un fichier"),
       ('echo "Camille" > prenom.txt', "crée le fichier, ou remplace son contenu")], ["R0.1", "R0.3"]),
    C("nano", "nano", BASE, "Éditeur de texte simple, dans le terminal ; ^ veut dire Ctrl.",
      ["nano <fichier>", "Ctrl+O, Entrée : enregistrer", "Ctrl+X : quitter"],
      [("nano notes.txt", "crée le fichier à l'enregistrement s'il n'existe pas")], ["R0.2"]),
    C("ip-a", "ip a", OBSERVE, "Les interfaces de la machine : état (UP / DOWN), adresse MAC (link/ether), adresses IP (inet).",
      ["ip a", "ip -br a", "ip a show dev <interface>"],
      [("ip a", "tout, en détail"), ("ip -br a", "une ligne par interface"), ("ip -4 a show dev eth0", "les adresses IPv4 de eth0")], ["R1.1"]),
    C("masque", "Masque et préfixe", OBSERVE, "Le masque sépare la partie réseau de la partie machine ; deux machines se parlent directement si elles sont sur le même réseau, chacune selon son propre masque.",
      ["<adresse>/<préfixe>", "/24 = 255.255.255.0 (256 adresses)", "/28 = 255.255.255.240 (16 adresses)"],
      [("172.16.5.70/24", "réseau 172.16.5.0 à 172.16.5.255"), ("172.16.5.70/28", "réseau 172.16.5.64 à 172.16.5.79 seulement")], ["R1.4"]),
    C("ping", "ping", TEST, "Envoie un message à une adresse et attend la réponse : le premier test à faire.",
      ["ping -c <nombre> <adresse>", "Destination Host Unreachable : sur mon réseau, personne ne répond", "Network is unreachable : pas sur mon réseau, et pas de route"],
      [("ping -c 3 172.16.5.20", "trois essais"), ("ping 172.16.5.20", "sans -c : Ctrl+C pour arrêter")], ["R1.2", "R1.3"]),
    C("ip-link", "ip link set", CONFIG, "Allume ou éteint une interface (sans toucher à ses adresses).",
      ["ip link set <interface> up", "ip link set <interface> down"],
      [("ip link set eth0 up", ""), ("ip -br link", "l'état de chaque interface")], ["R1.2"]),
    C("ip-addr", "ip addr add / del", CONFIG, "Ajoute ou retire une adresse IP sur une interface, avec son masque. Effet immédiat, perdu au redémarrage.",
      ["ip addr add <adresse>/<préfixe> dev <interface>", "ip addr del <adresse>/<préfixe> dev <interface>"],
      [("ip addr add 172.16.5.30/24 dev eth0", ""), ("ip addr del 172.16.5.30/28 dev eth0", "écrite exactement comme dans ip a")], ["R1.3", "R1.4", "R1.5"]),
    C("arp", "ip neigh / arping", TEST, "ARP : la correspondance entre une adresse IP et l'adresse MAC de la carte qui la porte.",
      ["ip neigh", "arping -c <nombre> -I <interface> <adresse>", "ip neigh flush dev <interface>"],
      [("ip neigh", "les voisins déjà connus"), ("arping -c 3 -I eth0 172.16.5.20", "deux MAC différentes : conflit d'adresses")], ["R1.5"]),
    C("interfaces", "/etc/network/interfaces", CONFIG, "La configuration réseau appliquée au démarrage (Debian) ; ifup / ifdown l'appliquent ou la retirent à la demande.",
      ["auto <interface>", "iface <interface> inet static | manual", "    address <adresse>", "    netmask <masque>", "ifup <interface> · ifdown <interface>"],
      [("auto eth0\niface eth0 inet static\n    address 172.16.5.30\n    netmask 255.255.255.0", "adresse fixe, activée au démarrage"),
       ("ifup eth0", "appliquer le fichier sans redémarrer")], ["R1.2", "R1.6"]),
    C("ip-route", "ip route", ROUTE, "La table de routage : les réseaux joignables directement, et la route par défaut (la passerelle).",
      ["ip route", "ip route add default via <passerelle>", "ip route replace default via <passerelle>", "ip route del default"],
      [("ip route", "default via … : la passerelle"), ("ip route add default via 172.16.5.254", ""),
       ("ip route replace default via 172.16.5.254", "remplace (ou ajoute) la route par défaut")], ["R2.1", "R2.2", "R2.4"]),
    C("ip-forward", "Routage du noyau", ROUTE, "Une machine Linux ne fait suivre les paquets d'une interface à l'autre que si net.ipv4.ip_forward vaut 1.",
      ["sysctl net.ipv4.ip_forward", "sysctl -w net.ipv4.ip_forward=1", "/etc/sysctl.conf : net.ipv4.ip_forward=1", "sysctl -p"],
      [("sysctl -w net.ipv4.ip_forward=1", "tout de suite (perdu au redémarrage)"), ("sysctl -p", "appliquer /etc/sysctl.conf")], ["R2.3", "R2.6"]),
    C("traceroute", "traceroute", TEST, "Le chemin vers une adresse : un routeur par ligne ; * * * là où le chemin se perd.",
      ["traceroute -n <adresse>"], [("traceroute -n 10.30.0.20", "-n : adresses sans recherche de nom")], ["R2.4"]),
    C("gateway", "gateway (interfaces)", ROUTE, "La passerelle permanente d'un poste Debian, déclarée avec son adresse.",
      ["iface eth0 inet static", "    address <adresse>", "    netmask <masque>", "    gateway <passerelle>"],
      [("    gateway 172.16.5.254", "dans la section iface de /etc/network/interfaces")], ["R2.5"]),
]
