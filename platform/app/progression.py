"""Progression ludique de Bakashell : grade par labo, intrusion jusqu'au noyau, réponse du collègue au ticket résolu.

Univers de la plateforme (le « bac à shell ») : cyberpunk, à la Neuromancer. Chaque étape d'un labo est une couche
d'ICE (les pare-feu du roman) à percer pour atteindre le noyau. L'histoire des tickets, elle, se passe chez
Cimes & Sentiers (scenario.py).

Rien ici ne change la note : grades et couches se déduisent des points et des étapes, déjà comptés ailleurs.
"""
import zlib

# Grades d'un labo, selon la part des points obtenus (seuil en %, nom, icône) : de la recrue au ghost (in the shell)
GRADES = [
    (0, "Recrue", "🔰"),
    (15, "Opérateur·rice", "🎧"),
    (40, "Hacker", "💻"),
    (70, "Architecte", "📐"),
    (90, "Ghost", "👻"),
]

# Noyau visé par chaque labo, au bout des couches d'ICE
CORES = {
    "linux": "Ring 0",
    "jest": "Zoo des mutants",
    "docker": "Port franc",
    "git": "Arbre des commits",
    "ansible": "La Ruche",
    "projet": "Cœur de prod",
}
DEFAULT_CORE = "Noyau"

# Réponses des collègues quand leur ticket est résolu : neutres, elles conviennent à tous leurs tickets.
# Un exercice peut fixer la sienne avec ticket["reply"].
REPLIES = {
    "sophie": ["Parfait, je clôture le ticket. Merci !", "Impeccable, c'est exactement ce qu'il fallait.",
               "Merci, je le note dans le compte rendu de la semaine.", "Très bien, un souci de moins. Merci !"],
    "lea": ["Propre. Je valide.", "Bien joué, rien à redire.", "C'est ça. Garde ce réflexe, il resservira.",
            "Vérifié de mon côté : c'est bon. Merci !"],
    "nadia": ["Nickel, je valide de mon côté 👍", "Bien vu, merci !", "C'est carré. On garde ça comme référence.",
              "Top, l'équipe va pouvoir avancer. Merci !"],
    "thomas": ["Génial, ça marche chez moi aussi 🙌", "Merci, tu me sauves la journée !",
               "Super, je n'aurais pas trouvé tout seul.", "Parfait, je reprends mon travail. Merci !"],
    "diallo": ["Merci, la compta peut avancer.", "Parfait, c'est exactement ce que j'attendais.",
               "Merci beaucoup, c'est clair et propre.", "Très bien, je transmets à l'équipe. Merci !"],
    "julien": ["Ah d'accord, je comprends mieux maintenant, merci !!", "Trop bien, merci ! Je note ça dans mon carnet.",
               "Merci, désolé pour le dérangement 😅", "Wow, merci ! Tu m'expliqueras comment tu as fait ?"],
}


def grade(score: int, max_score: int) -> dict:
    """Grade atteint et suivant, à partir des points."""
    pct = 100 * score / max_score if max_score else 0
    rank = max(i for i, (seuil, _, _) in enumerate(GRADES) if pct >= seuil)
    _, name, icon = GRADES[rank]
    out = {"rank": rank, "name": name, "icon": icon}
    if rank + 1 < len(GRADES):
        seuil, nxt, _ = GRADES[rank + 1]
        out["next"] = nxt
        out["next_points"] = max(0, -(-seuil * max_score // 100) - score)  # points manquants (arrondi au-dessus)
    return out


def breach(course: dict, completed) -> dict:
    """Couches d'ICE percées : les étapes entièrement réussies du labo."""
    completed = set(completed)
    layers = sum(1 for st in course["steps"].values()
                 if st["exercises"] and all(ex["id"] in completed for ex in st["exercises"]))
    return {"core": CORES.get(course["key"], DEFAULT_CORE), "layers": layers, "total": len(course["steps"])}


def progression(course: dict, score: int, completed) -> dict:
    """Grade et couches percées d'un labo (pas de grade pour une épreuve notée)."""
    out = {"breach": breach(course, completed)}
    if not course.get("exam"):
        out["grade"] = grade(score, course["max_score"])
        out["grades"] = [{"pct": s, "name": n, "icon": i} for s, n, i in GRADES]
    return out


def reply(ticket: dict, exercise_id: str) -> str:
    """Réponse du collègue au ticket résolu, toujours la même pour un exercice donné."""
    if ticket.get("reply"):
        return ticket["reply"]
    choices = REPLIES.get(ticket["from"], ["Merci !"])
    return choices[zlib.crc32(exercise_id.encode()) % len(choices)]
