// List the traceable functions in TypeScript files, with their line spans: the same set instrument() wraps.
//
//   node codestory/ts/functions.mjs <package-dir> <file>...      → JSON {file: [{name, line, end}]}
//
// .ts, .js and .vue files (a .vue file's script blocks, with everything around them blanked to spaces, so lines
// and offsets stay the file's own). A file given as "-" is read from stdin (one file only). Used to map diff hunks
// onto functions.

import { createRequire } from 'node:module'
import { readFileSync } from 'node:fs'
import { functions } from './instrument.mjs'

const [pkg, ...files] = process.argv.slice(2)
const ts = createRequire(`${pkg}/package.json`)('typescript')
function scriptBlocks(source) {
  const keep = new Array(source.length).fill(false)
  for (const m of source.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
    const start = m.index + m[0].indexOf('>') + 1
    for (let i = start; i < start + m[1].length; i++) keep[i] = true
  }
  return source.split('').map((c, i) => (keep[i] || c === '\n' ? c : ' ')).join('') // UTF-16 units, as m.index
}

const out = {}
for (const file of files) {
  let source = readFileSync(file === '-' ? 0 : file, 'utf8')
  if (file.endsWith('.vue')) source = scriptBlocks(source)
  const kind = /\.(m?js|cjs)$/.test(file) ? ts.ScriptKind.JS : ts.ScriptKind.TS
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, kind)
  out[file] = functions(ts, sf).map(({ name, line, end }) => ({ name, line, end }))
}
process.stdout.write(JSON.stringify(out) + '\n')
