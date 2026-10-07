// Module loader hook: hands each TypeScript file in the traced repo to instrument() before it is compiled.
//
// It must sit *after* the TypeScript loader in the chain (register it first: hooks run last-in, first-out), so
// that ts-node's load() asks us for the source and we see the raw .ts text, not compiled JavaScript. Line numbers
// then stay the file's own, and the compiler's source maps still point at the right lines.

import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { relative } from 'node:path'
import { instrument } from './instrument.mjs'

let cfg
let ts

export function initialize(data) {
  cfg = data
  ts = createRequire(`${cfg.pkg}/package.json`)('typescript') // the repo's own compiler, so its syntax is supported
}

export async function load(url, context, nextLoad) {
  const result = await nextLoad(url, context)
  if (!url.startsWith('file:') || result.source == null || !/\.(ts|mts|cts)$/.test(new URL(url).pathname)) return result
  const path = fileURLToPath(url)
  const inPkg = relative(cfg.pkg, path)
  if (inPkg.startsWith('..') || inPkg.includes('node_modules')) return result
  const roots = /\.spec\.ts$/.test(inPkg)
  if (!roots && !cfg.include.some((prefix) => inPkg.startsWith(prefix))) return result

  const source = typeof result.source === 'string' ? result.source : new TextDecoder().decode(result.source)
  try {
    return { ...result, source: instrument(ts, source, relative(cfg.git, path), { roots, soft: cfg.soft }) }
  } catch (e) {
    console.error(`[codestory] left ${inPkg} uninstrumented: ${e.message}`)
    return result
  }
}
