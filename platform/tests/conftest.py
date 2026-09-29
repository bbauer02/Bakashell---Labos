"""Tests unitaires de la plateforme : sans Docker (les conteneurs sont simulés), base SQLite temporaire.

    pip install -r platform/requirements.txt -r platform/requirements-dev.txt
    python -m pytest platform/tests
"""
import os
import sys
import tempfile

import pytest

PLATFORM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PLATFORM)

# Avant l'import de l'application : base temporaire, templates du dépôt, compte admin connu
_TMP = tempfile.mkdtemp(prefix="lab-tests-")
os.environ.update({
    "DB_PATH": os.path.join(_TMP, "platform.db"),
    "APP_DIR": PLATFORM,
    "ADMIN_EMAIL": "prof@lab.test",
    "ADMIN_PASSWORD": "motdepasse-prof",
    "BACKUP_DIR": "",
})

from fastapi.testclient import TestClient  # noqa: E402

from app import containers, database as db, main, ratelimit  # noqa: E402

ADMIN = ("prof@lab.test", "motdepasse-prof")


class FakeDocker:
    """Remplace les appels Docker : chaque vérification répond selon self.passing (identifiants d'exercices)."""

    def __init__(self):
        self.passing = set()
        self.status = "running"

    def install(self, monkeypatch):
        monkeypatch.setattr(containers, "get_or_create_container", lambda user_id, course: f"fake-{user_id}")
        monkeypatch.setattr(containers, "exec_in_container", self.exec)
        monkeypatch.setattr(containers, "container_status", lambda user_id, course: self.status)
        monkeypatch.setattr(containers, "list_student_containers", lambda: [])
        monkeypatch.setattr(containers, "remove_container", lambda *a, **k: None)
        monkeypatch.setattr(containers, "stop_idle_containers", lambda *a, **k: [])

    def exec(self, container_id, cmd, env=None, user="root", workdir=None):
        script = cmd[-1] if isinstance(cmd, list) else cmd
        if cmd[:2] == ["test", "-f"]:  # marqueur de mise en place : déjà faite
            return 0, ""
        for ex_id in self.passing:
            if f"#EX:{ex_id}#" in script:
                return 0, "@@OK\n"
        return 0, "@@FAIL 0\n"


@pytest.fixture()
def fake_docker(monkeypatch):
    fake = FakeDocker()
    fake.install(monkeypatch)
    # Chaque exercice est repérable dans la commande de vérification
    real = main.runner.check_command
    monkeypatch.setattr(main.runner, "check_command",
                        lambda course, ex: real(course, ex)[:-1] + [f"#EX:{ex['id']}#\n" + real(course, ex)[-1]])
    return fake


@pytest.fixture()
def app_client(fake_docker):
    if os.path.exists(os.environ["DB_PATH"]):
        os.remove(os.environ["DB_PATH"])
    ratelimit.reset_all()
    with TestClient(main.app) as client:
        yield client


def login(client, email, password):
    client.cookies.clear()
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=False)


def register(client, first="Ada", last="Lovelace", email="ada@lab.test", password="motdepasse1", code=""):
    client.cookies.clear()
    return client.post("/register", data={"first_name": first, "last_name": last, "email": email,
                                          "password": password, "password2": password, "class_code": code},
                       follow_redirects=False)


def admin_client(client):
    assert login(client, *ADMIN).status_code == 302
    return client


def make_class(client, name="BTS SIO 1", courses=("linux",)):
    """Crée une classe (en admin) avec des labos ouverts ; retourne (id, code)."""
    admin_client(client)
    client.post("/admin/classes", data={"name": name})
    cls = [c for c in db.list_classes() if c["name"] == name][0]
    client.post(f"/admin/classes/{cls['id']}/courses", data={f"course_{k}": "1" for k in courses})
    return cls["id"], cls["code"]


def user_id(email):
    conn = db.get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row["id"]
