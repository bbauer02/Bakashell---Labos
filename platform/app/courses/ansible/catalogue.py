"""Parcours « Ansible : automatiser l'infrastructure ».

L'étudiant travaille sur un poste de contrôle (Ansible, sans sudo). Les serveurs de l'entreprise (web1, web2, db1,
puis web3) sont de vrais conteneurs Debian avec SSH, qui tournent dans le moteur Docker interne du conteneur de
l'étudiant (runtime Sysbox en production). L'étudiant n'a pas accès à ce moteur : pour lui, ce sont des serveurs
distants, joignables uniquement en SSH. Un dépôt APT interne (depot.cimes.lan) fournit les paquets sans Internet.

Les vérifications (en root sur le poste de contrôle) observent le résultat réel sur les serveurs (docker exec,
requêtes HTTP, connexion à Redis) et, pour les exercices « manual », rejouent les playbooks de l'étudiant en tant
qu'etudiant pour juger leur idempotence.
"""

EXERCISES_VERSION = "1"

MENTOR = "lea"

SETUP_PRELUDE = r'''
set -e
H=/home/etudiant
I=$H/infra
emit() { echo "@$1=$2"; }
own() { chown -R etudiant:etudiant "$@"; }
# Attend le moteur Docker interne et l'image des serveurs (premier démarrage : environ 30 s)
for _ in $(seq 1 150); do [ -f /run/lab-ready ] && docker info >/dev/null 2>&1 && break; sleep 1; done
docker image inspect noeud-cimes:1 >/dev/null 2>&1 || { echo "Les serveurs ne sont pas prêts" >&2; exit 1; }
declare -A IP=([web1]=11 [web2]=12 [web3]=13 [db1]=21)
# serveur <nom> : démarre le serveur (le crée s'il n'existe pas), et attend son SSH
serveur() {
  if docker inspect "$1" >/dev/null 2>&1; then docker start "$1" >/dev/null
  # SYS_PTRACE : comme sur une vraie machine, root peut identifier les processus des autres comptes
  # (start-stop-daemon --exec en a besoin pour arrêter redis-server, qui tourne sous le compte redis)
  else docker run -d --name "$1" --hostname "$1" --network cimes --ip "10.10.0.${IP[$1]}" --cap-add SYS_PTRACE \
         --add-host depot.cimes.lan:10.10.0.1 --restart unless-stopped --init noeud-cimes:1 >/dev/null
  fi
  for _ in $(seq 1 40); do docker exec "$1" pgrep -x sshd >/dev/null 2>&1 && return 0; sleep 0.5; done
  echo "Le serveur $1 ne démarre pas" >&2; return 1
}
# neuf <nom> : serveur réinstallé à neuf (nouvelle empreinte SSH : on l'oublie côté étudiant)
neuf() {
  docker rm -f "$1" >/dev/null 2>&1 || true
  [ -f $H/.ssh/known_hosts ] && su etudiant -s /bin/bash -c "ssh-keygen -q -R $1 >/dev/null 2>&1; ssh-keygen -q -R 10.10.0.${IP[$1]} >/dev/null 2>&1" || true
  serveur "$1"
}
sur() { docker exec "$1" bash -c "$2"; }
mkdir -p $I/reponses
own $I
'''

CHECK_PRELUDE = r'''
H=/home/etudiant
I=$H/infra
ans() { tr -d '[:space:]' < "$1" 2>/dev/null; }
# sur <serveur> <commande> : exécutée sur le serveur géré
sur() { docker exec "$1" bash -c "$2" 2>/dev/null; }
# etu <commande> : exécutée par l'étudiant, depuis ~/infra (sa configuration Ansible s'applique)
etu() { su - etudiant -c "cd $I && ANSIBLE_NOCOLOR=1 ANSIBLE_PYTHON_INTERPRETER=auto_silent $1" </dev/null 2>/dev/null; }
page() { curl -fsS --max-time 5 "http://$1/"; }
yjson() { python3 -c 'import sys, yaml, json; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))' "$1" 2>/dev/null; }
# var <serveur> <variable> : valeur d'une variable d'inventaire (group_vars, host_vars…) pour ce serveur
var() { etu "ansible-inventory --host $1" | jq -r ".$2 // empty"; }
groupe() { etu "ansible-inventory -i inventaire.ini --list" | jq -r ".$1.hosts // [] | sort | join(\",\")"; }
ssh_ok() { etu "ssh -o BatchMode=yes -o ConnectTimeout=5 admin@$1 true" >/dev/null; }
# joue <playbook> [options] : lance le playbook de l'étudiant ; échoue si un serveur est en échec ou injoignable
joue() { etu "ansible-playbook $* 2>&1" > /tmp/lab-jeu.txt; grep -qE "^[a-z0-9]+ +: ok=" /tmp/lab-jeu.txt && ! grep -qE "failed=[1-9]|unreachable=[1-9]" /tmp/lab-jeu.txt; }
rien_change() { ! grep -qE "changed=[1-9]" /tmp/lab-jeu.txt; }
# recap : récapitulatif (ou erreur) du dernier jeu, affiché sous le message d'échec
recap() { grep -E "^[a-z0-9]+ +: ok=|ERROR!|fatal:" /tmp/lab-jeu.txt | head -3 | cut -c1-160 | sed 's/^/MSG:/'; return 1; }
# redis <commande>... : envoie des commandes à Redis sur db1 et affiche la dernière réponse
redis() ( exec 3<>/dev/tcp/10.10.0.21/6379 || exit 1; printf '%s\r\n' "$@" >&3; for _ in "$@"; do read -t 3 -r l <&3 || break; done; echo "${l%$'\r'}" )
'''

# ─── Schémas des cours (SVG en ligne, styles .schema de lab.html) ─────────────────────────────────

