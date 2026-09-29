"""Corrigé du parcours Ansible : un script par étape, exécuté en tant qu'« etudiant » par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Les données tirées au hasard (messages, demandes) sont relues dans les fichiers remis à l'étudiant.
"""

SOLUTIONS = {
    1: r'''
#@ A1.1
ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519
# Accepter l'empreinte de chaque serveur (ou se connecter une fois à la main, comparer l'empreinte, répondre « yes »)
ssh-keyscan web1 web2 db1 >> ~/.ssh/known_hosts
# Copier la clé publique : ssh-copy-id demande le mot de passe (cimes) ; sshpass le fournit ici
for s in web1 web2 db1; do sshpass -p cimes ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@$s; done
ssh -o BatchMode=yes admin@web1 hostname
#@ A1.2
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
cat > ansible.cfg <<'EOF'
[defaults]
inventory = inventaire.ini
remote_user = admin
EOF
ansible production -m ping
#@ A1.4
cat exercices/demandes.txt
# Pour chaque demande, le motif correspondant, vérifié avec --list-hosts (aucune connexion)
: > reponses/motifs.txt
grep -E '^[0-9]\. ' exercices/demandes.txt | while read -r num texte; do
  case "$texte" in
    "Les serveurs web de Lyon.") m='web:&lyon' ;;
    "Toute la production, sauf les bases de données.") m='production:!bdd' ;;
    "Les serveurs de recette situés à Paris.") m='recette:&paris' ;;
    "Le premier serveur du groupe web"*) m='web[0]' ;;
    "Tous les serveurs, sauf ceux de Lyon.") m='all:!lyon' ;;
    "Les serveurs de cache et les bases de données.") m='cache:bdd' ;;
  esac
  echo "$m" >> reponses/motifs.txt
  ansible -i exercices/parc.ini "$m" --list-hosts
done
''',
    2: r'''
#@ A2.1
cd ~/infra
cat ~/message-julien.txt
# La commande de Julien, en mode très bavard
cmd=$(grep -E '^ +ansible web1' ~/message-julien.txt | sed 's/^ *//')
eval "$cmd -vvv" > /tmp/vvv.txt 2>&1
# « PUT <fichier local> TO <dossier du serveur>/AnsiballZ_<module>.py » : le fichier envoyé et son dossier
grep -o "AnsiballZ_[a-z_]*\.py" /tmp/vvv.txt | head -1 > reponses/module.txt
grep " PUT " /tmp/vvv.txt | grep -o "TO /home/admin/[^ ]*" | head -1 | sed 's|^TO ||; s|/AnsiballZ.*||' >> reponses/module.txt
# « EXEC … /bin/sh -c '<interpréteur> …/AnsiballZ_<module>.py' » : l'interpréteur Python du serveur
grep " EXEC " /tmp/vvv.txt | grep AnsiballZ | grep -o "/usr/bin/python3[.0-9]*" | head -1 >> reponses/module.txt
cat reponses/module.txt
#@ A2.2
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
cat ~/message-thomas.txt
uid=$(grep -oE 'UID [0-9]+' ~/message-thomas.txt | cut -d' ' -f2)
ansible web -b -m user -a "name=deploy uid=$uid groups=www-data append=true shell=/bin/bash"
ansible web -b -m copy -a "dest=/etc/motd content='Serveur géré par Ansible - ne pas modifier à la main\n'"
#@ A2.4
cat ~/message-lea.txt
# 1. Comparer l'empreinte présentée par db1 à l'empreinte officielle
officielle=$(grep -oE 'SHA256:[^ ]+' ~/message-lea.txt)
presentee=$(ssh-keyscan -t ed25519 db1 2>/dev/null | ssh-keygen -lf - | awk '{print $2}')
[ "$officielle" = "$presentee" ] && echo "Empreinte conforme : on peut lui faire confiance"
# 2. Oublier l'ancien db1, enregistrer le nouveau (empreinte vérifiée), réinstaller la clé publique
ssh-keygen -R db1
ssh-keyscan db1 >> ~/.ssh/known_hosts 2>/dev/null
sshpass -p cimes ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@db1
ssh -o BatchMode=yes admin@db1 hostname
#@ A2.5
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
cat >> web.yml <<'EOF'

    - name: Page d'accueil de la boutique
      ansible.builtin.copy:
        src: fichiers/index.html
        dest: /var/www/html/index.html
        mode: "0644"
EOF
ansible-playbook web.yml
#@ A3.3
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
ansible-playbook marc/outils.yml --syntax-check || true
# Défauts possibles : tabulation, {{ }} sans guillemets, state: installed, module « fille », become absent,
# mode: 750 (décimal !), et surtout hosts: tous, qui ne correspond à aucun groupe (« no hosts matched »)
dossier=$(grep -o '/opt/cimes/[a-z-]*' marc/outils.yml)
cat > marc/outils.yml <<EOF
# Outils de Marc : unzip sur tous les serveurs de production, et un dossier de travail.
- name: Outils de Marc
  hosts: production
  become: true
  vars:
    paquet: unzip
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
        owner: admin
        mode: "0750"
EOF
ansible-playbook marc/outils.yml
ansible-playbook marc/outils.yml     # changed=0
''',
    4: r'''
#@ A4.1
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
mkdir -p host_vars
echo "environnement: recette" > host_vars/web2.yml
ansible-inventory --host web2
ansible-playbook web.yml
#@ A4.3
# L'adresse vient des facts du serveur ; la ferme, des variables magiques groups et hostvars
sed -i "s|  <p>Environnement : {{ environnement }}</p>|&\n  <p>Adresse : {{ ansible_facts['default_ipv4']['address'] }}</p>\n  <p>Ferme : {% for h in groups['web'] %}{{ h }} ({{ hostvars[h]['environnement'] }}){% if not loop.last %}, {% endif %}{% endfor %}</p>|" templates/index.html.j2
ansible-playbook web.yml
#@ A4.4
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
# Même si une tâche échoue ensuite, les handlers notifiés sont exécutés
sed -i 's/^  become: true$/&\n  force_handlers: true/' web.yml
ansible-playbook web.yml
''',
    6: r'''
#@ A6.1
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
# « false » entre guillemets est une chaîne non vide, donc vraie ; -e passe toujours des chaînes : | bool
ansible web -m debug -a "msg={{ maintenance | type_debug }} {{ maintenance }}" --playbook-dir julien
sed -i 's/^      when: maintenance$/      when: maintenance | bool/; s/^      when: not maintenance$/      when: not (maintenance | bool)/' julien/maintenance.yml
ansible-playbook julien/maintenance.yml
ansible-playbook julien/maintenance.yml -e maintenance=false
ansible-playbook julien/maintenance.yml
''',
    7: r'''
#@ A7.1
cd ~/infra
# 1. Les écarts avec le code : le mode vérification les voit
ansible-playbook web.yml --check --diff
ansible-playbook web.yml --check | grep -oE "changed: \[web[0-9]\]" | grep -oE "web[0-9]" | sort -u > reponses/derive.txt
cat reponses/derive.txt
# 2. Ce que le code ne décrit pas : il faut le chercher (ici, toute page qui parle de promotion)
for s in web1 web2; do
  for f in $(ansible $s -b -m find -a "paths=/var/www/html patterns=*.html contains=.*Promo.*" | grep -o '"path": "[^"]*"' | cut -d'"' -f4); do
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
# Ce que le code ne décrit pas n'existe pas pour --check : on décrit l'absence
cat >> roles/web/tasks/main.yml <<'EOF'

- name: Plus de compte marc (parti depuis des mois)
  ansible.builtin.user:
    name: marc
    state: absent
    remove: true

- name: Plus de droits sudo pour marc
  ansible.builtin.file:
    path: /etc/sudoers.d/marc
    state: absent
EOF
ansible-playbook site.yml
ansible-playbook site.yml    # changed=0
''',
    8: r'''
#@ A8.1
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
ssh-keyscan web3 >> ~/.ssh/known_hosts
sshpass -p cimes ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@web3
sed -i 's/^web2$/web2\nweb3/' inventaire.ini
# Seul web3 est configuré : web1 et web2 ne sont pas touchés
ansible-playbook site.yml --limit web3
#@ A8.3
# Tout est décrit dans les rôles : un serveur neuf est reconstruit par un seul passage
ansible-playbook site.yml
ansible-playbook site.yml    # changed=0 sur les quatre serveurs
#@ A8.4
# vars/main.yml l'emporte sur host_vars : les valeurs par défaut du rôle vont dans defaults/main.yml
# Diagnostic : ansible-inventory --host web2 dit « recette », mais pendant le jeu la valeur est « production »
ansible-inventory --host web2 | grep environnement
cat roles/web/vars/main.yml
printf -- '---\n# vars file for web\n' > roles/web/vars/main.yml
cat roles/web/defaults/main.yml
ansible-playbook site.yml
''',
    9: r'''
#@ A9.1
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
cat > purge.yml <<'EOF'
- name: Purge du cache des pages
  hosts: web
  become: true
  gather_facts: false
  tasks:
    - name: Purger le cache
      ansible.builtin.command: /usr/local/sbin/purge-cache
      register: purge
      changed_when: "'SUPPRIMES=' in purge.stdout and 'SUPPRIMES=0' not in purge.stdout"
      failed_when: "'ERREUR' in purge.stdout or purge.rc not in [0, 3]"
EOF
ansible-playbook purge.yml
ansible-playbook purge.yml     # caches vides : changed=0
#@ A9.3
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
# L'étiquette sur la seule tâche de la page (pas sur le rôle : elle s'étendrait à toutes ses tâches)
sed -i "/^- name: Page d'accueil de la boutique$/,/^    mode:/ s/^    mode: \"0644\"$/&\n  tags: [page]/" roles/web/tasks/main.yml
ansible-playbook site.yml --list-tags
ansible-playbook site.yml --list-tasks --tags page
ansible-playbook site.yml --tags page
''',
}
