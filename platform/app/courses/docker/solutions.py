"""Corrigé du parcours Docker : un script par étape, exécuté en tant qu'« etudiant » (groupe docker) par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
"""

SOLUTIONS = {
    1: r'''
#@ D1.1
#? C'est votre shell qui lit la ligne avant Docker : entre guillemets doubles, `$CIMES…` serait remplacé par une variable vide, et entre guillemets simples l'apostrophe de « l'équipe » fermerait la chaîne.
#? `"$(cat ~/message.txt)"` insère le contenu du fichier tel quel, sans réinterpréter le `$` ni l'apostrophe qu'il contient : Docker reçoit la phrase exacte.
#? Tout ce qui suit le nom de l'image est la commande du conteneur ; `echo` se termine aussitôt, d'où l'état exited avec le code 0 attendu.
#? La phrase est tirée au sort : celle de votre environnement diffère de celle de l'exemple, mais la commande reste la même.
# "$(cat …)" insère le contenu du fichier tel quel : ni le « $ » ni l'apostrophe ne sont interprétés
docker run --name premier alpine echo "$(cat ~/message.txt)"
#@ D1.2
#? Un conteneur n'est qu'un processus de l'hôte, isolé : `docker inspect -f '{{.State.Pid}}'` (ou `docker top dormeur`) donne son PID vu de l'hôte.
#? Vu de l'intérieur, grâce à l'espace de noms des PID, ce même `sleep` est le processus n°1 du conteneur, comme le montre `docker exec dormeur ps`.
#? Le piège : croire que les deux numéros sont égaux. Le PID de l'hôte change à chaque lancement, celui de l'intérieur vaut toujours 1 pour le processus principal.
docker run -d --name dormeur alpine sleep 3600
# Vu de l'hôte : un processus comme un autre, avec son PID
docker inspect -f '{{.State.Pid}}' dormeur > ~/pid-dormeur.txt
# Vu de l'intérieur : sleep est le processus n°1 du conteneur
docker exec dormeur ps
echo 1 > ~/pid-interne.txt
#@ D1.3
#? Deux filtres différents se combinent en ET, deux valeurs du même filtre en OU : label marketing ET (exited OU created).
#? On affiche toujours la liste avant de la donner à `docker rm` : c'est ce qui évite de supprimer un conteneur de la compta ou un conteneur sans équipe.
#? Le piège : `docker container prune`, qui supprimerait aussi les conteneurs arrêtés des autres équipes.
#? Les noms des conteneurs sont tirés au sort : les vôtres diffèrent, seuls les labels et les états comptent.
# Deux filtres différents se combinent en ET, deux valeurs de status en OU : on vérifie avant de supprimer
docker ps -a --filter label=equipe=marketing --filter status=exited --filter status=created
docker rm $(docker ps -aq --filter label=equipe=marketing --filter status=exited --filter status=created)
#@ D1.4
#? Docker conserve le code de sortie du processus principal : `docker ps -a` l'affiche entre parenthèses dans la colonne STATUS.
#? 127 signifie « commande introuvable » ; au-delà de 128, le processus a été tué par un signal : 137 = 128 + 9, SIGKILL.
#? Les tâches portent des noms tirés au sort : les vôtres diffèrent. `docker inspect -f '{{.State.ExitCode}}'` sur chaque tâche donne le même résultat que ce filtrage.
docker ps -a --filter name=tache- --format '{{.Names}} {{.Status}}'
# 137 = 128 + 9 : tuée par SIGKILL ; 127 : commande introuvable
docker ps -a --filter name=tache- --format '{{.Names}} {{.Status}}' | grep '(137)' | cut -d' ' -f1 > ~/tuee.txt
docker ps -a --filter name=tache- --format '{{.Names}} {{.Status}}' | grep '(127)' | cut -d' ' -f1 > ~/introuvable.txt
#@ D1.5
#? Pas besoin de démarrer les postes : `docker diff` liste ce qui a changé dans la couche inscriptible d'un conteneur, même arrêté (A = ajouté, C = modifié, D = supprimé).
#? La méthode consiste à écarter le bruit commun aux trois postes (historique dans `/root`, fichiers de `/tmp`, journaux de `/var/log`) : ce qui reste est l'intrus.
#? Le poste compromis et le chemin du fichier (un nom caché commençant par `.maj-`) sont tirés au sort : votre réponse diffère de celle d'un camarade.
for p in poste-1 poste-2 poste-3; do echo "== $p"; docker diff $p; done
# Bruit commun aux trois postes : /root (historique), /tmp, /var/log. L'intrus est ailleurs.
for p in poste-1 poste-2 poste-3; do
  f=$(docker diff $p | awk '$1 == "A" {print $2}' | grep -vE '^/(tmp|root|var/log)/')
  if [ -n "$f" ]; then echo "$p" > ~/poste-compromis.txt; echo "$f" > ~/fichier-depose.txt; fi
done
''',
    2: r'''
#@ D2.1
#? Le traitement écrit ses erreurs sur la sortie d'erreur, et `docker logs` les restitue sur la sortie d'erreur : un `|` seul ne transmet que la sortie standard, d'où le 0 de Julien.
#? `2>&1` redirige la sortie d'erreur vers la sortie standard avant le tube ; `grep -c` compte les lignes, `tail -1` garde la dernière erreur.
#? Variante : `docker logs paiements 2>&1 >/dev/null | grep …` ne garde que la sortie d'erreur. L'identifiant peut être écrit avec ou sans le préfixe `TX-`.
#? Le nombre d'erreurs et les identifiants sont tirés au sort : vos valeurs diffèrent de celles d'un camarade.
# Les erreurs sont écrites sur la sortie d'erreur : 2>&1 les fait passer dans le tube
docker logs paiements 2>&1 | grep -c ERREUR > ~/nb-erreurs.txt
docker logs paiements 2>&1 | grep ERREUR | tail -1 | grep -o 'TX-[0-9a-f]*' > ~/derniere-erreur.txt
#@ D2.2
#? `docker stop` arrête le conteneur sans le supprimer : ses journaux restent lisibles jusqu'au `docker rm`.
#? L'arrêt prend 10 secondes : le shell en PID 1 n'a pas de gestionnaire pour SIGTERM et l'ignore, Docker finit par envoyer SIGKILL, d'où le code 137 (vous comprendrez pourquoi au jour 7).
#? Le piège : `docker rm -f` (tout est perdu) ou `docker pause` (un conteneur en pause tourne toujours). On lit ensuite le code avec `docker inspect -f '{{.State.ExitCode}}'`.
# 10 s d'attente : le shell en PID 1 ignore SIGTERM, il finit tué (code 137)
docker stop traitement-nuit
docker inspect -f '{{.State.ExitCode}}' traitement-nuit > ~/code-sortie.txt
#@ D2.3
#? `docker exec` lance la commande sous l'utilisateur du conteneur, ici `guest`, qui n'a pas le droit de lire `/secret` : d'où le « Permission denied ».
#? `docker exec -u root` lance la commande en root dans le conteneur, sans l'arrêter ni le recréer.
#? Variante tout aussi valable : `docker cp coffre:/secret/cle.txt ~/cle-coffre.txt`, car `docker cp` passe par le moteur et ignore l'utilisateur du conteneur.
#? La clé est générée au hasard dans votre conteneur : sa valeur vous est propre.
# Le conteneur tourne sous l'utilisateur guest, qui n'a pas le droit de lire /secret
docker exec coffre id
docker exec -u root coffre cat /secret/cle.txt > ~/cle-coffre.txt
#@ D2.4
#? Les variables `ENV` d'une image ne sont que des valeurs par défaut : le `-e ENVIRONNEMENT=…` donné au lancement les remplace dans le conteneur.
#? Le piège était d'interroger l'image `coffre:1` au lieu du conteneur : on lit ce que voit le processus avec `docker exec coffre printenv ENVIRONNEMENT`.
#? Variante : `docker inspect -f '{{.Config.Env}}' coffre` ; la réponse peut garder le préfixe `ENVIRONNEMENT=`. La valeur (`preprod-…`) est tirée au sort.
# L'image dit « production », mais le -e du lancement l'emporte : on interroge le conteneur
docker exec coffre printenv ENVIRONNEMENT > ~/env-coffre.txt
#@ D2.5
#? `docker stats` mesure en direct le CPU et la mémoire de chaque conteneur ; `--no-stream` fait un seul relevé au lieu d'un affichage continu.
#? Le format `{{.MemPerc}} {{.Name}}` place le pourcentage en tête, ce qui permet de trier numériquement avec `sort -rn` et de garder le premier.
#? Lire simplement le tableau de `docker stats --no-stream` suffit aussi. Le worker gourmand est tiré au sort : le vôtre n'est peut-être pas celui d'un camarade.
docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' worker-a worker-b worker-c worker-d
docker stats --no-stream --format '{{.MemPerc}} {{.Name}}' worker-a worker-b worker-c worker-d | sort -rn | head -1 | cut -d' ' -f2 > ~/gourmand.txt
#@ D2.6
#? `docker update` modifie à chaud certaines options d'un conteneur (mémoire, CPU, politique de redémarrage), sans le recréer ni le redémarrer.
#? `--memory-swap` est la limite mémoire + swap : lui donner la même valeur que `--memory` interdit le swap, ce que la vérification contrôle.
#? `--cpus 0.5` correspond à un demi-CPU (500000000 NanoCpus dans `docker inspect`). Le nom du worker, lu dans `~/gourmand.txt`, dépend de votre tirage.
# Mémoire ET mémoire + swap (même valeur : pas de swap), et un demi-CPU, à chaud
docker update --memory 128m --memory-swap 128m --cpus 0.5 "$(cat ~/gourmand.txt)"
#@ D2.7
#? `docker exec` lance un nouveau processus, avec sa propre entrée standard : la caisse ne le verrait jamais. `docker attach` branche votre terminal sur le processus principal.
#? On se détache avec Ctrl+P puis Ctrl+Q, qui laisse le conteneur tourner ; Ctrl+D enverrait une fin de fichier, la boucle `while read` se terminerait et la caisse s'arrêterait.
#? Dans le corrigé, `script` simule un terminal pour pouvoir automatiser ces touches ; en salle, vous les tapez simplement au clavier.
#? Le code de clôture est tiré au sort dans la mémoire de la caisse : votre ticket diffère de celui d'un camarade.
# En salle : docker attach caisse, taper CLOTURE puis Entrée, et se détacher avec Ctrl+P Ctrl+Q.
# Ici, « script » simule le terminal : il envoie CLOTURE, Entrée, puis Ctrl+P Ctrl+Q.
(sleep 1; printf 'CLOTURE\r'; sleep 2; printf '\020\021'; sleep 1) | script -q -c "docker attach caisse" /dev/null > /dev/null
docker logs caisse
#@ D2.8
#? Un conteneur arrêté refuse `docker exec`, mais son système de fichiers existe toujours : `docker diff` montre où la facture a été écrite.
#? `docker cp` fonctionne sur un conteneur arrêté ; la forme `conteneur:/factures/.` copie le contenu du dossier, quel que soit le nom du fichier.
#? Le nom de la facture (`facture-mars-…`) est tiré au sort. Surtout, on ne supprime pas le conteneur : il n'y aurait plus rien à récupérer.
# Le conteneur est arrêté : pas d'exec, mais diff et cp fonctionnent
docker diff generateur-factures
mkdir -p ~/factures
docker cp generateur-factures:/factures/. ~/factures/
''',
    3: r'''
#@ D3.1
#? Un conteneur a son propre réseau : `-p 8080:80` publie le port 80 du conteneur, où écoute nginx, sur le port 8080 de la machine.
#? L'ordre est toujours hôte:conteneur ; `-d` rend la main en laissant le serveur tourner en arrière-plan.
#? Le piège : oublier `-p`, ou écrire `-p 80:8080`. On vérifie avec `curl localhost:8080`.
docker run -d --name vitrine -p 8080:80 nginx:alpine
#@ D3.2
#? Un bind mount partage le dossier de l'hôte avec le conteneur : une modification du HTML est visible immédiatement, sans rien reconstruire.
#? `:ro` monte le dossier en lecture seule : nginx ne peut pas modifier les fichiers du site.
#? Le piège : un chemin qui ne commence ni par `/` ni par `./` (par exemple `-v site:/…`) désigne un volume nommé, vide. Ici `~` est remplacé par votre shell par un chemin absolu.
#? Variante : `--mount type=bind,src=$HOME/projet/site,dst=/usr/share/nginx/html,readonly`.
docker run -d --name vitrine-site -p 8081:80 -v ~/projet/site:/usr/share/nginx/html:ro nginx:alpine
sleep 2
#@ D3.3
#? `docker ps --filter publish=8086` révèle le conteneur qui occupe le port ; son nom est tiré au sort, il diffère donc dans votre environnement.
#? On ne change pas les ports d'un conteneur existant : il faut le recréer. Mais sa page n'existe que dans sa couche inscriptible, que `docker rm` détruit.
#? D'où l'ordre : `docker diff` pour la trouver, `docker cp` pour la sauver, recréation sous le même nom avec `-p 8087:80`, puis `docker cp` pour la remettre.
#? Ensuite seulement, le port 8086 est libre pour `vitrine-promo`, avec le même bind mount en lecture seule qu'au D3.2.
nom=$(docker ps --filter publish=8086 --format '{{.Names}}')
# La page a été déposée dans la couche inscriptible : on la sauve avant de recréer le conteneur
docker diff "$nom"
docker cp "$nom":/usr/share/nginx/html/index.html /tmp/page-flash.html
docker rm -f "$nom"
docker run -d --name "$nom" -p 8087:80 nginx:alpine
docker cp /tmp/page-flash.html "$nom":/usr/share/nginx/html/index.html
docker run -d --name vitrine-promo -p 8086:80 -v ~/projet/site:/usr/share/nginx/html:ro nginx:alpine
sleep 2
#@ D3.4
#? Par défaut, un port publié écoute sur toutes les interfaces de la machine, donc depuis le réseau.
#? `-p 127.0.0.1:8088:80` ne publie le port que sur l'adresse locale : seule la machine elle-même (ou un tunnel SSH) peut joindre la console.
#? `docker port admin-console` doit afficher `127.0.0.1:8088` ; si vous voyez `0.0.0.0:8088`, il faut recréer le conteneur.
# Publié sur 127.0.0.1 seulement : injoignable depuis le réseau
docker run -d --name admin-console -p 127.0.0.1:8088:80 nginx:alpine
docker port admin-console
sleep 1
#@ D3.5
#? Un bind mount de fichier reste attaché au fichier d'origine, c'est-à-dire à son inode ; `sed -i` (comme la plupart des éditeurs) écrit un nouveau fichier et le renomme : le conteneur voit toujours l'ancien.
#? `ls -i` avant et après la modification le prouve : l'inode a changé.
#? En montant le dossier sur `/etc/nginx/conf.d`, le conteneur voit le contenu actuel du dossier, fichiers remplacés compris : un `nginx -s reload` suffit ensuite.
#? Les messages de maintenance sont tirés au sort : ceux de votre environnement diffèrent.
# Le conteneur voit encore l'ancien fichier : un bind mount de fichier suit l'inode d'origine, et sed -i en a créé un nouveau
ls -i ~/projet/maintenance/default.conf
docker exec maintenance cat /etc/nginx/conf.d/default.conf
# On monte le DOSSIER : les fichiers remplacés y sont bien visibles
docker rm -f maintenance
docker run -d --name maintenance -p 8089:80 -v ~/projet/maintenance:/etc/nginx/conf.d:ro nginx:alpine
sleep 2
#@ D3.6
#? Le processus maître de nginx tourne en root, mais ses processus de travail, qui lisent les fichiers, tournent sous l'utilisateur nginx (uid 101) : `docker top intranet` le montre.
#? Cet uid n'est ni le vôtre ni celui de votre groupe : il relève des droits des « autres ». Il lui faut la traversée (`x`) du dossier et la lecture (`r`) du fichier.
#? `chmod 755` sur le dossier et `644` sur le fichier suffisent, sans recréer le conteneur ; `chmod o+rx` et `o+r` sont équivalents.
#? Les pièges : `chmod 777` (tout le monde pourrait modifier le site) ou faire tourner les processus de travail en root.
docker logs intranet 2>&1 | tail -3
docker top intranet
ls -ln ~/projet/intranet
# Les processus de travail de nginx (uid 101) relèvent des droits des « autres » : lecture et traversée
chmod 755 ~/projet/intranet
chmod 644 ~/projet/intranet/index.html
''',
    4: r'''
#@ D4.1
#? Un volume nommé est géré par Docker, indépendamment de tout conteneur : les données survivent à `docker rm` et à la mise à jour de l'image.
#? Les arguments placés après le nom de l'image remplacent la commande par défaut : `redis-server --appendonly yes` fait écrire chaque modification sur disque.
#? Le piège : sans `--appendonly yes`, Redis n'écrit ses données que de temps en temps, et la clé n'est pas encore sur le volume au moment de la vérification.
docker volume create donnees-boutique
docker run -d --name cache -v donnees-boutique:/data redis:7-alpine redis-server --appendonly yes
sleep 2
docker exec cache redis-cli set promo RANDO10
sleep 1
#@ D4.2
#? On ne lit pas un volume directement : un conteneur jetable (`--rm`) monte à la fois le volume et un dossier de l'hôte, puis lance `tar`.
#? `-C /data .` archive le contenu du volume sans le préfixe `/data` dans les chemins ; le dossier de l'hôte doit être désigné par un chemin absolu (`~` est remplacé par votre shell).
#? L'archive doit être faite après l'écriture de la clé `promo` (D4.1), sinon elle ne la contient pas.
mkdir -p ~/sauvegardes
docker run --rm -v donnees-boutique:/data -v ~/sauvegardes:/backup alpine tar czf /backup/donnees-boutique.tar.gz -C /data .
#@ D4.3
#? Redis a changé le propriétaire du dossier pour son propre utilisateur (uid 999), et les droits sont en 700 : vous ne pouvez plus le lister.
#? Vous n'êtes pas root, mais le moteur Docker l'est : un conteneur jetable qui monte le dossier peut faire `chown -R` vers vos numéros (`id -u`, `id -g`).
#? C'est exactement pourquoi appartenir au groupe `docker` revient à avoir les droits de root. Supprimer le dossier aurait fait perdre `dump.rdb`.
# Propriétaire 999 (l'utilisateur redis de l'image), droits 700 : on passe par le moteur, qui est root
ls -ld ~/redis-local
docker run --rm -v ~/redis-local:/d alpine chown -R "$(id -u):$(id -g)" /d
ls -l ~/redis-local
#@ D4.4
#? Aucune commande ne renomme un volume : on crée le nouveau, puis un conteneur jetable monte les deux et copie le contenu.
#? `cp -a` conserve propriétaires et droits (les fichiers de Redis appartiennent à l'uid 999), et la forme `/de/.` copie aussi les fichiers cachés.
#? On ne supprime l'ancien volume qu'après la copie ; recréer les 150 articles à la main ne donnerait pas les mêmes valeurs, tirées au sort.
# Un volume ne se renomme pas : on copie son contenu dans un nouveau, avec un conteneur jetable
docker volume create stock-archive
docker run --rm -v stock-2024:/de -v stock-archive:/vers alpine cp -a /de/. /vers/
docker run -d --name stock -v stock-archive:/data redis:7-alpine
docker volume rm stock-2024
sleep 2
''',
    5: r'''
#@ D5.1
#? Un bind mount masque le contenu de l'image : un dossier vide donne un nginx sans page, d'où le 403 de Thomas.
#? Un volume nommé vide, au premier montage, reçoit une copie du contenu de l'image : la page d'accueil de nginx s'y retrouve.
#? `docker cp` écrit ensuite dans le volume, puisqu'il est monté sur ce dossier. Variante : `docker exec vitrine-pleine sh -c 'echo … > /usr/share/nginx/html/promo.html'`.
#? Le piège : un volume déjà rempli par un essai précédent n'est plus jamais recopié depuis l'image.
docker volume create html-vitrine
docker run -d --name vitrine-pleine -p 8082:80 -v html-vitrine:/usr/share/nginx/html nginx:alpine
echo "<h1>Soldes d'été : -20 % sur les sacs</h1>" > /tmp/promo.html
docker cp /tmp/promo.html vitrine-pleine:/usr/share/nginx/html/promo.html
sleep 1
#@ D5.2
#? La restauration est l'inverse de la sauvegarde : un conteneur jetable monte le volume et `~/sauvegardes`, puis extrait l'archive avec `tar xzf … -C /data`.
#? L'ordre est essentiel : on restaure avant de démarrer Redis, qui lit ses fichiers au démarrage. S'il tourne déjà, il travaille sur un volume vide.
#? Recréer les clés à la main ne suffit pas : la sauvegarde contient 41 clés, dont les fiches clients aux valeurs tirées au sort.
docker volume create donnees-restaurees
# Restauration AVANT le démarrage de Redis
docker run --rm -v donnees-restaurees:/data -v ~/sauvegardes:/backup alpine tar xzf /backup/cache-avant-migration.tar.gz -C /data
docker run -d --name cache-restaure -v donnees-restaurees:/data redis:7-alpine redis-server --appendonly yes
sleep 2
#@ D5.3
#? `docker volume ls -f dangling=true` liste les volumes qu'aucun conteneur, même arrêté, n'utilise ; les anonymes ont un nom de 64 caractères hexadécimaux.
#? `docker volume prune`, sans `-a`, ne supprime que les volumes anonymes inutilisés : `archives-2023`, nommé, est épargné.
#? Le piège : `docker volume prune -a`, qui supprime aussi les volumes nommés inutilisés, et donc le grand livre comptable.
docker volume ls -f dangling=true
# Sans -a : seuls les volumes anonymes inutilisés sont supprimés
docker volume prune -f
#@ D5.4
#? `--read-only` interdit toute écriture dans le système de fichiers du conteneur ; lancé ainsi seul, nginx s'arrête, et `docker logs` indique où il voulait écrire.
#? nginx a besoin d'écrire son cache (`/var/cache/nginx`) et son fichier PID (`/run`) : chacun reçoit un tmpfs, un petit système de fichiers en mémoire.
#? On limite les tmpfs au strict nécessaire : `/usr/share/nginx/html` reste en lecture seule. Syntaxe longue équivalente : `--mount type=tmpfs,dst=/run`.
# docker logs montre ce que nginx doit écrire : son cache et son fichier PID
docker run -d --name vitrine-ro -p 8083:80 --read-only --tmpfs /var/cache/nginx --tmpfs /run nginx:alpine
sleep 2
#@ D5.5
#? Le conteneur tourne bien sur la v2, mais le volume `html-maison`, monté par-dessus le site, a été rempli par la v1 au premier montage et ne l'est plus jamais ensuite.
#? Quand le contenu est livré par l'image, on ne monte rien sur son dossier : le conteneur est recréé sans `-v`, et la v3 s'affichera d'elle-même.
#? Le volume devenu inutile peut être supprimé ; vider son contenu à la main ne réglerait que la v2, pas la livraison suivante.
# Le conteneur est bien sur la v2… mais un volume rempli par la v1 masque le site de l'image
docker inspect -f '{{.Config.Image}}' vitrine-maison
docker inspect -f '{{range .Mounts}}{{.Name}} -> {{.Destination}}{{end}}' vitrine-maison
docker rm -f vitrine-maison
docker volume rm html-maison
# Le site est livré par l'image : on ne monte rien par-dessus
docker run -d --name vitrine-maison -p 8092:80 vitrine-maison:2
sleep 1
#@ D5.6
#? Le script est bien écrit dans `/work`, mais son exécution est refusée : Docker monte les tmpfs avec l'option `noexec` par défaut, visible avec `mount`.
#? `--tmpfs /work:exec` autorise l'exécution, tout en gardant une zone de travail en mémoire qui disparaît à l'arrêt.
#? On ne met pas `--rm` : la vérification lit les journaux du conteneur `compilateur`, qui doit donc exister après sa fin. Et pas de volume ni de bind mount sur `/work`.
# Les tmpfs sont montés « noexec » par défaut
docker run --rm --read-only --tmpfs /work compilateur:1 mount | grep /work || true
docker run --name compilateur --read-only --tmpfs /work:exec compilateur:1
#@ D5.7
#? On liste d'abord : `-f dangling=true` pour les volumes inutilisés, puis le filtre de label pour repérer ceux à conserver.
#? `docker volume prune -a` supprime les volumes nommés inutilisés, et `--filter 'label!=conserver=oui'` exclut ceux qui portent l'étiquette.
#? Variante : `docker volume rm` volume par volume après vérification. Les noms des volumes sont tirés au sort, et aucun conteneur ne doit être supprimé.
docker volume ls -f dangling=true
docker volume ls -f dangling=true -f label=conserver=oui
# Volumes nommés inutilisés, sauf ceux étiquetés conserver=oui
docker volume prune -a -f --filter 'label!=conserver=oui'
''',
    6: r'''
#@ D6.1
#? Un Dockerfile répond à quatre questions : l'image de départ (`FROM`), l'emplacement du code (`WORKDIR`, `COPY`), le port écouté (`EXPOSE`) et la commande de démarrage (`CMD`).
#? La forme JSON de `CMD` lance node directement, sans shell intermédiaire ; le dernier argument de `docker build`, ici `.`, est le contexte de construction.
#? `EXPOSE` ne fait que documenter le port : c'est `-p` qui le publie au lancement. Cette première image embarque encore `.env` et `node_modules`, on le corrige au D6.3.
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
EOF
docker build -t boutique-api:1.0 .
#@ D6.2
#? `--restart unless-stopped` relance le conteneur après un plantage ou un redémarrage du moteur, sauf si on l'a arrêté volontairement.
#? Le piège : `always`, qui relancerait aussi un conteneur arrêté volontairement au redémarrage du moteur, ou `on-failure`, qui ne couvre pas le redémarrage du serveur.
#? `-p 3000:3000` publie l'API sur le port 3000 de la machine.
docker run -d --name api -p 3000:3000 --restart unless-stopped boutique-api:1.0
#@ D6.3
#? `COPY . .` copie tout le contexte : le `.dockerignore` exclut `node_modules` (25 Mo inutiles) et `.env` (la clé Stripe), qui n'ont rien à faire dans l'image.
#? `USER node`, un utilisateur fourni par l'image node, fait tourner l'application sans les droits de root.
#? Un conteneur garde l'image avec laquelle il a été créé : reconstruire `boutique-api:1.0` ne suffit pas, il faut recréer `api`.
#? Variante : des `COPY` qui ne copient que les fichiers nécessaires plutôt qu'un `.dockerignore`.
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY . .
# L'application ne tourne pas en root
USER node
EXPOSE 3000
CMD ["node", "server.js"]
EOF
# Le contexte de construction exclut les dépendances locales et les secrets
printf 'node_modules\n.env\n' > .dockerignore
docker build -t boutique-api:1.0 .
# Un conteneur garde son image : on recrée « api » sur la nouvelle
docker rm -f api
docker run -d --name api -p 3000:3000 --restart unless-stopped boutique-api:1.0
sleep 2
#@ D6.4
#? « Restarting (3) » : le programme sort avec le code 3, et `docker logs` explique qu'il ne trouve pas `/config/stock.conf`.
#? On lui fournit le dossier de configuration par un bind mount en lecture seule ; monter le fichier seul (`-v ~/projet/synchro/stock.conf:/config/stock.conf:ro`) fonctionne aussi.
#? `--restart on-failure:5` ne relance qu'en cas d'échec, 5 fois au plus ; la politique se fixe à la création, d'où la recréation du conteneur.
#? Le contenu de `stock.conf` est tiré au sort : le message « Synchro OK » de votre environnement diffère.
# « Restarting (3) » : le programme sort avec le code 3, faute de configuration
docker logs synchro 2>&1 | tail -2
docker rm -f synchro
docker run -d --name synchro --restart on-failure:5 -v ~/projet/synchro:/config:ro synchro-stock:1.0
sleep 2
#@ D6.5
#? `HEALTHCHECK` place la vérification dans l'image : tout conteneur qui en est issu affiche son état de santé dans `docker ps`, sans option au lancement.
#? La commande s'exécute dans le conteneur : `wget` existe dans l'image (BusyBox), pas `curl`. Un test avec curl échouerait toujours, et le conteneur serait unhealthy.
#? `|| exit 1` garantit un code d'échec clair ; `wget -q --spider http://localhost:3000/health` est une variante valable. Pensez à recréer `api` sur la nouvelle image.
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY . .
USER node
EXPOSE 3000
# wget (BusyBox) est dans l'image, curl non
HEALTHCHECK --interval=10s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "server.js"]
EOF
docker build -t boutique-api:1.0 .
docker rm -f api
docker run -d --name api -p 3000:3000 --restart unless-stopped boutique-api:1.0
sleep 2
#@ D6.6
#? `docker diff bricolage-marc` révèle ce que Marc a ajouté à l'image alpine, même sur le conteneur arrêté : le script et sa configuration.
#? `docker cp` les récupère dans le contexte de construction, et des `COPY` les replacent aux mêmes emplacements ; `docker cp` et `COPY` conservent le droit d'exécution du script.
#? `CMD ["rapport.sh"]` suffit, car `/usr/local/bin` est dans le PATH. Surtout pas de `docker commit` : la vérification exige que `rapport:1.0` soit l'image produite par le Dockerfile.
#? Le site et l'édition du rapport sont tirés au sort : votre rapport diffère de celui d'un camarade.
# Ce que Marc a modifié par rapport à l'image alpine
docker diff bricolage-marc
cd ~/projet/rapport
docker cp bricolage-marc:/usr/local/bin/rapport.sh .
docker cp bricolage-marc:/etc/rapport.conf .
cat > Dockerfile <<'EOF'
FROM alpine
COPY rapport.conf /etc/rapport.conf
COPY rapport.sh /usr/local/bin/rapport.sh
CMD ["rapport.sh"]
EOF
docker build -t rapport:1.0 .
docker run --rm rapport:1.0
''',
    7: r'''
#@ D7.1
#? Docker réutilise une couche si l'instruction et tout ce qui la précède sont inchangés : on copie d'abord `package.json` et `package-lock.json`, puis on lance `npm ci`.
#? Quand seul `server.js` change, l'étape `npm ci` reste en cache ; quand `package-lock.json` change, elle est rejouée, ce que la vérification contrôle.
#? Le piège : `COPY . .` avant `npm ci`, qui invalide l'installation à chaque modification du code. `--no-audit --no-fund` évitent que npm contacte le registre sans Internet.
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
# Les dépendances d'abord : cette couche reste en cache tant que package*.json ne changent pas
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
# Le code ensuite : il change souvent
COPY . .
USER node
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "server.js"]
EOF
docker build -t boutique-api:1.0 .
#@ D7.2
#? Le PID 1 était le shell qui exécute `demarrer.sh` ; node n'était que son enfant, et un shell en PID 1 ne lui transmet pas SIGTERM : `docker stop` attendait 10 s puis tuait tout.
#? `exec node pointeuse.js` remplace le shell par node, qui devient le PID 1, reçoit SIGTERM et enregistre les passages avant de s'arrêter.
#? La forme exec du `CMD` ne gâche rien : on ne compte pas sur le shell pour lancer le script. Et `pointeuse.js` reste intact, comme exigé.
cd ~/projet/pointeuse
# exec : le shell est remplacé par node, qui devient le PID 1 et reçoit SIGTERM (c'est la correction essentielle)
sed -i 's/^node pointeuse.js/exec node pointeuse.js/' demarrer.sh
# Forme exec : on ne compte pas sur le shell pour lancer le script
sed -i 's|^CMD ./demarrer.sh|CMD ["./demarrer.sh"]|' Dockerfile
docker build -t pointeuse:1.0 .
#@ D7.3
#? `ENTRYPOINT` fixe le programme, toujours exécuté ; `CMD` donne ses arguments par défaut, remplacés par ce qui suit le nom de l'image dans `docker run`.
#? Ainsi `docker run --rm export-produits:1.0 --format csv` exécute `node export.js --format csv`.
#? Le piège : tout mettre dans `CMD`, et les arguments de `docker run` remplaceraient toute la commande. En forme shell, l'`ENTRYPOINT` ignorerait `CMD` et les arguments.
cd ~/projet/export
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY . .
USER node
# Le programme, toujours lancé, et ses arguments par défaut (remplacés par ceux de docker run)
ENTRYPOINT ["node", "export.js"]
CMD ["--format", "texte"]
EOF
docker build -t export-produits:1.0 .
#@ D7.4
#? Un `ARG` n'existe que pendant la construction : on le recopie dans un `ENV` pour que l'application le lise, et dans un `LABEL` pour les métadonnées de l'image.
#? On le déclare après `npm ci` : un ARG est transmis à tous les RUN qui le suivent, et changer sa valeur les reconstruirait tous.
#? La valeur par défaut (`dev`) ne sert que si l'on oublie `--build-arg` ; la version n'est jamais écrite en dur dans le Dockerfile.
cd ~/projet/api
cat > Dockerfile <<'EOF'
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
COPY . .
# Version passée à la construction, placée après npm ci pour ne pas invalider le cache
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
LABEL org.opencontainers.image.version=$APP_VERSION
USER node
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "server.js"]
EOF
docker build --build-arg APP_VERSION=1.1 -t boutique-api:1.1 .
#@ D7.5
#? Un script `ENTRYPOINT` reçoit le `CMD`, ou les arguments de `docker run`, dans `$@` : celui de Marc les ignorait et lançait toujours le serveur.
#? `exec "$@"` exécute la commande reçue après la préparation de la configuration, et remplace le shell : la commande devient le PID 1 et reçoit SIGTERM.
#? Le `CMD` en forme exec fournit la commande par défaut (`node server.js`) ; les guillemets de `"$@"` préservent chaque argument tel quel.
cd ~/projet/entree
# Le script prépare la configuration, puis se fait REMPLACER par la commande reçue (le CMD par défaut)
sed -i 's/^node server.js$/exec "$@"/' demarrage.sh
echo 'CMD ["node", "server.js"]' >> Dockerfile
docker build -t api-entree:1.0 .
docker run --rm -e REDIS_HOST=essai api-entree:1.0 cat /tmp/config.json
#@ D7.6
#? Le noyau n'applique pas au PID 1 l'action par défaut des signaux : `rapports.js`, sans gestionnaire de SIGTERM, l'ignore donc, et Docker finit par le tuer (code 137).
#? `docker run --init` place un mini-init (tini) en PID 1 : il transmet SIGTERM à node, qui n'est plus PID 1 et s'arrête aussitôt, sans toucher à l'image.
#? Un code de sortie 143 (128 + 15, SIGTERM) est alors normal. Dans compose, l'équivalent est `init: true`.
# node en PID 1 sans gestionnaire de SIGTERM ignore le signal : un mini-init (tini) le lui transmet
docker rm -f rapports-nuit
docker run -d --name rapports-nuit --init rapports-nuit:1.0
#@ D7.7
#? Un tag est une étiquette mobile posée sur un identifiant d'image : `latest` n'est pas « la plus récente », c'est le tag par défaut, qui désigne ce qu'on lui a fait désigner.
#? `docker tag etiqueteuse:1.5 etiqueteuse:latest` déplace l'étiquette ; `docker images etiqueteuse` montre alors le même IMAGE ID pour `1.5`, `1` et `latest`.
#? Un conteneur garde l'image avec laquelle il a été créé, même si le tag est déplacé : il faut recréer `etiqueteuse` depuis `etiqueteuse:latest`.
docker images etiqueteuse
docker tag etiqueteuse:1.5 etiqueteuse:latest
docker tag etiqueteuse:1.5 etiqueteuse:1
# Le conteneur garde l'ancienne image : on le recrée
docker rm -f etiqueteuse
docker run -d --name etiqueteuse etiqueteuse:latest
''',
    8: r'''
#@ D8.1
#? Une construction en plusieurs étapes génère la page avec Node dans la première étape ; seule la dernière étape forme l'image finale, qui ne contient que nginx et le résultat.
#? `COPY --from=construction` copie seulement `dist/` : son chemin dépend du `WORKDIR` de la première étape (ici `/src/dist/`).
#? Le piège : générer la page sur votre machine et la copier, alors que `node generer.js` doit s'exécuter pendant la construction pour suivre `produits.json`.
cd ~/projet/catalogue
cat > Dockerfile <<'EOF'
# Étape 1 : génération du site avec Node
FROM node:20-alpine AS construction
WORKDIR /src
COPY . .
RUN node generer.js

# Étape 2 : l'image finale ne contient que nginx et le résultat
FROM nginx:alpine
COPY --from=construction /src/dist/ /usr/share/nginx/html/
EOF
docker build -t catalogue-web:1.0 .
docker run -d --name catalogue -p 8084:80 catalogue-web:1.0
sleep 1
#@ D8.2
#? Une image garde la trace de sa construction : `docker history --no-trunc` affiche les commandes complètes, avec la valeur des ARG utilisés par chaque RUN.
#? Un `--build-arg` n'est donc jamais un moyen de passer un secret : quiconque récupère l'image peut le lire.
#? Le mot de passe est tiré au sort ; la réponse peut garder le préfixe `DB_PASSWORD=`.
docker history --no-trunc ancienne-api:0.9 | grep -o 'DB_PASSWORD=[^ ]*' | head -1 | cut -d= -f2 > ~/mdp-build.txt
#@ D8.3
#? Une image est l'empilement de toutes ses couches : le `rm` d'un RUN suivant ne fait que masquer le fichier, qui reste dans la couche du `COPY`.
#? `docker save` exporte l'image complète ; dans `blobs/sha256/`, chaque couche est une archive tar, et `tar -xOf couche config/identifiants.txt` affiche le fichier.
#? Sur les blobs qui ne contiennent pas ce fichier (autres couches, fichiers JSON), `tar` échoue, d'où le `2>/dev/null`. Le mot de passe est tiré au sort et la réponse peut garder le préfixe `motdepasse=`.
mkdir -p /tmp/ancienne-api && cd /tmp/ancienne-api
docker save ancienne-api:0.9 -o image.tar
tar -xf image.tar
# La couche du COPY contient encore le fichier ; celle du RUN ne fait que le masquer
for couche in blobs/sha256/*; do
  tar -xOf "$couche" config/identifiants.txt 2>/dev/null
done | cut -d= -f2 > ~/mdp-couche.txt
#@ D8.4
#? `RUN --mount=type=secret,id=licence` monte la licence dans `/run/secrets/licence` le temps de ce seul RUN : elle n'est écrite dans aucune couche ni dans l'historique.
#? `docker build --secret id=licence,src=$HOME/…` fournit le fichier ; dans `src=~/…`, le `~` n'est pas remplacé par le shell, car il n'est pas en début de mot.
#? Le piège : copier la licence dans le projet (un `COPY` l'embarquerait) ou la passer en ARG (visible dans `docker history`).
cd ~/projet/prive
cat > Dockerfile <<'EOF'
FROM alpine
WORKDIR /opt/reassort
COPY activer.sh reassort.sh ./
# La licence n'est montée que pendant ce RUN : elle n'est écrite dans aucune couche
RUN --mount=type=secret,id=licence ./activer.sh /run/secrets/licence
CMD ["./reassort.sh"]
EOF
docker build --secret id=licence,src=$HOME/licences/reassort.txt -t outil-reassort:1.0 .
#@ D8.5
#? Le secret monté n'est écrit dans aucune couche… sauf si une commande le recopie : le `cp` vers `/root/.jeton` l'enregistrait dans la couche du RUN.
#? Comme `installer.sh` accepte le chemin du jeton en argument, on lui fait lire directement `/run/secrets/jeton`.
#? Variante valable : supprimer la copie dans le même RUN (`… && ./installer.sh && rm /root/.jeton`) ; dans un RUN suivant, le jeton resterait dans la couche précédente.
cd ~/projet/outil-stock
# Le jeton est dans une couche : le RUN le recopie dans /root/.jeton
docker save outil-stock:1.0 | grep -ac "$(cat ~/licences/stock.txt)" || true
sed -i 's|cp /run/secrets/jeton /root/.jeton && ./installer.sh$|./installer.sh /run/secrets/jeton|' Dockerfile
docker build --secret id=jeton,src=$HOME/licences/stock.txt -t outil-stock:1.0 .
#@ D8.6
#? Chaque RUN produit une couche : le fichier de 50 Mo créé dans un RUN reste dans cette couche, même si un RUN suivant le supprime.
#? Créé, utilisé et supprimé dans le même RUN, le fichier brut n'est écrit dans aucune couche : l'image retombe à quelques Mo, avec exactement le même résultat.
#? Variante : une étape de construction séparée, puis `COPY --from` du seul `resultat.txt` dans l'image finale.
cd ~/projet/rapport-compact
docker history rapport-compact:1.0
cat > Dockerfile <<'EOF'
FROM alpine
WORKDIR /opt/rapport
COPY compacter.sh .
# Création, utilisation et suppression du fichier brut dans le MÊME RUN : aucune couche ne le contient
RUN yes "Cimes & Sentiers : ventes du jour" | head -c 50000000 > /tmp/brut \
 && ./compacter.sh /tmp/brut > resultat.txt \
 && rm /tmp/brut
CMD ["cat", "resultat.txt"]
EOF
docker build -t rapport-compact:1.0 .
#@ D8.7
#? `docker save` exporte l'image complète : couches, configuration (port, commande) et tag ; à Chamonix, `docker load` la recharge telle quelle.
#? Le piège : `docker export`, qui ne produit que les fichiers d'un conteneur, sans tag, sans CMD ni ENV.
#? Variante : `docker save -o ~/livraison/catalogue-web.tar catalogue-web:1.0` puis `gzip`. L'archive doit être refaite si vous reconstruisez l'image.
# docker save : l'image complète (couches, configuration, tag), et non les seuls fichiers d'un conteneur
mkdir -p ~/livraison
docker save catalogue-web:1.0 | gzip > ~/livraison/catalogue-web.tar.gz
''',
    9: r'''
#@ D9.1
#? Sur un réseau créé par vous, le DNS de Docker résout le nom des conteneurs : l'API joint Redis avec `REDIS_HOST=redis`.
#? Redis ne sert qu'à l'API : il ne publie aucun port. Et on n'utilise jamais une adresse IP de conteneur, qui change à chaque redémarrage.
#? Un conteneur ne change pas de variables d'environnement : on recrée `api` sur le réseau, avec la même politique de redémarrage.
docker network create reseau-boutique
docker run -d --name redis --network reseau-boutique redis:7-alpine
docker rm -f api
docker run -d --name api --network reseau-boutique -p 3000:3000 -e REDIS_HOST=redis --restart unless-stopped boutique-api:1.0
sleep 2
#@ D9.2
#? Sur le réseau `bridge` par défaut, aucun nom n'est résolu : il faut un réseau créé par vous, commun aux deux conteneurs.
#? `docker network connect` branche un conteneur sur un réseau à chaud, sans l'arrêter ni le recréer : on le fait pour chacun des deux.
#? Le piège : ajouter `legacy-db` à la main dans `/etc/hosts`, une adresse figée que le DNS de Docker rend inutile.
docker network create reseau-legacy
docker network connect reseau-legacy legacy-web
docker network connect reseau-legacy legacy-db
#@ D9.3
#? `docker network create --internal` crée un réseau sans passerelle vers l'extérieur : Redis, branché uniquement dessus, ne peut rien joindre au-dehors.
#? L'API doit être publiée, ce qu'un réseau interne ne permet pas : elle est lancée sur un réseau ordinaire, puis branchée aussi sur le réseau interne avec `docker network connect`.
#? Sur le réseau interne, l'API joint Redis par son nom (`REDIS_HOST=redis-sec`) ; Redis ne publie aucun port.
# Redis seulement sur un réseau interne ; l'API sur un réseau ordinaire (pour publier son port) ET sur l'interne
docker network create --internal reseau-donnees
docker network create reseau-front
docker run -d --name redis-sec --network reseau-donnees redis:7-alpine
docker run -d --name api-sec --network reseau-front -p 3002:3000 -e REDIS_HOST=redis-sec boutique-api:1.0
docker network connect reseau-donnees api-sec
sleep 2
#@ D9.4
#? Deux problèmes se cumulent : l'API cherche `redis-cache`, un nom qui n'existe pas, et Redis n'est pas sur le réseau de l'API (`nslookup` échoue).
#? `docker network connect --alias redis-cache` branche Redis, à chaud, sur le réseau de l'API, sous le nom attendu : il n'est ni arrêté ni recréé, et garde ses compteurs.
#? Variante acceptée : recréer `api-diag` avec le bon nom dans `REDIS_HOST`, sur un réseau qu'elle partage avec Redis. Les noms du Redis et des réseaux sont tirés au sort.
# L'API cherche « redis-cache », un nom qui n'existe pas, sur un réseau où Redis n'est pas
docker exec api-diag env | grep REDIS_HOST
docker exec api-diag nslookup redis-cache || true
cache=$(docker ps --format '{{.Names}}' | grep -E '^cache-[a-z]+-[0-9]+$')
reseau=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' api-diag)
# Redis rejoint le réseau de l'API, à chaud, sous le nom attendu
docker network connect --alias redis-cache "$reseau" "$cache"
sleep 1
#@ D9.5
#? Un alias donne un nom supplémentaire à un conteneur sur un réseau, et plusieurs conteneurs peuvent partager le même : le DNS renvoie alors toutes leurs adresses.
#? `--network-alias vitrine-interne` au lancement, ou `docker network connect --alias vitrine-interne` à chaud ; aucun port n'est publié.
#? On vérifie depuis un conteneur jetable branché sur le même réseau : `nslookup vitrine-interne` doit afficher les deux adresses.
docker run -d --name vitrine-a --network reseau-boutique --network-alias vitrine-interne nginx:alpine
docker run -d --name vitrine-b --network reseau-boutique --network-alias vitrine-interne nginx:alpine
docker run --rm --network reseau-boutique alpine nslookup vitrine-interne
''',
    10: r'''
#@ D10.1
#? Chaque option de `docker run` a son équivalent dans un service : `build`, `ports`, `environment`, `volumes`, `command`.
#? Compose crée un réseau pour le projet : l'API joint Redis par son nom de service, `REDIS_HOST: redis`.
#? Le volume nommé est déclaré dans la section `volumes:` de premier niveau. Les conteneurs lancés à la main sont supprimés pour libérer le port 3000.
cd ~/projet
# Les conteneurs lancés à la main occupent les noms et les ports : on les supprime
docker rm -f api redis vitrine vitrine-site cache > /dev/null
cat > compose.yaml <<'EOF'
services:
  api:
    build: ./api
    ports:
      - "3000:3000"
    environment:
      REDIS_HOST: redis
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - donnees:/data

volumes:
  donnees:
EOF
docker compose up -d --build
sleep 3
docker compose exec -T api wget -qO- http://localhost:3000/visites
#@ D10.2
#? `web` monte sa configuration et le site en lecture seule, et publie seul le port 8080 : c'est l'unique porte d'entrée, et `api` n'a plus de `ports`.
#? nginx résout le nom `api` de `proxy_pass` à son démarrage : `depends_on: [api]` fait démarrer l'API d'abord, sinon nginx s'arrête (« host not found in upstream »).
#? Le piège : le port 8080 encore occupé par le conteneur `vitrine` du jour 3.
# Ajout du service web ; l'API n'est plus publiée (plus de « ports » sur api)
cat > compose.yaml <<'EOF'
services:
  api:
    build: ./api
    environment:
      REDIS_HOST: redis
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - donnees:/data

  web:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./site:/usr/share/nginx/html:ro
    # nginx résout « api » à son démarrage : l'API doit exister avant lui
    depends_on:
      - api

volumes:
  donnees:
EOF
docker compose up -d
#@ D10.3
#? `depends_on` seul attend que le conteneur soit démarré, pas que le service soit prêt : un healthcheck fondé sur `redis-cli ping` signale quand Redis répond vraiment.
#? La forme longue `depends_on: redis: condition: service_healthy` fait attendre l'API jusqu'à ce que Redis soit healthy.
#? La forme `test: ["CMD", "redis-cli", "ping"]` exécute la commande directement, sans shell ; `CMD-SHELL` avec une chaîne serait aussi valable.
# Healthcheck sur redis, et l'API attend que redis soit « healthy »
cat > compose.yaml <<'EOF'
services:
  api:
    build: ./api
    environment:
      REDIS_HOST: redis
    depends_on:
      redis:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - donnees:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  web:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./site:/usr/share/nginx/html:ro
    depends_on:
      - api

volumes:
  donnees:
EOF
docker compose up -d
#@ D10.4
#? Compose lit le fichier `.env` du dossier du projet et remplace `${APP_VERSION}` dans `compose.yaml` à la lecture du fichier.
#? `docker compose config` montre la configuration réellement appliquée, variable remplacée ; `docker compose up -d` recrée ensuite le service dont la configuration a changé.
#? Le piège : laisser `2.0` écrit en dur dans `compose.yaml`. Passer la version en argument de construction (`build.args`) est aussi accepté par la vérification.
echo "APP_VERSION=2.0" > .env
# Dans compose.yaml, service api : ajout de la variable, lue dans .env
sed -i 's/      REDIS_HOST: redis/      REDIS_HOST: redis\n      APP_VERSION: ${APP_VERSION}/' compose.yaml
docker compose config | grep APP_VERSION
docker compose up -d
sleep 8
#@ D10.5
#? Un service rattaché à un profil (`profiles: [outils]`) est ignoré par un simple `docker compose up`.
#? `docker compose --profile outils run --rm outils redis-cli -h redis ping` le lance à la demande, sur le réseau de la pile, et `--rm` le supprime après usage.
#? Dans votre terminal, `-T` est inutile : il ne sert au corrigé qu'à fonctionner sans terminal.
# Service rattaché à un profil : ignoré par « docker compose up », lancé à la demande
sed -i 's/^volumes:$/  outils:\n    image: redis:7-alpine\n    profiles: [outils]\n\nvolumes:/' compose.yaml
docker compose up -d
docker compose --profile outils run --rm -T outils redis-cli -h redis ping
#@ D10.6
#? Avec `- /data`, le volume est anonyme : il appartient au conteneur, et après `down`, le `up` suivant crée un nouveau conteneur avec un volume neuf, vide.
#? Un volume nommé, déclaré dans la section `volumes:` de premier niveau, survit à `docker compose down` (sauf avec `down -v`) et est remonté au `up` suivant.
#? Le service garde son nom `redis`, comme exigé ; les anciennes données, restées dans l'ancien volume anonyme, ne sont pas reprises automatiquement.
cd ~/stock
# Avec « - /data », chaque nouveau conteneur reçoit un volume anonyme neuf : on nomme le volume
cat > compose.yaml <<'EOF'
# Pile du stock (Diallo) : Redis garde les quantités en stock.
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - stock:/data

volumes:
  stock:
EOF
docker compose up -d
''',
    11: r'''
#@ D11.1
#? Première erreur : l'image lance `serveur.js`, un fichier qui n'existe pas ; le Dockerfile doit lancer `server.js`.
#? Deuxième erreur : dans `ports:`, l'ordre est hôte:conteneur ; l'API écoute sur 3000 dans le conteneur et doit être publiée sur 8090, d'où `"8090:3000"`.
#? Troisième erreur : l'API lit `REDIS_HOST`, pas `REDIS_HOTE`. Chaque correction fait apparaître la suivante : `docker compose ps -a` et `docker compose logs api` à chaque étape.
#? `--build` est indispensable pour que la correction du Dockerfile soit prise en compte.
cd ~/incident
sed -i 's/"3000:8090"/"8090:3000"/; s/REDIS_HOTE/REDIS_HOST/' compose.yaml
sed -i 's/serveur\.js/server.js/' app/Dockerfile
docker compose up -d --build
sleep 5
#@ D11.2
#? `docker image prune` supprime les images pendantes (`<none>`) inutilisées, en gardant `brouillon-marc:latest` et les images de base.
#? Une ancienne version résiste : `prune` ne supprime jamais une image utilisée par un conteneur, même arrêté. `docker ps -a --filter ancestor=<id>` révèle `brouillon-test`.
#? Le piège : `docker image prune -a`, qui supprimerait aussi les images de base, impossibles à retélécharger sans Internet. Variante : `docker rmi <id>` après avoir supprimé le conteneur.
docker images -f dangling=true
docker image prune -f
# Une ancienne version résiste : elle est utilisée par un conteneur arrêté
for i in $(docker images -qf dangling=true); do docker ps -a --filter ancestor=$i; done
docker rm brouillon-test
docker image prune -f
#@ D11.3
#? Code 137 = 128 + 9 : l'import a été tué par SIGKILL, et `.State.OOMKilled` vaut true : le noyau l'a tué parce qu'il dépassait sa limite mémoire de 64 Mo.
#? L'application n'a rien pu écrire dans ses journaux : un SIGKILL ne se capture pas, d'où la mort « sans un mot ».
#? `docker update` modifie la limite même sur un conteneur arrêté ; 128 Mo (avec `--memory-swap` à la même valeur) suffisent, puis `docker start` relance l'import.
#? Variante : recréer le conteneur avec l'image et la commande d'origine, et `--memory 128m --memory-swap 128m`.
# Code 137 (SIGKILL) et OOMKilled=true : tué par le noyau, limite mémoire dépassée
docker inspect -f '{{.State.ExitCode}} {{.State.OOMKilled}} {{.HostConfig.Memory}}' import-compta
echo "Tué par le noyau (OOM) : la limite mémoire de 64 Mo est trop basse pour l'import" > ~/cause.txt
docker update --memory 128m --memory-swap 128m import-compta
docker start -a import-compta
#@ D11.4
#? `docker update --restart` change la politique de redémarrage à chaud, sans recréer ni redémarrer les conteneurs.
#? `unless-stopped` relance après un plantage ou un redémarrage du serveur, sauf arrêt volontaire ; `no` supprime tout redémarrage automatique pour `outil-ponctuel`.
#? Le piège : recréer les conteneurs pour changer leur politique, ou choisir `always`, qui relancerait aussi un conteneur arrêté volontairement au redémarrage du moteur.
# Politiques modifiées à chaud, sans recréer les conteneurs
docker update --restart unless-stopped badgeuse supervision
docker update --restart no outil-ponctuel
''',
}
