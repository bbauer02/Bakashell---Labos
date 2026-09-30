"""Corrigé du parcours Git : un script par étape, exécuté en tant qu'« etudiant » par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Aucun éditeur interactif : les messages sont passés avec -m / --no-edit, et le rebase interactif reçoit sa liste
de commits par GIT_SEQUENCE_EDITOR (un étudiant, lui, la modifie dans nano).
"""

SOLUTIONS = {
    1: r'''
#@ G1.1
#? `--global` écrit les réglages dans `~/.gitconfig` : ils valent pour tous vos dépôts, présents et futurs, sur ce serveur.
#? Chaque commit enregistre ce nom et cette adresse : configurez-les avant de commiter, sinon Git les déduit du compte système (ou refuse de commiter) et vos commits ne portent pas votre nom.
#? `init.defaultBranch main` ne concerne que les dépôts créés ensuite par `git init` ; sans ce réglage, Git 2.39 crée une branche `master`.
#? Le nom et l'adresse du corrigé ne sont qu'un exemple : utilisez les vôtres, au format « Prénom Nom » et prenom.nom@cimes-sentiers.fr.
git config --global user.name "Camille Martin"
git config --global user.email "camille.martin@cimes-sentiers.fr"
git config --global init.defaultBranch main
#@ G1.2
#? `git init` crée le dossier caché `.git` : le dossier devient un dépôt, encore sans aucun commit.
#? `git add` place les trois procédures dans l'index, puis `git commit` enregistre cet instantané ; nommer les fichiers plutôt que faire `git add .` évite d'embarquer `brouillon-perso.txt`.
#? Pièges classiques : commiter avant d'avoir configuré son identité, ou se retrouver sur `master` ; `git commit --amend --reset-author --no-edit` et `git branch -m main` réparent l'un et l'autre.
cd ~/procedures
git init
git add sauvegarde.md comptes.md imprimantes.md
git commit -m "Procédures d'exploitation"
#@ G1.3
#? La règle est écrite dans `.gitignore`, un fichier commité : elle voyage avec le dépôt et protège aussi contre un futur `git add .` de n'importe quel collègue.
#? Une règle d'ignorance n'a aucun effet sur un fichier déjà suivi : si le brouillon avait été commité, il fallait d'abord `git rm --cached brouillon-perso.txt` (retiré de l'index, conservé sur le disque), puis un commit.
#? À éviter : supprimer le fichier du disque, ou placer la règle dans `.git/info/exclude` ou dans votre configuration personnelle, qui ne sont pas partagés avec l'équipe.
cd ~/procedures
echo "brouillon-perso.txt" > .gitignore
git add .gitignore
git commit -m "Ignorer le brouillon personnel"
#@ G1.4
#? `git status` puis `git diff` révèlent deux fichiers modifiés : `stock.csv` (le travail de Léa) et le fichier où Julien a fait son essai.
#? En n'indexant que `stock.csv`, le commit ne contient que l'inventaire ; un `git commit -a` ou un `git add .` y aurait mêlé l'essai.
#? `git restore` sur le fichier de l'essai le ramène à sa version indexée, ici celle du dernier commit : c'est définitif, l'essai n'est enregistré nulle part, et c'est exactement ce que Léa demandait.
#? Le fichier de l'essai, son texte et la quantité de sacs sont tirés au sort : chez vous, l'essai n'est pas forcément dans le même fichier que chez votre voisin.
#? Variantes valables : `git checkout -- <fichier>` (ancienne syntaxe de `git restore`), ou `git commit stock.csv -m …`, qui ne commite que ce fichier.
cd ~/inventaire
git status                     # stock.csv ET le fichier de l'essai sont modifiés
git diff                       # l'essai de Julien
git add stock.csv
git commit -m "Inventaire d'octobre"
essai=$(git diff --name-only)  # le seul fichier encore modifié : celui de l'essai
git restore $essai             # jette l'essai (retour à la version du dernier commit)
#@ G1.5
#? `git add -p` découpe les modifications du fichier en morceaux (hunks) et demande pour chacun s'il faut l'indexer : `y` pour les centimes, `n` pour la ligne de debug.
#? `git diff --staged` montre ce qui partira dans le commit et `git diff` ce qui restera dans le fichier : contrôler les deux évite de commiter le debug par erreur.
#? Quand les deux modifications sont proches, elles forment un seul morceau : la touche `s` le découpe (ou `e` permet de l'éditer), puis on répond pour chaque partie.
#? L'ordre des fonctions et la place du debug sont tirés au sort : selon les environnements, les centimes viennent en premier ou en second, dans un morceau à part ou non. Lisez `git diff` avant de répondre.
#? Le `printf` du corrigé ne fait que simuler vos réponses au clavier, qu'il déduit de `git diff` (nombre de morceaux, ordre des deux modifications).
#? Variante valable : retirer la ligne de debug du fichier, commiter, puis la remettre ; le résultat est le même qu'avec `git add -p`.
cd ~/boutique-js
git diff                       # les centimes et le debug : un ou deux morceaux, dans un ordre qui varie
rep=""
if [ "$(git diff js/app.js | grep -c '^@@')" -eq 1 ]; then rep='s\n'; fi   # un seul morceau : le découper
if git diff js/app.js | grep '^+[^+]' | head -n 1 | grep -q DEBUG; then
  rep="${rep}n\ny\n"           # le debug d'abord : n, puis y pour les centimes
else
  rep="${rep}y\nn\n"           # les centimes d'abord : y, puis n pour le debug
fi
printf "$rep" | git add -p js/app.js
git diff --staged              # contrôle : seule la correction est indexée
git commit -m "Affichage des prix avec les centimes"
''',
    2: r'''
#@ G2.1
#? `git log -S "0.055"` (la « pioche ») liste les commits qui changent le nombre d'occurrences de ce texte, sans avoir à lire tout l'historique.
#? Le piège : deux commits sortent, dont « Rayon librairie : cartes et topoguides », qui introduit légitimement le taux réduit des livres dans `js/livres.js` ; limiter la recherche avec `-- js/panier.js` ne garde que le coupable.
#? `git show` sur ce commit permet de confirmer ; 7 caractères du hash suffisent, et une ligne entière de `git log --oneline` est acceptée.
#? Le commit fautif (son message et sa place dans l'historique) est tiré au sort, et son identifiant dépend de la date de création des archives : le vôtre diffère de celui de vos camarades.
cd ~/archives-site
git log -S "0.055" --oneline                   # deux commits : les livres (légitime) et le panier
git log -S "0.055" --oneline -- js/panier.js > ~/commit-tva.txt
#@ G2.2
#? `--diff-filter=D` ne montre que le commit qui a supprimé le fichier ; dans ce commit, le fichier n'existe plus, mais il existe encore dans son parent, noté avec `^`.
#? `git restore --source=...^ data/fournisseurs.csv` ne récupère que ce fichier dans le répertoire de travail ; il reste à l'ajouter et à le commiter.
#? Le piège : `git checkout` d'un commit sans nom de fichier (tête détachée) ou un `git reset --hard` ramèneraient tout le dépôt en arrière, au détriment du travail qui a suivi.
#? Variantes valables : l'ancienne syntaxe `git checkout hash^ -- data/fournisseurs.csv` (qui place en plus le fichier dans l'index), ou `git revert` du commit « Ménage », qui ne contenait que cette suppression.
cd ~/archives-site
# Le commit qui a supprimé le fichier ; le fichier existe encore dans son parent (^)
suppr=$(git log --diff-filter=D --format=%h -- data/fournisseurs.csv)
git restore --source="$suppr^" data/fournisseurs.csv
git add data/fournisseurs.csv
git commit -m "Restauration du fichier des fournisseurs"
#@ G2.3
#? `git revert` crée un nouveau commit qui applique l'inverse du commit visé : le commit de Marc reste dans l'historique, et son annulation s'y ajoute avec la mention « This reverts commit … ».
#? C'est la bonne façon d'annuler un commit déjà partagé : un `reset` ou un rebase réécriraient une histoire que d'autres possèdent déjà.
#? Remettre `0.20` à la main donnerait le même fichier, mais sans trace de ce qu'on annule : la vérification exige un commit dont le message cite le commit annulé, comme le fait `git revert`.
#? Le corrigé relit le hash dans `~/commit-tva.txt` (awk en prend le premier mot), et `--no-edit` accepte le message proposé sans ouvrir l'éditeur.
#? Variantes valables : un titre modifié dans l'éditeur, ou `git revert --no-commit` suivi d'un `git commit` dont le message cite le hash du commit annulé.
cd ~/archives-site
git revert --no-edit "$(awk '{ print $1 }' ~/commit-tva.txt)"
#@ G2.4
#? `git blame` attribue chaque ligne au dernier commit qui l'a touchée : ici « Mise en forme du code » de Julien, qui n'a fait que remplacer des tabulations par des espaces.
#? `git blame -w` ignore les changements d'espaces et remonte jusqu'au commit qui a réellement fixé le montant actuel.
#? Autre piège : « Frais de port 2024 » a bien modifié les frais standard, mais ce n'est pas la valeur actuelle ; `git log -L '/standard/,+1:js/port.js'`, qui retrace toute l'histoire de la ligne, est une variante valable.
#? Le montant actuel, le message, la place et l'auteur de ce commit sont tirés au sort : ils peuvent différer dans votre environnement.
cd ~/archives-site
git blame js/port.js                           # tout est attribué à « Mise en forme du code »…
git blame -w js/port.js                        # … -w ignore les changements d'espaces
git blame -w --porcelain -L '/standard/,+1' js/port.js | head -n 1 | cut -d ' ' -f 1 > ~/commit-frais.txt
#@ G2.5
#? Annuler un vieux commit, c'est appliquer son inverse sur la version actuelle : comme Marc a retouché la même ligne ensuite (« Précision sur le seuil »), le revert s'arrête sur un conflit.
#? Résoudre, c'est écrire la ligne voulue : la valeur d'avant « Seuil de livraison relevé » avec le commentaire précisé, sans aucun des marqueurs `<<<<<<<`, `=======` et `>>>>>>>`.
#? On termine par `git add` puis `git revert --continue`, et non par un nouveau `git revert` ; `git revert --abort` aurait tout annulé pour repartir de zéro.
#? Les seuils et les commentaires sont tirés au sort : le corrigé lit l'ancienne valeur dans le parent du commit annulé (`git show hash^:js/livraison.js`) et le commentaire dans la version actuelle.
#? Dans le corrigé, `GIT_EDITOR=true` accepte le message proposé sans ouvrir l'éditeur ; dans nano, il suffit d'enregistrer et de quitter.
#? Variantes valables : `git commit` au lieu de `git revert --continue` (le message proposé est conservé), ou `git checkout --ours` puis l'ancienne valeur remise à la main.
cd ~/archives-site
seuil=$(git log --format=%h --grep='^Seuil de livraison relevé$')
avant=$(git show "$seuil^:js/livraison.js" | sed -n 's/^const SEUIL_LIVRAISON = \([0-9]*\);.*/\1/p')   # l'ancien seuil
comm=$(git show HEAD:js/livraison.js | sed -n 's|^const SEUIL_LIVRAISON = [0-9]*; \(//.*\)$|\1|p')    # le commentaire précisé
git revert --no-edit "$seuil"                  # CONFLICT : la ligne a été retouchée depuis
# Résolution : l'ancienne valeur avec le commentaire précisé ensuite
sed -i "/^<<<<<<< /,/^>>>>>>> /c\\const SEUIL_LIVRAISON = $avant; $comm" js/livraison.js
git add js/livraison.js
GIT_EDITOR=true git revert --continue
''',
    3: r'''
#@ G3.1
#? `git clone` copie tout l'historique du dépôt partagé dans un nouveau dossier nommé d'après lui (`boutique`, sans le `.git`) et l'enregistre comme distant `origin`.
#? On le lance depuis `~` pour obtenir `~/boutique` ; un `git init` suivi d'une copie des fichiers ne donnerait ni l'historique ni le lien avec `origin`.
#? Variante valable : `git clone /srv/git/boutique.git ~/boutique`, qui précise le dossier de destination.
cd ~
git clone /srv/git/boutique.git
#@ G3.2
#? Deux fautes dans l'accroche : un mot mal écrit (« Randonée » pour « randonnée », par exemple), et une majuscule qui n'a rien à faire au milieu de la phrase.
#? La phrase est tirée au sort à la création du dépôt partagé : le corrigé contient la correction de chacune des versions possibles, une seule s'applique chez vous.
#? Relire `git diff` avant de commiter confirme qu'une seule ligne change ; `git commit -am` indexe les fichiers suivis modifiés et commite en une seule commande.
#? Rien n'arrive sur le dépôt partagé sans `git push` : un commit local reste local.
#? Si un collègue avait publié entre-temps, le push aurait été refusé : on intègre alors son travail avec `git pull` (jour 4), jamais avec `--force`.
cd ~/boutique
sed -i -e 's/matériel de Randonée,/matériel de randonnée,/' -e "s/l'équipemment de Montagne,/l'équipement de montagne,/" \
  -e 's/matériel de Bivouac, livrée/matériel de bivouac, livré/' -e "s/matériel d'Escalade, livrer/matériel d'escalade, livré/" index.html
git diff
git commit -am "Correction des fautes de la page d'accueil"
git push
#@ G3.3
#? Le message « does not appear to be a git repository » vient de l'adresse du distant : `git remote -v` révèle `vitrin.git`, une faute de frappe.
#? `git remote set-url origin` corrige l'adresse existante : inutile de créer un autre dépôt ou de supprimer le dossier `.git`.
#? `git push -u origin main` publie la branche et mémorise que `main` suit `origin/main` : la prochaine fois, un simple `git push` suffira.
#? Variante valable : `git remote remove origin` puis `git remote add origin /srv/git/vitrine.git`, suivis du même `git push -u origin main`.
cd ~/vitrine
git push || true                               # « does not appear to be a git repository »
git remote -v                                  # vitrin.git : faute de frappe
git remote set-url origin /srv/git/vitrine.git
git push -u origin main
''',
    4: r'''
#@ G4.1
#? Avec `pull.rebase true`, `git pull` rejoue vos commits locaux au-dessus de ceux du distant, au lieu de créer un commit « Merge branch 'main' of … ».
#? Avec `rebase.autoStash true`, Git met de côté vos modifications non commitées avant un rebase et les remet en place à la fin ; sans ce réglage, le rebase refuse de démarrer.
#? L'option `--global` est indispensable : la règle doit valoir pour tous vos dépôts, pas seulement pour celui où vous vous trouvez.
#? Variantes valables : `yes`, `on` ou `1` à la place de `true`, et `pull.rebase merges`, qui rebase en conservant les fusions locales.
git config --global pull.rebase true
git config --global rebase.autoStash true
#@ G4.2
#? Le premier `git push` est refusé (« fetch first ») : le dépôt partagé contient des commits que vous n'avez pas encore, et Git refuse de les écraser.
#? `git pull`, qui rebase grâce au réglage précédent, récupère ces commits et rejoue le vôtre au-dessus : l'historique reste linéaire et le second push passe.
#? Le piège majeur : `git push --force` aurait effacé du dépôt partagé le travail de Nadia et des autres.
#? Autre piège : un pull en mode fusion aurait ajouté un commit « Merge branch 'main' of … », contraire à la règle de l'équipe.
#? Le corrigé insère `$(git config user.name)` : la ligne ajoutée porte donc votre propre nom.
#? Variantes valables : `git pull --rebase`, ou `git fetch` puis `git rebase origin/main` ; `git push origin HEAD` publie aussi la branche courante.
cd ~/boutique
echo "- $(git config user.name) (admin système)" >> EQUIPE.md
git commit -am "Ajout de $(git config user.name) dans l'équipe"
git push || true   # refusé : l'équipe a publié entre-temps
git pull           # rejoue notre commit au-dessus des leurs (pull.rebase)
git push
#@ G4.3
#? `git fetch` télécharge les nouveaux commits et met à jour `origin/main` sans toucher à la branche `main` de Sophie ; `git pull`, lui, les aurait intégrés.
#? `main..origin/main` désigne les commits accessibles depuis `origin/main` mais pas depuis `main`, et `git rev-list --count` les compte.
#? Variante : `git status` affiche « Your branch is behind 'origin/main' by … commits » avec le même nombre.
#? Ce nombre dépend d'un tirage au sort (de zéro à cinq commits publiés en plus par l'équipe) et de ce que vous avez vous-même publié : il diffère d'un environnement à l'autre.
cd ~/poste-sophie
git fetch                                      # télécharge sans intégrer
git status                                     # « Your branch is behind 'origin/main' by … commits »
git rev-list --count main..origin/main > ~/nouveaux-commits.txt
#@ G4.4
#? Le push est refusé car Nadia a publié entre-temps ; `git pull` (en rebase) rejoue le commit de Thomas au-dessus du sien et s'arrête sur un conflit, car tous deux ont modifié la ligne `h1`.
#? La bonne résolution combine les deux intentions : la couleur de Thomas et la taille de Nadia, sur une seule ligne, sans marqueurs.
#? Pendant un rebase, on termine par `git add` puis `git rebase --continue`, et non `git commit` ; `git rebase --abort` permet de revenir à l'état de départ.
#? Attention au sens des marqueurs pendant un rebase : la partie `HEAD` (en haut) est la version déjà publiée par Nadia, la partie du bas est le commit de Thomas en train d'être rejoué.
#? La couleur de Thomas est tirée au sort : elle diffère d'un environnement à l'autre (le corrigé la lit avec `git show HEAD:css/style.css` avant le pull).
#? Variantes valables : `git fetch` puis `git rebase origin/main`, et une règle `h1` écrite sur plusieurs lignes ou avec les deux propriétés dans l'autre ordre.
cd ~/poste-thomas
git push || true                               # refusé : Nadia a publié entre-temps
coul=$(git show HEAD:css/style.css | sed -n 's/^h1 { color: \(#[0-9a-f]*\);.*/\1/p')   # la couleur de Thomas
git pull                                       # rebase : CONFLICT dans css/style.css
sed -i "/^<<<<<<< /,/^>>>>>>> /c\\h1 { color: $coul; font-size: 2rem; }" css/style.css
git add css/style.css
GIT_EDITOR=true git rebase --continue          # (pas git commit)
git push
''',
    5: r'''
#@ G5.1
#? `git switch -c` crée la branche et s'y place avant le commit : la promo reste en dehors de `main` tant qu'elle n'est pas validée.
#? `git push -u origin feature/promo-ete` publie la branche et enregistre son lien de suivi, pour que les prochains `git push` et `git pull` sachent où aller.
#? Le piège : commiter d'abord, puis créer la branche, laisserait aussi le commit de la promo sur votre `main` local.
#? Le contenu de `promo.html` est libre : seuls comptent le fichier, la branche et le suivi.
#? Variantes valables : `git checkout -b`, `git push -u origin HEAD`, ou `git branch -u origin/feature/promo-ete` après un push sans `-u`.
cd ~/boutique
git switch -c feature/promo-ete
echo "<h2>Promo d'été : -15 % sur les sacs</h2>" > promo.html
git add promo.html
git commit -m "Page de la promo d'été"
git push -u origin feature/promo-ete
#@ G5.2
#? On met d'abord `main` à jour avec `git pull`, pour fusionner dans la dernière version, qui contient le commit de Léa.
#? Comme `main` a avancé depuis la création de la branche de Thomas, `git merge` ne peut pas faire d'avance rapide : il crée un commit de fusion à deux parents.
#? Le piège : avec `pull.rebase=true`, un `git pull` lancé après une fusion locale non publiée rejoue les commits et fait disparaître la fusion ; d'où l'ordre pull, merge, push.
#? On fusionne `origin/feature/avis-clients` ; en revanche, `git pull origin feature/avis-clients` rebaserait votre `main` au-dessus de la branche au lieu de la fusionner.
cd ~/boutique
git switch main
git pull                                       # d'abord mettre main à jour (commit de Léa)
git merge --no-edit origin/feature/avis-clients   # vrai commit de fusion
git push
#@ G5.3
#? Une branche existe à deux endroits : `git push origin --delete` la supprime du dépôt partagé, `git branch -d` supprime votre copie locale si vous en aviez créé une.
#? `git fetch --prune` fait oublier à votre dépôt les branches distantes qui n'existent plus sur le dépôt partagé, comme celles que d'autres ont supprimées.
#? `git branch -d` refuse de supprimer une branche dont le travail n'est pas intégré : c'est une sécurité, que `-D` contourne.
#? Le `2>/dev/null` du corrigé masque seulement l'erreur si la branche locale n'avait jamais été créée.
#? Variante valable : `git push origin :feature/avis-clients` ; un push qui supprime une branche efface aussi sa branche distante connue chez vous.
cd ~/boutique
git push origin --delete feature/avis-clients
git branch -d feature/avis-clients 2>/dev/null   # seulement si elle avait été créée localement
git fetch --prune
#@ G5.4
#? `git fetch` rapatrie la branche de Léa sous la forme `origin/feature/code-promo-…`, que `git branch -r` affiche.
#? `git switch` suivi du nom exact, sans `origin/`, crée une branche locale du même nom qui suit automatiquement la branche distante.
#? Le piège : `git switch origin/…` refuse, et `git checkout origin/…` place sur une tête détachée, sans branche locale ; `git branch -u` permet d'établir le suivi après coup.
#? Le numéro de la branche et le code promo sont tirés au sort : ils diffèrent chez vous, et seul le code, sans guillemets, doit figurer dans le fichier.
#? Variantes valables : `git checkout <nom>`, `git checkout -b <nom> origin/<nom>` ou `git branch --track <nom> origin/<nom>`.
cd ~/boutique
git fetch
git branch -r                                  # origin/feature/code-promo-…
br=$(git branch -r --format='%(refname:lstrip=3)' | grep '^feature/code-promo-')
git switch "$br"                               # crée la branche locale qui suit origin/…
sed -n 's/^const CODE_PROMO = "\(.*\)";$/\1/p' code-promo.js > ~/code-promo.txt
git switch main
#@ G5.5
#? Une branche n'est qu'une étiquette : `git branch feature/panier-v2` en pose une nouvelle sur le dernier commit de Julien, sans s'y placer.
#? `git reset --hard` sur « Script du panier » recule ensuite l'étiquette `main` ; les commits du panier v2 ne sont pas perdus, puisque `feature/panier-v2` les désigne toujours.
#? Le nombre de commits de Julien est tiré au sort (de deux à quatre) : viser directement « Script du panier » évite de se tromper dans un `HEAD~n`.
#? L'ordre compte : un reset avant d'avoir posé la branche laisserait les commits sans étiquette, récupérables seulement par le reflog.
#? Réécrire est acceptable ici car rien n'est poussé ; un `git revert` aurait laissé les commits sur `main` au lieu de faire reculer l'étiquette.
#? Variante valable : `git switch -c feature/panier-v2` puis `git branch -f main <hash>`, qui déplace `main` sans quitter la nouvelle branche.
cd ~/panier-julien
git log --oneline                              # les commits « Panier v2 : … » au-dessus de « Script du panier »
base=$(git log --format=%h --grep='^Script du panier$')
git branch feature/panier-v2                   # une étiquette sur les commits de Julien
git reset --hard "$base"                       # main recule sur « Script du panier »
#@ G5.6
#? `git log main..feature/refonte -- js/formulaire.js` ne garde que les commits de la refonte qui modifient le formulaire : il n'y en a qu'un, le correctif, où qu'il soit.
#? Le message du correctif et sa place dans la refonte sont tirés au sort, et « Refonte : styles du formulaire » n'est qu'un leurre (il ne touche que la feuille de style) : fiez-vous au fichier modifié, ou vérifiez avec `git show`.
#? `git cherry-pick` rejoue ce seul commit sur `main` ; la copie reçoit un nouvel identifiant et `feature/refonte` reste intacte.
#? L'option `-x` ajoute « (cherry picked from commit …) » au message : c'est la traçabilité demandée par Nadia.
#? Le piège : fusionner ou rebaser la refonte apporterait sur `main` tout le travail inachevé de Thomas.
#? Une mention écrite à la main convient aussi, pourvu que le message cite l'identifiant du commit d'origine (7 caractères au moins).
cd ~/refonte
fix=$(git log --format=%h main..feature/refonte -- js/formulaire.js)
git switch main
git cherry-pick -x "$fix"
''',
    6: r'''
#@ G6.1
#? On met `main` à jour, puis on fusionne `origin/feature/tarifs` : le conflit vient de ce que Thomas (le libellé) et Nadia (le prix) ont modifié la même ligne.
#? La résolution garde une seule ligne qui combine les deux (par exemple « Sac à dos 40 L : 89 euros ») et supprime les trois marqueurs ; `git add` marque le conflit comme résolu et `git commit --no-edit` termine la fusion.
#? L'article, le libellé et le prix sont tirés au sort : le corrigé prend la ligne de Thomas (côté `HEAD`, en haut) et y met le prix de Nadia (côté de la branche, en bas).
#? Le piège : une branche publiée se fusionne, elle ne se rebase pas ; et avec `pull.rebase=true`, `git pull origin feature/tarifs` rebaserait votre `main` au lieu de fusionner.
#? Variantes valables : `git merge --continue` au lieu de `git commit`, `git pull --no-rebase origin feature/tarifs` au lieu du merge ; l'indentation de la ligne est libre.
cd ~/boutique
git switch main
git pull                                   # récupère d'abord le commit de Thomas
git merge origin/feature/tarifs            # CONFLICT (content): Merge conflict in tarifs.html
# Résolution : le libellé de Thomas et le prix de Nadia, sans les marqueurs de conflit
thomas=$(sed -n '/^<<<<<<< /{n;p;q}' tarifs.html)             # la ligne de main (Thomas)
nadia=$(grep -B 1 '^>>>>>>> ' tarifs.html | head -n 1)        # la ligne de la branche (Nadia)
prix=$(echo "$nadia" | sed 's/.* : \([0-9]*\) euros.*/\1/')
ligne=$(echo "$thomas" | sed "s/ : [0-9]* euros/ : $prix euros/")
sed -i "/^<<<<<<< /,/^>>>>>>> /c\\$ligne" tarifs.html
git add tarifs.html
git commit --no-edit
git push
#@ G6.2
#? `git merge --abort` ramène le dépôt à l'état d'avant la fusion : plus de fusion en cours, plus de marqueurs, et `main` toujours sur « Livraison le lundi ».
#? Le piège : résoudre le conflit puis commiter terminerait la fusion, alors que Julien n'en veut pas.
#? `git status` indiquait d'ailleurs la sortie ; `git reset --hard HEAD` annulerait aussi la fusion, mais en jetant sans prévenir toute modification non commitée.
cd ~/depot-julien
git merge --abort
#@ G6.3
#? Un commit de fusion a deux parents : le parent 1 est la branche sur laquelle on a fusionné, le parent 2 la branche fusionnée ; `git show` sur la fusion les liste dans cet ordre (ligne « Merge: »).
#? Selon les environnements (tirage au sort), Sophie a fusionné le paiement dans `main` (main = parent 1), ou fusionné `main` dans la branche du paiement avant d'avancer `main` dessus (main = parent 2) : il faut donc vérifier lequel des deux parents était `main`, celui qui n'a pas `paiement.js`.
#? `git revert -m <n>` crée un nouveau commit qui ramène le contenu à celui du parent n : tout ce que la branche a apporté disparaît (`paiement.js`, le lien), et ce qui a été commité ensuite (mentions légales) reste.
#? Les pièges : un `reset` ou un rebase réécriraient une histoire publiée, et le mauvais numéro de parent annulerait au contraire ce que `main` avait apporté (la page livraison).
#? Pour réintégrer la branche plus tard, il faudra annuler cette annulation : pour Git, ses commits sont déjà fusionnés.
#? Variante valable : `git revert --no-commit -m <n>`, puis un `git commit` dont le message cite la fusion annulée.
cd ~/boutique-prod
git log --oneline --graph
fusion=$(git log --merges --format=%h --grep='^Fusion du nouveau paiement$')
git show --no-patch "$fusion"              # Merge: <parent 1> <parent 2>
# Le parent de référence est main avant la fusion : celui qui n'a pas paiement.js
for n in 1 2; do git cat-file -e "$fusion^$n:paiement.js" 2>/dev/null || m=$n; done
git revert --no-edit -m "$m" "$fusion"
#@ G6.4
#? `git merge maj-stock` fusionne seul `README.md` (des lignes différentes des deux côtés) et s'arrête sur `stock.json`.
#? `git checkout --theirs stock.json` prend la version entière de la branche fusionnée (`--ours` désignerait `main`) ; `git add` puis `git commit --no-edit` terminent la fusion.
#? Le piège : `git merge -X theirs` ne tranche que les zones en conflit et garderait les retouches de Julien situées ailleurs dans le fichier, comme les lampes.
#? Les quantités du stock sont tirées au sort : elles peuvent différer dans votre environnement.
#? Variantes valables : `git checkout maj-stock -- stock.json` ou `git restore --theirs stock.json`, et `git merge --continue` pour terminer.
cd ~/reserve
git merge maj-stock                        # CONFLICT dans stock.json ; README.md fusionné seul
git checkout --theirs stock.json           # la version entière de la branche
git add stock.json
git commit --no-edit
''',
    7: r'''
#@ G7.1
#? `git stash` range le brouillon (modification d'un fichier suivi) et nettoie le répertoire de travail : on peut changer de branche sans rien commiter.
#? Sur `main`, on corrige et on commite ; de retour sur `feature/newsletter`, `git stash pop` réapplique le brouillon et le retire de la liste.
#? Le piège : `git stash apply` réapplique aussi, mais laisse l'entrée dans la liste ; il faudrait alors la supprimer avec `git stash drop`.
#? Commiter le brouillon « pour le mettre de côté » l'aurait fait entrer dans l'historique de la branche avant relecture.
#? Variante valable : corriger `main` dans un dossier temporaire créé par `git worktree add`, sans toucher au brouillon.
cd ~/atelier
git stash                                  # range le brouillon
git switch main
sed -i 's|04 76 00 00 0<|04 76 00 00 00<|' contact.html
git commit -am "Correction du numéro de téléphone"
git switch feature/newsletter
git stash pop                              # reprend le brouillon
#@ G7.2
#? `git commit --amend` remplace le dernier commit par un nouveau (nouveau hash, même parent) construit à partir de l'index actuel, qui contient donc `js/remise.js` ajouté juste avant.
#? L'option `-m` fixe le nouveau message ; sans elle, l'éditeur s'ouvre sur l'ancien.
#? On peut le faire parce que rien n'est poussé : amender un commit publié réécrirait une histoire partagée.
#? Le piège : un second commit pour le fichier oublié laisserait le message fautif et un commit en trop.
#? Variante valable : `git reset --soft HEAD~1`, puis un nouveau commit avec le fichier oublié et le bon message.
cd ~/corrections
git add js/remise.js
git commit --amend -m "Correction du calcul du panier"
#@ G7.3
#? Depuis `feature/filtres`, `git rebase main` rejoue ses deux commits au-dessus du `main` actuel ; ce sont des copies (nouveaux hash), et `main` ne bouge pas.
#? Les pièges : `git merge main` dans la branche créerait un commit de fusion, et lancer le rebase depuis `main` déplacerait la mauvaise branche.
#? Variante valable : `git rebase main feature/filtres`, qui change de branche et rebase en une seule commande.
#? La future fusion de la branche dans `main` sera une simple avance rapide (fast-forward).
cd ~/filtres
git switch feature/filtres
git rebase main
#@ G7.4
#? `git rebase -i main` ouvre la liste des cinq commits de la branche, du plus ancien au plus récent ; on la réorganise pour n'en garder que deux.
#? Chaque retouche rejoint le commit principal du fichier qu'elle modifie (`git show --stat` l'indique) : on la place juste en dessous et on remplace `pick` par `fixup`, pour qu'elle y fonde en abandonnant son message.
#? L'ordre des retouches et le fichier que chacune modifie sont tirés au sort : chez vous, ce n'est pas forcément « oups oubli » qu'il faut déplacer, ni vers le même commit que chez votre voisin.
#? Déplacer une retouche au-dessus d'un commit qui touche un autre fichier ne crée pas de conflit, et le contenu final reste identique ; l'ordre des retouches d'un même fichier, lui, doit être conservé.
#? `squash` fonctionnerait aussi, mais ouvrirait l'éditeur pour combiner les messages, qu'il faudrait ensuite nettoyer.
#? Le script du corrigé ne fait que réécrire cette liste à votre place, via `GIT_SEQUENCE_EDITOR` ; vous, vous la modifiez dans nano.
#? Variante valable : `git reset main`, puis deux commits (`contact.html`, puis `validation.js`) avec les bons messages : le contenu final est le même.
cd ~/contact
git log --oneline --stat main..feature/contact   # quel fichier chaque retouche modifie-t-elle ?
# L'étudiant fait « git rebase -i main » et modifie la liste dans nano ; ici, un script fait la même chose :
# chaque commit principal, suivi en fixup des retouches qui modifient le même fichier.
cat > /tmp/ordre-rebase.sh <<'EOF'
#!/bin/sh
{
  for principal in "Ajout du formulaire de contact" "Validation des champs du formulaire"; do
    ligne=$(grep " $principal\$" "$1")
    echo "$ligne"
    fichier=$(git show --name-only --format= "$(echo "$ligne" | cut -d ' ' -f 2)")
    grep -E '^pick [0-9a-f]+ (wip|faute de frappe|oups oubli)$' "$1" | while read -r cmd h msg; do
      if [ "$(git show --name-only --format= "$h")" = "$fichier" ]; then echo "fixup $h $msg"; fi
    done
  done
} > "$1.nouveau"
mv "$1.nouveau" "$1"
EOF
chmod +x /tmp/ordre-rebase.sh
GIT_SEQUENCE_EDITOR=/tmp/ordre-rebase.sh git rebase -i main
git log --oneline main..feature/contact
#@ G7.5
#? `git reset` sur le commit « Site » (mode `--mixed`, par défaut) recule la branche en gardant les modifications des commits retirés dans le répertoire de travail, non indexées.
#? Le nombre de commits ratés est tiré au sort (de deux à quatre) : viser directement « Site », ou compter les commits avec `git log --oneline` avant un `HEAD~n`, évite de se tromper.
#? On recommite ensuite seulement `faq.html` : `notes-perso.txt` redevient un simple fichier non suivi, toujours présent sur le disque.
#? Le piège : `--hard` jetterait les modifications, notes comprises ; `--soft` convient aussi, à condition de retirer les notes de l'index avec `git restore --staged notes-perso.txt`.
#? Ignorer ensuite les notes (dans `.git/info/exclude`, par exemple) est également accepté par la vérification.
cd ~/faq-julien
git log --oneline                          # les commits de Julien au-dessus de « Site »
git reset "$(git log --format=%h --grep='^Site$')"   # --mixed : les modifications restent, non indexées
git add faq.html
git commit -m "Page FAQ"
git status                                 # ?? notes-perso.txt
#@ G7.6
#? Un simple `git stash` ne range que les fichiers suivis : `bandeau.html`, tout neuf, reste sur le disque, et `git switch main` refuse car il écraserait le `bandeau.html` de `main`.
#? `git stash -u` (`--include-untracked`) range aussi les fichiers non suivis : le répertoire de travail est propre et le changement de branche passe.
#? Après la correction commitée sur `main`, `git stash pop` sur `feature/bandeau` restaure les deux fichiers et vide la liste.
#? Le corrigé rejoue d'abord l'essai voué à l'échec pour montrer le refus ; vous pouviez utiliser `git stash -u` directement.
#? Variantes valables : `git stash push -u -m "bandeau"` (le message aide à retrouver l'entrée), ou `git stash apply` suivi de `git stash drop`.
cd ~/bandeau
git stash || true
git switch main || true                    # refusé : bandeau.html (non suivi) serait écrasé
git stash pop || true                      # (on annule le premier essai)
git stash -u                               # range aussi les fichiers non suivis
git switch main
sed -i 's/contact@cimes-sentier\.fr/contact@cimes-sentiers.fr/' contact.html
git commit -am "Correction de l'adresse de contact"
git switch feature/bandeau
git stash pop
''',
    8: r'''
#@ G8.1
#? `git bisect` coupe l'intervalle en deux à chaque étape : entre le premier commit (bon) et le dernier (mauvais), six tests au plus suffisent pour 36 commits.
#? `git bisect run ./tests.sh` automatise la recherche : un code de retour 0 signifie « bon », de 1 à 127 (sauf 125) « mauvais ».
#? Le piège : il faut enregistrer `git bisect log` avant `git bisect reset`, qui termine la recherche et efface son journal.
#? `git log -S` ne sert à rien ici, puisque Marc réécrit la formule à chaque commit ; et la position du bug est tirée au sort, votre commit fautif diffère donc de celui d'un camarade.
#? À la fin de la recherche, `refs/bisect/bad` désigne le premier commit mauvais : c'est ce que le corrigé écrit dans `~/commit-fautif.txt`.
#? Variantes valables : `git bisect start HEAD <premier commit>`, la recherche à la main (good ou bad après chaque `./tests.sh`), ou les termes old / new.
cd ~/calculs
git bisect start
git bisect bad                                       # la version actuelle est fausse
git bisect good "$(git rev-list --max-parents=0 HEAD)"   # le premier commit était juste
git bisect run ./tests.sh
git rev-parse refs/bisect/bad > ~/commit-fautif.txt  # « … is the first bad commit »
git bisect log > ~/bisect.log
git bisect reset
#@ G8.2
#? L'étiquette `v1.0` de Julien est légère et publiée ; si un fetch l'a rapportée dans votre `~/boutique`, Git ne la remplacera jamais d'office.
#? On la supprime localement (`git tag -d`), on crée une étiquette annotée (`-a -m` : auteur, date et message) sur `main` à jour, puis on remplace celle du dépôt partagé avec `git push --force origin v1.0`.
#? Ce `--force` ne vise que l'étiquette, pas une branche : c'est l'un des rares cas légitimes, à annoncer à l'équipe.
#? Variante valable : `git push origin --delete v1.0` puis `git push origin v1.0`.
#? Autres pièges : un simple `git push` n'envoie pas les étiquettes, et oublier le `git pull` placerait l'étiquette sur un `main` sans « Préparation de la mise en production ».
cd ~/boutique
git switch main
git pull
git tag -d v1.0 2>/dev/null                          # l'étiquette légère de Julien, rapportée par le fetch
git tag -a v1.0 -m "Première version en production"
git push --force origin v1.0                         # remplace l'étiquette publiée
#@ G8.3
#? `reset --hard` n'a pas détruit les commits : il a seulement déplacé l'étiquette `main`, et le reflog garde la trace de toutes les positions de `HEAD`.
#? On repère dans `git reflog` la ligne du commit « Conclusion », la dernière position de `HEAD` avant la perte ; `git branch sauvetage` pose dessus une étiquette qui le met à l'abri.
#? Ce que Julien a fait ensuite est tiré au sort (rien, d'autres commits, un second reset, un détour par une autre branche) : la conclusion n'est donc pas forcément `HEAD@{1}`. Son hash, lu dans le reflog, ne trompe pas.
#? Variante : `git reset --hard` sur ce hash remettrait `main` dessus, mais Julien demande une branche `sauvetage` (et il perdrait ce qu'il a fait depuis).
#? Variante valable : `git switch -c sauvetage <hash>` (ou `git checkout -b`), qui crée la branche et s'y place.
cd ~/rapport
git reflog                                 # repérer la ligne du commit « Conclusion »
perdu=$(git log -g --format='%H %s' | awk '$2 == "Conclusion" { print $1; exit }')
git branch sauvetage "$perdu"
''',
    9: r'''
#@ G9.1
#? `.gitignore` ne s'applique qu'aux fichiers non suivis : `.env`, commité avant la règle, reste suivi et ses modifications apparaissent toujours.
#? `git rm --cached .env` le retire de l'index sans le supprimer du disque ; le commit qui suit enregistre sa sortie du dépôt, et la règle existante prend alors effet.
#? Le piège : `git update-index --assume-unchanged` ne fait que masquer les modifications ; le fichier reste suivi et présent dans les commits.
#? L'ancienne clé reste dans l'historique : en situation réelle, il faudrait la révoquer, puis nettoyer l'historique comme en G9.3.
cd ~/api-meteo
git status                                 # .env modifié, alors qu'il est dans .gitignore : il est suivi
git rm --cached .env
git commit -m "Ne plus suivre le fichier .env"
#@ G9.2
#? `*.log` (sans barre oblique) s'applique à tous les niveaux, et `!logs/LISEZMOI.log` le ré-inclut, car son dossier `logs/` n'est pas lui-même exclu.
#? Pour `build`, on exclut le contenu (`/build/*`) et non le dossier (`/build/`) : Git n'entre jamais dans un dossier exclu, et `!/build/.gitkeep` n'aurait alors aucun effet.
#? `node_modules/` (barre finale seulement) vise tous les dossiers de ce nom, à tout niveau ; `/config/local.ini`, ancré à la racine, épargne `src/local.ini`.
#? `config/local.ini` sans barre initiale fonctionnerait aussi : un motif qui contient une barre au milieu est déjà relatif à l'emplacement du `.gitignore`.
#? `git check-ignore -v` indique quelle règle ignore un chemin : c'est l'outil pour mettre au point un `.gitignore` ; les noms des journaux et fichiers de build sont tirés au sort.
cd ~/catalogue-web
cat > .gitignore <<'EOF'
*.log
!logs/LISEZMOI.log
/build/*
!/build/.gitkeep
node_modules/
/config/local.ini
EOF
git check-ignore -v build/.gitkeep src/local.ini config/local.ini || true
git add .
git commit -m "Règles d'ignorance du catalogue"
#@ G9.3
#? Supprimer le fichier dans un nouveau commit ne l'efface pas des commits précédents : il faut réécrire tous les commits qui le contiennent.
#? `git filter-branch --index-filter` retire le fichier de chaque commit de `main` ; sa sauvegarde `refs/original/` conserve l'ancienne histoire, d'où le `git update-ref -d`.
#? Variante recommandée : `git filter-repo --force --invert-paths --path config/api.env`, qui retire le distant `origin` par sécurité : il faut le redéclarer avant de publier.
#? `git push --force` est ici exceptionnel et justifié : la nouvelle histoire doit remplacer l'ancienne sur le dépôt partagé (ce qui met aussi à jour `origin/main`), en prévenant l'équipe.
#? Le premier geste reste de révoquer la clé, car les clones déjà faits la conservent ; `git log --all -p | grep` vérifie ensuite qu'aucune référence ne la contient plus.
#? Variante valable pour une histoire courte : `git rebase -i` avec `edit` sur le commit de la clé, `git rm --cached`, `git commit --amend`, puis `git rebase --skip` du commit de suppression devenu vide.
cd ~/meteo
git log --all -p | grep -c API_KEY=                  # la clé est toujours dans l'historique
git filter-branch --index-filter 'git rm -q --cached --ignore-unmatch config/api.env' -- main
git update-ref -d refs/original/refs/heads/main      # la sauvegarde de filter-branch contient la clé
echo "config/api.env" > .gitignore
git add .gitignore
git commit -m "Ignorer la configuration de l'API"
git push --force origin main                         # remplace l'histoire publiée (et met à jour origin/main)
git log --all -p | grep -c API_KEY= || true          # 0
#@ G9.4
#? Git exécute `.git/hooks/pre-commit` avant chaque commit, à condition qu'il porte exactement ce nom et soit exécutable (`chmod +x`) ; un code de retour non nul annule le commit.
#? `git diff --cached` examine l'index, c'est-à-dire ce qui va réellement partir dans le commit : un fichier secret non indexé qui traîne dans le dossier ne bloque donc rien.
#? Le motif `^\+` ne retient que les lignes ajoutées : retirer une ligne contenant `API_KEY=` reste permis, et `PASSWORD=` attrape aussi `DB_PASSWORD=`.
#? Un hook ne voyage pas avec le dépôt et `git commit --no-verify` le contourne : c'est un garde-fou, pas une sécurité absolue.
cat > ~/meteo/.git/hooks/pre-commit <<'EOF'
#!/bin/sh
# Refuse tout commit dont les lignes ajoutées (index) contiennent API_KEY= ou PASSWORD=
if git diff --cached | grep -qE '^\+.*(API_KEY|PASSWORD)='; then
  echo "Commit refusé : secret détecté (API_KEY= ou PASSWORD=)." >&2
  exit 1
fi
exit 0
EOF
chmod +x ~/meteo/.git/hooks/pre-commit
''',
}
