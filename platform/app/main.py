"""Linux Lab Platform — FastAPI : comptes, conteneurs par étudiant, terminal WebSocket, validation."""
import asyncio
import json
import logging
import os
import threading
import time
from collections import defaultdict

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import containers
from . import database as db
from . import runner
from .exercises import (CHARACTERS, EXERCISES_VERSION, MAX_SCORE, MENTOR, STEPS, TOTAL_EXERCISES,
                        get_exercise)

log = logging.getLogger("linux-lab")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Linux CLI Lab")
templates = Jinja2Templates(directory="/app/templates")

IDLE_TIMEOUT = int(os.environ.get("IDLE_TIMEOUT", "7200"))  # secondes avant d'arrêter un conteneur inactif
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
STARTED_AT = time.time()

# Activité des étudiants (en mémoire) pour l'arrêt des conteneurs inactifs
last_activity: dict = {}
open_terminals: dict = defaultdict(int)

# Un verrou par étudiant : évite deux mises en place simultanées d'une même étape
_locks: dict = {}
_locks_guard = threading.Lock()


def user_lock(user_id: int) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(user_id, threading.Lock())


def mark_active(user_id: int):
    last_activity[user_id] = time.time()


@app.on_event("startup")
async def startup():
    if db.init_db(EXERCISES_VERSION):
        log.warning("Catalogue d'exercices v%s : l'ancienne progression a été archivée dans progress_archive.", EXERCISES_VERSION)
    asyncio.create_task(idle_reaper())


async def idle_reaper():
    while True:
        await asyncio.sleep(300)
        try:
            active = {uid for uid, n in open_terminals.items() if n > 0}
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


# ─── Pages ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return RedirectResponse("/lab" if get_current_user(request) else "/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    user = await run_in_threadpool(db.authenticate, form.get("email", ""), form.get("password", ""))
    if not user:
        return templates.TemplateResponse(request, "login.html", {"error": "Email ou mot de passe incorrect."})
    response = RedirectResponse("/lab", status_code=302)
    set_session_cookie(response, db.create_session(user["id"]))
    return response


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@app.post("/register")
async def register_submit(request: Request):
    form = await request.form()
    first_name = form.get("first_name", "").strip()
    last_name = form.get("last_name", "").strip()
    email = form.get("email", "").strip()
    password = form.get("password", "")
    password2 = form.get("password2", "")

    def error(msg):
        return templates.TemplateResponse(request, "register.html", {"error": msg})

    if not all([first_name, last_name, email, password]):
        return error("Tous les champs sont obligatoires.")
    if password != password2:
        return error("Les mots de passe ne correspondent pas.")
    if len(password) < 8:
        return error("Mot de passe trop court (8 caractères minimum).")

    user_id = await run_in_threadpool(db.create_user, first_name, last_name, email, password)
    if not user_id:
        return error("Un compte existe déjà avec cet email.")

    response = RedirectResponse("/lab", status_code=302)
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
async def lab_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "lab.html", {"user": user})


# ─── Tableau de bord enseignant ─────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.get("is_admin"):
        return RedirectResponse("/lab", status_code=302)
    students = await run_in_threadpool(db.get_all_students)
    container_list = await run_in_threadpool(containers.list_student_containers)
    steps = [{"num": n, "title": s["title"], "total": len(s["exercises"])} for n, s in STEPS.items()]
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "students": students,
        "containers": container_list,
        "running": sum(1 for c in container_list if c["status"] == "running"),
        "steps": steps,
        "max_score": MAX_SCORE,
        "total_exercises": TOTAL_EXERCISES,
    })


