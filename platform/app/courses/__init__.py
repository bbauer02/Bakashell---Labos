"""Registre des parcours disponibles sur la plateforme.

Chaque parcours a son image Docker, son conteneur par étudiant, son catalogue d'étapes et
sa version (un changement de version archive la progression du parcours et recrée les
conteneurs). Les identifiants d'exercices sont uniques entre parcours (« 4.2 », « J4.2 », « D4.2 », « G4.2 », « A4.2 »).
"""
import importlib
import importlib.util
import os

from .ansible import catalogue as ansible_catalogue
from .docker import catalogue as docker_catalogue
from .git import catalogue as git_catalogue
from .jest import catalogue as jest_catalogue
from .linux import catalogue as linux_catalogue
from ..scenario import CHARACTERS

COURSES = {
    "linux": {
        "key": "linux",
        "title": "Linux en ligne de commande",
        "short": "Linux",
        "summary": "Admin système junior chez Cimes & Sentiers : navigation, fichiers, droits, processus, scripts, cron, réseau, SSH, sécurité et dépannage, dans un vrai serveur Ubuntu.",
        "level": "Débutant à intermédiaire",
        "duration": "20 à 30 h",
        "steps": linux_catalogue.STEPS,
        "version": linux_catalogue.EXERCISES_VERSION,
        "meta_key": "exercises_version",  # nom historique
        "id_glob": "[0-9]*",
        "image": os.environ.get("LAB_IMAGE", "linux-lab"),
        "container_prefix": "lab-student-",
        "setup_prelude": linux_catalogue.SETUP_PRELUDE,
        "check_prelude": linux_catalogue.CHECK_PRELUDE,
        "mentor": linux_catalogue.MENTOR,
        "editor_root": None,
        "auto_validate": True,
        "check_timeout": 45,
        "mem_limit": "256m",
        "cpu_quota": 50000,
        "pids_limit": 256,
    },
    "jest": {
        "key": "jest",
        "title": "Tests unitaires avec Jest",
        "short": "Jest",
        "summary": "Sécuriser le code de la boutique en ligne : matchers, cas limites, TDD, doublures, code asynchrone, faux minuteurs, couverture et intégration continue. Vos tests sont évalués par mutation.",
        "level": "Avancé (JavaScript requis)",
        "duration": "15 à 20 h",
        "steps": jest_catalogue.STEPS,
        "version": jest_catalogue.EXERCISES_VERSION,
        "meta_key": "exercises_version:jest",
        "id_glob": "J*",
        "image": os.environ.get("JEST_IMAGE", "jest-lab"),
        "container_prefix": "lab-jest-",
        "setup_prelude": jest_catalogue.SETUP_PRELUDE,
        "check_prelude": jest_catalogue.CHECK_PRELUDE,
        "mentor": jest_catalogue.MENTOR,
        "editor_root": "/home/etudiant/boutique",
        "auto_validate": False,
        "check_timeout": 240,
        "mem_limit": "1g",
        "cpu_quota": 100000,
        "pids_limit": 512,
    },
    "docker": {
        "key": "docker",
        "title": "Docker : conteneuriser la boutique",
        "short": "Docker",
        "summary": "Conteneurs, ports, volumes et leurs pièges, Dockerfile (cache, PID 1, ENTRYPOINT, ARG, multi-stage, secrets), réseaux et docker compose, avec votre propre moteur Docker, jusqu'au dépannage d'une pile en production.",
        "level": "Débutant à intermédiaire",
        "duration": "20 à 28 h",
        "steps": docker_catalogue.STEPS,
        "version": docker_catalogue.EXERCISES_VERSION,
        "meta_key": "exercises_version:docker",
        "id_glob": "D*",
        "image": os.environ.get("DOCKER_LAB_IMAGE", "docker-lab"),
        "container_prefix": "lab-docker-",
        "setup_prelude": docker_catalogue.SETUP_PRELUDE,
        "check_prelude": docker_catalogue.CHECK_PRELUDE,
        "mentor": docker_catalogue.MENTOR,
        "editor_root": "/home/etudiant/projet",
        "auto_validate": True,
        "check_timeout": 180,
        "mem_limit": "1536m",
        "cpu_quota": 100000,
        "pids_limit": 2048,
        # Moteur Docker propre à chaque étudiant : runtime Sysbox (recommandé) ou « privileged »
        # (Docker-in-Docker classique : à réserver à une machine dédiée ou au développement).
        "docker_in_docker": os.environ.get("DOCKER_LAB_RUNTIME", "sysbox-runc"),
    },
    "git": {
        "key": "git",
        "title": "Git : travailler en équipe",
        "short": "Git",
        "summary": "Versionner, explorer l'historique, collaborer sur un dépôt partagé : branches, conflits, rebase, stash, bisect, étiquettes et récupération de commits perdus.",
        "level": "Débutant à intermédiaire",
        "duration": "14 à 20 h",
        "steps": git_catalogue.STEPS,
        "version": git_catalogue.EXERCISES_VERSION,
        "meta_key": "exercises_version:git",
        "id_glob": "G*",
        "image": os.environ.get("GIT_LAB_IMAGE", "git-lab"),
        "container_prefix": "lab-git-",
        "setup_prelude": git_catalogue.SETUP_PRELUDE,
        "check_prelude": git_catalogue.CHECK_PRELUDE,
        "mentor": git_catalogue.MENTOR,
        "editor_root": None,
        "auto_validate": True,
        "check_timeout": 45,
        "mem_limit": "256m",
        "cpu_quota": 50000,
        "pids_limit": 256,
    },
    "ansible": {
        "key": "ansible",
        "title": "Ansible : automatiser l'infrastructure",
        "short": "Ansible",
        "summary": "Comprendre ce que fait Ansible et décrire toute l'infrastructure en code : inventaire, modules, playbooks, variables et modèles, handlers, rôles, Vault, sur de vrais serveurs joignables en SSH.",
        "level": "Intermédiaire (bases Linux requises)",
        "duration": "16 à 24 h",
        "steps": ansible_catalogue.STEPS,
        "version": ansible_catalogue.EXERCISES_VERSION,
        "meta_key": "exercises_version:ansible",
        "id_glob": "A*",
        "image": os.environ.get("ANSIBLE_LAB_IMAGE", "ansible-lab"),
        "container_prefix": "lab-ansible-",
        "setup_prelude": ansible_catalogue.SETUP_PRELUDE,
        "check_prelude": ansible_catalogue.CHECK_PRELUDE,
        "mentor": ansible_catalogue.MENTOR,
        "editor_root": "/home/etudiant/infra",
        "auto_validate": True,
        "check_timeout": 240,
        "mem_limit": "1536m",
        "cpu_quota": 100000,
        "pids_limit": 2048,
        # Les serveurs gérés (web1, web2, db1, web3) tournent dans un moteur Docker propre à l'étudiant
        "docker_in_docker": os.environ.get("DOCKER_LAB_RUNTIME", "sysbox-runc"),
    },
}

