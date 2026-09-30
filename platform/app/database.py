"""SQLite : comptes, sessions, progression, indices et données de mise en place."""
import datetime
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import statistics

DB_PATH = os.environ.get("DB_PATH", "/data/platform.db")
SESSION_HOURS = int(os.environ.get("SESSION_HOURS", "24"))


def get_db():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    return db


# Filtre d'identifiants d'un parcours -> sa clé (les points de QCM s'ajoutent au score du parcours)
_COURSE_OF_GLOB: dict = {}


def init_db(courses):
    """Crée ou met à jour le schéma, puis applique les changements de version des parcours.
    Retourne la liste des parcours dont la progression a été archivée."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS progress (
            user_id INTEGER NOT NULL,
            exercise_id TEXT NOT NULL,
            points INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, exercise_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS progress_archive (
            user_id INTEGER NOT NULL,
            exercise_id TEXT NOT NULL,
            points INTEGER NOT NULL,
            completed_at TIMESTAMP,
            exercises_version TEXT,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            container_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS hints_used (
            user_id INTEGER NOT NULL,
            exercise_id TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, exercise_id)
        );
        CREATE TABLE IF NOT EXISTS step_setup (
            user_id INTEGER NOT NULL,
            course TEXT NOT NULL DEFAULT 'linux',
            step INTEGER NOT NULL,
            data TEXT NOT NULL,
            PRIMARY KEY (user_id, course, step)
        );
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS class_members (
            class_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (class_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS class_courses (
            class_id INTEGER NOT NULL,
            course_key TEXT NOT NULL,
            PRIMARY KEY (class_id, course_key)
        );
        -- Vérifications lancées par l'étudiant (clic), réussies ou non : historique et statistiques
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise_id TEXT NOT NULL,
            passed INTEGER NOT NULL,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS attempts_user ON attempts (user_id, exercise_id);
        CREATE INDEX IF NOT EXISTS attempts_exercise ON attempts (exercise_id);
        -- Échéances : étape d'un parcours à terminer pour une date, par classe
        CREATE TABLE IF NOT EXISTS deadlines (
            class_id INTEGER NOT NULL,
            course_key TEXT NOT NULL,
            step INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            PRIMARY KEY (class_id, course_key, step)
        );
        -- Liens de réinitialisation de mot de passe (seule l'empreinte du jeton est stockée)
        CREATE TABLE IF NOT EXISTS password_resets (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        -- Saisie dans le terminal web (suivi d'intégrité : collages, commandes partagées), purgée après quelques mois
        CREATE TABLE IF NOT EXISTS terminal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course TEXT NOT NULL,
            step INTEGER,
            kind TEXT NOT NULL,
            text TEXT NOT NULL,
            at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS terminal_log_course ON terminal_log (course, at);
        -- QCM de fin de cours : une seule tentative par étape
        CREATE TABLE IF NOT EXISTS quiz_results (
            user_id INTEGER NOT NULL,
            course TEXT NOT NULL,
            step INTEGER NOT NULL,
            score INTEGER NOT NULL,
            max_score INTEGER NOT NULL,
            details TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, course, step)
        );
        -- Attestations de fin de parcours, vérifiables par leur code
        CREATE TABLE IF NOT EXISTS certificates (
            code TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            course_key TEXT NOT NULL,
            course_title TEXT NOT NULL,
            score INTEGER NOT NULL,
            max_score INTEGER NOT NULL,
            exercises INTEGER NOT NULL,
            total_exercises INTEGER NOT NULL,
            issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, course_key)
        );
    """)
    cols = [r["name"] for r in db.execute("PRAGMA table_info(users)").fetchall()]
    if "last_seen" not in cols:
        db.execute("ALTER TABLE users ADD COLUMN last_seen TIMESTAMP")
    # Ancienne table step_setup (un seul parcours) : on la convertit en conservant ses données
    cols = [r["name"] for r in db.execute("PRAGMA table_info(step_setup)").fetchall()]
    if "course" not in cols:
        db.executescript("""
            ALTER TABLE step_setup RENAME TO step_setup_old;
            CREATE TABLE step_setup (
                user_id INTEGER NOT NULL,
                course TEXT NOT NULL DEFAULT 'linux',
                step INTEGER NOT NULL,
                data TEXT NOT NULL,
                PRIMARY KEY (user_id, course, step)
            );
            INSERT INTO step_setup (user_id, course, step, data) SELECT user_id, 'linux', step, data FROM step_setup_old;
            DROP TABLE step_setup_old;
        """)
    db.execute(f"DELETE FROM sessions WHERE created_at < datetime('now', '-{SESSION_HOURS} hours')")
    # Les jetons de session sont stockés hachés : les sessions de l'ancien format (jeton en clair) sont fermées
    if not db.execute("SELECT 1 FROM meta WHERE key = 'sessions_hashed'").fetchone():
        db.execute("DELETE FROM sessions")
        db.execute("INSERT INTO meta (key, value) VALUES ('sessions_hashed', '1')")
    db.commit()
    db.close()

    _COURSE_OF_GLOB.update({c["id_glob"]: c["key"] for c in courses})
    migrated = [c["key"] for c in courses if _migrate_course(c)]
    _migrate_to_classes()
    _ensure_admin()
    return migrated


