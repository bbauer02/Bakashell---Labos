"""Limitation des tentatives (connexion, inscription, réinitialisation) contre le forçage de mots de passe.

Fenêtre glissante en mémoire, par clé (adresse IP ou compte visé) : suffisant pour une plateforme
à un seul processus ; l'état repart de zéro au redémarrage.
"""
import threading
import time

_hits: dict = {}
_guard = threading.Lock()
MAX_KEY = 300  # une clé (email saisi…) plus longue est tronquée : la mémoire utilisée reste bornée


class Limit:
    def __init__(self, name: str, max_hits: int, window: int):
        self.name, self.max_hits, self.window = name, max_hits, window

    def _recent(self, key: str, now: float) -> list:
        """Tentatives encore dans la fenêtre ; une clé sans tentative récente est oubliée."""
        k = (self.name, key[:MAX_KEY])
        hits = [t for t in _hits.get(k, []) if now - t < self.window]
        if hits:
            _hits[k] = hits
        else:
            _hits.pop(k, None)
        return hits

    def blocked(self, *keys) -> int:
        """0 si autorisé, sinon le nombre de secondes à attendre (la plus longue des clés bloquées)."""
        now = time.time()
        wait = 0
        with _guard:
            for key in keys:
                hits = self._recent(key, now)
                if len(hits) >= self.max_hits:
                    wait = max(wait, int(self.window - (now - hits[0])) + 1)
        return wait

    def hit(self, *keys):
        now = time.time()
        with _guard:
            for key in keys:
                hits = self._recent(key, now)
                hits.append(now)
                _hits[(self.name, key[:MAX_KEY])] = hits
            if len(_hits) > 50000:  # garde-fou : purge des clés expirées
                for k in [k for k, v in _hits.items() if v and now - v[-1] >= 3600]:
                    _hits.pop(k, None)

    def clear(self, *keys):
        with _guard:
            for key in keys:
                _hits.pop((self.name, key[:MAX_KEY]), None)


# Échecs de connexion sur 15 min. Une salle entière partage souvent la même IP (NAT) : la limite par IP est
# large et remise à zéro par une connexion réussie. Le couple compte + IP bloque le forçage d'un mot de passe ;
# la limite par compte seul, plus haute, freine un forçage réparti sur plusieurs IP sans permettre à un
# camarade de bloquer un compte en quelques essais.
LOGIN_IP = Limit("login-ip", 100, 15 * 60)
LOGIN_PAIR = Limit("login-pair", 10, 15 * 60)
LOGIN_ACCOUNT = Limit("login-account", 50, 15 * 60)
# Inscriptions par heure et par adresse IP : plusieurs classes derrière un même NAT doivent pouvoir s'inscrire
REGISTER = Limit("register", 200, 3600)
# Changement de mot de passe (ancien mot de passe erroné) et liens de réinitialisation
PASSWORD = Limit("password", 10, 15 * 60)


def login_keys(ip: str, email: str) -> list:
    return [(LOGIN_IP, f"ip:{ip}"), (LOGIN_PAIR, f"pair:{email}|{ip}"), (LOGIN_ACCOUNT, f"email:{email}")]


def login_blocked(ip: str, email: str) -> int:
    return max(limit.blocked(key) for limit, key in login_keys(ip, email))


def login_failed(ip: str, email: str):
    for limit, key in login_keys(ip, email):
        limit.hit(key)


def login_succeeded(ip: str, email: str):
    for limit, key in login_keys(ip, email):
        limit.clear(key)


def reset_all():
    """Pour les tests."""
    with _guard:
        _hits.clear()


def wait_message(seconds: int) -> str:
    minutes = max(1, round(seconds / 60))
    return f"Trop de tentatives : réessayez dans {minutes} minute{'s' if minutes > 1 else ''}."