def _fleches(i):
    return (f'<defs><marker id="fl{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            f'<path class="pa" d="M0,0 L10,5 L0,10 z"/></marker>'
            f'<marker id="fg{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            f'<path class="pt" d="M0,0 L10,5 L0,10 z"/></marker>'
            f'<marker id="fw{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            f'<path class="pw" d="M0,0 L10,5 L0,10 z"/></marker></defs>')


SCHEMA_SSH = f"""<figure class="schema"><svg viewBox="0 0 640 250" role="img" aria-label="Le poste de contrôle se connecte en SSH à chaque serveur">{_fleches(1)}
<rect class="a" x="16" y="30" width="200" height="190" rx="10"/>
<text class="ttl" x="30" y="56">Poste de contrôle</text>
<text class="t2" x="30" y="76">Ansible est installé ici, et seulement ici</text>
<text class="mono" x="30" y="108">inventaire.ini</text><text class="t2" x="130" y="108">quels serveurs</text>
<text class="mono" x="30" y="132">web.yml</text><text class="t2" x="130" y="132">quoi faire</text>
<text class="mono" x="30" y="156">ansible.cfg</text><text class="t2" x="130" y="156">réglages</text>
<text class="mono" x="30" y="180">~/.ssh/id_ed25519</text><text class="t2" x="30" y="200">clé privée : l'accès aux serveurs</text>
<rect class="b" x="430" y="18" width="194" height="58" rx="8"/><text x="444" y="42">web1</text><text class="t2" x="444" y="62">sshd · python3 · aucun agent</text>
<rect class="b" x="430" y="96" width="194" height="58" rx="8"/><text x="444" y="120">web2</text><text class="t2" x="444" y="140">sshd · python3 · aucun agent</text>
<rect class="b" x="430" y="174" width="194" height="58" rx="8"/><text x="444" y="198">db1</text><text class="t2" x="444" y="218">sshd · python3 · aucun agent</text>
<path class="la" d="M216,125 C320,125 320,47 428,47" marker-end="url(#fl1)"/>
<path class="la" d="M216,125 L428,125" marker-end="url(#fl1)"/>
<path class="la" d="M216,125 C320,125 320,203 428,203" marker-end="url(#fl1)"/>
<text class="t2" x="296" y="116">SSH (port 22)</text>
</svg><figcaption>Ansible « pousse » les changements depuis le poste de contrôle : rien à installer sur les serveurs, à part SSH et Python.</figcaption></figure>"""

SCHEMA_MODULE = f"""<figure class="schema"><svg viewBox="0 0 640 200" role="img" aria-label="Le module est copié sur le serveur, exécuté, puis supprimé">{_fleches(2)}
<rect class="a" x="10" y="20" width="170" height="160" rx="10"/>
<text class="ttl" x="24" y="46">Poste de contrôle</text>
<text class="mono" x="24" y="76">ansible web1 -m ping</text>
<text class="t2" x="24" y="104">① emballe le module</text><text class="mono" x="24" y="120">AnsiballZ_ping.py</text>
<text class="t2" x="24" y="160">⑤ affiche le résultat</text>
<rect class="b" x="440" y="20" width="190" height="160" rx="10"/>
<text class="ttl" x="454" y="46">web1</text>
<text class="t2" x="454" y="76">③ python3 AnsiballZ_ping.py</text>
<text class="t2" x="454" y="96">   (avec sudo si « become »)</text>
<text class="t2" x="454" y="124">④ supprime le fichier</text>
<text class="mono" x="454" y="152">~/.ansible/tmp/…</text>
<path class="la" d="M182,70 L436,70" marker-end="url(#fl2)"/><text class="t2" x="230" y="62">② copie par SSH (sftp)</text>
<path class="l" d="M436,150 L184,150" marker-end="url(#fg2)"/><text class="t2" x="230" y="142">résultat en JSON : ok, changed…</text>
</svg><figcaption>Chaque tâche suit ce trajet. L'option <code>-vvv</code> affiche toutes ces étapes.</figcaption></figure>"""

SCHEMA_IDEMPOTENCE = f"""<figure class="schema"><svg viewBox="0 0 640 190" role="img" aria-label="Le module compare l'état désiré et l'état actuel">{_fleches(3)}
<rect class="a" x="10" y="16" width="190" height="62" rx="8"/><text class="ttl" x="22" y="40">État désiré</text><text class="mono" x="22" y="62">nginx : installé</text>
<rect class="b" x="10" y="108" width="190" height="62" rx="8"/><text class="ttl" x="22" y="132">État actuel du serveur</text><text class="t2" x="22" y="154">nginx installé ? oui / non</text>
<rect class="b" x="250" y="62" width="150" height="62" rx="8"/><text x="264" y="88">Le module</text><text class="t2" x="264" y="108">compare les deux</text>
<path class="l" d="M200,47 L248,82" marker-end="url(#fg3)"/><path class="l" d="M200,139 L248,106" marker-end="url(#fg3)"/>
<rect class="g" x="440" y="10" width="190" height="46" rx="8"/><text x="452" y="30">ok</text><text class="t2" x="452" y="47">déjà conforme : rien à faire</text>
<rect class="w" x="440" y="70" width="190" height="46" rx="8"/><text x="452" y="90">changed</text><text class="t2" x="452" y="107">modifié pour être conforme</text>
<rect class="r" x="440" y="130" width="190" height="46" rx="8"/><text x="452" y="150">failed</text><text class="t2" x="452" y="167">impossible : erreur expliquée</text>
<path class="l" d="M400,86 L438,33" marker-end="url(#fg3)"/><path class="l" d="M400,93 L438,93" marker-end="url(#fg3)"/><path class="l" d="M400,100 L438,153" marker-end="url(#fg3)"/>
</svg><figcaption>On décrit un état, pas une suite de commandes : relancer la même tâche ne refait que ce qui manque. C'est l'idempotence.</figcaption></figure>"""

SCHEMA_PLAYBOOK = f"""<figure class="schema"><svg viewBox="0 0 640 250" role="img" aria-label="Un playbook contient des plays, qui contiennent des tâches">{_fleches(4)}
<rect class="b" x="8" y="8" width="420" height="234" rx="10"/><text class="ttl" x="22" y="32">Playbook</text><text class="mono" x="100" y="32">web.yml</text>
<rect class="a" x="22" y="44" width="392" height="186" rx="8"/><text x="36" y="68">Play : « Serveurs web »</text>
<text class="mono" x="36" y="88">hosts: web   become: true</text>
<rect class="g" x="36" y="102" width="364" height="54" rx="6"/><text x="48" y="124">Tâche 1 : Installer nginx</text><text class="mono" x="48" y="144">ansible.builtin.apt</text>
<rect class="g" x="36" y="166" width="364" height="54" rx="6"/><text x="48" y="188">Tâche 2 : Démarrer nginx</text><text class="mono" x="48" y="208">ansible.builtin.service</text>
<rect class="b" x="480" y="80" width="150" height="40" rx="8"/><text x="494" y="105">web1</text>
<rect class="b" x="480" y="140" width="150" height="40" rx="8"/><text x="494" y="165">web2</text>
<path class="la" d="M414,110 L478,100" marker-end="url(#fl4)"/><path class="la" d="M414,130 L478,158" marker-end="url(#fl4)"/>
<text class="t2" x="480" y="210">chaque tâche est jouée sur</text><text class="t2" x="480" y="226">tous les serveurs, puis la suivante</text>
</svg><figcaption>Un playbook est une liste de plays ; un play associe des serveurs (<code>hosts</code>) à une liste de tâches ; chaque tâche appelle un module.</figcaption></figure>"""

SCHEMA_VARIABLES = f"""<figure class="schema"><svg viewBox="0 0 640 240" role="img" aria-label="Les variables et les facts alimentent un modèle Jinja2">{_fleches(5)}
<rect class="b" x="8" y="10" width="200" height="56" rx="8"/><text class="mono" x="20" y="32">group_vars/web.yml</text><text class="t2" x="20" y="52">environnement: production</text>
<rect class="w" x="8" y="84" width="200" height="56" rx="8"/><text class="mono" x="20" y="106">host_vars/web2.yml</text><text class="t2" x="20" y="126">environnement: recette</text>
<rect class="b" x="8" y="158" width="200" height="66" rx="8"/><text x="20" y="180">Facts (collectés)</text><text class="mono" x="20" y="200">ansible_default_ipv4</text><text class="t2" x="20" y="216">IP, OS, mémoire…</text>
<rect class="a" x="250" y="70" width="170" height="92" rx="8"/><text class="ttl" x="262" y="94">Modèle Jinja2</text><text class="mono" x="262" y="116">index.html.j2</text><text class="mono" x="262" y="136">{{{{ inventory_hostname }}}}</text><text class="mono" x="262" y="152">{{{{ environnement }}}}</text>
<path class="l" d="M208,38 L248,92" marker-end="url(#fg5)"/><path class="l" d="M208,112 L248,116" marker-end="url(#fg5)"/><path class="l" d="M208,190 L248,140" marker-end="url(#fg5)"/>
<rect class="g" x="460" y="36" width="170" height="62" rx="8"/><text x="472" y="58">web1 : index.html</text><text class="t2" x="472" y="78">web1 · production</text><text class="t2" x="472" y="92">10.10.0.11</text>
<rect class="g" x="460" y="134" width="170" height="62" rx="8"/><text x="472" y="156">web2 : index.html</text><text class="t2" x="472" y="176">web2 · recette</text><text class="t2" x="472" y="190">10.10.0.12</text>
<path class="la" d="M420,100 L458,68" marker-end="url(#fl5)"/><path class="la" d="M420,132 L458,164" marker-end="url(#fl5)"/>
</svg><figcaption>Un seul modèle, un fichier différent par serveur. La variable de l'hôte (host_vars) l'emporte sur celle du groupe (group_vars).</figcaption></figure>"""

SCHEMA_HANDLERS = f"""<figure class="schema"><svg viewBox="0 0 640 210" role="img" aria-label="Un handler ne s'exécute que si une tâche qui le notifie a changé quelque chose">{_fleches(6)}
<text class="ttl" x="10" y="26">1er passage : la configuration change</text>
<rect class="g" x="10" y="38" width="130" height="44" rx="6"/><text x="20" y="58">apt nginx</text><text class="t2" x="20" y="74">ok</text>
<rect class="w" x="160" y="38" width="170" height="44" rx="6"/><text x="170" y="58">template site.conf</text><text class="t2" x="170" y="74">changed → notify</text>
<rect class="g" x="350" y="38" width="110" height="44" rx="6"/><text x="360" y="58">copy page</text><text class="t2" x="360" y="74">ok</text>
<rect class="a" x="490" y="38" width="140" height="44" rx="6"/><text x="500" y="58">handler</text><text class="t2" x="500" y="74">recharge nginx</text>
<path class="l" d="M140,60 L158,60"/><path class="l" d="M330,60 L348,60"/><path class="l" d="M460,60 L488,60" marker-end="url(#fg6)"/>
<path class="ld" d="M245,82 C245,112 560,112 560,84" marker-end="url(#fw6)"/><text class="t2" x="330" y="120">exécuté une fois, à la fin du play</text>
<text class="ttl" x="10" y="152">2e passage : rien n'a changé</text>
<rect class="g" x="10" y="162" width="130" height="40" rx="6"/><text x="20" y="187">apt nginx : ok</text>
<rect class="g" x="160" y="162" width="170" height="40" rx="6"/><text x="170" y="187">template : ok</text>
<rect class="g" x="350" y="162" width="110" height="40" rx="6"/><text x="360" y="187">copy : ok</text>
<rect class="b" x="490" y="162" width="140" height="40" rx="6"/><text class="t2" x="500" y="187">handler non exécuté</text>
<path class="l" d="M140,182 L158,182"/><path class="l" d="M330,182 L348,182"/><path class="l" d="M460,182 L488,182"/>
</svg><figcaption>Le service n'est rechargé que si sa configuration a réellement changé : pas de coupure inutile.</figcaption></figure>"""

SCHEMA_ROLES = f"""<figure class="schema"><svg viewBox="0 0 640 230" role="img" aria-label="site.yml applique des rôles à des groupes de serveurs">{_fleches(7)}
<rect class="a" x="10" y="80" width="130" height="60" rx="8"/><text class="ttl" x="24" y="106">site.yml</text><text class="t2" x="24" y="126">toute l'infra</text>
<rect class="b" x="200" y="10" width="220" height="100" rx="8"/><text class="ttl" x="214" y="32">rôle web</text>
<text class="mono" x="214" y="52">tasks/main.yml</text><text class="mono" x="214" y="68">handlers/main.yml</text><text class="mono" x="214" y="84">templates/*.j2</text><text class="mono" x="214" y="100">defaults/main.yml</text>
<rect class="b" x="200" y="130" width="220" height="84" rx="8"/><text class="ttl" x="214" y="152">rôle redis</text>
<text class="mono" x="214" y="172">tasks/main.yml</text><text class="mono" x="214" y="188">handlers/main.yml</text><text class="mono" x="214" y="204">defaults/main.yml</text>
<path class="la" d="M140,100 L198,62" marker-end="url(#fl7)"/><path class="la" d="M140,120 L198,170" marker-end="url(#fl7)"/>
<rect class="g" x="470" y="36" width="160" height="48" rx="8"/><text x="482" y="58">groupe web</text><text class="t2" x="482" y="75">web1 · web2 · web3</text>
<rect class="g" x="470" y="148" width="160" height="48" rx="8"/><text x="482" y="170">groupe bdd</text><text class="t2" x="482" y="187">db1</text>
<path class="l" d="M420,60 L468,60" marker-end="url(#fg7)"/><path class="l" d="M420,172 L468,172" marker-end="url(#fg7)"/>
</svg><figcaption>Un rôle range tout ce qu'il faut pour un service dans une arborescence standard, réutilisable d'un projet à l'autre.</figcaption></figure>"""

SCHEMA_VAULT = f"""<figure class="schema"><svg viewBox="0 0 640 200" role="img" aria-label="Le fichier chiffré est déchiffré en mémoire au moment du déploiement">{_fleches(8)}
<rect class="b" x="10" y="20" width="210" height="96" rx="8"/><text class="mono" x="22" y="42">group_vars/bdd/vault.yml</text>
<text class="mono" x="22" y="64">$ANSIBLE_VAULT;1.1;AES256</text><text class="mono" x="22" y="80">6264383931653…</text><text class="t2" x="22" y="104">chiffré : peut aller dans Git</text>
<rect class="w" x="10" y="136" width="210" height="50" rx="8"/><text class="mono" x="22" y="158">~/.vault_pass</text><text class="t2" x="22" y="176">la clé : jamais dans le dépôt</text>
<rect class="a" x="270" y="60" width="160" height="80" rx="8"/><text class="ttl" x="284" y="84">ansible-playbook</text><text class="t2" x="284" y="106">déchiffre en mémoire</text><text class="t2" x="284" y="124">au moment du jeu</text>
<path class="l" d="M220,68 L268,90" marker-end="url(#fg8)"/><path class="ld" d="M220,160 L268,118" marker-end="url(#fw8)"/>
<rect class="g" x="480" y="70" width="150" height="60" rx="8"/><text x="492" y="94">db1</text><text class="mono" x="492" y="116">requirepass ••••</text>
<path class="la" d="M430,100 L478,100" marker-end="url(#fl8)"/>
</svg><figcaption>Le secret n'apparaît en clair que sur le serveur qui en a besoin, jamais dans le dépôt.</figcaption></figure>"""

INTRO = """<div class="scenario"><h3>Automatiser l'infrastructure de Cimes &amp; Sentiers</h3><p>La boutique grossit : deux serveurs web, un serveur de base de données, et bientôt d'autres. Jusqu'ici, Marc configurait chaque serveur à la main, en SSH… et plus personne ne sait exactement ce qu'il y a dessus. Léa vous confie la mission : <strong>décrire toute l'infrastructure dans du code</strong> avec Ansible, pour pouvoir la reconstruire, la vérifier et la faire évoluer en une commande.</p><p>Vous travaillez sur le <strong>poste de contrôle</strong> (ce terminal). Les serveurs <code>web1</code>, <code>web2</code> et <code>db1</code> sont joignables en SSH avec le compte <code>admin</code> (mot de passe <code>cimes</code>, à n'utiliser qu'une fois). Votre projet se trouve dans <code>~/infra</code>, que vous pouvez modifier dans l'éditeur.</p></div>"""

STEPS = {
    # ─────────────────────────────────────────────────────────────────────
    1: {
        "title": "Jour 1 — Ce que fait Ansible",
        "description": "Comprendre le modèle d'Ansible et préparer l'accès aux serveurs. Compétences : clés SSH, inventaire, groupes, ansible.cfg, ansible -m ping.",
        "lesson": INTRO + """<h3>Le problème</h3><p>Configurer un serveur à la main, c'est taper des commandes en SSH. Pour trois serveurs, on recommence trois fois ; pour trente, on se trompe forcément. Et six mois plus tard, personne ne sait plus ce qui a été fait.</p><h3>La réponse d'Ansible</h3><ul><li>On <strong>décrit</strong> l'état voulu dans des fichiers texte (YAML), versionnés comme du code : c'est l'<em>Infrastructure as Code</em>.</li><li>Ansible se connecte aux serveurs en <strong>SSH</strong> et fait ce qu'il faut pour atteindre cet état.</li><li><strong>Sans agent</strong> : rien à installer sur les serveurs, à part SSH et Python (déjà présents sur presque tous les Linux).</li><li>Mode <strong>push</strong> : c'est le poste de contrôle qui décide quand agir.</li></ul>""" + SCHEMA_SSH + """<h3>1. L'accès SSH par clé</h3><p>Ansible ouvre des dizaines de connexions SSH : impossible de taper un mot de passe à chaque fois. On utilise une <strong>paire de clés</strong> : la clé privée reste sur le poste de contrôle, la clé publique est copiée sur chaque serveur.</p><pre>ssh-keygen -t ed25519            # crée ~/.ssh/id_ed25519 (privée) et id_ed25519.pub (publique)<br>ssh-copy-id admin@web1           # copie la clé publique (demande le mot de passe une dernière fois)<br>ssh admin@web1                   # plus de mot de passe ; exit pour revenir</pre><div class="tip">À la première connexion, SSH affiche l'<strong>empreinte</strong> du serveur et demande de la confirmer (<code>yes</code>). Elle est mémorisée dans <code>~/.ssh/known_hosts</code>. Ansible refuse de se connecter à un serveur dont l'empreinte est inconnue : faites une première connexion à la main, ou <code>ssh-keyscan web1 web2 db1 &gt;&gt; ~/.ssh/known_hosts</code>.</div><h3>2. L'inventaire : quels serveurs ?</h3><pre>[web]<br>web1<br>web2<br><br>[bdd]<br>db1<br><br>[production:children]   # un groupe de groupes<br>web<br>bdd</pre><p>Les groupes permettent de cibler : <code>web</code>, <code>bdd</code>, <code>production</code>, ou le groupe implicite <code>all</code>.</p><pre>ansible-inventory -i inventaire.ini --graph   # l'arbre des groupes</pre><h3>3. ansible.cfg : les réglages du projet</h3><p>Ansible lit le fichier <code>ansible.cfg</code> du <strong>dossier courant</strong> : plus besoin de répéter les options.</p><pre>[defaults]<br>inventory = inventaire.ini<br>remote_user = admin</pre><h3>4. Premier contact</h3><pre>cd ~/infra<br>ansible all -m ping        # le module ping vérifie SSH + Python, rien à voir avec le ping réseau</pre><pre>web1 | SUCCESS =&gt; { "changed": false, "ping": "pong" }</pre>""",
        "setup": r'''
for s in web1 web2 db1; do neuf $s; done
''',
        "exercises": [
            {"id": "A1.1", "points": 3, "title": "Les clés des serveurs",
             "ticket": {"from": "lea", "body": "Bienvenue ! Première chose : je ne veux plus de mots de passe qui traînent. Crée-toi une paire de clés SSH sur le poste de contrôle et installe ta clé publique sur <code>web1</code>, <code>web2</code> et <code>db1</code> (compte <code>admin</code>, mot de passe <code>cimes</code>). Tu dois pouvoir t'y connecter sans mot de passe."},
             "desc": "Connexion SSH sans mot de passe (et sans question sur l'empreinte) vers <code>admin@web1</code>, <code>admin@web2</code> et <code>admin@db1</code>.",
             "hints": ["<code>ssh-keygen -t ed25519</code> (Entrée à chaque question), puis <code>ssh-copy-id admin@web1</code>, et de même pour les autres.", "Testez avec <code>ssh admin@web1 hostname</code> : aucune question ne doit être posée."],
             "checks": [
                 ('ls $H/.ssh/*.pub >/dev/null 2>&1', "Aucune clé publique dans ~/.ssh (ssh-keygen)."),
                 ('for s in web1 web2 db1; do ssh_ok $s || { echo "MSG:Échec vers $s"; exit 1; }; done', "Connexion sans mot de passe impossible vers un serveur : clé non installée (ssh-copy-id) ou empreinte jamais acceptée."),
             ]},
            {"id": "A1.2", "points": 3, "title": "L'inventaire",
             "ticket": {"from": "sophie", "body": "Il nous faut enfin une liste officielle des serveurs. Crée l'inventaire <code>~/infra/inventaire.ini</code> : un groupe <code>web</code> (web1, web2), un groupe <code>bdd</code> (db1), et un groupe <code>production</code> qui regroupe les deux."},
             "desc": "<code>~/infra/inventaire.ini</code> : groupes <code>web</code> = web1, web2 ; <code>bdd</code> = db1 ; <code>production</code> a pour enfants <code>web</code> et <code>bdd</code>.",
             "hints": ["Un groupe par section <code>[nom]</code>, un serveur par ligne.", "Groupe de groupes : section <code>[production:children]</code>. Vérifiez avec <code>ansible-inventory -i inventaire.ini --graph</code>."],
             "checks": [
                 ('[ -f $I/inventaire.ini ]', "~/infra/inventaire.ini n'existe pas."),
                 ('[ "$(groupe web)" = "web1,web2" ]', "Le groupe web doit contenir exactement web1 et web2."),
                 ('[ "$(groupe bdd)" = db1 ]', "Le groupe bdd doit contenir exactement db1."),
                 ("etu 'ansible-inventory -i inventaire.ini --list' | jq -e '.production.children | sort == [\"bdd\",\"web\"]' >/dev/null", "Le groupe production doit avoir pour enfants les groupes web et bdd (section [production:children])."),
             ]},
            {"id": "A1.3", "points": 3, "title": "Premier contact", "manual": True,
             "ticket": {"from": "lea", "body": "Je ne veux pas taper <code>-i inventaire.ini -u admin</code> à chaque commande. Ajoute un <code>ansible.cfg</code> dans <code>~/infra</code>, puis vérifie qu'Ansible joint bien tous les serveurs de production."},
             "desc": "<code>~/infra/ansible.cfg</code> désigne l'inventaire et l'utilisateur distant <code>admin</code> ; depuis <code>~/infra</code>, <code>ansible production -m ping</code> répond <code>pong</code> pour les trois serveurs.",
             "hints": ["Section <code>[defaults]</code> avec <code>inventory = inventaire.ini</code> et <code>remote_user = admin</code>.", "<code>ansible-config dump --only-changed</code> montre les réglages lus."],
             "checks": [
                 ('[ -f $I/ansible.cfg ]', "~/infra/ansible.cfg n'existe pas."),
                 ('etu "ansible-config dump --only-changed" | grep -E "^DEFAULT_HOST_LIST" | grep -q inventaire.ini', "ansible.cfg ne désigne pas l'inventaire (inventory = inventaire.ini, section [defaults])."),
                 ('etu "ansible-config dump --only-changed" | grep -E "^DEFAULT_REMOTE_USER" | grep -q "= admin"', "ansible.cfg doit définir l'utilisateur distant admin (remote_user)."),
                 ('[ "$(etu "ansible production -m ping -o" | grep -c "SUCCESS.*pong")" = 3 ]', "ansible production -m ping ne répond pas « pong » pour les trois serveurs (lancé depuis ~/infra)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Jour 2 — Sous le capot : modules et commandes ad hoc",
        "description": "Ce qu'Ansible exécute vraiment, les facts, et les premières actions sur les serveurs. Compétences : -vvv, modules, setup, become, user, copy.",
        "lesson": """<h3>Une commande ad hoc</h3><pre>ansible &lt;cible&gt; -m &lt;module&gt; -a "&lt;arguments&gt;"<br>ansible web -m command -a "uptime"</pre><p>Un <strong>module</strong> est un petit programme Python qui sait faire une chose : installer un paquet (<code>apt</code>), gérer un utilisateur (<code>user</code>), copier un fichier (<code>copy</code>), un service (<code>service</code>)… Il en existe des milliers : <code>ansible-doc -l</code> les liste, <code>ansible-doc user</code> documente l'un d'eux.</p><h3>Que se passe-t-il vraiment ?</h3>""" + SCHEMA_MODULE + """<p>Pour le voir, ajoutez <code>-v</code>, <code>-vv</code> ou <code>-vvv</code> (de plus en plus bavard) : connexions SSH, fichiers envoyés (<code>PUT … AnsiballZ_…py</code>), commande exécutée, JSON renvoyé.</p><h3>État désiré et idempotence</h3>""" + SCHEMA_IDEMPOTENCE + """<pre>ansible web -b -m user -a "name=deploy"    # 1re fois : CHANGED (le compte est créé)<br>ansible web -b -m user -a "name=deploy"    # 2e fois  : SUCCESS (il existe déjà)</pre><div class="tip">Les modules <code>command</code> et <code>shell</code> exécutent une commande à l'aveugle : Ansible ne sait pas si elle a changé quelque chose, et répond toujours <code>changed</code>. Préférez un module dédié quand il existe.</div><h3>Devenir root : become</h3><p>Le compte <code>admin</code> n'est pas root. Pour administrer, Ansible passe par <code>sudo</code> : option <code>-b</code> (<em>become</em>) en ligne de commande, <code>become: true</code> dans un playbook.</p><h3>Les facts</h3><p>Avant de travailler, Ansible peut <strong>interroger</strong> chaque serveur : système, version, mémoire, adresses IP… Ce sont les <em>facts</em>, utilisables ensuite comme des variables.</p><pre>ansible db1 -m setup                                   # tous les facts (long !)<br>ansible db1 -m setup -a "filter=ansible_distribution*"<br>ansible all -m setup -a "filter=ansible_memtotal_mb"</pre><h3>Quelques modules utiles</h3><pre>ansible web -b -m user -a "name=deploy shell=/bin/bash"<br>ansible web -b -m copy -a "dest=/etc/motd content='Bonjour\\n'"<br>ansible web -b -m apt -a "name=tree update_cache=yes"<br>ansible all -m command -a "df -h /"</pre>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
''',
        "exercises": [
            {"id": "A2.1", "points": 3, "title": "Sous le capot",
             "ticket": {"from": "julien", "body": "Léa dit qu'Ansible n'installe rien sur les serveurs. Mais alors, comment il fait pour exécuter du code dessus ?! Tu peux regarder ce qui se passe vraiment pendant un <code>ansible web1 -m ping</code>, et me dire le nom du fichier Python qu'il envoie sur le serveur ?"},
             "desc": "Le nom du fichier Python envoyé sur <code>web1</code> par le module ping (seulement le nom, sans le chemin) dans <code>~/infra/reponses/module.txt</code>.",
             "hints": ["Relancez la commande avec <code>-vvv</code> et cherchez la ligne <code>PUT</code>.", "Le nom commence par <code>AnsiballZ_</code>."],
             "checks": [
                 ('[ "$(ans $I/reponses/module.txt)" = AnsiballZ_ping.py ]', "reponses/module.txt ne contient pas le nom du fichier envoyé par le module ping (regardez les lignes PUT avec -vvv)."),
             ]},
            {"id": "A2.2", "points": 3, "title": "Inventaire matériel",
             "ticket": {"from": "diallo", "body": "Pour le contrat de support, l'éditeur me demande la version exacte de Debian installée sur le serveur de base de données. Tu peux me la trouver, sans aller fouiller sur le serveur ?"},
             "desc": "La version de Debian de <code>db1</code>, telle que la donnent les facts (<code>ansible_distribution_version</code>), dans <code>~/infra/reponses/debian-db1.txt</code>.",
             "hints": ["Module <code>setup</code>, avec un filtre : <code>-a \"filter=ansible_distribution*\"</code>."],
             "checks": [
                 ('[ "$(ans $I/reponses/debian-db1.txt)" = "$(sur db1 "cat /etc/debian_version" | tr -d "[:space:]")" ]', "reponses/debian-db1.txt ne contient pas la version de Debian de db1 (fact ansible_distribution_version)."),
             ]},
            {"id": "A2.3", "points": 4, "title": "Opération commando",
             "ticket": {"from": "thomas", "body": "Pour les mises en ligne, il me faut un compte <code>deploy</code> sur les serveurs web (pas sur la base !). Et Sophie veut qu'on prévienne les gens qui se connectent : le fichier <code>/etc/motd</code> des serveurs web doit afficher <strong>Serveur géré par Ansible - ne pas modifier à la main</strong>."},
             "desc": "Un compte <code>deploy</code> sur web1 et web2 (pas sur db1), et <code>/etc/motd</code> de web1 et web2 contient « Serveur géré par Ansible - ne pas modifier à la main ». Deux commandes ad hoc suffisent.",
             "hints": ["Modules <code>user</code> et <code>copy</code> (argument <code>content=</code>) ; ciblez le groupe <code>web</code>.", "Modifier le système demande les droits root : option <code>-b</code>."],
             "checks": [
                 ('for s in web1 web2; do sur $s "id deploy" >/dev/null || exit 1; done', "Le compte deploy n'existe pas sur web1 et web2."),
                 ('! sur db1 "id deploy"', "Le compte deploy ne doit pas exister sur db1 : ciblez seulement le groupe web."),
                 ('for s in web1 web2; do sur $s "cat /etc/motd" | grep -qF "Serveur géré par Ansible" || exit 1; done', "/etc/motd de web1 et web2 ne contient pas « Serveur géré par Ansible - ne pas modifier à la main »."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Jour 3 — Premier playbook",
        "description": "Écrire, lancer et rejouer un playbook. Compétences : YAML, play, tâches, apt, service, copy, récapitulatif, idempotence.",
        "lesson": """<h3>Des commandes ad hoc au playbook</h3><p>Les commandes ad hoc s'oublient. Un <strong>playbook</strong> est un fichier YAML qui décrit ce qu'on veut, se relit, se versionne et se rejoue à volonté.</p>""" + SCHEMA_PLAYBOOK + """<h3>YAML en 5 règles</h3><ul><li>L'<strong>indentation</strong> (des espaces, jamais de tabulation) définit la structure : c'est la source d'erreur n°1.</li><li><code>clé: valeur</code> (un espace après les deux-points) ;</li><li><code>- élément</code> : un élément de liste ;</li><li><code># commentaire</code> ;</li><li>entre guillemets si la valeur commence par <code>{{</code> ou contient <code>: </code>.</li></ul><h3>Un premier playbook</h3><pre>- name: Serveurs web de la boutique<br>  hosts: web<br>  become: true<br>  tasks:<br>    - name: Installer nginx<br>      ansible.builtin.apt:<br>        name: nginx<br>        state: present<br>        update_cache: true<br>        cache_valid_time: 3600<br><br>    - name: nginx démarré, et lancé au démarrage du serveur<br>      ansible.builtin.service:<br>        name: nginx<br>        state: started<br>        enabled: true</pre><p><code>update_cache</code> rafraîchit la liste des paquets (comme <code>apt update</code>) ; <code>cache_valid_time</code> évite de le refaire si elle date de moins d'une heure.</p><h3>Lancer, lire le récapitulatif</h3><pre>ansible-playbook web.yml --syntax-check   # vérifie le YAML sans rien faire<br>ansible-playbook web.yml<br>…<br>PLAY RECAP ********************************************<br>web1  : ok=3  changed=2  unreachable=0  failed=0 …<br>web2  : ok=3  changed=2  unreachable=0  failed=0 …</pre><h3>Déposer un fichier</h3><pre>    - name: Page d'accueil<br>      ansible.builtin.copy:<br>        src: fichiers/index.html      # chemin sur le poste de contrôle (relatif au playbook)<br>        dest: /var/www/html/index.html  # chemin sur le serveur<br>        mode: "0644"</pre><h3>L'idempotence, la vraie</h3><p>Relancez le playbook : chaque tâche doit répondre <code>ok</code>, et le récapitulatif afficher <code>changed=0</code>. Un playbook idempotent peut être rejoué sans crainte, par exemple toutes les nuits pour corriger les dérives.</p><div class="tip">Le serveur <code>db1</code> ne fait pas partie du groupe <code>web</code> : il n'est pas concerné par ce play.</div>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
jeton="CS-$(tr -dc 'A-Z0-9' </dev/urandom | head -c 8)"
mkdir -p $I/fichiers
cat > $I/fichiers/index.html <<EOF
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Cimes & Sentiers</title></head>
<body>
  <h1>Boutique Cimes & Sentiers</h1>
  <p>Tout le matériel de randonnée, livré en 48 h.</p>
  <!-- version $jeton -->
</body>
</html>
EOF
own $I
emit JETON "$jeton"
''',
        "exercises": [
            {"id": "A3.1", "points": 5, "title": "nginx partout",
             "ticket": {"from": "thomas", "body": "On lance la boutique sur les deux serveurs web ! Écris un playbook <code>~/infra/web.yml</code> qui installe <strong>nginx</strong> sur le groupe <code>web</code> et s'assure qu'il tourne. Pas sur la base de données, bien sûr."},
             "desc": "<code>~/infra/web.yml</code> cible le groupe <code>web</code> ; nginx est installé et tourne sur web1 et web2, et n'est pas installé sur db1.",
             "hints": ["Reprenez l'exemple du cours : modules <code>ansible.builtin.apt</code> et <code>ansible.builtin.service</code>, avec <code>become: true</code>.", "Le cache APT des serveurs est vide au départ : <code>update_cache: true</code>, sinon « No package matching 'nginx' »."],
             "checks": [
                 ('[ -f $I/web.yml ]', "~/infra/web.yml n'existe pas."),
                 ("yjson $I/web.yml | jq -e '.[0].hosts == \"web\"' >/dev/null", "Le play de web.yml doit cibler le groupe web (hosts: web). Le fichier est-il du YAML valide ?"),
                 ('for s in web1 web2; do sur $s "pgrep -x nginx" >/dev/null || exit 1; done', "nginx ne tourne pas sur web1 et web2 (lancez ansible-playbook web.yml)."),
                 ('! sur db1 "test -e /usr/sbin/nginx"', "nginx a été installé sur db1 : il ne doit l'être que sur les serveurs web."),
             ]},
            {"id": "A3.2", "points": 4, "title": "La page d'accueil",
             "ticket": {"from": "thomas", "body": "J'ai mis la page d'accueil dans <code>~/infra/fichiers/index.html</code>. Ajoute une tâche à <code>web.yml</code> pour la déployer à la place de la page par défaut de nginx (<code>/var/www/html/index.html</code>)."},
             "desc": "web1 et web2 servent la page de <code>~/infra/fichiers/index.html</code>, déployée par une tâche de <code>web.yml</code>.",
             "hints": ["Module <code>ansible.builtin.copy</code> : <code>src</code> (sur le poste de contrôle) et <code>dest</code> (sur le serveur).", "Vérifiez avec <code>curl http://web1</code>."],
             "checks": [
                 ('grep -q "index.html" $I/web.yml', "La page doit être déployée par une tâche de web.yml (module copy)."),
                 ('for s in web1 web2; do page $s | grep -qF "$LAB_JETON" || exit 1; done', "web1 et web2 ne servent pas la page de ~/infra/fichiers/index.html."),
             ]},
            {"id": "A3.3", "points": 4, "title": "Rejouer sans crainte", "manual": True,
             "ticket": {"from": "lea", "body": "Le vrai test d'un playbook, c'est la deuxième exécution : si tout est déjà en place, il ne doit <strong>rien</strong> changer. Je vais le rejouer deux fois de suite ; au deuxième passage, je veux <code>changed=0</code> partout."},
             "desc": "<code>ansible-playbook web.yml</code>, lancé deux fois de suite depuis <code>~/infra</code>, réussit, et le second passage n'a rien changé (<code>changed=0</code>).",
             "hints": ["Lancez-le deux fois et lisez le récapitulatif : quelle tâche est encore <code>changed</code> ?", "Une tâche <code>command</code> ou <code>shell</code> est toujours <code>changed</code> : remplacez-la par un module dédié."],
             "checks": [
                 ('joue web.yml || recap', "Le playbook web.yml échoue (voir le récapitulatif)."),
                 ('joue web.yml || recap', "Le playbook web.yml échoue au second passage."),
                 ('rien_change || recap', "Au second passage, le playbook modifie encore quelque chose : il n'est pas idempotent."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Jour 4 — Variables, facts et modèles",
        "description": "Un même playbook, un résultat adapté à chaque serveur. Compétences : group_vars, host_vars, Jinja2, template, facts.",
        "lesson": """<h3>Des variables</h3><p>Plutôt que d'écrire les valeurs en dur, on les range dans des fichiers que Ansible charge automatiquement, <strong>à côté de l'inventaire ou du playbook</strong> :</p><pre>~/infra/<br>├── inventaire.ini<br>├── group_vars/<br>│   ├── all.yml        # tous les serveurs<br>│   └── web.yml        # les serveurs du groupe web<br>└── host_vars/<br>    └── web2.yml       # uniquement web2</pre><pre># group_vars/web.yml<br>environnement: production</pre><p>Ordre de priorité (simplifié), du plus faible au plus fort : <code>group_vars/all</code> &lt; <code>group_vars/&lt;groupe&gt;</code> &lt; <code>host_vars/&lt;serveur&gt;</code> &lt; <code>vars:</code> du play &lt; <code>-e</code> en ligne de commande.</p><pre>ansible-inventory --host web2       # toutes les variables vues pour web2</pre><h3>Des modèles Jinja2</h3><p>Le module <code>template</code> fonctionne comme <code>copy</code>, mais remplace d'abord les expressions <code>{{ … }}</code> par leur valeur, <strong>pour chaque serveur</strong>.</p>""" + SCHEMA_VARIABLES + """<pre>&lt;!-- templates/index.html.j2 --&gt;<br>&lt;h1&gt;Boutique Cimes &amp;amp; Sentiers&lt;/h1&gt;<br>&lt;p&gt;Serveur : {{ inventory_hostname }}&lt;/p&gt;<br>&lt;p&gt;Environnement : {{ environnement }}&lt;/p&gt;</pre><pre>    - name: Page d'accueil<br>      ansible.builtin.template:<br>        src: templates/index.html.j2<br>        dest: /var/www/html/index.html</pre><ul><li><code>inventory_hostname</code> : nom du serveur dans l'inventaire (variable magique, toujours définie) ;</li><li>les <strong>facts</strong> sont aussi des variables : <code>{{ ansible_default_ipv4.address }}</code>, <code>{{ ansible_distribution }}</code>, <code>{{ ansible_memtotal_mb }}</code>…</li><li>des filtres transforment les valeurs : <code>{{ environnement | upper }}</code>, <code>{{ liste | join(', ') }}</code>.</li></ul><div class="tip">Dans un fichier YAML, une valeur qui commence par <code>{{</code> doit être entre guillemets : <code>name: "{{ paquet }}"</code>.</div>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
''',
        "exercises": [
            {"id": "A4.1", "points": 5, "title": "Une page par serveur",
             "ticket": {"from": "thomas", "body": "Quand un client signale un bug, on ne sait jamais quel serveur lui a répondu. Remplace la page fixe par un <strong>modèle</strong> <code>templates/index.html.j2</code> qui affiche le nom du serveur et son environnement. L'environnement vient d'une variable <code>environnement</code>, qui vaut <code>production</code> pour tout le groupe web."},
             "desc": "La variable <code>environnement: production</code> est définie pour le groupe <code>web</code> (<code>group_vars</code>) ; la page de chaque serveur web, générée depuis <code>~/infra/templates/index.html.j2</code>, affiche son nom et son environnement.",
             "hints": ["Fichier <code>group_vars/web.yml</code> ; dans le modèle : <code>{{ inventory_hostname }}</code> et <code>{{ environnement }}</code>.", "Dans web.yml, remplacez le module <code>copy</code> par <code>template</code>."],
             "checks": [
                 ('[ -f $I/templates/index.html.j2 ]', "~/infra/templates/index.html.j2 n'existe pas."),
                 ('[ "$(var web1 environnement)" = production ]', "La variable environnement ne vaut pas production pour web1 (group_vars/web.yml)."),
                 ('page web1 | grep -q web1 && page web1 | grep -q production', "La page de web1 doit afficher son nom (web1) et son environnement (production)."),
                 ('page web2 | grep -q web2', "La page de web2 doit afficher son nom (web2)."),
             ]},
            {"id": "A4.2", "points": 4, "title": "web2 passe en recette",
             "ticket": {"from": "sophie", "body": "Changement de programme : <code>web2</code> devient le serveur de <strong>recette</strong>, pour tester les nouveautés avant la production. Seul web2 change, et je ne veux pas qu'on touche au modèle ni au playbook pour ça."},
             "desc": "<code>environnement</code> vaut <code>recette</code> pour web2 grâce à <code>host_vars</code>, <code>production</code> pour web1 ; les pages l'affichent.",
             "hints": ["Un fichier <code>host_vars/web2.yml</code> : la variable de l'hôte l'emporte sur celle du groupe.", "<code>ansible-inventory --host web2</code> pour vérifier, puis rejouez le playbook."],
             "checks": [
                 ('[ -e $I/host_vars/web2.yml ] || [ -e $I/host_vars/web2 ]', "Pas de host_vars pour web2 (host_vars/web2.yml)."),
                 ('[ "$(var web2 environnement)" = recette ] && [ "$(var web1 environnement)" = production ]', "environnement doit valoir recette pour web2 et production pour web1."),
                 ('page web2 | grep -q recette && page web1 | grep -q production', "Les pages n'affichent pas le bon environnement (rejouez le playbook)."),
             ]},
            {"id": "A4.3", "points": 3, "title": "Une information venue du serveur",
             "ticket": {"from": "julien", "body": "Et on pourrait afficher l'adresse IP du serveur sur la page ? Pas en l'écrivant à la main, hein, sinon ça va encore être faux le jour où on change de réseau."},
             "desc": "La page de chaque serveur web affiche son adresse IP, obtenue par les facts (web1 : 10.10.0.11, web2 : 10.10.0.12).",
             "hints": ["Le fact <code>ansible_default_ipv4.address</code> (voir <code>ansible web1 -m setup -a \"filter=ansible_default_ipv4\"</code>)."],
             "checks": [
                 ('grep -q "ansible_" $I/templates/index.html.j2', "Le modèle doit utiliser un fact (ansible_…), pas une adresse écrite en dur."),
                 ('page web1 | grep -qF 10.10.0.11 && page web2 | grep -qF 10.10.0.12', "Les pages n'affichent pas l'adresse IP de leur serveur."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Jour 5 — Configurer un service : les handlers",
        "description": "Déployer une configuration et ne redémarrer le service que si nécessaire. Compétences : template de configuration, notify, handlers, -e.",
        "lesson": """<h3>Le problème</h3><p>On déploie la configuration de nginx avec <code>template</code>. Mais nginx ne relit sa configuration que si on le <strong>recharge</strong>. Recharger à chaque exécution ? Inutile, et cela coupe parfois des connexions. Il faut recharger <strong>seulement si la configuration a changé</strong>.</p><h3>Les handlers</h3>""" + SCHEMA_HANDLERS + """<pre>  tasks:<br>    - name: Configuration du site<br>      ansible.builtin.template:<br>        src: templates/site.conf.j2<br>        dest: /etc/nginx/sites-available/default<br>      notify: Recharger nginx          # prévient le handler… si la tâche est « changed »<br><br>  handlers:<br>    - name: Recharger nginx            # même nom que dans notify<br>      ansible.builtin.service:<br>        name: nginx<br>        state: reloaded</pre><ul><li>Un handler n'est exécuté que s'il a été notifié par une tâche <code>changed</code>.</li><li>Il s'exécute <strong>une seule fois</strong>, à la fin du play, même si plusieurs tâches l'ont notifié.</li><li><code>reloaded</code> recharge la configuration sans couper le service ; <code>restarted</code> arrête puis relance.</li></ul><h3>La configuration de nginx</h3><pre># templates/site.conf.j2<br>server {<br>    listen {{ http_port }} default_server;<br>    root /var/www/html;<br>    index index.html;<br>}</pre><p>Sur Debian, le site par défaut est <code>/etc/nginx/sites-available/default</code> (activé par un lien dans <code>sites-enabled</code>) : le remplacer par votre modèle change le port d'écoute.</p><h3>Surcharger une variable pour un essai</h3><pre>ansible-playbook web.yml -e http_port=8089   # -e l'emporte sur tout le reste</pre>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
''',
        "exercises": [
            {"id": "A5.1", "points": 6, "title": "Le port 8080",
             "ticket": {"from": "sophie", "body": "Le nouveau pare-feu de l'hébergeur n'ouvre que le port <strong>8080</strong> vers les serveurs web. Configure nginx pour qu'il écoute sur ce port, avec un modèle de configuration. Le numéro de port doit être une variable <code>http_port</code> du groupe web, et nginx ne doit être rechargé que si sa configuration change."},
             "desc": "<code>http_port: 8080</code> pour le groupe web ; nginx de web1 et web2 sert la page sur le port 8080 et plus sur le port 80 ; <code>web.yml</code> a un handler notifié par la tâche de configuration.",
             "hints": ["Modèle <code>templates/site.conf.j2</code> déployé sur <code>/etc/nginx/sites-available/default</code>, avec <code>listen {{ http_port }} default_server;</code>.", "Ajoutez <code>notify:</code> à la tâche et une section <code>handlers:</code> au même niveau que <code>tasks:</code>."],
             "checks": [
                 ('[ "$(var web1 http_port)" = 8080 ]', "La variable http_port ne vaut pas 8080 pour les serveurs web (group_vars/web.yml)."),
                 ('page web1:8080 | grep -q web1 && page web2:8080 | grep -q web2', "Les serveurs web ne servent pas leur page sur le port 8080 (le handler a-t-il rechargé nginx ?)."),
                 ('! page web1:80 >/dev/null 2>&1', "nginx répond encore sur le port 80 de web1 : la configuration par défaut est-elle toujours active ?"),
                 ("yjson $I/web.yml | jq -e '[.[] | select(.handlers)] | length > 0' >/dev/null", "web.yml n'a pas de section handlers."),
             ]},
            {"id": "A5.2", "points": 5, "title": "Recharger seulement si nécessaire", "manual": True,
             "ticket": {"from": "lea", "body": "Je vais tester ton playbook comme en production : je le lance avec un autre port (<code>-e http_port=8089</code>), nginx doit suivre ; puis je le relance normalement, retour sur 8080 ; puis une dernière fois sans rien changer : là, nginx ne doit même pas être redémarré."},
             "desc": "Avec <code>-e http_port=8089</code>, nginx écoute sur 8089 ; relancé normalement, il revient sur 8080 ; relancé une troisième fois, rien ne change et nginx n'est pas redémarré.",
             "hints": ["Le port doit venir de <code>{{ http_port }}</code> dans le modèle, et le rechargement d'un handler notifié par la tâche <code>template</code>.", "Une tâche <code>service: state=restarted</code> dans <code>tasks</code> redémarre nginx à chaque fois : c'est un handler qu'il faut."],
             "checks": [
                 ('joue web.yml -e http_port=8089 || recap', "Le playbook échoue avec -e http_port=8089 (voir le récapitulatif)."),
                 ('page web1:8089 >/dev/null', "Avec http_port=8089, nginx n'écoute pas sur 8089 : le port vient-il de la variable, et le handler recharge-t-il nginx ?"),
                 ('joue web.yml || recap', "Le playbook web.yml échoue (voir le récapitulatif)."),
                 ('page web1:8080 >/dev/null', "Revenu à http_port=8080, nginx n'écoute plus sur 8080 : le handler a-t-il rechargé nginx ?"),
                 ('p=$(sur web1 "cat /run/nginx.pid"); joue web.yml && rien_change && [ "$(sur web1 "cat /run/nginx.pid")" = "$p" ] || recap', "Sans aucune modification, le playbook change encore quelque chose ou redémarre nginx : le handler ne doit s'exécuter que si la configuration change."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Jour 6 — Boucles et conditions",
        "description": "Répéter une tâche, et n'agir que sur certains serveurs. Compétences : loop, item, when, {% if %}.",
        "lesson": """<h3>Répéter une tâche : loop</h3><pre># group_vars/web.yml<br>equipe_web:<br>  - thomas<br>  - nadia<br>  - julien</pre><pre>    - name: Comptes de l'équipe web<br>      ansible.builtin.user:<br>        name: "{{ item }}"      # item : l'élément courant de la boucle<br>        groups: www-data<br>        append: true             # ajoute au groupe, sans retirer les autres<br>      loop: "{{ equipe_web }}"</pre><p>Une seule tâche, un résultat par élément. Ajouter une personne à l'équipe, c'est ajouter une ligne dans la variable.</p><h3>Agir sous condition : when</h3><pre>    - name: Outils de diagnostic en recette<br>      ansible.builtin.apt:<br>        name: htop<br>      when: environnement == "recette"</pre><ul><li>La condition est une expression Jinja2, <strong>sans</strong> <code>{{ }}</code>.</li><li>Sur les serveurs où elle est fausse, la tâche est <code>skipping</code>.</li><li>On peut tester des facts : <code>when: ansible_memtotal_mb &lt; 1024</code>, <code>when: ansible_distribution == "Debian"</code>.</li></ul><h3>Des conditions dans un modèle</h3><pre>{% if environnement == "recette" %}<br>&lt;div class="bandeau"&gt;RECETTE - site de test&lt;/div&gt;<br>{% endif %}<br><br>&lt;ul&gt;<br>{% for membre in equipe_web %}<br>  &lt;li&gt;{{ membre | capitalize }}&lt;/li&gt;<br>{% endfor %}<br>&lt;/ul&gt;</pre><div class="tip"><code>{{ … }}</code> affiche une valeur ; <code>{% … %}</code> est une instruction (condition, boucle) qui n'affiche rien elle-même.</div>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
''',
        "exercises": [
            {"id": "A6.1", "points": 4, "title": "L'équipe web",
             "ticket": {"from": "nadia", "body": "Thomas, Julien et moi avons besoin d'un compte sur les serveurs web, dans le groupe <code>www-data</code> pour pouvoir toucher aux fichiers du site. La liste va bouger souvent : je veux une variable <code>equipe_web</code> et <strong>une seule tâche</strong>, pas trois copier-coller."},
             "desc": "La variable <code>equipe_web</code> (thomas, nadia, julien) est définie pour le groupe web ; une tâche avec une boucle crée ces comptes, membres de <code>www-data</code>, sur web1 et web2 (pas sur db1).",
             "hints": ["La liste va dans <code>group_vars/web.yml</code>.", "<code>loop: \"{{ equipe_web }}\"</code> et <code>name: \"{{ item }}\"</code>, avec <code>groups: www-data</code> et <code>append: true</code>."],
             "checks": [
                 ("etu 'ansible-inventory --host web1' | jq -e '.equipe_web | sort == [\"julien\",\"nadia\",\"thomas\"]' >/dev/null", "La variable equipe_web doit être la liste thomas, nadia, julien pour les serveurs web."),
                 ('grep -qE "^[[:space:]]*(loop|with_items):" $I/web.yml', "Créez les comptes avec une seule tâche et une boucle (loop) sur equipe_web."),
                 ('for s in web1 web2; do for u in thomas nadia julien; do sur $s "id -nG $u" | grep -qw www-data || { echo "MSG:$u sur $s"; exit 1; }; done; done', "Les comptes thomas, nadia et julien doivent exister sur web1 et web2, membres du groupe www-data."),
                 ('! sur db1 "id thomas"', "Les comptes de l'équipe web ne doivent pas exister sur db1."),
             ]},
            {"id": "A6.2", "points": 4, "title": "Signaler la recette",
             "ticket": {"from": "sophie", "body": "Un client a passé une vraie commande sur le serveur de recette… Sur les serveurs de recette <strong>uniquement</strong>, la page doit afficher un bandeau <strong>RECETTE</strong>. Et Thomas voudrait l'outil <code>htop</code> pour ses tests, mais seulement en recette : pas d'outils superflus en production."},
             "desc": "La page de web2 (recette) affiche <code>RECETTE</code>, pas celle de web1 ; <code>htop</code> est installé sur web2 et pas sur web1, grâce à une condition <code>when</code>.",
             "hints": ["Dans le modèle : <code>{% if environnement == \"recette\" %}</code> … <code>{% endif %}</code>.", "Une tâche <code>apt</code> avec <code>when: environnement == \"recette\"</code>."],
             "checks": [
                 ('grep -qE "^[[:space:]]*when:" $I/web.yml', "L'installation de htop doit dépendre d'une condition (when)."),
                 ('sur web2 "test -x /usr/bin/htop"', "htop n'est pas installé sur web2 (recette)."),
                 ('! sur web1 "test -x /usr/bin/htop"', "htop ne doit être installé qu'en recette : web1 est en production."),
                 ('page web2:8080 | grep -q RECETTE', "La page de web2 doit afficher un bandeau RECETTE."),
                 ('! page web1:8080 | grep -q RECETTE', "Le bandeau RECETTE ne doit pas apparaître sur web1 (production) : utilisez {% if %} dans le modèle."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    7: {
        "title": "Jour 7 — La chasse aux dérives, puis les rôles",
        "description": "Détecter ce qui a été modifié à la main, puis organiser un projet réutilisable. Compétences : --check, --diff, ansible-galaxy init, rôles, site.yml.",
        "lesson": """<h3>Mode vérification : --check et --diff</h3><pre>ansible-playbook web.yml --check          # « à blanc » : dit ce qui changerait, sans rien changer<br>ansible-playbook web.yml --check --diff   # … et montre les différences dans les fichiers</pre><p>C'est l'outil idéal pour repérer une <strong>dérive</strong> : quelqu'un a modifié un serveur à la main, et il ne correspond plus à ce que décrit le code. Une tâche <code>changed</code> en mode vérification signale le serveur concerné. Rejouer le playbook ramène tout dans l'état décrit.</p><div class="tip">Si le code dit une chose et le serveur une autre, c'est le code qui a raison : toute modification passe par le playbook.</div><h3>Pourquoi des rôles ?</h3><p><code>web.yml</code> grossit, et demain il faudra un serveur de base de données, une supervision… Un <strong>rôle</strong> regroupe tout ce qu'il faut pour un service, dans une arborescence standard qu'Ansible sait lire.</p><pre>ansible-galaxy init --init-path roles web      # crée le squelette roles/web/</pre><pre>roles/web/<br>├── tasks/main.yml       # les tâches (une simple liste, sans hosts ni play)<br>├── handlers/main.yml    # les handlers<br>├── templates/           # les modèles .j2 (src: index.html.j2 suffit)<br>├── files/               # les fichiers copiés tels quels<br>└── defaults/main.yml    # valeurs par défaut des variables (priorité la plus faible)</pre>""" + SCHEMA_ROLES + """<pre># site.yml : le point d'entrée de toute l'infrastructure<br>- name: Serveurs web<br>  hosts: web<br>  become: true<br>  roles:<br>    - web</pre><p>Les <code>group_vars</code> et <code>host_vars</code> restent à la racine du projet : ce sont les réglages de <em>votre</em> infrastructure, alors que le rôle est générique.</p>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
d=web$((RANDOM % 2 + 1))
if sur $d "test -f /var/www/html/index.html"; then
  sur $d "sed -i 's|</body>|<p>Promo flash : -50 % sur tout le site ! (Julien)</p>\n</body>|' /var/www/html/index.html"
fi
emit DERIVE "$d"
''',
        "exercises": [
            {"id": "A7.1", "points": 4, "title": "La promo fantôme",
             "ticket": {"from": "sophie", "body": "Un client nous réclame une remise de 50 %… qu'on n'a jamais proposée ! Quelqu'un a modifié un serveur <strong>à la main</strong>. Sans te connecter aux serveurs, trouve lequel grâce à Ansible, note-le dans <code>~/infra/reponses/derive.txt</code>, puis remets tout en ordre."},
             "desc": "Le nom du serveur modifié à la main dans <code>~/infra/reponses/derive.txt</code>, et plus aucune fausse promotion en ligne.",
             "hints": ["<code>ansible-playbook web.yml --check --diff</code> : quel serveur a une tâche <code>changed</code> ? (Si vous avez déjà rejoué le playbook, la dérive est corrigée : « Réinitialiser les fichiers de cette étape » la recrée.)", "Puis rejouez <code>ansible-playbook web.yml</code> pour revenir à l'état décrit."],
             "checks": [
                 ('[ "$(ans $I/reponses/derive.txt)" = "$LAB_DERIVE" ]', "reponses/derive.txt ne contient pas le nom du serveur modifié à la main (ansible-playbook web.yml --check --diff)."),
                 ('for s in web1 web2; do ! page $s:8080 | grep -q "Promo flash" || exit 1; done', "La fausse promotion est toujours en ligne : rejouez le playbook."),
             ]},
            {"id": "A7.2", "points": 6, "title": "Ranger en rôle", "manual": True,
             "ticket": {"from": "lea", "body": "Avant d'ajouter la base de données, on range : transforme le contenu de <code>web.yml</code> en un rôle <code>web</code> (<code>roles/web</code>), et crée le playbook <code>site.yml</code> qui l'applique au groupe web. Le résultat sur les serveurs doit rester strictement le même."},
             "desc": "Le rôle <code>roles/web</code> contient les tâches, les handlers et les modèles ; <code>site.yml</code> l'applique au groupe <code>web</code> ; <code>ansible-playbook site.yml</code> réussit et, rejoué, ne change rien.",
             "hints": ["<code>ansible-galaxy init --init-path roles web</code>, puis déplacez les tâches dans <code>roles/web/tasks/main.yml</code>, les handlers dans <code>roles/web/handlers/main.yml</code> et les modèles dans <code>roles/web/templates/</code>.", "Dans un rôle, <code>src: index.html.j2</code> suffit : Ansible cherche dans <code>templates/</code> du rôle."],
             "checks": [
                 ('[ -f $I/roles/web/tasks/main.yml ] && [ -f $I/roles/web/handlers/main.yml ]', "Le rôle web doit avoir tasks/main.yml et handlers/main.yml (ansible-galaxy init --init-path roles web)."),
                 ('ls $I/roles/web/templates/*.j2 >/dev/null 2>&1', "Les modèles doivent être rangés dans roles/web/templates/."),
                 ("yjson $I/site.yml | jq -e 'any(.[]; .hosts == \"web\" and ((.roles // []) | map(if type == \"string\" then . else (.role // .name) end) | index(\"web\")))' >/dev/null", "site.yml doit appliquer le rôle web au groupe web (roles: - web)."),
                 ('joue site.yml || recap', "ansible-playbook site.yml échoue (voir le récapitulatif)."),
                 ('joue site.yml && rien_change || recap', "Rejoué, site.yml modifie encore quelque chose : il n'est pas idempotent."),
                 ('page web1:8080 | grep -q web1 && page web2:8080 | grep -q web2', "Après site.yml, les serveurs web ne servent plus leur page sur le port 8080."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Jour 8 — Secrets et mise en production",
        "description": "Protéger les secrets, ajouter un serveur, tout décrire en une commande. Compétences : ansible-vault, lineinfile, --limit, projet complet.",
        "lesson": """<h3>Les secrets</h3><p>Un mot de passe ne doit jamais être écrit en clair dans un dépôt Git. <strong>Ansible Vault</strong> chiffre des fichiers de variables (AES-256) ; ils ne sont déchiffrés qu'en mémoire, au moment du déploiement.</p>""" + SCHEMA_VAULT + """<pre>echo "une-longue-phrase-secrète" &gt; ~/.vault_pass && chmod 600 ~/.vault_pass   # la clé, hors du projet<br>ansible-vault create group_vars/bdd/vault.yml    # crée et ouvre un fichier chiffré<br>ansible-vault encrypt group_vars/bdd/vault.yml   # ou chiffre un fichier existant<br>ansible-vault view group_vars/bdd/vault.yml<br>ansible-vault edit group_vars/bdd/vault.yml</pre><pre># ansible.cfg<br>[defaults]<br>vault_password_file = ~/.vault_pass</pre><p>Convention : préfixer les variables secrètes par <code>vault_</code>. <code>group_vars/bdd/</code> peut être un dossier : tous ses fichiers sont chargés.</p><div class="tip">Ajoutez <code>no_log: true</code> à une tâche qui manipule un secret : sa valeur n'apparaîtra pas dans la sortie d'Ansible.</div><h3>Modifier une ligne d'un fichier : lineinfile</h3><pre>    - name: Redis écoute sur le réseau<br>      ansible.builtin.lineinfile:<br>        path: /etc/redis/redis.conf<br>        regexp: '^bind '<br>        line: bind 0.0.0.0<br>      notify: Redémarrer redis</pre><p>La ligne qui correspond à <code>regexp</code> est remplacée (ou ajoutée si aucune ne correspond) : c'est idempotent.</p><h3>Un nouveau serveur</h3><ol><li>accès : empreinte SSH et clé (comme au jour 1) ;</li><li>une ligne dans l'inventaire ;</li><li><code>ansible-playbook site.yml --limit web3</code> : seul web3 est configuré, identique aux autres.</li></ol><h3>Toute l'infra en une commande</h3><pre>- name: Serveurs web<br>  hosts: web<br>  become: true<br>  roles: [web]<br><br>- name: Base de données<br>  hosts: bdd<br>  become: true<br>  roles: [redis]</pre><p>Un serveur tombe en panne ? On en installe un neuf, on lance <code>site.yml</code>, et il est reconstruit à l'identique. C'est tout l'intérêt de l'<em>Infrastructure as Code</em>.</p>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
neuf web3
pw="Rando-$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 14)"
printf 'De : Sophie Marchand\nObjet : Redis de production\n\nLe mot de passe de Redis sur db1 sera : %s\nNe le recopie surtout pas en clair dans ~/infra !\n' "$pw" > $H/message-sophie.txt
own $H/message-sophie.txt
chmod 600 $H/message-sophie.txt
emit REDISPW "$pw"
''',
        "exercises": [
            {"id": "A8.1", "points": 6, "title": "Le mot de passe de Redis",
             "ticket": {"from": "sophie", "body": "L'API aura besoin d'un Redis sur <code>db1</code>, accessible depuis le réseau (port 6379), mais <strong>protégé par mot de passe</strong>. Je t'ai laissé le mot de passe dans <code>~/message-sophie.txt</code>. Écris un rôle <code>redis</code> appliqué au groupe <code>bdd</code> dans <code>site.yml</code>, et range le mot de passe dans un fichier chiffré avec Ansible Vault : je ne veux le voir en clair nulle part dans <code>~/infra</code>."},
             "desc": "Redis tourne sur db1, écoute sur le réseau et exige le mot de passe de Sophie ; il est installé par un rôle <code>redis</code> appliqué au groupe <code>bdd</code> dans <code>site.yml</code> ; le mot de passe est dans <code>group_vars/bdd/vault.yml</code>, chiffré, et n'apparaît en clair nulle part dans <code>~/infra</code>.",
             "hints": ["Rôle <code>redis</code> : <code>apt</code> redis-server, deux <code>lineinfile</code> sur <code>/etc/redis/redis.conf</code> (<code>^bind </code> → <code>bind 0.0.0.0</code> ; <code>^#? ?requirepass </code> → <code>requirepass {{ vault_redis_password }}</code>), un handler qui redémarre <code>redis-server</code>.", "<code>ansible-vault encrypt group_vars/bdd/vault.yml</code>, et <code>vault_password_file = ~/.vault_pass</code> dans ansible.cfg (la clé hors de ~/infra)."],
             "checks": [
                 ('[ -f $I/roles/redis/tasks/main.yml ]', "Le rôle redis n'existe pas (roles/redis/tasks/main.yml)."),
                 ("yjson $I/site.yml | jq -e 'any(.[]; .hosts == \"bdd\" and ((.roles // []) | map(if type == \"string\" then . else (.role // .name) end) | index(\"redis\")))' >/dev/null", "site.yml doit appliquer le rôle redis au groupe bdd."),
                 ('head -c 14 $I/group_vars/bdd/vault.yml 2>/dev/null | grep -q "^\\$ANSIBLE_VAULT"', "group_vars/bdd/vault.yml doit exister et être chiffré avec ansible-vault."),
                 ('! grep -rqF -- "$LAB_REDISPW" $I', "Le mot de passe de Redis apparaît en clair dans ~/infra : il ne doit être que dans le fichier chiffré."),
                 ('r=$(redis PING); [ "${r%% *}" = -NOAUTH ]', "Redis de db1 ne répond pas sur 10.10.0.21:6379, ou accepte les commandes sans mot de passe."),
                 ('[ "$(redis "AUTH $LAB_REDISPW" PING)" = +PONG ]', "Redis n'accepte pas le mot de passe donné par Sophie."),
             ]},
            {"id": "A8.2", "points": 5, "title": "web3 arrive",
             "ticket": {"from": "thomas", "body": "Les soldes approchent : l'hébergeur vient de nous livrer un troisième serveur web, <code>web3</code> (compte <code>admin</code>, mot de passe <code>cimes</code>, installation neuve). Il doit être configuré exactement comme les deux autres. Et ne relance pas tout le parc pour ça, on est en pleine journée."},
             "desc": "web3 est dans le groupe <code>web</code> de l'inventaire, accessible par clé SSH, et configuré comme les autres serveurs web (page sur le port 8080, comptes de l'équipe).",
             "hints": ["Accès : <code>ssh-keyscan web3 &gt;&gt; ~/.ssh/known_hosts</code> et <code>ssh-copy-id admin@web3</code> ; puis une ligne dans l'inventaire.", "<code>ansible-playbook site.yml --limit web3</code>"],
             "checks": [
                 ('[ "$(groupe web)" = "web1,web2,web3" ]', "web3 doit être ajouté au groupe web de l'inventaire."),
                 ('ssh_ok web3', "Pas de connexion SSH sans mot de passe vers web3 (empreinte et clé)."),
                 ('page web3:8080 | grep -q web3', "web3 ne sert pas la page de la boutique sur le port 8080 (site.yml --limit web3)."),
                 ('sur web3 "id -nG nadia" | grep -qw www-data', "web3 n'a pas reçu toute la configuration des serveurs web (comptes de l'équipe)."),
             ]},
            {"id": "A8.3", "points": 4, "title": "Toute l'infra en une commande", "manual": True,
             "ticket": {"from": "lea", "body": "Dernière étape avant l'audit de demain : une seule commande, <code>ansible-playbook site.yml</code>, doit décrire <strong>toute</strong> l'infrastructure (les trois serveurs web et la base), et ne rien changer si tout est conforme. Bravo pour ce parcours !"},
             "desc": "<code>ansible-playbook site.yml</code> configure web1, web2, web3 et db1 ; lancé deux fois, il réussit et le second passage ne change rien.",
             "hints": ["Deux plays dans <code>site.yml</code> : le rôle web pour le groupe <code>web</code>, le rôle redis pour <code>bdd</code>.", "Une tâche toujours <code>changed</code> ? Regardez le récapitulatif, puis la tâche en cause avec <code>--diff</code>."],
             "checks": [
                 ('joue site.yml || recap', "ansible-playbook site.yml échoue (voir le récapitulatif)."),
                 ('[ "$(grep -cE "^(web1|web2|web3|db1) +: ok=" /tmp/lab-jeu.txt)" = 4 ]', "site.yml doit configurer les quatre serveurs : web1, web2, web3 et db1."),
                 ('joue site.yml && rien_change || recap', "Rejoué, site.yml modifie encore quelque chose : il n'est pas idempotent."),
             ]},
        ],
    },
}
