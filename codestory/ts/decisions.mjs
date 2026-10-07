// The decisions a TypeScript function made in a run, for the flowchart: render.py's Python `decisions()`, for TS.
//
//   echo '{"pkg": "<package dir>", "requests": [{"file", "source", "line", "ran": [..]}]}' | node decisions.mjs
//   → [{"file", "line", "end", "decisions": [{kind, line, end, question, answer, side, exit}]}]
//
// `line` names the function the way the trace does (the line of its name); `ran` holds the lines that executed.
// An if/else-if chain is one decision; so is a switch; a try with a catch asks whether its first statement fails.
// Decisions a flowchart shouldn't show are skipped, as in render.py: flags (`if (x)`) and default-filling
// (`x === undefined`). Nested functions are their own calls, so their decisions stay with them.

import { createRequire } from 'node:module'
import { readFileSync } from 'node:fs'
import { functions } from './instrument.mjs'

const input = JSON.parse(readFileSync(0, 'utf8'))
const ts = createRequire(`${input.pkg}/package.json`)('typescript')

const short = (text) => text.replace(/\s+/g, ' ').trim().slice(0, 80)

function find(ts, sf, line) {
  return functions(ts, sf).find((f) => f.line === line)
}

function decisionsOf(sf, fn, ran) {
  const lineOf = (pos) => sf.getLineAndCharacterOfPosition(pos).line + 1
  const start = (n) => lineOf(n.getStart(sf))
  const end = (n) => lineOf(n.getEnd())
  // Did a branch run? Judged by its statements' lines, not its braces (a `{` sits on the line that tests the
  // condition, which always runs). null when line coverage can't tell: an empty branch, or one that shares a line
  // with the condition (`if (x) continue`).
  const touched = (n, header) => {
    if (!n) return false
    const stmts = ts.isBlock(n) ? [...n.statements] : [n]
    if (!stmts.length || start(stmts[0]) <= header) return null
    for (let l = start(stmts[0]); l <= end(stmts.at(-1)); l++) if (ran.has(l)) return true
    return false
  }
  const isNullish = (e) => e.kind === ts.SyntaxKind.NullKeyword || (ts.isIdentifier(e) && e.text === 'undefined')
  const isNoise = (test) => {
    if (ts.isIdentifier(test) || ts.isPropertyAccessExpression(test)) return true
    if (ts.isPrefixUnaryExpression(test) && test.operator === ts.SyntaxKind.ExclamationToken &&
        (ts.isIdentifier(test.operand) || ts.isPropertyAccessExpression(test.operand))) return true
    const eq = [ts.SyntaxKind.EqualsEqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsEqualsToken,
      ts.SyntaxKind.EqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsToken]
    return ts.isBinaryExpression(test) && eq.includes(test.operatorToken.kind) && (isNullish(test.right) || isNullish(test.left))
  }
  const statements = (n) => (!n ? [] : ts.isBlock(n) ? [...n.statements] : [n])
  const summarize = (stmts) => {
    for (const s of stmts) {
      let thrown = null
      const look = (n) => {
        if (thrown || ts.isFunctionLike(n)) return
        if (ts.isThrowStatement(n) && n.expression) {
          const e = n.expression
          thrown = 'throw ' + short((ts.isNewExpression(e) || ts.isCallExpression(e) ? e.expression : e).getText(sf))
        } else ts.forEachChild(n, look)
      }
      look(s)
      if (thrown) return thrown
    }
    const ret = stmts.find((s) => ts.isReturnStatement(s))
    if (ret) return 'return ' + (ret.expression ? short(ret.expression.getText(sf)) : '')
    return stmts.length ? short(stmts[0].getText(sf).split('\n')[0]) : 'carry on'
  }
  const elseIfs = new Set()
  const found = []
  const visit = (n) => {
    if (n !== fn.node && ts.isFunctionLike(n)) return
    if (ts.isIfStatement(n) && !elseIfs.has(n) && ran.has(start(n)) && !isNoise(n.expression)) {
      const chain = [n]
      while (chain.at(-1).elseStatement && ts.isIfStatement(chain.at(-1).elseStatement)) {
        elseIfs.add(chain.at(-1).elseStatement)
        chain.push(chain.at(-1).elseStatement)
      }
      const finalElse = chain.at(-1).elseStatement
      const seen = chain.map((c) => touched(c.thenStatement, end(c.expression)))
      if (seen.includes(null)) { ts.forEachChild(n, visit); return } // can't tell which way it went
      const taken = chain[seen.indexOf(true)]
      let question, answer, side, exit
      if (chain.length > 1) {
        const lefts = new Set(chain.map((c) => c.expression).filter((e) => ts.isBinaryExpression(e) &&
          [ts.SyntaxKind.EqualsEqualsEqualsToken, ts.SyntaxKind.EqualsEqualsToken].includes(e.operatorToken.kind))
          .map((e) => e.left.getText(sf)))
        const sameLeft = lefts.size === 1 && chain.every((c) => ts.isBinaryExpression(c.expression))
        question = sameLeft ? `${[...lefts][0]} === ?` : short(n.expression.getText(sf))
        answer = taken ? short(sameLeft ? taken.expression.right.getText(sf) : taken.expression.getText(sf))
          : sameLeft ? 'none of them' : 'else'
        side = 'otherwise'
        exit = finalElse ? summarize(statements(finalElse)) : 'no branch matches'
      } else {
        const yes = !!taken
        question = short(n.expression.getText(sf))
        answer = yes ? 'yes' : 'no'
        side = yes ? 'no' : 'yes'
        let untaken = yes ? statements(finalElse) : statements(n.thenStatement)
        if (yes && !finalElse && n.parent && 'statements' in n.parent) {
          const siblings = [...n.parent.statements] // a guard: `if (ok) return x`, then the fall-through is the other road
          untaken = siblings.slice(siblings.indexOf(n) + 1, siblings.indexOf(n) + 2)
        }
        exit = untaken.length ? summarize(untaken) : 'carry on'
      }
      found.push({ kind: 'decision', line: start(n), end: end(chain.at(-1)), question, answer, side, exit })
    } else if (ts.isSwitchStatement(n) && ran.has(start(n))) {
      const clauses = [...n.caseBlock.clauses]
      const taken = clauses.find((c) => c.statements.some((s) => touched(s, start(c))))
      const fallback = clauses.find((c) => ts.isDefaultClause(c))
      found.push({
        kind: 'decision', line: start(n), end: end(n), question: `${short(n.expression.getText(sf))} === ?`,
        answer: taken ? (ts.isDefaultClause(taken) ? 'default' : short(taken.expression.getText(sf))) : 'none of them',
        side: 'otherwise', exit: fallback && fallback !== taken ? summarize([...fallback.statements]) : 'no case matches',
      })
    } else if (ts.isTryStatement(n) && n.catchClause && ran.has(start(n))) {
      const caught = touched(n.catchClause.block, start(n.catchClause))
      if (caught === null) { ts.forEachChild(n, visit); return }
      const first = n.tryBlock.statements[0]
      found.push({
        kind: 'decision', line: start(n), end: end(n),
        question: (first ? short(first.getText(sf).split('\n')[0]) : 'try') + ' fails?',
        answer: caught ? 'yes' : 'no', side: caught ? 'no' : 'yes',
        exit: caught ? 'carry on' : summarize([...n.catchClause.block.statements]),
      })
    }
    ts.forEachChild(n, visit)
  }
  ts.forEachChild(fn.node, visit)
  return found.sort((a, b) => a.line - b.line)
}

// A .vue file's script blocks, every other line blanked: the line numbers stay the file's own.
function scriptOnly(source) {
  let inside = false
  return source.split('\n').map((line) => {
    if (/^\s*<script\b/.test(line)) { inside = !/<\/script>/.test(line); return '' }
    if (/^\s*<\/script>/.test(line)) { inside = false; return '' }
    return inside ? line : ''
  }).join('\n')
}

const out = []
const parsed = new Map()
for (const r of input.requests) {
  let sf = parsed.get(r.file + '\0' + r.source.length)
  if (!sf) {
    const text = r.file.endsWith('.vue') ? scriptOnly(r.source) : r.source
    sf = ts.createSourceFile(r.file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
    parsed.set(r.file + '\0' + r.source.length, sf)
  }
  const fn = find(ts, sf, r.line)
  out.push({ file: r.file, line: r.line, end: fn ? fn.end : r.line,
    decisions: fn ? decisionsOf(sf, fn, new Set(r.ran)) : [] })
}
process.stdout.write(JSON.stringify(out) + '\n')
