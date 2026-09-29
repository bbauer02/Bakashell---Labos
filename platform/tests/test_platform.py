"""Comptes, accès par classe, sécurité, export, échéances, historique, statistiques, attestations, sauvegarde."""
import asyncio
import csv
import datetime
import io
import os
import re

from conftest import ADMIN, admin_client, login, make_class, register, user_id

from app import database as db
from app import main, memo, solutions, terminals
from app.courses import COURSES, EXERCISE_INDEX

LINUX = COURSES["linux"]
FIRST = LINUX["steps"][1]["exercises"][0]["id"]  # « 1.1 »


def student_in_class(client, email="ada@lab.test", courses=("linux",)):
    _, code = make_class(client, courses=courses)
    assert register(client, email=email, code=code).status_code == 302
    return user_id(email)


# ─── Catalogues ─────────────────────────────────────────────────────────

def test_catalogues_coherents():
    memo.check(COURSES, EXERCISE_INDEX)
    solutions.check_coverage(COURSES)
    for course in COURSES.values():
        for step in course["steps"].values():
            assert len(step["exercises"]) < 10, "numéro de ticket : 10 exercices maximum par étape"
            for ex in step["exercises"]:
                assert ex.get("ticket"), f"{ex['id']} : exercice sans ticket"
                assert ex["checks"] and ex["points"] > 0


# ─── Comptes et accès ───────────────────────────────────────────────────

def test_inscription_puis_acces_selon_la_classe(app_client):
    assert register(app_client).status_code == 302
    assert app_client.get("/lab/linux", follow_redirects=False).status_code == 302  # aucune classe
    assert app_client.get("/api/linux/steps").status_code == 404

    _, code = make_class(app_client, courses=("linux",))
    login(app_client, "ada@lab.test", "motdepasse1")
    app_client.post("/catalogue/rejoindre", data={"code": code.lower().replace("-", " ")})
    assert app_client.get("/lab/linux").status_code == 200
    assert len(app_client.get("/api/linux/steps").json()) == len(LINUX["steps"])
    assert app_client.get("/api/jest/steps").status_code == 404  # labo non ouvert à la classe


def test_pages_enseignant_interdites_aux_etudiants(app_client):
    uid = student_in_class(app_client)
    for url in ("/dashboard", "/admin/classes", "/admin/stats", "/admin/export.csv", f"/admin/terminal/{uid}"):
        r = app_client.get(url, follow_redirects=False)
        assert r.status_code == 302, url
    assert app_client.get(f"/api/solution/{FIRST}").status_code == 403
    assert app_client.post(f"/api/admin/reset-link/{uid}").status_code == 403


def test_limitation_des_tentatives_de_connexion(app_client):
    register(app_client)
    for _ in range(10):
        assert login(app_client, "ada@lab.test", "mauvais").status_code == 200
    r = login(app_client, "ada@lab.test", "motdepasse1")
    assert r.status_code == 429 and "Trop de tentatives" in r.text


def test_changement_de_mot_de_passe(app_client):
    register(app_client)
    other = app_client.cookies.get("session")
    r = app_client.post("/compte", data={"current": "faux", "password": "nouveau-mdp", "password2": "nouveau-mdp"})
    assert "incorrect" in r.text
    login(app_client, "ada@lab.test", "motdepasse1")
    r = app_client.post("/compte", data={"current": "motdepasse1", "password": "nouveau-mdp",
                                         "password2": "nouveau-mdp"}, follow_redirects=False)
    assert r.status_code == 302
    assert db.get_session(other) is None  # les autres sessions sont fermées
    assert login(app_client, "ada@lab.test", "nouveau-mdp").status_code == 302


