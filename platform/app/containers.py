"""Gestion des conteneurs Docker des étudiants."""
import os
import time

import docker

from .exercises import EXERCISES_VERSION

LAB_IMAGE = os.environ.get("LAB_IMAGE", "linux-lab")
# Réseau dédié aux étudiants, sans communication entre conteneurs (ICC désactivé).
NETWORK_NAME = os.environ.get("LAB_NETWORK", "linux-lab-students")
CONTAINER_PREFIX = "lab-student-"
STUDENT_USER = "etudiant"
STUDENT_HOME = "/home/etudiant"

client = docker.from_env()


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


def get_container_name(user_id: int) -> str:
    return f"{CONTAINER_PREFIX}{user_id}"


def get_or_create_container(user_id: int) -> str:
    """Retourne l'ID du conteneur de l'étudiant (démarré), en le créant si besoin.
    Un conteneur créé pour une autre version du catalogue est recréé."""
    name = get_container_name(user_id)

    try:
        container = client.containers.get(name)
        if container.labels.get("linux-lab.version") != EXERCISES_VERSION:
            container.remove(force=True)
        else:
            if container.status != "running":
                container.start()
            return container.id
    except docker.errors.NotFound:
        pass

    get_or_create_network()
    container = client.containers.run(
        LAB_IMAGE,
        name=name,
        hostname="linux-lab",
        detach=True,
        stdin_open=True,
        tty=True,
        init=True,  # tini en PID 1 : récupère les processus orphelins
        network=NETWORK_NAME,
        mem_limit="256m",
        cpu_period=100000,
        cpu_quota=50000,  # 50 % d'un CPU
        pids_limit=256,  # protège l'hôte d'une fork bomb
        cap_drop=["MKNOD", "SETFCAP", "SETPCAP"],
        labels={
            "linux-lab": "student",
            "linux-lab.user": str(user_id),
            "linux-lab.version": EXERCISES_VERSION,
        },
    )
    # Laisse start.sh lancer sshd, cron et rsyslog avant les premières commandes
    for _ in range(20):
        code, _ = exec_in_container(container.id, ["pgrep", "-x", "cron"])
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


def stop_container(user_id: int):
    try:
        client.containers.get(get_container_name(user_id)).stop(timeout=5)
    except docker.errors.NotFound:
        pass


def remove_container(user_id: int):
    try:
        client.containers.get(get_container_name(user_id)).remove(force=True)
    except docker.errors.NotFound:
        pass


def stop_idle_containers(last_activity: dict, active_users: set, max_idle_seconds: int, default_ts: float) -> list:
    """Arrête (sans les supprimer : le travail est conservé) les conteneurs
    inactifs depuis plus de max_idle_seconds et sans terminal ouvert."""
    now = time.time()
    stopped = []
    for c in client.containers.list(filters={"label": "linux-lab=student", "status": "running"}):
        try:
            user_id = int(c.labels.get("linux-lab.user", c.name.replace(CONTAINER_PREFIX, "")))
        except ValueError:
            continue
        if user_id in active_users:
            continue
        if now - last_activity.get(user_id, default_ts) > max_idle_seconds:
            c.stop(timeout=5)
            stopped.append(c.name)
    return stopped


def list_student_containers():
    containers = client.containers.list(all=True, filters={"name": CONTAINER_PREFIX})
    return [{"name": c.name, "status": c.status, "id": c.short_id} for c in containers]
