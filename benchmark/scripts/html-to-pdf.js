#!/usr/bin/env node
/**
 * html-to-pdf.js
 * Converts benchmark/fixtures/<slug>/source.html → source.pdf using Puppeteer.
 *
 * Usage:
 *   node scripts/html-to-pdf.js                         # all fixtures
 *   node scripts/html-to-pdf.js --fixture 01-basic-paragraphs
 */

import puppeteer from 'puppeteer';
import { readFileSync, existsSync, readdirSync } from 'fs';
import { resolve, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const FIXTURES_DIR = resolve(__dirname, '../fixtures');

const DEFAULT_PDF_OPTIONS = {
  format: 'A4',
  printBackground: false,
  displayHeaderFooter: false,
  margin: { top: '40px', bottom: '40px', left: '40px', right: '40px' },
};

function loadFixtureConfig(fixturePath) {
  const configPath = join(fixturePath, 'config.json');
  if (!existsSync(configPath)) return { ...DEFAULT_PDF_OPTIONS };
  const overrides = JSON.parse(readFileSync(configPath, 'utf8'));
  return { ...DEFAULT_PDF_OPTIONS, ...overrides };
}

function getFixtureDirs() {
  return readdirSync(FIXTURES_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory() && /^\d{2}-/.test(d.name))
    .sort((a, b) => a.name.localeCompare(b.name))
    .map(d => ({ name: d.name, path: join(FIXTURES_DIR, d.name) }));
}

async function convertFixture(browser, fixturePath, fixtureName) {
  const sourceHtml = join(fixturePath, 'source.html');
  const sourcePdf = join(fixturePath, 'source.pdf');

  if (!existsSync(sourceHtml)) {
    console.warn(`[SKIP] ${fixtureName} — source.html not found`);
    return { skipped: true };
  }

  const page = await browser.newPage();
  try {
    await page.setViewport({ width: 1280, height: 900 });
    await page.goto(`file://${sourceHtml}`, { waitUntil: 'networkidle0', timeout: 30000 });
    await page.emulateMediaType('print');
    const pdfOptions = loadFixtureConfig(fixturePath);
    await page.pdf({ path: sourcePdf, ...pdfOptions });
    console.log(`[OK]   ${fixtureName}`);
    return { ok: true };
  } catch (err) {
    console.error(`[ERR]  ${fixtureName} — ${err.message}`);
    return { error: err.message };
  } finally {
    await page.close();
  }
}

const LAUNCH_ARGS = [
  '--no-sandbox', '--disable-setuid-sandbox',
  '--disable-dev-shm-usage', '--disable-gpu',
];

async function launchBrowser() {
  return puppeteer.launch({ headless: 'new', args: LAUNCH_ARGS });
}

async function main() {
  const args = process.argv.slice(2);
  const fixtureIdx = args.indexOf('--fixture');
  const targetFixture = fixtureIdx !== -1 ? args[fixtureIdx + 1] : null;

  const allFixtures = getFixtureDirs();
  const fixtures = targetFixture
    ? allFixtures.filter(f => f.name === targetFixture)
    : allFixtures;

  if (targetFixture && fixtures.length === 0) {
    console.error(`Fixture not found: ${targetFixture}`);
    process.exit(1);
  }

  console.log(`Converting ${fixtures.length} fixture(s)…\n`);

  let ok = 0, skipped = 0, errors = 0;

  // Use a fresh browser every 10 fixtures to avoid Chrome memory/crash issues
  const BATCH = 10;
  for (let i = 0; i < fixtures.length; i += BATCH) {
    const batch = fixtures.slice(i, i + BATCH);
    const browser = await launchBrowser();
    for (const fixture of batch) {
      const result = await convertFixture(browser, fixture.path, fixture.name);
      if (result.ok) ok++;
      else if (result.skipped) skipped++;
      else errors++;
    }
    await browser.close();
  }

  console.log(`\nDone — ${ok} generated, ${skipped} skipped, ${errors} errors`);
  if (errors > 0) process.exit(1);
}

main().catch(err => { console.error(err); process.exit(1); });
