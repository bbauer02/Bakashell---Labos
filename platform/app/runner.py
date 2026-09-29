"""Construction des commandes de mise en place / vérification et lecture de leurs résultats.

Module sans dépendance à Docker ni à la base : utilisé par la plateforme et par les tests.
Chaque fonction reçoit le parcours (dict de courses.COURSES) pour ses préludes et délais.
"""
import hashlib
import html
import json
import pathlib
import posixpath
import re
import secrets

SETUP_TIMEOUT = 120

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


def setup_command(course: dict, step_num: int, step: dict) -> list:
    marker = marker_path(step_num, step)
    script = (
        course["setup_prelude"]
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
    # Les clés « _… » sont des métadonnées de la plateforme (empreinte), pas des valeurs attendues
    return {f"LAB_{k}": v for k, v in (setup_data or {}).items() if not k.startswith("_")}


# Empreintes des mises en place publiées avant leur enregistrement en base (données sans « _empreinte »)
_LEGACY_FINGERPRINTS = json.loads(
    (pathlib.Path(__file__).with_name("empreintes_mises_en_place.json")).read_text(encoding="utf-8")
)


def setup_fingerprint(step: dict) -> str:
    """Empreinte du script de mise en place d'une étape : change quand l'étape est modifiée."""
    return hashlib.sha256(step.get("setup", "").encode()).hexdigest()[:16]


def setup_outdated(course: dict, step_num: int, step: dict, setup_data) -> bool:
    """Vrai si l'étape a été préparée par une ancienne version de sa mise en place."""
    if setup_data is None or not has_setup(step):
        return False
    done_with = setup_data.get("_empreinte") or _LEGACY_FINGERPRINTS.get(f"{course['key']}:{step_num}")
    return done_with is not None and done_with != setup_fingerprint(step)


def check_command(course: dict, exercise: dict) -> list:
    """Un seul `docker exec` par exercice : les vérifications s'enchaînent, la première
    en échec est signalée par « @@FAIL <index> », suivie des lignes « MSG:… » qu'elle a produites."""
    return ["timeout", "-k", "5", str(course["check_timeout"]), "bash", "-c",
            _check_script(course["check_prelude"], exercise)]


def _check_script(prelude: str, exercise: dict) -> str:
    parts = [prelude, _UNEXPORT, "cd /home/etudiant\n", '_out=$(mktemp)\n']
    for i, (cmd, _msg) in enumerate(exercise["checks"]):
        parts.append(
            f"( {cmd}\n) >\"$_out\" 2>/dev/null </dev/null || "
            f"{{ echo '@@FAIL {i}'; grep '^MSG:' \"$_out\" | tail -n 3; rm -f \"$_out\"; exit 0; }}\n"
        )
    parts.append('rm -f "$_out"\necho \'@@OK\'\n')
    return "".join(parts)


def check_batch_script(course: dict, exercises: list) -> tuple:
    """Script de check_batch_command et son délai global (le banc de test l'envoie par l'entrée standard)."""
    timeout = course["check_timeout"]
    # Le prélude n'est écrit qu'une fois : un argument de commande est limité à 128 Ko sous Linux
    tag = f"__LAB_{secrets.token_hex(8)}__"
    parts = ['_lab_d=$(mktemp -d)\n', f"cat > \"$_lab_d/prelude\" <<'{tag}'\n{course['check_prelude']}\n{tag}\n"]
    for i, ex in enumerate(exercises):
        body = _check_script('. "$_lab_d/prelude"\n', ex)
        parts.append(f"cat > \"$_lab_d/{i}\" <<'{tag}'\n{body}\n{tag}\n")
    for i, ex in enumerate(exercises):
        parts.append(f"echo '@@EX {ex['id']}'\n_lab_d=\"$_lab_d\" timeout -k 5 {timeout} bash \"$_lab_d/{i}\"\n"
                     "echo \"@@CODE $?\"\n")
    parts.append('rm -rf "$_lab_d"\n')
    return "".join(parts), timeout * len(exercises) + 15


def check_batch_command(course: dict, exercises: list) -> list:
    """Vérifie plusieurs exercices en UN seul `docker exec` (le lancement d'un exec coûte bien plus cher que les
    vérifications elles-mêmes). Chaque exercice garde son propre bash et son propre délai : un exercice bloqué
    n'empêche pas de vérifier les autres. Sortie : « @@EX <id> », la sortie de check_command, « @@CODE <code> »."""
    script, total = check_batch_script(course, exercises)
    return ["timeout", "-k", "5", str(total), "bash", "-c", script]


def parse_batch_output(exercises: list, output: str) -> dict:
    """Résultat de check_batch_command : {identifiant: (réussi, message)}."""
    segments = {}
    current = None
    for line in output.splitlines(keepends=True):
        if line.startswith("@@EX "):
            current = line[5:].strip()
            segments[current] = ""
        elif current is not None:
            segments[current] += line
    results = {}
    for ex in exercises:
        seg = segments.get(ex["id"])
        if seg is None:  # délai global dépassé avant cet exercice
            results[ex["id"]] = parse_check_output(ex, 124, "")
            continue
        m = re.search(r"^@@CODE (\d+)$", seg, re.M)
        results[ex["id"]] = parse_check_output(ex, int(m.group(1)) if m else 124, seg)
    return results


def parse_check_output(exercise: dict, exit_code: int, output: str):
    """Retourne (réussi, message d'échec HTML ou None)."""
    if "@@OK" in output:
        return True, None
    m = re.search(r"@@FAIL (\d+)", output)
    if m:
        idx = int(m.group(1))
        checks = exercise["checks"]
        if 0 <= idx < len(checks):
            message = checks[idx][1]
            details = [html.escape(line[4:].strip()) for line in output[m.end():].splitlines() if line.startswith("MSG:")]
            if details:
                message += "<br><span class='fail-detail'>" + "<br>".join(details) + "</span>"
            return False, message
    if exit_code in (124, 137):
        return False, "La vérification a dépassé le délai autorisé : un de vos scripts ou tests attend-il indéfiniment ?"
    return False, "La vérification n'a pas pu aboutir. Réessayez dans un instant."
