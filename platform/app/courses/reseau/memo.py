"""Mémo du parcours Réseau : une fiche par commande ou notion, débloquée par un exercice.

Les exemples visent volontairement un autre réseau (le magasin de Chamonix, 172.16.5.0/24) : une fiche rappelle une
syntaxe, elle ne donne jamais la réponse d'un exercice.
"""
from ..linux.memo import C

OBSERVE, CONFIG, TEST = ("Observer", "Configurer", "Tester")

CARDS = [
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
]
