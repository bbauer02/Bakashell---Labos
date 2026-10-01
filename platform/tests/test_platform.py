"""Comptes, accès par classe, sécurité, export, échéances, historique, statistiques, attestations, sauvegarde."""
import asyncio
import csv
import datetime
import io
import json
import os
import re
import sqlite3

import pytest
from starlette.websockets import WebSocketDisconnect

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
    # Tous les exercices, aucun QCM : le maximum inclut aussi les points de QCM
    exercises = LINUX["max_score"] - LINUX["quiz_max"]
    assert page.status_code == 200 and "Ada Lovelace" in page.text and f"{exercises} / {LINUX['max_score']}" in page.text
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


def test_correction_commentee_apres_reussite(app_client, fake_docker):
    student_in_class(app_client)
    login(app_client, "ada@lab.test", "motdepasse1")
    assert app_client.get(f"/api/solution/{FIRST}").status_code == 403  # pas avant la réussite
    fake_docker.passing.add(FIRST)
    assert app_client.post(f"/api/linux/validate/1?exercise={FIRST}").json()["validation"]["results"][0]["passed"]
    s = app_client.get(f"/api/solution/{FIRST}").json()
    assert s["code"] and "explanation" in s and "checks" not in s  # sans le détail des vérifications
    assert not any(line.startswith("#? ") for line in s["code"].splitlines())
    second = LINUX["steps"][1]["exercises"][1]["id"]
    assert app_client.get(f"/api/solution/{second}").status_code == 403
    admin_client(app_client)
    assert "checks" in app_client.get(f"/api/solution/{second}").json()


def test_empreintes_des_images_a_jour():
    # Les conteneurs sont recréés quand l'empreinte de leur image change : elle doit suivre images/<parcours>
    import json
    from revisions_images import TARGET, all_revisions
    assert json.load(open(TARGET, encoding="utf-8")) == all_revisions(), \
        "images/ modifié : lancez python platform/tests/revisions_images.py"


def test_qcm_une_tentative_et_points(app_client, monkeypatch):
    pool = [{"q": f"Question {i}", "choices": ["bonne", "b", "c", "d"], "answer": 0, "explain": "car"} for i in range(6)]
    pool[5] = {"q": "Multi", "choices": ["x", "bonne1", "y", "bonne2"], "answer": [1, 3], "explain": ""}
    monkeypatch.setitem(LINUX, "quiz", {1: pool})
    student_in_class(app_client)
    login(app_client, "ada@lab.test", "motdepasse1")
    assert app_client.get("/api/linux/step/1").json()["quiz"] == {"done": None, "max": 4}
    q = app_client.get("/api/linux/quiz/1").json()
    assert not q["done"] and len(q["questions"]) == 4
    assert "answer" not in str(q) and "explain" not in str(q)  # pas de réponse avant la tentative
    assert app_client.get("/api/linux/quiz/1").json() == q  # tirage stable
    # Coche la « bonne » réponse partout (et les deux bonnes pour la question multiple) sauf pour la première question
    answers = []
    for n, question in enumerate(q["questions"]):
        good = [i for i, c in enumerate(question["choices"]) if c.startswith("bonne")]
        answers.append([] if n == 0 else good)
    r = app_client.post("/api/linux/quiz/1", json={"answers": answers}).json()
    assert r["done"] and r["score"] == 3 and r["max"] == 4
    assert r["progress"]["score"] == 3
    assert r["details"][0]["correct"] and not r["details"][0]["ok"]
    # Une seule tentative : un nouvel envoi ne change rien
    r2 = app_client.post("/api/linux/quiz/1", json={"answers": [[0]] * 4}).json()
    assert r2["score"] == 3
    assert app_client.get("/api/linux/step/1").json()["quiz"]["done"] == [3, 4]
    assert app_client.get("/api/linux/quiz/2").status_code == 404  # pas de QCM pour cette étape


def test_mode_epreuve_sans_correction(app_client, fake_docker, monkeypatch):
    monkeypatch.setitem(LINUX, "exam", True)
    student_in_class(app_client)
    login(app_client, "ada@lab.test", "motdepasse1")
    fake_docker.passing.add(FIRST)
    assert app_client.post(f"/api/linux/validate/1?exercise={FIRST}").json()["validation"]["results"][0]["passed"]
    assert app_client.get("/api/linux/step/1").json()["exam"] is True
    assert app_client.get(f"/api/solution/{FIRST}").status_code == 403  # même après réussite
    admin_client(app_client)
    assert app_client.get(f"/api/solution/{FIRST}").status_code == 200


# ─── Suivi d'intégrité ──────────────────────────────────────────────────

