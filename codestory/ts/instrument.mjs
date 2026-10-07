// Rewrite a TypeScript module so every named function records itself into the trace, without moving a line.
//
// A function body `{ BODY }` becomes `{ return __cs$(file, name, line, {params}, () => { BODY }) }`. The wrapper
// is an arrow, so `this`, `arguments`, `super` and `new.target` inside BODY still mean what they meant; async
// functions get an async arrow so `await` stays legal. Insertions never add a newline, so every line number the
// story cites is the line number in the file. Constructors, accessors, generators and anonymous callbacks are
// left alone (the same way trace.py folds lambdas and comprehensions into their parent).
//
// In spec files (`roots`), the callback of each `test(title, cb)` / `test(title).run(cb)` (Japa) or
// `it(title, cb)` / `test(title, cb)` (Vitest) becomes a scenario root instead: the calls made while that test runs
// are the journey.
//
// The helpers are appended after the last line; function declarations hoist, so they exist before any call.

const OPEN = 0
const CLOSE = 1

const HELPERS =
  '\n;function __cs$(f: any, n: any, l: any, a: any, b: any): any { const r = (globalThis as any).__csrt; return r ? r(f, n, l, a, b) : b() }' +
  '\n;function __cs$t(f: any, l: any, t: any, cb: any): any { const r = (globalThis as any).__csrt; return r ? r.root(f, l, t, cb) : cb }\n'

/** Function-like nodes worth tracing in a source file: {node, name, line, end, async, params}. */
export function functions(ts, sf) {
  const found = []
  const visit = (node) => {
    const fn = describe(ts, sf, node)
    if (fn) found.push(fn)
    ts.forEachChild(node, visit)
  }
  visit(sf)
  return found
}

function describe(ts, sf, node) {
  const kinds = [ts.SyntaxKind.FunctionDeclaration, ts.SyntaxKind.FunctionExpression, ts.SyntaxKind.ArrowFunction,
    ts.SyntaxKind.MethodDeclaration]
  if (!kinds.includes(node.kind) || !node.body || node.asteriskToken) return null
  const own = ownName(ts, node)
  if (!own) return null // anonymous callback: its calls fold into the parent
  const name = [...enclosingNames(ts, node), own].join('.')
  const at = node.name ?? node
  const line = sf.getLineAndCharacterOfPosition(at.getStart(sf)).line + 1
  const end = sf.getLineAndCharacterOfPosition(node.getEnd()).line + 1
  const isAsync = !!node.modifiers?.some((m) => m.kind === ts.SyntaxKind.AsyncKeyword)
  const params = []
  for (const p of node.parameters) {
    if (ts.isIdentifier(p.name) && p.name.text === 'this') continue // TS `this:` annotation, not a parameter
    bindings(ts, p.name, params)
  }
  return { node, name, line, end, async: isAsync, params }
}

function ownName(ts, node) {
  if (node.name) return node.name.getText()
  const p = node.parent
  if (ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text
  if ((ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p)) && p.initializer === node) return p.name.getText()
  if (ts.isBinaryExpression(p) && p.right === node && p.operatorToken.kind === ts.SyntaxKind.EqualsToken)
    return p.left.getText().replace(/^this\./, '')
  return null
}

function enclosingNames(ts, node) {
  const names = []
  for (let p = node.parent; p; p = p.parent) {
    if ((ts.isClassDeclaration(p) || ts.isClassExpression(p)) && p.name) names.unshift(p.name.text)
    else if (ts.isFunctionLike(p) && p !== node) {
      const own = p.body && ownName(ts, p)
      if (own) names.unshift(own)
    }
  }
  return names
}

function bindings(ts, name, out) {
  if (ts.isIdentifier(name)) out.push(name.text)
  else for (const el of name.elements) if (!ts.isOmittedExpression(el)) bindings(ts, el.name, out)
}

function testRoot(ts, sf, node) {
  // test('title', cb)  or  test('title').run(cb); Vitest's it('title', cb), it.only and test.only too
  if (!ts.isCallExpression(node)) return null
  const callee = node.expression
  const isTest = (e) => ts.isIdentifier(e) && (e.text === 'test' || e.text === 'it')
  let title, cb
  if ((isTest(callee) || (ts.isPropertyAccessExpression(callee) && callee.name.text === 'only' &&
       isTest(callee.expression))) && node.arguments.length >= 2) {
    ;[title, cb] = node.arguments
  } else if (ts.isPropertyAccessExpression(callee) && callee.name.text === 'run' && node.arguments.length >= 1 &&
             ts.isCallExpression(callee.expression) && ts.isIdentifier(callee.expression.expression) &&
             callee.expression.expression.text === 'test' && callee.expression.arguments.length >= 1) {
    title = callee.expression.arguments[0]
    cb = node.arguments[0]
  } else return null
  if (!(ts.isArrowFunction(cb) || ts.isFunctionExpression(cb))) return null
  const text = ts.isStringLiteralLike(title) ? JSON.stringify(title.text) : JSON.stringify(title.getText(sf))
  return { cb, text, line: sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1 }
}

