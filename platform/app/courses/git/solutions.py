"""Corrigé du parcours Git : un script par étape, exécuté en tant qu'« etudiant » par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (affichée aux admins dans la plateforme).
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
echo "brouillon-perso.txt" > .gitignore
git add .gitignore
git commit -m "Ignorer le brouillon personnel"
''',
    2: r'''
#@ G2.1
cd ~/archives-site
git log -S "0.055" --format=%h -- js/panier.js > ~/commit-tva.txt
#@ G2.2
# Le commit qui a supprimé le fichier ; le fichier existe encore dans son parent (^)
suppr=$(git log --diff-filter=D --format=%h -- data/fournisseurs.csv)
git restore --source="$suppr^" data/fournisseurs.csv
git add data/fournisseurs.csv
git commit -m "Restauration du fichier des fournisseurs"
#@ G2.3
git revert --no-edit "$(cat ~/commit-tva.txt)"
''',
    3: r'''
#@ G3.1
cd ~
git clone /srv/git/boutique.git
#@ G3.2
cd ~/boutique
sed -i 's/Randonée/Randonnée/' index.html
git commit -am "Correction de la faute sur la page d'accueil"
git push
''',
    4: r'''
#@ G4.1
git config --global pull.rebase true
#@ G4.2
cd ~/boutique
echo "- $(git config user.name) (admin système)" >> EQUIPE.md
git commit -am "Ajout de $(git config user.name) dans l'équipe"
git push     # refusé : Nadia a publié entre-temps
git pull     # rejoue notre commit au-dessus du sien (pull.rebase)
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
git switch main
git pull
git merge --no-edit origin/feature/avis-clients
git push
#@ G5.3
git push origin --delete feature/avis-clients
git branch -d feature/avis-clients 2>/dev/null   # seulement si elle avait été créée localement
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
''',
    8: r'''
#@ G8.1
cd ~/calculs
git bisect start
git bisect bad                                       # la version actuelle est fausse
git bisect good "$(git rev-list --max-parents=0 HEAD)"   # le premier commit était juste
git bisect run ./tests.sh
git rev-parse refs/bisect/bad > ~/commit-fautif.txt  # « … is the first bad commit »
git bisect reset
#@ G8.2
cd ~/boutique
git switch main
git pull
git tag -a v1.0 -m "Première version en production"
git push origin v1.0
#@ G8.3
cd ~/rapport
git reflog                                 # HEAD@{1} : le commit « Conclusion », juste avant le reset
git branch sauvetage "HEAD@{1}"
''',
}
