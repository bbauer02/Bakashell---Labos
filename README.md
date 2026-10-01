# Bakashell — Labo DevOps

Auteur : Bauer Baptiste — bbauer02@gmail.com · en ligne sur https://bakashell.fr

Plateforme d'apprentissage (BTS SIO / DevOps) : chaque étudiant dispose, dans son navigateur, d'un conteneur
personnel, d'un cours par étape et d'exercices validés automatiquement. Cinq parcours et une épreuve de synthèse :

| Parcours | URL | Contenu |
|---|---|---|
| **Linux en ligne de commande** | `/lab/linux` | 25 étapes, 207 exercices, 834 points — terminal Ubuntu |
| **Tests unitaires avec Jest** (niveau avancé) | `/lab/jest` | 11 journées, 38 exercices, 198 points — éditeur de code + terminal Node |
| **Docker : conteneuriser la boutique** | `/lab/docker` | 11 journées, 65 exercices, 280 points — un moteur Docker par étudiant + éditeur |
| **Git : travailler en équipe** | `/lab/git` | 9 journées, 40 exercices, 178 points — terminal + dépôt partagé de l'équipe |
| **Ansible : automatiser l'infrastructure** | `/lab/ansible` | 10 journées, 39 exercices, 188 points — poste de contrôle + vrais serveurs joignables en SSH + éditeur |
| **Projet final** (épreuve notée) | `/lab/projet` | 5 missions, 20 exercices, 100 points — les cinq parcours enchaînés sur l'API de la boutique, sans indice ni correction |

## Organisation : catalogue et classes

- Après connexion, l'étudiant arrive sur **son catalogue** (`/catalogue`) : les labos ouverts à ses classes, chacun
  avec sa vignette d'illustration et sa progression.
- **Vignettes** : sur le catalogue, l'administrateur survole la vignette d'un labo puis clique sur « 🖼 Changer la
  vignette » (PNG, JPEG ou WebP, 3 Mo au plus, format paysage 16:7, par exemple 1280×560) ; « Rétablir » revient à
  l'illustration fournie (`platform/static/vignettes/<parcours>.svg`). Une vignette est commune à toutes les classes :
  les enseignants ne peuvent pas la changer. Les images envoyées sont gardées avec la base (`/data/vignettes`, variable
  `VIGNETTES_DIR`) : elles survivent aux reconstructions de la plateforme. Les SVG ne sont pas acceptés à l'envoi (ils
  peuvent contenir du script).
- L'enseignant gère **ses classes** sur `/admin/classes` : il coche les labos ouverts à chaque classe et ajoute ou
  retire des étudiants (ajout par **adresse e-mail exacte** du compte, ou en cochant un étudiant de ses autres classes).
  Chaque classe a un **code d'inscription** (ex. `QTQ-V95`) que les étudiants saisissent à l'inscription ou depuis leur
  catalogue. Un étudiant peut appartenir à plusieurs classes, y compris de plusieurs enseignants.
- L'accès est contrôlé côté serveur (pages, API, terminal, éditeur, indices). Un compte du personnel (enseignant ou
  administrateur) voit tous les labos, et un bouton « Voir la correction » sur chaque exercice.

### Comptes : étudiant, enseignant, administrateur

| Profil | Création | Voit et gère |
|---|---|---|
| **Étudiant** | inscription libre (`/register`), avec ou sans code de classe | ses labos |
| **Enseignant** | **invitation** de l'administrateur uniquement (pas d'inscription enseignant libre) | **ses** classes (dont il est propriétaire) et les étudiants membres d'au moins une d'entre elles |
| **Administrateur** | le compte `ADMIN_EMAIL`, créé ou mis à jour au démarrage | tout : toutes les classes, tous les étudiants, les comptes enseignants |

- **Cloisonnement** : chaque classe a un propriétaire ; le nom d'une classe est unique pour un même enseignant (deux
  enseignants peuvent avoir chacun leur « BTS SIO 1 »). Un enseignant ne voit que ses étudiants partout : tableau de
  bord et flux en direct, statistiques, intégrité, export CSV, terminal en lecture seule, lien de réinitialisation du
  mot de passe, remise à zéro d'un parcours. Il ne peut ni agir sur un compte du personnel, ni supprimer
  définitivement un étudiant (il le retire de sa classe) : la suppression d'un compte étudiant est réservée à
  l'administrateur. Chaque page enseignant affiche le profil connecté (« Enseignant » ou « Administrateur »).
