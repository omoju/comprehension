// Vite plugin: hands each module of the traced frontend to instrument() before Vue or TypeScript compiles it.
//
// It runs first (enforce: 'pre'), so it sees each file as written: .ts and .js modules under the include prefixes,
// the <script> and <script setup> blocks of .vue files there, and spec files anywhere in the package, whose test
// callbacks become scenario roots. A .vue block is instrumented in place: everything before it is blanked to spaces
// (newlines kept), so instrument() counts lines as the .vue file does, and only the block is spliced back.
//
// The helpers come from an import on the first line (of the file, or of the block) instead of the declarations
// instrument() appends: a plain-JS block can't take their type annotations, and in <script setup> a declared helper
// would be a local of setup(), which defineProps() defaults and validators, hoisted out of setup(), may not use.
// No line is added anywhere, so returning no source map leaves the next compiler's map right line for line.

import { createRequire } from 'node:module'
import { join, relative } from 'node:path'
import { instrument, softenImports } from './instrument.mjs'

const HELPERS_ID = 'virtual:codestory'
const HELPERS =
  'export function __cs$(f, n, l, a, b) { const r = globalThis.__csrt; return r ? r(f, n, l, a, b) : b() }\n' +
  'export function __cs$t(f, l, t, cb) { const r = globalThis.__csrt; return r ? r.root(f, l, t, cb) : cb }\n'
const IMPORT = `import { __cs$, __cs$t } from '${HELPERS_ID}';`
const APPENDED = '\n;function __cs$(' // where the helper declarations instrument() appends begin
const SPEC = /\.(spec|test)\.[cm]?[jt]s$/
const MODULE = /\.[cm]?[jt]s$/
const SCRIPT_LANG = /^(ts|js)?$/ // tsx / jsx blocks are left alone: instrument() parses TypeScript without JSX

/** instrument()'s output with its appended helper declarations swapped for an import at `at` (if it added any). */
export function importHelpers(out, at) {
  const cut = out.lastIndexOf(APPENDED)
  return cut === -1 ? out : out.slice(0, at) + IMPORT + out.slice(at, cut)
}

/** Names the module turns into source text, `f.toString()`, `String(f)`, `${f}` or `'…' + f`, to run elsewhere. */
function stringified(ts, node, out = new Set()) {
  const id = (e) => (e && ts.isIdentifier(e) ? e.text : null)
  let name = null
  if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression) &&
      node.expression.name.text === 'toString') name = id(node.expression.expression)
  else if (ts.isCallExpression(node) && id(node.expression) === 'String') name = id(node.arguments[0])
  else if (ts.isTemplateSpan(node)) name = id(node.expression)
  else if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) {
    if (ts.isStringLiteralLike(node.left) || ts.isTemplateExpression(node.left)) name = id(node.right)
    else if (ts.isStringLiteralLike(node.right) || ts.isTemplateExpression(node.right)) name = id(node.left)
  }
  if (name) out.add(name)
  ts.forEachChild(node, (child) => void stringified(ts, child, out)) // a truthy return would stop the walk
  return out
}

/**
 * instrument(), except for functions the module stringifies (an iframe's or a vm's script built from them): wrapped,
 * their text would call a helper that isn't there. Each is swapped for a placeholder with its line breaks while
 * instrument() runs, then put back as written.
 */
export function instrumentModule(ts, source, file) {
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
  const names = stringified(ts, sf)
  const raw = []
  const visit = (node) => {
    const fn = ts.isFunctionDeclaration(node) && node.name && node.body ? node
      : ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer &&
        (ts.isFunctionExpression(node.initializer) || ts.isArrowFunction(node.initializer)) ? node.initializer : null
    const name = fn && (ts.isFunctionDeclaration(fn) ? fn.name.text : node.name.text)
    if (fn && names.has(name)) raw.push(fn) // nested functions go with it
    else ts.forEachChild(node, visit)
  }
  if (names.size) visit(sf)
  let masked = source
  const kept = raw.reverse().map((fn, i) => {
    const text = source.slice(fn.getStart(sf), fn.getEnd())
    const breaks = '\n'.repeat(text.split('\n').length - 1)
    const holder = ts.isFunctionDeclaration(fn) ? `/*cs:raw${i}*/${breaks}` : `(0/*cs:raw${i}*/${breaks})`
    masked = masked.slice(0, fn.getStart(sf)) + holder + masked.slice(fn.getEnd())
    return [holder, text]
  })
  let out = instrument(ts, masked, file)
  for (const [holder, text] of kept) out = out.replace(holder, () => text)
  return out
}

