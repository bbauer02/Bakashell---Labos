"""QCM noté de fin de cours : pour chaque étape, QUIZ_QUESTIONS questions tirées au sort parmi celles du parcours
(courses/<parcours>/quiz.py), choix mélangés, une seule tentative, corrigé côté serveur.

Le tirage dépend de l'étudiant, du parcours et de l'étape : il est stable (même quiz si l'étudiant recharge la
page) mais diffère d'un étudiant à l'autre. Les bonnes réponses ne sont envoyées au navigateur qu'après la
tentative.
"""
import hashlib
import random

from .courses import QUIZ_QUESTIONS

_SALT = "quiz-cimes-et-sentiers"


def _rng(user_id: int, course: dict, step: int) -> random.Random:
    seed = hashlib.sha256(f"{_SALT}:{user_id}:{course['key']}:{step}".encode()).hexdigest()
    return random.Random(seed)


def _correct(question: dict) -> set:
    a = question["answer"]
    return set(a) if isinstance(a, (list, tuple)) else {a}


def draw(user_id: int, course: dict, step: int) -> list:
    """Questions de l'étudiant : [(question, ordre des choix)] ; ordre[i] = index d'origine du choix affiché en i."""
    pool = course.get("quiz", {}).get(step) or []
    if len(pool) < QUIZ_QUESTIONS:
        return []
    rng = _rng(user_id, course, step)
    drawn = []
    for q in rng.sample(pool, QUIZ_QUESTIONS):
        order = list(range(len(q["choices"])))
        rng.shuffle(order)
        drawn.append((q, order))
    return drawn


def public(drawn: list) -> list:
    """Ce que voit l'étudiant avant de répondre : questions et choix mélangés, sans les réponses."""
    return [{"q": q["q"], "choices": [q["choices"][i] for i in order], "multi": len(_correct(q)) > 1}
            for q, order in drawn]


def grade(drawn: list, answers: list) -> tuple:
    """answers : pour chaque question, les index des choix cochés (dans l'ordre affiché).
    Une question rapporte 1 point si l'ensemble des choix cochés est exactement l'ensemble des bonnes réponses.
    Retourne (points, détails affichables après la tentative)."""
    points, details = 0, []
    for n, (q, order) in enumerate(drawn):
        raw = answers[n] if n < len(answers) and isinstance(answers[n], list) else []
        chosen = sorted({i for i in raw if isinstance(i, int) and 0 <= i < len(order)})
        correct = sorted(pos for pos, orig in enumerate(order) if orig in _correct(q))
        ok = chosen == correct
        points += ok
        details.append({"q": q["q"], "choices": [q["choices"][i] for i in order], "chosen": chosen,
                        "correct": correct, "ok": ok, "explain": q.get("explain", "")})
    return points, details
