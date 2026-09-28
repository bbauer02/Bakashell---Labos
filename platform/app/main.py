"""Linux Lab Platform — FastAPI : comptes, parcours, conteneurs par étudiant, terminal, éditeur, validation."""
import asyncio
import base64
import json
import logging
import os
import posixpath
import re
import threading
import time
from collections import defaultdict
from urllib.parse import quote_plus

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from . import containers
from . import database as db
from . import live
from . import memo
from . import runner
from . import solutions
from .courses import COURSES, DEFAULT_COURSE, EXERCISE_INDEX, get_course, get_exercise
from .scenario import CHARACTERS

log = logging.getLogger("linux-lab")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Linux CLI Lab")
templates = Jinja2Templates(directory="/app/templates")

IDLE_TIMEOUT = int(os.environ.get("IDLE_TIMEOUT", "7200"))  # secondes avant d'arrêter un conteneur inactif
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
STARTED_AT = time.time()
MAX_FILE_BYTES = 256 * 1024

# Activité des étudiants (en mémoire) pour l'arrêt des conteneurs inactifs ; clés (user_id, parcours)
last_activity: dict = {}
open_terminals: dict = defaultdict(int)

# Un verrou par étudiant et par parcours : évite deux mises en place simultanées
_locks: dict = {}
_locks_guard = threading.Lock()


def user_lock(user_id: int, course_key: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault((user_id, course_key), threading.Lock())


def mark_active(user_id: int, course_key: str, step: int = None):
    last_activity[(user_id, course_key)] = time.time()
    live.touch(user_id, course_key, step=step)


@app.on_event("startup")
async def startup():
    live.attach_loop(asyncio.get_running_loop())
    solutions.check_coverage(COURSES)
    memo.check(COURSES, EXERCISE_INDEX)
    for key in db.init_db(list(COURSES.values())):
        log.warning("Parcours %s : nouvelle version du catalogue, l'ancienne progression a été archivée.", key)
    asyncio.create_task(idle_reaper())


async def idle_reaper():
    while True:
        await asyncio.sleep(300)
        try:
            active = {key for key, n in open_terminals.items() if n > 0}
            stopped = await run_in_threadpool(
                containers.stop_idle_containers, last_activity, active, IDLE_TIMEOUT, STARTED_AT
            )
            for name in stopped:
                log.info("Conteneur inactif arrêté : %s", name)
        except Exception:
            log.exception("Erreur lors de l'arrêt des conteneurs inactifs")


# ─── Auth ───────────────────────────────────────────────────────────────

def get_current_user(request: Request):
    return db.get_session(request.cookies.get("session"))


def set_session_cookie(response, token: str):
    response.set_cookie("session", token, httponly=True, samesite="lax", secure=COOKIE_SECURE,
                        max_age=db.SESSION_HOURS * 3600)


def accessible_keys(user) -> list:
    """Parcours ouverts à l'utilisateur : tous pour un admin, sinon ceux de ses classes."""
    if user.get("is_admin"):
        return list(COURSES)
    allowed = db.get_user_courses(user["user_id"])
    return [k for k in COURSES if k in allowed]


def course_for(user, course_key: str):
    """Le parcours demandé, si l'utilisateur y a accès ; sinon None."""
    course = get_course(course_key)
    if not course or not user:
        return None
    if user.get("is_admin") or course_key in db.get_user_courses(user["user_id"]):
        return course
    return None


def courses_menu(user=None):
    keys = accessible_keys(user) if user else list(COURSES)
    return [{"key": k, "title": COURSES[k]["title"], "short": COURSES[k]["short"]} for k in keys]


# ─── Pages ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return RedirectResponse("/catalogue" if get_current_user(request) else "/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    user = await run_in_threadpool(db.authenticate, form.get("email", ""), form.get("password", ""))
    if not user:
        return templates.TemplateResponse(request, "login.html", {"error": "Email ou mot de passe incorrect."})
    response = RedirectResponse("/catalogue", status_code=302)
    set_session_cookie(response, db.create_session(user["id"]))
    return response


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None, "form": {}})


