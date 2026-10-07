// Entry point for tracing a TypeScript run. Load it before the TypeScript loader:
//
//   CS_TRACE_OUT=/abs/trace.json node --enable-source-maps \
//     --import /abs/codestory/ts/register.mjs --import ts-node-maintained/register/esm \
//     bin/test.ts unit --files=parser.spec.ts
//
// Run from the package root (the directory with package.json). Environment:
//   CS_TRACE_OUT  where to write the trace (required)
//   CS_INCLUDE    comma-separated path prefixes, relative to the package, to instrument (default: app/)
//   CS_TEST       record only tests whose title contains this
//   CS_SOFT_IMPORTS=1  a spec's missing imports become undefined instead of failing the file (for the base side)
//   CS_MAX_CALLS  stop recording a test after this many calls (default 20000), so a runaway loop stays bounded
// Spec files (*.spec.ts) are always rewritten so that each test callback is a scenario root.

import { register } from 'node:module'
import { execFileSync } from 'node:child_process'
import './runtime.mjs'

const pkg = process.cwd()
const git = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd: pkg, encoding: 'utf8' }).trim()
const include = (process.env.CS_INCLUDE ?? 'app/').split(',').map((s) => s.trim()).filter(Boolean)

register('./hooks.mjs', import.meta.url, { data: { pkg, git, include, soft: process.env.CS_SOFT_IMPORTS === '1' } })
