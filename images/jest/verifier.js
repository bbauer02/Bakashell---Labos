#!/usr/bin/env node
/*
 * Correcteur du parcours Jest. Exécuté en root par la plateforme ; les tests de l'étudiant
 * tournent dans un bac à sable, sous l'utilisateur « correcteur » (sans accès au dossier de
 * l'étudiant ni aux fichiers de référence).
 *
 * Code de sortie 0 = vérification réussie. Les lignes « MSG:... » précisent un échec.
 *
 *   deliver [--set ID] chemin...             livre des fichiers dans ~/boutique (sans écraser)
 *   grep    fichier regex                    le fichier (sans ses commentaires) contient le motif
 *   pass    --tests a,b [--src ref|student] [--bug ID] [--min N] [--seeds 1,2] [--isolate]
 *           [--fake-date] [--tz ZONE] [--max-ms N]
 *                                            les tests passent (sur la référence, le code de
 *                                            l'étudiant, ou la référence avec les bugs du jeu ID)
 *   kill    --tests a,b --set ID [--tz ZONE] [--no-hint]
 *                                            les tests échouent contre chaque mutant du jeu
 *   survive --tests a,b --set ID             les tests passent sur chaque variante CORRECTE du jeu
 *   hidden  --set ID[,ID]                    tests cachés du jeu, contre le code de l'étudiant
 *   reproduce --tests a (--set ID [--each] | --ref)
 *                                            les tests échouent contre la version boguée (chaque
 *                                            bug du jeu avec --each), ou contre la référence (--ref)
 *   coverage --tests a --file src/x.js [--branches N] [--lines N]
 *   suite                                    toute la suite de l'étudiant, avec sa config Jest
 *   config  --expr EXPR                      la configuration Jest de l'étudiant (variable c, et
 *                                            where = « package.json » ou « jest.config.js »)
 *   workflow fichier                         workflow GitHub Actions attendu au jour 10
 */
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const LAB = '/opt/jest-lab';
const PRIVATE = path.join(LAB, 'private');
const PROJECT = '/home/etudiant/boutique';
const RUNS = '/var/lib/correcteur';
const JEST = path.join(LAB, 'node_modules', 'jest', 'bin', 'jest.js');
const MUTANTS = JSON.parse(fs.readFileSync(path.join(PRIVATE, 'mutants.json'), 'utf8'));
const ATTEMPTS = '/var/lib/lab/jest-tentatives.json';
// À partir de cette tentative ratée, kill décrit un défaut non détecté
const HINT_AFTER = 3;

// ─── Utilitaires ──────────────────────────────────────────────────────────

function args(argv) {
  const opts = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const key = argv[i].slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) opts[key] = true;
      else { opts[key] = next; i++; }
    } else {
      opts._.push(argv[i]);
    }
  }
  return opts;
}

const list = (v) => (v && v !== true ? String(v).split(',').map((s) => s.trim()).filter(Boolean) : []);
const msg = (text) => console.log(`MSG:${text}`);
const clean = (s) => String(s || '').replace(/\u001b\[[0-9;]*m/g, '').split('\n').map((l) => l.trim()).filter(Boolean);

function fail(text) {
  if (text) msg(text);
  process.exit(1);
}

function sh(cmd, argv, options = {}) {
  return cp.spawnSync(cmd, argv, { encoding: 'utf8', ...options });
}

function applyMutation(root, mutation) {
  const file = path.join(root, mutation.file);
  const code = fs.readFileSync(file, 'utf8');
  if (!code.includes(mutation.from)) {
    throw new Error(`Mutant invalide (${mutation.desc}) : extrait introuvable dans ${mutation.file}`);
  }
  fs.writeFileSync(file, code.replace(mutation.from, mutation.to));
}

function mutantSet(id) {
  const set = MUTANTS[id];
  if (!set) throw new Error(`Jeu de mutants inconnu : ${id}`);
  return set;
}

/** Retire les commentaires d'un code JavaScript (les « // » précédés de « : » sont gardés : URL). */
function stripComments(code) {
  return code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:\\])\/\/.*$/gm, '$1');
}

