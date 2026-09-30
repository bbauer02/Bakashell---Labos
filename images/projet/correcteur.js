#!/usr/bin/env node
/*
 * Correcteur de la mission 1 du projet final (tests Jest de l'étudiant et correction du bug).
 * Exécuté en root par les mises en place et les vérifications ; les tests de l'étudiant tournent dans un bac à
 * sable, sous l'utilisateur « correcteur » (sans accès au dossier de l'étudiant ni aux fichiers privés).
 * Code de sortie 0 = vérification réussie ; les lignes « MSG:... » précisent un échec (sans donner la solution).
 *
 *   livrer DOSSIER                      écrit le projet d'origine de l'étudiant (avec son bug) dans DOSSIER
 *   ticket                              texte du ticket du bug de l'étudiant
 *   valeur CLE                          une donnée de la variante (tests du parcours)
 *   pass --tests a,b|tout --src ref|etudiant [--bug]
 *                                       les tests passent (code juste, code de l'étudiant, ou code bogué d'origine)
 *   reproduit --tests a                 les tests échouent sur le code bogué d'origine
 *   tue                                 la suite de l'étudiant échoue contre chaque version boguée plausible
 *   valide                              tests de validation cachés, contre le code de l'étudiant
 *   suite                               toute la suite de l'étudiant passe avec son code, sans test retiré ni ignoré
 *
 * Données de l'étudiant (tirées à la mise en place) : /var/lib/docker/lab-projet (BUG, SEUIL, FRAIS, QTE, TAUX,
 * TICKET, W). Les fichiers privés contiennent des marqueurs {{NOM}}, remplacés par ces valeurs.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const LAB = '/opt/projet-lab';
const PRIVE = path.join(LAB, 'prive');
const MODELE = path.join(PRIVE, 'boutique');
const ETAT = '/var/lib/docker/lab-projet';
const PROJET = '/home/etudiant/boutique';
const RUNS = '/var/lib/correcteur';
const JEST = path.join(LAB, 'node_modules', 'jest', 'bin', 'jest.js');
const VARIANTES = JSON.parse(fs.readFileSync(path.join(PRIVE, 'variantes.json'), 'utf8')).variantes;
// Tests livrés dans tests/devis.test.js (dont le test « complice » du bug) : aucun ne doit disparaître
const TESTS_LIVRES = 7;

// ─── Utilitaires ──────────────────────────────────────────────────────────

function options(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const suivant = argv[i + 1];
      if (suivant === undefined || suivant.startsWith('--')) o[argv[i].slice(2)] = true;
      else { o[argv[i].slice(2)] = suivant; i++; }
    } else o._.push(argv[i]);
  }
  return o;
}

const msg = (texte) => console.log(`MSG:${texte}`);
function echec(texte) {
  if (texte) msg(texte);
  process.exit(1);
}
const propre = (s) => String(s || '').replace(/\u001b\[[0-9;]*m/g, '').split('\n').map((l) => l.trim()).filter(Boolean);
const arrondi = (x) => Math.round(Number((x * 100).toFixed(6))) / 100;
const cts = (x) => Math.round(Number((x * 100).toFixed(6)));
const fr = (x) => x.toFixed(2).replace('.', ',');

// ─── Variante de l'étudiant ───────────────────────────────────────────────

function lire(cle) {
  const f = path.join(ETAT, cle);
  if (!fs.existsSync(f)) throw new Error(`donnée ${cle} absente (la mise en place a-t-elle été jouée ?)`);
  return fs.readFileSync(f, 'utf8').trim();
}

let cache = null;
function valeurs() {
  if (cache) return cache;
  const SEUIL = Number(lire('SEUIL'));
  const FRAIS = Number(lire('FRAIS'));
  const QTE = Number(lire('QTE'));
  const TAUX = Number(lire('TAUX'));
  const SEUIL_HT = Math.round(SEUIL / 1.2);
  // Article dont QTE exemplaires atteignent le seuil avant remise, mais plus après (bug « seuil avant remise »)
  let c = Math.floor((SEUIL * 100) / (QTE * 1.2));
  let brut;
  let net;
  for (;; c++) {
    brut = cts(c / 100 * 1.2) * QTE;
    net = brut - Math.round((brut * TAUX) / 100);
    if (brut >= SEUIL * 100 && net < SEUIL * 100) break;
  }
  cache = {
    VERSION: lire('W'), TICKET: lire('TICKET'), SEUIL, SEUIL_HT, SOUS_HT: SEUIL_HT - 0.5,
    FRAIS: String(FRAIS), FRAIS_FR: fr(FRAIS), QTE, TAUX,
    TOTAL_PETITE: arrondi(24 + FRAIS), REMISE_TENTE: arrondi((120 * TAUX) / 100),
    V2_HT: c / 100, V2_HT_FR: fr(c / 100), V2_BRUT: brut / 100, V2_BRUT_FR: fr(brut / 100), V2_NET_FR: fr(net / 100),
    COMPLICE_PRIX: '', COMPLICE_DEVIS: '',
  };
  const v = variante();
  cache[v.complice.zone] = v.complice.code;
  return cache;
}

function variante() {
  const n = Number(lire('BUG'));
  if (!VARIANTES[n]) throw new Error(`variante de bug inconnue : ${n}`);
  return VARIANTES[n];
}

function rendre(texte) {
  let t = String(texte);
  for (let i = 0; i < 3 && t.includes('{{'); i++) {
    t = t.replace(/\{\{(\w+)\}\}/g, (m, nom) => {
      if (!(nom in valeurs())) throw new Error(`marqueur inconnu : ${nom}`);
      return String(valeurs()[nom]);
    });
  }
  return t;
}

function muter(fichier, { from, to }) {
  const code = fs.readFileSync(fichier, 'utf8');
  if (!code.includes(from)) throw new Error(`mutation impossible dans ${fichier} : ${from}`);
  fs.writeFileSync(fichier, code.replace(from, to));
}

function rendreArbre(dossier) {
  for (const e of fs.readdirSync(dossier, { withFileTypes: true })) {
    const f = path.join(dossier, e.name);
    if (e.isDirectory()) rendreArbre(f);
    else if (e.isFile()) {
      const t = fs.readFileSync(f, 'utf8');
      if (t.includes('{{')) fs.writeFileSync(f, rendre(t));
    }
  }
}

// ─── Bac à sable ──────────────────────────────────────────────────────────

let compteur = 0;

function copieFichier(de, vers, nom) {
  const st = fs.lstatSync(de, { throwIfNoEntry: false });
  if (!st) echec(`Le fichier ${nom} n'existe pas.`);
  if (st.isSymbolicLink()) echec(`${nom} est un lien symbolique : seuls les fichiers ordinaires sont acceptés.`);
  if (!st.isFile()) echec(`${nom} n'est pas un fichier.`);
  fs.mkdirSync(path.dirname(vers), { recursive: true });
  fs.copyFileSync(de, vers);
}

function copieArbre(de, vers, nom) {
  fs.mkdirSync(vers, { recursive: true });
  for (const e of fs.readdirSync(de, { withFileTypes: true })) {
    const rel = path.join(nom, e.name);
    if (e.name === 'node_modules' || e.name === '__snapshots__') continue;
    if (e.isSymbolicLink()) echec(`${rel} est un lien symbolique : seuls les fichiers ordinaires sont acceptés.`);
    if (e.isDirectory()) copieArbre(path.join(de, e.name), path.join(vers, e.name), rel);
    else if (e.isFile()) fs.copyFileSync(path.join(de, e.name), path.join(vers, e.name));
  }
}

/** Fichiers de tests/ de l'étudiant (chemins relatifs au projet). */
function fichiersTests() {
  const out = [];
  const parcours = (rel) => {
    let entrees = [];
    try { entrees = fs.readdirSync(path.join(PROJET, rel), { withFileTypes: true }); } catch (e) { return; }
    for (const e of entrees) {
      const r = path.join(rel, e.name);
      if (e.isDirectory() && e.name !== 'node_modules' && e.name !== '__snapshots__') parcours(r);
      else if (e.isFile() || e.isSymbolicLink()) out.push(r);
    }
  };
  parcours('tests');
  return out;
}