@app.post("/admin/delete-user/{user_id}")
async def admin_delete_user(request: Request, user_id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    await run_in_threadpool(containers.remove_container, user_id)
    db.delete_user(user_id)
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/admin/reset-user/{user_id}")
async def admin_reset_user(request: Request, user_id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    db.reset_user_progress(user_id)
    await run_in_threadpool(containers.remove_container, user_id)
    return RedirectResponse("/dashboard", status_code=302)


# ─── Mise en place et validation (fonctions bloquantes, exécutées en thread) ──

def ensure_setup(user_id: int, container_id: str, step_num: int, force: bool = False) -> dict:
    """Prépare l'étape dans le conteneur (une fois) et retourne ses données attendues."""
    step = STEPS[step_num]
    if not runner.has_setup(step):
        return {}
    with user_lock(user_id):
        if not force:
            code, _ = containers.exec_in_container(container_id, runner.marker_test_command(step_num, step))
            if code == 0:
                data = db.get_setup(user_id, step_num)
                if data is not None:
                    return data
        code, out = containers.exec_in_container(container_id, runner.setup_command(step_num, step))
        data = runner.parse_setup_output(out)
        if code != 0:
            log.error("Échec de la mise en place de l'étape %s (étudiant %s, code %s) :\n%s", step_num, user_id, code, out[-2000:])
        db.save_setup(user_id, step_num, data)
        return data


def prepare_step(user_id: int, step_num: int) -> bool:
    container_id = containers.get_or_create_container(user_id)
    ensure_setup(user_id, container_id, step_num)
    return True


def validate_step(user_id: int, step_num: int, auto: bool) -> dict:
    step = STEPS[step_num]
    container_id = containers.get_or_create_container(user_id)
    env = runner.check_env(ensure_setup(user_id, container_id, step_num))
    progress = db.get_user_score(user_id)
    hints = db.get_hints_used(user_id)

    results = []
    for ex in step["exercises"]:
        res = {"id": ex["id"], "title": ex["title"], "points": ex["points"],
               "passed": False, "already": False, "skipped": False, "message": None, "earned": 0}
        if ex["id"] in progress["completed"]:
            res.update(passed=True, already=True, earned=progress["earned"][ex["id"]])
        elif auto and ex.get("manual"):
            res.update(skipped=True, message="Cliquez sur « Vérifier maintenant » pour tester cet exercice.")
        else:
            code, out = containers.exec_in_container(container_id, runner.check_command(ex), env=env)
            passed, message = runner.parse_check_output(ex, code, out)
            if passed:
                earned = max(1, ex["points"] - hints.get(ex["id"], 0))
                db.add_exercise_completion(user_id, ex["id"], earned)
                res.update(passed=True, earned=earned)
            else:
                res["message"] = message
        results.append(res)

    return {"validation": {"step": step_num, "results": results}, "progress": progress_payload(user_id)}


def progress_payload(user_id: int) -> dict:
    p = db.get_user_score(user_id)
    return {"score": p["score"], "completed": p["completed"], "max_score": MAX_SCORE, "total_exercises": TOTAL_EXERCISES}


# ─── API ────────────────────────────────────────────────────────────────

def unauthorized():
    return JSONResponse({"error": "unauthorized"}, status_code=401)


@app.get("/api/steps")
async def api_steps(request: Request):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    progress = db.get_user_score(user["user_id"])
    return [{
        "num": num,
        "title": step["title"],
        "description": step["description"],
        "total": len(step["exercises"]),
        "completed": sum(1 for ex in step["exercises"] if ex["id"] in progress["completed"]),
    } for num, step in STEPS.items()]


def ticket_payload(ex: dict):
    ticket = ex.get("ticket")
    if not ticket:
        return None
    person = CHARACTERS[ticket["from"]]
    step, index = ex["id"].split(".")
    return {
        "num": 1000 + int(step) * 10 + int(index),
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


@app.get("/api/step/{num}")
async def api_step(request: Request, num: int):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    step = STEPS.get(num)
    if not step:
        return JSONResponse({"error": "not found"}, status_code=404)
    mark_active(user["user_id"])
    # Prépare l'étape (fichiers, processus…) dès son ouverture
    try:
        await run_in_threadpool(prepare_step, user["user_id"], num)
    except Exception:
        log.exception("Préparation de l'étape %s impossible", num)

    progress = db.get_user_score(user["user_id"])
    hints = db.get_hints_used(user["user_id"])
    return {
        "num": num,
        "title": step["title"],
        "description": step["description"],
        "lesson": step.get("lesson", ""),
        "has_setup": runner.has_setup(step),
        "mentor": CHARACTERS[MENTOR]["name"].split()[0],
        "exercises": [exercise_payload(ex, progress, hints) for ex in step["exercises"]],
    }


@app.post("/api/validate/{num}")
async def api_validate(request: Request, num: int, auto: bool = False):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    if num not in STEPS:
        return JSONResponse({"error": "not found"}, status_code=404)
    if not auto:
        mark_active(user["user_id"])
        db.touch_user(user["user_id"])
    return await run_in_threadpool(validate_step, user["user_id"], num, auto)


@app.post("/api/hint/{exercise_id}")
async def api_hint(request: Request, exercise_id: str):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    _, ex = get_exercise(exercise_id)
    if not ex or not ex.get("hints"):
        return JSONResponse({"error": "not found"}, status_code=404)
    count = db.use_hint(user["user_id"], exercise_id, len(ex["hints"]))
    return {"hints": ex["hints"][:count], "hints_total": len(ex["hints"])}


@app.post("/api/reset-step/{num}")
async def api_reset_step(request: Request, num: int):
    """Rejoue la mise en place de l'étape (fichiers fournis, processus…), sans toucher au score."""
    user = get_current_user(request)
    if not user:
        return unauthorized()
    if num not in STEPS:
        return JSONResponse({"error": "not found"}, status_code=404)

    def reset():
        container_id = containers.get_or_create_container(user["user_id"])
        ensure_setup(user["user_id"], container_id, num, force=True)

    await run_in_threadpool(reset)
    return {"status": "ok"}


@app.get("/api/progress")
async def api_progress(request: Request):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    return progress_payload(user["user_id"])


@app.post("/api/reset")
async def api_reset(request: Request):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    db.reset_user_progress(user["user_id"])
    await run_in_threadpool(containers.remove_container, user["user_id"])
    return {"status": "ok"}


# ─── Terminal WebSocket ─────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_terminal(ws: WebSocket):
    token = ws.cookies.get("session")
    user = db.get_session(token) if token else None
    if not user:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()
    user_id = user["user_id"]
    mark_active(user_id)

    try:
        container_id = await run_in_threadpool(containers.get_or_create_container, user_id)
        exec_id, sock = await run_in_threadpool(containers.create_exec_stream, container_id)
    except Exception as e:
        log.exception("Ouverture du terminal impossible")
        await ws.send_text(json.dumps({"error": str(e)}))
        await ws.close()
        return

    open_terminals[user_id] += 1
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
            mark_active(user_id)
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
        open_terminals[user_id] -= 1
        reader_task.cancel()
        try:
            raw_sock.close()
        except Exception:
            pass