function readProjectFile(rel) {
  const file = path.join(PROJECT, rel);
  const st = fs.lstatSync(file, { throwIfNoEntry: false });
  if (!st || !st.isFile()) return null;
  return fs.readFileSync(file, 'utf8');
}

// Un test doit vérifier un comportement, pas relire le code source (qui change avec chaque mutant).
const SOURCE_READING = /\b(?:require|requireActual|import)\s*\(\s*['"`](?:node:)?(?:fs|fs\/promises|child_process|vm|module|inspector|worker_threads)['"`]|\bfrom\s+['"](?:node:)?(?:fs|fs\/promises|child_process)['"]|\bprocess\s*\.\s*(?:binding|_linkedBinding|mainModule)\b/;

function forbidSourceReading(tests) {
  for (const t of [...tests, ...helperFiles()]) {
    const code = readProjectFile(t);
    if (code !== null && SOURCE_READING.test(stripComments(code))) {
      fail(`${t} accède au système de fichiers ou aux processus (fs, child_process…) : un test unitaire doit vérifier le comportement du code, pas lire son source.`);
    }
  }
}

// ─── Bac à sable ──────────────────────────────────────────────────────────

let counter = 0;

/** Copie un fichier ordinaire ; les liens symboliques sont refusés (ils pourraient viser des fichiers privés). */
function copyRegular(from, to, label) {
  const st = fs.lstatSync(from, { throwIfNoEntry: false });
  if (!st) fail(`Le fichier ${label} n'existe pas.`);
  if (st.isSymbolicLink()) fail(`${label} est un lien symbolique : seuls les fichiers ordinaires sont acceptés.`);
  if (!st.isFile()) fail(`${label} n'est pas un fichier.`);
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
}

/** Copie récursive d'un dossier, sans suivre les liens symboliques. */
function copyTree(from, to, label, filter = () => true) {
  fs.mkdirSync(to, { recursive: true });
  for (const e of fs.readdirSync(from, { withFileTypes: true })) {
    const rel = path.join(label, e.name);
    if (!filter(rel, e)) continue;
    if (e.isSymbolicLink()) fail(`${rel} est un lien symbolique : seuls les fichiers ordinaires sont acceptés.`);
    if (e.isDirectory()) copyTree(path.join(from, e.name), path.join(to, e.name), rel, filter);
    else if (e.isFile()) fs.copyFileSync(path.join(from, e.name), path.join(to, e.name));
  }
}

/** Fichiers annexes de tests/ (aides, données de test) : tout sauf les *.test.js et les snapshots. */
function helperFiles() {
  const out = [];
  const walk = (rel) => {
    const abs = path.join(PROJECT, rel);
    let entries = [];
    try { entries = fs.readdirSync(abs, { withFileTypes: true }); } catch (e) { return; }
    for (const e of entries) {
      const r = path.join(rel, e.name);
      if (e.isDirectory() && e.name !== '__snapshots__' && e.name !== 'node_modules') walk(r);
      else if (e.isFile() && !e.name.endsWith('.test.js')) out.push(r);
    }
  };
  walk('tests');
  return out;
}

/** Crée un projet temporaire : src (référence ou étudiant), tests de l'étudiant, tests cachés. */
function sandbox({ src = 'ref', tests = [], mutations = [], hiddenSets = [], projectFiles = false }) {
  fs.mkdirSync(RUNS, { recursive: true });
  const dir = fs.mkdtempSync(path.join(RUNS, `run-${process.pid}-${counter++}-`));
  const srcDir = src === 'student' ? path.join(PROJECT, 'src') : path.join(PRIVATE, 'ref', 'src');
  if (!fs.existsSync(srcDir)) fail("Le dossier src/ du projet est introuvable : ouvrez l'étape pour le recréer.");
  copyTree(srcDir, path.join(dir, 'src'), 'src');
  for (const m of mutations) applyMutation(dir, m);
  if (!projectFiles) {
    for (const t of tests) {
      copyRegular(path.join(PROJECT, t), path.join(dir, t), t);
      const snap = path.join(path.dirname(t), '__snapshots__', `${path.basename(t)}.snap`);
      if (fs.existsSync(path.join(PROJECT, snap))) copyRegular(path.join(PROJECT, snap), path.join(dir, snap), snap);
    }
    for (const h of helperFiles()) copyRegular(path.join(PROJECT, h), path.join(dir, h), h);
  }
  for (const set of hiddenSets) {
    fs.cpSync(path.join(PRIVATE, 'hidden', set), path.join(dir, '__hidden__', set), { recursive: true });
  }
  if (projectFiles) {
    for (const f of ['package.json', 'jest.config.js']) {
      if (fs.existsSync(path.join(PROJECT, f))) copyRegular(path.join(PROJECT, f), path.join(dir, f), f);
    }
    if (fs.existsSync(path.join(PROJECT, 'tests'))) {
      copyTree(path.join(PROJECT, 'tests'), path.join(dir, 'tests'), 'tests', (rel) => !rel.includes('node_modules'));
    }
  }
  fs.symlinkSync(path.join(LAB, 'node_modules'), path.join(dir, 'node_modules'));
  return dir;
}

/** Fichier chargé avant chaque fichier de test : le code source des fonctions n'est pas lisible. */
function writeProtection(dir) {
  const file = path.join(dir, '__setup__', 'protection.js');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `
const masque = function toString() { return 'function () { [code masqué] }'; };
Object.defineProperty(Function.prototype, 'toString', { value: masque, writable: false, configurable: false });
`);
  return file;
}

const DATE_SHIFT = `
const CIBLE = new Date('2031-03-15T12:00:00').getTime();
const DateReelle = global.Date;
const ECART = CIBLE - DateReelle.now();
class DateDecalee extends DateReelle {
  constructor(...a) { if (a.length === 0) super(DateReelle.now() + ECART); else super(...a); }
  static now() { return DateReelle.now() + ECART; }
}
global.Date = DateDecalee;
`;

/** Horloge système décalée (15 mars 2031) : dans les tests, et dans Jest lui-même (faux minuteurs). */
function writeFakeDate(dir) {
  const file = path.join(dir, '__setup__', 'date-decalee.js');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, DATE_SHIFT);
  return file;
}

