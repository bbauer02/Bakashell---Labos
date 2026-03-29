"""Linux Lab Platform — FastAPI app with auth, container management, WebSocket terminal."""
import asyncio
import json
import os
import threading

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import database as db
from . import containers
from .exercises import STEPS, get_exercise_points

app = FastAPI(title="Linux CLI Lab")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "change-me-in-production"))

templates = Jinja2Templates(directory="/app/templates")


@app.on_event("startup")
def startup():
    db.init_db()


# ─── Auth helpers ───────────────────────────────────────────────────────

def get_current_user(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None
    return db.get_session(token)


# ─── Pages ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/lab", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    email = form.get("email", "")
    password = form.get("password", "")

    user = db.authenticate(email, password)
    if not user:
        return templates.TemplateResponse(request, "login.html", {"error": "Email ou mot de passe incorrect."})

    token = db.create_session(user["id"])
    response = RedirectResponse("/lab", status_code=302)
    response.set_cookie("session", token, httponly=True, max_age=86400)
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

    if not all([first_name, last_name, email, password]):
        return templates.TemplateResponse(request, "register.html", {"error": "Tous les champs sont obligatoires."})

    if password != password2:
        return templates.TemplateResponse(request, "register.html", {"error": "Les mots de passe ne correspondent pas."})

    if len(password) < 4:
        return templates.TemplateResponse(request, "register.html", {"error": "Mot de passe trop court (4 caractères minimum)."})

    user_id = db.create_user(first_name, last_name, email, password)
    if not user_id:
        return templates.TemplateResponse(request, "register.html", {"error": "Un compte existe déjà avec cet email."})

    token = db.create_session(user_id)
    response = RedirectResponse("/lab", status_code=302)
    response.set_cookie("session", token, httponly=True, max_age=86400)
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


# ─── Dashboard (teacher view) ──────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.get("is_admin"):
        return RedirectResponse("/lab", status_code=302)
    students = db.get_all_students()
    container_list = containers.list_student_containers()
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "students": students,
        "containers": container_list,
    })


@app.post("/admin/delete-user/{user_id}")
async def admin_delete_user(request: Request, user_id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    containers.remove_container(user_id)
    db.delete_user(user_id)
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/admin/reset-user/{user_id}")
async def admin_reset_user(request: Request, user_id: int):
    user = get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    db.reset_user_progress(user_id)
    containers.remove_container(user_id)
    return RedirectResponse("/dashboard", status_code=302)


# ─── API ────────────────────────────────────────────────────────────────

@app.get("/api/steps")
async def api_steps(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    progress = db.get_user_score(user["user_id"])
    result = []
    for num, step in STEPS.items():
        completed = sum(1 for ex in step["exercises"] if ex["id"] in progress["completed"])
        result.append({
            "num": num,
            "title": step["title"],
            "description": step["description"],
            "total": len(step["exercises"]),
            "completed": completed,
        })
    return result


@app.get("/api/step/{num}")
async def api_step(request: Request, num: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    step = STEPS.get(num)
    if not step:
        return JSONResponse({"error": "not found"}, status_code=404)

    progress = db.get_user_score(user["user_id"])
    exercises = []
    for ex in step["exercises"]:
        exercises.append({
            "id": ex["id"],
            "points": ex["points"],
            "title": ex["title"],
            "desc": ex["desc"],
            "completed": ex["id"] in progress["completed"],
        })
    return {
        "num": num,
        "title": step["title"],
        "description": step["description"],
        "lesson": step.get("lesson", ""),
        "exercises": exercises,
    }


@app.post("/api/validate/{num}")
async def api_validate(request: Request, num: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    step = STEPS.get(num)
    if not step:
        return JSONResponse({"error": "not found"}, status_code=404)

    # Get or create container for this student
    container_id = containers.get_or_create_container(user["user_id"])
    progress = db.get_user_score(user["user_id"])

    results = []
    for ex in step["exercises"]:
        already = ex["id"] in progress["completed"]
        passed = False
        msg = ex["title"]

        if not already:
            exit_code, _ = containers.exec_in_container(container_id, ex["check"])
            passed = (exit_code == 0)
            if passed:
                db.add_exercise_completion(user["user_id"], ex["id"], ex["points"])
                msg = f"{ex['title']} — validé !"
        else:
            passed = True
            msg = f"{ex['title']} — déjà validé"

        results.append({
            "id": ex["id"],
            "title": ex["title"],
            "points": ex["points"],
            "passed": passed,
            "already": already,
            "message": msg,
        })

    # Refresh progress
    progress = db.get_user_score(user["user_id"])
    return {"validation": {"step": num, "results": results}, "progress": progress}


@app.get("/api/progress")
async def api_progress(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return db.get_user_score(user["user_id"])


@app.post("/api/reset")
async def api_reset(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    db.reset_user_progress(user["user_id"])
    containers.remove_container(user["user_id"])
    return {"status": "ok"}


# ─── WebSocket Terminal ─────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_terminal(ws: WebSocket):
    # Auth from cookie
    token = ws.cookies.get("session")
    user = db.get_session(token) if token else None
    if not user:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()

    # Get or create container
    container_id = containers.get_or_create_container(user["user_id"])

    # Create exec session with PTY
    try:
        exec_id, sock = containers.create_exec_stream(container_id)
    except Exception as e:
        await ws.send_text(json.dumps({"error": str(e)}))
        await ws.close()
        return

    # Get the raw socket
    raw_sock = sock._sock
    raw_sock.setblocking(False)

    alive = True

    async def read_from_container():
        """Read from Docker exec socket and send to WebSocket."""
        loop = asyncio.get_event_loop()
        try:
            while alive:
                await asyncio.sleep(0.01)
                try:
                    data = raw_sock.recv(4096)
                    if data:
                        # Docker stream may include 8-byte header in non-tty mode
                        # In tty mode, data is raw
                        await ws.send_bytes(data)
                    else:
                        break
                except BlockingIOError:
                    pass
                except OSError:
                    break
        except asyncio.CancelledError:
            pass

    reader_task = asyncio.ensure_future(read_from_container())

    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.receive":
                if "text" in msg:
                    payload = json.loads(msg["text"])
                    if payload.get("type") == "input":
                        raw_sock.sendall(payload["data"].encode())
                    elif payload.get("type") == "resize":
                        containers.resize_exec(
                            exec_id,
                            rows=payload.get("rows", 24),
                            cols=payload.get("cols", 80),
                        )
                elif "bytes" in msg:
                    raw_sock.sendall(msg["bytes"])
            elif msg["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        alive = False
        reader_task.cancel()
        try:
            raw_sock.close()
        except Exception:
            pass
