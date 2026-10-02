#!/usr/bin/env node
'use strict';
// deck.pptx → page PNGs for the review step. Uses LibreOffice when installed; otherwise PowerPoint for Mac, exporting
// inside its sandbox container so macOS shows no file-access prompt. Without pdftoppm the PDF is left to read directly.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const has = cmd => {
  try { execFileSync(process.platform === 'win32' ? 'where' : 'which', [cmd], { stdio: 'ignore' }); return true; } catch { return false; }
};
const [input, outArg] = process.argv.slice(2);
if (!input) { console.error('Usage: node preview-deck.js deck.pptx [outdir]'); process.exit(2); }
const deck = path.resolve(input), name = path.basename(deck, path.extname(deck));
const out = path.resolve(outArg || path.join(path.dirname(deck), 'preview'));
const pdf = path.join(out, `${name}.pdf`);
fs.mkdirSync(out, { recursive: true });

let renderer;
if (has('soffice')) {
  renderer = 'LibreOffice (substitute fonts, layout only)';
  execFileSync('soffice', ['--headless', '--convert-to', 'pdf', '--outdir', out, deck], { stdio: 'ignore' });
} else if (process.platform === 'darwin' && fs.existsSync('/Applications/Microsoft PowerPoint.app')) {
  renderer = 'PowerPoint';
  const box = path.join(os.homedir(), 'Library/Containers/com.microsoft.Powerpoint/Data/iysl-transglobe-preview');
  // A distinct name avoids PowerPoint refusing a second open presentation with the same name.
  const src = path.join(box, `${name}-preview.pptx`), dst = path.join(box, `${name}-preview.pdf`);
  fs.mkdirSync(box, { recursive: true });
  fs.copyFileSync(deck, src);
  execFileSync('osascript', ['-e', 'on run argv', '-e', 'tell application "Microsoft PowerPoint"',
    '-e', 'open POSIX file (item 1 of argv)', '-e', 'delay 1',
    '-e', 'save active presentation in POSIX file (item 2 of argv) as save as PDF',
    '-e', 'close active presentation saving no', '-e', 'end tell', '-e', 'end run', src, dst]);
  fs.copyFileSync(dst, pdf);
} else {
  console.error('No LibreOffice or PowerPoint for Mac found: skip the visual review and say so when delivering.');
  process.exit(3);
}
if (has('pdftoppm')) {
  execFileSync('pdftoppm', ['-png', '-r', '60', pdf, path.join(out, 'page')]);
  console.log(`${renderer}: page images in ${out}`);
} else console.log(`${renderer}: ${pdf} (no pdftoppm; read the PDF directly)`);
