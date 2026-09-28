# Linux CLI Lab

Plateforme d'apprentissage (BTS SIO / DevOps) : chaque étudiant dispose, dans son navigateur, d'un conteneur
personnel, d'un cours par étape et d'exercices validés automatiquement. Trois parcours :

| Parcours | URL | Contenu |
|---|---|---|
| **Linux en ligne de commande** | `/lab/linux` | 25 étapes, 119 exercices, 422 points — terminal Ubuntu |
| **Tests unitaires avec Jest** (niveau avancé) | `/lab/jest` | 10 journées, 21 exercices, 103 points — éditeur de code + terminal Node |
| **Docker : conteneuriser la boutique** (révision des bases) | `/lab/docker` | 8 journées, 21 exercices, 87 points — un moteur Docker par étudiant + éditeur |

## Organisation : catalogue et classes

- Après connexion, l'étudiant arrive sur **son catalogue** (`/catalogue`) : les labos ouverts à ses classes, avec sa
  progression dans chacun.
- L'enseignant (compte admin) gère les **classes** sur `/admin/classes` : il coche les labos ouverts à chaque classe et
  ajoute ou retire des étudiants. Chaque classe a un **code d'inscription** (ex. `QTQ-V95`) que les étudiants saisissent
  à l'inscription ou depuis leur catalogue. Un étudiant peut appartenir à plusieurs classes.
- L'accès est contrôlé côté serveur (pages, API, terminal, éditeur, indices). Un compte admin voit tous les labos, et
  un bouton « Voir la correction » sur chaque exercice.
- Le tableau de bord (`/dashboard`) se filtre par parcours et par classe, et se met à jour en temps réel (présence,
  progression, élèves bloqués, fil d'activité).

## Architecture

| Composant | Rôle |
|---|---|
| `platform/` | Application FastAPI : comptes, sessions, terminal WebSocket (xterm.js), éditeur (Monaco), validation, tableau de bord |
| `platform/app/courses.py` | Registre des parcours (image, ressources, catalogue, version) |
| `platform/app/exercises.py` | Catalogue du parcours Linux : cours, mises en place, exercices, vérifications, indices |
| `platform/app/jest_course.py` | Catalogue du parcours Jest |
| `platform/app/docker_course.py` | Catalogue du parcours Docker |
| `platform/app/scenario.py` | Entreprise fictive et personnages communs aux parcours |
| `platform/app/runner.py` | Construit les commandes de mise en place et de vérification (partagé avec les tests) |
| `lab/` | Image `linux-lab` : utilisateur `etudiant` (sudoer), sshd, cron, rsyslog |
| `jest-lab/` | Image `jest-lab` : Node 20 + Jest, code de référence, mutants, tests cachés, correcteur (`verifier.js`) |
| `docker-lab/` | Image `docker-lab` : moteur Docker complet (docker:dind), images de base préchargées, projet de la boutique |
| `platform/app/solutions/` | Corrigés de référence (un script par étape, un repère `#@ <exercice>` par exercice), visibles par les admins |
| `platform/tests/` | Banc de test des parcours |
| `step-*/` | Tutoriel texte d'origine (historique, non utilisé par la plateforme) |

Chaque étudiant a un conteneur **par parcours** (`lab-student-<id>`, `lab-jest-<id>`, `lab-docker-<id>`), créé à sa
première visite.

Fonctionnement d'une étape :

1. À l'ouverture d'une étape, la plateforme exécute sa **mise en place** dans le conteneur (fichiers générés
   aléatoirement, processus, pannes à réparer, code livré…). Les réponses attendues sont renvoyées à la
   plateforme et stockées en base, **jamais dans le conteneur**.
2. L'étudiant travaille en tant qu'`etudiant` (avec `sudo`, mot de passe `etudiant`, dans le parcours Linux).
3. Les vérifications tournent en root via `docker exec` et testent le **comportement**. La première
   vérification en échec renvoie un message explicite, éventuellement détaillé (valeurs attendues, défaut non
   détecté…).
4. Les exercices marqués `manual` (qui exécutent du code de l'étudiant) ne sont testés que sur clic ; dans le
   parcours Linux, les autres sont vérifiés automatiquement toutes les 5 s.
5. Chaque indice débloqué coûte 1 point (minimum 1 point par exercice réussi).

## Scénario

L'étudiant travaille chez **Cimes & Sentiers**, une PME fictive de vente de matériel de randonnée. Les exercices
arrivent sous forme de **tickets** envoyés par des collègues récurrents : Sophie (DSI), Léa (admin senior, mentore
du parcours Linux), Nadia (lead développeuse, mentore du parcours Jest), Thomas (développeur), Aminata
(comptabilité), Julien (stagiaire). Un exercice sans clé `ticket` s'affiche au format classique (parcours Linux,
étapes 6 à 25 pour l'instant).

## Parcours Linux

1. Navigation · 2. Manuel et chemins · 3. Fichiers et dossiers · 4. Liens · 5. Recherche (find, grep) ·
6. Redirections et pipes · 7. Édition (nano, vim, sed) · 8. Expressions régulières · 9. Filtrage (awk, sort, uniq) ·
10. Utilisateurs, groupes, permissions · 11. sudo et processus · 12. Cas pratique · 13. Paquets (apt, dpkg) ·
14. Disques · 15. Environnement, PATH, alias · 16. Archives · 17. Scripts Bash · 18. cron · 19. Supervision ·
20. Logs et logrotate · 21. Réseau · 22. SSH (clés, config, scp, durcissement) · 23. Sécurité (audit et correction) ·
24. **Dépannage** (script CRLF, disque plein, SSH refusé, cron fantôme, service en échec) ·
25. Intégration finale (serveur web, sauvegardes avec rotation, supervision, accès SSH)

## Parcours Jest

L'étudiant teste le code métier de la boutique (`~/boutique`) : 1. La CI est rouge (toBe, toBeCloseTo, scripts
npm, arrondis) · 2. Le panier (matchers, toThrow, encapsulation) · 3. Livraison (test.each, valeurs limites,
beforeEach, `--randomize`) · 4. TDD des codes promo (tests d'après une spécification, puis implémentation) ·
5. Doublures (jest.fn, jest.mock) · 6. Erreurs asynchrones (rejects, reprise après panne) · 7. Faux minuteurs ·
8. Couverture (seuils, 100 % des branches) · 9. Bug #218 (test de reproduction puis correction) ·
10. Mise en production (.only/.skip, suite complète, workflow GitHub Actions).

**Évaluation par mutation** : les tests de l'étudiant doivent passer sur le code de référence, puis **échouer**
contre chaque version volontairement boguée (« mutant ») décrite dans `jest-lab/mutants.json`. Un test trop
permissif est signalé avec le défaut qu'il laisse passer. S'y ajoutent des tests cachés (TDD, correction de bug),
la couverture de code, l'exécution en ordre aléatoire et avec une date système décalée. Les tests de l'étudiant
tournent dans un bac à sable, sous un utilisateur dédié, sans accès au code de référence.

## Parcours Docker

L'étudiant conteneurise la boutique : 1. Image, conteneur, processus (run, ps -a, rm, PID vu de l'hôte) ·
2. Enquête sur les conteneurs de Marc (logs, stop, exec, inspect) · 3. Vitrine en ligne (ports, bind mount en lecture
seule) · 4. Données persistantes (volume nommé, sauvegarde) · 5. Dockerfile de l'API (build, EXPOSE, CMD, USER,
`.dockerignore`, politique de redémarrage) · 6. Réseau utilisateur et résolution par nom · 7. docker compose (build,
volume, proxy nginx, healthcheck + `depends_on`, `.env`) · 8. Incident en production (pile cassée à réparer, images
pendantes).

