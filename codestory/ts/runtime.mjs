// The trace recorder for instrumented TypeScript: the Node counterpart of trace.py's tracer.
//
// Instrumented functions call globalThis.__csrt(file, name, line, args, body). A call is recorded only inside a
// scenario root (a test callback), so app boot and providers are setting, not the journey, as import-time code is
// for trace.py. The current node travels with AsyncLocalStorage, so awaited and interleaved calls still land under
// the call that made them. At exit the tree is written to CS_TRACE_OUT in trace.py's shape (fn, file, line,
// called_from, args, calls, returned | raised), so compress() and render() in trace.py work on it unchanged.
// Each test also gets the lines that ran during it (V8 coverage, mapped to the .ts lines; CS_LINES=0 turns it
// off), so the page can show which way each branch went, on each side of a change.

import { AsyncLocalStorage } from 'node:async_hooks'
import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { basename, relative } from 'node:path'
import { types } from 'node:util'
import * as coverage from './coverage.mjs'

const als = new AsyncLocalStorage()
const only = process.env.CS_TEST // record only tests whose title contains this
const MAX_CALLS = Number(process.env.CS_MAX_CALLS ?? 20000) // per test; a runaway loop must not exhaust memory
const counts = new WeakMap() // test node -> calls recorded under it
const testOf = new WeakMap() // node -> its test node
const SAVE_EVERY = 2000 // calls; a run that dies mid-test still leaves most of that test behind
const SAVE_GAP_MS = 500 // at most this often for a test's later direct calls
let recorded = 0
let lastSave = 0

const gitRoot = (() => {
  try {
    return execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim()
  } catch {
    return null
  }
})()
const LINES = process.env.CS_LINES !== '0' && gitRoot !== null
const tracedFiles = new Set() // repo-relative files with a recorded call: the only ones worth mapping lines for
if (LINES) coverage.start()

/** {file: [lines]} that ran since the last call, for the files the trace touched. */
function takeLines() {
  if (!LINES) return {}
  const out = {}
  for (const [abs, lines] of coverage.take((abs) => tracedFiles.has(relative(gitRoot, abs)))) {
    out[relative(gitRoot, abs)] = [...lines].sort((a, b) => a - b)
  }
  return out
}

function addLines(into, lines) {
  for (const [file, ls] of Object.entries(lines)) into[file] = [...new Set([...(into[file] ?? []), ...ls])].sort((a, b) => a - b)
}
const root = { fn: 'scenario', file: process.env.CS_SCENARIO ?? 'scenario', line: 1, args: {}, calls: [], lines: {} }

const MAX_STRING = 80
const MAX_ITEMS = 6
const MAX_REPR = 200
const HIDDEN_KEY = /^(_|\$|lc_)/ // private fields and framework bookkeeping (Lucid's $-fields, LangChain's lc_*)

function clip(text, max) {
  return text.length > max ? text.slice(0, max - 1) + '…' : text
}

function ctorName(v) {
  try {
    return Object.getPrototypeOf(v)?.constructor?.name ?? ''
  } catch {
    return ''
  }
}

function show(v, depth = 0) {
  try {
    if (v === null) return 'null'
    if (v === undefined) return 'undefined'
    const t = typeof v
    if (t === 'string') return JSON.stringify(clip(v, MAX_STRING))
    if (t === 'number' || t === 'boolean') return String(v)
    if (t === 'bigint') return `${v}n`
    if (t === 'symbol') return v.toString()
    if (t === 'function') return `<function ${v.name || 'anonymous'}>`
    if (v instanceof Error) return `${v.name}(${JSON.stringify(clip(String(v.message), MAX_STRING))})`
    if (types.isPromise(v)) return '<Promise>'
    if (Buffer.isBuffer(v)) return `<Buffer ${v.length} bytes>`
    if (v instanceof Date) return `Date(${isNaN(v) ? 'invalid' : v.toISOString()})`
    if (v instanceof Map) return `Map(${v.size})`
    if (v instanceof Set) return `Set(${v.size})`
    if (ArrayBuffer.isView(v)) return `<${ctorName(v)} ${v.byteLength} bytes>`
    if (Array.isArray(v)) {
      if (depth >= 2) return `[… ${v.length} items]`
      const items = v.slice(0, MAX_ITEMS).map((x) => show(x, depth + 1))
      if (v.length > MAX_ITEMS) items.push(`… ${v.length - MAX_ITEMS} more`)
      return clip(`[${items.join(', ')}]`, MAX_REPR)
    }
    const name = ctorName(v)
    if (depth >= 2) return `<${name || 'Object'}>`
    // A Lucid model's state is its $attributes; elsewhere, the object's own visible keys.
    const src = v.$attributes && typeof v.$attributes === 'object' ? v.$attributes : v
    const keys = Object.keys(src).filter((k) => !HIDDEN_KEY.test(k))
    const parts = keys.slice(0, MAX_ITEMS).map((k) => `${k}: ${show(src[k], depth + 1)}`)
    if (keys.length > MAX_ITEMS) parts.push(`… ${keys.length - MAX_ITEMS} more`)
    const body = `{${parts.join(', ')}}`
    return clip(name && name !== 'Object' ? `${name} ${body}` : body, MAX_REPR)
  } catch {
    return `<${typeof v}>` // a getter or proxy that throws tells the story nothing
  }
}

