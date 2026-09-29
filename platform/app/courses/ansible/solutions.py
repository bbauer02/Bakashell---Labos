"""Corrigé du parcours Ansible : un script par étape, exécuté en tant qu'« etudiant » par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
"""

SOLUTIONS = {
    1: r'''
#@ A1.1
ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519
# Accepter l'empreinte de chaque serveur (ou se connecter une fois à la main et répondre « yes »)
ssh-keyscan web1 web2 db1 >> ~/.ssh/known_hosts
# Copier la clé publique : ssh-copy-id demande le mot de passe (cimes) ; sshpass le fournit ici
for s in web1 web2 db1; do sshpass -p cimes ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@$s; done
ssh admin@web1 hostname
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
''',
    2: r'''
#@ A2.1
cd ~/infra
# La ligne « PUT … TO …/AnsiballZ_ping.py » montre le module envoyé sur le serveur
ansible web1 -m ping -vvv | grep -o "AnsiballZ_[a-z_]*\.py" | head -1 > reponses/module.txt
#@ A2.2
ansible db1 -m setup -a "filter=ansible_distribution_version"
ansible db1 -m setup -a "filter=ansible_distribution_version" | grep -o '"[0-9.]*"' | tr -d '"' > reponses/debian-db1.txt
#@ A2.3
ansible web -b -m user -a "name=deploy shell=/bin/bash"
ansible web -b -m copy -a "dest=/etc/motd content='Serveur géré par Ansible - ne pas modifier à la main\n'"
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
ansible-playbook web.yml     # second passage : changed=0 sur web1 et web2
''',
    4: r'''
#@ A4.1
cd ~/infra
mkdir -p group_vars templates
echo "environnement: production" > group_vars/web.yml
cat > templates/index.html.j2 <<'EOF'
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Cimes & Sentiers</title></head>
<body>
  <h1>Boutique Cimes & Sentiers</h1>
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
sed -i 's|  <p>Environnement : {{ environnement }}</p>|&\n  <p>Adresse : {{ ansible_default_ipv4.address }}</p>|' templates/index.html.j2
ansible-playbook web.yml
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

  handlers:
    - name: Recharger nginx
      ansible.builtin.service:
        name: nginx
        state: reloaded
EOF
ansible-playbook web.yml
#@ A5.2
# Démonstration : le port suit la variable, et nginx n'est rechargé que si la configuration change
ansible-playbook web.yml -e http_port=8089
ansible-playbook web.yml
ansible-playbook web.yml     # changed=0, handler non exécuté
''',
    6: r'''
#@ A6.1
cd ~/infra
cat >> group_vars/web.yml <<'EOF'
equipe_web:
  - thomas
  - nadia
  - julien
EOF
cat >> web.yml.tmp <<'EOF'
    - name: Comptes de l'équipe web
      ansible.builtin.user:
        name: "{{ item }}"
        groups: www-data
        append: true
        shell: /bin/bash
      loop: "{{ equipe_web }}"

EOF
# Insertion de la tâche juste avant la section handlers
sed -i '/^  handlers:/e cat web.yml.tmp' web.yml && rm web.yml.tmp
ansible-playbook web.yml
#@ A6.2
cat > web.yml.tmp <<'EOF'
    - name: Outils de diagnostic, en recette seulement
      ansible.builtin.apt:
        name: htop
        state: present
      when: environnement == "recette"

EOF
sed -i '/^  handlers:/e cat web.yml.tmp' web.yml && rm web.yml.tmp
# Bandeau dans le modèle, juste après <body>
sed -i 's|<body>|<body>\n{% if environnement == "recette" %}\n  <div class="bandeau">RECETTE - site de test</div>\n{% endif %}|' templates/index.html.j2
ansible-playbook web.yml
''',
    7: r'''
#@ A7.1
cd ~/infra
# En mode vérification, seul le serveur modifié à la main a une tâche « changed »
ansible-playbook web.yml --check --diff
ansible-playbook web.yml --check | grep -oE "changed: \[web[0-9]\]" | head -1 | grep -oE "web[0-9]" > reponses/derive.txt
ansible-playbook web.yml    # retour à l'état décrit
#@ A7.2
ansible-galaxy init --init-path roles web
mv templates/*.j2 roles/web/templates/
cat > roles/web/tasks/main.yml <<'EOF'
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
    src: site.conf.j2
    dest: /etc/nginx/sites-available/default
    mode: "0644"
  notify: Recharger nginx

- name: Page d'accueil de la boutique
  ansible.builtin.template:
    src: index.html.j2
    dest: /var/www/html/index.html
    mode: "0644"

- name: Comptes de l'équipe web
  ansible.builtin.user:
    name: "{{ item }}"
    groups: www-data
    append: true
    shell: /bin/bash
  loop: "{{ equipe_web }}"

- name: Outils de diagnostic, en recette seulement
  ansible.builtin.apt:
    name: htop
    state: present
  when: environnement == "recette"
EOF
cat > roles/web/handlers/main.yml <<'EOF'
- name: Recharger nginx
  ansible.builtin.service:
    name: nginx
    state: reloaded
EOF
cat > roles/web/defaults/main.yml <<'EOF'
http_port: 80
environnement: production
equipe_web: []
EOF
cat > site.yml <<'EOF'
- name: Serveurs web
  hosts: web
  become: true
  roles:
    - web
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
ansible-playbook site.yml
#@ A8.2
ssh-keyscan web3 >> ~/.ssh/known_hosts
sshpass -p cimes ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@web3
sed -i 's/^web2$/web2\nweb3/' inventaire.ini
ansible-playbook site.yml --limit web3
#@ A8.3
ansible-playbook site.yml
ansible-playbook site.yml    # changed=0 sur les quatre serveurs
''',
}
