#!/usr/bin/env node
/**
 * Regenerates the inline <script id="inlineMonthData"> and INLINE_MANIFEST
 * in index.html from data/index.json + data/*.json files.
 *
 * Usage: node scripts/update_inline.js
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const INDEX_HTML = path.join(ROOT, 'index.html');
const DATA_DIR = path.join(ROOT, 'data');

// Read manifest
const manifest = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'index.json'), 'utf8'));

// Read all month files
const months = {};
for (const ym of manifest.months) {
  const fp = path.join(DATA_DIR, ym + '.json');
  if (fs.existsSync(fp)) {
    months[ym] = JSON.parse(fs.readFileSync(fp, 'utf8'));
  }
}

// Read index.html
let html = fs.readFileSync(INDEX_HTML, 'utf8');

// Replace inline month data
const inlineMonthsStr = 'window._INLINE_MONTHS=' + JSON.stringify(months) + ';';
html = html.replace(
  /window\._INLINE_MONTHS=\{[\s\S]*?\};\s*\n/,
  inlineMonthsStr + '\n'
);

// Replace inline manifest
const inlineManifestStr = JSON.stringify(manifest);
html = html.replace(
  /const INLINE_MANIFEST=\{[\s\S]*?\};/,
  'const INLINE_MANIFEST=' + inlineManifestStr + ';'
);

fs.writeFileSync(INDEX_HTML, html, 'utf8');

const totalRuns = Object.values(months).reduce((n, m) =>
  n + (m.events || []).reduce((r, e) => r + (e.runs || []).length, 0), 0);
console.log(`Updated inline data: ${manifest.months.length} month(s), ${totalRuns} runs`);
console.log('Manifest and month data synced to index.html');