def _migrate_to_classes():
    """Passage à l'accès par classes : les étudiants déjà inscrits sont regroupés dans une classe
    « Promotion actuelle », avec accès aux parcours sur lesquels ils ont déjà progressé (Linux au minimum),
    pour que personne ne perde l'accès à son travail."""
    db = get_db()
    if db.execute("SELECT 1 FROM meta WHERE key = 'classes_migrated'").fetchone():
        db.close()
        return
    students = [r["id"] for r in db.execute("SELECT id FROM users WHERE is_admin = 0").fetchall()]
    if students:
        cur = db.execute("INSERT INTO classes (name, code) VALUES (?, ?)", ("Promotion actuelle", _new_code(db)))
        class_id = cur.lastrowid
        db.executemany("INSERT INTO class_members (class_id, user_id) VALUES (?, ?)", [(class_id, u) for u in students])
        courses = {"linux"}
        for glob, key in (("J*", "jest"), ("D*", "docker")):
            if db.execute("SELECT 1 FROM progress WHERE exercise_id GLOB ? LIMIT 1", (glob,)).fetchone():
                courses.add(key)
        db.executemany("INSERT INTO class_courses (class_id, course_key) VALUES (?, ?)", [(class_id, k) for k in courses])
    db.execute("INSERT INTO meta (key, value) VALUES ('classes_migrated', '1')")
    db.commit()
    db.close()


def _migrate_course(course: dict) -> bool:
    """Si le catalogue d'un parcours a changé, sa progression est archivée (pas supprimée)."""
    db = get_db()
    row = db.execute("SELECT value FROM meta WHERE key = ?", (course["meta_key"],)).fetchone()
    current = row["value"] if row else None
    if current == course["version"]:
        db.close()
        return False
    has_progress = db.execute(
        "SELECT COUNT(*) AS n FROM progress WHERE exercise_id GLOB ?", (course["id_glob"],)
    ).fetchone()["n"] > 0
    if has_progress:
        db.execute(
            "INSERT INTO progress_archive (user_id, exercise_id, points, completed_at, exercises_version) "
            "SELECT user_id, exercise_id, points, completed_at, ? FROM progress WHERE exercise_id GLOB ?",
            (f"{course['key']}:{current or '1'}", course["id_glob"]),
        )
        db.execute("DELETE FROM progress WHERE exercise_id GLOB ?", (course["id_glob"],))
    db.execute("DELETE FROM hints_used WHERE exercise_id GLOB ?", (course["id_glob"],))
    db.execute("DELETE FROM attempts WHERE exercise_id GLOB ?", (course["id_glob"],))
    db.execute("DELETE FROM step_setup WHERE course = ?", (course["key"],))
    db.execute("DELETE FROM quiz_results WHERE course = ?", (course["key"],))
    db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (course["meta_key"], course["version"]))
    db.commit()
    db.close()
    return has_progress


# ─── Administrateur ────────────────────────────────────────────────────

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@lab.local").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ADMIN_FIRST = os.environ.get("ADMIN_FIRST", "Admin")
ADMIN_LAST = os.environ.get("ADMIN_LAST", "Lab")


def _ensure_admin():
    """Crée le compte admin s'il manque. Si ADMIN_PASSWORD est défini, il est
    (ré)appliqué à chaque démarrage ; sinon un mot de passe aléatoire est
    généré à la création et affiché une seule fois dans les logs."""
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)).fetchone()
    if not row:
        password = ADMIN_PASSWORD or secrets.token_urlsafe(12)
        db.execute(
            "INSERT INTO users (first_name, last_name, email, password_hash, is_admin) VALUES (?, ?, ?, ?, 1)",
            (ADMIN_FIRST, ADMIN_LAST, ADMIN_EMAIL, hash_password(password)),
        )
        if not ADMIN_PASSWORD:
            print(f"[linux-lab] Compte admin créé : {ADMIN_EMAIL} / {password} (définissez ADMIN_PASSWORD pour le fixer)", flush=True)
    else:
        db.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (row["id"],))
        if ADMIN_PASSWORD:
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(ADMIN_PASSWORD), row["id"]))
    db.commit()
    db.close()


