"""Badges : ils récompensent les bonnes pratiques (autonomie, persévérance, régularité), pas seulement le volume.

Tout se calcule à partir des données déjà enregistrées (réussites, indices, vérifications, QCM, attestations) :
rien n'est stocké, et un badge ne change jamais la note.
"""
import datetime
import re

from . import database as db
from . import memo
from .courses import COURSES, EXERCISE_INDEX
from .scenario import CHARACTERS

# (identifiant, icône, nom, ce qu'il faut faire, objectif)
BADGES = [
    ("premier-ticket", "👋", "Hello, world", "Résoudre un premier ticket.", 1),
    ("sans-filet", "🪂", "Sans filet", "Terminer une étape entière sans demander aucun indice.", 1),
    ("autonome", "🐺", "Loup solitaire", "Résoudre 25 tickets sans aucun indice.", 25),
    ("perseverant", "🔨", "Brute force", "Réussir un exercice après au moins 5 vérifications ratées : ne rien lâcher.", 5),
    ("equipe", "🤝", "Toute l'équipe", "Résoudre au moins un ticket de chacun des six collègues.", 6),
    ("archeologue", "🔍", "Forensique", "Résoudre 5 tickets liés à l'héritage de Marc.", 5),
    ("tuteur", "🧑‍🏫", "Mentor de Julien", "Résoudre 5 tickets de Julien, le stagiaire.", 5),
    ("qcm", "🧠", "Mémoire vive", "Réussir 5 QCM de fin de cours sans aucune faute.", 5),
    ("encyclopedie", "📚", "RTFM", "Découvrir toutes les fiches du mémo d'un labo.", 1),
    ("polyvalent", "🧩", "Full stack", "Terminer au moins une étape dans 3 labos différents.", 3),
    ("regulier", "⏰", "Cron humain", "Résoudre des tickets 3 semaines d'affilée.", 3),
    ("sommet", "⚡", "Root", "Atteindre le grade Ghost (90 % des points) dans un labo.", 1),
    ("diplome", "🎓", "Certifié·e", "Obtenir une attestation de fin de parcours.", 1),
]

# Exercices dont le ticket évoque Marc, le prédécesseur
MARC = {ex_id for ex_id, (_, _, _, ex) in EXERCISE_INDEX.items()
        if re.search(r"\bMarc\b", " ".join((ex.get("ticket", {}).get("body", ""), ex["title"], ex["desc"])))}


def _week(ts: str) -> int:
    """Numéro de semaine (lundi) d'une date SQLite « AAAA-MM-JJ HH:MM:SS »."""
    d = datetime.date.fromisoformat(ts[:10])
    return (d.toordinal() - 1) // 7


def _longest_run(weeks) -> int:
    best = run = 0
    prev = None
    for w in sorted(set(weeks)):
        run = run + 1 if prev is not None and w == prev + 1 else 1
        best, prev = max(best, run), w
    return best


def compute(user_id: int) -> list:
    """Tous les badges, avec pour chacun : obtenu ou non, et l'avancement (valeur, objectif)."""
    f = db.badge_facts(user_id)
    # Exercices encore au catalogue (un exercice retiré peut rester dans la progression)
    done = {e: t for e, t in f["completed"].items() if e in EXERCISE_INDEX}
    # L'épreuve notée n'a pas d'indice : elle ne compte pas pour les badges d'autonomie
    practice = {e for e in done if not COURSES[EXERCISE_INDEX[e][0]].get("exam")}
    no_hint = {e for e in practice if not f["hints"].get(e)}

    steps_no_hint, labs_with_step = 0, set()
    for key, course in COURSES.items():
        for step in course["steps"].values():
            ids = [ex["id"] for ex in step["exercises"]]
            if ids and all(i in done for i in ids):
                labs_with_step.add(key)
                if not course.get("exam") and all(i in no_hint for i in ids):
                    steps_no_hint += 1

    senders = {}
    for e in done:
        ticket = EXERCISE_INDEX[e][3].get("ticket")
        if ticket:
            senders[ticket["from"]] = senders.get(ticket["from"], 0) + 1

    memo_best = max((found / total for found, total in (memo.counts(k, done) for k in memo.MEMOS) if total), default=0)
    best_pct = 0
    for key, course in COURSES.items():
        if not course.get("exam") and course["max_score"]:
            best_pct = max(best_pct, 100 * db.get_user_score(user_id, course["id_glob"])["score"] / course["max_score"])

    value = {
        "premier-ticket": len(done),
        "sans-filet": steps_no_hint,
        "autonome": len(no_hint),
        "perseverant": max((f["fails"].get(e, 0) for e in done), default=0),
        "equipe": sum(1 for c in CHARACTERS if senders.get(c)),
        "archeologue": len(MARC & set(done)),
        "tuteur": senders.get("julien", 0),
        "qcm": sum(1 for q in f["quiz"] if q["max_score"] and q["score"] == q["max_score"]),
        "encyclopedie": 1 if memo_best >= 1 else 0,
        "polyvalent": len(labs_with_step),
        "regulier": _longest_run(_week(t) for t in done.values() if t),
        "sommet": 1 if best_pct >= 90 else 0,
        "diplome": 1 if f["certificates"] else 0,
    }
    # Badges à objectif unique : l'avancement montre où l'on en est (mémo, points du meilleur labo)
    progress = {"encyclopedie": (round(100 * memo_best), 100), "sommet": (min(90, int(best_pct)), 90)}
    out = []
    for bid, icon, name, desc, target in BADGES:
        v = value[bid]
        cur, goal = progress.get(bid, (min(v, target), target))
        out.append({"id": bid, "icon": icon, "name": name, "desc": desc, "earned": v >= target,
                    "value": cur, "target": goal, "unit": " %" if bid in progress else ""})
    return out
