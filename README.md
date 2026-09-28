# Linux CLI Lab

Plateforme d'apprentissage de la ligne de commande Linux (BTS SIO / DevOps) : chaque étudiant dispose d'un
conteneur Ubuntu personnel accessible depuis le navigateur, d'un cours par étape et d'exercices validés
automatiquement.

## Architecture

| Composant | Rôle |
|---|---|
| `platform/` | Application FastAPI : comptes, sessions, terminal WebSocket (xterm.js), validation, tableau de bord enseignant |
| `platform/app/exercises.py` | **Source unique** des étapes : cours, mises en place, exercices, vérifications, indices |
| `platform/app/runner.py` | Construit les commandes de mise en place et de vérification (partagé avec les tests) |
| `lab/` | Image `linux-lab` des conteneurs étudiants : utilisateur `etudiant` (sudoer), sshd, cron, rsyslog |
| `platform/tests/` | Solutions de référence et banc de test de tous les exercices |
| `step-*/` | Tutoriel texte d'origine (historique, non utilisé par la plateforme) |

Fonctionnement d'une étape :

1. À l'ouverture d'une étape, la plateforme exécute sa **mise en place** dans le conteneur (fichiers générés
   aléatoirement, processus, pannes à réparer…). Les réponses attendues sont renvoyées à la plateforme et
   stockées en base, **jamais dans le conteneur**.
2. L'étudiant travaille dans son terminal en tant qu'`etudiant` et utilise `sudo` (mot de passe `etudiant`)
   pour l'administration.
3. Les vérifications tournent en root via `docker exec`. Elles testent le **comportement** (ex. « bob peut
   écrire, intrus ne peut pas lister ») plutôt que de simples existences de fichiers. La première vérification
   en échec renvoie un message explicite.
4. Les exercices marqués `manual` (qui exécutent des scripts de l'étudiant) ne sont testés que sur clic ; les
   autres sont vérifiés automatiquement toutes les 5 s.
5. Chaque indice débloqué coûte 1 point (minimum 1 point par exercice réussi).

## Scénario

L'étudiant est **admin système junior chez Cimes & Sentiers**, une PME fictive de vente de matériel de randonnée.
Les exercices arrivent sous forme de **tickets** envoyés par des collègues récurrents (Sophie la DSI, Léa l'admin
senior qui donne les indices, Thomas le développeur, Aminata de la comptabilité, Julien le stagiaire) ; le cours de
chaque étape sert de documentation. Personnages et introduction : `CHARACTERS` et `SCENARIO_INTRO` dans
`exercises.py`. Un exercice sans clé `ticket` s'affiche au format classique (étapes 6 à 25 pour l'instant).

## Parcours (25 étapes, 119 exercices, 422 points)

1. Navigation · 2. Manuel et chemins · 3. Fichiers et dossiers · 4. Liens · 5. Recherche (find, grep) ·
6. Redirections et pipes · 7. Édition (nano, vim, sed) · 8. Expressions régulières · 9. Filtrage (awk, sort, uniq) ·
10. Utilisateurs, groupes, permissions · 11. sudo et processus · 12. Cas pratique famille · 13. Paquets (apt, dpkg) ·
14. Disques · 15. Environnement, PATH, alias · 16. Archives · 17. Scripts Bash · 18. cron · 19. Supervision ·
20. Logs et logrotate · 21. Réseau · 22. SSH (clés, config, scp, durcissement) · 23. Sécurité (audit et correction) ·
24. **Dépannage** (script CRLF, disque plein, SSH refusé, cron fantôme, service en échec) ·
25. Intégration finale (serveur web, sauvegardes avec rotation, supervision, accès SSH)

## Déploiement

```bash
cp .env.example .env        # puis définir ADMIN_EMAIL / ADMIN_PASSWORD
docker compose up -d --build
```

La plateforme écoute sur le port 8080. Le compte enseignant (`/dashboard`) est créé au premier démarrage avec
`ADMIN_EMAIL` / `ADMIN_PASSWORD` ; si `ADMIN_PASSWORD` est défini, il est réappliqué à chaque démarrage (pratique
pour changer le mot de passe). Sans `ADMIN_PASSWORD`, un mot de passe aléatoire est affiché une fois dans
`docker compose logs platform`.

Variables utiles : `IDLE_TIMEOUT` (secondes avant l'arrêt d'un conteneur inactif, 7200 par défaut — le travail
est conservé), `COOKIE_SECURE=1` derrière un reverse proxy HTTPS.

Isolation des étudiants : réseau `linux-lab-students` sans communication entre conteneurs, sshd limité à
`localhost`, 256 Mo de RAM, 50 % d'un CPU, 256 processus maximum.

Seule l'étape 13 (apt, wget) nécessite un accès Internet depuis les conteneurs.

## Modifier ou ajouter des exercices

Tout se passe dans `platform/app/exercises.py` (le format est documenté en tête du fichier), avec la solution
correspondante dans `platform/tests/solutions.py`. Puis :

```bash
docker build -t linux-lab ./lab
python platform/tests/run_lab_tests.py            # toutes les étapes (~5 min, dont cron)
python platform/tests/run_lab_tests.py --only 1-8 --skip 13
```

Le banc vérifie, pour chaque étape jouée dans l'ordre du parcours, qu'**aucun exercice ne passe avant d'être
fait** puis que **tous passent après la solution de référence**.

Si les identifiants d'exercices changent de sens, incrémentez `EXERCISES_VERSION` : au démarrage, la
progression existante est archivée dans la table `progress_archive` et les conteneurs des étudiants sont
recréés à leur prochaine connexion.
