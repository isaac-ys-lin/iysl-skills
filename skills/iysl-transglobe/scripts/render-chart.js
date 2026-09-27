#!/usr/bin/env node
'use strict';
// Local, original SVG algorithms adapted from the TransGlobe source examples.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const U = require('./chart-utils');
const { C, esc, finite, fail, el, text, line, rect, dot, label, wrap, rows, extent, scale, ticks, tick, num, plot, xAxis } = U;

function waterfall(s, m) {
  const parts = U.waterfallData(s);
  const focus = s.focus || parts.at(-1).label;
  if (!parts.some(r => r.label === focus)) fail('waterfall focus must match a label');
  const [lo, hi] = extent(parts.flatMap(r => [r.from, r.to]));
  const p = plot(m, 125, 45), Y = v => scale(v, lo, hi, p.y + p.h, p.y), step = p.w / parts.length;
  if (step < 75) fail('waterfall labels too dense; widen canvas or use a table');
  let out = '';
  for (const v of ticks(lo, hi)) out += line(p.x, Y(v), p.x + p.w, Y(v)) + text(p.x - 12, Y(v) + 5, tick(v), { 'text-anchor': 'end', fill: C.muted, 'font-size': 18 });
  out += line(p.x, Y(0), p.x + p.w, Y(0), { stroke: C.gray, 'data-baseline': 0 });
  parts.forEach((r, i) => {
    const x = p.x + (i + .18) * step, width = step * .64, y = Math.min(Y(r.from), Y(r.to)), height = Math.abs(Y(r.from) - Y(r.to));
    out += rect(x, y, width, height, r.label === focus ? C.blue : C.gray, { 'data-from': r.from, 'data-to': r.to, 'data-value': r.total ? r.to : r.value });
    if (!height) out += line(x, y, x + width, y, { stroke: C.gray, 'stroke-width': 2 });
    out += label(x + width / 2, p.y + p.h + 26, r.label, step - 10, { 'text-anchor': 'middle' });
    out += label(x + width / 2, y - 10, r.total ? num(r.to) : `${r.value >= 0 ? '+' : ''}${num(r.value)}`, step - 6, { 'text-anchor': 'middle' }, 1);
    if (i < parts.length - 1) out += line(x + width, Y(r.to), p.x + (i + 1.18) * step, Y(r.to), { stroke: C.gray, 'stroke-dasharray': '5 4' });
  });
  return out;
}

function dumbbell(s, m) {
  const data = rows(s, 1, 10);
  if (data.some(r => !finite(r.before) || !finite(r.after))) fail('dumbbell needs numeric before and after');
  const [lo, hi] = extent(data.flatMap(r => [r.before, r.after])), p = plot(m, 220, 280), X = v => scale(v, lo, hi, p.x, p.x + p.w), slot = p.h / data.length;
  if (slot < 46) fail('dumbbell rows too dense; increase height or split');
  if (s.focus !== undefined) U.namedFocus(s, data);
  const beforeLabel = s.beforeLabel || '前', afterLabel = s.afterLabel || '後';
  let out = xAxis(p, lo, hi, m.unit);
  out += label(p.x + p.w + 32, p.y - 18, `${beforeLabel} → ${afterLabel}（差值）`, 248, { fill: C.muted, 'font-size': 18 });
  data.forEach((r, i) => {
    const y = p.y + (i + .5) * slot, color = !s.focus || r.label === s.focus ? C.blue : C.gray;
    const delta = U.difference(r.before, r.after);
    out += label(p.x - 16, y - 4, r.label, p.x - 35, { 'text-anchor': 'end' });
    out += line(X(r.before), y, X(r.after), y, { stroke: C.gray, 'stroke-width': 3 });
    out += dot(X(r.before), y, 'white', { stroke: C.gray, 'stroke-width': 3, 'data-before': r.before });
    out += dot(X(r.after), y, color, { stroke: color, 'data-after': r.after });
    if (slot >= 70) {
      out += text(X(r.before), y - 18, num(r.before), { 'text-anchor': 'middle', fill: C.muted, 'font-size': 18 });
      out += text(X(r.after), y + 27, num(r.after), { 'text-anchor': 'middle', fill: color === C.gray ? C.muted : color, 'font-size': 18 });
    }
    out += label(p.x + p.w + 32, y + 5, `${num(r.before)} → ${num(r.after)} (${delta >= 0 ? '+' : ''}${num(delta)})`, 248);
  });
  return out + label(p.x, p.y + p.h + 60, `空心＝${beforeLabel}；實心＝${afterLabel}；差值＝後減前`, m.w - p.x - 44, { fill: C.muted });
}