@app.post("/register")
async def register_submit(request: Request):
    form = await request.form()
    first_name = form.get("first_name", "").strip()
    last_name = form.get("last_name", "").strip()
    email = form.get("email", "").strip()
    password = form.get("password", "")
    password2 = form.get("password2", "")
    class_code = form.get("class_code", "").strip()

    def error(msg):
        return templates.TemplateResponse(request, "register.html", {"error": msg, "form": dict(form)})

    if not all([first_name, last_name, email, password]):
        return error("Tous les champs sont obligatoires.")
    if password != password2:
        return error("Les mots de passe ne correspondent pas.")
    if len(password) < 8:
        return error("Mot de passe trop court (8 caractères minimum).")
    if class_code and not db.class_exists_for_code(class_code):
        return error("Ce code de classe n'existe pas : vérifiez-le auprès de votre enseignant·e.")

    user_id = await run_in_threadpool(db.create_user, first_name, last_name, email, password)
    if not user_id:
        return error("Un compte existe déjà avec cet email.")
    if class_code:
        db.join_class_by_code(user_id, class_code)

    response = RedirectResponse("/catalogue", status_code=302)
    set_session_cookie(response, db.create_session(user_id))
    return response


@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session")
    if token:
        db.delete_session(token)
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("session")
    return response


@app.get("/lab", response_class=HTMLResponse)
async def lab_default(request: Request):
    return RedirectResponse("/catalogue", status_code=302)


