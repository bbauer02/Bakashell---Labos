"""Docker container management for student labs."""
import asyncio
import docker
import os
import struct
import fcntl
import termios

LAB_IMAGE = os.environ.get("LAB_IMAGE", "linux-lab")
NETWORK_NAME = os.environ.get("LAB_NETWORK", "linux-lab-net")
CONTAINER_PREFIX = "lab-student-"

client = docker.from_env()


def get_or_create_network():
    """Ensure the lab network exists."""
    try:
        return client.networks.get(NETWORK_NAME)
    except docker.errors.NotFound:
        return client.networks.create(NETWORK_NAME, driver="bridge")


def get_container_name(user_id: int) -> str:
    return f"{CONTAINER_PREFIX}{user_id}"


def get_or_create_container(user_id: int) -> str:
    """Get existing or create new container for a student. Returns container ID."""
    name = get_container_name(user_id)

    try:
        container = client.containers.get(name)
        if container.status != "running":
            container.start()
        return container.id
    except docker.errors.NotFound:
        pass

    network = get_or_create_network()
    container = client.containers.run(
        LAB_IMAGE,
        name=name,
        hostname="linux-lab",
        detach=True,
        stdin_open=True,
        tty=True,
        network=NETWORK_NAME,
        mem_limit="256m",
        cpu_period=100000,
        cpu_quota=50000,  # 50% of one CPU
    )
    return container.id


def exec_in_container(container_id: str, cmd: str) -> tuple:
    """Execute a command in a container. Returns (exit_code, output)."""
    try:
        container = client.containers.get(container_id)
        result = container.exec_run(["bash", "-c", cmd], demux=True)
        stdout = result.output[0].decode() if result.output[0] else ""
        return result.exit_code, stdout
    except Exception as e:
        return 1, str(e)


def create_exec_stream(container_id: str):
    """Create an interactive exec session with PTY. Returns (exec_id, socket)."""
    container = client.containers.get(container_id)

    exec_instance = client.api.exec_create(
        container.id,
        "bash",
        stdin=True,
        stdout=True,
        stderr=True,
        tty=True,
        environment={"TERM": "xterm-256color"},
    )

    sock = client.api.exec_start(
        exec_instance["Id"],
        socket=True,
        tty=True,
    )

    return exec_instance["Id"], sock


def resize_exec(exec_id: str, rows: int, cols: int):
    """Resize the PTY of an exec session."""
    try:
        client.api.exec_resize(exec_id, height=rows, width=cols)
    except Exception:
        pass


def stop_container(user_id: int):
    """Stop a student's container."""
    name = get_container_name(user_id)
    try:
        container = client.containers.get(name)
        container.stop(timeout=5)
    except docker.errors.NotFound:
        pass


def remove_container(user_id: int):
    """Remove a student's container."""
    name = get_container_name(user_id)
    try:
        container = client.containers.get(name)
        container.remove(force=True)
    except docker.errors.NotFound:
        pass


def cleanup_idle_containers(max_idle_seconds: int = 1800):
    """Remove containers idle for more than max_idle_seconds."""
    import datetime
    containers = client.containers.list(
        all=True,
        filters={"name": CONTAINER_PREFIX},
    )
    for c in containers:
        if c.status == "running":
            # Check last activity via process count or similar heuristic
            pass  # For now, don't auto-cleanup running containers


def list_student_containers():
    """List all student containers and their status."""
    containers = client.containers.list(
        all=True,
        filters={"name": CONTAINER_PREFIX},
    )
    return [
        {"name": c.name, "status": c.status, "id": c.short_id}
        for c in containers
    ]