function funnel(s, m) {
  const data = rows(s, 2, 8);
  data.forEach((r, i) => {
    if (!Number.isSafeInteger(r.value) || r.value < 0) fail('funnel counts must be nonnegative integers');
    if (i && r.value > data[i - 1].value) fail('funnel stages must not increase; verify same cohort');
  });
  if (!data[0].value) fail('funnel starting cohort must be above zero');
  if (s.sameCohort !== true) fail('funnel requires confirmed sameCohort: true from source data');
  const rates = U.funnelRates(data);
  const p = plot(m, 220, 210), slot = p.h / data.length, base = data[0].value;
  if (slot < 45) fail('funnel too dense; increase height or use a stage table');
  let out = text(p.x + p.w + 12, p.y - 18, '件數 / 階段完成率', { fill: C.muted, 'font-size': 18 });
  data.forEach((r, i) => {
    const height = Math.min(48, slot - 16), y = p.y + i * slot + (slot - height) / 2, width = p.w * r.value / base;
    const rate = !i ? '起始母體' : rates.stages[i] === null ? '不適用' : `${U.derived(rates.stages[i], 2)}%`;
    out += label(p.x - 16, y + 20, r.label, p.x - 40, { 'text-anchor': 'end' });
    out += rect(p.x + (p.w - width) / 2, y, width, height, i === data.length - 1 ? C.blue : C.gray, { 'data-count': r.value });
    out += label(p.x + p.w + 12, y + 20, `${num(r.value)} / ${rate}`, 180);
  });
  return out + label(p.x, p.y + p.h + 36, `階段率以前一階段為分母；最終完成率 ${U.derived(rates.completion, 2)}%（起始母體 ${num(base)}）`, p.w + 100, { fill: C.muted, 'font-size': 18 });
}

