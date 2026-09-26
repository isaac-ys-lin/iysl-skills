#!/usr/bin/env node
'use strict';
// Usage: node make-gallery.js /absolute/output-directory
const fs = require('node:fs'), path = require('node:path');
const { render, chartTypes } = require('../scripts/render-chart');
const { esc } = require('../scripts/chart-utils');
const out = process.argv[2];
if (!out) throw Error('give an output directory');
const examples = JSON.parse(fs.readFileSync(path.join(__dirname, '../assets/chart-examples.json'), 'utf8'));
const { provenance, charts } = examples;
const catalog = {};
for (const row of fs.readFileSync(path.join(__dirname, '../references/chart-selection.md'), 'utf8').split('\n')) {
  const cells = row.split('|').map(s => s.trim()), id = cells[1]?.match(/^\`([^\`]+)\` (.+)/);
  if (id) catalog[id[1]] = { name: id[2], question: cells[2] };
}
catalog.table = { name: '資料表', question: '需要逐項查核精確數值' };
if (chartTypes.some(chart => !charts[chart]) || Object.keys(charts).some(chart => !chartTypes.includes(chart))) throw Error('source-derived gallery must cover exactly every chart type');
fs.mkdirSync(out, { recursive: true });
const composition = charts.stacked;
if (JSON.stringify(charts.mekko.data) !== JSON.stringify(composition.data)) throw Error('stacked and mekko must retain the same composition source data');
const number = value => Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)));
const totals = composition.data.map(row => ({ label: row.label, value: row.values.reduce((sum, value) => sum + value, 0) }));
const largest = totals.reduce((best, row) => row.value > best.value ? row : best);
const grandTotal = totals.reduce((sum, row) => sum + row.value, 0);
const largestSegment = composition.data.flatMap(row => row.values.map((value, index) => ({
  channel: row.label, category: composition.categories[index], share: value / totals.find(total => total.label === row.label).value * 100
}))).reduce((best, cell) => cell.share > best.share ? cell : best);
const story = [
  {
    id: 'same-data-total-size', question: '哪一個通路的總規模最大？', why: '先把每個通路的三種商品加總，再用排行比較總額。',
    spec: { chart: 'ranking', title: `${largest.label}通路總規模最大，為 ${number(largest.value)} 萬元`, subtitle: '每條是同一通路三種商品的原始金額加總；比較的是總規模。', unit: composition.unit, period: composition.period, source: composition.source, notes: ['由同一份通路×商品原始金額加總；設計示意資料。'], focus: largest.label, data: totals }
  },
  {
    id: 'same-data-within-channel', question: '每個通路內，哪種商品占比最高？', why: '各通路先各自除以總額，再用 100% 堆疊圖比較內部組成。',
    spec: { ...composition, title: `${largestSegment.channel}的${largestSegment.category}占比 ${number(largestSegment.share)}%，三個通路中最高`, subtitle: '每列固定為 100%；比較的是各通路內的商品組成，不比較通路總規模。' }
  },
  {
    id: 'same-data-size-and-composition', question: '總規模與通路內組成要一起看時，誰占整體最大？', why: '矩形寬度保留通路總額、高度保留通路內組成，面積才代表整體份額。',
    spec: { ...charts.mekko, title: `${largest.label}通路規模最大，占三通路總額約 ${number(largest.value / grandTotal * 100)}%`, subtitle: '寬度是通路總規模、高度是通路內組成；矩形面積才可比較整體份額。' }
  }
];
function readerSpec(spec) {
  const notes = spec.chart === 'tracking' ? ['固定通路資料為設計示意，不能視為實際營運值。'] : spec.notes;
  return {
    ...spec,
    source: spec.source.startsWith('iysl-transglobe') ? spec.source : 'TransGlobe Blue 設計原型（示意資料）',
    notes,
    sourceReference: spec.source,
    provenance: { sourceReference: spec.source, originalNotes: spec.notes }
  };
}
function downloadableCard(id, heading, purpose, spec) {
  const outputSpec = readerSpec(spec), svg = render(outputSpec);
  fs.writeFileSync(path.join(out, id + '.json'), JSON.stringify(outputSpec, null, 2));
  fs.writeFileSync(path.join(out, id + '.svg'), svg);
  return `<article id="${id}"><h3>${esc(heading)}</h3><p class="purpose"><strong>問題：</strong>${esc(purpose.question)}<br><strong>選圖：</strong>${esc(purpose.why)}</p><p><a href="${id}.svg" download>SVG</a> · <a href="${id}.json" download>資料 JSON</a></p><div class="chart" tabindex="0" aria-label="${esc(heading)}，窄螢幕可左右捲動">${svg}</div></article>`;
}
const storyCards = story.map(row => downloadableCard(row.id, row.id === 'same-data-total-size' ? '總規模：排行比較' : row.id === 'same-data-within-channel' ? '通路內組成：100% 堆疊長條圖' : '整體規模＋組成：Marimekko 市場結構圖', row, row.spec));
const cards = [];
for (const chart of chartTypes) {
  const spec = charts[chart], { name, question } = catalog[chart];
  const outputSpec = readerSpec(spec), svg = render(outputSpec);
  fs.writeFileSync(path.join(out, chart + '.json'), JSON.stringify(outputSpec, null, 2));
  fs.writeFileSync(path.join(out, chart + '.svg'), svg);
  cards.push(`<section id="${chart}"><h2>${esc(name)}</h2><p class="purpose">用途：${esc(question)}</p><p><a href="${chart}.svg" download>SVG</a> · <a href="${chart}.json" download>資料 JSON</a></p><div class="chart" tabindex="0" aria-label="${esc(name)}，窄螢幕可左右捲動">${svg}</div></section>`);
}
for (const name of fs.readdirSync(path.join(__dirname, '../scripts'))) if (name.endsWith('.js')) fs.copyFileSync(path.join(__dirname, '../scripts', name), path.join(out, name));
const nav = `<a href="#same-data">相同數據，不同問題</a>` + chartTypes.map(id => `<a href="#${id}">${esc(catalog[id].name)}</a>`).join('');
fs.writeFileSync(path.join(out, 'index.html'), `<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>iysl-transglobe｜圖表庫</title><style>
body{font:16px Arial,"Microsoft JhengHei","PingFang TC",sans-serif;color:#111;margin:32px auto;padding:0 24px;max-width:1200px}h1,h2{color:#000099}p{line-height:1.6}.purpose{color:#4A4A4A}nav{display:flex;gap:10px 20px;flex-wrap:wrap}a{color:#28317B}section{margin:48px 0;border-top:1px solid #ddd;padding-top:16px}.story{background:#F7F8FC;border:0;padding:24px}.story article{margin:32px 0}.story article+article{border-top:1px solid #ddd;padding-top:24px}.chart{overflow:auto}svg{display:block;width:100%;min-width:960px;height:auto}code{overflow-wrap:anywhere}@media(max-width:600px){body{margin:20px auto;padding:0 16px}.story{padding:16px}}
</style><h1>iysl-transglobe</h1><p>${esc(provenance.scope)} 每張圖均可下載完整可重製 spec，保留結論、視覺編碼、期間與資料來源。</p><nav>${nav}</nav><section id="same-data" class="story"><h2>相同數據，不同問題</h2><p>三張圖都只讀取同一份「通路 × 商品」原始金額；問題改變，選圖才改變。</p>${storyCards.join('')}</section>${cards.join('')}<p>離線重製：下載整個圖庫目錄後執行 <code>node render-chart.js ranking.json output.svg</code>；各圖均附原始資料與產圖程式。</p></html>`);
console.log(`wrote ${cards.length + story.length} source-derived SVG charts to ${out}`);
