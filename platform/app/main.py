"""Linux Lab Platform — FastAPI : comptes, parcours, conteneurs par étudiant, terminal, éditeur, validation."""
import asyncio
import base64
import csv
import datetime
import io
import json
import logging
import os
import posixpath
import html as html_lib
import re
import threading
import time
from collections import defaultdict
from urllib.parse import quote, quote_plus

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import containers
from . import database as db
from . import live
from . import progression
from . import badges
from . import objectif
from . import integrity
from . import memo
from . import quiz
from . import ratelimit
from . import runner
from . import solutions
from . import terminals
from .courses import COURSES, DEFAULT_COURSE, EXERCISE_INDEX, QUIZ_QUESTIONS, get_course, get_exercise
from .scenario import CHARACTERS, contexte

log = logging.getLogger("linux-lab")
logging.basicConfig(level=logging.INFO)

APP_DIR = os.environ.get("APP_DIR", "/app")

# Nom de l'application et auteur, affichés sur toutes les pages
APP_TITLE, APP_SHORT = "Bakashell — Labo DevOps", "Bakashell"
AUTHOR_NAME, AUTHOR_EMAIL = "Bauer Baptiste", "bbauer02@gmail.com"

app = FastAPI(title=APP_TITLE)
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))
templates.env.globals.update(APP_TITLE=APP_TITLE, APP_SHORT=APP_SHORT,
                             AUTHOR_NAME=AUTHOR_NAME, AUTHOR_EMAIL=AUTHOR_EMAIL)
