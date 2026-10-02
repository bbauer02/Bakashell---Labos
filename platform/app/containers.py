"""Gestion des conteneurs Docker des étudiants (un conteneur par étudiant et par parcours)."""
import json
import logging
import os
import pathlib
import socket
import threading
import time

import docker

from .courses import COURSES

log = logging.getLogger("linux-lab")

# Réseau dédié aux étudiants, sans communication entre conteneurs (ICC désactivé).
NETWORK_NAME = os.environ.get("LAB_NETWORK", "linux-lab-students")
STUDENT_USER = "etudiant"
STUDENT_HOME = "/home/etudiant"

_client = None


def client():
    """Client Docker, créé à la première utilisation (les tests importent l'application sans Docker)."""
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


# Un verrou par conteneur : le terminal et la préparation d'étape peuvent le demander en même temps
_create_locks: dict = {}
_create_guard = threading.Lock()


def _lock_for(name: str) -> threading.Lock:
    with _create_guard:
        return _create_locks.setdefault(name, threading.Lock())


def get_or_create_network():
    try:
        return client().networks.get(NETWORK_NAME)
    except docker.errors.NotFound:
        return client().networks.create(
            NETWORK_NAME,
            driver="bridge",
            options={"com.docker.network.bridge.enable_icc": "false"},
            labels={"linux-lab": "students"},
        )


def get_container_name(user_id: int, course: dict) -> str:
    return f"{course['container_prefix']}{user_id}"


def docker_volume_name(user_id: int, course: dict) -> str:
    return f"{course['container_prefix']}{user_id}-docker"


def get_or_create_container(user_id: int, course: dict) -> str:
    """Retourne l'ID du conteneur de l'étudiant pour ce parcours (démarré), en le créant si besoin.
    Un conteneur créé pour une autre version du parcours est recréé."""
    name = get_container_name(user_id, course)
    with _lock_for(name):
        return _get_or_create(user_id, course, name)


def container_status(user_id: int, course: dict) -> str:
    """État de l'environnement avant son ouverture : « running », « stopped » (arrêté après inactivité,
    le travail est conservé), « outdated » (nouvelle version du parcours : il sera recréé), « refreshed »
    (nouvelle image du labo : il sera recréé en gardant le dossier personnel) ou « absent »."""
    try:
        container = client().containers.get(get_container_name(user_id, course))
    except docker.errors.NotFound:
        return "absent"
    if container.labels.get("linux-lab.version") != course["version"]:
        return "outdated"
    if _image_changed(container, course):
        return "refreshed"
    return "running" if container.status == "running" else "stopped"


# Empreinte du contenu de chaque image de lab (images/<parcours>), tenue à jour par tests/revisions_images.py
IMAGE_REVISIONS = json.loads(
    (pathlib.Path(__file__).with_name("revisions_images.json")).read_text(encoding="utf-8")
)
REVISION_LABEL = "linux-lab.image-rev"


def _image_changed(container, course: dict) -> bool:
    """Vrai si le contenu de l'image du parcours a changé depuis la création du conteneur.
    On compare l'empreinte du contenu, pas l'identifiant de l'image : reconstruire une image sans la modifier
    (images de base retéléchargées…) change son identifiant et ne doit pas recréer les conteneurs en plein cours."""
    expected = IMAGE_REVISIONS.get(course["key"])
    rev = container.labels.get(REVISION_LABEL)
    if rev is not None:
        return expected is not None and rev != expected
    # Conteneur créé avant les empreintes : recréé seulement si l'image actuelle est PLUS RÉCENTE que la sienne
    # (une ancienne construction remise en place par le cache ne doit pas provoquer de recréation)
    try:
        current = client().images.get(course["image"])
        own = client().images.get(container.attrs.get("Image"))
    except docker.errors.ImageNotFound:
        return False
    return own.id != current.id and current.attrs.get("Created", "") > own.attrs.get("Created", "")