Les vérifications interrogent le moteur Docker de l'étudiant : `docker inspect`, appels HTTP aux services,
reconstruction de l'image depuis son Dockerfile, contrôle du contenu de l'image, `docker compose config`…
Les images `hello-world`, `alpine`, `nginx:alpine`, `node:20-alpine` et `redis:7-alpine` sont intégrées à l'image
`docker-lab` : pas de limite de téléchargement Docker Hub en salle, et le parcours fonctionne sans Internet.

### Sysbox (serveur Linux)

Chaque étudiant fait tourner son propre moteur Docker dans son conteneur. Pour que ce soit sûr, le conteneur
utilise le runtime **Sysbox** (conteneur non privilégié, espaces de noms utilisateur) :

```bash
# Ubuntu / Debian, noyau récent (5.12 ou plus conseillé). Télécharger le paquet .deb de la dernière version sur
# https://github.com/nestybox/sysbox/releases (documentation : docs/user-guide/install-package.md du dépôt), puis :
sudo apt-get install ./sysbox-ce_<version>.linux_amd64.deb   # redémarre le démon Docker de l'hôte
docker info | grep -i runtimes                                # doit mentionner sysbox-runc
```

`DOCKER_LAB_RUNTIME=sysbox-runc` (valeur par défaut) active ce mode. `DOCKER_LAB_RUNTIME=privileged` lance à la place
des conteneurs **privilégiés** (Docker-in-Docker classique) : un étudiant malveillant pourrait alors prendre le
contrôle de l'hôte. À réserver au développement (Docker Desktop, où Sysbox n'existe pas) ou à une VM dédiée.