DEFAULT_COURSE = "linux"

# Index global : identifiant d'exercice -> (parcours, étape, position dans l'étape, exercice)
QUIZ_QUESTIONS = 4  # questions du QCM de fin de cours tirées au sort pour chaque étudiant, 1 point chacune

EXERCISE_INDEX = {}
for _key, _course in COURSES.items():
    for _num, _step in _course["steps"].items():
        for _pos, _ex in enumerate(_step["exercises"], 1):
            assert _ex["id"] not in EXERCISE_INDEX, f"Identifiant d'exercice en double : {_ex['id']}"
            if "ticket" in _ex:
                assert _ex["ticket"]["from"] in CHARACTERS, f"Personnage inconnu dans {_ex['id']}"
            EXERCISE_INDEX[_ex["id"]] = (_key, _num, _pos, _ex)
    _course["max_score"] = sum(ex["points"] for s in _course["steps"].values() for ex in s["exercises"])
    # QCM de fin de cours (courses/<parcours>/quiz.py) : QUIZ_QUESTIONS points par étape qui en a un
    _quiz = (importlib.import_module(f"{__name__}.{_key}.quiz").QUIZ
             if importlib.util.find_spec(f"{__name__}.{_key}.quiz") else {})
    _course["quiz"] = {n: q for n, q in _quiz.items() if n in _course["steps"] and len(q) >= QUIZ_QUESTIONS}
    _course["quiz_max"] = QUIZ_QUESTIONS * len(_course["quiz"])
    _course["max_score"] += _course["quiz_max"]
    _course["total_exercises"] = sum(len(s["exercises"]) for s in _course["steps"].values())
    _course["ids"] = {ex["id"] for s in _course["steps"].values() for ex in s["exercises"]}


def get_course(key: str):
    return COURSES.get(key)


def get_exercise(exercise_id: str):
    """Retourne (parcours, étape, position, exercice) ou (None, None, None, None)."""
    return EXERCISE_INDEX.get(exercise_id, (None, None, None, None))
