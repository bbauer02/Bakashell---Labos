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


def init_db(exercises_version: str):
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
            step INTEGER NOT NULL,
            data TEXT NOT NULL,
            PRIMARY KEY (user_id, step)
        );
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    cols = [r["name"] for r in db.execute("PRAGMA table_info(users)").fetchall()]
    if "last_seen" not in cols:
        db.execute("ALTER TABLE users ADD COLUMN last_seen TIMESTAMP")
    db.execute(f"DELETE FROM sessions WHERE created_at < datetime('now', '-{SESSION_HOURS} hours')")
    db.commit()
    db.close()

    migrated = _migrate_exercises(exercises_version)
    _ensure_admin()
    return migrated


def _migrate_exercises(version: str) -> bool:
    """Si le catalogue d'exercices a changé, la progression est archivée (pas supprimée)."""
    db = get_db()
    row = db.execute("SELECT value FROM meta WHERE key = 'exercises_version'").fetchone()
    current = row["value"] if row else None
    if current == version:
        db.close()
        return False
    has_progress = db.execute("SELECT COUNT(*) AS n FROM progress").fetchone()["n"] > 0
    if has_progress:
        db.execute(
            "INSERT INTO progress_archive (user_id, exercise_id, points, completed_at, exercises_version) "
            "SELECT user_id, exercise_id, points, completed_at, ? FROM progress",
            (current or "1",),
        )
        db.execute("DELETE FROM progress")
    db.execute("DELETE FROM hints_used")
    db.execute("DELETE FROM step_setup")
    db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('exercises_version', ?)", (version,))
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

def get_user_score(user_id: int):
    db = get_db()
    rows = db.execute("SELECT exercise_id, points FROM progress WHERE user_id = ?", (user_id,)).fetchall()
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


def reset_user_progress(user_id: int):
    db = get_db()
    db.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM hints_used WHERE user_id = ?", (user_id,))
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

def get_setup(user_id: int, step: int):
    db = get_db()
    row = db.execute("SELECT data FROM step_setup WHERE user_id = ? AND step = ?", (user_id, step)).fetchone()
    db.close()
    return json.loads(row["data"]) if row else None


def save_setup(user_id: int, step: int, data: dict):
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO step_setup (user_id, step, data) VALUES (?, ?, ?)",
        (user_id, step, json.dumps(data)),
    )
    db.commit()
    db.close()


# ─── Tableau de bord ───────────────────────────────────────────────────

def get_all_students():
    """Pour le tableau de bord enseignant — exclut les admins."""
    db = get_db()
    rows = db.execute("""
        SELECT u.id, u.first_name, u.last_name, u.email, u.is_admin, u.last_seen,
               COALESCE(SUM(p.points), 0) as score,
               COUNT(p.exercise_id) as exercises_done,
               u.created_at
        FROM users u
        LEFT JOIN progress p ON u.id = p.user_id
        WHERE u.is_admin = 0
        GROUP BY u.id
        ORDER BY score DESC
    """).fetchall()
    matrix = {}
    for r in db.execute("SELECT user_id, exercise_id FROM progress").fetchall():
        step = int(r["exercise_id"].split(".")[0])
        matrix.setdefault(r["user_id"], {}).setdefault(step, 0)
        matrix[r["user_id"]][step] += 1
    db.close()
    students = [dict(r) for r in rows]
    for s in students:
        s["per_step"] = matrix.get(s["id"], {})
    return students


def delete_user(user_id: int):
    """Supprime un utilisateur (non admin) et toutes ses données."""
    db = get_db()
    row = db.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row or row["is_admin"]:
        db.close()
        return
    for table in ("progress", "sessions", "hints_used", "step_setup"):
        db.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ? AND is_admin = 0", (user_id,))
    db.commit()
    db.close()
