"""Corrigé du parcours Linux : un script par étape, exécuté en tant qu'« etudiant » par le banc de test
(avec sudo sans mot de passe dans le conteneur de test).

Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Un même repère peut réapparaître plus loin : le bloc suivant est ajouté à la correction de l'exercice.
Les solutions résolvent les énigmes comme un étudiant, sans lire les réponses attendues.
"""

SOLUTIONS = {
    1: r'''
#@ 1.1
#? L'idée est de parcourir toute l'arborescence de Marc : `ls -R` montre d'un coup le contenu de chaque sous-dossier, et `grep` permet ensuite de trier les notes sans les ouvrir une à une.
#? Le piège, c'est de prendre la première note trouvée ou celle de l'année la plus récente : quatre notes sont marquées PÉRIMÉ, et la seule à jour peut être rangée dans n'importe quelle année.
#? `grep -rL 'PÉRIMÉ'` liste les fichiers qui ne contiennent pas ce mot ; parmi eux, on garde celui qui a une ligne `CODE=`.
#? Écrire la ligne complète `CODE=…` est aussi accepté, mais le plus propre est de n'extraire que la valeur avec `cut -d= -f2`.
#? Les emplacements des notes et le code sont tirés au sort à la mise en place : ceux de votre environnement diffèrent de ceux du corrigé.
# On explore l'arborescence ; seule une note n'est pas marquée PÉRIMÉ et contient un code
cd /opt/archives-marc
ls -R
f=$(grep -rL 'PÉRIMÉ' --include=note.txt . | xargs grep -l '^CODE=')
cat "$f"
grep '^CODE=' "$f" | cut -d= -f2 > ~/code-baie.txt
cd ~
#@ 1.2
#? Un fichier dont le nom commence par un point est caché : `ls` ne l'affiche pas, il faut `ls -a` pour le voir.
#? Le piège : il y a deux fichiers cachés, et `.jeton-vpn.ancien` contient un jeton révoqué qui ne doit surtout pas être recopié.
#? Une simple copie avec `cp ~/passation/.jeton-vpn ~/jeton-vpn.txt` convient tout autant que la redirection du corrigé.
#? Les jetons sont tirés au sort à la mise en place : les vôtres ne sont pas ceux affichés ici.
ls -a ~/passation
cat ~/passation/.jeton-vpn.ancien
cat ~/passation/.jeton-vpn > ~/jeton-vpn.txt
#@ 1.3
#? `mkdir` crée des dossiers et accepte plusieurs noms à la suite, d'où une seule commande pour les deux.
#? Le piège était d'utiliser `sudo` : les dossiers appartiendraient alors à root et vous ne pourriez plus y écrire librement ; dans votre dossier personnel, vous avez déjà tous les droits.
#? `ls -l ~` permet de vérifier que le propriétaire affiché est bien etudiant.
mkdir ~/documents ~/projets
#@ 1.4
#? `touch` crée un fichier vide s'il n'existe pas, sans ouvrir d'éditeur.
#? Attention à `echo "" > fichier` : il écrit un retour à la ligne, donc le fichier n'est plus vide et la vérification échoue.
#? Une redirection seule, `> ~/documents/journal.txt`, crée elle aussi un fichier vide et reste acceptée.
#? Comme pour les dossiers, il faut le créer sans `sudo` pour qu'il vous appartienne.
touch ~/documents/journal.txt
#@ 1.5
#? Le shell découpe la ligne aux espaces : entre guillemets, `"notes de réunion.txt"` redevient un seul argument.
#? Un argument qui commence par un tiret est pris pour une option ; `./-urgent.txt` le désigne par un chemin qui ne commence plus par `-`, et `cat -- -urgent.txt` fonctionne aussi, puisque `--` marque la fin des options.
#? Le premier `>` crée le fichier et le second doit être `>>` : sinon la deuxième valeur écraserait la première, alors que l'ordre des deux lignes est vérifié.
#? Les deux mots sont tirés au sort à la mise en place : ils diffèrent de ceux de votre environnement.
# Guillemets pour l'espace, ./ (ou --) pour le tiret
cd ~/passation/boite
cat "notes de réunion.txt" | grep '^MOT=' | cut -d= -f2 > ~/mots.txt
cat ./-urgent.txt | grep '^MOT=' | cut -d= -f2 >> ~/mots.txt
cd ~
#@ 1.6
#? Sous Linux, l'extension n'est qu'une convention : `file` examine le contenu d'un fichier pour en deviner le type.
#? Le piège était d'afficher chaque pièce avec `cat` : sur un binaire ou un fichier compressé, cela remplit le terminal de caractères illisibles.
#? Donner tous les fichiers d'un coup avec `file ~/passation/pieces/*` suffit, puis on repère la ligne qui mentionne un script.
#? Seul le nom compte pour la vérification, mais le chemin complet serait aussi accepté.
#? Les noms des pièces sont tirés au sort à la mise en place : le vôtre n'est pas forcément celui du corrigé.
file ~/passation/pieces/*
file ~/passation/pieces/* | grep -i script | cut -d: -f1 | xargs basename > ~/script-trouve.txt
#@ 1.7
#? Se placer dans `~/projets/vitrine` raccourcit les chemins : `mkdir` et `touch` acceptent plusieurs noms, y compris des chemins comme `css/style.css`.
#? La vérification compare le contenu exact du dossier : un fichier en trop, par exemple un `style.css` créé à la racine du projet, suffit à la faire échouer.
#? Une variante compacte, `mkdir -p ~/projets/vitrine/{css,js,img}`, crée tous les dossiers en une seule commande grâce aux accolades.
#? Tout doit être créé sans `sudo`, pour que chaque élément vous appartienne.
mkdir ~/projets/vitrine
cd ~/projets/vitrine
mkdir css js img
touch index.html css/style.css
cd ~
''',
    2: r'''
#@ 2.1
#? L'option `-p` (ou `--parents`) de `mkdir` crée tous les dossiers intermédiaires manquants et ne proteste pas s'ils existent déjà.
#? Le piège : sans `-p`, la commande notée dans la documentation échouerait sur un poste où `boutique` n'existe pas encore.
#? Le chemin doit être absolu et écrit en toutes lettres, sans `~`, pour fonctionner depuis n'importe quel dossier.
#? Le chemin peut être écrit entre guillemets dans la commande notée (`mkdir -p "/home/etudiant/projets/boutique/src"`) : c'est accepté aussi.
#? Les guillemets simples autour de la commande dans `echo` empêchent le shell de l'interpréter : on l'écrit dans le fichier, puis on l'exécute une fois pour de bon.
mkdir -p /home/etudiant/projets/boutique/src
echo 'mkdir -p /home/etudiant/projets/boutique/src' > ~/doc-install.txt
#@ 2.2
#? La question est tirée au sort parmi plusieurs (tri par taille, par extension, par version, ou pas de tri du tout) : la réponse d'un camarade n'est donc pas forcément la vôtre.
#? La démarche est toujours la même : `man ls`, puis `/` suivi du mot anglais de la question (size, extension, version, sort…) et `n` pour passer à l'occurrence suivante.
#? Les réponses possibles : `-S` (taille, du plus gros au plus petit), `-X` (extension), `-v` (version), `-U` (pas de tri) ; l'écriture longue `--sort=…` est aussi acceptée, tout comme `ls -S` écrit en entier.
#? Attention à la casse : `-s` affiche la taille sans trier, alors que `-S` trie par taille.
cat ~/question-man.txt
case $(cat ~/question-man.txt) in
  *taille*) mot='sort by file size'; opt=-S ;;
  *extension*) mot='by entry extension'; opt=-X ;;
  *version*) mot='(version)'; opt=-v ;;
  *) mot='do not sort'; opt=-U ;;
esac
man ls 2>/dev/null | grep -F -- "$mot"
echo "$opt" > ~/reponse-man.txt
#@ 2.3
#? Marc n'a pas rangé `tarifs.txt` au même endroit chez tout le monde : il faut d'abord le trouver (`ls -R ~/partage-marc` ou `find ~/partage-marc -name tarifs.txt`).
#? Ensuite, `..` remonte d'un niveau : depuis `devis`, on remonte jusqu'au dossier commun, puis on redescend vers le fichier (par exemple `../../tarifs.txt` s'il est dans `clients`, `../../2023/tarifs.txt` s'il est dans `clients/2023`).
#? Le piège : un chemin qui commence par `/` ou par `~` est absolu, et c'est justement ce que Julien voulait éviter.
#? `realpath --relative-to=DOSSIER FICHIER` calcule ce chemin pour vous ; testez toujours le résultat avec `cat` depuis le dossier `devis`.
t=$(find ~/partage-marc -name tarifs.txt)
realpath --relative-to="$HOME/partage-marc/clients/2024/devis" "$t" > ~/chemin-relatif.txt
cd ~/partage-marc/clients/2024/devis && cat "$(cat ~/chemin-relatif.txt)"
cd ~
#@ 2.4
#? Le chemin du script est tiré au sort à la mise en place : lisez-le dans `~/partage-marc/vieux-script.sh`.
#? On le lit de gauche à droite : chaque `..` annule le dossier précédent et `.` ne change rien, donc `clients/2024/../..` ramène à `partage-marc`.
#? Le plus sûr est de laisser le shell calculer : `cd` dans ce chemin, puis `pwd` affiche le chemin absolu réel.
#? La réponse doit commencer par `/home/etudiant` et non par `~`, sinon ce n'est pas un chemin absolu ; une barre oblique finale est tolérée.
cat ~/partage-marc/vieux-script.sh
c=$(grep -oE '^cd [^ ]+' ~/partage-marc/vieux-script.sh | cut -d' ' -f2)
cd "${c/#\~/$HOME}" && pwd > ~/chemin-absolu.txt
cd ~
#@ 2.5
#? La commande de la question est tirée au sort (cd, type, export ou jobs) ; toutes sont des commandes internes (builtins) du shell et non des programmes installés sur le disque : c'est pourquoi `man` ne trouve rien.
#? `type nom` répond « nom is a shell builtin », et `help nom` affiche la documentation des commandes internes (`man bash` la décrit aussi).
#? `command -V nom` donne la même réponse, et `type -t nom` répond simplement « builtin » : ces réponses sont acceptées aussi.
#? Les réponses : `cd -P` suit la structure physique des dossiers, `type -a` affiche toutes les définitions d'un nom, `export -n` retire l'export d'une variable, `jobs -l` ajoute le PID des tâches.
#? Le piège était de conclure que la commande n'avait pas de documentation. Autre piège pour écrire la réponse : `echo -n > fichier` prend `-n` pour une option d'echo et n'écrit rien ; `printf '%s\n' -n > fichier` convient.
cat ~/question-shell.txt
c=$(grep -oE 'man [a-z]+' ~/question-shell.txt | head -n1 | cut -d' ' -f2)
type "$c" > ~/type-commande.txt
case $c in cd) o=-P ;; type) o=-a ;; export) o=-n ;; jobs) o=-l ;; esac
help "$c" | grep -- "$o"
# printf plutôt que echo : « echo -n » prendrait -n pour une option d'echo
printf '%s\n' "$o" > ~/option-commande.txt
#@ 2.6
#? `ls -t` trie par date de dernière modification, la plus récente en premier ; `head -n1` ne garde que la première ligne.
#? Le piège était de se fier aux noms : « DEFINITIF », « final-v2 » ou une date dans le nom ne disent rien de la date réelle de modification.
#? `ls -lt` permet de contrôler visuellement les dates avant d'écrire la réponse.
#? Les dates des rapports sont tirées au sort à la mise en place : le plus récent chez vous n'est pas forcément celui du corrigé.
ls -lt /opt/rapports-marc
ls -t /opt/rapports-marc | head -n1 > ~/dernier-rapport.txt
#@ 2.7
#? Un fichier de 8 000 lignes se lit avec `less`, qui a les mêmes touches que `man` : `/=== CLÔTURE` puis Entrée saute directement à la bonne ligne.
#? Le piège : les lignes `--- CLÔTURE partielle ---` sont suivies d'autres numéros de lot, qui ne sont pas la réponse.
#? Le corrigé fait la même chose sans interaction : `grep -A1` affiche la ligne trouvée et celle qui la suit, puis on isole le nombre.
#? Le numéro du lot et la position de la clôture sont tirés au sort à la mise en place.
# Avec less : /=== CLÔTURE puis Entrée ; équivalent non interactif :
grep -A1 '^=== CLÔTURE ===$' ~/exports/journal-export.log | tail -n1 | grep -oE '[0-9]+' > ~/lot.txt
#@ 2.8
#? Pour aller d'une branche à une autre, on remonte jusqu'au dossier commun, ici `partage-marc`, puis on redescend vers la cible.
#? Depuis `devis`, il faut trois `..` pour atteindre `partage-marc`, puis `fournisseurs/…` jusqu'au catalogue.
#? Le piège est de compter une remontée de trop ou de moins : testez toujours le chemin avec `cat` depuis le dossier `devis`.
#? Le catalogue indiqué dans `A-LIRE.txt` est tiré au sort à la mise en place : votre chemin diffère sans doute de celui du corrigé.
cat ~/partage-marc/clients/2024/devis/A-LIRE.txt
c=$(grep -o 'fournisseurs/[^ ]*' ~/partage-marc/clients/2024/devis/A-LIRE.txt)
echo "../../../$c" > ~/chemin-fournisseur.txt
cd ~/partage-marc/clients/2024/devis && cat "../../../$c"
cd ~
''',
    3: r'''
#@ 3.1
#? `mkdir -p` crée les dossiers parents manquants, et les accolades `{procedures,comptes-rendus}` sont développées par le shell en deux chemins distincts.
#? Sans `-p`, `mkdir` refuse de créer `archives` tant que son dossier parent n'existe pas.
#? Deux commandes séparées, ou `mkdir -p` suivi des deux chemins complets, donnent exactement le même résultat.
#? Comme toujours dans votre dossier personnel, pas de `sudo` : les dossiers doivent vous appartenir.
mkdir -p ~/documents/{procedures,comptes-rendus}/archives
#@ 3.2
#? Le symbole `>` envoie la sortie d'`echo` dans le fichier, en le créant s'il n'existe pas.
#? Les guillemets gardent la phrase en un seul argument, et le texte doit être recopié exactement, accents compris.
#? Vérifiez le résultat avec `cat` : la moindre faute de frappe dans le titre fait échouer la vérification.
echo "Procédure arrivée nouveau salarié" > ~/documents/procedures/arrivee.txt
#@ 3.3
#? `>>` ajoute à la fin du fichier, alors que `>` en remplace tout le contenu : c'est la différence qui protège le titre.
#? Le piège classique : utiliser `>` et effacer le titre, ou lancer deux fois la commande `>>` et obtenir trois lignes au lieu de deux.
#? En cas d'erreur, réécrivez le titre avec `>`, puis ajoutez l'étape avec `>>`.
#? Une ligne vide ajoutée à la fin par un éditeur, ou l'absence de retour à la ligne final (avec `printf`), ne comptent pas comme une ligne de plus.
echo "1. Créer le compte utilisateur" >> ~/documents/procedures/arrivee.txt
#@ 3.4
#? `cp` accepte comme destination un chemin qui se termine par un nouveau nom : la copie est créée directement sous ce nom.
#? Le piège était d'utiliser `mv`, qui déplace le fichier au lieu de le dupliquer : l'original disparaîtrait.
#? La copie doit être faite après l'ajout de la deuxième ligne, sinon elle diffère de l'original.
cp ~/documents/procedures/arrivee.txt ~/documents/comptes-rendus/arrivee-a-relire.txt
#@ 3.5
#? Tester le motif avec `ls ~/bureau-marc/*.tmp` avant `rm` montre exactement ce qui sera supprimé.
#? `rm` seul refuse de supprimer un dossier : `rm -r` supprime `vieux-projets` et tout son contenu.
#? Le piège serait un `rm -r ~/bureau-marc/*` trop large : le contrat, seul exemplaire, disparaîtrait, et il n'y a pas de corbeille.
#? La vérification contrôle l'inode du contrat : même recréé à l'identique, ce ne serait plus le fichier d'origine.
ls ~/bureau-marc/*.tmp
rm ~/bureau-marc/*.tmp
rm -r ~/bureau-marc/vieux-projets
#@ 3.6
#? `mv` écrase la destination sans prévenir : il faut d'abord mettre l'ancien `bilan.txt` de côté, puis renommer le brouillon.
#? Dans l'ordre inverse, le brouillon renommé écraserait la version de Marc, perdue pour de bon.
#? L'option `-n` refuse d'écraser un fichier existant : c'est un filet de sécurité très utile quand l'ordre des opérations compte.
cd ~/bilans
mv -n bilan.txt bilan-ancien.txt
mv -n brouillon-bilan.txt bilan.txt
cd ~
#@ 3.7
#? Le joker `facture-2024-*` ne retient que les noms qui commencent exactement par ce préfixe.
#? Le piège était de placer une étoile devant, comme `*facture-2024*` : le motif attraperait aussi les relances `relance-facture-2024-…`.
#? Tester d'abord le motif avec `ls` montre la liste exacte des fichiers qui seront déplacés.
#? Les numéros des factures sont tirés au sort à la mise en place : vos noms de fichiers diffèrent de ceux du corrigé.
ls ~/factures/inbox/facture-2024-*
mv ~/factures/inbox/facture-2024-* ~/factures/2024/
#@ 3.8
#? Le crochet `[1-9]` désigne un seul caractère parmi les chiffres de 1 à 9 : `rapport[1-9].txt` ne prend que `rapport1.txt` à `rapport9.txt`.
#? `rapport*.txt` supprimerait tout, y compris la synthèse ; `rapport?.txt` attraperait aussi `rapportA.txt`, car `?` accepte n'importe quel caractère.
#? `rapport10.txt` et les suivants ne correspondent pas, puisque le motif n'autorise qu'un seul caractère entre `rapport` et `.txt`.
#? Le nombre de rapports est tiré au sort à la mise en place, mais le motif fonctionne quel que soit ce nombre.
# rapport?.txt attraperait aussi rapportA.txt ; [1-9] ne prend que les chiffres
ls ~/rapports-hebdo/rapport[1-9].txt
rm ~/rapports-hebdo/rapport[1-9].txt
#@ 3.9
#? Le joker `*` ne correspond jamais à un nom qui commence par un point : les `.tmp` cachés avaient échappé au ménage de l'exercice 3.5.
#? Un motif qui commence lui-même par un point, `.*.tmp`, attrape les noms cachés ; `ls -a` permet de les voir avant de supprimer.
#? Le piège est d'être trop large : `notes.tmp.txt` ne se termine pas par `.tmp` et `.parametres` n'est pas un fichier temporaire, les deux doivent rester.
#? `find ~/bureau-marc -maxdepth 1 -name '*.tmp' -delete` est une variante valable, car le `-name` de `find` ne fait pas d'exception pour les noms cachés.
#? Le numéro dans le nom du fichier `.verrou-….tmp` est tiré au sort à la mise en place.
# * ignore les noms cachés : il faut un motif qui commence par un point
ls -a ~/bureau-marc
ls ~/bureau-marc/.*.tmp
rm ~/bureau-marc/.*.tmp
''',
    4: r'''
#@ 4.1
#? `ln` sans option crée un lien dur : un second nom pour le même inode, sans aucune copie des données.
#? Le piège était d'utiliser `cp`, qui crée un fichier indépendant (celui qui diverge), ou `ln -s`, qui crée un raccourci et non un second nom.
#? `ln` prend d'abord le fichier existant, puis le nouveau nom ; `ls -li` confirme que les deux noms ont le même numéro d'inode.
#? Le fichier officiel ne doit pas être modifié : la vérification contrôle son contenu.
ln ~/tarifs-2025.csv ~/tarifs-courant.csv
ls -li ~/tarifs-2025.csv ~/tarifs-courant.csv
#@ 4.2
#? Un lien dur partage l'inode de l'original, alors qu'une copie en a un autre, même si elle porte un nom semblable.
#? `find -samefile` retrouve tous les noms d'un même inode, l'original compris, avec des chemins complets puisque la recherche part de `/opt/sauvegardes`.
#? Le piège était de se fier aux noms `export-*.db` : certains sont des copies, qui ne comptent pas.
#? `find /opt/sauvegardes -inum` suivi du numéro affiché par `ls -i` donne la même liste.
#? Le nombre de liens, les copies et leurs emplacements sont tirés au sort à la mise en place.
# Les copies (export-*.db compris) ont un autre inode : seul -samefile fait le tri
find /opt/sauvegardes -samefile /opt/sauvegardes/base-clients.db > ~/liens-base.txt
#@ 4.3
#? Seul un lien symbolique peut désigner un dossier : un lien dur vers `/etc` est impossible.
#? Avec `ln -s`, on donne d'abord la cible, puis le nom du lien : inverser les deux est l'erreur la plus fréquente.
#? `ls -l ~/conf-systeme` affiche la flèche vers `/etc`, ce qui permet de vérifier le résultat.
ln -s /etc ~/conf-systeme
#@ 4.4
#? `ls -l` affiche la cible de chaque lien, et `find -xtype l` ne liste que les liens symboliques dont la cible n'existe pas.
#? Le lien cassé pointe vers `/mnt/ancien-nas`, qui n'existe plus ; les autres pointent vers des fichiers présents dans le dossier.
#? La réponse doit tenir sur une seule ligne, avec le seul nom du lien ; `-printf '%f\n'` retire le chemin du dossier.
#? Le lien cassé est tiré au sort à la mise en place : chez vous, ce n'est pas forcément le même service.
b=$(find ~/raccourcis-marc -xtype l -printf '%f\n')
echo "$b" > ~/lien-casse.txt
#@ 4.5
#? `ln -s` refuse de créer un lien dont le nom existe déjà ; l'option `-f` remplace l'ancien lien.
#? Une cible relative comme `annuaire.txt` est interprétée depuis le dossier du lien, pas depuis le dossier où l'on tape la commande.
#? Le piège : lancée depuis `~` avec le seul nom du lien, la commande créerait un nouveau lien dans `~` au lieu de réparer celui de `~/raccourcis-marc`.
#? Une cible absolue vers `/home/etudiant/raccourcis-marc/annuaire.txt` serait aussi acceptée ; ici `-n` n'est pas indispensable, car l'ancienne cible n'était pas un dossier.
#? Le nom du lien à réparer vient de l'exercice précédent, tiré au sort à la mise en place.
b=$(cat ~/lien-casse.txt)
ln -sfn annuaire.txt ~/raccourcis-marc/"$b"
#@ 4.6
#? Un lien symbolique ne contient qu'un texte : s'il commence par `/`, il désignera toujours `~/site-v1/…`, même après le déménagement.
#? Un chemin relatif comme `releases/rN`, interprété depuis le dossier du lien, suit le dossier partout où il est déplacé.
#? Le lien actuel désigne un dossier : `-n` est nécessaire avec `-sf`, sinon `ln` crée le nouveau lien à l'intérieur de la release.
#? `readlink ~/site-v1/current` montre la release en production ; elle est tirée au sort à la mise en place, gardez la vôtre.
# Le lien contient un chemin absolu : on le remplace par un chemin relatif au dossier du lien
r=$(basename "$(readlink ~/site-v1/current)")
cd ~/site-v1 && ln -sfn releases/$r current
cd ~
#@ 4.7
#? Sans `-n`, quand la destination est un lien vers un dossier, `ln` le suit et crée le nouveau lien dans ce dossier : c'est ainsi que le lien parasite est apparu dans l'ancienne release.
#? `ln -sfn` traite `current` comme un simple fichier et le remplace directement.
#? Les deux releases sont tirées au sort à la mise en place : lisez la cible dans `A-DEPLOYER`, et trouvez le parasite avec `find releases -type l` plutôt que de recopier le chemin d'un camarade.
#? Le lien parasite se supprime avec `rm` sans `-r` : c'est un lien, et `rm -r` sur un lien vers un dossier ne supprime de toute façon que le lien.
# Sans -n, ln traite current (lien vers un dossier) comme ce dossier et crée le nouveau lien à l'intérieur
cd ~/deploi
r=$(grep -oE 'r[0-9]+' A-DEPLOYER)
ln -sfn "releases/$r" current
p=$(find releases -type l)
echo "$p"
rm $p
cd ~
#@ 4.8
#? Tant qu'un nom pointe vers un inode, les données existent : il suffit de retrouver ce nom de secours et d'en créer un nouveau.
#? `find ~ -inum` cherche par numéro d'inode, y compris dans les dossiers cachés comme `~/.cache`.
#? Le piège est la copie `grille.csv.bak`, au nom plus parlant : elle a un autre inode, et la recopier ne rendrait pas le fichier d'origine.
#? Il faut un lien dur (`ln` sans `-s`) : un lien symbolique n'aurait pas le bon inode.
#? Le numéro d'inode et les noms des dossiers de secours sont tirés au sort à la mise en place.
n=$(grep -oE '[0-9]+' ~/grilles/LISEZ-MOI | head -n1)
f=$(find ~ -inum "$n" 2>/dev/null | head -n1)
ln "$f" ~/grilles/grille.csv
#@ 4.9
#? `readlink` sans option n'affiche que la cible immédiate, qui peut elle-même être un lien, parfois caché comme `.relais/niveau3`.
#? `readlink -f` suit toute la chaîne jusqu'au vrai fichier et affiche son chemin absolu ; `realpath` fait de même.
#? Le piège était de s'arrêter au premier maillon, qui n'est qu'un autre raccourci.
#? Le fichier au bout de la chaîne est tiré au sort à la mise en place : votre chemin diffère sans doute du corrigé.
readlink ~/raccourcis/dernier
readlink -f ~/raccourcis/dernier > ~/fichier-final.txt
''',
    5: r'''
#@ 5.1
#? Les critères de `find` s'additionnent : `-type f` ne garde que les fichiers ordinaires, `-name "*.conf"` filtre le nom.
#? Le piège était le dossier `anciens.conf`, qui porte un nom en `.conf` sans être un fichier ; `-type f` écarte aussi les liens symboliques.
#? Les erreurs « Permission denied » partent vers `/dev/null` grâce à `2>/dev/null`, pour ne garder que la liste.
#? Lancez la commande sans `sudo` : la liste attendue est celle des fichiers visibles par etudiant, et root en verrait davantage.
#? Le nombre de modules de /etc/cimes-sentiers est tiré au sort à la mise en place : votre liste est propre à votre serveur.
find /etc -type f -name "*.conf" 2>/dev/null > ~/audit-conf.txt
#@ 5.2
#? `grep -r` cherche dans tout un dossier et ses sous-dossiers, et `-l` n'affiche que le nom des fichiers trouvés, avec leur chemin complet.
#? Le piège : sans `-l`, on obtient la ligne du bon et non le chemin demandé.
#? Le chemin doit commencer par `/srv`, ce que donne naturellement une recherche lancée sur `/srv/archives`.
#? L'emplacement du fichier et le code du bon sont tirés au sort à la mise en place.
grep -rl "BON-" /srv/archives > ~/bon-reduction.txt
#@ 5.3
#? `-path` filtre sur le chemin complet et non sur le seul nom : `'*/2023/*'` retient ce qui est rangé dans un dossier 2023.
#? Le piège : `-name '*2023*.log'` compterait les `bilan-2023.log` rangés dans les dossiers 2024.
#? `wc -l` compte ensuite les lignes, donc les fichiers trouvés.
#? Une variante valable est `find /srv/archives/*/2023 -name '*.log' | wc -l`, où c'est le joker du shell qui sélectionne les dossiers 2023.
#? La répartition des fichiers est tirée au sort à la mise en place : votre nombre diffère sans doute de celui du corrigé.
find /srv/archives -path '*/2023/*' -name "*.log" | wc -l > ~/nb-logs.txt
#@ 5.4
#? `-size +5M` retient les fichiers de plus de 5 Mio ; le signe `+` signifie « plus de » et `-` « moins de ».
#? Sans le `+`, `find` chercherait des fichiers d'exactement 5 Mio une fois arrondis, et ne trouverait rien.
#? Le nom et l'emplacement du gros fichier sont tirés au sort à la mise en place.
find /srv/archives -size +5M > ~/gros-fichier.txt
#@ 5.5
#? `-i` ignore la casse et `-c` compte les lignes correspondantes ; les deux se combinent en `-ci`.
#? Le piège était d'oublier `-i` : on ne compterait alors que les lignes écrites en minuscules.
#? `grep -i erreur fichier | wc -l` donne le même résultat, mais `-c` est plus direct.
#? Le contenu du rapport est tiré au sort à la mise en place : votre nombre diffère de celui du corrigé.
grep -ci erreur /srv/archives/rapport.txt > ~/nb-erreurs.txt
#@ 5.6
#? `-newer fichier` retient ce qui a été modifié plus récemment que le fichier repère : c'est une comparaison de dates sans calcul.
#? `-type f` écarte les dossiers, dont la date change aussi quand on y crée ou modifie un fichier.
#? `ls -l` sur quelques résultats permet de vérifier que leurs dates sont bien postérieures à celle de `.derniere-sauvegarde`.
#? Les fichiers modifiés sont tirés au sort à la mise en place.
find /srv/archives -type f -newer /srv/archives/.derniere-sauvegarde > ~/modifies.txt
#@ 5.7
#? `-w` ne retient que les correspondances qui forment un mot entier, sans lettre collée avant ni après.
#? Le piège : sans `-w`, « terreur » et « erreurs » contiennent la suite de lettres « erreur » et seraient comptées à tort.
#? Avec `-c` et `-i`, cela donne `grep -ciw`, et l'ordre des lettres d'options n'a pas d'importance.
#? Le contenu du rapport est tiré au sort à la mise en place : votre nombre diffère de celui du corrigé.
grep -ciw erreur /srv/archives/rapport2.txt > ~/nb-erreur-mot.txt
#@ 5.8
#? `find -size` arrondit la taille de chaque fichier à l'unité demandée, vers le haut, avant de comparer.
#? Avec `-1M`, un fichier de 300 Kio compte pour 1 Mio, qui n'est pas strictement inférieur à 1 : seuls les fichiers vides sont retenus, d'où la liste presque vide de Julien.
#? En exprimant la limite en octets (`-size -1048576c`), l'arrondi ne pose plus de problème ; `-size -1024k` fonctionne aussi.
#? `-type f` écarte les dossiers `photos` et `sons`, qui ne sont pas des médias.
# -size -1M arrondit chaque taille au Mio supérieur : seuls les fichiers vides sont « à moins de 1 »
find /srv/medias -type f -size -1048576c > ~/petits-medias.txt
#@ 5.9
#? `grep -B1` affiche chaque ligne trouvée précédée d'une ligne de contexte (B pour before) ; `head -n1` ne garde que cette ligne d'avant.
#? La recherche doit respecter la casse : avec `-i`, les lignes « erreur non fatale ignorée » seraient aussi retenues.
#? Écrire directement la sortie de `grep -B1 FATAL` (les deux lignes) est accepté, mais la réponse la plus précise est la seule ligne de cause.
#? La position de l'erreur et le texte de la cause sont tirés au sort à la mise en place.
grep -B1 'FATAL' ~/logs-app/app.log
grep -B1 'FATAL' ~/logs-app/app.log | head -n1 > ~/cause.txt
''',
    6: r'''
#@ 6.1
#? Le pipe envoie la liste produite par `ls` à `wc -l`, qui compte les lignes : quand sa sortie part dans un pipe, `ls` écrit un nom par ligne.
#? Le piège était `ls -a` : il ajoute `.` et `..`, ce qui fausse le compte de deux ; `ls -A` (« almost all ») montre les entrées cachées sans eux.
#? `find /etc -mindepth 1 -maxdepth 1 | wc -l` donne le même nombre, à condition de ne pas descendre dans les sous-dossiers.
#? Des marqueurs d'audit cachés, en nombre tiré au sort, ont été déposés dans /etc : le nombre d'un camarade n'est pas le vôtre.
ls -A /etc | wc -l > ~/nb-etc.txt
#@ 6.2
#? Chaque flux a son numéro : `>` (ou `1>`) redirige la sortie normale, `2>` la sortie d'erreur, et les deux redirections se combinent sur la même commande.
#? Sans sudo, `find` affiche `/root` puis se heurte à « Permission denied » : c'est exactement le mélange qu'on voulait séparer.
#? L'ordre des deux redirections n'a pas d'importance ici, puisqu'elles visent deux fichiers différents.
find /root > ~/find-ok.txt 2> ~/erreurs.txt
#@ 6.3
#? `2>&1` signifie « envoyer les erreurs là où va la sortie standard à cet instant » : il faut donc d'abord diriger la sortie standard vers le fichier.
#? Écrit `2>&1 > ~/tout.txt`, les erreurs restent à l'écran, car au moment du `2>&1` la sortie standard allait encore vers le terminal.
#? Deux redirections vers le même nom (`> tout.txt 2> tout.txt`) ouvrent le fichier deux fois et les lignes s'écrasent : le fichier doit être ouvert une seule fois.
#? En bash, `bavard &> ~/tout.txt` est un raccourci équivalent, lui aussi accepté.
#? L'ordre des lignes de `bavard` est tiré au sort à la mise en place : votre fichier peut différer de celui d'un camarade.
# L'ordre compte : d'abord la sortie standard vers le fichier, puis les erreurs au même endroit
bavard > ~/tout.txt 2>&1
#@ 6.4
#? `tee` écrit ce qu'il reçoit dans un fichier et le laisse passer vers la commande suivante : une seule ligne suffit pour garder la liste et la compter.
#? `wc -l` qui lit son entrée standard n'affiche que le nombre ; avec un nom de fichier (`wc -l fichier`), il ajouterait ce nom et la réponse ne serait plus un simple nombre.
#? Le nombre de programmes dépend de ce qui est installé : ne comparez pas le vôtre à celui d'un autre conteneur.
#? Des outils maison, en nombre tiré au sort, ont été installés dans /usr/bin : ne comparez pas votre nombre à celui d'un autre conteneur.
ls /usr/bin | tee ~/programmes.txt | wc -l > ~/nb-programmes.txt
#@ 6.5
#? `cut -d' ' -f4` isole le 4e champ (les champs sont séparés par une espace), puis `sort -u` trie et supprime les doublons en une seule étape.
#? `sort | uniq` donne le même résultat ; en revanche `uniq` seul, sans tri préalable, laisse passer les doublons non voisins.
#? `awk '{print $4}'` est une autre façon valable d'extraire la colonne.
#? Les personnes et leurs passages sont tirés au sort à la mise en place : vos noms diffèrent sans doute de ceux du corrigé.
cut -d' ' -f4 ~/texte/badges.txt | sort -u > ~/badgeurs.txt
#@ 6.6
#? `find /etc -type f` ne garde que les fichiers ; sans `-type f`, les dossiers seraient comptés aussi.
#? Les « Permission denied » passent par la sortie d'erreur : `2>/dev/null` les fait disparaître sans toucher à la sortie normale, qui seule arrive dans le pipe.
#? Surtout pas de sudo : root voit davantage de fichiers, et la question portait sur ce que voit un utilisateur ordinaire.
#? Des relevés d'audit, en nombre tiré au sort, ont été déposés sous /etc : le nombre d'un camarade n'est pas le vôtre.
find /etc -type f 2>/dev/null | wc -l > ~/nb-fichiers-etc.txt
#@ 6.7
#? On veut compter un flux, pas un mot : certaines erreurs ne contiennent pas « ERR », et certaines lignes normales en parlent (« 0 ERR »), d'où l'échec de `grep -c ERR`.
#? `2>&1 >/dev/null` se lit de gauche à droite : les erreurs vont d'abord là où va la sortie standard (le pipe), puis l'ancienne sortie standard est jetée.
#? Variante tout aussi juste : `compteur 2> /tmp/erreurs.txt`, puis `wc -l < /tmp/erreurs.txt`.
#? Le nombre d'erreurs est tiré au sort à la mise en place : votre résultat peut différer de celui du corrigé.
# 2>&1 envoie les erreurs dans le pipe, puis >/dev/null jette la sortie normale
compteur 2>&1 >/dev/null | wc -l > ~/nb-erreurs-compteur.txt
#@ 6.8
#? Par défaut, `sort` compare des caractères : « 9876 » passe après « 12000 » parce que « 9 » vient après « 1 » ; `-n` trie selon la valeur numérique.
#? `-r` inverse l'ordre pour avoir les plus grands en premier, et `head -n3` garde les trois premières lignes.
#? `sort -n | tail -n3` trouve les bons montants, mais du plus petit au plus grand : l'ordre demandé ne serait pas respecté.
#? Les montants sont tirés au sort à la mise en place : vos trois valeurs sont propres à votre environnement.
sort -rn ~/texte/ventes.txt | head -n3 > ~/top-ventes.txt
#@ 6.9
#? `uniq` ne compare que des lignes voisines : il faut trier avant, sinon deux passages éloignés de la même personne ne sont pas regroupés.
#? `uniq -d` (« duplicate ») n'affiche qu'une fois chaque ligne répétée, ce qui donne directement la liste voulue.
#? Variante acceptée : `sort | uniq -c | awk '$1 > 1 {print $2}'`, qui passe par le décompte.
#? Les badges sont tirés au sort à la mise en place : les noms de votre environnement peuvent différer.
cut -d' ' -f4 ~/texte/badges.txt | sort | uniq -d > ~/badges-multiples.txt
''',
    7: r'''
#@ 7.1
#? Le ticket demandait nano : `nano ~/config.txt`, on tape les trois lignes, `Ctrl+O` puis Entrée pour enregistrer, `Ctrl+X` pour quitter.
#? Le `printf` du corrigé produit le même fichier en une commande ; la vérification ne regarde que le contenu.
#? Le piège est dans les détails : une espace autour du `=`, une faute de frappe ou une ligne en trop suffisent à faire échouer la vérification (les lignes vides finales sont tolérées).
# Attendu avec nano ; équivalent en une commande :
printf 'serveur=localhost\nport=8080\ndebug=false\n' > ~/config.txt
#@ 7.2
#? Dans vim, tout se fait en mode normal : `dd` supprime la ligne du curseur, `G` va à la fin, `o` ouvre une ligne dessous en mode insertion.
#? Après avoir tapé « Fin », `Echap` ramène en mode normal, puis `:wq` enregistre et quitte ; en cas de doute, `Echap` puis `:q!` quitte sans rien enregistrer.
#? Le piège classique est de taper du texte en mode normal : chaque lettre devient une commande et le poème est abîmé, ce que la vérification détecte.
#? Les deux commandes `sed` du corrigé sont un équivalent non interactif.
# Attendu avec vim (dd sur la ligne INTRUS, G puis o pour ajouter « Fin », :wq) ; équivalent :
sed -i '/INTRUS/d' ~/config/poeme.txt
echo "Fin" >> ~/config/poeme.txt
#@ 7.3
#? La commande `s/ancien/nouveau/` de sed remplace un texte, et `-i` écrit le résultat dans le fichier au lieu de l'afficher.
#? Sans `-i`, sed n'affiche que le résultat et le fichier reste inchangé : c'est justement la bonne façon de tester avant de modifier.
#? `sed -i 's/^debug=false$/debug=true/'` est encore plus précis, car il n'accepte que la ligne entière.
sed -i 's/debug=false/debug=true/' ~/config/dev.conf
#@ 7.4
#? Sans option, `s///` ne remplace que la première occurrence de chaque ligne ; le `g` final (global) les remplace toutes.
#? Le piège était dans les lignes `backend_…`, qui contiennent deux fois `ancien-serveur` : sans `g`, la seconde restait.
#? Le nombre de lignes du fichier est tiré au sort à la mise en place : votre fichier peut être plus court ou plus long que celui du corrigé.
sed -i 's/ancien-serveur/nouveau-serveur/g' ~/config/app.conf
#@ 7.5
#? Le séparateur de `s` est le caractère qui suit immédiatement le `s` : avec `|`, les `/` des chemins deviennent des caractères ordinaires.
#? Variante acceptée : protéger chaque `/` avec un antislash, comme dans `s/\/var\/log\/boutique/\/srv\/logs\/boutique/g`, moins lisible mais correcte.
#? Le `g` reste indispensable : la ligne `rotation=` contient deux chemins à changer.
#? `/var/log/boutique-old` change aussi, comme le demandait le ticket, alors que `/var/log/nginx/boutique.log` ne contient pas le motif et reste intact.
sed -i 's|/var/log/boutique|/srv/logs/boutique|g' ~/config/chemins.conf
#@ 7.6
#? Un suffixe collé à `-i` (`-i.bak`) demande à sed de garder une copie de l'original sous ce nom avant de modifier le fichier.
#? Écrit avec une espace (`-i .bak`), le suffixe n'est plus rattaché à l'option : sed prend `.bak` pour son script et échoue.
#? Attention à ne pas relancer la commande : la seconde exécution remplacerait la copie par la version déjà modifiée (réinitialisez l'étape si besoin).
#? Faire `cp app-prod.conf app-prod.conf.bak` avant un `sed -i` est une variante tout aussi acceptée.
sed -i.bak 's/^maintenance=on$/maintenance=off/' ~/config/app-prod.conf
#@ 7.7
#? Une adresse de la forme `/début/,/fin/` limite la commande de sed aux lignes comprises entre ces deux motifs : ici, de `[admin]` jusqu'à la section suivante.
#? Un remplacement sur tout le fichier aurait changé le port des trois sections : c'est le piège que visait le ticket.
#? Variante acceptée : repérer le numéro de la bonne ligne avec `grep -n port= ~/config/services.ini`, puis `sed -i 'Ns/…/…/'` avec ce numéro, ou modifier la ligne dans un éditeur.
#? L'ordre des sections est tiré au sort à la mise en place : le numéro de ligne n'est pas le même chez tout le monde.
# De la ligne [admin] à la section suivante seulement
sed -i '/^\[admin\]/,/^\[/ s/^port=8080$/port=9090/' ~/config/services.ini
#@ 7.8
#? `/motif/d` supprime les lignes qui correspondent au motif, et `^` ancre ce motif au début de la ligne.
#? Avec `/DEBUG/d`, les lignes qui parlent du mode DEBUG plus loin dans le texte auraient disparu aussi.
#? Variante : `grep -v '^DEBUG' app.log > tmp && mv tmp app.log` ; en revanche `grep -v … app.log > app.log` vide le fichier, car le shell le tronque avant que grep ne le lise.
sed -i '/^DEBUG/d' ~/config/app.log
#@ 7.9
#? vim garde les modifications en cours dans un fichier d'échange caché, `.tarifs-groupes.conf.swp` : après une session interrompue, il reste là, et vim affiche l'avertissement E325 à chaque ouverture.
#? Tout se joue sur les dates, que l'avertissement affiche : si le fichier est plus ancien que le fichier d'échange, celui-ci contient le travail le plus récent, qu'on récupère avec `vim -r` (ou R dans l'avertissement), puis `:wq`.
#? Si vim signale « NEWER than swap file! », le fichier a été enregistré après l'interruption : le fichier d'échange n'est qu'un vieux brouillon, et le récupérer écraserait la version enregistrée.
#? Dans les deux cas, il faut ensuite supprimer le fichier d'échange (D dans l'avertissement, ou `rm`) ; le supprimer sans réfléchir perd les modifications quand elles n'ont jamais été enregistrées.
#? `[ fichier -nt autre ]` compare deux dates de modification, comme le fait vim. Au clavier : `vim tarifs-groupes.conf`, lire l'avertissement, puis R ou D. La variante (brouillon à récupérer ou périmé) est tirée au sort.
cd ~/config
ls -a
if [ tarifs-groupes.conf -nt .tarifs-groupes.conf.swp ]; then
    echo "Fichier enregistré après l'interruption : le fichier d'échange est périmé"
else
    # Récupération sans terminal : -es exécute les commandes sans interface
    vim -es -r tarifs-groupes.conf -c wq
fi
rm -f .tarifs-groupes.conf.swp
cd ~
''',
    8: r'''
cd ~/regex
#@ 8.1
#? `^` ancre le motif au début de la ligne, et `[rs]` accepte un seul caractère parmi `r` et `s`.
#? Sans l'ancre, grep garderait toutes les lignes qui contiennent un r ou un s n'importe où, c'est-à-dire presque tout le fichier.
#? `grep -E '^(r|s)' /etc/passwd` est une variante équivalente avec une alternative.
#? Des comptes de service, tirés au sort à la mise en place, s'ajoutent à /etc/passwd : votre résultat est propre à votre serveur.
grep '^[rs]' /etc/passwd > rs.txt
#@ 8.2
#? Le motif décrit l'adresse morceau par morceau : partie locale `[a-z0-9._-]+`, un `@`, un mot de domaine, zéro ou plusieurs « point + mot » `(\.[a-z0-9-]+)*`, puis un point et au moins deux lettres.
#? `-o` n'affiche que la partie reconnue et `-E` active la syntaxe étendue (`+`, `{2,}`, les parenthèses).
#? Le piège principal était `-i` : il aurait accepté l'adresse en majuscules, que la consigne exclut.
#? Le point doit être échappé (`\.`) : non échappé, il accepte n'importe quel caractère et laisse passer des adresses mal formées.
#? Les adresses et les pièges sont tirés au sort à la mise en place ; l'ordre des lignes et les doublons ne comptent pas dans la vérification.
grep -oE '[a-z0-9._-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}' contacts.txt > emails-valides.txt
#@ 8.3
#? `^[[:space:]]*(#|$)` décrit « des blancs éventuels en début de ligne, puis un # ou la fin de la ligne », et `-v` inverse la sélection.
#? `grep -v '^#'` laissait passer les commentaires indentés et les lignes faites seulement d'espaces ou de tabulations.
#? À l'inverse, `grep -v '#'` supprimait aussi `password=ab#12` et l'URL, où le `#` fait partie de la valeur.
#? `\s` à la place de `[[:space:]]` fonctionne aussi avec GNU grep.
grep -vE '^[[:space:]]*(#|$)' serveur.conf > serveur-clean.txt
#@ 8.4
#? Le motif décrit un numéro entier : un 0, un chiffre de 1 à 9, puis quatre fois « espace + deux chiffres » ; `\b` empêche de mordre dans un nombre plus long.
#? Le résultat est redirigé vers `censure.txt` : avec `sed -i`, c'est l'original `contacts.txt` qui aurait été modifié, ce que la vérification refuse.
#? Remplacer tous les chiffres aurait aussi masqué les adresses et les numéros de contact.
#? Les numéros et les faux numéros sont tirés au sort à la mise en place : votre fichier diffère de celui du corrigé.
sed -E 's/\b0[1-9]( [0-9]{2}){4}\b/XX XX XX XX XX/g' contacts.txt > censure.txt
#@ 8.5
#? `-o` n'affiche que les morceaux reconnus, et `-w` n'accepte une correspondance que si elle n'est pas collée à d'autres lettres ou chiffres.
#? Sans `-w`, un numéro trop long comme `101 22 33 44 55` ou `01 23 45 67 890` aurait fourni un faux numéro valide extrait de son milieu.
#? `grep -oE '\b0[1-9]( [0-9]{2}){4}\b'` est une variante équivalente ; l'ordre et les doublons ne comptent pas dans la vérification.
#? Les numéros sont tirés au sort à la mise en place.
grep -owE '0[1-9]( [0-9]{2}){4}' contacts.txt > telephones.txt
#@ 8.6
#? Les parenthèses capturent le jour, le mois et l'année, et `\3-\2-\1` les réécrit dans l'ordre ISO.
#? Le séparateur `#` évite d'avoir à protéger les `/` des dates, et le `g` convertit les deux dates de la ligne des relances.
#? Les quantités exactes `{2}`, `{2}` et `{4}` laissent intactes les échéances incomplètes comme `03/2026` ou `1/4/2026`.
#? Les dates sont tirées au sort à la mise en place : votre fichier diffère de celui du corrigé.
sed -E 's#([0-9]{2})/([0-9]{2})/([0-9]{4})#\3-\2-\1#g' paiements.txt > paiements-iso.txt
#@ 8.7
#? `-x` impose que la ligne entière corresponde au motif, comme si on l'encadrait par `^` et `$`.
#? Sans cet ancrage, grep trouvait un morceau valide dans une ligne invalide (« dmin » dans « Admin », « bob » dans « bob smith »).
#? `{2,15}` compte les caractères après la première lettre : un identifiant fait donc de 3 à 16 caractères au total.
#? `grep -E '^[a-z][a-z0-9_-]{2,15}$'` est une variante équivalente ; une partie des demandes est tirée au sort à la mise en place.
grep -xE '[a-z][a-z0-9_-]{2,15}' demandes.txt > identifiants.txt
#@ 8.8
#? Dans un motif, le point est un joker : `9.99` accepte aussi `9x99`, et il se trouve à l'intérieur de `19.99` ou `29.99`.
#? `\.` désigne un vrai point, et `;9\.99$` ancre le motif sur la dernière colonne : entre le dernier `;` et la fin de la ligne.
#? Grâce au `;` en tête du motif, la référence `REF-9599` et les prix plus longs ne sont pas touchés.
#? Variante valable avec awk, sur la 3e colonne : `awk -F';' 'BEGIN { OFS = ";" } $3 == "9.99" { $3 = "10.49" } { print }'` vers un fichier temporaire, puis `mv`.
sed -i -E 's/;9\.99$/;10.49/' tarifs.csv
''',
    9: r'''
#@ 9.1
#? Le schéma classique : extraire le champ (`cut -d: -f7`), trier, compter avec `uniq -c`, puis trier à nouveau sur le nombre avec `sort -rn`.
#? Le premier tri est indispensable : `uniq -c` ne regroupe que les lignes voisines.
#? `awk -F: '{print $7}'` peut remplacer `cut` pour extraire le shell.
#? Des comptes de bornes et d'impression, aux shells tirés au sort, s'ajoutent à /etc/passwd : votre décompte est propre à votre serveur.
cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn > ~/shells-count.txt
#@ 9.2
#? On filtre d'abord les requêtes en erreur (`$9 >= 400`, le code HTTP est le 9e champ), puis on applique le « top » classique à l'IP.
#? Le piège : les IP qui font le plus de requêtes ne sont pas celles qui cumulent le plus d'erreurs, et la mise en place a fait exprès de les séparer.
#? Le dernier `awk '{print $2}'` retire les compteurs, mais la vérification accepte aussi le résultat de `uniq -c` tel quel, compteurs compris.
#? Les adresses sont tirées au sort à la mise en place : vos IP diffèrent de celles d'un camarade.
awk '$9 >= 400 {print $1}' ~/logs/access.log | sort | uniq -c | sort -rn | head -3 | awk '{print $2}' > ~/top-ip.txt
#@ 9.3
#? Le code HTTP est le 9e champ : `awk '$9 == 404'` ne garde que les requêtes qui ont réellement reçu une 404.
#? Un simple `grep 404` compte aussi la page `/produits/404-sac-randonnee` et les tailles de réponse 1404 et 4040, glissées exprès comme pièges.
#? Variante : `awk '$9 == 404 { n++ } END { print n }'` compte sans passer par `wc -l`.
#? Le nombre attendu dépend du journal, tiré au sort à la mise en place.
# Piège : « grep 404 » compte aussi les tailles et les pages qui contiennent 404 ; le code HTTP est le 9e champ
awk '$9 == 404' ~/logs/access.log | wc -l > ~/nb-404.txt
#@ 9.4
#? Avec `-F:`, `$3` est l'UID et `$7` le shell ; `&&` combine les conditions, et `!~` teste qu'un champ ne correspond pas à une regex.
#? Les bornes étaient piégées : l'UID 1000 est inclus, 65534 (nobody) est exclu, et le compte de service en 999 ne compte pas.
#? Les shells en `nologin` ou en `false` interdisent la connexion ; `/bin/sh` et `/bin/zsh`, eux, sont de vrais shells.
#? `print $1, $3` sépare les deux valeurs par une espace ; les UID sont tirés au sort à la mise en place, et l'ordre des lignes ne compte pas.
awk -F: '$3 >= 1000 && $3 < 65534 && $7 !~ /(nologin|false)$/ {print $1, $3}' ~/texte/passwd-serveur > ~/users-uid.txt
#@ 9.5
#? `tr` ne prend pas de nom de fichier : il lit son entrée standard, qu'on alimente avec `<` (ou `cat fichier |`).
#? `tr 'a-z' 'A-Z'` remplace chaque caractère du premier ensemble par celui qui occupe la même place dans le second.
#? `tr '[:lower:]' '[:upper:]'` est une variante équivalente pour ce texte sans accents.
tr 'a-z' 'A-Z' < ~/texte/minuscules.txt > ~/texte/majuscules.txt
#@ 9.6
#? Dans awk, `s += $10` additionne la taille de chaque requête retenue, et le bloc `END` affiche le total après la dernière ligne.
#? `-v ip="$ip"` transmet l'adresse à awk, et l'égalité exacte `$1 == ip` ne retient que cette adresse.
#? Le piège : une adresse plus longue qui commence pareil existe dans le journal, et un `grep` sur l'adresse l'aurait comptée aussi.
#? L'adresse du client et le journal sont tirés au sort à la mise en place : votre total est propre à votre environnement.
ip=$(grep -oE '([0-9]+\.){3}[0-9]+' ~/logs/LISEZ-MOI)
awk -v ip="$ip" '$1 == ip { s += $10 } END { print s }' ~/logs/access.log > ~/octets-ip.txt
#@ 9.7
#? Il faut additionner les montants de chaque produit avant de classer : `t[$1] += $2 * $3` accumule le chiffre d'affaires dans un tableau indexé par le nom du produit.
#? `NR > 1` saute la ligne d'en-tête, et la boucle `for (p in t)` du bloc `END` affiche chaque total avant le tri numérique.
#? Le piège : classer les lignes une par une donne un autre podium, et la mise en place s'est assurée que les deux résultats diffèrent.
#? La vérification accepte aussi les lignes qui gardent le total à côté du nom ; les ventes sont tirées au sort à la mise en place.
awk -F';' 'NR > 1 { t[$1] += $2 * $3 } END { for (p in t) print t[p], p }' ~/texte/ventes.csv | sort -rn | head -n3 | awk '{print $2}' > ~/top-produits.txt
#@ 9.8
#? `tr` travaille octet par octet ; en UTF-8, « é » occupe deux octets, et `tr` ne sait pas le convertir comme une seule lettre.
#? GNU sed comprend les caractères : dans le remplacement, `\U` passe en majuscules tout ce qui suit, et `&` désigne le texte trouvé (ici la ligne entière).
#? `sed -E 's/(.*)/\U\1/'` est une écriture équivalente ; `\U` est une extension propre à GNU sed.
sed 's/.*/\U&/' ~/texte/accents.txt > ~/texte/accents-maj.txt
#@ 9.9
#? Avec `-F:`, awk découpe aux deux-points : l'heure, placée entre le premier et le deuxième « : » de la date, devient le 2e champ.
#? Avec le séparateur par défaut, l'heure reste noyée dans le 4e champ, avec le jour, les minutes et les secondes.
#? Le « top » classique (`sort | uniq -c | sort -rn | head -n1`) donne ensuite l'heure la plus chargée ; « 09 » comme « 9 » sont acceptés.
#? L'heure de pointe est tirée au sort à la mise en place : la vôtre peut différer de celle du corrigé.
awk -F: '{print $2}' ~/logs/access.log | sort | uniq -c | sort -rn | head -n1 | awk '{print $2}' > ~/heure-pointe.txt
''',
    10: r'''
#@ 10.1
#? Créer un compte est une tâche d'administration, d'où `sudo` ; `-m` crée le dossier personnel et `-s /bin/bash` choisit le shell.
#? Sans `-m`, pas de dossier personnel, et le créer ensuite avec `sudo mkdir` le laisse appartenir à root : la vérification le refuse.
#? Sur Debian et Ubuntu, `sudo adduser alice` (version interactive) crée aussi le dossier personnel et convient.
sudo useradd -m -s /bin/bash alice
sudo useradd -m -s /bin/bash bob
#@ 10.2
#? `groupadd` crée le groupe, puis `usermod -aG` y ajoute chaque utilisateur sans lui retirer ses autres groupes.
#? Le piège : `-G` sans `-a` remplace toute la liste des groupes secondaires.
#? `sudo gpasswd -a alice equipe` est une variante équivalente ; `id alice` permet de vérifier le résultat.
#? Une nouvelle appartenance ne s'applique qu'aux sessions ouvertes après le changement.
sudo groupadd equipe
sudo usermod -aG equipe alice
sudo usermod -aG equipe bob
#@ 10.3
#? Trois réglages : le groupe du dossier (`chgrp equipe`), tous les droits pour ce groupe, et aucun pour les autres, d'où `770`.
#? Créé par root avec la umask habituelle, le dossier est en `755` : les autres pouvaient encore le lister et y entrer, et c'est ce que la vérification contrôle avec `intrus`.
#? Sur un dossier, `w` permet de créer des fichiers et `x` d'y entrer : il faut les deux, plus `r` pour lister.
#? `chmod 2770` est également accepté, et prépare déjà l'exercice sur l'héritage du groupe.
sudo mkdir /home/partage
sudo chgrp equipe /home/partage
sudo chmod 770 /home/partage
#@ 10.4
#? Créé avec sudo, le fichier appartient à root : `chown alice:equipe` change d'un coup le propriétaire et le groupe.
#? `640` se lit triade par triade : `rw-` (6) pour alice, `r--` (4) pour le groupe, `---` (0) pour les autres.
#? Le piège était d'oublier le groupe ou de laisser des droits aux autres : bob doit pouvoir lire sans modifier, et intrus ne doit rien voir.
sudo touch /home/partage/secret.txt
sudo chown alice:equipe /home/partage/secret.txt
sudo chmod 640 /home/partage/secret.txt
#@ 10.5
#? La notation symbolique change un seul droit : `u+x` ajoute l'exécution pour le propriétaire, sans toucher au reste.
#? `chmod +x` sans préciser qui l'ajouterait aussi au groupe et aux autres, et un `chmod 700` ou `744` écraserait les droits de départ.
#? Les droits de départ sont tirés au sort à la mise en place : comparez `ls -l` avant et après, seul un `x` doit apparaître dans la première triade.
ls -l ~/scripts/deploy.sh
chmod u+x ~/scripts/deploy.sh
#@ 10.6
#? Le bit setgid posé sur un dossier (`g+s`, ou le 2 de `2770`) fait hériter aux nouveaux fichiers le groupe du dossier, au lieu du groupe principal de leur créateur.
#? Il ne s'applique qu'aux fichiers créés ensuite : les fichiers déjà présents gardent leur groupe, qu'on changerait au besoin avec `chgrp`.
#? Le setgid règle le groupe d'un nouveau fichier, pas ses droits : ceux-ci dépendent toujours de la umask de son créateur.
sudo chmod g+s /home/partage
#@ 10.7
#? `usermod -aG boutique webdev` ajoute le groupe sans rien retirer : `-a` (append) s'utilise avec `-G`.
#? Le piège du ticket : `usermod -G boutique webdev` remplace la liste des groupes secondaires, et webdev perd ceux qu'il avait.
#? Si c'est arrivé, on rajoute les groupes notés dans `~/rh/webdev.txt` de la même façon ; `sudo gpasswd -a webdev boutique` est une variante valable.
#? Les groupes d'origine de webdev sont tirés au sort à la mise en place : les vôtres peuvent différer.
id webdev
sudo usermod -aG boutique webdev
#@ 10.8
#? Dans `sudo echo … >> fichier`, c'est votre shell, qui n'est pas root, qui ouvre le fichier avant même le lancement de sudo : d'où le « Permission denied ».
#? `tee -a`, lancé avec sudo, ouvre lui-même le fichier en root et ajoute à la fin ; `> /dev/null` évite seulement de réafficher la ligne.
#? Sans `-a`, `tee` écrase le fichier et le contenu d'origine est perdu : la vérification le détecte.
#? `echo 'BOUTIQUE_ENV=prod' | sudo sh -c 'cat >> /etc/boutique.env'` est une variante valable, alors qu'un `chmod` ou un `chown` pour contourner est refusé.
# « sudo echo … >> f » : la redirection est faite par le shell de l'étudiant, pas par root
echo "BOUTIQUE_ENV=prod" | sudo tee -a /etc/boutique.env > /dev/null
#@ 10.9
#? Chaque triade se traduit en un chiffre : r vaut 4, w vaut 2, x vaut 1, et on additionne (`rwxr-x--x` donne 751).
#? Le premier caractère affiché par `ls -l` indique le type de fichier (`-`), pas un droit : on ne traduit que les neuf suivants.
#? Le corrigé automatise la traduction, mais un simple `chmod` en octal par fichier, ou la forme symbolique `chmod u=rwx,g=rx,o=x`, convient tout autant.
#? Les droits demandés sont tirés au sort à la mise en place : votre consigne diffère de celle du corrigé.
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
#? Sous Ubuntu, la règle `%sudo ALL=(ALL:ALL) ALL` existe déjà : ajouter le compte au groupe `sudo` avec `usermod -aG` suffit à lui donner tous les droits d'administration.
#? Le piège classique est d'oublier le mot de passe : un compte créé par `useradd` n'en a pas d'utilisable, et sudo demande toujours le mot de passe de l'utilisateur lui-même, pas celui de root.
#? Ici `chpasswd` définit le mot de passe sans interaction ; en classe, `sudo passwd stagiaire` fait exactement la même chose en vous le demandant au clavier.
#? Vous pouvez aussi créer le compte directement dans le groupe avec `sudo useradd -m -s /bin/bash -G sudo stagiaire`, puis vérifier le résultat avec `sudo -l -U stagiaire`.
sudo useradd -m -s /bin/bash stagiaire
sudo usermod -aG sudo stagiaire
echo 'stagiaire:Stagiaire-2026!' | sudo chpasswd
sudo -l -U stagiaire
#@ 11.2
#? `pgrep -x` donne le PID d'un processus d'après son nom exact, et `ps -o user= -p PID` affiche uniquement son propriétaire, sans ligne d'en-tête.
#? Avec `ps aux | grep rogue-worker`, attention à ne pas confondre la vraie ligne avec celle de la commande grep elle-même.
#? Le fichier ne doit contenir qu'une ligne de deux mots, le PID puis l'utilisateur : aucune phrase ni colonne supplémentaire.
#? Le PID change à chaque démarrage du processus, et le compte qui l'a lancé est tiré au sort à la mise en place : ne recopiez ni l'un ni l'autre chez un camarade.
p=$(pgrep -x rogue-worker)
echo "$p $(ps -o user= -p "$p")" > ~/rogue.txt
#@ 11.3
#? Sans option, `kill` envoie le signal TERM : le programme peut l'intercepter, faire son ménage et s'arrêter proprement, ce que confirme son journal.
#? Le processus appartient à intrus : sans `sudo`, vous obtenez « Operation not permitted », car on ne signale que ses propres processus.
#? Le piège est `kill -9` : KILL arrête le programme sans lui laisser la moindre chance, et le journal ne mentionne alors aucun arrêt propre.
#? Ici `$p` est le PID trouvé à l'exercice précédent ; `sudo pkill -x rogue-worker` envoie lui aussi TERM et convient tout autant.
# Le processus appartient à « intrus » : sudo est indispensable ; kill sans option envoie TERM
sudo kill "$p"
sleep 1
#@ 11.4
#? `nice -n 10 commande` lance la commande avec une gentillesse de 10, c'est-à-dire une priorité plus basse, et le `&` final la place en arrière-plan.
#? Le processus doit vous appartenir : le lancer avec `sudo nice …` le ferait tourner en root, et la vérification ne le reconnaîtrait pas.
#? Variante valable : lancer `sleep 1000 &`, puis `renice -n 10 -p PID`, car un utilisateur ordinaire a le droit d'augmenter la gentillesse de ses processus.
#? Les redirections vers /dev/null du corrigé servent seulement au banc de test ; contrôlez le résultat avec `ps -o pid,ni,cmd -C sleep`.
nice -n 10 sleep 1000 > /dev/null 2>&1 &
#@ 11.5
#? Par convention, beaucoup de services traitent HUP comme « relis ta configuration », mais ce n'est qu'une convention : lab-service documente son propre signal (`lab-service --aide`), HUP, USR1 ou USR2 selon les serveurs.
#? Le piège est d'envoyer un signal que le service n'intercepte pas : TERM, mais aussi HUP ou USR1 quand ce n'est pas le sien, l'arrêteraient, alors que la vérification exige que le même processus tourne toujours.
#? Le service appartient à root, d'où le `sudo` ; `sudo pkill -USR1 -x lab-service` est une écriture équivalente quand le signal est USR1.
# On lit d'abord dans la documentation du service le signal qu'il intercepte
lab-service --aide
sig=$(lab-service --aide | grep -oE 'signal (HUP|USR1|USR2)' | cut -d' ' -f2)
sudo kill -"$sig" "$(pgrep -x lab-service)"
sleep 2
#@ 11.6
#? Si un processus revient avec un nouveau PID, c'est que quelque chose le relance : la colonne PPID de `ps` (ou `pstree -p`) permet de remonter jusqu'au responsable.
#? Selon les serveurs, mineur est relancé par son parent, par une chaîne de deux processus (le parent est lui-même relancé par un grand-parent) ou par une boucle anonyme qui s'appelle simplement `bash` : il faut remonter la chaîne jusqu'en haut plutôt que de chercher un nom.
#? On arrête tous les processus de la chaîne, puis mineur : si l'on épargne un maillon, il relance les autres deux secondes plus tard.
#? Tous appartiennent à intrus, d'où le `sudo` ; les noms (veille-…, relais-…) sont tirés au sort, ne recopiez pas ceux d'un camarade.
# On remonte les parents de mineur tant qu'ils appartiennent à intrus, puis on arrête toute la chaîne
m=$(pgrep -x mineur | head -n1)
chaine=""
p=$(ps -o ppid= -p "$m" | tr -d ' ')
while [ "$p" -gt 1 ] && [ "$(ps -o user= -p "$p")" = intrus ]; do
    ps -o pid,ppid,user,args -p "$p"
    chaine="$chaine $p"
    p=$(ps -o ppid= -p "$p" | tr -d ' ')
done
sudo kill $chaine
sudo kill $(pgrep -x mineur)
sleep 1
#@ 11.7
#? Le signal STOP gèle un processus sans le terminer, et le signal CONT le fait repartir exactement là où il en était : `kill -CONT PID` pour la reprise du soir.
#? Le piège est d'utiliser un signal d'arrêt comme TERM ou KILL : le processus disparaît et son travail est perdu.
#? export-nuit vous appartient, donc pas besoin de sudo ; `pkill -STOP -x export-nuit` est une variante équivalente.
#? Dans `ps`, la colonne STAT affiche `T` pour un processus suspendu.
kill -STOP "$(pgrep -x export-nuit)"
ps -o pid,stat,cmd -C export-nuit
#@ 11.8
#? La règle `thomas ALL=(root) NOPASSWD: /usr/local/sbin/relance-boutique` n'autorise qu'une commande, désignée par son chemin absolu, sans mot de passe.
#? Une erreur de syntaxe dans les fichiers de sudo peut bloquer tout sudo : on valide toujours avant, ici avec `visudo -cf` sur un fichier temporaire.
#? Le fichier de /etc/sudoers.d doit appartenir à root avec les droits 0440, d'où `install -m 440 -o root -g root` ; sinon `visudo -c` signale « bad permissions ».
#? La méthode la plus simple reste `sudo visudo -f /etc/sudoers.d/thomas`, qui vérifie la syntaxe à l'enregistrement ; évitez un point dans le nom du fichier, car sudo l'ignorerait.
#? Le piège est une règle trop large, comme `ALL` en fin de ligne : Sophie voulait cette commande et rien d'autre.
echo 'thomas ALL=(root) NOPASSWD: /usr/local/sbin/relance-boutique' > /tmp/regle-thomas
sudo visudo -cf /tmp/regle-thomas
sudo install -m 440 -o root -g root /tmp/regle-thomas /etc/sudoers.d/thomas
sudo -l -U thomas
''',
    12: r'''
#@ 12.1
#? La boucle `for` répète la création pour les quatre comptes ; `useradd -m` crée le dossier personnel de chacun.
#? `sudo -u papa mkdir …` crée le dossier au nom de papa, qui en est donc propriétaire.
#? Le piège classique est `sudo mkdir /home/papa/Travail` : le dossier appartient alors à root et la vérification échoue.
#? Variante valable : créer les dossiers avec sudo, puis les donner à chacun avec `sudo chown papa: /home/papa/Travail /home/papa/Bazar`.
for u in papa maman fils fille; do sudo useradd -m -s /bin/bash $u; done
for u in papa maman fils fille; do sudo -u $u mkdir /home/$u/Travail /home/$u/Bazar; done
#@ 12.2
#? On crée les deux groupes, puis on ajoute chaque membre avec `usermod -aG`, qui ajoute un groupe sans retirer les autres.
#? Le piège est d'oublier le `-a` : `usermod -G` remplace toute la liste des groupes secondaires du compte.
#? `sudo gpasswd -a papa parents` est une autre façon valable d'ajouter un membre ; vérifiez ensuite avec `getent group parents` et `getent group enfants`.
sudo groupadd parents
sudo groupadd enfants
for u in papa maman; do sudo usermod -aG parents $u; done
for u in fils fille; do sudo usermod -aG enfants $u; done
#@ 12.3
#? Il faut un groupe `famille` qui rassemble les quatre membres, propriétaire du dossier, avec tous les droits pour le groupe et aucun pour les autres.
#? Le 2 de `2770` est le bit setgid : les fichiers créés dans le dossier hériteront du groupe famille, ce qui facilite le partage.
#? Le setgid n'est pas exigé par la vérification : `chmod 770` suffit, mais 2770 est la bonne pratique pour un dossier partagé.
#? Le piège est de donner des droits aux autres (755 ou 777) : la baby-sitter y aurait alors accès.
sudo groupadd famille
for u in papa maman fils fille; do sudo usermod -aG famille $u; done
sudo mkdir /home/famille
sudo chgrp famille /home/famille
sudo chmod 2770 /home/famille
#@ 12.4
#? Même schéma que l'espace commun, mais avec le groupe `parents`, qui existe déjà et ne contient que papa et maman.
#? Les enfants ne sont pas dans ce groupe : ils tombent dans la catégorie des « autres », qui n'a aucun droit, et ne peuvent donc même pas lister le dossier.
#? Testez-vous toujours en vous mettant à la place des utilisateurs, par exemple avec `sudo -u fils ls /home/parents-only`.
sudo mkdir /home/parents-only
sudo chgrp parents /home/parents-only
sudo chmod 2770 /home/parents-only
#@ 12.5
#? Les nouveaux dossiers personnels sont créés en 755, lisibles par tout le monde. Selon les serveurs, Marc s'y est pris de trois façons : `HOME_MODE 0755` dans /etc/login.defs, HOME_MODE mis en commentaire (useradd applique alors la UMASK 022, donc 755), ou une « surcouche » /usr/local/sbin/useradd qui ouvre chaque dossier après coup.
#? La démarche vaut pour tous les cas : `grep -n HOME_MODE /etc/login.defs`, puis `sudo sh -c 'command -v useradd'` pour savoir quel useradd lance sudo (/usr/local/sbin passe avant /usr/sbin dans son PATH).
#? Il faut ensuite corriger les deux aspects : la cause pour les futurs comptes, et un `chmod 750` sur les dossiers déjà créés, car `useradd` n'applique HOME_MODE qu'à la création.
#? Le piège est de ne corriger qu'un des deux, ou de recopier la correction d'un camarade : sa cause n'est pas forcément la vôtre, et la vérification crée un vrai compte pour tester.
#? `HOME_MODE 0700` convient également : la vérification exige seulement qu'aucun droit ne soit donné aux « autres ».
sudo useradd -m -s /bin/bash invite
# Les dossiers de la famille ont été créés en 755 : qu'est-ce qui fixe les droits des nouveaux dossiers ?
ls -l /home
grep -n 'HOME_MODE\|^UMASK' /etc/login.defs
u=$(sudo sh -c 'command -v useradd')
echo "sudo useradd lance : $u"
# Une surcouche de useradd placée avant le vrai : on la retire
if [ "$u" != /usr/sbin/useradd ]; then sudo cat "$u"; sudo rm -f "$u"; fi
# HOME_MODE absent, en commentaire ou trop ouvert : on le fixe à 0750
if grep -qE '^#?HOME_MODE' /etc/login.defs; then
    sudo sed -i -E 's/^#?HOME_MODE.*/HOME_MODE\t0750/' /etc/login.defs
else
    echo 'HOME_MODE 0750' | sudo tee -a /etc/login.defs > /dev/null
fi
for u in papa maman fils fille invite; do sudo chmod 750 /home/$u; done
#@ 12.6
#? Pour atteindre un dossier, il faut le droit `x` sur chaque dossier du chemin, alors que `r` ne sert qu'à lister son contenu.
#? On donne donc au groupe enfants, qui rassemble exactement le frère et la sœur, le droit de traverser /home/fille (710) et celui de lister et traverser Bazar (750).
#? Les parents et invite ne sont pas dans ce groupe : sans droit pour les autres sur /home/fille, ils ne peuvent même pas atteindre Bazar.
#? Le piège est de donner `r` au groupe sur /home/fille (le fils verrait tout son contenu) ou `x` aux autres ; fille reste propriétaire et garde tous ses droits.
# Le groupe enfants peut traverser /home/fille (sans la lister) et lister Bazar
sudo chgrp enfants /home/fille /home/fille/Bazar
sudo chmod 710 /home/fille
sudo chmod 750 /home/fille/Bazar
#@ 12.7
#? Avec un tiret, `-perm -o=r` (ou `-perm -004`) signifie « au moins ces bits-là » : on ne teste que le droit de lecture des autres, quels que soient les autres bits.
#? Le piège est `-perm 644`, qui ne trouve que les fichiers dont les droits sont exactement 644, et en oublie donc plusieurs.
#? Le `-type f` est indispensable : les dossiers de /srv/ancien-pc sont en 755 et apparaîtraient sinon en trop dans la liste.
#? Les droits sont distribués au hasard par la mise en place : votre liste peut différer de celle d'un camarade, et l'ordre des lignes n'a pas d'importance.
find /srv/ancien-pc -type f -perm -o=r > ~/fichiers-ouverts.txt
''',
    13: r'''
#@ 13.1
#? Dans ce lab, la liste des paquets disponibles est vide au départ : `apt update` doit la télécharger depuis le dépôt déclaré dans /etc/apt/sources.list (ici le miroir interne, depot.cimes.lan) avant que `apt install` puisse trouver quoi que ce soit.
#? Le piège classique est de lancer directement `sudo apt install tree` et d'obtenir « Unable to locate package ».
#? `apt search tree` ou `apt show tree`, après la mise à jour, permettent de vérifier le nom exact du paquet avant de l'installer.
#? Le corrigé utilise `apt-get` avec des options silencieuses, pratiques dans un script ; au clavier, `sudo apt update` puis `sudo apt install tree` conviennent parfaitement.
sudo apt-get update -qq
sudo apt-get install -y -qq tree > /dev/null
#@ 13.2
#? dpkg connaît la liste des fichiers installés par chaque paquet, et `dpkg -S /chemin` fait la recherche dans l'autre sens : quel paquet a installé ce fichier ?
#? La réponse de dpkg a la forme `paquet: /chemin` : on ne garde que ce qui précède les deux-points, par exemple avec `cut -d: -f1`.
#? Le piège est de recopier toute la ligne : le fichier ne doit contenir que le nom du paquet.
#? La commande de la question est tirée au sort : votre fichier question.txt ne désigne pas forcément la même que celle d'un camarade.
cat ~/paquets/question.txt
f=$(grep -oE '/[^ ]+' ~/paquets/question.txt | head -n1)
dpkg -S "$f" | cut -d: -f1 > ~/paquet.txt
#@ 13.3
#? `wget -O fichier URL` enregistre la page sous le nom choisi ; avec curl, l'équivalent est `curl -o fichier URL`.
#? Le dossier de destination doit exister avant le téléchargement, d'où le `mkdir -p` : ni wget ni curl ne le créent.
#? Le piège est d'oublier l'option de sortie : wget enregistrerait index.html dans le dossier courant, et curl afficherait la page dans le terminal.
#? La page de l'intranet est générée à chaque visite et le serveur garde l'empreinte de ce qu'il envoie : un fichier écrit à la main, retouché, ou enregistré avec les en-têtes HTTP (`curl -i`) n'est pas accepté.
#? `curl -o ~/telechargements/page.html http://intranet.cimes.lan/` convient tout autant.
mkdir -p ~/telechargements
wget -q -O ~/telechargements/page.html http://intranet.cimes.lan/
#@ 13.4
#? `apt show cowsay` montre ses dépendances (perl…) : en l'installant, apt ajoute aussi celles qui manquent, et les marque « installées automatiquement ».
#? `apt remove cowsay` ne retire que cowsay : apt signale ensuite les paquets devenus inutiles (« no longer required »), que `apt autoremove` désinstalle.
#? Le piège est de s'arrêter après `apt remove` : perl et les autres dépendances restent sur le serveur. Désinstaller ces paquets un par un marcherait aussi, mais autoremove sait lesquels ont été installés pour cowsay.
#? `sudo apt purge cowsay` puis `sudo apt autoremove --purge` conviennent aussi : ils retirent en plus les fichiers de configuration. Les journaux (/var/log/apt/history.log, /var/log/dpkg.log) gardent la trace de chaque étape.
apt show cowsay 2>/dev/null | grep '^Depends'
sudo apt-get install -y -qq cowsay > /dev/null
/usr/games/cowsay Bonjour
sudo apt-get remove -y -qq cowsay > /dev/null
sudo apt-get autoremove -y -qq > /dev/null
#@ 13.5
#? `dpkg -c fichier.deb` liste le contenu d'un paquet sans l'installer : on sait ainsi ce qu'il va déposer sur le système avant de lui faire confiance.
#? La liste affiche des chemins qui commencent par `./` : le corrigé retire ce point pour obtenir un vrai chemin absolu, comme /usr/bin/….
#? Le nom du programme et la version du paquet sont tirés au sort, d'où le joker `cs-outils_*_all.deb` : votre programme peut différer de celui d'un camarade.
#? `dpkg-deb -c` est équivalent pour la lecture ; l'installation d'un paquet local se fait ensuite avec `sudo dpkg -i`.
dpkg -c /srv/paquets/cs-outils_*_all.deb
dpkg -c /srv/paquets/cs-outils_*_all.deb | grep -oE '\./usr/bin/[^ ]+' | sed 's/^\.//' > ~/contenu-deb.txt
sudo dpkg -i /srv/paquets/cs-outils_*_all.deb > /dev/null
#@ 13.6
#? `dpkg -I` affiche la ligne `Depends` de cs-rapport : le paquet exigé et sa version minimale, tirés au sort à la mise en place (cs-base ou cs-commun, 1.2 ou 2.0…) ; contrairement à apt, dpkg ne va jamais chercher les dépendances lui-même.
#? Le piège est de prendre le premier fichier venu, ou celui qu'a installé un camarade : il faut le bon paquet, dans une version au moins égale au minimum exigé (`dpkg-deb -f fichier Version` lit la version d'un .deb).
#? Installer les deux fichiers dans la même commande `dpkg -i` permet à dpkg de les configurer ensemble.
#? Variante valable : installer d'abord la dépendance, puis réinstaller cs-rapport ou terminer sa configuration avec `sudo dpkg --configure -a`.
dpkg -I /srv/paquets/cs-rapport_2.0_all.deb | grep Depends
# « paquet (>= version) » : on cherche parmi les .deb livrés une version suffisante de ce paquet
dep=$(dpkg-deb -f /srv/paquets/cs-rapport_2.0_all.deb Depends)
nom=${dep%% *}
min=$(echo "$dep" | grep -oE '[0-9][0-9.]*')
for f in /srv/paquets/"$nom"_*_all.deb; do
    dpkg --compare-versions "$(dpkg-deb -f "$f" Version)" ge "$min" && bon=$f
done
sudo dpkg -i "$bon" /srv/paquets/cs-rapport_2.0_all.deb > /dev/null
#@ 13.7
#? `apt purge` désinstalle le programme et supprime aussi ses fichiers de configuration, comme /etc/cs-ancien.conf.
#? Le piège est `apt remove` : le paquet reste alors dans `dpkg -l` avec l'état `rc`, programme retiré mais configuration conservée.
#? `sudo dpkg -P cs-ancien` est l'équivalent avec dpkg, et un `purge` rattrape aussi un paquet déjà laissé à l'état `rc`.
sudo apt-get purge -y -qq cs-ancien > /dev/null
dpkg -l cs-ancien 2>&1 | tail -n1
#@ 13.8
#? Sur Ubuntu récent, /bin est un lien vers /usr/bin : un même programme a deux chemins, mais dpkg ne connaît que celui sous lequel le paquet l'a installé.
#? `which` renvoie le chemin sous /usr/bin, d'où le « no path found » ; en interrogeant `dpkg -S /bin/nom`, on obtient le bon paquet.
#? Variante valable : chercher un simple motif, comme `dpkg -S bin/nom`, puis ne garder que le nom du paquet avant les deux-points.
#? La commande de la question est tirée au sort : la vôtre peut être différente de celle du corrigé.
c=$(grep -oE 'commande [a-z]+' ~/paquets/question-bin.txt | cut -d' ' -f2)
dpkg -S /usr/bin/$c || true
dpkg -S /bin/$c | cut -d: -f1 > ~/paquet-bin.txt
#@ 13.9
#? dpkg garde une empreinte de chaque fichier installé : `dpkg -V paquet` signale ceux dont le contenu a changé, avec un 5 dans la troisième colonne.
#? Chaque ligne de `dpkg -V` commence par des indicateurs : le corrigé ne garde que le dernier champ, le chemin complet, car le fichier ne doit contenir que lui.
#? Réinstaller le même `.deb` avec `sudo dpkg -i` remet les fichiers d'origine ; `dpkg -V` ne doit ensuite plus rien afficher.
#? Le fichier modifié est tiré au sort par la mise en place : ce n'est pas forcément le même que chez un camarade.
dpkg -V cs-supervision
dpkg -V cs-supervision | awk '{print $NF}' > ~/fichier-modifie.txt
sudo dpkg -i /srv/paquets/cs-supervision_1.0_all.deb > /dev/null
''',
    14: r'''
#@ 14.1
#? Le point de montage à relever est tiré au sort (/, /dev/shm, /proc ou /dev/pts) : lisez-le dans `~/inventaire-montage.txt`, la réponse d'un camarade ne vaut pas forcément pour vous.
#? `df -T point` ajoute une colonne Type : sur la deuxième ligne, c'est le type du système de fichiers monté à cet endroit.
#? Le piège est de répondre « ext4 » par habitude : la racine d'un conteneur est souvent en overlay, /proc est un système de fichiers virtuel (proc), /dev/shm un tmpfs en mémoire.
#? `findmnt -n -o FSTYPE point` donne la même information, sans en-tête.
p=$(grep -oE '/[^ ]*$' ~/inventaire-montage.txt)
df -T "$p" | awk 'NR==2{print $2}' > ~/fs-type.txt
#@ 14.2
#? `du -s` affiche l'espace total occupé par chaque dossier, en blocs de 1 Kio ; `sort -n` les classe et `tail -1` garde le plus gros.
#? Le piège est de trier des tailles lisibles comme `12M` et `900K` avec `sort -n`, qui ignore les unités : utilisez `du -sh … | sort -h` si vous préférez l'affichage lisible.
#? `ls -l` ne convient pas : il affiche la taille de l'entrée du dossier, pas celle de son contenu.
#? Le dossier le plus gros est tiré au sort ; le nom seul ou le chemin complet sont tous deux acceptés.
du -s /srv/data/* | sort -n | tail -1 | cut -f2 > ~/plus-gros.txt
#@ 14.3
#? `du -s` n'affiche qu'un total, et `-m` fixe l'unité au Mio, arrondie au supérieur comme le demande l'énoncé ; `cut -f1` garde le nombre.
#? Sans `-s`, du affiche une ligne par sous-dossier, et le total n'est que la dernière ligne.
#? Le piège est `du -sh`, dont l'unité change selon la taille et qui affiche parfois une décimale : `-m` donne toujours le même format.
#? Le nombre seul est attendu, mais un suffixe `M` ou `Mio` est toléré ; la taille dépend des fichiers générés au hasard pour vous.
du -sm /srv/data | cut -f1 > ~/taille-data.txt
#@ 14.4
#? `blkid` lit l'UUID et le type d'un système de fichiers, même dans un fichier image ; `-o export` les présente sous la forme `UUID=…` et `TYPE=…`, que `eval` transforme en variables.
#? La ligne a six champs : la source `UUID=…`, le point de montage, le type, les options, dump à 0 et pass à 2 pour un disque vérifié après la racine.
#? L'option `nofail` laisse le serveur démarrer si le disque est absent ; le piège est `noauto`, qui empêcherait aussi le montage automatique quand il est branché.
#? `nofail` seul, sans `defaults`, est accepté aussi : les autres options gardent leur valeur par défaut ; des options comme `ro` ou `noexec` les changeraient.
#? Autre piège : désigner le disque par /dev/sdX, un nom qui dépend de l'ordre de détection des disques.
#? L'UUID est tiré au sort lors de la mise en place : le vôtre est forcément différent ; `blkid -s UUID -o value fichier` l'affiche seul si besoin.
sudo mkdir -p /mnt/usb
# blkid lit l'UUID et le type, même dans un fichier image ; nofail : le démarrage continue si le disque est absent
eval "$(blkid -o export /srv/disques/usb-sauvegarde.img)"
echo "UUID=$UUID  /mnt/usb  $TYPE  defaults,nofail  0  2" > ~/fstab-usb.txt
#@ 14.5
#? Le joker `*` ignore les noms qui commencent par un point : `du -s dossier/*` ne voit pas le dossier caché, qui occupe pourtant l'essentiel de la place.
#? Le motif `.[!.]*` désigne les noms cachés sans attraper `.` ni `..` ; avec `.*`, selon la version de bash, `..` (donc tout /srv) pourrait sortir en tête.
#? Variante valable : `du -h -d 1 /srv/stockage`, qui liste tous les sous-dossiers, cachés compris.
#? Le nom du dossier caché est tiré au sort ; la réponse attendue est son chemin complet.
# Le joker * ignore les dossiers cachés : on les ajoute avec .[!.]*
du -s /srv/stockage/* /srv/stockage/.[!.]* | sort -n | tail -n1 | cut -f2 > ~/fantome.txt
#@ 14.6
#? `du` compte les blocs réellement occupés, alors que `ls -l` affiche la taille annoncée : un fichier creux peut annoncer plusieurs gigaoctets et n'occuper presque rien.
#? Le piège est de se fier à `ls -lh` ou `ls -lS` : l'image la plus « grosse » en apparence est justement un fichier creux.
#? Pour voir la différence, comparez `du -h /srv/vm/*` et `du -h --apparent-size /srv/vm/*`, ou regardez la première colonne de `ls -ls`.
#? Les noms et les tailles sont tirés au sort ; le nom seul ou le chemin complet sont acceptés.
# du compte les blocs réellement occupés ; ls -l affiche la taille annoncée des fichiers creux
du -s /srv/vm/* | sort -n | tail -n1 | cut -f2 | xargs basename > ~/vm-reel.txt
#@ 14.7
#? Chaque fichier consomme un inode, même vide : un disque peut être « plein » d'inodes alors qu'il reste des octets libres, d'où l'erreur « No space left on device ».
#? Il faut donc compter les fichiers de chaque sous-dossier, et non mesurer leur taille : le dossier le plus lourd en octets contient justement très peu de fichiers.
#? Variante valable : `du --inodes -s /srv/sessions/*`, qui compte directement les inodes utilisés par chaque dossier.
#? Le dossier recherché est tiré au sort ; le nom seul ou le chemin complet sont acceptés.
# On compte les fichiers (donc les inodes) de chaque sous-dossier, pas leur taille
for d in /srv/sessions/*/; do echo "$(find "$d" -type f | wc -l) $(basename "$d")"; done | sort -n | tail -n1 | cut -d' ' -f2 > ~/inodes.txt
''',
    15: r'''
#@ 15.1
#? ~/.bashrc est relu à chaque ouverture de terminal : c'est là qu'une définition devient permanente.
#? Le mot `export` est indispensable : sans lui, la variable reste locale au shell et les scripts lancés depuis ce shell ne la voient pas.
#? Le piège est de taper la commande seulement dans le terminal courant : elle disparaît à la fermeture ; pour l'appliquer tout de suite, faites `source ~/.bashrc`.
#? Attention à utiliser `>>` et non `>` : une seule flèche écraserait tout votre .bashrc.
echo 'export PROJET=linux-lab' >> ~/.bashrc
#@ 15.2
#? Un script lançable comme une commande a besoin d'un shebang, du droit d'exécution (`chmod +x`) et d'un dossier présent dans le PATH.
#? Les apostrophes autour de `export PATH="$PATH:$HOME/outils"` empêchent le shell de remplacer les variables au moment du `echo` : elles le seront à chaque ouverture de terminal.
#? Le piège est d'écrire `~/outils` entre guillemets : bash trouverait encore la commande, mais ni sh ni cron ne comprennent ce `~`, d'où l'emploi de `$HOME`.
mkdir -p ~/outils
printf '#!/bin/bash\necho "Bonjour !"\n' > ~/outils/bonjour
chmod +x ~/outils/bonjour
# $HOME et non ~ : entre guillemets, ~ resterait tel quel et seul bash saurait l'interpréter
echo 'export PATH="$PATH:$HOME/outils"' >> ~/.bashrc
#@ 15.3
#? ~/.bashrc est lu de haut en bas et, pour une même définition, la dernière l'emporte : l'alias de Marc, placé en haut, est écrasé par celui d'Ubuntu, plus bas.
#? Il suffit donc d'ajouter votre définition à la fin du fichier, puis d'ouvrir un nouveau terminal ; `grep -n "alias ll" ~/.bashrc` montre toutes les définitions.
#? Variante valable : modifier ou supprimer la ligne d'Ubuntu ; l'ordre des options est libre, `ls -hal` ou `ls -l -a -h` conviennent aussi.
# L'alias de Marc est en haut du fichier ; celui d'Ubuntu, plus bas, l'écrase : la dernière définition gagne
grep -n "alias ll" ~/.bashrc
echo "alias ll='ls -lah'" >> ~/.bashrc
#@ 15.4
#? Un script est un programme à part : il ne reçoit que les variables exportées. `bash -c 'echo $CIBLE'` le montre tout de suite, puis `grep -n -e CIBLE -e BASH_ENV ~/.bashrc` montre pourquoi.
#? La cause est tirée au sort : CIBLE définie sans `export` (on ajoute `export` devant), exportée puis « désexportée » plus loin par un `export -n CIBLE` (on supprime cette ligne), ou exportée mais supprimée par le fichier que `BASH_ENV` fait lire à chaque script (on retire BASH_ENV ou le `unset`).
#? Le piège est de recopier la correction d'un camarade : un `sed` qui ajoute `export` ne sert à rien si la variable est déjà exportée puis retirée plus loin.
#? Ne modifiez pas lancer.sh : le script est identique sur tous les serveurs, et la vérification contrôle qu'il n'a pas changé ; la valeur de CIBLE est propre à votre .bashrc, testez dans un nouveau terminal.
grep -n -e CIBLE -e BASH_ENV ~/.bashrc
# Définie sans export : on l'exporte
sed -i 's/^CIBLE=/export CIBLE=/' ~/.bashrc
# Exportée puis retirée de l'environnement plus loin : on supprime ce retrait
sed -i '/^export -n CIBLE/d' ~/.bashrc
# BASH_ENV fait lire aux scripts un fichier qui supprime CIBLE : on retire cette ligne
sed -i '/^export BASH_ENV=/d' ~/.bashrc
#@ 15.5
#? Le shell cherche les commandes dans les dossiers du PATH, dans l'ordre : un dossier ajouté en tête du PATH de julien fournit un faux sudo qui récolte son mot de passe.
#? Le piège est d'enquêter dans votre propre environnement : il faut interroger un shell interactif de julien, par exemple `sudo -iu julien` puis `type -a sudo`.
#? Il faut supprimer à la fois le faux programme et la ligne de /home/julien/.bashrc qui modifie le PATH : sinon, il suffirait de recréer le dossier pour recommencer.
#? Le `sed` utilise `#` comme délimiteur parce que le chemin contient des `/` ; le nom du dossier caché est tiré au sort, le vôtre diffère donc de celui d'un camarade.
#? En situation réelle, julien devrait aussi changer son mot de passe, puisqu'il a pu être enregistré par le faux sudo.
# Dans un shell interactif de julien, un dossier placé en tête du PATH fournit un faux sudo
f=$(sudo -iu julien bash -ic 'type -P sudo' 2>/dev/null | tail -n1)
echo "$f" > ~/faux-sudo.txt
d=$(dirname "$f")
sudo grep -n "$d" /home/julien/.bashrc
sudo sed -i "\#$d#d" /home/julien/.bashrc
sudo rm -rf "$d"
#@ 15.6
#? sudo n'utilise pas votre PATH mais le sien, `secure_path`, défini dans sa configuration : ~/outils n'y figure pas, d'où « command not found ».
#? La bonne réponse est d'installer une copie appartenant à root dans un dossier de ce PATH, comme /usr/local/bin, sans toucher à la configuration de sudo.
#? Le piège est un lien vers ~/outils/bonjour ou une copie qui vous appartient : vous pourriez alors modifier ce que root exécute, une porte ouverte vers root.
#? `sudo install -m 755 -o root -g root` fait tout en une commande ; `sudo cp` suivi de `sudo chmod 755` convient aussi, car la copie appartient alors à root.
# sudo utilise son propre PATH (secure_path) : on y installe une copie appartenant à root
sudo grep -r secure_path /etc/sudoers /etc/sudoers.d/
sudo install -m 755 -o root -g root ~/outils/bonjour /usr/local/bin/bonjour
sudo bonjour
''',
    16: r'''
#@ 16.1
#? tar enregistre les chemins exactement comme vous les lui donnez : en lançant la commande depuis ~, l'archive contient `archive-test/a.txt` et non `home/etudiant/archive-test/a.txt`.
#? Le piège classique est d'écrire `tar -czf archive-test.tar.gz /home/etudiant/archive-test` : tar retire le `/` initial mais conserve tout le reste du chemin.
#? Autre piège : l'option `f` attend le nom de l'archive juste après elle ; avec `tar -cfz …`, l'archive s'appellerait « z ».
#? Variante tout aussi valable, depuis n'importe quel dossier : `tar -czf ~/archive-test.tar.gz -C ~ archive-test`.
mkdir -p ~/archive-test
touch ~/archive-test/a.txt ~/archive-test/b.txt ~/archive-test/c.txt
cd ~ && tar -czf archive-test.tar.gz archive-test
#@ 16.2
#? L'option `-C` indique à tar dans quel dossier extraire, sans avoir à s'y déplacer.
#? Ce dossier de destination doit exister avant l'extraction : d'où le `mkdir -p` placé juste avant.
#? La vérification compare chaque fichier extrait à l'original : c'est exactement le réflexe à avoir, car une sauvegarde qu'on n'a jamais restaurée ne prouve rien.
#? Variante valable : `cd ~/extraction && tar -xzf ~/archive-test.tar.gz`.
mkdir -p ~/extraction && tar -xzf ~/archive-test.tar.gz -C ~/extraction
#@ 16.3
#? Face à une archive inconnue, on commence toujours par la lister avec `tar -tzf` pour voir sa structure avant d'extraire quoi que ce soit.
#? Vous ne pouvez pas écrire dans /srv/livraison : il faut donc extraire ailleurs, avec `-C` vers un dossier qui vous appartient.
#? Variante sans rien extraire sur le disque : `tar -xzOf /srv/livraison/paquet.tar.gz paquet/docs/LISEZMOI.txt`, l'option `-O` envoyant le membre sur la sortie standard.
#? Le code est tiré au sort à la mise en place : celui de votre environnement est différent de celui qu'aurait obtenu un camarade.
tar -tzf /srv/livraison/paquet.tar.gz
mkdir -p /tmp/livraison && tar -xzf /srv/livraison/paquet.tar.gz -C /tmp/livraison
cat /tmp/livraison/paquet/docs/LISEZMOI.txt > ~/code-livraison.txt
#@ 16.4
#? Par défaut, `gzip fichier` remplace le fichier par sa version compressée : l'original disparaît, c'est le piège de cet exercice.
#? L'option `-k` (keep) conserve l'original à côté du fichier `.gz`.
#? Variante équivalente : `gzip -c ~/compress-me.txt > ~/compress-me.txt.gz`, où `-c` écrit le résultat sur la sortie standard sans toucher au fichier d'origine.
echo "du contenu à compresser" > ~/compress-me.txt
gzip -k ~/compress-me.txt
#@ 16.5
#? Comme tar, zip enregistre les chemins tels qu'on les lui donne : on se place donc dans ~ pour obtenir `archive-test/a.txt`.
#? Sans l'option `-r`, zip n'ajoute que l'entrée du dossier lui-même, sans descendre dans son contenu.
#? L'option `-q` rend simplement la commande silencieuse ; `unzip -l ~/backup.zip` permet de vérifier le contenu de l'archive.
cd ~ && zip -qr backup.zip archive-test
#@ 16.6
#? tar sait extraire un seul membre, à condition de le désigner par son chemin exact tel qu'il est stocké dans l'archive : on le cherche d'abord avec `tar -tzf … | grep`.
#? Le piège est le fichier voisin `tarifs-2026-brouillon.csv` : un simple `grep tarifs-2026` renvoie les deux, d'où le motif ancré `/tarifs-2026\.csv$`.
#? tar recrée l'arborescence du membre (par exemple `compta/2026/referentiels/`) dans ~/restauration ; c'est accepté, car seul compte le fait qu'il n'y ait qu'un seul fichier, et que ce soit le bon.
#? Variantes valables : ajouter `--strip-components=3` pour déposer le fichier directement dans ~/restauration, ou utiliser `-O` avec une redirection vers `~/restauration/tarifs-2026.csv`.
#? L'arborescence de la sauvegarde est tirée au sort à la mise en place : la commande exacte d'un camarade échouerait chez vous (« Not found in archive »), il faut lire le chemin dans votre archive.
# Le membre s'extrait par son chemin exact dans l'archive (attention au brouillon au nom voisin)
m=$(tar -tzf /srv/sauvegardes/compta-2026-09-28.tar.gz | grep '/tarifs-2026\.csv$')
mkdir -p ~/restauration
tar -xzf /srv/sauvegardes/compta-2026-09-28.tar.gz -C ~/restauration "$m"
#@ 16.7
#? Une empreinte SHA-256 change dès qu'un seul octet du fichier change : recalculer les empreintes et les comparer à la liste fournie suffit à repérer les archives abîmées.
#? `sha256sum -c SHA256SUMS` fait cette comparaison et affiche `OK` ou `FAILED` pour chaque fichier ; il faut le lancer depuis /srv/livraison2, car la liste contient des noms relatifs.
#? On ne garde ensuite que les lignes qui ne se terminent pas par `: OK` et on isole le nom ; `sha256sum -c SHA256SUMS 2>/dev/null | grep FAILED | cut -d: -f1` convient tout autant.
#? Les deux lots corrompus sont tirés au sort à la mise en place : vos numéros peuvent différer de ceux d'un autre environnement.
cd /srv/livraison2 && sha256sum -c SHA256SUMS 2>/dev/null | grep -v ': OK$' | cut -d: -f1 > ~/corrompues.txt
#@ 16.8
#? Sous Linux, l'extension n'est qu'une partie du nom : `file` examine le contenu et révèle le vrai format de chaque fichier.
#? Ici, `rapport.zip` est en réalité un tar compressé avec gzip, `photos.tar.gz` un zip et `notes.gz` un tar non compressé : chacun s'ouvre avec l'outil de son vrai format.
#? `tar -xf` reconnaît seul la compression, et `unzip` se moque de l'extension : il suffit de choisir le bon outil.
#? On extrait dans un dossier temporaire (`mktemp -d`), car on ne peut pas écrire dans /srv/mystere.
#? Les trois mots secrets sont tirés au sort ; l'ordre des lignes dans ~/secrets.txt n'a pas d'importance pour la vérification.
# file révèle le vrai format de chaque fichier, quelle que soit son extension
file /srv/mystere/*
d=$(mktemp -d)
tar -xf /srv/mystere/rapport.zip -C "$d"        # en réalité une archive tar compressée (gzip)
unzip -q /srv/mystere/photos.tar.gz -d "$d"     # en réalité une archive zip
tar -xf /srv/mystere/notes.gz -C "$d"           # en réalité une archive tar non compressée
cat "$d"/*/secret.txt > ~/secrets.txt
#@ 16.9
#? L'option `--exclude` écarte, au moment de la création, tout fichier ou dossier dont le nom correspond au motif.
#? Ces options doivent être placées avant le dossier à archiver : tar ne les applique qu'aux noms qui les suivent.
#? Mettez le motif `'*.log'` entre apostrophes : sans elles, le shell pourrait le remplacer lui-même par les fichiers .log du dossier courant.
#? Vérifiez toujours le résultat avec `tar -tzf ~/boutique.tar.gz` : aucune ligne ne doit contenir node_modules, .git ou .log.
cd ~ && tar -czf boutique.tar.gz --exclude=node_modules --exclude=.git --exclude='*.log' projet-boutique
tar -tzf ~/boutique.tar.gz
''',
    17: r'''
#@ 17.1
#? Deux éléments font d'un fichier texte un script qu'on lance directement : le shebang `#!/bin/bash` sur la toute première ligne, et le droit d'exécution donné par `chmod +x`.
#? Le corrigé écrit le fichier avec un heredoc ; vous pouvez tout aussi bien l'écrire avec nano ou vim.
#? Le piège est le texte affiché : la vérification exige exactement `Bonjour depuis mon script !`, espace avant le point d'exclamation compris.
cat > ~/hello.sh <<'EOF'
#!/bin/bash
echo "Bonjour depuis mon script !"
EOF
chmod +x ~/hello.sh
#@ 17.2
#? Le script doit exécuter `date`, `whoami` et `pwd` à chaque lancement : c'est le principe même d'un script, qui calcule au lieu de recopier un résultat.
#? Le piège est d'écrire en dur le résultat obtenu dans votre terminal : la vérification lance le script sous un autre compte et depuis un autre dossier.
#? Variantes valables : `id -un` à la place de `whoami`, ou `echo "$PWD"` à la place de `pwd`.
cat > ~/info-system.sh <<'EOF'
#!/bin/bash
date
whoami
pwd
EOF
chmod +x ~/info-system.sh
#@ 17.3
#? `$#` donne le nombre d'arguments : s'il vaut 0, on écrit l'usage sur la sortie d'erreur avec `>&2` et on sort avec un code non nul (`exit 1`).
#? Le test `-e` accepte les fichiers comme les dossiers ; avec `-f`, un dossier serait déclaré ABSENT à tort.
#? Les guillemets autour de `"$1"` sont indispensables : sans eux, un chemin contenant une espace est coupé en plusieurs mots et le test échoue.
#? Sans argument, rien ne doit s'afficher sur la sortie standard : le message d'usage passe uniquement par la sortie d'erreur.
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
#? `seq 1 "$1"` produit la suite des nombres de 1 à N, que la boucle `for` parcourt pour créer chaque fichier.
#? Le piège est `{1..$1}` : l'expansion des accolades a lieu avant celle des variables, elle ne fonctionne donc pas avec un nombre contenu dans une variable.
#? Autre piège : un chemin relatif comme `users/` ; la vérification lance le script depuis /tmp, d'où `~/users` (ou `$HOME/users`) dans le script.
#? Variante valable : `for ((i = 1; i <= $1; i++))`.
#? La vérification choisit un nombre au hasard à chaque essai : le script doit fonctionner pour n'importe quelle valeur.
cat > ~/create-users.sh <<'EOF'
#!/bin/bash
mkdir -p ~/users
for i in $(seq 1 "$1"); do
    touch ~/users/user$i.txt
done
EOF
chmod +x ~/create-users.sh
#@ 17.5
#? `find "$1" -maxdepth 1 -type f -name '*.txt'` ne retient que les fichiers placés directement dans le dossier, puis `wc -l` les compte.
#? Le dossier de test contient un piège : un sous-dossier nommé `vieux.txt` et un fichier .txt dans un sous-dossier ; `ls "$1"/*.txt | wc -l` compterait le premier.
#? Les guillemets autour de `"$1"` protègent les noms comme « Factures mars », et ceux autour de `'*.txt'` empêchent le shell de développer le motif à la place de find.
#? Variante valable : une boucle `for f in "$1"/*.txt` avec un compteur, qui ne compte que si `[ -f "$f" ]` est vrai.
cat > ~/compteur.sh <<'EOF'
#!/bin/bash
find "$1" -maxdepth 1 -type f -name '*.txt' | wc -l
EOF
chmod +x ~/compteur.sh
#@ 17.6
#? Le joker `"$1"/IMG_*.JPG` développe les noms dans l'ordre alphabétique : il suffit de les parcourir avec un compteur.
#? `printf -v nom 'photo-%03d.jpg' "$i"` fabrique le nom avec un numéro sur trois chiffres (001, 002…).
#? Le piège est le fichier « (copie) » dont le nom contient une espace : `for f in $(ls …)` le couperait en morceaux, alors que le joker et les guillemets le gardent entier.
#? Le `--` de `mv` signale la fin des options, et `[ -e "$f" ] || continue` évite une erreur si aucun fichier ne correspond au motif.
#? La vérification génère un dossier de photos différent à chaque essai : le script ne doit dépendre d'aucun nom particulier.
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
#? awk découpe chaque ligne sur le `;` (`-F';'`), saute l'en-tête (`NR > 1`) et additionne les montants dans un tableau indexé par le nom du client.
#? Le tri se fait sur le deuxième champ, numériquement et en ordre décroissant : `sort -k2,2nr`.
#? Le piège est `sort -rn` sans préciser le champ : la ligne commence par le nom du client, et le tri ne porte alors pas sur les totaux.
#? Le séparateur affiché entre le client et le total peut être une espace, un `;` ou un `:` : la vérification accepte les trois.
cat > ~/totaux.sh <<'EOF'
#!/bin/bash
awk -F';' 'NR > 1 { t[$1] += $2 } END { for (c in t) print c, t[c] }' "$1" | sort -k2,2nr
EOF
chmod +x ~/totaux.sh
#@ 17.8
#? Premier bogue : `DEST = ~/marc/copies` ; en Bash, une affectation ne tolère aucune espace autour du `=`.
#? Deuxième et troisième bogues : `[$# -eq 0]` exige des espaces à l'intérieur des crochets, et `for f in $(ls …)` coupe les noms à chaque espace ; on parcourt directement `"$1"/*.conf`, entre guillemets.
#? Quatrième bogue : `$DEST/$f.bak` contient le chemin complet du fichier source ; `basename` n'en garde que le nom.
#? Cinquième bogue : `N=$N+1` produit le texte « 0+1+1… » ; le calcul entier s'écrit `N=$((N + 1))`.
#? Pour trouver ce genre d'erreur, `bash -x script.sh dossier-de-test` affiche chaque commande réellement exécutée, variables remplacées.
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
#? `crontab -e` ouvre votre table personnelle ; le corrigé ajoute la ligne sans éditeur, en recombinant `crontab -l` et la nouvelle ligne envoyées à `crontab -`.
#? Cinq étoiles signifient « chaque minute » ; `*/1 * * * *` ou `0-59 * * * *` sont aussi acceptés.
#? Utilisez un chemin absolu vers tick.log : cron ne lance pas la tâche dans votre dossier courant.
(crontab -l 2>/dev/null; echo '* * * * * date >> /home/etudiant/tick.log') | crontab -
#@ 18.5
#? Dans une ligne de crontab, un `%` non échappé marque la fin de la commande : la suite est envoyée sur son entrée standard, et la commande reçoit un format tronqué.
#? `grep CRON /var/log/syslog` montre la commande réellement lancée par cron, coupée au premier `%`.
#? La commande de Julien est tirée au sort (`date +%H:%M`, `date '+%H:%M'`, `date +%R`, ou un `printf` qui contient plusieurs `%`) : il faut échapper chaque `%` de la ligne, en écrivant `\%` ; `crontab -e` est tout aussi valable que le sed du corrigé.
#? Dans le corrigé, `\\%` est doublé parce que l'antislash doit survivre au passage dans sed : c'est bien `\%` qui arrive dans la crontab.
# cron coupe la commande au premier % (la suite devient l'entrée standard de la commande) : on écrit \% partout sur la ligne
grep CRON /var/log/syslog | tail -n 3
crontab -l | grep heure.log
crontab -l | sed '/heure\.log/ s/%/\\%/g' | crontab -
#@ 18.6
#? cron lance les tâches avec `/bin/sh` et un environnement minimal : il ne lit pas ~/.bashrc, donc ni la variable PROJET ni votre PATH étendu ne sont connus.
#? On peut définir des variables en tête de crontab : `PROJET=linux-lab` et un PATH complet qui inclut ~/outils, où se trouve `bonjour`.
#? Attention : dans une crontab, la valeur d'une variable n'est pas interprétée par un shell ; écrivez le chemin en entier (`/home/etudiant/outils`), sans `~` ni `$HOME`.
#? Variante valable : modifier le script lui-même, en y définissant PROJET et en appelant bonjour par son chemin absolu.
# cron ne lit pas ~/.bashrc : on définit PROJET et un PATH complet en tête de crontab
(echo 'PROJET=linux-lab'; echo 'PATH=/home/etudiant/outils:/usr/local/bin:/usr/bin:/bin'; crontab -l) | crontab -
#@ 18.7
#? Sans serveur de messagerie, cron jette la sortie des tâches : avant de réparer, il faut la capturer avec `>> /var/log/export-compta.log 2>&1`.
#? L'ordre des redirections compte : d'abord la sortie standard vers le journal, puis `2>&1` pour que les erreurs suivent le même chemin.
#? `>> /var/log/export-compta.log 2>> /var/log/export-compta.log` convient aussi ; en revanche `&>>` n'existe pas pour /bin/sh, le shell de cron.
#? La vérification exige que le journal contienne l'erreur de la tâche : il faut donc laisser cron s'exécuter une fois avant de corriger.
#? La cause est tirée au sort, et seule l'erreur capturée la donne : dossier d'export absent (on le crée), fichier ordinaire à la place de ce dossier (on le remplace par un dossier), configuration absente (on la recrée à partir du modèle indiqué) ou outil non exécutable (`chmod 755`).
#? Le piège est d'appliquer la correction d'un camarade sans lire son propre journal : un `mkdir` ne sert à rien si c'est la configuration qui manque.
#? Une fois la cause corrigée, la tâche écrit « export OK » dans le journal à l'exécution suivante.
# D'abord voir ce que dit la tâche : sortie et erreurs ajoutées à un journal
printf '# Export de la comptabilité (toutes les minutes pour le lab)\n* * * * * root /usr/local/sbin/export-compta >> /var/log/export-compta.log 2>&1\n' | sudo tee /etc/cron.d/export-compta > /dev/null
for i in $(seq 90); do sudo grep -q ERREUR /var/log/export-compta.log 2>/dev/null && break; sleep 1; done
sudo cat /var/log/export-compta.log
# On corrige la cause qu'indique l'erreur
err=$(sudo grep ERREUR /var/log/export-compta.log | tail -n1)
case $err in
    *"pas un dossier"*) sudo rm -f /srv/compta/exports; sudo mkdir -p /srv/compta/exports ;;
    *configuration*) sudo cp /usr/share/doc/export-compta/export-compta.conf.exemple /etc/export-compta.conf ;;
    *exécutable*) sudo chmod 755 /usr/local/lib/export-compta/horodatage ;;
    *dossier*introuvable*) sudo mkdir -p /srv/compta/exports ;;
esac
#@ 18.8
#? `flock` pose un verrou sur un fichier avant de lancer la commande : tant que la première synchronisation tourne, le verrou reste pris.
#? L'option `-n` est essentielle : sans elle, la seconde exécution attendrait la libération du verrou au lieu d'abandonner, et les tâches continueraient de s'empiler.
#? Le fichier de verrou peut porter n'importe quel nom, pourvu que toutes les exécutions utilisent le même ; /run/lock est l'emplacement habituel.
#? La tâche doit rester en root : le sixième champ de la ligne ne change pas.
# flock -n : si le verrou est déjà pris, l'exécution suivante abandonne aussitôt
printf '# Synchronisation du catalogue\n* * * * * root flock -n /run/lock/sync-catalogue.lock /usr/local/sbin/sync-catalogue\n' | sudo tee /etc/cron.d/sync-catalogue > /dev/null
#@ 18.2
#? Dans /etc/cron.d, chaque ligne comporte un sixième champ, l'utilisateur qui exécute la commande : ici `root`.
#? Le piège de sécurité : ~/hello.sh vous appartient, donc root exécuterait un fichier que vous pouvez modifier ; on planifie une copie installée par `install -o root -m 755` dans /usr/local/sbin.
#? Le fichier de cron.d doit appartenir à root, ne pas être modifiable par le groupe ni les autres, et se terminer par un retour à la ligne, ce que `echo … | sudo tee` garantit.
#? Variante valable : copier le script dans /usr/local/bin, qui appartient aussi à root, tant que la commande planifiée est un chemin absolu.
# root ne doit exécuter qu'un fichier que seul root peut modifier : copie dans un dossier système
sudo install -m 755 -o root -g root ~/hello.sh /usr/local/sbin/hello
echo '0 2 * * * root /usr/local/sbin/hello' | sudo tee /etc/cron.d/backup-lab > /dev/null
#@ 18.3
#? run-parts ignore les fichiers dont le nom contient un point : `nettoyage-tmp.sh` ne serait jamais lancé, d'où le nom sans extension.
#? Le script doit aussi être exécutable (`chmod 755`), et `run-parts --test /etc/cron.daily` permet de vérifier qu'il sera bien pris en compte.
#? Le motif `/tmp/*.tmp` ne touche que les fichiers .tmp ; un `rm -rf /tmp/*` supprimerait aussi les fichiers d'autres applications.
#? Les apostrophes autour du `printf` empêchent le shell de développer `/tmp/*.tmp` au moment de l'écriture : c'est dans le script que le motif doit rester.
#? Variante valable dans le script : `find /tmp -maxdepth 1 -type f -name '*.tmp' -delete`.
# Pas de « .sh » : run-parts ignore les noms contenant un point
printf '#!/bin/bash\nrm -f /tmp/*.tmp\n' | sudo tee /etc/cron.daily/nettoyage-tmp > /dev/null
sudo chmod 755 /etc/cron.daily/nettoyage-tmp
run-parts --test /etc/cron.daily
#@ 18.4
#? Les cinq champs sont, dans l'ordre : minute, heure, jour du mois, mois et jour de la semaine.
#? Ligne 1 : le pas `*/10` porte sur les minutes et la plage `8-18` sur les heures, ce qui donne une dernière exécution à 18h50.
#? La vérification compare les instants désignés et non le texte : `0-59/10` pour les minutes, `mon-fri` pour les jours, `sun` ou `7` pour le dimanche sont acceptés.
#? Ligne 4 : `1,4,7,10` peut aussi s'écrire `jan,apr,jul,oct` ou `1-12/3`.
printf '%s\n' '*/10 8-18 * * 1-5' '45 23 1,15 * *' '0 0 * * 0' '0 6 1 1,4,7,10 *' > ~/cron-quiz.txt
#@ 18.1
#? Cette seconde partie sert au banc de test : elle attend simplement que cron ait exécuté la tâche au moins deux fois.
#? De votre côté, il suffit de patienter deux minutes, puis de regarder `cat ~/tick.log` (et `grep CRON /var/log/syslog`) avant de valider.
# Attendre que cron ait exécuté la tâche au moins deux fois
for i in $(seq 150); do [ "$(sort -u ~/tick.log 2>/dev/null | wc -l)" -ge 2 ] && break; sleep 2; done
''',
    19: r'''
#@ 19.1
#? Le bloc `{ cmd1; cmd2; }` regroupe plusieurs commandes pour rediriger leur sortie d'un seul coup vers le rapport.
#? `>` remplace le fichier à chaque exécution, alors que `>>` empilerait les rapports : c'est le piège que la vérification contrôle en lançant le script deux fois.
#? Le chemin `$HOME/rapport-systeme.txt` est absolu : la vérification lance le script depuis /tmp, où un chemin relatif créerait le rapport au mauvais endroit.
#? Variante valable : `date > "$HOME/rapport-systeme.txt"` suivi de `>>` pour les commandes suivantes.
cat > ~/rapport.sh <<'EOF'
#!/bin/bash
{ date; df -h; free -h; uptime; } > "$HOME/rapport-systeme.txt"
EOF
chmod +x ~/rapport.sh
#@ 19.2
#? La colonne RSS indique la mémoire réellement occupée par chaque processus, en Kio : `ps` sait trier sur cette colonne avec `--sort=-rss`.
#? `--no-headers` supprime la ligne de titre, sinon `head -1` renverrait l'en-tête au lieu du premier processus.
#? Variantes valables : `ps aux --sort=-rss | head`, ou `top` puis la touche `M`, en lisant le PID à l'œil.
#? Le PID dépend de votre conteneur : celui de votre environnement est différent de celui du corrigé.
ps -eo pid,rss --sort=-rss --no-headers | head -1 | awk '{print $1}' > ~/gourmand.txt
#@ 19.3
#? `find -printf '%s %p\n'` affiche la taille en octets et le chemin de chaque fichier ; un tri numérique puis `tail -n1` donne le plus gros.
#? Le piège est de chercher le plus gros dossier avec `du -s` : on demande ici un fichier.
#? `sudo` est nécessaire, car certains dossiers de /var ne sont lisibles que par root ; `-xdev` évite de descendre dans d'autres systèmes de fichiers montés.
#? Variantes valables : `sudo find /var -type f -size +10M` ou `sudo du -ah /var | sort -h | tail`.
#? Le nom du fichier est tiré au sort à la mise en place : il diffère d'un environnement à l'autre.
sudo find /var -xdev -type f -printf '%s %p\n' 2>/dev/null | sort -n | tail -n1 | cut -d' ' -f2- > ~/plus-gros-var.txt
#@ 19.4
#? `free` lit /proc, qui décrit la mémoire de l'hôte tout entier : il ignore la limite imposée au conteneur.
#? Cette limite est appliquée par le noyau grâce aux cgroups et se lit dans `/sys/fs/cgroup/memory.max` (cgroup v2) ou `/sys/fs/cgroup/memory/memory.limit_in_bytes` (cgroup v1).
#? La valeur est en octets : on la divise par 1 048 576 pour obtenir des Mio.
#? Le nombre attendu dépend de la configuration de votre conteneur, pas d'un tirage au sort.
# free montre la mémoire de l'hôte ; la limite du conteneur est dans les cgroups
f=/sys/fs/cgroup/memory.max; [ -r $f ] || f=/sys/fs/cgroup/memory/memory.limit_in_bytes
echo $(( $(cat $f) / 1048576 )) > ~/limite-memoire.txt
#@ 19.5
#? `top` mesure la consommation instantanée du processeur ; le corrigé prend la deuxième mesure, car la première porte sur toute la durée de vie des processus.
#? `renice -n 15 -p PID` change la gentillesse d'un processus déjà lancé, alors que `nice` ne sert qu'à lancer un nouveau programme.
#? Le processus appartient à root : sans `sudo`, renice est refusé.
#? Le piège est de tuer le processus : la vérification exige qu'il tourne encore, seule sa priorité devait baisser.
#? Le nom du processus est tiré au sort parmi plusieurs possibles : le vôtre peut différer de celui qu'on trouve en suivant le corrigé ailleurs.
# top mesure la consommation instantanée (2e mesure, triée par %CPU)
pid=$(top -b -d 2 -n 2 -o %CPU | awk '/^ *PID/ {n++; next} n == 2 && /^ *[0-9]/ {print $1; exit}')
ps -o comm= -p "$pid" > ~/cpu.txt
sudo renice -n 15 -p "$pid"
#@ 19.6
#? Un fichier supprimé mais encore ouvert n'est pas libéré : son espace reste occupé tant que le processus garde le fichier ouvert, et df ne baisse pas.
#? `sudo lsof +L1` liste les fichiers dont le nombre de liens est tombé à 0, avec le PID et le numéro de descripteur (colonne FD) qui les retiennent.
#? Le lien `/proc/PID/fd/N` donne encore accès au fichier : `truncate -s 0` le vide sans arrêter le processus.
#? Variante valable : `sudo sh -c ': > /proc/PID/fd/3'` ; attention, `sudo : > fichier` échouerait, car la redirection serait faite par votre shell et non par root.
#? Le piège est de tuer le processus : l'espace serait libéré, mais la boutique perdrait son service, et la vérification le refuse.
# Le fichier supprimé est toujours ouvert : lsof +L1 le montre, /proc/PID/fd permet de le vider
read -r pid fd < <(sudo lsof +L1 2>/dev/null | awk '/cache-vignettes/ {print $2, $4; exit}')
echo "$pid" > ~/cache-pid.txt
sudo truncate -s 0 "/proc/$pid/fd/${fd%%[a-z]*}"
#@ 19.7
#? Un zombie est un processus déjà terminé : aucun signal ne peut le tuer, pas même `kill -9`.
#? Il attend que son parent lise son code de retour ; `ps -eo pid,ppid,stat,comm` montre l'état `Z` et le PPID qui désigne ce parent.
#? Quand on arrête le parent, les zombies sont confiés au processus n° 1, qui récupère leur fin et les fait disparaître.
#? Le PID du parent dépend de votre conteneur : il diffère de celui qu'on obtiendrait ailleurs.
# Un zombie ne se tue pas : on arrête son parent, et le processus n°1 récupère les zombies
ps -eo pid,ppid,stat,comm | awk '$3 ~ /^Z/'
pp=$(ps -eo ppid=,stat= | awk '$2 ~ /^Z/ {print $1; exit}')
echo "$pp" > ~/parent-zombies.txt
sudo kill "$pp"
sleep 1
''',
    20: r'''
#@ 20.1
#? `logger` envoie un message au journal système, et l'option `-t` choisit l'étiquette qui le précède.
#? On vérifie ensuite avec `sudo grep cimes-backup /var/log/syslog` ; le `sleep 1` du corrigé laisse à rsyslog le temps d'écrire.
#? Le message doit être exactement `Test de journalisation`, sans ponctuation ajoutée.
logger -t cimes-backup "Test de journalisation"
sleep 1
#@ 20.2
#? Le piège : certaines lignes de niveau INFO contiennent le mot ERROR (« aucune ERROR bloquante ») ; on compte donc le niveau `[ERROR]`, pas le mot.
#? Les crochets doivent être échappés : `grep -c '[ERROR]'` serait compris comme « une lettre parmi E, R et O » et compterait presque toutes les lignes.
#? Variante valable : `sudo grep -cF '[ERROR]' /var/log/app/app.log`, où `-F` rend la recherche littérale.
#? Le journal est généré au hasard : le nombre d'erreurs de votre environnement est propre à votre conteneur.
# Piège : certaines lignes INFO contiennent le mot ERROR ; on compte le niveau [ERROR]
sudo grep -c '\[ERROR\]' /var/log/app/app.log > ~/error-count.txt
#@ 20.3
#? Le motif `^2026-03-15 .*\[ERROR\]` combine la date, ancrée au début de la ligne, et le niveau entre crochets échappés.
#? L'ancrage `^` évite les faux positifs : une date qui apparaîtrait ailleurs dans une ligne ne doit pas compter.
#? Variante valable : `sudo grep '^2026-03-15' … | grep -F '[ERROR]'`, qui produit les mêmes lignes dans le même ordre.
#? Les lignes du journal sont générées au hasard : votre fichier diffère de celui d'un autre environnement.
sudo grep '^2026-03-15 .*\[ERROR\]' /var/log/app/app.log > ~/erreurs-15.txt
#@ 20.4
#? Une boucle `for` sur les trois niveaux évite de répéter la même commande, et `"$1"` désigne le fichier passé en argument.
#? On compte `\[NIVEAU\]` entre crochets et en majuscules : les journaux de test contiennent exprès « reprise après une ERROR », « [DEBUG] WARNING ignoré » et « [error] » en minuscules, qui ne doivent pas compter.
#? N'utilisez donc ni `grep -i`, ni le mot seul sans crochets.
#? L'affichage attendu est `INFO: n` ; des espaces autour du deux-points sont tolérés.
cat > ~/log-analyzer.sh <<'EOF'
#!/bin/bash
for niveau in INFO WARNING ERROR; do
    echo "$niveau: $(grep -c "\[$niveau\]" "$1")"
done
EOF
chmod +x ~/log-analyzer.sh
#@ 20.5
#? Un bloc logrotate commence par le motif des fichiers visés, suivi des directives entre accolades : `daily` pour la fréquence, `rotate 7` pour le nombre d'archives, `compress` pour la compression.
#? `missingok` évite une erreur si aucun fichier ne correspond ; l'ordre des directives n'a pas d'importance.
#? `sudo logrotate -d /etc/logrotate.d/app-lab` teste la configuration à blanc, sans rien modifier.
#? `delaycompress` est aussi accepté : la première archive reste alors non compressée, les suivantes le sont.
printf '/var/log/app/*.log {\n    daily\n    rotate 7\n    compress\n    missingok\n}\n' | sudo tee /etc/logrotate.d/app-lab > /dev/null
sudo logrotate -d /etc/logrotate.d/app-lab
#@ 20.6
#? Une même tentative laisse plusieurs lignes dans auth.log (utilisateur invalide, échec PAM, fermeture) : on ne compte que les lignes `Failed password`.
#? `grep -oE 'from [0-9.]+'` isole l'adresse, puis `sort | uniq -c | sort -rn` classe les adresses par nombre d'échecs.
#? Pour les comptes, « invalid user » décale les champs : on prend le mot qui précède « from » plutôt qu'un numéro de champ fixe.
#? L'adresse de l'attaquant, le nombre de tentatives et les comptes visés sont tirés au sort : vos valeurs diffèrent de celles d'un autre environnement.
# Une tentative laisse plusieurs lignes : on ne compte que « Failed password »
A=/var/log/lab/auth.log
read -r n ip < <(sudo grep 'Failed password' $A | grep -oE 'from [0-9.]+' | sort | uniq -c | sort -rn | head -n1 | awk '{print $1, $3}')
echo "$ip $n" > ~/attaquant.txt
# Le compte visé est le mot qui précède « from » (« invalid user » décale les champs)
sudo grep 'Failed password' $A | grep " from $ip port" | awk '{for (i = 1; i < NF; i++) if ($(i + 1) == "from") print $i}' | sort -u > ~/comptes-vises.txt
#@ 20.7
#? Après rotation, les erreurs du 14 mars sont réparties entre `shop.log.2.gz` et `shop.log.1` ; il faut lire toutes les versions, compressées comprises.
#? `zgrep` lit indifféremment les fichiers compressés et non compressés ; `-h` supprime le nom du fichier devant chaque ligne avant le comptage par `wc -l`.
#? Le piège est `zgrep -c`, qui affiche un compte par fichier au lieu d'un total ; autre piège, la ligne INFO « reprise après une ERROR réseau », écartée grâce au motif `\[ERROR\]`.
#? Variante valable : `sudo zcat -f /var/log/boutique/shop.log* | grep -c '^2026-03-14 .*\[ERROR\]'`.
#? Le total est tiré au sort à la mise en place : il est propre à votre environnement.
sudo zgrep -h '^2026-03-14 .*\[ERROR\]' /var/log/boutique/shop.log* | wc -l > ~/erreurs-14.txt
#@ 20.8
#? Le service garde son journal ouvert : après un renommage, il continue d'écrire dans le même fichier, qui s'appelle désormais caisse.log.1.
#? Le bloc `postrotate … endscript` envoie le signal HUP au PID lu dans /run/journal-caisse.pid, et le service rouvre alors un nouveau caisse.log.
#? Variante valable : la directive `copytruncate`, qui copie le journal puis le vide sans le renommer (quelques lignes peuvent se perdre entre la copie et la remise à zéro).
#? Le `kill -HUP` lancé à la main dans le corrigé répare la situation actuelle, où le service écrit déjà dans caisse.log.1.
#? Le piège est d'arrêter ou de redémarrer le service : la vérification exige qu'il tourne toujours après la rotation.
# Le service garde son journal ouvert : après la rotation, on lui demande de le rouvrir (HUP)
printf '/var/log/caisse/caisse.log {\n    daily\n    rotate 5\n    missingok\n    postrotate\n        kill -HUP "$(cat /run/journal-caisse.pid)"\n    endscript\n}\n' | sudo tee /etc/logrotate.d/caisse > /dev/null
sudo kill -HUP "$(cat /run/journal-caisse.pid)"
#@ 20.9
#? rsyslog range les messages selon des règles `facility.niveau destination` : `local3.*`, par exemple, envoie tous les niveaux de local3 vers /var/log/paiement.log.
#? La facility du module est tirée au sort à la mise en place : lisez-la dans /etc/paiement/module.conf. La règle d'un camarade ne capterait pas vos messages, et une règle qui attrape toutes les facilities est refusée (seuls les messages du module sont attendus).
#? La règle se place dans un fichier dont le nom se termine par `.conf` dans /etc/rsyslog.d ; un autre nom serait ignoré.
#? Un simple signal HUP ne relit pas les règles : il faut redémarrer rsyslogd, ce que l'on fait ici avec `pkill` puis `rsyslogd`, faute de systemd dans le conteneur.
#? On teste enfin avec `logger -p FACILITY.info -t paiement "essai"`, puis on lit /var/log/paiement.log.
cat /etc/paiement/module.conf
f=$(sed -n 's/^SYSLOG_FACILITY=//p' /etc/paiement/module.conf)
echo "$f.*    /var/log/paiement.log" | sudo tee /etc/rsyslog.d/30-paiement.conf > /dev/null
# Pas de systemd dans ce conteneur : on arrête puis on relance rsyslogd (HUP ne relit pas les règles)
sudo pkill -x rsyslogd
while pgrep -x rsyslogd > /dev/null; do sleep 0.2; done
sudo rsyslogd
sleep 1
logger -p "$f.info" -t paiement "essai"
''',
    21: r'''
#@ 21.1
#? `ip -4 -o addr show eth0` affiche l'adresse avec la longueur de son préfixe (par exemple 172.18.0.5/16) : on ne garde que la partie avant le « / » pour `~/mon-ip.txt`.
#? L'adresse du réseau s'obtient en mettant à 0 les bits réservés à la machine ; la table de routage (`ip route`) l'affiche directement sur la ligne du réseau local de eth0.
#? Piège classique : écrire l'adresse de la machine suivie du préfixe (172.18.0.5/16) au lieu de l'adresse du réseau (172.18.0.0/16).
#? Ces adresses dépendent du réseau Docker de votre conteneur : celles que vous voyez peuvent différer de l'exemple.
ip -4 -o addr show eth0 | awk '{print $4}' | cut -d/ -f1 > ~/mon-ip.txt
# Le réseau local apparaît dans la table de routage (adresse du réseau et longueur du préfixe)
ip route | awk '!/^default/ && / dev eth0 / {print $1; exit}' > ~/reseau.txt
#@ 21.2
#? Pour sortir de ses réseaux, la machine envoie les paquets à sa passerelle : c'est l'adresse qui suit `via` sur la ligne `default` de `ip route`.
#? Piège classique : recopier toute la ligne `default via … dev eth0` ; le fichier ne doit contenir que l'adresse.
#? `ip route show default` n'affiche que cette ligne et convient tout aussi bien.
ip route | awk '/^default/ {print $3}' > ~/passerelle.txt
#@ 21.3
#? `ss -tln` liste les ports TCP en écoute avec leur adresse locale ; `0.0.0.0` (ou `*`) signifie « toutes les interfaces », donc joignable depuis le réseau.
#? Piège classique : retenir un port lié à 127.0.0.x, qui n'est joignable que depuis la machine elle-même.
#? Le numéro de port est tiré au sort à la mise en place : le vôtre diffère sans doute de celui qu'a trouvé la correction.
# Le programme mystère écoute sur 0.0.0.0 ; les ports en 127.0.0.x ne sont joignables que localement
ss -tln | awk '$4 ~ /^0\.0\.0\.0:/ {split($4, a, ":"); print a[2]}' | head -1 > ~/port-mystere.txt
#@ 21.4
#? `getent hosts serveur-local` montre ce que le système résout réellement, et `grep -n serveur-loca /etc/hosts` toutes les lignes en cause : une ancienne adresse (tirée au sort) qui porte aussi ce nom, parfois comme deuxième nom d'une ligne.
#? Quand un nom figure sur plusieurs lignes, les programmes reçoivent toutes les adresses et utilisent en général la première. Selon les serveurs, la ligne de Thomas est en plus mise en commentaire, ou comporte une faute de frappe dans le nom (serveur-locale) : elle n'est alors jamais prise en compte.
#? La correction qui vaut dans tous les cas : ne garder qu'une ligne pour ce nom, `192.168.1.100   serveur-local`, sans ajouter une énième ligne par-dessus les autres.
#? Piège propre au conteneur : `sed -i` échoue sur ce fichier fourni par Docker (« Device or resource busy ») ; `sudo nano /etc/hosts` fonctionne, tout comme la copie par-dessus avec `sudo cp` utilisée ici.
getent hosts serveur-local
grep -n 'serveur-loca' /etc/hosts
# On retire toutes les lignes en cause (périmée, commentée ou mal orthographiée), puis on remet la bonne
grep -v 'serveur-loca' /etc/hosts > /tmp/hosts.new
echo '192.168.1.100   serveur-local' >> /tmp/hosts.new
sudo cp /tmp/hosts.new /etc/hosts
#@ 21.5
#? Les serveurs de /etc/resolv.conf sont interrogés dans l'ordre : un premier serveur injoignable fait attendre chaque résolution plusieurs secondes.
#? Le serveur ajouté par Marc est tiré au sort dans les plages 192.0.2.0/24, 198.51.100.0/24 ou 203.0.113.0/24, réservées à la documentation et jamais routées : c'est lui qu'il faut noter et retirer, en gardant l'autre ligne `nameserver`.
#? Le piège est de recopier l'adresse d'un camarade : lisez votre propre /etc/resolv.conf.
#? Comme pour /etc/hosts, `sed -i` échoue sur ce fichier dans le conteneur : `sudo nano /etc/resolv.conf` est la méthode la plus simple.
cat /etc/resolv.conf
# Le premier serveur appartient à une plage de documentation : il ne peut pas répondre
mort=$(awk '/^nameserver/ {print $2}' /etc/resolv.conf | grep -E '^(192\.0\.2|198\.51\.100|203\.0\.113)\.' | head -n1)
echo "$mort" > ~/dns-injoignable.txt
grep -vx "nameserver $mort" /etc/resolv.conf > /tmp/resolv.new && sudo cp /tmp/resolv.new /etc/resolv.conf
#@ 21.6
#? Dans ce conteneur, `ss -p` ne montre que les processus de root ; en revanche `ss -tlne` indique l'uid propriétaire de chaque socket, que `getent passwd` traduit en nom.
#? `ps -u compte -o pid,args` révèle ensuite le programme qui écoute sur 8081 ; son nom et son propriétaire sont tirés au sort à la mise en place, la réponse d'un camarade ne vaut donc pas pour vous.
#? Piège classique : oublier `sudo` pour le `kill`, alors que le processus appartient à un autre compte ; `sudo pkill -x nom-du-programme` fonctionne aussi.
#? Relancer `appli-caisse` à la fin confirme que le port est bien libéré.
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
#? Un service lié à 127.0.0.1 n'accepte que les connexions venant de la boucle locale : l'adresse de eth0 obtient donc « connection refused » (`ss -tln | grep 8088` le montre).
#? Reste à trouver où cette adresse est fixée : l'en-tête de /usr/local/sbin/mini-web indique qu'il lit /etc/mini-web.conf, puis /etc/mini-web.d/*.conf, puis /etc/default/mini-web. Selon les serveurs, c'est BIND dans le fichier principal, une surcharge dans mini-web.d ou MINIWEB_BIND dans /etc/default.
#? `grep -rn BIND` sur ces trois emplacements montre la valeur qui l'emporte (la dernière lue) ; on la passe à `0.0.0.0` (toutes les interfaces), ou à l'adresse de eth0.
#? Piège classique : corriger le fichier principal alors qu'une surcharge lue ensuite remet 127.0.0.1, ou oublier de redémarrer le service (`sudo mini-web-ctl restart`).
# mini-web n'écoute que sur la boucle locale : où cette adresse est-elle fixée ?
ss -tln | grep 8088
sudo grep -rnE '^(MINIWEB_)?BIND=' /etc/mini-web.conf /etc/mini-web.d /etc/default/mini-web 2>/dev/null
for f in $(sudo grep -rlE '^(MINIWEB_)?BIND=' /etc/mini-web.conf /etc/mini-web.d /etc/default/mini-web 2>/dev/null); do
    sudo sed -i -E 's/^(MINIWEB_)?BIND=.*/\1BIND=0.0.0.0/' "$f"
done
sudo mini-web-ctl restart
#@ 21.8
#? `nc -z` tente une connexion TCP sans rien envoyer : son code de retour indique si quelqu'un accepte les connexions sur ce port.
#? Piège classique : se fier à un serveur qui répond sur un autre port (5433 ou 6432) ; seul le port 5432 compte ici.
#? Autre méthode valable : comparer les adresses en écoute de `ss -tln` avec les correspondances de /etc/hosts.
#? La machine active et les adresses sont tirées au sort à la mise en place : votre réponse peut différer de celle de la correction.
for h in bdd-1 bdd-2 bdd-3 bdd-4 bdd-5; do nc -z -w1 "$h" 5432 2>/dev/null && echo "$h"; done | head -n1 > ~/bdd-active.txt
#@ 21.9
#? `ss -tn` affiche les connexions établies ; avec root, `-p` ajoute le programme et son PID dans `users:((…))`.
#? Piège classique : confondre les deux extrémités ; il faut la connexion dont l'adresse distante (colonne Peer) se termine par :4444, pas le programme qui écoute localement sur ce port.
#? Le PID change à chaque mise en place : c'est celui que vous observez qui compte, et le programme doit ensuite être arrêté avec `sudo kill`.
# Connexion établie dont l'adresse distante se termine par :4444
sudo ss -tnp
pid=$(sudo ss -Htnp | awk '$5 ~ /:4444$/' | grep -o 'pid=[0-9]*' | head -n1 | cut -d= -f2)
echo "$pid $(ps -o comm= -p "$pid")" > ~/connexion.txt
sudo kill "$pid"
''',
    22: r'''
#@ 22.1
#? `ssh-keygen -t ed25519` crée la clé privée ~/.ssh/id_ed25519 et la clé publique id_ed25519.pub ; `-N ''` fixe une passphrase vide et `-f` l'emplacement, sans questions.
#? En interactif, il suffit d'appuyer sur Entrée à chaque question, y compris pour la passphrase.
#? Piège classique : mettre une passphrase ; c'est une bonne pratique en général, mais les connexions automatiques des exercices suivants échoueraient.
#? ssh-keygen donne lui-même les droits 600 à la clé privée : inutile de les modifier.
mkdir -p -m 700 ~/.ssh
ssh-keygen -q -t ed25519 -N '' -f ~/.ssh/id_ed25519
#@ 22.2
#? `ssh-copy-id` ajoute votre clé publique au fichier authorized_keys du compte distant ; il demande une dernière fois le mot de passe de deploy (deploy123).
#? La correction utilise `sshpass` uniquement pour que le banc de test tourne sans clavier ; en classe, vous tapez le mot de passe.
#? À la première connexion, ssh vous demande de confirmer la clé du serveur : répondez `yes`.
#? Piège classique : envoyer la clé privée au lieu de la publique ; la clé privée ne quitte jamais votre machine.
# En classe : ssh-copy-id deploy@localhost (mot de passe deploy123)
sshpass -p deploy123 ssh-copy-id -o StrictHostKeyChecking=accept-new deploy@localhost 2>/dev/null
#@ 22.3
#? Un bloc `Host prod` de ~/.ssh/config regroupe `HostName`, `User` et `Port` : ensuite, `ssh prod` suffit, et l'alias fonctionne aussi avec scp.
#? `ssh -G prod` affiche la configuration finale : c'est le meilleur moyen de vérifier l'alias ; `HostName 127.0.0.1` est accepté aussi bien que `localhost`.
#? Le serveur du port 2222 partage les comptes de la machine : la clé installée pour deploy à l'exercice précédent fonctionne donc aussi.
#? À la première connexion, ssh demande de confirmer la clé de ce nouveau serveur, comme pour tout hôte inconnu.
printf 'Host prod\n    HostName localhost\n    User deploy\n    Port 2222\n' > ~/.ssh/config
ssh -o StrictHostKeyChecking=accept-new prod true
#@ 22.4
#? scp s'utilise comme cp, mais une extrémité est de la forme `hôte:chemin` ; un « : » sans chemin désigne le dossier personnel distant.
#? Grâce à l'alias, `prod:` suffit ; `scp ~/a-envoyer/livrable.txt deploy@localhost:` est tout aussi valable.
#? Piège classique : copier avec `sudo cp` ; le fichier appartiendrait alors à root, alors qu'une copie par scp est écrite par deploy lui-même.
scp -q ~/a-envoyer/livrable.txt prod:
#@ 22.6
#? Dans authorized_keys, des options placées devant une clé la restreignent : `command="…"` impose la commande exécutée, quelle que soit celle que demande le client.
#? `no-pty`, `no-port-forwarding`, `no-agent-forwarding` et `no-X11-forwarding` ferment les autres usages de la clé ; l'option unique `restrict` les regroupe.
#? Piège classique : écraser authorized_keys avec `>` au lieu d'ajouter avec `>>` ; votre clé personnelle perdrait son accès normal.
#? On se sert ici de sa clé personnelle pour ajouter la ligne à distance ; éditer /home/deploy/.ssh/authorized_keys avec sudo marche aussi, à condition de garder le propriétaire et les droits.
# Options devant la clé dans authorized_keys : cette clé ne peut lancer que deploy-only
ssh-keygen -q -t ed25519 -N '' -C integration-continue -f ~/.ssh/ci_key
echo "command=\"/usr/local/bin/deploy-only\",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding $(cat ~/.ssh/ci_key.pub)" | ssh deploy@localhost 'cat >> ~/.ssh/authorized_keys'
ssh -i ~/.ssh/ci_key -o IdentitiesOnly=yes deploy@localhost whoami
#@ 22.7
#? Quand ssh ne peut pas se servir d'une clé, il le dit dès les premières lignes, puis se rabat sur le mot de passe : tout est dans le message. La cause est tirée au sort à la mise en place.
#? « UNPROTECTED PRIVATE KEY FILE » : le client refuse une clé privée lisible par d'autres que vous, `chmod 600` (ou 400) suffit.
#? « Load key … : Permission denied » : la clé appartient à root et vous ne pouvez pas la lire ; `sudo chown etudiant: fichier` vous la rend.
#? « Load key … : error in libcrypto » (ou « invalid format ») : le fichier a été abîmé en passant par Windows ; `cat -A` montre des `^M` en fin de ligne, que `sed -i 's/\r$//'` supprime.
#? Piège classique : régénérer une clé ou modifier le compte sauvegarde ; c'est la clé fournie qui doit fonctionner.
k=~/cles/sauvegarde_key
ls -l "$k"
# Une clé qui appartient à un autre compte : on la reprend
[ "$(stat -c %U "$k")" = "$(whoami)" ] || sudo chown "$(whoami):" "$k"
# Des fins de ligne Windows : on les retire
grep -q $'\r' "$k" && sed -i 's/\r$//' "$k"
# Une clé privée ne doit être lisible que par son propriétaire
chmod 600 "$k"
ssh -i "$k" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new sauvegarde@localhost true
#@ 22.5
#? `PasswordAuthentication no` et `PermitRootLogin no` dans /etc/ssh/sshd_config ; le sed traite aussi les lignes commentées par défaut (#PasswordAuthentication…).
#? Toujours `sudo sshd -t` avant de recharger : une erreur de syntaxe empêcherait le service de redémarrer ; `sudo sshd -T` montre la configuration effective.
#? Piège classique : oublier `sudo service ssh reload` ; le fichier est correct, mais le serveur applique encore l'ancienne configuration.
#? `PermitRootLogin prohibit-password` ne suffit pas ici : le ticket demande d'interdire complètement la connexion directe de root.
#? C'est pour cela que ce durcissement se fait après les exercices qui utilisent le mot de passe de deploy : ssh-copy-id ne fonctionnerait plus.
sudo sed -i -E 's/^#?PasswordAuthentication .*/PasswordAuthentication no/; s/^#?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sshd -t
sudo service ssh reload
sleep 1
#@ 22.8
#? `DenyUsers intrus toor` est une liste noire : seuls ces comptes sont refusés, quelle que soit la méthode d'authentification.
#? Piège classique : utiliser `AllowUsers` ou `AllowGroups`, une liste blanche qui refuserait aussi tous les comptes créés plus tard.
#? Comme toujours : `sudo sshd -t`, puis `sudo service ssh reload`, et `sudo sshd -T | grep denyusers` pour vérifier la configuration effective.
#? Attention en ajoutant une ligne à la fin de sshd_config : si le fichier se termine par un bloc `Match` actif, la ligne ne s'appliquerait qu'à ce bloc.
# Liste noire : les comptes créés plus tard ne sont pas concernés (AllowUsers les exclurait)
echo 'DenyUsers intrus toor' | sudo tee -a /etc/ssh/sshd_config > /dev/null
sudo sshd -t
sudo service ssh reload
sleep 1
''',
    23: r'''
#@ 23.1
#? `sudo find / -perm -4000 -type f 2>/dev/null` liste tous les fichiers portant le bit SUID ; sudo permet de fouiller partout et `2>/dev/null` jette les erreurs restantes.
#? `dpkg -S chemin` indique le paquet qui a installé un fichier ; un fichier SUID qu'aucun paquet ne revendique mérite une enquête.
#? Piège classique : sous Ubuntu, dpkg connaît certains fichiers sous leur ancien chemin (/bin/mount plutôt que /usr/bin/mount) ; sans le second essai, on accuse à tort des binaires légitimes.
#? Les deux suspects (leurs noms et leurs emplacements) sont tirés au sort à la mise en place : seule la vérification par dpkg de votre propre liste les révèle, la liste d'un camarade ne vaut pas pour vous.
sudo find / -perm -4000 -type f 2>/dev/null > ~/suid-files.txt
# Un binaire légitime appartient à un paquet ; dpkg connaît parfois l'ancien chemin (/bin/… plutôt que /usr/bin/…)
: > ~/suid-suspects.txt
for f in $(cat ~/suid-files.txt); do
    dpkg -S "$f" > /dev/null 2>&1 || dpkg -S "${f#/usr}" > /dev/null 2>&1 || echo "$f" >> ~/suid-suspects.txt
done
cat ~/suid-suspects.txt
#@ 23.2
#? `chmod u-s` retire le bit SUID sans toucher au fichier : l'auditeur peut ainsi examiner les programmes, que le ticket interdisait de supprimer.
#? L'un des suspects est une copie de cat, l'autre une copie de find, cp ou tail : en SUID root, ils permettaient de lire ou de copier n'importe quel fichier, et même de lancer des commandes en root avec `find -exec`.
#? On traite chaque ligne de l'inventaire de l'exercice précédent : c'est lui, et non la liste d'un camarade, qui désigne vos suspects.
#? Pour savoir quel programme se cache derrière chaque nom, `--version` suffit ; relancer ensuite la copie de cat sur /etc/shadow en simple utilisateur doit échouer avec « Permission denied ».
ls -l $(cat ~/suid-suspects.txt)
sudo chmod u-s $(cat ~/suid-suspects.txt)
for f in $(cat ~/suid-suspects.txt); do "$f" --version 2>/dev/null | head -n 1; done
#@ 23.3
#? `find /etc -type f -perm -o+w` trouve les fichiers que « les autres » peuvent modifier : ici /etc/app-secret.conf.
#? `chown root:root` puis `chmod 600` : seul root peut désormais le lire et le modifier.
#? Un secret qui a été lisible par tous doit être considéré comme compromis : on remplace sa valeur, en gardant la ligne `db_password=`.
#? Piège classique : supprimer le fichier, ou corriger les droits sans changer le mot de passe ; `sudo nano` convient parfaitement pour saisir la nouvelle valeur.
f=$(sudo find /etc -type f -perm -o+w)
sudo chown root:root "$f"
sudo chmod 600 "$f"
# Le mot de passe a pu être lu par n'importe qui : on le remplace
sudo sed -i "s/^db_password=.*/db_password=$(head -c 12 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')/" "$f"
#@ 23.4
#? Un compte d'UID 0 est root, quel que soit son nom : `awk -F: '$3 == 0 {print $1}' /etc/passwd` les liste tous. Le nom du faux root est tiré au sort à la mise en place (toor, sysmaint…) : seule cette recherche le révèle.
#? `userdel` refuse ici, car des processus tournent avec l'UID 0 ; on neutralise donc le compte : mot de passe verrouillé (`passwd -l`) et shell `/usr/sbin/nologin` (ou `/bin/false`).
#? Faire expirer le compte avec `chage -E 0 nom` (ou toute date passée, comme `usermod -e 1 nom`) est accepté à la place du verrouillage du mot de passe, mais il faut quand même retirer le shell.
#? Ne tentez surtout pas `userdel -r` sur ce compte : son dossier personnel est /root.
awk -F: '$3 == 0 {print $1}' /etc/passwd > ~/uid-zero.txt
# userdel refuse (des processus tournent en UID 0) : on neutralise le compte qui n'est pas root
faux=$(awk -F: '$3 == 0 && $1 != "root" {print $1}' /etc/passwd)
sudo passwd -l "$faux"
sudo usermod -s /usr/sbin/nologin "$faux"
#@ 23.5
#? `chage -E 0` fait expirer le compte : plus aucune connexion n'est possible, par mot de passe comme par clé SSH, sans rien supprimer ; `usermod -e 1` a le même effet.
#? Piège classique : `passwd -l` ne verrouille que le mot de passe (la clé SSH fonctionne encore), et un shell nologin n'empêche pas un tunnel avec `ssh -N`.
#? `chage -M 90` fixe la durée de validité maximale du mot de passe, conformément à la politique de l'entreprise ; `chage -l securise` permet de vérifier les deux réglages.
sudo chage -M 90 securise
# passwd -l ne bloque que le mot de passe : la clé SSH fonctionnerait encore. On fait expirer le compte.
sudo chage -E 0 securise
#@ 23.6
#? Le bit sticky (le `t` final de `drwxrwxrwt`, comme sur /tmp) limite la suppression et le renommage aux propriétaires des fichiers dans un dossier ouvert à tous.
#? `chmod +t` le pose ; en octal, `chmod 1777 /srv/depot` donne le même résultat.
#? Piège classique : retirer le droit d'écriture aux autres ; plus personne ne pourrait alors déposer de fichier.
# Le bit sticky : dans un dossier ouvert à tous, chacun ne supprime que ses fichiers
sudo chmod +t /srv/depot
#@ 23.7
#? La umask retire des droits à la création : un `umask 000` exécuté à chaque ouverture de session créait des fichiers en 666, modifiables par tous.
#? Marc a rangé ses réglages de confort à un endroit tiré au sort : /etc/profile.d/, /etc/profile ou /etc/bash.bashrc. `grep -rn umask /etc/profile /etc/profile.d /etc/bash.bashrc` retrouve le coupable chez vous.
#? On supprime cette seule ligne, ou on la remplace par `umask 022`. Piège classique : supprimer tout le bloc, ce qui ferait perdre HISTTIMEFORMAT et l'alias, ou ne corriger que son propre ~/.bashrc, ce qui laisse les autres comptes exposés.
#? La nouvelle umask ne s'applique qu'aux sessions ouvertes après la correction.
grep -rn umask /etc/profile /etc/profile.d /etc/bash.bashrc
for f in $(grep -rlE '^\s*umask\s+0+\s*$' /etc/profile /etc/profile.d /etc/bash.bashrc); do
    sudo sed -i -E '/^\s*umask\s+0+\s*$/d' "$f"
done
#@ 23.8
#? Une tâche root ne doit exécuter qu'un fichier que seul root peut modifier : le fichier lui-même, mais aussi chacun de ses dossiers, puisqu'on peut remplacer un fichier dans un dossier où l'on a le droit d'écrire.
#? `namei -l chemin` affiche le propriétaire et les droits de chaque élément du chemin. Trois défauts sont possibles, répartis au hasard entre les scripts : un fichier modifiable par tous (777), un dossier modifiable par un groupe (on peut y remplacer le script), ou un fichier qui appartient à un autre compte que root.
#? Piège classique : recopier la liste d'un camarade, signaler un script sain, ou oublier le cas du dossier ; la liste doit être exacte.
#? La correction garde les scripts exécutables (`chown root:root`, `chmod go-w` sur le fichier ou le dossier en cause) : un `chmod 644` casserait la tâche, et déplacer le script est interdit.
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
# Correction : chaque élément du chemin qui n'appartient pas à root ou qui est modifiable par le groupe ou les autres
for p in $(cat ~/cron-risque.txt); do
    d=$p
    while [ "$d" != / ]; do
        if [ -n "$(find "$d" -maxdepth 0 \( ! -user root -o -perm /022 \))" ]; then
            sudo chown root "$d"
            sudo chmod go-w "$d"
        fi
        d=$(dirname "$d")
    done
done
#@ 23.9
#? C'est la clé elle-même, la longue suite de caractères, qui donne l'accès ; le commentaire en fin de ligne s'écrit librement et ne prouve rien.
#? On relève donc la clé de marc@portable dans /root/.ssh/authorized_keys, puis on la cherche dans tous les authorized_keys du système (`sudo find / -xdev -name authorized_keys`).
#? Piège classique : ne supprimer que la ligne commentée marc@portable ; la même clé se cache chez deux autres comptes, sous d'autres commentaires. Ces comptes sont tirés au sort à la mise en place : seule la recherche de la clé dans tous les fichiers les révèle.
#? Le sed utilise `#` comme délimiteur parce qu'une clé peut contenir des « / » ; supprimer des fichiers entiers couperait votre propre accès à deploy.
#? La clé de Marc est générée à la mise en place : sa valeur exacte diffère d'une machine à l'autre.
# C'est la clé elle-même qu'on cherche, pas son commentaire
cle=$(sudo awk '/marc@portable/ {print $2}' /root/.ssh/authorized_keys)
for f in $(sudo find / -xdev -name authorized_keys 2>/dev/null); do
    sudo grep -q "$cle" "$f" && sudo sed -i "\#$cle#d" "$f"
done
ssh deploy@localhost true
''',
    24: r'''
#@ 24.1
#? Plusieurs problèmes se cachent l'un derrière l'autre, tirés au sort parmi ce que Windows fait subir à un script : fichier non exécutable, fins de ligne Windows (CRLF), shebang erroné (`#!/bin/bsh`), fichier enregistré en UTF-16, ou marque d'ordre des octets (BOM) UTF-8 collée devant le shebang.
#? `file deploy.sh` annonce l'encodage et les fins de ligne ; `cat -A` révèle les `^M` (le caractère \r) et les octets placés avant `#!`.
#? Remèdes : `iconv -f UTF-16 -t UTF-8` pour l'UTF-16, `sed -i '1s/^\xEF\xBB\xBF//'` pour le BOM, `sed -i 's/\r$//'` (ou `dos2unix`) pour les fins de ligne, un shebang valide (`#!/bin/bash`, `#!/bin/sh` ou `#!/usr/bin/env bash`) et `chmod +x`.
#? Piège classique : recopier les commandes d'un camarade (un `sed` sur un fichier UTF-16 le massacre) ou lancer `bash deploy.sh`, qui masque le shebang et les droits ; il faut que `~/depannage/deploy.sh` fonctionne seul.
f=~/depannage/deploy.sh
file "$f"
# Enregistré en UTF-16 : on le convertit en UTF-8
case $(file -b "$f") in *UTF-16*) iconv -f UTF-16 -t UTF-8 "$f" > /tmp/deploy.sh && cat /tmp/deploy.sh > "$f" ;; esac
# BOM UTF-8 en tête et fins de ligne Windows (CRLF)
sed -i '1s/^\xEF\xBB\xBF//; s/\r$//' "$f"
# Un shebang qui désigne un interpréteur inexistant
head -n1 "$f" | grep -qxE '#!/bin/(ba)?sh' || sed -i '1s|.*|#!/bin/bash|' "$f"
chmod +x "$f"
cat -A "$f"
#@ 24.2
#? `sudo find /var/log -type f -size +10M` (ou `du -ah /var/log | sort -h | tail`) désigne le journal énorme.
#? Piège classique : le supprimer ; l'application le garde ouvert, l'espace n'est donc pas libéré et elle continue d'écrire dans un fichier invisible.
#? On le vide sans le supprimer : `sudo truncate -s 0 fichier` ; `sudo sh -c ': > fichier'` convient aussi (la redirection doit être faite par root).
#? Le nom du fichier est tiré au sort à la mise en place : le vôtre diffère de celui de la correction.
big=$(sudo find /var/log -type f -size +10M)
echo "$big" > ~/gros-log.txt
# On vide le fichier sans le supprimer : l'application le garde ouvert
sudo truncate -s 0 "$big"
#@ 24.3
#? La cause du refus est tirée au sort ; ssh et sshd la donnent toujours : `ssh -v` côté client, `sudo tail /var/log/auth.log` côté serveur. C'est la démarche qui compte, la correction d'un camarade ne vaut pas forcément pour vous.
#? « Authentication refused: bad ownership or modes » : avec StrictModes (activé par défaut), sshd ignore authorized_keys si ce fichier, ~/.ssh ou le dossier personnel sont modifiables par le groupe ou par les autres ; `namei -l` montre les droits de chaque élément (dossier personnel sans écriture pour les autres, .ssh en 700, authorized_keys en 600, le tout à ops).
#? « … but not from a permitted host » : une option `from="…"` placée devant la clé dans authorized_keys la réserve à d'autres adresses ; on retire cette option (ou on y ajoute 127.0.0.1).
#? « account has expired » : `sudo chage -l ops` le confirme, `sudo chage -E -1 ops` annule l'expiration. « This account is currently not available » : le shell de ops est nologin, `sudo usermod -s /bin/bash ops` lui rend un vrai shell.
#? Piège classique : désactiver StrictModes ou supprimer la clé ; le symptôme disparaît parfois, mais la garde est baissée.
ssh -v -i ~/depannage/cle_ops -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new ops@localhost true 2>&1 | tail -n 3
sudo tail -n 5 /var/log/auth.log
# Droits : ni le dossier personnel, ni .ssh, ni authorized_keys ne doivent être modifiables par d'autres
namei -l /home/ops/.ssh/authorized_keys
sudo chmod go-w /home/ops
sudo chown -R ops:ops /home/ops/.ssh
sudo chmod 700 /home/ops/.ssh
sudo chmod 600 /home/ops/.ssh/authorized_keys
# Une clé réservée à d'autres adresses : on retire l'option from="…"
sudo grep -q '^from=' /home/ops/.ssh/authorized_keys && sudo sed -i -E 's/^from="[^"]*" //' /home/ops/.ssh/authorized_keys
# Un compte expiré : on annule l'expiration
sudo chage -l ops
[ -z "$(sudo getent shadow ops | cut -d: -f8)" ] || sudo chage -E -1 ops
# Un shell qui refuse toute session : on lui rend bash
getent passwd ops | cut -d: -f7 | grep -qE '(nologin|false)$' && sudo usermod -s /bin/bash ops
ssh -i ~/depannage/cle_ops -o IdentitiesOnly=yes -o BatchMode=yes ops@localhost true && echo "connexion rétablie"
#@ 24.4
#? Les erreurs de Marc sont tirées au sort parmi les pièges de l'étape cron ; `grep CRON /var/log/syslog` montre ce que cron exécute réellement, et les fichiers qu'il refuse avec la raison (WRONG FILE OWNER, INSECURE MODE, Missing newline before EOF).
#? Côté fichier : cron ignore ceux dont le nom contient un point, ceux qui n'appartiennent pas à root ou sont modifiables par le groupe ou les autres, et une dernière ligne sans retour à la ligne ; chaque ligne a besoin du 6e champ utilisateur et du chemin absolu du script (cron n'a qu'un PATH minimal).
#? Côté script : lancez-le vous-même avec sudo pour voir l'erreur (une fois réparé, ce passage manuel ajoute une ligne au journal : attendez ensuite deux exécutions de cron). Il doit être exécutable, et son shebang doit désigner un interpréteur qui existe : un `#!/bin/bsh`, ou un `#!/bin/bash` suivi d'un \r invisible (fins de ligne Windows, « bad interpreter »), le rendent inutilisable.
#? Réécrire proprement le fichier de la tâche (ici avec `sudo tee`) règle d'un coup les défauts du fichier ; il faut ensuite attendre au moins deux exécutions.
# Le fichier de Marc est refusé ou mal écrit : on le remplace par une tâche propre (nom sans point, root, 644, retour à la ligne)
grep CRON /var/log/syslog | tail -n 5
ls -l /etc/cron.d
for f in $(sudo grep -l rapport-cron /etc/cron.d/*); do sudo rm "$f"; done
echo '* * * * * root /usr/local/bin/rapport-cron.sh' | sudo tee /etc/cron.d/rapport > /dev/null
# Le script : fins de ligne Windows, shebang, droit d'exécution
s=/usr/local/bin/rapport-cron.sh
sudo sed -i 's/\r$//' "$s"
head -n1 "$s" | grep -qx '#!/bin/bash' || sudo sed -i '1s|.*|#!/bin/bash|' "$s"
sudo chmod 755 "$s"
head -n1 "$s" | cat -A
#@ 24.5
#? On lit chaque message de `--check`, on corrige, on relance : c'est la méthode « une hypothèse, une correction ». Les erreurs de configuration sont tirées au sort, d'où la boucle du corrigé, qui réagit au message obtenu.
#? « configuration illisible » : le fichier n'est lisible que par root, `chmod 644` suffit (il ne contient pas de secret). « PORT=… invalide » : il faut un nombre entre 1024 et 65535, ici `PORT=8080`.
#? « LOG_DIR=… n'existe pas » ou « ne peut pas écrire » : le dossier doit être /var/log/mon-service (attention aux fautes de frappe dans LOG_DIR), exister et appartenir à monsvc.
#? Un message qui paraît absurde (un port ou un dossier qui semble correct) trahit souvent des fins de ligne Windows : `sudo cat -A /etc/mon-service.conf` montre les `^M`, `sed -i 's/\r$//'` les retire.
#? Piège classique : `chmod 777` sur le dossier ou changer LOG_DIR ; les journaux doivent rester dans /var/log/mon-service, sans être modifiables par les autres.
C=/etc/mon-service.conf
sudo cat -A "$C"
for essai in 1 2 3 4 5; do
    msg=$(sudo -u monsvc mon-service --check 2>&1) && break
    echo "$msg"
    case $msg in
        *illisible*) sudo chmod 644 "$C" ;;
        *PORT=*) sudo sed -i 's/\r$//' "$C"; sudo sed -i 's/^PORT=.*/PORT=8080/' "$C" ;;
        *"n'existe pas"*) sudo sed -i 's/\r$//' "$C"; sudo sed -i 's|^LOG_DIR=.*|LOG_DIR=/var/log/mon-service|' "$C"
                          sudo mkdir -p /var/log/mon-service; sudo chown monsvc: /var/log/mon-service ;;
        *"ne peut pas écrire"*) sudo chown monsvc: /var/log/mon-service ;;
    esac
done
sudo chmod 755 /var/log/mon-service
sudo -u monsvc mon-service --check
#@ 24.6
#? Pour atteindre un fichier, il faut pouvoir traverser chaque dossier du chemin (droit x) ; `namei -l` montre lequel bloque webapp, et ce n'est pas le même chez tout le monde : /srv/app, ou /srv/app/public (fermé aux autres, ou lisible mais pas traversable).
#? Sur un dossier, x sans r permet de le traverser sans le lister : on ajoute donc seulement le droit x des autres (`chmod o+x`) sur chaque dossier du chemin qui ne l'a pas.
#? Piège classique : `chmod 755` sur /srv/app laisse lister son contenu, et un `chmod -R` ouvrirait les secrets ; /srv/app/secrets, en 700, reste protégé.
# Chaque dossier du chemin doit être traversable (x) par les autres, sans rien ouvrir de plus
namei -l /srv/app/public/index.html
for d in /srv/app /srv/app/public; do
    [ -n "$(find "$d" -maxdepth 0 ! -perm -o=x 2>/dev/null)" ] && sudo chmod o+x "$d"
done
namei -l /srv/app/public/index.html
#@ 24.7
#? L'hébergeur a rouvert les mots de passe d'une façon tirée au sort ; `sudo sshd -T` (configuration effective) et `sudo sshd -T -C user=deploy,host=localhost,addr=127.0.0.1` (pour une connexion précise) permettent de la trouver.
#? sshd_config commence par `Include /etc/ssh/sshd_config.d/*.conf` : ces fichiers, quel que soit leur nom, sont lus en premier, et la première valeur lue l'emporte ; `grep -ri` sur sshd_config.d/ trouve celui de l'hébergeur.
#? Un bloc `Match Address 127.0.0.1` en fin de sshd_config ne change rien à `sshd -T` sans `-C`, mais rouvre les mots de passe pour les connexions locales.
#? `KbdInteractiveAuthentication yes` demande aussi le mot de passe (par PAM) : `PasswordAuthentication no` ne suffit pas, il faut la remettre à `no`.
#? Supprimer le réglage fautif (ou le passer à `no`) est la correction ; ensuite `sudo sshd -t` et `sudo service ssh reload`. Piège classique : retoucher la ligne `PasswordAuthentication no` de sshd_config, qui n'est pas en cause.
sudo sshd -T | grep -iE 'passwordauthentication|kbdinteractive'
sudo sshd -T -C user=deploy,host=localhost,addr=127.0.0.1 | grep -iE 'passwordauthentication|kbdinteractive'
grep -n -e Include -e '^Match' /etc/ssh/sshd_config
sudo grep -rniE 'passwordauthentication|kbdinteractiveauthentication' /etc/ssh/sshd_config.d/
# Les fichiers inclus qui rouvrent un mode d'authentification par mot de passe : on les retire
for f in $(sudo grep -rliE '^\s*(PasswordAuthentication|KbdInteractiveAuthentication)\s+yes' /etc/ssh/sshd_config.d/); do sudo rm "$f"; done
# Un bloc Match qui rouvre les mots de passe : on le referme
sudo sed -i -E '/^\s*Match /,$ s/^(\s*PasswordAuthentication)\s+yes/\1 no/I' /etc/ssh/sshd_config
sudo sshd -t
sudo service ssh reload
sleep 1
#@ 24.8
#? `for f in $(ls $SRC)` découpe les noms aux espaces : « facture mars.pdf » devient deux éléments inexistants.
#? Le joker `"$SRC"/*` donne chaque nom entier, et les guillemets autour de chaque variable empêchent tout nouveau découpage, y compris dans SOURCE et DEST.
#? `[ -f "$f" ] || continue` ignore le motif resté tel quel si le dossier est vide ; `sudo bash -x` permet de voir ce que la boucle reçoit réellement.
#? Piège classique : une variante en `find … | while read` ; la boucle tourne alors dans un sous-shell et le compteur n affiché à la fin resterait à 0.
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
#? On compare l'empreinte calculée avec `ssh-keygen -lf` sur la vraie clé publique à celle qu'annonce ssh dans son avertissement : si elles sont identiques, c'est bien notre serveur.
#? `ssh-keygen -R '[localhost]:2222'` oublie l'ancienne clé ; les crochets désignent un hôte sur un port non standard, et les guillemets les protègent du shell.
#? `StrictHostKeyChecking=accept-new` accepte une clé inconnue mais refuserait toujours une clé changée : la vérification reste active.
#? Piège classique : désactiver la vérification (`StrictHostKeyChecking no` ou `UserKnownHostsFile /dev/null`), exactement ce que le ticket interdit.
#? La clé d'hôte est générée à la mise en place : votre empreinte diffère de celle de toute autre machine.
# On vérifie l'empreinte de la nouvelle clé, puis on oublie l'ancienne (sans désactiver la vérification)
ssh-keygen -lf /etc/ssh/prod/ssh_host_ed25519_key.pub | awk '{print $2}' > ~/empreinte.txt
ssh-keygen -R '[localhost]:2222'
ssh -p 2222 -o StrictHostKeyChecking=accept-new deploy@localhost true
#@ 24.4
#? Cette dernière partie ne fait qu'attendre : cron n'exécute la tâche réparée qu'au début de chaque minute, et la vérification exige deux exécutions.
#? De votre côté, il suffit de patienter deux minutes en surveillant /var/log/rapport-cron.log, par exemple avec `tail -f`.
# Attendre que cron exécute deux fois la tâche réparée
for i in $(seq 100); do [ "$(grep -c 'rapport généré' /var/log/rapport-cron.log 2>/dev/null)" -ge 2 ] && break; sleep 2; done
''',
    25: r'''
#@ 25.1
#? Le groupe www devient propriétaire de toute l'arborescence (`chgrp -R`), et `chmod -R 2775` donne l'écriture au groupe, la lecture aux autres et le bit setgid.
#? Le setgid (le 2 en tête) fait hériter le groupe www aux fichiers créés dans ces dossiers.
#? Piège classique : oublier le dossier monsite lui-même, ou ouvrir en 777 ; les autres ne doivent écrire nulle part.
#? `useradd -m -G www webmaster` (après avoir créé le groupe) et `mkdir -p /var/www/monsite/{html,logs,backup}` sont des raccourcis tout aussi valables.
sudo useradd -m -s /bin/bash webmaster
sudo groupadd www
sudo usermod -aG www webmaster
sudo mkdir -p /var/www/monsite/html /var/www/monsite/logs /var/www/monsite/backup
sudo chgrp -R www /var/www/monsite
sudo chmod -R 2775 /var/www/monsite
#@ 25.2
#? `sudo -u webmaster bash -c '…'` exécute toutes les commandes, redirections comprises, sous le compte webmaster : les fichiers lui appartiennent.
#? Piège classique : `sudo -u webmaster echo … > fichier`, où c'est votre shell à vous qui ouvre le fichier ; il échoue ou le crée à votre nom.
#? Ouvrir un shell avec `sudo -u webmaster bash`, ou écrire via `… | sudo -u webmaster tee fichier`, convient tout aussi bien.
sudo -u webmaster bash -c 'echo "<h1>Bienvenue</h1>" > /var/www/monsite/html/index.html; for i in 1 2 3 4 5; do echo "GET /page$i 200" >> /var/www/monsite/logs/access.log; done'
#@ 25.3
#? `date +%Y%m%d-%H%M%S` produit l'horodatage, et `tar -C /var/www/monsite html` stocke html/ sans le chemin complet /var/www/monsite.
#? La vérification lance le script en tant que webmaster depuis /tmp : tous les chemins du script doivent être absolus.
#? Piège classique : `tar -czf … /var/www/monsite/html`, qui enregistre le chemin var/www/monsite/html dans l'archive.
#? Le script appartient à webmaster et reste exécutable : ce sera utile pour la planification et la revue de sécurité.
sudo tee /home/webmaster/backup.sh > /dev/null <<'EOF'
#!/bin/bash
B=/var/www/monsite/backup
tar -czf "$B/site-$(date +%Y%m%d-%H%M%S).tar.gz" -C /var/www/monsite html
df -h > "$B/disk-report.txt"
EOF
sudo chown webmaster: /home/webmaster/backup.sh
sudo chmod 755 /home/webmaster/backup.sh
#@ 25.4
#? Une tâche de /etc/cron.d comporte un 6e champ, l'utilisateur, ici webmaster ; `0 3 * * *` signifie chaque jour à 3h00.
#? Le fichier doit appartenir à root, n'être modifiable ni par le groupe ni par les autres, et se terminer par un retour à la ligne : `echo … | sudo tee` remplit ces trois conditions.
#? Piège classique : un nom de fichier avec un point, un chemin relatif, ou une crontab personnelle de webmaster au lieu du fichier demandé.
echo '0 3 * * * webmaster /home/webmaster/backup.sh' | sudo tee /etc/cron.d/backup-web > /dev/null
#@ 25.5
#? `ls -1t` trie du plus récent au plus ancien, `tail -n +8` garde tout à partir de la 8e ligne, et `xargs -r rm -f` supprime ces archives en trop (sans rien lancer si la liste est vide).
#? La ligne est ajoutée à la fin du script, après la création de la nouvelle archive : placée avant, elle laisserait 8 archives.
#? Les apostrophes empêchent `$B` d'être remplacé au moment de l'ajout : il sera interprété à l'exécution du script.
#? Piège classique : un motif trop large qui supprimerait disk-report.txt ; ici seul `site-*.tar.gz` est concerné, et comme le nom contient la date, un tri par nom fonctionnerait aussi.
# Ligne ajoutée à la fin de backup.sh : garde les 7 archives les plus récentes
echo 'ls -1t "$B"/site-*.tar.gz | tail -n +8 | xargs -r rm -f' | sudo tee -a /home/webmaster/backup.sh > /dev/null
#@ 25.6
#? `df -P /` donne une ligne stable ; on extrait la 5e colonne et on retire le « % » pour obtenir un nombre comparable.
#? « Dépasse » signifie strictement supérieur : `-gt`, et non `-ge`, car un seuil égal à l'occupation doit répondre OK.
#? Piège classique : comparer des chaînes avec `>` au lieu de nombres ; la vérification teste des seuils juste au-dessous, égal et juste au-dessus.
#? Sans argument, le script affiche l'usage sur la sortie d'erreur et sort avec `exit 1` ; chaque contrôle ajoute une ligne datée par `date '+%F %T'` à monitoring.txt.
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
#? webmaster n'a pas de mot de passe (et sshd les refuse depuis l'exercice 22.5) : ssh-copy-id ne peut pas s'y connecter, on installe donc la clé soi-même avec sudo.
#? `install -d -m 700 -o webmaster -g webmaster` crée .ssh avec le bon propriétaire et les bons droits en une commande ; authorized_keys doit lui aussi appartenir à webmaster, en 600.
#? Piège classique : `sudo cat … >> authorized_keys`, où la redirection est faite par votre shell sans droits ; `sudo tee -a` règle le problème.
#? Comme à l'exercice 24.3, un .ssh ou un authorized_keys modifiable par d'autres serait ignoré par sshd.
# webmaster n'a pas de mot de passe : on installe la clé soi-même
sudo install -d -m 700 -o webmaster -g webmaster /home/webmaster/.ssh
sudo tee -a /home/webmaster/.ssh/authorized_keys < ~/.ssh/id_ed25519.pub > /dev/null
sudo chown webmaster: /home/webmaster/.ssh/authorized_keys
sudo chmod 600 /home/webmaster/.ssh/authorized_keys
#@ 25.8
#? Une réponse HTTP minimale, c'est une ligne de statut, des en-têtes, une ligne vide puis le contenu ; `nc -N -l 127.0.0.1 8000` l'envoie au client et ferme la connexion.
#? nc ne sert qu'une connexion : la boucle `while true` le relance après chaque requête, et une ligne est ajoutée à access.log à chaque tour.
#? `sudo -u webmaster setsid …` lance le serveur sous le compte webmaster, détaché du terminal ; `nohup` est une alternative valable.
#? Piège classique : lancer le script avec sudo seul, il tournerait alors en root ; ou oublier `-N`, et le client attendrait indéfiniment la fin de la réponse.
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
#? `chmod o-rwx` sur backup/ bloque les comptes extérieurs à www, y compris la lecture de disk-report.txt, sans gêner l'équipe web.
#? Pour les archives des prochaines nuits, c'est la umask qui décide : `umask 027` en tête de backup.sh s'applique quelle que soit la umask de la session qui le lance.
#? Piège classique : changer seulement les droits des archives existantes, ou compter sur la umask de sa propre session ; la vérification lance le script avec une umask 002.
#? `sed -i '2i …'` insère la ligne juste après le shebang ; un `chmod o-rwx` sur l'archive, ajouté dans le script après le tar, serait aussi accepté.
# Plus aucun accès pour les autres au dossier des sauvegardes, et des archives créées sans droits pour les autres
sudo chmod o-rwx /var/www/monsite/backup
sudo sed -i '2i umask 027' /home/webmaster/backup.sh
''',
}
