"""SQLite database for users and progress."""
import sqlite3
import hashlib
import secrets
import os
import json

DB_PATH = os.environ.get("DB_PATH", "/data/platform.db")


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
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
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            container_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    db.commit()
    db.close()

    # Create admin account if it doesn't exist
    _ensure_admin()


ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "bbauer02@gmail.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "bb1212")
ADMIN_FIRST = os.environ.get("ADMIN_FIRST", "Baptiste")
ADMIN_LAST = os.environ.get("ADMIN_LAST", "Bauer")


def _ensure_admin():
    db = get_db()
    row = db.execute("SELECT id, is_admin FROM users WHERE email = ?", (ADMIN_EMAIL,)).fetchone()
    if not row:
        db.execute(
            "INSERT INTO users (first_name, last_name, email, password_hash, is_admin) VALUES (?, ?, ?, ?, 1)",
            (ADMIN_FIRST, ADMIN_LAST, ADMIN_EMAIL, hash_password(ADMIN_PASSWORD)),
        )
        db.commit()
    elif not row["is_admin"]:
        db.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (row["id"],))
        db.commit()
    db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password: str, password_hash: str) -> bool:
    salt, h = password_hash.split(":")
    return hashlib.sha256((salt + password).encode()).hexdigest() == h


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
    db.close()
    if row and verify_password(password, row["password_hash"]):
        return dict(row)
    return None


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
        "SELECT s.*, u.first_name, u.last_name, u.email, u.is_admin FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ?",
        (token,),
    ).fetchone()
    db.close()
    return dict(row) if row else None


def delete_session(token: str):
    db = get_db()
    db.execute("DELETE FROM sessions WHERE token = ?", (token,))
    db.commit()
    db.close()


def set_container_id(token: str, container_id: str):
    db = get_db()
    db.execute("UPDATE sessions SET container_id = ? WHERE token = ?", (container_id, token))
    db.commit()
    db.close()


def get_user_score(user_id: int):
    db = get_db()
    rows = db.execute("SELECT exercise_id, points FROM progress WHERE user_id = ?", (user_id,)).fetchall()
    db.close()
    completed = [r["exercise_id"] for r in rows]
    score = sum(r["points"] for r in rows)
    return {"score": score, "completed": completed}


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
        return False  # Already completed
    finally:
        db.close()


def reset_user_progress(user_id: int):
    db = get_db()
    db.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
    db.commit()
    db.close()


def get_all_students():
    """For teacher dashboard — excludes admins."""
    db = get_db()
    rows = db.execute("""
        SELECT u.id, u.first_name, u.last_name, u.email, u.is_admin,
               COALESCE(SUM(p.points), 0) as score,
               COUNT(p.exercise_id) as exercises_done,
               u.created_at
        FROM users u
        LEFT JOIN progress p ON u.id = p.user_id
        WHERE u.is_admin = 0
        GROUP BY u.id
        ORDER BY score DESC
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]


def delete_user(user_id: int):
    """Delete a user, their progress and their sessions."""
    db = get_db()
    db.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ? AND is_admin = 0", (user_id,))
    db.commit()
    db.close()
