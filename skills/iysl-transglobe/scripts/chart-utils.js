'use strict';

// The six source chart families share scales and text, not their visual encoding.
const C = {
  ink: '#111111', muted: '#4A4A4A', blue: '#28317B', gray: '#7F7F7F', grid: '#DDDDDD',
  seq: ['#D1DDF7', '#9DB1D9', '#7285BB', '#4B5A9C', '#28317B'],
  cat: ['#28317B', '#04696C', '#4A8F5B', '#D09FE2'],
};
const esc = value => String(value).replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;',
}[c]));
const finite = value => typeof value === 'number' && Number.isFinite(value);
const fail = message => { throw new Error(`iysl-transglobe chart: ${message}`); };
const pos = n => Number(n.toFixed(3));
const el = (tag, attrs, body = '') => `<${tag}${Object.entries(attrs).map(([k, v]) => {
  if (typeof v === 'number' && !finite(v)) fail(`nonfinite SVG attribute ${k}`);
  return ` ${k}="${esc(typeof v === 'number' && !k.startsWith('data-') ? pos(v) : v)}"`;
}).join('')}>${body}</${tag}>`;
const text = (x, y, value, attrs = {}) => el('text', { x, y, fill: C.ink, 'font-size': 20, ...attrs }, esc(value));
const line = (x1, y1, x2, y2, attrs = {}) => el('line', { x1, y1, x2, y2, stroke: C.grid, ...attrs });
const rect = (x, y, width, height, fill, attrs = {}) => {
  if (width < 0 || height < 0) fail('negative rectangle dimensions; increase canvas or split the chart');
  return el('rect', { x, y, width, height, fill, ...attrs });
};
const dot = (cx, cy, fill, attrs = {}) => el('circle', { cx, cy, r: 5, fill, ...attrs });
const countWidth = s => [...String(s)].reduce((n, c) => n + (/[^\x00-\x7F]/.test(c) ? 1 : 0.57), 0);

function wrap(value, width) {
  const result = []; let row = '';
  for (const c of String(value)) {
    if (countWidth(row + c) > width && row) { result.push(row); row = ''; }
    row += c;
  }
  if (row) result.push(row);
  return result;
}

function label(x, y, value, width, attrs = {}, maxLines = 2) {
  const fontSize = attrs['font-size'] || 20, lines = wrap(value, width / fontSize);
  if (lines.length > maxLines) fail(`label "${value}" needs more room; enlarge or split the chart, or use a table`);
  return lines.map((s, i) => text(x, y + i * fontSize * 1.25, s, attrs)).join('');
}

function rows(s, min = 1, max = 12) {
  if (!Array.isArray(s.data) || s.data.length < min || s.data.length > max) fail(`needs ${min}–${max} rows; split or use a table`);
  const names = new Set();
  for (const r of s.data) {
    if (!r || typeof r.label !== 'string' || !r.label.trim() || names.has(r.label)) fail('row labels must be unique nonempty strings');
    names.add(r.label);
  }
  return s.data;
}

function namedFocus(s, data) {
  if (typeof s.focus !== 'string' || !data.some(r => r.label === s.focus)) fail('Focus chart requires focus matching a row or series label');
  return s.focus;
}

function extent(values) {
  if (!values.length) fail('no observed numbers; retain missing values in a table');
  let lo = Math.min(0, ...values), hi = Math.max(0, ...values);
  if (lo === hi) hi = 1;
  const span = hi - lo;
  if (!finite(span) || span <= 0) fail('numeric range is too large; change the declared unit explicitly');
  const step = niceStep(span);
  lo = Math.floor(lo / step) * step;
  hi = Math.ceil(hi / step) * step;
  return [lo, hi];
}
function niceStep(span) {
  const target = span / 4, magnitude = 10 ** Math.floor(Math.log10(target));
  const multiplier = [1, 2, 2.5, 5, 10].find(n => n * magnitude >= target);
  const step = multiplier * magnitude;
  if (!finite(step) || step <= 0) fail('numeric range is not drawable; change the declared unit explicitly');
  return step;
}
function ticks(lo, hi) {
  const step = niceStep(hi - lo), result = [];
  for (let i = Math.ceil(lo / step); i * step <= hi + step * 1e-9; i++) result.push(Number((i * step).toPrecision(12)));
  return result;
}
const scale = (v, lo, hi, start, end) => start + (v - lo) / (hi - lo) * (end - start);
const tick = v => String(Number(v.toPrecision(3)));

function plot(m, left = 220, right = 140) {
  const top = m.plotTop || 115, bottom = m.plotBottom || m.h - 125;
  const width = m.w - left - right, height = bottom - top;
  if (width < 260 || height < 100) fail('canvas too small; enlarge it or use a table');
  return { x: left, y: top, w: width, h: height };
}

function xAxis(p, lo, hi, unit) {
  let out = '';
  for (const v of ticks(lo, hi)) {
    const x = scale(v, lo, hi, p.x, p.x + p.w);
    out += line(x, p.y, x, p.y + p.h) + text(x, p.y - 16, tick(v), { 'text-anchor': 'middle', fill: C.muted, 'font-size': 18 });
  }
  const zero = scale(0, lo, hi, p.x, p.x + p.w);
  if (lo <= 0 && hi >= 0) out += line(zero, p.y, zero, p.y + p.h, { stroke: C.gray, 'stroke-width': 1.5, 'data-baseline': 0 });
  if (unit) out += text(p.x + p.w, p.y + p.h + 28, unit, { 'text-anchor': 'end', fill: C.muted, 'font-size': 18 });
  return out;
}

function columns(s, n) {
  if (!Array.isArray(s.labels) || s.labels.length !== n || s.labels.some(v => typeof v !== 'string' || !v.trim()) || new Set(s.labels).size !== n) fail('labels must name every column/period uniquely');
  return s.labels;
}

module.exports = { C, esc, finite, fail, pos, el, text, line, rect, dot, countWidth, wrap, label, rows, namedFocus, extent, niceStep, scale, tick, ticks, plot, xAxis, columns };
