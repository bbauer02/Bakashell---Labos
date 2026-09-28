"""Corrigés de référence des parcours.

Chaque parcours fournit un script par étape (exécuté tel quel par le banc de test) dans lequel les lignes
« #@ <exercice> » délimitent la correction de chaque exercice. Ce module découpe ces scripts pour afficher
la correction d'un exercice aux comptes admin.
"""
import re

from .courses.docker import solutions as docker
from .courses.jest import solutions as jest
from .courses.linux import solutions as linux

SCRIPTS = {"linux": linux.SOLUTIONS, "jest": jest.SOLUTIONS, "docker": docker.SOLUTIONS}

_MARKER = re.compile(r"^#@\s*(\S+)\s*$")


def split(script: str):
    """Retourne (préambule, {exercice: code}). Un repère répété ajoute un bloc à l'exercice."""
    preamble, blocks, current = [], {}, None
    for line in script.strip("\n").splitlines():
        m = _MARKER.match(line)
        if m:
            current = m.group(1)
            blocks.setdefault(current, [])
            if blocks[current]:
                blocks[current].append("")
            continue
        (blocks[current] if current else preamble).append(line)
    return "\n".join(preamble).strip("\n"), {k: "\n".join(v).strip("\n") for k, v in blocks.items()}


_INDEX = {}
for _course, _steps in SCRIPTS.items():
    for _num, _script in _steps.items():
        _pre, _blocks = split(_script)
        for _ex, _code in _blocks.items():
            _INDEX[_ex] = {"course": _course, "step": _num, "preamble": _pre, "code": _code}


def for_exercise(exercise_id: str):
    return _INDEX.get(exercise_id)


def check_coverage(courses: dict):
    """Chaque exercice doit avoir une correction : appelé au démarrage de la plateforme."""
    missing = [ex["id"] for c in courses.values() for s in c["steps"].values() for ex in s["exercises"]
               if ex["id"] not in _INDEX]
    unknown = [ex for ex in _INDEX if not any(ex == e["id"] for c in courses.values()
                                              for s in c["steps"].values() for e in s["exercises"])]
    assert not missing, f"Exercices sans correction : {missing}"
    assert not unknown, f"Corrections sans exercice : {unknown}"