function writeConfig(dir, extra = {}) {
  const setupFiles = [writeProtection(dir), ...(extra.setupFiles || [])];
  const config = {
    rootDir: dir,
    displayName: path.basename(dir),
    testEnvironment: 'node',
    testMatch: ['<rootDir>/tests/**/*.test.js', '<rootDir>/__hidden__/**/*.test.js'],
    ...extra,
    setupFiles,
  };
  fs.writeFileSync(path.join(dir, 'jest.config.js'), `module.exports = ${JSON.stringify(config, null, 2)};\n`);
}

const quote = (a) => `'${String(a).replace(/'/g, "'\\''")}'`;

/** Lance Jest (un « projet » par dossier) sous l'utilisateur correcteur. */
function runJest(dirs, { extraArgs = [], cwd = null, timeoutMs = 120000, tz = null, fakeDate = null } = {}) {
  const out = path.join(RUNS, `resultat-${process.pid}-${counter++}.json`);
  for (const d of dirs) sh('chown', ['-R', 'correcteur:correcteur', d]);
  const base = ['--ci', '--runInBand', '--watchman=false', `--cacheDirectory=${RUNS}/cache`, '--json', `--outputFile=${out}`];
  const target = cwd ? [] : ['--projects', ...dirs];
  const jestArgs = [JEST, ...base, ...target, ...extraArgs].map(quote).join(' ');
  if (tz && !/^[A-Za-z_]+(\/[A-Za-z_+-]+)*$/.test(tz)) throw new Error(`Fuseau invalide : ${tz}`);
  const env = tz ? `TZ=${tz} ` : '';
  const preload = fakeDate ? `--require ${quote(fakeDate)} ` : '';
  const r = sh('su', ['-s', '/bin/sh', 'correcteur', '-c', `cd ${quote(cwd || dirs[0])} && exec env ${env}node ${preload}${jestArgs}`], { timeout: timeoutMs });
  let report = null;
  try { report = JSON.parse(fs.readFileSync(out, 'utf8')); } catch (e) { /* pas de rapport */ }
  fs.rmSync(out, { force: true });
  const timedOut = Boolean(r.error && r.error.code === 'ETIMEDOUT');
  return { timedOut, report, status: r.status, stderr: r.stderr };
}

