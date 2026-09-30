"""Suivi d'intégrité : ce que l'étudiant saisit dans le terminal web, pour aider l'enseignant à repérer le
copier-coller entre étudiants et les réussites suspectes.

- Saisie tapée : reconstituée ligne par ligne (retour arrière pris en compte, séquences d'échappement
  ignorées ; la complétion par Tab n'est pas visible, la ligne peut donc être incomplète).
- Collage : un bloc de texte reçu d'un coup (le navigateur envoie la frappe caractère par caractère, un
  collage en un seul message).
Les étudiants en sont informés sur la page du labo. Les enregistrements sont purgés après RETENTION_DAYS.
"""
import os
import re

RETENTION_DAYS = int(os.environ.get("INTEGRITY_RETENTION_DAYS", "120"))
PASTE_MIN = 15      # caractères imprimables reçus d'un coup à partir desquels on parle de collage
LINE_MAX = 500      # une ligne plus longue est tronquée


class InputRecorder:
    """Reconstitue les lignes saisies dans un terminal et repère les collages ; save(kind, text) enregistre."""

    def __init__(self, save):
        self.save = save
        self.line = ""
        self.escape = 0  # 0 : texte ; 1 : après ESC ; 2 : dans une séquence « ESC [ … » (peut chevaucher deux envois)

    def _strip_escapes(self, data: str) -> str:
        """Retire les séquences d'échappement (flèches, touches de fonction…), même coupées entre deux envois."""
        out = []
        for ch in data:
            if self.escape == 1:
                self.escape = 2 if ch in "[O" else 0
            elif self.escape == 2:
                if "@" <= ch <= "~":  # octet final de la séquence (les paramètres sont des chiffres, « ; », « ? »)
                    self.escape = 0
            elif ch == "\x1b":
                self.escape = 1
            else:
                out.append(ch)
        return "".join(out)

    def feed(self, data: str):
        clean = self._strip_escapes(data)
        printable = sum(1 for ch in clean if ch.isprintable())
        if printable >= PASTE_MIN:
            self.save("collage", clean.strip()[:LINE_MAX * 4])
        for ch in clean:
            if ch in "\r\n":
                if self.line.strip():
                    self.save("ligne", self.line.strip()[:LINE_MAX])
                self.line = ""
            elif ch in "\x7f\b":
                self.line = self.line[:-1]
            elif ch == "\x03" or ch == "\x15":  # Ctrl+C, Ctrl+U : ligne abandonnée
                self.line = ""
            elif ch.isprintable():
                self.line += ch


def normalize(command: str) -> str:
    """Forme comparable d'une commande : espaces multiples réduits, espaces de début et de fin retirés."""
    return re.sub(r"\s+", " ", command).strip()


# ─── Analyse (rapport pour l'enseignant) ────────────────────────────────

RAPID_MIN_S = 20          # une réussite en moins de 20 s…
RAPID_RATIO = 0.2         # … ou en moins de 20 % du temps médian de la classe
RAPID_MEDIAN_MIN_S = 120  # seulement pour les exercices qui prennent d'habitude au moins 2 min
BURST_COUNT, BURST_WINDOW_S = 5, 180
PASTE_REPORT_MIN = 40
SHARED_MIN_LEN = 25
SESSION_GAP_S = 3600


def _median(values):
    s = sorted(values)
    n = len(s)
    return (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2) if s else None


def report(course: dict, names: dict, completions: list, logs: list, reference: str) -> dict:
    """Signaux à examiner (jamais une preuve : l'enseignant juge).
    completions : [(user_id, exercise_id, horodatage en secondes)] ; logs : [(user_id, kind, text, horodatage)] ;
    reference : texte du cours, des tickets et des indices (une commande qui y figure n'est pas suspecte)."""
    step_of = {ex["id"]: (n, ex) for n, s in course["steps"].items() for ex in s["exercises"]}
    by_user = {}
    for uid, ex_id, at in sorted(completions, key=lambda r: (r[0], r[2])):
        if uid in names and ex_id in step_of:
            by_user.setdefault(uid, []).append((ex_id, at))

    # Temps passé sur chaque exercice (écart avec la réussite précédente, dans la même séance)
    durations = {}
    for uid, rows in by_user.items():
        for (_, before), (ex_id, at) in zip(rows, rows[1:]):
            if 0 <= at - before <= SESSION_GAP_S:
                durations.setdefault(ex_id, []).append((uid, at - before, at))
    medians = {ex: _median([d for _, d, _ in v]) for ex, v in durations.items() if len(v) >= 3}

    rapid = []
    for ex_id, rows in durations.items():
        med = medians.get(ex_id)
        if not med or med < RAPID_MEDIAN_MIN_S:
            continue
        for uid, d, at in rows:
            if d < max(RAPID_MIN_S, RAPID_RATIO * med):
                rapid.append({"user": names[uid], "user_id": uid, "exercise": ex_id, "title": step_of[ex_id][1]["title"],
                              "seconds": round(d), "median": round(med), "at": at})

    # Rafales : au moins BURST_COUNT réussites en BURST_WINDOW_S ; des rafales qui se chevauchent sont fusionnées
    bursts = []
    for uid, rows in by_user.items():
        i, current = 0, None
        for j in range(len(rows)):
            while rows[j][1] - rows[i][1] > BURST_WINDOW_S:
                i += 1
            if j - i + 1 < BURST_COUNT:
                continue
            if current and rows[i][1] <= current["end"]:
                current["exercises"] += [e for e, _ in rows[len(current["exercises"]) + current["first"]:j + 1]]
                current["end"] = rows[j][1]
            else:
                current = {"user": names[uid], "user_id": uid, "first": i,
                           "exercises": [e for e, _ in rows[i:j + 1]], "start": rows[i][1], "end": rows[j][1]}
                bursts.append(current)
    for b in bursts:
        del b["first"]
        b["count"] = len(b["exercises"])

    ref = normalize(reference)
    pastes = []
    shared = {}
    for uid, kind, text, at in logs:
        if uid not in names:
            continue
        if kind == "collage" and len(text) >= PASTE_REPORT_MIN:
            after = [e for e, t in by_user.get(uid, []) if 0 <= t - at <= 180]
            pastes.append({"user": names[uid], "user_id": uid, "text": text, "at": at, "then": after})
        cmd = normalize(text)
        if len(cmd) >= SHARED_MIN_LEN and cmd not in ref:
            shared.setdefault(cmd, set()).add(uid)

    pairs = {}
    for cmd, users in shared.items():
        if not 2 <= len(users) <= 3:  # partagé par tout le monde = consigne ; par 2 ou 3 = à regarder
            continue
        users = sorted(users)
        for a in range(len(users)):
            for b in range(a + 1, len(users)):
                pairs.setdefault((users[a], users[b]), []).append(cmd)
    similar = sorted(({"users": (names[a], names[b]), "count": len(cmds), "examples": cmds[:3]}
                      for (a, b), cmds in pairs.items() if len(cmds) >= 2), key=lambda p: -p["count"])

    return {"rapid": sorted(rapid, key=lambda r: r["at"], reverse=True), "bursts": bursts,
            "pastes": sorted(pastes, key=lambda p: p["at"], reverse=True)[:200], "similar": similar}
