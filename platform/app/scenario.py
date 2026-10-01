"""Univers commun aux parcours : l'entreprise fictive et ses personnages.

Les labos peuvent être suivis dans n'importe quel ordre : chacun présente l'entreprise et l'équipe avec
contexte(), sans supposer qu'un autre labo a été fait avant.
"""
from html import escape

COMPANY = "Cimes & Sentiers"

CHARACTERS = {
    "sophie": {"name": "Sophie Marchand", "role": "DSI, votre responsable", "color": "#6c5ce7"},
    "lea": {"name": "Léa Nguyen", "role": "Admin système senior, votre mentore", "color": "#00a383"},
    "thomas": {"name": "Thomas Leroy", "role": "Développeur web", "color": "#d35400"},
    "julien": {"name": "Julien Petit", "role": "Stagiaire", "color": "#b7950b"},
    "diallo": {"name": "Aminata Diallo", "role": "Responsable comptabilité", "color": "#0e8f8c"},
    "nadia": {"name": "Nadia Haddad", "role": "Lead développeuse, votre mentore", "color": "#c0392b"},
}

# Présentation de chacun, indépendante du labo (le rôle de mentore dépend du labo : voir contexte())
_CAST = [
    ("sophie", "DSI, votre responsable : c'est elle qui fixe les priorités"),
    ("lea", "admin système senior : serveurs, réseau, automatisation"),
    ("nadia", "lead développeuse : le code de la boutique et la qualité"),
    ("thomas", "développeur web"),
    ("diallo", "responsable comptabilité, utilisatrice exigeante"),
    ("julien", "stagiaire, plein de bonne volonté… et souvent perdu"),
]


def initials(key: str) -> str:
    return "".join(w[0] for w in CHARACTERS[key]["name"].split()[:2])


def contexte(mentor: str = None, independant: bool = True) -> str:
    """Présentation de l'entreprise et de l'équipe, affichée au début de chaque labo.

    mentor : le personnage qui donne les indices dans ce labo (None : pas d'indice, comme dans l'épreuve).
    independant : rappeler que le labo se suit sans avoir fait les autres.
    """
    cast = []
    for key, desc in _CAST:
        p = CHARACTERS[key]
        badge = ' <span class="cast-mentor">votre mentore dans ce labo</span>' if key == mentor else ""
        cast.append(f'<li><span class="cast-avatar" style="background:{p["color"]}">{initials(key)}</span>'
                    f'<span><strong>{escape(p["name"])}</strong>{badge}<br><small>{escape(desc)}</small></span></li>')
    aide = (f"<p>Bloqué·e ? {escape(CHARACTERS[mentor]['name'].split()[0])} vous donne des <strong>indices</strong> "
            "sous chaque ticket (chacun coûte un point).</p>") if mentor else ""
    seul = ("<p class=\"company-note\">Chaque labo est une mission à part entière : il n'est pas nécessaire "
            "d'avoir suivi les autres, ni de les faire dans un ordre particulier.</p>") if independant else ""
    return (
        '<div class="scenario company"><h3>L\'entreprise : Cimes &amp; Sentiers</h3>'
        "<p><strong>Cimes &amp; Sentiers</strong> est une PME de 40 salariés qui vend du matériel de randonnée, "
        "en ligne et dans ses magasins. Vous faites partie de son <strong>équipe informatique</strong> : selon "
        "les missions, vous épaulez les administrateurs système ou l'équipe de développement.</p>"
        "<p>Votre prédécesseur, <strong>Marc Dumas</strong>, a quitté l'entreprise précipitamment. Il a laissé "
        "des notes éparpillées, des scripts obscurs et des installations que personne ne sait refaire : vous "
        "croiserez souvent son travail.</p>"
        "<p>Les demandes de vos collègues arrivent sous forme de <strong>tickets</strong> (onglet "
        "<em>Exercices</em>). Le cours de chaque étape est votre documentation : lisez-le, puis traitez les "
        "tickets.</p>"
        f'<ul class="cast">{"".join(cast)}</ul>{aide}{seul}</div>'
    )
