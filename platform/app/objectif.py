"""Objectif collectif de classe : les tickets résolus ensemble, par paliers, annoncés par Sophie.

Le potentiel d'une classe est son nombre d'étudiants × les exercices des labos qui lui sont ouverts (hors épreuve
notée) : les paliers s'adaptent d'eux-mêmes à la taille de la classe. Aucun classement, aucun nom : le total, la
semaine écoulée, le nombre d'étudiants actifs, et pour l'étudiant connecté sa propre part. Sans effet sur la note.
"""
from . import database as db
from .courses import COURSES
from .scenario import CHARACTERS

# (part du potentiel en %, message de Sophie quand le palier est atteint)
PALIERS = [
    (5, "Les premiers tickets tombent : l'équipe démarre bien !"),
    (15, "La file d'attente du support diminue à vue d'œil. Continuez comme ça."),
    (30, "La direction a remarqué la différence. Bravo à toute l'équipe."),
    (50, "La moitié du chantier est derrière nous. Pizza pour tout le monde vendredi 🍕"),
    (75, "Marc n'aurait jamais cru ça possible. Plus que la dernière ligne droite !"),
    (100, "Tout est en ordre. Cimes & Sentiers vous doit une fière chandelle 🎉"),
]


def compute(class_id: int, course_keys, user_id: int = None):
    """Avancement de la classe, ou None si elle n'a ni étudiant ni labo comptabilisé."""
    keys = [k for k in course_keys if k in COURSES and not COURSES[k].get("exam")]
    counts = db.class_progress_counts(class_id, [COURSES[k]["id_glob"] for k in keys], user_id)
    potential = counts["students"] * sum(COURSES[k]["total_exercises"] for k in keys)
    if not potential:
        return None
    total = counts["total"]
    tiers = [{"pct": pct, "target": -(-pct * potential // 100), "message": msg} for pct, msg in PALIERS]
    reached = sum(1 for t in tiers if total >= t["target"])
    previous = tiers[reached - 1]["target"] if reached else 0
    nxt = tiers[reached] if reached < len(tiers) else None
    # Barre alignée sur les losanges des paliers, répartis à égale distance (palier k au centre de sa colonne)
    n = len(tiers)
    pos = [0] + [(k - .5) / n for k in range(1, n + 1)]
    frac = (total - previous) / (nxt["target"] - previous) if nxt else 0
    bar = 100 if not nxt else 100 * (pos[reached] + frac * (pos[reached + 1] - pos[reached]))
    sophie = CHARACTERS["sophie"]
    return {
        **counts, "potential": potential, "tiers": tiers, "reached": reached,
        "next": nxt, "remaining": nxt["target"] - total if nxt else 0,
        "bar_pct": round(bar, 1),
        "message": tiers[reached - 1]["message"] if reached else None,
        "from": {"name": sophie["name"], "color": sophie["color"],
                 "initials": "".join(w[0] for w in sophie["name"].split()[:2])},
    }