@app.get("/catalogue", response_class=HTMLResponse)
async def catalogue(request: Request, msg: str = "", err: str = ""):
    """Page d'accueil : les labos auxquels l'étudiant a accès, avec sa progression."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    cards = []
    for key in accessible_keys(user):
        c = COURSES[key]
        p = db.get_user_score(user["user_id"], c["id_glob"])
        done = len(p["completed"])
        memo_found, memo_total = memo.counts(key, p["completed"])
        cards.append({
            "memo_found": memo_found, "memo_total": memo_total,
            "key": key, "title": c["title"], "summary": c["summary"], "level": c["level"],
            "duration": c["duration"], "steps": len(c["steps"]), "total": c["total_exercises"],
            "score": p["score"], "max": c["max_score"], "done": done,
            "pct": round(100 * p["score"] / c["max_score"]) if c["max_score"] else 0,
        })
    return templates.TemplateResponse(request, "catalogue.html", {
        "user": user, "cards": cards, "classes": db.get_user_classes(user["user_id"]), "msg": msg, "err": err,
    })


@app.post("/catalogue/rejoindre")
async def catalogue_join(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    name = db.join_class_by_code(user["user_id"], form.get("code", ""))
    if not name:
        return RedirectResponse("/catalogue?err=Code+de+classe+inconnu", status_code=302)
    return RedirectResponse(f"/catalogue?msg=Vous+avez+rejoint+la+classe+{quote_plus(name)}", status_code=302)


@app.get("/lab/{course_key}", response_class=HTMLResponse)
async def lab_page(request: Request, course_key: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    course = course_for(user, course_key)
    if not course:
        return RedirectResponse("/catalogue?err=Ce+labo+ne+vous+est+pas+ouvert", status_code=302)
    return templates.TemplateResponse(request, "lab.html", {
        "user": user,
        "course": {"key": course["key"], "title": course["title"], "short": course["short"],
                   "editor": bool(course["editor_root"]), "auto_validate": course["auto_validate"]},
        "courses": courses_menu(user),
    })


# ─── Tableau de bord enseignant ─────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, course: str = DEFAULT_COURSE, classe: int = 0):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.get("is_admin"):
        return RedirectResponse("/catalogue", status_code=302)
    c = get_course(course) or COURSES[DEFAULT_COURSE]
    step_of = {ex["id"]: n for n, s in c["steps"].items() for ex in s["exercises"]}
    students = await run_in_threadpool(db.get_all_students, c, step_of)
    classes = db.list_classes()
    if classe:
        members = db.class_member_ids(classe)
        students = [s for s in students if s["id"] in members]
    container_list = await run_in_threadpool(containers.list_student_containers)
    course_containers = [x for x in container_list if x["course"] == c["key"]]
    steps = [{"num": n, "title": s["title"], "total": len(s["exercises"])} for n, s in c["steps"].items()]
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "course": c,
        "courses": courses_menu(),
        "students": students,
        "containers": course_containers,
        "running": sum(1 for x in course_containers if x["status"] == "running"),
        "steps": steps,
        "max_score": c["max_score"],
        "total_exercises": c["total_exercises"],
        "courses_meta": {k: {"short": v["short"], "steps": {n: s["title"] for n, s in v["steps"].items()}}
                         for k, v in COURSES.items()},
        "classes": classes,
        "classe": classe,
    })


# ─── Classes (admin) ────────────────────────────────────────────────────

def admin_or_none(request: Request):
    user = get_current_user(request)
    return user if user and user.get("is_admin") else None


def back_to_classes(msg: str = "", anchor: str = "", err: bool = False):
    key = "err" if err else "msg"
    query = f"?{key}={quote_plus(msg)}" if msg else ""
    return RedirectResponse(f"/admin/classes{query}{anchor}", status_code=302)


@app.get("/admin/classes", response_class=HTMLResponse)
async def admin_classes(request: Request, msg: str = "", err: str = ""):
    user = admin_or_none(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "admin_classes.html", {
        "user": user, "classes": db.list_classes(), "students": db.list_students(),
        "all_courses": [{"key": k, "title": c["title"], "short": c["short"]} for k, c in COURSES.items()],
        "msg": msg, "err": err,
    })


@app.post("/admin/classes")
async def admin_class_create(request: Request):
    if not admin_or_none(request):
        return RedirectResponse("/login", status_code=302)
    name = (await request.form()).get("name", "").strip()
    if not name:
        return back_to_classes("Donnez un nom à la classe.", err=True)
    class_id = db.create_class(name)
    if not class_id:
        return back_to_classes(f"Une classe « {name} » existe déjà.", err=True)
    return back_to_classes(f"Classe « {name} » créée.", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/courses")
async def admin_class_courses(request: Request, class_id: int):
    if not admin_or_none(request):
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    keys = [k for k in COURSES if form.get(f"course_{k}")]
    db.set_class_courses(class_id, keys)
    return back_to_classes("Labos de la classe mis à jour.", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/members")
async def admin_class_add_members(request: Request, class_id: int):
    if not admin_or_none(request):
        return RedirectResponse("/login", status_code=302)
    ids = [int(v) for v in (await request.form()).getlist("user_ids") if str(v).isdigit()]
    db.add_members(class_id, ids)
    return back_to_classes(f"{len(ids)} étudiant(s) ajouté(s).", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/remove/{user_id}")
async def admin_class_remove_member(request: Request, class_id: int, user_id: int):
    if not admin_or_none(request):
        return RedirectResponse("/login", status_code=302)
    db.remove_member(class_id, user_id)
    return back_to_classes("Étudiant retiré de la classe.", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/rename")
async def admin_class_rename(request: Request, class_id: int):
    if not admin_or_none(request):
        return RedirectResponse("/login", status_code=302)
    name = (await request.form()).get("name", "").strip()
    if not name or not db.rename_class(class_id, name):
        return back_to_classes("Nom vide ou déjà utilisé.", f"#classe-{class_id}", err=True)
    return back_to_classes("Classe renommée.", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/code")
async def admin_class_new_code(request: Request, class_id: int):
    if not admin_or_none(request):
        return RedirectResponse("/login", status_code=302)
    db.regenerate_code(class_id)
    return back_to_classes("Nouveau code généré (l'ancien ne fonctionne plus).", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/delete")
async def admin_class_delete(request: Request, class_id: int):
    if not admin_or_none(request):
        return RedirectResponse("/login", status_code=302)
    db.delete_class(class_id)
    return back_to_classes("Classe supprimée (les comptes et leur progression sont conservés).")


@app.get("/api/admin/live")
async def admin_live(request: Request):
    """Flux temps réel (Server-Sent Events) pour le tableau de bord."""
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return unauthorized()
    return StreamingResponse(live.stream(request.is_disconnected), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/admin/delete-user/{user_id}")
async def admin_delete_user(request: Request, user_id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    await run_in_threadpool(containers.remove_container, user_id)
    db.delete_user(user_id)
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/admin/reset-user/{user_id}")
async def admin_reset_user(request: Request, user_id: int, course: str = DEFAULT_COURSE):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    c = get_course(course) or COURSES[DEFAULT_COURSE]
    db.reset_user_progress(user_id, c)
    await run_in_threadpool(containers.remove_container, user_id, c)
    return RedirectResponse(f"/dashboard?course={c['key']}", status_code=302)


# ─── Mise en place et validation (fonctions bloquantes, exécutées en thread) ──

def ensure_setup(user_id: int, course: dict, container_id: str, step_num: int, force: bool = False) -> dict:
    """Prépare l'étape dans le conteneur (une fois) et retourne ses données attendues."""
    step = course["steps"][step_num]
    if not runner.has_setup(step):
        return {}
    with user_lock(user_id, course["key"]):
        if not force:
            code, _ = containers.exec_in_container(container_id, runner.marker_test_command(step_num, step))
            if code == 0:
                data = db.get_setup(user_id, course["key"], step_num)
                if data is not None:
                    return data
        code, out = containers.exec_in_container(container_id, runner.setup_command(course, step_num, step))
        data = runner.parse_setup_output(out)
        if code != 0:
            log.error("Échec de la mise en place %s/%s (étudiant %s, code %s) :\n%s",
                      course["key"], step_num, user_id, code, out[-2000:])
        db.save_setup(user_id, course["key"], step_num, data)
        return data


