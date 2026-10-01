"""Progression ludique : grade par labo, altitude gravie sur le sentier, réponse du collègue à un ticket résolu.

Rien ici ne change la note : grades et altitude se déduisent des points, déjà comptés ailleurs.
"""
import zlib

# Grades d'un labo, selon la part des points obtenus (seuil en %, nom, icône)
GRADES = [
    (0, "Stagiaire", "🎒"),
    (15, "Junior", "🥾"),
    (40, "Confirmé·e", "🧗"),
    (70, "Senior", "⛰"),
    (90, "Référent·e", "🏔"),
]

# Sommet visé par chaque labo : les points se convertissent en mètres gravis
SUMMITS = {
    "linux": ("Mont Blanc", 4808),
    "jest": ("Barre des Écrins", 4102),
    "docker": ("Grande Casse", 3855),
    "git": ("Pic du Midi d'Ossau", 2884),
    "ansible": ("Vignemale", 3298),
    "projet": ("Aiguille du Midi", 3842),
}
DEFAULT_SUMMIT = ("Sommet", 3000)

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


def altitude(course_key: str, score: int, max_score: int) -> dict:
    name, height = SUMMITS.get(course_key, DEFAULT_SUMMIT)
    return {"summit": name, "height": height, "meters": round(height * score / max_score) if max_score else 0}


def progression(course: dict, score: int) -> dict:
    """Grade et altitude d'un labo (pas de grade pour une épreuve notée)."""
    out = {"altitude": altitude(course["key"], score, course["max_score"])}
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