# ─── Mots de passe ─────────────────────────────────────────────────────

_SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${h.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith("scrypt$"):
        _, salt, h = password_hash.split("$")
        computed = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), **_SCRYPT).hex()
        return hmac.compare_digest(computed, h)
    # Ancien format (sha256 salé), converti à la prochaine connexion réussie
    salt, h = password_hash.split(":")
    return hmac.compare_digest(hashlib.sha256((salt + password).encode()).hexdigest(), h)


def create_user(first_name: str, last_name: str, email: str, password: str) -> int:
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO users (first_name, last_name, email, password_hash) VALUES (?, ?, ?, ?)",
            (first_name.strip(), last_name.strip(), email.strip().lower(), hash_password(password)),
        )
        db.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        db.close()


# Empreinte factice : un email inconnu coûte le même calcul qu'un email existant (pas d'énumération des comptes
# par le temps de réponse)
_DUMMY_HASH = None


def authenticate(email: str, password: str):
    global _DUMMY_HASH
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    if not row:
        db.close()
        _DUMMY_HASH = _DUMMY_HASH or hash_password(secrets.token_hex(8))
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, row["password_hash"]):
        db.close()
        return None
    if not row["password_hash"].startswith("scrypt$"):
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), row["id"]))
        db.commit()
    db.close()
    return dict(row)


def get_user(user_id: int):
    db = get_db()
    row = db.execute("SELECT id, first_name, last_name, email, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def set_password(user_id: int, password: str, keep_session: str = None):
    """Change le mot de passe et ferme toutes les sessions (sauf keep_session : celle qui fait le changement)."""
    db = get_db()
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), user_id))
    keep = _token_hash(keep_session) if keep_session else ""
    db.execute("DELETE FROM sessions WHERE user_id = ? AND token != ?", (user_id, keep))
    db.execute("DELETE FROM password_resets WHERE user_id = ?", (user_id,))
    db.commit()
    db.close()


def check_password(user_id: int, password: str) -> bool:
    db = get_db()
    row = db.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return bool(row) and verify_password(password, row["password_hash"])


# ─── Réinitialisation du mot de passe (lien généré par l'enseignant) ───

RESET_HOURS = 48


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_reset_token(user_id: int) -> str:
    """Nouveau lien de réinitialisation (les précédents sont annulés). Retourne le jeton en clair."""
    token = secrets.token_urlsafe(24)
    db = get_db()
    db.execute("DELETE FROM password_resets WHERE user_id = ?", (user_id,))
    db.execute("INSERT INTO password_resets (token_hash, user_id) VALUES (?, ?)", (_token_hash(token), user_id))
    db.commit()
    db.close()
    return token


def reset_token_user(token: str):
    """L'utilisateur associé à un jeton valide (non expiré), ou None."""
    if not token:
        return None
    db = get_db()
    row = db.execute(
        "SELECT u.id, u.first_name, u.last_name, u.email FROM password_resets r JOIN users u ON u.id = r.user_id "
        f"WHERE r.token_hash = ? AND r.created_at >= datetime('now', '-{RESET_HOURS} hours')",
        (_token_hash(token),),
    ).fetchone()
    db.close()
    return dict(row) if row else None


# ─── Sessions ──────────────────────────────────────────────────────────

# La base ne contient que l'empreinte SHA-256 des jetons de session : une copie de la base (sauvegarde)
# ne permet pas de se connecter à la place de quelqu'un.

def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db = get_db()
    db.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (_token_hash(token), user_id))
    db.commit()
    db.close()
    return token


def get_session(token: str):
    if not token:
        return None
    db = get_db()
    row = db.execute(
        "SELECT s.*, u.first_name, u.last_name, u.email, u.is_admin FROM sessions s "
        "JOIN users u ON s.user_id = u.id "
        f"WHERE s.token = ? AND s.created_at >= datetime('now', '-{SESSION_HOURS} hours')",
        (_token_hash(token),),
    ).fetchone()
    db.close()
    return dict(row) if row else None


def delete_session(token: str):
    db = get_db()
    db.execute("DELETE FROM sessions WHERE token = ?", (_token_hash(token),))
    db.commit()
    db.close()