def prepare_step(user_id: int, course: dict, step_num: int):
    container_id = containers.get_or_create_container(user_id, course)
    ensure_setup(user_id, course, container_id, step_num)


def validate_step(user_id: int, course: dict, step_num: int, auto: bool, only: str = "") -> dict:
    """Vérifie les exercices de l'étape (ou seulement « only », un identifiant d'exercice)."""
    newly_passed = []
    step = course["steps"][step_num]
    container_id = containers.get_or_create_container(user_id, course)
    env = runner.check_env(ensure_setup(user_id, course, container_id, step_num))
    progress = db.get_user_score(user_id, course["id_glob"])
    hints = db.get_hints_used(user_id)

    results = []
    for ex in step["exercises"]:
        if only and ex["id"] != only:
            continue
        res = {"id": ex["id"], "title": ex["title"], "points": ex["points"],
               "passed": False, "already": False, "skipped": False, "message": None, "earned": 0}
        if ex["id"] in progress["completed"]:
            res.update(passed=True, already=True, earned=progress["earned"][ex["id"]])
        elif auto and ex.get("manual"):
            res.update(skipped=True)
        else:
            code, out = containers.exec_in_container(container_id, runner.check_command(course, ex), env=env)
            passed, message = runner.parse_check_output(ex, code, out)
            if passed:
                earned = max(1, ex["points"] - hints.get(ex["id"], 0))
                if db.add_exercise_completion(user_id, ex["id"], earned):
                    newly_passed.append((ex, earned))
                res.update(passed=True, earned=earned)
            else:
                res["message"] = message
        results.append(res)

    payload = progress_payload(user_id, course)
    payload["discoveries"] = memo.discoveries(course["key"], progress["completed"], payload["completed"])
    remaining = [r for r in results if not r["passed"]]
    left_in_step = sum(1 for ex in step["exercises"] if ex["id"] not in payload["completed"])
    if not auto and not newly_passed and remaining:
        count = live.stalled(user_id, course["key"], step_num)
        live.publish({"type": "attempt", "user_id": user_id, "name": live.names.get(user_id),
                      "course": course["key"], "step": step_num, "count": count, "remaining": left_in_step})
    if newly_passed:
        live.progressed(user_id, course["key"], step_num)
    for ex, earned in newly_passed:
        live.publish({"type": "progress", "user_id": user_id, "name": live.names.get(user_id),
                      "course": course["key"], "step": step_num, "exercise": ex["id"], "title": ex["title"],
                      "earned": earned, "score": payload["score"], "done": len(payload["completed"])})
    return {"validation": {"step": step_num, "results": results}, "progress": payload}


def progress_payload(user_id: int, course: dict) -> dict:
    p = db.get_user_score(user_id, course["id_glob"])
    return {"score": p["score"], "completed": p["completed"],
            "max_score": course["max_score"], "total_exercises": course["total_exercises"]}