// Un test doit vérifier un comportement, pas relire le code source (qui change avec chaque version boguée)
const LECTURE_SOURCE = /\b(?:require|requireActual|import)\s*\(\s*['"`](?:node:)?(?:fs|fs\/promises|child_process|vm|module|inspector|worker_threads)['"`]|\bfrom\s+['"](?:node:)?(?:fs|fs\/promises|child_process)['"]|\bprocess\s*\.\s*(?:binding|_linkedBinding|mainModule)\b/;
const sansCommentaires = (code) => code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:\\])\/\/.*$/gm, '$1');

function interdireLectureSource() {
  for (const t of fichiersTests()) {
    const f = path.join(PROJET, t);
    if (!fs.lstatSync(f).isFile()) continue;
    if (LECTURE_SOURCE.test(sansCommentaires(fs.readFileSync(f, 'utf8')))) {
      echec(`${t} accède au système de fichiers ou aux processus (fs, child_process…) : un test doit vérifier le comportement du code, pas lire son source.`);
    }
  }
}

/** Projet temporaire : src (juste, bogué, muté ou de l'étudiant), tests de l'étudiant et/ou tests cachés. */
function bacASable({ src = 'ref', tests = [], mutations = [], caches = false }) {
  fs.mkdirSync(RUNS, { recursive: true });
  const d = fs.mkdtempSync(path.join(RUNS, `run-${process.pid}-${compteur++}-`));
  if (src === 'etudiant') {
    if (!fs.existsSync(path.join(PROJET, 'src'))) echec('Le dossier src/ de ~/boutique est introuvable.');
    copieArbre(path.join(PROJET, 'src'), path.join(d, 'src'), 'src');
  } else {
    copieArbre(path.join(MODELE, 'src'), path.join(d, 'src'), 'src');
    for (const m of mutations) muter(path.join(d, 'src', 'devis.js'), m);
    rendreArbre(path.join(d, 'src'));
  }
  for (const t of tests) copieFichier(path.join(PROJET, t), path.join(d, t), t);
  if (caches) {
    fs.mkdirSync(path.join(d, '__caches__', 'validation'), { recursive: true });
    fs.writeFileSync(path.join(d, '__caches__', 'validation', 'devis.hidden.test.js'),
      rendre(fs.readFileSync(path.join(PRIVE, 'hidden', 'devis.hidden.test.js'), 'utf8')));
  }
  // Le code source des fonctions n'est pas lisible depuis les tests
  fs.mkdirSync(path.join(d, '__setup__'), { recursive: true });
  fs.writeFileSync(path.join(d, '__setup__', 'protection.js'),
    "Object.defineProperty(Function.prototype, 'toString', { value: function toString() { return 'function () { [code masqué] }'; }, writable: false, configurable: false });\n");
  const config = {
    rootDir: d, testEnvironment: 'node', setupFiles: ['<rootDir>/__setup__/protection.js'],
    testMatch: caches ? ['<rootDir>/__caches__/**/*.test.js'] : ['<rootDir>/tests/**/*.test.js'],
  };
  fs.writeFileSync(path.join(d, 'jest.config.js'), `module.exports = ${JSON.stringify(config)};\n`);
  fs.symlinkSync(path.join(LAB, 'node_modules'), path.join(d, 'node_modules'));
  return d;
}