templates.env.filters["heure"] = lambda ts: datetime.datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")
# xterm.js et Monaco servis par la plateforme (installés dans l'image) : pas besoin d'Internet en salle
if os.path.isdir(os.path.join(APP_DIR, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")

IDLE_TIMEOUT = int(os.environ.get("IDLE_TIMEOUT", "7200"))  # secondes avant d'arrêter un conteneur inactif
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
# Adresse publique de la plateforme (ex. https://lab.mon-lycee.fr) pour les liens transmis (réinitialisation,
# attestation) ; vide : l'adresse par laquelle la page a été ouverte
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").strip().rstrip("/")
STARTED_AT = time.time()
MAX_FILE_BYTES = 256 * 1024
# Pourcentage des points à atteindre pour obtenir l'attestation de fin de parcours
CERTIFICATE_MIN_PCT = int(os.environ.get("CERTIFICATE_MIN_PCT", "70"))
# Sauvegarde automatique de la base : dossier (vide = désactivée), intervalle et nombre de copies gardées
BACKUP_DIR = os.environ.get("BACKUP_DIR", "")
BACKUP_HOURS = max(1.0, float(os.environ.get("BACKUP_HOURS", "24")))  # au moins une heure entre deux copies
BACKUP_KEEP = int(os.environ.get("BACKUP_KEEP", "14"))

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
    db.purge_terminal_log(integrity.RETENTION_DAYS)
    asyncio.create_task(idle_reaper())
    if BACKUP_DIR:
        asyncio.create_task(backup_loop())


def backup_now() -> str:
    """Copie datée de la base dans BACKUP_DIR ; ne garde que les BACKUP_KEEP plus récentes."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    path = os.path.join(BACKUP_DIR, time.strftime("platform-%Y%m%d-%H%M%S.db"))
    db.backup_to(path)
    old = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("platform-") and f.endswith(".db"))
    for name in old[:-BACKUP_KEEP] if BACKUP_KEEP > 0 else []:
        os.remove(os.path.join(BACKUP_DIR, name))
    return path


async def backup_loop():
    await asyncio.sleep(60)  # laisse la plateforme démarrer
    while True:
        try:
            path = await run_in_threadpool(backup_now)
            log.info("Sauvegarde de la base : %s", path)
        except Exception:
            log.exception("Sauvegarde de la base impossible")
        await asyncio.sleep(BACKUP_HOURS * 3600)


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


# Vignettes d'illustration des labos. Par ordre de priorité :
# 1. l'image envoyée par l'administrateur depuis le catalogue, gardée avec la base (VIGNETTES_DIR) : elle survit aux
#    reconstructions de l'image de la plateforme ;
# 2. une image déposée dans static/vignettes/<parcours>.webp, .png ou .jpg (copiée dans l'image) ;
# 3. l'illustration .svg fournie dans static/vignettes.
THUMBNAIL_EXTS = ("webp", "png", "jpg", "jpeg", "svg")
VIGNETTES_DIR = os.environ.get("VIGNETTES_DIR") or os.path.join(os.path.dirname(db.DB_PATH), "vignettes")
VIGNETTE_MAX_BYTES = 3 * 1024 * 1024
# Formats acceptés à l'envoi, reconnus à leur signature (jamais de SVG envoyé : il peut contenir du script)
VIGNETTE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


def vignette_format(data: bytes):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def uploaded_thumbnail(key: str):
    """Chemin de la vignette envoyée pour ce parcours, ou None."""
    for ext in VIGNETTE_TYPES:
        path = os.path.join(VIGNETTES_DIR, f"{key}.{ext}")
        if os.path.isfile(path):
            return path
    return None


def thumbnail_url(key: str):
    """Adresse de la vignette du parcours (avec sa date de modification, pour le cache), ou None."""
    path = uploaded_thumbnail(key)
    if path:
        return f"/vignettes/{os.path.basename(path)}?v={int(os.path.getmtime(path))}"
    for ext in THUMBNAIL_EXTS:
        path = os.path.join(APP_DIR, "static", "vignettes", f"{key}.{ext}")
        if os.path.isfile(path):
            return f"/static/vignettes/{key}.{ext}?v={int(os.path.getmtime(path))}"
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


def client_ip(request) -> str:
    # Derrière un reverse proxy, lancer uvicorn avec --proxy-headers (voir le Dockerfile) pour obtenir l'IP réelle
    return request.client.host if request.client else "?"


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    email = form.get("email", "").strip().lower()
    ip = client_ip(request)
    wait = ratelimit.login_blocked(ip, email)
    if wait:
        return templates.TemplateResponse(request, "login.html", {"error": ratelimit.wait_message(wait)},
                                          status_code=429)
    user = await run_in_threadpool(db.authenticate, email, form.get("password", ""))
    if not user:
        ratelimit.login_failed(ip, email)
        return templates.TemplateResponse(request, "login.html", {"error": "Email ou mot de passe incorrect."})
    ratelimit.login_succeeded(ip, email)
    if user.get("disabled"):  # vérifié après le mot de passe : un inconnu n'apprend rien sur le compte
        return templates.TemplateResponse(request, "login.html", {
            "error": "Ce compte a été désactivé : contactez l'administrateur de la plateforme."}, status_code=403)
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

    def error(msg, status_code=200):
        return templates.TemplateResponse(request, "register.html", {"error": msg, "form": dict(form)},
                                          status_code=status_code)

    ip_key = f"ip:{client_ip(request)}"
    wait = ratelimit.REGISTER.blocked(ip_key)
    if wait:
        return error(ratelimit.wait_message(wait), 429)
    if not all([first_name, last_name, email, password]):
        return error("Tous les champs sont obligatoires.")
    if password != password2:
        return error("Les mots de passe ne correspondent pas.")
    if len(password) < 8:
        return error("Mot de passe trop court (8 caractères minimum).")
    if class_code and not db.class_exists_for_code(class_code):
        return error("Ce code de classe n'existe pas : vérifiez-le auprès de votre enseignant·e.")

    ratelimit.REGISTER.hit(ip_key)
    user_id = await run_in_threadpool(db.create_user, first_name, last_name, email, password)
    if not user_id:
        return error("Un compte existe déjà avec cet email.")
    if class_code:
        db.join_class_by_code(user_id, class_code)

    response = RedirectResponse("/catalogue", status_code=302)
    set_session_cookie(response, db.create_session(user_id))
    return response


@app.get("/invitation/{token}", response_class=HTMLResponse)
async def invitation_page(request: Request, token: str):
    """Invitation d'un enseignant (lien créé par l'administrateur) : formulaire de création du compte."""
    invite = db.invite_info(token)
    return templates.TemplateResponse(request, "invitation.html", {
        "invite": invite, "error": None, "form": {"email": invite["email"] or ""} if invite else {},
    }, status_code=200 if invite else 404)


@app.post("/invitation/{token}")
async def invitation_submit(request: Request, token: str):
    """Mêmes règles et même limitation des tentatives que l'inscription ; crée un compte enseignant et le connecte."""
    form = await request.form()
    first_name = form.get("first_name", "").strip()
    last_name = form.get("last_name", "").strip()
    email = form.get("email", "").strip()
    password = form.get("password", "")
    password2 = form.get("password2", "")
    ip_key = f"ip:{client_ip(request)}"
    invite = db.invite_info(token)

    def error(msg, status_code=200):
        return templates.TemplateResponse(request, "invitation.html", {
            "invite": invite, "error": msg, "form": {**dict(form), "email": (invite or {}).get("email") or email},
        }, status_code=status_code)

    wait = ratelimit.REGISTER.blocked(ip_key)
    if wait:
        return error(ratelimit.wait_message(wait), 429)
    if not invite:
        ratelimit.REGISTER.hit(ip_key)
        return error(None, 404)
    if not all([first_name, last_name, email, password]):
        return error("Tous les champs sont obligatoires.")
    if password != password2:
        return error("Les mots de passe ne correspondent pas.")
    if len(password) < MIN_PASSWORD:
        return error(f"Mot de passe trop court ({MIN_PASSWORD} caractères minimum).")

    ratelimit.REGISTER.hit(ip_key)
    user_id, reason = await run_in_threadpool(db.accept_invite, token, first_name, last_name, email, password)
    if reason == "exists":
        return error("Un compte existe déjà avec cet email.")
    if reason == "email":
        return error("Cette invitation est réservée à une autre adresse e-mail.")
    if not user_id:
        invite = None
        return error(None, 404)
    log.info("Compte enseignant créé par invitation : %s", email.lower())
    response = RedirectResponse("/dashboard", status_code=302)
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


MIN_PASSWORD = 8


@app.get("/compte", response_class=HTMLResponse)
async def account_page(request: Request, ok: int = 0):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    msg = "Mot de passe modifié. Vos autres sessions ont été fermées." if ok else ""
    return templates.TemplateResponse(request, "account.html", {"user": user, "error": None, "msg": msg})


@app.post("/compte")
async def account_submit(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    current, new, new2 = form.get("current", ""), form.get("password", ""), form.get("password2", "")

    def error(msg, status_code=200):
        return templates.TemplateResponse(request, "account.html", {"user": user, "error": msg, "msg": ""},
                                          status_code=status_code)

    key = f"user:{user['user_id']}"
    wait = ratelimit.PASSWORD.blocked(key)
    if wait:
        return error(ratelimit.wait_message(wait), 429)
    if not await run_in_threadpool(db.check_password, user["user_id"], current):
        ratelimit.PASSWORD.hit(key)
        return error("Mot de passe actuel incorrect.")
    if new != new2:
        return error("Les nouveaux mots de passe ne correspondent pas.")
    if len(new) < MIN_PASSWORD:
        return error(f"Mot de passe trop court ({MIN_PASSWORD} caractères minimum).")
    await run_in_threadpool(db.set_password, user["user_id"], new, request.cookies.get("session"))
    return RedirectResponse("/compte?ok=1", status_code=302)


@app.get("/confidentialite", response_class=HTMLResponse)
async def privacy_page(request: Request):
    """Mentions légales et politique de confidentialité (page publique)."""
    return templates.TemplateResponse(request, "confidentialite.html", {"integrity_days": integrity.RETENTION_DAYS})


@app.get("/reinitialiser/{token}", response_class=HTMLResponse)
async def reset_page(request: Request, token: str):
    target = db.reset_token_user(token)
    return templates.TemplateResponse(request, "reset_password.html", {"target": target, "error": None},
                                      status_code=200 if target else 404)


@app.post("/reinitialiser/{token}")
async def reset_submit(request: Request, token: str):
    key = f"ip:{client_ip(request)}"
    wait = ratelimit.PASSWORD.blocked(key)
    if wait:
        return templates.TemplateResponse(request, "reset_password.html",
                                          {"target": None, "error": ratelimit.wait_message(wait), "limited": True},
                                          status_code=429)
    target = db.reset_token_user(token)
    if not target:
        ratelimit.PASSWORD.hit(key)
        return templates.TemplateResponse(request, "reset_password.html", {"target": None, "error": None},
                                          status_code=404)
    form = await request.form()
    new, new2 = form.get("password", ""), form.get("password2", "")
    error = None
    if new != new2:
        error = "Les mots de passe ne correspondent pas."
    elif len(new) < MIN_PASSWORD:
        error = f"Mot de passe trop court ({MIN_PASSWORD} caractères minimum)."
    if error:
        return templates.TemplateResponse(request, "reset_password.html", {"target": target, "error": error})
    await run_in_threadpool(db.set_password, target["id"], new)  # ferme toutes ses sessions, annule le lien
    ratelimit.LOGIN_ACCOUNT.clear(f"email:{target['email']}")
    response = RedirectResponse("/catalogue", status_code=302)
    set_session_cookie(response, db.create_session(target["id"]))
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
    certificates = db.user_certificates(user["user_id"])
    today = datetime.date.today().isoformat()
    for key in accessible_keys(user):
        c = COURSES[key]
        p = db.get_user_score(user["user_id"], c["id_glob"])
        done = len(p["completed"])
        memo_found, memo_total = memo.counts(key, p["completed"])
        pending = step_deadlines(user["user_id"], c, p["completed"])
        cards.append({
            "memo_found": memo_found, "memo_total": memo_total,
            "key": key, "title": c["title"], "summary": c["summary"], "level": c["level"],
            "thumbnail": thumbnail_url(key), "custom_thumbnail": bool(uploaded_thumbnail(key)),
            **progression.progression(c, p["score"], p["completed"]),
            "exam": bool(c.get("exam")),
            "duration": c["duration"], "steps": len(c["steps"]), "total": c["total_exercises"],
            "score": p["score"], "max": c["max_score"], "done": done,
            # Arrondi vers le bas, comme les seuils des grades : 14,9 % n'affiche pas « 15 % »
            "pct": 100 * p["score"] // c["max_score"] if c["max_score"] else 0,
            "certificate": certificates.get(key),
            "certificate_ok": certificate_eligible(c, p["score"]),
            "next_deadline": pending[0] if pending else None,
            "late": sum(1 for d in pending if d["due"] < today),
        })
    classes = db.get_user_classes(user["user_id"])
    # Objectif collectif de chaque classe de l'étudiant (sa propre part comprise)
    goals = [{"name": cl["name"], **g} for cl in classes
             if (g := objectif.compute(cl["id"], db.class_course_keys(cl["id"]), user["user_id"]))]
    return templates.TemplateResponse(request, "catalogue.html", {
        "user": user, "cards": cards, "classes": classes, "goals": goals, "msg": msg, "err": err,
        "uptime": badges.streak(user["user_id"]),
        "today": today, "certificate_pct": CERTIFICATE_MIN_PCT,
    })


def step_deadlines(user_id: int, course: dict, completed) -> list:
    """Échéances des étapes pas encore terminées, de la plus proche à la plus lointaine."""
    completed = set(completed)
    out = []
    for step, due in db.user_deadlines(user_id, course["key"]).items():
        s = course["steps"].get(step)
        if s and any(ex["id"] not in completed for ex in s["exercises"]):
            out.append({"step": step, "title": s["title"], "due": due})
    return sorted(out, key=lambda d: (d["due"], d["step"]))


def certificate_eligible(course: dict, score: int) -> bool:
    return bool(course["max_score"]) and score * 100 >= CERTIFICATE_MIN_PCT * course["max_score"]


@app.post("/attestation/{course_key}")
async def certificate_issue(request: Request, course_key: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    course = course_for(user, course_key)
    if not course:
        return RedirectResponse("/catalogue?err=Ce+labo+ne+vous+est+pas+ouvert", status_code=302)
    p = db.get_user_score(user["user_id"], course["id_glob"])
    if not certificate_eligible(course, p["score"]):
        return RedirectResponse(
            f"/catalogue?err={quote_plus(f'Attestation disponible à partir de {CERTIFICATE_MIN_PCT} % des points.')}",
            status_code=302)
    code = db.issue_certificate(user["user_id"], course, p["score"], len(p["completed"]))
    return RedirectResponse(f"/attestation/{code}", status_code=302)


@app.get("/attestation/{code}", response_class=HTMLResponse)
async def certificate_page(request: Request, code: str):
    """Page publique (vérifiable par un jury ou un employeur), imprimable en PDF depuis le navigateur."""
    cert = db.get_certificate(code)
    if cert:
        course = get_course(cert["course_key"])
        cert["pct"] = round(100 * cert["score"] / cert["max_score"]) if cert["max_score"] else 0
        # Compétences travaillées : les étapes où l'étudiant a réussi au moins un exercice
        done = set(db.get_user_score(cert["user_id"], course["id_glob"])["completed"]) if course else set()
        cert["steps"] = [s["title"] for s in course["steps"].values()
                         if any(ex["id"] in done for ex in s["exercises"])] if course else []
        cert["issued"] = datetime.datetime.strptime(cert["issued_at"][:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    # Lien de vérification construit à partir du code seul (jamais de l'URL demandée : rien n'est réfléchi)
    url = f"{public_base(request)}/attestation/{quote(code, safe='')}"
    return templates.TemplateResponse(request, "certificate.html", {
        "cert": cert, "url": url, "viewer": get_current_user(request),
    }, status_code=200 if cert else 404)


def public_base(request: Request) -> str:
    return PUBLIC_URL or str(request.base_url).rstrip("/")


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


@app.get("/vignettes/{name}")
async def vignette(name: str):
    m = re.fullmatch(r"([a-z]+)\.(png|jpg|webp)", name)
    path = os.path.join(VIGNETTES_DIR, name) if m and m.group(1) in COURSES else None
    if not path or not os.path.isfile(path):
        return not_found()
    with open(path, "rb") as f:
        data = f.read()
    return Response(data, media_type=VIGNETTE_TYPES[m.group(2)],
                    headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"})


@app.post("/admin/vignettes/{course_key}")
async def vignette_upload(request: Request, course_key: str):
    """Vignette d'un labo envoyée depuis le catalogue (administrateur : elle est commune à toutes les classes)."""
    if not superadmin_or_none(request):
        return RedirectResponse("/catalogue", status_code=302)
    if course_key not in COURSES:
        return not_found()
    form = await request.form()
    if form.get("action") == "supprimer":
        path = uploaded_thumbnail(course_key)
        if path:
            os.remove(path)
        return RedirectResponse("/catalogue?msg=Illustration+d%27origine+r%C3%A9tablie", status_code=302)
    upload = form.get("image")
    data = await upload.read(VIGNETTE_MAX_BYTES + 1) if hasattr(upload, "read") else b""
    if len(data) > VIGNETTE_MAX_BYTES:
        return RedirectResponse("/catalogue?err=Image+trop+lourde+%283+Mo+au+plus%29", status_code=302)
    ext = vignette_format(data)
    if not ext:
        return RedirectResponse("/catalogue?err=Format+non+reconnu+%3A+PNG%2C+JPEG+ou+WebP", status_code=302)
    os.makedirs(VIGNETTES_DIR, exist_ok=True)
    old = uploaded_thumbnail(course_key)
    tmp = os.path.join(VIGNETTES_DIR, f".{course_key}.{ext}.tmp")
    with open(tmp, "wb") as f:
        f.write(data)
    if old and not old.endswith(f".{ext}"):
        os.remove(old)
    os.replace(tmp, os.path.join(VIGNETTES_DIR, f"{course_key}.{ext}"))
    return RedirectResponse(f"/catalogue?msg={quote_plus('Vignette mise à jour : ' + COURSES[course_key]['short'])}",
                            status_code=302)


@app.get("/profil", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return profile_response(request, user, user, own=True)


@app.get("/profil/{student_id}", response_class=HTMLResponse)
async def student_profile_page(request: Request, student_id: int):
    """Profil d'un étudiant, vu par un membre du personnel qui le suit."""
    viewer = staff_or_none(request)
    if not viewer or not can_see_student(viewer, student_id):
        return RedirectResponse("/catalogue", status_code=302)
    target = db.get_user(student_id)
    return profile_response(request, viewer, {**target, "user_id": student_id}, own=False)


def profile_response(request: Request, viewer: dict, target: dict, own: bool):
    """Badges, grade et couches d'ICE percées dans chaque labo, collègues aidés."""
    uid = target["user_id"]
    labs, layers, tickets = [], 0, 0
    for key in accessible_keys(target):
        c = COURSES[key]
        p = db.get_user_score(uid, c["id_glob"])
        prog = progression.progression(c, p["score"], p["completed"])
        layers += prog["breach"]["layers"]
        tickets += len(p["completed"])
        labs.append({"key": key, "title": c["title"], "short": c["short"], "thumbnail": thumbnail_url(key),
                     "done": len(p["completed"]), "total": c["total_exercises"], "score": p["score"],
                     "max": c["max_score"], "pct": 100 * p["score"] // c["max_score"] if c["max_score"] else 0, **prog})
    # Collègues aidés : tickets résolus par personnage
    helped = {}
    for e in db.get_user_score(uid)["completed"]:
        ticket = EXERCISE_INDEX.get(e, (None, None, None, {}))[3].get("ticket")
        if ticket:
            helped[ticket["from"]] = helped.get(ticket["from"], 0) + 1
    colleagues = [{"name": ch["name"], "role": ch["role"].split(",")[0], "color": ch["color"],
                   "initials": "".join(w[0] for w in ch["name"].split()[:2]), "count": helped.get(k, 0)}
                  for k, ch in CHARACTERS.items()]
    colleagues.sort(key=lambda x: -x["count"])
    all_badges = badges.compute(uid)
    return templates.TemplateResponse(request, "profile.html", {
        "user": viewer, "target": target, "own": own, "labs": labs, "badges": all_badges,
        "earned": sum(b["earned"] for b in all_badges), "layers": layers,
        "tickets": tickets if labs else 0, "colleagues": colleagues,
        "classes": db.get_user_classes(uid), "certificates": len(db.user_certificates(uid)),
        "uptime": badges.streak(uid),
    })


@app.get("/api/badges")
async def api_badges(request: Request):
    user = get_current_user(request)
    if not user:
        return unauthorized()
    return {"badges": badges.compute(user["user_id"]), "uptime": badges.streak(user["user_id"])}


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
        "integrity_days": integrity.RETENTION_DAYS,
        "certificate_pct": CERTIFICATE_MIN_PCT,
        "thumbnail": thumbnail_url(course["key"]),
        "company_html": contexte(None if course.get("exam") else course["mentor"],
                                 independant=not course.get("exam")),
    })


# ─── Profils du personnel et cloisonnement ──────────────────────────────
# Trois profils : étudiant (is_admin = 0), enseignant (is_admin = 1) et administrateur (is_admin = 1 et
# is_superadmin = 1 : le seul compte ADMIN_EMAIL). is_admin donne l'accès à tous les parcours, au mémo complet et
# aux corrections. Un enseignant ne voit et n'agit que sur SES classes et sur les étudiants membres d'au moins
# une d'entre elles ; l'administrateur voit tout. Toutes les pages et API enseignant passent par ces fonctions.

def staff_or_none(request: Request):
    """Le compte connecté s'il fait partie du personnel (enseignant ou administrateur), sinon None."""
    user = get_current_user(request)
    return user if user and user.get("is_admin") else None


def is_superadmin(user) -> bool:
    return bool(user and user.get("is_admin") and user.get("is_superadmin"))


def superadmin_or_none(request: Request):
    """Le compte connecté s'il est l'administrateur de la plateforme, sinon None."""
    user = get_current_user(request)
    return user if is_superadmin(user) else None


def owner_filter(user):
    """Propriétaire des classes à montrer : None (toutes) pour l'administrateur, l'enseignant lui-même sinon."""
    return None if is_superadmin(user) else user["user_id"]


def visible_student_ids(user):
    """None pour l'administrateur (tous les étudiants) ; pour un enseignant, l'ensemble des étudiants membres
    d'au moins une de ses classes."""
    return None if is_superadmin(user) else db.owner_student_ids(user["user_id"])


def owns_class(user, class_id: int) -> bool:
    """La classe existe et l'utilisateur peut la gérer : il en est le propriétaire, ou il est l'administrateur."""
    if not user or not user.get("is_admin") or not class_id:
        return False
    if is_superadmin(user):
        return db.class_exists(class_id)
    return db.class_owner(class_id) == user["user_id"]


def can_see_student(user, student_id: int) -> bool:
    """Compte étudiant (jamais un compte du personnel) visible par ce membre du personnel."""
    if not user or not user.get("is_admin"):
        return False
    target = db.get_user(student_id)
    if not target or target["is_admin"]:
        return False
    visible = visible_student_ids(user)
    return visible is None or student_id in visible


def class_filter(user, classe: int) -> int:
    """Filtre de classe demandé s'il porte sur une classe de l'utilisateur ; sinon 0 (toutes ses classes)."""
    return classe if classe and owns_class(user, classe) else 0


def scoped_student_ids(user, classe: int):
    """Étudiants pris en compte : ceux de la classe filtrée (déjà vérifiée par class_filter), sinon tous ceux que
    l'utilisateur voit (None : tous, pour l'administrateur)."""
    return db.class_member_ids(classe) if classe else visible_student_ids(user)


def forbidden_page(request: Request):
    return templates.TemplateResponse(request, "forbidden.html", {}, status_code=403)


def staff_redirect(request: Request):
    """Refus d'une page réservée : un membre du personnel sans le droit voulu reçoit un 403, les autres vont
    à la page de connexion."""
    return forbidden_page(request) if staff_or_none(request) else RedirectResponse("/login", status_code=302)


def live_filter(user):
    """Filtre du flux en direct pour une connexion : None pour l'administrateur ; pour un enseignant, ses
    étudiants, relus au plus toutes les 30 s (un étudiant qui rejoint sa classe apparaît sans recharger)."""
    if is_superadmin(user):
        return None
    cache = {"ids": set(), "at": 0.0}

    def allowed(student_id) -> bool:
        if time.time() - cache["at"] > 30:
            cache.update(ids=db.owner_student_ids(user["user_id"]), at=time.time())
        return student_id in cache["ids"]
    return allowed


# ─── Tableau de bord enseignant ─────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, course: str = DEFAULT_COURSE, classe: int = 0):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.get("is_admin"):
        return RedirectResponse("/catalogue", status_code=302)
    c = get_course(course) or COURSES[DEFAULT_COURSE]
    classe = class_filter(user, classe)
    students = await run_in_threadpool(course_students, c, scoped_student_ids(user, classe))
    classes = db.list_classes(owner_filter(user))
    try:
        container_list = await run_in_threadpool(containers.list_student_containers)
    except Exception:
        log.exception("Liste des conteneurs indisponible")
        container_list = []
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
        "late_total": sum(1 for s in students if s["late"]),
    })


def course_students(course: dict, student_ids=None) -> list:
    """Étudiants (ceux de student_ids, ou tous si None) avec leur progression sur le parcours et leurs retards."""
    step_of = {ex["id"]: n for n, s in course["steps"].items() for ex in s["exercises"]}
    students = db.get_all_students(course, step_of)
    if student_ids is not None:
        students = [s for s in students if s["id"] in student_ids]
    deadlines = db.deadlines_per_user(course["key"])
    today = datetime.date.today().isoformat()
    for s in students:
        s["deadlines"] = deadlines.get(s["id"], {})
        s["late"] = sorted(step for step, due in s["deadlines"].items()
                           if due < today and step in course["steps"]
                           and s["per_step"].get(step, 0) < len(course["steps"][step]["exercises"]))
    return students


@app.get("/admin/export.csv")
async def admin_export(request: Request, course: str = DEFAULT_COURSE, classe: int = 0):
    """Notes du parcours au format CSV (séparateur « ; », UTF-8 avec BOM : s'ouvre directement dans Excel)."""
    user = staff_or_none(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    c = get_course(course) or COURSES[DEFAULT_COURSE]
    classe = class_filter(user, classe)
    students = await run_in_threadpool(course_students, c, scoped_student_ids(user, classe))
    hints = db.hints_per_user(c["id_glob"])
    last = db.last_completion_per_user(c["id_glob"])
    class_names = db.class_names_per_user(owner_filter(user))
    certificates = {}
    for s in students:
        certificates[s["id"]] = db.user_certificates(s["id"]).get(c["key"], "")

    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    step_nums = list(c["steps"])
    w.writerow(["Nom", "Prénom", "Email", "Classes", "Score", "Score max", "Note /20", "Exercices réussis",
                "Exercices", "Indices utilisés", "Étapes terminées", "Étapes en retard", "Dernière réussite (UTC)",
                "Attestation"] + [f"Étape {n}" for n in step_nums])
    for s in sorted(students, key=lambda s: (s["last_name"].lower(), s["first_name"].lower())):
        finished = sum(1 for n in step_nums if s["per_step"].get(n, 0) >= len(c["steps"][n]["exercises"]))
        note = round(20 * s["score"] / c["max_score"], 2) if c["max_score"] else 0
        w.writerow([csv_text(s["last_name"]), csv_text(s["first_name"]), csv_text(s["email"]),
                    csv_text(", ".join(class_names.get(s["id"], []))),
                    s["score"], c["max_score"], str(note).replace(".", ","), s["exercises_done"],
                    c["total_exercises"], hints.get(s["id"], 0), finished, " ".join(map(str, s["late"])),
                    last.get(s["id"]) or "", certificates.get(s["id"], "")]
                   + [f"{s['per_step'].get(n, 0)}/{len(c['steps'][n]['exercises'])}" for n in step_nums])
    suffix = ""
    if classe:
        match = [cl["name"] for cl in db.list_classes(owner_filter(user)) if cl["id"] == classe]
        suffix = "-" + re.sub(r"[^A-Za-z0-9_-]+", "-", match[0]).strip("-") if match else ""
    filename = f"notes-{c['key']}{suffix}-{datetime.date.today().isoformat()}.csv"
    return Response("﻿" + out.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def csv_text(value) -> str:
    """Texte saisi par un utilisateur : un tableur ne doit pas l'interpréter comme une formule."""
    value = str(value)
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


@app.get("/admin/stats", response_class=HTMLResponse)
async def admin_stats(request: Request, course: str = DEFAULT_COURSE, classe: int = 0):
    """Statistiques par exercice : où les étudiants bloquent, pour ajuster le catalogue."""
    user = staff_or_none(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    c = get_course(course) or COURSES[DEFAULT_COURSE]
    classe = class_filter(user, classe)
    data = await run_in_threadpool(db.exercise_stats, c, scoped_student_ids(user, classe))
    steps = []
    for num, step in c["steps"].items():
        rows = []
        for ex in step["exercises"]:
            st = data["exercises"].get(ex["id"], {"tried": 0, "passed": 0, "fails": 0, "hints": 0,
                                                  "top_message": None, "top_count": 0})
            rate = round(100 * st["passed"] / st["tried"]) if st["tried"] else None
            rows.append({**st, "id": ex["id"], "title": ex["title"], "points": ex["points"],
                         "rate": rate, "fails_per_student": round(st["fails"] / st["tried"], 1) if st["tried"] else 0,
                         "hints_total": len(ex.get("hints", []))})
        steps.append({"num": num, "title": step["title"], "rows": rows})
    return templates.TemplateResponse(request, "stats.html", {
        "user": user, "course": c, "courses": courses_menu(), "classes": db.list_classes(owner_filter(user)),
        "classe": classe, "steps": steps, "students": data["students"],
    })


def _reference_text(course: dict) -> str:
    """Tout ce que les étudiants lisent (cours, tickets, consignes, indices) : une commande qui en vient n'est pas suspecte."""
    parts = []
    for step in course["steps"].values():
        parts.append(step.get("lesson", ""))
        for ex in step["exercises"]:
            parts += [ex.get("desc", ""), (ex.get("ticket") or {}).get("body", ""), *ex.get("hints", [])]
    text = re.sub(r"<br\s*/?>", "\n", " ".join(parts))
    return html_lib.unescape(re.sub(r"<[^>]+>", "", text))


@app.get("/admin/integrite", response_class=HTMLResponse)
async def admin_integrity(request: Request, course: str = DEFAULT_COURSE, classe: int = 0):
    """Signaux à examiner : réussites éclair, rafales, collages, commandes identiques entre étudiants."""
    user = staff_or_none(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    c = get_course(course) or COURSES[DEFAULT_COURSE]
    classe = class_filter(user, classe)
    names, completions, logs = await run_in_threadpool(db.integrity_data, c, scoped_student_ids(user, classe))
    data = integrity.report(c, names, completions, logs, _reference_text(c))
    return templates.TemplateResponse(request, "integrity.html", {
        "user": user, "course": c, "courses": courses_menu(), "classes": db.list_classes(owner_filter(user)),
        "classe": classe, "data": data, "retention": integrity.RETENTION_DAYS,
    })


@app.post("/api/admin/reset-link/{user_id}")
async def admin_reset_link(request: Request, user_id: int):
    """Lien de réinitialisation du mot de passe, à transmettre à l'étudiant (valable RESET_HOURS heures).
    Un enseignant : pour ses étudiants seulement ; l'administrateur : pour tout étudiant et tout enseignant."""
    user = staff_or_none(request)
    if not user:
        return JSONResponse({"error": "Réservé aux enseignants"}, status_code=403)
    target = db.get_user(user_id)
    if not target:
        return not_found()
    teacher = target["is_admin"] and not target["is_superadmin"]
    if not (can_see_student(user, user_id) or (is_superadmin(user) and teacher)):
        return JSONResponse({"error": "Ce compte n'est pas dans vos classes"}, status_code=403)
    token = db.create_reset_token(user_id)
    return {"link": f"{public_base(request)}/reinitialiser/{token}", "hours": db.RESET_HOURS,
            "name": f"{target['first_name']} {target['last_name']}"}


# ─── Classes (chaque enseignant gère les siennes ; l'administrateur, toutes) ──

def back_to_classes(msg: str = "", anchor: str = "", err: bool = False):
    key = "err" if err else "msg"
    query = f"?{key}={quote_plus(msg)}" if msg else ""
    return RedirectResponse(f"/admin/classes{query}{anchor}", status_code=302)


@app.get("/admin/classes", response_class=HTMLResponse)
async def admin_classes(request: Request, msg: str = "", err: str = ""):
    user = staff_or_none(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    # Un enseignant ne choisit que parmi ses propres étudiants ; les autres s'ajoutent par leur adresse e-mail exacte
    classes = db.list_classes(owner_filter(user))
    for c in classes:
        c["goal"] = objectif.compute(c["id"], c["courses"])
    return templates.TemplateResponse(request, "admin_classes.html", {
        "user": user, "classes": classes, "students": db.list_students(owner_filter(user)),
        "all_courses": [{"key": k, "title": c["title"], "short": c["short"],
                         "steps": [{"num": n, "title": s["title"]} for n, s in c["steps"].items()]}
                        for k, c in COURSES.items()],
        "deadlines": db.list_deadlines(), "today": datetime.date.today().isoformat(),
        "msg": msg, "err": err,
    })


def class_or_refusal(request: Request, class_id: int):
    """(utilisateur, None) si la classe appartient à l'utilisateur (ou s'il est l'administrateur) ;
    sinon (None, réponse de refus) : connexion pour un visiteur, « classe inconnue » pour un autre enseignant
    (sans dire si la classe existe chez quelqu'un d'autre)."""
    user = staff_or_none(request)
    if not user:
        return None, RedirectResponse("/login", status_code=302)
    if not owns_class(user, class_id):
        return None, back_to_classes("Classe inconnue.", err=True)
    return user, None


@app.post("/admin/classes/{class_id}/deadlines")
async def admin_class_deadline(request: Request, class_id: int):
    """Ajoute ou modifie une échéance ; « jusqu'à » applique la même date à toutes les étapes d'un intervalle."""
    user, refusal = class_or_refusal(request, class_id)
    if refusal:
        return refusal
    form = await request.form()
    course = get_course(form.get("course", ""))
    due = form.get("due_date", "")
    try:
        first, last = int(form.get("step", "0")), int(form.get("step_to") or form.get("step", "0"))
        datetime.date.fromisoformat(due)
    except ValueError:
        return back_to_classes("Échéance invalide : choisissez une étape et une date.", f"#classe-{class_id}", err=True)
    if not course:
        return back_to_classes("Parcours inconnu.", f"#classe-{class_id}", err=True)
    steps = [n for n in course["steps"] if min(first, last) <= n <= max(first, last)]
    if not steps:
        return back_to_classes("Aucune étape dans cet intervalle.", f"#classe-{class_id}", err=True)
    for n in steps:
        db.set_deadline(class_id, course["key"], n, due)
    label = f"étape {steps[0]}" if len(steps) == 1 else f"étapes {steps[0]} à {steps[-1]}"
    return back_to_classes(f"Échéance enregistrée : {course['short']}, {label}.", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/deadlines/delete")
async def admin_class_deadline_delete(request: Request, class_id: int):
    user, refusal = class_or_refusal(request, class_id)
    if refusal:
        return refusal
    form = await request.form()
    try:
        db.delete_deadline(class_id, form.get("course", ""), int(form.get("step", "0")))
    except ValueError:
        pass
    return back_to_classes("Échéance supprimée.", f"#classe-{class_id}")


@app.post("/admin/classes")
async def admin_class_create(request: Request):
    """Nouvelle classe, qui appartient à son créateur (nom unique parmi ses propres classes)."""
    user = staff_or_none(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    name = (await request.form()).get("name", "").strip()
    if not name:
        return back_to_classes("Donnez un nom à la classe.", err=True)
    class_id = db.create_class(name, user["user_id"])
    if not class_id:
        return back_to_classes(f"Vous avez déjà une classe « {name} ».", err=True)
    return back_to_classes(f"Classe « {name} » créée.", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/courses")
async def admin_class_courses(request: Request, class_id: int):
    user, refusal = class_or_refusal(request, class_id)
    if refusal:
        return refusal
    form = await request.form()
    keys = [k for k in COURSES if form.get(f"course_{k}")]
    db.set_class_courses(class_id, keys)
    return back_to_classes("Labos de la classe mis à jour.", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/members")
async def admin_class_add_members(request: Request, class_id: int):
    """Ajout d'étudiants : cochés parmi ceux que l'utilisateur voit déjà (ses autres classes ; tous pour
    l'administrateur), ou désignés par leur adresse e-mail exacte. Aucune liste des étudiants des autres
    enseignants n'est exposée, et un compte du personnel n'est jamais ajouté."""
    user, refusal = class_or_refusal(request, class_id)
    if refusal:
        return refusal
    form = await request.form()
    visible = visible_student_ids(user)
    if visible is None:
        visible = {s["id"] for s in db.list_students()}
    ids = {int(v) for v in form.getlist("user_ids") if str(v).isdigit() and int(v) in visible}
    unknown = []
    for email in re.split(r"[\s,;]+", form.get("emails", "")):
        if email:
            student_id = db.find_student_by_email(email)
            if student_id:
                ids.add(student_id)
            else:
                unknown.append(email)
    db.add_members(class_id, sorted(ids))
    msg = f"{len(ids)} étudiant(s) ajouté(s)."
    if unknown:
        msg += f" Aucun compte étudiant pour : {', '.join(unknown[:10])}{'…' if len(unknown) > 10 else ''}."
    return back_to_classes(msg, f"#classe-{class_id}", err=bool(unknown))


@app.post("/admin/classes/{class_id}/remove/{user_id}")
async def admin_class_remove_member(request: Request, class_id: int, user_id: int):
    user, refusal = class_or_refusal(request, class_id)
    if refusal:
        return refusal
    db.remove_member(class_id, user_id)
    return back_to_classes("Étudiant retiré de la classe.", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/rename")
async def admin_class_rename(request: Request, class_id: int):
    user, refusal = class_or_refusal(request, class_id)
    if refusal:
        return refusal
    name = (await request.form()).get("name", "").strip()
    if not name or not db.rename_class(class_id, name):
        return back_to_classes("Nom vide ou déjà utilisé.", f"#classe-{class_id}", err=True)
    return back_to_classes("Classe renommée.", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/code")
async def admin_class_new_code(request: Request, class_id: int):
    user, refusal = class_or_refusal(request, class_id)
    if refusal:
        return refusal
    db.regenerate_code(class_id)
    return back_to_classes("Nouveau code généré (l'ancien ne fonctionne plus).", f"#classe-{class_id}")


@app.post("/admin/classes/{class_id}/delete")
async def admin_class_delete(request: Request, class_id: int):
    user, refusal = class_or_refusal(request, class_id)
    if refusal:
        return refusal
    db.delete_class(class_id)
    return back_to_classes("Classe supprimée (les comptes et leur progression sont conservés).")


@app.get("/api/admin/live")
async def admin_live(request: Request):
    """Flux temps réel (Server-Sent Events) pour le tableau de bord, filtré pour chaque connexion : un enseignant
    ne reçoit que la présence et les événements de ses étudiants."""
    user = staff_or_none(request)
    if not user:
        return unauthorized()
    return StreamingResponse(live.stream(request.is_disconnected, live_filter(user)), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/admin/delete-user/{user_id}")
async def admin_delete_user(request: Request, user_id: int):
    """Suppression définitive d'un compte étudiant : administrateur seulement (un enseignant retire l'étudiant
    de sa classe)."""
    if not superadmin_or_none(request):
        return staff_redirect(request)
    target = db.get_user(user_id)
    if target and not target["is_admin"]:
        await remove_containers_safely(user_id)
        db.delete_user(user_id)
    return RedirectResponse("/dashboard", status_code=302)


async def remove_containers_safely(user_id: int, course: dict = None):
    """Supprime les conteneurs de l'étudiant ; si Docker ne répond pas, on le journalise et on continue."""
    try:
        await run_in_threadpool(containers.remove_container, user_id, *([course] if course else []))
    except Exception:
        log.exception("Suppression des conteneurs de l'utilisateur %s impossible", user_id)


@app.post("/admin/reset-user/{user_id}")
async def admin_reset_user(request: Request, user_id: int, course: str = DEFAULT_COURSE):
    user = staff_or_none(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not can_see_student(user, user_id):
        return forbidden_page(request)
    c = get_course(course) or COURSES[DEFAULT_COURSE]
    db.reset_user_progress(user_id, c)
    await remove_containers_safely(user_id, c)
    return RedirectResponse(f"/dashboard?course={c['key']}", status_code=302)


# ─── Comptes enseignants (administrateur seulement) ─────────────────────

def teachers_page(request: Request, user, msg: str = "", err: str = "", new_link: str = "", new_email: str = ""):
    return templates.TemplateResponse(request, "admin_teachers.html", {
        "user": user, "teachers": db.list_teachers(), "invites": db.list_pending_invites(),
        "invite_days": db.INVITE_DAYS, "msg": msg, "err": err, "new_link": new_link, "new_email": new_email,
    })


def back_to_teachers(msg: str = "", err: bool = False):
    key = "err" if err else "msg"
    return RedirectResponse(f"/admin/enseignants?{key}={quote_plus(msg)}" if msg else "/admin/enseignants",
                            status_code=302)


@app.get("/admin/enseignants", response_class=HTMLResponse)
async def admin_teachers(request: Request, msg: str = "", err: str = ""):
    user = superadmin_or_none(request)
    if not user:
        return staff_redirect(request)
    return teachers_page(request, user, msg=msg, err=err)


@app.post("/admin/enseignants/invitation", response_class=HTMLResponse)
async def admin_teacher_invite(request: Request):
    """Lien d'invitation à usage unique, valable INVITE_DAYS jours ; affiché une seule fois (seule son empreinte
    est conservée)."""
    user = superadmin_or_none(request)
    if not user:
        return staff_redirect(request)
    email = (await request.form()).get("email", "").strip().lower()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+", email):
        return teachers_page(request, user, err="Adresse e-mail invalide.")
    token = db.create_invite(user["user_id"], email)
    return teachers_page(request, user, new_link=f"{public_base(request)}/invitation/{token}", new_email=email)


@app.post("/admin/enseignants/invitation/{invite_id}/revoke")
async def admin_teacher_invite_revoke(request: Request, invite_id: int):
    if not superadmin_or_none(request):
        return staff_redirect(request)
    db.revoke_invite(invite_id)
    return back_to_teachers("Invitation annulée : le lien ne fonctionne plus.")


@app.post("/admin/enseignants/{teacher_id}/{action}")
async def admin_teacher_action(request: Request, teacher_id: int, action: str):
    """Désactivation, réactivation ou suppression d'un compte enseignant ; jamais du compte administrateur."""
    user = superadmin_or_none(request)
    if not user:
        return staff_redirect(request)
    target = db.get_user(teacher_id)
    if not target or not target["is_admin"]:
        return back_to_teachers("Compte enseignant inconnu.", err=True)
    if target["is_superadmin"]:
        return back_to_teachers("Le compte administrateur ne peut être ni désactivé ni supprimé.", err=True)
    name = f"{target['first_name']} {target['last_name']}"
    if action == "disable":
        db.set_disabled(teacher_id, True)
        return back_to_teachers(f"Compte de {name} désactivé : ses sessions sont fermées.")
    if action == "enable":
        db.set_disabled(teacher_id, False)
        return back_to_teachers(f"Compte de {name} réactivé.")
    if action == "delete":
        await remove_containers_safely(teacher_id)
        db.delete_teacher(teacher_id, user["user_id"])
        return back_to_teachers(f"Compte de {name} supprimé : ses classes vous sont rattachées, "
                                "les étudiants et leur progression sont conservés.")
    return back_to_teachers("Action inconnue.", err=True)


# ─── Mise en place et validation (fonctions bloquantes, exécutées en thread) ──

# (conteneur, étape) dont la mise en place a été constatée : un conteneur recréé change d'identifiant
_setup_seen: set = set()


def ensure_setup(user_id: int, course: dict, container_id: str, step_num: int, force: bool = False) -> dict:
    """Prépare l'étape dans le conteneur (une fois) et retourne ses données attendues."""
    step = course["steps"][step_num]
    if not runner.has_setup(step):
        return {}
    with user_lock(user_id, course["key"]):
        if not force:
            # Marqueur persistant déjà vu dans ce conteneur : inutile de relancer un docker exec à chaque vérification
            cached = (container_id, step_num) in _setup_seen and not step.get("volatile")
            if cached or containers.exec_in_container(container_id, runner.marker_test_command(step_num, step))[0] == 0:
                data = db.get_setup(user_id, course["key"], step_num)
                if data is not None:
                    _setup_seen.add((container_id, step_num))
                    return data
        code, out = containers.exec_in_container(container_id, runner.setup_command(course, step_num, step))
        data = runner.parse_setup_output(out)
        data["_empreinte"] = runner.setup_fingerprint(step)
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

    exercises = [ex for ex in step["exercises"] if not only or ex["id"] == only]
    to_check = [ex for ex in exercises
                if ex["id"] not in progress["completed"] and not (auto and ex.get("manual"))]
    checked = {}
    if to_check:  # toutes les vérifications en un seul docker exec
        _, out = containers.exec_in_container(container_id, runner.check_batch_command(course, to_check), env=env)
        checked = runner.parse_batch_output(to_check, out)

    results = []
    for ex in exercises:
        res = {"id": ex["id"], "title": ex["title"], "points": ex["points"],
               "passed": False, "already": False, "skipped": False, "message": None, "earned": 0}
        if ex["id"] in progress["completed"]:
            res.update(passed=True, already=True, earned=progress["earned"][ex["id"]])
        elif auto and ex.get("manual"):
            res.update(skipped=True)
        else:
            passed, message = checked[ex["id"]]
            if not auto:  # historique : seulement les vérifications demandées par l'étudiant
                db.record_attempt(user_id, ex["id"], passed, None if passed else message)
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
            "max_score": course["max_score"], "total_exercises": course["total_exercises"],
            **progression.progression(course, p["score"], p["completed"])}


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
    deadlines = db.user_deadlines(user["user_id"], course["key"])
    return [{
        "num": num,
        "title": step["title"],
        "description": step["description"],
        "total": len(step["exercises"]),
        "completed": sum(1 for ex in step["exercises"] if ex["id"] in progress["completed"]),
        "due": deadlines.get(num),
    } for num, step in course["steps"].items()]


@app.get("/api/{course_key}/status")
async def api_status(request: Request, course_key: str):
    """État de l'environnement avant son ouverture, pour prévenir l'étudiant d'un démarrage un peu long."""
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    if not course:
        return not_found()
    try:
        status = await run_in_threadpool(containers.container_status, user["user_id"], course)
    except Exception:
        status = "unknown"
    return {"status": status, "idle_hours": round(IDLE_TIMEOUT / 3600, 1)}


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
        "reply": progression.reply(ticket, ex["id"]),
    }


def exercise_payload(ex: dict, progress: dict, hints: dict, attempts: dict = None) -> dict:
    used = hints.get(ex["id"], 0)
    all_hints = ex.get("hints", [])
    history = (attempts or {}).get(ex["id"], {"count": 0, "items": []})
    return {
        "attempts": history["items"],
        "attempts_total": history["count"],
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
    attempts = db.get_attempts(user["user_id"], [ex["id"] for ex in step["exercises"]])
    return {
        "num": num,
        "title": step["title"],
        "description": step["description"],
        "lesson": step.get("lesson", ""),
        "has_setup": runner.has_setup(step),
        # Étape modifiée depuis sa préparation : l'étudiant est invité à la réinitialiser
        "setup_outdated": runner.setup_outdated(course, num, step, db.get_setup(user["user_id"], course["key"], num)),
        # Épreuve : ni indices ni correction affichée aux étudiants
        "exam": bool(course.get("exam")),
        # QCM de fin de cours : absent, à faire (None) ou (points, maximum)
        "quiz": ({"done": db.quiz_scores(user["user_id"], course["key"]).get(num), "max": QUIZ_QUESTIONS}
                 if num in course["quiz"] else None),
        "mentor": CHARACTERS[course["mentor"]]["name"].split()[0],
        "due": db.user_deadlines(user["user_id"], course["key"]).get(num),
        "exercises": [exercise_payload(ex, progress, hints, attempts) for ex in step["exercises"]],
    }


@app.get("/api/{course_key}/quiz/{num}")
async def api_quiz(request: Request, course_key: str, num: int):
    """QCM de fin de cours de l'étape : les questions (sans les réponses) ou, après la tentative, le corrigé."""
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    if not course or num not in course["quiz"]:
        return not_found()
    done = db.get_quiz_result(user["user_id"], course["key"], num)
    if done:
        return {"done": True, **done}
    return {"done": False, "max": QUIZ_QUESTIONS,
            "questions": quiz.public(quiz.draw(user["user_id"], course, num))}


@app.post("/api/{course_key}/quiz/{num}")
async def api_quiz_answer(request: Request, course_key: str, num: int):
    """Une seule tentative : corrige, enregistre les points, renvoie le corrigé et la progression."""
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    if not course or num not in course["quiz"]:
        return not_found()
    try:
        answers = (await request.json()).get("answers", [])
    except Exception:
        answers = []
    drawn = quiz.draw(user["user_id"], course, num)
    points, details = quiz.grade(drawn, answers if isinstance(answers, list) else [])
    if db.save_quiz_result(user["user_id"], course["key"], num, points, len(drawn), details):
        live.publish({"type": "quiz", "user_id": user["user_id"], "name": live.names.get(user["user_id"]),
                      "course": course["key"], "step": num, "score": points, "max": len(drawn)})
    return {"done": True, **db.get_quiz_result(user["user_id"], course["key"], num),
            "progress": progress_payload(user["user_id"], course)}


@app.get("/api/{course_key}/attempts/{exercise_id}")
async def api_attempts(request: Request, course_key: str, exercise_id: str):
    """Historique des vérifications d'un exercice (mis à jour après chaque vérification)."""
    user = get_current_user(request)
    if not user:
        return unauthorized()
    course = course_for(user, course_key)
    key, _, _, ex = get_exercise(exercise_id)
    if not course or not ex or key != course["key"]:
        return not_found()
    h = db.get_attempts(user["user_id"], [exercise_id]).get(exercise_id, {"count": 0, "items": []})
    return {"attempts": h["items"], "attempts_total": h["count"]}


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
    """Correction d'un exercice : pour les comptes admin, et pour l'étudiant qui a réussi l'exercice
    (correction commentée, sans le détail des vérifications)."""
    user = get_current_user(request)
    if not user:
        return unauthorized()
    key, _, _, ex = get_exercise(exercise_id)
    sol = solutions.for_exercise(exercise_id)
    if not ex or not sol:
        return not_found()
    if not user.get("is_admin"):
        course = course_for(user, key)
        if course and course.get("exam"):
            return JSONResponse({"error": "Pas de correction pendant une épreuve"}, status_code=403)
        if not course or exercise_id not in db.get_user_score(user["user_id"], course["id_glob"])["completed"]:
            return JSONResponse({"error": "Correction disponible une fois l'exercice réussi"}, status_code=403)
        return {"exercise": exercise_id, "preamble": sol["preamble"], "code": sol["code"],
                "explanation": sol["explanation"], "manual": bool(ex.get("manual"))}
    return {
        "exercise": exercise_id,
        "preamble": sol["preamble"],
        "code": sol["code"],
        "explanation": sol["explanation"],
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
    await remove_containers_safely(user["user_id"], course)
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
    term_id = terminals.opened(key)
    live.remember_name(user)
    live.terminal_opened(user_id, course["key"])
    raw_sock = sock._sock
    raw_sock.setblocking(False)
    loop = asyncio.get_running_loop()

    def save_input(kind, text):  # suivi d'intégrité (écriture en base hors de la boucle asyncio)
        step = live.presence.get(key, {}).get("step")
        loop.run_in_executor(None, db.log_terminal, user_id, course["key"], step, kind, text)
    recorder = integrity.InputRecorder(save_input)

    async def read_from_container():
        try:
            while True:
                data = await loop.sock_recv(raw_sock, 4096)
                if not data:
                    break
                terminals.feed(key, term_id, data)  # copie pour l'enseignant qui regarde (lecture seule)
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
                    recorder.feed(payload["data"])
                elif payload.get("type") == "resize":
                    rows, cols = int(payload.get("rows", 24)), int(payload.get("cols", 80))
                    containers.resize_exec(exec_id, rows=rows, cols=cols)
                    terminals.resized(key, term_id, cols, rows)
            elif msg.get("bytes") is not None:
                await loop.sock_sendall(raw_sock, msg["bytes"])
                recorder.feed(msg["bytes"].decode(errors="replace"))
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        open_terminals[key] -= 1
        terminals.closed(key, term_id)
        live.terminal_closed(user_id, course["key"])
        reader_task.cancel()
        try:
            raw_sock.close()
        except Exception:
            pass


# ─── Terminal d'un étudiant, vu par l'enseignant (lecture seule) ────────

@app.get("/admin/terminal/{user_id}", response_class=HTMLResponse)
async def admin_watch_page(request: Request, user_id: int, course: str = DEFAULT_COURSE):
    user = staff_or_none(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    c = get_course(course) or COURSES[DEFAULT_COURSE]
    target = db.get_user(user_id)
    if not target:
        return RedirectResponse(f"/dashboard?course={c['key']}", status_code=302)
    if not can_see_student(user, user_id):
        return forbidden_page(request)
    return templates.TemplateResponse(request, "watch.html", {
        "user": user, "target": target, "course": c,
    })


@app.websocket("/ws/watch")
async def websocket_watch(ws: WebSocket):
    """Recopie la sortie des terminaux ouverts d'un étudiant ; les messages reçus de l'enseignant sont ignorés."""
    user = db.get_session(ws.cookies.get("session"))
    course = get_course(ws.query_params.get("course", DEFAULT_COURSE))
    try:
        target_id = int(ws.query_params.get("user", ""))
    except ValueError:
        target_id = None
    if not user or not user.get("is_admin") or not course or target_id is None:
        await ws.close(code=4001, reason="Unauthorized")
        return
    if not can_see_student(user, target_id):  # un enseignant ne regarde que ses étudiants
        await ws.close(code=4003, reason="Forbidden")
        return
    await ws.accept()
    key = (target_id, course["key"])
    q = terminals.subscribe(key)

    async def drain_input():
        # Lecture seule : on consomme les messages uniquement pour détecter la déconnexion
        while (await ws.receive())["type"] != "websocket.disconnect":
            pass

    input_task = asyncio.ensure_future(drain_input())
    try:
        await ws.send_text(json.dumps({"type": "hello", "open": terminals.is_open(key)}))
        while not input_task.done():
            try:
                kind, term_id, data = await asyncio.wait_for(q.get(), timeout=15)
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "ping"}))
                continue
            if kind == "data":
                await ws.send_bytes(term_id.to_bytes(4, "big") + data)
            elif kind == "size":
                await ws.send_text(json.dumps({"type": "size", "term": term_id, "cols": data[0], "rows": data[1]}))
            else:
                await ws.send_text(json.dumps({"type": kind, "term": term_id}))
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        input_task.cancel()
        terminals.unsubscribe(key, q)