# ─── API ────────────────────────────────────────────────────────────────

def unauthorized():
    return JSONResponse({"error": "unauthorized"}, status_code=401)


def not_found(what="not found"):
    return JSONResponse({"error": what}, status_code=404)


@app.get("/api/{course_key}/steps")
async def api_steps(request: Request, course_key: str):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    if not course:
        return not_found()
    progress = db.get_user_score(user["user_id"], course["id_glob"])
    return [{
        "num": num,
        "title": step["title"],
        "description": step["description"],
        "total": len(step["exercises"]),
        "completed": sum(1 for ex in step["exercises"] if ex["id"] in progress["completed"]),
    } for num, step in course["steps"].items()]


def ticket_payload(ex: dict):
    ticket = ex.get("ticket")
    if not ticket:
        return None
    _, step, pos, _ = get_exercise(ex["id"])
    person = CHARACTERS[ticket["from"]]
    return {
        "num": 1000 + step * 10 + pos,
        "from": person["name"],
        "role": person["role"],
        "color": person["color"],
        "initials": "".join(w[0] for w in person["name"].split()[:2]),
        "body": ticket["body"],
    }


def exercise_payload(ex: dict, progress: dict, hints: dict) -> dict:
    used = hints.get(ex["id"], 0)
    all_hints = ex.get("hints", [])
    return {
        "ticket": ticket_payload(ex),
        "id": ex["id"],
        "points": ex["points"],
        "title": ex["title"],
        "desc": ex["desc"],
        "manual": bool(ex.get("manual")),
        "completed": ex["id"] in progress["completed"],
        "earned": progress["earned"].get(ex["id"]),
        "hints": all_hints[:used],
        "hints_total": len(all_hints),
    }


@app.get("/api/{course_key}/step/{num}")
async def api_step(request: Request, course_key: str, num: int):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    step = course["steps"].get(num) if course else None
    if not step:
        return not_found()
    live.remember_name(user)
    mark_active(user["user_id"], course["key"], step=num)
    # Le contenu s'affiche tout de suite ; l'environnement est préparé par /prepare (appelé juste après)
    progress = db.get_user_score(user["user_id"], course["id_glob"])
    hints = db.get_hints_used(user["user_id"])
    return {
        "num": num,
        "title": step["title"],
        "description": step["description"],
        "lesson": step.get("lesson", ""),
        "has_setup": runner.has_setup(step),
        "mentor": CHARACTERS[course["mentor"]]["name"].split()[0],
        "exercises": [exercise_payload(ex, progress, hints) for ex in step["exercises"]],
    }


@app.post("/api/{course_key}/prepare/{num}")
async def api_prepare(request: Request, course_key: str, num: int):
    """Crée le conteneur si besoin et prépare l'étape (fichiers, processus…). Peut prendre
    quelques secondes (premier démarrage du parcours Docker : environ 10 s)."""
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    if not course or num not in course["steps"]:
        return not_found()
    try:
        await run_in_threadpool(prepare_step, user["user_id"], course, num)
    except Exception:
        log.exception("Préparation de l'étape %s/%s impossible", course_key, num)
        return JSONResponse({"error": "La préparation de l'environnement a échoué, réessayez."}, status_code=500)
    return {"status": "ok"}


@app.post("/api/{course_key}/ping")
async def api_ping(request: Request, course_key: str):
    """Signal d'activité (frappe dans l'éditeur), limité côté page à un appel toutes les 20 s."""
    user = get_current_user(request)
    course = course_for(user, course_key)
    if not user or not course:
        return unauthorized()
    live.remember_name(user)
    mark_active(user["user_id"], course["key"])
    return {"status": "ok"}


@app.post("/api/{course_key}/validate/{num}")
async def api_validate(request: Request, course_key: str, num: int, auto: bool = False, exercise: str = ""):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    if not course or num not in course["steps"]:
        return not_found()
    live.remember_name(user)
    if not auto:
        mark_active(user["user_id"], course["key"], step=num)
        db.touch_user(user["user_id"])
    if exercise and exercise not in {ex["id"] for ex in course["steps"][num]["exercises"]}:
        return not_found()
    return await run_in_threadpool(validate_step, user["user_id"], course, num, auto, exercise)


