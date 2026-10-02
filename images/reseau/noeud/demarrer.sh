#!/bin/sh
# Démarrage d'une machine du réseau simulé. Elle naît sans câble : la console branche ses câbles (lab-cablage),
# puis lui fait appliquer sa configuration réseau (ifup), comme au démarrage d'un vrai poste.
# L'état d'ifupdown ne doit pas survivre à un redémarrage (sinon ifup croit les interfaces déjà configurées).
rm -rf /run/network
mkdir -p /run/network
# Réglages du noyau de la machine (/etc/sysctl.conf : routage net.ipv4.ip_forward…), comme au démarrage d'une Debian.
# Seuls les routeurs peuvent les modifier (/proc/sys en écriture) ; ailleurs, l'échec est sans conséquence.
sysctl -q -p /etc/sysctl.conf > /dev/null 2>&1
exec sleep infinity
