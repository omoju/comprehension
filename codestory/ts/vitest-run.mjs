// Run spec files of a Vite / Vue frontend under the tracer: the frontend counterpart of register.mjs.
//
//   cd <package> && CS_TRACE_OUT=/abs/trace.json node /abs/codestory/ts/vitest-run.mjs tests/unit/foo.spec.ts
//
// Vitest comes from codestory/ts/web (`npm install` there once), so the traced repo needs no test runner of its own
// and nothing is installed into it. The package's vitest.config.* or vite.config.* is loaded for its resolve, define,
// plugins and test settings (server, build and dependency pre-bundling are dropped); the codestory plugin goes first.
// One worker runs each spec file in jsdom (or the environment the config names) with runtime.mjs loaded before it, so
// a single process writes the trace. Vite's cache goes to a temporary directory: nothing is written into the package.
//
// Environment, as for register.mjs: CS_TRACE_OUT (required), CS_INCLUDE (default src/), CS_SOFT_IMPORTS=1, CS_TEST,
// CS_MAX_CALLS. Also CS_ENVIRONMENT to override the test environment, and CS_INSTRUMENT=0 to run the same setup
// without the plugin, to compare against.
// Exit code: 0 every test passed, 1 some failed, 2 the run itself broke (no spec, a spec that doesn't load).

import { createRequire, register } from 'node:module'
import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, relative } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import codestory from './vite-plugin.mjs'

const here = fileURLToPath(new URL('.', import.meta.url))
const specs = process.argv.slice(2)
const out = process.env.CS_TRACE_OUT
const pkg = process.cwd()

function fail(message) {
  console.error(`[codestory] ${message}`)
  process.exit(2)
}

if (!specs.length || !out) fail('usage: CS_TRACE_OUT=/abs/trace.json node vitest-run.mjs <spec>... (from the package)')
for (const spec of specs) if (!existsSync(join(pkg, spec))) fail(`no such spec: ${spec}`)

let startVitest, loadConfigFromFile
try {
  const web = createRequire(join(here, 'web', 'package.json'))
  ;({ startVitest } = await import(pathToFileURL(web.resolve('vitest/node')).href))
  ;({ loadConfigFromFile } = await import(pathToFileURL(web.resolve('vite')).href))
} catch (e) {
  fail(`Vitest is not installed: run \`npm install\` in ${join(here, 'web')} (${e.message})`)
}

const git = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd: pkg, encoding: 'utf8' }).trim()
const include = (process.env.CS_INCLUDE ?? 'src/').split(',').map((s) => s.trim()).filter(Boolean)
const soft = process.env.CS_SOFT_IMPORTS === '1'
process.env.VITEST_SKIP_INSTALL_CHECKS = '1' // a missing package is an error, never an offer to install it here

// As Vitest chooses: a vitest.config.* (the test setup the specs were written for) before a vite.config.*. A
// vitest.config imports vitest itself (`defineConfig` from 'vitest/config'): a package without it gets ours.
const configFile = ['vitest.config', 'vite.config']
  .flatMap((name) => ['ts', 'mts', 'cts', 'js', 'mjs', 'cjs'].map((ext) => join(pkg, `${name}.${ext}`)))
  .find((path) => existsSync(path))
const webUrl = pathToFileURL(join(here, 'web', 'package.json')).href
register('data:text/javascript,' + encodeURIComponent(`
  export async function resolve(specifier, context, next) {
    try {
      return await next(specifier, context)
    } catch (e) {
      if (!/^(vitest|@vitest\\/)/.test(specifier)) throw e
      return next(specifier, { ...context, parentURL: ${JSON.stringify(webUrl)} })
    }
  }`))
let loaded = null
if (configFile) {
  try {
    const env = { command: 'serve', mode: 'test', isSsrBuild: false, isPreview: false }
    loaded = await loadConfigFromFile(env, configFile, pkg, 'silent', undefined, 'native')
  } catch (e) {
    fail(`could not load ${configFile}: ${e.message}`)
  }
}
const { server, preview, build, optimizeDeps, cacheDir, root, test: own = {}, plugins = [], ...rest } =
  loaded?.config ?? {}
const inline = own.server?.deps?.inline
const manifest = existsSync(join(pkg, 'package.json')) ? JSON.parse(readFileSync(join(pkg, 'package.json'), 'utf8')) : {}
const usesVuetify = Boolean({ ...manifest.dependencies, ...manifest.devDependencies }.vuetify)