- **Invitation** (`/admin/enseignants`, administrateur seulement) : « Créer un lien d'invitation », éventuellement
  réservé à une adresse e-mail. Le lien `/invitation/<jeton>` est **à usage unique, valable 7 jours**, et n'est affiché
  qu'une fois (la base n'en garde que l'empreinte SHA-256, comme pour les liens de réinitialisation) : copiez-le et
  transmettez-le. La personne y choisit prénom, nom, e-mail et mot de passe (mêmes règles et même limitation des
  tentatives que l'inscription) ; son compte enseignant est créé et connecté. Une invitation en attente peut être annulée.
- **Gestion des enseignants** (même page) : nom, e-mail, nombre de classes et d'étudiants, dernière connexion ; lien de
  réinitialisation du mot de passe ; **désactivation** (connexion refusée, sessions en cours coupées aussitôt) et
  réactivation ; **suppression** : ses classes sont rattachées à l'administrateur (renommées « Nom (Prénom Nom) » si
  le nom est déjà pris chez lui), les étudiants et leur progression sont conservés. Le compte administrateur ne peut
  être ni désactivé ni supprimé.
- **Mise à jour d'une installation existante** : la migration est automatique au démarrage. Les classes existantes
  sont rattachées à l'administrateur (identifiants, codes, membres, labos ouverts et échéances conservés) ; les
  autres comptes qui avaient `is_admin = 1` deviennent des comptes enseignants, sans classe : ils créent les leurs
  (il n'existe pas de transfert d'une classe vers un autre enseignant). Si `ADMIN_EMAIL` change, l'ancien compte
  administrateur devient un compte enseignant.

### Suivi, notes et attestations

