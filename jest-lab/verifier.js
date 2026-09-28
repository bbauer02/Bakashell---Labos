#!/usr/bin/env node
/*
 * Correcteur du parcours Jest. Exécuté en root par la plateforme ; les tests de l'étudiant
 * tournent dans un bac à sable, sous l'utilisateur « correcteur » (sans accès au dossier de
 * l'étudiant ni aux fichiers de référence).
 *
 * Code de sortie 0 = vérification réussie. Les lignes « MSG:... » précisent un échec.
 *
 *   deliver [--set ID] chemin...            livre des fichiers dans ~/boutique (sans écraser)
 *   pass    --tests a,b [--src ref|student] [--min N] [--seeds 1,2] [--fake-date] [--max-ms N]
 *   kill    --tests a,b --set ID            les tests doivent échouer contre chaque mutant du jeu
 *   hidden  --set ID                        tests cachés du jeu, contre le code de l'étudiant
 *   reproduce --tests a --set ID            les tests doivent échouer contre la version boguée
 *   coverage --tests a --file src/x.js [--branches N] [--lines N]
 *   suite                                   toute la suite de l'étudiant, avec sa config Jest
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

const list = (v) => (v ? String(v).split(',').map((s) => s.trim()).filter(Boolean) : []);
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

// ─── Bac à sable ──────────────────────────────────────────────────────────

let counter = 0;

/** Crée un projet temporaire : src (référence ou étudiant), tests de l'étudiant, tests cachés. */
function sandbox({ src = 'ref', tests = [], mutation = null, hiddenSet = null, projectFiles = false }) {
  fs.mkdirSync(RUNS, { recursive: true });
  const dir = fs.mkdtempSync(path.join(RUNS, `run-${process.pid}-${counter++}-`));
  const srcDir = src === 'student' ? path.join(PROJECT, 'src') : path.join(PRIVATE, 'ref', 'src');
  if (!fs.existsSync(srcDir)) fail("Le dossier src/ du projet est introuvable : ouvrez l'étape pour le recréer.");
  fs.cpSync(srcDir, path.join(dir, 'src'), { recursive: true, dereference: true });
  if (mutation) applyMutation(dir, mutation);
  for (const t of tests) {
    const from = path.join(PROJECT, t);
    if (!fs.existsSync(from)) fail(`Le fichier ${t} n'existe pas.`);
    fs.mkdirSync(path.dirname(path.join(dir, t)), { recursive: true });
    fs.copyFileSync(from, path.join(dir, t));
  }
  if (hiddenSet) {
    fs.cpSync(path.join(PRIVATE, 'hidden', hiddenSet), path.join(dir, '__hidden__'), { recursive: true });
  }
  if (projectFiles) {
    for (const f of ['package.json']) {
      if (fs.existsSync(path.join(PROJECT, f))) fs.copyFileSync(path.join(PROJECT, f), path.join(dir, f));
    }
    if (fs.existsSync(path.join(PROJECT, 'jest.config.js'))) {
      fs.copyFileSync(path.join(PROJECT, 'jest.config.js'), path.join(dir, 'jest.config.js'));
    }
    if (fs.existsSync(path.join(PROJECT, 'tests'))) {
      fs.cpSync(path.join(PROJECT, 'tests'), path.join(dir, 'tests'), { recursive: true, dereference: true });
    }
  }
  fs.symlinkSync(path.join(LAB, 'node_modules'), path.join(dir, 'node_modules'));
  return dir;
}

function writeConfig(dir, extra = {}) {
  const config = {
    rootDir: dir,
    displayName: path.basename(dir),
    testEnvironment: 'node',
    testMatch: ['<rootDir>/tests/**/*.test.js', '<rootDir>/__hidden__/**/*.test.js'],
    ...extra,
  };
  fs.writeFileSync(path.join(dir, 'jest.config.js'), `module.exports = ${JSON.stringify(config, null, 2)};\n`);
}