const q = (a) => `'${String(a).replace(/'/g, "'\\''")}'`;

/** Lance Jest sous l'utilisateur correcteur ; renvoie le rapport JSON. */
function jest(dossiers, delai = 90000) {
  const sortie = path.join(RUNS, `resultat-${process.pid}-${compteur++}.json`);
  for (const d of dossiers) cp.spawnSync('chown', ['-R', 'correcteur:correcteur', d]);
  const args = [JEST, '--ci', '--runInBand', '--watchman=false', `--cacheDirectory=${RUNS}/cache`, '--json',
    `--outputFile=${sortie}`, '--projects', ...dossiers].map(q).join(' ');
  const r = cp.spawnSync('su', ['-s', '/bin/sh', 'correcteur', '-c', `cd ${q(dossiers[0])} && exec node ${args}`],
    { encoding: 'utf8', timeout: delai });
  let rapport = null;
  try { rapport = JSON.parse(fs.readFileSync(sortie, 'utf8')); } catch (e) { /* aucun rapport */ }
  fs.rmSync(sortie, { force: true });
  return { rapport, delai: Boolean(r.error && r.error.code === 'ETIMEDOUT'), stderr: r.stderr };
}

function bilan(rapport, dossier) {
  const suites = (rapport ? rapport.testResults : []).filter((s) => !dossier || s.name.startsWith(dossier + path.sep));
  const b = { total: 0, echecs: 0, premier: null, erreur: null, parFichier: {} };
  for (const s of suites) {
    if (s.status === 'failed' && s.assertionResults.length === 0) b.erreur = b.erreur || propre(s.message).slice(0, 2).join(' ');
    const rel = path.relative(dossier || '', s.name);
    for (const a of s.assertionResults) {
      if (['pending', 'todo', 'skipped', 'disabled'].includes(a.status)) continue;
      b.total += 1;
      b.parFichier[rel] = (b.parFichier[rel] || 0) + 1;
      if (a.status === 'failed') {
        b.echecs += 1;
        b.premier = b.premier || a.fullName;
      }
    }
  }
  return b;
}