function tornado(s, m) {
  const input = rows(s, 2, 8);
  if (!finite(s.baseline)) fail('tornado requires numeric baseline outcome');
  if (typeof s.model !== 'string' || !s.model.trim() || !Array.isArray(s.assumptions) || !s.assumptions.length || s.assumptions.some(v => typeof v !== 'string' || !v.trim())) fail('tornado requires model and assumptions');
  if (input.some(r => !finite(r.low) || !finite(r.high) || r.low > s.baseline || r.high < s.baseline)) fail('each tornado outcome must bracket baseline; use a range plot/table for non-bracketing scenarios');
  if (input.some(r => (r.lowLabel !== undefined || r.highLabel !== undefined) && [r.lowLabel, r.highLabel].some(v => typeof v !== 'string' || !v.trim()))) fail('tornado lowLabel and highLabel must both describe source assumptions');
  const data = [...input].sort((a, b) => (b.high - b.low) - (a.high - a.low));
  const span = Math.max(...data.flatMap(r => [s.baseline - r.low, r.high - s.baseline])) * 1.2 || 1;
  const lo = s.baseline - span, hi = s.baseline + span, p = plot(m, 300, 220), X = v => scale(v, lo, hi, p.x, p.x + p.w), slot = p.h / data.length;
  // Two-line factor labels (name + tested range) span ~41px; single-line rows need 40px.
  if (slot < (data.some(r => r.lowLabel) ? 50 : 40)) fail('tornado rows too dense; increase height or split');
  const focus = s.focus === undefined ? null : U.namedFocus(s, data);
  let out = xAxis(p, lo, hi, m.unit) + line(X(s.baseline), p.y, X(s.baseline), p.y + p.h, { stroke: C.ink, 'stroke-width': 2, 'data-baseline': s.baseline });
  out += text(p.x + p.w + 32, p.y - 18, '下界 / 上界結果', { fill: C.muted, 'font-size': 18 });
  data.forEach((r, i) => {
    const y = p.y + (i + .5) * slot;
    out += label(p.x - 16, y - (r.lowLabel ? 6 : 4), r.label, p.x - 40, { 'text-anchor': 'end' }, 1);
    if (r.lowLabel) out += label(p.x - 16, y + 15, `${r.lowLabel} ／ ${r.highLabel}`, p.x - 40, { 'text-anchor': 'end', fill: C.muted, 'font-size': 18 }, 1);
    // Focus semantics: the titled factor is blue, others gray; low/high are read from their side of the baseline.
    const color = !focus || r.label === focus ? C.blue : C.gray;
    out += rect(X(r.low), y - 12, X(s.baseline) - X(r.low), 24, color, { 'data-low': r.low });
    out += rect(X(s.baseline), y - 12, X(r.high) - X(s.baseline), 24, color, { 'data-high': r.high });
    out += label(p.x + p.w + 32, y + 5, `${num(r.low)} / ${num(r.high)}`, 185);
  });
  return out + text(X(s.baseline), p.y + p.h + 28, `基準 ${num(s.baseline)}`, { 'text-anchor': 'middle', fill: C.ink, 'font-size': 18 });
}

function table(s, m) {
  const data = rows(s, 1, 30), p = plot(m, 60, 60), rowHeight = p.h / (data.length + 1);
  if (data.some(r => r.value !== null && !finite(r.value))) fail('table values must be numbers or null');
  if (rowHeight < 34) fail('table too dense; increase height or use a native paginated table');
  if (s.focus !== undefined) U.namedFocus(s, data);
  let out = rect(p.x, p.y, p.w, rowHeight, '#F1F3F7') + text(p.x + 12, p.y + 26, s.labelHeader || '項目', { 'font-weight': 700 }) + text(p.x + p.w - 12, p.y + 26, m.unit, { 'text-anchor': 'end', 'font-weight': 700 });
  data.forEach((r, i) => {
    const y = p.y + (i + 1) * rowHeight;
    out += line(p.x, y + rowHeight, p.x + p.w, y + rowHeight);
    const emphasis = r.label === s.focus ? { fill: C.blue, 'font-weight': 700 } : {};
    out += label(p.x + 12, y + 24, r.label, p.w * .65, emphasis);
    out += label(p.x + p.w - 12, y + 24, r.value === null ? '未提供' : num(r.value), p.w * .3, { 'text-anchor': 'end', ...emphasis });
  });
  return out;
}

const renderers = { ...require('./basic-charts'), waterfall, dumbbell, funnel, tornado, table,
  ...require('./composition-charts'), ...require('./statistical-charts'), ...require('./extension-charts') };

