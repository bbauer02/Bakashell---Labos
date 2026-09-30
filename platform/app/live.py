"""Suivi en temps réel pour le tableau de bord enseignant.

- présence : dernière activité, terminaux ouverts et étape en cours, par (étudiant, parcours) ;
- blocages : nombre de vérifications d'une étape sans aucun nouveau succès (repère les élèves bloqués) ;
- diffusion : les événements sont poussés aux tableaux de bord ouverts (Server-Sent Events).

Tout est en mémoire : l'état repart de zéro au redémarrage de la plateforme (la progression,
elle, est en base).
"""
import asyncio
import json
import threading
import time

PRESENCE_THROTTLE = 20  # secondes minimum entre deux annonces d'activité d'un même étudiant

_loop = None
_subscribers: set = set()
_guard = threading.Lock()

presence: dict = {}   # (user_id, parcours) -> {"step", "last", "terminals"}
names: dict = {}      # user_id -> "Prénom Nom"
stalls: dict = {}     # (user_id, parcours, étape) -> vérifications consécutives sans nouveau succès
_last_announce: dict = {}


def attach_loop(loop):
    global _loop
    _loop = loop


def publish(event: dict):
    """Diffuse un événement ; utilisable depuis la boucle asyncio ou depuis un thread."""
    if _loop is None:
        return
    event.setdefault("at", time.time())
    for q in list(_subscribers):
        _loop.call_soon_threadsafe(_offer, q, event)


def _offer(q, event):
    if not q.full():
        q.put_nowait(event)


def remember_name(user: dict):
    if user and user.get("first_name") is not None:
        names[user["user_id"]] = f"{user['first_name']} {user['last_name']}"


def touch(user_id: int, course_key: str, step: int = None, force: bool = False):
    """Enregistre une activité. N'annonce aux tableaux de bord qu'un changement d'étape,
    un événement forcé, ou au plus une activité toutes les PRESENCE_THROTTLE secondes."""
    now = time.time()
    key = (user_id, course_key)
    with _guard:
        entry = presence.setdefault(key, {"step": None, "last": 0, "terminals": 0})
        changed = step is not None and step != entry["step"]
        entry["last"] = now
        if step is not None:
            entry["step"] = step
        announce = force or changed or now - _last_announce.get(key, 0) > PRESENCE_THROTTLE
        if announce:
            _last_announce[key] = now
            snapshot = dict(entry)
    if announce:
        publish({"type": "presence", "user_id": user_id, "name": names.get(user_id), "course": course_key, **snapshot})


def terminal_opened(user_id: int, course_key: str):
    with _guard:
        presence.setdefault((user_id, course_key), {"step": None, "last": 0, "terminals": 0})["terminals"] += 1
    touch(user_id, course_key, force=True)


def terminal_closed(user_id: int, course_key: str):
    with _guard:
        entry = presence.get((user_id, course_key))
        if entry:
            entry["terminals"] = max(0, entry["terminals"] - 1)
    touch(user_id, course_key, force=True)


def stalled(user_id: int, course_key: str, step: int) -> int:
    """Une vérification manuelle de l'étape n'a rien validé de nouveau."""
    key = (user_id, course_key, step)
    with _guard:
        stalls[key] = stalls.get(key, 0) + 1
        return stalls[key]


def progressed(user_id: int, course_key: str, step: int):
    with _guard:
        stalls.pop((user_id, course_key, step), None)


def snapshot(allowed=None) -> dict:
    """État courant ; allowed(user_id) -> bool limite aux étudiants visibles par l'enseignant connecté."""
    with _guard:
        entries = [{"user_id": uid, "name": names.get(uid), "course": course, **dict(e)}
                   for (uid, course), e in presence.items()]
        stuck = [{"user_id": uid, "course": course, "step": step, "count": n}
                 for (uid, course, step), n in stalls.items()]
    if allowed is not None:
        entries = [e for e in entries if allowed(e["user_id"])]
        stuck = [a for a in stuck if allowed(a["user_id"])]
    return {"type": "snapshot", "now": time.time(), "entries": entries, "attempts": stuck}


def sse(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


async def stream(is_disconnected, allowed=None):
    """Générateur SSE pour un tableau de bord : état initial, puis événements au fil de l'eau.
    allowed(user_id) -> bool : filtre propre à chaque connexion (un enseignant ne reçoit que ses étudiants) ;
    None : tout est transmis (administrateur)."""
    q = asyncio.Queue(maxsize=500)
    _subscribers.add(q)
    try:
        yield sse(snapshot(allowed))
        while True:
            if await is_disconnected():
                break
            try:
                event = await asyncio.wait_for(q.get(), timeout=15)
                if allowed is None or allowed(event.get("user_id")):
                    yield sse(event)
            except asyncio.TimeoutError:
                yield f"event: ping\ndata: {json.dumps({'now': time.time()})}\n\n"
    finally:
        _subscribers.discard(q)
