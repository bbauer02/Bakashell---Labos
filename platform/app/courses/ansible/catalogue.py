"""Parcours « Ansible : automatiser l'infrastructure ».

L'étudiant travaille sur un poste de contrôle (Ansible, sans sudo). Les serveurs de l'entreprise (web1, web2, db1,
puis web3) sont de vrais conteneurs Debian avec SSH, qui tournent dans le moteur Docker interne du conteneur de
l'étudiant (runtime Sysbox en production). L'étudiant n'a pas accès à ce moteur : pour lui, ce sont des serveurs
distants, joignables uniquement en SSH. Un dépôt APT interne (depot.cimes.lan) fournit les paquets sans Internet.

Les vérifications (en root sur le poste de contrôle) observent le résultat réel sur les serveurs (docker exec,
requêtes HTTP, connexion à Redis) et, pour les exercices « manual », rejouent les playbooks de l'étudiant en tant
qu'etudiant. Quand l'enjeu est de prouver que le travail est fait PAR le code (et non à la main en SSH), elles
cassent d'abord l'état du serveur (ou le réinstallent à neuf) puis rejouent le playbook ; pour les commandes ad hoc,
elles lisent le journal de sudo des serveurs (/var/log/sudo.log), où chaque commande d'Ansible porte la marque
« BECOME-SUCCESS ».
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
docker image inspect noeud-cimes:2 >/dev/null 2>&1 || { echo "Les serveurs ne sont pas prêts" >&2; exit 1; }
declare -A IP=([web1]=11 [web2]=12 [web3]=13 [db1]=21)
# serveur <nom> : démarre le serveur (le crée s'il n'existe pas), et attend son SSH
serveur() {
  if docker inspect "$1" >/dev/null 2>&1; then docker start "$1" >/dev/null
  # SYS_PTRACE : comme sur une vraie machine, root peut identifier les processus des autres comptes
  # (start-stop-daemon --exec en a besoin pour arrêter redis-server, qui tourne sous le compte redis)
  else docker run -d --name "$1" --hostname "$1" --network cimes --ip "10.10.0.${IP[$1]}" --cap-add SYS_PTRACE \
         --add-host depot.cimes.lan:10.10.0.1 --restart unless-stopped --init noeud-cimes:2 >/dev/null
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
# reinstalle <nom> : réinstallé par l'hébergeur, SANS prévenir le poste de contrôle (l'ancienne empreinte reste connue)
reinstalle() { docker rm -f "$1" >/dev/null 2>&1 || true; serveur "$1"; }
sur() { docker exec "$1" bash -c "$2"; }
# serveurs web existants (web3 n'arrive qu'au jour 8)
webs() { for s in web1 web2 web3; do docker inspect "$s" >/dev/null 2>&1 && echo $s; done; true; }
mkdir -p $I/reponses $H/demandes
own $I $H/demandes
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
# texte <hôte:port> : la page, balises retirées et espaces regroupés (pour chercher une phrase)
texte() { page "$1" | sed 's/<[^>]*>/ /g' | tr -s ' \t\n' ' '; }
yjson() { python3 -c 'import sys, yaml, json; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))' "$1" 2>/dev/null; }
# var <serveur> <variable> : valeur d'une variable d'inventaire (group_vars, host_vars…) pour ce serveur
var() { etu "ansible-inventory --host $1" | jq -r ".$2 // empty"; }
groupe() { etu "ansible-inventory -i inventaire.ini --list" | jq -r ".$1.hosts // [] | sort | join(\",\")"; }
ssh_ok() { etu "ssh -o BatchMode=yes -o ConnectTimeout=5 admin@$1 true" >/dev/null; }
# joue <playbook> [options] : lance le playbook de l'étudiant ; échoue si un serveur est en échec ou injoignable
joue() { etu "ansible-playbook $* 2>&1" > /tmp/lab-jeu.txt; grep -qE "^[a-z0-9]+ +: ok=" /tmp/lab-jeu.txt && ! grep -qE "failed=[1-9]|unreachable=[1-9]" /tmp/lab-jeu.txt; }
rien_change() { ! grep -qE "changed=[1-9]" /tmp/lab-jeu.txt; }
# echec_attendu : le dernier jeu a bien démarré, puis échoué sur un serveur (pas une erreur de syntaxe)
echec_attendu() { grep -qE "failed=[1-9]" /tmp/lab-jeu.txt && ! grep -q "^ERROR!" /tmp/lab-jeu.txt; }
# changes <serveur> : valeur de changed= pour ce serveur dans le dernier jeu
changes() { grep -E "^$1 +: ok=" /tmp/lab-jeu.txt | grep -oE "changed=[0-9]+" | cut -d= -f2; }
# recap : récapitulatif (ou erreur) du dernier jeu, affiché sous le message d'échec
recap() {
  grep -E "^[a-z0-9]+ +: ok=|ERROR!|fatal:" /tmp/lab-jeu.txt | head -3 | cut -c1-160 | sed 's/^/MSG:/'
  grep -qiE "no hosts matched|Could not match supplied host pattern" /tmp/lab-jeu.txt && echo "MSG:aucun serveur visé : « hosts » ne correspond à aucun serveur de l'inventaire (no hosts matched)"
  return 1
}
# redis <commande>... : envoie des commandes à Redis sur db1 et affiche la dernière réponse
redis() ( exec 3<>/dev/tcp/10.10.0.21/6379 || exit 1; printf '%s\r\n' "$@" >&3; for _ in "$@"; do read -t 3 -r l <&3 || break; done; echo "${l%$'\r'}" )
# droits <serveur> <chemin> : « mode propriétaire groupe »
droits() { sur "$1" "stat -c '%a %U %G' '$2'"; }
# paquet <serveur> <nom> : vrai si le paquet est installé
paquet() { sur "$1" "dpkg-query -W -f='\${Status}' $2 2>/dev/null" | grep -q "install ok installed"; }
# somme <serveur> <fichier> : empreinte du contenu (pour vérifier qu'un fichier n'a pas changé)
somme() { sur "$1" "sha256sum < '$2' 2>/dev/null" | cut -c1-64; }
# sans_commentaires <modèle.j2> : le modèle sans ses commentaires Jinja {# … #}
sans_commentaires() { python3 -c 'import re, sys; print(re.sub(r"\{#.*?#\}", "", open(sys.argv[1], encoding="utf-8").read(), flags=re.S))' "$1" 2>/dev/null; }
# taches <fichiers…> : toutes les tâches et tous les handlers (blocs compris) des playbooks et des rôles, en JSON
taches() { python3 - "$@" <<'PY' 2>/dev/null
import glob, json, sys, yaml
class L(yaml.SafeLoader): pass
L.add_multi_constructor("!", lambda l, s, n: None)
SECTIONS = ("pre_tasks", "roles", "tasks", "post_tasks", "handlers")
def parcours(x):
    if isinstance(x, list):
        for e in x: yield from parcours(e)
    elif isinstance(x, dict):
        if "hosts" in x:
            for k in SECTIONS:
                if k != "roles": yield from parcours(x.get(k) or [])
            return
        yield x
        for k in ("block", "rescue", "always"):
            yield from parcours(x.get(k) or [])
for motif in sys.argv[1:]:
    for f in sorted(glob.glob(motif)):
        try: d = yaml.load(open(f, encoding="utf-8"), Loader=L)
        except Exception: continue
        for t in parcours(d): print(json.dumps(t, ensure_ascii=False))
PY
}
# M : fonction jq « mod(nom) », vraie pour une tâche qui appelle ce module (nom court ou FQCN)
M='def mod($m): has($m) or has("ansible.builtin." + $m) or has("ansible.legacy." + $m);'
PROJET="$I/site.yml $I/roles/*/tasks/*.yml $I/roles/*/handlers/*.yml"
# a_la_main <serveur> <depuis (epoch)> : commandes de modification lancées avec sudo À LA MAIN (hors Ansible)
a_la_main() { sur "$1" "cat /var/log/sudo.log 2>/dev/null" | python3 -c '
import calendar, re, sys, time
suspects = {"useradd", "usermod", "userdel", "adduser", "deluser", "gpasswd", "chmod", "chown", "rm", "mv", "cp", "tee",
            "sed", "nano", "vi", "vim", "apt", "apt-get", "dpkg", "service", "bash", "sh", "su", "install", "touch", "ln"}
an = time.gmtime().tm_year
for l in sys.stdin:
    m = re.match(r"(\w{3} +\d+ \d\d:\d\d:\d\d) : \S+ : .*?COMMAND=(\S+)(.*)", l)
    if not m or "BECOME-SUCCESS" in l: continue
    t = calendar.timegm(time.strptime(f"{an} {m.group(1)}", "%Y %b %d %H:%M:%S"))
    if t >= int(sys.argv[1]) and m.group(2).rsplit("/", 1)[-1] in suspects: print((m.group(2) + m.group(3))[:90])' "$2"; }
# coffres : contenu déchiffré (avec la clé configurée de l'étudiant) de tout ce qui est chiffré par Ansible Vault dans
# ~/infra : fichiers entiers (ansible-vault encrypt) et valeurs « !vault » (ansible-vault encrypt_string)
coffres() {
  local f n=0
  for f in $(grep -rlE '^\$ANSIBLE_VAULT|!vault' $I 2>/dev/null); do
    if head -c 14 "$f" | grep -q '^\$ANSIBLE_VAULT'; then etu "ansible-vault view '$f'"; continue; fi
    rm -rf /tmp/lab-coffres && mkdir -p /tmp/lab-coffres && chmod 755 /tmp/lab-coffres
    python3 - "$f" /tmp/lab-coffres <<'PY' 2>/dev/null
import os, re, sys, textwrap
t = open(sys.argv[1], encoding="utf-8").read()
for i, m in enumerate(re.finditer(r"!vault *\|?-? *\n((?:[ \t]+\S.*\n?)+)", t)):
    open(os.path.join(sys.argv[2], str(i)), "w").write(textwrap.dedent(m.group(1)))
PY
    chmod 644 /tmp/lab-coffres/* 2>/dev/null
    for n in /tmp/lab-coffres/*; do [ -f "$n" ] && etu "ansible-vault view $n"; echo; done
  done
  rm -rf /tmp/lab-coffres
}
# cle_coffre : fichier de la clé du coffre désigné par ansible.cfg (vault_password_file, ou vault_identity_list)
cle_coffre() {
  local d f
  d=$(etu "ansible-config dump --only-changed")
  f=$(sed -n 's/^DEFAULT_VAULT_PASSWORD_FILE([^)]*) = //p' <<<"$d")
  [ -n "$f" ] || f=$(sed -n "s/^DEFAULT_VAULT_IDENTITY_LIST([^)]*) = \['\([^']*\)'.*/\1/p" <<<"$d" | sed 's/^[^@]*@//')
  echo "${f/#\~/$H}"
}
# sudo_ansible <serveur> : heure (epoch) de chaque commande lancée par Ansible avec become
sudo_ansible() { sur "$1" "grep BECOME-SUCCESS /var/log/sudo.log 2>/dev/null" | cut -c1-15 | python3 -c '
import calendar, sys, time
an = time.gmtime().tm_year
for l in sys.stdin: print(calendar.timegm(time.strptime(f"{an} {l.strip()}", "%Y %b %d %H:%M:%S")))'; }
# reconstruit <serveur> : serveur réinstallé à neuf par l'hébergeur, avec les mêmes clés d'hôte et la clé d'admin
# déjà installée (comme une image de l'hébergeur) : tout ce qui n'est pas décrit par le code est perdu
reconstruit() {
  local d=/tmp/lab-rec-$1 ip
  ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$1") || return 1
  rm -rf $d && mkdir -p $d && docker cp "$1":/etc/ssh $d/ssh && docker cp "$1":/home/admin/.ssh $d/cles || return 1
  docker rm -f "$1" >/dev/null
  docker create --name "$1" --hostname "$1" --network cimes --ip "$ip" --cap-add SYS_PTRACE \
    --add-host depot.cimes.lan:10.10.0.1 --restart unless-stopped --init noeud-cimes:2 >/dev/null || return 1
  docker cp $d/ssh/. "$1":/etc/ssh/ && docker cp $d/cles "$1":/home/admin/.ssh && docker start "$1" >/dev/null || return 1
  rm -rf $d
  for _ in $(seq 1 40); do docker exec "$1" pgrep -x sshd >/dev/null 2>&1 && break; sleep 0.5; done
  docker exec "$1" chown -R admin:admin /home/admin/.ssh
}
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
<text class="mono" x="24" y="76">ansible vitrine1 -m …</text>
<text class="t2" x="24" y="104">① emballe le module</text><text class="mono" x="24" y="120">AnsiballZ_&lt;module&gt;.py</text>
<text class="t2" x="24" y="160">⑤ affiche le résultat</text>
<rect class="b" x="440" y="20" width="190" height="160" rx="10"/>
<text class="ttl" x="454" y="46">vitrine1</text>
<text class="t2" x="454" y="76">③ python3 AnsiballZ_….py</text>
<text class="t2" x="454" y="96">   (avec sudo si « become »)</text>
<text class="t2" x="454" y="124">④ supprime le fichier</text>
<text class="mono" x="454" y="152">~/.ansible/tmp/…</text>
<path class="la" d="M182,70 L436,70" marker-end="url(#fl2)"/><text class="t2" x="230" y="62">② copie par SSH (sftp)</text>
<path class="l" d="M436,150 L184,150" marker-end="url(#fg2)"/><text class="t2" x="230" y="142">résultat en JSON : ok, changed…</text>
</svg><figcaption>Chaque tâche suit ce trajet (le module ping compris). L'option <code>-vvv</code> affiche toutes ces étapes.</figcaption></figure>"""

SCHEMA_IDEMPOTENCE = f"""<figure class="schema"><svg viewBox="0 0 640 190" role="img" aria-label="Le module compare l'état désiré et l'état actuel">{_fleches(3)}
<rect class="a" x="10" y="16" width="190" height="62" rx="8"/><text class="ttl" x="22" y="40">État désiré</text><text class="mono" x="22" y="62">haproxy : installé</text>
<rect class="b" x="10" y="108" width="190" height="62" rx="8"/><text class="ttl" x="22" y="132">État actuel du serveur</text><text class="t2" x="22" y="154">haproxy installé ? oui / non</text>
<rect class="b" x="250" y="62" width="150" height="62" rx="8"/><text x="264" y="88">Le module</text><text class="t2" x="264" y="108">compare les deux</text>
<path class="l" d="M200,47 L248,82" marker-end="url(#fg3)"/><path class="l" d="M200,139 L248,106" marker-end="url(#fg3)"/>
<rect class="g" x="440" y="10" width="190" height="46" rx="8"/><text x="452" y="30">ok</text><text class="t2" x="452" y="47">déjà conforme : rien à faire</text>
<rect class="w" x="440" y="70" width="190" height="46" rx="8"/><text x="452" y="90">changed</text><text class="t2" x="452" y="107">modifié pour être conforme</text>
<rect class="r" x="440" y="130" width="190" height="46" rx="8"/><text x="452" y="150">failed</text><text class="t2" x="452" y="167">impossible : erreur expliquée</text>
<path class="l" d="M400,86 L438,33" marker-end="url(#fg3)"/><path class="l" d="M400,93 L438,93" marker-end="url(#fg3)"/><path class="l" d="M400,100 L438,153" marker-end="url(#fg3)"/>
</svg><figcaption>On décrit un état, pas une suite de commandes : relancer la même tâche ne refait que ce qui manque. C'est l'idempotence.</figcaption></figure>"""

SCHEMA_PLAYBOOK = f"""<figure class="schema"><svg viewBox="0 0 640 250" role="img" aria-label="Un playbook contient des plays, qui contiennent des tâches">{_fleches(4)}
<rect class="b" x="8" y="8" width="420" height="234" rx="10"/><text class="ttl" x="22" y="32">Playbook</text><text class="mono" x="100" y="32">lb.yml</text>
<rect class="a" x="22" y="44" width="392" height="186" rx="8"/><text x="36" y="68">Play : « Répartiteurs de charge »</text>
<text class="mono" x="36" y="88">hosts: lb   become: true</text>
<rect class="g" x="36" y="102" width="364" height="54" rx="6"/><text x="48" y="124">Tâche 1 : Installer haproxy</text><text class="mono" x="48" y="144">ansible.builtin.apt</text>
<rect class="g" x="36" y="166" width="364" height="54" rx="6"/><text x="48" y="188">Tâche 2 : Démarrer haproxy</text><text class="mono" x="48" y="208">ansible.builtin.service</text>
<rect class="b" x="480" y="80" width="150" height="40" rx="8"/><text x="494" y="105">lb1</text>
<rect class="b" x="480" y="140" width="150" height="40" rx="8"/><text x="494" y="165">lb2</text>
<path class="la" d="M414,110 L478,100" marker-end="url(#fl4)"/><path class="la" d="M414,130 L478,158" marker-end="url(#fl4)"/>
<text class="t2" x="480" y="210">chaque tâche est jouée sur</text><text class="t2" x="480" y="226">tous les serveurs, puis la suivante</text>
</svg><figcaption>Un playbook est une liste de plays ; un play associe des serveurs (<code>hosts</code>) à une liste de tâches ; chaque tâche appelle un module.</figcaption></figure>"""

SCHEMA_VARIABLES = f"""<figure class="schema"><svg viewBox="0 0 640 240" role="img" aria-label="Les variables et les facts alimentent un modèle Jinja2">{_fleches(5)}
<rect class="b" x="8" y="10" width="200" height="56" rx="8"/><text class="mono" x="20" y="32">group_vars/front.yml</text><text class="t2" x="20" y="52">saison: hiver</text>
<rect class="w" x="8" y="84" width="200" height="56" rx="8"/><text class="mono" x="20" y="106">host_vars/vitrine2.yml</text><text class="t2" x="20" y="126">saison: été</text>
<rect class="b" x="8" y="158" width="200" height="66" rx="8"/><text x="20" y="180">Facts (collectés)</text><text class="mono" x="20" y="200">ansible_facts[…]</text><text class="t2" x="20" y="216">IP, OS, mémoire…</text>
<rect class="a" x="250" y="70" width="170" height="92" rx="8"/><text class="ttl" x="262" y="94">Modèle Jinja2</text><text class="mono" x="262" y="116">accueil.html.j2</text><text class="mono" x="262" y="136">{{{{ inventory_hostname }}}}</text><text class="mono" x="262" y="152">{{{{ saison }}}}</text>
<path class="l" d="M208,38 L248,92" marker-end="url(#fg5)"/><path class="l" d="M208,112 L248,116" marker-end="url(#fg5)"/><path class="l" d="M208,190 L248,140" marker-end="url(#fg5)"/>
<rect class="g" x="460" y="36" width="170" height="62" rx="8"/><text x="472" y="58">vitrine1 : accueil.html</text><text class="t2" x="472" y="78">vitrine1 · hiver</text><text class="t2" x="472" y="92">192.168.5.21</text>
<rect class="g" x="460" y="134" width="170" height="62" rx="8"/><text x="472" y="156">vitrine2 : accueil.html</text><text class="t2" x="472" y="176">vitrine2 · été</text><text class="t2" x="472" y="190">192.168.5.22</text>
<path class="la" d="M420,100 L458,68" marker-end="url(#fl5)"/><path class="la" d="M420,132 L458,164" marker-end="url(#fl5)"/>
</svg><figcaption>Un seul modèle, un fichier différent par serveur. La variable de l'hôte (host_vars) l'emporte sur celle du groupe (group_vars).</figcaption></figure>"""

SCHEMA_HANDLERS = f"""<figure class="schema"><svg viewBox="0 0 640 210" role="img" aria-label="Un handler ne s'exécute que si une tâche qui le notifie a changé quelque chose">{_fleches(6)}
<text class="ttl" x="10" y="26">1er passage : la configuration change</text>
<rect class="g" x="10" y="38" width="130" height="44" rx="6"/><text x="20" y="58">apt haproxy</text><text class="t2" x="20" y="74">ok</text>
<rect class="w" x="160" y="38" width="170" height="44" rx="6"/><text x="170" y="58">template haproxy.cfg</text><text class="t2" x="170" y="74">changed → notify</text>
<rect class="g" x="350" y="38" width="110" height="44" rx="6"/><text x="360" y="58">copy page</text><text class="t2" x="360" y="74">ok</text>
<rect class="a" x="490" y="38" width="140" height="44" rx="6"/><text x="500" y="58">handler</text><text class="t2" x="500" y="74">recharge haproxy</text>
<path class="l" d="M140,60 L158,60"/><path class="l" d="M330,60 L348,60"/><path class="l" d="M460,60 L488,60" marker-end="url(#fg6)"/>
<path class="ld" d="M245,82 C245,112 560,112 560,84" marker-end="url(#fw6)"/><text class="t2" x="300" y="120">exécuté une fois, à la fin de la section de tâches</text>
<text class="ttl" x="10" y="152">2e passage : rien n'a changé</text>
<rect class="g" x="10" y="162" width="130" height="40" rx="6"/><text x="20" y="187">apt haproxy : ok</text>
<rect class="g" x="160" y="162" width="170" height="40" rx="6"/><text x="170" y="187">template : ok</text>
<rect class="g" x="350" y="162" width="110" height="40" rx="6"/><text x="360" y="187">copy : ok</text>
<rect class="b" x="490" y="162" width="140" height="40" rx="6"/><text class="t2" x="500" y="187">handler non exécuté</text>
<path class="l" d="M140,182 L158,182"/><path class="l" d="M330,182 L348,182"/><path class="l" d="M460,182 L488,182"/>
</svg><figcaption>Le service n'est rechargé que si sa configuration a réellement changé : pas de coupure inutile. Attention : si une tâche échoue avant la fin de la section, le handler n'est pas exécuté sur ce serveur.</figcaption></figure>"""