// Reader-facing facts use the same calculations and display precision as the marks.
function derivedSummary(spec) {
  if (['stacked', 'mekko', 'sharetrend'].includes(spec.chart)) {
    const { data, categories, totals, shares } = U.composition(spec, null, spec.data.length);
    const grand = U.sum(totals);
    return data.map((row, i) => `${row.label} 總量 ${num(totals[i])}，${categories.map((name, j) => `${name} ${U.derived(shares[i][j], 1)}%`).join('、')}${spec.chart === 'mekko' ? `，市場占比 ${U.derived(U.percent(totals[i], grand), 1)}%` : ''}`).join('；');
  }
  if (spec.chart === 'indexed') return U.indexedData(spec.data).map(row => `${row.label} 指數：${row.values.map((value, i) => `${spec.labels[i]} ${value === null ? '未提供' : U.derived(value)}`).join('、')}`).join('；');
  if (spec.chart === 'waterfall') return U.waterfallData(spec).map(row => `${row.label} 餘額 ${num(row.to)}`).join('；');
  if (spec.chart === 'dumbbell') return spec.data.map(row => `${row.label} 差值 ${num(U.difference(row.before, row.after))}`).join('；');
  if (spec.chart === 'funnel') {
    const rates = U.funnelRates(spec.data);
    return spec.data.map((row, i) => `${row.label} 階段率 ${!i ? '起始母體' : rates.stages[i] === null ? '不適用' : U.derived(rates.stages[i], 2) + '%'}`).join('；') + `；最終完成率 ${U.derived(rates.completion, 2)}%`;
  }
  if (spec.chart === 'pareto') {
    const { data, cumulative } = U.paretoData(spec);
    return data.map((row, i) => `${row.label} 累計 ${U.derived(cumulative[i])}%`).join('；');
  }
  if (spec.chart === 'histogram') {
    const { counts, edges } = U.histogramData(spec);
    return counts.map((count, i) => `[${num(edges[i])}, ${num(edges[i + 1])}) ${num(count)} 筆`).join('；');
  }
  return '';
}

function readingNotes(spec) {
  const notes = [], data = Array.isArray(spec.data) ? spec.data : [];
  if (['trend', 'tracking', 'indexed'].includes(spec.chart)) {
    for (const row of data) {
      if (!Array.isArray(row?.values)) continue;
      const missing = row.values.flatMap((value, i) => value === null ? [spec.labels?.[i] ?? i + 1] : []);
      if (missing.length) notes.push(`未提供：${row.label}／${missing.join('、')}（缺值斷線）`);
    }
  }
  if (spec.chart === 'combo') for (const [key, name] of [['value', `柱（${spec.unit}）`], ['rate', spec.rateLabel]]) {
    const missing = data.filter(row => row?.[key] === null).map(row => row.label);
    if (missing.length) notes.push(`未提供：${name}／${missing.join('、')}${key === 'rate' ? '（缺值斷線）' : ''}`);
  }
  if (['trend', 'tracking', 'box'].includes(spec.chart) && spec.yDomain !== undefined) {
    const [lo, hi] = U.domain(spec.yDomain, 'yDomain');
    notes.push(`顯示範圍：${num(lo)}–${num(hi)} ${spec.unit}${lo > 0 || hi < 0 ? '；縱軸不含零' : ''}`);
  }
  return notes;
}

// Long description for screen readers and detached SVGs: the plotted values, not only the metadata.
function dataSummary(spec) {
  const value = v => v === null ? '未提供' : num(v), data = Array.isArray(spec.data) ? spec.data : [];
  if (data.length && data.every(finite)) return `${num(data.length)} 筆觀察值，範圍 ${num(Math.min(...data))}–${num(Math.max(...data))}`;
  const names = { actual: '實際', target: '目標', before: spec.beforeLabel || '前', after: spec.afterLabel || '後', low: '下界', high: '上界', x: spec.xLabel || 'x', y: spec.yLabel || 'y', q1: 'Q1', median: '中位', q3: 'Q3', outliers: '離群', rate: spec.rateLabel || '比率' };
  const columns = spec.labels || spec.series || spec.categories || [];
  const text = data.filter(r => r && typeof r === 'object').map(r => `${r.label}：` + Object.entries(r).filter(([k]) => k === 'value' || names[k] || k === 'values').map(([k, v]) =>
    Array.isArray(v) ? (k === 'values' ? v.map((x, i) => `${columns[i] ?? i + 1} ${value(x)}`).join('、') : `${names[k]} ${v.length ? v.map(value).join('、') : '無'}`) : `${k === 'value' ? '' : names[k] + ' '}${value(v)}`).join('，')).join('；');
  const full = (finite(spec.start) ? `期初 ${num(spec.start)}；` : '') + text;
  return full.length > 600 ? full.slice(0, 600) + '…（完整數值見附表與 metadata）' : full;
}