/**
 * Soft imports for the base side, except Vitest's own: hoisted vi.mock() calls must still find `vi`. Vite resolves a
 * literal dynamic import while transforming the file and rejects the whole file if one is missing, so each softened
 * specifier becomes an expression, resolved (or not) when it runs.
 */
export function softenSpec(ts, source, file) {
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
  const kept = sf.statements.filter((s) => ts.isImportDeclaration(s) && ts.isStringLiteral(s.moduleSpecifier) &&
    /^(vitest|@vitest\/)/.test(s.moduleSpecifier.text))
  let out = source
  const texts = []
  for (const st of [...kept].reverse()) {
    const text = out.slice(st.getStart(sf), st.getEnd())
    out = out.slice(0, st.getStart(sf)) + `/*cs:keep${texts.length}*/` + '\n'.repeat(text.split('\n').length - 1) +
      out.slice(st.getEnd())
    texts.push(text)
  }
  out = softenImports(ts, out, file).replace(/await import\((['"][^'"\n]*['"])\)\.catch\(/g,
    "await import(/* @vite-ignore */ $1 + '').catch(")
  texts.forEach((text, i) => {
    out = out.replace(`/*cs:keep${i}*/` + '\n'.repeat(text.split('\n').length - 1), () => text)
  })
  return out
}

/** The .vue source with its script blocks instrumented, or null when there is nothing to trace in them. */
export function instrumentVue(ts, sfc, source, file) {
  const { descriptor, errors } = sfc.parse(source, { filename: file, sourceMap: false })
  if (errors.length) throw errors[0]
  const blocks = [descriptor.script, descriptor.scriptSetup]
    .filter((b) => b && !b.src && SCRIPT_LANG.test(b.lang ?? ''))
  const done = new Map()
  for (const b of blocks) {
    const [start, end] = [b.loc.start.offset, b.loc.end.offset]
    const masked = source.slice(0, start).replace(/[^\n]/g, ' ') + source.slice(start, end)
    const out = instrumentModule(ts, masked, file)
    const cut = out.lastIndexOf(APPENDED)
    if (cut !== -1) done.set(b, out.slice(start, cut))
  }
  if (!done.size) return null
  // One import serves both blocks: a normal <script> is module scope, which <script setup> sees too.
  const home = blocks.includes(descriptor.script) ? descriptor.script : descriptor.scriptSetup
  done.set(home, IMPORT + (done.get(home) ?? source.slice(home.loc.start.offset, home.loc.end.offset)))
  let out = source
  for (const [b, text] of [...done].sort((x, y) => y[0].loc.start.offset - x[0].loc.start.offset)) {
    out = out.slice(0, b.loc.start.offset) + text + out.slice(b.loc.end.offset)
  }
  return out
}

/**
 * pkg: the package directory; git: the repository root (trace paths are relative to it); include: path prefixes,
 * relative to pkg, whose modules are traced; soft: spec imports missing on this side become undefined.
 */
export default function codestory({ pkg, git, include = ['src/'], soft = false }) {
  const req = createRequire(join(pkg, 'package.json'))
  const ts = req('typescript') // the package's own compiler, so its syntax is supported
  let sfc // the package's Vue compiler, loaded at the first .vue file
  return {
    name: 'codestory',
    enforce: 'pre',
    resolveId(id) {
      if (id === HELPERS_ID) return '\0' + HELPERS_ID
    },
    load(id) {
      if (id === '\0' + HELPERS_ID) return HELPERS
    },
    transform(code, id) {
      if (id.includes('?') || id.startsWith('\0')) return null
      const inPkg = relative(pkg, id)
      if (inPkg.startsWith('..') || inPkg.includes('node_modules')) return null
      const spec = SPEC.test(inPkg)
      if (!spec && !include.some((prefix) => inPkg.startsWith(prefix))) return null
      const file = relative(git, id)
      try {
        let out = null
        if (spec) {
          const source = soft ? softenSpec(ts, code, file) : code
          out = importHelpers(instrument(ts, source, file, { roots: true }), 0)
        } else if (inPkg.endsWith('.vue')) {
          out = instrumentVue(ts, (sfc ??= req('vue/compiler-sfc')), code, file)
        } else if (MODULE.test(inPkg) && !inPkg.endsWith('.d.ts')) {
          out = importHelpers(instrumentModule(ts, code, file), 0)
        }
        return out === null || out === code ? null : { code: out, map: null }
      } catch (e) {
        console.error(`[codestory] left ${inPkg} uninstrumented: ${e.message}`)
        return null
      }
    },
  }
}