def test_lien_de_reinitialisation(app_client):
    uid = student_in_class(app_client)
    admin_client(app_client)
    link = app_client.post(f"/api/admin/reset-link/{uid}").json()["link"]
    path = "/" + link.split("/", 3)[3]
    app_client.cookies.clear()
    assert "Ada Lovelace" in app_client.get(path).text
    r = app_client.post(path, data={"password": "court", "password2": "court"})
    assert "trop court" in r.text
    r = app_client.post(path, data={"password": "tout-nouveau", "password2": "tout-nouveau"}, follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/catalogue"
    assert app_client.get(path).status_code == 404  # lien à usage unique
    assert login(app_client, "ada@lab.test", "motdepasse1").status_code == 200  # ancien mot de passe refusé
    assert login(app_client, "ada@lab.test", "tout-nouveau").status_code == 302


# ─── Vérifications, historique, statistiques ────────────────────────────

def test_historique_et_statistiques(app_client, fake_docker):
    student_in_class(app_client)
    login(app_client, "ada@lab.test", "motdepasse1")
    r = app_client.post(f"/api/linux/validate/1?exercise={FIRST}").json()
    assert not r["validation"]["results"][0]["passed"]
    app_client.post(f"/api/linux/validate/1?auto=true")  # vérification automatique : pas d'historique
    fake_docker.passing.add(FIRST)
    r = app_client.post(f"/api/linux/validate/1?exercise={FIRST}").json()
    assert r["validation"]["results"][0]["passed"]

    h = app_client.get(f"/api/linux/attempts/{FIRST}").json()
    assert h["attempts_total"] == 2
    assert h["attempts"][0]["passed"] and not h["attempts"][1]["passed"]
    step = app_client.get("/api/linux/step/1").json()
    assert step["exercises"][0]["attempts_total"] == 2

    stats = db.exercise_stats(LINUX)
    assert stats["exercises"][FIRST] == {**stats["exercises"][FIRST], "tried": 1, "passed": 1, "fails": 1}
    admin_client(app_client)
    page = app_client.get("/admin/stats?course=linux")
    assert page.status_code == 200 and "100 %" in page.text


# ─── Échéances et export ────────────────────────────────────────────────

def test_echeances_retard_et_export(app_client):
    class_id, code = make_class(app_client)
    register(app_client, code=code)
    uid = user_id("ada@lab.test")
    db.add_exercise_completion(uid, FIRST, 3)
    admin_client(app_client)
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    later = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    app_client.post(f"/admin/classes/{class_id}/deadlines", data={"course": "linux", "step": "1", "due_date": yesterday})
    app_client.post(f"/admin/classes/{class_id}/deadlines",
                    data={"course": "linux", "step": "2", "step_to": "3", "due_date": later})
    assert len(db.list_deadlines()[class_id]) == 3

    assert "En retard : étape 1" in app_client.get("/dashboard?course=linux").text
    r = app_client.get(f"/admin/export.csv?course=linux&classe={class_id}")
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.startswith("﻿")
    rows = list(csv.reader(io.StringIO(r.text.lstrip("﻿")), delimiter=";"))
    head, ada = rows[0], rows[1]
    assert ada[head.index("Nom")] == "Lovelace" and ada[head.index("Score")] == "3"
    assert ada[head.index("Étapes en retard")] == "1"
    assert ada[head.index("Note /20")] == str(round(20 * 3 / LINUX["max_score"], 2)).replace(".", ",")

    login(app_client, "ada@lab.test", "motdepasse1")
    steps = {s["num"]: s for s in app_client.get("/api/linux/steps").json()}
    assert steps[1]["due"] == yesterday and steps[3]["due"] == later and steps[4]["due"] is None
    assert "en retard" in app_client.get("/catalogue").text


# ─── Attestations ───────────────────────────────────────────────────────

def test_attestation(app_client):
    uid = student_in_class(app_client)
    login(app_client, "ada@lab.test", "motdepasse1")
    r = app_client.post("/attestation/linux", follow_redirects=False)
    assert "err=" in r.headers["location"]  # score insuffisant

    for ex_id, (key, _, _, ex) in EXERCISE_INDEX.items():
        if key == "linux":
            db.add_exercise_completion(uid, ex_id, ex["points"])
    r = app_client.post("/attestation/linux", follow_redirects=False)
    code = r.headers["location"].rsplit("/", 1)[1]
    app_client.cookies.clear()
    page = app_client.get(f"/attestation/{code}")  # page publique
    assert page.status_code == 200 and "Ada Lovelace" in page.text and f"{LINUX['max_score']} / {LINUX['max_score']}" in page.text
    assert app_client.get("/attestation/AAAA-BBBB-CCCC").status_code == 404


# ─── Migrations, sauvegarde, terminaux ──────────────────────────────────

def test_changement_de_version_archive_la_progression(app_client):
    uid = student_in_class(app_client)
    db.add_exercise_completion(uid, FIRST, 3)
    db.record_attempt(uid, FIRST, False, "raté")
    assert db._migrate_course({**LINUX, "version": "test-nouvelle-version"})
    assert db.get_user_score(uid, LINUX["id_glob"])["score"] == 0
    assert db.get_attempts(uid, [FIRST]) == {}
    conn = db.get_db()
    assert conn.execute("SELECT COUNT(*) FROM progress_archive WHERE user_id = ?", (uid,)).fetchone()[0] == 1
    conn.close()


def test_sauvegarde(app_client, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(main, "BACKUP_KEEP", 2)
    for i in range(3):
        (tmp_path / f"platform-2000010{i}-000000.db").write_text("ancienne")
    path = main.backup_now()
    kept = sorted(os.listdir(tmp_path))
    assert len(kept) == 2 and os.path.basename(path) in kept
    conn = __import__("sqlite3").connect(path)
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] >= 1  # copie exploitable
    conn.close()


def test_terminal_en_lecture_seule():
    async def scenario():
        key = (42, "linux")
        tid = terminals.opened(key)
        terminals.feed(key, tid, b"etudiant@lab:~$ ls\r\n")
        q = terminals.subscribe(key)  # arrivée de l'enseignant : il reçoit l'écran récent
        assert q.get_nowait() == ("open", tid, b"")
        assert q.get_nowait() == ("data", tid, b"etudiant@lab:~$ ls\r\n")
        terminals.feed(key, tid, b"notes.txt\r\n")
        assert q.get_nowait() == ("data", tid, b"notes.txt\r\n")
        terminals.closed(key, tid)
        assert q.get_nowait() == ("close", tid, b"")
        assert not terminals.is_open(key)
        terminals.unsubscribe(key, q)

    asyncio.run(scenario())


def test_page_du_terminal_enseignant(app_client):
    uid = student_in_class(app_client)
    admin_client(app_client)
    page = app_client.get(f"/admin/terminal/{uid}?course=linux")
    assert page.status_code == 200 and "Lecture seule" in page.text
    with app_client.websocket_connect(f"/ws/watch?user={uid}&course=linux") as ws:
        assert ws.receive_json() == {"type": "hello", "open": False}


def test_statut_de_l_environnement(app_client, fake_docker):
    student_in_class(app_client)
    login(app_client, "ada@lab.test", "motdepasse1")
    fake_docker.status = "stopped"
    assert app_client.get("/api/linux/status").json()["status"] == "stopped"


def test_admin_voit_tout(app_client):
    admin_client(app_client)
    for key in COURSES:
        assert app_client.get(f"/lab/{key}").status_code == 200
    assert re.search(r"Exporter les notes", app_client.get("/dashboard").text)
    assert ADMIN[0] in app_client.get("/compte").text


# ─── Correctifs de sécurité ─────────────────────────────────────────────

def test_attestation_ne_reflete_pas_l_url(app_client):
    uid = student_in_class(app_client)
    for ex_id, (key, _, _, ex) in EXERCISE_INDEX.items():
        if key == "linux":
            db.add_exercise_completion(uid, ex_id, ex["points"])
    login(app_client, "ada@lab.test", "motdepasse1")
    code = app_client.post("/attestation/linux", follow_redirects=False).headers["location"].rsplit("/", 1)[1]
    app_client.cookies.clear()
    page = app_client.get(f"/attestation/{code}?/autofocus/onfocus=alert(1)//").text
    assert "onfocus" not in page and "autofocus" not in page
    assert f'data-url="http://testserver/attestation/{code}"' in page


def test_export_csv_neutralise_les_formules(app_client):
    _, code = make_class(app_client)
    register(app_client, first="=HYPERLINK(\"http://x\";\"y\")", last="@SUM(1+1)", email="f@lab.test", code=code)
    admin_client(app_client)
    rows = list(csv.reader(io.StringIO(app_client.get("/admin/export.csv").text.lstrip("﻿")), delimiter=";"))
    row = [r for r in rows if "f@lab.test" in r][0]
    assert row[0] == "'@SUM(1+1)" and row[1].startswith("'=")


def test_limitation_remise_a_zero_et_autres_comptes(app_client):
    register(app_client)
    register(app_client, first="Grace", last="Hopper", email="grace@lab.test")
    # Des fautes de frappe d'autres personnes de la salle (même IP) ne bloquent pas un autre compte…
    for i in range(9):
        login(app_client, f"inconnu{i}@lab.test", "faux")
    assert login(app_client, "grace@lab.test", "motdepasse1").status_code == 302
    # … et une connexion réussie remet à zéro le compteur de l'adresse IP
    assert main.ratelimit.LOGIN_IP.blocked("ip:testclient") == 0
    assert main.ratelimit._hits.get(("login-ip", "ip:testclient")) is None
    # Le forçage d'un compte depuis une IP reste bloqué, sans empêcher un autre compte de se connecter
    for _ in range(10):
        login(app_client, "ada@lab.test", "faux")
    assert login(app_client, "ada@lab.test", "motdepasse1").status_code == 429
    assert login(app_client, "grace@lab.test", "motdepasse1").status_code == 302


def test_sessions_stockees_hachees(app_client):
    register(app_client)
    token = app_client.cookies.get("session")
    conn = db.get_db()
    stored = [r[0] for r in conn.execute("SELECT token FROM sessions").fetchall()]
    conn.close()
    assert token not in stored and db._token_hash(token) in stored
    assert db.get_session(token)["email"] == "ada@lab.test"


# ─── Étapes modifiées après leur préparation ────────────────────────────

def test_etape_modifiee_depuis_sa_preparation():
    from app import runner
    course = COURSES["linux"]
    num, step = next((n, s) for n, s in course["steps"].items() if runner.has_setup(s))
    a_jour = {"CLE": "x", "_empreinte": runner.setup_fingerprint(step)}
    assert not runner.setup_outdated(course, num, step, a_jour)
    assert runner.setup_outdated(course, num, step, {**a_jour, "_empreinte": "ancienne"})
    assert not runner.setup_outdated(course, num, step, None)  # jamais préparée
    # L'empreinte n'est pas transmise aux vérifications
    assert runner.check_env(a_jour) == {"LAB_CLE": "x"}
    # Données enregistrées avant les empreintes : comparées à la version publiée auparavant
    legacy = runner._LEGACY_FINGERPRINTS.get(f"linux:{num}")
    assert runner.setup_outdated(course, num, step, {"CLE": "x"}) == (legacy is not None and legacy != runner.setup_fingerprint(step))


def test_verification_groupee():
    from app import runner
    course = COURSES["linux"]
    exs = course["steps"][1]["exercises"][:3]
    cmd = runner.check_batch_command(course, exs)
    assert cmd[-1].count("@@EX ") == 3  # un seul docker exec pour les trois exercices
    out = (f"@@EX {exs[0]['id']}\n@@OK\n@@CODE 0\n"
           f"@@EX {exs[1]['id']}\n@@FAIL 0\nMSG:détail\n@@CODE 0\n"
           f"@@EX {exs[2]['id']}\n@@CODE 124\n")
    r = runner.parse_batch_output(exs, out)
    assert r[exs[0]["id"]] == (True, None)
    assert not r[exs[1]["id"]][0] and "détail" in r[exs[1]["id"]][1]
    assert not r[exs[2]["id"]][0] and "délai" in r[exs[2]["id"]][1]
    # Délai global dépassé avant le dernier exercice : échec explicite, pas d'exception
    r = runner.parse_batch_output(exs, out.split(f"@@EX {exs[2]['id']}")[0])
    assert not r[exs[2]["id"]][0]