function writeFakeDate(dir) {
  const file = path.join(dir, '__setup__', 'date-fixe.js');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `
const FIXE = new Date('2031-03-15T12:00:00').getTime();
const DateReelle = Date;
class DateFixe extends DateReelle {
  constructor(...a) { if (a.length === 0) super(FIXE); else super(...a); }
  static now() { return FIXE; }
}
global.Date = DateFixe;
`);
  return file;
}

/** Lance Jest (un « projet » par dossier) sous l'utilisateur correcteur. */
function runJest(dirs, { extraArgs = [], cwd = null, timeoutMs = 120000 } = {}) {
  const out = path.join(RUNS, `resultat-${process.pid}-${counter++}.json`);
  for (const d of dirs) sh('chown', ['-R', 'correcteur:correcteur', d]);
  const base = ['--ci', '--runInBand', '--watchman=false', `--cacheDirectory=${RUNS}/cache`, '--json', `--outputFile=${out}`];
  const target = cwd ? [] : ['--projects', ...dirs];
  const jestArgs = [JEST, ...base, ...target, ...extraArgs].map((a) => `'${a.replace(/'/g, "'\\''")}'`).join(' ');
  const r = sh('su', ['-s', '/bin/sh', 'correcteur', '-c', `cd '${cwd || dirs[0]}' && exec node ${jestArgs}`], { timeout: timeoutMs });
  let report = null;
  try { report = JSON.parse(fs.readFileSync(out, 'utf8')); } catch (e) { /* pas de rapport */ }
  fs.rmSync(out, { force: true });
  if (r.error && r.error.code === 'ETIMEDOUT') {
    return { timedOut: true, report, status: r.status, stderr: r.stderr };
  }
  return { timedOut: false, report, status: r.status, stderr: r.stderr };
}

function summarize(report, dir) {
  const suites = (report ? report.testResults : []).filter((s) => !dir || s.name.startsWith(dir + path.sep));
  let total = 0;
  let failed = 0;
  let firstFailure = null;
  let suiteError = null;
  for (const s of suites) {
    if (s.status === 'failed' && s.assertionResults.length === 0) {
      suiteError = suiteError || clean(s.message).slice(0, 3).join(' ');
    }
    for (const a of s.assertionResults) {
      if (a.status === 'pending' || a.status === 'todo' || a.status === 'skipped') continue;
      total += 1;
      if (a.status === 'failed') {
        failed += 1;
        if (!firstFailure) {
          const lines = clean(a.failureMessages.join('\n'));
          const values = lines.filter((l) => /^(Expected|Received)/.test(l)).slice(0, 2).join(' ; ');
          firstFailure = { name: a.fullName, detail: values || lines[0] || '' };
        }
      }
    }
  }
  const durationMs = suites.reduce((t, s) => t + ((s.endTime || 0) - (s.startTime || 0)), 0);
  return { total, failed, firstFailure, suiteError, durationMs, ok: total > 0 && failed === 0 && !suiteError };
}

function cleanup(dirs) {
  for (const d of dirs) fs.rmSync(d, { recursive: true, force: true });
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
  if (!fs.existsSync(nm)) fs.symlinkSync(path.join(LAB, 'node_modules'), nm);
  sh('chown', ['-R', '-h', 'etudiant:etudiant', PROJECT]);
}

