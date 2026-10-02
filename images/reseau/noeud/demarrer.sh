#!/bin/sh
# Démarrage d'une machine du réseau simulé. Elle naît sans câble : la console branche ses câbles (lab-cablage),
# puis lui fait appliquer sa configuration réseau (ifup), comme au démarrage d'un vrai poste.
# L'état d'ifupdown ne doit pas survivre à un redémarrage (sinon ifup croit les interfaces déjà configurées).
rm -rf /run/network
mkdir -p /run/network
exec sleep infinity
