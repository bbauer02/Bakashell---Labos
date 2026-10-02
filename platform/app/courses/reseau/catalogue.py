"""Parcours « Réseau : du câble à la sécurité ».

Des modules courts pour démarrer (découverte, BTS 1re année), puis des chantiers plus longs, jusqu'à la sécurité
réseau. Chaque module installe un réseau d'entreprise réaliste : des machines Debian (postes, imprimante, switch…)
reliées par des câbles virtuels, qui tournent dans le moteur Docker interne du conteneur de l'étudiant (runtime
Sysbox en production).

L'étudiant travaille sur une « console » qui n'est pas branchée sur le réseau : `plan` affiche le schéma,
`connexion <machine>` ouvre un terminal root sur une machine (via sudo, liste fermée), `redemarrer <machine>` la
redémarre. Les câbles sont des paires veth branchées par /usr/local/sbin/lab-cablage (images/reseau), qui rebranche
tout au redémarrage ; au démarrage, chaque machine applique son /etc/network/interfaces (ifupdown), comme une Debian.

Les vérifications (en root sur la console) observent l'état réel du réseau de chaque machine avec les outils de la
console (nsenter dans son espace réseau) : root sur une machine, l'étudiant ne peut pas falsifier ce qu'elles voient.
"""

EXERCISES_VERSION = "2"

MENTOR = "lea"

SETUP_PRELUDE = r'''
set -e
H=/home/etudiant
emit() { echo "@$1=$2"; }
own() { chown -R etudiant:etudiant "$@"; }
# Attend le moteur Docker interne et l'image des machines (premier démarrage : environ 30 s)
for _ in $(seq 1 150); do [ -f /run/lab-ready ] && docker info >/dev/null 2>&1 && break; sleep 1; done
docker image inspect machine-reseau:3 >/dev/null 2>&1 || { echo "Le réseau n'est pas prêt" >&2; exit 1; }
R=/etc/reseau
mkdir -p $R
# reseau_neuf : retire toutes les machines et tous les câbles du module précédent. Par leur étiquette, pas par la
# liste : après une recréation de la console (nouvelle image), la liste est vide mais les machines existent encore
# dans le moteur Docker (volume conservé), et leurs noms bloqueraient la création des nouvelles.
reseau_neuf() {
  local m
  for m in $(docker ps -aq --filter label=reseau-lab); do docker rm -f "$m" >/dev/null 2>&1 || true; done
  : > $R/machines; : > $R/cables; : > $R/plan.txt
  chmod 644 $R/machines $R/cables $R/plan.txt
}
# machine <nom> [routeur] : une machine Debian, sans câble (lab-cablage les branche), qui redémarre avec la console.
# IPv6 désactivé : ses adresses fe80:: encombreraient « ip a » dans les premiers modules. Un routeur peut modifier
# les réglages réseau de son noyau (/proc/sys en écriture : net.ipv4.ip_forward), un simple poste non.
machine() {
  local extra=()
  [ "${2:-}" = routeur ] && extra=(--security-opt systempaths=unconfined)
  docker run -d --name "$1" --hostname "$1" --label reseau-lab --network none --cap-add NET_ADMIN "${extra[@]}" \
    --sysctl net.ipv6.conf.all.disable_ipv6=1 --sysctl net.ipv6.conf.default.disable_ipv6=1 \
    --restart unless-stopped --init machine-reseau:3 >/dev/null
  echo "$1" >> $R/machines
}
# fichier_sur <machine> <chemin> [droits] : écrit un fichier sur la machine (contenu lu sur l'entrée standard)
fichier_sur() { docker exec -i "$1" sh -c "cat > '$2'${3:+ && chmod $3 '$2'}"; }
# interfaces <machine> : son /etc/network/interfaces (lu sur l'entrée standard), appliqué à chaque démarrage
interfaces() { docker exec -i "$1" sh -c 'cat > /etc/network/interfaces'; }
# cable <machine A> <interface A> <MAC A|-> <machine B> <interface B> <MAC B|-> (côté « sw-… » : port du switch)
cable() { echo "$*" >> $R/cables; }
# mac <préfixe du fabricant> : adresse MAC de ce fabricant, fin tirée au hasard
mac() { printf '%s:%02x:%02x:%02x' "$1" $((RANDOM % 256)) $((RANDOM % 256)) $((RANDOM % 256)); }
cabler() { /usr/local/sbin/lab-cablage; }
'''

CHECK_PRELUDE = r'''
H=/home/etudiant
ans() { tr -d '[:space:]' < "$1" 2>/dev/null; }
pid() { docker inspect -f '{{if .State.Running}}{{.State.Pid}}{{end}}' "$1" 2>/dev/null; }
# sur <machine> <commande…> : lancée dans l'espace réseau de la machine, avec les outils de la console
sur() { local p; p=$(pid "$1"); [ -n "$p" ] || return 1; shift; nsenter -t "$p" -n -- "$@"; }
# ipv4 <machine> : adresses IPv4 de eth0, avec leur masque (« 192.168.10.12/24 »), une par ligne
ipv4() { sur "$1" ip -4 -o addr show dev eth0 2>/dev/null | awk '{print $4}'; }
# montre <machine> : ses adresses, en détail sous le message d'échec
montre() { echo "MSG:adresses de $1 : $(ipv4 "$1" | paste -sd' ' | sed 's/^$/aucune/')"; }
allumee() { sur "$1" ip -o link show dev eth0 2>/dev/null | grep -q '[<,]UP[,>]'; }
macde() { sur "$1" ip -o link show dev eth0 2>/dev/null | grep -o 'link/ether [0-9a-f:]*' | cut -d' ' -f2; }
# joint <machine> <adresse> : la machine reçoit une réponse au ping
joint() { sur "$1" ping -c 2 -i 0.3 -W 1 "$2" >/dev/null 2>&1; }
# fichier <machine> <chemin> : contenu d'un fichier de la machine
fichier() { docker exec "$1" cat "$2" 2>/dev/null; }
# passerelle <machine> : adresse de la passerelle de sa route par défaut (vide sans route par défaut)
passerelle() { sur "$1" ip -4 route show default 2>/dev/null | awk '/^default via/ {print $3; exit}'; }
montre_routes() { echo "MSG:routes de $1 : $(sur "$1" ip -4 route 2>/dev/null | paste -sd';' | sed 's/;/ ; /g; s/^$/aucune/')"; }
# transfert <machine> : 1 si la machine fait suivre les paquets d'un réseau à l'autre (routage activé)
transfert() { sur "$1" sysctl -n net.ipv4.ip_forward 2>/dev/null; }
# redemarree <machine> : l'étudiant a redémarré la machine depuis la console (commande redemarrer)
redemarree() { grep -q "^$1 " /var/lib/lab/redemarrages 2>/dev/null; }
# reboot_test <machine> : redémarre la machine comme le ferait l'étudiant, et attend qu'elle ait appliqué sa configuration
reboot_test() { docker restart -t 1 "$1" >/dev/null && /usr/local/sbin/lab-cablage && sleep 1; }
'''

# ─── Schémas des cours (SVG en ligne, styles .schema de lab.html) ─────────────────────────────────