function cmdPass(o) {
  const tests = list(o.tests);
  const seeds = list(o.seeds);
  const runs = seeds.length ? seeds : [null];
  for (const seed of runs) {
    const dir = sandbox({ src: o.src || 'ref', tests });
    const extra = {};
    if (o['fake-date']) extra.setupFiles = [writeFakeDate(dir)];
    writeConfig(dir, extra);
    const res = runJest([dir], { extraArgs: seed ? ['--randomize', `--seed=${seed}`] : [] });
    const s = summarize(res.report, dir);
    cleanup([dir]);
    const where = o.src === 'student' ? 'avec votre code' : 'avec le code de référence';
    const when = seed ? ` (ordre aléatoire, graine ${seed})` : '';
    const date = o['fake-date'] ? ' quand on change la date du jour' : '';
    if (res.timedOut) fail(`Vos tests ne se terminent pas${when} : attendent-ils un vrai délai ?`);
    if (s.suiteError) fail(`La suite ne s'exécute pas : ${s.suiteError}`);
    if (s.total === 0) fail('Aucun test trouvé.');
    if (s.failed) {
      fail(`${s.failed} test(s) échouent ${where}${when}${date}. Premier échec : « ${s.firstFailure.name} » — ${s.firstFailure.detail}`);
    }
    if (o.min && s.total < Number(o.min)) fail(`Seulement ${s.total} test(s) : il en faut au moins ${o.min}.`);
    if (o['max-ms'] && s.durationMs > Number(o['max-ms'])) {
      fail(`La suite met ${Math.round(s.durationMs / 1000)} s à s'exécuter : elle attend de vrais délais.`);
    }
  }
}

function cmdKill(o) {
  const tests = list(o.tests);
  const set = mutantSet(o.set);
  const dirs = set.map((m) => {
    const d = sandbox({ src: 'ref', tests, mutation: m });
    writeConfig(d);
    return d;
  });
  const res = runJest(dirs, { timeoutMs: 180000 });
  const survivors = [];
  dirs.forEach((d, i) => {
    const s = summarize(res.report, d);
    const killed = s.failed > 0 || s.suiteError || (res.timedOut && !s.total);
    if (!killed) survivors.push(set[i].desc);
  });
  cleanup(dirs);
  if (survivors.length) {
    fail(`Vos tests laissent passer ${survivors.length} défaut(s) sur ${set.length}. Par exemple : « ${survivors[0]} ».`);
  }
}

function cmdHidden(o) {
  const dir = sandbox({ src: 'student', hiddenSet: o.set });
  writeConfig(dir, { testMatch: ['<rootDir>/__hidden__/**/*.test.js'] });
  const res = runJest([dir]);
  const s = summarize(res.report, dir);
  cleanup([dir]);
  if (res.timedOut) fail('Les tests de validation ne se terminent pas avec votre code.');
  if (s.suiteError) fail(`Votre code ne se charge pas : ${s.suiteError}`);
  if (!s.ok) fail(`${s.failed} test(s) de validation sur ${s.total} échouent. Premier échec : « ${s.firstFailure.name} ».`);
}

function cmdReproduce(o) {
  const tests = list(o.tests);
  const [bug] = mutantSet(o.set);
  const dir = sandbox({ src: 'ref', tests, mutation: bug });
  writeConfig(dir);
  const res = runJest([dir]);
  const s = summarize(res.report, dir);
  cleanup([dir]);
  if (s.suiteError) fail(`La suite ne s'exécute pas : ${s.suiteError}`);
  if (s.failed === 0) fail("Vos tests passent sur la version boguée : ils ne reproduisent pas le bug signalé.");
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
  if (res.timedOut) fail('La suite complète ne se termine pas.');
  if (s.suiteError) fail(`Une suite ne s'exécute pas : ${s.suiteError}`);
  if (s.total === 0) fail('Aucun test trouvé dans le projet.');
  if (s.failed) fail(`${s.failed} test(s) échouent. Premier échec : « ${s.firstFailure.name} » — ${s.firstFailure.detail}`);
  if (res.status !== 0) fail("Les tests passent mais Jest termine en erreur : les seuils de couverture de votre configuration ne sont pas atteints.");
}

const COMMANDS = { deliver: cmdDeliver, pass: cmdPass, kill: cmdKill, hidden: cmdHidden, reproduce: cmdReproduce, coverage: cmdCoverage, suite: cmdSuite };

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