@app.post("/api/hint/{exercise_id}")
async def api_hint(request: Request, exercise_id: str):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course_key, _, _, ex = get_exercise(exercise_id)
    if not ex or not ex.get("hints") or not course_for(user, course_key):
        return not_found()
    count = db.use_hint(user["user_id"], exercise_id, len(ex["hints"]))
    course_key, step_num, _, _ = get_exercise(exercise_id)
    live.remember_name(user)
    live.publish({"type": "hint", "user_id": user["user_id"], "name": live.names.get(user["user_id"]),
                  "course": course_key, "step": step_num, "exercise": exercise_id, "title": ex["title"], "count": count})
    return {"hints": ex["hints"][:count], "hints_total": len(ex["hints"])}


@app.get("/api/{course_key}/memo")
async def api_memo(request: Request, course_key: str):
    """Mémo des commandes du parcours : fiches débloquées par les exercices réussis."""
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    if not course:
        return not_found()
    progress = db.get_user_score(user["user_id"], course["id_glob"])
    return memo.build(course, progress["completed"], full_access=bool(user.get("is_admin")))


@app.get("/api/solution/{exercise_id}")
async def api_solution(request: Request, exercise_id: str):
    """Correction d'un exercice : réservée aux comptes admin."""
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return JSONResponse({"error": "Réservé aux enseignants"}, status_code=403)
    _, _, _, ex = get_exercise(exercise_id)
    sol = solutions.for_exercise(exercise_id)
    if not ex or not sol:
        return not_found()
    return {
        "exercise": exercise_id,
        "preamble": sol["preamble"],
        "code": sol["code"],
        "checks": [message for _cmd, message in ex["checks"]],
        "hints": ex.get("hints", []),
        "manual": bool(ex.get("manual")),
    }


@app.post("/api/{course_key}/reset-step/{num}")
async def api_reset_step(request: Request, course_key: str, num: int):
    """Rejoue la mise en place de l'étape (fichiers fournis, processus…), sans toucher au score."""
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    if not course or num not in course["steps"]:
        return not_found()

    def reset():
        container_id = containers.get_or_create_container(user["user_id"], course)
        ensure_setup(user["user_id"], course, container_id, num, force=True)

    await run_in_threadpool(reset)
    return {"status": "ok"}


@app.get("/api/{course_key}/progress")
async def api_progress(request: Request, course_key: str):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    if not course:
        return not_found()
    return progress_payload(user["user_id"], course)


@app.post("/api/{course_key}/reset")
async def api_reset(request: Request, course_key: str):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    if not course:
        return not_found()
    db.reset_user_progress(user["user_id"], course)
    await run_in_threadpool(containers.remove_container, user["user_id"], course)
    return {"status": "ok"}


# ─── Éditeur de fichiers (parcours avec editor_root) ────────────────────

_SAFE_PATH = re.compile(r"^[A-Za-z0-9_.\-/]+$")


def resolve_path(course: dict, rel: str):
    """Chemin absolu sûr dans le dossier du projet, ou None."""
    root = course["editor_root"]
    if not root or not rel or rel.startswith("/") or not _SAFE_PATH.match(rel):
        return None
    if any(part in ("", ".", "..") for part in rel.split("/")):
        return None
    full = posixpath.normpath(posixpath.join(root, rel))
    return full if full.startswith(root + "/") else None


def editor_course(user, course_key: str):
    course = course_for(user, course_key)
    return course if course and course["editor_root"] else None


@app.get("/api/{course_key}/files")
async def api_files(request: Request, course_key: str):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = editor_course(user, course_key)
    if not course:
        return not_found()
    root = course["editor_root"]
    script = ('cd "$1" 2>/dev/null || exit 0; find . \\( -name node_modules -o -name coverage -o -name .git \\) -prune '
              '-o -type f -size -256k -print | sed "s|^\\./||" | sort')

    def listing():
        container_id = containers.get_or_create_container(user["user_id"], course)
        return containers.exec_in_container(container_id, ["bash", "-c", script, "_", root], user="etudiant")

    code, out = await run_in_threadpool(listing)
    return {"root": root, "files": [f for f in out.splitlines() if f and _SAFE_PATH.match(f)]}