Chaque étudiant dispose d'un volume `lab-docker-<id>-docker` pour son moteur (environ 300 Mo au départ, plus ses
propres images) : prévoir 1 Go de disque par étudiant.

## Déploiement

```bash
cp .env.example .env        # puis définir ADMIN_EMAIL / ADMIN_PASSWORD
docker compose up -d --build
```

La plateforme écoute sur le port 8080. Le compte enseignant (`/dashboard`, un onglet par parcours) est créé au
premier démarrage avec `ADMIN_EMAIL` / `ADMIN_PASSWORD` ; si `ADMIN_PASSWORD` est défini, il est réappliqué à
chaque démarrage. Sans `ADMIN_PASSWORD`, un mot de passe aléatoire est affiché une fois dans
`docker compose logs platform`.

Variables utiles : `IDLE_TIMEOUT` (secondes avant l'arrêt d'un conteneur inactif, 7200 par défaut — le travail
est conservé), `COOKIE_SECURE=1` derrière un reverse proxy HTTPS.

Isolation des étudiants : réseau `linux-lab-students` sans communication entre conteneurs ; parcours Linux :
256 Mo de RAM, 50 % d'un CPU, 256 processus, sshd limité à `localhost` ; parcours Jest : 1 Go, 1 CPU, 512 processus ;
parcours Docker : 1,5 Go, 1 CPU, 2048 processus, runtime Sysbox.

Accès Internet depuis les conteneurs : nécessaire uniquement pour l'étape 13 du parcours Linux. Les navigateurs
chargent xterm.js et l'éditeur Monaco depuis le CDN jsDelivr.

## Mettre à jour une installation existante

Les données (comptes, classes, progression) sont dans le volume Docker `<projet>_platform-data` ; le travail de chaque
étudiant est dans son conteneur (et, pour Docker, dans le volume `lab-docker-<id>-docker`). Une mise à jour ne les
touche pas, à condition de rester dans **le même dossier** (le nom du projet compose, donc du volume, en dépend) et de
ne **jamais** utiliser `docker compose down -v`.

```bash
cd labo-linux                                   # le dossier d'origine
docker volume ls | grep platform-data           # repérer le volume (ex. labo-linux_platform-data)
docker run --rm -v labo-linux_platform-data:/data -v "$PWD":/backup alpine     cp /data/platform.db /backup/platform-$(date +%Y%m%d-%H%M).db   # sauvegarde de la base
git pull
docker compose up -d --build
docker compose logs platform | tail                                  # vérifier le démarrage
```

Au premier démarrage d'une version qui introduit les classes, les étudiants existants sont placés dans une classe
« Promotion actuelle » avec accès au labo Linux (et aux autres labos s'ils y avaient déjà progressé) : personne ne
perd l'accès à son travail. Si le numéro de version d'un catalogue change (`EXERCISES_VERSION`), l'ancienne
progression de ce parcours est archivée dans la table `progress_archive`, jamais supprimée.

## Modifier ou ajouter des exercices

Catalogues : `platform/app/exercises.py` (Linux), `platform/app/jest_course.py` (Jest) et `docker_course.py` (Docker),
format documenté en tête
de fichier ; corrigés correspondants dans `platform/app/solutions/` (`linux.py`, `jest.py`, `docker.py`). Dans
chaque script d'étape, une ligne `#@ <exercice>` ouvre la correction de cet exercice : c'est ce découpage que voient
les admins (bouton « Voir la correction »), et la plateforme refuse de démarrer si un exercice n'a pas de correction. Pour Jest, le code
de référence est dans `jest-lab/ref/`, les fichiers livrés aux étudiants dans `jest-lab/student/`, les mutants dans
`jest-lab/mutants.json` et les tests cachés dans `jest-lab/hidden/`. Puis :

```bash
docker build -t linux-lab ./lab && docker build -t jest-lab ./jest-lab && docker build -t docker-lab ./docker-lab
python platform/tests/run_lab_tests.py                  # parcours Linux (~5 min, dont cron)
python platform/tests/run_lab_tests.py --only 1-8 --skip 13
python platform/tests/run_lab_tests.py --course jest    # parcours Jest (~1,5 min)
python platform/tests/run_lab_tests.py --course docker  # parcours Docker (~2 min, conteneur privilégié par défaut)
```

Le banc vérifie, pour chaque étape jouée dans l'ordre du parcours, qu'**aucun exercice ne passe avant d'être
fait** puis que **tous passent après la solution de référence**.

Si les identifiants d'exercices d'un parcours changent de sens, incrémentez son `EXERCISES_VERSION` : au
démarrage, la progression de ce parcours est archivée dans la table `progress_archive` et les conteneurs
correspondants sont recréés à la prochaine connexion.
