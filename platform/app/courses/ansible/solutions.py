"""Corrigé du parcours Ansible : un script par étape, exécuté en tant qu'« etudiant » par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Les données tirées au hasard (messages, demandes) sont relues dans les fichiers remis à l'étudiant.
"""

SOLUTIONS = {
    1: r'''
#@ A1.1
#? Ansible se connecte en SSH sans jamais pouvoir répondre à une question : il faut donc une authentification par clé (plus de mot de passe) et une empreinte de chaque serveur déjà connue dans `~/.ssh/known_hosts`.
#? `ssh-keygen` crée la paire de clés sur le poste de contrôle, `ssh-copy-id` dépose la moitié publique dans `~/.ssh/authorized_keys` du compte `admin` de chaque serveur.
#? Ici, `ssh-keyscan` enregistre les empreintes sans les vérifier, ce qui est acceptable dans ce labo fermé ; en production, on compare l'empreinte à une source sûre avant de répondre « yes ».
#? Le test `ssh -o BatchMode=yes admin@web1 hostname` est le bon réflexe : il échoue au lieu de poser une question, exactement comme le ferait Ansible.
ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519
# Accepter l'empreinte de chaque serveur (ou se connecter une fois à la main, comparer l'empreinte, répondre « yes »)
ssh-keyscan web1 web2 db1 >> ~/.ssh/known_hosts
# Copier la clé publique : ssh-copy-id demande le mot de passe (cimes) ; sshpass le fournit ici
for s in web1 web2 db1; do sshpass -p cimes ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@$s; done
ssh -o BatchMode=yes admin@web1 hostname
#@ A1.2
#? Le suffixe `:children` fait de `production` un groupe de groupes : un serveur ajouté plus tard au groupe `web` sera automatiquement en production, sans toucher à cette section.
#? Le piège était de recopier web1, web2 et db1 sous `[production]` : le résultat semble identique aujourd'hui, mais la liste serait à tenir à jour à la main.
#? `ansible-inventory -i inventaire.ini --graph` affiche l'arborescence des groupes : c'est la façon la plus rapide de vérifier un inventaire sans se connecter aux serveurs.
cd ~/infra
cat > inventaire.ini <<'EOF'
[web]
web1
web2

[bdd]
db1

[production:children]
web
bdd
EOF
ansible-inventory -i inventaire.ini --graph
#@ A1.3
#? Lancé depuis `~/infra`, Ansible lit le fichier `ansible.cfg` du dossier courant : la section `[defaults]` y fixe l'inventaire (`inventory`) et le compte distant (`remote_user`) une fois pour toutes.
#? `ansible-config dump --only-changed` montre les réglages réellement pris en compte : pratique pour repérer une faute de frappe dans un nom de clé, qu'Ansible ne signale pas toujours.
#? Le module `ping` n'est pas un ping réseau : il vérifie toute la chaîne (connexion SSH, Python sur le serveur, exécution d'un module) et répond `pong` si tout fonctionne.
#? Variante acceptée : le compte peut aussi être donné dans l'inventaire (`ansible_user=admin` sous `[all:vars]`, ou dans `group_vars/all.yml`) plutôt que par `remote_user`.
cat > ansible.cfg <<'EOF'
[defaults]
inventory = inventaire.ini
remote_user = admin
EOF
ansible production -m ping
#@ A1.4
#? Un motif combine des groupes : `a:b` pour l'union, `a:&b` pour l'intersection, `a:!b` pour l'exclusion, `a[0]` pour le premier serveur du groupe `a` et `a[-1]` pour le dernier, dans l'ordre de l'inventaire.
#? Le piège était de recopier des noms de serveurs : le motif doit rester juste le jour où le parc change, et seuls des noms de groupes le permettent.
#? Entourez toujours le motif de guillemets simples : sans eux, le shell interprète lui-même `!` et `&` avant qu'Ansible ne les voie.
#? L'ordre des termes ne compte pas (`lyon:&web` vaut `web:&lyon`), et la virgule peut remplacer les deux-points (`web,&lyon`) : seuls les serveurs visés sont vérifiés.
#? `--list-hosts` affiche les serveurs visés sans rien exécuter : c'est le moyen sûr de tester un motif. Les villes du parc et les quatre demandes sont tirées au sort : vos motifs diffèrent de ceux d'un camarade, même quand les phrases se ressemblent.
cat exercices/demandes.txt
# Pour chaque demande, le motif correspondant, vérifié avec --list-hosts (aucune connexion).
# Les villes sont des groupes de l'inventaire : leur nom en minuscules.
: > reponses/motifs.txt
grep -E '^[0-9]\. ' exercices/demandes.txt | while read -r num texte; do
  ville=$(echo "$texte" | grep -oE '(de|à) [A-Z][a-z]+' | head -1 | cut -d' ' -f2 | tr 'A-Z' 'a-z')
  case "$texte" in
    "Les serveurs web de "*) m="web:&$ville" ;;
    "Toute la production, sauf les bases de données.") m='production:!bdd' ;;
    "Les serveurs de recette situés à "*) m="recette:&$ville" ;;
    "Le premier serveur du groupe web"*) m='web[0]' ;;
    "Le dernier serveur du groupe bdd"*) m='bdd[-1]' ;;
    "Tous les serveurs, sauf ceux de "*) m="all:!$ville" ;;
    "Les serveurs de cache et les bases de données.") m='cache:bdd' ;;
    *"qui ne sont pas en production.") m="$ville:!production" ;;
  esac
  echo "$m" >> reponses/motifs.txt
  ansible -i exercices/parc.ini "$m" --list-hosts
done
''',
    2: r'''
#@ A2.4
#? Une empreinte qui change peut signaler une réinstallation… ou une attaque de l'homme du milieu : on ne fait confiance à la nouvelle qu'après l'avoir comparée à une source sûre, ici le message de Léa.
#? `ssh-keygen -R <serveur>` oublie l'ancienne empreinte, puis on enregistre la nouvelle ; comme le serveur est neuf, sa liste de clés autorisées est vide et il faut y réinstaller votre clé publique avec `ssh-copy-id`.
#? Le piège était de désactiver la vérification des empreintes (`host_key_checking = False`, `StrictHostKeyChecking no`) : la connexion passe, mais vous accepteriez n'importe quel serveur, y compris celui d'un attaquant.
#? `StrictHostKeyChecking accept-new` (accepte un serveur inconnu, refuse une empreinte changée) ou `host_key_checking = True` explicite restent permis.
#? Le serveur réinstallé est tiré au sort (db1, web1 ou web2), et son empreinte dépend de votre propre environnement : refaire les commandes d'un camarade ne répare pas forcément le bon serveur.
#? Ce corrigé passe en premier : tant que l'accès au serveur réinstallé n'est pas rétabli, Ansible ne peut plus le joindre, et les autres exercices qui le visent échouent.
cd ~/infra
cat ~/message-lea.txt
s=$(sed -n 's/^Objet : \([a-z0-9]*\) réinstallé$/\1/p' ~/message-lea.txt)
# 1. Comparer l'empreinte présentée par le serveur à l'empreinte officielle
officielle=$(grep -oE 'SHA256:[^ ]+' ~/message-lea.txt)
presentee=$(ssh-keyscan -t ed25519 $s 2>/dev/null | ssh-keygen -lf - | awk '{print $2}')
[ "$officielle" = "$presentee" ] && echo "Empreinte conforme : on peut lui faire confiance"
# 2. Oublier l'ancien serveur, enregistrer le nouveau (empreinte vérifiée), réinstaller la clé publique
ssh-keygen -R $s
ssh-keyscan $s >> ~/.ssh/known_hosts 2>/dev/null
sshpass -p cimes ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@$s
ssh -o BatchMode=yes admin@$s hostname
#@ A2.1
#? Ansible n'installe aucun agent : pour chaque tâche, il emballe le module dans un fichier `AnsiballZ_<module>.py`, l'envoie par SSH dans un dossier temporaire du serveur, l'exécute avec le Python du serveur, lit le JSON renvoyé, puis efface le tout.
#? Avec `-vvv`, la ligne `PUT` montre l'envoi du fichier et son dossier de destination, et la ligne `EXEC` montre l'interpréteur qui l'exécute.
#? Le piège était de confondre les deux dossiers temporaires : `ansible-local-…` est sur le poste de contrôle, alors que la réponse attendue est celui du serveur, sous `/home/admin/.ansible/tmp`.
#? La commande de Julien est tirée au sort : le module (donc le nom du fichier) et le serveur visé peuvent différer des vôtres.
cat ~/message-julien.txt
# La commande de Julien, en mode très bavard
cmd=$(grep -E '^ +ansible ' ~/message-julien.txt | sed 's/^ *//')
eval "$cmd -vvv" > /tmp/vvv.txt 2>&1
# « PUT <fichier local> TO <dossier du serveur>/AnsiballZ_<module>.py » : le fichier envoyé et son dossier
grep -o "AnsiballZ_[a-z_]*\.py" /tmp/vvv.txt | head -1 > reponses/module.txt
grep " PUT " /tmp/vvv.txt | grep -o "TO /home/admin/[^ ]*" | head -1 | sed 's|^TO ||; s|/AnsiballZ.*||' >> reponses/module.txt
# « EXEC … /bin/sh -c '<interpréteur> …/AnsiballZ_<module>.py' » : l'interpréteur Python du serveur
grep " EXEC " /tmp/vvv.txt | grep AnsiballZ | grep -o "/usr/bin/python3[.0-9]*" | head -1 >> reponses/module.txt
cat reponses/module.txt
#@ A2.2
#? Les facts sont ce qu'Ansible collecte sur un serveur (module `setup`) ; l'option `filter` évite de parcourir des centaines de lignes.
#? Un serveur peut déclarer ses propres facts dans `/etc/ansible/facts.d/<nom>.fact` : ici, le fichier `materiel.fact` apparaît sous `ansible_local.materiel`, section `contrat`, clé `numero_serie`.
#? Les numéros de série sont tirés au sort à chaque préparation de l'étape : les vôtres diffèrent forcément de ceux d'un camarade.
ansible web -m setup -a "filter=ansible_distribution_version"
ansible web -m setup -a "filter=ansible_local"
: > reponses/materiel.csv
for s in web1 web2; do
  v=$(ansible $s -m setup -a "filter=ansible_distribution_version" | grep -o '"ansible_distribution_version": "[^"]*"' | cut -d'"' -f4)
  n=$(ansible $s -m setup -a "filter=ansible_local" | grep -o '"numero_serie": "[^"]*"' | cut -d'"' -f4)
  echo "$s;$v;$n" >> reponses/materiel.csv
done
cat reponses/materiel.csv
#@ A2.3
#? Les modules `user` et `copy` décrivent un état voulu : relancées, ces commandes ne changent plus rien, contrairement à un `useradd` qui échouerait au second passage.
#? `append=true` ajoute `www-data` aux groupes secondaires existants au lieu de remplacer toute la liste, et `-b` fait passer Ansible par sudo pour agir en root.
#? Le piège était de se connecter aux serveurs pour taper `sudo useradd` : la vérification lit `/var/log/sudo.log` et distingue les commandes d'Ansible de celles tapées à la main.
#? Cibler le groupe `web`, et non `all`, laisse db1 intact. L'UID demandé par Thomas est tiré au sort : le vôtre peut différer de celui de ce corrigé.
cat ~/message-thomas.txt
uid=$(grep -oE 'UID [0-9]+' ~/message-thomas.txt | cut -d' ' -f2)
ansible web -b -m user -a "name=deploy uid=$uid groups=www-data append=true shell=/bin/bash"
ansible web -b -m copy -a "dest=/etc/motd content='Serveur géré par Ansible - ne pas modifier à la main\n'"
#@ A2.5
#? Le module `find` cherche sur tous les serveurs à la fois ; `-b` est indispensable, car certains dossiers ne sont lisibles que par root et seraient sinon ignorés.
#? Le motif `clients-*.csv` porte sur le nom complet du fichier : il écarte les leurres comme `clients.csv.gpg`, `clients-….csv.bak` ou `fournisseurs-….csv`.
#? Le piège était un motif trop large, ou une suppression lancée sur `all` : on supprime avec `file state=absent` sur le seul serveur concerné, après avoir regardé ce que `find` a trouvé.
#? Le serveur, le dossier et le code du fichier sont tirés au sort : votre export n'était sans doute pas au même endroit.
# Chercher partout (-b : certains dossiers ne sont lisibles que par root), puis supprimer sur le seul serveur concerné
ansible all -b -m find -a "paths=/srv,/home,/var/backups patterns='clients-*.csv' recurse=yes"
for s in web1 web2 db1; do
  f=$(ansible $s -b -m find -a "paths=/srv,/home,/var/backups patterns='clients-*.csv' recurse=yes" | grep -o '"path": "[^"]*"' | cut -d'"' -f4)
  if [ -n "$f" ]; then
    echo "$s:$f" > reponses/rgpd.txt
    ansible $s -b -m file -a "path=$f state=absent"
  fi
done
cat reponses/rgpd.txt
''',
    3: r'''
#@ A3.1
#? Un playbook décrit un état : « nginx présent, démarré, activé au démarrage ». Les modules `apt` et `service` ne font que ce qui manque, d'où `changed=0` au second passage.
#? `hosts: web` limite le play aux serveurs web, db1 n'est donc jamais touché ; `become: true` est nécessaire pour installer un paquet.
#? Le piège classique sur un serveur neuf est l'erreur « No package matching » : le cache APT est vide, d'où `update_cache: true`, et `cache_valid_time: 3600` évite de le rafraîchir à chaque passage.
#? `ansible.builtin.package` au lieu d'`apt`, des noms courts (`apt:`, `service:`) ou `become: true` sur chaque tâche plutôt que sur le play donnent le même résultat.
cd ~/infra
cat > web.yml <<'EOF'
- name: Serveurs web de la boutique
  hosts: web
  become: true
  tasks:
    - name: Installer nginx
      ansible.builtin.apt:
        name: nginx
        state: present
        update_cache: true
        cache_valid_time: 3600

    - name: nginx démarré, et lancé au démarrage du serveur
      ansible.builtin.service:
        name: nginx
        state: started
        enabled: true
EOF
ansible-playbook web.yml
#@ A3.2
#? Le module `copy` compare l'empreinte du fichier local à celle du fichier distant : il ne copie (et ne répond `changed`) que si le contenu diffère.
#? Un `src:` relatif est cherché à côté du playbook : `fichiers/index.html` désigne donc `~/infra/fichiers/index.html`.
#? `template` au lieu de `copy`, ou `dest: /var/www/html/` (un dossier : le nom du fichier source est repris), conviennent aussi.
#? Écrivez toujours les droits entre guillemets avec le zéro initial (`"0644"`) : sans guillemets, YAML lit un entier décimal et les droits obtenus sont absurdes.
cat >> web.yml <<'EOF'

    - name: Page d'accueil de la boutique
      ansible.builtin.copy:
        src: fichiers/index.html
        dest: /var/www/html/index.html
        mode: "0644"
EOF
ansible-playbook web.yml
#@ A3.3
#? Chaque commande de Julien est remplacée par le module qui décrit l'état voulu : `file` pour le dossier, `lineinfile` pour la ligne d'annonce, `apt` pour l'outil tree.
#? `lineinfile` n'ajoute la ligne que si elle est absente, alors qu'un `echo … >>` l'ajoute à chaque passage : c'est ce qui dupliquait l'annonce.
#? Le piège était de garder des tâches `command` ou `shell` : Ansible ne sait pas ce qu'elles modifient et répond toujours `changed`, si bien que le second passage n'est jamais à `changed=0`.
#? La date de l'annonce est tirée au sort : la vôtre peut différer de celle de ce corrigé.
# Chaque commande de Julien devient la description de l'état qu'elle cherchait à obtenir
jour=$(sed -n 's/.*echo "Maintenance prévue le \(.*\)" >>.*/\1/p' fichiers/julien-taches.yml)
cat >> web.yml <<EOF

    - name: Dossier des promotions, modifiable par l'équipe web
      ansible.builtin.file:
        path: /var/www/html/promo
        state: directory
        owner: www-data
        group: www-data
        mode: "0755"

    - name: Annonce de la maintenance (une seule fois)
      ansible.builtin.lineinfile:
        path: /var/www/html/promo/annonce.txt
        line: "Maintenance prévue le $jour"
        create: true
        owner: www-data
        group: www-data
        mode: "0644"

    - name: L'outil tree pour l'équipe
      ansible.builtin.apt:
        name: tree
        state: present
EOF
ansible-playbook web.yml
ansible-playbook web.yml     # second passage : changed=0
#@ A3.4
#? Les défauts se corrigent un par un, en relisant les erreurs : tabulation interdite en YAML, `{{ }}` en début de valeur sans guillemets, valeur de `state` inconnue du module `apt`, nom de module erroné, `become` absent.
#? `mode: 750` sans guillemets est l'entier décimal 750, soit 1356 en octal : les droits s'écrivent en octal, entre guillemets et avec le zéro initial, en traduisant ceux de l'en-tête (`rwxr-x---` donne `"0750"` : r = 4, w = 2, x = 1 pour chaque tiers).
#? Le défaut le plus sournois est `hosts: tous` : aucun groupe ne porte ce nom, Ansible affiche « no hosts matched » et termine sans erreur… sans rien avoir fait. Lisez toujours le récapitulatif.
#? L'outil, les droits, le propriétaire et le nom du dossier de travail sont tirés au sort : le playbook réparé d'un camarade ne ferait pas ce que votre Marc a prévu.
ansible-playbook marc/outils.yml --syntax-check || true
# Défauts possibles : tabulation, {{ }} sans guillemets, state: installed, module « fille », become absent,
# mode sans guillemets (décimal !), et surtout hosts: tous, qui ne correspond à aucun groupe (« no hosts matched »)
# Ce que Marc a prévu : l'en-tête et les variables du fichier
head -3 marc/outils.yml
dossier=$(grep -o '/opt/cimes/[a-z-]*' marc/outils.yml)
paquet=$(sed -n 's/^    paquet: *//p' marc/outils.yml)
proprio=$(sed -n 's/^# (droits [rwx-]*, propriétaire \(.*\))\.$/\1/p' marc/outils.yml)
rwx=$(grep -oE 'droits [rwx-]{9}' marc/outils.yml | cut -d' ' -f2)
# rwx → octal : r = 4, w = 2, x = 1, pour le propriétaire, le groupe et les autres
mode=0
for i in 0 3 6; do
  c=0
  [ "${rwx:$i:1}" = r ] && c=$((c + 4))
  [ "${rwx:$((i + 1)):1}" = w ] && c=$((c + 2))
  [ "${rwx:$((i + 2)):1}" = x ] && c=$((c + 1))
  mode="$mode$c"
done
echo "$paquet, $dossier : $rwx = $mode, propriétaire $proprio"
cat > marc/outils.yml <<EOF
# Outils de Marc : $paquet sur tous les serveurs de production, et un dossier de travail
# (droits $rwx, propriétaire $proprio).
- name: Outils de Marc
  hosts: production
  become: true
  vars:
    paquet: $paquet
    dossier: $dossier
  tasks:
    - name: Installer l'outil
      ansible.builtin.apt:
        name: "{{ paquet }}"
        state: present
        update_cache: true
        cache_valid_time: 3600

    - name: Dossier de travail
      ansible.builtin.file:
        path: "{{ dossier }}"
        state: directory
        owner: $proprio
        mode: "$mode"
EOF
ansible-playbook marc/outils.yml
ansible-playbook marc/outils.yml     # changed=0
''',
    4: r'''
#@ A4.1
#? Les fichiers de `group_vars/` placés à côté de l'inventaire sont chargés automatiquement : `group_vars/web.yml` définit des variables pour le groupe `web`, et pour lui seul.
#? Le module `template` génère le fichier avec Jinja2 sur le poste de contrôle : `{{ inventory_hostname }}` donne une page différente sur chaque serveur, à partir d'un seul modèle.
#? Les pièges étaient d'écrire le slogan en dur dans le modèle, ou de définir les variables dans `group_vars/all.yml`, ce qui les aurait aussi données à db1.
#? Le slogan est tiré au sort : le vôtre peut différer de celui de ce corrigé.
cd ~/infra
mkdir -p group_vars templates
slogan=$(tail -1 ~/demandes/slogan.txt)
cat > group_vars/web.yml <<EOF
environnement: production
slogan: "$slogan"
EOF
cat > templates/index.html.j2 <<'EOF'
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Cimes & Sentiers</title></head>
<body>
  <h1>Boutique Cimes & Sentiers</h1>
  <p>{{ slogan }}</p>
  <p>Serveur : {{ inventory_hostname }}</p>
  <p>Environnement : {{ environnement }}</p>
</body>
</html>
EOF
# Dans web.yml, la page est désormais générée par le module template
sed -i 's|ansible.builtin.copy:|ansible.builtin.template:|; s|src: fichiers/index.html|src: templates/index.html.j2|' web.yml
ansible-playbook web.yml
#@ A4.2
#? `host_vars/web2.yml` définit des variables pour le seul serveur web2 ; elles l'emportent sur celles du groupe (`group_vars/web.yml`), sans toucher ni au modèle ni au playbook.
#? `ansible-inventory --host web2` affiche les variables fusionnées de web2 : on y voit `environnement: recette` avant même de lancer le playbook.
#? Le piège était de modifier `group_vars/web.yml` ou d'ajouter un test dans le modèle : on décrit une exception au bon niveau, celui du serveur.
#? Une variable d'hôte dans l'inventaire (`web2 environnement=recette`) ou un dossier `host_vars/web2/` conviennent aussi : les variables d'hôte l'emportent toujours sur celles du groupe.
mkdir -p host_vars
echo "environnement: recette" > host_vars/web2.yml
ansible-inventory --host web2
ansible-playbook web.yml
#@ A4.3
#? L'adresse vient d'un fact (`ansible_facts['default_ipv4']['address']`) collecté au début du jeu : si le réseau change, la page suit toute seule.
#? `groups['web']` donne la liste des serveurs du groupe dans l'ordre de l'inventaire, et `hostvars[h]` permet de lire les variables d'un autre serveur que celui en cours.
#? `loop.last` évite la virgule après le dernier serveur : un web3 ajouté plus tard apparaîtra sans aucune modification du modèle.
#? La forme `{{ ansible_default_ipv4.address }}` est aussi acceptée : ansible-core 2.18 injecte encore les facts comme variables `ansible_*` par défaut.
# L'adresse vient des facts du serveur ; la ferme, des variables magiques groups et hostvars
sed -i "s|  <p>Environnement : {{ environnement }}</p>|&\n  <p>Adresse : {{ ansible_facts['default_ipv4']['address'] }}</p>\n  <p>Ferme : {% for h in groups['web'] %}{{ h }} ({{ hostvars[h]['environnement'] }}){% if not loop.last %}, {% endif %}{% endfor %}</p>|" templates/index.html.j2
ansible-playbook web.yml
#@ A4.4
#? Quand une variable est définie à plusieurs endroits, la plus spécifique l'emporte : `host_vars` passe avant tout ce qui concerne les groupes, et un groupe enfant (`web`) passe avant son parent (`production`), qui passe avant `all`.
#? Plutôt que de raisonner de tête, ce corrigé fait parler Ansible : on modifie la valeur dans un seul fichier à la fois et `ansible-inventory --host` montre quels serveurs la reprennent.
#? Le piège était de répondre « le dernier fichier lu » ou « celui qui est le plus bas dans l'arborescence » : seule la priorité d'Ansible compte.
#? Les fichiers présents dans la copie de Julien sont tirés au sort : vos trois réponses peuvent différer de celles d'un camarade.
# Toutes les valeurs sont identiques : on en change une à la fois, et on regarde quels serveurs suivent
cd ~/infra/exercices/precedence
declare -A source
for f in inventaire.ini group_vars/all.yml group_vars/production.yml group_vars/web.yml host_vars/web2.yml; do
  [ -f $f ] || continue
  sed -i 's/Sentiers"/Sentiers-essai"/' $f
  for h in web1 web2 db1; do
    ansible-inventory -i inventaire.ini --host $h | grep -q "Sentiers-essai" && source[$h]=$f
  done
  sed -i 's/Sentiers-essai"/Sentiers"/' $f
done
for h in web1 web2 db1; do echo "$h=${source[$h]}"; done > ~/infra/reponses/precedence.txt
cat ~/infra/reponses/precedence.txt
cd ~/infra
''',
    5: r'''
#@ A5.1
#? Un handler est une tâche qui ne s'exécute que si une tâche l'a notifiée (`notify`) et que cette tâche a répondu `changed` ; il est lancé à la fin du play, une seule fois même s'il a été notifié plusieurs fois.
#? nginx n'est donc rechargé que lorsque sa configuration change réellement ; `state: reloaded` relit la configuration sans couper les connexions en cours, contrairement à `restarted`.
#? Le modèle remplace le site par défaut de Debian (`sites-available/default`) : c'est ce qui fait disparaître l'écoute sur le port 80.
#? Le piège était une tâche qui recharge nginx à chaque passage : le playbook ne serait jamais à `changed=0`.
#? Le handler peut aussi utiliser `state: restarted`, un nom d'écoute (`listen:`), ou la commande `nginx -s reload` : seul compte qu'il ne s'exécute que sur notification.
cd ~/infra
echo "http_port: 8080" >> group_vars/web.yml
cat > templates/site.conf.j2 <<'EOF'
server {
    listen {{ http_port }} default_server;
    root /var/www/html;
    index index.html;
}
EOF
jour=$(sed -n 's/.*line: "Maintenance prévue le \(.*\)"/\1/p' web.yml)
cat > web.yml <<EOF
- name: Serveurs web de la boutique
  hosts: web
  become: true
  tasks:
    - name: Installer nginx
      ansible.builtin.apt:
        name: nginx
        state: present
        update_cache: true
        cache_valid_time: 3600

    - name: nginx démarré, et lancé au démarrage du serveur
      ansible.builtin.service:
        name: nginx
        state: started
        enabled: true

    - name: Configuration du site
      ansible.builtin.template:
        src: templates/site.conf.j2
        dest: /etc/nginx/sites-available/default
        mode: "0644"
      notify: Recharger nginx

    - name: Page d'accueil de la boutique
      ansible.builtin.template:
        src: templates/index.html.j2
        dest: /var/www/html/index.html
        mode: "0644"

    - name: Dossier des promotions, modifiable par l'équipe web
      ansible.builtin.file:
        path: /var/www/html/promo
        state: directory
        owner: www-data
        group: www-data
        mode: "0755"

    - name: Annonce de la maintenance (une seule fois)
      ansible.builtin.lineinfile:
        path: /var/www/html/promo/annonce.txt
        line: "Maintenance prévue le $jour"
        create: true
        owner: www-data
        group: www-data
        mode: "0644"

    - name: L'outil tree pour l'équipe
      ansible.builtin.apt:
        name: tree
        state: present

  handlers:
    - name: Recharger nginx
      ansible.builtin.service:
        name: nginx
        state: reloaded
EOF
ansible-playbook web.yml
#@ A5.2
#? Les handlers attendent normalement la fin du play : sans `meta: flush_handlers`, le test s'exécuterait alors que nginx écoute encore sur l'ancien port.
#? Le module `uri` échoue si le code HTTP n'est pas 200 (valeur par défaut de `status_code`) : une page illisible (403) fait donc échouer le jeu, comme demandé.
#? `-e http_port=8089` a la priorité la plus forte : le modèle change, le handler recharge nginx, le test vise 8089. Relancé normalement, tout revient sur 8080, puis un troisième passage ne recharge plus rien.
#? Variante acceptée : placer le test dans `post_tasks`, car les handlers notifiés par `tasks` sont exécutés à la fin de cette section, avant `post_tasks`.
# Les handlers en attente sont exécutés AVANT le test : sinon nginx n'écoute pas encore sur le nouveau port
cat > /tmp/fumee.yml <<'EOF'
    - name: Recharger nginx maintenant si la configuration a changé
      ansible.builtin.meta: flush_handlers

    - name: Test de fumée, la boutique répond sur son port
      ansible.builtin.uri:
        url: "http://localhost:{{ http_port }}/"

EOF
sed -i '/^  handlers:/e cat /tmp/fumee.yml' web.yml
ansible-playbook web.yml -e http_port=8089
ansible-playbook web.yml
ansible-playbook web.yml     # changed=0, handler non exécuté
#@ A5.3
#? `validate` teste le fichier candidat avant de le mettre en place : `%s` est remplacé par le chemin d'une copie temporaire, et si la commande échoue, la configuration en place n'est pas touchée.
#? `nginx -t` ne sait tester qu'une configuration complète : un bloc `server` isolé, hors de tout bloc `http`, serait refusé même s'il est correct. D'où le petit script, déployé par Ansible avant la configuration, qui l'enveloppe dans une configuration minimale.
#? Le piège était de compter sur le refus de nginx au rechargement : la configuration cassée serait tout de même sur le disque, prête à faire tomber le site au prochain redémarrage.
# Un petit script teste un fichier de site dans une configuration nginx minimale mais complète
cat > /tmp/testeur.yml <<'EOF'
    - name: Script de test des configurations de site nginx
      ansible.builtin.copy:
        dest: /usr/local/sbin/tester-site-nginx
        mode: "0755"
        content: |
          #!/bin/sh
          # Teste le fichier de site $1 dans une configuration nginx minimale et complète
          printf 'events {}\nhttp {\n  include /etc/nginx/mime.types;\n  include %s;\n}\n' "$1" > /tmp/test-site-nginx.conf
          exec nginx -t -q -c /tmp/test-site-nginx.conf

EOF
sed -i '/^    - name: Configuration du site$/e cat /tmp/testeur.yml' web.yml
sed -i 's|^        dest: /etc/nginx/sites-available/default$|&\n        validate: /usr/local/sbin/tester-site-nginx %s|' web.yml
ansible-playbook web.yml
ansible-playbook web.yml -e http_port=abc || echo "Refusé, comme prévu : la configuration en place n'a pas bougé"
#@ A5.4
#? Par défaut, quand une tâche échoue sur un serveur, celui-ci est retiré du jeu, et les handlers qu'il avait en attente ne sont jamais exécutés : la configuration est modifiée, mais nginx n'est pas rechargé.
#? `force_handlers: true` au niveau du play exécute quand même les handlers notifiés ; `force_handlers = True` dans la section `[defaults]` d'`ansible.cfg` est une variante également acceptée.
#? L'option `--force-handlers` de la ligne de commande a le même effet, mais elle dépend de la mémoire de la personne qui lance le playbook : l'écrire dans le code est plus sûr.
#? Autre variante acceptée : un `block` dont le `rescue` exécute `meta: flush_handlers` avant d'échouer (`fail`).
# Même si une tâche échoue ensuite, les handlers notifiés sont exécutés
sed -i 's/^  become: true$/&\n  force_handlers: true/' web.yml
ansible-playbook web.yml
''',
    6: r'''
#@ A6.1
#? `loop` répète une seule tâche pour chaque élément de la liste, disponible dans `{{ item }}` : ajouter une personne revient à ajouter une ligne dans `group_vars/web.yml`, sans toucher au playbook.
#? `append: true` ajoute `www-data` aux groupes existants de chaque compte au lieu de remplacer la liste.
#? Le piège était de copier-coller une tâche par personne. Les prénoms de l'équipe sont tirés au sort : les vôtres diffèrent de ceux d'un camarade.
cd ~/infra
{ echo "equipe_web:"; grep -E '^[a-z]+$' ~/demandes/equipe.txt | sed 's/^/  - /'; } >> group_vars/web.yml
cat > /tmp/comptes.yml <<'EOF'
    - name: Comptes de l'équipe web
      ansible.builtin.user:
        name: "{{ item }}"
        groups: www-data
        append: true
        shell: /bin/bash
      loop: "{{ equipe_web }}"

EOF
# Insertion de la tâche avant le test de fumée
sed -i '/^    - name: Recharger nginx maintenant/e cat /tmp/comptes.yml' web.yml
ansible-playbook web.yml
#@ A6.2
#? `when:` s'évalue pour chaque serveur : la tâche est exécutée sur web2 (recette) et marquée `skipping` sur web1 ; l'expression s'écrit sans `{{ }}`.
#? Dans le modèle, `{% if … %}…{% endif %}` joue le même rôle : le bandeau n'est écrit que sur les pages des serveurs de recette.
#? Le piège était de viser web2 par son nom : la condition porte sur la variable `environnement`, donc un futur serveur de recette recevra lui aussi le bandeau et htop.
#? `package` au lieu d'`apt`, ou un `block` portant le `when:` et contenant la tâche d'installation, conviennent aussi.
cat > /tmp/htop.yml <<'EOF'
    - name: Outils de diagnostic, en recette seulement
      ansible.builtin.apt:
        name: htop
        state: present
      when: environnement == "recette"

EOF
sed -i '/^    - name: Recharger nginx maintenant/e cat /tmp/htop.yml' web.yml
# Bandeau dans le modèle, juste après <body>
sed -i 's|<body>|<body>\n{% if environnement == "recette" %}\n  <div class="bandeau">RECETTE - site de test</div>\n{% endif %}|' templates/index.html.j2
ansible-playbook web.yml
#@ A6.3
#? Une seule liste de fiches alimente deux tâches : `selectattr('actif')` garde les actifs pour créer leurs comptes, `rejectattr('actif')` garde les anciens pour les supprimer.
#? `state: absent` avec `remove: true` supprime le compte et son dossier personnel ; sans `remove`, les fichiers des anciens resteraient sur le disque.
#? Variante acceptée : une seule tâche sur `personnel`, avec `state: "{{ item.actif | ternary('present', 'absent') }}"` et `remove: "{{ not item.actif }}"`.
#? Le piège était d'écrire `actif: "false"` entre guillemets : c'est une chaîne non vide, donc considérée comme vraie, et l'ancien garderait son compte. Les booléens s'écrivent `true` et `false`, sans guillemets.
#? La composition de l'équipe est tirée au sort : vos noms diffèrent de ceux d'un camarade.
# Une seule liste de fiches, tirée de equipe.csv, remplace equipe_web
grep -E '^(environnement|slogan|http_port):' group_vars/web.yml > /tmp/web-vars.yml
{
  cat /tmp/web-vars.yml
  echo "personnel:"
  tail -n +2 ~/demandes/equipe.csv | while IFS=';' read -r nom statut; do
    echo "  - nom: $nom"
    if [ "$statut" = actif ]; then echo "    actif: true"; else echo "    actif: false"; fi
  done
} > group_vars/web.yml
cat group_vars/web.yml
# Les deux tâches de comptes, alimentées par la même liste
cat > /tmp/comptes.yml <<'EOF'
    - name: Comptes des membres actifs de l'équipe web
      ansible.builtin.user:
        name: "{{ item }}"
        groups: www-data
        append: true
        shell: /bin/bash
      loop: "{{ personnel | selectattr('actif') | map(attribute='nom') | list }}"

    - name: Plus aucun compte (ni dossier) pour les anciens
      ansible.builtin.user:
        name: "{{ item }}"
        state: absent
        remove: true
      loop: "{{ personnel | rejectattr('actif') | map(attribute='nom') | list }}"

EOF
# Remplacement de l'ancienne tâche (de son nom jusqu'à la ligne vide qui la suit)
sed -i "/^    - name: Comptes de l'équipe web$/,/^$/d" web.yml
sed -i '/^    - name: Outils de diagnostic, en recette seulement/e cat /tmp/comptes.yml' web.yml
ansible-playbook web.yml
ansible-playbook web.yml     # changed=0
#@ A6.4
#? Une valeur entre guillemets (`"false"`, `"no"`, `"off"`…) est une chaîne : non vide, elle est vraie pour `when`, et elle n'est jamais égale au booléen `true` ni au booléen `false`. `type_debug` le révèle en affichant `str`.
#? Le filtre `| bool` convertit les chaînes `"true"`, `"false"`, `"yes"`, `"no"`, `"on"`, `"off"`… en vrais booléens ; c'est indispensable ici, car `-e variable=false` passe toujours une chaîne.
#? Retirer les guillemets dans les fichiers de Julien ne suffisait donc pas : seul `| bool` fonctionne aussi avec `-e`. Une valeur JSON (`-e '{"maintenance": false}'`) donnerait un vrai booléen, mais on ne peut pas compter sur tous les utilisateurs pour y penser.
#? Le nom de la variable, ses valeurs, l'écriture des conditions et le serveur mis en maintenance sont tirés au sort : le playbook réparé d'un camarade ne fonctionnerait pas chez vous.
# Le nom de la variable de Julien, et sa valeur (avec son type) sur chaque serveur
var=$(sed -n 's/^\([a-z_]*\): .*/\1/p' julien/group_vars/web.yml)
ansible web -m debug -a "msg={{ $var | type_debug }} {{ $var }}" --playbook-dir julien
# Une chaîne non vide est vraie, et n'est égale à aucun booléen ; -e passe toujours des chaînes : | bool
sed -i -E "s/^( +when: )not $var\$/\1not ($var | bool)/; s/^( +when: )$var( == (true|false))?\$/\1$var | bool\2/" julien/maintenance.yml
grep 'when:' julien/maintenance.yml
ansible-playbook julien/maintenance.yml
ansible-playbook julien/maintenance.yml -e $var=false
ansible-playbook julien/maintenance.yml
''',
    7: r'''
#@ A7.1
#? `--check --diff` compare les serveurs à ce que décrit le code, sans rien modifier : les serveurs qui ont une tâche `changed` sont ceux qui ont dérivé.
#? Le mode vérification ne voit pas ce que le code ne décrit pas : la page de promotion ajoutée à la main se cherche avec un module (`find` avec `contains`, ou `grep` via `command`).
#? Le piège était de corriger en SSH avec sudo : on ajouterait une dérive de plus. On supprime avec `file state=absent`, puis on rejoue le playbook pour revenir à l'état décrit.
#? Les serveurs modifiés, ainsi que le serveur et l'emplacement de la page ajoutée (parfois dans un sous-dossier, d'où `recurse=yes`), sont tirés au sort : les réponses d'un camarade ne sont pas les vôtres.
cd ~/infra
# 1. Les écarts avec le code : le mode vérification les voit
ansible-playbook web.yml --check --diff
ansible-playbook web.yml --check | grep -oE "changed: \[web[0-9]\]" | grep -oE "web[0-9]" | sort -u > reponses/derive.txt
cat reponses/derive.txt
# 2. Ce que le code ne décrit pas : il faut le chercher (ici, toute page qui parle de promotion)
for s in web1 web2; do
  for f in $(ansible $s -b -m find -a "paths=/var/www/html patterns=*.html contains=.*Promo.* recurse=yes" | grep -o '"path": "[^"]*"' | cut -d'"' -f4); do
    if [ "$f" != /var/www/html/index.html ]; then
      echo "$s:$f" > reponses/fantome.txt
      ansible $s -b -m file -a "path=$f state=absent"
    fi
  done
done
cat reponses/fantome.txt
# 3. Retour à l'état décrit
ansible-playbook web.yml
#@ A7.2
#? Un rôle range tâches, handlers, modèles et valeurs par défaut dans une arborescence standard : dans un rôle, `src: index.html.j2` est cherché dans `roles/web/templates/`.
#? `defaults/main.yml` a la priorité la plus faible de toutes : ces valeurs servent si rien d'autre ne les définit, et `group_vars` ou `host_vars` les surchargent.
#? Le piège était de mettre ces valeurs dans `vars/main.yml`, dont la priorité dépasse celle de `host_vars` : web2 ne serait plus en recette (c'est exactement l'incident du jour 8).
#? `site.yml` ne contient plus que la cible, `become` et la liste des rôles : c'est le point d'entrée de toute l'infrastructure.
#? Un rôle créé à la main (sans `ansible-galaxy init`), des tâches réparties en plusieurs fichiers avec `import_tasks`, ou des fichiers `main.yaml`, sont aussi acceptés.
ansible-galaxy init --init-path roles web
mv templates/*.j2 roles/web/templates/
jour=$(sed -n 's/.*line: "Maintenance prévue le \(.*\)"/\1/p' web.yml)
cat > roles/web/tasks/main.yml <<EOF
- name: Installer nginx
  ansible.builtin.apt:
    name: nginx
    state: present
    update_cache: true
    cache_valid_time: 3600

- name: nginx démarré, et lancé au démarrage du serveur
  ansible.builtin.service:
    name: nginx
    state: started
    enabled: true

- name: Script de test des configurations de site nginx
  ansible.builtin.copy:
    dest: /usr/local/sbin/tester-site-nginx
    mode: "0755"
    content: |
      #!/bin/sh
      # Teste le fichier de site \$1 dans une configuration nginx minimale et complète
      printf 'events {}\nhttp {\n  include /etc/nginx/mime.types;\n  include %s;\n}\n' "\$1" > /tmp/test-site-nginx.conf
      exec nginx -t -q -c /tmp/test-site-nginx.conf

- name: Configuration du site
  ansible.builtin.template:
    src: site.conf.j2
    dest: /etc/nginx/sites-available/default
    validate: /usr/local/sbin/tester-site-nginx %s
    mode: "0644"
  notify: Recharger nginx

- name: Page d'accueil de la boutique
  ansible.builtin.template:
    src: index.html.j2
    dest: /var/www/html/index.html
    mode: "0644"

- name: Dossier des promotions, modifiable par l'équipe web
  ansible.builtin.file:
    path: /var/www/html/promo
    state: directory
    owner: www-data
    group: www-data
    mode: "0755"

- name: Annonce de la maintenance (une seule fois)
  ansible.builtin.lineinfile:
    path: /var/www/html/promo/annonce.txt
    line: "Maintenance prévue le $jour"
    create: true
    owner: www-data
    group: www-data
    mode: "0644"

- name: L'outil tree pour l'équipe
  ansible.builtin.apt:
    name: tree
    state: present

- name: Comptes des membres actifs de l'équipe web
  ansible.builtin.user:
    name: "{{ item }}"
    groups: www-data
    append: true
    shell: /bin/bash
  loop: "{{ personnel | selectattr('actif') | map(attribute='nom') | list }}"

- name: Plus aucun compte (ni dossier) pour les anciens
  ansible.builtin.user:
    name: "{{ item }}"
    state: absent
    remove: true
  loop: "{{ personnel | rejectattr('actif') | map(attribute='nom') | list }}"

- name: Outils de diagnostic, en recette seulement
  ansible.builtin.apt:
    name: htop
    state: present
  when: environnement == "recette"

- name: Recharger nginx maintenant si la configuration a changé
  ansible.builtin.meta: flush_handlers

- name: Test de fumée, la boutique répond sur son port
  ansible.builtin.uri:
    url: "http://localhost:{{ http_port }}/"
EOF
cat > roles/web/handlers/main.yml <<'EOF'
- name: Recharger nginx
  ansible.builtin.service:
    name: nginx
    state: reloaded
EOF
# Valeurs par défaut, surchargées par group_vars et host_vars (rien dans vars/main.yml)
cat > roles/web/defaults/main.yml <<'EOF'
http_port: 80
environnement: production
personnel: []
EOF
cat > site.yml <<'EOF'
- name: Serveurs web
  hosts: web
  become: true
  force_handlers: true
  roles:
    - web
EOF
ansible-playbook site.yml
ansible-playbook site.yml    # changed=0
#@ A7.3
#? `--check` ne signale que les écarts avec ce que décrit le code ; un compte que le code ne mentionne pas lui est invisible.
#? On le trouve en lisant, avec Ansible, les fichiers de `/etc/sudoers.d` : `admin` (le compte d'administration) et `journal` (le journal de sudo) sont légitimes, l'intrus donne tous les droits au compte oublié.
#? La solution est de décrire l'absence : `user` avec `state: absent` et `remove: true` pour le compte et son dossier, `file` avec `state: absent` pour son fichier de sudoers (dont le nom n'est pas forcément celui du compte).
#? Supprimer le compte à la main ne suffisait pas : s'il est recréé, seul le code le fera disparaître au passage suivant, tout en restant à `changed=0` quand il n'y a rien à faire. Le compte et son fichier de sudoers sont tirés au sort : ceux d'un camarade ne sont pas les vôtres.
# 1. Trouver l'intrus : quels fichiers de /etc/sudoers.d donnent des droits, et à qui ?
ansible web -b -m find -a "paths=/etc/sudoers.d"
for s in web1 web2; do
  for f in $(ansible $s -b -m find -a "paths=/etc/sudoers.d" | grep -o '"path": "[^"]*"' | cut -d'"' -f4); do
    case $f in */admin|*/journal|*/README) continue;; esac
    fichier=$f
    compte=$(ansible $s -b -m command -a "cat $f" | grep -oE '^[a-z][a-z0-9_-]* ALL=' | cut -d' ' -f1)
  done
done
echo "Compte oublié : $compte (droits donnés par $fichier)"
# 2. Ce que le code ne décrit pas n'existe pas pour --check : on décrit l'absence
cat >> roles/web/tasks/main.yml <<EOF

- name: Plus de compte $compte (parti depuis des mois)
  ansible.builtin.user:
    name: $compte
    state: absent
    remove: true

- name: Plus de droits sudo pour $compte
  ansible.builtin.file:
    path: $fichier
    state: absent
EOF
ansible-playbook site.yml
ansible-playbook site.yml    # changed=0
''',
    8: r'''
#@ A8.1
#? Le mot de passe est rangé dans `group_vars/bdd/vault.yml`, chiffré par `ansible-vault` : tous les fichiers du dossier `group_vars/bdd/` sont chargés pour le groupe, et le coffre n'est déchiffré qu'en mémoire pendant le jeu.
#? La clé du coffre est dans `~/.vault_pass`, hors du projet, désignée par `vault_password_file` dans `ansible.cfg` : le dépôt peut être partagé sans révéler ni le mot de passe, ni la clé.
#? `lineinfile` avec `regexp` remplace la ligne existante, y compris la ligne `requirepass` commentée d'origine ; `no_log: true` évite d'afficher le mot de passe dans la sortie, et le handler redémarre Redis pour qu'il prenne en compte ces réglages.
#? Le piège était de laisser le mot de passe en clair dans le rôle, ou la clé du coffre dans `~/infra`. Le mot de passe de Sophie est tiré au sort : le vôtre diffère de celui d'un camarade.
#? Variantes acceptées : un coffre sous un autre nom, ou une valeur chiffrée par `ansible-vault encrypt_string` dans `group_vars/bdd.yml` ; `vault_identity_list` au lieu de `vault_password_file`.
cd ~/infra
ansible-galaxy init --init-path roles redis
cat > roles/redis/tasks/main.yml <<'EOF'
- name: Installer Redis
  ansible.builtin.apt:
    name: redis-server
    state: present
    update_cache: true
    cache_valid_time: 3600

- name: Redis écoute sur le réseau
  ansible.builtin.lineinfile:
    path: /etc/redis/redis.conf
    regexp: '^bind '
    line: bind 0.0.0.0
  notify: Redémarrer redis

- name: Mot de passe de Redis
  ansible.builtin.lineinfile:
    path: /etc/redis/redis.conf
    regexp: '^#? ?requirepass '
    line: "requirepass {{ vault_redis_password }}"
  no_log: true
  notify: Redémarrer redis

- name: Redis démarré, et lancé au démarrage du serveur
  ansible.builtin.service:
    name: redis-server
    state: started
    enabled: true
EOF
cat > roles/redis/handlers/main.yml <<'EOF'
- name: Redémarrer redis
  ansible.builtin.service:
    name: redis-server
    state: restarted
EOF
# La clé du coffre, hors du projet ; le mot de passe de Sophie, dans un fichier chiffré
echo "Une-longue-phrase-pour-le-coffre-2024" > ~/.vault_pass
chmod 600 ~/.vault_pass
echo "vault_password_file = ~/.vault_pass" >> ansible.cfg
mkdir -p group_vars/bdd
printf 'vault_redis_password: "%s"\n' "$(sed -n 's/.*sera : //p' ~/message-sophie.txt)" > group_vars/bdd/vault.yml
ansible-vault encrypt group_vars/bdd/vault.yml
cat >> site.yml <<'EOF'

- name: Base de données
  hosts: bdd
  become: true
  roles:
    - redis
EOF
ansible-playbook site.yml --limit bdd
#@ A8.2
#? Un nouveau serveur se prépare comme au premier jour (empreinte, clé), puis une ligne dans l'inventaire suffit : les rôles et `group_vars/web.yml` s'appliquent automatiquement.
#? `--limit web3` (ou `-l web3`) restreint le jeu à ce seul serveur : web1 et web2 ne sont ni contactés ni modifiés.
#? Le piège était de relancer `site.yml` sur tout le parc : le résultat aurait été le même, mais la vérification lit le journal de sudo de web1 et web2 et y aurait vu le passage d'Ansible.
ssh-keyscan web3 >> ~/.ssh/known_hosts
sshpass -p cimes ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@web3
sed -i 's/^web2$/web2\nweb3/' inventaire.ini
# Seul web3 est configuré : web1 et web2 ne sont pas touchés
ansible-playbook site.yml --limit web3
#@ A8.3
#? Si tout est décrit dans les rôles, reconstruire un serveur neuf ne demande qu'une commande, et un second passage le confirme par `changed=0` sur les quatre serveurs.
#? Le piège était ce qui avait été fait à la main ou en commande ad hoc : sur un serveur réinstallé, cela disparaît, et seul le code survit.
#? En cas d'échec, lisez le récapitulatif, puis relancez avec `-v` pour voir le détail de la première tâche en erreur.
# Tout est décrit dans les rôles : un serveur neuf est reconstruit par un seul passage
ansible-playbook site.yml
ansible-playbook site.yml    # changed=0 sur les quatre serveurs
#@ A8.4
#? Julien a défini `environnement: production` à un endroit dont la priorité dépasse celle de `host_vars` : `vars/main.yml` du rôle, `vars:` du play, une tâche `set_fact` ou une tâche `include_vars`. Chacun écrasait `environnement: recette` de web2.
#? `ansible-inventory --host web2` ne montre que les variables de l'inventaire, pas celles des rôles, des plays ou des tâches : c'est pour cela qu'il affichait « recette » alors que le jeu utilisait « production ». Chercher où la variable est définie (`grep -rn`) désigne le coupable.
#? L'endroit choisi par Julien est tiré au sort : la réparation d'un camarade ne vise pas forcément le bon fichier. Les valeurs par défaut du rôle vont dans `defaults/main.yml`, la priorité la plus faible, que tout le reste peut surcharger.
# Diagnostic : ansible-inventory --host web2 dit « recette », mais pendant le jeu la valeur est « production »
ansible-inventory --host web2 | grep environnement
# Qui définit environnement, en dehors de l'inventaire (group_vars, host_vars) et des valeurs par défaut du rôle ?
grep -rnE 'environnement:|set_fact|include_vars' site.yml roles/web/tasks roles/web/vars
# 1. vars/main.yml du rôle : vidé
if grep -qE '^(environnement|http_port):' roles/web/vars/main.yml; then printf -- '---\n# vars file for web\n' > roles/web/vars/main.yml; fi
# 2. vars: ajouté au play des serveurs web (avec le commentaire de Julien)
sed -i '/# Valeurs communes, rangées par Julien/,/environnement: production/d' site.yml
# 3. et 4. set_fact ou include_vars ajouté en tête du rôle : la tâche (jusqu'à la ligne vide qui la suit), et son fichier
sed -i '/^- name: .*(rangée\?s\? par Julien)$/,/^$/d' roles/web/tasks/main.yml
rm -f roles/web/vars/reglages.yml
cat roles/web/defaults/main.yml
ansible-playbook site.yml
''',
    9: r'''
#@ A9.1
#? Une lecture ne modifie rien : `register` capture la sortie de la commande et `changed_when: false` rend la tâche honnête dans le récapitulatif.
#? `nginx -v` écrit sa version sur la sortie d'erreur, d'où `stderr`, alors que `redis-server --version` l'écrit sur `stdout`.
#? Le rapport est écrit une seule fois (`run_once: true`) sur le poste de contrôle (`delegate_to: localhost`, sans sudo), à partir de `hostvars` ; comme son contenu est identique d'un passage à l'autre, `copy` répond `ok` au second passage.
#? Les numéros de version dépendent des paquets installés dans votre environnement : ceux de votre rapport peuvent différer d'un exemple à l'autre.
cd ~/infra
cat > rapport.yml <<'EOF'
- name: Versions des logiciels exposés
  hosts: web:bdd
  become: true
  gather_facts: false
  tasks:
    - name: Version de nginx (écrite sur la sortie d'erreur)
      ansible.builtin.command: nginx -v
      register: v_nginx
      changed_when: false
      when: "'web' in group_names"

    - name: Version de Redis
      ansible.builtin.command: redis-server --version
      register: v_redis
      changed_when: false
      when: "'bdd' in group_names"

    - name: Rapport sur le poste de contrôle
      ansible.builtin.copy:
        dest: "{{ playbook_dir }}/reponses/versions.txt"
        mode: "0644"
        content: |
          {% for h in groups['all'] | sort %}
          {% if 'web' in hostvars[h]['group_names'] %}
          {{ h }};nginx;{{ hostvars[h]['v_nginx']['stderr'].split('/')[-1] }}
          {% endif %}
          {% if 'bdd' in hostvars[h]['group_names'] %}
          {{ h }};redis;{{ hostvars[h]['v_redis']['stdout'].split('v=')[1].split()[0] }}
          {% endif %}
          {% endfor %}
      delegate_to: localhost
      run_once: true
      become: false
EOF
ansible-playbook rapport.yml
cat reponses/versions.txt
ansible-playbook rapport.yml     # changed=0
#@ A9.2
#? `changed_when` et `failed_when` remplacent le jugement par défaut d'Ansible (toujours `changed` pour `command`, échec si le code de retour n'est pas 0) par une règle adaptée au script.
#? `failed_when` combine deux conditions : le mot qui signale une erreur dans la sortie (le script renvoie 0 même en cas d'échec) et un code de retour autre que 0 ou celui d'une purge déjà en cours.
#? Le piège était `ignore_errors: true` : la purge déjà en cours passerait, mais une vraie erreur serait masquée elle aussi.
#? `changed_when: purge.stdout is search('CLE=[1-9]')` teste directement qu'au moins un fichier a été supprimé ; `'CLE=' in purge.stdout and 'CLE=0' not in purge.stdout` est une variante valable.
#? Les conventions du script (code de retour, mot d'erreur, clé du compte rendu) sont tirées au sort : on les lit dans le script, et le `purge.yml` d'un camarade ne conviendrait pas au vôtre.
# Les conventions de Marc, lues dans son script : code « purge déjà en cours », mot d'erreur, clé du compte rendu
ansible web1 -m command -a "cat /usr/local/sbin/purge-cache"
script=$(ansible web1 -m command -a "cat /usr/local/sbin/purge-cache")
en_cours=$(echo "$script" | grep 'déjà en cours' | grep -oE 'exit [0-9]+' | cut -d' ' -f2)
erreur=$(echo "$script" | grep 'introuvable' | grep -oE 'echo "[A-Z]+:' | sed 's/echo "//; s/://')
cle=$(echo "$script" | grep -oE 'echo "[A-Z_]+=' | sed 's/echo "//; s/=//')
echo "Purge en cours : code $en_cours ; erreur : « $erreur » ; compte rendu : $cle=<nombre>"
cat > purge.yml <<EOF
- name: Purge du cache des pages
  hosts: web
  become: true
  gather_facts: false
  tasks:
    - name: Purger le cache
      ansible.builtin.command: /usr/local/sbin/purge-cache
      register: purge
      changed_when: purge.stdout is search('$cle=[1-9]')
      failed_when: "'$erreur' in purge.stdout or purge.rc not in [0, $en_cours]"
EOF
cat purge.yml
ansible-playbook purge.yml
ansible-playbook purge.yml     # caches vides : changed=0
#@ A9.3
#? Les `pre_tasks` s'exécutent avant les rôles : si `assert` échoue, le jeu s'arrête avant d'avoir touché à la configuration de nginx ou à la page.
#? `http_port | int` est nécessaire, car une valeur passée par `-e` est une chaîne : on compare alors des nombres, et non du texte.
#? Le piège était de placer la vérification après des tâches qui modifient les serveurs : le refus arriverait trop tard. Une tâche `assert` placée en toute première position du rôle aurait aussi fonctionné.
cat > site.yml <<'EOF'
- name: Serveurs web
  hosts: web
  become: true
  force_handlers: true
  pre_tasks:
    - name: Paramètres de déploiement cohérents
      ansible.builtin.assert:
        that:
          - http_port | int >= 1024
          - http_port | int <= 65535
          - environnement in ['production', 'recette']
        fail_msg: "Déploiement refusé : http_port={{ http_port }}, environnement={{ environnement }}"
        quiet: true
  roles:
    - web

- name: Base de données
  hosts: bdd
  become: true
  roles:
    - redis
EOF
ansible-playbook site.yml -e http_port=80 || echo "Refusé, comme prévu"
ansible-playbook site.yml
#@ A9.4
#? `block` regroupe les étapes de la livraison, `rescue` s'exécute seulement si l'une d'elles échoue, et `always` s'exécute dans tous les cas, ce qui garantit une ligne de journal par tentative.
#? La tâche `stat` lancée avant le bloc mémorise la cible actuelle du lien (`lnk_source`) : c'est elle que `rescue` remet en place pour revenir à la version précédente.
#? Le piège était d'oublier `fail` à la fin de `rescue` : un `rescue` réussi fait considérer le serveur comme rattrapé, et le jeu afficherait un succès alors que la livraison a échoué.
#? Les numéros de version sont tirés au sort dans `~/demandes/livraisons.txt` : les vôtres diffèrent de ceux d'un camarade.
cat ~/demandes/livraisons.txt
cat > livraison.yml <<'EOF'
- name: Livraison du site vitrine
  hosts: web
  become: true
  gather_facts: false
  vars:
    racine: /var/www/vitrine
  tasks:
    - name: Version en place avant la livraison
      ansible.builtin.stat:
        path: "{{ racine }}/current"
      register: avant

    - name: Livrer la version {{ version }}
      block:
        - name: Dossier de la version
          ansible.builtin.file:
            path: "{{ racine }}/releases/{{ version }}"
            state: directory
            mode: "0755"

        - name: Contenu de l'archive, téléchargée depuis le dépôt interne
          ansible.builtin.unarchive:
            src: "http://depot.cimes.lan:8000/livraisons/vitrine-{{ version }}.tar.gz"
            dest: "{{ racine }}/releases/{{ version }}"
            remote_src: true

        - name: Bascule vers la nouvelle version
          ansible.builtin.file:
            src: "{{ racine }}/releases/{{ version }}"
            dest: "{{ racine }}/current"
            state: link

        - name: La page d'accueil est bien là
          ansible.builtin.stat:
            path: "{{ racine }}/current/index.html"
          register: accueil

        - name: Vérification de la livraison
          ansible.builtin.assert:
            that: accueil.stat.exists
            fail_msg: "La version {{ version }} n'a pas de page d'accueil"
      rescue:
        - name: Retour à la version précédente
          ansible.builtin.file:
            src: "{{ avant.stat.lnk_source }}"
            dest: "{{ racine }}/current"
            state: link
          when: avant.stat.islnk | default(false)

        - name: La livraison reste en échec
          ansible.builtin.fail:
            msg: "Livraison {{ version }} annulée : retour à la version précédente"
      always:
        - name: Journal des livraisons
          ansible.builtin.shell: >-
            echo "$(date '+%F %T') version {{ version }}
            {{ 'échec' if ansible_failed_task is defined else 'réussie' }}" >> /var/log/livraisons.log
EOF
v1=$(grep -oE "À déployer dans l'ordre : [^,]+" ~/demandes/livraisons.txt | sed 's/.*: //')
v2=$(grep -oE "puis [0-9][^.]*\.[0-9]+\.[0-9]+" ~/demandes/livraisons.txt | sed 's/^puis //')
vc=$(grep -oE "La [0-9][^ ]*-rc[0-9]+" ~/demandes/livraisons.txt | sed 's/^La //')
ansible-playbook livraison.yml -e version=$v1
ansible-playbook livraison.yml -e version=$v2
ansible-playbook livraison.yml -e version=$vc || echo "Échec rattrapé : retour à la $v2"
''',
    10: r'''
#@ A10.1
#? Face à un incident, on constate d'abord sans rien toucher (SSH, HTTP, Redis, groupe sudo), on rétablit l'accès en vérifiant les empreintes comme au jour 2, puis on laisse le code remettre l'infrastructure en ordre.
#? Ce que le code ne décrivait pas (droits du dossier du site, compte stagiaire) doit y entrer : `file` avec `mode` pour le dossier, `user` avec `state: absent` dans un rôle appliqué à tous les serveurs.
#? Le piège était de réparer à la main avec `chmod` ou `userdel` : la vérification recrée ces écarts avant de rejouer `site.yml`, et seul le code les corrige de façon durable.
#? Les pannes et les serveurs touchés sont tirés au sort, et au moins un serveur est toujours épargné : l'`incident.txt` d'un camarade, ou la liste de tous les serveurs, ne correspond pas au vôtre.
cd ~/infra
: > reponses/incident.txt
# 1. Constater, sans rien toucher. Qui répond encore à SSH ?
for s in web1 web2 web3 db1; do
  if ! ssh -o BatchMode=yes -o ConnectTimeout=5 admin@$s true 2>/dev/null; then
    echo "$s : injoignable, empreinte SSH changée (serveur réinstallé par l'hébergeur)" >> reponses/incident.txt
    # Empreinte à vérifier auprès de l'hébergeur (jour 2), puis accès rétabli
    ssh-keygen -R $s
    ssh-keyscan $s >> ~/.ssh/known_hosts 2>/dev/null
    sshpass -p cimes ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@$s
  fi
done
# Qui sert sa page ?
for s in web1 web2 web3; do
  grep -q "^$s " reponses/incident.txt && continue
  c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://$s:8080/)
  [ "$c" = 200 ] || echo "$s : la boutique ne répond pas sur 8080 (code HTTP $c)" >> reponses/incident.txt
done
# Redis exige-t-il toujours son mot de passe ?
ansible db1 -b -m command -a "redis-cli ping" | grep -q PONG && echo "db1 : Redis accepte les commandes sans mot de passe" >> reponses/incident.txt
# Des comptes en trop dans le groupe sudo ?
for s in web1 web2 web3 db1; do
  ansible $s -m getent -a "database=group key=sudo" | grep -q stagiaire && echo "$s : compte stagiaire membre de sudo" >> reponses/incident.txt
done
cat reponses/incident.txt
# 2. Compléter le code pour ce qu'il ne décrivait pas : droits du dossier du site, compte interdit partout
{ cat <<'EOF'
- name: Dossier du site lisible par nginx
  ansible.builtin.file:
    path: /var/www/html
    state: directory
    owner: root
    group: root
    mode: "0755"

EOF
cat roles/web/tasks/main.yml; } > /tmp/taches.yml && mv /tmp/taches.yml roles/web/tasks/main.yml
ansible-galaxy init --init-path roles commun
cat > roles/commun/tasks/main.yml <<'EOF'
- name: Pas de compte stagiaire sur nos serveurs
  ansible.builtin.user:
    name: stagiaire
    state: absent
    remove: true
EOF
cat > site.yml <<'EOF'
- name: Socle commun à tous les serveurs
  hosts: all
  become: true
  roles:
    - commun

- name: Serveurs web
  hosts: web
  become: true
  force_handlers: true
  pre_tasks:
    - name: Paramètres de déploiement cohérents
      ansible.builtin.assert:
        that:
          - http_port | int >= 1024
          - http_port | int <= 65535
          - environnement in ['production', 'recette']
        fail_msg: "Déploiement refusé : http_port={{ http_port }}, environnement={{ environnement }}"
        quiet: true
  roles:
    - web

- name: Base de données
  hosts: bdd
  become: true
  roles:
    - redis
EOF
# 3. Rejouer, puis vérifier que tout est rentré dans l'ordre
ansible-playbook site.yml
ansible-playbook site.yml    # changed=0
#@ A10.2
#? `serial: 1` traite les serveurs un par un, dans l'ordre de l'inventaire : si tous les serveurs d'un lot échouent, Ansible arrête le jeu et les serveurs suivants gardent l'ancienne version.
#? `max_fail_percentage: 0` arrête tout dès le premier échec, même avec des lots de plusieurs serveurs : avec `serial: 1`, c'est une sécurité supplémentaire, et `serial: 1` seul suffit déjà.
#? Le module `copy` avec `content` écrit la version seule sur sa ligne, et ne répond `changed` que si elle change.
cat > deploiement.yml <<'EOF'
- name: Déploiement progressif de l'application
  hosts: web
  become: true
  serial: 1                  # un serveur à la fois, dans l'ordre de l'inventaire
  max_fail_percentage: 0     # le premier échec arrête tout
  gather_facts: false
  tasks:
    - name: Version déployée
      ansible.builtin.copy:
        dest: /var/www/html/version.txt
        content: "{{ version }}\n"
        mode: "0644"
EOF
ansible-playbook deploiement.yml -e version=2025.1
#@ A10.3
#? Une étiquette posée sur une tâche permet de n'exécuter qu'elle avec `--tags page` ; posée sur le rôle dans `site.yml`, elle serait héritée par toutes ses tâches, y compris la configuration de nginx.
#? `--list-tags` et `--list-tasks --tags page` montrent ce qui serait exécuté, sans rien lancer : le bon réflexe avant de s'en servir.
#? Un `site.yml` complet, sans `--tags`, remet ensuite en ordre tout ce que la page seule n'a pas touché.
#? Variantes acceptées : l'étiquette sur un `import_tasks` qui ne contient que la page, ou sur un petit rôle `page` appliqué dans `site.yml`.
# L'étiquette sur la seule tâche de la page (pas sur le rôle : elle s'étendrait à toutes ses tâches)
sed -i "/^- name: Page d'accueil de la boutique$/,/^    mode:/ s/^    mode: \"0644\"$/&\n  tags: [page]/" roles/web/tasks/main.yml
ansible-playbook site.yml --list-tags
ansible-playbook site.yml --list-tasks --tags page
ansible-playbook site.yml --tags page
''',
}