@app.get("/api/{course_key}/file")
async def api_file_read(request: Request, course_key: str, path: str):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = editor_course(user, course_key)
    full = resolve_path(course, path) if course else None
    if not full:
        return JSONResponse({"error": "Chemin invalide"}, status_code=400)

    def read():
        container_id = containers.get_or_create_container(user["user_id"], course)
        return containers.exec_in_container(
            container_id, ["bash", "-c", 'test -f "$1" && [ $(stat -c %s "$1") -le 262144 ] && base64 -w0 -- "$1"', "_", full],
            user="etudiant")

    code, out = await run_in_threadpool(read)
    if code != 0:
        return JSONResponse({"error": "Fichier introuvable ou trop volumineux"}, status_code=404)
    try:
        content = base64.b64decode(out).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return JSONResponse({"error": "Fichier binaire : ouvrez-le dans le terminal"}, status_code=415)
    return {"path": path, "content": content}


@app.put("/api/{course_key}/file")
async def api_file_write(request: Request, course_key: str):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = editor_course(user, course_key)
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Requête invalide"}, status_code=400)
    path, content = payload.get("path", ""), payload.get("content", "")
    full = resolve_path(course, path) if course else None
    if not full or not isinstance(content, str):
        return JSONResponse({"error": "Chemin invalide"}, status_code=400)
    data = content.encode("utf-8")
    if len(data) > MAX_FILE_BYTES:
        return JSONResponse({"error": "Fichier trop volumineux (256 Ko maximum)"}, status_code=413)
    mark_active(user["user_id"], course["key"])

    def write():
        container_id = containers.get_or_create_container(user["user_id"], course)
        return containers.exec_in_container(
            container_id,
            ["bash", "-c", 'mkdir -p "$(dirname "$2")" && printf %s "$1" | base64 -d > "$2"', "_",
             base64.b64encode(data).decode(), full],
            user="etudiant")

    code, out = await run_in_threadpool(write)
    if code != 0:
        return JSONResponse({"error": "Écriture impossible : " + out.strip()[:200]}, status_code=500)
    return {"status": "ok", "path": path}


# ─── Terminal WebSocket ─────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_terminal(ws: WebSocket):
    token = ws.cookies.get("session")
    user = db.get_session(token) if token else None
    course = course_for(user, ws.query_params.get("course", DEFAULT_COURSE))
    if not user or not course:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()
    user_id = user["user_id"]
    key = (user_id, course["key"])
    mark_active(user_id, course["key"])

    try:
        container_id = await run_in_threadpool(containers.get_or_create_container, user_id, course)
        exec_id, sock = await run_in_threadpool(containers.create_exec_stream, container_id)
    except Exception as e:
        log.exception("Ouverture du terminal impossible")
        await ws.send_text(json.dumps({"error": str(e)}))
        await ws.close()
        return

    open_terminals[key] += 1
    live.remember_name(user)
    live.terminal_opened(user_id, course["key"])
    raw_sock = sock._sock
    raw_sock.setblocking(False)
    loop = asyncio.get_running_loop()

    async def read_from_container():
        try:
            while True:
                data = await loop.sock_recv(raw_sock, 4096)
                if not data:
                    break
                await ws.send_bytes(data)
        except (OSError, asyncio.CancelledError):
            pass
        finally:
            # Le shell s'est terminé (exit) : on ferme la page proprement
            try:
                await ws.close()
            except Exception:
                pass

    reader_task = asyncio.ensure_future(read_from_container())

    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            mark_active(user_id, course["key"])
            if msg.get("text") is not None:
                payload = json.loads(msg["text"])
                if payload.get("type") == "input":
                    await loop.sock_sendall(raw_sock, payload["data"].encode())
                elif payload.get("type") == "resize":
                    containers.resize_exec(exec_id, rows=payload.get("rows", 24), cols=payload.get("cols", 80))
            elif msg.get("bytes") is not None:
                await loop.sock_sendall(raw_sock, msg["bytes"])
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        open_terminals[key] -= 1
        live.terminal_closed(user_id, course["key"])
        reader_task.cancel()
        try:
            raw_sock.close()
        except Exception:
            pass
