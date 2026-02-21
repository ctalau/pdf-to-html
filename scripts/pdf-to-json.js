#!/usr/bin/env node
import { readdir, writeFile } from 'fs/promises';
import { join, dirname, basename } from 'path';
import { fileURLToPath } from 'url';
import PDFParser from 'pdf2json';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

async function findPDFs(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const pdfs = [];
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      pdfs.push(...await findPDFs(fullPath));
    } else if (entry.isFile() && entry.name.endsWith('.pdf')) {
      pdfs.push(fullPath);
    }
  }
  return pdfs;
}

function parsePDF(pdfPath) {
  return new Promise((resolve, reject) => {
    const parser = new PDFParser(null, 1);
    parser.on('pdfParser_dataError', reject);
    parser.on('pdfParser_dataReady', (data) => resolve(data));
    parser.loadPDF(pdfPath);
  });
}

const pdfs = await findPDFs(ROOT + '/benchmark');
console.log(`Found ${pdfs.length} PDFs`);

for (const pdfPath of pdfs) {
  const outPath = pdfPath.replace(/\.pdf$/, '.json');
  try {
    const data = await parsePDF(pdfPath);
    await writeFile(outPath, JSON.stringify(data, null, 2));
    console.log(`  wrote ${basename(outPath)} in ${dirname(pdfPath).split('/').slice(-2).join('/')}`);
  } catch (err) {
    console.error(`  ERROR ${pdfPath}: ${err.message}`);
  }
}

console.log('Done.');