function summarize(report, dir) {
  const suites = (report ? report.testResults : []).filter((s) => !dir || s.name.startsWith(dir + path.sep));
  let total = 0;
  let failed = 0;
  let firstFailure = null;
  let suiteError = null;
  const names = [];
  for (const s of suites) {
    if (s.status === 'failed' && s.assertionResults.length === 0) {
      suiteError = suiteError || clean(s.message).slice(0, 3).join(' ');
    }
    for (const a of s.assertionResults) {
      if (a.status === 'pending' || a.status === 'todo' || a.status === 'skipped' || a.status === 'disabled') continue;
      total += 1;
      names.push(a.fullName);
      if (a.status === 'failed') {
        failed += 1;
        if (!firstFailure) {
          const lines = clean(a.failureMessages.join('\n'));
          const values = lines.filter((l) => /^(Expected|Received|Snapshot|- Snapshot|\+ Received)/.test(l)).slice(0, 2).join(' ; ');
          firstFailure = { name: a.fullName, detail: values || lines[0] || '' };
        }
      }
    }
  }
  const durationMs = suites.reduce((t, s) => t + ((s.endTime || 0) - (s.startTime || 0)), 0);
  return { total, failed, firstFailure, suiteError, durationMs, names, ok: total > 0 && failed === 0 && !suiteError };
}

function crashDetail(res) {
  const lines = clean(res.stderr).filter((l) => !/^at /.test(l));
  const useful = lines.find((l) => /Error|rejected|Received|Expected/.test(l)) || lines[0] || '';
  return useful.slice(0, 200);
}

function cleanup(dirs) {
  for (const d of dirs) fs.rmSync(d, { recursive: true, force: true });
}

function attempts(key) {
  let data = {};
  try { data = JSON.parse(fs.readFileSync(ATTEMPTS, 'utf8')); } catch (e) { /* premier essai */ }
  data[key] = (data[key] || 0) + 1;
  try {
    fs.mkdirSync(path.dirname(ATTEMPTS), { recursive: true });
    fs.writeFileSync(ATTEMPTS, JSON.stringify(data));
  } catch (e) { /* sans importance */ }
  return data[key];
}

// ─── Commandes ────────────────────────────────────────────────────────────

function cmdDeliver(o) {
  fs.mkdirSync(PROJECT, { recursive: true });
  for (const rel of o._) {
    const dest = path.join(PROJECT, rel);
    if (fs.existsSync(dest)) continue;
    const studentVersion = path.join(PRIVATE, 'student', rel);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    if (fs.existsSync(studentVersion)) {
      fs.copyFileSync(studentVersion, dest);
    } else {
      fs.copyFileSync(path.join(PRIVATE, 'ref', rel), dest);
      if (o.set) {
        for (const m of mutantSet(o.set).filter((x) => x.file === rel)) applyMutation(PROJECT, m);
      }
    }
    fs.chmodSync(dest, 0o644);
  }
  const nm = path.join(PROJECT, 'node_modules');
  if (!fs.lstatSync(nm, { throwIfNoEntry: false })) fs.symlinkSync(path.join(LAB, 'node_modules'), nm);
  sh('chown', ['-R', '-h', 'etudiant:etudiant', PROJECT]);
}

function cmdGrep(o) {
  const [rel, pattern] = o._;
  const code = readProjectFile(rel);
  if (code === null) process.exit(1);
  const text = rel.endsWith('.js') ? stripComments(code) : code;
  process.exit(new RegExp(pattern, o.i ? 'i' : '').test(text) ? 0 : 1);
}

function runOnce(o, tests, { seed = null, testName = null } = {}) {
  const mutations = o.bug ? mutantSet(o.bug) : [];
  const dir = sandbox({ src: o.src || 'ref', tests, mutations });
  const extra = {};
  let fakeDate = null;
  if (o['fake-date']) {
    fakeDate = writeFakeDate(dir);
    extra.setupFiles = [fakeDate];
  }
  writeConfig(dir, extra);
  const extraArgs = [];
  if (seed) extraArgs.push('--randomize', `--seed=${seed}`);
  if (testName !== null) extraArgs.push('-t', `^${testName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`);
  const res = runJest([dir], { extraArgs, tz: o.tz || null, fakeDate });
  const s = summarize(res.report, dir);
  cleanup([dir]);
  return { res, s };
}