- Le tableau de bord (`/dashboard`) se filtre par parcours et par classe, et se met à jour en temps réel (présence,
  progression, élèves bloqués, fil d'activité). Depuis la ligne d'un étudiant, l'enseignant peut **regarder son
  terminal en direct** (lecture seule : ses frappes ne sont pas transmises) ou générer un **lien de réinitialisation
  du mot de passe** (valable 48 h, à transmettre à l'étudiant).
- **Échéances** : sur `/admin/classes`, l'enseignant fixe une date par classe, parcours et étape (« étapes 1 à 8 pour
  le 15/10 »). L'étudiant les voit dans son catalogue et dans le lab ; le tableau de bord signale les retards.
- **Export des notes** (`/admin/export.csv`, par parcours et par classe) : points, exercices réussis, indices utilisés,
  dernière réussite, attestation. Séparateur `;`, UTF-8 avec BOM : s'ouvre directement dans Excel ou LibreOffice.
- **Statistiques par exercice** (`/admin/stats`) : taux de réussite, vérifications en échec, indices consommés, pour
  repérer les exercices qui font buter toute la classe. Chaque vérification en échec est conservée : l'étudiant
  retrouve ses tentatives précédentes sous chaque exercice.
- **Attestation de fin de parcours** : à partir de `CERTIFICATE_MIN_PCT` % des points (70 % par défaut), l'étudiant
  obtient depuis son catalogue une page publique vérifiable (`/attestation/<code>`), imprimable en PDF, pour son
  portfolio.
- Chaque utilisateur change son mot de passe sur `/compte`. Connexion, inscription et réinitialisation sont limitées
  (10 échecs de connexion en 15 min) contre le forçage des mots de passe.

## Architecture

| Composant | Rôle |
|---|---|
| `platform/` | Application FastAPI : comptes, sessions, terminal WebSocket (xterm.js), éditeur (Monaco), validation, tableau de bord |
| `platform/app/courses/__init__.py` | Registre des parcours (image, ressources, catalogue, version) |
| `platform/app/courses/<parcours>/` | Un dossier par parcours (`linux`, `jest`, `docker`, `git`, `ansible`, `projet`) : `catalogue.py` (cours, mises en place, exercices, vérifications, indices), `memo.py` (fiches du mémo), `solutions.py` (corrigés) |
| `platform/app/memo.py` | Mémo des commandes : déblocage des fiches selon la progression |
| `platform/app/solutions.py` | Découpage des corrigés (un script par étape, un repère `#@ <exercice>` par exercice), visibles par les admins |
| `platform/app/objectif.py` | Objectif collectif de classe (paliers, messages de Sophie) |
| `platform/app/badges.py` | Badges, calculés à partir de la progression (rien n'est stocké) |
| `platform/app/progression.py` | Grades, couches d'ICE percées, réponses des collègues aux tickets résolus |
| `platform/app/scenario.py` | Entreprise fictive et personnages communs aux parcours, présentation affichée au début de chaque labo |
| `platform/static/vignettes/` | Vignettes d'illustration des labos (une par parcours) |
| `platform/app/runner.py` | Construit les commandes de mise en place et de vérification (partagé avec les tests) |
| `platform/app/terminals.py` | Diffusion du terminal d'un étudiant vers l'enseignant qui le regarde |
| `platform/app/ratelimit.py` | Limitation des tentatives (connexion, inscription, mot de passe) |
| `images/linux/` | Image `linux-lab` : utilisateur `etudiant` (sudoer), sshd, cron, rsyslog |
| `images/jest/` | Image `jest-lab` : Node 24 + Jest, code de référence, mutants, tests cachés, correcteur (`verifier.js`) |
| `images/docker/` | Image `docker-lab` : moteur Docker complet (docker:dind), images de base préchargées, projet de la boutique |
| `images/git/` | Image `git-lab` : Git, invite qui affiche la branche courante, dépôt partagé de l'équipe dans `/srv/git` |
| `images/ansible/` | Image `ansible-lab` : poste de contrôle (ansible-core) + moteur Docker interne qui fait tourner les serveurs gérés (Debian + SSH) et le dépôt APT interne |
| `images/projet/` | Image `projet-lab` (projet final) : poste de contrôle du parcours Ansible + Git, Node et Jest, serveurs Debian, serveur de construction Docker `ci1`, modèle du projet, tests cachés et correcteur (`correcteur.js`) |
| `platform/tests/` | Banc de test des parcours (`run_lab_tests.py`) et tests unitaires de la plateforme (`test_platform.py`) |
| `.github/workflows/ci.yml` | Intégration continue : tests unitaires, image de la plateforme, banc de test de chaque parcours |
| `docs/tutoriel/step-*/` | Tutoriel texte d'origine (historique, non utilisé par la plateforme) |

Chaque étudiant a un conteneur **par parcours** (`lab-student-<id>`, `lab-jest-<id>`, `lab-docker-<id>`,
`lab-git-<id>`, `lab-ansible-<id>`, `lab-projet-<id>`), créé à sa première visite. Un conteneur arrêté pour inactivité redémarre à la visite suivante, avec
un message qui prévient l'étudiant ; son travail est conservé.

Fonctionnement d'une étape :

1. À l'ouverture d'une étape, la plateforme exécute sa **mise en place** dans le conteneur (fichiers générés
   aléatoirement, processus, pannes à réparer, code livré…). Les réponses attendues sont renvoyées à la
   plateforme et stockées en base, **jamais dans le conteneur**.
2. L'étudiant travaille en tant qu'`etudiant` (avec `sudo`, mot de passe `etudiant`, dans le parcours Linux).
3. Les vérifications tournent en root via `docker exec` et testent le **comportement**. La première
   vérification en échec renvoie un message explicite, éventuellement détaillé (valeurs attendues, défaut non
   détecté…).
4. Les exercices marqués `manual` (qui exécutent du code de l'étudiant) ne sont testés que sur clic ; dans le
   parcours Linux, Docker, Git et Ansible, les autres sont vérifiés automatiquement toutes les 5 s.
5. Chaque indice débloqué coûte 1 point (minimum 1 point par exercice réussi).

## Scénario

L'étudiant travaille chez **Cimes & Sentiers**, une PME fictive de vente de matériel de randonnée. Les exercices
arrivent sous forme de **tickets** envoyés par des collègues récurrents : Sophie (DSI), Léa (admin senior, mentore
des parcours Linux et Ansible), Nadia (lead développeuse, mentore des parcours Jest et Git), Thomas (développeur), Aminata
(comptabilité), Julien (stagiaire), et Marc, le prédécesseur parti précipitamment dont on retrouve le travail un peu
partout. Tous les exercices des cinq parcours ont leur ticket ; un exercice sans clé `ticket` s'affiche au format
classique.

**Progression ludique** (`platform/app/progression.py`, sans effet sur la note : seuls les points comptent). Deux
univers coexistent : **Cimes & Sentiers** est l'histoire (l'entreprise, les tickets, les collègues) ; la progression
parle **Bakashell**, le « bac à shell » : cyberpunk à la *Neuromancer*, avec une pointe de japonais.

- **Ticket résolu** : tampon néon `[ RÉSOLU ]` et réponse du collègue (phrase tirée de sa liste, toujours la même pour un
  exercice ; un exercice peut fixer la sienne avec `ticket["reply"]`). Gerbe de caractères (`0 1 { } $ #`) en fin
  d'étape, désactivée si le système de l'élève demande moins d'animations.
- **Grades par labo**, selon la part des points : Recrue, Opérateur·rice (15 %), Hacker (40 %), Architecte (70 %),
  Ghost (90 %, *ghost in the shell*). Le passage d'un grade est annoncé par Bakashell seul (la plateforme), sans personnage de l'histoire.
- **L'intrusion** : chaque étape terminée est une couche d'ICE percée (les pare-feu du roman) vers le noyau du labo
  (Ring 0 pour Linux, Zoo des mutants pour Jest, Port franc pour Docker, Arbre des commits pour Git, La Ruche pour
  Ansible, Cœur de prod pour le projet final). Le bouton du grade, dans la barre du lab, ouvre la pile des couches
  (cliquables) jusqu'au noyau et à l'attestation. Le catalogue affiche grade et couches sur chaque carte.
- **Vignettes** synthwave (soleil néon, skyline, grille en perspective), une couleur et un motif par labo.
- **Badges** (`platform/app/badges.py`) : 13 badges qui récompensent l'autonomie, la persévérance et la régularité
  (étape entière sans indice, exercice réussi après 5 vérifications ratées, uptime de 3 semaines, un ticket de
  chacun des six collègues, QCM sans faute, mémo complet…). Ils se calculent à partir des données déjà enregistrées :
  rien n'est stocké. Une notification « Nouveau badge » apparaît dans le lab.
- **Profil** (`/profil`, lien « Mon profil » du catalogue) : badges obtenus et à venir avec leur avancement, grade et
  couches d'ICE percées dans chaque labo, tickets résolus pour chacun des collègues. L'enseignant ouvre le profil
  d'un étudiant en cliquant sur son nom dans le tableau de bord (`/profil/<id>`, mêmes règles de cloisonnement).
- **Uptime** (série hebdomadaire) : les semaines consécutives avec au moins un ticket résolu, tous labos confondus.
  Jusqu'à deux semaines vides d'affilée (les vacances) mettent la série en pause sans la casser ; trois la terminent.
  Rien de punitif : l'uptime actuel, le record, et « un ticket suffit pour le prolonger ». Affiché dans le catalogue,
  le profil et le panneau d'intrusion ; notification « Uptime prolongé » au premier ticket de la semaine. Le badge
  « Cron humain » demande un uptime de 3 semaines.
- **Objectif de classe** (`platform/app/objectif.py`) : les tickets résolus par les étudiants d'une classe, dans les
  labos qui lui sont ouverts (hors projet final), comptent pour un objectif commun en six paliers (5, 15, 30, 50, 75 et
  100 % du potentiel : nombre d'étudiants × exercices). Chaque palier atteint débloque un message de Sophie. Sans
  classement ni nom : le total, la semaine écoulée, le nombre d'étudiants actifs et, pour l'étudiant, sa propre part.
  Affiché dans le catalogue de l'étudiant et, pour l'enseignant, sur `/admin/classes`.
- Le projet final (épreuve notée) n'a ni grade, ni réponse des collègues, ni animation, ni notification de badge :
  seulement les couches percées. Il ne compte pas pour les badges d'autonomie (il n'a pas d'indice).

**Les labos se suivent dans n'importe quel ordre** : aucun ne doit supposer qu'un autre a été fait avant. La
présentation de l'entreprise et de l'équipe (`scenario.contexte()`) est ajoutée automatiquement en tête de la première
étape de chaque parcours (avec la mentore du labo), et reste accessible à toute étape par le bouton « 🏔 L'équipe » du
lab. L'introduction propre à chaque parcours ne décrit que sa mission.

## Parcours Linux

1. Navigation · 2. Manuel et chemins · 3. Fichiers et dossiers · 4. Liens · 5. Recherche (find, grep) ·
6. Redirections et pipes · 7. Édition (nano, vim, sed) · 8. Expressions régulières · 9. Filtrage (awk, sort, uniq) ·
10. Utilisateurs, groupes, permissions · 11. sudo et processus · 12. Cas pratique · 13. Paquets (apt, dpkg) ·
14. Disques · 15. Environnement, PATH, alias · 16. Archives · 17. Scripts Bash · 18. cron · 19. Supervision ·
20. Logs et logrotate · 21. Réseau · 22. SSH (clés, config, scp, durcissement) · 23. Sécurité (audit et correction) ·
24. **Dépannage** (script CRLF, disque plein, SSH refusé, cron fantôme, service en échec) ·
25. Intégration finale (serveur web, sauvegardes avec rotation, supervision, accès SSH)

Chaque étape mêle des exercices d'application et des exercices de diagnostic ou d'enquête (pièges classiques,
pannes à réparer), avec des données tirées au sort à chaque mise en place. Les fiches du mémo ne donnent jamais
la réponse d'un exercice, et les messages d'échec ne révèlent pas la valeur attendue. L'étape 13 comporte des
entièrement faisable sans Internet (miroir APT interne dans l'image).

## Parcours Jest

L'étudiant teste le code métier de la boutique (`~/boutique`) : 1. La CI est rouge (toBe, toBeCloseTo, scripts
npm, arrondis) · 2. Le panier (matchers, toThrow, encapsulation) · 3. Livraison (test.each, valeurs limites,
beforeEach, `--randomize`) · 4. TDD des codes promo (tests d'après une spécification, puis implémentation) ·
5. Doublures (jest.fn, jest.mock) · 6. Erreurs asynchrones (rejects, reprise après panne) · 7. Faux minuteurs ·
8. Couverture (seuils, 100 % des branches) · 9. Bug #218 (test de reproduction puis correction) ·
10. Mise en production (.only/.skip, suite complète, workflow GitHub Actions) · 11. Instantanés (snapshots, et
le snapshot qui fige un bug). Chaque journée comporte aussi des exercices de diagnostic : tests qui ne testent
rien, mock qui fuit d'un test à l'autre, test instable à stabiliser, cas limite manquant dans une spécification…

**Évaluation par mutation** : les tests de l'étudiant doivent passer sur le code de référence, puis **échouer**
contre chaque version volontairement boguée (« mutant ») décrite dans `images/jest/mutants.json`. Un test trop
permissif est signalé avec le défaut qu'il laisse passer. S'y ajoutent des tests cachés (TDD, correction de bug),
la couverture de code, l'exécution en ordre aléatoire et avec une date système décalée. Les tests de l'étudiant
tournent dans un bac à sable, sous un utilisateur dédié, sans accès au code de référence.

## Parcours Docker

L'étudiant conteneurise la boutique : 1. Image, conteneur, processus (run, ps -a, rm, PID vu de l'hôte) ·
2. Enquête sur les conteneurs de Marc (logs, stop, exec, inspect) · 3. Vitrine en ligne (ports, bind mount en lecture
seule) · 4. Données persistantes (volume nommé, sauvegarde) · 5. Les pièges des données (volume pré-rempli ou bind
mount qui masque, restauration, volumes anonymes et `volume prune`, `--read-only` + `--tmpfs`) · 6. Dockerfile de l'API
(build, EXPOSE, CMD, USER, `.dockerignore`, politique de redémarrage) · 7. Subtilités du Dockerfile (ordre des couches
et cache avec `npm ci`, forme exec et PID 1 face à `docker stop`, ENTRYPOINT et CMD, ARG, ENV et LABEL) · 8. Images
légères et sans secrets (multi-stage, mot de passe lisible dans `docker history`, fichier « supprimé » retrouvé dans
une couche avec `docker save`, `RUN --mount=type=secret`) · 9. Réseaux (réseau utilisateur, résolution par nom,
`network connect` à chaud) · 10. docker compose (build, volume, proxy nginx, healthcheck + `depends_on`, `.env`) ·
11. Incident en production (pile cassée à réparer, images pendantes).

Les vérifications des jours 7 et 8 testent le **comportement** : l'étape `npm ci` doit être reprise du cache après une
modification du code, `docker stop` doit arrêter la pointeuse proprement en moins de 3 s, la licence ne doit
apparaître dans aucune couche de l'image…

Les vérifications interrogent le moteur Docker de l'étudiant : `docker inspect`, appels HTTP aux services,
reconstruction de l'image depuis son Dockerfile, contrôle du contenu de l'image, `docker compose config`…
Les images `hello-world`, `alpine`, `nginx:alpine`, `node:20-alpine` et `redis:7-alpine` sont intégrées à l'image
`docker-lab` : pas de limite de téléchargement Docker Hub en salle, et le parcours fonctionne sans Internet.

## Parcours Git

L'étudiant met en place Git dans l'équipe web : 1. Premiers pas (config, init, add, commit, `.gitignore`,
`rm --cached`) · 2. Enquête dans les archives de Marc (log, `log -S`, show, restauration d'un fichier supprimé,
revert) · 3. Le dépôt de l'équipe (clone, push) · 4. À plusieurs sur la même branche (push refusé, pull,
`pull.rebase`) · 5. Branches (switch, `push -u`, merge, suppression locale et distante) · 6. Conflits (résolution,
`merge --abort`, revert d'une fusion) · 7. Réécrire son histoire locale (stash, `commit --amend`, rebase interactif,
reset soft/mixed) · 8. Enquêtes et mise en
production (bisect, étiquette annotée, reflog) · 9. Secrets et garde-fous (`.env` déjà suivi,
`.gitignore` piégeux, clé effacée de tout l'historique, hook pre-commit).

Le dépôt partagé est un dépôt nu local (`/srv/git/boutique.git`) : pas besoin de GitHub ni d'Internet. Pendant le
parcours, les collègues y publient leurs propres commits : un commit de Nadia qui fait refuser le push, une branche de
Thomas à fusionner, une modification concurrente de la même ligne… Les vérifications lisent les dépôts sans les
modifier : auteur des commits, ancêtres (`merge-base --is-ancestor`), contenu d'un fichier dans un commit, absence de
marqueurs de conflit, historique conservé (un `push --force` qui efface le travail d'un collègue est signalé).

## Parcours Ansible

L'étudiant automatise l'infrastructure de la boutique : 1. Ce que fait Ansible (inventaire, clés SSH, `ping`) ·
2. Modules et commandes ad hoc · 3. Premier playbook (idempotence) · 4. Variables, facts et modèles Jinja2 ·
5. Configurer un service : les handlers (validate, handler perdu, flush_handlers) · 6. Boucles, conditions et filtres ·
7. La chasse aux dérives, puis les rôles · 8. Secrets (Ansible Vault) et mise en production (arrivée de `web3`,
`site.yml` qui décrit toute l'infrastructure) · 9. Fiabiliser ses playbooks (register, changed_when/failed_when,
assert, block/rescue) · 10. Déployer sans couper (serial, tags, incident à diagnostiquer).

Les exercices où l'enjeu est d'utiliser Ansible ne se valident pas par une modification faite à la main : les
vérifications cassent l'état du serveur (ou le réinstallent) puis rejouent le playbook de l'étudiant, ou lisent le
journal sudo des serveurs, où les commandes lancées par Ansible sont reconnaissables.

L'étudiant travaille sur un **poste de contrôle** sans `sudo`. Les serveurs `web1`, `web2`, `db1` (puis `web3`) sont
de vrais conteneurs Debian avec SSH (compte `admin`, mot de passe `cimes` pour le premier contact), qui tournent dans
un moteur Docker interne au conteneur de l'étudiant, sur le réseau `10.10.0.0/24`. L'étudiant n'a pas accès à ce
moteur : pour lui, ce sont des serveurs distants. Un dépôt APT interne (`depot.cimes.lan`) fournit nginx, Redis…
sans Internet. Les vérifications observent le résultat réel sur les serveurs (pages HTTP, Redis, comptes) et, pour
les exercices `manual`, rejouent les playbooks de l'étudiant pour contrôler qu'un second passage ne change rien.

## Projet final

Épreuve notée de synthèse (parcours marqué `"exam": True` : aucun indice, aucune correction montrée aux étudiants ; les
comptes admin voient le corrigé). Cinq missions sur un même projet, l'API de la boutique (`~/boutique`, clone du dépôt
partagé `/srv/git/boutique.git`), avec les tickets de l'élève dans `~/tickets` :

1. **Jest — le bug du devis** : un bug du calcul des devis, tiré au sort parmi quatre (seuil de port offert exclu, remise
   étendue à toute la commande, seuil comparé avant remise, prix unitaire non arrondi), avec des règles métier propres à
   chaque élève (seuil, frais de port, remise). Test de reproduction jugé sur le code corrigé et sur le code bogué,
   correction validée par des tests cachés, suite complète verte sans test supprimé ni désactivé (un test existant fige
   le bug), et mutation : la suite doit détecter les erreurs voisines du bug.
2. **Git — livrer la correction** : branche `correctif-<ticket>`, commits à son identité qui citent le ticket,
   intégration du commit publié entre-temps par Thomas (conflit probable dans `CHANGELOG.md`), version corrective et
   étiquette annotée sur le dépôt partagé, sans réécrire l'historique.
3. **Docker — l'image de l'API** : Dockerfile sur `node:24-alpine`, exécuté sans root, sans Git, tests ni Jest dans
   l'image, cache de `npm ci`, HEALTHCHECK, image `boutique-api:<version>`. L'élève utilise le moteur du serveur de
   construction `ci1` (`DOCKER_HOST=tcp://ci1:2375`) : il n'a accès ni au moteur qui héberge les serveurs, ni aux
   fichiers privés du correcteur.
4. **Ansible — déployer** : rôle `api` et playbook `deploiement.yml` pour web1 et web2 (Node du dépôt APT interne,
   compte système, script de service fourni dans le dépôt, modèle, handler, service activé). Les vérifications
   réinstallent les serveurs avant de rejouer le playbook, surchargent `api_port`, modifient le code d'un serveur à la
   main, redémarrent web2.
5. **Linux — incident en production** sur web3 (SSH, sudo) : deux causes tirées au sort, l'une parmi disque plein
   (partition des journaux de 8 Mo), droits d'un fichier de données ou réglage erroné, l'autre parmi le port pris par la
   maquette de Julien ou par une ancienne version lancée en root (toutes deux relancées au démarrage). Vérifié : l'API
   revient sous son service, rien d'autre n'est cassé (données, journaux d'accès, droits, vitrine nginx, comptes, code,
   réglages), la réparation tient après un redémarrage, et le rapport nomme les éléments en cause.

Chaque mise en place prépare ce dont sa mission a besoin (dépôt partagé, clone, serveurs, accès SSH) : une mission se
commence même si la précédente n'est pas terminée, et aucune vérification ne dépend de la réussite d'une autre. Les
données sont tirées une fois pour toutes (volume du moteur Docker de l'élève) ; `LAB_VARIANTE_P1_1` (0 à 3) et
`LAB_VARIANTE_P5_1` (0 à 5, précisée par `LAB_VARIANTE_P5_1_A`) les imposent pour les tests. Tout est intégré à l'image
(images Docker, paquets Debian, Jest) : l'épreuve se déroule sans Internet. La mission 5 est rejouée après un
redémarrage du conteneur (partition des journaux en mémoire) : l'incident est alors recréé.

### Sysbox (serveur Linux)

Dans les parcours Docker et Ansible et le projet final, chaque étudiant fait tourner son propre moteur Docker dans son conteneur. Pour que ce soit sûr, le conteneur
utilise le runtime **Sysbox** (conteneur non privilégié, espaces de noms utilisateur) :

```bash
# Ubuntu / Debian, noyau récent (5.12 ou plus conseillé). Télécharger le paquet .deb de la dernière version sur
# https://github.com/nestybox/sysbox/releases (documentation : docs/user-guide/install-package.md du dépôt), puis :
sudo apt-get install ./sysbox-ce_<version>.linux_amd64.deb   # redémarre le démon Docker de l'hôte
docker info | grep -i runtimes                                # doit mentionner sysbox-runc
```

`DOCKER_LAB_RUNTIME=sysbox-runc` (valeur par défaut) active ce mode, pour ces trois parcours. `DOCKER_LAB_RUNTIME=privileged` lance à la place
des conteneurs **privilégiés** (Docker-in-Docker classique) : un étudiant malveillant pourrait alors prendre le
contrôle de l'hôte. À réserver au développement (Docker Desktop, où Sysbox n'existe pas) ou à une VM dédiée.

Chaque étudiant dispose d'un volume `lab-docker-<id>-docker` pour son moteur (environ 300 Mo au départ, plus ses
propres images) : prévoir 1 Go de disque par étudiant. De même pour Ansible (volume `lab-ansible-<id>-docker`, qui contient les
serveurs de l'étudiant) et pour le projet final (volume `lab-projet-<id>-docker` : serveurs, serveur de construction `ci1`
et ses images, environ 1,5 Go). Dans le projet final, `ci1` est un conteneur privilégié **à l'intérieur** du conteneur
Sysbox de l'étudiant (Docker dans Docker dans Docker) : à valider sur le serveur Sysbox avant l'épreuve.

## Déploiement

```bash
cp .env.example .env        # puis définir ADMIN_EMAIL / ADMIN_PASSWORD
docker compose up -d --build
```

La plateforme écoute sur le port 8080. Le compte enseignant (`/dashboard`, un onglet par parcours) est créé au
premier démarrage avec `ADMIN_EMAIL` / `ADMIN_PASSWORD` ; si `ADMIN_PASSWORD` est défini, il est réappliqué à
chaque démarrage. Sans `ADMIN_PASSWORD`, un mot de passe aléatoire est affiché une fois dans
`docker compose logs platform`.

Variables utiles (voir `.env.example`) :

- `IDLE_TIMEOUT` : secondes avant l'arrêt d'un conteneur inactif (7200 par défaut ; le travail est conservé) ;
- `COOKIE_SECURE=1` derrière un reverse proxy HTTPS, avec `FORWARDED_ALLOW_IPS` = adresse du proxy (pour que la
  limitation des tentatives voie l'IP réelle des étudiants) ;
- `BACKUP_HOURS` / `BACKUP_KEEP` : **sauvegarde automatique** de la base toutes les 24 h dans `./backups` (sur
  l'hôte), en gardant les 14 dernières ;
- `CERTIFICATE_MIN_PCT` : part des points exigée pour l'attestation (70 par défaut).

Isolation des étudiants : réseau `linux-lab-students` sans communication entre conteneurs ; parcours Linux :
256 Mo de RAM, 50 % d'un CPU, 256 processus, sshd limité à `localhost` ; parcours Jest : 1 Go, 1 CPU, 512 processus ;
parcours Docker : 1,5 Go, 1 CPU, 2048 processus, runtime Sysbox ; parcours Git : 256 Mo, 50 % d'un CPU,
256 processus ; parcours Ansible : 1,5 Go, 1 CPU, 2048 processus, runtime Sysbox ; projet final : 1,5 Go, 1 CPU, 2048 processus,
runtime Sysbox.

Accès Internet depuis les conteneurs : inutile, tous les parcours fonctionnent hors ligne. xterm.js et l'éditeur
Monaco sont installés dans l'image de la plateforme et servis par elle : en salle, les navigateurs n'ont pas besoin
d'Internet.

## HTTPS derrière un reverse proxy

En production, la plateforme est servie en HTTPS par un reverse proxy (Caddy, qui obtient et renouvelle seul son
certificat Let's Encrypt) ; le port 8080 n'écoute plus que sur l'hôte. Le proxy et la plateforme partagent le réseau
Docker externe `web-proxy`, où le proxy a une adresse fixe :

```bash
docker network create --subnet 172.30.0.0/24 web-proxy     # une seule fois, sur le serveur
```

```text
# Caddyfile (proxy en 172.30.0.10 sur web-proxy)
mon-domaine.fr {
	reverse_proxy linux-lab-platform:8080 {
		flush_interval -1          # flux temps réel du tableau de bord ; la WebSocket du terminal passe telle quelle
	}
}
```

```bash
# .env de la plateforme
COOKIE_SECURE=1
FORWARDED_ALLOW_IPS=172.30.0.10    # seul le proxy peut indiquer l'adresse réelle des étudiants
PUBLIC_URL=https://mon-domaine.fr
PLATFORM_BIND=127.0.0.1           # port 8080 fermé à l'extérieur
```

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

Catalogues : `platform/app/courses/<parcours>/catalogue.py` (`linux`, `jest`, `docker`, `git`, `ansible`, `projet`),
format documenté en tête
de fichier ; corrigés correspondants dans `solutions.py` du même dossier. Dans
chaque script d'étape, une ligne `#@ <exercice>` ouvre la correction de cet exercice : c'est ce découpage que voient
les admins (bouton « Voir la correction »), et la plateforme refuse de démarrer si un exercice n'a pas de correction. Pour Jest, le code
de référence est dans `images/jest/ref/`, les fichiers livrés aux étudiants dans `images/jest/student/`, les mutants dans
`images/jest/mutants.json` et les tests cachés dans `images/jest/hidden/`. Puis :

```bash
docker build -t linux-lab ./images/linux && docker build -t jest-lab ./images/jest && docker build -t docker-lab ./images/docker && docker build -t git-lab ./images/git && docker build -t ansible-lab ./images/ansible && docker build -t projet-lab ./images/projet
python platform/tests/run_lab_tests.py                  # parcours Linux (~8 min, dont cron)
python platform/tests/run_lab_tests.py --only 1-8
python platform/tests/run_lab_tests.py --course jest    # parcours Jest (~3,5 min)
python platform/tests/run_lab_tests.py --course docker  # parcours Docker (~7 min, conteneur privilégié par défaut)
python platform/tests/run_lab_tests.py --course git     # parcours Git (~30 s)
python platform/tests/run_lab_tests.py --course ansible # parcours Ansible (~17 min, conteneur privilégié par défaut)
python platform/tests/run_lab_tests.py --course projet  # projet final (~5 min, conteneur privilégié par défaut)
```

Le banc vérifie, pour chaque étape jouée dans l'ordre du parcours, qu'**aucun exercice ne passe avant d'être
fait** puis que **tous passent après la solution de référence**.

Les tests unitaires de la plateforme (droits d'accès par classe, mots de passe, limitation des tentatives, échéances,
export, attestation, sauvegarde, terminal en lecture seule…) n'ont pas besoin de Docker :

```bash
pip install -r platform/requirements.txt -r platform/requirements-dev.txt
python -m pytest platform/tests
```

Sur GitHub, la CI (`.github/workflows/ci.yml`) lance à chaque push les tests unitaires, construit l'image de la
plateforme et passe le banc de test de chaque parcours.

Si les identifiants d'exercices d'un parcours changent de sens, incrémentez son `EXERCISES_VERSION` : au
démarrage, la progression de ce parcours est archivée dans la table `progress_archive` et les conteneurs
correspondants sont recréés à la prochaine connexion.