def touch_user(user_id: int):
    db = get_db()
    db.execute("UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
    db.commit()
    db.close()


# ─── Progression ───────────────────────────────────────────────────────

def get_user_score(user_id: int, id_glob: str = "*"):
    """Score de l'étudiant, limité aux exercices dont l'identifiant correspond à id_glob."""
    db = get_db()
    rows = db.execute(
        "SELECT exercise_id, points FROM progress WHERE user_id = ? AND exercise_id GLOB ?", (user_id, id_glob)
    ).fetchall()
    course_key = _COURSE_OF_GLOB.get(id_glob)
    quiz = db.execute("SELECT COALESCE(SUM(score), 0) FROM quiz_results WHERE user_id = ? AND course = ?",
                      (user_id, course_key)).fetchone()[0] if course_key else 0
    db.close()
    return {
        "score": sum(r["points"] for r in rows) + quiz,
        "quiz": quiz,
        "completed": [r["exercise_id"] for r in rows],
        "earned": {r["exercise_id"]: r["points"] for r in rows},
    }


def add_exercise_completion(user_id: int, exercise_id: str, points: int) -> bool:
    db = get_db()
    try:
        db.execute(
            "INSERT INTO progress (user_id, exercise_id, points) VALUES (?, ?, ?)",
            (user_id, exercise_id, points),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        db.close()


def reset_user_progress(user_id: int, course: dict = None):
    """Remet à zéro un parcours (ou tous si course est None)."""
    glob = course["id_glob"] if course else "*"
    db = get_db()
    db.execute("DELETE FROM progress WHERE user_id = ? AND exercise_id GLOB ?", (user_id, glob))
    db.execute("DELETE FROM hints_used WHERE user_id = ? AND exercise_id GLOB ?", (user_id, glob))
    db.execute("DELETE FROM attempts WHERE user_id = ? AND exercise_id GLOB ?", (user_id, glob))
    if course:
        db.execute("DELETE FROM step_setup WHERE user_id = ? AND course = ?", (user_id, course["key"]))
        db.execute("DELETE FROM quiz_results WHERE user_id = ? AND course = ?", (user_id, course["key"]))
    else:
        db.execute("DELETE FROM step_setup WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM quiz_results WHERE user_id = ?", (user_id,))
    db.commit()
    db.close()


# ─── Suivi d'intégrité ─────────────────────────────────────────────────

def log_terminal(user_id: int, course_key: str, step, kind: str, text: str):
    db = get_db()
    db.execute("INSERT INTO terminal_log (user_id, course, step, kind, text) VALUES (?, ?, ?, ?, ?)",
               (user_id, course_key, step, kind, text))
    db.commit()
    db.close()


def purge_terminal_log(days: int) -> int:
    db = get_db()
    cur = db.execute("DELETE FROM terminal_log WHERE at < datetime('now', ?)", (f"-{int(days)} days",))
    db.commit()
    db.close()
    return cur.rowcount


def integrity_data(course: dict, user_ids=None):
    """Noms des étudiants, réussites (user, exercice, secondes) et saisies (user, type, texte, secondes) d'un parcours."""
    db = get_db()
    students = {r["id"]: f"{r['first_name']} {r['last_name']}" for r in db.execute(
        "SELECT id, first_name, last_name FROM users WHERE is_admin = 0").fetchall()
        if user_ids is None or r["id"] in set(user_ids)}
    completions = [(r["user_id"], r["exercise_id"], _epoch(r["completed_at"])) for r in db.execute(
        "SELECT user_id, exercise_id, completed_at FROM progress WHERE exercise_id GLOB ?", (course["id_glob"],))
        if r["user_id"] in students]
    logs = [(r["user_id"], r["kind"], r["text"], _epoch(r["at"])) for r in db.execute(
        "SELECT user_id, kind, text, at FROM terminal_log WHERE course = ? ORDER BY at", (course["key"],))
        if r["user_id"] in students]
    db.close()
    return students, completions, logs


def _epoch(value) -> float:
    return datetime.datetime.fromisoformat(str(value)).replace(tzinfo=datetime.timezone.utc).timestamp()


# ─── QCM de fin de cours ───────────────────────────────────────────────

def get_quiz_result(user_id: int, course_key: str, step: int):
    db = get_db()
    row = db.execute("SELECT score, max_score, details FROM quiz_results WHERE user_id = ? AND course = ? AND step = ?",
                     (user_id, course_key, step)).fetchone()
    db.close()
    return {"score": row["score"], "max": row["max_score"], "details": json.loads(row["details"])} if row else None


def save_quiz_result(user_id: int, course_key: str, step: int, score: int, max_score: int, details: list) -> bool:
    """Enregistre la tentative ; False si l'étudiant avait déjà répondu (une seule tentative)."""
    db = get_db()
    cur = db.execute("INSERT OR IGNORE INTO quiz_results (user_id, course, step, score, max_score, details) "
                     "VALUES (?, ?, ?, ?, ?, ?)", (user_id, course_key, step, score, max_score, json.dumps(details)))
    db.commit()
    db.close()
    return cur.rowcount == 1


def quiz_scores(user_id: int, course_key: str) -> dict:
    """Étape -> (points, maximum) des QCM passés par l'étudiant sur ce parcours."""
    db = get_db()
    rows = db.execute("SELECT step, score, max_score FROM quiz_results WHERE user_id = ? AND course = ?",
                      (user_id, course_key)).fetchall()
    db.close()
    return {r["step"]: (r["score"], r["max_score"]) for r in rows}


# ─── Indices ───────────────────────────────────────────────────────────

def get_hints_used(user_id: int) -> dict:
    db = get_db()
    rows = db.execute("SELECT exercise_id, count FROM hints_used WHERE user_id = ?", (user_id,)).fetchall()
    db.close()
    return {r["exercise_id"]: r["count"] for r in rows}


def use_hint(user_id: int, exercise_id: str, max_hints: int) -> int:
    db = get_db()
    db.execute(
        "INSERT INTO hints_used (user_id, exercise_id, count) VALUES (?, ?, 1) "
        "ON CONFLICT(user_id, exercise_id) DO UPDATE SET count = MIN(count + 1, ?)",
        (user_id, exercise_id, max_hints),
    )
    db.commit()
    count = db.execute(
        "SELECT count FROM hints_used WHERE user_id = ? AND exercise_id = ?", (user_id, exercise_id)
    ).fetchone()["count"]
    db.close()
    return count


# ─── Données de mise en place (réponses attendues, jamais dans le conteneur) ──

def get_setup(user_id: int, course_key: str, step: int):
    db = get_db()
    row = db.execute(
        "SELECT data FROM step_setup WHERE user_id = ? AND course = ? AND step = ?", (user_id, course_key, step)
    ).fetchone()
    db.close()
    return json.loads(row["data"]) if row else None


def save_setup(user_id: int, course_key: str, step: int, data: dict):
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO step_setup (user_id, course, step, data) VALUES (?, ?, ?, ?)",
        (user_id, course_key, step, json.dumps(data)),
    )
    db.commit()
    db.close()


# ─── Tableau de bord ───────────────────────────────────────────────────

def get_all_students(course: dict, step_of: dict):
    """Pour le tableau de bord enseignant, sur un parcours — exclut les admins.
    step_of : identifiant d'exercice -> numéro d'étape (exercices du parcours)."""
    db = get_db()
    users = db.execute(
        "SELECT id, first_name, last_name, email, last_seen, created_at FROM users WHERE is_admin = 0"
    ).fetchall()
    rows = db.execute(
        "SELECT user_id, exercise_id, points FROM progress WHERE exercise_id GLOB ?", (course["id_glob"],)
    ).fetchall()
    quiz = dict(db.execute("SELECT user_id, SUM(score) FROM quiz_results WHERE course = ? GROUP BY user_id",
                           (course["key"],)).fetchall())
    db.close()
    students = {u["id"]: {**dict(u), "score": quiz.get(u["id"], 0), "quiz": quiz.get(u["id"], 0),
                          "exercises_done": 0, "per_step": {}} for u in users}
    for r in rows:
        s = students.get(r["user_id"])
        step = step_of.get(r["exercise_id"])
        if s is None or step is None:
            continue
        s["score"] += r["points"]
        s["exercises_done"] += 1
        s["per_step"][step] = s["per_step"].get(step, 0) + 1
    return sorted(students.values(), key=lambda s: -s["score"])


def delete_user(user_id: int):
    """Supprime un utilisateur (non admin) et toutes ses données."""
    db = get_db()
    row = db.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row or row["is_admin"]:
        db.close()
        return
    for table in ("progress", "sessions", "hints_used", "step_setup", "class_members", "attempts",
                  "password_resets", "certificates", "quiz_results", "terminal_log"):
        db.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ? AND is_admin = 0", (user_id,))
    db.commit()
    db.close()


# ─── Classes et accès aux parcours ─────────────────────────────────────

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans 0/O ni 1/I : codes faciles à recopier


def _new_code(db) -> str:
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        code = f"{code[:3]}-{code[3:]}"
        if not db.execute("SELECT 1 FROM classes WHERE code = ?", (code,)).fetchone():
            return code


def create_class(name: str):
    db = get_db()
    try:
        cur = db.execute("INSERT INTO classes (name, code) VALUES (?, ?)", (name.strip(), _new_code(db)))
        db.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        db.close()


def rename_class(class_id: int, name: str) -> bool:
    db = get_db()
    try:
        db.execute("UPDATE classes SET name = ? WHERE id = ?", (name.strip(), class_id))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        db.close()


def regenerate_code(class_id: int):
    db = get_db()
    db.execute("UPDATE classes SET code = ? WHERE id = ?", (_new_code(db), class_id))
    db.commit()
    db.close()


def delete_class(class_id: int):
    """Supprime la classe (les comptes et leur progression sont conservés)."""
    db = get_db()
    db.execute("DELETE FROM class_members WHERE class_id = ?", (class_id,))
    db.execute("DELETE FROM class_courses WHERE class_id = ?", (class_id,))
    db.execute("DELETE FROM deadlines WHERE class_id = ?", (class_id,))
    db.execute("DELETE FROM classes WHERE id = ?", (class_id,))
    db.commit()
    db.close()


def set_class_courses(class_id: int, course_keys):
    db = get_db()
    db.execute("DELETE FROM class_courses WHERE class_id = ?", (class_id,))
    db.executemany("INSERT INTO class_courses (class_id, course_key) VALUES (?, ?)", [(class_id, k) for k in course_keys])
    db.commit()
    db.close()


def add_members(class_id: int, user_ids):
    db = get_db()
    db.executemany("INSERT OR IGNORE INTO class_members (class_id, user_id) VALUES (?, ?)",
                   [(class_id, int(u)) for u in user_ids])
    db.commit()
    db.close()


def remove_member(class_id: int, user_id: int):
    db = get_db()
    db.execute("DELETE FROM class_members WHERE class_id = ? AND user_id = ?", (class_id, user_id))
    db.commit()
    db.close()


def join_class_by_code(user_id: int, code: str):
    """Inscrit l'étudiant dans la classe correspondant au code. Retourne le nom de la classe, ou None."""
    code = code.strip().upper().replace(" ", "").replace("-", "")
    code = f"{code[:3]}-{code[3:]}"
    db = get_db()
    row = db.execute("SELECT id, name FROM classes WHERE code = ?", (code,)).fetchone()
    if row:
        db.execute("INSERT OR IGNORE INTO class_members (class_id, user_id) VALUES (?, ?)", (row["id"], user_id))
        db.commit()
    db.close()
    return row["name"] if row else None


def class_exists(class_id: int) -> bool:
    db = get_db()
    row = db.execute("SELECT 1 FROM classes WHERE id = ?", (class_id,)).fetchone()
    db.close()
    return row is not None


def class_exists_for_code(code: str) -> bool:
    code = code.strip().upper().replace(" ", "").replace("-", "")
    db = get_db()
    row = db.execute("SELECT 1 FROM classes WHERE code = ?", (f"{code[:3]}-{code[3:]}",)).fetchone()
    db.close()
    return row is not None


def get_user_classes(user_id: int):
    db = get_db()
    rows = db.execute(
        "SELECT c.id, c.name FROM classes c JOIN class_members m ON m.class_id = c.id WHERE m.user_id = ? ORDER BY c.name",
        (user_id,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_user_courses(user_id: int) -> set:
    """Parcours accessibles à un étudiant : union des parcours de ses classes."""
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT cc.course_key FROM class_courses cc JOIN class_members m ON m.class_id = cc.class_id "
        "WHERE m.user_id = ?",
        (user_id,),
    ).fetchall()
    db.close()
    return {r["course_key"] for r in rows}


def list_classes():
    db = get_db()
    classes = [dict(r) for r in db.execute("SELECT id, name, code, created_at FROM classes ORDER BY name").fetchall()]
    for c in classes:
        c["courses"] = [r["course_key"] for r in db.execute(
            "SELECT course_key FROM class_courses WHERE class_id = ?", (c["id"],)).fetchall()]
        c["members"] = [dict(r) for r in db.execute(
            "SELECT u.id, u.first_name, u.last_name, u.email FROM users u JOIN class_members m ON m.user_id = u.id "
            "WHERE m.class_id = ? ORDER BY u.last_name, u.first_name", (c["id"],)).fetchall()]
    db.close()
    return classes


def list_students():
    db = get_db()
    rows = db.execute(
        "SELECT u.id, u.first_name, u.last_name, u.email, "
        "(SELECT COUNT(*) FROM class_members m WHERE m.user_id = u.id) AS nb_classes "
        "FROM users u WHERE u.is_admin = 0 ORDER BY u.last_name, u.first_name"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def class_member_ids(class_id: int) -> set:
    db = get_db()
    rows = db.execute("SELECT user_id FROM class_members WHERE class_id = ?", (class_id,)).fetchall()
    db.close()
    return {r["user_id"] for r in rows}



# ─── Historique des vérifications ──────────────────────────────────────

def record_attempt(user_id: int, exercise_id: str, passed: bool, message: str = None):
    db = get_db()
    db.execute("INSERT INTO attempts (user_id, exercise_id, passed, message) VALUES (?, ?, ?, ?)",
               (user_id, exercise_id, int(passed), message))
    db.commit()
    db.close()


def get_attempts(user_id: int, exercise_ids, limit: int = 10) -> dict:
    """Dernières vérifications de l'étudiant, par exercice (les plus récentes d'abord)."""
    ids = list(exercise_ids)
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    db = get_db()
    rows = db.execute(
        f"SELECT exercise_id, passed, message, created_at FROM attempts WHERE user_id = ? "
        f"AND exercise_id IN ({marks}) ORDER BY id DESC",
        (user_id, *ids),
    ).fetchall()
    db.close()
    out = {}
    for r in rows:
        entry = out.setdefault(r["exercise_id"], {"count": 0, "items": []})
        entry["count"] += 1
        if len(entry["items"]) < limit:
            entry["items"].append({"passed": bool(r["passed"]), "message": r["message"], "at": r["created_at"]})
    return out


# ─── Statistiques par exercice (enseignant) ───────────────────────────

def exercise_stats(course: dict, user_ids=None) -> dict:
    """Par exercice : étudiants qui l'ont tenté, réussi, vérifications en échec, indices, erreur la plus fréquente.
    user_ids : limite aux étudiants donnés (une classe) ; les comptes admin sont toujours exclus."""
    glob = course["id_glob"]
    db = get_db()
    students = {r["id"] for r in db.execute("SELECT id FROM users WHERE is_admin = 0").fetchall()}
    if user_ids is not None:
        students &= set(user_ids)
    done = db.execute("SELECT user_id, exercise_id FROM progress WHERE exercise_id GLOB ?", (glob,)).fetchall()
    attempts = db.execute("SELECT user_id, exercise_id, passed, message FROM attempts WHERE exercise_id GLOB ?",
                          (glob,)).fetchall()
    hints = db.execute("SELECT user_id, exercise_id, count FROM hints_used WHERE exercise_id GLOB ?", (glob,)).fetchall()
    db.close()
    stats = {}

    def entry(ex_id):
        return stats.setdefault(ex_id, {"tried": set(), "passed": set(), "fails": 0, "hints": 0, "messages": {}})

    for r in done:
        if r["user_id"] in students:
            e = entry(r["exercise_id"])
            e["tried"].add(r["user_id"])
            e["passed"].add(r["user_id"])
    for r in attempts:
        if r["user_id"] not in students:
            continue
        e = entry(r["exercise_id"])
        e["tried"].add(r["user_id"])
        if not r["passed"]:
            e["fails"] += 1
            if r["message"]:
                # Le détail (valeurs propres à l'étudiant) suit le message du catalogue : on regroupe sans lui
                msg = r["message"].split("<br><span class='fail-detail'>")[0]
                e["messages"][msg] = e["messages"].get(msg, 0) + 1
    for r in hints:
        if r["user_id"] in students:
            entry(r["exercise_id"])["hints"] += r["count"]
    minutes = _minutes_per_exercise(glob, students)
    result = {}
    for ex_id, e in stats.items():
        top = max(e["messages"].items(), key=lambda kv: kv[1]) if e["messages"] else None
        result[ex_id] = {"tried": len(e["tried"]), "passed": len(e["passed"]), "fails": e["fails"],
                         "hints": e["hints"], "top_message": top[0] if top else None,
                         "top_count": top[1] if top else 0, "minutes": minutes.get(ex_id)}
    return {"students": len(students), "exercises": result}


def _minutes_per_exercise(glob: str, students: set) -> dict:
    """Temps médian (minutes) passé sur chaque exercice : écart entre deux réussites successives d'un même
    étudiant, dans la même séance (écarts de plus d'une heure ignorés : pause, autre jour)."""
    db = get_db()
    rows = db.execute("SELECT user_id, exercise_id, completed_at FROM progress WHERE exercise_id GLOB ? "
                      "ORDER BY user_id, completed_at", (glob,)).fetchall()
    db.close()
    gaps, previous = {}, {}
    for r in rows:
        if r["user_id"] not in students:
            continue
        at = datetime.datetime.fromisoformat(str(r["completed_at"]))
        before = previous.get(r["user_id"])
        if before is not None and 0 <= (at - before).total_seconds() <= 3600:
            gaps.setdefault(r["exercise_id"], []).append((at - before).total_seconds() / 60)
        previous[r["user_id"]] = at
    return {ex: round(statistics.median(g), 1) for ex, g in gaps.items()}


# ─── Export des notes ─────────────────────────────────────────────────

def hints_per_user(glob: str) -> dict:
    db = get_db()
    rows = db.execute("SELECT user_id, SUM(count) AS n FROM hints_used WHERE exercise_id GLOB ? GROUP BY user_id",
                      (glob,)).fetchall()
    db.close()
    return {r["user_id"]: r["n"] for r in rows}


def last_completion_per_user(glob: str) -> dict:
    db = get_db()
    rows = db.execute("SELECT user_id, MAX(completed_at) AS t FROM progress WHERE exercise_id GLOB ? GROUP BY user_id",
                      (glob,)).fetchall()
    db.close()
    return {r["user_id"]: r["t"] for r in rows}


def class_names_per_user() -> dict:
    db = get_db()
    rows = db.execute("SELECT m.user_id, c.name FROM class_members m JOIN classes c ON c.id = m.class_id "
                      "ORDER BY c.name").fetchall()
    db.close()
    out = {}
    for r in rows:
        out.setdefault(r["user_id"], []).append(r["name"])
    return out


# ─── Échéances ────────────────────────────────────────────────────────

def set_deadline(class_id: int, course_key: str, step: int, due_date: str):
    db = get_db()
    db.execute("INSERT OR REPLACE INTO deadlines (class_id, course_key, step, due_date) VALUES (?, ?, ?, ?)",
               (class_id, course_key, step, due_date))
    db.commit()
    db.close()


def delete_deadline(class_id: int, course_key: str, step: int):
    db = get_db()
    db.execute("DELETE FROM deadlines WHERE class_id = ? AND course_key = ? AND step = ?", (class_id, course_key, step))
    db.commit()
    db.close()


def list_deadlines() -> dict:
    """class_id -> liste d'échéances {course_key, step, due_date}, triées par date."""
    db = get_db()
    rows = db.execute("SELECT * FROM deadlines ORDER BY due_date, course_key, step").fetchall()
    db.close()
    out = {}
    for r in rows:
        out.setdefault(r["class_id"], []).append(dict(r))
    return out


def user_deadlines(user_id: int, course_key: str) -> dict:
    """Étape -> date limite la plus proche parmi les classes de l'étudiant."""
    db = get_db()
    rows = db.execute(
        "SELECT d.step, MIN(d.due_date) AS due FROM deadlines d JOIN class_members m ON m.class_id = d.class_id "
        "WHERE m.user_id = ? AND d.course_key = ? GROUP BY d.step", (user_id, course_key)).fetchall()
    db.close()
    return {r["step"]: r["due"] for r in rows}


def deadlines_per_user(course_key: str) -> dict:
    """user_id -> {étape: date limite la plus proche} pour un parcours (tableau de bord, export)."""
    db = get_db()
    rows = db.execute(
        "SELECT m.user_id, d.step, MIN(d.due_date) AS due FROM deadlines d "
        "JOIN class_members m ON m.class_id = d.class_id WHERE d.course_key = ? GROUP BY m.user_id, d.step",
        (course_key,)).fetchall()
    db.close()
    out = {}
    for r in rows:
        out.setdefault(r["user_id"], {})[r["step"]] = r["due"]
    return out


# ─── Attestations ─────────────────────────────────────────────────────

def _certificate_code() -> str:
    return "-".join("".join(secrets.choice(_CODE_ALPHABET) for _ in range(4)) for _ in range(3))


def issue_certificate(user_id: int, course: dict, score: int, exercises: int) -> str:
    """Crée ou met à jour l'attestation de l'étudiant pour ce parcours (le code ne change pas)."""
    db = get_db()
    row = db.execute("SELECT code FROM certificates WHERE user_id = ? AND course_key = ?",
                     (user_id, course["key"])).fetchone()
    code = row["code"] if row else _certificate_code()
    db.execute(
        "INSERT INTO certificates (code, user_id, course_key, course_title, score, max_score, exercises, total_exercises) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(user_id, course_key) DO UPDATE SET "
        "score = excluded.score, max_score = excluded.max_score, exercises = excluded.exercises, "
        "total_exercises = excluded.total_exercises, course_title = excluded.course_title, issued_at = CURRENT_TIMESTAMP",
        (code, user_id, course["key"], course["title"], score, course["max_score"], exercises, course["total_exercises"]),
    )
    db.commit()
    db.close()
    return code


def get_certificate(code: str):
    db = get_db()
    row = db.execute(
        "SELECT c.*, u.first_name, u.last_name FROM certificates c JOIN users u ON u.id = c.user_id WHERE c.code = ?",
        (code.strip().upper(),)).fetchone()
    db.close()
    return dict(row) if row else None


def user_certificates(user_id: int) -> dict:
    db = get_db()
    rows = db.execute("SELECT course_key, code FROM certificates WHERE user_id = ?", (user_id,)).fetchall()
    db.close()
    return {r["course_key"]: r["code"] for r in rows}


# ─── Sauvegarde ───────────────────────────────────────────────────────

def backup_to(path: str):
    """Copie cohérente de la base (API de sauvegarde de SQLite : sûre pendant que la plateforme tourne)."""
    src = get_db()
    dst = sqlite3.connect(path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    os.chmod(path, 0o600)  # comptes et empreintes de mots de passe : lisible par le seul propriétaire
