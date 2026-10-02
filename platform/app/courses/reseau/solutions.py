"""Corrigé du parcours Réseau : un script par module, exécuté en tant qu'« etudiant » sur la console par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Les commandes passent par « connexion <machine> <commande> » ; en cours, on ouvre plutôt un terminal sur la machine.
"""

SOLUTIONS = {
    1: r'''
#@ R1.1
#? Sur la caisse, `ip a` affiche un bloc par interface. `lo` est la boucle locale (la machine elle-même) : la carte branchée au switch est `eth0`.
#? Dans son bloc, l'adresse MAC suit `link/ether` et l'adresse IP suit `inet`. Le plan donne l'adresse prévue ; seule la machine dit l'adresse réelle.
connexion caisse ip a
mkdir -p ~/reponses
ip=$(connexion caisse ip -4 -o addr show dev eth0 | awk '{print $4}' | cut -d/ -f1)
mac=$(connexion caisse ip -o link show dev eth0 | grep -o 'link/ether [0-9a-f:]*' | cut -d' ' -f2)
printf '%s\n%s\n' "$ip" "$mac" > ~/reponses/caisse.txt
#@ R1.2
#? Depuis la caisse, `ping 192.168.10.50` répond « Destination Host Unreachable » : l'adresse est bien sur le réseau, mais personne ne répond.
#? Sur l'imprimante, `ip a` montre `eth0` en `state DOWN`, sans adresse : son fichier `/etc/network/interfaces` décrit la bonne adresse, mais sans la ligne `auto eth0`, rien ne l'applique au démarrage.
#? `ifup eth0` applique la configuration du fichier : l'interface s'allume et reçoit son adresse. `ip link set eth0 up` seul ne suffisait pas : l'interface aurait été allumée, mais toujours sans adresse.
connexion imprimante ifup eth0
connexion caisse ping -c 3 192.168.10.50
#@ R1.3
#? Une adresse s'ajoute à une interface avec son masque : sans `/24`, `ip` suppose `/32`, une adresse seule sur son réseau, qui ne voit aucune voisine.
#? Le réglage est immédiat, mais il ne vit qu'en mémoire : il disparaîtra au prochain redémarrage (ticket R1.6).
connexion bureau ip addr add 192.168.10.12/24 dev eth0
connexion bureau ping -c 3 192.168.10.11
#@ R1.4
#? L'adresse de la borne était bonne, pas son masque : en /28 (255.255.255.240), son réseau ne va que de .16 à .31. La caisse (.11) est donc « ailleurs », et la borne ne sait pas où l'envoyer : « Network is unreachable ».
#? Ajouter la bonne adresse ne suffit pas : l'interface porterait les deux. On retire la mauvaise, écrite exactement comme elle apparaît dans `ip a`, puis on ajoute la bonne.
connexion borne ip addr del 192.168.10.30/28 dev eth0
connexion borne ip addr add 192.168.10.30/24 dev eth0
connexion borne ping -c 3 192.168.10.11
#@ R1.5
#? Le portable de Julien avait pris 192.168.10.11, l'adresse de la caisse. Les deux répondent aux requêtes ARP « qui a 192.168.10.11 ? » : chaque poste envoie ses messages à celle qui a répondu en dernier, d'où une caisse qui ne répond « qu'une fois sur deux ».
#? `arping -I eth0 192.168.10.11` (depuis le bureau) montrait deux adresses MAC différentes pour la même IP : c'est la signature d'un conflit.
#? Le portable reprend l'adresse qui lui est réservée dans le plan. Dans un vrai réseau, un serveur DHCP éviterait ces erreurs de saisie : ce sera pour un prochain module.
connexion portable-julien ip addr del 192.168.10.11/24 dev eth0
connexion portable-julien ip addr add 192.168.10.40/24 dev eth0
connexion portable-julien ping -c 3 192.168.10.11
#@ R1.6
#? `ip addr add` ne modifie que la configuration en cours. Au démarrage, Debian applique `/etc/network/interfaces` : `auto eth0` active l'interface, `inet static` lui donne une adresse fixe.
#? Le seul test qui prouve quelque chose est un vrai redémarrage : `redemarrer bureau`, puis `ip a`.
connexion bureau 'cat > /etc/network/interfaces' <<'EOF'
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address 192.168.10.12
    netmask 255.255.255.0
EOF
redemarrer bureau
connexion bureau ip a
''',
}
