"""Banc de test des exercices, dans un vrai conteneur de lab.

Pour chaque étape (dans l'ordre du parcours, comme un étudiant) :
  1. exécute la mise en place ;
  2. vérifie qu'AUCUN exercice ne passe avant d'avoir été fait (pas de points gratuits) ;
  3. exécute la solution de référence en tant qu'etudiant ;
  4. vérifie que TOUS les exercices passent.

Usage (depuis la racine du dépôt, images construites avec
`docker build -t linux-lab ./images/linux`, `docker build -t jest-lab ./images/jest`, etc.) :
    python platform/tests/run_lab_tests.py              # toutes les étapes du parcours Linux
    python platform/tests/run_lab_tests.py --course jest
    python platform/tests/run_lab_tests.py --skip 13    # sans l'étape qui a besoin d'Internet
    python platform/tests/run_lab_tests.py --only 1-5   # jusqu'à l'étape 5
    python platform/tests/run_lab_tests.py --keep       # garde le conteneur pour inspection

Seul le client `docker` est nécessaire (pas de dépendance Python).
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
# Sortie redirigée sous Windows (cp1252) : les caractères « ─ » ou « É » feraient planter l'affichage
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app import runner  # noqa: E402
from app.courses import COURSES  # noqa: E402
from app.solutions import SCRIPTS, check_coverage  # noqa: E402

CONTAINER = "lab-test-runner"
NETWORK = "linux-lab-test"


def docker(*args, input=None, check=False):
    # Entrée en binaire : en mode texte, Windows convertirait les \n en \r\n
    r = subprocess.run(["docker", *args], input=input.encode() if input is not None else None,
                       capture_output=True)
    r.stdout = r.stdout.decode("utf-8", errors="replace")
    r.stderr = r.stderr.decode("utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"docker {' '.join(args[:3])}… : {r.stderr.strip()}")
    return r


def dexec(argv, env=None, user="root", input=None):
    opts = ["exec", *(["-i"] if input is not None else []), "-u", user, "-w", "/home/etudiant"]
    for k, v in (env or {}).items():
        opts += ["-e", f"{k}={v}"]
    r = docker(*opts, CONTAINER, *argv, input=input)
    return r.returncode, r.stdout, r.stderr


def run_checks(course, step, env):
    out = {}
    for ex in step["exercises"]:
        code, stdout, _ = dexec(runner.check_command(course, ex), env=env)
        out[ex["id"]] = runner.parse_check_output(ex, code, stdout)
    return out


def parse_range(spec):
    nums = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            nums.update(range(int(a), int(b) + 1))
        elif part:
            nums.add(int(part))
    return nums


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="étapes à exécuter, ex. 1-5,8")
    ap.add_argument("--skip", default="", help="étapes à ignorer, ex. 13")
    ap.add_argument("--keep", action="store_true", help="ne pas supprimer le conteneur à la fin")
    ap.add_argument("--course", default="linux", choices=sorted(COURSES))
    ap.add_argument("--image", default=None, help="image à tester (par défaut celle du parcours)")
    args = ap.parse_args()

    check_coverage(COURSES)
    course = COURSES[args.course]
    STEPS = course["steps"]
    SOLUTIONS = SCRIPTS[args.course]
    image = args.image or course["image"]

    steps = sorted(STEPS)
    if args.only:
        wanted = parse_range(args.only)
        # Les étapes s'enchaînent : on joue aussi les précédentes
        steps = [n for n in steps if n <= max(wanted)]
    skipped = parse_range(args.skip)

    docker("rm", "-f", CONTAINER)
    if docker("network", "inspect", NETWORK).returncode != 0:
        docker("network", "create", "-o", "com.docker.network.bridge.enable_icc=false", NETWORK, check=True)
    extra = []
    if course.get("docker_in_docker"):
        # Sur un poste de développement (Docker Desktop), Sysbox n'est pas disponible : mode privilégié
        runtime = os.environ.get("DOCKER_LAB_RUNTIME", "privileged")
        extra = ["--privileged"] if runtime == "privileged" else [f"--runtime={runtime}"]
        extra += ["-v", "/var/lib/docker"]
    docker("run", "-d", "--init", "--name", CONTAINER, "--hostname", "linux-lab", "--network", NETWORK,
           "--memory", course["mem_limit"], "--pids-limit", str(course["pids_limit"]), *extra, image, check=True)
    time.sleep(2)
    dexec(["bash", "-c", "echo 'etudiant ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/zz-test && chmod 440 /etc/sudoers.d/zz-test"])

    problems = []
    t0 = time.time()
    try:
        for num in steps:
            if num in skipped:
                print(f"── Étape {num:2d} : ignorée")
                continue
            step = STEPS[num]
            ts = time.time()
            data = {}
            if runner.has_setup(step):
                code, stdout, stderr = dexec(runner.setup_command(course, num, step))
                data = runner.parse_setup_output(stdout)
                if code != 0:
                    problems.append(f"{num} : setup en échec (code {code}) {stderr.strip()[-500:]}")
            env = runner.check_env(data)

            for ex_id, (passed, _) in run_checks(course, step, env).items():
                if passed:
                    problems.append(f"{ex_id} : valide AVANT la solution (points gratuits)")

            sol = SOLUTIONS.get(num)
            if not sol:
                problems.append(f"{num} : pas de solution de référence")
                continue
            dexec(["bash", "-c", "cat > /tmp/solution.sh && chmod 755 /tmp/solution.sh"], input=sol)
            _, _, sol_err = dexec(["bash", "/tmp/solution.sh"], user="etudiant")

            failed = []
            for ex_id, (passed, msg) in run_checks(course, step, env).items():
                if not passed:
                    failed.append(ex_id)
                    problems.append(f"{ex_id} : échoue APRÈS la solution → {msg}")
            status = "OK " if not failed else "KO "
            print(f"── Étape {num:2d} : {status} ({time.time() - ts:5.1f} s) {step['title']}"
                  + (f"  [échecs : {', '.join(failed)}]" if failed else ""))
            if failed and sol_err.strip():
                print("   stderr de la solution :", sol_err.strip()[-800:].replace("\n", "\n   "))
    finally:
        if not args.keep:
            docker("rm", "-f", CONTAINER)

    print(f"\nDurée : {time.time() - t0:.0f} s")
    if problems:
        print(f"\n{len(problems)} problème(s) :")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("Tous les exercices se comportent comme prévu.")


if __name__ == "__main__":
    main()
