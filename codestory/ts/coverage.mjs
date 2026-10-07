// Which lines of the .ts files ran: V8's precise coverage, mapped back through the compiler's source maps.
// trace.py records executed lines with its tracer; here they come from an inspector session on this thread, so the
// flowchart can say which way each branch went. take() returns what ran since the last take() (V8 resets its
// counters), so a caller can attribute lines to the test that just finished.

import inspector from 'node:inspector'
import { SourceMap, findSourceMap } from 'node:module'
import { fileURLToPath } from 'node:url'

let session = null
const sources = new Map() // scriptId -> the generated JavaScript, to turn offsets into lines

function post(method, params = {}) {
  let out, err
  session.post(method, params, (e, r) => { err = e; out = r }) // an in-thread session answers synchronously
  if (err) throw err
  return out
}

export function start() {
  try {
    session = new inspector.Session()
    session.connect()
    post('Profiler.enable')
    post('Profiler.startPreciseCoverage', { callCount: true, detailed: true })
    post('Debugger.enable') // only for getScriptSource; never pause, or a `debugger;` would hang this thread
    post('Debugger.setSkipAllPauses', { skip: true })
  } catch {
    session = null // no inspector (a worker without it): the trace simply carries no lines
  }
}

// Vite (and so Vitest) evaluates transformed modules itself, so Node's source map cache never sees them; their
// maps are inlined at the end of the generated text.
const inlineMaps = new Map()
function inlineMap(scriptId, text) {
  if (!inlineMaps.has(scriptId)) {
    const m = /\/\/# sourceMappingURL=data:application\/json[^,]*;base64,([A-Za-z0-9+/=]+)\s*$/m.exec(text.slice(-2_000_000))
    let map = null
    try {
      if (m) map = new SourceMap(JSON.parse(Buffer.from(m[1], 'base64').toString('utf8')))
    } catch {
      map = null
    }
    inlineMaps.set(scriptId, map)
  }
  return inlineMaps.get(scriptId)
}

/** Map(absolute .ts path -> Set of 1-based lines) that ran since the last call, for paths `wanted` accepts. */
export function take(wanted) {
  const lines = new Map()
  if (!session) return lines
  let result
  try {
    result = post('Profiler.takePreciseCoverage').result
  } catch {
    return lines
  }
  for (const script of result) {
    if (!script.url.startsWith('file:')) continue
    const path = fileURLToPath(script.url)
    if (!wanted(path)) continue
    let text = sources.get(script.scriptId)
    if (text === undefined) {
      try {
        text = post('Debugger.getScriptSource', { scriptId: script.scriptId }).scriptSource
      } catch {
        continue
      }
      sources.set(script.scriptId, text)
    }
    const map = findSourceMap(script.url) ?? findSourceMap(path) ?? inlineMap(script.scriptId, text)
    if (!map) continue // without a map, generated lines are not the file's lines: report nothing rather than wrong
    const ranges = script.functions.flatMap((f) => f.ranges)
    const out = lines.get(path) ?? new Set()
    let lineStart = 0
    for (let ln = 0; lineStart <= text.length; ln++) {
      const next = text.indexOf('\n', lineStart)
      const lineEnd = next === -1 ? text.length : next
      let col = 0
      while (lineStart + col < lineEnd && /\s/.test(text[lineStart + col])) col++
      const at = lineStart + col
      if (at < lineEnd) {
        // The innermost range holding the line's first character decides whether it ran.
        let best = null
        for (const r of ranges) {
          if (r.startOffset <= at && at < r.endOffset && (!best || r.endOffset - r.startOffset < best.endOffset - best.startOffset)) best = r
        }
        if (best && best.count > 0) {
          const entry = map.findEntry(ln, col)
          if (entry && typeof entry.originalLine === 'number') out.add(entry.originalLine + 1)
        }
      }
      if (next === -1) break
      lineStart = next + 1
    }
    if (out.size) lines.set(path, out)
  }
  return lines
}