function nettoyer(dossiers) {
  for (const d of dossiers) fs.rmSync(d, { recursive: true, force: true });
}

function lancer(opts) {
  const d = bacASable(opts);
  const r = jest([d]);
  const b = bilan(r.rapport, d);
  nettoyer([d]);
  return { r, b };
}

const listeTests = (o) => (o.tests === 'tout' || !o.tests ? fichiersTests() : String(o.tests).split(','));

// ─── Commandes ────────────────────────────────────────────────────────────

function cmdLivrer(o) {
  const dest = o._[0];
  fs.rmSync(dest, { recursive: true, force: true });
  fs.cpSync(MODELE, dest, { recursive: true });
  muter(path.join(dest, 'src', 'devis.js'), variante().bug);
  rendreArbre(dest);
  // Droits ordinaires (les fichiers privés sont réservés à root) ; seul le script de service est exécutable
  const droits = (d) => {
    fs.chmodSync(d, 0o755);
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      if (e.isDirectory()) droits(path.join(d, e.name));
      else fs.chmodSync(path.join(d, e.name), 0o644);
    }
  };
  droits(dest);
  fs.chmodSync(path.join(dest, 'deploiement', 'api-boutique'), 0o755);
  const verrou = path.join(dest, 'package-lock.json');
  const lock = JSON.parse(fs.readFileSync(verrou, 'utf8'));
  lock.version = valeurs().VERSION;
  lock.packages[''].version = valeurs().VERSION;
  fs.writeFileSync(verrou, `${JSON.stringify(lock, null, 2)}\n`);
}

function cmdPass(o) {
  const tests = listeTests(o);
  if (!tests.length) echec('Aucun fichier de tests dans ~/boutique/tests.');
  const src = o.src === 'etudiant' ? 'etudiant' : 'ref';
  const { r, b } = lancer({ src, tests, mutations: o.bug ? [variante().bug] : [] });
  const avec = src === 'etudiant' ? 'avec votre code' : (o.bug ? 'avec le code bogué d\'origine' : 'avec une version corrigée du code');
  if (r.delai) echec(`Les tests ne se terminent pas ${avec}.`);
  if (!r.rapport) echec(`Jest s'arrête brutalement ${avec}.`);
  if (b.erreur) echec(`Un fichier de tests ne s'exécute pas : ${b.erreur}`);
  if (!b.total) echec('Aucun test trouvé.');
  if (b.echecs) echec(`${b.echecs} test(s) échouent ${avec}. Premier échec : « ${b.premier} ».`);
}