# Copie de secours des dossiers personnels avant recréation d'un conteneur (volume de la plateforme)
HOME_BACKUP_DIR = os.path.join(os.path.dirname(os.environ.get("DB_PATH", "/data/platform.db")), "dossiers-personnels")


def _save_home(container) -> bytes:
    """Archive tar du dossier personnel de l'étudiant, avec une copie de secours sur disque.
    Par tar dans le conteneur : sous Sysbox, l'API de copie de Docker échoue (volume sur /var/lib/docker)."""
    if container.status != "running":
        container.start()
    result = container.exec_run(["tar", "-c", "-C", os.path.dirname(STUDENT_HOME), os.path.basename(STUDENT_HOME)],
                                user="root", demux=True)
    if result.exit_code != 0 or not result.output[0]:
        raise RuntimeError(f"Archive du dossier personnel de {container.name} impossible : {result.output[1]!r}")
    os.makedirs(HOME_BACKUP_DIR, exist_ok=True)
    with open(os.path.join(HOME_BACKUP_DIR, f"{container.name}-{time.strftime('%Y%m%d-%H%M%S')}.tar"), "wb") as f:
        f.write(result.output[0])
    return result.output[0]


def _restore_home(container, data: bytes):
    """Extrait l'archive du dossier personnel dans le nouveau conteneur (tar lit l'entrée standard)."""
    api = client().api
    ex = api.exec_create(container.id, ["tar", "-x", "-p", "-C", os.path.dirname(STUDENT_HOME)],
                         stdin=True, user="root")
    sock = api.exec_start(ex["Id"], socket=True)
    raw = getattr(sock, "_sock", sock)
    raw.sendall(data)
    raw.shutdown(socket.SHUT_WR)
    while raw.recv(65536):
        pass
    raw.close()
    code = api.exec_inspect(ex["Id"])["ExitCode"]
    if code != 0:
        raise RuntimeError(f"Restauration du dossier personnel dans {container.name} impossible (tar : code {code})")


def _get_or_create(user_id: int, course: dict, name: str) -> str:
    home = None
    try:
        container = client().containers.get(name)
        if container.labels.get("linux-lab.version") != course["version"]:
            container.remove(force=True)
        elif _image_changed(container, course):
            # Nouvelle image du labo (exercices enrichis, outils ajoutés) : conteneur recréé, dossier personnel
            # conservé. Les mises en place seront rejouées à l'ouverture de chaque étape (marqueurs absents).
            try:
                home = _save_home(container)
            except Exception:
                # Sans copie du travail de l'étudiant, on garde l'ancien conteneur plutôt que de le perdre
                log.exception("Mise à jour de %s impossible : ancien conteneur conservé", name)
                container.reload()
                if container.status != "running":
                    container.start()
                return container.id
            container.remove(force=True)
        else:
            if container.status != "running":
                container.start()
            return container.id
    except docker.errors.NotFound:
        pass

    get_or_create_network()
    extra = {"cap_drop": ["MKNOD", "SETFCAP", "SETPCAP"]}
    dind = course.get("docker_in_docker")
    if dind:
        # Moteur Docker interne : ses images et conteneurs vivent dans un volume dédié
        extra = {"volumes": {docker_volume_name(user_id, course): {"bind": "/var/lib/docker", "mode": "rw"}}}
        if dind == "privileged":
            extra["privileged"] = True
        else:
            extra["runtime"] = dind
    container = client().containers.run(
        course["image"],
        name=name,
        hostname="linux-lab",
        detach=True,
        stdin_open=True,
        tty=True,
        init=True,  # tini en PID 1 : récupère les processus orphelins
        network=NETWORK_NAME,
        mem_limit=course["mem_limit"],
        cpu_period=100000,
        cpu_quota=course["cpu_quota"],
        pids_limit=course["pids_limit"],  # protège l'hôte d'une fork bomb
        **extra,
        labels={
            "linux-lab": "student",
            "linux-lab.user": str(user_id),
            "linux-lab.course": course["key"],
            "linux-lab.version": course["version"],
            REVISION_LABEL: IMAGE_REVISIONS.get(course["key"], ""),
        },
    )
    # Laisse start.sh préparer le conteneur avant les premières commandes
    for _ in range(20):
        code, _ = exec_in_container(container.id, ["test", "-d", "/run/lab-setup"])
        if code == 0:
            break
        time.sleep(0.25)
    if home is not None:
        try:
            _restore_home(container, home)
        except Exception:
            log.exception("Dossier personnel non restauré dans %s (copie de secours dans %s)", name, HOME_BACKUP_DIR)
    return container.id