/**
 * The runtime puts a test on record when its callback runs. One that failed before that (in a beforeEach, or on a
 * module that didn't load) failed all the same: it goes on record with its error, and the trace file always exists.
 */
function complete(trace, spec, tests) {
  let tree = { fn: 'scenario', file: 'scenario', line: 1, args: {}, calls: [], lines: {} }
  try {
    if (existsSync(trace)) tree = JSON.parse(readFileSync(trace, 'utf8'))
  } catch {
    return // cut off mid-write: leave it as the run left it
  }
  const seen = new Set(tree.calls.map((c) => c.fn))
  const clip = (text) => (text.length > 80 ? text.slice(0, 79) + '…' : text)
  for (const t of tests) {
    const fn = `test: ${t.name}`
    if (t.result().state !== 'failed' || seen.has(fn) || !t.name.includes(process.env.CS_TEST ?? '')) continue
    const e = t.result().errors?.[0] ?? {}
    tree.calls.push({ fn, file: relative(git, join(pkg, spec)), line: t.location?.line ?? 1, args: {}, calls: [],
      raised: `${e.name ?? 'Error'}(${JSON.stringify(clip(String(e.message ?? '')))})` })
  }
  writeFileSync(trace, JSON.stringify(tree, null, 1) + '\n')
}

/** Run one spec file; its trace goes to `trace`. Returns the exit code for that file. */
async function run(spec, trace) {
  process.env.CS_TRACE_OUT = trace // the worker is forked per run and inherits it
  const cache = mkdtempSync(join(tmpdir(), 'codestory-vite-'))
  try {
    const plugin = process.env.CS_INSTRUMENT === '0' ? [] : [codestory({ pkg, git, include, soft })]
    const vitest = await startVitest('test', [], {
      config: false,
      root: pkg,
      include: [spec],
      run: true,
      watch: false,
      environment: process.env.CS_ENVIRONMENT ?? own.environment ?? 'jsdom',
      pool: 'forks',
      maxWorkers: 1,
      fileParallelism: false,
      setupFiles: [join(here, 'runtime.mjs'), ...[own.setupFiles ?? []].flat()],
      cache: false,
      includeTaskLocation: true,
      // Vuetify's components import their own CSS, which Node can't load: run them through Vite instead.
      server: { deps: { inline: inline === true || [...(inline ?? []), ...(usesVuetify ? ['vuetify'] : [])] } },
    }, {
      ...rest,
      plugins: [...plugin, ...plugins],
      cacheDir: cache,
      server: { fs: { strict: false } }, // runtime.mjs, and in a worktree the linked node_modules, live outside it
      test: own,
    })
    const modules = vitest.state.getTestModules()
    const tests = modules.flatMap((m) => [...m.children.allTests()])
    complete(trace, spec, tests)
    const ran = tests.filter((t) => ['passed', 'failed'].includes(t.result().state))
    if (!modules.length || (modules.some((m) => m.errors().length) && !ran.length)) return 2
    const failed = tests.some((t) => t.result().state === 'failed') || modules.some((m) => m.errors().length) ||
      vitest.state.getUnhandledErrors().length > 0
    return failed ? 1 : 0
  } finally {
    rmSync(cache, { recursive: true, force: true })
  }
}

// Each spec file runs on its own, as Vitest isolates files by default; with several, their traces are merged.
let code = 0
const parts = specs.length === 1 ? [out] : specs.map((_, i) => `${out}.${i}.part`)
const merged = { fn: 'scenario', file: 'scenario', line: 1, args: {}, calls: [], lines: {} }
for (const [i, spec] of specs.entries()) {
  let result
  try {
    result = await run(spec, parts[i])
  } catch (e) {
    console.error(`[codestory] ${spec}: ${e.stack ?? e}`)
    result = 2
  }
  code = Math.max(code, result)
  if (!existsSync(parts[i])) complete(parts[i], spec, [])
  if (specs.length > 1) {
    try {
      merged.calls.push(...JSON.parse(readFileSync(parts[i], 'utf8')).calls)
    } catch (e) {
      console.error(`[codestory] ${spec}: unreadable trace (${e.message})`)
    }
    rmSync(parts[i])
    writeFileSync(out, JSON.stringify(merged, null, 1) + '\n')
  }
}
process.exit(code)