function cmdPass(o) {
  const tests = list(o.tests);
  const seeds = list(o.seeds);
  const where = o.src === 'student' ? 'avec votre code' : (o.bug ? 'avec le code actuel (bogué)' : 'avec le code de référence');
  const date = o['fake-date'] ? ' quand on change la date du jour' : '';
  const zone = o.tz ? ` sur une machine réglée sur le fuseau ${o.tz}` : '';
  let names = [];
  for (const seed of (seeds.length ? seeds : [null])) {
    const { res, s } = runOnce(o, tests, { seed });
    const when = seed ? ` (ordre aléatoire, graine ${seed})` : '';
    if (res.timedOut) fail(`Vos tests ne se terminent pas${when} : attendent-ils un vrai délai ?`);
    if (!res.report) fail(`Jest s'est arrêté brutalement${when}${zone} : ${crashDetail(res)} (une assertion sur une promesse non attendue ?)`);
    if (s.suiteError) fail(`La suite ne s'exécute pas : ${s.suiteError}`);
    if (s.total === 0) fail('Aucun test trouvé.');
    if (s.failed) {
      fail(`${s.failed} test(s) échouent ${where}${when}${date}${zone}. Premier échec : « ${s.firstFailure.name} » — ${s.firstFailure.detail}`);
    }
    if (o.min && s.total < Number(o.min)) fail(`Seulement ${s.total} test(s) : il en faut au moins ${o.min}.`);
    if (o['max-ms'] && s.durationMs > Number(o['max-ms'])) {
      fail(`La suite met ${(s.durationMs / 1000).toFixed(1)} s à s'exécuter : elle attend de vrais délais.`);
    }
    names = s.names;
  }
  if (o.isolate) {
    for (const name of names) {
      const { res, s } = runOnce(o, tests, { testName: name });
      if (res.timedOut || !res.report || s.suiteError || s.failed || s.total === 0) {
        const detail = s.firstFailure ? ` — ${s.firstFailure.detail}` : '';
        fail(`Le test « ${name} » échoue quand il est lancé seul (npx jest -t) : il dépend d'un autre test${detail}`);
      }
    }
  }
}

/** Exécute les tests contre chaque mutant ; retourne, pour chacun, s'il a été détecté. */
function runMutants(tests, set, tz) {
  const make = (m) => {
    const d = sandbox({ src: 'ref', tests, mutations: [m] });
    writeConfig(d);
    return d;
  };
  const dirs = set.map(make);
  const res = runJest(dirs, { timeoutMs: 90000, tz });
  if (!res.timedOut && res.report) {
    const detected = dirs.map((d) => {
      const s = summarize(res.report, d);
      return s.failed > 0 || Boolean(s.suiteError);
    });
    cleanup(dirs);
    return detected;
  }
  // Exécution interrompue (délai, arrêt brutal) : on reprend mutant par mutant, pour que seul
  // le mutant en cause soit compté comme détecté.
  cleanup(dirs);
  return set.map((m) => {
    const d = make(m);
    const r = runJest([d], { timeoutMs: 30000, tz });
    const s = summarize(r.report, d);
    cleanup([d]);
    return r.timedOut || !r.report || s.failed > 0 || Boolean(s.suiteError);
  });
}

function cmdKill(o) {
  const tests = list(o.tests);
  forbidSourceReading(tests);
  const set = mutantSet(o.set);
  const detected = runMutants(tests, set, o.tz || null);
  const survivors = set.filter((m, i) => !detected[i]);
  if (!survivors.length) return;
  const n = attempts(`kill:${o.set}`);
  const head = `Vos tests laissent passer ${survivors.length} défaut(s) sur ${set.length}.`;
  if (o['no-hint']) fail(`${head} Cherchez les cas que vos tests ne couvrent pas encore.`);
  if (n < HINT_AFTER) {
    fail(`${head} Cherchez quelles erreurs plausibles vos tests ne verraient pas (un défaut vous sera décrit à partir de la ${HINT_AFTER}e vérification ratée).`);
  }
  fail(`${head} Par exemple : « ${survivors[0].desc} ».`);
}