/**
 * A spec written against the head often imports what the change adds. Run on the base, those names don't exist and
 * the whole file fails to link, so no test runs at all. Soft imports turn each value import into a dynamic import
 * whose missing names are `undefined` (and a missing module an empty object, reported on stderr): the file loads,
 * and only the tests that use the new names fail, each on its own. Every import keeps its line count.
 */
export function softenImports(ts, source, file) {
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
  let out = source
  const imports = sf.statements.filter((s) => ts.isImportDeclaration(s) && s.importClause && !s.importClause.isTypeOnly)
  imports.reverse().forEach((st, i) => {
    const { name, namedBindings } = st.importClause
    const from = st.moduleSpecifier.getText(sf)
    const m = `__cs_m${imports.length - 1 - i}`
    const binds = []
    if (name) binds.push(`const ${name.text} = ${m}.default;`)
    if (namedBindings && ts.isNamespaceImport(namedBindings)) binds.push(`const ${namedBindings.name.text} = ${m};`)
    if (namedBindings && ts.isNamedImports(namedBindings)) {
      const els = namedBindings.elements.filter((e) => !e.isTypeOnly)
      const list = els.map((e) => (e.propertyName ? `${e.propertyName.getText(sf)}: ${e.name.text}` : e.name.text))
      if (list.length) binds.push(`const { ${list.join(', ')} } = ${m};`)
    }
    const text = `const ${m}: any = await import(${from}).catch((e: any) => ` +
      `(console.error('[codestory] import ' + ${from} + ' failed: ' + e.message), {})); ${binds.join(' ')}`
    const newlines = st.getText(sf).split('\n').length - 1
    out = out.slice(0, st.getStart(sf)) + text + '\n'.repeat(newlines) + out.slice(st.getEnd())
  })
  return out
}

export function instrument(ts, source, file, { roots = false, soft = false } = {}) {
  if (roots && soft) source = softenImports(ts, source, file)
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
  const edits = [] // [position, text, OPEN|CLOSE]; applied from the end so positions stay valid
  const f = JSON.stringify(file)

  if (roots) {
    const visit = (node) => {
      const t = testRoot(ts, sf, node)
      if (t) {
        edits.push([t.cb.getStart(sf), `__cs$t(${f},${t.line},${t.text},`, OPEN])
        edits.push([t.cb.getEnd(), ')', CLOSE])
      }
      ts.forEachChild(node, visit)
    }
    visit(sf)
  } else {
    for (const fn of functions(ts, sf)) {
      const head = `__cs$(${f},${JSON.stringify(fn.name)},${fn.line},{${fn.params.join(',')}},${fn.async ? 'async ' : ''}()=>`
      const body = fn.node.body
      if (ts.isBlock(body) && body.getStart(sf) + 1 === body.getEnd() - 1) {
        edits.push([body.getStart(sf) + 1, `return ${head}{})`, OPEN]) // `{}`: open and close share one spot
      } else if (ts.isBlock(body)) {
        edits.push([body.getStart(sf) + 1, `return ${head}{`, OPEN])
        edits.push([body.getEnd() - 1, '})', CLOSE])
      } else {
        edits.push([body.getStart(sf), `${head}(`, OPEN])
        edits.push([body.getEnd(), '))', CLOSE])
      }
    }
  }
  if (!edits.length) return source

  // Applied from the end. Two insertions at one position: the one applied later lands to the left. Outer functions
  // are pushed before inner ones, so opens apply inner-first (outer lands leftmost) and closes outer-first (outer
  // lands rightmost); an open applies before a close at the same spot, so a close never lands inside the next open.
  const order = edits.map((e, i) => [...e, i]).sort((a, b) =>
    b[0] - a[0] || a[2] - b[2] || (a[2] === OPEN ? b[3] - a[3] : a[3] - b[3]))
  let out = source
  for (const [pos, text] of order) out = out.slice(0, pos) + text + out.slice(pos)
  return out + HELPERS
}
