#!/usr/bin/env node
/**
 * verify-fixtures.js
 * Checks every numbered fixture directory has both source.html and source.pdf.
 */

import { readdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const FIXTURES_DIR = resolve(__dirname, '../fixtures');

const dirs = readdirSync(FIXTURES_DIR, { withFileTypes: true })
  .filter(d => d.isDirectory() && /^\d{2}-/.test(d.name))
  .sort((a, b) => a.name.localeCompare(b.name));

let missing = 0;
for (const dir of dirs) {
  const base = join(FIXTURES_DIR, dir.name);
  const hasHtml = existsSync(join(base, 'source.html'));
  const hasPdf  = existsSync(join(base, 'source.pdf'));
  const status  = hasHtml && hasPdf ? '✓' : '✗';
  const detail  = [
    !hasHtml && 'missing source.html',
    !hasPdf  && 'missing source.pdf',
  ].filter(Boolean).join(', ');
  console.log(`${status} ${dir.name}${detail ? '  ← ' + detail : ''}`);
  if (!hasHtml || !hasPdf) missing++;
}

console.log(`\n${dirs.length - missing}/${dirs.length} fixtures complete${missing ? `, ${missing} missing` : ''}`);
process.exit(missing > 0 ? 1 : 0);