def _fleches(i):
    return (f'<defs><marker id="rl{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            f'<path class="pa" d="M0,0 L10,5 L0,10 z"/></marker>'
            f'<marker id="rg{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            f'<path class="pt" d="M0,0 L10,5 L0,10 z"/></marker>'
            f'<marker id="rw{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            f'<path class="pw" d="M0,0 L10,5 L0,10 z"/></marker></defs>')


def _poste(x, nom, ip, role, port):
    """Une machine du schéma du magasin, reliée au port du switch."""
    c = x + 56
    return (f'<rect class="b" x="{x}" y="150" width="112" height="72" rx="8"/>'
            f'<text x="{x + 10}" y="172">{nom}</text><text class="mono" x="{x + 10}" y="192">{ip}</text>'
            f'<text class="t2" x="{x + 10}" y="210">{role}</text>'
            f'<path class="l" d="M{port},70 C{port},112 {c},106 {c},148"/>'
            f'<rect class="b" x="{port - 5}" y="62" width="10" height="8" rx="1"/>')


SCHEMA_MAGASIN = (
    '<figure class="schema"><svg viewBox="0 0 640 250" role="img" aria-label="Le switch du magasin relie cinq machines">'
    '<rect class="a" x="200" y="12" width="240" height="50" rx="8"/>'
    '<text class="ttl" x="214" y="34">sw-annecy</text><text class="t2" x="214" y="52">switch : relie les machines du magasin</text>'
    '<rect class="w" x="480" y="12" width="152" height="50" rx="8"/>'
    '<text x="494" y="34">console (vous)</text><text class="mono" x="494" y="52">connexion caisse</text>'
    + _poste(8, "caisse", "192.168.10.11", "poste de caisse", 232)
    + _poste(136, "bureau", "192.168.10.12", "poste du bureau", 276)
    + _poste(264, "imprimante", "192.168.10.50", "imprimante réseau", 320)
    + _poste(392, "borne", "192.168.10.30", "borne de commande", 364)
    + _poste(520, "portable-julien", "192.168.10.40", "PC du stagiaire", 408)
    + '<text class="t2" x="8" y="244">Réseau local 192.168.10.0/24 : les adresses prévues par le plan d\'installation.</text>'
    '</svg><figcaption>Toutes les machines du magasin sont branchées sur le même switch : c\'est un <strong>réseau local</strong> (LAN). '
    'La console, elle, n\'est pas branchée dessus : <code>connexion</code> vous ouvre un terminal sur la machine de votre choix.</figcaption></figure>'
)

SCHEMA_IP_A = (
    f'<figure class="schema"><svg viewBox="0 0 640 214" role="img" aria-label="Lecture de la sortie de ip a">{_fleches(1)}'
    '<rect class="b" x="8" y="8" width="380" height="198" rx="8"/>'
    '<text class="mono" x="20" y="32">root@vitrine:~# ip a</text>'
    '<text class="mono" x="20" y="58">1: <tspan class="ttl">lo</tspan>: &lt;LOOPBACK,UP,LOWER_UP&gt;</text>'
    '<text class="mono" x="44" y="76">inet 127.0.0.1/8 scope host lo</text>'
    '<text class="mono" x="20" y="106">2: <tspan class="ttl">eth0</tspan>: &lt;BROADCAST,UP&gt; state <tspan class="ttl">UP</tspan></text>'
    '<text class="mono" x="44" y="140">link/ether <tspan class="ttl">3c:52:82:4a:10:7e</tspan></text>'
    '<text class="mono" x="44" y="174">inet <tspan class="ttl">172.16.5.21/24</tspan> scope global eth0</text>'
    '<rect class="b" x="420" y="38" width="212" height="30" rx="6"/><text x="432" y="58">lo : la machine elle-même</text>'
    '<rect class="a" x="420" y="76" width="212" height="40" rx="6"/><text x="432" y="93">eth0 : la carte réseau</text>'
    '<text class="t2" x="432" y="108">state UP : allumée · DOWN : éteinte</text>'
    '<rect class="w" x="420" y="122" width="212" height="38" rx="6"/>'
    '<text x="432" y="139">link/ether : l\'adresse MAC</text><text class="t2" x="432" y="153">fixée en usine, propre à la carte</text>'
    '<rect class="g" x="420" y="166" width="212" height="40" rx="6"/>'
    '<text x="432" y="183">inet : l\'adresse IP / masque</text><text class="t2" x="432" y="198">choisie par l\'administrateur</text>'
    '<path class="l" d="M300,54 L418,53" marker-end="url(#rg1)"/>'
    '<path class="l" d="M372,102 L418,96" marker-end="url(#rg1)"/>'
    '<path class="l" d="M300,136 L418,141" marker-end="url(#rg1)"/>'
    '<path class="l" d="M312,170 L418,184" marker-end="url(#rg1)"/>'
    '</svg><figcaption><code>ip a</code> sur une machine d\'un autre magasin (Chamonix) : une carte réseau par bloc, '
    'et pour chacune son état, son adresse MAC et son adresse IP.</figcaption></figure>'
)


def _x(adresse):
    """Position de l'adresse 172.16.5.<adresse> sur la règle du schéma du masque (de .0 à .255)."""
    return round(20 + 440 * (adresse + 0.5) / 256, 1)


def _cas(y, titre, etendue, regle, verdict, detail, ok):
    """Un cas du schéma du masque : ce que la vitrine considère comme son réseau, et le verdict pour le serveur."""
    return (f'<rect class="b" x="8" y="{y}" width="624" height="104" rx="8"/>'
            f'<text class="ttl" x="20" y="{y + 22}">{titre}</text>'
            f'<text class="t2" x="20" y="{y + 40}">{etendue}</text>'
            + regle
            + f'<circle class="a" cx="{_x(20)}" cy="{y + 59}" r="6"/><circle class="w" cx="{_x(70)}" cy="{y + 59}" r="6"/>'
            f'<text class="t2" x="{_x(20)}" y="{y + 86}" text-anchor="middle">serveur .20</text>'
            f'<text class="t2" x="{_x(70)}" y="{y + 86}" text-anchor="middle">vitrine .70</text>'
            f'<text class="t2" x="20" y="{y + 98}">.0</text><text class="t2" x="460" y="{y + 98}" text-anchor="end">.255</text>'
            f'<rect class="{"g" if ok else "r"}" x="468" y="{y + 30}" width="160" height="50" rx="6"/>'
            f'<text x="478" y="{y + 51}">{verdict}</text><text class="t2" x="478" y="{y + 69}">{detail}</text>')


SCHEMA_MASQUE = (
    '<figure class="schema"><svg viewBox="0 0 640 100" role="img" aria-label="Une adresse IP : partie réseau et partie machine">'
    '<rect class="g" x="150" y="10" width="190" height="40" rx="6"/><text class="ttl" x="214" y="35">172.16.5</text>'
    '<rect class="a" x="346" y="10" width="110" height="40" rx="6"/><text class="ttl" x="388" y="35">.70</text>'
    '<text class="t2" x="160" y="66">partie réseau (/24 : 24 bits)</text><text class="t2" x="356" y="66">partie machine</text>'
    '<text class="t2" x="150" y="88">Masque /24 = 255.255.255.0 : même réseau = mêmes trois premiers nombres.</text>'
    '</svg></figure>'
    '<figure class="schema"><svg viewBox="0 0 640 262" role="img" aria-label="Avec /24 le serveur est sur le réseau de la vitrine, avec /28 il ne l\'est plus">'
    '<text x="8" y="18">La vitrine (172.16.5.70) veut joindre le serveur (172.16.5.20). Est-il sur son réseau ?</text>'
    + _cas(34, "Avec le masque /24 (255.255.255.0)", "réseau de la vitrine : de 172.16.5.0 à 172.16.5.255 (256 adresses)",
           '<rect class="g" x="20" y="86" width="440" height="14" rx="3"/>',
           "✓ même réseau", "elle lui parle directement", True)
    + _cas(152, "Avec le masque /28 (255.255.255.240)", "réseau de la vitrine : de 172.16.5.64 à 172.16.5.79 (16 adresses)",
           f'<rect class="r" x="20" y="204" width="440" height="14" rx="3"/>'
           f'<rect class="g" x="{_x(64) - 0.9}" y="204" width="{round(440 * 16 / 256, 1)}" height="14"/>',
           "✗ autre réseau", "« Network is unreachable »", False)
    + '</svg><figcaption>En vert, les adresses que la vitrine considère comme <strong>son</strong> réseau, d\'après son masque. '
    'En /28, ce réseau ne compte plus que 16 adresses : le serveur (.20) n\'en fait pas partie, et la vitrine ne sait pas '
    'où lui envoyer ses messages.</figcaption></figure>'
)

SCHEMA_ARP = (
    f'<figure class="schema"><svg viewBox="0 0 640 214" role="img" aria-label="Une requête ARP et deux réponses : un conflit d\'adresses">{_fleches(2)}'
    '<text class="t2" x="205" y="74" text-anchor="middle">« Qui a 172.16.5.20 ? »</text>'
    '<rect class="b" x="10" y="82" width="150" height="56" rx="8"/><text x="22" y="104">poste A</text><text class="mono" x="22" y="124">172.16.5.30</text>'
    '<rect class="a" x="250" y="88" width="100" height="44" rx="8"/><text x="268" y="115">switch</text>'
    '<path class="la" d="M160,104 L248,104" marker-end="url(#rl2)"/>'
    '<path class="la" d="M350,100 C380,100 380,52 408,52" marker-end="url(#rl2)"/>'
    '<path class="la" d="M350,120 C380,120 380,168 408,168" marker-end="url(#rl2)"/>'
    '<text class="t2" x="300" y="150" text-anchor="middle">diffusé à tous</text>'
    '<rect class="g" x="410" y="24" width="222" height="56" rx="8"/><text x="422" y="46">serveur  172.16.5.20</text>'
    '<text class="mono" x="422" y="68">« moi ! 3c:52:82:4a:10:7e »</text>'
    '<rect class="r" x="410" y="140" width="222" height="56" rx="8"/><text x="422" y="162">intrus  172.16.5.20</text>'
    '<text class="mono" x="422" y="184">« moi ! 00:21:5a:9c:01:33 »</text>'
    '<text class="t2" x="10" y="160">deux réponses : le poste garde</text><text class="t2" x="10" y="176">la dernière arrivée…</text>'
    '</svg><figcaption>Pour parler à une adresse IP, une machine demande à tout le réseau quelle carte la porte (ARP). '
    'Si deux machines ont la même adresse IP, les deux répondent : c\'est un <strong>conflit d\'adresses</strong>.</figcaption></figure>'
)

SCHEMA_PERMANENT = (
    f'<figure class="schema"><svg viewBox="0 0 640 214" role="img" aria-label="Configuration en cours et configuration au démarrage">{_fleches(3)}'
    '<rect class="w" x="10" y="14" width="260" height="70" rx="8"/>'
    '<text class="mono" x="22" y="38">ip addr add …/24 dev eth0</text>'
    '<text x="22" y="58">effet immédiat…</text><text class="t2" x="22" y="74">… oublié au prochain démarrage</text>'
    '<rect class="g" x="10" y="112" width="260" height="92" rx="8"/>'
    '<text class="mono" x="22" y="134">/etc/network/interfaces</text>'
    '<text class="mono" x="22" y="154">auto eth0</text><text class="mono" x="22" y="170">iface eth0 inet static</text>'
    '<text class="mono" x="48" y="186">address 172.16.5.30/24</text>'
    '<rect class="a" x="360" y="70" width="160" height="70" rx="8"/>'
    '<text class="ttl" x="374" y="96">configuration</text><text class="ttl" x="374" y="114">en cours</text><text class="t2" x="374" y="130">en mémoire</text>'
    '<path class="la" d="M270,50 C320,50 320,90 358,92" marker-end="url(#rl3)"/>'
    '<path class="l" d="M270,158 C320,158 320,122 358,120" marker-end="url(#rg3)"/>'
    '<text class="t2" x="282" y="190">au démarrage : ifup -a</text>'
    '<rect class="r" x="552" y="76" width="80" height="58" rx="8"/><text x="562" y="100">éteinte</text><text class="t2" x="562" y="118">mémoire vide</text>'
    '<path class="ld" d="M520,105 L550,105" marker-end="url(#rw3)"/>'
    '</svg><figcaption><code>ip</code> modifie la configuration en cours, perdue à l\'extinction. Ce qui doit survivre à un '
    'redémarrage s\'écrit dans <code>/etc/network/interfaces</code>, que la machine relit à chaque démarrage.</figcaption></figure>'
)




def _machine_box(x, y, nom, ip, w=120, cls="b"):
    """Une machine d'un schéma : nom et adresse."""
    return (f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="50" rx="8"/>'
            f'<text x="{x + 10}" y="{y + 21}">{nom}</text><text class="mono" x="{x + 10}" y="{y + 39}">{ip}</text>')


# ─── Module 0 : prise en main ────────────────────────────────────────────────────────────────

SCHEMA_CONSOLE = (
    f'<figure class="schema"><svg viewBox="0 0 640 240" role="img" aria-label="La console ouvre un terminal sur chaque machine">{_fleches(4)}'
    '<rect class="w" x="10" y="84" width="190" height="62" rx="8"/>'
    '<text x="22" y="108">console (vous)</text><text class="mono" x="22" y="130">etudiant@console:~$</text>'
    '<rect class="a" x="390" y="14" width="160" height="44" rx="8"/><text class="ttl" x="404" y="41">sw-formation</text>'
    + _machine_box(330, 160, "poste1", "192.168.50.1") + _machine_box(490, 160, "poste2", "192.168.50.2")
    + '<path class="l" d="M440,58 C440,110 390,110 390,158"/><path class="l" d="M500,58 C500,110 550,110 550,158"/>'
    '<path class="ld" d="M200,108 C270,108 280,185 328,185" marker-end="url(#rw4)"/>'
    '<path class="ld" d="M200,124 C250,124 250,226 420,226 C470,226 500,226 520,212" marker-end="url(#rw4)"/>'
    '<text class="t2" x="212" y="96">onglet ou connexion</text>'
    '</svg><figcaption>La console n\'est pas branchée sur le réseau : c\'est votre poste de travail. Un onglet (ou la commande '
    '<code>connexion</code>) vous ouvre un terminal <strong>directement</strong> sur une machine, comme si vous étiez devant elle.</figcaption></figure>'
)

SCHEMA_INVITE = (
    '<figure class="schema"><svg viewBox="0 0 640 196" role="img" aria-label="Lecture de l\'invite du terminal">'
    '<rect class="b" x="10" y="10" width="620" height="176" rx="8"/>'
    '<text class="mono" x="40" y="54" style="font-size:20px"><tspan class="ttl">etudiant</tspan>@<tspan class="ttl">console</tspan>:<tspan class="ttl">~</tspan>$</text>'
    '<path class="l" d="M40,64 L135,64"/><text class="t2" x="40" y="80">qui : votre compte</text>'
    '<path class="l" d="M148,64 L230,64"/><text class="t2" x="150" y="98">sur quelle machine</text>'
    '<path class="l" d="M242,64 L254,64"/><text class="t2" x="262" y="80">où : le dossier (~ = dossier personnel)</text>'
    '<text class="mono" x="40" y="146" style="font-size:20px"><tspan class="ttl">root</tspan>@<tspan class="ttl">poste1</tspan>:~<tspan class="ttl">#</tspan></text>'
    '<path class="l" d="M40,156 L84,156"/><text class="t2" x="40" y="172">root : l\'administrateur</text>'
    '<text class="t2" x="330" y="128">$ : compte ordinaire</text><text class="t2" x="330" y="148"># : administrateur (root), tout est permis</text>'
    '<text class="t2" x="330" y="168">couleur : chaque machine a la sienne</text>'
    '</svg><figcaption>Lisez l\'invite avant chaque commande : elle dit <strong>qui</strong> vous êtes, <strong>sur quelle '
    'machine</strong> et <strong>dans quel dossier</strong>.</figcaption></figure>'
)

INTRO = """<div class="scenario"><h3>Le réseau de Cimes &amp; Sentiers</h3><p>Léa, l'admin système senior, s'occupe aussi du réseau de l'entreprise : les magasins, le siège, la boutique en ligne. Elle vous forme. Avant de vous confier un vrai magasin, elle vous installe sur une <strong>maquette de formation</strong> : un switch et deux postes, sans aucune panne, pour apprendre à vous servir des outils.</p><p>Chaque module de ce parcours est court : quelques tickets, une notion à la fois. Prenez le temps de lire le cours : tout ce qui est demandé y est montré.</p></div>"""

MODULE_0 = {
    "title": "Module 0 — Prise en main",
    "description": "Apprendre à se servir de la console et des machines, sans aucune panne. Compétences : lire l'invite, changer de machine (onglets, connexion), ls, cat, echo, nano, redémarrer une machine.",
    "lesson": INTRO + """<h3>La console et les machines</h3>""" + SCHEMA_CONSOLE + """<p>Au-dessus du terminal, un <strong>onglet par machine</strong> : <em>console</em>, puis les machines du réseau. Un clic, et vous travaillez sur la machine choisie. Chaque machine a sa couleur, la même dans son onglet et dans son invite.</p><pre>plan                      # (sur la console) le schéma du réseau et les adresses prévues
connexion poste1          # (sur la console) même effet qu'un clic sur l'onglet poste1
exit                      # (sur une machine) referme sa session : retour à la console</pre><h3>Lire l'invite</h3>""" + SCHEMA_INVITE + """<div class="tip">L'erreur la plus fréquente, même chez les professionnels : taper une commande sur la <strong>mauvaise machine</strong>. Un coup d'œil à l'invite avant d'appuyer sur Entrée évite bien des soucis.</div><h3>Premières commandes</h3><table class="lesson-table"><tr><th>Commande</th><th>Ce qu'elle fait</th></tr><tr><td><code>ls</code></td><td>liste les fichiers du dossier courant</td></tr><tr><td><code>cat notes.txt</code></td><td>affiche le contenu d'un fichier</td></tr><tr><td><code>echo "Camille" &gt; prenom.txt</code></td><td>écrit un texte dans un fichier (le crée, ou remplace son contenu)</td></tr><tr><td><code>nano notes.txt</code></td><td>ouvre un fichier dans un éditeur de texte simple</td></tr><tr><td><code>clear</code></td><td>efface l'écran</td></tr></table><p>Trois réflexes qui font gagner du temps :</p><ul><li><strong>↑</strong> (flèche du haut) : rappelle les commandes précédentes, pour les relancer ou les corriger ;</li><li><strong>Tab</strong> : complète un nom de commande ou de fichier commencé ;</li><li><strong>Ctrl+C</strong> : arrête une commande qui ne s'arrête pas toute seule (un <code>ping</code> sans <code>-c</code>, par exemple).</li></ul><h3>nano en 30 secondes</h3><p>On tape le texte directement. En bas de l'écran, <code>^</code> veut dire <strong>Ctrl</strong> :</p><ul><li><strong>Ctrl+O</strong> puis <strong>Entrée</strong> : enregistrer (<em>Write Out</em>) ;</li><li><strong>Ctrl+X</strong> : quitter (nano demande d'enregistrer si besoin : <strong>O</strong> pour oui) ;</li><li>les flèches déplacent le curseur ; la souris ne sert pas.</li></ul><h3>Redémarrer une machine</h3><pre>redemarrer poste2         # (sur la console) éteint puis rallume poste2</pre><p>Les <strong>fichiers</strong> d'une machine survivent à un redémarrage. Ce n'est pas le cas de tous les réglages : vous verrez au module 1 lesquels disparaissent, et comment les rendre permanents.</p>""",
    "setup": r'''
reseau_neuf
machine sw-formation
for m in poste1 poste2; do machine $m; done
LO='auto lo
iface lo inet loopback
'
interfaces poste1 <<EOF
$LO
auto eth0
iface eth0 inet static
    address 192.168.50.1
    netmask 255.255.255.0
EOF
interfaces poste2 <<EOF
$LO
auto eth0
iface eth0 inet static
    address 192.168.50.2
    netmask 255.255.255.0
EOF
cable poste1 eth0 $(mac 3c:52:82) sw-formation port1 -
cable poste2 eth0 $(mac 3c:52:82) sw-formation port2 -
cabler
# R0.3 : un message de Marc sur l'une des deux machines (tirée au sort), avec un code propre à chaque étudiant
code=$(printf 'MARC-%04d' $((RANDOM % 10000)))
cache=$(shuf -n1 -e poste1 poste2); autre=poste1; [ "$cache" = poste1 ] && autre=poste2
fichier_sur $cache /root/message-de-marc.txt <<EOF
Message de Marc, pour la personne qui me remplacera :
le code de la baie de brassage est $code.
Bon courage, et lis toujours l'invite avant de taper une commande !
EOF
fichier_sur $autre /root/lisez-moi.txt <<'EOF'
Rien d'intéressant ici. Le message de Marc est sur l'autre machine.
EOF
emit CODE "$code"
cat > $R/plan.txt <<'EOF'

  Maquette de formation — réseau 192.168.50.0/24

  sw-formation (switch)
   ├─ port1 ── poste1   192.168.50.1
   └─ port2 ── poste2   192.168.50.2

  Onglets au-dessus du terminal, ou connexion <machine> : travailler sur une machine.

EOF
mkdir -p $H/reponses
own $H/reponses
''',
    "exercises": [
        {"id": "R0.1", "points": 2, "title": "Signer le registre",
         "ticket": {"from": "lea", "body": "Bienvenue ! Premier exercice : prouve-moi que tu sais travailler <strong>sur une machine</strong>, pas seulement sur ta console. Sur <code>poste1</code>, crée le fichier <code>/root/signature.txt</code> avec ton prénom dedans."},
         "desc": "Sur <code>poste1</code> (et pas sur la console), le fichier <code>/root/signature.txt</code> existe et contient votre prénom.",
         "hints": ["Passez d'abord sur poste1 : son onglet, ou <code>connexion poste1</code>. L'invite doit devenir <code>root@poste1</code>. Le cours montre une commande qui écrit un texte dans un fichier.",
                   "Sur poste1 : <code>echo \"Camille\" &gt; /root/signature.txt</code> (avec votre prénom), puis <code>cat /root/signature.txt</code> pour vérifier."],
         "checks": [
             ('[ -n "$(fichier poste1 /root/signature.txt | tr -d "[:space:]")" ] || { [ -e $H/signature.txt ] && echo "MSG:un fichier signature.txt existe sur la console : il fallait le créer sur poste1"; exit 1; }',
              "Le fichier /root/signature.txt n'existe pas sur poste1, ou il est vide."),
         ]},
        {"id": "R0.2", "points": 2, "title": "Le carnet de bord",
         "ticket": {"from": "sophie", "body": "Bonjour ! Ici, chacun tient un carnet de bord. Sur ta <strong>console</strong>, crée avec <code>nano</code> le fichier <code>~/carnet.txt</code> : au moins trois lignes, une par commande que tu as découverte aujourd'hui, avec à quoi elle sert."},
         "desc": "Sur la console, le fichier <code>~/carnet.txt</code> contient au moins trois lignes non vides.",
         "hints": ["Revenez sur la console (son onglet). <code>nano ~/carnet.txt</code> ouvre le fichier, même s'il n'existe pas encore. La section « nano en 30 secondes » du cours dit comment enregistrer.",
                   "Tapez trois lignes (par exemple <code>plan : affiche le schéma du réseau</code>), puis <strong>Ctrl+O</strong>, <strong>Entrée</strong>, et <strong>Ctrl+X</strong>. Vérifiez avec <code>cat ~/carnet.txt</code>."],
         "checks": [
             ('[ -f $H/carnet.txt ]', "Le fichier ~/carnet.txt n'existe pas sur la console (nano ne crée le fichier qu'à l'enregistrement : Ctrl+O, puis Entrée)."),
             ('n=$(grep -c "[^[:space:]]" $H/carnet.txt); [ "$n" -ge 3 ] || { echo "MSG:$n ligne(s) non vide(s)"; exit 1; }', "~/carnet.txt doit contenir au moins trois lignes non vides."),
         ]},
        {"id": "R0.3", "points": 3, "title": "Le message de Marc", "manual": True,
         "ticket": {"from": "julien", "body": "Salut ! Il paraît que Marc, ton prédécesseur, a laissé un message sur l'une des deux machines de la maquette, dans le dossier de root. Il contient un code. Tu peux le recopier dans <code>~/reponses/code.txt</code>, sur la console ? Moi je n'ai pas trouvé 😅"},
         "desc": "Sur la console, <code>~/reponses/code.txt</code> contient le code du message de Marc (de la forme <code>MARC-1234</code>).",
         "hints": ["Sur chaque machine, <code>ls</code> montre les fichiers du dossier de root, et <code>cat</code> affiche leur contenu. Puis revenez sur la console pour écrire la réponse.",
                   "Sur poste1 puis poste2 : <code>ls</code>, puis <code>cat message-de-marc.txt</code> là où il se trouve. Sur la console : <code>echo MARC-1234 &gt; ~/reponses/code.txt</code> (avec le vrai code)."],
         "checks": [
             ('[ -s $H/reponses/code.txt ]', "~/reponses/code.txt n'existe pas sur la console, ou il est vide."),
             ('[ "$(ans $H/reponses/code.txt)" = "$LAB_CODE" ] || { echo "MSG:code saisi : $(ans $H/reponses/code.txt)"; exit 1; }', "Ce n'est pas le code du message de Marc."),
         ]},
        {"id": "R0.4", "points": 2, "title": "Redémarrer sans paniquer",
         "ticket": {"from": "lea", "body": "Dernière chose pour aujourd'hui : redémarre <code>poste2</code> depuis la console. Puis va voir si les fichiers de poste2 sont toujours là. Ça te servira dès le module suivant."},
         "desc": "<code>poste2</code> a été redémarré depuis la console (commande <code>redemarrer</code>).",
         "hints": ["La commande se lance sur la console, pas sur la machine : le cours, section « Redémarrer une machine ».",
                   "Sur la console : <code>redemarrer poste2</code>. Puis, sur poste2 : <code>ls</code>."],
         "checks": [
             ('redemarree poste2', "poste2 n'a pas encore été redémarré depuis la console (commande redemarrer, lancée sur la console)."),
         ]},
    ],
}

SCENARIO_ANNECY = """<div class="scenario"><h3>Le magasin d'Annecy</h3><p>Cimes &amp; Sentiers ouvre un nouveau magasin à <strong>Annecy</strong>, lundi. Julien, le stagiaire, a installé le réseau ce week-end : un switch, deux postes, une imprimante, une borne de commande pour les clients… et son propre portable. Léa vous confie la mise en route, à distance, depuis votre console.</p></div>"""

# ─── Module 2 : la passerelle ────────────────────────────────────────────────────────────────

SCHEMA_DEUX_RESEAUX = (
    '<figure class="schema"><svg viewBox="0 0 640 250" role="img" aria-label="La box relie le réseau du magasin et le réseau du siège">'
    '<rect class="g" x="8" y="8" width="268" height="234" rx="10" style="fill-opacity:.35"/>'
    '<text class="ttl" x="20" y="30">Magasin d\'Annecy</text><text class="mono" x="20" y="48">192.168.10.0/24</text>'
    '<rect class="w" x="364" y="8" width="268" height="234" rx="10" style="fill-opacity:.35"/>'
    '<text class="ttl" x="376" y="30">Siège</text><text class="mono" x="376" y="48">10.20.0.0/24</text>'
    + _machine_box(20, 70, "caisse", "192.168.10.11") + _machine_box(20, 150, "bureau", "192.168.10.12")
    + _machine_box(500, 110, "srv-stock", "10.20.0.10")
    + '<rect class="a" x="232" y="96" width="176" height="76" rx="10"/>'
    '<text class="ttl" x="246" y="118">box-annecy (routeur)</text>'
    '<text class="mono" x="246" y="140">eth0 192.168.10.254</text><text class="mono" x="246" y="158">eth1 10.20.0.254</text>'
    '<path class="l" d="M140,95 L230,120"/><path class="l" d="M140,175 L230,150"/><path class="l" d="M408,134 L498,134"/>'
    '</svg><figcaption>Un <strong>routeur</strong> appartient aux deux réseaux à la fois : une adresse dans chacun. C\'est la '
    '<strong>passerelle</strong> : la porte de sortie du magasin vers le siège.</figcaption></figure>'
)

SCHEMA_DECISION = (
    f'<figure class="schema"><svg viewBox="0 0 640 210" role="img" aria-label="Comment une machine décide où envoyer un paquet">{_fleches(5)}'
    '<rect class="b" x="10" y="80" width="140" height="50" rx="8"/><text x="22" y="102">un paquet pour</text><text class="mono" x="22" y="120">10.20.0.10</text>'
    '<rect class="a" x="190" y="72" width="170" height="66" rx="8"/><text x="204" y="96">la destination est-elle</text><text x="204" y="116">sur l\'un de mes réseaux ?</text>'
    '<rect class="g" x="430" y="10" width="200" height="50" rx="8"/><text x="442" y="32">oui : envoi direct</text><text class="t2" x="442" y="49">(ARP, comme au module 1)</text>'
    '<rect class="a" x="400" y="80" width="230" height="50" rx="8"/><text x="412" y="102">non : ai-je une route par défaut ?</text><text class="t2" x="412" y="119">ip route : la ligne « default via … »</text>'
    '<rect class="g" x="250" y="160" width="180" height="44" rx="8"/><text x="262" y="186">oui : à la passerelle</text>'
    '<rect class="r" x="450" y="160" width="180" height="44" rx="8"/><text x="462" y="180">non : erreur</text><text class="t2" x="462" y="196">Network is unreachable</text>'
    '<path class="la" d="M150,105 L188,105" marker-end="url(#rl5)"/>'
    '<path class="l" d="M360,92 C395,92 395,35 428,35" marker-end="url(#rg5)"/>'
    '<path class="l" d="M360,110 L398,108" marker-end="url(#rg5)"/>'
    '<path class="l" d="M480,130 C480,150 380,145 360,158" marker-end="url(#rg5)"/>'
    '<path class="l" d="M560,130 L560,158" marker-end="url(#rg5)"/>'
    '</svg><figcaption>Toute machine se pose cette question avant d\'envoyer un paquet. La <strong>route par défaut</strong> '
    'dit à qui confier ce qui n\'est pas sur ses propres réseaux.</figcaption></figure>'
)

SCHEMA_RETOUR = (
    f'<figure class="schema"><svg viewBox="0 0 640 180" role="img" aria-label="La réponse doit pouvoir revenir">{_fleches(6)}'
    '<text class="t2" x="20" y="22">aller : la vitrine connaît sa passerelle →</text>'
    '<text class="t2" x="400" y="22">← retour : et le serveur, connaît-il la sienne ?</text>'
    + _machine_box(10, 40, "vitrine", "172.16.5.30", w=130)
    + '<rect class="a" x="250" y="32" width="140" height="66" rx="8"/><text class="ttl" x="262" y="56">routeur</text>'
    '<text class="mono" x="262" y="74">172.16.5.254</text><text class="mono" x="262" y="90">10.30.0.254</text>'
    + _machine_box(500, 40, "serveur", "10.30.0.20", w=130)
    + '<path class="la" d="M140,56 L248,56" marker-end="url(#rl6)"/><path class="la" d="M390,56 L498,56" marker-end="url(#rl6)"/>'
    '<path class="ld" d="M498,80 L392,80" marker-end="url(#rw6)"/>'
    '<rect class="r" x="360" y="126" width="270" height="44" rx="8"/><text x="372" y="146">serveur sans route vers 172.16.5.0/24 :</text>'
    '<text class="t2" x="372" y="163">la réponse ne part jamais, le ping reste muet</text>'
    '<path class="ld" d="M560,92 L560,124"/>'
    '</svg><figcaption>Un échange réseau est un <strong>aller-retour</strong>. Chaque machine du trajet, dans un sens comme '
    'dans l\'autre, doit savoir où envoyer le paquet.</figcaption></figure>'
)

SCENARIO_SIEGE = """<div class="scenario"><h3>Relier le magasin au siège</h3><p>Le magasin d'Annecy fonctionne : bravo ! Mais il vit encore en vase clos. Le <strong>serveur de stock</strong> est au siège, sur un autre réseau, et la caisse doit l'interroger à chaque vente. L'opérateur a installé une box, <code>box-annecy</code>, qui relie les deux réseaux. Sur le papier, tout est branché. En pratique…</p></div>"""

MODULE_2 = {
    "title": "Module 2 — Sortir du magasin : la passerelle",
    "description": "Relier deux réseaux par un routeur. Compétences : table de routage, route par défaut, passerelle, routage sur le routeur (ip_forward), aller et retour, traceroute, configuration permanente (gateway, sysctl.conf).",
    "lesson": SCENARIO_SIEGE + """<h3>Deux réseaux, un routeur</h3>""" + SCHEMA_DEUX_RESEAUX + """<p>Au module 1, toutes les machines étaient sur le <strong>même réseau</strong> : elles se parlaient directement. Le serveur de stock, lui, est sur un autre réseau. Pour le joindre, il faut passer par un <strong>routeur</strong> : ici, la box. Pour les machines du magasin, c'est leur <strong>passerelle</strong>.</p><h3>La table de routage</h3>""" + SCHEMA_DECISION + """<p>La commande <code>ip route</code> affiche la table de routage. Exemple d'un poste du magasin de Chamonix :</p><pre>root@vitrine:~# ip route
default via 172.16.5.254 dev eth0                      # tout le reste : à la passerelle 172.16.5.254
172.16.5.0/24 dev eth0 proto kernel scope link src 172.16.5.30   # mon réseau : envoi direct</pre><p>La deuxième ligne apparaît toute seule, avec l'adresse et son masque. La première, la <strong>route par défaut</strong>, c'est à vous de la donner.</p><h3>Configurer la passerelle</h3><pre>ip route add default via 172.16.5.254        # ajouter la route par défaut
ip route del default                         # la retirer
ip route replace default via 172.16.5.254    # la remplacer (ou l'ajouter si elle manque)</pre><div class="tip">La passerelle doit être sur <strong>votre</strong> réseau : la machine doit pouvoir la joindre directement. Une passerelle qui n'existe pas donne <code>Destination Host Unreachable</code>, et l'erreur vient de votre propre adresse.</div><h3>Le routeur doit faire suivre les paquets</h3><p>Une machine Linux qui a deux interfaces ne passe <strong>pas</strong> les paquets de l'une à l'autre par défaut. Le routage s'active par un réglage du noyau :</p><pre>sysctl net.ipv4.ip_forward          # 0 : désactivé · 1 : activé
sysctl -w net.ipv4.ip_forward=1     # l'activer tout de suite</pre><p>Symptôme typique d'un routage désactivé : les postes joignent les deux adresses du routeur, mais <strong>rien</strong> ne passe au-delà.</p><h3>L'aller… et le retour</h3>""" + SCHEMA_RETOUR + """<h3>Suivre le chemin : traceroute</h3><pre>root@vitrine:~# traceroute -n 10.30.0.20
 1  172.16.5.254  0.312 ms  0.285 ms  0.270 ms     # étape 1 : la passerelle
 2  10.30.0.20    0.654 ms  0.589 ms  0.610 ms     # étape 2 : le serveur</pre><p>Chaque ligne est un routeur traversé. Des étoiles <code>* * *</code> montrent l'étape où le chemin se perd. <code>-n</code> affiche les adresses sans chercher leur nom.</p><h3>Rendre permanent</h3><p>Comme les adresses au module 1, une route ou un réglage tapé à la main est perdu au redémarrage. Sur Debian :</p><pre># /etc/network/interfaces : la passerelle se déclare avec l'adresse
iface eth0 inet static
    address 172.16.5.30
    netmask 255.255.255.0
    gateway 172.16.5.254

# /etc/sysctl.conf : réglages du noyau, appliqués au démarrage
net.ipv4.ip_forward=1</pre><p><code>sysctl -p</code> applique tout de suite le contenu de <code>/etc/sysctl.conf</code>. Et l'unique vraie preuve reste la même : <code>redemarrer &lt;machine&gt;</code>.</p>""",
    "setup": r'''
reseau_neuf
machine sw-annecy
machine caisse
machine bureau
machine box-annecy routeur
machine sw-siege
machine srv-stock
LO='auto lo
iface lo inet loopback
'
# R2.1 : la caisse n'a pas de passerelle
interfaces caisse <<EOF
$LO
auto eth0
iface eth0 inet static
    address 192.168.10.11
    netmask 255.255.255.0
EOF
# R2.2 : le bureau a gardé la passerelle de l'ancienne installation, qui n'existe plus
interfaces bureau <<EOF
$LO
auto eth0
iface eth0 inet static
    address 192.168.10.12
    netmask 255.255.255.0
    gateway 192.168.10.1
EOF
interfaces box-annecy <<EOF
$LO
auto eth0
iface eth0 inet static
    address 192.168.10.254
    netmask 255.255.255.0

auto eth1
iface eth1 inet static
    address 10.20.0.254
    netmask 255.255.255.0
EOF
# R2.3 : le routage de la box est désactivé
fichier_sur box-annecy /etc/sysctl.conf <<'EOF'
# Réglages du noyau, appliqués au démarrage
net.ipv4.ip_forward=0
EOF
docker exec box-annecy sysctl -q -w net.ipv4.ip_forward=0
# R2.4 : le serveur ne sait pas renvoyer ses réponses vers le magasin
interfaces srv-stock <<EOF
$LO
auto eth0
iface eth0 inet static
    address 10.20.0.10
    netmask 255.255.255.0
EOF
cable caisse eth0 $(mac 3c:52:82) sw-annecy port1 -
cable bureau eth0 $(mac 3c:52:82) sw-annecy port2 -
cable box-annecy eth0 $(mac 00:24:d4) sw-annecy port8 -
cable box-annecy eth1 $(mac 00:24:d4) sw-siege port1 -
cable srv-stock eth0 $(mac 00:50:56) sw-siege port2 -
cabler
cat > $R/plan.txt <<'EOF'

  Magasin d'Annecy (192.168.10.0/24) relié au siège (10.20.0.0/24) par box-annecy

  sw-annecy (switch du magasin)              sw-siege (switch du siège)
   ├─ port1 ── caisse   192.168.10.11          └─ port2 ── srv-stock   10.20.0.10
   ├─ port2 ── bureau   192.168.10.12                       (serveur de stock)
   └─ port8 ──┐                                 ┌── port1
              └── box-annecy (routeur) ─────────┘
                    eth0 192.168.10.254   eth1 10.20.0.254

  Passerelle du magasin : 192.168.10.254 · passerelle du siège : 10.20.0.254

EOF
''',
    "exercises": [
        {"id": "R2.1", "points": 3, "title": "La caisse ne sort pas",
         "ticket": {"from": "diallo", "body": "La caisse doit consulter le serveur de stock du siège (<code>10.20.0.10</code>) à chaque vente. Elle répond <code>Network is unreachable</code>. Pourtant, elle marche très bien avec les autres machines du magasin !"},
         "desc": "La caisse a une route par défaut vers la passerelle du magasin (<code>192.168.10.254</code>), et joint la box côté siège (<code>10.20.0.254</code>).",
         "hints": ["« Network is unreachable » : la caisse ne sait pas où envoyer un paquet qui n'est pas pour son réseau. Regardez sa table de routage (<code>ip route</code>) et relisez le schéma « comment une machine décide ».",
                   "Sur la caisse : <code>ip route add default via 192.168.10.254</code>, puis <code>ping -c 2 10.20.0.254</code>."],
         "checks": [
             ('[ "$(passerelle caisse)" = 192.168.10.254 ] || { montre_routes caisse; exit 1; }', "La caisse n'a pas de route par défaut vers la passerelle du magasin, 192.168.10.254."),
             ('joint caisse 10.20.0.254', "La caisse ne joint pas l'adresse de la box côté siège (10.20.0.254)."),
         ]},
        {"id": "R2.2", "points": 3, "title": "La mauvaise porte",
         "ticket": {"from": "sophie", "body": "Le bureau, lui, a bien une passerelle : Julien dit l'avoir recopiée de l'ancien magasin. Mais il n'atteint pas non plus le siège, et le message est différent : <code>Destination Host Unreachable</code>. Tu regardes ?"},
         "desc": "Le bureau a une seule route par défaut, vers <code>192.168.10.254</code>, et joint la box côté siège (<code>10.20.0.254</code>).",
         "hints": ["Le bureau envoie tout à une passerelle… qui existe-t-elle sur le réseau du magasin ? Comparez sa route par défaut avec le plan, et essayez de la joindre.",
                   "La passerelle <code>192.168.10.1</code> n'existe pas. Sur le bureau : <code>ip route replace default via 192.168.10.254</code>, puis <code>ip route</code> pour vérifier."],
         "checks": [
             ('[ "$(sur bureau ip -4 route show default | grep -c "^default")" = 1 ] && [ "$(passerelle bureau)" = 192.168.10.254 ] || { montre_routes bureau; exit 1; }', "Le bureau doit avoir une seule route par défaut, vers 192.168.10.254."),
             ('joint bureau 10.20.0.254', "Le bureau ne joint pas l'adresse de la box côté siège (10.20.0.254)."),
         ]},
        {"id": "R2.3", "points": 3, "title": "Un routeur qui ne route pas",
         "ticket": {"from": "lea", "body": "Bizarre : depuis la caisse, la box répond sur ses deux adresses, côté magasin et côté siège. Mais rien ne passe au-delà de la box. Un routeur qui ne route pas, ça te dit quelque chose ?"},
         "desc": "La box fait suivre les paquets d'un réseau à l'autre : routage du noyau activé (<code>net.ipv4.ip_forward = 1</code>).",
         "hints": ["Une machine Linux qui a deux interfaces ne passe pas les paquets de l'une à l'autre sans qu'on le lui demande. Le cours, section « Le routeur doit faire suivre les paquets ».",
                   "Sur box-annecy : <code>sysctl net.ipv4.ip_forward</code> affiche 0 ; <code>sysctl -w net.ipv4.ip_forward=1</code> l'active."],
         "checks": [
             ('[ "$(transfert box-annecy)" = 1 ]', "Le routage de la box est toujours désactivé (net.ipv4.ip_forward = 0)."),
         ]},
        {"id": "R2.4", "points": 3, "title": "L'aller sans le retour",
         "ticket": {"from": "thomas", "body": "J'ai lancé un <code>ping</code> de la caisse vers le serveur de stock : rien, pas même un message d'erreur. Le serveur reçoit pourtant quelque chose, ses voyants clignotent… On dirait que la réponse se perd en route."},
         "desc": "Le serveur de stock a une route par défaut vers sa passerelle (<code>10.20.0.254</code>), et la caisse reçoit ses réponses (<code>ping 10.20.0.10</code>).",
         "hints": ["Un ping est un aller-retour. L'aller fonctionne maintenant ; et le retour ? Regardez la table de routage du serveur, et relisez le schéma « l'aller… et le retour ».",
                   "Sur srv-stock : <code>ip route add default via 10.20.0.254</code>. Puis, depuis la caisse : <code>ping -c 2 10.20.0.10</code> et <code>traceroute -n 10.20.0.10</code>."],
         "checks": [
             ('[ "$(passerelle srv-stock)" = 10.20.0.254 ] || { montre_routes srv-stock; exit 1; }', "Le serveur de stock n'a pas de route par défaut vers sa passerelle, 10.20.0.254."),
             ('joint caisse 10.20.0.10', "La caisse ne reçoit toujours pas de réponse du serveur de stock (ping 10.20.0.10)."),
         ]},
        {"id": "R2.5", "points": 4, "title": "Une passerelle qui survit", "manual": True,
         "ticket": {"from": "lea", "body": "Bien. Maintenant, la question qui fâche : après la prochaine coupure de courant, la caisse aura-t-elle encore sa passerelle ? Rends-la permanente, et prouve-le avec <code>redemarrer caisse</code>."},
         "desc": "Après un redémarrage, la caisse retrouve toute seule sa route par défaut vers <code>192.168.10.254</code> (fichier <code>/etc/network/interfaces</code>). <strong>La vérification redémarre la caisse.</strong>",
         "hints": ["Une route tapée avec <code>ip route</code> vit en mémoire. Au module 1, l'adresse du bureau est devenue permanente grâce à un fichier ; la passerelle se déclare dans le même fichier.",
                   "Sur la caisse : <code>nano /etc/network/interfaces</code>, ajoutez sous <code>netmask</code> la ligne indentée <code>gateway 192.168.10.254</code>. Puis, depuis la console : <code>redemarrer caisse</code>."],
         "checks": [
             ('fichier caisse /etc/network/interfaces | grep -v "^ *#" | grep -qE "^[[:space:]]*gateway[[:space:]]+192\\.168\\.10\\.254"', "Le fichier /etc/network/interfaces de la caisse ne déclare pas de passerelle (ligne gateway)."),
             ('reboot_test caisse && [ "$(passerelle caisse)" = 192.168.10.254 ] || { montre_routes caisse; exit 1; }', "Après redémarrage, la caisse n'a pas retrouvé sa route par défaut vers 192.168.10.254."),
         ]},
        {"id": "R2.6", "points": 4, "title": "Un routage qui survit", "manual": True,
         "ticket": {"from": "lea", "body": "Même question pour la box : après un redémarrage, routera-t-elle encore ? Fais en sorte que oui, et vérifie avec <code>redemarrer box-annecy</code>."},
         "desc": "Après un redémarrage, la box active toute seule son routage (fichier <code>/etc/sysctl.conf</code>). <strong>La vérification redémarre la box.</strong>",
         "hints": ["<code>sysctl -w</code> ne dure que jusqu'à l'extinction. Au démarrage, la box relit un fichier de réglages du noyau : le cours le montre. Regardez ce qu'il contient déjà.",
                   "Sur box-annecy : <code>nano /etc/sysctl.conf</code>, remplacez <code>net.ipv4.ip_forward=0</code> par <code>net.ipv4.ip_forward=1</code>, puis <code>sysctl -p</code>. Testez avec <code>redemarrer box-annecy</code>."],
         "checks": [
             ('fichier box-annecy /etc/sysctl.conf | grep -v "^ *#" | grep -qE "^[[:space:]]*net\\.ipv4\\.ip_forward[[:space:]]*=[[:space:]]*1"', "Le fichier /etc/sysctl.conf de la box n'active pas le routage (net.ipv4.ip_forward=1)."),
             ('reboot_test box-annecy && [ "$(transfert box-annecy)" = 1 ]', "Après redémarrage, la box n'a pas réactivé son routage."),
         ]},
    ],
}

STEPS = {
    1: MODULE_0,
    # ─────────────────────────────────────────────────────────────────────
    2: {
        "title": "Module 1 — Le magasin d'Annecy",
        "description": "Découvrir un réseau local et ses premières pannes. Compétences : ip a, adresses IP et MAC, état d'une interface, masque, ping, ARP et conflit d'adresses, configuration temporaire et permanente.",
        "lesson": SCENARIO_ANNECY + """<h3>Le réseau du magasin</h3>""" + SCHEMA_MAGASIN + """<p>Chaque machine a une <strong>carte réseau</strong> (une <em>interface</em>, ici <code>eth0</code>) reliée par un câble à un port du <strong>switch</strong>. Le switch fait circuler les messages entre les machines qui lui sont branchées.</p><div class="tip">Rappel du module 0 : un onglet par machine au-dessus du terminal (ou <code>connexion &lt;machine&gt;</code>), <code>plan</code> pour le schéma, <code>redemarrer &lt;machine&gt;</code> depuis la console. Et toujours un coup d'œil à l'invite avant d'appuyer sur Entrée.</div><h3>Deux adresses par machine</h3><ul><li>L'adresse <strong>MAC</strong> identifie la carte réseau : fixée en usine, unique, six nombres en hexadécimal (<code>3c:52:82:4a:10:7e</code>). Les trois premiers désignent le fabricant.</li><li>L'adresse <strong>IP</strong> est choisie par l'administrateur, selon le réseau où la machine est branchée, comme une adresse postale : on la change quand on déménage. Elle s'écrit avec son <strong>masque</strong> : <code>172.16.5.21/24</code>.</li></ul>""" + SCHEMA_IP_A + """<pre>ip a          # toutes les interfaces, en détail
ip -br a      # en bref : une ligne par interface (nom, état, adresses)</pre><h3>Réseau et masque</h3><p>Une adresse IP a deux parties : le <strong>réseau</strong> et la <strong>machine</strong>. Le masque dit où passe la frontière. Deux machines ne se parlent directement que si elles sont <strong>sur le même réseau</strong>… et chacune en juge avec <strong>son propre masque</strong>.</p>""" + SCHEMA_MASQUE + """<table class="lesson-table"><tr><th>Préfixe</th><th>Masque</th><th>Adresses dans le réseau</th></tr><tr><td><code>/8</code></td><td><code>255.0.0.0</code></td><td>16 millions</td></tr><tr><td><code>/16</code></td><td><code>255.255.0.0</code></td><td>65 536</td></tr><tr><td><code>/24</code></td><td><code>255.255.255.0</code></td><td>256</td></tr><tr><td><code>/28</code></td><td><code>255.255.255.240</code></td><td>16</td></tr></table><h3>Tester : ping</h3><p><code>ping</code> envoie un petit message à une adresse et attend la réponse : c'est le premier test à faire.</p><pre>root@vitrine:~# ping -c 3 172.16.5.20      # -c 3 : trois essais (sinon, Ctrl+C pour arrêter)
64 bytes from 172.16.5.20: icmp_seq=1 ttl=64 time=0.081 ms     # elle répond</pre><ul><li><code>Destination Host Unreachable</code> : l'adresse est sur mon réseau, mais personne ne répond (machine éteinte, câble débranché, interface éteinte…).</li><li><code>Network is unreachable</code> : d'après mon adresse et mon masque, cette adresse n'est <strong>pas</strong> sur mon réseau, et je ne sais pas où l'envoyer.</li></ul><h3>Configurer une interface</h3><pre>ip link set eth0 up                    # allumer l'interface (down : l'éteindre)
ip addr add 172.16.5.30/24 dev eth0    # ajouter une adresse, avec son masque
ip addr del 172.16.5.30/24 dev eth0    # retirer une adresse (écrite comme à l'ajout)</pre><div class="tip">Une interface peut porter <strong>plusieurs</strong> adresses : en ajouter une bonne ne retire pas la mauvaise. Vérifiez toujours le résultat avec <code>ip a</code>.</div><h3>Trouver la carte derrière une adresse : ARP</h3>""" + SCHEMA_ARP + """<pre>ip neigh                          # les correspondances IP → MAC déjà apprises (le « voisinage »)
arping -c 3 -I eth0 172.16.5.20   # qui répond pour cette adresse ? Une MAC par réponse</pre><p>Si <code>arping</code> affiche <strong>deux MAC différentes</strong> pour la même adresse, deux machines se la disputent. Les symptômes sont trompeurs : ça marche… une fois sur deux.</p><h3>Temporaire ou permanent ?</h3>""" + SCHEMA_PERMANENT + """<p>Sur Debian, la configuration réseau de démarrage est dans <code>/etc/network/interfaces</code>. Exemple d'un poste de Chamonix :</p><pre>auto lo
iface lo inet loopback

auto eth0                     # à activer au démarrage
iface eth0 inet static        # adresse fixe (static)
    address 172.16.5.30
    netmask 255.255.255.0</pre><pre>nano /etc/network/interfaces   # modifier le fichier (Ctrl+O pour enregistrer, Ctrl+X pour quitter)
ifup eth0                      # appliquer la configuration du fichier à eth0
ifdown eth0                    # la retirer (éteint l'interface)</pre><div class="tip">Modifier le fichier ne change rien <strong>tout de suite</strong> : la machine ne le relit qu'avec <code>ifup</code>, ou au démarrage. Testez toujours avec un vrai redémarrage (<code>redemarrer &lt;machine&gt;</code> depuis la console) : c'est le seul moyen d'être sûr.</div>""",
        "setup": r'''
reseau_neuf
machine sw-annecy
for m in caisse bureau imprimante borne portable-julien; do machine $m; done
LO='auto lo
iface lo inet loopback
'
interfaces caisse <<EOF
$LO
auto eth0
iface eth0 inet static
    address 192.168.10.11
    netmask 255.255.255.0
EOF
# Bureau : interface allumée, sans adresse (R1.3, puis R1.6)
interfaces bureau <<EOF
$LO
auto eth0
iface eth0 inet manual
EOF
# Imprimante : configuration présente, mais pas activée au démarrage (R1.2)
interfaces imprimante <<EOF
$LO
iface eth0 inet static
    address 192.168.10.50
    netmask 255.255.255.0
EOF
# Borne : la bonne adresse, avec un mauvais masque (R1.4)
interfaces borne <<EOF
$LO
auto eth0
iface eth0 inet static
    address 192.168.10.30
    netmask 255.255.255.240
EOF
# Portable de Julien : l'adresse de la caisse (R1.5)
interfaces portable-julien <<EOF
$LO
auto eth0
iface eth0 inet static
    address 192.168.10.11
    netmask 255.255.255.0
EOF
cable caisse eth0 $(mac 3c:52:82) sw-annecy port1 -
cable bureau eth0 $(mac 3c:52:82) sw-annecy port2 -
cable imprimante eth0 $(mac 00:1e:0b) sw-annecy port3 -
cable borne eth0 $(mac b8:27:eb) sw-annecy port4 -
cable portable-julien eth0 $(mac f4:8e:38) sw-annecy port5 -
cabler
cat > $R/plan.txt <<'EOF'

  Magasin d'Annecy — réseau local 192.168.10.0/24 (masque 255.255.255.0)

  sw-annecy (switch)
   ├─ port1 ── caisse            192.168.10.11   poste de caisse
   ├─ port2 ── bureau            192.168.10.12   poste du bureau
   ├─ port3 ── imprimante        192.168.10.50   imprimante réseau
   ├─ port4 ── borne             192.168.10.30   borne de commande des clients
   └─ port5 ── portable-julien   192.168.10.40   portable du stagiaire

  Ce sont les adresses PRÉVUES par le plan d'installation : la réalité peut différer…
  connexion <machine> : travailler sur une machine (exit pour revenir à la console)

EOF
mkdir -p $H/reponses
own $H/reponses
''',
        "exercises": [
            {"id": "R1.1", "points": 2, "title": "Faire connaissance", "manual": True,
             "ticket": {"from": "sophie", "body": "Bonjour ! Pour l'inventaire du magasin, il me faut les deux adresses de la caisse : son adresse <strong>IP</strong> et son adresse <strong>MAC</strong>. Notez-les dans <code>~/reponses/caisse.txt</code>, sur la console : l'IP sur la première ligne, la MAC sur la deuxième. Relevez-les sur la caisse elle-même, pas dans le plan : avec Julien, on ne sait jamais."},
             "desc": "<code>~/reponses/caisse.txt</code> (sur la console) : ligne 1, l'adresse IP de la caisse (le <code>/24</code> est facultatif) ; ligne 2, l'adresse MAC de sa carte réseau <code>eth0</code>.",
             "hints": ["Connectez-vous à la caisse et affichez ses interfaces. Laquelle est branchée au switch ? Dans son bloc, une ligne donne l'adresse MAC et une autre l'adresse IP : le schéma du cours les montre sur une autre machine.",
                       "<code>connexion caisse ip a</code> : la MAC suit <code>link/ether</code>, l'IP suit <code>inet</code> dans le bloc de <code>eth0</code>. Puis, sur la console : <code>nano ~/reponses/caisse.txt</code>."],
             "checks": [
                 ('[ -s $H/reponses/caisse.txt ]', "~/reponses/caisse.txt n'existe pas ou est vide (il se crée sur la console, pas sur la caisse)."),
                 (r'''l=$(sed -n 1p $H/reponses/caisse.txt | tr -d ' \r'); [ "${l%/24}" = 192.168.10.11 ] || { echo "MSG:ligne 1 : « $l »"; exit 1; }''',
                  "La première ligne n'est pas l'adresse IP de la caisse."),
                 (r'''l=$(sed -n 2p $H/reponses/caisse.txt | tr -d ' \r' | tr 'A-F-' 'a-f:'); [ -n "$l" ] && [ "$l" = "$(macde caisse)" ] || { echo "MSG:ligne 2 : « $l »"; exit 1; }''',
                  "La deuxième ligne n'est pas l'adresse MAC de la carte eth0 de la caisse."),
             ]},
            {"id": "R1.2", "points": 3, "title": "L'imprimante muette",
             "ticket": {"from": "diallo", "body": "Je dois imprimer les étiquettes de prix pour l'ouverture, et l'imprimante ne répond pas. Pourtant elle est allumée, et Julien jure qu'il l'a bien branchée. Vous pouvez regarder ?"},
             "desc": "L'imprimante porte son adresse prévue (<code>192.168.10.50/24</code>) et répond au <code>ping</code> de la caisse.",
             "hints": ["Faites d'abord le constat depuis la caisse : l'imprimante répond-elle ? Quel message ? Puis allez voir l'interface de l'imprimante elle-même : le cours explique ce que signifient UP et DOWN.",
                       "Sur l'imprimante, <code>ip a</code> montre <code>eth0</code> en <code>state DOWN</code> et sans adresse : sa configuration existe (<code>cat /etc/network/interfaces</code>) mais n'a jamais été appliquée. <code>ifup eth0</code> l'applique."],
             "checks": [
                 ('allumee imprimante', "L'interface eth0 de l'imprimante est toujours éteinte (state DOWN)."),
                 ('[ "$(ipv4 imprimante)" = 192.168.10.50/24 ] || { montre imprimante; exit 1; }', "L'imprimante n'a pas son adresse prévue, 192.168.10.50/24 (et seulement celle-là)."),
                 ('joint caisse 192.168.10.50', "La caisse ne reçoit toujours pas de réponse de l'imprimante (ping 192.168.10.50)."),
             ]},
            {"id": "R1.3", "points": 3, "title": "Le poste du bureau",
             "ticket": {"from": "lea", "body": "Julien n'a pas eu le temps de configurer le poste du bureau : il n'a pas d'adresse IP. Donne-lui celle qui est prévue dans le plan, avec le bon masque, et vérifie qu'il joint la caisse."},
             "desc": "Le poste <code>bureau</code> porte l'adresse prévue par le plan, en <code>/24</code>, et aucune autre ; il reçoit une réponse de la caisse (<code>192.168.10.11</code>).",
             "hints": ["<code>plan</code> donne l'adresse prévue. Une adresse s'ajoute à une interface, avec son masque : la section « Configurer une interface » du cours montre la syntaxe sur un autre réseau.",
                       "Sur le bureau : <code>ip addr add 192.168.10.12/24 dev eth0</code>, puis <code>ping -c 3 192.168.10.11</code>."],
             "checks": [
                 ('[ -n "$(ipv4 bureau)" ]', "Le bureau n'a toujours aucune adresse IP sur eth0."),
                 ('[ "$(ipv4 bureau)" = 192.168.10.12/24 ] || { montre bureau; exit 1; }', "Le bureau doit porter exactement l'adresse prévue, 192.168.10.12, en /24 (et aucune autre)."),
                 ('joint bureau 192.168.10.11', "Le bureau ne reçoit pas de réponse de la caisse (ping 192.168.10.11)."),
             ]},
            {"id": "R1.4", "points": 3, "title": "La borne ne voit personne",
             "ticket": {"from": "thomas", "body": "La borne de commande affiche bien le catalogue, mais elle doit envoyer les commandes des clients à la caisse… et là, rien : <code>Network is unreachable</code>. Pourtant son adresse est la bonne, j'ai vérifié trois fois !"},
             "desc": "La borne garde son adresse <code>192.168.10.30</code>, avec le masque du réseau du magasin (<code>/24</code>), sans autre adresse ; elle reçoit une réponse de la caisse.",
             "hints": ["Son adresse est la bonne… mais une adresse ne va jamais seule. Comparez ce qu'affiche <code>ip a</code> sur la borne avec le plan, puis relisez le schéma du cours sur le masque : quelles adresses la borne croit-elle « sur son réseau » ?",
                       "La borne est en <code>/28</code> : pour elle, seules les adresses .16 à .31 sont voisines, et la caisse (.11) n'en fait pas partie. Sur la borne : <code>ip addr del 192.168.10.30/28 dev eth0</code>, puis <code>ip addr add 192.168.10.30/24 dev eth0</code>."],
             "checks": [
                 ('[ "$(ipv4 borne)" = 192.168.10.30/24 ] || { montre borne; exit 1; }', "La borne doit porter 192.168.10.30 avec le masque /24, et aucune autre adresse."),
                 ('joint borne 192.168.10.11', "La borne ne reçoit pas de réponse de la caisse (ping 192.168.10.11)."),
             ]},
            {"id": "R1.5", "points": 3, "title": "Une caisse capricieuse",
             "ticket": {"from": "julien", "body": "Euh… depuis que j'ai branché mon portable sur le switch du magasin, la caisse ne répond plus qu'une fois sur deux. Je lui ai mis une adresse fixe, comme on me l'a appris. C'est sûrement une coïncidence ? 😅"},
             "desc": "Plus aucune autre machine ne porte l'adresse de la caisse : le portable de Julien prend l'adresse qui lui est réservée dans le plan (en <code>/24</code>), la caisse garde la sienne, et le portable joint la vraie caisse.",
             "hints": ["Deux machines avec la même adresse IP : laquelle répond ? Comparez l'adresse du portable de Julien avec le plan, et regardez qui répond pour l'adresse de la caisse (section ARP du cours).",
                       "Le portable a pris 192.168.10.11, l'adresse de la caisse. Sur portable-julien : <code>ip addr del 192.168.10.11/24 dev eth0</code>, puis <code>ip addr add 192.168.10.40/24 dev eth0</code>."],
             "checks": [
                 ('[ "$(ipv4 portable-julien)" = 192.168.10.40/24 ] || { montre portable-julien; exit 1; }', "Le portable de Julien doit porter l'adresse qui lui est réservée, 192.168.10.40/24, et aucune autre."),
                 ('[ "$(ipv4 caisse)" = 192.168.10.11/24 ] || { montre caisse; exit 1; }', "La caisse doit garder son adresse, 192.168.10.11/24."),
                 ('for m in bureau imprimante borne portable-julien; do ipv4 $m | grep -q "^192\\.168\\.10\\.11/" && { echo "MSG:$m porte aussi 192.168.10.11"; exit 1; }; done; true', "Une autre machine que la caisse porte encore l'adresse 192.168.10.11."),
                 ('joint portable-julien 192.168.10.11 && sur portable-julien ip neigh show 192.168.10.11 dev eth0 | grep -qi "$(macde caisse)"', "Le portable de Julien ne joint pas la caisse elle-même (ping 192.168.10.11)."),
             ]},
            {"id": "R1.6", "points": 4, "title": "À l'épreuve du redémarrage", "manual": True,
             "ticket": {"from": "lea", "body": "L'adresse que tu as donnée au bureau tient… jusqu'au prochain redémarrage. Une coupure de courant cette nuit, et Aminata ne pourra plus rien faire demain matin. Rends-la permanente, et prouve-le : redémarre le bureau (<code>redemarrer bureau</code>, depuis la console)."},
             "desc": "Le poste <code>bureau</code> retrouve tout seul l'adresse <code>192.168.10.12/24</code> au démarrage, grâce à son fichier <code>/etc/network/interfaces</code>. <strong>La vérification redémarre le bureau.</strong>",
             "hints": ["<code>ip addr</code> ne touche qu'à la configuration en cours, en mémoire. Au démarrage, Debian relit un fichier : le cours en montre un exemple. Regardez ce que contient déjà celui du bureau.",
                       "Sur le bureau : <code>nano /etc/network/interfaces</code>, remplacez <code>iface eth0 inet manual</code> par <code>iface eth0 inet static</code>, suivi de deux lignes indentées : <code>address 192.168.10.12</code> et <code>netmask 255.255.255.0</code>. Testez depuis la console : <code>redemarrer bureau</code>, puis <code>connexion bureau ip a</code>."],
             "checks": [
                 ('fichier bureau /etc/network/interfaces | grep -v "^ *#" | grep -q "192\\.168\\.10\\.12"', "Le fichier /etc/network/interfaces du bureau ne contient pas son adresse : au démarrage, il n'en aura aucune."),
                 ('docker restart -t 1 bureau >/dev/null && /usr/local/sbin/lab-cablage && sleep 1 && [ "$(ipv4 bureau)" = 192.168.10.12/24 ] || { montre bureau; exit 1; }',
                  "Après redémarrage, le bureau ne retrouve pas exactement 192.168.10.12/24 : vérifiez les mots-clés auto, iface … inet static, address et netmask (puis testez avec redemarrer bureau)."),
             ]},
        ],
    },
    3: MODULE_2,
}
