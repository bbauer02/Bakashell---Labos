"""Terminaux des étudiants vus par l'enseignant, en lecture seule.

Chaque terminal ouvert recopie sa sortie ici : un tampon des derniers octets (pour afficher l'écran
en cours à l'arrivée de l'enseignant), sa taille (colonnes, lignes : l'enseignant affiche le terminal
à la même taille que l'étudiant) et les files des enseignants qui regardent. Rien n'est écrit sur
disque ; aucune saisie de l'enseignant n'est transmise au conteneur.
"""
import asyncio
import itertools
from collections import deque

BUFFER_BYTES = 64 * 1024

_ids = itertools.count(1)
_terminals: dict = {}   # (user_id, parcours) -> {id_terminal: _Term}
_watchers: dict = {}    # (user_id, parcours) -> set de asyncio.Queue


class _Term:
    __slots__ = ("buf", "size", "dims", "label")

    def __init__(self, label: str = ""):
        self.buf = deque()
        self.size = 0        # octets dans le tampon (tenu à jour, pas recalculé à chaque paquet)
        self.dims = None     # (colonnes, lignes) du terminal de l'étudiant
        self.label = label   # machine du terminal (parcours Réseau : « console », « caisse »…), sinon vide


def opened(key, label: str = "") -> int:
    term_id = next(_ids)
    _terminals.setdefault(key, {})[term_id] = _Term(label)
    _broadcast(key, ("open", term_id, label))
    return term_id


def closed(key, term_id: int):
    terms = _terminals.get(key, {})
    terms.pop(term_id, None)
    if not terms:
        _terminals.pop(key, None)
    _broadcast(key, ("close", term_id, b""))


def feed(key, term_id: int, data: bytes):
    term = _terminals.get(key, {}).get(term_id)
    if term is None:
        return
    term.buf.append(data)
    term.size += len(data)
    while term.size > BUFFER_BYTES and len(term.buf) > 1:
        term.size -= len(term.buf.popleft())
    _broadcast(key, ("data", term_id, data))


def resized(key, term_id: int, cols: int, rows: int):
    """L'étudiant a redimensionné son terminal : les enseignants qui regardent s'y adaptent."""
    term = _terminals.get(key, {}).get(term_id)
    if term is None:
        return
    term.dims = (cols, rows)
    _broadcast(key, ("size", term_id, term.dims))


def is_open(key) -> bool:
    return bool(_terminals.get(key))


def open_keys() -> set:
    return {k for k, v in _terminals.items() if v}


def _broadcast(key, event):
    for q in list(_watchers.get(key, ())):
        if q.qsize() < 2000:
            q.put_nowait(event)


def subscribe(key) -> asyncio.Queue:
    """Abonne un enseignant ; la file reçoit d'abord, pour chaque terminal ouvert, sa taille et son écran récent."""
    q = asyncio.Queue()
    for term_id, term in _terminals.get(key, {}).items():
        q.put_nowait(("open", term_id, term.label))
        if term.dims:
            q.put_nowait(("size", term_id, term.dims))
        if term.buf:
            q.put_nowait(("data", term_id, b"".join(term.buf)))
    _watchers.setdefault(key, set()).add(q)
    return q


def unsubscribe(key, q):
    watchers = _watchers.get(key)
    if watchers:
        watchers.discard(q)
        if not watchers:
            _watchers.pop(key, None)
