"""Corrigé du parcours Linux : un script par étape, exécuté en tant qu'« etudiant » par le banc de test
(avec sudo sans mot de passe dans le conteneur de test).

Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Un même repère peut réapparaître plus loin : le bloc suivant est ajouté à la correction de l'exercice.
Les solutions résolvent les énigmes comme un étudiant, sans lire les réponses attendues.
"""

SOLUTIONS = {
    1: r'''
#@ 1.1
# On explore l'arborescence ; seule une note n'est pas marquée PÉRIMÉ et contient un code
cd /opt/archives-marc
ls -R
f=$(grep -rL 'PÉRIMÉ' --include=note.txt . | xargs grep -l '^CODE=')
cat "$f"
grep '^CODE=' "$f" | cut -d= -f2 > ~/code-baie.txt
cd ~
#@ 1.2
ls -a ~/passation
cat ~/passation/.jeton-vpn.ancien
cat ~/passation/.jeton-vpn > ~/jeton-vpn.txt
#@ 1.3
mkdir ~/documents ~/projets
#@ 1.4
touch ~/documents/journal.txt
#@ 1.5
# Guillemets pour l'espace, ./ (ou --) pour le tiret
cd ~/passation/boite
cat "notes de réunion.txt" | grep '^MOT=' | cut -d= -f2 > ~/mots.txt
cat ./-urgent.txt | grep '^MOT=' | cut -d= -f2 >> ~/mots.txt
cd ~
#@ 1.6
file ~/passation/pieces/*
file ~/passation/pieces/* | grep -i script | cut -d: -f1 | xargs basename > ~/script-trouve.txt
#@ 1.7
mkdir ~/projets/vitrine
cd ~/projets/vitrine
mkdir css js img
touch index.html css/style.css
cd ~
''',
    2: r'''
#@ 2.1
mkdir -p /home/etudiant/projets/boutique/src
echo 'mkdir -p /home/etudiant/projets/boutique/src' > ~/doc-install.txt
#@ 2.2
echo "-S" > ~/reponse-man.txt
#@ 2.3
echo "../../tarifs.txt" > ~/chemin-relatif.txt
#@ 2.4
cd ~/partage-marc/clients/2024/../.. && pwd > ~/chemin-absolu.txt
cd ~
#@ 2.5
# cd est une commande interne du shell : pas de page de manuel, mais « help cd »
type cd > ~/cd-type.txt
help cd | grep -- '-P'
echo "-P" > ~/cd-option.txt
#@ 2.6
ls -lt /opt/rapports-marc
ls -t /opt/rapports-marc | head -n1 > ~/dernier-rapport.txt
#@ 2.7
# Avec less : /=== CLÔTURE puis Entrée ; équivalent non interactif :
grep -A1 '^=== CLÔTURE ===$' ~/exports/journal-export.log | tail -n1 | grep -oE '[0-9]+' > ~/lot.txt
#@ 2.8
cat ~/partage-marc/clients/2024/devis/A-LIRE.txt
c=$(grep -o 'fournisseurs/[^ ]*' ~/partage-marc/clients/2024/devis/A-LIRE.txt)
echo "../../../$c" > ~/chemin-fournisseur.txt
cd ~/partage-marc/clients/2024/devis && cat "../../../$c"
cd ~
''',
    3: r'''
#@ 3.1
mkdir -p ~/documents/{procedures,comptes-rendus}/archives
#@ 3.2
echo "Procédure arrivée nouveau salarié" > ~/documents/procedures/arrivee.txt
#@ 3.3
echo "1. Créer le compte utilisateur" >> ~/documents/procedures/arrivee.txt
#@ 3.4
cp ~/documents/procedures/arrivee.txt ~/documents/comptes-rendus/arrivee-a-relire.txt
#@ 3.5
ls ~/bureau-marc/*.tmp
rm ~/bureau-marc/*.tmp
rm -r ~/bureau-marc/vieux-projets
#@ 3.6
cd ~/bilans
mv -n bilan.txt bilan-ancien.txt
mv -n brouillon-bilan.txt bilan.txt
cd ~
#@ 3.7
ls ~/factures/inbox/facture-2024-*
mv ~/factures/inbox/facture-2024-* ~/factures/2024/
#@ 3.8
# rapport?.txt attraperait aussi rapportA.txt ; [1-9] ne prend que les chiffres
ls ~/rapports-hebdo/rapport[1-9].txt
rm ~/rapports-hebdo/rapport[1-9].txt
#@ 3.9
# * ignore les noms cachés : il faut un motif qui commence par un point
ls -a ~/bureau-marc
ls ~/bureau-marc/.*.tmp
rm ~/bureau-marc/.*.tmp
''',
    4: r'''
#@ 4.1
ln ~/tarifs-2025.csv ~/tarifs-courant.csv
ls -li ~/tarifs-2025.csv ~/tarifs-courant.csv
#@ 4.2
# Les copies (export-*.db compris) ont un autre inode : seul -samefile fait le tri
find /opt/sauvegardes -samefile /opt/sauvegardes/base-clients.db > ~/liens-base.txt
#@ 4.3
ln -s /etc ~/conf-systeme
#@ 4.4
b=$(find ~/raccourcis-marc -xtype l -printf '%f\n')
echo "$b" > ~/lien-casse.txt
#@ 4.5
b=$(cat ~/lien-casse.txt)
ln -sfn annuaire.txt ~/raccourcis-marc/"$b"
#@ 4.6
# Le lien contient un chemin absolu : on le remplace par un chemin relatif au dossier du lien
r=$(basename "$(readlink ~/site-v1/current)")
cd ~/site-v1 && ln -sfn releases/$r current
cd ~
#@ 4.7
# Sans -n, ln traite current (lien vers un dossier) comme ce dossier et crée releases/r2/r3
cd ~/deploi
ln -sfn releases/r3 current
find releases -type l
rm releases/r2/r3
cd ~
#@ 4.8
n=$(grep -oE '[0-9]+' ~/grilles/LISEZ-MOI | head -n1)
f=$(find ~ -inum "$n" 2>/dev/null | head -n1)
ln "$f" ~/grilles/grille.csv
#@ 4.9
readlink ~/raccourcis/dernier
readlink -f ~/raccourcis/dernier > ~/fichier-final.txt
''',
    5: r'''
#@ 5.1
find /etc -type f -name "*.conf" 2>/dev/null > ~/audit-conf.txt
#@ 5.2
grep -rl "BON-" /srv/archives > ~/bon-reduction.txt
#@ 5.3
find /srv/archives -path '*/2023/*' -name "*.log" | wc -l > ~/nb-logs.txt
#@ 5.4
find /srv/archives -size +5M > ~/gros-fichier.txt
#@ 5.5
grep -ci erreur /srv/archives/rapport.txt > ~/nb-erreurs.txt
#@ 5.6
find /srv/archives -type f -newer /srv/archives/.derniere-sauvegarde > ~/modifies.txt
#@ 5.7
grep -ciw erreur /srv/archives/rapport2.txt > ~/nb-erreur-mot.txt
#@ 5.8
# -size -1M arrondit chaque taille au Mio supérieur : seuls les fichiers vides sont « à moins de 1 »
find /srv/medias -type f -size -1048576c > ~/petits-medias.txt
#@ 5.9
grep -B1 'FATAL' ~/logs-app/app.log
grep -B1 'FATAL' ~/logs-app/app.log | head -n1 > ~/cause.txt
''',
    6: r'''
#@ 6.1
ls -A /etc | wc -l > ~/nb-etc.txt
#@ 6.2
find /root > ~/find-ok.txt 2> ~/erreurs.txt
#@ 6.3
# L'ordre compte : d'abord la sortie standard vers le fichier, puis les erreurs au même endroit
bavard > ~/tout.txt 2>&1
#@ 6.4
ls /usr/bin | tee ~/programmes.txt | wc -l > ~/nb-programmes.txt
#@ 6.5
cut -d' ' -f4 ~/texte/badges.txt | sort -u > ~/badgeurs.txt
#@ 6.6
find /etc -type f 2>/dev/null | wc -l > ~/nb-fichiers-etc.txt
#@ 6.7
# 2>&1 envoie les erreurs dans le pipe, puis >/dev/null jette la sortie normale
compteur 2>&1 >/dev/null | wc -l > ~/nb-erreurs-compteur.txt
#@ 6.8
sort -rn ~/texte/ventes.txt | head -n3 > ~/top-ventes.txt
#@ 6.9
cut -d' ' -f4 ~/texte/badges.txt | sort | uniq -d > ~/badges-multiples.txt
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
sed -i 's/debug=false/debug=true/' ~/config/dev.conf
#@ 7.4
sed -i 's/ancien-serveur/nouveau-serveur/g' ~/config/app.conf
#@ 7.5
sed -i 's|/var/log/boutique|/srv/logs/boutique|g' ~/config/chemins.conf
#@ 7.6
sed -i.bak 's/^maintenance=on$/maintenance=off/' ~/config/app-prod.conf
#@ 7.7
# De la ligne [admin] à la section suivante seulement
sed -i '/^\[admin\]/,/^\[/ s/^port=8080$/port=9090/' ~/config/services.ini
#@ 7.8
sed -i '/^DEBUG/d' ~/config/app.log
''',
    8: r'''
cd ~/regex
#@ 8.1
grep '^[rs]' /etc/passwd > rs.txt
#@ 8.2
grep -oE '[a-z0-9._-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}' contacts.txt > emails-valides.txt
#@ 8.3
grep -vE '^[[:space:]]*(#|$)' serveur.conf > serveur-clean.txt
#@ 8.4
sed -E 's/\b0[1-9]( [0-9]{2}){4}\b/XX XX XX XX XX/g' contacts.txt > censure.txt
#@ 8.5
grep -owE '0[1-9]( [0-9]{2}){4}' contacts.txt > telephones.txt
#@ 8.6
sed -E 's#([0-9]{2})/([0-9]{2})/([0-9]{4})#\3-\2-\1#g' paiements.txt > paiements-iso.txt
#@ 8.7
grep -xE '[a-z][a-z0-9_-]{2,15}' demandes.txt > identifiants.txt
#@ 8.8
sed -i -E 's/;9\.99$/;10.49/' tarifs.csv
''',
    9: r'''
#@ 9.1
cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn > ~/shells-count.txt
#@ 9.2
awk '$9 >= 400 {print $1}' ~/logs/access.log | sort | uniq -c | sort -rn | head -3 | awk '{print $2}' > ~/top-ip.txt
#@ 9.3
# Piège : « grep 404 » compte aussi les tailles et les pages qui contiennent 404 ; le code HTTP est le 9e champ
awk '$9 == 404' ~/logs/access.log | wc -l > ~/nb-404.txt
#@ 9.4
awk -F: '$3 >= 1000 && $3 < 65534 && $7 !~ /(nologin|false)$/ {print $1, $3}' ~/texte/passwd-serveur > ~/users-uid.txt
#@ 9.5
tr 'a-z' 'A-Z' < ~/texte/minuscules.txt > ~/texte/majuscules.txt
#@ 9.6
ip=$(grep -oE '([0-9]+\.){3}[0-9]+' ~/logs/LISEZ-MOI)
awk -v ip="$ip" '$1 == ip { s += $10 } END { print s }' ~/logs/access.log > ~/octets-ip.txt
#@ 9.7
awk -F';' 'NR > 1 { t[$1] += $2 * $3 } END { for (p in t) print t[p], p }' ~/texte/ventes.csv | sort -rn | head -n3 | awk '{print $2}' > ~/top-produits.txt
#@ 9.8
sed 's/.*/\U&/' ~/texte/accents.txt > ~/texte/accents-maj.txt
#@ 9.9
awk -F: '{print $2}' ~/logs/access.log | sort | uniq -c | sort -rn | head -n1 | awk '{print $2}' > ~/heure-pointe.txt
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
ls -l ~/scripts/deploy.sh
chmod u+x ~/scripts/deploy.sh
#@ 10.6
sudo chmod g+s /home/partage
#@ 10.7
id webdev
sudo usermod -aG boutique webdev
#@ 10.8
# « sudo echo … >> f » : la redirection est faite par le shell de l'étudiant, pas par root
echo "BOUTIQUE_ENV=prod" | sudo tee -a /etc/boutique.env > /dev/null
#@ 10.9
cat ~/droits/CONSIGNE
# Traduction de chaque triade de la consigne en chiffre octal
while read -r f d; do
  o=$(echo "${d:1}" | sed 's/r/4/g; s/w/2/g; s/x/1/g; s/-/0/g' | fold -w3 | awk -F '' '{ print $1 + $2 + $3 }' | paste -sd '')
  chmod "$o" ~/droits/"$f"
done < ~/droits/CONSIGNE
ls -l ~/droits
''',
    11: r'''
#@ 11.1
sudo useradd -m -s /bin/bash stagiaire
sudo usermod -aG sudo stagiaire
echo 'stagiaire:Stagiaire-2026!' | sudo chpasswd
sudo -l -U stagiaire
#@ 11.2
p=$(pgrep -x rogue-worker)
echo "$p $(ps -o user= -p "$p")" > ~/rogue.txt
#@ 11.3
# Le processus appartient à « intrus » : sudo est indispensable ; kill sans option envoie TERM
sudo kill "$p"
sleep 1
#@ 11.4
nice -n 10 sleep 1000 > /dev/null 2>&1 &
#@ 11.5
sudo kill -HUP "$(pgrep -x lab-service)"
sleep 2
#@ 11.6
# mineur est relancé par son parent : on arrête d'abord le parent, puis l'enfant
m=$(pgrep -x mineur | head -n1)
pp=$(ps -o ppid= -p "$m" | tr -d ' ')
ps -o pid,ppid,user,cmd -p "$m,$pp"
sudo kill "$pp"
sudo kill "$(pgrep -x mineur)"
sleep 1
#@ 11.7
kill -STOP "$(pgrep -x export-nuit)"
ps -o pid,stat,cmd -C export-nuit
#@ 11.8
echo 'thomas ALL=(root) NOPASSWD: /usr/local/sbin/relance-boutique' > /tmp/regle-thomas
sudo visudo -cf /tmp/regle-thomas
sudo install -m 440 -o root -g root /tmp/regle-thomas /etc/sudoers.d/thomas
sudo -l -U thomas
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
# Les dossiers de la famille ont été créés en 755 : Marc avait changé HOME_MODE
ls -l /home
grep HOME_MODE /etc/login.defs
sudo sed -i 's/^HOME_MODE.*/HOME_MODE\t0750/' /etc/login.defs
for u in papa maman fils fille invite; do sudo chmod 750 /home/$u; done
#@ 12.6
# Le groupe enfants peut traverser /home/fille (sans la lister) et lister Bazar
sudo chgrp enfants /home/fille /home/fille/Bazar
sudo chmod 710 /home/fille
sudo chmod 750 /home/fille/Bazar
#@ 12.7
find /srv/ancien-pc -type f -perm -o=r > ~/fichiers-ouverts.txt
''',
    13: r'''
#@ 13.1
sudo apt-get update -qq
sudo apt-get install -y -qq tree > /dev/null
#@ 13.2
cat ~/paquets/question.txt
f=$(grep -oE '/[^ ]+' ~/paquets/question.txt | head -n1)
dpkg -S "$f" | cut -d: -f1 > ~/paquet.txt
#@ 13.3
mkdir -p ~/telechargements
wget -q -O ~/telechargements/page.html https://example.com
#@ 13.4
sudo apt-get install -y -qq cowsay > /dev/null
sudo apt-get remove -y -qq cowsay > /dev/null
#@ 13.5
dpkg -c /srv/paquets/cs-outils_*_all.deb
dpkg -c /srv/paquets/cs-outils_*_all.deb | grep -oE '\./usr/bin/[^ ]+' | sed 's/^\.//' > ~/contenu-deb.txt
sudo dpkg -i /srv/paquets/cs-outils_*_all.deb > /dev/null
#@ 13.6
dpkg -I /srv/paquets/cs-rapport_2.0_all.deb | grep Depends
# cs-base 1.0 ne suffit pas (>= 1.2 exigé) : on installe la 1.3 en même temps
sudo dpkg -i /srv/paquets/cs-base_1.3_all.deb /srv/paquets/cs-rapport_2.0_all.deb > /dev/null
#@ 13.7
sudo apt-get purge -y -qq cs-ancien > /dev/null
dpkg -l cs-ancien 2>&1 | tail -n1
#@ 13.8
c=$(grep -oE 'commande [a-z]+' ~/paquets/question-bin.txt | cut -d' ' -f2)
dpkg -S /usr/bin/$c || true
dpkg -S /bin/$c | cut -d: -f1 > ~/paquet-bin.txt
#@ 13.9
dpkg -V cs-supervision
dpkg -V cs-supervision | awk '{print $NF}' > ~/fichier-modifie.txt
sudo dpkg -i /srv/paquets/cs-supervision_1.0_all.deb > /dev/null
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
# blkid lit l'UUID et le type, même dans un fichier image ; nofail : le démarrage continue si le disque est absent
eval "$(blkid -o export /srv/disques/usb-sauvegarde.img)"
echo "UUID=$UUID  /mnt/usb  $TYPE  defaults,nofail  0  2" > ~/fstab-usb.txt
#@ 14.5
# Le joker * ignore les dossiers cachés : on les ajoute avec .[!.]*
du -s /srv/stockage/* /srv/stockage/.[!.]* | sort -n | tail -n1 | cut -f2 > ~/fantome.txt
#@ 14.6
# du compte les blocs réellement occupés ; ls -l affiche la taille annoncée des fichiers creux
du -s /srv/vm/* | sort -n | tail -n1 | cut -f2 | xargs basename > ~/vm-reel.txt
#@ 14.7
# On compte les fichiers (donc les inodes) de chaque sous-dossier, pas leur taille
for d in /srv/sessions/*/; do echo "$(find "$d" -type f | wc -l) $(basename "$d")"; done | sort -n | tail -n1 | cut -d' ' -f2 > ~/inodes.txt
''',
    15: r'''
#@ 15.1
echo 'export PROJET=linux-lab' >> ~/.bashrc
#@ 15.2
mkdir -p ~/outils
printf '#!/bin/bash\necho "Bonjour !"\n' > ~/outils/bonjour
chmod +x ~/outils/bonjour
# $HOME et non ~ : entre guillemets, ~ resterait tel quel et seul bash saurait l'interpréter
echo 'export PATH="$PATH:$HOME/outils"' >> ~/.bashrc
#@ 15.3
# L'alias de Marc est en haut du fichier ; celui d'Ubuntu, plus bas, l'écrase : la dernière définition gagne
grep -n "alias ll" ~/.bashrc
echo "alias ll='ls -lah'" >> ~/.bashrc
#@ 15.4
# CIBLE est définie sans export : les programmes lancés depuis le shell ne la reçoivent pas
sed -i 's/^CIBLE=/export CIBLE=/' ~/.bashrc
#@ 15.5
# Dans un shell interactif de julien, un dossier placé en tête du PATH fournit un faux sudo
f=$(sudo -iu julien bash -ic 'type -P sudo' 2>/dev/null | tail -n1)
echo "$f" > ~/faux-sudo.txt
d=$(dirname "$f")
sudo grep -n "$d" /home/julien/.bashrc
sudo sed -i "\#$d#d" /home/julien/.bashrc
sudo rm -rf "$d"
#@ 15.6
# sudo utilise son propre PATH (secure_path) : on y installe une copie appartenant à root
sudo grep -r secure_path /etc/sudoers /etc/sudoers.d/
sudo install -m 755 -o root -g root ~/outils/bonjour /usr/local/bin/bonjour
sudo bonjour
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
#@ 16.6
# Le membre s'extrait par son chemin exact dans l'archive (attention au brouillon au nom voisin)
m=$(tar -tzf /srv/sauvegardes/compta-2026-09-28.tar.gz | grep '/tarifs-2026\.csv$')
mkdir -p ~/restauration
tar -xzf /srv/sauvegardes/compta-2026-09-28.tar.gz -C ~/restauration "$m"
#@ 16.7
cd /srv/livraison2 && sha256sum -c SHA256SUMS 2>/dev/null | grep -v ': OK$' | cut -d: -f1 > ~/corrompues.txt
#@ 16.8
# file révèle le vrai format de chaque fichier, quelle que soit son extension
file /srv/mystere/*
d=$(mktemp -d)
tar -xf /srv/mystere/rapport.zip -C "$d"        # en réalité une archive tar compressée (gzip)
unzip -q /srv/mystere/photos.tar.gz -d "$d"     # en réalité une archive zip
tar -xf /srv/mystere/notes.gz -C "$d"           # en réalité une archive tar non compressée
cat "$d"/*/secret.txt > ~/secrets.txt
#@ 16.9
cd ~ && tar -czf boutique.tar.gz --exclude=node_modules --exclude=.git --exclude='*.log' projet-boutique
tar -tzf ~/boutique.tar.gz
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
    echo "Usage : $0 chemin" >&2
    exit 1
fi
if [ -e "$1" ]; then echo "EXISTE"; else echo "ABSENT"; fi
EOF
chmod +x ~/check-file.sh
#@ 17.4
cat > ~/create-users.sh <<'EOF'
#!/bin/bash
mkdir -p ~/users
for i in $(seq 1 "$1"); do
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
#@ 17.6
cat > ~/renommer.sh <<'EOF'
#!/bin/bash
# Le joker trie les noms par ordre alphabétique ; les guillemets protègent les espaces
i=1
for f in "$1"/IMG_*.JPG; do
    [ -e "$f" ] || continue
    printf -v nom 'photo-%03d.jpg' "$i"
    mv -- "$f" "$1/$nom"
    i=$((i + 1))
done
EOF
chmod +x ~/renommer.sh
#@ 17.7
cat > ~/totaux.sh <<'EOF'
#!/bin/bash
awk -F';' 'NR > 1 { t[$1] += $2 } END { for (c in t) print c, t[c] }' "$1" | sort -k2,2nr
EOF
chmod +x ~/totaux.sh
#@ 17.8
# Cinq bogues : espaces autour du =, crochets collés, boucle sur ls, nom de la copie (chemin complet) et calcul du compteur
cat > ~/marc/sauvegarde-conf.sh <<'EOF'
#!/bin/bash
# Sauvegarde des fichiers de configuration (script de Marc, réparé)
# Usage : sauvegarde-conf.sh DOSSIER
# Copie chaque fichier .conf de DOSSIER dans ~/marc/copies/ en ajoutant .bak à son nom
# (exemple : DOSSIER/nginx.conf -> ~/marc/copies/nginx.conf.bak),
# puis affiche : N fichier(s) sauvegardé(s)
DEST=~/marc/copies
if [ $# -eq 0 ]; then
    echo "Usage : $0 DOSSIER" >&2
    exit 1
fi
mkdir -p "$DEST"
N=0
for f in "$1"/*.conf; do
    [ -e "$f" ] || continue
    cp -- "$f" "$DEST/$(basename "$f").bak"
    N=$((N + 1))
done
echo "$N fichier(s) sauvegardé(s)"
EOF
''',
    18: r'''
#@ 18.1
(crontab -l 2>/dev/null; echo '* * * * * date >> /home/etudiant/tick.log') | crontab -
#@ 18.5
# cron coupe la commande au premier % (la suite devient l'entrée standard de la commande) : on écrit \%
grep CRON /var/log/syslog | tail -n 3
crontab -l | sed 's/date +%H:%M/date +\\%H:\\%M/' | crontab -
#@ 18.6
# cron ne lit pas ~/.bashrc : on définit PROJET et un PATH complet en tête de crontab
(echo 'PROJET=linux-lab'; echo 'PATH=/home/etudiant/outils:/usr/local/bin:/usr/bin:/bin'; crontab -l) | crontab -
#@ 18.7
# D'abord voir ce que dit la tâche : sortie et erreurs ajoutées à un journal
printf '# Export de la comptabilité (toutes les minutes pour le lab)\n* * * * * root /usr/local/sbin/export-compta >> /var/log/export-compta.log 2>&1\n' | sudo tee /etc/cron.d/export-compta > /dev/null
for i in $(seq 90); do sudo grep -q introuvable /var/log/export-compta.log 2>/dev/null && break; sleep 1; done
sudo cat /var/log/export-compta.log
# L'erreur indique le dossier manquant : on le crée
sudo mkdir -p /srv/compta/exports
#@ 18.8
# flock -n : si le verrou est déjà pris, l'exécution suivante abandonne aussitôt
printf '# Synchronisation du catalogue\n* * * * * root flock -n /run/lock/sync-catalogue.lock /usr/local/sbin/sync-catalogue\n' | sudo tee /etc/cron.d/sync-catalogue > /dev/null
#@ 18.2
# root ne doit exécuter qu'un fichier que seul root peut modifier : copie dans un dossier système
sudo install -m 755 -o root -g root ~/hello.sh /usr/local/sbin/hello
echo '0 2 * * * root /usr/local/sbin/hello' | sudo tee /etc/cron.d/backup-lab > /dev/null
#@ 18.3
# Pas de « .sh » : run-parts ignore les noms contenant un point
printf '#!/bin/bash\nrm -f /tmp/*.tmp\n' | sudo tee /etc/cron.daily/nettoyage-tmp > /dev/null
sudo chmod 755 /etc/cron.daily/nettoyage-tmp
run-parts --test /etc/cron.daily
#@ 18.4
printf '%s\n' '*/10 8-18 * * 1-5' '45 23 1,15 * *' '0 0 * * 0' '0 6 1 1,4,7,10 *' > ~/cron-quiz.txt
#@ 18.1
# Attendre que cron ait exécuté la tâche au moins deux fois
for i in $(seq 150); do [ "$(sort -u ~/tick.log 2>/dev/null | wc -l)" -ge 2 ] && break; sleep 2; done
''',
    19: r'''
#@ 19.1
cat > ~/rapport.sh <<'EOF'
#!/bin/bash
{ date; df -h; free -h; uptime; } > "$HOME/rapport-systeme.txt"
EOF
chmod +x ~/rapport.sh
#@ 19.2
ps -eo pid,rss --sort=-rss --no-headers | head -1 | awk '{print $1}' > ~/gourmand.txt
#@ 19.3
sudo find /var -xdev -type f -printf '%s %p\n' 2>/dev/null | sort -n | tail -n1 | cut -d' ' -f2- > ~/plus-gros-var.txt
#@ 19.4
# free montre la mémoire de l'hôte ; la limite du conteneur est dans les cgroups
f=/sys/fs/cgroup/memory.max; [ -r $f ] || f=/sys/fs/cgroup/memory/memory.limit_in_bytes
echo $(( $(cat $f) / 1048576 )) > ~/limite-memoire.txt
#@ 19.5
# top mesure la consommation instantanée (2e mesure, triée par %CPU)
pid=$(top -b -d 2 -n 2 -o %CPU | awk '/^ *PID/ {n++; next} n == 2 && /^ *[0-9]/ {print $1; exit}')
ps -o comm= -p "$pid" > ~/cpu.txt
sudo renice -n 15 -p "$pid"
#@ 19.6
# Le fichier supprimé est toujours ouvert : lsof +L1 le montre, /proc/PID/fd permet de le vider
read -r pid fd < <(sudo lsof +L1 2>/dev/null | awk '/cache-vignettes/ {print $2, $4; exit}')
echo "$pid" > ~/cache-pid.txt
sudo truncate -s 0 "/proc/$pid/fd/${fd%%[a-z]*}"
#@ 19.7
# Un zombie ne se tue pas : on arrête son parent, et le processus n°1 récupère les zombies
ps -eo pid,ppid,stat,comm | awk '$3 ~ /^Z/'
pp=$(ps -eo ppid=,stat= | awk '$2 ~ /^Z/ {print $1; exit}')
echo "$pp" > ~/parent-zombies.txt
sudo kill "$pp"
sleep 1
''',
    20: r'''
#@ 20.1
logger -t cimes-backup "Test de journalisation"
sleep 1
#@ 20.2
# Piège : certaines lignes INFO contiennent le mot ERROR ; on compte le niveau [ERROR]
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
sudo logrotate -d /etc/logrotate.d/app-lab
#@ 20.6
# Une tentative laisse plusieurs lignes : on ne compte que « Failed password »
A=/var/log/lab/auth.log
read -r n ip < <(sudo grep 'Failed password' $A | grep -oE 'from [0-9.]+' | sort | uniq -c | sort -rn | head -n1 | awk '{print $1, $3}')
echo "$ip $n" > ~/attaquant.txt
# Le compte visé est le mot qui précède « from » (« invalid user » décale les champs)
sudo grep 'Failed password' $A | grep " from $ip port" | awk '{for (i = 1; i < NF; i++) if ($(i + 1) == "from") print $i}' | sort -u > ~/comptes-vises.txt
#@ 20.7
sudo zgrep -h '^2026-03-14 .*\[ERROR\]' /var/log/boutique/shop.log* | wc -l > ~/erreurs-14.txt
#@ 20.8
# Le service garde son journal ouvert : après la rotation, on lui demande de le rouvrir (HUP)
printf '/var/log/caisse/caisse.log {\n    daily\n    rotate 5\n    missingok\n    postrotate\n        kill -HUP "$(cat /run/journal-caisse.pid)"\n    endscript\n}\n' | sudo tee /etc/logrotate.d/caisse > /dev/null
sudo kill -HUP "$(cat /run/journal-caisse.pid)"
#@ 20.9
echo 'local0.*    /var/log/paiement.log' | sudo tee /etc/rsyslog.d/30-paiement.conf > /dev/null
# Pas de systemd dans ce conteneur : on arrête puis on relance rsyslogd (HUP ne relit pas les règles)
sudo pkill -x rsyslogd
while pgrep -x rsyslogd > /dev/null; do sleep 0.2; done
sudo rsyslogd
sleep 1
logger -p local0.info -t paiement "essai"
''',
    21: r'''
#@ 21.1
ip -4 -o addr show eth0 | awk '{print $4}' | cut -d/ -f1 > ~/mon-ip.txt
# Le réseau local apparaît dans la table de routage (adresse du réseau et longueur du préfixe)
ip route | awk '!/^default/ && / dev eth0 / {print $1; exit}' > ~/reseau.txt
#@ 21.2
ip route | awk '/^default/ {print $3}' > ~/passerelle.txt
#@ 21.3
# Le programme mystère écoute sur 0.0.0.0 ; les ports en 127.0.0.x ne sont joignables que localement
ss -tln | awk '$4 ~ /^0\.0\.0\.0:/ {split($4, a, ":"); print a[2]}' | head -1 > ~/port-mystere.txt
#@ 21.4
getent hosts serveur-local
# serveur-local figure deux fois : on retire la ligne périmée (sed -i échoue sur ce fichier monté par Docker)
grep -v '^10\.20\.30\.40' /etc/hosts > /tmp/hosts.new && sudo cp /tmp/hosts.new /etc/hosts
#@ 21.5
# Le premier serveur (192.0.2.53, plage de documentation) ne peut pas répondre
awk '/^nameserver/ && $2 != "192.0.2.53" {print $2; exit}' /etc/resolv.conf > ~/dns.txt
grep -v '192\.0\.2\.53' /etc/resolv.conf > /tmp/resolv.new && sudo cp /tmp/resolv.new /etc/resolv.conf
#@ 21.6
# ss -p ne voit pas les processus des autres comptes dans ce conteneur : ss -e donne l'uid du socket
uid=$(ss -Htlne 'sport = :8081' | grep -o 'uid:[0-9]*' | head -n1 | cut -d: -f2)
u=$(getent passwd "$uid" | cut -d: -f1)
ps -u "$u" -o pid,args
pid=$(ps -u "$u" -o pid=,args= | awk '/ 8081$/ {print $1; exit}')
echo "$(ps -o comm= -p "$pid") $u" > ~/squatteur.txt
sudo kill "$pid"
sleep 0.5
appli-caisse
#@ 21.7
# mini-web n'écoute que sur la boucle locale : on l'ouvre sur toutes les interfaces
ss -tln | grep 8088
sudo sed -i 's/^BIND=.*/BIND=0.0.0.0/' /etc/mini-web.conf
sudo mini-web-ctl restart
#@ 21.8
for h in bdd-1 bdd-2 bdd-3 bdd-4 bdd-5; do nc -z -w1 "$h" 5432 2>/dev/null && echo "$h"; done | head -n1 > ~/bdd-active.txt
#@ 21.9
# Connexion établie dont l'adresse distante se termine par :4444
sudo ss -tnp
pid=$(sudo ss -Htnp | awk '$5 ~ /:4444$/' | grep -o 'pid=[0-9]*' | head -n1 | cut -d= -f2)
echo "$pid $(ps -o comm= -p "$pid")" > ~/connexion.txt
sudo kill "$pid"
''',
    22: r'''
#@ 22.1
mkdir -p -m 700 ~/.ssh
ssh-keygen -q -t ed25519 -N '' -f ~/.ssh/id_ed25519
#@ 22.2
# En classe : ssh-copy-id deploy@localhost (mot de passe deploy123)
sshpass -p deploy123 ssh-copy-id -o StrictHostKeyChecking=accept-new deploy@localhost 2>/dev/null
#@ 22.3
printf 'Host prod\n    HostName localhost\n    User deploy\n    Port 2222\n' > ~/.ssh/config
ssh -o StrictHostKeyChecking=accept-new prod true
#@ 22.4
scp -q ~/a-envoyer/livrable.txt prod:
#@ 22.6
# Options devant la clé dans authorized_keys : cette clé ne peut lancer que deploy-only
ssh-keygen -q -t ed25519 -N '' -C integration-continue -f ~/.ssh/ci_key
echo "command=\"/usr/local/bin/deploy-only\",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding $(cat ~/.ssh/ci_key.pub)" | ssh deploy@localhost 'cat >> ~/.ssh/authorized_keys'
ssh -i ~/.ssh/ci_key -o IdentitiesOnly=yes deploy@localhost whoami
#@ 22.7
# « UNPROTECTED PRIVATE KEY FILE » : le client refuse une clé privée lisible par d'autres
chmod 600 ~/cles/sauvegarde_key
ssh -i ~/cles/sauvegarde_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new sauvegarde@localhost true
#@ 22.5
sudo sed -i -E 's/^#?PasswordAuthentication .*/PasswordAuthentication no/; s/^#?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sshd -t
sudo service ssh reload
sleep 1
#@ 22.8
# Liste noire : les comptes créés plus tard ne sont pas concernés (AllowUsers les exclurait)
echo 'DenyUsers intrus toor' | sudo tee -a /etc/ssh/sshd_config > /dev/null
sudo sshd -t
sudo service ssh reload
sleep 1
''',
    23: r'''
#@ 23.1
sudo find / -perm -4000 -type f 2>/dev/null > ~/suid-files.txt
# Un binaire légitime appartient à un paquet ; dpkg connaît parfois l'ancien chemin (/bin/… plutôt que /usr/bin/…)
: > ~/suid-suspects.txt
for f in $(cat ~/suid-files.txt); do
    dpkg -S "$f" > /dev/null 2>&1 || dpkg -S "${f#/usr}" > /dev/null 2>&1 || echo "$f" >> ~/suid-suspects.txt
done
cat ~/suid-suspects.txt
#@ 23.2
/usr/local/bin/lecteur-root /etc/shadow | head -n 2
sudo chmod u-s $(cat ~/suid-suspects.txt)
#@ 23.3
f=$(sudo find /etc -type f -perm -o+w)
sudo chown root:root "$f"
sudo chmod 600 "$f"
# Le mot de passe a pu être lu par n'importe qui : on le remplace
sudo sed -i "s/^db_password=.*/db_password=$(head -c 12 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')/" "$f"
#@ 23.4
awk -F: '$3 == 0 {print $1}' /etc/passwd > ~/uid-zero.txt
# userdel refuse (des processus tournent en UID 0) : on neutralise le compte
sudo passwd -l toor
sudo usermod -s /usr/sbin/nologin toor
#@ 23.5
sudo chage -M 90 securise
# passwd -l ne bloque que le mot de passe : la clé SSH fonctionnerait encore. On fait expirer le compte.
sudo chage -E 0 securise
#@ 23.6
# Le bit sticky : dans un dossier ouvert à tous, chacun ne supprime que ses fichiers
sudo chmod +t /srv/depot
#@ 23.7
grep -rn umask /etc/profile /etc/profile.d /etc/bash.bashrc
sudo sed -i '/^umask 000/d' /etc/profile.d/zz-confort.sh
#@ 23.8
# Pour chaque script lancé en root : le fichier et chacun de ses dossiers doivent appartenir à root, sans écriture pour le groupe ni les autres
: > ~/cron-risque.txt
for p in $(grep -hvE '^\s*(#|$)' /etc/cron.d/* | awk '$6 == "root" && $7 ~ /^\// {print $7}' | sort -u); do
    namei -l "$p"
    d=$p; risque=0
    while [ "$d" != / ]; do
        [ -n "$(find "$d" -maxdepth 0 \( ! -user root -o -perm /022 \))" ] && risque=1
        d=$(dirname "$d")
    done
    [ $risque = 1 ] && echo "$p" >> ~/cron-risque.txt
done
cat ~/cron-risque.txt
sudo chmod 755 /opt/scripts/purge-cache.sh
sudo chmod g-w /srv/outils
#@ 23.9
# C'est la clé elle-même qu'on cherche, pas son commentaire
cle=$(sudo awk '/marc@portable/ {print $2}' /root/.ssh/authorized_keys)
for f in $(sudo find / -xdev -name authorized_keys 2>/dev/null); do
    sudo grep -q "$cle" "$f" && sudo sed -i "\#$cle#d" "$f"
done
ssh deploy@localhost true
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
# On vide le fichier sans le supprimer : l'application le garde ouvert
sudo truncate -s 0 "$big"
#@ 24.3
# StrictModes : ni le dossier personnel, ni .ssh, ni authorized_keys ne doivent être modifiables par d'autres
sudo tail -n 5 /var/log/auth.log
sudo chmod 755 /home/ops
sudo chown -R ops:ops /home/ops/.ssh
sudo chmod 700 /home/ops/.ssh
sudo chmod 600 /home/ops/.ssh/authorized_keys
#@ 24.4
# Quatre erreurs : nom de fichier avec un point (ignoré), champ utilisateur absent, chemin relatif (PATH de cron), script non exécutable
sudo rm /etc/cron.d/rapport.cron
echo '* * * * * root /usr/local/bin/rapport-cron.sh' | sudo tee /etc/cron.d/rapport > /dev/null
sudo chmod +x /usr/local/bin/rapport-cron.sh
#@ 24.5
sudo -u monsvc mon-service --check
sudo sed -i 's/^PORT=.*/PORT=8080/' /etc/mon-service.conf
sudo mkdir -p /var/log/mon-service
sudo chown monsvc: /var/log/mon-service
sudo -u monsvc mon-service --check
#@ 24.6
# Il faut pouvoir traverser /srv/app (x) sans pouvoir le lister (r)
namei -l /srv/app/public/index.html
sudo chmod 711 /srv/app
#@ 24.7
# Un fichier inclus en tête de sshd_config réactive les mots de passe : la première valeur lue l'emporte
sudo sshd -T | grep -i passwordauthentication
grep -n Include /etc/ssh/sshd_config
grep -ri passwordauthentication /etc/ssh/sshd_config.d/
sudo rm /etc/ssh/sshd_config.d/50-cloud-init.conf
sudo sshd -t
sudo service ssh reload
sleep 1
#@ 24.8
sudo tee /usr/local/bin/archiver-factures > /dev/null <<'EOF'
#!/bin/bash
# Archive les factures : copie chaque facture de SOURCE dans DEST, puis affiche le nombre copié
# Usage : archiver-factures [SOURCE] [DEST]   (par défaut /srv/factures et /srv/archives-factures)
SRC=${1:-/srv/factures}
DEST=${2:-/srv/archives-factures}
mkdir -p "$DEST"
n=0
for f in "$SRC"/*; do
    [ -f "$f" ] || continue
    cp -- "$f" "$DEST/" && n=$((n + 1))
done
echo "$n facture(s) archivée(s)"
EOF
sudo archiver-factures
#@ 24.9
# On vérifie l'empreinte de la nouvelle clé, puis on oublie l'ancienne (sans désactiver la vérification)
ssh-keygen -lf /etc/ssh/prod/ssh_host_ed25519_key.pub | awk '{print $2}' > ~/empreinte.txt
ssh-keygen -R '[localhost]:2222'
ssh -p 2222 -o StrictHostKeyChecking=accept-new deploy@localhost true
#@ 24.4
# Attendre que cron exécute deux fois la tâche réparée
for i in $(seq 100); do [ "$(grep -c 'rapport généré' /var/log/rapport-cron.log 2>/dev/null)" -ge 2 ] && break; sleep 2; done
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
if [ $# -eq 0 ]; then
    echo "Usage : $0 SEUIL" >&2
    exit 1
fi
u=$(df -P / | awk 'NR==2{print $5}' | tr -d %)
if [ "$u" -gt "$1" ]; then m="ALERTE disque : ${u}% (seuil $1%)"; else m="OK disque : ${u}%"; fi
echo "$m"
echo "$(date '+%F %T') $m" >> /var/www/monsite/logs/monitoring.txt
EOF
sudo chown webmaster: /home/webmaster/monitoring.sh
sudo chmod 755 /home/webmaster/monitoring.sh
#@ 25.7
# webmaster n'a pas de mot de passe : on installe la clé soi-même
sudo install -d -m 700 -o webmaster -g webmaster /home/webmaster/.ssh
sudo tee -a /home/webmaster/.ssh/authorized_keys < ~/.ssh/id_ed25519.pub > /dev/null
sudo chown webmaster: /home/webmaster/.ssh/authorized_keys
sudo chmod 600 /home/webmaster/.ssh/authorized_keys
#@ 25.8
sudo tee /home/webmaster/serveur.sh > /dev/null <<'EOF'
#!/bin/bash
# Mini serveur HTTP : une réponse par connexion, une ligne de journal par requête
W=/var/www/monsite
while true; do
    { printf 'HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n'; cat "$W/html/index.html"; } | nc -N -l 127.0.0.1 8000 > /dev/null
    echo "$(date '+%F %T') GET /" >> "$W/logs/access.log"
done
EOF
sudo chown webmaster: /home/webmaster/serveur.sh
sudo chmod 755 /home/webmaster/serveur.sh
sudo -u webmaster setsid /home/webmaster/serveur.sh > /dev/null 2>&1 < /dev/null &
sleep 1
curl -s http://127.0.0.1:8000/
#@ 25.9
# Plus aucun accès pour les autres au dossier des sauvegardes, et des archives créées sans droits pour les autres
sudo chmod o-rwx /var/www/monsite/backup
sudo sed -i '2i umask 027' /home/webmaster/backup.sh
''',
}
