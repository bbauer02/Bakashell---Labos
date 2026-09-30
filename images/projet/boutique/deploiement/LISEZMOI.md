# Installer l'API sur un serveur Debian

Les serveurs n'ont pas systemd : l'API tourne comme un service classique, piloté par le script
`api-boutique` de ce dossier.

- Node.js : paquet `nodejs` du dépôt APT de l'entreprise (`depot.cimes.lan`, déjà configuré sur les serveurs).
- Code de l'API : `server.js`, `package.json`, `produits.json` et le dossier `src/` (rien d'autre n'est utile
  pour l'exécuter : ni les tests, ni Jest).
- Script de service : `/etc/init.d/api-boutique` (exécutable), puis `service api-boutique start|stop|restart|status`.
- Réglages lus par le script : `/etc/default/api-boutique`, par exemple :

```sh
API_USER=api                 # compte qui exécute l'API (jamais root)
API_DIR=/opt/api-boutique    # dossier du code
API_PORT=3000                # port d'écoute
# Facultatif (serveurs des magasins) :
# API_DATA=/var/lib/api-boutique       données : commandes.json et stock.json lisibles, etat.json modifiable
# API_JOURNAUX=/var/log/api-boutique   journaux : modifiables par API_USER
```

Les messages de l'API (démarrage, erreurs) sont dans `API_JOURNAUX/api-boutique.log`, ou
`/var/log/api-boutique.log` si `API_JOURNAUX` n'est pas défini.