function render(spec) {
  if (!spec || typeof spec !== 'object') fail('spec must be an object');
  for (const field of ['chart', 'title', 'unit', 'period', 'source']) if (typeof spec[field] !== 'string' || !spec[field].trim()) fail(`requires nonempty ${field}`);
  if (!Array.isArray(spec.notes) || spec.notes.some(v => typeof v !== 'string')) fail('notes must be an array of strings');
  const invalidXML = value => typeof value === 'string' ? /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/.test(value) : Array.isArray(value) ? value.some(invalidXML) : value && typeof value === 'object' ? Object.values(value).some(invalidXML) : false;
  if (invalidXML(spec)) fail('input contains invalid XML control characters');
  const fn = renderers[spec.chart];
  if (typeof fn !== 'function' || !Object.hasOwn(renderers, spec.chart)) fail(`unknown chart; use ${Object.keys(renderers).join(', ')}`);
  if (spec.categoryDomain !== undefined && !['waffle', 'stacked', 'mekko', 'sharetrend', 'grouped', 'tracking'].includes(spec.chart)) fail('categoryDomain is only supported by categorical charts');
  if (spec.yDomain !== undefined && !['trend', 'tracking', 'box', 'scatter', 'matrix'].includes(spec.chart)) fail('yDomain is only supported by trend, tracking, box, scatter and matrix');
  if (spec.xDomain !== undefined && !['scatter', 'matrix'].includes(spec.chart)) fail('xDomain is only supported by scatter and matrix');
  if (spec.subtitle !== undefined && (typeof spec.subtitle !== 'string' || !spec.subtitle.trim())) fail('subtitle must be a nonempty reading explanation');
  const layout = spec.layout ?? 'web';
  const size = { web: [1200, 800], document: [840, 720], slide: [960, 540] };
  if (typeof layout !== 'string' || !Object.hasOwn(size, layout)) fail('layout must be web, document, or slide');
  const w = spec.width ?? size[layout][0], h = spec.height ?? size[layout][1];
  if (!Number.isInteger(w) || !Number.isInteger(h) || w < 500 || h < 350 || w > 10000 || h > 20000) fail('canvas must be 500–10000 wide and 350–20000 high');
  if (layout !== 'web' && (!finite(spec.placementWidthInches) || spec.placementWidthInches <= 0)) fail('Office layout requires the actual placementWidthInches');
  if (layout === 'web' && spec.placementWidthInches !== undefined) fail('placementWidthInches requires document or slide layout');
  // Slide titles follow design-rules: 36px on the 1280 base × 0.75 = 27pt on a 960pt slide.
  const titleSize = layout === 'slide' ? 27 : 34, titleTop = 18 + titleSize, titleStep = Math.round(titleSize * 1.24);
  const titleLines = wrap(spec.title, (w - 88) / titleSize);
  if (titleLines.length > 2) fail('title needs more than two lines; increase width or revise title without changing meaning');
  const subtitleLines = spec.subtitle ? wrap(spec.subtitle, (w - 88) / 18) : [];
  if (subtitleLines.length > 3) fail('subtitle needs more than three lines; move supporting detail to notes');
  const subtitleTop = titleTop + titleLines.length * titleStep;
  const extra = [...(spec.chart === 'tornado' ? [`模型：${spec.model}；假設：${(spec.assumptions || []).join('；')}`] : spec.chart === 'matrix' ? [`評分：${spec.rubric}`] : []), ...readingNotes(spec)];
  const footer = [`單位：${spec.unit}　期間：${spec.period}`, `資料來源：${spec.source}`, ...spec.notes, ...extra].flatMap(v => wrap(v, (w - 88) / 16));
  const footerTop = h - 32 - (footer.length - 1) * 22;
  const bottomGap = { ranking: 70, ordered: 70, bullet: 90, heatmap: 100, trend: 75, tracking: 75, waterfall: 85, dumbbell: 120, funnel: 115, tornado: 70, table: 40, waffle: 40, stacked: 120, mekko: 145, pareto: 90, indexed: 110, scatter: 160, box: 110, matrix: 95, grouped: 70, combo: 95, histogram: 90, sharetrend: 130 }[spec.chart];
  const topGap = { heatmap: 60, stacked: 72, mekko: 72, grouped: 60, combo: 60, sharetrend: 60 }[spec.chart] || 40;
  const m = { w, h, unit: spec.unit, plotTop: subtitleTop + subtitleLines.length * 24 + topGap, plotBottom: footerTop - bottomGap };
  if (m.plotBottom - m.plotTop < 100) fail('metadata and chart need more height; enlarge canvas or split content');
  const body = fn(spec, m);
  const placement = { 'data-layout': layout };
  if (layout !== 'web') {
    const scaleToPoints = spec.placementWidthInches * 72 / w;
    const bodyPoints = Math.min(18, ...[...body.matchAll(/font-size="([\d.]+)"/g)].map(match => Number(match[1]))) * scaleToPoints;
    const footerPoints = 16 * scaleToPoints;
    const [minBody, minFooter] = layout === 'document' ? [9, 8] : [16, 12];
    if (bodyPoints < minBody || footerPoints < minFooter) fail(`text would be too small at ${spec.placementWidthInches} inches; reflow with a narrower canvas, enlarge the placement, or split the chart`);
    Object.assign(placement, { 'data-placement-width-inches': spec.placementWidthInches, 'data-body-size-pt': bodyPoints, 'data-footer-size-pt': footerPoints });
  }
  const id = 'tg-' + crypto.createHash('sha256').update(JSON.stringify(spec)).digest('hex').slice(0, 12);
  return el('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: 'img', 'aria-labelledby': `${id}-title ${id}-desc`, 'font-family': 'Arial, Microsoft JhengHei, PingFang TC, Noto Sans TC, sans-serif', ...placement },
    el('title', { id: `${id}-title` }, esc(spec.title)) + el('desc', { id: `${id}-desc` }, esc([spec.title, spec.subtitle, spec.unit, spec.period, spec.source, ...spec.notes, ...extra, `數值：${dataSummary(spec)}`, derivedSummary(spec)].filter(Boolean).join('；'))) +
    el('metadata', {}, esc(JSON.stringify(spec))) + rect(0, 0, w, h, '#FFFFFF') + titleLines.map((v, i) => text(44, titleTop + i * titleStep, v, { fill: '#000099', 'font-size': titleSize, 'font-weight': 700 })).join('') +
    subtitleLines.map((v, i) => text(44, subtitleTop + i * 24, v, { fill: C.muted, 'font-size': 18, 'data-reading-guide': true })).join('') + body + line(44, footerTop - 24, w - 44, footerTop - 24) +
    footer.map((v, i) => text(44, footerTop + i * 22, v, { fill: C.muted, 'font-size': 16 })).join(''));
}

module.exports = { render, chartTypes: Object.keys(renderers) };
if (require.main === module) {
  const [input, output] = process.argv.slice(2);
  if (!input || !output) { console.error('Usage: node render-chart.js input.json output.svg'); process.exit(2); }
  try {
    if (path.resolve(input) === path.resolve(output)) fail('input and output paths must differ');
    const svg = render(JSON.parse(fs.readFileSync(input, 'utf8')));
    fs.writeFileSync(output, svg);
  } catch (error) { console.error(error.message); process.exit(1); }
}
