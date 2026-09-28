"""Solutions de référence, une par étape, exécutées en tant qu'« etudiant »
(avec sudo sans mot de passe dans le conteneur de test).

Elles résolvent les exercices comme le ferait un étudiant, sans lire les
réponses attendues : elles valident donc aussi que chaque énigme est soluble.
Elles servent également de corrigé pour l'enseignant.
"""

SOLUTIONS = {
    1: r'''
sed -n 's/^CODE=//p' /opt/archives-marc/2024/reseau/baie/note.txt > ~/code-baie.txt
cat ~/passation/.jeton-vpn > ~/jeton-vpn.txt
mkdir -p ~/documents ~/projets
touch ~/documents/journal.txt
''',
    2: r'''
mkdir -p /home/etudiant/projets/boutique/src
echo "-S" > ~/reponse-man.txt
echo "../../tarifs.txt" > ~/chemin-relatif.txt
cd ~/partage-marc/clients/2024/../.. && pwd > ~/chemin-absolu.txt
''',
    3: r'''
mkdir -p ~/documents/procedures ~/documents/comptes-rendus
echo "Procédure arrivée nouveau salarié" > ~/documents/procedures/arrivee.txt
echo "1. Créer le compte utilisateur" >> ~/documents/procedures/arrivee.txt
cp ~/documents/procedures/arrivee.txt ~/documents/comptes-rendus/arrivee-a-relire.txt
rm ~/bureau-marc/*.tmp
rm -r ~/bureau-marc/vieux-projets
''',
    4: r'''
echo "produit;prix" > ~/tarifs-2025.csv
ln ~/tarifs-2025.csv ~/tarifs-courant.csv
stat -c %h /opt/sauvegardes/base-clients.db > ~/nb-liens.txt
ln -s /etc ~/conf-systeme
b=$(find ~/raccourcis-marc -xtype l -printf '%f\n')
echo "$b" > ~/lien-casse.txt
ln -sfn annuaire.txt ~/raccourcis-marc/"$b"
''',
    5: r'''
find /etc -name "*.conf" 2>/dev/null > ~/audit-conf.txt
grep -rl "BON-" /srv/archives > ~/bon-reduction.txt
find /srv/archives -name "*.log" | wc -l > ~/nb-logs.txt
find /srv/archives -size +5M > ~/gros-fichier.txt
grep -ci erreur /srv/archives/rapport.txt > ~/nb-erreurs.txt
''',
    6: r'''
ls /etc | wc -l > ~/nb-etc.txt
find /root > ~/find-ok.txt 2> ~/erreurs.txt
bavard > ~/sortie.txt 2> ~/erreurs-bavard.txt
ls /usr/bin | tee ~/programmes.txt > /dev/null
cut -d: -f1 /etc/passwd | sort -u > ~/users-sorted.txt
find /etc -type f 2>/dev/null | wc -l > ~/nb-fichiers-etc.txt
''',
    7: r'''
printf 'serveur=localhost\nport=8080\ndebug=false\n' > ~/config.txt
sed -i '/INTRUS/d' ~/config/poeme.txt
echo "Fin" >> ~/config/poeme.txt
sed -i 's/debug=false/debug=true/' ~/config.txt
sed -i 's/ancien-serveur/nouveau-serveur/g' ~/config/app.conf
''',
    8: r'''
cd ~/regex
grep '^[rs]' /etc/passwd > rs.txt
grep -oE '[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]{2,}' contacts.txt > emails-valides.txt
grep -vE '^\s*(#|$)' serveur.conf > serveur-clean.txt
sed 's/[0-9]/X/g' contacts.txt > censure.txt
grep -oE '0[1-9]( [0-9]{2}){4}' contacts.txt > telephones.txt
''',
    9: r'''
cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn > ~/shells-count.txt
awk '{print $1}' ~/logs/access.log | sort | uniq -c | sort -rn | head -3 | awk '{print $2}' > ~/top-ip.txt
awk '$9 == 404' ~/logs/access.log | wc -l > ~/nb-404.txt
awk -F: '$3 >= 1000 && $3 < 65534 {print $1, $3}' /etc/passwd > ~/users-uid.txt
tr 'a-z' 'A-Z' < ~/texte/minuscules.txt > ~/texte/majuscules.txt
''',
    10: r'''
sudo useradd -m -s /bin/bash alice
sudo useradd -m -s /bin/bash bob
sudo groupadd equipe
sudo usermod -aG equipe alice
sudo usermod -aG equipe bob
sudo mkdir /home/partage
sudo chgrp equipe /home/partage
sudo chmod 2770 /home/partage
sudo touch /home/partage/secret.txt
sudo chown alice:equipe /home/partage/secret.txt
sudo chmod 640 /home/partage/secret.txt
chmod u+x ~/scripts/deploy.sh
''',
    11: r'''
sudo useradd -m -s /bin/bash stagiaire
sudo usermod -aG sudo stagiaire
p=$(pgrep -x rogue-worker)
echo "$p $(ps -o user= -p "$p")" > ~/rogue.txt
sudo kill "$p"
setsid nohup nice -n 10 sleep 1000 > /dev/null 2>&1 < /dev/null &
sudo kill -HUP "$(pgrep -x lab-service)"
sleep 2
''',
    12: r'''
for u in papa maman fils fille invite; do sudo useradd -m -s /bin/bash $u; done
for u in papa maman fils fille; do sudo -u $u mkdir /home/$u/Travail /home/$u/Bazar; done
sudo groupadd parents
sudo groupadd enfants
sudo groupadd famille
for u in papa maman; do sudo usermod -aG parents,famille $u; done
for u in fils fille; do sudo usermod -aG enfants,famille $u; done
sudo mkdir /home/famille /home/parents-only
sudo chgrp famille /home/famille
sudo chmod 2770 /home/famille
sudo chgrp parents /home/parents-only
sudo chmod 2770 /home/parents-only
for u in papa maman fils fille; do sudo chmod 750 /home/$u; done
''',
    13: r'''
sudo apt-get update -qq
sudo apt-get install -y -qq tree > /dev/null
dpkg -S /usr/bin/pgrep | cut -d: -f1 > ~/paquet.txt
mkdir -p ~/telechargements
wget -q -O ~/telechargements/page.html https://example.com
sudo apt-get install -y -qq cowsay > /dev/null
sudo apt-get remove -y -qq cowsay > /dev/null
''',
    14: r'''
df -T / | awk 'NR==2{print $2}' > ~/fs-racine.txt
du -s /srv/data/* | sort -n | tail -1 | cut -f2 > ~/plus-gros.txt
du -sm /srv/data | cut -f1 > ~/taille-data.txt
sudo mkdir -p /mnt/usb
echo "/dev/sdb1  /mnt/usb  ext4  defaults  0  2" > ~/fstab-usb.txt
''',
    15: r'''
echo 'export PROJET=linux-lab' >> ~/.bashrc
mkdir -p ~/outils
printf '#!/bin/bash\necho "Bonjour !"\n' > ~/outils/bonjour
chmod +x ~/outils/bonjour
echo 'export PATH="$PATH:$HOME/outils"' >> ~/.bashrc
echo "alias ll='ls -la'" >> ~/.bashrc
''',
    16: r'''
mkdir -p ~/archive-test
touch ~/archive-test/a.txt ~/archive-test/b.txt ~/archive-test/c.txt
cd ~ && tar -czf archive-test.tar.gz archive-test
mkdir -p ~/extraction && tar -xzf ~/archive-test.tar.gz -C ~/extraction
mkdir -p /tmp/livraison && tar -xzf /srv/livraison/paquet.tar.gz -C /tmp/livraison
cat /tmp/livraison/paquet/docs/LISEZMOI.txt > ~/code-livraison.txt
echo "du contenu à compresser" > ~/compress-me.txt
gzip -k ~/compress-me.txt
cd ~ && zip -qr backup.zip archive-test
''',
    17: r'''
cat > ~/hello.sh <<'EOF'
#!/bin/bash
echo "Bonjour depuis mon script !"
EOF
cat > ~/info-system.sh <<'EOF'
#!/bin/bash
date
whoami
pwd
EOF
cat > ~/check-file.sh <<'EOF'
#!/bin/bash
if [ $# -eq 0 ]; then
    echo "Usage : $0 chemin"
    exit 1
fi
if [ -e "$1" ]; then echo "EXISTE"; else echo "ABSENT"; fi
EOF
cat > ~/create-users.sh <<'EOF'
#!/bin/bash
mkdir -p ~/users
for i in 1 2 3 4 5; do
    touch ~/users/user$i.txt
done
EOF
cat > ~/compteur.sh <<'EOF'
#!/bin/bash
find "$1" -maxdepth 1 -type f -name '*.txt' | wc -l
EOF
chmod +x ~/hello.sh ~/info-system.sh ~/check-file.sh ~/create-users.sh ~/compteur.sh
''',
    18: r'''
(crontab -l 2>/dev/null; echo '* * * * * date >> /home/etudiant/tick.log') | crontab -
echo '0 2 * * * root /home/etudiant/hello.sh' | sudo tee /etc/cron.d/backup-lab > /dev/null
printf '#!/bin/bash\nrm -f /tmp/*.tmp\n' | sudo tee /etc/cron.daily/nettoyage-tmp > /dev/null
sudo chmod 755 /etc/cron.daily/nettoyage-tmp
echo '30 8 * * 1' > ~/cron-quiz.txt
sleep 130
''',
    19: r'''
cat > ~/rapport.sh <<'EOF'
#!/bin/bash
{ date; df -h; free -h; uptime; } > ~/rapport-systeme.txt
EOF
chmod +x ~/rapport.sh
ps -eo pid,rss --sort=-rss --no-headers | head -1 | awk '{print $1}' > ~/gourmand.txt
sudo du -s /var/* 2>/dev/null | sort -n | tail -1 | cut -f2 > ~/plus-gros-var.txt
''',
    20: r'''
logger "Mon premier log"
sleep 1
sudo grep -c '\[ERROR\]' /var/log/app/app.log > ~/error-count.txt
sudo grep '^2026-03-15 .*\[ERROR\]' /var/log/app/app.log > ~/erreurs-15.txt
cat > ~/log-analyzer.sh <<'EOF'
#!/bin/bash
for niveau in INFO WARNING ERROR; do
    echo "$niveau: $(grep -c "\[$niveau\]" "$1")"
done
EOF
chmod +x ~/log-analyzer.sh
printf '/var/log/app/*.log {\n    daily\n    rotate 7\n    compress\n    missingok\n}\n' | sudo tee /etc/logrotate.d/app-lab > /dev/null
''',
    21: r'''
hostname -I | awk '{print $1}' > ~/mon-ip.txt
hostname > ~/hostname.txt
ss -tln | awk '$4 ~ /^0\.0\.0\.0:/ {split($4, a, ":"); print a[2]}' | head -1 > ~/port-mystere.txt
echo "192.168.1.100 serveur-local" | sudo tee -a /etc/hosts > /dev/null
awk '/^nameserver/{print $2; exit}' /etc/resolv.conf > ~/dns.txt
''',
    22: r'''
mkdir -p -m 700 ~/.ssh
ssh-keygen -q -t ed25519 -N '' -f ~/.ssh/id_ed25519
sshpass -p deploy123 ssh-copy-id -o StrictHostKeyChecking=accept-new deploy@localhost 2>/dev/null
printf 'Host prod\n    HostName localhost\n    User deploy\n' > ~/.ssh/config
scp -q ~/a-envoyer/livrable.txt prod:
sudo sed -i -E 's/^#?PasswordAuthentication .*/PasswordAuthentication no/; s/^#?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sshd -t
sudo service ssh reload
sleep 1
''',
    23: r'''
find / -perm -4000 -type f 2>/dev/null > ~/suid-files.txt
sudo chmod u-s /usr/local/bin/lecteur-root
sudo chmod 600 /etc/app-secret.conf
awk -F: '$3 == 0 {print $1}' /etc/passwd > ~/uid-zero.txt
sudo passwd -l toor
sudo usermod -s /usr/sbin/nologin toor
sudo chage -M 90 securise
sudo passwd -l securise
''',
    24: r'''
f=~/depannage/deploy.sh
sed -i 's/\r$//' "$f"
sed -i '1s|.*|#!/bin/bash|' "$f"
chmod +x "$f"
big=$(sudo find /var/log -type f -size +10M)
echo "$big" > ~/gros-log.txt
sudo truncate -s 0 "$big"
sudo chmod 755 /home/ops
sudo chown -R ops:ops /home/ops/.ssh
sudo chmod 700 /home/ops/.ssh
sudo chmod 600 /home/ops/.ssh/authorized_keys
sudo rm /etc/cron.d/rapport.cron
echo '* * * * * root /usr/local/bin/rapport-cron.sh' | sudo tee /etc/cron.d/rapport > /dev/null
sudo chmod +x /usr/local/bin/rapport-cron.sh
sudo sed -i 's/^PORT=.*/PORT=8080/' /etc/mon-service.conf
sudo mkdir -p /var/log/mon-service
sudo chown monsvc /var/log/mon-service
sleep 75
''',
    25: r'''
sudo useradd -m -s /bin/bash webmaster
sudo groupadd www
sudo usermod -aG www webmaster
sudo mkdir -p /var/www/monsite/html /var/www/monsite/logs /var/www/monsite/backup
sudo chgrp -R www /var/www/monsite
sudo chmod -R 2775 /var/www/monsite
sudo -u webmaster bash -c 'echo "<h1>Bienvenue</h1>" > /var/www/monsite/html/index.html; for i in 1 2 3 4 5; do echo "GET /page$i 200" >> /var/www/monsite/logs/access.log; done'
sudo tee /home/webmaster/backup.sh > /dev/null <<'EOF'
#!/bin/bash
B=/var/www/monsite/backup
tar -czf "$B/site-$(date +%Y%m%d-%H%M%S).tar.gz" -C /var/www/monsite html
df -h > "$B/disk-report.txt"
ls -1t "$B"/site-*.tar.gz | tail -n +8 | xargs -r rm -f
EOF
sudo tee /home/webmaster/monitoring.sh > /dev/null <<'EOF'
#!/bin/bash
u=$(df / | awk 'NR==2{print $5}' | tr -d %)
if [ "$u" -gt "$1" ]; then m="ALERTE disque : ${u}% (seuil $1%)"; else m="OK disque : ${u}%"; fi
echo "$m"
echo "$(date '+%F %T') $m" >> /var/www/monsite/logs/monitoring.txt
EOF
sudo chown webmaster: /home/webmaster/backup.sh /home/webmaster/monitoring.sh
sudo chmod 755 /home/webmaster/backup.sh /home/webmaster/monitoring.sh
echo '0 3 * * * webmaster /home/webmaster/backup.sh' | sudo tee /etc/cron.d/backup-web > /dev/null
sudo install -d -m 700 -o webmaster -g webmaster /home/webmaster/.ssh
sudo tee -a /home/webmaster/.ssh/authorized_keys < ~/.ssh/id_ed25519.pub > /dev/null
sudo chown webmaster: /home/webmaster/.ssh/authorized_keys
sudo chmod 600 /home/webmaster/.ssh/authorized_keys
''',
}
