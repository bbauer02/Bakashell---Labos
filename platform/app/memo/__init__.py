"""Mémo des commandes (« Pokédex ») : des fiches débloquées au fil des exercices réussis.

Chaque fiche indique les exercices qui la débloquent (« unlock ») ; aucune donnée n'est stockée :
le déblocage se calcule à partir de la progression de l'étudiant.
"""
from . import docker, jest, linux

MEMOS = {"linux": linux.CARDS, "jest": jest.CARDS, "docker": docker.CARDS}


def check(courses: dict, exercise_index: dict):
    """Au démarrage : identifiants uniques, et chaque fiche débloquée par un exercice existant du parcours."""
    for key, cards in MEMOS.items():
        ids = [c["id"] for c in cards]
        assert len(ids) == len(set(ids)), f"Mémo {key} : identifiants de fiche en double"
        for c in cards:
            assert c["unlock"], f"Mémo {key} : la fiche {c['id']} n'est débloquée par aucun exercice"
            for ex in c["unlock"]:
                assert ex in exercise_index and exercise_index[ex][0] == key, \
                    f"Mémo {key} : la fiche {c['id']} dépend de l'exercice inconnu {ex}"


def _unlocked(card, completed) -> bool:
    return any(ex in completed for ex in card["unlock"])


def build(course: dict, completed, full_access: bool = False) -> dict:
    """Fiches du parcours : contenu complet si débloquée, sinon seulement la catégorie et l'étape où la trouver."""
    completed = set(completed)
    first_exercise = {ex["id"]: n for n, s in course["steps"].items() for ex in s["exercises"]}
    cards = []
    for c in MEMOS.get(course["key"], []):
        step = min(first_exercise[ex] for ex in c["unlock"])
        entry = {"id": c["id"], "category": c["category"], "step": step, "step_title": course["steps"][step]["title"],
                 "unlocked": full_access or _unlocked(c, completed), "earned": _unlocked(c, completed)}
        if entry["unlocked"]:
            entry.update(name=c["name"], desc=c["desc"], syntax=c["syntax"],
                         examples=[{"code": code, "note": note} for code, note in c["examples"]])
        cards.append(entry)
    return {"cards": cards, "total": len(cards), "unlocked": sum(1 for c in cards if c["earned"])}


def counts(course_key: str, completed) -> tuple:
    completed = set(completed)
    cards = MEMOS.get(course_key, [])
    return sum(1 for c in cards if _unlocked(c, completed)), len(cards)


def discoveries(course_key: str, before, after) -> list:
    """Fiches débloquées par les exercices réussis entre « before » et « after »."""
    before, after = set(before), set(after)
    return [{"id": c["id"], "name": c["name"]} for c in MEMOS.get(course_key, [])
            if _unlocked(c, after) and not _unlocked(c, before)]
