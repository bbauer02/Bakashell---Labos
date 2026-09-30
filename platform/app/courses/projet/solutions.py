"""Corrigé du projet final : un script par mission, exécuté en tant qu'« etudiant » par le banc de test.
Chaque ligne « #@ <exercice> » ouvre la correction de cet exercice (visible des seuls comptes admin : c'est une
épreuve, les corrections ne sont pas montrées aux étudiants, et les blocs n'ont pas de lignes d'explication « #? »).
Les données tirées au sort (bug, règles métier, numéro de ticket, versions, port, pannes) sont relues dans les fichiers
remis à l'étudiant, ou observées sur les serveurs, comme le ferait un candidat.
"""

SOLUTIONS = {
    1: r'''
cd ~/boutique
#@ P1.1
# Numéro du ticket, et règles du service commercial lues en tête de src/devis.js
N=$(ls ~/tickets/ticket-*.txt | head -1 | grep -oE '[0-9]+' | tail -1)
cat ~/tickets/ticket-$N.txt
# Valeurs attendues calculées à la main (en centimes), d'après les règles : le test couvre le cas du ticket et les
# cas voisins (seuil exact et juste en dessous, remise au seuil de quantité, remise limitée à sa ligne, seuil
# apprécié remises déduites, arrondi du prix unitaire dans les deux sens)
node - "$N" <<'EOF'
const fs = require('fs');
const n = process.argv[2];
const src = fs.readFileSync('src/devis.js', 'utf8');
const regle = (nom) => Number(src.match(new RegExp(`const ${nom} = ([\\d.]+);`))[1]);
const QTE = regle('QUANTITE_REMISE');
const TAUX = regle('TAUX_REMISE');
const FRAIS = Math.round(regle('FRAIS_PORT') * 100);
const SEUIL = Math.round(regle('SEUIL_PORT_OFFERT') * 100);
const cts = (x) => Math.round(Number((x * 100).toFixed(6)));
// Article dont QTE exemplaires atteignent le seuil avant remise, mais plus après
let c = Math.floor(SEUIL / (QTE * 1.2));
while (!(cts(c / 100 * 1.2) * QTE >= SEUIL && cts(c / 100 * 1.2) * QTE - Math.round(cts(c / 100 * 1.2) * QTE * TAUX / 100) < SEUIL)) c++;
const catalogue = [
  { ref: 'CARTE', prixHT: 10.01 }, { ref: 'GOURDE', prixHT: 19.99 }, { ref: 'TENTE', prixHT: 100 },
  { ref: 'PILE', prixHT: SEUIL / 120 }, { ref: 'SOUS', prixHT: SEUIL / 120 - 0.5 }, { ref: 'PAIRE', prixHT: c / 100 },
];
function attendu(lignes) {
  const details = lignes.map(({ ref, quantite }) => {
    const brut = cts(catalogue.find((p) => p.ref === ref).prixHT * 1.2) * quantite;
    const remise = quantite >= QTE ? Math.round(brut * TAUX / 100) : 0;
    return { ref, quantite, brut: brut / 100, remise: remise / 100, net: (brut - remise) / 100 };
  });
  const brut = details.reduce((s, l) => s + Math.round(l.brut * 100), 0);
  const remises = details.reduce((s, l) => s + Math.round(l.remise * 100), 0);
  const produits = brut - remises;
  const port = produits >= SEUIL ? 0 : FRAIS;
  return { lignes: details, brut: brut / 100, remises: remises / 100, produits: produits / 100, port: port / 100, total: (produits + port) / 100 };
}
const cas = {
  'pile au seuil : le port est offert': [{ ref: 'PILE', quantite: 1 }],
  'juste sous le seuil : le port est dû': [{ ref: 'SOUS', quantite: 1 }],
  'remise dès le seuil de quantité': [{ ref: 'CARTE', quantite: QTE }],
  'pas de remise juste en dessous du seuil de quantité': [{ ref: 'CARTE', quantite: QTE - 1 }],
  'la remise ne profite qu\'à la ligne concernée': [{ ref: 'CARTE', quantite: QTE }, { ref: 'TENTE', quantite: 1 }],
  'le seuil de port offert s\'apprécie remises déduites': [{ ref: 'PAIRE', quantite: QTE }],
  'prix unitaire arrondi avant la quantité': [{ ref: 'GOURDE', quantite: 3 }],
  'arrondi vers le bas': [{ ref: 'CARTE', quantite: 1 }],
};
let code = `// Ticket #${n} : test de non-régression du calcul des devis (valeurs calculées d'après les règles de src/devis.js)
const { calculerDevis, prixUnitaireTTC } = require('../src/devis');

const catalogue = ${JSON.stringify(catalogue)};

test('prix unitaires TTC arrondis au centime', () => {
  expect(prixUnitaireTTC(19.99)).toBe(23.99);
  expect(prixUnitaireTTC(10.01)).toBe(12.01);
});
`;
for (const [nom, lignes] of Object.entries(cas)) {
  code += `
test(${JSON.stringify(nom)}, () => {
  expect(calculerDevis(${JSON.stringify(lignes)}, catalogue)).toEqual(${JSON.stringify(attendu(lignes))});
});
`;
}
fs.writeFileSync(`tests/ticket-${n}.test.js`, code);
EOF
npx jest tests/ticket-$N.test.js || true
#@ P1.2
# Correction du bug décrit par le ticket (selon le projet : seuil exclu, remise étendue à toute la commande, seuil
# comparé avant remise, ou prix unitaire non arrondi)
node <<'EOF'
const fs = require('fs');
let src = fs.readFileSync('src/devis.js', 'utf8');
src = src
  .replace('const port = produits > SEUIL_PORT_OFFERT ? 0 : FRAIS_PORT;', 'const port = produits >= SEUIL_PORT_OFFERT ? 0 : FRAIS_PORT;')
  .replace('const port = brut >= SEUIL_PORT_OFFERT ? 0 : FRAIS_PORT;', 'const port = produits >= SEUIL_PORT_OFFERT ? 0 : FRAIS_PORT;')
  .replace('lignes.some((l) => l.quantite >= QUANTITE_REMISE)', 'quantite >= QUANTITE_REMISE')
  .replace('return prixHT * (1 + TVA);', 'return arrondi(prixHT * (1 + TVA));');
fs.writeFileSync('src/devis.js', src);
EOF
N=$(ls ~/tickets/ticket-*.txt | head -1 | grep -oE '[0-9]+' | tail -1)
npx jest tests/ticket-$N.test.js
#@ P1.3
# Le test existant qui figeait le comportement bogué est corrigé (valeur attendue selon la règle), pas supprimé
node <<'EOF'
const fs = require('fs');
const src = fs.readFileSync('src/devis.js', 'utf8');
const FRAIS = src.match(/const FRAIS_PORT = ([\d.]+);/)[1];
let t = fs.readFileSync('tests/devis.test.js', 'utf8');
const bloc = (nom, nouveau, remplacer) => {
  const i = t.indexOf(`test('${nom}'`);
  if (i < 0) return;
  const j = t.indexOf('\n  });', i);
  t = t.slice(0, i) + remplacer(t.slice(i, j).replace(nom, nouveau)) + t.slice(j);
};
bloc('pile au seuil, le port reste dû', 'pile au seuil, le port est offert', (b) => b.replace(/expect\(d\.port\)\.toBe\([\d.]+\);/, 'expect(d.port).toBe(0);'));
bloc('remise par quantité : toute la commande en profite', 'remise par quantité : seule la ligne concernée en profite', (b) => b.replace(/toBe\([\d.]+\);$/, 'toBe(0);'));
bloc('port offert : le panier atteint le seuil', 'port dû : le seuil est apprécié remises déduites', (b) => b.replace('expect(d.port).toBe(0);', `expect(d.port).toBe(${FRAIS});`));
t = t.replace('toBeCloseTo(23.988, 3)', 'toBe(23.99)');
fs.writeFileSync('tests/devis.test.js', t);
EOF
npx jest
#@ P1.4
# La suite complète passe avec le code corrigé ; le test du ticket couvre aussi les erreurs voisines du bug
npx jest --verbose 2>&1 | tail -n 5
''',
    2: r'''
cd ~/boutique
N=$(ls ~/tickets/ticket-*.txt | head -1 | grep -oE '[0-9]+' | tail -1)
#@ P2.1
git config --global user.name "Camille Martin"
git config --global user.email "camille.martin@cimes-sentiers.fr"
git switch -q -c correctif-$N
git add src/devis.js tests/
git status --short
git commit -q -m "Devis : correction du ticket #$N, avec son test de non-régression"
git push -q -u origin correctif-$N
#@ P2.2
git switch -q main
git pull -q --ff-only origin main
git merge -q --no-ff correctif-$N -m "Intégration du correctif du ticket #$N"
git push -q origin main
#@ P2.3
W=$(node -p "require('./package.json').version")
X=${W%.*}.$(( ${W##*.} + 1 ))
npm version "$X" --no-git-tag-version >/dev/null
python3 - "$X" "$N" <<'EOF'
import sys
x, n = sys.argv[1], sys.argv[2]
t = open("CHANGELOG.md", encoding="utf-8").read()
t = t.replace("## [Non publié]\n", f"## [Non publié]\n\n## [{x}]\n- Devis : correction du ticket #{n}\n", 1)
open("CHANGELOG.md", "w", encoding="utf-8").write(t)
EOF
git commit -q -am "Version $X (ticket #$N)"
git tag -a "v$X" -m "Version $X : correction du ticket #$N"
git push -q origin main "v$X"
git log --oneline --graph -6
''',
    3: r'''
cd ~/boutique
#@ P3.1
cat > Dockerfile <<'EOF'
FROM node:24-alpine
WORKDIR /app
# Dépendances d'abord (reprises du cache tant que package*.json ne change pas), sans les outils de développement
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
# Puis le code : seulement ce qui sert à exécuter l'API
COPY server.js produits.json ./
COPY src ./src
USER node
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "server.js"]
EOF
#@ P3.2
printf 'node_modules\n.git\ntests\ncoverage\nDockerfile\n.dockerignore\n' > .dockerignore
docker build -q -t boutique-api:essai . >/dev/null
docker run --rm --entrypoint sh boutique-api:essai -c 'ls -la /app'
#@ P3.3
echo "// essai du cache" >> server.js
docker build --progress=plain -t boutique-api:essai . 2>&1 | grep -E 'npm ci|CACHED' | head -n 4
git checkout -- server.js
#@ P3.4
docker rm -f essai-sante >/dev/null 2>&1 || true
docker run -d --name essai-sante boutique-api:essai >/dev/null
sleep 8
docker inspect -f '{{.State.Health.Status}}' essai-sante
docker rm -f essai-sante >/dev/null
#@ P3.5
X=$(node -p "require('./package.json').version")
docker build -q -t "boutique-api:$X" . >/dev/null
docker run -d --rm --name essai-version -p 3000:3000 "boutique-api:$X" >/dev/null
sleep 2
curl -s ci1:3000/health
docker rm -f essai-version >/dev/null
''',
    4: r'''
cd ~/infra
#@ P4.1
P=$(sed -n 's/^Port *: *\([0-9]*\).*/\1/p' ~/tickets/deploiement.txt)
mkdir -p roles/api/tasks roles/api/handlers roles/api/templates roles/api/defaults
cat > roles/api/defaults/main.yml <<EOF
api_port: $P
api_user: api
api_dir: /opt/api-boutique
api_journaux: /var/log/api-boutique
api_source: /home/etudiant/boutique
EOF
cat > roles/api/templates/api-boutique.j2 <<'EOF'
# {{ ansible_managed }}
API_USER={{ api_user }}
API_DIR={{ api_dir }}
API_PORT={{ api_port }}
API_JOURNAUX={{ api_journaux }}
EOF
cat > roles/api/tasks/main.yml <<'EOF'
- name: Node.js, depuis le dépôt interne
  ansible.builtin.apt:
    name: nodejs
    state: present
    update_cache: true
    cache_valid_time: 3600

- name: Compte système de l'API
  ansible.builtin.user:
    name: "{{ api_user }}"
    system: true
    shell: /usr/sbin/nologin
    create_home: false

- name: Dossiers du code et des journaux
  ansible.builtin.file:
    path: "{{ item.chemin }}"
    state: directory
    owner: "{{ item.proprietaire }}"
    group: "{{ item.proprietaire }}"
    mode: "0755"
  loop:
    - { chemin: "{{ api_dir }}", proprietaire: root }
    - { chemin: "{{ api_journaux }}", proprietaire: "{{ api_user }}" }

- name: Code de l'API (sans les tests ni les outils de développement)
  ansible.builtin.copy:
    src: "{{ api_source }}/{{ item }}"
    dest: "{{ api_dir }}/"
    owner: root
    group: root
    mode: u=rwX,go=rX
  loop: [server.js, package.json, produits.json, src]
  notify: Redémarrer l'API

- name: Script de service
  ansible.builtin.copy:
    src: "{{ api_source }}/deploiement/api-boutique"
    dest: /etc/init.d/api-boutique
    mode: "0755"
  notify: Redémarrer l'API

- name: Réglages de l'API
  ansible.builtin.template:
    src: api-boutique.j2
    dest: /etc/default/api-boutique
    mode: "0644"
  notify: Redémarrer l'API

- name: API démarrée, et activée au démarrage du serveur
  ansible.builtin.service:
    name: api-boutique
    state: started
    enabled: true
EOF
cat > roles/api/handlers/main.yml <<'EOF'
- name: Redémarrer l'API
  ansible.builtin.service:
    name: api-boutique
    state: restarted
EOF
cat > deploiement.yml <<'EOF'
- name: API de la boutique
  hosts: web
  become: true
  roles:
    - api
EOF
#@ P4.2
ansible-playbook deploiement.yml
P=$(sed -n 's/^Port *: *\([0-9]*\).*/\1/p' ~/tickets/deploiement.txt)
curl -s web1:$P/health; echo; curl -s web2:$P/health; echo
#@ P4.3
ansible-playbook deploiement.yml | tail -n 4
#@ P4.4
P=$(sed -n 's/^Port *: *\([0-9]*\).*/\1/p' ~/tickets/deploiement.txt)
ansible-playbook deploiement.yml -e api_port=$((P + 50)) | tail -n 4
curl -s web1:$((P + 50))/health; echo
ansible-playbook deploiement.yml | tail -n 4
''',
    5: r'''
mkdir -p ~/incident
#@ P5.1
# Diagnostic et réparation sur web3 : réglages, partition des journaux, droits des données, port de l'API
ssh -o BatchMode=yes admin@web3 'sudo bash -s' > ~/incident/constats.txt <<'EOF'
R=/etc/default/api-boutique
. $R
if ! id "$API_USER" >/dev/null 2>&1; then echo "Réglage API_USER de $R : le compte $API_USER n'existe pas, remis à api."; sed -i 's/^API_USER=.*/API_USER=api/' $R; fi
if [ ! -d "$API_DIR" ]; then echo "Réglage API_DIR de $R : $API_DIR n'existe pas, remis à /opt/api-boutique."; sed -i 's|^API_DIR=.*|API_DIR=/opt/api-boutique|' $R; fi
if [ ! -d "$API_DATA" ]; then echo "Réglage API_DATA de $R : $API_DATA n'existe pas, remis à /var/lib/api-boutique."; sed -i 's|^API_DATA=.*|API_DATA=/var/lib/api-boutique|' $R; fi
. $R
if [ "$(df --output=pcent "$API_JOURNAUX" | tail -n 1 | tr -dc 0-9)" -ge 95 ]; then
  f=$(ls -S "$API_JOURNAUX" | grep -v '^acces\.log' | head -n 1)
  echo "Partition $API_JOURNAUX pleine : $f ($(du -h "$API_JOURNAUX/$f" | cut -f1)), fichier de trace sans utilité, supprimé (journaux d'accès conservés)."
  rm -f "$API_JOURNAUX/$f"
fi
for f in "$API_DATA"/*; do
  if [ "$(stat -c %U "$f")" != api ]; then echo "Droits : $(basename "$f") appartenait à $(stat -c %U:%G "$f") ($(stat -c %a "$f")), rendu à api (640)."; chown api:api "$f"; chmod 640 "$f"; fi
done
p=$(ss -ltnpH "sport = :$API_PORT" | grep -oE 'pid=[0-9]+' | head -n 1 | cut -d= -f2)
if [ -n "$p" ] && [ "$p" != "$(cat /run/api-boutique.pid 2>/dev/null)" ]; then
  s=$(basename "$(grep -lx "$p" /run/*.pid | head -n 1)" .pid)
  echo "Port $API_PORT occupé par le service $s : $(tr '\0' ' ' < /proc/$p/cmdline)(utilisateur $(ps -o user= -p $p), dossier $(readlink /proc/$p/cwd)), arrêté."
  service "$s" stop
fi
service api-boutique restart
service api-boutique status
EOF
cat ~/incident/constats.txt
#@ P5.2
P=$(sed -n 's/.*(port \([0-9]*\)).*/\1/p' ~/tickets/incident.txt)
curl -s web3:$P/health; echo
curl -s web3/ | head -c 200; echo
#@ P5.3
# Les services parasites ne doivent plus démarrer avec le serveur
ssh -o BatchMode=yes admin@web3 'sudo bash -s' >> ~/incident/constats.txt <<'EOF'
. /etc/default/api-boutique
for s in $(grep -lE "http\.server $API_PORT|PORT=$API_PORT" /etc/init.d/* | xargs -r -n1 basename); do
  [ "$s" = api-boutique ] && continue
  service "$s" stop >/dev/null 2>&1
  update-rc.d -f "$s" remove >/dev/null 2>&1
  echo "Service $s retiré du démarrage du serveur (update-rc.d -f $s remove)."
done
service api-boutique status >/dev/null || service api-boutique restart >/dev/null
EOF
#@ P5.4
{ echo "Rapport d'incident — web3, API des magasins"; echo; echo "Causes et actions :"; sed 's/^/- /' ~/incident/constats.txt | grep -v 'est en marche'; } > ~/incident/rapport.txt
cat ~/incident/rapport.txt
''',
}
