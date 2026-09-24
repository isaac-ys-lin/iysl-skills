#!/usr/bin/env node
'use strict';
// Local, original SVG algorithms adapted from the TransGlobe source examples.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const U = require('./chart-utils');
const { C, esc, finite, fail, el, text, line, rect, dot, label, wrap, rows, extent, scale, ticks, tick, plot, xAxis } = U;

function waterfall(s, m) {
  const data = rows(s, 1, 10);
  if (!finite(s.start)) fail('waterfall requires numeric start');
  let total = s.start;
  const parts = [{ label: s.startLabel || '期初', from: 0, to: total, total: true }];
  for (const r of data) {
    if (!finite(r.value)) fail('waterfall changes must be finite');
    const from = total; total += r.value;
    if (!finite(total)) fail('waterfall running balance is not finite');
    parts.push({ ...r, from, to: total });
  }
  parts.push({ label: s.endLabel || '期末', from: 0, to: total, total: true });
  if (new Set(parts.map(r => r.label)).size !== parts.length) fail('waterfall start/change/end labels must be unique');
  const tolerance = Number.EPSILON * 16 * Math.max(1, Math.abs(total), Math.abs(s.start), ...data.map(r => Math.abs(r.value)));
  if (s.end !== undefined && (!finite(s.end) || Math.abs(s.end - total) > tolerance)) fail('waterfall end does not equal start plus changes');
  const focus = s.focus || parts.at(-1).label;
  if (!parts.some(r => r.label === focus)) fail('waterfall focus must match a label');
  const [lo, hi] = extent(parts.flatMap(r => [r.from, r.to]));
  const p = plot(m, 125, 45), Y = v => scale(v, lo, hi, p.y + p.h, p.y), step = p.w / parts.length;
  if (step < 75) fail('waterfall labels too dense; widen canvas or use a table');
  let out = '';
  for (const v of ticks(lo, hi)) out += line(p.x, Y(v), p.x + p.w, Y(v)) + text(p.x - 12, Y(v) + 5, tick(v), { 'text-anchor': 'end', fill: C.muted, 'font-size': 16 });
  out += line(p.x, Y(0), p.x + p.w, Y(0), { stroke: C.gray, 'data-baseline': 0 });
  parts.forEach((r, i) => {
    const x = p.x + (i + .18) * step, width = step * .64, y = Math.min(Y(r.from), Y(r.to)), height = Math.abs(Y(r.from) - Y(r.to));
    out += rect(x, y, width, height, r.label === focus ? C.blue : C.gray, { 'data-from': r.from, 'data-to': r.to, 'data-value': r.total ? r.to : r.value });
    if (!height) out += line(x, y, x + width, y, { stroke: C.gray, 'stroke-width': 2 });
    out += label(x + width / 2, p.y + p.h + 26, r.label, step - 10, { 'text-anchor': 'middle' });
    out += label(x + width / 2, y - 10, r.total ? String(r.to) : `${r.value >= 0 ? '+' : ''}${r.value}`, step - 6, { 'text-anchor': 'middle' }, 1);
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
  out += label(p.x + p.w + 12, p.y - 18, `${beforeLabel} → ${afterLabel}（差值）`, 235);
  data.forEach((r, i) => {
    const y = p.y + (i + .5) * slot, color = !s.focus || r.label === s.focus ? C.blue : C.gray;
    const delta = Number((r.after - r.before).toPrecision(12));
    out += label(p.x - 16, y - 4, r.label, p.x - 35, { 'text-anchor': 'end' });
    out += line(X(r.before), y, X(r.after), y, { stroke: C.gray, 'stroke-width': 3 });
    out += dot(X(r.before), y, 'white', { stroke: C.gray, 'stroke-width': 3, 'data-before': r.before });
    out += dot(X(r.after), y, color, { stroke: color, 'data-after': r.after });
    if (slot >= 70) {
      out += text(X(r.before), y - 18, r.before, { 'text-anchor': 'middle', fill: C.muted, 'font-size': 16 });
      out += text(X(r.after), y + 27, r.after, { 'text-anchor': 'middle', fill: color, 'font-size': 16 });
    }
    out += label(p.x + p.w + 12, y + 5, `${r.before} → ${r.after} (${delta >= 0 ? '+' : ''}${delta})`, 240);
  });
  return out + label(p.x, p.y + p.h + 60, `空心＝${beforeLabel}；實心＝${afterLabel}；差值＝後減前`, p.w, { fill: C.muted });
}

function funnel(s, m) {
  const data = rows(s, 2, 8);
  data.forEach((r, i) => {
    if (!Number.isSafeInteger(r.value) || r.value < 0) fail('funnel counts must be nonnegative integers');
    if (i && r.value > data[i - 1].value) fail('funnel stages must not increase; verify same cohort');
  });
  if (!data[0].value) fail('funnel starting cohort must be above zero');
  if (s.sameCohort !== true) fail('funnel requires confirmed sameCohort: true from source data');
  const p = plot(m, 220, 210), slot = p.h / data.length, base = data[0].value;
  if (slot < 45) fail('funnel too dense; increase height or use a stage table');
  let out = text(p.x + p.w + 12, p.y - 18, '件數 / 階段完成率', { fill: C.muted, 'font-size': 16 });
  data.forEach((r, i) => {
    const height = Math.min(48, slot - 16), y = p.y + i * slot + (slot - height) / 2, width = p.w * r.value / base;
    const rate = !i ? '起始母體' : !data[i - 1].value ? '不適用' : `${Number((r.value / data[i - 1].value * 100).toFixed(2))}%`;
    out += label(p.x - 16, y + 20, r.label, p.x - 40, { 'text-anchor': 'end' });
    out += rect(p.x + (p.w - width) / 2, y, width, height, i === data.length - 1 ? C.blue : C.gray, { 'data-count': r.value });
    out += label(p.x + p.w + 12, y + 20, `${r.value} / ${rate}`, 180);
  });
  return out + label(p.x, p.y + p.h + 36, `階段率以前一階段為分母；最終完成率 ${Number((data.at(-1).value / base * 100).toFixed(2))}%（起始母體 ${base}）`, p.w + 100, { fill: C.muted });
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
  if (slot < 60) fail('tornado rows too dense; increase height or split');
  let out = xAxis(p, lo, hi, m.unit) + line(X(s.baseline), p.y, X(s.baseline), p.y + p.h, { stroke: C.ink, 'stroke-width': 2, 'data-baseline': s.baseline });
  out += text(p.x + p.w + 16, p.y - 18, '下界 / 上界結果', { fill: C.muted, 'font-size': 16 });
  data.forEach((r, i) => {
    const y = p.y + (i + .5) * slot;
    out += label(p.x - 16, y - (r.lowLabel ? 8 : 4), r.label, p.x - 40, { 'text-anchor': 'end' }, 1);
    if (r.lowLabel) out += label(p.x - 16, y + 18, `${r.lowLabel} ／ ${r.highLabel}`, p.x - 40, { 'text-anchor': 'end', fill: C.muted, 'font-size': 16 }, 1);
    out += rect(X(r.low), y - 12, X(s.baseline) - X(r.low), 24, C.gray, { 'data-low': r.low });
    out += rect(X(s.baseline), y - 12, X(r.high) - X(s.baseline), 24, C.blue, { 'data-high': r.high });
    out += label(p.x + p.w + 16, y + 5, `${r.low} / ${r.high}`, 185);
  });
  return out + text(p.x, p.y + p.h + 55, `基準：${s.baseline}；橫軸以基準為中心；灰＝下界結果，藍＝上界結果`, { fill: C.muted, 'font-size': 16 });
}

function table(s, m) {
  const data = rows(s, 1, 30), p = plot(m, 60, 60), rowHeight = p.h / (data.length + 1);
  if (data.some(r => r.value !== null && !finite(r.value))) fail('table values must be numbers or null');
  if (rowHeight < 40) fail('table too dense; increase height or use a native paginated table');
  let out = rect(p.x, p.y, p.w, rowHeight, '#F1F3F7') + text(p.x + 12, p.y + 26, s.labelHeader || '項目', { 'font-weight': 700 }) + text(p.x + p.w - 12, p.y + 26, m.unit, { 'text-anchor': 'end', 'font-weight': 700 });
  data.forEach((r, i) => {
    const y = p.y + (i + 1) * rowHeight;
    out += line(p.x, y + rowHeight, p.x + p.w, y + rowHeight);
    out += label(p.x + 12, y + 24, r.label, p.w * .65);
    out += label(p.x + p.w - 12, y + 24, r.value === null ? '未提供' : String(r.value), p.w * .3, { 'text-anchor': 'end' });
  });
  return out;
}

const renderers = { ...require('./basic-charts'), waterfall, dumbbell, funnel, tornado, table,
  ...require('./composition-charts'), ...require('./statistical-charts') };

function render(spec) {
  if (!spec || typeof spec !== 'object') fail('spec must be an object');
  for (const field of ['chart', 'title', 'unit', 'period', 'source']) if (typeof spec[field] !== 'string' || !spec[field].trim()) fail(`requires nonempty ${field}`);
  if (!Array.isArray(spec.notes) || spec.notes.some(v => typeof v !== 'string')) fail('notes must be an array of strings');
  const invalidXML = value => typeof value === 'string' ? /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/.test(value) : Array.isArray(value) ? value.some(invalidXML) : value && typeof value === 'object' ? Object.values(value).some(invalidXML) : false;
  if (invalidXML(spec)) fail('input contains invalid XML control characters');
  const fn = renderers[spec.chart];
  if (typeof fn !== 'function' || !Object.hasOwn(renderers, spec.chart)) fail(`unknown chart; use ${Object.keys(renderers).join(', ')}`);
  if (spec.subtitle !== undefined && (typeof spec.subtitle !== 'string' || !spec.subtitle.trim())) fail('subtitle must be a nonempty reading explanation');
  const w = spec.width ?? 1200, h = spec.height ?? 800;
  if (!Number.isInteger(w) || !Number.isInteger(h) || w < 500 || h < 350 || w > 10000 || h > 20000) fail('canvas must be 500–10000 wide and 350–20000 high');
  const titleLines = wrap(spec.title, (w - 88) / 34);
  if (titleLines.length > 2) fail('title needs more than two lines; increase width or revise title without changing meaning');
  const subtitleLines = spec.subtitle ? wrap(spec.subtitle, (w - 88) / 18) : [];
  if (subtitleLines.length > 3) fail('subtitle needs more than three lines; move supporting detail to notes');
  const subtitleTop = 52 + titleLines.length * 42;
  const extra = spec.chart === 'tornado' ? [`模型：${spec.model}`, ...(spec.assumptions || [])] : spec.chart === 'matrix' ? [`評分：${spec.rubric}`] : [];
  const footer = [`單位：${spec.unit}　期間：${spec.period}`, `資料來源：${spec.source}`, ...spec.notes, ...extra].flatMap(v => wrap(v, (w - 88) / 16));
  const footerTop = h - 32 - (footer.length - 1) * 22;
  const m = { w, h, unit: spec.unit, plotTop: subtitleTop + subtitleLines.length * 24 + 40, plotBottom: footerTop - 148 };
  if (m.plotBottom - m.plotTop < 100) fail('metadata and chart need more height; enlarge canvas or split content');
  const body = fn(spec, m);
  const id = 'tg-' + crypto.createHash('sha256').update(JSON.stringify(spec)).digest('hex').slice(0, 12);
  return el('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: 'img', 'aria-labelledby': `${id}-title ${id}-desc`, 'font-family': 'Arial, Microsoft JhengHei, PingFang TC, Noto Sans TC, sans-serif', 'font-variant-numeric': 'tabular-nums' },
    el('title', { id: `${id}-title` }, esc(spec.title)) + el('desc', { id: `${id}-desc` }, esc([spec.title, spec.subtitle, spec.unit, spec.period, spec.source, ...spec.notes, ...extra].filter(Boolean).join('；'))) +
    el('metadata', {}, esc(JSON.stringify(spec))) + rect(0, 0, w, h, '#FFFFFF') + titleLines.map((v, i) => text(44, 52 + i * 42, v, { fill: '#000099', 'font-size': 34, 'font-weight': 700 })).join('') +
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
