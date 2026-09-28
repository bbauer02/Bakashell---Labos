"""Gestion des conteneurs Docker des étudiants (un conteneur par étudiant et par parcours)."""
import os
import threading
import time

import docker

from .courses import COURSES

# Réseau dédié aux étudiants, sans communication entre conteneurs (ICC désactivé).
NETWORK_NAME = os.environ.get("LAB_NETWORK", "linux-lab-students")
STUDENT_USER = "etudiant"
STUDENT_HOME = "/home/etudiant"

client = docker.from_env()

# Un verrou par conteneur : le terminal et la préparation d'étape peuvent le demander en même temps
_create_locks: dict = {}
_create_guard = threading.Lock()


def _lock_for(name: str) -> threading.Lock:
    with _create_guard:
        return _create_locks.setdefault(name, threading.Lock())


def get_or_create_network():
    try:
        return client.networks.get(NETWORK_NAME)
    except docker.errors.NotFound:
        return client.networks.create(
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


def _get_or_create(user_id: int, course: dict, name: str) -> str:
    try:
        container = client.containers.get(name)
        if container.labels.get("linux-lab.version") != course["version"]:
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
    container = client.containers.run(
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
        },
    )
    # Laisse start.sh préparer le conteneur avant les premières commandes
    for _ in range(20):
        code, _ = exec_in_container(container.id, ["test", "-d", "/run/lab-setup"])
        if code == 0:
            break
        time.sleep(0.25)
    return container.id


def exec_in_container(container_id: str, cmd, env: dict = None, user: str = "root",
                      workdir: str = STUDENT_HOME) -> tuple:
    """Exécute une commande (liste d'arguments ou chaîne bash). Retourne (code, stdout).
    Appel bloquant : à lancer dans un thread (run_in_threadpool) depuis une route async."""
    if isinstance(cmd, str):
        cmd = ["bash", "-c", cmd]
    try:
        container = client.containers.get(container_id)
        result = container.exec_run(cmd, demux=True, environment=env or {}, user=user, workdir=workdir)
        stdout = result.output[0].decode(errors="replace") if result.output and result.output[0] else ""
        return result.exit_code, stdout
    except Exception as e:  # conteneur arrêté, supprimé…
        return 1, str(e)


def create_exec_stream(container_id: str):
    """Ouvre un shell de connexion interactif (PTY) en tant qu'étudiant."""
    container = client.containers.get(container_id)
    exec_instance = client.api.exec_create(
        container.id,
        ["bash", "-l"],
        stdin=True,
        stdout=True,
        stderr=True,
        tty=True,
        user=STUDENT_USER,
        workdir=STUDENT_HOME,
        environment={"TERM": "xterm-256color", "HOME": STUDENT_HOME, "USER": STUDENT_USER},
    )
    sock = client.api.exec_start(exec_instance["Id"], socket=True, tty=True)
    return exec_instance["Id"], sock


def resize_exec(exec_id: str, rows: int, cols: int):
    try:
        client.api.exec_resize(exec_id, height=rows, width=cols)
    except Exception:
        pass


def remove_container(user_id: int, course: dict = None):
    """Supprime le conteneur d'un parcours, ou de tous les parcours si course est None."""
    for c in ([course] if course else COURSES.values()):
        try:
            client.containers.get(get_container_name(user_id, c)).remove(force=True)
        except docker.errors.NotFound:
            pass
        if c.get("docker_in_docker"):
            try:
                client.volumes.get(docker_volume_name(user_id, c)).remove(force=True)
            except docker.errors.NotFound:
                pass


def stop_idle_containers(last_activity: dict, active: set, max_idle_seconds: int, default_ts: float) -> list:
    """Arrête (sans les supprimer : le travail est conservé) les conteneurs inactifs depuis
    plus de max_idle_seconds et sans terminal ouvert. Clés : (user_id, parcours)."""
    now = time.time()
    stopped = []
    for c in client.containers.list(filters={"label": "linux-lab=student", "status": "running"}):
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
        for c in client.containers.list(all=True, filters={"name": prefix}):
            seen[c.name] = {"name": c.name, "status": c.status, "id": c.short_id,
                            "course": c.labels.get("linux-lab.course", "linux")}
    return list(seen.values())
