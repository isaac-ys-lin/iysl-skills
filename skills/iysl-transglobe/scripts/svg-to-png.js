#!/usr/bin/env node
'use strict';
// PNG fallback for an SVG chart (Office svgBlip fallback, previews). Usage: node svg-to-png.js in.svg out.png [widthPx]
const fs = require('node:fs');
const [input, output, width = '2400'] = process.argv.slice(2);
if (!input || !output) { console.error('Usage: node svg-to-png.js in.svg out.png [widthPx]'); process.exit(2); }
let Resvg;
try { ({ Resvg } = require('@resvg/resvg-js')); } catch { console.error(`missing dependency @resvg/resvg-js; run: npm ci --prefix "${__dirname}"`); process.exit(1); }
const png = new Resvg(fs.readFileSync(input, 'utf8'), { fitTo: { mode: 'width', value: Number(width) }, font: { loadSystemFonts: true, defaultFontFamily: 'Arial' }, background: 'white' }).render().asPng();
fs.writeFileSync(output, png);
console.log(`wrote ${output}`);