function cmdSurvive(o) {
  const tests = list(o.tests);
  for (const variant of mutantSet(o.set)) {
    const d = sandbox({ src: 'ref', tests, mutations: [variant] });
    writeConfig(d);
    const r = runJest([d]);
    const s = summarize(r.report, d);
    cleanup([d]);
    if (!s.ok) {
      const first = s.firstFailure ? ` Premier échec : « ${s.firstFailure.name} ».` : '';
      fail(`Vos tests échouent sur une version CORRECTE du code (${variant.desc}) : ils exigent plus que la règle.${first}`);
    }
  }
}

function cmdHidden(o) {
  const dir = sandbox({ src: 'student', hiddenSets: list(o.set) });
  writeConfig(dir, { testMatch: ['<rootDir>/__hidden__/**/*.test.js'] });
  const res = runJest([dir]);
  const s = summarize(res.report, dir);
  cleanup([dir]);
  if (res.timedOut) fail('Les tests de validation ne se terminent pas avec votre code.');
  if (!res.report) fail(`Les tests de validation s'arrêtent brutalement avec votre code : ${crashDetail(res)}`);
  if (s.suiteError) fail(`Votre code ne se charge pas : ${s.suiteError}`);
  if (!s.ok) fail(`${s.failed} test(s) de validation sur ${s.total} échouent. Premier échec : « ${s.firstFailure.name} ».`);
}

function cmdReproduce(o) {
  const tests = list(o.tests);
  forbidSourceReading(tests);
  const runWith = (mutations) => {
    const dir = sandbox({ src: 'ref', tests, mutations });
    writeConfig(dir);
    const res = runJest([dir]);
    const s = summarize(res.report, dir);
    cleanup([dir]);
    if (s.suiteError) fail(`La suite ne s'exécute pas : ${s.suiteError}`);
    return res.timedOut || !res.report || s.failed > 0;
  };
  if (o.ref) {
    if (!runWith([])) fail('Vos tests passent aussi sur la version corrigée : personne ne saura que le bug a été corrigé.');
    return;
  }
  const set = mutantSet(o.set);
  const bugs = o.each ? set : [set[0]];
  for (const bug of bugs) {
    if (!runWith([bug])) {
      if (o.each) fail(`Aucun de vos tests n'échoue quand seul ce bug est présent : « ${bug.desc} ». Il manque un test de non-régression.`);
      fail('Vos tests passent sur la version boguée : ils ne reproduisent pas le bug signalé.');
    }
  }
}

function cmdCoverage(o) {
  const tests = list(o.tests);
  const dir = sandbox({ src: 'ref', tests });
  writeConfig(dir, {
    collectCoverage: true,
    collectCoverageFrom: [o.file],
    coverageReporters: ['json-summary'],
    coverageDirectory: path.join(dir, 'coverage'),
  });
  const res = runJest([dir]);
  const s = summarize(res.report, dir);
  let summary = null;
  try { summary = JSON.parse(fs.readFileSync(path.join(dir, 'coverage', 'coverage-summary.json'), 'utf8')); } catch (e) { /* absent */ }
  cleanup([dir]);
  if (!s.ok) fail('La suite ne passe pas entièrement.');
  const entry = summary && Object.entries(summary).find(([k]) => k.endsWith(o.file));
  if (!entry) fail(`${o.file} n'est pas couvert du tout par vos tests.`);
  const c = entry[1];
  for (const [kind, label] of [['branches', 'branches'], ['lines', 'lignes']]) {
    if (o[kind] && c[kind].pct < Number(o[kind])) {
      fail(`Couverture des ${label} de ${o.file} : ${c[kind].pct} % (objectif : ${o[kind]} %).`);
    }
  }
}

