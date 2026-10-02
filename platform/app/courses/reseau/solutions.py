"""Corrigé du parcours Réseau : un script par module, exécuté en tant qu'« etudiant » sur la console par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Les commandes passent par « connexion <machine> <commande> » ; en cours, on ouvre plutôt un terminal sur la machine.
"""

SOLUTIONS = {
    1: r'''
#@ R0.1
#? Tout se joue sur la bonne machine : l'onglet poste1 (ou `connexion poste1`) ouvre un terminal dont l'invite devient `root@poste1`. Le même `echo` lancé sur la console aurait créé le fichier… sur la console.
#? `echo "texte" > fichier` crée le fichier (ou remplace son contenu) ; `cat` permet de vérifier.
connexion poste1 'echo "Camille" > /root/signature.txt'
connexion poste1 cat /root/signature.txt
#@ R0.2
#? En cours, on tape `nano ~/carnet.txt`, on écrit les lignes, puis Ctrl+O, Entrée (enregistrer) et Ctrl+X (quitter). Ce corrigé, lui, est un script : il écrit le fichier d'un coup.
cat > ~/carnet.txt <<'EOF'
plan : affiche le schéma du réseau
connexion <machine> : ouvre un terminal sur une machine (ou son onglet)
redemarrer <machine> : redémarre une machine, depuis la console
EOF
#@ R0.3
#? `ls` sur chaque machine montre les fichiers du dossier de root ; le message est sur l'une des deux, tirée au sort pour chaque étudiant. `cat` l'affiche.
#? La réponse s'écrit sur la console : l'invite doit être `etudiant@console`.
for m in poste1 poste2; do connexion $m ls; done
code=$(for m in poste1 poste2; do connexion $m 'cat /root/message-de-marc.txt 2>/dev/null'; done | grep -o 'MARC-[0-9]*' | head -n 1)
echo "$code" > ~/reponses/code.txt
#@ R0.4
#? `redemarrer` se lance sur la console : on éteint et rallume la machine « de l'extérieur », comme on le ferait avec son bouton.
#? Les fichiers sont toujours là après le redémarrage ; au module 1, vous verrez ce qui, en revanche, disparaît.
redemarrer poste2
connexion poste2 ls
''',
    2: r'''
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
    3: r'''
#@ R2.1
#? « Network is unreachable » : la destination n'est pas sur le réseau de la caisse, et la caisse n'a pas de route par défaut (`ip route` ne montre que la ligne de son propre réseau).
#? La passerelle est l'adresse de la box côté magasin. La box répond sur ses deux adresses même quand elle ne route pas : c'est pourquoi 10.20.0.254 répond déjà.
connexion caisse ip route
connexion caisse ip route add default via 192.168.10.254
connexion caisse ping -c 2 10.20.0.254
#@ R2.2
#? « Destination Host Unreachable », renvoyé par la propre adresse du bureau : sa passerelle, 192.168.10.1, n'existe pas sur le réseau du magasin (personne ne répond aux requêtes ARP).
#? `ip route replace` remplace la route par défaut en une commande ; `del` puis `add` aurait aussi fonctionné.
connexion bureau ip route
connexion bureau ip route replace default via 192.168.10.254
connexion bureau ping -c 2 10.20.0.254
#@ R2.3
#? Une machine Linux ne passe pas les paquets d'une interface à l'autre tant que le routage du noyau est désactivé (net.ipv4.ip_forward = 0) : la box répondait pour elle-même, mais ne relayait rien.
connexion box-annecy sysctl net.ipv4.ip_forward
connexion box-annecy sysctl -w net.ipv4.ip_forward=1
#@ R2.4
#? Les demandes arrivaient au serveur, mais ses réponses, destinées à 192.168.10.11, n'étaient pas sur son réseau : sans route par défaut, il ne savait pas où les envoyer. Un ping muet, sans message d'erreur, est typique d'un problème de retour.
#? `traceroute -n` montre ensuite le chemin complet : la box, puis le serveur.
connexion srv-stock ip route add default via 10.20.0.254
connexion caisse ping -c 2 10.20.0.10
connexion caisse traceroute -n 10.20.0.10
#@ R2.5
#? La passerelle se déclare dans /etc/network/interfaces, dans la même section que l'adresse, avec le mot-clé `gateway` : ifup crée la route par défaut à chaque démarrage.
connexion caisse 'cat > /etc/network/interfaces' <<'EOF'
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address 192.168.10.11
    netmask 255.255.255.0
    gateway 192.168.10.254
EOF
redemarrer caisse
connexion caisse ip route
#@ R2.6
#? Les réglages du noyau tapés avec `sysctl -w` sont perdus à l'extinction ; /etc/sysctl.conf est relu à chaque démarrage. `sysctl -p` l'applique tout de suite, sans attendre.
connexion box-annecy "sed -i 's/^net.ipv4.ip_forward=0/net.ipv4.ip_forward=1/' /etc/sysctl.conf"
connexion box-annecy sysctl -p
redemarrer box-annecy
connexion box-annecy sysctl net.ipv4.ip_forward
''',
}