function showArgs(args) {
  const out = {}
  for (const [k, v] of Object.entries(args)) out[k] = show(v)
  return out
}

// The caller's file:line, from the stack (source-mapped to the .ts line under --enable-source-maps).
// Frames below `call`: __cs$ (appended helper), the instrumented function, then its caller.
const FRAME = /\(?(?:file:\/\/)?([^()\s]+):(\d+):\d+\)?$/
function callerOf() {
  const limit = Error.stackTraceLimit
  Error.stackTraceLimit = 4
  const holder = {}
  Error.captureStackTrace(holder, call)
  Error.stackTraceLimit = limit
  const frame = holder.stack?.split('\n')[3]
  const m = frame && FRAME.exec(frame.trim())
  return m ? `${basename(m[1])}:${m[2]}` : null
}

// Written after every test and when a test turns runaway, not only at exit: a run that dies (out of memory, killed)
// still leaves every test that finished, and the first MAX_CALLS calls of the one that didn't.
function save() {
  lastSave = Date.now()
  if (process.env.CS_TRACE_OUT) writeFileSync(process.env.CS_TRACE_OUT, JSON.stringify(root, null, 1) + '\n')
}

function settle(node, result, done = () => {}) {
  // Only native promises: a Lucid query builder is a thenable, and calling its then() would run the query.
  if (types.isPromise(result)) {
    result.then(
      (v) => { node.returned = show(v); done() },
      (e) => { node.raised = show(e); done() }
    )
  } else {
    node.returned = show(result)
    done()
  }
  return result
}

function call(file, fn, line, args, body) {
  const parent = als.getStore()
  if (!parent) return body() // outside a scenario: setting, not the journey
  const test = testOf.get(parent) ?? parent
  const n = (counts.get(test) ?? 0) + 1
  counts.set(test, n)
  if (n > MAX_CALLS) {
    test.elided = n - MAX_CALLS // render() prints it as "… N nested calls"
    if (!test.runaway) {
      test.runaway = MAX_CALLS
      save()
    }
    return body()
  }
  const node = { fn, file, line, called_from: callerOf(), args: showArgs(args), calls: [] }
  tracedFiles.add(file)
  testOf.set(node, test)
  parent.calls.push(node)
  // A test's direct calls are saved as they open: a loop that only awaits stubs starves the event loop, so no
  // signal handler or timer ever runs again, and this is the last chance to put the open call on record. Each save
  // writes the whole trace, so after a test's first direct call they are throttled (a file of 80 short tests would
  // otherwise spend most of its time writing).
  const first = parent === test && !test.calls.some((c) => c !== node)
  if (++recorded % SAVE_EVERY === 0 || first || (parent === test && Date.now() - lastSave > SAVE_GAP_MS)) save()
  let result
  try {
    result = als.run(node, body)
  } catch (e) {
    node.raised = show(e)
    throw e
  }
  return settle(node, result)
}

call.root = (file, line, written, cb) =>
  function (...a) {
    // The title as the runner evaluated it (a table-driven test builds its own); the source text is the fallback.
    const title = (a[0] && (a[0].task?.name ?? a[0].test?.title)) || written
    if (only && !String(title).includes(only)) return cb.apply(this, a)
    const node = { fn: `test: ${title}`, file, line, args: {}, calls: [] }
    root.calls.push(node)
    takeLines() // what ran before the test (boot, earlier hooks) is not this test's
    save() // on record as started: if the run dies inside it, the test reads "unfinished", not "absent"
    const done = () => {
      node.lines = takeLines()
      addLines(root.lines, node.lines)
      save()
    }
    let result
    try {
      result = als.run(node, () => cb.apply(this, a))
    } catch (e) {
      node.raised = show(e)
      done()
      throw e
    }
    return settle(node, result, done)
  }

globalThis.__csrt = call

process.on('exit', save)
