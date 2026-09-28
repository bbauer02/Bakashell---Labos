"""Corrigé du parcours Linux : un script par étape, exécuté en tant qu'« etudiant » par le banc de test
(avec sudo sans mot de passe dans le conteneur de test).

Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Un même repère peut réapparaître plus loin : le bloc suivant est ajouté à la correction de l'exercice.
Les solutions résolvent les énigmes comme un étudiant, sans lire les réponses attendues.
"""

SOLUTIONS = {
    1: r'''
#@ 1.1
# La note à jour est dans le dossier 2024 ; les autres sont marquées PÉRIMÉ
sed -n 's/^CODE=//p' /opt/archives-marc/2024/reseau/baie/note.txt > ~/code-baie.txt
#@ 1.2
ls -a ~/passation
cat ~/passation/.jeton-vpn > ~/jeton-vpn.txt
#@ 1.3
mkdir -p ~/documents ~/projets
#@ 1.4
touch ~/documents/journal.txt
''',
    2: r'''
#@ 2.1
mkdir -p /home/etudiant/projets/boutique/src
#@ 2.2
echo "-S" > ~/reponse-man.txt
#@ 2.3
echo "../../tarifs.txt" > ~/chemin-relatif.txt
#@ 2.4
cd ~/partage-marc/clients/2024/../.. && pwd > ~/chemin-absolu.txt
''',
    3: r'''
#@ 3.1
mkdir -p ~/documents/procedures ~/documents/comptes-rendus
#@ 3.2
echo "Procédure arrivée nouveau salarié" > ~/documents/procedures/arrivee.txt
#@ 3.3
echo "1. Créer le compte utilisateur" >> ~/documents/procedures/arrivee.txt
#@ 3.4
cp ~/documents/procedures/arrivee.txt ~/documents/comptes-rendus/arrivee-a-relire.txt
#@ 3.5
rm ~/bureau-marc/*.tmp
rm -r ~/bureau-marc/vieux-projets
''',
    4: r'''
#@ 4.1
echo "produit;prix" > ~/tarifs-2025.csv
ln ~/tarifs-2025.csv ~/tarifs-courant.csv
#@ 4.2
# 2e colonne de ls -l, ou : find /opt/sauvegardes -samefile /opt/sauvegardes/base-clients.db | wc -l
stat -c %h /opt/sauvegardes/base-clients.db > ~/nb-liens.txt
#@ 4.3
ln -s /etc ~/conf-systeme
#@ 4.4
b=$(find ~/raccourcis-marc -xtype l -printf '%f\n')
echo "$b" > ~/lien-casse.txt
#@ 4.5
b=$(cat ~/lien-casse.txt)
ln -sfn annuaire.txt ~/raccourcis-marc/"$b"
''',
    5: r'''
#@ 5.1
find /etc -name "*.conf" 2>/dev/null > ~/audit-conf.txt
#@ 5.2
grep -rl "BON-" /srv/archives > ~/bon-reduction.txt
#@ 5.3
find /srv/archives -name "*.log" | wc -l > ~/nb-logs.txt
#@ 5.4
find /srv/archives -size +5M > ~/gros-fichier.txt
#@ 5.5
grep -ci erreur /srv/archives/rapport.txt > ~/nb-erreurs.txt
''',
    6: r'''
#@ 6.1
ls /etc | wc -l > ~/nb-etc.txt
#@ 6.2
find /root > ~/find-ok.txt 2> ~/erreurs.txt
#@ 6.3
bavard > ~/sortie.txt 2> ~/erreurs-bavard.txt
#@ 6.4
ls /usr/bin | tee ~/programmes.txt > /dev/null
#@ 6.5
cut -d: -f1 /etc/passwd | sort -u > ~/users-sorted.txt
#@ 6.6
find /etc -type f 2>/dev/null | wc -l > ~/nb-fichiers-etc.txt
''',
    7: r'''
#@ 7.1
# Attendu avec nano ; équivalent en une commande :
printf 'serveur=localhost\nport=8080\ndebug=false\n' > ~/config.txt
#@ 7.2
# Attendu avec vim (dd sur la ligne INTRUS, G puis o pour ajouter « Fin », :wq) ; équivalent :
sed -i '/INTRUS/d' ~/config/poeme.txt
echo "Fin" >> ~/config/poeme.txt
#@ 7.3
sed -i 's/debug=false/debug=true/' ~/config.txt
#@ 7.4
sed -i 's/ancien-serveur/nouveau-serveur/g' ~/config/app.conf
''',
    8: r'''
cd ~/regex
#@ 8.1
grep '^[rs]' /etc/passwd > rs.txt
#@ 8.2
grep -oE '[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]{2,}' contacts.txt > emails-valides.txt
#@ 8.3
grep -vE '^\s*(#|$)' serveur.conf > serveur-clean.txt
#@ 8.4
sed 's/[0-9]/X/g' contacts.txt > censure.txt
#@ 8.5
grep -oE '0[1-9]( [0-9]{2}){4}' contacts.txt > telephones.txt
''',
    9: r'''
#@ 9.1
cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn > ~/shells-count.txt
#@ 9.2
awk '{print $1}' ~/logs/access.log | sort | uniq -c | sort -rn | head -3 | awk '{print $2}' > ~/top-ip.txt
#@ 9.3
# Piège : « grep 404 » compte aussi les tailles de réponse contenant 404 ; le code HTTP est le 9e champ
awk '$9 == 404' ~/logs/access.log | wc -l > ~/nb-404.txt
#@ 9.4
awk -F: '$3 >= 1000 && $3 < 65534 {print $1, $3}' /etc/passwd > ~/users-uid.txt
#@ 9.5
tr 'a-z' 'A-Z' < ~/texte/minuscules.txt > ~/texte/majuscules.txt
''',
    10: r'''
#@ 10.1
sudo useradd -m -s /bin/bash alice
sudo useradd -m -s /bin/bash bob
#@ 10.2
sudo groupadd equipe
sudo usermod -aG equipe alice
sudo usermod -aG equipe bob
#@ 10.3
sudo mkdir /home/partage
sudo chgrp equipe /home/partage
sudo chmod 770 /home/partage
#@ 10.4
sudo touch /home/partage/secret.txt
sudo chown alice:equipe /home/partage/secret.txt
sudo chmod 640 /home/partage/secret.txt
#@ 10.5
chmod u+x ~/scripts/deploy.sh
#@ 10.6
sudo chmod g+s /home/partage
''',
    11: r'''
#@ 11.1
sudo useradd -m -s /bin/bash stagiaire
sudo usermod -aG sudo stagiaire
#@ 11.2
p=$(pgrep -x rogue-worker)
echo "$p $(ps -o user= -p "$p")" > ~/rogue.txt
#@ 11.3
# Le processus appartient à « intrus » : sudo est indispensable
sudo kill "$p"
#@ 11.4
nice -n 10 sleep 1000 > /dev/null 2>&1 &
#@ 11.5
sudo kill -HUP "$(pgrep -x lab-service)"
sleep 2
''',
    12: r'''
#@ 12.1
for u in papa maman fils fille; do sudo useradd -m -s /bin/bash $u; done
for u in papa maman fils fille; do sudo -u $u mkdir /home/$u/Travail /home/$u/Bazar; done
#@ 12.2
sudo groupadd parents
sudo groupadd enfants
for u in papa maman; do sudo usermod -aG parents $u; done
for u in fils fille; do sudo usermod -aG enfants $u; done
#@ 12.3
sudo groupadd famille
for u in papa maman fils fille; do sudo usermod -aG famille $u; done
sudo mkdir /home/famille
sudo chgrp famille /home/famille
sudo chmod 2770 /home/famille
#@ 12.4
sudo mkdir /home/parents-only
sudo chgrp parents /home/parents-only
sudo chmod 2770 /home/parents-only
#@ 12.5
sudo useradd -m -s /bin/bash invite
for u in papa maman fils fille; do sudo chmod 750 /home/$u; done
''',
    13: r'''
#@ 13.1
sudo apt-get update -qq
sudo apt-get install -y -qq tree > /dev/null
#@ 13.2
dpkg -S /usr/bin/pgrep | cut -d: -f1 > ~/paquet.txt
#@ 13.3
mkdir -p ~/telechargements
wget -q -O ~/telechargements/page.html https://example.com
#@ 13.4
sudo apt-get install -y -qq cowsay > /dev/null
sudo apt-get remove -y -qq cowsay > /dev/null
''',
    14: r'''
#@ 14.1
df -T / | awk 'NR==2{print $2}' > ~/fs-racine.txt
#@ 14.2
du -s /srv/data/* | sort -n | tail -1 | cut -f2 > ~/plus-gros.txt
#@ 14.3
du -sm /srv/data | cut -f1 > ~/taille-data.txt
#@ 14.4
sudo mkdir -p /mnt/usb
echo "/dev/sdb1  /mnt/usb  ext4  defaults  0  2" > ~/fstab-usb.txt
''',
    15: r'''
#@ 15.1
echo 'export PROJET=linux-lab' >> ~/.bashrc
#@ 15.2
mkdir -p ~/outils
printf '#!/bin/bash\necho "Bonjour !"\n' > ~/outils/bonjour
chmod +x ~/outils/bonjour
echo 'export PATH="$PATH:$HOME/outils"' >> ~/.bashrc
#@ 15.3
# À la fin du fichier : la dernière définition de ll l'emporte sur celle d'Ubuntu
echo "alias ll='ls -la'" >> ~/.bashrc
''',
    16: r'''
#@ 16.1
mkdir -p ~/archive-test
touch ~/archive-test/a.txt ~/archive-test/b.txt ~/archive-test/c.txt
cd ~ && tar -czf archive-test.tar.gz archive-test
#@ 16.2
mkdir -p ~/extraction && tar -xzf ~/archive-test.tar.gz -C ~/extraction
#@ 16.3
tar -tzf /srv/livraison/paquet.tar.gz
mkdir -p /tmp/livraison && tar -xzf /srv/livraison/paquet.tar.gz -C /tmp/livraison
cat /tmp/livraison/paquet/docs/LISEZMOI.txt > ~/code-livraison.txt
#@ 16.4
echo "du contenu à compresser" > ~/compress-me.txt
gzip -k ~/compress-me.txt
#@ 16.5
cd ~ && zip -qr backup.zip archive-test
''',
    17: r'''
#@ 17.1
cat > ~/hello.sh <<'EOF'
#!/bin/bash
echo "Bonjour depuis mon script !"
EOF
chmod +x ~/hello.sh
#@ 17.2
cat > ~/info-system.sh <<'EOF'
#!/bin/bash
date
whoami
pwd
EOF
chmod +x ~/info-system.sh
#@ 17.3
cat > ~/check-file.sh <<'EOF'
#!/bin/bash
if [ $# -eq 0 ]; then
    echo "Usage : $0 chemin"
    exit 1
fi
if [ -e "$1" ]; then echo "EXISTE"; else echo "ABSENT"; fi
EOF
chmod +x ~/check-file.sh
#@ 17.4
cat > ~/create-users.sh <<'EOF'
#!/bin/bash
mkdir -p ~/users
for i in 1 2 3 4 5; do
    touch ~/users/user$i.txt
done
EOF
chmod +x ~/create-users.sh
#@ 17.5
cat > ~/compteur.sh <<'EOF'
#!/bin/bash
find "$1" -maxdepth 1 -type f -name '*.txt' | wc -l
EOF
chmod +x ~/compteur.sh
''',
    18: r'''
#@ 18.1
(crontab -l 2>/dev/null; echo '* * * * * date >> /home/etudiant/tick.log') | crontab -
#@ 18.2
# Le 6e champ est l'utilisateur ; chemin absolu obligatoire
echo '0 2 * * * root /home/etudiant/hello.sh' | sudo tee /etc/cron.d/backup-lab > /dev/null
#@ 18.3
# Pas de « .sh » : run-parts ignore les noms contenant un point
printf '#!/bin/bash\nrm -f /tmp/*.tmp\n' | sudo tee /etc/cron.daily/nettoyage-tmp > /dev/null
sudo chmod 755 /etc/cron.daily/nettoyage-tmp
#@ 18.4
echo '30 8 * * 1' > ~/cron-quiz.txt
#@ 18.1
# Attendre que cron ait écrit au moins deux horodatages
sleep 130
''',
    19: r'''
#@ 19.1
cat > ~/rapport.sh <<'EOF'
#!/bin/bash
{ date; df -h; free -h; uptime; } > ~/rapport-systeme.txt
EOF
chmod +x ~/rapport.sh
#@ 19.2
ps -eo pid,rss --sort=-rss --no-headers | head -1 | awk '{print $1}' > ~/gourmand.txt
#@ 19.3
sudo du -s /var/* 2>/dev/null | sort -n | tail -1 | cut -f2 > ~/plus-gros-var.txt
''',
    20: r'''
#@ 20.1
logger "Mon premier log"
sleep 1
#@ 20.2
# Piège : certaines lignes INFO contiennent le mot ERROR ; on cherche le niveau [ERROR]
sudo grep -c '\[ERROR\]' /var/log/app/app.log > ~/error-count.txt
#@ 20.3
sudo grep '^2026-03-15 .*\[ERROR\]' /var/log/app/app.log > ~/erreurs-15.txt
#@ 20.4
cat > ~/log-analyzer.sh <<'EOF'
#!/bin/bash
for niveau in INFO WARNING ERROR; do
    echo "$niveau: $(grep -c "\[$niveau\]" "$1")"
done
EOF
chmod +x ~/log-analyzer.sh
#@ 20.5
printf '/var/log/app/*.log {\n    daily\n    rotate 7\n    compress\n    missingok\n}\n' | sudo tee /etc/logrotate.d/app-lab > /dev/null
''',
    21: r'''
#@ 21.1
hostname -I | awk '{print $1}' > ~/mon-ip.txt
#@ 21.2
hostname > ~/hostname.txt
#@ 21.3
# Le programme mystère écoute sur 0.0.0.0 ; les ports en 127.0.0.x sont SSH et le DNS interne de Docker
ss -tln | awk '$4 ~ /^0\.0\.0\.0:/ {split($4, a, ":"); print a[2]}' | head -1 > ~/port-mystere.txt
#@ 21.4
echo "192.168.1.100 serveur-local" | sudo tee -a /etc/hosts > /dev/null
#@ 21.5
awk '/^nameserver/{print $2; exit}' /etc/resolv.conf > ~/dns.txt
''',
    22: r'''
#@ 22.1
mkdir -p -m 700 ~/.ssh
ssh-keygen -q -t ed25519 -N '' -f ~/.ssh/id_ed25519
#@ 22.2
# En classe : ssh-copy-id deploy@localhost (mot de passe deploy123)
sshpass -p deploy123 ssh-copy-id -o StrictHostKeyChecking=accept-new deploy@localhost 2>/dev/null
#@ 22.3
printf 'Host prod\n    HostName localhost\n    User deploy\n' > ~/.ssh/config
#@ 22.4
scp -q ~/a-envoyer/livrable.txt prod:
#@ 22.5
sudo sed -i -E 's/^#?PasswordAuthentication .*/PasswordAuthentication no/; s/^#?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sshd -t
sudo service ssh reload
sleep 1
''',
    23: r'''
#@ 23.1
find / -perm -4000 -type f 2>/dev/null > ~/suid-files.txt
#@ 23.2
sudo chmod u-s /usr/local/bin/lecteur-root
#@ 23.3
sudo chmod 600 /etc/app-secret.conf
#@ 23.4
awk -F: '$3 == 0 {print $1}' /etc/passwd > ~/uid-zero.txt
# userdel refuse (des processus tournent en UID 0) : on neutralise le compte
sudo passwd -l toor
sudo usermod -s /usr/sbin/nologin toor
#@ 23.5
sudo chage -M 90 securise
sudo passwd -l securise
''',
    24: r'''
#@ 24.1
# Trois problèmes : fins de ligne Windows (CRLF), shebang « /bin/bsh », fichier non exécutable
f=~/depannage/deploy.sh
sed -i 's/\r$//' "$f"
sed -i '1s|.*|#!/bin/bash|' "$f"
chmod +x "$f"
#@ 24.2
big=$(sudo find /var/log -type f -size +10M)
echo "$big" > ~/gros-log.txt
sudo truncate -s 0 "$big"
#@ 24.3
# StrictModes : ni le home, ni .ssh, ni authorized_keys ne doivent être modifiables par d'autres
sudo chmod 755 /home/ops
sudo chown -R ops:ops /home/ops/.ssh
sudo chmod 700 /home/ops/.ssh
sudo chmod 600 /home/ops/.ssh/authorized_keys
#@ 24.4
# Trois erreurs : nom de fichier avec un point (ignoré par cron), champ utilisateur absent, script non exécutable
sudo rm /etc/cron.d/rapport.cron
echo '* * * * * root /usr/local/bin/rapport-cron.sh' | sudo tee /etc/cron.d/rapport > /dev/null
sudo chmod +x /usr/local/bin/rapport-cron.sh
#@ 24.5
sudo sed -i 's/^PORT=.*/PORT=8080/' /etc/mon-service.conf
sudo mkdir -p /var/log/mon-service
sudo chown monsvc /var/log/mon-service
#@ 24.4
# Attendre que cron exécute la tâche réparée
sleep 75
''',
    25: r'''
#@ 25.1
sudo useradd -m -s /bin/bash webmaster
sudo groupadd www
sudo usermod -aG www webmaster
sudo mkdir -p /var/www/monsite/html /var/www/monsite/logs /var/www/monsite/backup
sudo chgrp -R www /var/www/monsite
sudo chmod -R 2775 /var/www/monsite
#@ 25.2
sudo -u webmaster bash -c 'echo "<h1>Bienvenue</h1>" > /var/www/monsite/html/index.html; for i in 1 2 3 4 5; do echo "GET /page$i 200" >> /var/www/monsite/logs/access.log; done'
#@ 25.3
sudo tee /home/webmaster/backup.sh > /dev/null <<'EOF'
#!/bin/bash
B=/var/www/monsite/backup
tar -czf "$B/site-$(date +%Y%m%d-%H%M%S).tar.gz" -C /var/www/monsite html
df -h > "$B/disk-report.txt"
EOF
sudo chown webmaster: /home/webmaster/backup.sh
sudo chmod 755 /home/webmaster/backup.sh
#@ 25.4
echo '0 3 * * * webmaster /home/webmaster/backup.sh' | sudo tee /etc/cron.d/backup-web > /dev/null
#@ 25.5
# Ligne ajoutée à la fin de backup.sh : garde les 7 archives les plus récentes
echo 'ls -1t "$B"/site-*.tar.gz | tail -n +8 | xargs -r rm -f' | sudo tee -a /home/webmaster/backup.sh > /dev/null
#@ 25.6
sudo tee /home/webmaster/monitoring.sh > /dev/null <<'EOF'
#!/bin/bash
u=$(df / | awk 'NR==2{print $5}' | tr -d %)
if [ "$u" -gt "$1" ]; then m="ALERTE disque : ${u}% (seuil $1%)"; else m="OK disque : ${u}%"; fi
echo "$m"
echo "$(date '+%F %T') $m" >> /var/www/monsite/logs/monitoring.txt
EOF
sudo chown webmaster: /home/webmaster/monitoring.sh
sudo chmod 755 /home/webmaster/monitoring.sh
#@ 25.7
sudo install -d -m 700 -o webmaster -g webmaster /home/webmaster/.ssh
sudo tee -a /home/webmaster/.ssh/authorized_keys < ~/.ssh/id_ed25519.pub > /dev/null
sudo chown webmaster: /home/webmaster/.ssh/authorized_keys
sudo chmod 600 /home/webmaster/.ssh/authorized_keys
''',
}