function cmdSuite() {
  const dir = sandbox({ src: 'student', projectFiles: true });
  const res = runJest([dir], { cwd: dir, extraArgs: ['--coverage', '--coverageReporters=text-summary'] });
  const s = summarize(res.report, dir);
  cleanup([dir]);
  const err = clean(res.stderr);
  const multiple = err.find((l) => /Multiple configurations found/.test(l));
  if (multiple) fail('Deux configurations Jest coexistent (clé « jest » de package.json et jest.config.js) : Jest refuse de démarrer.');
  if (res.timedOut) fail('La suite complète ne se termine pas.');
  if (!res.report) fail(`Jest ne démarre pas ou s'arrête brutalement : ${crashDetail(res)}`);
  if (s.suiteError) fail(`Une suite ne s'exécute pas : ${s.suiteError}`);
  if (s.total === 0) fail('Aucun test trouvé dans le projet.');
  if (s.failed) fail(`${s.failed} test(s) échouent. Premier échec : « ${s.firstFailure.name} » — ${s.firstFailure.detail}`);
  if (res.status !== 0) {
    const seuil = err.find((l) => /coverage threshold/i.test(l));
    if (seuil) fail(`Les tests passent, mais un seuil de couverture n'est pas atteint : ${seuil}`);
    const obsolete = err.find((l) => /obsolete|snapshot/i.test(l));
    fail(`Les tests passent, mais Jest termine en erreur : ${obsolete || err[0] || 'code de sortie non nul'}`);
  }
}

/** Charge la configuration Jest de l'étudiant (sous l'utilisateur correcteur : jest.config.js est du code). */
function loadConfig() {
  fs.mkdirSync(RUNS, { recursive: true });
  const dir = fs.mkdtempSync(path.join(RUNS, `config-${process.pid}-`));
  for (const f of ['package.json', 'jest.config.js']) {
    if (fs.existsSync(path.join(PROJECT, f))) copyRegular(path.join(PROJECT, f), path.join(dir, f), f);
  }
  sh('chown', ['-R', 'correcteur:correcteur', dir]);
  const script = `
    const fs = require('fs');
    let pkg = {};
    try { pkg = JSON.parse(fs.readFileSync('package.json', 'utf8')); } catch (e) { pkg = {}; }
    const out = { where: null, c: null, error: null };
    const hasFile = fs.existsSync('jest.config.js');
    if (hasFile && pkg.jest) out.error = 'multiple';
    else if (hasFile) {
      try { out.c = require(process.cwd() + '/jest.config.js'); out.where = 'jest.config.js'; }
      catch (e) { out.error = 'Erreur au chargement de jest.config.js : ' + e.message; }
      if (typeof out.c === 'function') out.error = 'jest.config.js doit exporter un objet';
    } else if (pkg.jest) { out.c = pkg.jest; out.where = 'package.json'; }
    else out.error = 'none';
    process.stdout.write('\\n@@CONFIG@@' + JSON.stringify(out) + '\\n');
  `;
  const r = sh('su', ['-s', '/bin/sh', 'correcteur', '-c', `cd ${quote(dir)} && exec node -e ${quote(script)}`], { timeout: 15000 });
  cleanup([dir]);
  const line = String(r.stdout || '').split('\n').find((l) => l.startsWith('@@CONFIG@@'));
  if (!line) fail('Impossible de lire la configuration de Jest (jest.config.js se termine-t-il ?).');
  const res = JSON.parse(line.slice('@@CONFIG@@'.length));
  if (res.error === 'multiple') fail('Deux configurations Jest coexistent (clé « jest » de package.json et jest.config.js) : Jest refuse de démarrer.');
  if (res.error === 'none') fail('Aucune configuration Jest : ni clé « jest » dans package.json, ni jest.config.js.');
  if (res.error) fail(res.error);
  return res;
}

function cmdConfig(o) {
  const { c, where } = loadConfig();
  let ok = false;
  try {
    ok = Boolean(new Function('c', 'where', `return (${o.expr});`)(c || {}, where));
  } catch (e) { ok = false; }
  process.exit(ok ? 0 : 1);
}