def exec_in_container(container_id: str, cmd, env: dict = None, user: str = "root",
                      workdir: str = STUDENT_HOME) -> tuple:
    """Exécute une commande (liste d'arguments ou chaîne bash). Retourne (code, stdout).
    Appel bloquant : à lancer dans un thread (run_in_threadpool) depuis une route async."""
    if isinstance(cmd, str):
        cmd = ["bash", "-c", cmd]
    try:
        container = client().containers.get(container_id)
        result = container.exec_run(cmd, demux=True, environment=env or {}, user=user, workdir=workdir)
        stdout = result.output[0].decode(errors="replace") if result.output and result.output[0] else ""
        return result.exit_code, stdout
    except Exception as e:  # conteneur arrêté, supprimé…
        return 1, str(e)


def create_exec_stream(container_id: str, command: list = None):
    """Ouvre un shell de connexion interactif (PTY) en tant qu'étudiant, ou la commande donnée (même PTY)."""
    container = client().containers.get(container_id)
    exec_instance = client().api.exec_create(
        container.id,
        command or ["bash", "-l"],
        stdin=True,
        stdout=True,
        stderr=True,
        tty=True,
        user=STUDENT_USER,
        workdir=STUDENT_HOME,
        environment={"TERM": "xterm-256color", "HOME": STUDENT_HOME, "USER": STUDENT_USER},
    )
    sock = client().api.exec_start(exec_instance["Id"], socket=True, tty=True)
    return exec_instance["Id"], sock


def resize_exec(exec_id: str, rows: int, cols: int):
    try:
        client().api.exec_resize(exec_id, height=rows, width=cols)
    except Exception:
        pass


def remove_container(user_id: int, course: dict = None):
    """Supprime le conteneur d'un parcours, ou de tous les parcours si course est None."""
    for c in ([course] if course else COURSES.values()):
        try:
            client().containers.get(get_container_name(user_id, c)).remove(force=True)
        except docker.errors.NotFound:
            pass
        if c.get("docker_in_docker"):
            try:
                client().volumes.get(docker_volume_name(user_id, c)).remove(force=True)
            except docker.errors.NotFound:
                pass


def stop_idle_containers(last_activity: dict, active: set, max_idle_seconds: int, default_ts: float) -> list:
    """Arrête (sans les supprimer : le travail est conservé) les conteneurs inactifs depuis
    plus de max_idle_seconds et sans terminal ouvert. Clés : (user_id, parcours)."""
    now = time.time()
    stopped = []
    for c in client().containers.list(filters={"label": "linux-lab=student", "status": "running"}):
        try:
            key = (int(c.labels.get("linux-lab.user", "")), c.labels.get("linux-lab.course", "linux"))
        except ValueError:
            continue
        if key in active:
            continue
        if now - last_activity.get(key, default_ts) > max_idle_seconds:
            c.stop(timeout=5)
            stopped.append(c.name)
    return stopped


def list_student_containers():
    seen = {}
    for prefix in {c["container_prefix"] for c in COURSES.values()}:
        for c in client().containers.list(all=True, filters={"name": prefix}):
            seen[c.name] = {"name": c.name, "status": c.status, "id": c.short_id,
                            "course": c.labels.get("linux-lab.course", "linux")}
    return list(seen.values())
