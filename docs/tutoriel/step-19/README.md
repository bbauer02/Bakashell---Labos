# Etape 19

## Exercice d'intégration finale : Administrer un serveur web

Cet exercice final met en pratique toutes les compétences acquises dans ce tutoriel. Vous allez simuler la mise en place et l'administration d'un serveur web.

### Scénario

Vous êtes l'administrateur système d'une petite entreprise. On vous demande de :

  1. **Préparer l'environnement** : créer les utilisateurs et l'arborescence du projet web
  2. **Installer les outils nécessaires** et télécharger les ressources du site
  3. **Écrire un script de sauvegarde** automatisé
  4. **Planifier** l'exécution automatique de la sauvegarde
  5. **Mettre en place un rapport de surveillance** du système

### Ce que vous devez faire

#### 1. Préparer l'environnement
  * Créer un utilisateur `webmaster` membre du groupe `www`
  * Créer l'arborescence `/var/www/monsite/` avec les sous-dossiers `html`, `logs` et `backup`
  * Le dossier `/var/www/monsite` doit appartenir au groupe `www` avec les permissions 775

#### 2. Créer le contenu web
  * Créer un fichier `index.html` dans le dossier `html` avec du contenu
  * Créer un fichier `access.log` dans le dossier `logs` simulant des logs

#### 3. Script de sauvegarde
  * Écrire un script `/home/webmaster/backup.sh` qui :
    - Crée une archive `.tar.gz` du dossier `html` dans le dossier `backup`
    - Génère un rapport de l'espace disque
  * Le script doit être exécutable

#### 4. Planifier la sauvegarde
  * Ajouter une tâche cron pour le script de backup

#### 5. Rapport de surveillance
  * Créer un script `/home/webmaster/monitoring.sh` qui génère un rapport contenant :
    - L'espace disque
    - La mémoire
    - La liste des processus
  * Sauvegarder le rapport dans `/var/www/monsite/logs/monitoring.txt`

### Compétences mobilisées

  * Gestion d'utilisateurs et groupes (étapes 4-6)
  * Permissions (étape 4)
  * Édition de fichiers (étape 11)
  * Archivage (étape 14)
  * Scripting bash (étape 16)
  * Tâches planifiées (étape 17)
  * Surveillance système (étape 18)
  * Redirections et pipes (étape 10)

>Cet exercice reprend l'ensemble des compétences du tutoriel. Prenez le temps de bien lire chaque consigne et de vérifier votre travail avec `check 19`.

Félicitations d'être arrivé jusqu'ici ! 🎉