/** Vérifie le workflow GitHub Actions du jour 10 (analyse du YAML, pas une simple recherche de texte). */
function cmdWorkflow(o) {
  const rel = o._[0];
  const text = readProjectFile(rel);
  if (text === null) fail(`Le fichier ${rel} n'existe pas.`);
  const yaml = require(path.join(LAB, 'node_modules', 'js-yaml'));
  let wf;
  try { wf = (yaml.safeLoad || yaml.load)(text); } catch (e) { fail(`Le YAML est invalide : ${String(e.message).split('\n')[0]}`); }
  if (!wf || typeof wf !== 'object') fail('Le workflow est vide.');
  const problems = [];
  const on = wf.on !== undefined ? wf.on : wf.true;
  const events = typeof on === 'string' ? [on] : Array.isArray(on) ? on : (on && typeof on === 'object' ? Object.keys(on) : []);
  if (!events.includes('push') || !events.includes('pull_request')) problems.push('il doit se déclencher sur push ET sur pull_request');
  let pkg = {};
  try { pkg = JSON.parse(readProjectFile('package.json') || '{}'); } catch (e) { pkg = {}; }
  const scripts = pkg.scripts || {};
  const runsCoverage = (run) => String(run).split('\n').some((line) => {
    if (/--coverage\b/.test(line) && /\b(jest|npm)\b/.test(line)) return true;
    const m = line.match(/\bnpm\s+(?:run\s+([\w:.-]+)|(test|t)\b)/);
    const name = m && (m[1] || 'test');
    return Boolean(name && /--coverage\b/.test(scripts[name] || ''));
  });
  const jobs = wf.jobs && typeof wf.jobs === 'object' ? Object.values(wf.jobs) : [];
  if (!jobs.length) problems.push('aucun job défini');
  let best = null;
  for (const job of jobs) {
    const steps = Array.isArray(job && job.steps) ? job.steps : [];
    const found = { checkout: false, versions: null, ci: false, coverage: false };
    for (const st of steps) {
      if (!st || typeof st !== 'object') continue;
      if (typeof st.uses === 'string' && /^actions\/checkout@/.test(st.uses)) found.checkout = true;
      if (typeof st.uses === 'string' && /^actions\/setup-node@/.test(st.uses)) {
        const v = st.with && st.with['node-version'];
        const m = String(v === undefined ? '' : v).match(/^\$\{\{\s*matrix\.([\w-]+)\s*\}\}$/);
        const matrix = job.strategy && job.strategy.matrix;
        found.versions = m ? (matrix && Array.isArray(matrix[m[1]]) ? matrix[m[1]] : []) : (v === undefined ? [] : [v]);
      }
      if (typeof st.run === 'string' && /\bnpm\s+ci\b/.test(st.run)) found.ci = true;
      if (typeof st.run === 'string' && runsCoverage(st.run)) found.coverage = true;
    }
    if (!best || Object.values(found).filter(Boolean).length > Object.values(best).filter(Boolean).length) best = found;
  }
  if (best) {
    if (!best.checkout) problems.push('le code doit être récupéré avec actions/checkout');
    if (!best.versions) problems.push('Node doit être installé avec actions/setup-node');
    else {
      const majors = best.versions.map((v) => parseInt(String(v).replace(/^v/, ''), 10));
      if (!majors.includes(22) || !majors.includes(24)) problems.push(`les tests doivent tourner sur Node 22 ET Node 24 (versions trouvées : ${best.versions.join(', ') || 'aucune'})`);
      else if (majors.some((m) => !(m >= 22))) problems.push('aucune version de Node en fin de vie (avant la 22) ne doit rester');
    }
    if (!best.ci) problems.push('les dépendances doivent être installées avec npm ci');
    if (!best.coverage) problems.push('une étape doit lancer les tests avec la couverture (--coverage)');
  }
  if (!fs.existsSync(path.join(PROJECT, 'package-lock.json'))) problems.push('package-lock.json est absent du projet : npm ci en a besoin');
  if (problems.length) fail(`Workflow incomplet : ${problems.join(' ; ')}.`);
}

const COMMANDS = {
  deliver: cmdDeliver, grep: cmdGrep, pass: cmdPass, kill: cmdKill, survive: cmdSurvive, hidden: cmdHidden,
  reproduce: cmdReproduce, coverage: cmdCoverage, suite: cmdSuite, config: cmdConfig, workflow: cmdWorkflow,
};

const [command, ...rest] = process.argv.slice(2);
if (!COMMANDS[command]) {
  console.error(`Commande inconnue : ${command}`);
  process.exit(2);
}
try {
  COMMANDS[command](args(rest));
} catch (e) {
  msg(`Erreur du correcteur : ${e.message}`);
  process.exit(3);
}
