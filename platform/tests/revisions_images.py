"""Empreintes du contenu des images de lab (dossiers images/<parcours>).

La plateforme recrée le conteneur d'un étudiant quand l'empreinte de l'image de son parcours change (nouveaux
fichiers, outils…), et seulement dans ce cas : une simple reconstruction de l'image, qui change son identifiant
sans changer son contenu, ne dérange plus les étudiants en plein cours.

Après toute modification d'un dossier images/<parcours> :
    python platform/tests/revisions_images.py          # met à jour platform/app/revisions_images.json
(tests/test_platform.py vérifie que le fichier est à jour.)
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGET = os.path.join(ROOT, "platform", "app", "revisions_images.json")
COURSES = ("linux", "jest", "docker", "git", "ansible", "reseau", "projet")


def revision(course: str) -> str:
    """Empreinte des fichiers de images/<parcours> (chemins et contenus ; fins de ligne normalisées, pour
    obtenir la même empreinte sous Windows et sous Linux)."""
    base = os.path.join(ROOT, "images", course)
    h = hashlib.sha256()
    for folder, dirs, files in sorted(os.walk(base)):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(folder, name)
            h.update(os.path.relpath(path, base).replace(os.sep, "/").encode())
            with open(path, "rb") as f:
                h.update(f.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def all_revisions() -> dict:
    return {c: revision(c) for c in COURSES}


if __name__ == "__main__":
    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        json.dump(all_revisions(), f, indent=1, sort_keys=True)
        f.write("\n")
    print(open(TARGET, encoding="utf-8").read())
