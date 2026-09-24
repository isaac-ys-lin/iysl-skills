#!/usr/bin/env node
'use strict';
// Usage: node make-gallery.js /absolute/output-directory
const fs = require('node:fs'), path = require('node:path');
const { render } = require('../scripts/render-chart');
const { esc } = require('../scripts/chart-utils');
const { specs, valid } = require('./render-chart.test');
const out = process.argv[2];
if (!out) throw Error('give an output directory');
fs.mkdirSync(out, { recursive: true });
const catalog = {};
for (const row of fs.readFileSync(path.join(__dirname, '../references/chart-selection.md'), 'utf8').split('\n')) {
  const cells = row.split('|').map(s => s.trim()), id = cells[1]?.match(/^`([^`]+)` (.+)/);
  if (id) catalog[id[1]] = { name: id[2], question: cells[2] };
}
catalog.table = { name: '資料表', question: '需要逐項查核精確數值' };
const cards = [];
for (const [chart, data] of Object.entries(specs)) {
  const spec = valid(chart, data), { name, question } = catalog[chart];
  spec.title = question;
  spec.source = '合成驗證資料，非實際營運數據';
  if (chart === 'waffle') spec.unit = '%';
  const svg = render(spec);
  fs.writeFileSync(path.join(out, chart + '.json'), JSON.stringify(spec, null, 2));
  fs.writeFileSync(path.join(out, chart + '.svg'), svg);
  cards.push(`<section id="${chart}"><h2>${esc(name)}</h2><p>${esc(question)}</p><p><a href="${chart}.svg" download>SVG</a> · <a href="${chart}.json" download>資料 JSON</a></p><div class="chart" tabindex="0" aria-label="${esc(name)}，窄螢幕可左右捲動">${svg}</div></section>`);
}
for (const name of fs.readdirSync(path.join(__dirname, '../scripts'))) {
  if (name.endsWith('.js')) fs.copyFileSync(path.join(__dirname, '../scripts', name), path.join(out, name));
}
const nav = Object.entries(catalog).map(([id, c]) => `<a href="#${id}">${esc(c.name)}</a>`).join('');
fs.writeFileSync(path.join(out, 'index.html'), `<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>iysl-transglobe｜圖表庫</title><style>
body{font:16px Arial,"Microsoft JhengHei","PingFang TC",sans-serif;color:#111;margin:32px auto;padding:0 24px;max-width:1200px}h1,h2{color:#000099}p{line-height:1.6}nav{display:flex;gap:10px 20px;flex-wrap:wrap}a{color:#28317B}section{margin:48px 0;border-top:1px solid #ddd;padding-top:16px}.chart{overflow:auto}svg{display:block;width:100%;min-width:960px;height:auto}code{overflow-wrap:anywhere}@media(max-width:600px){body{margin:20px auto;padding:0 16px}}
</style><h1>iysl-transglobe</h1><p>18 種情境圖表，加上資料表。以下均為合成資料；使用時會依問題和資料資格自動選圖。</p><nav>${nav}</nav>${cards.join('')}<p>離線重製：下載整個圖庫目錄後執行 <code>node render-chart.js ranking.json output.svg</code>；各圖均附原始資料與產圖程式。</p></html>`);
console.log(`wrote ${cards.length} SVG charts to ${out}`);
