"""Construction des commandes de mise en place / vérification et lecture de leurs résultats.

Module sans dépendance à Docker ni à la base : utilisé par la plateforme et par les tests.
"""
import posixpath
import re

from .exercises import CHECK_PRELUDE, SETUP_PRELUDE

SETUP_TIMEOUT = 120
CHECK_TIMEOUT = 45

PERSISTENT_MARKERS = "/var/lib/lab/setup"
VOLATILE_MARKERS = "/run/lab-setup"  # vidé par start.sh à chaque démarrage du conteneur

# Les valeurs LAB_* servent aux vérifications : on ne les transmet pas aux
# programmes de l'étudiant exécutés pendant la vérification.
_UNEXPORT = 'for _v in ${!LAB_@}; do declare +x "$_v"; done\n'


def has_setup(step: dict) -> bool:
    return bool(step.get("setup", "").strip())


def marker_path(step_num: int, step: dict) -> str:
    base = VOLATILE_MARKERS if step.get("volatile") else PERSISTENT_MARKERS
    return f"{base}/step-{step_num}"


def marker_test_command(step_num: int, step: dict) -> list:
    return ["test", "-f", marker_path(step_num, step)]


def setup_command(step_num: int, step: dict) -> list:
    marker = marker_path(step_num, step)
    script = (
        SETUP_PRELUDE
        + step["setup"]
        + f"\nmkdir -p {posixpath.dirname(marker)}\ntouch {marker}\n"
    )
    return ["timeout", "-k", "5", str(SETUP_TIMEOUT), "bash", "-c", script]


def parse_setup_output(output: str) -> dict:
    """Récupère les lignes « @CLE=valeur » émises par un setup."""
    data = {}
    for line in output.splitlines():
        m = re.match(r"^@([A-Z0-9_]+)=(.*)$", line)
        if m:
            data[m.group(1)] = m.group(2)
    return data


def check_env(setup_data: dict) -> dict:
    return {f"LAB_{k}": v for k, v in (setup_data or {}).items()}


def check_command(exercise: dict) -> list:
    """Un seul `docker exec` par exercice : les vérifications s'enchaînent,
    la première en échec est signalée par « @@FAIL <index> »."""
    parts = [CHECK_PRELUDE, _UNEXPORT, "cd /home/etudiant\n"]
    for i, (cmd, _msg) in enumerate(exercise["checks"]):
        parts.append(f"( {cmd}\n) >/dev/null 2>&1 </dev/null || {{ echo '@@FAIL {i}'; exit 0; }}\n")
    parts.append("echo '@@OK'\n")
    return ["timeout", "-k", "5", str(CHECK_TIMEOUT), "bash", "-c", "".join(parts)]


def parse_check_output(exercise: dict, exit_code: int, output: str):
    """Retourne (réussi, message d'échec ou None)."""
    if "@@OK" in output:
        return True, None
    m = re.search(r"@@FAIL (\d+)", output)
    if m:
        idx = int(m.group(1))
        checks = exercise["checks"]
        if 0 <= idx < len(checks):
            return False, checks[idx][1]
    if exit_code in (124, 137):
        return False, "La vérification a dépassé le délai autorisé : un de vos scripts attend-il une saisie ou boucle-t-il sans fin ?"
    return False, "La vérification n'a pas pu aboutir. Réessayez dans un instant."