def test_saisie_terminal_lignes_et_collages():
    from app.integrity import InputRecorder
    saved = []
    rec = InputRecorder(lambda kind, text: saved.append((kind, text)))
    for ch in "lss\x7f -la\x1b[A\r":  # frappe caractère par caractère, retour arrière, flèche
        rec.feed(ch)
    rec.feed("cat /etc/passwd | cut -d: -f1 | sort\r")  # collé d'un coup
    assert saved == [("ligne", "ls -la"), ("collage", "cat /etc/passwd | cut -d: -f1 | sort"),
                     ("ligne", "cat /etc/passwd | cut -d: -f1 | sort")]


def test_rapport_d_integrite():
    from app import integrity
    names = {1: "Ada", 2: "Bob", 3: "Cyd", 4: "Dan"}
    ids = [ex["id"] for s in LINUX["steps"].values() for ex in s["exercises"]]
    comp = []
    for uid in (1, 2, 3):  # trois élèves « normaux » : 5 min par exercice
        comp += [(uid, ids[i], 1000 + 300 * i) for i in range(4)]
    comp += [(4, ids[i], 5000 + 10 * i) for i in range(6)]  # Dan : 6 exercices en 50 s
    rare = "grep -E '^[a-z]+:x:1[0-9]{3}:' /etc/passwd | cut -d: -f1"
    logs = [(1, "ligne", rare, 1200), (2, "ligne", rare, 1300), (1, "ligne", rare + " | sort", 1250),
            (2, "ligne", rare + " | sort", 1350), (3, "ligne", "commande du cours bien longue et partagée", 1400),
            (4, "collage", "x" * 50, 4995)]
    r = integrity.report(LINUX, names, comp, logs, reference="commande du cours bien longue et partagée")
    assert {x["user"] for x in r["rapid"]} == {"Dan"}
    assert r["bursts"] and r["bursts"][0]["user"] == "Dan" and r["bursts"][0]["count"] == 6
    assert r["pastes"][0]["user"] == "Dan" and r["pastes"][0]["then"]
    assert len(r["similar"]) == 1 and set(r["similar"][0]["users"]) == {"Ada", "Bob"} and r["similar"][0]["count"] == 2


def test_page_integrite(app_client):
    student_in_class(app_client)
    login(app_client, "ada@lab.test", "motdepasse1")
    assert app_client.get("/admin/integrite", follow_redirects=False).status_code == 302
    db.log_terminal(user_id("ada@lab.test"), "linux", 1, "collage", "echo " + "a" * 60)
    admin_client(app_client)
    page = app_client.get("/admin/integrite?course=linux")
    assert page.status_code == 200 and "Collages dans le terminal" in page.text and "a" * 60 in page.text


def test_titre_et_auteur(app_client):
    page = app_client.get("/login").text
    assert "Connexion — Bakashell</title>" in page and "Bakashell — Labo DevOps" in page
    assert "Bauer Baptiste" in page and 'href="mailto:bbauer02@gmail.com"' in page
    assert '<meta name="author" content="Bauer Baptiste (bbauer02@gmail.com)">' in page


# ─── Comptes enseignants : invitation, cloisonnement, désactivation ─────

TEACHER_PASSWORD = "motdepasse-ens"


def teacher_form(email, first="Alan", last="Turing", password=TEACHER_PASSWORD):
    return {"first_name": first, "last_name": last, "email": email, "password": password, "password2": password}


def invite_path(client, email=""):
    """Lien d'invitation créé par l'administrateur (chemin relatif /invitation/<jeton>)."""
    admin_client(client)
    page = client.post("/admin/enseignants/invitation", data={"email": email})
    assert page.status_code == 200
    link = re.search(r'id="invite-url" readonly value="([^"]+)"', page.text).group(1)
    return "/" + link.split("/", 3)[3]


def make_teacher(client, email, first="Alan", last="Turing"):
    path = invite_path(client)
    client.cookies.clear()
    assert client.post(path, data=teacher_form(email, first, last), follow_redirects=False).status_code == 302
    return user_id(email)


def teacher_class(client, teacher_email, name, student_email, first="Ada"):
    """L'enseignant crée une classe (labo Linux ouvert), un étudiant s'y inscrit avec le code ; retourne (classe, étudiant)."""
    login(client, teacher_email, TEACHER_PASSWORD)
    client.post("/admin/classes", data={"name": name})
    cls = [c for c in db.list_classes(user_id(teacher_email)) if c["name"] == name][0]
    client.post(f"/admin/classes/{cls['id']}/courses", data={"course_linux": "1"})
    assert register(client, first=first, email=student_email, code=cls["code"]).status_code == 302
    return cls["id"], user_id(student_email)


