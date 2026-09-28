"""SQLite : comptes, sessions, progression, indices et données de mise en place."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/data/platform.db")
SESSION_HOURS = int(os.environ.get("SESSION_HOURS", "24"))


def get_db():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    return db


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
    db.commit()
    db.close()

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
    db.execute("DELETE FROM step_setup WHERE course = ?", (course["key"],))
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


def authenticate(email: str, password: str):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        db.close()
        return None
    if not row["password_hash"].startswith("scrypt$"):
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), row["id"]))
        db.commit()
    db.close()
    return dict(row)


# ─── Sessions ──────────────────────────────────────────────────────────

def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db = get_db()
    db.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
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
        (token,),
    ).fetchone()
    db.close()
    return dict(row) if row else None


def delete_session(token: str):
    db = get_db()
    db.execute("DELETE FROM sessions WHERE token = ?", (token,))
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
    db.close()
    return {
        "score": sum(r["points"] for r in rows),
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
    if course:
        db.execute("DELETE FROM step_setup WHERE user_id = ? AND course = ?", (user_id, course["key"]))
    else:
        db.execute("DELETE FROM step_setup WHERE user_id = ?", (user_id,))
    db.commit()
    db.close()


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
    db.close()
    students = {u["id"]: {**dict(u), "score": 0, "exercises_done": 0, "per_step": {}} for u in users}
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
    for table in ("progress", "sessions", "hints_used", "step_setup", "class_members"):
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
