"""Corrigé du parcours Git : un script par étape, exécuté en tant qu'« etudiant » par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
Aucun éditeur interactif : les messages sont passés avec -m / --no-edit, et le rebase interactif reçoit sa liste
de commits par GIT_SEQUENCE_EDITOR (un étudiant, lui, la modifie dans nano).
"""

SOLUTIONS = {
    1: r'''
#@ G1.1
git config --global user.name "Camille Martin"
git config --global user.email "camille.martin@cimes-sentiers.fr"
git config --global init.defaultBranch main
#@ G1.2
cd ~/procedures
git init
git add sauvegarde.md comptes.md imprimantes.md
git commit -m "Procédures d'exploitation"
#@ G1.3
cd ~/procedures
echo "brouillon-perso.txt" > .gitignore
git add .gitignore
git commit -m "Ignorer le brouillon personnel"
#@ G1.4
cd ~/inventaire
git status                     # stock.csv ET README.md sont modifiés
git diff                       # README.md : l'essai de Julien
git add stock.csv
git commit -m "Inventaire d'octobre"
git restore README.md          # jette l'essai (retour à la version du dernier commit)
#@ G1.5
cd ~/boutique-js
git diff                       # deux morceaux : les centimes (en haut), le debug (en bas)
printf 'y\nn\n' | git add -p js/app.js    # y : les centimes, n : le debug
git diff --staged              # contrôle : seule la correction est indexée
git commit -m "Affichage des prix avec les centimes"
''',
    2: r'''
#@ G2.1
cd ~/archives-site
git log -S "0.055" --oneline                   # deux commits : les livres (légitime) et le panier
git log -S "0.055" --oneline -- js/panier.js > ~/commit-tva.txt
#@ G2.2
cd ~/archives-site
# Le commit qui a supprimé le fichier ; le fichier existe encore dans son parent (^)
suppr=$(git log --diff-filter=D --format=%h -- data/fournisseurs.csv)
git restore --source="$suppr^" data/fournisseurs.csv
git add data/fournisseurs.csv
git commit -m "Restauration du fichier des fournisseurs"
#@ G2.3
cd ~/archives-site
git revert --no-edit "$(awk '{ print $1 }' ~/commit-tva.txt)"
#@ G2.4
cd ~/archives-site
git blame js/port.js                           # tout est attribué à « Mise en forme du code »…
git blame -w js/port.js                        # … -w ignore les changements d'espaces
git blame -w --porcelain -L '/standard/,+1' js/port.js | head -n 1 | cut -d ' ' -f 1 > ~/commit-frais.txt
#@ G2.5
cd ~/archives-site
seuil=$(git log --format=%h --grep='^Seuil de livraison relevé$')
git revert --no-edit "$seuil"                  # CONFLICT : la ligne a été retouchée depuis
# Résolution : la valeur d'origine (60) avec le commentaire précisé ensuite
sed -i '/^<<<<<<< /,/^>>>>>>> /c\const SEUIL_LIVRAISON = 60; // livraison offerte à partir de ce montant (TTC)' js/livraison.js
git add js/livraison.js
GIT_EDITOR=true git revert --continue
''',
    3: r'''
#@ G3.1
cd ~
git clone /srv/git/boutique.git
#@ G3.2
cd ~/boutique
sed -i 's/Tout le matériel de Randonée/Tout le matériel de randonnée/' index.html
git diff
git commit -am "Correction des fautes de la page d'accueil"
git push
#@ G3.3
cd ~/vitrine
git push || true                               # « does not appear to be a git repository »
git remote -v                                  # vitrin.git : faute de frappe
git remote set-url origin /srv/git/vitrine.git
git push -u origin main
''',
    4: r'''
#@ G4.1
git config --global pull.rebase true
git config --global rebase.autoStash true
#@ G4.2
cd ~/boutique
echo "- $(git config user.name) (admin système)" >> EQUIPE.md
git commit -am "Ajout de $(git config user.name) dans l'équipe"
git push || true   # refusé : l'équipe a publié entre-temps
git pull           # rejoue notre commit au-dessus des leurs (pull.rebase)
git push
#@ G4.3
cd ~/poste-sophie
git fetch                                      # télécharge sans intégrer
git status                                     # « Your branch is behind 'origin/main' by … commits »
git rev-list --count main..origin/main > ~/nouveaux-commits.txt
#@ G4.4
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
cd ~/boutique
git switch -c feature/promo-ete
echo "<h2>Promo d'été : -15 % sur les sacs</h2>" > promo.html
git add promo.html
git commit -m "Page de la promo d'été"
git push -u origin feature/promo-ete
#@ G5.2
cd ~/boutique
git switch main
git pull                                       # d'abord mettre main à jour (commit de Léa)
git merge --no-edit origin/feature/avis-clients   # vrai commit de fusion
git push
#@ G5.3
cd ~/boutique
git push origin --delete feature/avis-clients
git branch -d feature/avis-clients 2>/dev/null   # seulement si elle avait été créée localement
git fetch --prune
#@ G5.4
cd ~/boutique
git fetch
git branch -r                                  # origin/feature/code-promo-…
br=$(git branch -r --format='%(refname:lstrip=3)' | grep '^feature/code-promo-')
git switch "$br"                               # crée la branche locale qui suit origin/…
sed -n 's/^const CODE_PROMO = "\(.*\)";$/\1/p' code-promo.js > ~/code-promo.txt
git switch main
#@ G5.5
cd ~/panier-julien
git branch feature/panier-v2                   # une étiquette sur les commits de Julien
git reset --hard HEAD~2                        # main recule de deux commits
#@ G5.6
cd ~/refonte
fix=$(git log --format=%h --grep='^Échappement des champs du formulaire$' feature/refonte)
git switch main
git cherry-pick -x "$fix"
''',
    6: r'''
#@ G6.1
cd ~/boutique
git switch main
git pull                                   # récupère d'abord le commit de Thomas
git merge origin/feature/tarifs            # CONFLICT (content): Merge conflict in tarifs.html
# Résolution : le libellé de Thomas et le prix de Nadia, sans les marqueurs de conflit
sed -i '/^<<<<<<< /,/^>>>>>>> /c\  <li>Sac à dos 40 L : 89 euros</li>' tarifs.html
git add tarifs.html
git commit --no-edit
git push
#@ G6.2
cd ~/depot-julien
git merge --abort
#@ G6.3
cd ~/boutique-prod
git log --oneline --graph
fusion=$(git log --merges --format=%h --grep='^Fusion du nouveau paiement$')
git revert --no-edit -m 1 "$fusion"        # parent 1 : main avant la fusion
#@ G6.4
cd ~/reserve
git merge maj-stock                        # CONFLICT dans stock.json ; README.md fusionné seul
git checkout --theirs stock.json           # la version entière de la branche
git add stock.json
git commit --no-edit
''',
    7: r'''
#@ G7.1
cd ~/atelier
git stash                                  # range le brouillon
git switch main
sed -i 's|04 76 00 00 0<|04 76 00 00 00<|' contact.html
git commit -am "Correction du numéro de téléphone"
git switch feature/newsletter
git stash pop                              # reprend le brouillon
#@ G7.2
cd ~/corrections
git add js/remise.js
git commit --amend -m "Correction du calcul du panier"
#@ G7.3
cd ~/filtres
git switch feature/filtres
git rebase main
#@ G7.4
cd ~/contact
# L'étudiant fait « git rebase -i main » et modifie la liste dans nano ; ici, un script fait la même chose :
# le formulaire, ses trois retouches en fixup (oups oubli remonté), puis la validation.
cat > /tmp/ordre-rebase.sh <<'EOF'
#!/bin/sh
{
  grep ' Ajout du formulaire de contact$' "$1"
  grep -E ' (wip|faute de frappe|oups oubli)$' "$1" | sed 's/^pick/fixup/'
  grep ' Validation des champs du formulaire$' "$1"
} > "$1.nouveau"
mv "$1.nouveau" "$1"
EOF
chmod +x /tmp/ordre-rebase.sh
GIT_SEQUENCE_EDITOR=/tmp/ordre-rebase.sh git rebase -i main
git log --oneline main..feature/contact
#@ G7.5
cd ~/faq-julien
git reset HEAD~2                           # --mixed : les modifications restent, non indexées
git add faq.html
git commit -m "Page FAQ"
git status                                 # ?? notes-perso.txt
#@ G7.6
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
cd ~/calculs
git bisect start
git bisect bad                                       # la version actuelle est fausse
git bisect good "$(git rev-list --max-parents=0 HEAD)"   # le premier commit était juste
git bisect run ./tests.sh
git rev-parse refs/bisect/bad > ~/commit-fautif.txt  # « … is the first bad commit »
git bisect log > ~/bisect.log
git bisect reset
#@ G8.2
cd ~/boutique
git switch main
git pull
git tag -d v1.0 2>/dev/null                          # l'étiquette légère de Julien, rapportée par le fetch
git tag -a v1.0 -m "Première version en production"
git push --force origin v1.0                         # remplace l'étiquette publiée
#@ G8.3
cd ~/rapport
git reflog                                 # HEAD@{1} : le commit « Conclusion », juste avant le reset
git branch sauvetage "HEAD@{1}"
''',
    9: r'''
#@ G9.1
cd ~/api-meteo
git status                                 # .env modifié, alors qu'il est dans .gitignore : il est suivi
git rm --cached .env
git commit -m "Ne plus suivre le fichier .env"
#@ G9.2
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