function cmdReproduit(o) {
  interdireLectureSource();
  const { r, b } = lancer({ src: 'ref', tests: listeTests(o), mutations: [variante().bug] });
  if (b.erreur) echec(`Un fichier de tests ne s'exécute pas : ${b.erreur}`);
  if (!(r.delai || !r.rapport || b.echecs > 0)) echec('Sur le code bogué d\'origine, tous ces tests passent.');
}

function cmdTue() {
  interdireLectureSource();
  const tests = fichiersTests();
  const jeu = variante().tuer;
  const dossiers = jeu.map((m) => bacASable({ src: 'ref', tests, mutations: [m] }));
  const r = jest(dossiers, 120000);
  const detectes = dossiers.map((d) => {
    const b = bilan(r.rapport, d);
    return r.delai || !r.rapport || b.echecs > 0 || Boolean(b.erreur);
  });
  nettoyer(dossiers);
  const survivants = detectes.filter((x) => !x).length;
  if (survivants) echec(`Votre suite laisse passer ${survivants} version(s) boguée(s) plausible(s) du calcul sur ${jeu.length}.`);
}

function cmdValide() {
  const { r, b } = lancer({ src: 'etudiant', caches: true });
  if (r.delai) echec('Les tests de validation ne se terminent pas avec votre code.');
  if (!r.rapport) echec('Les tests de validation s\'arrêtent brutalement avec votre code.');
  if (b.erreur) echec(`Votre code ne se charge pas : ${b.erreur}`);
  if (b.echecs) echec(`${b.echecs} test(s) de validation sur ${b.total} échouent.`);
}

const FOCUS = /(^|[^\w$.])(fit|fdescribe|xit|xtest|xdescribe)\s*\(|\b(test|it|describe)(\.\w+)*\.(only|skip)\b/;

function cmdSuite() {
  const tests = fichiersTests();
  for (const t of tests) {
    const f = path.join(PROJET, t);
    if (fs.lstatSync(f).isFile() && FOCUS.test(sansCommentaires(fs.readFileSync(f, 'utf8')))) {
      echec(`${t} contient un test désactivé ou isolé (.skip, .only, xit…).`);
    }
  }
  const { r, b } = lancer({ src: 'etudiant', tests });
  if (r.delai || !r.rapport) echec('La suite ne se termine pas ou s\'arrête brutalement.');
  if (b.erreur) echec(`Un fichier de tests ne s'exécute pas : ${b.erreur}`);
  if (b.echecs) echec(`${b.echecs} test(s) échouent avec votre code. Premier échec : « ${b.premier} ».`);
  const livres = b.parFichier[path.join('tests', 'devis.test.js')] || 0;
  if (livres < TESTS_LIVRES) echec(`tests/devis.test.js compte ${livres} test(s) au lieu d'au moins ${TESTS_LIVRES} : un test existant a disparu.`);
}

const COMMANDES = {
  livrer: cmdLivrer, pass: cmdPass, reproduit: cmdReproduit, tue: cmdTue, valide: cmdValide, suite: cmdSuite,
  ticket: () => process.stdout.write(rendre(variante().ticket)),
  valeur: (o) => console.log(valeurs()[o._[0]]),
};

const [commande, ...reste] = process.argv.slice(2);
if (!COMMANDES[commande]) {
  console.error(`Commande inconnue : ${commande}`);
  process.exit(2);
}
try {
  COMMANDES[commande](options(reste));
} catch (e) {
  msg(`Erreur du correcteur : ${e.message}`);
  process.exit(3);
}
