#!/usr/bin/env node
/**
 * run-all.js
 * Runs html-to-pdf.js for all fixtures, isolating per-fixture errors.
 */

import { spawn } from 'child_process';
import { resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const converterScript = resolve(__dirname, 'html-to-pdf.js');

const child = spawn(process.execPath, [converterScript], {
  stdio: 'inherit',
  env: process.env,
});

child.on('exit', code => process.exit(code ?? 0));