def invites_count():
    conn = db.get_db()
    n = conn.execute("SELECT COUNT(*) FROM teacher_invites").fetchone()[0]
    conn.close()
    return n


def test_invitation_enseignant(app_client):
    path = invite_path(app_client, email="alan@lab.test")
    app_client.cookies.clear()
    assert app_client.get(path).status_code == 200
    r = app_client.post(path, data=teacher_form("autre@lab.test"))
    assert "réservée à une autre adresse" in r.text
    r = app_client.post(path, data=teacher_form("alan@lab.test", password="court"))
    assert "trop court" in r.text
    r = app_client.post(path, data=teacher_form("alan@lab.test"), follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/dashboard"
    teacher = db.get_user(user_id("alan@lab.test"))
    assert teacher["is_admin"] == 1 and teacher["is_superadmin"] == 0
    page = app_client.get("/dashboard")  # connecté directement
    assert page.status_code == 200 and ">Enseignant</span>" in page.text and "/admin/enseignants" not in page.text
    conn = db.get_db()
    stored = [r[0] for r in conn.execute("SELECT token_hash FROM teacher_invites").fetchall()]
    conn.close()
    token = path.rsplit("/", 1)[1]
    assert token not in stored and db._token_hash(token) in stored  # seule l'empreinte est conservée

    # Lien déjà utilisé, faux ou expiré : refusé, aucun compte créé
    app_client.cookies.clear()
    assert app_client.get(path).status_code == 404
    assert app_client.post(path, data=teacher_form("bis@lab.test"), follow_redirects=False).status_code == 404
    assert app_client.get("/invitation/jeton-invente").status_code == 404
    expired = invite_path(app_client)
    conn = db.get_db()
    conn.execute("UPDATE teacher_invites SET created_at = datetime('now', '-8 days') WHERE used_at IS NULL")
    conn.commit()
    conn.close()
    app_client.cookies.clear()
    assert app_client.get(expired).status_code == 404
    assert app_client.post(expired, data=teacher_form("tard@lab.test"), follow_redirects=False).status_code == 404
    assert db.find_student_by_email("bis@lab.test") is None
    conn = db.get_db()
    assert conn.execute("SELECT COUNT(*) FROM users WHERE email IN ('bis@lab.test', 'tard@lab.test')").fetchone()[0] == 0
    conn.close()

    # Ni un enseignant ni un étudiant ne créent d'invitation ; pas d'inscription enseignant libre
    before = invites_count()
    login(app_client, "alan@lab.test", TEACHER_PASSWORD)
    assert app_client.get("/admin/enseignants").status_code == 403
    assert app_client.post("/admin/enseignants/invitation", data={"email": ""}).status_code == 403
    register(app_client, email="eve@lab.test")
    assert app_client.post("/admin/enseignants/invitation", follow_redirects=False).status_code == 302
    assert invites_count() == before
    assert db.get_user(user_id("eve@lab.test"))["is_admin"] == 0


def test_cloisonnement_entre_enseignants(app_client):
    make_teacher(app_client, "alan@lab.test")
    make_teacher(app_client, "barbara@lab.test", first="Barbara", last="Liskov")
    # Même nom de classe pour deux enseignants : autorisé (unique par propriétaire)
    ca, sa = teacher_class(app_client, "alan@lab.test", "BTS SIO 1", "ada@lab.test")
    cb, sb = teacher_class(app_client, "barbara@lab.test", "BTS SIO 1", "bob@lab.test", first="Bob")
    db.add_exercise_completion(sb, FIRST, 3)
    db.log_terminal(sa, "linux", 1, "collage", "echo " + "a" * 60)
    db.log_terminal(sb, "linux", 1, "collage", "echo " + "b" * 60)
    later = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    login(app_client, "barbara@lab.test", TEACHER_PASSWORD)
    app_client.post(f"/admin/classes/{cb}/deadlines", data={"course": "linux", "step": "1", "due_date": later})
    before_b = [c for c in db.list_classes() if c["id"] == cb][0]
    deadlines_b = db.list_deadlines()[cb]

    login(app_client, "alan@lab.test", TEACHER_PASSWORD)
    # Pages de suivi : seulement ses étudiants, même en demandant la classe de B
    for classe in (0, cb):
        dash = app_client.get(f"/dashboard?course=linux&classe={classe}").text
        assert "ada@lab.test" in dash and "bob@lab.test" not in dash
        assert "1 étudiant(s) pris en compte" in app_client.get(f"/admin/stats?course=linux&classe={classe}").text
        integ = app_client.get(f"/admin/integrite?course=linux&classe={classe}").text
        assert "a" * 60 in integ and "b" * 60 not in integ
        export = app_client.get(f"/admin/export.csv?course=linux&classe={classe}").text
        assert "ada@lab.test" in export and "bob@lab.test" not in export
    classes_page = app_client.get("/admin/classes").text
    assert "bob@lab.test" not in classes_page and before_b["code"] not in classes_page and "Bob" not in classes_page

    # Actions sur l'étudiant de B : refusées ; sur le sien : permises
    assert app_client.get(f"/admin/terminal/{sb}?course=linux").status_code == 403
    assert app_client.get(f"/admin/terminal/{sa}?course=linux").status_code == 200
    with pytest.raises(WebSocketDisconnect):
        with app_client.websocket_connect(f"/ws/watch?user={sb}&course=linux") as ws:
            ws.receive_json()
    with app_client.websocket_connect(f"/ws/watch?user={sa}&course=linux") as ws:
        assert ws.receive_json()["type"] == "hello"
    assert app_client.post(f"/api/admin/reset-link/{sb}").status_code == 403
    assert app_client.post(f"/api/admin/reset-link/{sa}").status_code == 200
    assert app_client.post(f"/admin/reset-user/{sb}?course=linux").status_code == 403
    assert db.get_user_score(sb, LINUX["id_glob"])["score"] == 3
    # Jamais sur un compte du personnel, ni suppression définitive d'un étudiant (même le sien)
    assert app_client.post(f"/api/admin/reset-link/{user_id('barbara@lab.test')}").status_code == 403
    assert app_client.post(f"/api/admin/reset-link/{user_id(ADMIN[0])}").status_code == 403
    assert app_client.post(f"/admin/delete-user/{sa}").status_code == 403
    assert db.get_user(sa) is not None

    # La classe de B et ses échéances : ni modifiées ni supprimées
    app_client.post(f"/admin/classes/{cb}/rename", data={"name": "Piratée"})
    app_client.post(f"/admin/classes/{cb}/courses", data={"course_jest": "1"})
    app_client.post(f"/admin/classes/{cb}/code")
    app_client.post(f"/admin/classes/{cb}/remove/{sb}")
    app_client.post(f"/admin/classes/{cb}/members", data={"emails": "ada@lab.test"})
    app_client.post(f"/admin/classes/{cb}/deadlines", data={"course": "linux", "step": "2", "due_date": later})
    app_client.post(f"/admin/classes/{cb}/deadlines/delete", data={"course": "linux", "step": "1"})
    r = app_client.post(f"/admin/classes/{cb}/delete", follow_redirects=False)
    assert "err=" in r.headers["location"]
    after_b = [c for c in db.list_classes() if c["id"] == cb][0]
    assert after_b == before_b and db.list_deadlines()[cb] == deadlines_b
    # Ajout à sa classe : une case forgée vers l'étudiant de B est ignorée, un compte du personnel est introuvable
    app_client.post(f"/admin/classes/{ca}/members", data={"user_ids": str(sb), "emails": "barbara@lab.test"})
    assert db.class_member_ids(ca) == {sa}

    # Flux en direct : l'événement d'un étudiant de B n'arrive pas chez A
    token_a = app_client.cookies.get("session")
    assert [e for e in live_events(token_a, [sb, sa]) if e.get("user_id") == sb] == []
    assert [e["user_id"] for e in live_events(token_a, [sb, sa]) if e.get("type") == "progress"] == [sa]

    # L'administrateur voit tout, et lui seul supprime un étudiant
    admin_client(app_client)
    dash = app_client.get("/dashboard?course=linux").text
    assert "ada@lab.test" in dash and "bob@lab.test" in dash
    assert "2 étudiant(s) pris en compte" in app_client.get("/admin/stats?course=linux").text
    assert app_client.get(f"/admin/terminal/{sb}?course=linux").status_code == 200
    events = live_events(app_client.cookies.get("session"), [sb, sa])
    assert {e["user_id"] for e in events if e.get("type") == "progress"} == {sa, sb}
    assert "Barbara Liskov" in app_client.get("/admin/classes").text
    assert app_client.post(f"/admin/delete-user/{sb}", follow_redirects=False).status_code == 302
    assert db.get_user(sb) is None


class FakeRequest:
    """Requête minimale pour appeler directement la route du flux SSE (le client de test n'arrête pas un flux infini)."""

    def __init__(self, token):
        self.cookies = {"session": token}

    async def is_disconnected(self):
        return False


def live_events(token, publish_for) -> list:
    """Ouvre /api/admin/live avec cette session : présence de chaque étudiant de publish_for dans l'instantané,
    puis un événement de progression pour chacun ; retourne les entrées de l'instantané et les événements reçus."""
    from app import live

    async def scenario():
        previous = live._loop
        live.attach_loop(asyncio.get_running_loop())
        live.presence.clear()
        try:
            for uid in publish_for:
                live.touch(uid, "linux", step=1, force=True)
            response = await main.admin_live(FakeRequest(token))
            stream = response.body_iterator
            received = [await stream.__anext__()]  # instantané
            for uid in publish_for:
                live.publish({"type": "progress", "user_id": uid, "course": "linux", "step": 1})
            live.publish({"type": "fin", "user_id": publish_for[-1]})  # marqueur de fin (étudiant visible)
            while True:
                chunk = await asyncio.wait_for(stream.__anext__(), timeout=5)
                received.append(chunk)
                if chunk.startswith("event: fin"):
                    break
            await stream.aclose()
        finally:
            live._loop = previous
            live.presence.clear()
        out = []
        for chunk in received:
            data = json.loads(chunk.split("data: ", 1)[1])
            out += data["entries"] if data.get("type") == "snapshot" else [data]
        return out

    return asyncio.run(scenario())


def test_migration_depuis_l_ancien_schema(tmp_path, monkeypatch):
    path = tmp_path / "ancienne.db"
    monkeypatch.setattr(db, "DB_PATH", str(path))
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_seen TIMESTAMP);
        CREATE TABLE classes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, code TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE class_members (class_id INTEGER NOT NULL, user_id INTEGER NOT NULL, PRIMARY KEY (class_id, user_id));
        CREATE TABLE class_courses (class_id INTEGER NOT NULL, course_key TEXT NOT NULL, PRIMARY KEY (class_id, course_key));
        CREATE TABLE deadlines (class_id INTEGER NOT NULL, course_key TEXT NOT NULL, step INTEGER NOT NULL,
            due_date TEXT NOT NULL, PRIMARY KEY (class_id, course_key, step));
        CREATE TABLE progress (user_id INTEGER NOT NULL, exercise_id TEXT NOT NULL, points INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, exercise_id));
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO users (id, first_name, last_name, email, password_hash, is_admin) VALUES
            (1, 'Prof', 'Lab', 'prof@lab.test', 'x:y', 1), (2, 'Ada', 'Lovelace', 'ada@lab.test', 'x:y', 0),
            (3, 'Alan', 'Turing', 'alan@lab.test', 'x:y', 1), (4, 'Grace', 'Hopper', 'grace@lab.test', 'x:y', 1);
        INSERT INTO classes (id, name, code, created_at) VALUES (3, 'BTS SIO 1', 'ABC-DEF', '2025-09-01 08:00:00'),
            (5, 'BTS SIO 2', 'GHJ-KLM', '2025-09-02 08:00:00');
        UPDATE sqlite_sequence SET seq = 7 WHERE name = 'classes';
        INSERT INTO class_members VALUES (3, 2), (5, 2);
        INSERT INTO class_courses VALUES (3, 'linux'), (5, 'docker');
        INSERT INTO deadlines VALUES (3, 'linux', 1, '2026-10-15');
        INSERT INTO meta VALUES ('classes_migrated', '1'), ('sessions_hashed', '1');
    """)
    conn.executemany("INSERT INTO meta VALUES (?, ?)", [(c["meta_key"], c["version"]) for c in COURSES.values()])
    conn.execute("INSERT INTO progress (user_id, exercise_id, points) VALUES (2, ?, 3)", (FIRST,))
    conn.commit()
    conn.close()

    for _ in range(2):  # migration idempotente : un second démarrage ne change rien
        db.init_db(list(COURSES.values()))
        classes = {c["id"]: c for c in db.list_classes()}
        assert {i: (c["name"], c["code"], c["owner_id"], c["created_at"]) for i, c in classes.items()} == {
            3: ("BTS SIO 1", "ABC-DEF", 1, "2025-09-01 08:00:00"), 5: ("BTS SIO 2", "GHJ-KLM", 1, "2025-09-02 08:00:00")}
        assert classes[3]["courses"] == ["linux"] and [m["id"] for m in classes[3]["members"]] == [2]
        assert db.list_deadlines() == {3: [{"class_id": 3, "course_key": "linux", "step": 1, "due_date": "2026-10-15"}]}
        assert db.get_user_score(2, LINUX["id_glob"])["score"] == 3
        assert db.get_user_courses(2) == {"linux", "docker"}
        assert db.get_user(1)["is_superadmin"] == 1 and db.get_user(3)["is_superadmin"] == 0
        assert db.get_user(3)["disabled"] == 0
    # Nom unique par propriétaire seulement ; le compteur d'identifiants ne recule pas
    new_a = db.create_class("BTS SIO 1", 3)
    assert new_a and new_a > 7
    assert db.create_class("BTS SIO 1", 4)
    assert db.create_class("BTS SIO 1", 3) is None and db.create_class("BTS SIO 1", 1) is None
    assert db.class_owner(new_a) == 3 and db.owner_student_ids(3) == set()


def test_compte_desactive_et_administrateur_protege(app_client):
    tid = make_teacher(app_client, "alan@lab.test")
    login(app_client, "alan@lab.test", TEACHER_PASSWORD)
    token = app_client.cookies.get("session")
    assert db.get_session(token)
    admin_client(app_client)
    app_client.post(f"/admin/enseignants/{tid}/disable")
    assert db.get_user(tid)["disabled"] == 1
    assert db.get_session(token) is None  # session existante coupée
    app_client.cookies.clear()
    app_client.cookies.set("session", token)
    assert app_client.get("/dashboard", follow_redirects=False).headers["location"] == "/login"
    r = login(app_client, "alan@lab.test", TEACHER_PASSWORD)
    assert r.status_code == 403 and "désactivé" in r.text and "session" not in r.cookies

    # L'administrateur ne peut être ni désactivé ni supprimé
    admin_client(app_client)
    admin_id = user_id(ADMIN[0])
    r = app_client.post(f"/admin/enseignants/{admin_id}/disable", follow_redirects=False)
    assert "err=" in r.headers["location"]
    app_client.post(f"/admin/enseignants/{admin_id}/delete")
    assert not db.set_disabled(admin_id, True) and not db.delete_teacher(admin_id, admin_id)
    assert db.get_user(admin_id)["disabled"] == 0 and app_client.get("/admin/enseignants").status_code == 200

    app_client.post(f"/admin/enseignants/{tid}/enable")
    assert login(app_client, "alan@lab.test", TEACHER_PASSWORD).status_code == 302
    # Un enseignant ne gère pas les comptes du personnel
    assert app_client.post(f"/admin/enseignants/{admin_id}/disable").status_code == 403
    assert app_client.post(f"/admin/enseignants/{tid}/delete").status_code == 403
    assert db.get_user(tid) is not None


def test_suppression_d_un_enseignant(app_client):
    make_class(app_client, name="BTS SIO 1")  # classe de l'administrateur, même nom que celle de l'enseignant
    tid = make_teacher(app_client, "alan@lab.test")
    cid, sid = teacher_class(app_client, "alan@lab.test", "BTS SIO 1", "ada@lab.test")
    db.add_exercise_completion(sid, FIRST, 3)
    admin_client(app_client)
    page = app_client.get("/admin/enseignants").text
    assert "alan@lab.test" in page and ">Administrateur</span>" in page
    app_client.post(f"/admin/enseignants/{tid}/delete")
    assert db.get_user(tid) is None
    moved = [c for c in db.list_classes() if c["id"] == cid][0]
    assert moved["owner_id"] == user_id(ADMIN[0]) and moved["name"] == "BTS SIO 1 (Alan Turing)"
    assert db.class_member_ids(cid) == {sid} and db.get_user_score(sid, LINUX["id_glob"])["score"] == 3


def test_page_confidentialite(app_client):
    page = app_client.get("/confidentialite")  # page publique, sans connexion
    assert page.status_code == 200
    for attendu in ("Hetzner Online GmbH", "Bauer Baptiste", "CNIL", "120 jours", "session"):
        assert attendu in page.text
    assert 'href="/confidentialite"' in app_client.get("/register").text


def test_contexte_entreprise_dans_chaque_labo():
    # Les labos se suivent dans n'importe quel ordre : chacun présente l'entreprise, Marc et toute l'équipe
    for key, course in COURSES.items():
        lesson = course["steps"][min(course["steps"])]["lesson"]
        assert lesson.startswith('<div class="scenario company">'), key
        assert lesson.count('class="scenario company"') == 1, key
        for nom in ("Cimes &amp; Sentiers", "Marc Dumas", "Sophie Marchand", "Léa Nguyen", "Nadia Haddad",
                    "Thomas Leroy", "Aminata Diallo", "Julien Petit"):
            assert nom in lesson, (key, nom)
        assert ("votre mentore dans ce labo" in lesson) != bool(course.get("exam")), key
    # Aucune autre étape ne la répète
    assert all('class="scenario company"' not in s["lesson"]
               for c in COURSES.values() for n, s in c["steps"].items() if n != min(c["steps"]) and "lesson" in s)


def test_vignettes_des_labos(app_client, tmp_path, monkeypatch):
    admin_client(app_client)
    page = app_client.get("/catalogue").text
    for key in COURSES:
        assert f'src="/static/vignettes/{key}.svg?v=' in page, key
    assert app_client.get("/static/vignettes/linux.svg").status_code == 200
    assert 'id="team-panel"' in app_client.get("/lab/docker").text
    # Une image déposée en .png remplace l'illustration .svg ; sans image, la carte garde un fond neutre
    os.makedirs(tmp_path / "static" / "vignettes")
    (tmp_path / "static" / "vignettes" / "git.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(main, "APP_DIR", str(tmp_path))
    assert main.thumbnail_url("git").startswith("/static/vignettes/git.png?v=")
    assert main.thumbnail_url("linux") is None
    assert 'class="ph"' in app_client.get("/catalogue").text


def test_envoi_d_une_vignette(app_client, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "VIGNETTES_DIR", str(tmp_path / "vignettes"))
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100

    def envoi(data, nom="image.png", key="docker"):
        return app_client.post(f"/admin/vignettes/{key}", files={"image": (nom, data)}, follow_redirects=False)

    # Réservé à l'administrateur (la vignette est commune à toutes les classes)
    student_in_class(app_client)
    assert login(app_client, "ada@lab.test", "motdepasse1").status_code == 302
    assert envoi(png).headers["location"] == "/catalogue" and main.uploaded_thumbnail("docker") is None
    assert "Changer la vignette" not in app_client.get("/catalogue").text

    admin_client(app_client)
    assert "Changer la vignette" in app_client.get("/catalogue").text
    # Formats reconnus à leur signature : pas de SVG (script possible), pas d'image trop lourde
    assert "err=" in envoi(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "x.svg").headers["location"]
    assert "err=" in envoi(b"\xff\xd8\xff" + b"0" * main.VIGNETTE_MAX_BYTES).headers["location"]
    assert "msg=" in envoi(png).headers["location"]
    page = app_client.get("/catalogue").text
    assert 'src="/vignettes/docker.png?v=' in page and "Rétablir" in page
    r = app_client.get("/vignettes/docker.png")
    assert r.status_code == 200 and r.content == png and r.headers["content-type"] == "image/png"
    assert app_client.get("/vignettes/..%2Fplatform.db").status_code == 404
    # Une image d'un autre format remplace la précédente ; « Rétablir » revient à l'illustration fournie
    assert "msg=" in envoi(b"RIFF\0\0\0\0WEBPVP8 ", "a.webp").headers["location"]
    assert sorted(os.listdir(tmp_path / "vignettes")) == ["docker.webp"]
    app_client.post("/admin/vignettes/docker", data={"action": "supprimer"})
    assert main.thumbnail_url("docker").startswith("/static/vignettes/docker.svg")


def test_grade_intrusion_et_reponse_du_collegue(app_client):
    from app import progression
    assert [progression.grade(s, 200)["name"] for s in (0, 29, 30, 80, 140, 180)] == [
        "Recrue", "Recrue", "Opérateur·rice", "Hacker", "Architecte", "Ghost"]
    assert progression.grade(29, 200)["next_points"] == 1 and "next" not in progression.grade(200, 200)
    admin_client(app_client)
    uid = user_id(ADMIN[0])
    seuil = -(-15 * LINUX["max_score"] // 100)
    db.add_exercise_completion(uid, FIRST, seuil)
    p = app_client.get("/api/linux/progress").json()
    assert p["grade"]["name"] == "Opérateur·rice" and p["breach"] == {"core": "Ring 0", "layers": 0, "total": len(LINUX["steps"])}
    # Une couche d'ICE percée par étape entièrement réussie
    for ex in LINUX["steps"][1]["exercises"][1:]:
        db.add_exercise_completion(uid, ex["id"], 1)
    assert app_client.get("/api/linux/progress").json()["breach"]["layers"] == 1
    # Épreuve notée : les couches, pas de grade
    assert "grade" not in app_client.get("/api/projet/progress").json()
    page = app_client.get("/catalogue").text
    assert "Opérateur·rice" in page and "Ring 0" in page
    # Le collègue répond toujours la même chose à un même ticket
    ex = app_client.get("/api/linux/step/1").json()["exercises"][0]
    assert ex["ticket"]["reply"] in progression.REPLIES[LINUX["steps"][1]["exercises"][0]["ticket"]["from"]]
    assert ex["ticket"]["reply"] == app_client.get("/api/linux/step/1").json()["exercises"][0]["ticket"]["reply"]


def test_badges_et_profil(app_client):
    from app import badges
    up = badges.uptime
    assert up([], 20) == {"current": 0, "record": 0, "this_week": False, "pause": 2}
    # Semaine en cours pas encore comptée : la série reste en vie ; deux semaines vides (vacances) ne la cassent pas
    assert up([17, 18, 19], 20) == {"current": 3, "record": 3, "this_week": False, "pause": 2}
    assert up([14, 15, 18, 20], 20)["current"] == 4 and up([14, 15, 18, 20], 20)["this_week"]
    # Trois semaines vides d'affilée la terminent ; le record reste
    assert up([10, 11, 12, 16], 16) == {"current": 1, "record": 3, "this_week": True, "pause": 2}
    assert up([10, 11, 12], 16)["current"] == 0
    uid = student_in_class(app_client)
    b = {x["id"]: x for x in app_client.get("/api/badges").json()["badges"]}
    assert len(b) == len(badges.BADGES) and not any(x["earned"] for x in b.values())
    # Étape 1 de Linux terminée sans indice, plus un exercice réussi après 5 vérifications ratées
    step1 = [ex["id"] for ex in LINUX["steps"][1]["exercises"]]
    for i in step1:
        db.add_exercise_completion(uid, i, 1)
    for _ in range(5):
        db.record_attempt(uid, step1[0], False, "pas encore")
    b = {x["id"]: x for x in app_client.get("/api/badges").json()["badges"]}
    assert b["premier-ticket"]["earned"] and b["sans-filet"]["earned"] and b["perseverant"]["earned"]
    assert not b["autonome"]["earned"] and b["autonome"]["value"] == len(step1)
    assert b["polyvalent"]["value"] == 1 and b["regulier"]["value"] == 1
    u = app_client.get("/api/badges").json()["uptime"]
    assert u["current"] == 1 and u["this_week"]
    assert "✓ prolongé cette semaine" in app_client.get("/catalogue").text
    # Un indice demandé dans l'étape : plus « sans filet »
    db.use_hint(uid, step1[1], 3)
    assert not {x["id"]: x for x in badges.compute(uid)}["sans-filet"]["earned"]
    page = app_client.get("/profil").text
    assert "Hello, world" in page and "Brute force" in page and "Ring 0" in page
    # Un étudiant ne voit pas le profil d'un autre ; l'enseignant de sa classe, si
    assert app_client.get(f"/profil/{uid}", follow_redirects=False).status_code == 302
    admin_client(app_client)
    assert "Vue enseignant" in app_client.get(f"/profil/{uid}").text
    assert f'href="/profil/{uid}"' in app_client.get("/dashboard?course=linux").text


def test_objectif_de_classe(app_client):
    from app import objectif
    admin_client(app_client)
    cid, code = make_class(app_client, courses=("linux", "projet"))
    assert objectif.compute(cid, ["linux", "projet"]) is None  # aucun étudiant
    for email in ("ada@lab.test", "alan@lab.test"):
        assert register(app_client, email=email, code=code).status_code == 302
    ada, alan = user_id("ada@lab.test"), user_id("alan@lab.test")
    g = objectif.compute(cid, ["linux", "projet"], ada)
    # Potentiel : 2 étudiants × exercices de Linux (l'épreuve notée ne compte pas)
    assert g["potential"] == 2 * LINUX["total_exercises"] and g["total"] == 0 and g["reached"] == 0
    premier = g["tiers"][0]["target"]
    ids = [ex["id"] for s in LINUX["steps"].values() for ex in s["exercises"]]
    for i in ids[:premier - 1]:
        db.add_exercise_completion(ada, i, 1)
    db.add_exercise_completion(alan, ids[0], 1)
    db.add_exercise_completion(alan, COURSES["projet"]["steps"][1]["exercises"][0]["id"], 1)  # ne compte pas
    g = objectif.compute(cid, ["linux", "projet"], ada)
    assert g["total"] == premier and g["reached"] == 1 and g["mine"] == premier - 1
    assert g["week"] == premier and g["active"] == 2 and g["message"] == objectif.PALIERS[0][1]
    # L'étudiant voit l'objectif de sa classe dans son catalogue, l'enseignant sur la page des classes
    login(app_client, "ada@lab.test", "motdepasse1")
    page = app_client.get("/catalogue").text
    assert "Objectif de classe" in page and f"dont <b>{premier - 1}</b> par vous" in page
    admin_client(app_client)
    assert "Objectif de classe" in app_client.get("/admin/classes").text