SCHEMA_ROLES = f"""<figure class="schema"><svg viewBox="0 0 640 230" role="img" aria-label="site.yml applique des rôles à des groupes de serveurs">{_fleches(7)}
<rect class="a" x="10" y="80" width="130" height="60" rx="8"/><text class="ttl" x="24" y="106">site.yml</text><text class="t2" x="24" y="126">toute l'infra</text>
<rect class="b" x="200" y="10" width="220" height="100" rx="8"/><text class="ttl" x="214" y="32">rôle web</text>
<text class="mono" x="214" y="52">tasks/main.yml</text><text class="mono" x="214" y="68">handlers/main.yml</text><text class="mono" x="214" y="84">templates/*.j2</text><text class="mono" x="214" y="100">defaults/ · vars/</text>
<rect class="b" x="200" y="130" width="220" height="84" rx="8"/><text class="ttl" x="214" y="152">rôle redis</text>
<text class="mono" x="214" y="172">tasks/main.yml</text><text class="mono" x="214" y="188">handlers/main.yml</text><text class="mono" x="214" y="204">defaults/main.yml</text>
<path class="la" d="M140,100 L198,62" marker-end="url(#fl7)"/><path class="la" d="M140,120 L198,170" marker-end="url(#fl7)"/>
<rect class="g" x="470" y="36" width="160" height="48" rx="8"/><text x="482" y="58">groupe web</text><text class="t2" x="482" y="75">web1 · web2</text>
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
        "description": "Comprendre le modèle d'Ansible et préparer l'accès aux serveurs. Compétences : clés SSH, empreintes, inventaire, groupes, motifs de cible, ansible.cfg, ansible -m ping.",
        "lesson": INTRO + """<h3>Le problème</h3><p>Configurer un serveur à la main, c'est taper des commandes en SSH. Pour trois serveurs, on recommence trois fois ; pour trente, on se trompe forcément. Et six mois plus tard, personne ne sait plus ce qui a été fait.</p><h3>La réponse d'Ansible</h3><ul><li>On <strong>décrit</strong> l'état voulu dans des fichiers texte (YAML), versionnés comme du code : c'est l'<em>Infrastructure as Code</em>.</li><li>Ansible se connecte aux serveurs en <strong>SSH</strong> et fait ce qu'il faut pour atteindre cet état.</li><li><strong>Sans agent</strong> : rien à installer sur les serveurs, à part SSH et Python (déjà présents sur presque tous les Linux).</li><li>Mode <strong>push</strong> : c'est le poste de contrôle qui décide quand agir.</li></ul>""" + SCHEMA_SSH + """<h3>1. L'accès SSH par clé</h3><p>Ansible ouvre des dizaines de connexions SSH : impossible de taper un mot de passe à chaque fois. On utilise une <strong>paire de clés</strong> : la clé privée reste sur le poste de contrôle, la clé publique est ajoutée au fichier <code>~/.ssh/authorized_keys</code> du compte distant, sur chaque serveur. Exemple pour un serveur <code>vitrine1</code> et un compte <code>exploitant</code> :</p><pre>ssh-keygen -t ed25519                 # crée ~/.ssh/id_ed25519 (privée) et id_ed25519.pub (publique)<br>ssh-copy-id exploitant@vitrine1       # installe la clé publique (demande le mot de passe une dernière fois)<br>ssh exploitant@vitrine1 hostname      # plus de mot de passe</pre><div class="tip">À la première connexion, SSH affiche l'<strong>empreinte</strong> du serveur et demande de la confirmer ; elle est ensuite mémorisée dans <code>~/.ssh/known_hosts</code>. Ansible, lui, ne sait pas répondre à cette question : face à un serveur inconnu, la connexion échoue (<em>Host key verification failed</em>). Faites donc une première connexion à la main, en comparant l'empreinte affichée à celle que vous a communiquée l'hébergeur. <code>ssh-keyscan vitrine1 &gt;&gt; ~/.ssh/known_hosts</code> enregistre l'empreinte sans rien demander… donc <strong>sans la vérifier</strong> : acceptable sur un réseau de confiance, dangereux ailleurs.</div><h3>2. L'inventaire : quels serveurs ?</h3><p>Un fichier texte (format INI ou YAML) qui liste les serveurs et les range en <strong>groupes</strong>. Exemple d'une autre entreprise :</p><pre>[front]<br>vitrine1<br>vitrine2<br><br>[cache]<br>memo1<br><br>[prod:children]    # « children » : un groupe dont les membres sont d'autres groupes<br>front<br>cache</pre><p>Deux groupes existent toujours : <code>all</code> (tous les serveurs) et <code>ungrouped</code> (ceux qui ne sont dans aucun groupe). Un serveur peut appartenir à plusieurs groupes : par fonction, par ville, par environnement…</p><pre>ansible-inventory -i serveurs.ini --graph   # l'arbre des groupes<br>ansible-inventory -i serveurs.ini --list    # la même chose en JSON</pre><h3>3. Viser des serveurs : les motifs</h3><p>Partout où Ansible attend une cible (<code>ansible &lt;cible&gt;</code>, <code>hosts:</code> dans un playbook, <code>--limit</code>), on peut combiner des groupes :</p><pre>front              # un groupe<br>front:cache        # union : dans front OU dans cache<br>prod:&amp;front       # intersection : dans prod ET dans front<br>prod:!cache        # exclusion : dans prod SAUF ceux de cache<br>front[0]           # le premier serveur du groupe, dans l'ordre de l'inventaire<br>vitrine*           # joker sur les noms</pre><pre>ansible 'prod:!cache' -i serveurs.ini --list-hosts   # affiche les serveurs visés, sans rien exécuter</pre><div class="tip">Entourez les motifs de guillemets simples : sinon, c'est le shell qui interprète <code>!</code> et <code>&amp;</code>, avant même qu'Ansible ne les voie.</div><h3>4. ansible.cfg : les réglages du projet</h3><p>Ansible lit le fichier <code>ansible.cfg</code> du <strong>dossier courant</strong> (à défaut <code>~/.ansible.cfg</code>, puis <code>/etc/ansible/ansible.cfg</code>) : plus besoin de répéter les options à chaque commande. Exemple :</p><pre>[defaults]<br>inventory = serveurs.ini      # l'inventaire utilisé sans -i<br>remote_user = exploitant      # le compte utilisé sur les serveurs</pre><pre>ansible --version                     # version d'Ansible, et fichier de configuration réellement lu<br>ansible-config dump --only-changed    # les réglages qui diffèrent des valeurs par défaut</pre><h3>5. Premier contact</h3><pre>ansible prod -m ping    # le module ping vérifie SSH + Python : rien à voir avec le ping réseau</pre><pre>vitrine1 | SUCCESS =&gt; { "changed": false, "ping": "pong" }</pre><p>Ce poste utilise <strong>ansible-core 2.18</strong> : la documentation d'une autre version peut différer sur quelques détails.</p>""",
        "setup": r'''
for s in web1 web2 db1; do neuf $s; done
# Inventaire du futur datacenter (A1.4) : les deux villes (variante), les serveurs, les groupes et les demandes
# sont tirés au hasard ; les réponses attendues sont calculées par Ansible lui-même
v=${LAB_VARIANTE_A1_4:-$((RANDOM % 4))}
python3 - "$I/exercices" "$v" <<'PY'
import os, random, subprocess, sys
d, v = sys.argv[1], int(sys.argv[2])
os.makedirs(d, exist_ok=True)
VILLES = [("paris", "lyon"), ("lille", "nantes"), ("bordeaux", "rennes"), ("marseille", "toulouse")][v]
A, B = random.sample(VILLES, 2)
DEMANDES = [(f"Les serveurs web de {B.capitalize()}.", f"web:&{B}"),
            ("Toute la production, sauf les bases de données.", "production:!bdd"),
            (f"Les serveurs de recette situés à {A.capitalize()}.", f"recette:&{A}"),
            ("Le premier serveur du groupe web, dans l'ordre de l'inventaire (un seul serveur).", "web[0]"),
            ("Le dernier serveur du groupe bdd, dans l'ordre de l'inventaire (un seul serveur).", "bdd[-1]"),
            (f"Tous les serveurs, sauf ceux de {B.capitalize()}.", f"all:!{B}"),
            ("Les serveurs de cache et les bases de données.", "cache:bdd"),
            (f"Les serveurs de {A.capitalize()} qui ne sont pas en production.", f"{A}:!production")]
def cible(motif):
    r = subprocess.run(["ansible", "-i", "parc.ini", motif, "--list-hosts"], cwd=d, capture_output=True, text=True)
    return ",".join(sorted(l.strip() for l in r.stdout.splitlines()[1:] if l.strip()))
while True:
    hotes = {}
    for ville in VILLES:
        p = ville[:3]
        for i in range(1, random.randint(2, 4) + 1): hotes[f"{p}-web{i:02d}"] = ("web", ville)
        for i in range(1, random.randint(1, 3) + 1): hotes[f"{p}-db{i:02d}"] = ("bdd", ville)
        hotes[f"{p}-cache01"] = ("cache", ville)
    noms = list(hotes)
    random.shuffle(noms)
    recette = set(random.sample([n for n in noms if "cache" not in n], 3))
    txt = ""
    for g in ("web", "bdd", "cache") + VILLES:
        txt += f"[{g}]\n" + "".join(n + "\n" for n in noms if g in hotes[n]) + "\n"
    txt += "[recette]\n" + "".join(n + "\n" for n in noms if n in recette) + "\n"
    txt += "[production]\n" + "".join(n + "\n" for n in noms if n not in recette)
    open(os.path.join(d, "parc.ini"), "w").write("# Futur datacenter de Cimes & Sentiers (ne pas modifier)\n\n" + txt)
    choix = random.sample(DEMANDES, 4)
    attendus = [cible(m) for _, m in choix]
    if all(attendus) and len(set(attendus)) == 4:
        break
with open(os.path.join(d, "demandes.txt"), "w") as f:
    f.write("Demandes de Léa : pour chacune, un motif Ansible qui vise EXACTEMENT ces serveurs dans parc.ini.\n"
            "Réponses dans ~/infra/reponses/motifs.txt, une ligne par demande, dans l'ordre.\n\n")
    for i, (texte, _) in enumerate(choix, 1):
        f.write(f"{i}. {texte}\n")
for i, a in enumerate(attendus, 1):
    print(f"@ATTENDU{i}={a}")
PY
own $I
''',
        "exercises": [
            {"id": "A1.1", "points": 3, "title": "Les clés des serveurs",
             "ticket": {"from": "lea", "body": "Bienvenue ! Première chose : je ne veux plus de mots de passe qui traînent. Fais en sorte de pouvoir te connecter à <code>web1</code>, <code>web2</code> et <code>db1</code> (compte <code>admin</code>, mot de passe <code>cimes</code> pour la toute dernière fois) sans taper de mot de passe, et sans qu'aucune question ne soit posée : Ansible ne saura pas y répondre."},
             "desc": "Depuis le poste de contrôle, une connexion SSH non interactive vers <code>admin@web1</code>, <code>admin@web2</code> et <code>admin@db1</code> réussit : ni mot de passe, ni question sur l'empreinte.",
             "hints": ["Il faut deux choses : une paire de clés sur le poste de contrôle, et sa moitié publique dans le bon fichier de chaque serveur. Deux programmes d'OpenSSH font exactement cela. Et que demande SSH la toute première fois qu'il rencontre un serveur ?", "<code>ssh-keygen -t ed25519</code> (Entrée à chaque question), puis <code>ssh-copy-id admin@&lt;serveur&gt;</code> pour chacun, en répondant <code>yes</code> à la question de l'empreinte. Testez avec <code>ssh -o BatchMode=yes admin@&lt;serveur&gt; true</code>."],
             "checks": [
                 ('ls $H/.ssh/*.pub >/dev/null 2>&1', "Aucune clé publique dans ~/.ssh : il faut d'abord créer une paire de clés."),
                 ('for s in web1 web2 db1; do ssh_ok $s || { echo "MSG:Échec vers $s"; exit 1; }; done', "Connexion non interactive impossible vers un serveur : clé publique non installée, ou empreinte jamais acceptée."),
             ]},
            {"id": "A1.2", "points": 3, "title": "L'inventaire",
             "ticket": {"from": "sophie", "body": "Il nous faut enfin une liste officielle des serveurs. Crée l'inventaire <code>~/infra/inventaire.ini</code> : les serveurs web (web1, web2) dans un groupe <code>web</code>, la base (db1) dans un groupe <code>bdd</code>, et un groupe <code>production</code> qui réunit ces deux groupes. Le jour où on ajoute un serveur web, il doit être en production sans qu'on touche au groupe <code>production</code>."},
             "desc": "<code>~/infra/inventaire.ini</code> : groupe <code>web</code> = web1 et web2, groupe <code>bdd</code> = db1, et un groupe <code>production</code> dont les membres sont les <strong>groupes</strong> <code>web</code> et <code>bdd</code> (pas une liste de serveurs).",
             "hints": ["Un fichier INI : une section par groupe, un serveur par ligne. Un groupe peut aussi contenir d'autres groupes : cherchez dans le cours le suffixe de section qui le permet.", "<code>[production:children]</code> suivi des noms des groupes ; vérifiez avec <code>ansible-inventory -i inventaire.ini --graph</code>."],
             "checks": [
                 ('[ -f $I/inventaire.ini ]', "~/infra/inventaire.ini n'existe pas."),
                 ('[ "$(groupe web)" = "web1,web2" ]', "Le groupe web doit contenir exactement web1 et web2."),
                 ('[ "$(groupe bdd)" = db1 ]', "Le groupe bdd doit contenir exactement db1."),
                 ("etu 'ansible-inventory -i inventaire.ini --list' | jq -e '.production.children | sort == [\"bdd\",\"web\"]' >/dev/null", "Le groupe production doit avoir pour membres les groupes web et bdd (un groupe de groupes), pas une liste de serveurs."),
             ]},
            {"id": "A1.3", "points": 3, "title": "Premier contact", "manual": True,
             "ticket": {"from": "lea", "body": "Je ne veux pas taper <code>-i inventaire.ini -u admin</code> à chaque commande. Règle le projet <code>~/infra</code> pour qu'Ansible sache tout seul où sont les serveurs et avec quel compte s'y connecter, puis vérifie qu'il joint bien toute la production."},
             "desc": "Depuis <code>~/infra</code>, sans aucune option, Ansible utilise <code>inventaire.ini</code> et le compte distant <code>admin</code> (réglages du fichier <code>~/infra/ansible.cfg</code>), et <code>ansible production -m ping</code> répond <code>pong</code> pour les trois serveurs.",
             "hints": ["Ansible cherche ses réglages dans un fichier du dossier courant. Quel nom, quelle section, quelles clés ? Le cours donne un exemple pour une autre entreprise.", "Section <code>[defaults]</code>, clés <code>inventory</code> et <code>remote_user</code> ; <code>ansible-config dump --only-changed</code> montre les réglages pris en compte."],
             "checks": [
                 ('[ -f $I/ansible.cfg ]', "~/infra/ansible.cfg n'existe pas."),
                 ('etu "ansible-config dump --only-changed" | grep -E "^DEFAULT_HOST_LIST" | grep -q inventaire.ini', "ansible.cfg ne désigne pas l'inventaire inventaire.ini (section [defaults])."),
                 # Compte distant : remote_user dans ansible.cfg, ou ansible_user dans l'inventaire ([all:vars], group_vars…)
                 ('etu "ansible-config dump --only-changed" | grep -E "^DEFAULT_REMOTE_USER" | grep -q "= admin" || for s in web1 web2 db1; do [ "$(var $s ansible_user)" = admin ] || exit 1; done', "Le compte distant admin n'est pas réglé dans le projet : remote_user dans la section [defaults] d'ansible.cfg (ou ansible_user dans l'inventaire)."),
                 ('[ "$(etu "ansible production -m ping -o" | grep -c "SUCCESS.*pong")" = 3 ]', "ansible production -m ping ne répond pas « pong » pour les trois serveurs (lancé depuis ~/infra)."),
             ]},
            {"id": "A1.4", "points": 4, "title": "Viser juste", "manual": True,
             "ticket": {"from": "lea", "body": "Demain, on aura des dizaines de serveurs : il faudra savoir viser sans se tromper, et sans recopier des listes de noms. J'ai mis l'inventaire du futur datacenter dans <code>~/infra/exercices/parc.ini</code>, et quatre demandes dans <code>~/infra/exercices/demandes.txt</code>. Pour chacune, trouve le <strong>motif</strong> qui vise exactement les bons serveurs."},
             "desc": "<code>~/infra/reponses/motifs.txt</code> : une ligne par demande, dans l'ordre ; chaque ligne est un motif de groupes (aucun nom de serveur) qui, avec <code>-i exercices/parc.ini</code>, vise exactement les serveurs demandés.",
             "hints": ["Avant d'écrire une réponse, regardez ce qu'un motif sélectionne : une option d'<code>ansible</code> affiche les serveurs visés sans rien exécuter ni se connecter. Le cours présente l'union, l'intersection, l'exclusion et l'index.", "<code>ansible -i exercices/parc.ini '&lt;motif&gt;' --list-hosts</code> ; <code>groupe1:&amp;groupe2</code> (et), <code>groupe1:!groupe2</code> (sauf), <code>groupe1:groupe2</code> (ou), <code>groupe[0]</code> (le premier), <code>groupe[-1]</code> (le dernier), toujours entre guillemets simples."],
             "checks": [
                 ('[ -s $I/reponses/motifs.txt ]', "~/infra/reponses/motifs.txt n'existe pas ou est vide."),
                 (r'''for i in 1 2 3 4; do m=$(sed -n "${i}p" $I/reponses/motifs.txt | tr -d '\r' | sed "s/^ *//; s/ *\$//; s/^'\(.*\)'\$/\1/; s/^\"\(.*\)\"\$/\1/")
  case "$m" in *"'"*) echo "MSG:ligne $i : apostrophe dans le motif"; exit 1;; esac
  [ -n "$m" ] || { echo "MSG:ligne $i vide"; exit 1; }
  for h in $(grep -oE '^[a-z]{3}-[a-z]+[0-9]{2}' $I/exercices/parc.ini | sort -u); do
    case "$m" in *"$h"*) echo "MSG:ligne $i : $h est un nom de serveur, pas un groupe"; exit 1;; esac; done
  got=$(etu "ansible -i exercices/parc.ini '$m' --list-hosts" | sed 1d | tr -d ' ' | sort | paste -sd,)
  v=LAB_ATTENDU$i; [ "$got" = "${!v}" ] || { echo "MSG:ligne $i ($m) : vise ${got:-aucun serveur}"; exit 1; }
done''', "Un motif ne vise pas exactement les serveurs demandés (ou cite des noms de serveurs au lieu de groupes)."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Jour 2 — Sous le capot : modules et commandes ad hoc",
        "description": "Ce qu'Ansible exécute vraiment, les facts, les empreintes, et les premières actions sur les serveurs. Compétences : -vvv, modules et collections, setup, facts locaux, become, user, copy, find, file.",
        "lesson": """<h3>Une commande ad hoc</h3><pre>ansible &lt;cible&gt; -m &lt;module&gt; -a "&lt;arguments&gt;"<br>ansible front -m command -a "uptime"</pre><p>Un <strong>module</strong> est un petit programme Python qui sait faire une chose : installer un paquet (<code>apt</code>), gérer un compte (<code>user</code>), copier un fichier (<code>copy</code>), chercher des fichiers (<code>find</code>)…</p><h3>Modules, collections et FQCN</h3><p>Ce poste de contrôle dispose d'<strong>ansible-core</strong>, qui fournit environ 70 modules rangés dans la collection <code>ansible.builtin</code>. Des milliers d'autres existent, distribués en <strong>collections</strong> (<code>ansible.posix</code>, <code>community.general</code>…) qu'on installe avec <code>ansible-galaxy collection install</code> : impossible ici, faute d'accès à Internet. Dans ce parcours, tout se fait avec <code>ansible.builtin</code>.</p><pre>ansible-doc -l                       # les modules disponibles ICI<br>ansible-doc -l | grep -i user        # chercher un module<br>ansible-doc ansible.builtin.user     # sa documentation : paramètres et exemples (q pour quitter)</pre><p>Le nom complet <code>ansible.builtin.user</code> est le <strong>FQCN</strong> (<em>fully qualified collection name</em>) : dans un playbook, on l'écrit en entier pour éviter toute ambiguïté ; en ad hoc, <code>-m user</code> suffit.</p><h3>Que se passe-t-il vraiment ?</h3>""" + SCHEMA_MODULE + """<p>Pour le voir, ajoutez <code>-v</code>, <code>-vv</code> ou <code>-vvv</code> (de plus en plus bavard) : connexion SSH, dossier temporaire créé sur le serveur, fichier envoyé (ligne <code>PUT</code>), commande exécutée (ligne <code>EXEC</code>), JSON renvoyé. Attention : Ansible crée aussi un dossier temporaire sur le poste de contrôle (<code>ansible-local-…</code>) ; ne confondez pas les deux.</p><h3>État désiré et idempotence</h3>""" + SCHEMA_IDEMPOTENCE + """<pre>ansible front -b -m user -a "name=livreur"    # 1re fois : CHANGED (le compte est créé)<br>ansible front -b -m user -a "name=livreur"    # 2e fois  : SUCCESS (il existe déjà)</pre><h3>command ou shell ?</h3><ul><li><code>command</code> lance un programme <strong>sans shell</strong> : un tube <code>|</code>, une redirection <code>&gt;</code>, un joker <code>*</code> ou une <code>$VARIABLE</code> sont passés tels quels au programme, qui n'y comprend rien ;</li><li><code>shell</code> passe par <code>/bin/sh</code> : tubes et redirections fonctionnent ;</li><li>les deux exécutent la commande à l'aveugle : Ansible ne peut pas savoir si elle a modifié quelque chose, et répond toujours <code>changed</code>. Préférez un module dédié quand il existe ; sinon, <code>creates=&lt;fichier&gt;</code> (ne rien faire si ce fichier existe déjà) ou <code>changed_when</code> (jour 9) rendent la tâche honnête.</li></ul><h3>Devenir root : become</h3><p>Le compte distant n'est pas root. Pour administrer, Ansible passe par <code>sudo</code> : option <code>-b</code> (<em>become</em>) en ligne de commande, <code>become: true</code> dans un playbook. Sur ces serveurs, chaque commande lancée avec sudo est notée dans <code>/var/log/sudo.log</code> : celles d'Ansible y sont reconnaissables à la marque <code>BECOME-SUCCESS</code>.</p><h3>Les facts</h3><p>Avant de travailler, Ansible peut <strong>interroger</strong> chaque serveur : système, version, mémoire, adresses IP… Ce sont les <em>facts</em>, utilisables ensuite comme des variables.</p><pre>ansible memo1 -m setup                                  # tous les facts (long !)<br>ansible memo1 -m setup -a "filter=ansible_kernel*"<br>ansible all -m setup -a "filter=ansible_memtotal_mb"</pre><p>Un serveur peut aussi <strong>déclarer ses propres facts</strong> : chaque fichier <code>/etc/ansible/facts.d/&lt;nom&gt;.fact</code> (au format INI ou JSON) apparaît sous <code>ansible_local.&lt;nom&gt;</code>. Par exemple, un fichier <code>site.fact</code> contenant une section <code>[salle]</code> et une ligne <code>baie=B12</code> donne <code>ansible_local.site.salle.baie</code>.</p><h3>Quand un serveur change d'empreinte</h3><p>Un serveur réinstallé génère de nouvelles clés d'hôte. SSH refuse alors de s'y connecter (<em>REMOTE HOST IDENTIFICATION HAS CHANGED</em>) : c'est exactement ce qu'il verrait si quelqu'un se faisait passer pour lui. Avant de faire confiance à la nouvelle empreinte, comparez-la à une source sûre (l'hébergeur, la console du serveur) :</p><pre>ssh-keyscan -t ed25519 vitrine1 | ssh-keygen -lf -    # l'empreinte que présente le serveur<br>ssh-keygen -R vitrine1                                 # oublie l'ancienne empreinte</pre><div class="tip">Ne désactivez jamais la vérification des empreintes (<code>host_key_checking = False</code>, <code>StrictHostKeyChecking no</code>) pour « faire passer » une connexion : vous accepteriez n'importe quel serveur, y compris celui d'un attaquant.</div><h3>Quelques modules utiles</h3><pre>ansible front -b -m user -a "name=livreur uid=1500 groups=adm shell=/bin/sh"<br>ansible front -b -m copy -a "dest=/etc/issue.net content='Accès réservé\\n'"<br>ansible front -b -m apt -a "name=tree update_cache=yes"<br>ansible all -b -m find -a "paths=/var/log patterns='*.gz' recurse=yes"<br>ansible memo1 -b -m file -a "path=/tmp/vieux.log state=absent"<br>ansible all -m command -a "df -h /"</pre>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
emit DEBUT "$(date +%s)"
# A2.4 : un serveur (variante) réinstallé par l'hébergeur, sans que le poste de contrôle le sache. Réinstallé en
# premier : les données des autres exercices sont déposées sur le serveur neuf
v=${LAB_VARIANTE_A2_4:-$((RANDOM % 3))}
r=$(echo db1 web1 web2 | cut -d' ' -f$((v + 1)))
reinstalle $r
emit REINSTALLE "$r"
emit REINSTALLE_IP "10.10.0.${IP[$r]}"
# A2.1 : le module de Julien (variante), sur un serveur qui n'a pas été réinstallé
v=${LAB_VARIANTE_A2_1:-$((RANDOM % 4))}
mod=$(echo stat getent find file | cut -d' ' -f$((v + 1)))
hote=$(shuf -n1 -e $(echo web1 web2 db1 | tr ' ' '\n' | grep -vx $r))
case $mod in
  stat) a="path=/etc/hostname";; getent) a="database=passwd key=admin";;
  find) a="paths=/etc/ssh patterns=*.pub";; file) a="path=/tmp state=directory";;
esac
cat > $H/message-julien.txt <<EOF
De : Julien Petit
Objet : et avec mon module à moi ?

Léa dit qu'Ansible n'installe rien sur les serveurs. Moi, je lance souvent :

    ansible $hote -m $mod -a "$a"

Du coup, il envoie quoi, exactement, sur $hote ? Dans quel dossier du serveur ?
Et c'est quel programme, là-bas, qui l'exécute ?
EOF
emit MODULE "$mod"
# A2.2 : chaque serveur web déclare son numéro de série (fact local)
for s in web1 web2; do
  n="CS-$(tr -dc 'A-Z0-9' </dev/urandom | head -c 6)"
  sur $s "mkdir -p /etc/ansible/facts.d && printf '[contrat]\nnumero_serie=%s\nfournisseur=Hébergeur des Alpes\n' $n > /etc/ansible/facts.d/materiel.fact && chmod 644 /etc/ansible/facts.d/materiel.fact"
  emit "SERIE_${s^^}" "$n"
done
# A2.3 : l'UID du compte deploy
uid=$((2000 + RANDOM % 1000))
cat > $H/message-thomas.txt <<EOF
De : Thomas Leroy
Objet : compte deploy

Pour les mises en ligne, il me faut un compte « deploy » sur les serveurs web (pas sur la base) :
  - UID $uid, le même partout (les fichiers partagés en dépendent) ;
  - membre du groupe www-data ;
  - shell /bin/bash.

Et Sophie veut que /etc/motd des serveurs web contienne exactement cette ligne :
Serveur géré par Ansible - ne pas modifier à la main
EOF
emit UID "$uid"
# A2.4 : le message de Léa, avec l'empreinte officielle du serveur réinstallé
fp=$(sur $r "ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub" | awk '{print $2}')
cat > $H/message-lea.txt <<EOF
De : Léa Nguyen
Objet : $r réinstallé

L'hébergeur a réinstallé $r ce week-end (disque changé). Le compte admin a de nouveau le mot de passe cimes.
Empreinte officielle de la nouvelle clé ED25519 de $r, lue sur la console de l'hébergeur :
    $fp
EOF
# A2.5 : l'export oublié (dossier : variante), et des fichiers qui lui ressemblent
hex=$(tr -dc 'a-f0-9' </dev/urandom | head -c 6)
# (un export laissé par une préparation précédente de l'étape serait un second export)
for s in web1 web2 db1; do sur $s "find /srv /home /var/backups -name 'clients-*.csv' -delete 2>/dev/null; true"; done
srv=$(shuf -n1 -e web1 web2 db1)
case ${LAB_VARIANTE_A2_5:-$((RANDOM % 3))} in 0) dir=/srv/exports/$((2021 + RANDOM % 4));; 1) dir=/home/admin/archives/crm;; *) dir=/var/backups/crm;; esac
sur $srv "mkdir -p $dir && chmod 700 $dir && printf 'nom;prenom;email;telephone\nMartin;Claire;claire.martin@example.org;0600000000\n' > $dir/clients-$hex.csv && chmod 600 $dir/clients-$hex.csv"
emit CIBLE "$srv:$dir/clients-$hex.csv"
leurres=""
for l in "web1:/srv/exports/clients-modele.txt" "web2:/var/backups/crm/fournisseurs-$hex.csv" "db1:/home/admin/archives/clients.csv.gpg" "$(shuf -n1 -e web1 web2 db1):/srv/clients-$hex.csv.bak"; do
  s=${l%%:*}; f=${l#*:}; [ "$l" = "$srv:$dir/clients-$hex.csv" ] && continue
  sur $s "mkdir -p $(dirname $f) && echo 'ne pas supprimer' > $f"; leurres="$leurres $l"
done
emit LEURRES "${leurres# }"
for f in message-julien message-thomas message-lea; do own $H/$f.txt; chmod 600 $H/$f.txt; done
''',
        "exercises": [
            {"id": "A2.1", "points": 3, "title": "Sous le capot",
             "ticket": {"from": "julien", "body": "Léa dit qu'Ansible n'installe rien sur les serveurs. Mais alors, comment il fait pour exécuter du code dessus ?! Je t'ai mis ma commande préférée dans <code>~/message-julien.txt</code> : tu peux regarder ce qu'elle fait <strong>vraiment</strong> sur le serveur qu'elle vise ?"},
             "desc": "<code>~/infra/reponses/module.txt</code>, trois lignes, pour la commande de Julien : 1) le nom du fichier Python envoyé sur le serveur visé (sans le chemin) ; 2) le dossier du <strong>serveur</strong> où il est déposé ; 3) le chemin complet de l'interpréteur qui l'exécute sur le serveur.",
             "hints": ["Relancez la commande de Julien en mode très bavard, puis retrouvez dans la sortie les étapes du schéma du cours : l'envoi du fichier, puis son exécution. Attention, deux dossiers temporaires apparaissent : un sur le poste de contrôle, un sur le serveur.", "Avec <code>-vvv</code> : la ligne <code>PUT … TO &lt;dossier&gt;/AnsiballZ_….py</code> donne le fichier et son dossier sur le serveur (dans <code>/home/admin</code>) ; la ligne <code>EXEC … /bin/sh -c '&lt;interpréteur&gt; &lt;dossier&gt;/AnsiballZ_….py'</code> donne l'interpréteur."],
             "checks": [
                 ('[ "$(sed -n 1p $I/reponses/module.txt 2>/dev/null | tr -d "[:space:]")" = "AnsiballZ_$LAB_MODULE.py" ]', "Ligne 1 de reponses/module.txt : ce n'est pas le nom du fichier envoyé sur le serveur par la commande de Julien (lignes PUT de -vvv)."),
                 ('l=$(sed -n 2p $I/reponses/module.txt); echo "$l" | grep -q "\\.ansible/tmp" && ! echo "$l" | grep -qE "etudiant|ansible-local"', "Ligne 2 : ce n'est pas le dossier temporaire du serveur visé (celui du compte admin, pas celui du poste de contrôle)."),
                 ('sed -n 3p $I/reponses/module.txt | tr -d "[:space:]" | grep -qxE "/usr/bin/python3(\\.[0-9]+)?"', "Ligne 3 : ce n'est pas le chemin complet de l'interpréteur qui exécute le module sur le serveur (ligne EXEC de -vvv)."),
             ]},
            {"id": "A2.2", "points": 3, "title": "Inventaire matériel",
             "ticket": {"from": "diallo", "body": "Pour renouveler le contrat de support, l'hébergeur me demande, pour chaque serveur web, la version exacte de Debian et le numéro de série du contrat. Paraît-il que les serveurs le déclarent eux-mêmes ? Il me faut un fichier <code>~/infra/reponses/materiel.csv</code>, une ligne par serveur : <code>serveur;version;numéro</code>."},
             "desc": "<code>~/infra/reponses/materiel.csv</code> contient une ligne <code>web1;&lt;version de Debian&gt;;&lt;numéro de série&gt;</code> et la même pour web2, avec les valeurs que donnent les facts de chaque serveur.",
             "hints": ["Tout ce qu'Ansible sait d'un serveur se trouve dans ses facts, y compris ce que le serveur déclare lui-même. Ne les affichez pas tous : filtrez.", "<code>ansible web -m setup -a \"filter=ansible_distribution_version\"</code>, puis <code>filter=ansible_local</code> : les facts déclarés par le serveur (fichiers de <code>/etc/ansible/facts.d/</code>)."],
             "checks": [
                 ('[ -f $I/reponses/materiel.csv ]', "~/infra/reponses/materiel.csv n'existe pas."),
                 ('v=$(sur web1 "cat /etc/debian_version" | tr -d "[:space:]"); for s in web1 web2; do k=LAB_SERIE_${s^^}; tr -d " \\r" < $I/reponses/materiel.csv | grep -qxF "$s;$v;${!k}" || { echo "MSG:ligne de $s absente ou fausse"; exit 1; }; done', "Une ligne attendue manque ou est fausse (format serveur;version;numéro, valeurs des facts ansible_distribution_version et ansible_local)."),
             ]},
            {"id": "A2.3", "points": 4, "title": "Opération commando",
             "ticket": {"from": "thomas", "body": "Pour les mises en ligne, il me faut un compte <code>deploy</code> sur les serveurs web, avec des réglages précis : tout est dans <code>~/message-thomas.txt</code>. Et Sophie veut une ligne d'avertissement dans <code>/etc/motd</code>. Pas le temps d'écrire un playbook : fais-le avec des commandes Ansible ponctuelles, pas en te connectant aux serveurs."},
             "desc": "Sur web1 et web2 (pas sur db1) : compte <code>deploy</code> avec l'UID, le groupe secondaire et le shell demandés par Thomas ; <code>/etc/motd</code> contient exactement la ligne demandée. Le tout fait avec des commandes ad hoc d'Ansible, sans commande <code>sudo</code> tapée à la main sur les serveurs.",
             "hints": ["Un module gère les comptes (UID, groupes, shell…), un autre dépose un fichier dont on donne le contenu. Lisez leur documentation avec <code>ansible-doc</code> : quels paramètres correspondent aux demandes de Thomas ?", "<code>ansible web -b -m user -a \"name=deploy uid=… groups=… shell=…\"</code> et <code>ansible web -b -m copy -a \"dest=/etc/motd content='…\\n'\"</code>."],
             "checks": [
                 ('for s in web1 web2; do [ "$(sur $s "id -u deploy")" = "$LAB_UID" ] || { echo "MSG:$s : UID $(sur $s "id -u deploy" || echo absent)"; exit 1; }; done', "Le compte deploy n'existe pas sur web1 et web2, ou n'a pas l'UID demandé par Thomas."),
                 ('for s in web1 web2; do sur $s "id -nG deploy" | grep -qw www-data && [ "$(sur $s "getent passwd deploy" | cut -d: -f7)" = /bin/bash ] || exit 1; done', "Le compte deploy doit être membre du groupe www-data et avoir le shell /bin/bash."),
                 ('! sur db1 "id deploy"', "Le compte deploy ne doit pas exister sur db1 : ciblez seulement le groupe web."),
                 ('for s in web1 web2; do sur $s "cat /etc/motd" | grep -qxF "Serveur géré par Ansible - ne pas modifier à la main" || exit 1; done', "/etc/motd de web1 et web2 ne contient pas exactement la ligne « Serveur géré par Ansible - ne pas modifier à la main »."),
                 ('for s in web1 web2; do m=$(a_la_main $s $LAB_DEBUT); [ -z "$m" ] || { echo "MSG:$s : $(head -1 <<<"$m")"; exit 1; }; done', "Une commande a été tapée à la main avec sudo sur un serveur web (voir /var/log/sudo.log) : Thomas voulait des commandes Ansible. Refaites le travail avec Ansible (au besoin, « Réinitialiser les fichiers de cette étape »)."),
             ]},
            {"id": "A2.4", "points": 4, "title": "Le serveur réinstallé",
             "ticket": {"from": "lea", "body": "L'hébergeur a réinstallé un de nos serveurs ce week-end, et depuis SSH hurle au piratage (Ansible aussi : il ne le joint plus). Je t'ai mis son nom et l'empreinte officielle de sa nouvelle clé dans <code>~/message-lea.txt</code>. <strong>Vérifie-la avant de faire confiance</strong>, puis rétablis l'accès comme au premier jour. Et je ne veux voir nulle part la vérification des empreintes désactivée."},
             "desc": "La connexion non interactive vers le compte <code>admin</code> du serveur réinstallé fonctionne ; <code>~/.ssh/known_hosts</code> ne contient plus aucune ancienne empreinte de ce serveur ; ni Ansible ni SSH n'ont la vérification des empreintes désactivée.",
             "hints": ["Comparez l'empreinte que présente le serveur aujourd'hui à celle du message de Léa. Si elles concordent, il reste deux choses à défaire ou refaire : ce que votre poste sait de l'ancien serveur, et ce que le nouveau ne sait pas encore de vous.", "<code>ssh-keyscan -t ed25519 &lt;serveur&gt; | ssh-keygen -lf -</code> pour comparer ; <code>ssh-keygen -R &lt;serveur&gt;</code> retire les anciennes empreintes ; puis nouvelle connexion (ou <code>ssh-copy-id</code>) : le serveur est neuf, votre clé publique n'y est plus."],
             "checks": [
                 ('ssh_ok $LAB_REINSTALLE', "Pas de connexion SSH non interactive vers le serveur réinstallé (compte admin) : ancienne empreinte encore présente, ou clé publique à réinstaller sur le serveur neuf."),
                 ('cur=$(sur $LAB_REINSTALLE "cat /etc/ssh/ssh_host_*_key.pub" | awk "{print \\$2}"); k=$(etu "ssh-keygen -F $LAB_REINSTALLE; ssh-keygen -F $LAB_REINSTALLE_IP" | grep -v "^#" | awk "{print \\$3}"); [ -n "$k" ] && for x in $k; do grep -qxF "$x" <<<"$cur" || exit 1; done', "~/.ssh/known_hosts contient encore une ancienne empreinte du serveur réinstallé (ssh-keygen -R)."),
                 # host_key_checking = True (explicite) reste permis ; ssh_args -o StrictHostKeyChecking=no est refusé aussi
                 (r'''! etu "ansible-config dump --only-changed -t all" | grep -qiE "^HOST_KEY_CHECKING.*= *False|StrictHostKeyChecking *=? *(no|off)|UserKnownHostsFile *=? */dev/null" && ! grep -qsiE "StrictHostKeyChecking *=? *(no|off)|UserKnownHostsFile *=? */dev/null" $H/.ssh/config && ! grep -qsiE "ANSIBLE_HOST_KEY_CHECKING *= *[\"']?(false|no|off|0)" $H/.bashrc $H/.profile $H/.bash_profile''',"La vérification des empreintes est désactivée (ansible.cfg, ~/.ssh/config ou variable d'environnement) : retirez ce réglage."),
             ]},
            {"id": "A2.5", "points": 4, "title": "L'export oublié",
             "ticket": {"from": "sophie", "body": "L'audit RGPD est formel : un export de la base clients (un fichier <code>clients-&lt;code&gt;.csv</code>) traîne quelque part sous <code>/srv</code>, <code>/home</code> ou <code>/var/backups</code> sur un de nos trois serveurs. Trouve-le avec Ansible, note où il était dans <code>~/infra/reponses/rgpd.txt</code> (<code>serveur:chemin</code>), et supprime-le. <strong>Lui seul</strong> : il y a des fichiers qui lui ressemblent, on en a besoin."},
             "desc": "<code>reponses/rgpd.txt</code> contient <code>serveur:chemin complet</code> de l'export ; ce fichier n'existe plus ; tous les autres fichiers sont intacts ; aucune commande <code>sudo</code> tapée à la main sur les serveurs.",
             "hints": ["Un module sait chercher des fichiers selon un motif de nom, sur tous les serveurs à la fois (<code>ansible-doc -l | grep -i find</code>). Certains dossiers ne sont lisibles que par root. Un motif trop large ramènera les fichiers qui lui ressemblent.", "<code>ansible all -b -m find -a \"paths=/srv,/home,/var/backups patterns='clients-*.csv' recurse=yes\"</code> ; puis <code>-m file -a \"path=… state=absent\"</code> sur le seul serveur concerné."],
             "checks": [
                 ('[ "$(ans $I/reponses/rgpd.txt)" = "$LAB_CIBLE" ]', "reponses/rgpd.txt ne contient pas serveur:chemin de l'export (ex. web9:/srv/…/clients-xxxx.csv)."),
                 ('! sur "${LAB_CIBLE%%:*}" "test -e ${LAB_CIBLE#*:}"', "L'export des clients existe toujours sur le serveur : supprimez-le (module file, state=absent)."),
                 ('for l in $LAB_LEURRES; do sur ${l%%:*} "test -e ${l#*:}" || { echo "MSG:${l} a disparu"; exit 1; }; done', "Un fichier qui n'était pas l'export a été supprimé : votre motif était trop large."),
                 ('for s in web1 web2 db1; do [ -z "$(a_la_main $s $LAB_DEBUT)" ] || { echo "MSG:$s"; exit 1; }; done', "Une commande a été tapée à la main avec sudo sur un serveur : la recherche et la suppression doivent se faire avec Ansible."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    3: {
        "title": "Jour 3 — Premier playbook",
        "description": "Écrire, lancer, réparer et rejouer un playbook. Compétences : YAML, play, tâches, apt, service, copy, file, lineinfile, récapitulatif, lecture des erreurs, idempotence.",
        "lesson": """<h3>Des commandes ad hoc au playbook</h3><p>Les commandes ad hoc s'oublient. Un <strong>playbook</strong> est un fichier YAML qui décrit ce qu'on veut, se relit, se versionne et se rejoue à volonté.</p>""" + SCHEMA_PLAYBOOK + """<h3>YAML en 6 règles</h3><ul><li>L'<strong>indentation</strong> (des espaces, jamais de tabulation) définit la structure : c'est la source d'erreur n°1.</li><li><code>clé: valeur</code> (un espace après les deux-points) ;</li><li><code>- élément</code> : un élément de liste ;</li><li><code># commentaire</code> ;</li><li>entre guillemets si la valeur commence par <code>{{</code> ou contient <code>: </code> ;</li><li>un nombre n'est pas du texte : <code>mode: 644</code> est l'entier <em>décimal</em> 644, soit <code>1204</code> en octal, des droits absurdes. Les droits s'écrivent entre guillemets, avec le zéro : <code>mode: "0644"</code>.</li></ul><h3>Un premier playbook</h3><p>Exemple d'une autre entreprise, qui installe le répartiteur de charge haproxy sur son groupe <code>lb</code> :</p><pre>- name: Répartiteurs de charge<br>  hosts: lb<br>  become: true<br>  tasks:<br>    - name: Installer haproxy<br>      ansible.builtin.apt:<br>        name: haproxy<br>        state: present<br>        update_cache: true<br>        cache_valid_time: 3600<br><br>    - name: haproxy démarré, et lancé au démarrage du serveur<br>      ansible.builtin.service:<br>        name: haproxy<br>        state: started<br>        enabled: true</pre><p><code>update_cache</code> rafraîchit la liste des paquets (comme <code>apt update</code>) ; <code>cache_valid_time</code> évite de le refaire si elle date de moins d'une heure.</p><h3>Lancer, lire le récapitulatif</h3><pre>ansible-playbook lb.yml --syntax-check   # vérifie le YAML et la structure du playbook<br>ansible-playbook lb.yml<br>…<br>PLAY RECAP ********************************************<br>lb1  : ok=3  changed=1  unreachable=0  failed=0  skipped=0 …<br>lb2  : ok=3  changed=1  unreachable=0  failed=0  skipped=0 …</pre><ul><li><code>ok</code> : tâches réussies (y compris celles qui n'avaient rien à faire) ; <code>changed</code> : celles qui ont modifié le serveur ; <code>failed</code> et <code>unreachable</code> : les problèmes.</li><li><code>--syntax-check</code> ne vérifie ni les paramètres des modules, ni les variables, ni l'existence des serveurs : un playbook qui le passe peut encore échouer.</li><li>Si <code>hosts:</code> ne correspond à aucun serveur, Ansible affiche un simple avertissement (<em>Could not match supplied host pattern</em>, puis <em>skipping: no hosts matched</em>) et… « réussit » sans rien faire. Lisez toujours le récapitulatif.</li><li>Face à une erreur, lisez le <strong>premier</strong> message en entier : fichier, ligne, colonne, et souvent la cause probable. Corrigez une erreur à la fois.</li></ul><h3>Déposer un fichier</h3><pre>    - name: Consignes pour les robots d'indexation<br>      ansible.builtin.copy:<br>        src: fichiers/robots.txt        # chemin sur le poste de contrôle (relatif au playbook)<br>        dest: /var/www/html/robots.txt  # chemin sur le serveur<br>        mode: "0644"</pre><h3>Décrire un état, pas une action</h3><p>L'idempotence ne tombe pas du ciel : elle vient des modules, qui comparent l'état voulu à l'état réel. Une commande « à l'ancienne » dans <code>command</code> ou <code>shell</code> est rejouée à chaque passage : <code>echo … &gt;&gt; fichier</code> ajoute une ligne de plus à chaque fois.</p><pre>ansible.builtin.file:        path, state: directory, owner, group, mode   # au lieu de mkdir, chown, chmod<br>ansible.builtin.lineinfile:  path, line, create: true                     # au lieu de echo … &gt;&gt; fichier<br>ansible.builtin.apt:         name, state: present                         # au lieu de apt-get install<br>ansible.builtin.command:     cmd, creates: &lt;fichier&gt;                      # s'il n'existe aucun module : ne rien faire si le fichier existe</pre><p>Relancez le playbook : chaque tâche doit répondre <code>ok</code>, et le récapitulatif afficher <code>changed=0</code>. Un playbook idempotent peut être rejoué sans crainte, par exemple toutes les nuits pour corriger les dérives.</p><div class="tip">Un play ne s'applique qu'aux serveurs de <code>hosts:</code> : les autres ne sont pas concernés.</div>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
jeton="CS-$(tr -dc 'A-Z0-9' </dev/urandom | head -c 8)"
mkdir -p $I/fichiers $I/marc
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
emit JETON "$jeton"
# A3.3 : les tâches de Julien (non idempotentes). Une annonce laissée par une préparation précédente (autre date) est
# retirée : l'annonce doit rester unique
for s in web1 web2; do sur $s "rm -f /var/www/html/promo/annonce.txt"; done
jour=$(shuf -n1 -e "lundi 6 octobre" "mardi 14 octobre" "jeudi 23 octobre" "mercredi 5 novembre" "vendredi 14 novembre")
cat > $I/fichiers/julien-taches.yml <<EOF
# Tâches de Julien pour les promotions, à intégrer à web.yml (« ça marche chez moi ! »)

    - name: Dossier des promotions
      ansible.builtin.command: mkdir -p /var/www/html/promo

    - name: L'équipe web peut modifier les promotions
      ansible.builtin.command: chown -R www-data:www-data /var/www/html/promo

    - name: Annonce de la maintenance
      ansible.builtin.shell: echo "Maintenance prévue le $jour" >> /var/www/html/promo/annonce.txt

    - name: L'outil tree pour l'équipe
      ansible.builtin.shell: apt-get install -y tree
EOF
emit JOUR "$jour"
# A3.4 : le playbook de Marc, avec quatre défauts dont une cible qui ne correspond à rien. L'outil, les droits et
# le propriétaire du dossier de travail dépendent de la variante : le playbook réparé diffère d'un étudiant à l'autre
dossier="outils-$(tr -dc 'a-z' </dev/urandom | head -c 5)"
v=${LAB_VARIANTE_A3_4:-$((RANDOM % 4))}
python3 - "$I/marc/outils.yml" "$dossier" "$v" <<'PY'
import random, sys
chemin, dossier, v = sys.argv[1], sys.argv[2], int(sys.argv[3])
paquet, mode, rwx, proprio = [("unzip", "0750", "rwxr-x---", "admin"), ("rsync", "0770", "rwxrwx---", "admin"),
                              ("unzip", "0700", "rwx------", "www-data"), ("rsync", "0710", "rwx--x---", "www-data")][v]
d = {"hosts"} | set(random.sample(["tab", "state", "quotes", "become", "mode", "module"], 3))
t = f"""# Outils de Marc : {paquet} sur tous les serveurs de production, et un dossier de travail
# (droits {rwx}, propriétaire {proprio}).
# « Testé et approuvé ! »
- name: Outils de Marc
  hosts: {"tous" if "hosts" in d else "production"}
{"" if "become" in d else "  become: true" + chr(10)}  vars:
    paquet: {paquet}
    dossier: /opt/cimes/{dossier}
  tasks:
    - name: Installer l'outil
      ansible.builtin.apt:
        name: {"{{ paquet }}" if "quotes" in d else '"{{ paquet }}"'}
        state: {"installed" if "state" in d else "present"}
{chr(9) if "tab" in d else "        "}update_cache: true
        cache_valid_time: 3600

    - name: Dossier de travail
      ansible.builtin.{"fille" if "module" in d else "file"}:
        path: "{{{{ dossier }}}}"
        state: directory
        owner: {proprio}
        mode: {mode[1:] if "mode" in d else '"' + mode + '"'}
"""
open(chemin, "w").write(t)
print(f"@PAQUET={paquet}")
print(f"@DROITS={mode[1:]} {proprio}")
PY
emit DOSSIER "$dossier"
own $I
''',
        "exercises": [
            {"id": "A3.1", "points": 5, "title": "nginx partout",
             "ticket": {"from": "thomas", "body": "On lance la boutique sur les deux serveurs web ! Écris un playbook <code>~/infra/web.yml</code> qui fait en sorte que le serveur web <strong>nginx</strong> soit installé et en marche sur le groupe <code>web</code>, et qu'il redémarre avec le serveur. Pas sur la base de données, bien sûr."},
             "desc": "<code>~/infra/web.yml</code> contient un play qui vise le groupe <code>web</code> ; après son exécution, nginx est installé et tourne sur web1 et web2, et n'est pas installé sur db1.",
             "hints": ["Un playbook, c'est un play (une cible + une liste de tâches). Il faut un module pour les paquets, un autre pour les services. Installer un paquet demande les droits root. Le cours montre la même chose pour un autre logiciel.", "<code>ansible.builtin.apt</code> (le cache APT des serveurs neufs est vide : <code>update_cache: true</code>, sinon « No package matching ») et <code>ansible.builtin.service</code> (<code>state</code>, <code>enabled</code>), avec <code>become: true</code>."],
             "checks": [
                 ('[ -f $I/web.yml ]', "~/infra/web.yml n'existe pas."),
                 ("yjson $I/web.yml | jq -e 'any(.[]; .hosts == \"web\" or .hosts == [\"web\"])' >/dev/null", "web.yml doit contenir un play qui cible le groupe web (hosts: web). Le fichier est-il du YAML valide ?"),
                 ('for s in web1 web2; do sur $s "pgrep -x nginx" >/dev/null || exit 1; done', "nginx ne tourne pas sur web1 et web2 (lancez ansible-playbook web.yml)."),
                 ('! sur db1 "test -e /usr/sbin/nginx"', "nginx a été installé sur db1 : il ne doit l'être que sur les serveurs web."),
             ]},
            {"id": "A3.2", "points": 4, "title": "La page d'accueil",
             "ticket": {"from": "thomas", "body": "J'ai mis la page d'accueil dans <code>~/infra/fichiers/index.html</code>. Elle doit remplacer la page par défaut de nginx (<code>/var/www/html/index.html</code>) sur les serveurs web, et c'est <code>web.yml</code> qui doit la déployer : la prochaine fois que je la modifie, un simple <code>ansible-playbook web.yml</code> doit suffire."},
             "desc": "Une tâche de <code>web.yml</code> dépose <code>~/infra/fichiers/index.html</code> à la place de <code>/var/www/html/index.html</code> ; web1 et web2 servent cette page.",
             "hints": ["Quel module dépose un fichier du poste de contrôle sur les serveurs ? Et par rapport à quoi Ansible cherche-t-il un chemin source relatif ?", "<code>ansible.builtin.copy</code> avec <code>src: fichiers/index.html</code> (relatif au playbook), <code>dest:</code> et <code>mode: \"0644\"</code> ; vérifiez avec <code>curl http://web1</code>."],
             "checks": [
                 ("taches $I/web.yml | jq -s -e \"$M\"' any(.[]; (mod(\"copy\") or mod(\"template\")) and (tostring | test(\"index\\\\.html\")))' >/dev/null", "Aucune tâche de web.yml ne dépose la page d'accueil (module copy, src: fichiers/index.html, vers /var/www/html/index.html)."),
                 ('for s in web1 web2; do page $s | grep -qF "$LAB_JETON" || exit 1; done', "web1 et web2 ne servent pas la page de ~/infra/fichiers/index.html (rejouez le playbook)."),
             ]},
            {"id": "A3.3", "points": 5, "title": "Les tâches de Julien", "manual": True,
             "ticket": {"from": "lea", "body": "Julien a écrit des tâches pour les promotions, dans <code>~/infra/fichiers/julien-taches.yml</code>. Le résultat voulu est bon, mais pas la méthode : au deuxième passage tout est encore « changed », et l'annonce se répète dans le fichier à chaque exécution ! Intègre-les à <code>web.yml</code> en les réécrivant proprement. Je le rejouerai plusieurs fois : je veux le même résultat que Julien, <code>changed=0</code> dès le deuxième passage, et une seule ligne d'annonce."},
             "desc": "Après <code>web.yml</code> : sur web1 et web2, le dossier <code>/var/www/html/promo</code> appartient à www-data (utilisateur et groupe), <code>promo/annonce.txt</code> contient une seule fois la ligne d'annonce de Julien, <code>tree</code> est installé ; rejoué, le playbook ne change plus rien. Il n'y a plus de tâche <code>command</code> ou <code>shell</code> qui répond toujours « changed ».",
             "hints": ["Pour chaque tâche de Julien, demandez-vous quel <strong>état</strong> elle cherche à obtenir, et quel module sait décrire cet état (au lieu de répéter une action). Le cours en liste quatre.", "<code>file</code> (<code>state: directory</code>, <code>owner</code>, <code>group</code>), <code>lineinfile</code> (<code>path</code>, <code>line</code>, <code>create: true</code>), <code>apt</code> (<code>name: tree</code>)."],
             "checks": [
                 ('sur web1 "rm -rf /var/www/html/promo; dpkg -r tree >/dev/null 2>&1"; joue web.yml || recap', "Le playbook web.yml échoue (voir le récapitulatif)."),
                 ('for s in web1 web2; do [ "$(droits $s /var/www/html/promo | cut -d" " -f2-)" = "www-data www-data" ] || { echo "MSG:$s : $(droits $s /var/www/html/promo || echo absent)"; exit 1; }; done', "Le dossier /var/www/html/promo doit exister sur web1 et web2 et appartenir à www-data (utilisateur et groupe), comme le voulait Julien. (Le vérificateur l'a supprimé de web1 avant de rejouer web.yml.)"),
                 ('for s in web1 web2; do paquet $s tree || exit 1; done', "tree n'est pas installé sur web1 et web2 par le playbook (le vérificateur l'a retiré de web1 avant de rejouer web.yml)."),
                 ('joue web.yml && rien_change || recap', "Au deuxième passage, web.yml modifie encore quelque chose : une tâche n'est pas idempotente."),
                 ('for s in web1 web2; do [ "$(sur $s "grep -c . /var/www/html/promo/annonce.txt")" = 1 ] && sur $s "grep -qxF \\"Maintenance prévue le $LAB_JOUR\\" /var/www/html/promo/annonce.txt" || { echo "MSG:$s"; exit 1; }; done', "promo/annonce.txt doit contenir une seule ligne : l'annonce de Julien, à l'identique."),
                 ("taches $I/web.yml | jq -s -e \"$M\"' all(.[]; ((mod(\"command\") or mod(\"shell\")) | not) or (tostring | test(\"creates|removes|changed_when\")))' >/dev/null", "web.yml contient encore une tâche command ou shell qui répond toujours « changed » : remplacez-la par un module qui décrit l'état voulu."),
             ]},
            {"id": "A3.4", "points": 6, "title": "Le playbook de Marc", "manual": True,
             "ticket": {"from": "lea", "body": "Marc nous a laissé <code>~/infra/marc/outils.yml</code>, « testé et approuvé ». Son en-tête dit ce qu'il doit faire : installer un outil sur tous les serveurs de production, et y créer un dossier de travail avec des droits et un propriétaire précis. Il plante… et paraît-il qu'une fois corrigé, il ne fait rien du tout. Répare-le, sans changer ce qu'il est censé faire."},
             "desc": "<code>ansible-playbook marc/outils.yml</code> réussit sur web1, web2 et db1 : l'outil prévu par Marc est installé, et le dossier de travail existe avec les droits et le propriétaire annoncés dans l'en-tête du fichier ; rejoué, il ne change plus rien.",
             "hints": ["Une erreur à la fois : <code>--syntax-check</code>, puis un vrai lancement, et lisez le <strong>premier</strong> message en entier. Quand il « réussit », lisez le récapitulatif : combien de serveurs ont-ils été visés ? Et vérifiez les droits obtenus.", "Les suspects habituels : une tabulation, une valeur qui commence par <code>{{</code> sans guillemets, une valeur de <code>state</code> inconnue (<code>ansible-doc apt</code>), un nom de module, un groupe qui n'existe pas, <code>become</code>, et <code>mode</code> sans guillemets."],
             "checks": [
                 ('for s in web1 db1; do sur $s "rm -rf /opt/cimes"; done; joue marc/outils.yml || recap', "ansible-playbook marc/outils.yml échoue encore (voir le récapitulatif)."),
                 ('[ "$(grep -cE "^(web1|web2|db1) +: ok=" /tmp/lab-jeu.txt)" = 3 ]', "Le playbook de Marc ne s'applique pas à web1, web2 et db1 (lisez le récapitulatif : quels serveurs sont visés ?)."),
                 ('for s in web1 web2 db1; do paquet $s $LAB_PAQUET || { echo "MSG:$s"; exit 1; }; done', "L'outil prévu par Marc (en-tête du fichier) n'est pas installé sur tous les serveurs de production."),
                 ('for s in web1 web2 db1; do d=$(droits $s /opt/cimes/$LAB_DOSSIER | cut -d" " -f1,2); [ "$d" = "$LAB_DROITS" ] || { echo "MSG:$s : ${d:-absent}"; exit 1; }; done', "Le dossier de travail de Marc doit exister sur les trois serveurs, avec les droits et le propriétaire annoncés dans l'en-tête du fichier (le vérificateur l'a supprimé de web1 et db1 avant de rejouer le playbook)."),
                 ('joue marc/outils.yml && rien_change || recap', "Rejoué, le playbook de Marc modifie encore quelque chose."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    4: {
        "title": "Jour 4 — Variables, facts et modèles",
        "description": "Un même playbook, un résultat adapté à chaque serveur. Compétences : group_vars, host_vars, précédence des variables, Jinja2, template, facts, variables magiques (groups, hostvars).",
        "lesson": """<h3>Des variables</h3><p>Plutôt que d'écrire les valeurs en dur, on les range dans des fichiers qu'Ansible charge automatiquement, <strong>à côté de l'inventaire ou du playbook</strong>. Exemple d'une autre entreprise :</p><pre>~/projet/<br>├── serveurs.ini<br>├── group_vars/<br>│   ├── all.yml         # tous les serveurs<br>│   └── front.yml       # les serveurs du groupe front<br>└── host_vars/<br>    └── vitrine2.yml    # uniquement vitrine2</pre><pre># group_vars/front.yml<br>saison: hiver<br>couleur: bleu</pre><p>Le fichier peut s'appeler <code>front.yml</code>, <code>front.yaml</code>, <code>front.json</code>, ou être un <strong>dossier</strong> <code>front/</code> dont tous les fichiers sont chargés.</p><h3>Qui l'emporte ?</h3><p>Une même variable peut être définie à plusieurs endroits. Du plus faible au plus fort :</p><ol><li><code>defaults/</code> d'un rôle (jour 7) ;</li><li>variables de groupe écrites <strong>dans l'inventaire</strong> (section <code>[front:vars]</code>) ;</li><li><code>group_vars/all</code> ;</li><li><code>group_vars/&lt;groupe&gt;</code> : un groupe enfant l'emporte sur son groupe parent ;</li><li>variables d'hôte écrites dans l'inventaire (<code>vitrine1 saison=été</code>) ;</li><li><code>host_vars/&lt;serveur&gt;</code> ;</li><li>facts du serveur ;</li><li><code>vars:</code> du play ;</li><li><code>vars/</code> d'un rôle (jour 7, piège classique) ;</li><li><code>set_fact</code> et <code>register</code> (jour 9) ;</li><li><code>-e</code> en ligne de commande : l'emporte toujours.</li></ol><figure class="schema"><svg viewBox="0 0 640 300" role="img" aria-label="Échelle de précédence des variables, du plus faible au plus fort"><defs><marker id="a4a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="pa" d="M0,0 L10,5 L0,10 z"/></marker><marker id="a4g" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="pt" d="M0,0 L10,5 L0,10 z"/></marker><marker id="a4w" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="pw" d="M0,0 L10,5 L0,10 z"/></marker></defs>
<text class="t2" x="10" y="20">du plus faible (en haut) au plus fort (en bas) : la définition la plus forte l'emporte</text>
<rect class="a" x="10" y="30" width="290" height="19" rx="4"/><text class="t2" x="18" y="44">1</text><text x="40" y="44">defaults/ d'un rôle</text>
<rect class="b" x="10" y="52" width="320" height="19" rx="4"/><text class="t2" x="18" y="66">2</text><text x="40" y="66">[front:vars] dans l'inventaire</text>
<rect class="b" x="10" y="74" width="350" height="19" rx="4"/><text class="t2" x="18" y="88">3</text><text x="40" y="88">group_vars/all</text>
<rect class="b" x="10" y="96" width="380" height="19" rx="4"/><text class="t2" x="18" y="110">4</text><text x="40" y="110">group_vars/&lt;groupe&gt; (enfant &gt; parent)</text>
<rect class="b" x="10" y="118" width="410" height="19" rx="4"/><text class="t2" x="18" y="132">5</text><text x="40" y="132">variable d'hôte dans l'inventaire</text>
<rect class="b" x="10" y="140" width="440" height="19" rx="4"/><text class="t2" x="18" y="154">6</text><text x="40" y="154">host_vars/&lt;serveur&gt;</text>
<rect class="b" x="10" y="162" width="470" height="19" rx="4"/><text class="t2" x="18" y="176">7</text><text x="40" y="176">facts du serveur</text>
<rect class="b" x="10" y="184" width="500" height="19" rx="4"/><text class="t2" x="18" y="198">8</text><text x="40" y="198">vars: du play</text>
<rect class="a" x="10" y="206" width="530" height="19" rx="4"/><text class="t2" x="18" y="220">9</text><text x="40" y="220">vars/ d'un rôle</text>
<rect class="b" x="10" y="228" width="560" height="19" rx="4"/><text class="t2" x="18" y="242">10</text><text x="40" y="242">set_fact, register</text>
<rect class="g" x="10" y="250" width="590" height="19" rx="4"/><text class="t2" x="18" y="264">11</text><text x="40" y="264">-e en ligne de commande</text>
<path class="la" d="M626,32 L626,266" marker-end="url(#a4a)"/>
<rect class="a" x="10" y="280" width="14" height="12" rx="2"/><text class="t2" x="30" y="290">les deux dossiers de variables d'un rôle, aux deux extrémités</text>
<rect class="g" x="440" y="280" width="14" height="12" rx="2"/><text class="t2" x="460" y="290">gagne toujours</text>
</svg><figcaption>Plus la barre est longue, plus la définition est forte. Les variables de l'inventaire (2 à 6) cèdent devant celles du play ; les defaults d'un rôle cèdent devant tout.</figcaption></figure><div class="tip">Contre-intuitif : <code>group_vars/all.yml</code> l'emporte sur une section <code>[front:vars]</code> de l'inventaire, alors que <code>front</code> est plus précis que <code>all</code>. Et une variable d'hôte écrite dans l'inventaire l'emporte sur <code>group_vars/front.yml</code>.</div><pre>ansible-inventory --host vitrine2                  # valeur finale de chaque variable pour vitrine2 (pas son origine)<br>ansible vitrine2 -m debug -a "var=saison"          # la valeur vue pendant un jeu</pre><h3>Des modèles Jinja2</h3><p>Le module <code>template</code> fonctionne comme <code>copy</code>, mais remplace d'abord les expressions <code>{{ … }}</code> par leur valeur, <strong>pour chaque serveur</strong>.</p>""" + SCHEMA_VARIABLES + """<pre>&lt;!-- templates/accueil.html.j2 --&gt;<br>&lt;h1&gt;{{ enseigne }}&lt;/h1&gt;<br>&lt;p&gt;Collection {{ saison }} ({{ saison | upper }})&lt;/p&gt;<br>{# un commentaire Jinja : il n'apparaît pas dans le fichier produit #}</pre><pre>    - name: Page d'accueil<br>      ansible.builtin.template:<br>        src: templates/accueil.html.j2<br>        dest: /srv/vitrine/accueil.html</pre><h3>Des informations venues du serveur : les facts</h3><p>Les facts sont des variables comme les autres. Deux écritures équivalentes :</p><pre>{{ ansible_facts['memtotal_mb'] }}        # forme recommandée<br>{{ ansible_memtotal_mb }}                 # forme historique (« fact injecté »), vouée à disparaître<br>{{ ansible_facts['distribution'] }} {{ ansible_facts['distribution_version'] }}</pre><h3>Les variables magiques</h3><p>Ansible fournit des variables qui décrivent l'inventaire, utiles pour qu'un serveur « connaisse » les autres :</p><ul><li><code>inventory_hostname</code> : le nom du serveur dans l'inventaire ;</li><li><code>group_names</code> : les groupes du serveur ;</li><li><code>groups['front']</code> : la liste des serveurs d'un groupe (<code>groups['all']</code> : tous) ;</li><li><code>hostvars['vitrine2']</code> : toutes les variables d'un <strong>autre</strong> serveur, par exemple <code>hostvars['vitrine2']['saison']</code>.</li></ul><pre>&lt;p&gt;Vitrines : {{ groups['front'] | join(', ') }}&lt;/p&gt;<br>{% for v in groups['front'] %}<br>&lt;li&gt;{{ v }} : {{ hostvars[v]['saison'] }}&lt;/li&gt;<br>{% endfor %}</pre><div class="tip">Dans <code>hostvars</code>, les variables d'inventaire (<code>group_vars</code>, <code>host_vars</code>…) de tous les serveurs sont toujours disponibles. Les <strong>facts</strong> d'un autre serveur, en revanche, n'y sont que s'il a été contacté pendant ce jeu (ou gardé en cache, jour 10).</div><div class="tip">Dans un fichier YAML, une valeur qui commence par <code>{{</code> doit être entre guillemets : <code>name: "{{ paquet }}"</code>. Une variable absente fait échouer le modèle ; <code>{{ promo | default('') }}</code> ou <code>{% if promo is defined %}</code> évitent l'erreur.</div>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
slogan=$(shuf -n1 -e "Plus haut, plus loin, plus léger" "La montagne commence à votre porte" "Du sentier au sommet, on vous équipe" "Randonnez léger, revenez chargé de souvenirs" "Chaque sommet mérite le bon équipement")
printf 'De : Thomas Leroy\nObjet : slogan de la saison\n\nLe slogan à afficher sur la page de tous les serveurs web :\n%s\n' "$slogan" > $H/demandes/slogan.txt
emit SLOGAN "$slogan"
# A4.4 : la même variable définie « un peu partout » par Julien. Les réponses sont mesurées avec Ansible,
# dans une copie où chaque source a une valeur différente.
P=$I/exercices/precedence
rm -rf $P && mkdir -p $P/group_vars $P/host_vars
python3 - "$P" <<'PY'
import json, os, random, shutil, subprocess, sys, tempfile
P = sys.argv[1]
FICHIER = {"inv_groupe": "inventaire.ini", "inv_hote": "inventaire.ini", "all": "group_vars/all.yml",
           "production": "group_vars/production.yml", "web": "group_vars/web.yml", "hv_web2": "host_vars/web2.yml"}
def ecrire(d, pres, val):
    inv = "[web]\nweb1" + (f' titre_site="{val("inv_hote")}"' if "inv_hote" in pres else "") + "\nweb2\n\n[bdd]\ndb1\n\n[production:children]\nweb\nbdd\n"
    if "inv_groupe" in pres:
        inv += f'\n[web:vars]\ntitre_site="{val("inv_groupe")}"\n'
    open(os.path.join(d, "inventaire.ini"), "w").write(inv)
    for s in ("all", "production", "web", "hv_web2"):
        if s in pres:
            f = os.path.join(d, FICHIER[s]); os.makedirs(os.path.dirname(f), exist_ok=True)
            open(f, "w").write(f'titre_site: "{val(s)}"\n')
while True:
    pres = set(random.sample(list(FICHIER), random.randint(3, 5)))
    if not pres & {"all", "production"}:
        continue
    t = tempfile.mkdtemp()
    ecrire(t, pres, lambda s: "valeur-" + s)
    rep = {}
    for h in ("web1", "web2", "db1"):
        r = subprocess.run(["ansible-inventory", "-i", "inventaire.ini", "--host", h], cwd=t, capture_output=True, text=True)
        rep[h] = FICHIER[json.loads(r.stdout)["titre_site"][len("valeur-"):]]
    shutil.rmtree(t)
    if len(set(rep.values())) >= 2:
        break
ecrire(P, pres, lambda s: "Boutique Cimes et Sentiers")
for h, f in rep.items():
    print(f"@SRC_{h.upper()}={f}")
PY
own $I
''',
        "exercises": [
            {"id": "A4.1", "points": 5, "title": "Une page par serveur",
             "ticket": {"from": "thomas", "body": "Quand un client signale un bug, on ne sait jamais quel serveur lui a répondu. Remplace la page fixe par un <strong>modèle</strong> <code>templates/index.html.j2</code> qui affiche le nom du serveur, son environnement et le slogan de la saison (dans <code>~/demandes/slogan.txt</code>). L'environnement vient d'une variable <code>environnement</code>, qui vaut <code>production</code> pour les serveurs web, et le slogan d'une variable <code>slogan</code>, valable elle aussi pour les serveurs web seulement."},
             "desc": "Les variables <code>environnement</code> (<code>production</code>) et <code>slogan</code> (celui du message) sont définies pour le groupe <code>web</code> et pour lui seul ; <code>web.yml</code> génère la page de chaque serveur web depuis <code>~/infra/templates/index.html.j2</code>, qui affiche le nom du serveur, son environnement et le slogan, sans rien écrire en dur.",
             "hints": ["Deux choses distinctes : des valeurs rangées dans un fichier qu'Ansible charge automatiquement pour les membres d'un groupe, et un modèle qui les affiche. Dans le modèle, quelle variable magique donne le nom du serveur ?", "<code>group_vars/web.yml</code> ; dans <code>templates/index.html.j2</code> : <code>{{ inventory_hostname }}</code>, <code>{{ environnement }}</code>, <code>{{ slogan }}</code> ; dans web.yml, le module <code>template</code> remplace <code>copy</code>."],
             "checks": [
                 ('[ -f $I/templates/index.html.j2 ]', "~/infra/templates/index.html.j2 n'existe pas."),
                 (r'''etu "ansible-inventory --host web1" > /tmp/lab-web1.json; etu "ansible-inventory --host db1" > /tmp/lab-db1.json; [ "$(jq -r '.environnement // empty' /tmp/lab-web1.json)" = production ]''', "La variable environnement ne vaut pas production pour les serveurs web (group_vars)."),
                 (r'''[ "$(jq -r '.slogan // empty' /tmp/lab-web1.json)" = "$LAB_SLOGAN" ]''', "La variable slogan des serveurs web ne contient pas le slogan de ~/demandes/slogan.txt."),
                 (r'''[ -z "$(jq -r '(.environnement // empty), (.slogan // empty)' /tmp/lab-db1.json)" ]''', "environnement et slogan sont aussi définies pour db1 : elles doivent l'être pour le groupe web seulement (pas dans group_vars/all)."),
                 ('! sans_commentaires $I/templates/index.html.j2 | grep -qF "$LAB_SLOGAN"', "Le slogan est écrit en dur dans le modèle : il doit venir de la variable slogan."),
                 ("taches $I/web.yml | jq -s -e \"$M\"' any(.[]; mod(\"template\") and (tostring | test(\"index.html.j2\")))' >/dev/null", "web.yml ne génère pas la page avec le module template et le modèle templates/index.html.j2."),
                 ('t=$(texte web1); grep -q web1 <<<"$t" && grep -q production <<<"$t" && grep -qF "$LAB_SLOGAN" <<<"$t" && texte web2 | grep -q web2', "Les pages ne sont pas à jour : celle de web1 doit afficher web1, production et le slogan, celle de web2 afficher web2 (rejouez web.yml)."),
             ]},
            {"id": "A4.2", "points": 4, "title": "web2 passe en recette",
             "ticket": {"from": "sophie", "body": "Changement de programme : <code>web2</code> devient le serveur de <strong>recette</strong>, pour tester les nouveautés avant la production. Seul web2 change, et je ne veux pas qu'on touche au modèle, au playbook, ni à ce qui est défini pour le groupe web."},
             "desc": "<code>environnement</code> vaut <code>recette</code> pour web2 et <code>production</code> pour web1, sans modifier le modèle, <code>web.yml</code> ni les variables du groupe web ; les pages l'affichent.",
             "hints": ["La valeur ne change que pour un serveur. Quel dossier contient des variables propres à un serveur, et qui l'emporte entre une variable de groupe et une variable d'hôte ?", "Un fichier <code>host_vars/web2.yml</code> ; <code>ansible-inventory --host web2</code> pour vérifier, puis rejouez le playbook."],
             "checks": [
                 # host_vars/web2.yml, host_vars/web2/…, ou variable d'hôte dans l'inventaire : seul le résultat compte
                 ('[ "$(var web2 environnement)" = recette ]', "environnement ne vaut pas recette pour web2 : pas de variable propre à web2 (host_vars/web2.yml)."),
                 ('[ "$(var web2 environnement)" = recette ] && [ "$(var web1 environnement)" = production ]', "environnement doit valoir recette pour web2 et production pour web1."),
                 ('texte web2 | grep -q recette && texte web1 | grep -q production', "Les pages n'affichent pas le bon environnement (rejouez le playbook)."),
             ]},
            {"id": "A4.3", "points": 5, "title": "Qui est où ?",
             "ticket": {"from": "julien", "body": "Deux idées pour la page ! Afficher l'adresse IP du serveur, et en dessous l'état de toute la ferme web, du genre <code>Ferme : web1 (production), web2 (recette)</code>. Mais rien d'écrit à la main dans le modèle, hein : le jour où on change de réseau ou qu'on ajoute un serveur, tout doit suivre tout seul."},
             "desc": "La page de chaque serveur web affiche son adresse IP (web1 : 10.10.0.11, web2 : 10.10.0.12) et la phrase <code>Ferme : web1 (production), web2 (recette)</code> (serveurs du groupe web, dans l'ordre de l'inventaire, avec leur environnement). Le modèle ne contient ni adresse IP, ni nom de serveur, ni nom d'environnement.",
             "hints": ["Deux sources : les facts du serveur lui-même pour l'adresse, et les variables magiques qui décrivent tout l'inventaire (la liste des membres d'un groupe, les variables des autres serveurs).", "<code>{{ ansible_facts['default_ipv4']['address'] }}</code> ; <code>{% for h in groups['web'] %}{{ h }} ({{ hostvars[h]['environnement'] }}){% if not loop.last %}, {% endif %}{% endfor %}</code>."],
             "checks": [
                 ('! sans_commentaires $I/templates/index.html.j2 | grep -qE "10\\.10\\.0\\.|web[0-9]|\\((production|recette)\\)"', "Le modèle contient une adresse IP, un nom de serveur ou un environnement écrit en dur : tout doit venir des facts et des variables."),
                 ('texte web1 | grep -qF 10.10.0.11 && texte web2 | grep -qF 10.10.0.12', "Les pages n'affichent pas l'adresse IP de leur serveur (fact default_ipv4)."),
                 ('for s in web1 web2; do texte $s | grep -qF "Ferme : web1 (production), web2 (recette)" || { echo "MSG:$s"; exit 1; }; done', "Les pages n'affichent pas exactement « Ferme : web1 (production), web2 (recette) »."),
             ]},
            {"id": "A4.4", "points": 5, "title": "Qui a raison ?",
             "ticket": {"from": "lea", "body": "Julien a défini la variable <code>titre_site</code> un peu partout « pour être sûr », avec la même valeur, dans une copie de test : <code>~/infra/exercices/precedence/</code>. Le jour où quelqu'un voudra changer le titre de web1, web2 ou db1, il devra modifier le <strong>bon</strong> fichier, celui dont la valeur l'emporte. Dis-moi lequel, pour chacun des trois serveurs."},
             "desc": "<code>~/infra/reponses/precedence.txt</code> : trois lignes <code>web1=&lt;fichier&gt;</code>, <code>web2=&lt;fichier&gt;</code>, <code>db1=&lt;fichier&gt;</code>, où le fichier (chemin relatif au dossier <code>precedence</code>, ex. <code>group_vars/all.yml</code> ou <code>inventaire.ini</code>) est celui dont la valeur s'applique à ce serveur.",
             "hints": ["<code>ansible-inventory -i exercices/precedence/inventaire.ini --host web1</code> donne la valeur finale, pas son origine ; comme toutes les valeurs sont identiques, changez-en une à la fois (dans cette copie de test) et observez. Ou raisonnez avec le tableau du cours.", "Du plus faible au plus fort : <code>[groupe:vars]</code> de l'inventaire &lt; <code>group_vars/all</code> &lt; <code>group_vars/&lt;parent&gt;</code> &lt; <code>group_vars/&lt;enfant&gt;</code> &lt; variable d'hôte dans l'inventaire &lt; <code>host_vars</code>."],
             "checks": [
                 ('[ -f $I/reponses/precedence.txt ]', "~/infra/reponses/precedence.txt n'existe pas."),
                 (r'''for h in web1 web2 db1; do r=$(tr -d ' \r' < $I/reponses/precedence.txt | grep "^$h=" | head -1 | cut -d= -f2- | sed 's|.*precedence/||; s|^\./||')
  k=LAB_SRC_${h^^}; [ "$r" = "${!k}" ] || { echo "MSG:$h : ${r:-pas de réponse}"; exit 1; }; done''', "Au moins une réponse est fausse : ce n'est pas le fichier dont la valeur s'applique à ce serveur."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    5: {
        "title": "Jour 5 — Configurer un service : les handlers",
        "description": "Déployer une configuration, ne recharger le service que si nécessaire, et ne jamais laisser un service dans un état incohérent. Compétences : template de configuration, notify, handlers, flush_handlers, force_handlers, validate, uri, -e.",
        "lesson": """<h3>Le problème</h3><p>On déploie la configuration d'un service avec <code>template</code>. Mais le service ne relit sa configuration que si on le <strong>recharge</strong>. Recharger à chaque exécution ? Inutile, et cela coupe parfois des connexions. Il faut recharger <strong>seulement si la configuration a changé</strong>.</p><h3>Les handlers</h3>""" + SCHEMA_HANDLERS + """<pre>  tasks:<br>    - name: Configuration de haproxy<br>      ansible.builtin.template:<br>        src: templates/haproxy.cfg.j2<br>        dest: /etc/haproxy/haproxy.cfg<br>      notify: Recharger haproxy        # prévient le handler… si la tâche est « changed »<br><br>  handlers:<br>    - name: Recharger haproxy          # même nom que dans notify<br>      ansible.builtin.service:<br>        name: haproxy<br>        state: reloaded</pre><ul><li>Un handler n'est exécuté que s'il a été notifié par une tâche <code>changed</code>, et <strong>une seule fois</strong> même si plusieurs tâches l'ont notifié.</li><li>Il s'exécute à la fin de chaque <strong>section</strong> du play (<code>pre_tasks</code>, puis rôles et <code>tasks</code>, puis <code>post_tasks</code>), dans l'ordre où les handlers sont <em>déclarés</em> (pas dans l'ordre des notifications).</li><li><code>- ansible.builtin.meta: flush_handlers</code> exécute tout de suite les handlers en attente : indispensable quand une tâche suivante a besoin du service rechargé.</li><li>Plusieurs handlers peuvent réagir au même événement : chacun déclare <code>listen: "config modifiée"</code>, et les tâches notifient <code>"config modifiée"</code>.</li><li><code>reloaded</code> recharge la configuration sans couper le service ; <code>restarted</code> arrête puis relance.</li></ul><h3>Le piège du handler perdu</h3><p>Si une tâche <strong>échoue</strong> sur un serveur après avoir notifié un handler, le jeu s'arrête pour ce serveur… et le handler n'est pas exécuté. La configuration est modifiée sur le disque, mais le service tourne toujours avec l'ancienne. Au passage suivant, la tâche de configuration répond <code>ok</code> (le fichier est déjà à jour) : le handler n'est plus jamais notifié, et le récapitulatif affiche <code>changed=0</code> pendant que le service dysfonctionne.</p><ul><li><code>force_handlers: true</code> au niveau du play (ou <code>force_handlers = True</code> dans la section <code>[defaults]</code> d'<code>ansible.cfg</code>) exécute les handlers notifiés même si le serveur échoue ensuite ;</li><li>pour réparer un serveur déjà dans ce cas : une commande ad hoc qui recharge le service.</li></ul><h3>Tester une configuration avant de l'installer : validate</h3><p><code>template</code>, <code>copy</code> et <code>lineinfile</code> acceptent <code>validate</code> : une commande lancée sur le fichier <strong>candidat</strong> (désigné par <code>%s</code>) avant qu'il ne remplace le vrai. Si elle échoue, rien n'est remplacé et la tâche échoue.</p><pre>    - name: Droits sudo de l'équipe<br>      ansible.builtin.template:<br>        src: templates/equipe.sudoers.j2<br>        dest: /etc/sudoers.d/equipe<br>        validate: /usr/sbin/visudo -cf %s</pre><div class="tip">Pour nginx, <code>nginx -t -c %s</code> ne marche que sur une configuration <strong>complète</strong> : un fichier de site isolé ne l'est pas. On fait alors tester une petite configuration complète qui inclut le fichier candidat. À savoir : sur Debian, <code>service nginx reload</code> refuse de recharger une configuration invalide ; nginx continue de tourner… mais le fichier cassé reste sur le disque, et le prochain redémarrage sera fatal.</div><h3>Vérifier que le service répond : uri</h3><p>Un déploiement n'est fini que quand le service répond. Le module <code>uri</code> fait une requête HTTP et échoue si le code de retour n'est pas celui attendu (200 par défaut) :</p><pre>    - name: L'interface d'administration répond<br>      ansible.builtin.uri:<br>        url: "http://localhost:{{ port_admin }}/sante"<br>        return_content: true</pre><h3>Un exemple de configuration nginx</h3><pre># templates/vitrine.conf.j2<br>server {<br>    listen {{ port_vitrine }};<br>    root /srv/vitrine;<br>    index accueil.html;<br>}</pre><p>Sur Debian, le site servi par défaut est décrit par <code>/etc/nginx/sites-available/default</code> (activé par un lien dans <code>sites-enabled</code>) : le remplacer par votre modèle change le port d'écoute. <code>default_server</code> sur la ligne <code>listen</code> en fait le site par défaut de ce port.</p><h3>Surcharger une variable pour un essai</h3><pre>ansible-playbook vitrine.yml -e port_vitrine=8001   # -e l'emporte sur tout le reste</pre>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
''',
        "exercises": [
            {"id": "A5.1", "points": 6, "title": "Le port 8080",
             "ticket": {"from": "sophie", "body": "Le nouveau pare-feu de l'hébergeur n'ouvre que le port <strong>8080</strong> vers les serveurs web. Configure nginx pour qu'il serve la boutique sur ce port (et plus sur le port 80), avec un modèle de configuration qui remplace le site par défaut de Debian, <code>/etc/nginx/sites-available/default</code> : nos outils de contrôle lisent ce fichier. Le numéro de port doit être une variable <code>http_port</code> du groupe web, et nginx ne doit être rechargé que si sa configuration change."},
             "desc": "<code>http_port: 8080</code> pour le groupe web ; nginx de web1 et web2 sert la page sur le port 8080 et plus sur le port 80 ; dans <code>web.yml</code>, la tâche qui déploie la configuration de nginx notifie un handler qui recharge nginx.",
             "hints": ["Trois pièces : une variable pour le groupe web ; un modèle de configuration qui remplace le site par défaut de nginx sur Debian ; une réaction qui ne se déclenche que si ce fichier change.", "<code>templates/site.conf.j2</code> (<code>listen {{ http_port }} default_server;</code>, <code>root</code>, <code>index</code>) déployé sur <code>/etc/nginx/sites-available/default</code> avec <code>notify:</code> ; une section <code>handlers:</code> au même niveau que <code>tasks:</code>."],
             "checks": [
                 ('[ "$(var web1 http_port)" = 8080 ]', "La variable http_port ne vaut pas 8080 pour les serveurs web (group_vars)."),
                 ('page web1:8080 | grep -q web1 && page web2:8080 | grep -q web2', "Les serveurs web ne servent pas leur page sur le port 8080 (le handler a-t-il rechargé nginx ?)."),
                 ('! page web1:80 >/dev/null 2>&1', "nginx répond encore sur le port 80 de web1 : la configuration par défaut est-elle toujours active ?"),
                 ("taches $I/web.yml | jq -s -e \"$M\"' any(.[]; mod(\"template\") and (tostring | test(\"sites-available/default\")) and has(\"notify\"))' >/dev/null", "Dans web.yml, la tâche qui déploie /etc/nginx/sites-available/default doit notifier un handler (notify)."),
                 # Handler : module service (ou systemd), ou commande de rechargement (nginx -s reload, service nginx reload…)
                 ("taches $I/web.yml | jq -s -e \"$M\"' any(.[]; ((mod(\"service\") or mod(\"systemd\") or mod(\"systemd_service\")) and (tostring | test(\"nginx\")) and (tostring | test(\"reloaded|restarted\"))) or ((mod(\"command\") or mod(\"shell\")) and (tostring | test(\"nginx +-s +reload|(service|systemctl) +nginx +(reload|restart)|systemctl +(reload|restart) +nginx\"))))' >/dev/null", "web.yml n'a pas de handler qui recharge nginx (module service, state: reloaded)."),
             ]},
            {"id": "A5.2", "points": 5, "title": "Le test de fumée", "manual": True,
             "ticket": {"from": "lea", "body": "Un déploiement n'est fini que quand le site répond. Ajoute à la fin de <code>web.yml</code> une vérification : chaque serveur doit servir sa page sur son port, sinon le playbook échoue. Je la testerai avec un autre port (<code>-e http_port=8089</code>), avec un serveur qui ne sert plus sa page, puis normalement, deux fois : et là, rien ne doit changer ni être rechargé."},
             "desc": "<code>web.yml</code> se termine par une vérification HTTP (module <code>uri</code>) : avec <code>-e http_port=8089</code>, le jeu réussit et nginx sert sur 8089 ; si un serveur ne sert plus sa page, le jeu échoue ; relancé normalement, il revient sur 8080 ; rejoué, il ne change rien et ne recharge pas nginx.",
             "hints": ["Au moment où votre vérification s'exécute, le handler qui recharge nginx a-t-il déjà tourné ? Cherchez comment exécuter les handlers en attente au milieu d'un play.", "<code>- ansible.builtin.meta: flush_handlers</code>, puis <code>ansible.builtin.uri</code> avec <code>url: \"http://localhost:{{ http_port }}/\"</code> : un code autre que 200 fait échouer la tâche."],
             "checks": [
                 # uri, get_url, ou curl/wget : les essais qui suivent jugent son comportement
                 ("taches $I/web.yml | jq -s -e \"$M\"' any(.[]; mod(\"uri\") or mod(\"get_url\") or ((mod(\"command\") or mod(\"shell\")) and (tostring | test(\"curl|wget\"))))' >/dev/null", "web.yml ne contient pas de vérification HTTP (module uri)."),
                 ('joue web.yml -e http_port=8089 || recap', "Avec -e http_port=8089, le playbook échoue : au moment de la vérification, nginx a-t-il déjà été rechargé ?"),
                 ('page web1:8089 >/dev/null', "Avec http_port=8089, nginx n'écoute pas sur 8089 : le port vient-il de la variable, et le handler recharge-t-il nginx ?"),
                 ('sur web1 "chmod 000 /var/www/html"; joue web.yml; r=$?; sur web1 "chmod 755 /var/www/html"; [ $r != 0 ] && echec_attendu', "Le vérificateur a rendu la page de web1 illisible (erreur 403) : le playbook a pourtant réussi. La vérification doit échouer quand la page n'est pas servie."),
                 ('joue web.yml || recap', "Relancé normalement, le playbook web.yml échoue (voir le récapitulatif)."),
                 ('page web1:8080 >/dev/null', "Revenu à http_port=8080, nginx n'écoute plus sur 8080 : le handler a-t-il rechargé nginx ?"),
                 ('p=$(sur web1 "cat /run/nginx.pid"); joue web.yml && rien_change && [ "$(sur web1 "cat /run/nginx.pid")" = "$p" ] || recap', "Sans aucune modification, le playbook change encore quelque chose (ou relance nginx) : le rechargement ne doit avoir lieu que si la configuration change."),
             ]},
            {"id": "A5.3", "points": 5, "title": "Plus jamais de configuration cassée", "manual": True,
             "ticket": {"from": "lea", "body": "Hier, chez un confrère, un modèle nginx cassé est parti en production. nginx a tenu, parce que Debian refuse de recharger une configuration invalide… mais au redémarrage suivant, tout est tombé. Je veux qu'une configuration invalide ne puisse <strong>jamais</strong> atteindre le disque de nos serveurs. Je testerai avec un port absurde : <code>-e http_port=abc</code>."},
             "desc": "Lancé avec <code>-e http_port=abc</code>, <code>web.yml</code> échoue <strong>sans</strong> modifier <code>/etc/nginx/sites-available/default</code> ; nginx sert toujours la boutique sur 8080 ; relancé normalement, le playbook réussit.",
             "hints": ["Le module qui dépose le fichier sait le faire tester <strong>avant</strong> de le mettre en place : cherchez <code>validate</code> dans <code>ansible-doc template</code>. Quelle commande teste une configuration nginx ? Sur quoi fonctionne-t-elle ?", "<code>validate: &lt;commande&gt; %s</code>. <code>nginx -t -c</code> exige une configuration complète : déposez d'abord (avec Ansible) un petit script qui écrit une configuration minimale <code>events {} http { include &lt;fichier candidat&gt;; }</code> puis lance <code>nginx -t -c</code> dessus, et utilisez-le dans <code>validate</code>."],
             "checks": [
                 ('a=$(somme web1 /etc/nginx/sites-available/default); echo "$a" > /tmp/lab-conf; [ -n "$a" ] && ! joue web.yml -e http_port=abc', "Avec http_port=abc, le playbook réussit : une configuration invalide est acceptée."),
                 ('echec_attendu || recap', "Avec http_port=abc, le playbook ne démarre même pas (erreur de syntaxe ?) : voir le récapitulatif."),
                 ('[ "$(somme web1 /etc/nginx/sites-available/default)" = "$(cat /tmp/lab-conf)" ]', "Avec http_port=abc, la configuration invalide a été écrite sur le disque de web1 : elle doit être testée avant de remplacer l'ancienne."),
                 ('joue web.yml || recap', "Relancé normalement (8080), le playbook échoue : voir le récapitulatif."),
                 ('sur web1 "nginx -t" >/dev/null 2>&1 && page web1:8080 >/dev/null', "nginx de web1 n'a pas une configuration valide, ou ne sert plus la boutique sur 8080."),
             ]},
            {"id": "A5.4", "points": 5, "title": "Le handler perdu", "manual": True,
             "ticket": {"from": "sophie", "body": "Hier soir, un déploiement a planté sur un serveur juste après la mise à jour de la configuration de nginx. Ce matin, le site ne répondait plus sur ce serveur… et pourtant ton playbook affichait <code>ok</code> partout, <code>changed=0</code> ! Léa m'a expliqué : le handler n'a jamais été exécuté. Fais en sorte que ça ne puisse plus arriver : même si une tâche échoue après une modification de configuration, nginx doit être rechargé."},
             "desc": "Si une tâche échoue sur un serveur après une modification de la configuration de nginx, les handlers notifiés sont exécutés quand même. (Test : le vérificateur provoque l'échec du dépôt de la page sur web1 pendant un changement de port ; dans web.yml, la configuration est déployée avant la page, comme dans le cours.)",
             "hints": ["Quand une tâche échoue sur un serveur, que deviennent les handlers déjà notifiés pour ce serveur ? Et au passage suivant, la tâche de configuration est-elle encore « changed » ? Le cours cite un réglage qui change ce comportement.", "<code>force_handlers: true</code> au niveau du play (ou <code>force_handlers = True</code> dans la section <code>[defaults]</code> d'ansible.cfg)."],
             "checks": [
                 # force_handlers dans le play ou dans ansible.cfg, ou un rescue qui exécute les handlers (meta: flush_handlers)
                 ('yjson $I/web.yml | jq -e "any(.[]; .force_handlers == true)" >/dev/null || etu "ansible-config dump --only-changed" | grep -q "^DEFAULT_FORCE_HANDLERS.*True" || taches $I/web.yml | jq -s -e "any(.[]; (.rescue // []) + (.always // []) | tostring | test(\\"flush_handlers\\"))" >/dev/null', "Rien ne force l'exécution des handlers quand un serveur échoue (ni dans le play de web.yml, ni dans ansible.cfg)."),
                 ('sur web1 "mv /var/www/html /var/www/html.sauve && ln -s /nulle-part /var/www/html"; joue web.yml -e http_port=8094; sur web1 "rm -f /var/www/html; mv /var/www/html.sauve /var/www/html"; echec_attendu || recap', "Le vérificateur a rendu impossible le dépôt de la page sur web1 : le playbook aurait dû échouer sur web1 (voir le récapitulatif)."),
                 ('sur web1 "grep -q 8094 /etc/nginx/sites-available/default"', "Pendant ce test (port 8094, échec sur web1), la configuration de web1 n'a pas été modifiée : dans web.yml, la tâche de configuration doit précéder celle de la page."),
                 ('page web1:8094 >/dev/null', "La configuration de web1 est passée sur le port 8094, mais nginx n'a pas été rechargé après l'échec : le handler a été perdu."),
                 ('joue web.yml || recap', "Relancé normalement, le playbook web.yml échoue (voir le récapitulatif)."),
                 ('page web1:8080 >/dev/null && page web2:8080 >/dev/null', "Relancés normalement, web1 et web2 ne servent pas la boutique sur 8080."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    6: {
        "title": "Jour 6 — Boucles, conditions et filtres",
        "description": "Répéter une tâche, n'agir que là où il faut, transformer des données. Compétences : listes et dictionnaires, loop, item, when, | bool, filtres (selectattr, map, join…), {% for %} et {% if %}, debug.",
        "lesson": """<h3>1. Listes et dictionnaires en YAML</h3><pre># group_vars/front.yml (exemple d'une autre entreprise)<br>operateurs:                 # une liste<br>  - alice<br>  - bruno<br>limites:                    # un dictionnaire (clé → valeur)<br>  cpu: 2<br>  memoire: 512<br>comptes:                    # une liste de dictionnaires : une « fiche » par élément<br>  - nom: alice<br>    admin: true<br>  - nom: bruno<br>    admin: false</pre><h3>2. Répéter une tâche : loop</h3><pre>    - name: Comptes des opérateurs<br>      ansible.builtin.user:<br>        name: "{{ item }}"        # item : l'élément courant<br>        groups: adm<br>        append: true              # ajoute au groupe, sans retirer les autres<br>      loop: "{{ operateurs }}"</pre><ul><li>Sur une liste de fiches, <code>item</code> est un dictionnaire : <code>{{ item.nom }}</code>, <code>{{ item.admin }}</code>. <code>loop_control: {label: "{{ item.nom }}"}</code> rend la sortie lisible.</li><li><code>loop</code> n'accepte qu'une liste : pour parcourir un dictionnaire, <code>loop: "{{ limites | dict2items }}"</code> donne des paires <code>item.key</code> / <code>item.value</code>.</li><li>Vous rencontrerez aussi <code>with_items:</code>, l'ancienne écriture, encore très répandue.</li><li>Ajouter un opérateur, c'est ajouter une ligne dans la variable : le code ne change pas.</li></ul><h3>3. Agir sous condition : when</h3><pre>    - name: Sonde de supervision, hors des serveurs de test<br>      ansible.builtin.apt:<br>        name: htop<br>      when: saison == "hiver" and "front" in group_names</pre><ul><li>La condition est une expression Jinja2, <strong>sans</strong> <code>{{ }}</code>. Les textes s'écrivent entre guillemets : <code>saison == hiver</code> chercherait une <em>variable</em> <code>hiver</code>.</li><li>Opérateurs : <code>==</code>, <code>!=</code>, <code>&lt;</code>, <code>in</code>, <code>not</code>, <code>and</code>, <code>or</code>, <code>is defined</code>. Une liste de conditions sous <code>when:</code> équivaut à un <code>and</code>.</li><li>Sur les serveurs où elle est fausse, la tâche est <code>skipping</code>. Avec une boucle, <code>when</code> est évalué <strong>pour chaque élément</strong> : <code>when: item.admin</code>.</li><li>On peut tester des facts : <code>when: ansible_facts['memtotal_mb'] &lt; 1024</code>.</li></ul><div class="tip"><strong>Piège des booléens.</strong> <code>actif: false</code> est un booléen, mais <code>actif: "false"</code> est une <em>chaîne</em>, et une chaîne non vide est… vraie. Les valeurs passées par <code>-e actif=false</code> sont toujours des chaînes. Le filtre <code>| bool</code> convertit proprement : <code>when: actif | bool</code>. Pour voir le type réel : <code>{{ actif | type_debug }}</code>.</div><h3>4. Les filtres : transformer des données</h3><pre>{{ saison | upper }}                                     # HIVER<br>{{ ville | default('inconnue') }}                        # valeur par défaut si la variable n'existe pas<br>{{ operateurs | join(', ') }}                            # alice, bruno<br>{{ operateurs | sort | first }}  {{ operateurs | length }}<br>{{ comptes | map(attribute='nom') | list }}              # ['alice', 'bruno']<br>{{ comptes | selectattr('admin') | list }}               # les fiches dont admin est vrai<br>{{ comptes | rejectattr('admin') | map(attribute='nom') | list }}   # les noms des non-admins</pre><h3>5. Jinja2 dans un modèle</h3><pre>{% if saison == "hiver" %}<br>&lt;p class="bandeau"&gt;Collection hiver&lt;/p&gt;<br>{% elif saison == "été" %}<br>&lt;p&gt;Collection été&lt;/p&gt;<br>{% endif %}<br><br>&lt;ul&gt;<br>{% for c in comptes %}<br>  &lt;li&gt;{{ loop.index }}. {{ c.nom | capitalize }}{% if not loop.last %},{% endif %}&lt;/li&gt;<br>{% endfor %}<br>&lt;/ul&gt;</pre><div class="tip"><code>{{ … }}</code> affiche une valeur ; <code>{% … %}</code> est une instruction (condition, boucle, <code>{% set x = … %}</code>) qui n'affiche rien elle-même. <code>{%-</code> et <code>-%}</code> suppriment les espaces et retours à la ligne autour de l'instruction.</div><h3>6. Déboguer une expression</h3><pre>    - ansible.builtin.debug:<br>        var: comptes                                           # affiche une variable<br>    - ansible.builtin.debug:<br>        msg: "{{ comptes | selectattr('admin') | map(attribute='nom') | list }}"</pre><pre>ansible vitrine1 -m debug -a "msg={{ operateurs | length }}"   # en ad hoc, sans playbook</pre>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
# A6.1 : l'équipe web (3 ou 4 personnes)
equipe=$(shuf -n $((3 + RANDOM % 2)) -e thomas nadia julien ines yanis lina malik chloe hugo sarah noah emma | sort | xargs)
printf 'De : Nadia Haddad\nObjet : équipe web\n\nVoici l'"'"'équipe web actuelle (un identifiant par ligne) :\n\n' > $H/demandes/equipe.txt
for u in $equipe; do echo "$u" >> $H/demandes/equipe.txt; done
emit EQUIPE "$equipe"
# A6.3 : d'anciens membres, dont les comptes traînent encore sur les serveurs web
anciens=$(shuf -n $((2 + RANDOM % 2)) -e kevin laura damien oceane bastien manon | sort | xargs)
{ echo "nom;statut"; for u in $equipe; do echo "$u;actif"; done; for u in $anciens; do echo "$u;parti"; done; } > $H/demandes/equipe.csv
for s in web1 web2; do for u in $anciens; do sur $s "id $u >/dev/null 2>&1 || useradd -m -s /bin/bash -G www-data $u"; done; done
emit ANCIENS "$anciens"
# A6.4 : le playbook de maintenance de Julien, et ses variables « booléennes » entre guillemets. La variante fixe
# le nom de la variable, ses valeurs et l'écriture des conditions (même piège, réparation propre à chacun)
m=$(shuf -n1 -e web1 web2)
case ${LAB_VARIANTE_A6_4:-$((RANDOM % 4))} in
  0) var=maintenance; non=false; oui=true; si="maintenance"; sinon="not maintenance";;
  1) var=en_travaux; non=no; oui=yes; si="en_travaux"; sinon="not en_travaux";;
  2) var=mode_maintenance; non=false; oui=true; si="mode_maintenance == true"; sinon="mode_maintenance == false";;
  *) var=page_travaux; non=off; oui=on; si="page_travaux"; sinon="not page_travaux";;
esac
rm -rf $I/julien
mkdir -p $I/julien/group_vars $I/julien/host_vars
cat > $I/julien/maintenance.yml <<EOF
# Page de maintenance : affichée seulement là où « $var » est vrai (Julien)
- name: Page de maintenance
  hosts: web
  become: true
  tasks:
    - name: Page de maintenance là où elle est demandée
      ansible.builtin.copy:
        dest: /var/www/html/maintenance.html
        content: "<h1>Maintenance en cours</h1>\n"
        mode: "0644"
      when: $si

    - name: Pas de page de maintenance ailleurs
      ansible.builtin.file:
        path: /var/www/html/maintenance.html
        state: absent
      when: $sinon
EOF
printf '# Par défaut, pas de maintenance\n%s: "%s"\n' $var $non > $I/julien/group_vars/web.yml
printf '# Ce serveur passe en maintenance\n%s: "%s"\n' $var $oui > $I/julien/host_vars/$m.yml
emit MAINT "$m"
emit MAINTVAR "$var"
own $I $H/demandes
''',
        "exercises": [
            {"id": "A6.1", "points": 4, "title": "L'équipe web",
             "ticket": {"from": "nadia", "body": "Les membres de l'équipe web (liste dans <code>~/demandes/equipe.txt</code>) ont besoin d'un compte sur les serveurs web, dans le groupe <code>www-data</code> pour pouvoir toucher aux fichiers du site. La liste va bouger souvent : je veux une variable <code>equipe_web</code> et <strong>une seule tâche</strong> dans <code>web.yml</code>, pas un copier-coller par personne."},
             "desc": "Pour chaque personne de <code>~/demandes/equipe.txt</code>, un compte membre de <code>www-data</code> existe sur web1 et web2 (pas sur db1) ; il est créé par une seule tâche de <code>web.yml</code> qui boucle sur une variable.",
             "hints": ["Une liste, rangée là où les serveurs web la trouveront, et une tâche qui se répète pour chacun de ses éléments. Ajouter au groupe ne doit pas retirer des autres groupes.", "<code>equipe_web</code> dans <code>group_vars/web.yml</code> ; une tâche <code>ansible.builtin.user</code> avec <code>name: \"{{ item }}\"</code>, <code>groups: www-data</code>, <code>append: true</code> et <code>loop: \"{{ equipe_web }}\"</code>."],
             "checks": [
                 ('for s in web1 web2; do for u in $LAB_EQUIPE; do sur $s "id -nG $u" | grep -qw www-data || { echo "MSG:$u sur $s"; exit 1; }; done; done', "Chaque personne de ~/demandes/equipe.txt doit avoir un compte sur web1 et web2, membre du groupe www-data."),
                 ('for u in $LAB_EQUIPE; do ! sur db1 "id $u" || exit 1; done', "Les comptes de l'équipe web ne doivent pas exister sur db1."),
                 ("taches $I/web.yml | jq -s -e \"$M\"' any(.[]; mod(\"user\") and ((.loop // .with_items // \"\") | type == \"string\" and test(\"{{\")))' >/dev/null", "web.yml doit créer les comptes avec une seule tâche user qui boucle sur une variable (loop: \"{{ … }}\")."),
             ]},
            {"id": "A6.2", "points": 4, "title": "Signaler la recette",
             "ticket": {"from": "sophie", "body": "Un client a passé une vraie commande sur le serveur de recette… Sur les serveurs de recette <strong>uniquement</strong>, la page doit afficher un bandeau <strong>RECETTE</strong>. Et Thomas voudrait l'outil <code>htop</code> pour ses tests, mais seulement en recette : pas d'outils superflus en production."},
             "desc": "La page de web2 (recette) affiche <code>RECETTE</code>, pas celle de web1 ; <code>htop</code> est installé sur web2 et pas sur web1, par une tâche de <code>web.yml</code> soumise à une condition.",
             "hints": ["Deux endroits réagissent à l'environnement : une tâche (qui ne doit s'exécuter que sur certains serveurs) et le modèle de la page (qui n'affiche le bandeau que sur certains serveurs).", "<code>when: environnement == \"recette\"</code> sur la tâche <code>apt</code> ; <code>{% if environnement == \"recette\" %}…{% endif %}</code> dans le modèle."],
             "checks": [
                 # when sur la tâche (apt ou package) ou sur un bloc qui la contient
                 ("taches $I/web.yml | jq -s -e \"$M\"' any(.[]; has(\"when\") and (tostring | test(\"htop\")) and (mod(\"apt\") or mod(\"package\") or has(\"block\")))' >/dev/null", "La tâche qui installe htop doit dépendre d'une condition (when)."),
                 ('paquet web2 htop', "htop n'est pas installé sur web2 (recette)."),
                 ('! paquet web1 htop', "htop ne doit être installé qu'en recette : web1 est en production."),
                 ('page web2:8080 | grep -q RECETTE', "La page de web2 doit afficher un bandeau RECETTE."),
                 ('p=$(page web1:8080) && ! grep -q RECETTE <<<"$p"', "Le bandeau RECETTE ne doit pas apparaître sur web1 (production), qui doit toujours servir sa page sur 8080."),
             ]},
            {"id": "A6.3", "points": 6, "title": "Arrivées et départs", "manual": True,
             "ticket": {"from": "nadia", "body": "L'équipe bouge : la liste complète, avec les anciens, est dans <code>~/demandes/equipe.csv</code>. Les anciens ont encore un compte (et leurs fichiers !) sur les serveurs web : ça ne doit plus exister. Je ne veux plus deux listes à tenir : une seule variable <code>personnel</code>, une fiche par personne (<code>nom</code>, et <code>actif</code> vrai ou faux), qui remplace <code>equipe_web</code>. Quand quelqu'un part, on passe sa fiche à <code>false</code>, et c'est tout."},
             "desc": "La variable <code>personnel</code> des serveurs web est une liste de fiches (<code>nom</code>, <code>actif</code> booléen) qui reprend tout le fichier, et <code>equipe_web</code> n'existe plus ; <code>web.yml</code> garantit que les actifs ont leur compte dans <code>www-data</code> et que les anciens n'ont plus ni compte ni dossier personnel sur web1 et web2 (le vérificateur recrée un ancien compte avant de rejouer).",
             "hints": ["Un compte parti doit être <strong>décrit</strong> comme absent, pas simplement oublié du code. Et une même liste de fiches peut alimenter deux tâches, grâce à des filtres qui trient les fiches selon un attribut.", "<code>loop: \"{{ personnel | selectattr('actif') | map(attribute='nom') | list }}\"</code> pour créer ; <code>rejectattr('actif')</code> avec <code>state: absent</code> et <code>remove: true</code> pour supprimer."],
             "checks": [
                 ('p=$(etu "ansible-inventory --host web1" | jq -c ".personnel"); echo "$p" | jq -e "type == \\"array\\" and all(.[]; type == \\"object\\" and has(\\"nom\\") and (.actif | type == \\"boolean\\"))" >/dev/null', "La variable personnel des serveurs web doit être une liste de fiches, chacune avec nom et actif (true ou false, sans guillemets)."),
                 ('p=$(etu "ansible-inventory --host web1" | jq -c ".personnel"); [ "$(echo "$p" | jq -r "[.[] | select(.actif) | .nom] | sort | join(\\" \\")")" = "$LAB_EQUIPE" ] && for u in $LAB_ANCIENS; do echo "$p" | jq -e --arg u $u "any(.[]; .nom == \\$u and .actif == false)" >/dev/null || exit 1; done', "personnel ne reprend pas ~/demandes/equipe.csv : les actifs avec actif: true, les partis avec actif: false."),
                 ('[ -z "$(var web1 equipe_web)" ]', "equipe_web existe encore : personnel doit la remplacer (une seule liste à tenir)."),
                 ('u=${LAB_ANCIENS%% *}; sur web2 "id $u >/dev/null 2>&1 || useradd -m -s /bin/bash -G www-data $u"; joue web.yml || recap', "Le playbook web.yml échoue (voir le récapitulatif)."),
                 ('for s in web1 web2; do for u in $LAB_ANCIENS; do ! sur $s "id $u" && ! sur $s "test -d /home/$u" || { echo "MSG:$u sur $s"; exit 1; }; done; done', "Un ancien a encore un compte ou un dossier personnel sur un serveur web (le vérificateur en avait recréé un sur web2 avant de rejouer web.yml)."),
                 ('for s in web1 web2; do for u in $LAB_EQUIPE; do sur $s "id -nG $u" | grep -qw www-data || { echo "MSG:$u sur $s"; exit 1; }; done; done', "Un membre actif n'a plus son compte dans www-data."),
                 ('joue web.yml && rien_change || recap', "Rejoué, web.yml modifie encore quelque chose."),
             ]},
            {"id": "A6.4", "points": 5, "title": "La maintenance fantôme", "manual": True,
             "ticket": {"from": "julien", "body": "J'ai écrit <code>~/infra/julien/maintenance.yml</code> : il affiche une page de maintenance là où ma variable de maintenance (son nom est en tête du playbook) est vraie. Je l'ai mise à faux pour le groupe web et à vrai pour un seul serveur… et la page n'est pas du tout là où je l'attendais ! Et Léa voudrait pouvoir tout lever d'un coup en passant cette variable à <code>false</code> avec <code>-e</code>. Tu peux regarder ?"},
             "desc": "<code>ansible-playbook julien/maintenance.yml</code> dépose <code>/var/www/html/maintenance.html</code> sur le seul serveur que Julien a mis en maintenance, et la retire des autres ; avec <code>-e &lt;variable de Julien&gt;=false</code>, elle n'existe plus nulle part. Le choix du serveur reste dans les variables de Julien.",
             "hints": ["Pour Jinja2, que vaut une chaîne de caractères non vide ? Et une chaîne comparée à un booléen ? Affichez la valeur et son type sur chaque serveur : <code>ansible web -m debug -a \"msg={{ &lt;variable&gt; | type_debug }}\"</code> (depuis <code>~/infra</code>, avec l'option <code>--playbook-dir julien</code> pour qu'Ansible charge les variables de Julien). Et de quel type sont les valeurs passées par <code>-e</code> ?", "Le filtre <code>| bool</code> dans les deux conditions (par exemple <code>when: ma_variable | bool</code>) : c'est la seule solution qui marche aussi avec <code>-e ma_variable=false</code>."],
             "checks": [
                 ("yjson $I/julien/maintenance.yml | jq -e 'any(.[]; .hosts == \"web\")' >/dev/null && [ -z \"$(ls $I/julien/host_vars | grep -vE \"^$LAB_MAINT(\\.|$)\")\" ]", "Le playbook de Julien doit toujours viser le groupe web, et seul le serveur choisi par Julien doit avoir des host_vars : corrigez la condition, pas la cible."),
                 ('for s in web1 web2; do sur $s "rm -f /var/www/html/maintenance.html"; done; sur web1 "touch /var/www/html/maintenance.html"; sur web2 "touch /var/www/html/maintenance.html"; joue julien/maintenance.yml || recap', "ansible-playbook julien/maintenance.yml échoue (voir le récapitulatif)."),
                 ('for s in web1 web2; do if [ $s = "$LAB_MAINT" ]; then sur $s "test -f /var/www/html/maintenance.html" || { echo "MSG:$s devrait être en maintenance"; exit 1; }; else ! sur $s "test -e /var/www/html/maintenance.html" || { echo "MSG:$s ne devrait pas être en maintenance"; exit 1; }; fi; done', "La page de maintenance n'est pas là où Julien l'a demandée (et seulement là)."),
                 ('joue julien/maintenance.yml -e $LAB_MAINTVAR=false || recap', "Avec -e <variable de Julien>=false, le playbook de Julien échoue (voir le récapitulatif)."),
                 ('for s in web1 web2; do ! sur $s "test -e /var/www/html/maintenance.html" || { echo "MSG:$s"; exit 1; }; done', "Avec -e <variable de Julien>=false, une page de maintenance reste en place : la chaîne « false » est-elle vraiment comprise comme faux ?"),
                 ('joue julien/maintenance.yml || recap', "Relancé sans -e, le playbook de Julien échoue."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    7: {
        "title": "Jour 7 — La chasse aux dérives, puis les rôles",
        "description": "Détecter ce qui a été modifié à la main (et comprendre ce que le code ne voit pas), puis organiser un projet réutilisable. Compétences : --check, --diff, state: absent, ansible-galaxy init, rôles, defaults et vars, site.yml.",
        "lesson": """<h3>Mode vérification : --check et --diff</h3><pre>ansible-playbook vitrine.yml --check          # « à blanc » : dit ce qui changerait, sans rien changer<br>ansible-playbook vitrine.yml --check --diff   # … et montre les différences dans les fichiers</pre><p>C'est l'outil idéal pour repérer une <strong>dérive</strong> : quelqu'un a modifié un serveur à la main, et il ne correspond plus à ce que décrit le code. Une tâche <code>changed</code> en mode vérification signale le serveur concerné. Rejouer le playbook ramène tout dans l'état décrit.</p><h3>Les limites du mode vérification</h3><ul><li><strong>Ansible ne voit que ce que le code décrit.</strong> Un fichier ajouté, un paquet installé ou un compte créé à la main, dont le code ne parle pas, est invisible pour <code>--check</code>… et rejouer le playbook ne le retirera pas.</li><li>Pour qu'une chose n'existe pas, il faut la <strong>décrire absente</strong> : <code>state: absent</code> (modules <code>file</code>, <code>user</code>, <code>apt</code>…).</li><li>En mode vérification, les tâches <code>command</code> et <code>shell</code> ne sont pas exécutées, et une tâche qui dépend d'une précédente (un paquet pas encore installé, par exemple) peut échouer « pour de faux ».</li></ul><div class="tip">Si le code dit une chose et le serveur une autre, c'est le code qui a raison : toute modification passe par le playbook.</div><h3>Pourquoi des rôles ?</h3><p>Le playbook grossit, et demain il faudra un serveur de base de données, une supervision… Un <strong>rôle</strong> regroupe tout ce qu'il faut pour un service, dans une arborescence standard qu'Ansible sait lire.</p><pre>ansible-galaxy init --init-path roles vitrine      # crée le squelette roles/vitrine/</pre><pre>roles/vitrine/<br>├── tasks/main.yml       # les tâches (une simple liste, sans hosts ni play)<br>├── handlers/main.yml    # les handlers<br>├── templates/           # les modèles .j2 (src: accueil.html.j2 suffit)<br>├── files/               # les fichiers copiés tels quels<br>├── defaults/main.yml    # valeurs PAR DÉFAUT des variables : la priorité la plus faible<br>├── vars/main.yml        # variables internes du rôle : priorité TRÈS forte (au-dessus de host_vars !)<br>└── meta/main.yml        # description du rôle, et ses dépendances (autres rôles à jouer avant lui)</pre>""" + SCHEMA_ROLES + """<pre># site.yml : le point d'entrée de toute l'infrastructure<br>- name: Vitrines<br>  hosts: front<br>  become: true<br>  roles:<br>    - vitrine</pre><ul><li>Les <code>group_vars</code> et <code>host_vars</code> restent à la racine du projet : ce sont les réglages de <em>votre</em> infrastructure, alors que le rôle est générique.</li><li>Une valeur que chaque infrastructure doit pouvoir changer va dans <code>defaults/</code>, jamais dans <code>vars/</code> : une variable de <code>vars/</code> écrase silencieusement vos <code>group_vars</code> et <code>host_vars</code>.</li><li>Les rôles de <code>roles:</code> passent <strong>avant</strong> les <code>tasks:</code> du play. On peut aussi appeler un rôle au milieu des tâches : <code>ansible.builtin.import_role</code> (statique) ou <code>include_role</code> (dynamique).</li></ul>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
emit DEBUT "$(date +%s)"
# A7.1 : des dérives visibles par --check (page, configuration), et une invisible (un fichier dont le code ne parle pas)
p=web$((RANDOM % 2 + 1)); derives=$p
sur $p "test -f /var/www/html/index.html && sed -i 's|</body>|<p>Promo flash : -50 % sur tout le site ! (Julien)</p>\n</body>|' /var/www/html/index.html" || true
if [ $((RANDOM % 2)) = 0 ]; then
  c=web$((RANDOM % 2 + 1)); derives="$derives $c"
  sur $c "test -f /etc/nginx/sites-available/default && echo '# Réglage manuel de Marc : ne pas toucher' >> /etc/nginx/sites-available/default" || true
fi
emit DERIVES "$(printf '%s\n' $derives | sort -u | paste -sd,)"
# La page ajoutée : serveur tiré au hasard, emplacement selon la variante
f=web$((RANDOM % 2 + 1))
fp=$(echo soldes.html promo/flash.html offre-speciale.html archives/soldes-2024.html | cut -d' ' -f$((${LAB_VARIANTE_A7_1:-$((RANDOM % 4))} + 1)))
for s in web1 web2; do sur $s "rm -f /var/www/html/soldes.html /var/www/html/promo/flash.html /var/www/html/offre-speciale.html /var/www/html/archives/soldes-2024.html"; done
sur $f "mkdir -p \$(dirname /var/www/html/$fp) && printf '<h1>SOLDES</h1><p>Promo flash : -50 %% sur tout le site !</p>\n' > /var/www/html/$fp"
emit FANTOME "$f:/var/www/html/$fp"
# A7.3 : un compte avec tous les droits, créé à la main ; le compte et le fichier de sudoers dépendent de la variante
for s in web1 web2; do sur $s "for c in marc presta sauvegarde olivier; do userdel -r \$c >/dev/null 2>&1; done; rm -f /etc/sudoers.d/marc /etc/sudoers.d/prestataire /etc/sudoers.d/90-sauvegarde /etc/sudoers.d/zz-olivier"; done
case ${LAB_VARIANTE_A7_3:-$((RANDOM % 4))} in
  0) c=marc; sf=/etc/sudoers.d/marc;;
  1) c=presta; sf=/etc/sudoers.d/prestataire;;
  2) c=sauvegarde; sf=/etc/sudoers.d/90-sauvegarde;;
  *) c=olivier; sf=/etc/sudoers.d/zz-olivier;;
esac
m=web$((RANDOM % 2 + 1))
sur $m "useradd -m -s /bin/bash $c; echo '$c ALL=(ALL) NOPASSWD:ALL' > $sf; chmod 440 $sf"
emit COMPTE "$c"
emit SUDOERS "$sf"
''',
        "exercises": [
            {"id": "A7.1", "points": 5, "title": "La promo fantôme",
             "ticket": {"from": "sophie", "body": "Des clients nous réclament une remise de 50 %… qu'on n'a jamais proposée ! Quelqu'un a modifié des serveurs <strong>à la main</strong>, et peut-être pas seulement la page d'accueil. Sans te connecter aux serveurs : dis-moi dans <code>~/infra/reponses/derive.txt</code> quels serveurs ne correspondent plus au code, trouve la page de promotion qui a été <strong>ajoutée</strong> (<code>~/infra/reponses/fantome.txt</code>, au format <code>serveur:chemin</code>), puis remets tout en ordre avec Ansible."},
             "desc": "<code>reponses/derive.txt</code> : les serveurs dont l'état diffère de ce que décrit le playbook (un nom par ligne) ; <code>reponses/fantome.txt</code> : <code>serveur:chemin</code> de la page de promotion ajoutée à la main ; ensuite, plus aucune fausse promotion ni modification manuelle sur web1 et web2, corrigées avec Ansible (aucune commande <code>sudo</code> tapée à la main).",
             "hints": ["Le mode vérification compare chaque serveur à ce que décrit le code et signale les écarts. Mais un fichier dont le code ne parle pas lui est invisible : celui-là, cherchez-le autrement, toujours avec Ansible. (Si vous avez déjà rejoué le playbook, les dérives visibles sont corrigées : « Réinitialiser les fichiers de cette étape » les recrée.)", "<code>ansible-playbook web.yml --check --diff</code> (ou <code>site.yml</code> si le rôle existe déjà) : les serveurs avec une tâche <code>changed</code> ; <code>ansible web -m find -a \"paths=/var/www/html patterns=*.html recurse=yes\"</code> ou <code>-m command -a \"grep -rl Promo /var/www/html\"</code> ; <code>-b -m file -a \"path=… state=absent\"</code> ; puis rejouez le playbook."],
             "checks": [
                 ('[ "$(tr -s " ,\\r\\n" "\\n" < $I/reponses/derive.txt 2>/dev/null | grep . | sort -u | paste -sd,)" = "$LAB_DERIVES" ]', "reponses/derive.txt ne contient pas exactement les serveurs dont l'état diffère du code (mode vérification du playbook)."),
                 ('[ "$(ans $I/reponses/fantome.txt)" = "$LAB_FANTOME" ]', "reponses/fantome.txt ne contient pas serveur:chemin de la page de promotion ajoutée à la main (--check ne la voit pas : cherchez-la avec un module)."),
                 ('for s in web1 web2; do c=$(page $s:8080) && ! grep -q "Promo flash" <<<"$c" || { echo "MSG:$s"; exit 1; }; done; ! sur "${LAB_FANTOME%%:*}" "test -e ${LAB_FANTOME#*:}" || { echo "MSG:la page ajoutée à la main est toujours là"; exit 1; }', "Une fausse promotion est toujours en ligne (page d'accueil ou page ajoutée), ou un serveur ne répond plus sur 8080."),
                 ('for s in web1 web2; do ! sur $s "grep -q Marc /etc/nginx/sites-available/default" || exit 1; done', "La modification manuelle de la configuration de nginx est toujours là : rejouez le playbook."),
                 ('for s in web1 web2; do m=$(a_la_main $s $LAB_DEBUT); [ -z "$m" ] || { echo "MSG:$s : $(head -1 <<<"$m")"; exit 1; }; done', "Une commande a été tapée à la main avec sudo sur un serveur web : la remise en ordre doit se faire avec Ansible, pas en ajoutant une dérive de plus."),
             ]},
            {"id": "A7.2", "points": 6, "title": "Ranger en rôle", "manual": True,
             "ticket": {"from": "lea", "body": "Avant d'ajouter la base de données, on range : transforme le contenu de <code>web.yml</code> en un rôle <code>web</code> (<code>roles/web</code>), et crée le playbook <code>site.yml</code> qui l'applique au groupe web. Le résultat sur les serveurs doit rester strictement le même. Et je veux un vrai rôle : plus aucune tâche dans <code>site.yml</code>, et des valeurs par défaut que chacun peut surcharger."},
             "desc": "Le rôle <code>roles/web</code> contient les tâches, les handlers et les modèles ; <code>site.yml</code> l'applique au groupe <code>web</code> et ne contient plus de tâches ; <code>roles/web/vars/main.yml</code> ne fixe ni <code>environnement</code> ni <code>http_port</code> ; <code>ansible-playbook site.yml</code> reconstruit une page supprimée et, rejoué, ne change rien.",
             "hints": ["Un rôle, c'est une arborescence convenue : chaque morceau de web.yml a sa place (tâches, handlers, modèles, valeurs par défaut). Qu'est-ce qui reste alors dans site.yml ?", "<code>ansible-galaxy init --init-path roles web</code> ; tâches dans <code>roles/web/tasks/main.yml</code>, handlers dans <code>handlers/main.yml</code>, modèles dans <code>templates/</code> (<code>src: index.html.j2</code> suffit), valeurs par défaut dans <code>defaults/main.yml</code> ; <code>site.yml</code> : <code>hosts: web</code>, <code>become: true</code>, <code>roles: [web]</code>."],
             "checks": [
                 # main.yml, main.yaml ou main/ : les trois formes sont chargées par Ansible
                 ('ls -d $I/roles/web/tasks/main.yml $I/roles/web/tasks/main.yaml $I/roles/web/tasks/main 2>/dev/null | grep -q . && ls -d $I/roles/web/handlers/main.yml $I/roles/web/handlers/main.yaml $I/roles/web/handlers/main 2>/dev/null | grep -q .', "Le rôle web doit avoir tasks/main.yml et handlers/main.yml (ansible-galaxy init --init-path roles web)."),
                 ('find $I/roles/web/templates -type f 2>/dev/null | grep -q .', "Les modèles doivent être rangés dans roles/web/templates/."),
                 ("yjson $I/site.yml | jq -e 'any(.[]; ([.hosts] | flatten) == [\"web\"] and ((.roles // []) | map(if type == \"string\" then . else (.role // .name) end) | index(\"web\")))' >/dev/null", "site.yml doit appliquer le rôle web au groupe web (roles: - web)."),
                 ("yjson $I/site.yml | jq -e 'all(.[]; (.tasks // []) | length == 0)' >/dev/null", "site.yml contient encore des tâches : elles doivent être dans le rôle (roles/web/tasks/main.yml)."),
                 ("taches \"$I/roles/web/tasks/*.y*ml\" \"$I/roles/web/tasks/*/*.y*ml\" | jq -s -e \"$M\"' any(.[]; mod(\"template\") and (tostring | test(\"index.html\")))' >/dev/null", "Les tâches du rôle web ne génèrent pas la page d'accueil (module template)."),
                 (r'''! grep -rqsE '^[[:space:]]*(environnement|http_port)[[:space:]]*:' $I/roles/web/vars/main.yml $I/roles/web/vars/main.yaml $I/roles/web/vars/main''', "roles/web/vars/main.yml fixe environnement ou http_port : ces valeurs doivent pouvoir être surchargées (defaults/main.yml)."),
                 ('sur web2 "rm -f /var/www/html/index.html"; joue site.yml || recap', "ansible-playbook site.yml échoue (voir le récapitulatif)."),
                 ('joue site.yml && rien_change || recap', "Rejoué, site.yml modifie encore quelque chose : il n'est pas idempotent."),
                 ('page web1:8080 | grep -q web1 && page web2:8080 | grep -q web2', "Après site.yml, les serveurs web ne servent plus leur page sur le port 8080 (le vérificateur avait supprimé celle de web2)."),
             ]},
            {"id": "A7.3", "points": 4, "title": "Ce que --check ne voit pas", "manual": True,
             "ticket": {"from": "sophie", "body": "L'audit a trouvé, sur un de nos serveurs web, un compte avec tous les droits sudo : celui de quelqu'un qui est parti depuis des mois ! Et ton <code>--check</code> n'avait rien signalé… Trouve-le (le compte, et le fichier qui lui donne ces droits), supprime-le, et surtout fais en sorte que <code>site.yml</code> l'interdise : si quelqu'un le recrée, le prochain passage doit le faire disparaître."},
             "desc": "<code>site.yml</code> garantit l'absence, sur web1 et web2, du compte trouvé par l'audit, de son dossier personnel et du fichier de <code>/etc/sudoers.d</code> qui lui donne tous les droits (le vérificateur les recrée sur les deux serveurs avant de rejouer) ; rejoué, il ne change rien.",
             "hints": ["<code>--check</code> compare les serveurs à ce que décrit le code : ce que le code ne mentionne pas n'existe pas pour lui. Commencez par trouver le compte, avec Ansible : quels fichiers de <code>/etc/sudoers.d</code> donnent des droits, et à qui ? Puis, comment <em>décrire</em> une absence ?", "<code>ansible web -b -m find -a \"paths=/etc/sudoers.d\"</code>, puis <code>ansible web -b -m command -a \"cat &lt;fichier&gt;\"</code>. Dans le rôle web : <code>ansible.builtin.user</code> avec <code>name: &lt;compte&gt;</code>, <code>state: absent</code>, <code>remove: true</code> ; <code>ansible.builtin.file</code> avec <code>path: &lt;fichier de sudoers&gt;</code>, <code>state: absent</code>."],
             "checks": [
                 (r'''for s in web1 web2; do sur $s "id $LAB_COMPTE >/dev/null 2>&1 || useradd -m -s /bin/bash $LAB_COMPTE; echo '$LAB_COMPTE ALL=(ALL) NOPASSWD:ALL' > $LAB_SUDOERS; chmod 440 $LAB_SUDOERS"; done; joue site.yml || recap''', "ansible-playbook site.yml échoue (voir le récapitulatif)."),
                 ('for s in web1 web2; do ! sur $s "id $LAB_COMPTE" && ! sur $s "test -e $LAB_SUDOERS" && ! sur $s "test -d /home/$LAB_COMPTE" || { echo "MSG:$s"; exit 1; }; done', "Le vérificateur a recréé le compte trouvé par l'audit (et ses droits sudo) : après site.yml, il existe encore, ou son dossier personnel, ou son fichier dans /etc/sudoers.d."),
                 ('joue site.yml && rien_change || recap', "Rejoué, site.yml modifie encore quelque chose."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    8: {
        "title": "Jour 8 — Secrets et mise en production",
        "description": "Protéger les secrets, ajouter un serveur, reconstruire un serveur à l'identique. Compétences : ansible-vault, lineinfile, --limit, vars de rôle, projet complet.",
        "lesson": """<h3>Les secrets</h3><p>Un mot de passe ne doit jamais être écrit en clair dans un dépôt Git. <strong>Ansible Vault</strong> chiffre des fichiers de variables (AES-256) ; ils ne sont déchiffrés qu'en mémoire, au moment du déploiement.</p>""" + SCHEMA_VAULT + """<pre>echo "une-longue-phrase-secrète" &gt; ~/.vault_pass &amp;&amp; chmod 600 ~/.vault_pass   # la clé, hors du projet<br>ansible-vault create group_vars/cache/vault.yml    # crée et ouvre un fichier chiffré<br>ansible-vault encrypt group_vars/cache/vault.yml   # ou chiffre un fichier existant<br>ansible-vault view group_vars/cache/vault.yml<br>ansible-vault edit group_vars/cache/vault.yml<br>ansible-vault rekey group_vars/cache/vault.yml     # change la clé du coffre</pre><pre># ansible.cfg<br>[defaults]<br>vault_password_file = ~/.vault_pass</pre><ul><li><code>group_vars/cache/</code> peut être un <strong>dossier</strong> : tous ses fichiers sont chargés.</li><li>Convention : préfixer les variables secrètes par <code>vault_</code>, et les exposer dans un fichier en clair du même dossier (<code>vars.yml</code> : <code>memcache_mdp: "{{ vault_memcache_mdp }}"</code>) : on voit quelles variables existent sans ouvrir le coffre.</li><li>Alternative : chiffrer une seule valeur, <code>ansible-vault encrypt_string</code>, à coller dans un fichier en clair.</li></ul><div class="tip">Ajoutez <code>no_log: true</code> à une tâche qui manipule un secret : sa valeur n'apparaîtra ni dans la sortie d'Ansible, ni dans ses journaux.</div><h3>Modifier une ligne d'un fichier : lineinfile</h3><pre>    - name: Memcached écoute sur le réseau<br>      ansible.builtin.lineinfile:<br>        path: /etc/memcached.conf<br>        regexp: '^-l '<br>        line: -l 0.0.0.0<br>      notify: Redémarrer memcached</pre><p>La <strong>dernière</strong> ligne qui correspond à <code>regexp</code> est remplacée par <code>line</code> (ou <code>line</code> est ajoutée à la fin si aucune ne correspond) : c'est idempotent. S'il y a plusieurs lignes correspondantes, les autres restent en place : vérifiez le fichier.</p><h3>Un nouveau serveur</h3><ol><li>accès : empreinte SSH vérifiée et clé installée (comme au jour 1) ;</li><li>une ligne dans l'inventaire ;</li><li><code>ansible-playbook site.yml --limit vitrine3</code> : seul ce serveur est configuré, identique aux autres, sans toucher au reste du parc.</li></ol><div class="tip">Avec <code>--limit</code>, les serveurs exclus ne participent pas au jeu : leurs facts ne sont pas collectés (leurs variables d'inventaire restent disponibles dans <code>hostvars</code>).</div><h3>Toute l'infra en une commande</h3><pre>- name: Vitrines<br>  hosts: front<br>  become: true<br>  roles: [vitrine]<br><br>- name: Cache<br>  hosts: cache<br>  become: true<br>  roles: [memcached]</pre><p>Un serveur tombe en panne ? On en installe un neuf, on lance <code>site.yml</code>, et il est reconstruit à l'identique… à condition que <strong>tout</strong> soit décrit dans le code : ce qui a été fait à la main, ou en commande ad hoc, est perdu avec le serveur.</p><h3>Le piège de vars/</h3><p>Rappel du tableau du jour 4 : les variables de <code>roles/&lt;rôle&gt;/vars/main.yml</code> l'emportent sur <code>host_vars</code>. <code>ansible-inventory --host</code> ne les montre pas (elles ne font pas partie de l'inventaire) : pour voir la valeur réellement utilisée, affichez-la <strong>pendant le jeu</strong>, avec une tâche <code>ansible.builtin.debug: var=…</code>.</p>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
neuf web3
pw="Rando-$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 14)"
printf 'De : Sophie Marchand\nObjet : Redis de production\n\nLe mot de passe de Redis sur db1 sera : %s\nNe le recopie surtout pas en clair dans ~/infra !\n' "$pw" > $H/message-sophie.txt
own $H/message-sophie.txt
chmod 600 $H/message-sophie.txt
emit REDISPW "$pw"
# A8.4 : Julien a « rangé » le projet pendant le week-end, et quelque chose impose désormais environnement: production
# au-dessus de host_vars. La variante dit quoi : vars/ du rôle, vars: du play, set_fact ou include_vars dans le rôle
# (si le projet de l'étudiant ne s'y prête pas, vars/ du rôle). Ce qu'une préparation précédente avait ajouté est retiré.
if [ -d $I/roles/web ]; then
  mkdir -p $I/roles/web/vars
  python3 - "$I" "${LAB_VARIANTE_A8_4:-$((RANDOM % 4))}" <<'PY'
import os, re, sys, yaml
I, v = sys.argv[1], int(sys.argv[2])
R = os.path.join(I, "roles/web")
SITE, TACHES, VARS = os.path.join(I, "site.yml"), os.path.join(R, "tasks/main.yml"), os.path.join(R, "vars/main.yml")
VARS_JULIEN = "---\n# Variables du rôle web, rangées par Julien le week-end dernier\nenvironnement: production\nhttp_port: 8080\n"
PLAY_JULIEN = "{0}# Valeurs communes, rangées par Julien le week-end dernier\n{0}vars:\n{0}  environnement: production\n"
FAIT = "- name: Valeurs par défaut du site (rangées par Julien)\n  ansible.builtin.set_fact:\n    environnement: production\n\n"
INCLUS = "- name: Réglages du site (rangés par Julien)\n  ansible.builtin.include_vars: reglages.yml\n\n"
def lire(f):
    try:
        return open(f, encoding="utf-8").read()
    except OSError:
        return None
def ecrire(f, t):
    open(f, "w", encoding="utf-8").write(t)
if lire(VARS) == VARS_JULIEN:
    ecrire(VARS, "---\n# vars file for web\n")
t = lire(SITE)
if t is not None:
    ecrire(SITE, re.sub(r"(?m)^ *# Valeurs communes, rangées par Julien le week-end dernier\n *vars:\n *environnement: production\n", "", t))
t = lire(TACHES)
if t is not None:
    ecrire(TACHES, t.replace(FAIT, "").replace(INCLUS, ""))
if os.path.exists(os.path.join(R, "vars/reglages.yml")):
    os.remove(os.path.join(R, "vars/reglages.yml"))
def dans_le_role():
    ecrire(VARS, VARS_JULIEN)
    return True
def dans_le_play():
    t = lire(SITE)
    try:
        jeux = yaml.safe_load(t)
    except Exception:
        return False
    if not isinstance(jeux, list) or any(isinstance(j, dict) and j.get("hosts") == "web" and "vars" in j for j in jeux):
        return False
    m = re.search(r"(?m)^( *- +| *)hosts: *web *\n", t or "")
    if not m:
        return False
    ecrire(SITE, t[:m.end()] + PLAY_JULIEN.format(" " * len(m.group(1))) + t[m.end():])
    return True
def en_tete(bloc):
    t = lire(TACHES)
    if t is None:
        return False
    lignes = t.splitlines(keepends=True)
    i = 0
    while i < len(lignes) and (not lignes[i].strip() or lignes[i].startswith("#") or lignes[i].strip() == "---"):
        i += 1
    if i < len(lignes) and not lignes[i].startswith("- "):
        return False
    ecrire(TACHES, "".join(lignes[:i]) + bloc + "".join(lignes[i:]))
    return True
def par_include_vars():
    if not en_tete(INCLUS):
        return False
    ecrire(os.path.join(R, "vars/reglages.yml"), "---\n# Réglages du site, rangés par Julien le week-end dernier\nenvironnement: production\n")
    return True
if not [dans_le_role, dans_le_play, lambda: en_tete(FAIT), par_include_vars][v]():
    dans_le_role()
PY
  own $I/roles
fi
''',
        "exercises": [
            {"id": "A8.1", "points": 6, "title": "Le mot de passe de Redis", "manual": True,
             "ticket": {"from": "sophie", "body": "L'API aura besoin d'un Redis sur <code>db1</code>, accessible depuis le réseau (port 6379), mais <strong>protégé par mot de passe</strong>. Je t'ai laissé le mot de passe dans <code>~/message-sophie.txt</code>. Écris un rôle <code>redis</code> appliqué au groupe <code>bdd</code> dans <code>site.yml</code>, et range le mot de passe dans un fichier chiffré avec Ansible Vault : je ne veux le voir en clair nulle part dans <code>~/infra</code>, ni la clé du coffre. Je ferai réinstaller db1 à neuf pour vérifier que ton code suffit à tout remettre en place."},
             "desc": "Le rôle <code>redis</code>, appliqué au groupe <code>bdd</code> par <code>site.yml</code>, installe Redis sur db1, le fait écouter sur le réseau et exiger le mot de passe de Sophie ; le mot de passe est chiffré par Ansible Vault (par exemple dans <code>group_vars/bdd/vault.yml</code>) ; ni lui ni la clé du coffre n'apparaissent en clair dans <code>~/infra</code>. Test : db1 est réinstallé à neuf, puis <code>site.yml --limit bdd</code> doit suffire. (Attention : « Réinitialiser les fichiers de cette étape » tire un nouveau mot de passe et réinstalle web3.)",
             "hints": ["Le rôle doit tout faire sur un serveur neuf : installer, régler deux lignes de la configuration de Redis, et redémarrer Redis seulement si elles changent. Le secret, lui, vit dans un fichier chiffré que les serveurs du groupe bdd chargent automatiquement ; la clé du coffre reste hors du projet.", "Rôle <code>redis</code> : <code>apt</code> redis-server, deux <code>lineinfile</code> sur <code>/etc/redis/redis.conf</code> (lignes <code>bind</code> et <code>requirepass</code>, cette dernière est commentée à l'origine), un handler qui redémarre <code>redis-server</code>. <code>ansible-vault encrypt group_vars/bdd/vault.yml</code> et <code>vault_password_file</code> dans ansible.cfg."],
             "checks": [
                 ('ls -d $I/roles/redis/tasks/main.yml $I/roles/redis/tasks/main.yaml $I/roles/redis/tasks/main 2>/dev/null | grep -q .', "Le rôle redis n'existe pas (roles/redis/tasks/main.yml)."),
                 ("yjson $I/site.yml | jq -e 'any(.[]; ([.hosts] | flatten) == [\"bdd\"] and ((.roles // []) | map(if type == \"string\" then . else (.role // .name) end) | index(\"redis\")))' >/dev/null", "site.yml doit appliquer le rôle redis au groupe bdd."),
                 # Fichier entier chiffré (group_vars/bdd/vault.yml, ou un autre nom) ou valeur chiffrée par encrypt_string
                 ("grep -rqE '^\\$ANSIBLE_VAULT|!vault' $I","Aucun fichier chiffré avec ansible-vault dans ~/infra (group_vars/bdd/vault.yml, par exemple)."),
                 ('coffres | grep -qF -- "$LAB_REDISPW"', "Le coffre (group_vars/bdd/vault.yml) ne contient pas le mot de passe de Sophie, ou ne s'ouvre pas avec la clé configurée (vault_password_file)."),
                 ('! grep -rqF -- "$LAB_REDISPW" $I', "Le mot de passe de Redis apparaît en clair dans ~/infra : il ne doit être que dans le fichier chiffré."),
                 (r'''f=$(cle_coffre); [ -n "$f" ] && case "$f" in $I/*|*/infra/*) exit 1;; esac; if [ -x "$f" ]; then k=$(etu "$f" | head -1); else k=$(head -1 "$f" 2>/dev/null); fi; [ -n "$k" ] && ! grep -rqF -- "$k" $I''', "La clé du coffre doit être dans un fichier hors de ~/infra, désigné par vault_password_file dans ansible.cfg, et n'apparaître dans aucun fichier du projet."),
                 ('reconstruit db1 && joue site.yml --limit bdd || recap', "Le vérificateur a réinstallé db1 à neuf : site.yml --limit bdd échoue (voir le récapitulatif)."),
                 ('r=$(redis PING); [ "${r%% *}" = -NOAUTH ]', "Sur db1 réinstallé, après site.yml, Redis ne répond pas sur 10.10.0.21:6379, ou accepte les commandes sans mot de passe : le rôle ne fait pas tout."),
                 ('[ "$(redis "AUTH $LAB_REDISPW" PING)" = +PONG ]', "Redis n'accepte pas le mot de passe donné par Sophie."),
             ]},
            {"id": "A8.2", "points": 5, "title": "web3 arrive",
             "ticket": {"from": "thomas", "body": "Les soldes approchent : l'hébergeur vient de nous livrer un troisième serveur web, <code>web3</code> (compte <code>admin</code>, mot de passe <code>cimes</code>, installation neuve). Il doit être configuré exactement comme les deux autres. Et ne relance pas tout le parc pour ça, on est en pleine journée : pendant que tu configures web3, personne ne touche à web1 et web2."},
             "desc": "web3 est dans le groupe <code>web</code> de l'inventaire, accessible par clé SSH, et configuré comme les autres serveurs web (page sur le port 8080, comptes de l'équipe) ; pendant sa première configuration, Ansible n'est pas intervenu sur web1 ni sur web2.",
             "hints": ["Trois étapes : l'accès (comme au premier jour), l'inventaire, puis un jeu restreint au nouveau serveur. Une option d'ansible-playbook restreint les serveurs visés par un jeu.", "<code>ssh-copy-id admin@web3</code> (après avoir vérifié l'empreinte) ; une ligne dans l'inventaire ; <code>ansible-playbook site.yml --limit web3</code>."],
             "checks": [
                 ('[ "$(groupe web)" = "web1,web2,web3" ]', "web3 doit être ajouté au groupe web de l'inventaire."),
                 ('ssh_ok web3', "Pas de connexion SSH sans mot de passe vers web3 (empreinte et clé)."),
                 ('page web3:8080 | grep -q web3', "web3 ne sert pas la page de la boutique sur le port 8080."),
                 (r'''u=$(etu "ansible-inventory --host web1" | jq -r '[(.personnel // [])[] | select(.actif) | .nom] + (.equipe_web // []) | .[]'); [ -n "$u" ] && for x in $u; do sur web3 "id -nG $x" | grep -qw www-data || { echo "MSG:$x"; exit 1; }; done''', "web3 n'a pas reçu toute la configuration des serveurs web (comptes de l'équipe)."),
                 (r'''T=$(sudo_ansible web3 | head -1); [ -n "$T" ] && for s in web1 web2; do sudo_ansible $s | awk -v t=$T '$1 >= t - 5 && $1 <= t + 5 { n++ } END { exit (n > 0) }' || { echo "MSG:$s"; exit 1; }; done''', "Pendant la première configuration de web3, Ansible est aussi intervenu sur web1 ou web2 (journal de sudo) : il fallait restreindre le jeu à web3."),
             ]},
            {"id": "A8.3", "points": 6, "title": "Toute l'infra en une commande", "manual": True,
             "ticket": {"from": "lea", "body": "Dernière épreuve avant l'audit de demain : l'auditeur va faire réinstaller <code>web2</code> à neuf par l'hébergeur (mêmes clés SSH, notre clé déjà installée), puis lancer <strong>une seule fois</strong> <code>ansible-playbook site.yml</code>. web2 doit revenir exactement comme les autres serveurs web, la base doit être décrite aussi, et un second passage ne doit rien changer. Tout ce qui a été fait à la main ou en commande ponctuelle sera perdu : vérifie que ton code décrit vraiment tout."},
             "desc": "Après la réinstallation de web2 à neuf et un seul <code>ansible-playbook site.yml</code> : les quatre serveurs sont configurés, web2 a la même configuration nginx que web1, sert sa page sur 8080, a les comptes de l'équipe, le dossier des promotions et l'outil tree ; rejoué, <code>site.yml</code> ne change rien.",
             "hints": ["Sur un serveur neuf, seul compte ce que décrit le code. Faites l'essai vous-même sur la version actuelle : qu'est-ce qui avait été fait à la main ou en ad hoc, et qu'est-ce qu'un serveur neuf n'a pas encore (cache APT vide, dossiers absents…) ?", "Un play par groupe dans <code>site.yml</code> (rôle web pour <code>web</code>, rôle redis pour <code>bdd</code>) ; lisez le récapitulatif, puis la première tâche en échec avec <code>-v</code>."],
             "checks": [
                 ('reconstruit web2 && joue site.yml || recap', "Le vérificateur a réinstallé web2 à neuf : un seul site.yml ne suffit pas à le reconstruire (voir le récapitulatif)."),
                 ('[ "$(grep -cE "^(web1|web2|web3|db1) +: ok=" /tmp/lab-jeu.txt)" = 4 ]', "site.yml doit configurer les quatre serveurs : web1, web2, web3 et db1."),
                 ('page web2:8080 | grep -q web2 && [ "$(somme web2 /etc/nginx/sites-available/default)" = "$(somme web1 /etc/nginx/sites-available/default)" ]', "web2 reconstruit ne sert pas sa page sur 8080, ou sa configuration nginx diffère de celle de web1."),
                 (r'''u=$(etu "ansible-inventory --host web1" | jq -r '[(.personnel // [])[] | select(.actif) | .nom] + (.equipe_web // []) | .[]'); [ -n "$u" ] && for x in $u; do sur web2 "id -nG $x" | grep -qw www-data || { echo "MSG:$x"; exit 1; }; done''', "web2 reconstruit n'a pas les comptes de l'équipe web."),
                 ('paquet web2 tree && [ "$(droits web2 /var/www/html/promo | cut -d" " -f2-)" = "www-data www-data" ]', "web2 reconstruit n'a pas l'outil tree ou le dossier des promotions : ce n'est pas décrit par le code."),
                 ('joue site.yml && rien_change || recap', "Rejoué, site.yml modifie encore quelque chose : il n'est pas idempotent."),
             ]},
            {"id": "A8.4", "points": 5, "title": "Le bandeau a disparu", "manual": True,
             "ticket": {"from": "thomas", "body": "Julien a « rangé » le projet ce week-end. Relance <code>site.yml</code> : web2, notre serveur de recette, se prend pour la production ! Plus de bandeau, plus de htop. Pourtant <code>host_vars/web2.yml</code> dit bien recette, et <code>ansible-inventory --host web2</code> aussi. Je n'y comprends rien."},
             "desc": "Après <code>site.yml</code>, web2 affiche le bandeau RECETTE et a htop, web1 non : plus rien, dans le projet, n'impose <code>environnement</code> au-dessus de <code>host_vars</code>, et <code>roles/web/vars/main.yml</code> ne fixe ni <code>environnement</code> ni <code>http_port</code> (les valeurs par défaut du rôle vont là où elles peuvent être surchargées).",
             "hints": ["<code>ansible-inventory</code> ne voit que l'inventaire : ni les variables des rôles, ni celles des plays, ni celles que les tâches définissent. Affichez la valeur de <code>environnement</code> <strong>pendant le jeu</strong>, sur web2, puis cherchez qui la définit : lesquelles de ces sources l'emportent sur <code>host_vars</code> ? (Tableau du jour 4.)", "<code>grep -rn environnement ~/infra --include=*.yml</code> : <code>vars/</code> d'un rôle, <code>vars:</code> d'un play, <code>set_fact</code> ou <code>include_vars</code> passent tous avant <code>host_vars</code>. Retirez ce que Julien a ajouté ; les valeurs par défaut vont dans <code>roles/web/defaults/main.yml</code>."],
             "checks": [
                 (r'''! grep -rqsE '^[[:space:]]*(environnement|http_port)[[:space:]]*:' $I/roles/web/vars/main.yml $I/roles/web/vars/main.yaml $I/roles/web/vars/main''', "roles/web/vars/main.yml fixe encore environnement ou http_port : ces variables y ont une priorité plus forte que host_vars."),
                 ('joue site.yml || recap', "ansible-playbook site.yml échoue (voir le récapitulatif)."),
                 ('page web2:8080 | grep -q RECETTE && p=$(page web1:8080) && ! grep -q RECETTE <<<"$p"', "Après site.yml, web2 n'affiche pas le bandeau RECETTE (ou web1 l'affiche)."),
                 ('paquet web2 htop', "htop n'est pas installé sur web2 (recette) après site.yml."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    9: {
        "title": "Jour 9 — En conditions réelles : fiabiliser ses playbooks",
        "description": "Lire le résultat d'une tâche, décider soi-même de ce qui est « changé » ou « en échec », poser des garde-fous, prévoir l'échec et revenir en arrière. Compétences : register, debug, changed_when, failed_when, delegate_to, run_once, assert, pre_tasks, block/rescue/always, unarchive.",
        "lesson": """<h3>1. Garder le résultat d'une tâche : register</h3><pre>    - name: Version du noyau<br>      ansible.builtin.command: uname -r<br>      register: noyau<br>      changed_when: false          # une lecture ne change rien : ne pas mentir au récapitulatif<br><br>    - ansible.builtin.debug:<br>        var: noyau                 # tout le résultat : rc, stdout, stderr, stdout_lines, changed, failed…</pre><ul><li><code>noyau.rc</code> : code de retour ; <code>noyau.stdout</code> / <code>noyau.stderr</code> : sorties standard et d'erreur (certains programmes, comme <code>java -version</code>, écrivent leur version sur la sortie d'erreur !) ; <code>noyau.stdout_lines</code> : la sortie découpée en lignes.</li><li>Le résultat est une variable du serveur : d'une tâche à l'autre, et depuis un autre serveur via <code>hostvars['vitrine1']['noyau']</code>.</li><li><code>-v</code> affiche le résultat complet de chaque tâche : le meilleur moyen de savoir ce qu'on peut tester.</li></ul><h3>2. Décider de ce qui est « changé » ou « en échec »</h3><pre>    - name: Rotation des journaux<br>      ansible.builtin.command: /usr/local/sbin/tourner-journaux<br>      register: rotation<br>      changed_when: "'ROTATION=0' not in rotation.stdout"<br>      failed_when: rotation.rc not in [0, 2] or 'CRITIQUE' in rotation.stderr</pre><ul><li><code>changed_when</code> et <code>failed_when</code> remplacent le jugement d'Ansible par une condition (les mêmes que <code>when</code>) ;</li><li><code>failed_when: false</code> : la tâche ne peut pas échouer. <code>ignore_errors: true</code> affiche l'échec puis continue : presque toujours une mauvaise idée, qui cache les vrais problèmes.</li></ul><h3>3. Écrire sur le poste de contrôle : delegate_to, run_once</h3><pre>    - name: Rapport sur le poste de contrôle<br>      ansible.builtin.copy:<br>        dest: "{{ playbook_dir }}/rapport.txt"<br>        content: |<br>          {% for h in groups['front'] %}<br>          {{ h }};{{ hostvars[h]['noyau']['stdout'] }}<br>          {% endfor %}<br>      delegate_to: localhost       # exécutée sur le poste de contrôle…<br>      run_once: true               # … une seule fois, pas une fois par serveur<br>      become: false                # pas de sudo sur le poste de contrôle !</pre><h3>4. Des garde-fous : assert</h3><pre>  pre_tasks:                        # avant les rôles et les tâches<br>    - name: Paramètres cohérents<br>      ansible.builtin.assert:<br>        that:<br>          - port_vitrine | int &gt; 1024<br>          - saison in ['hiver', 'été']<br>        fail_msg: "Paramètres refusés : port {{ port_vitrine }}, saison {{ saison }}"</pre><p>Vérifier les données d'entrée <strong>avant</strong> d'agir évite de laisser un serveur à moitié configuré. Attention à l'ordre d'un play : <code>pre_tasks</code>, puis <code>roles</code>, puis <code>tasks</code>, puis <code>post_tasks</code>. Le module <code>ansible.builtin.fail</code> arrête le jeu avec un message, sous une condition <code>when</code>.</p><h3>5. Prévoir l'échec : block, rescue, always</h3><pre>    - name: Mise à jour du catalogue<br>      block:                                   # on essaie…<br>        - ansible.builtin.unarchive:<br>            src: "http://depot.exemple.lan/catalogue-{{ version }}.tar.gz"<br>            dest: /srv/catalogue<br>            remote_src: true                   # l'archive est téléchargée par le serveur<br>        - ansible.builtin.command: /srv/catalogue/verifier<br>          changed_when: false<br>      rescue:                                  # … si une tâche du bloc échoue<br>        - ansible.builtin.debug:<br>            msg: "Échec de {{ ansible_failed_task.name }} : retour arrière"<br>        - ansible.builtin.fail:<br>            msg: "Mise à jour annulée"       # pour que le jeu reste en échec<br>      always:                                  # … dans tous les cas<br>        - ansible.builtin.lineinfile:<br>            path: /var/log/catalogue.log<br>            line: "{{ now() }} {{ version }}"<br>            create: true</pre><p>Si <code>rescue</code> se termine sans erreur, l'échec est considéré comme <em>rattrapé</em> (<code>rescued=1</code> au récapitulatif) et le jeu continue : ajoutez un <code>fail</code> si l'échec doit rester visible. Pour revenir en arrière, il faut avoir noté l'état d'avant (<code>stat</code> + <code>register</code>) <strong>avant</strong> de le modifier.</p><figure class="schema"><svg viewBox="0 0 640 266" role="img" aria-label="Un bloc : on essaie, on rattrape l'échec, et always s'exécute dans tous les cas"><defs><marker id="a9a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="pa" d="M0,0 L10,5 L0,10 z"/></marker><marker id="a9g" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="pt" d="M0,0 L10,5 L0,10 z"/></marker><marker id="a9w" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="pw" d="M0,0 L10,5 L0,10 z"/></marker></defs>
<rect class="a" x="10" y="12" width="180" height="140" rx="8"/><text class="ttl" x="22" y="36">block</text><text class="t2" x="22" y="54">on essaie, dans l'ordre</text>
<rect class="b" x="22" y="64" width="156" height="22" rx="4"/><text class="t2" x="32" y="79">tâche 1</text>
<rect class="b" x="22" y="92" width="156" height="22" rx="4"/><text class="t2" x="32" y="107">tâche 2</text>
<rect class="b" x="22" y="120" width="156" height="22" rx="4"/><text class="t2" x="32" y="135">tâche 3</text>
<rect class="w" x="238" y="112" width="192" height="72" rx="8"/><text x="250" y="134">rescue</text><text class="t2" x="250" y="154">si une tâche du block échoue</text><text class="t2" x="250" y="172">(les suivantes sont sautées)</text>
<rect class="b" x="470" y="12" width="160" height="70" rx="8"/><text x="482" y="36">always</text><text class="t2" x="482" y="56">exécuté dans tous</text><text class="t2" x="482" y="72">les cas : journal…</text>
<path class="la" d="M190,44 L468,44" marker-end="url(#a9a)"/><text class="t2" x="226" y="36">tout a réussi : rescue est ignoré</text>
<path class="ld" d="M190,120 L236,140" marker-end="url(#a9w)"/><text class="t2" x="196" y="170">échec</text>
<path class="la" d="M430,148 C520,148 550,120 550,84" marker-end="url(#a9a)"/>
<text class="t2" x="10" y="212">Issue, une fois always terminé :</text>
<rect class="g" x="10" y="220" width="200" height="40" rx="6"/><text x="22" y="237">block réussi</text><text class="t2" x="22" y="253">le jeu continue</text>
<rect class="w" x="220" y="220" width="200" height="40" rx="6"/><text x="232" y="237">rescue réussi</text><text class="t2" x="232" y="253">rescued=1, le jeu continue</text>
<rect class="r" x="430" y="220" width="200" height="40" rx="6"/><text x="442" y="237">rescue en échec (fail)</text><text class="t2" x="442" y="253">le serveur passe en échec</text>
</svg><figcaption>rescue ne s'exécute qu'en cas d'échec dans le block ; always, dans tous les cas. Un rescue qui se termine sans erreur efface l'échec : terminez-le par fail si l'échec doit rester visible.</figcaption></figure>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
docker inspect web3 >/dev/null 2>&1 && serveur web3
# A9.2 : le script de purge de Marc, sur les serveurs web. Ses conventions (code « purge déjà en cours », mot qui
# signale une erreur, clé du compte rendu) dépendent de la variante
case ${LAB_VARIANTE_A9_2:-$((RANDOM % 4))} in
  0) rc=3; err=ERREUR; cle=SUPPRIMES;;
  1) rc=4; err=ECHEC; cle=PURGES;;
  2) rc=5; err=FATAL; cle=EFFACES;;
  *) rc=2; err=IMPOSSIBLE; cle=RETIRES;;
esac
for s in $(webs); do
  docker exec -i $s bash -c "mkdir -p /var/cache/boutique /etc/boutique && cat > /usr/local/sbin/purge-cache && chmod 755 /usr/local/sbin/purge-cache" <<EOF
#!/bin/bash
# Purge du cache des pages de la boutique (Marc)
if [ -e /run/purge.lock ]; then echo "Une purge est déjà en cours"; exit $rc; fi
if [ ! -f /etc/boutique/purge.conf ]; then echo "$err: /etc/boutique/purge.conf introuvable"; exit 0; fi
n=\$(find /var/cache/boutique -type f | wc -l)
find /var/cache/boutique -type f -delete
echo "$cle=\$n"
EOF
  sur $s "echo 'repertoire=/var/cache/boutique' > /etc/boutique/purge.conf; touch /var/cache/boutique/page-accueil.html /var/cache/boutique/page-soldes.html"
done
# A9.4 : les livraisons du site vitrine, sur le dépôt interne (deux bonnes, une cassée)
v1="2.$((4 + RANDOM % 3)).$((RANDOM % 9))"; v2="3.0.$((RANDOM % 9))"; vc="3.1.0-rc$((1 + RANDOM % 4))"
d=/opt/ansible-lab/depot/livraisons
rm -rf $d && mkdir -p $d
for v in $v1 $v2; do
  t=$(mktemp -d); mkdir $t/css
  printf '<!DOCTYPE html>\n<html lang="fr"><head><meta charset="utf-8"><title>Vitrine</title></head>\n<body><h1>Vitrine Cimes &amp; Sentiers</h1><p>Version %s</p></body></html>\n' $v > $t/index.html
  echo 'h1 { color: #2d6a4f; }' > $t/css/vitrine.css
  tar czf $d/vitrine-$v.tar.gz -C $t . && rm -rf $t
done
t=$(mktemp -d); echo "Version $vc : archive incomplète" > $t/LISEZMOI.txt; tar czf $d/vitrine-$vc.tar.gz -C $t . && rm -rf $t
chmod -R a+rX $d
cat > $H/demandes/livraisons.txt <<EOF
De : Thomas Leroy
Objet : livraisons du site vitrine

Les versions du site vitrine sont sur le dépôt interne : http://depot.cimes.lan:8000/livraisons/vitrine-<version>.tar.gz
À déployer dans l'ordre : $v1, puis $v2.
La $vc sort tout juste du four : essaie-la, mais je ne suis pas sûr qu'elle soit complète.
EOF
own $H/demandes
emit V1 "$v1"; emit V2 "$v2"; emit VC "$vc"
''',
        "exercises": [
            {"id": "A9.1", "points": 6, "title": "Quelle version tourne où ?", "manual": True,
             "ticket": {"from": "lea", "body": "L'éditeur de sécurité nous demande la version exacte de nginx sur chaque serveur web et celle de Redis sur db1. Et il la redemandera à chaque alerte : écris <code>rapport.yml</code>, qui produit <code>~/infra/reponses/versions.txt</code>, une ligne par logiciel : <code>serveur;logiciel;version</code> (ex. <code>web9;nginx;1.2.3</code>, ou <code>db9;redis;4.5.6</code>), triée par serveur, régénérée à chaque exécution. Je le relancerai deux fois : le second passage ne doit rien changer."},
             "desc": "<code>ansible-playbook rapport.yml</code> (re)crée <code>reponses/versions.txt</code> sur le poste de contrôle : une ligne <code>serveur;nginx;&lt;version&gt;</code> par serveur web et <code>db1;redis;&lt;version&gt;</code>, triées par nom de serveur, avec les versions que donnent <code>nginx -v</code> et <code>redis-server --version</code> ; rejoué, il ne change rien.",
             "hints": ["Une commande ne suffit pas : il faut garder son résultat (regardez-le en entier avec <code>-v</code> : sur quelle sortie <code>nginx -v</code> écrit-il ?), puis écrire UN fichier, sur le poste de contrôle, avec les résultats de tous les serveurs.", "<code>register</code> + <code>changed_when: false</code> sur chaque lecture ; puis une tâche <code>copy</code> (<code>content:</code> construit avec une boucle sur <code>groups['all']</code> et <code>hostvars[h]</code>) avec <code>delegate_to: localhost</code>, <code>run_once: true</code> et <code>become: false</code>."],
             "checks": [
                 ('rm -f $I/reponses/versions.txt; joue rapport.yml || recap', "ansible-playbook rapport.yml échoue (voir le récapitulatif)."),
                 ('[ -f $I/reponses/versions.txt ]', "Après rapport.yml, ~/infra/reponses/versions.txt n'existe pas (le vérificateur l'avait supprimé)."),
                 (r'''a=$( { for s in $(groupe web | tr , ' '); do echo "$s;nginx;$(sur $s 'nginx -v 2>&1' | sed 's|.*/||')"; done; echo "db1;redis;$(sur db1 'redis-server --version' | sed 's/.*v=\([^ ]*\).*/\1/')"; } | sort)
  r=$(tr -d ' \r' < $I/reponses/versions.txt | grep .); [ "$r" = "$a" ] || { echo "MSG:attendu : $(echo $a)"; exit 1; }''', "reponses/versions.txt ne contient pas exactement une ligne serveur;logiciel;version par logiciel, triée par serveur."),
                 ('joue rapport.yml && rien_change || recap', "Rejoué, rapport.yml annonce des changements : une simple lecture ne change rien, et le rapport est identique."),
             ]},
            {"id": "A9.2", "points": 6, "title": "La purge qui ment", "manual": True,
             "ticket": {"from": "thomas", "body": "Le script <code>/usr/local/sbin/purge-cache</code> de Marc (sur chaque serveur web) vide le cache des pages et affiche le nombre de fichiers supprimés. Écris <code>purge.yml</code> qui le lance sur les serveurs web. Mais attention, Marc a ses propres conventions (lis son script) : quand il échoue, il affiche un message d'erreur et renvoie 0 quand même ; et quand une purge est déjà en cours, il renvoie un code non nul, ce qui n'est pas grave. Je veux un récapitulatif honnête : « changed » seulement si des fichiers ont été supprimés, « failed » en cas d'erreur, et rien d'autre."},
             "desc": "<code>purge.yml</code> lance le script sur les serveurs web ; un serveur n'est <code>changed</code> que si des fichiers ont été supprimés ; le jeu échoue quand le script signale une erreur ; le code de retour « purge déjà en cours » n'est pas un échec.",
             "hints": ["Lisez d'abord le script (avec Ansible : <code>-m command -a \"cat /usr/local/sbin/purge-cache\"</code>) : quels messages, quels codes de retour ? Puis enregistrez le résultat de la commande et regardez-le en entier (<code>-v</code>) : <code>rc</code>, <code>stdout</code>… C'est à vous de dire à Ansible ce que « changé » et « échoué » veulent dire pour ce script.", "<code>register</code>, puis <code>changed_when:</code> une condition sur le texte de <code>stdout</code>, et <code>failed_when:</code> qui combine deux conditions avec <code>or</code> ; <code>in</code> teste la présence d'un texte, et aussi l'appartenance à une liste (<code>rc in [0, …]</code>)."],
             "checks": [
                 ('for s in $(groupe web | tr , " "); do sur $s "rm -f /run/purge.lock /var/cache/boutique/*; test -f /etc/boutique/purge.conf || echo repertoire=/var/cache/boutique > /etc/boutique/purge.conf"; done; sur web1 "touch /var/cache/boutique/a.html /var/cache/boutique/b.html"; joue purge.yml || recap', "ansible-playbook purge.yml échoue alors que la purge s'est bien passée (voir le récapitulatif)."),
                 ('[ "$(changes web1)" = 1 ] && [ "$(changes web2)" = 0 ] && [ -z "$(sur web1 "ls /var/cache/boutique")" ]', "Le vérificateur avait mis deux fichiers dans le cache de web1 et aucun dans celui de web2 : web1 seul doit être « changed » (changed=1), et son cache vidé."),
                 ('joue purge.yml && rien_change || recap', "Relancé sur des caches vides, purge.yml annonce encore des changements."),
                 ('sur web2 "touch /run/purge.lock"; joue purge.yml; r=$?; sur web2 "rm -f /run/purge.lock"; [ $r = 0 ] || recap', "Une purge déjà en cours a fait échouer le jeu : d'après le script de Marc, ce n'est pas une erreur."),
                 ('sur web1 "mv /etc/boutique/purge.conf /etc/boutique/purge.conf.sauve"; joue purge.yml; r=$?; sur web1 "mv /etc/boutique/purge.conf.sauve /etc/boutique/purge.conf"; [ $r != 0 ] && echec_attendu', "Le script a signalé une erreur sur web1 (le vérificateur avait retiré sa configuration), mais le jeu a réussi : l'échec doit être signalé."),
             ]},
            {"id": "A9.3", "points": 4, "title": "Garde-fous", "manual": True,
             "ticket": {"from": "sophie", "body": "Julien a lancé <code>site.yml -e http_port=80</code> « pour voir »… Plus jamais de déploiement avec un port réservé ou un environnement inventé : <code>site.yml</code> doit refuser un <code>http_port</code> hors de 1024-65535 et un <code>environnement</code> autre que <code>production</code> ou <code>recette</code>, <strong>avant</strong> de toucher à quoi que ce soit sur les serveurs, avec un message clair."},
             "desc": "Avec <code>-e http_port=80</code> ou <code>-e environnement=preprod</code>, <code>site.yml</code> échoue sans rien modifier (ni la configuration de nginx, ni la page) ; avec les valeurs normales, il réussit.",
             "hints": ["Un module sert à vérifier des conditions et à arrêter le jeu avec un message. Mais attention à l'ordre des sections d'un play : les rôles passent avant la section <code>tasks</code>.", "<code>pre_tasks:</code> dans le play des serveurs web, avec <code>ansible.builtin.assert</code> (<code>that:</code> une liste de conditions, <code>fail_msg:</code>) ; <code>http_port | int</code> pour comparer un nombre."],
             "checks": [
                 ('echo "$(somme web1 /etc/nginx/sites-available/default)$(somme web1 /var/www/html/index.html)" > /tmp/lab-avant; ! joue site.yml -e http_port=80', "Avec -e http_port=80, site.yml réussit : ce port doit être refusé."),
                 ('echec_attendu && rien_change || recap', "Avec -e http_port=80, site.yml a modifié quelque chose avant de s'arrêter (ou n'a même pas démarré) : la vérification doit passer avant toute tâche."),
                 ('! joue site.yml -e environnement=preprod', "Avec -e environnement=preprod, site.yml réussit : cet environnement doit être refusé."),
                 ('echec_attendu && rien_change || recap', "Avec -e environnement=preprod, site.yml a modifié quelque chose avant de s'arrêter."),
                 ('[ "$(somme web1 /etc/nginx/sites-available/default)$(somme web1 /var/www/html/index.html)" = "$(cat /tmp/lab-avant)" ]', "La configuration de nginx ou la page de web1 ont été modifiées par un déploiement refusé."),
                 ('joue site.yml || recap', "Avec les valeurs normales, site.yml échoue (voir le récapitulatif)."),
             ]},
            {"id": "A9.4", "points": 7, "title": "Livraison avec filet", "manual": True,
             "ticket": {"from": "thomas", "body": "Le site vitrine arrive en archives sur le dépôt interne (détails dans <code>~/demandes/livraisons.txt</code>). Écris <code>livraison.yml</code>, lancé avec <code>-e version=X</code> sur les serveurs web : il déploie l'archive dans <code>/var/www/vitrine/releases/X</code>, fait pointer le lien <code>/var/www/vitrine/current</code> dessus, et vérifie que <code>current/index.html</code> existe. Si quoi que ce soit échoue, on revient à la version précédente et le jeu échoue. Et chaque tentative, réussie ou non, est notée dans <code>/var/log/livraisons.log</code> (une ligne avec la version)."},
             "desc": "Après <code>-e version=</code> la 1re puis la 2e version de Thomas, <code>/var/www/vitrine/current</code> est un lien vers la release déployée ; avec la version cassée, le jeu échoue et <code>current</code> pointe toujours sur la 2e version ; <code>/var/log/livraisons.log</code> compte une ligne par tentative, la dernière citant la version cassée. Le playbook utilise <code>block</code>, <code>rescue</code> et <code>always</code>.",
             "hints": ["Trois temps : essayer, rattraper l'échec, toujours journaliser. Pour revenir en arrière, il faut savoir où pointait le lien <strong>avant</strong> de le changer.", "<code>stat</code> du lien <code>current</code> → <code>register</code> (<code>stat.lnk_source</code>) ; <code>block</code> : <code>file</code> (dossier de la release), <code>unarchive</code> depuis l'URL avec <code>remote_src: true</code>, <code>file state=link</code>, <code>stat</code> de <code>current/index.html</code> et <code>assert</code> ; <code>rescue</code> : lien remis sur l'ancienne cible, puis <code>fail</code> ; <code>always</code> : <code>lineinfile</code> (ou <code>shell</code> avec <code>&gt;&gt;</code>) dans le journal."],
             "checks": [
                 ("taches $I/livraison.yml | jq -s -e 'any(.[]; has(\"block\") and has(\"rescue\") and has(\"always\"))' >/dev/null", "livraison.yml doit contenir un bloc avec block, rescue et always."),
                 ('for s in $(groupe web | tr , " "); do sur $s "rm -rf /var/www/vitrine /var/log/livraisons.log"; done; joue livraison.yml -e version=$LAB_V1 || recap', "Le déploiement de la 1re version échoue (voir le récapitulatif)."),
                 ('for s in web1 web2; do sur $s "test -L /var/www/vitrine/current && grep -q \\"Version $LAB_V1\\" /var/www/vitrine/current/index.html" || { echo "MSG:$s"; exit 1; }; done', "Après la 1re version, /var/www/vitrine/current n'est pas un lien vers la release déployée (index.html de cette version)."),
                 ('joue livraison.yml -e version=$LAB_V2 || recap', "Le déploiement de la 2e version échoue (voir le récapitulatif)."),
                 ('! joue livraison.yml -e version=$LAB_VC && echec_attendu', "Avec la version cassée (sans index.html), le jeu aurait dû échouer (le rattrapage ne doit pas cacher l'échec)."),
                 ('for s in web1 web2; do sur $s "test -L /var/www/vitrine/current && grep -q \\"Version $LAB_V2\\" /var/www/vitrine/current/index.html" || { echo "MSG:$s"; exit 1; }; done', "Après l'échec de la version cassée, current ne pointe plus sur la 2e version : le retour arrière n'a pas eu lieu."),
                 ('[ "$(sur web1 "grep -c . /var/log/livraisons.log")" = 3 ] && sur web1 "tail -1 /var/log/livraisons.log" | grep -qF "$LAB_VC"', "/var/log/livraisons.log de web1 doit compter exactement une ligne par tentative (3), la dernière citant la version cassée."),
             ]},
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    10: {
        "title": "Jour 10 — En conditions réelles : déployer sans couper",
        "description": "Diagnostiquer un incident, déployer progressivement, ne rejouer que ce qu'il faut. Compétences : méthode de diagnostic, serial, max_fail_percentage, tags, --list-tags, --start-at-task, --limit.",
        "lesson": """<h3>1. Méthode face à un incident</h3><ol><li><strong>Constater</strong> sans rien toucher : <code>ansible all -m ping</code>, des requêtes HTTP, <code>ansible-playbook site.yml --check --diff</code>.</li><li><strong>Lire</strong> le récapitulatif, puis la première tâche en échec, en entier ; <code>-vvv</code> si le message ne suffit pas.</li><li><strong>Corriger dans le code</strong> ce qui doit l'être (ce que le code ne décrit pas, il ne le répare pas), puis rejouer.</li><li><strong>Rejouer une seconde fois</strong> : <code>changed=0</code> prouve que tout est rentré dans l'ordre.</li></ol><div class="tip">Un serveur réinstallé change d'empreinte SSH : Ansible le déclare <code>UNREACHABLE</code>. Vérifiez l'empreinte avant de l'accepter, comme au jour 2.</div><h3>2. Déployer par lots : serial</h3><p>Par défaut, chaque tâche s'exécute sur tous les serveurs (5 à la fois, réglage <code>forks</code>) avant de passer à la suivante : une erreur dans le playbook touche tout le parc en même temps. <code>serial</code> découpe le play en <strong>lots</strong> : le play entier est joué sur le premier lot, puis sur le suivant…</p><pre>- name: Vitrines, une par une<br>  hosts: front<br>  serial: 1                    # ou 2, ou "30%", ou une liste : [1, "50%"]<br>  max_fail_percentage: 0       # s'arrêter dès qu'un serveur d'un lot échoue<br>  become: true<br>  roles: [vitrine]</pre><ul><li>Si <strong>tous</strong> les serveurs d'un lot échouent, le jeu s'arrête : les lots suivants gardent l'ancienne version.</li><li>Avec des lots de plusieurs serveurs, un seul échec ne suffit pas à arrêter le jeu : c'est le rôle de <code>max_fail_percentage</code> (ou <code>any_errors_fatal: true</code>).</li><li><code>pre_tasks</code> et <code>post_tasks</code> encadrent chaque lot : sortir le serveur de la répartition de charge, puis l'y remettre.</li></ul><figure class="schema"><svg viewBox="0 0 640 214" role="img" aria-label="Avec serial, le play est joué lot après lot ; max_fail_percentage arrête au premier échec"><defs><marker id="a10a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="pa" d="M0,0 L10,5 L0,10 z"/></marker><marker id="a10g" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="pt" d="M0,0 L10,5 L0,10 z"/></marker><marker id="a10w" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="pw" d="M0,0 L10,5 L0,10 z"/></marker></defs>
<text class="ttl" x="10" y="22">serial: 2</text><text class="t2" x="90" y="22">six vitrines, lots de deux</text>
<rect class="g" x="10" y="32" width="186" height="52" rx="8"/><text x="22" y="54">Lot 1 : réussi</text><text class="t2" x="22" y="72">vitrine1 ✓ vitrine2 ✓</text>
<rect class="w" x="226" y="32" width="186" height="52" rx="8"/><text x="238" y="54">Lot 2 : un échec</text><text class="t2" x="238" y="72">vitrine3 ✗ vitrine4 ✓</text>
<rect class="w" x="442" y="32" width="188" height="52" rx="8"/><text x="454" y="54">Lot 3 : joué quand même</text><text class="t2" x="454" y="72">vitrine5 ✓ vitrine6 ✓</text>
<path class="la" d="M196,58 L224,58" marker-end="url(#a10a)"/><path class="la" d="M412,58 L440,58" marker-end="url(#a10a)"/>
<text class="ttl" x="10" y="122">serial: 2</text><text class="mono" x="90" y="122">+ max_fail_percentage: 0</text>
<rect class="g" x="10" y="132" width="186" height="52" rx="8"/><text x="22" y="154">Lot 1 : réussi</text><text class="t2" x="22" y="172">vitrine1 ✓ vitrine2 ✓</text>
<rect class="r" x="226" y="132" width="186" height="52" rx="8"/><text x="238" y="154">Lot 2 : un échec</text><text class="t2" x="238" y="172">vitrine3 ✗ : le jeu s'arrête</text>
<rect class="b" x="442" y="132" width="188" height="52" rx="8"/><text x="454" y="154">Lot 3 : jamais joué</text><text class="t2" x="454" y="172">garde l'ancienne version</text>
<path class="la" d="M196,158 L224,158" marker-end="url(#a10a)"/><path class="ld" d="M412,158 L440,158"/>
<text class="t2" x="10" y="206">Sans max_fail_percentage, seul un lot entièrement en échec arrête le jeu.</text>
</svg><figcaption>Le play entier est joué sur un lot avant de passer au suivant. Avec max_fail_percentage: 0, le premier échec protège tous les lots restants.</figcaption></figure><h3>3. Ne jouer qu'une partie : les tags</h3><pre>    - name: Page d'accueil<br>      ansible.builtin.template:<br>        src: accueil.html.j2<br>        dest: /srv/vitrine/accueil.html<br>      tags: [contenu]</pre><pre>ansible-playbook site.yml --list-tags            # les étiquettes existantes<br>ansible-playbook site.yml --list-tasks --tags contenu   # ce qui serait joué<br>ansible-playbook site.yml --tags contenu         # seulement ces tâches<br>ansible-playbook site.yml --skip-tags contenu    # tout sauf elles</pre><ul><li>Un tag posé sur un rôle (dans <code>roles:</code>) ou sur un bloc s'applique à <strong>toutes</strong> ses tâches.</li><li>Deux tags spéciaux : <code>always</code> (toujours jouée, même avec <code>--tags</code>) et <code>never</code> (jamais, sauf si on la demande explicitement).</li><li>Attention : une tâche non étiquetée n'est pas jouée avec <code>--tags</code> ; si elle prépare quelque chose dont une tâche étiquetée a besoin, le jeu partiel peut échouer.</li></ul><h3>4. Reprendre après une panne</h3><pre>ansible-playbook site.yml --limit vitrine3 --start-at-task "Page d'accueil"   # reprend à cette tâche<br>ansible-playbook site.yml --step                                              # demande confirmation avant chaque tâche</pre>""",
        "setup": r'''
for s in web1 web2 db1; do serveur $s; done
docker inspect web3 >/dev/null 2>&1 && serveur web3
# A10.1 : quatre incidents tirés au hasard (la réinstallation d'un serveur, s'il y en a une, en dernier). La variante
# désigne un serveur épargné : « tous les serveurs » n'est jamais la bonne réponse
W=($(webs))
T=("${W[@]}" db1)
i=${LAB_VARIANTE_A10_1:-$RANDOM}
intact=${T[$((i % ${#T[@]}))]}
W=($(printf '%s\n' "${W[@]}" | grep -vx "$intact"))
autres=$(printf '%s\n' "${T[@]}" | grep -vx "$intact" | xargs)
pool="nginx port page droits stagiaire reinstalle"; [ "$intact" = db1 ] || pool="$pool redis"
touches=""
choix=$(shuf -n4 -e $pool)
for c in $(grep -v reinstalle <<<"$choix") $(grep reinstalle <<<"$choix"); do
  s=$(shuf -n1 -e "${W[@]}")
  case $c in
    nginx) sur $s "service nginx stop >/dev/null 2>&1" || true;;
    redis) s=db1; sur db1 "sed -i 's/^requirepass /# requirepass /' /etc/redis/redis.conf && service redis-server restart >/dev/null 2>&1" || true;;
    port) sur $s "sed -i 's/listen [0-9]*/listen 8081/' /etc/nginx/sites-available/default && nginx -s reload" || true;;
    page) sur $s "rm -f /var/www/html/index.html" || true;;
    droits) sur $s "chmod 000 /var/www/html" || true; emit DROITS "$s";;
    stagiaire) s=$(shuf -n1 -e $autres); sur $s "id stagiaire >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo stagiaire"; emit STAGIAIRE "$s";;
    reinstalle) reinstalle $s;;
  esac
  touches="$touches $s"
done
emit TOUCHES "$(printf '%s\n' $touches | sort -u | paste -sd,)"
''',
        "exercises": [
            {"id": "A10.1", "points": 8, "title": "L'incident du vendredi 17 h", "manual": True,
             "ticket": {"from": "sophie", "body": "Vendredi, 17 h, tout va mal : des clients voient des erreurs, l'API se plaint de Redis, et l'hébergeur a peut-être encore réinstallé un serveur sans prévenir. Remets l'infrastructure dans l'état décrit par le code, et complète le code pour ce qu'il ne décrivait pas encore. Puis écris dans <code>~/infra/reponses/incident.txt</code>, serveur par serveur, ce qui était cassé : je veux y voir le nom de chaque serveur touché, et d'aucun autre."},
             "desc": "Tous les serveurs sont joignables ; <code>site.yml</code> réussit, puis ne change plus rien ; chaque serveur web sert sa page sur 8080 ; Redis exige un mot de passe ; ce qui avait été ajouté à la main et que le code ne décrivait pas est désormais interdit par le code (le vérificateur le recrée avant de rejouer). <code>reponses/incident.txt</code> cite exactement les serveurs touchés par l'incident.",
             "hints": ["Constatez d'abord, sans rien corriger : qui répond à Ansible ? Qui sert sa page, avec quel code HTTP ? Redis demande-t-il un mot de passe ? Qui a un compte en trop dans le groupe <code>sudo</code> ? Notez tout. Puis demandez-vous, pour chaque symptôme, si le code le corrige… ou s'il faut compléter le code.", "<code>ansible all -m ping</code> ; <code>curl -s -o /dev/null -w '%{http_code}' http://web1:8080/</code> ; <code>ansible db1 -m command -a \"redis-cli ping\"</code> ; <code>ansible all -m getent -a \"database=group key=sudo\"</code> ; empreinte changée : comme au jour 2. Dans le code : un dossier décrit avec ses droits (<code>file</code>, <code>mode</code>), un compte décrit absent (<code>user</code>, <code>state: absent</code>)."],
             "checks": [
                 ('[ "$(grep -oE "web[0-9]|db1" $I/reponses/incident.txt 2>/dev/null | sort -u | paste -sd,)" = "$LAB_TOUCHES" ]', "reponses/incident.txt ne cite pas exactement les serveurs touchés par l'incident (ni plus, ni moins)."),
                 ('for s in $(groupe web | tr , " ") db1; do ssh_ok $s || { echo "MSG:$s"; exit 1; }; done', "Un serveur n'est pas joignable sans mot de passe (serveur réinstallé : empreinte et clé)."),
                 ('[ -z "$LAB_DROITS" ] || sur $LAB_DROITS "chmod 000 /var/www/html"; [ -z "$LAB_STAGIAIRE" ] || sur $LAB_STAGIAIRE "id stagiaire >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo stagiaire"; joue site.yml || recap', "site.yml échoue (voir le récapitulatif). (Le vérificateur a d'abord recréé ce que le code ne décrivait pas : droits du dossier du site, compte en trop.)"),
                 ('joue site.yml && rien_change || recap', "Rejoué, site.yml modifie encore quelque chose."),
                 ('for s in $(groupe web | tr , " "); do page $s:8080 | grep -q $s || { echo "MSG:$s"; exit 1; }; done', "Un serveur web ne sert pas sa page sur 8080 après site.yml : le code ne décrit pas tout (droits du dossier du site ?)."),
                 ('r=$(redis PING); [ "${r%% *}" = -NOAUTH ]', "Redis accepte encore les commandes sans mot de passe."),
                 ('[ -z "$LAB_STAGIAIRE" ] || ! sur $LAB_STAGIAIRE "id stagiaire"', "Le compte stagiaire (membre de sudo) existe encore après site.yml : le code doit l'interdire."),
             ]},
            {"id": "A10.2", "points": 6, "title": "Mise en production progressive", "manual": True,
             "ticket": {"from": "sophie", "body": "Pour les soldes, on déploie la version de l'application avec un nouveau playbook <code>deploiement.yml -e version=…</code>, qui écrit la version dans <code>/var/www/html/version.txt</code> sur les serveurs web. Mais un serveur à la fois, dans l'ordre de l'inventaire : si un serveur échoue, on s'arrête là, et les suivants gardent l'ancienne version."},
             "desc": "<code>deploiement.yml</code> écrit la version (seule, sur une ligne) dans <code>/var/www/html/version.txt</code> des serveurs web, un serveur à la fois ; si le déploiement échoue sur web2, les serveurs suivants de l'inventaire gardent l'ancienne version, les précédents ont la nouvelle.",
             "hints": ["Par défaut, chaque tâche s'exécute sur tous les serveurs avant la suivante. Un mot-clé du play change la taille des lots. Et qu'arrive-t-il quand un lot échoue ?", "<code>serial: 1</code> dans le play ; avec des lots plus grands, <code>max_fail_percentage: 0</code> arrête tout dès le premier échec. <code>copy</code> avec <code>content: \"{{ version }}\\n\"</code>."],
             "checks": [
                 ('for s in $(groupe web | tr , " "); do sur $s "rm -rf /var/www/html/version.txt"; done; joue deploiement.yml -e version=2025.1 || recap', "ansible-playbook deploiement.yml -e version=2025.1 échoue (voir le récapitulatif)."),
                 ('for s in $(groupe web | tr , " "); do [ "$(sur $s "cat /var/www/html/version.txt" | tr -d "[:space:]")" = 2025.1 ] || { echo "MSG:$s"; exit 1; }; done', "Après -e version=2025.1, /var/www/html/version.txt ne contient pas 2025.1 sur tous les serveurs web."),
                 ('sur web2 "rm -f /var/www/html/version.txt && mkdir /var/www/html/version.txt"; joue deploiement.yml -e version=2025.2; sur web2 "rmdir /var/www/html/version.txt"; echec_attendu || recap', "Le vérificateur a rendu impossible l'écriture de la version sur web2 : le jeu aurait dû échouer."),
                 (r'''avant=1; for s in $(etu "ansible-inventory --list" | jq -r '.web.hosts[]'); do [ $s = web2 ] && { avant=0; continue; }; v=$(sur $s "cat /var/www/html/version.txt" | tr -d '[:space:]'); if [ $avant = 1 ]; then [ "$v" = 2025.2 ]; else [ "$v" = 2025.1 ]; fi || { echo "MSG:$s : $v"; exit 1; }; done''', "Après l'échec sur web2, les serveurs placés avant lui dans l'inventaire doivent avoir la nouvelle version (2025.2), ceux placés après garder l'ancienne (2025.1)."),
                 ('joue deploiement.yml -e version=2025.2 || recap', "Relancé après la panne, deploiement.yml échoue (voir le récapitulatif)."),
             ]},
            {"id": "A10.3", "points": 4, "title": "Juste la page", "manual": True,
             "ticket": {"from": "thomas", "body": "Je modifie souvent le modèle de la page d'accueil. Je veux pouvoir ne déployer <strong>que</strong> la page, sans rien toucher d'autre sur les serveurs (surtout pas la configuration de nginx), avec <code>ansible-playbook site.yml --tags page</code>."},
             "desc": "<code>ansible-playbook site.yml --tags page</code> redéploie la page d'accueil et rien d'autre : une modification de la configuration de nginx reste en place (le vérificateur l'a faite exprès) ; un <code>site.yml</code> complet la corrige ensuite.",
             "hints": ["On peut étiqueter des tâches et ne lancer que celles qui portent une étiquette. Vérifiez ce qu'une étiquette sélectionne avant de lancer. Où poser l'étiquette pour qu'elle ne s'étende pas à tout le rôle ?", "<code>tags: [page]</code> sur la seule tâche du modèle de la page, dans le rôle ; <code>ansible-playbook site.yml --list-tasks --tags page</code> pour vérifier."],
             "checks": [
                 ('etu "ansible-playbook site.yml --list-tags" | grep -q "page"', "site.yml ne comporte pas d'étiquette page (ansible-playbook site.yml --list-tags)."),
                 ('sur web1 "echo casse > /var/www/html/index.html; echo \'# derive\' >> /etc/nginx/sites-available/default"; joue site.yml --tags page || recap', "ansible-playbook site.yml --tags page échoue (voir le récapitulatif)."),
                 ('page web1:8080 | grep -q web1', "Après --tags page, la page de web1 n'a pas été redéployée (le vérificateur l'avait cassée)."),
                 ('sur web1 "grep -q \'# derive\' /etc/nginx/sites-available/default"', "Avec --tags page, la configuration de nginx a aussi été redéployée : l'étiquette s'applique à trop de tâches."),
                 ('joue site.yml || recap', "ansible-playbook site.yml (complet) échoue ensuite (voir le récapitulatif)."),
                 ('! sur web1 "grep -q \'# derive\' /etc/nginx/sites-available/default"', "Un site.yml complet ne corrige pas la configuration de nginx de web1."),
             ]},
        ],
    },
}
