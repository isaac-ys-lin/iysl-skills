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
// Width in em. CJK and other non-ASCII glyphs are full width; Latin classes follow Arial rounded up a few
// percent, because Office may substitute a font with different metrics (Windows vs Mac).
const latinWidth = c => /[MW@]/.test(c) ? .94 : /[A-Z%&]/.test(c) ? .72 : /[mw]/.test(c) ? .83 : /[il.,:;!|'`\s]/.test(c) ? .28 : /[fjrt()[\]\/-]/.test(c) ? .39 : .58;
const countWidth = s => [...String(s)].reduce((n, c) => n + (/[^\x00-\x7F]/.test(c) ? 1 : latinWidth(c)), 0);

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
  const first = Math.ceil(lo / step), places = Math.max(0, 1 - Math.floor(Math.log10(step)));
  if (!finite(first)) fail('numeric range is not drawable; change the declared unit explicitly');
  // Bound the loop even when a large offset cannot be incremented by one in IEEE-754.
  for (let i = 0; i <= Math.ceil((hi - lo) / step) + 1; i++) {
    const raw = (first + i) * step;
    const value = places <= 100 ? Number(raw.toFixed(places)) : Number(raw.toPrecision(12));
    if (value >= lo - step * 1e-9 && value <= hi + step * 1e-9 && !result.includes(value)) result.push(value);
  }
  return result;
}
const scale = (v, lo, hi, start, end) => start + (v - lo) / (hi - lo) * (end - start);
// Visible numbers get thousands separators; data-* attributes and metadata keep raw values.
const num = v => typeof v === 'number' || /^-?\d+(\.\d+)?$/.test(v) ? String(v).replace(/^-?\d+/, s => s.replace(/\B(?=(\d{3})+$)/g, ',')) : String(v);
const tick = v => num(v);

function domain(value, name) {
  if (!Array.isArray(value) || value.length !== 2 || !value.every(finite) || value[0] >= value[1] || !finite(value[1] - value[0])) fail(`${name} must be [min, max] with min < max and a finite span`);
  ticks(...value);
  return value;
}

function observedDomain(values, explicit, name = 'yDomain') {
  if (!values.length) fail('no observed numbers; retain missing values in a table');
  const bounds = explicit === undefined ? extent(values) : domain(explicit, name);
  if (values.some(value => value < bounds[0] || value > bounds[1])) fail(`${name} must cover every observed value`);
  return bounds;
}

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

// Categorical fill (fifth slot is the existing Other) and the label colour that keeps 4.5:1 on it.
const catFill = index => index === 4 ? '#DDDDDD' : C.cat[index];
const catText = index => index >= 2 ? C.ink : '#FFFFFF';
// Add the input numbers' decimal representations before returning a JS number.
// This avoids displaying 0.0001 + 0.0003 as 0.00039999999999999996 without dropping source digits.
function sum(values) {
  if (!values.length) return 0;
  if (!values.every(finite)) fail('sum requires finite numbers');
  const parts = values.map(value => {
    const [mantissa, exponent = '0'] = String(value).split('e');
    const places = (mantissa.split('.')[1]?.length || 0) - Number(exponent);
    return { integer: BigInt(mantissa.replace('.', '')), places };
  });
  const places = Math.max(...parts.map(part => part.places));
  const integer = parts.reduce((total, part) => total + part.integer * 10n ** BigInt(places - part.places), 0n);
  return Number(`${integer}e${-places}`);
}
const percent = (value, total) => {
  const result = value / total * 100;
  if (!finite(result)) fail('percentage calculation overflowed; change the declared unit');
  return result;
};
const derived = (value, places = 3) => {
  if (!finite(value)) fail('derived value is not finite');
  const rounded = Number(value.toFixed(places));
  return num(value !== 0 && rounded === 0 ? Number(value.toPrecision(2)) : rounded);
};
const difference = (before, after) => {
  const value = sum([after, -before]);
  if (!finite(value)) fail('difference is not finite; change the declared unit');
  return value;
};
const indexedData = data => data.map(row => ({
  label: row.label,
  values: row.values.map(value => value === null ? null : percent(value, row.values[0])),
  originals: [...row.values],
}));

function categoryIndices(s, names) {
  const values = s.categoryDomain === undefined ? names : s.categoryDomain;
  const name = s.categoryDomain === undefined ? 'categories' : 'categoryDomain';
  if (!Array.isArray(values) || values.length < 1 || values.length > 5 || values.some(value => typeof value !== 'string' || !value.trim()) || new Set(values).size !== values.length) fail(`${name} must contain unique nonempty names, at most four plus Other`);
  if (values.length === 5 && !/^(other|其他)$/i.test(values[4].trim())) fail(`the fifth entry in ${name} must be the existing Other category`);
  // Other is identified by name, not position: it always takes the neutral fifth slot (#DDDDDD).
  return names.map(name => {
    const index = values.indexOf(name);
    if (index < 0) fail(`categoryDomain does not include "${name}"`);
    return /^(other|其他)$/i.test(name.trim()) ? 4 : index;
  });
}

function categorySet(s) {
  if (!Array.isArray(s.categories) || s.categories.length < 2 || s.categories.length > 5 ||
      s.categories.some(value => typeof value !== 'string' || !value.trim()) ||
      new Set(s.categories).size !== s.categories.length) fail('categories must be 2–4 unique names; a fifth is allowed only for existing Other');
  categoryIndices(s, s.categories);
  return s.categories;
}

function composition(s, m, maxRows) {
  const categories = categorySet(s), data = rows(s, 2, maxRows), n = categories.length;
  if (data.some(row => !Array.isArray(row.values) || row.values.length !== n ||
      row.values.some(value => !finite(value) || value < 0))) {
    fail('composition rows need one nonnegative finite value per category and a positive row total');
  }
  const totals = data.map(row => sum(row.values));
  if (totals.some(total => !finite(total) || total <= 0)) fail('composition rows need a positive finite row total');
  const shares = data.map((row, i) => row.values.map(value => percent(value, totals[i])));
  return { categories, data, n, totals, shares };
}

const funnelRates = data => ({
  stages: data.map((row, i) => i && data[i - 1].value ? percent(row.value, data[i - 1].value) : null),
  completion: percent(data.at(-1).value, data[0].value),
});

function paretoData(s) {
  const input = rows(s, 3, 10);
  if (input.some(row => !Number.isSafeInteger(row.value) || row.value < 0)) fail('pareto needs nonnegative integer counts');
  const total = sum(input.map(row => row.value));
  if (!Number.isSafeInteger(total) || total <= 0) fail('pareto needs a positive safe-integer total count');
  const data = [...input].sort((a, b) => b.value - a.value);
  let count = 0;
  return { data, total, cumulative: data.map(row => percent(count += row.value, total)) };
}

function columns(s, n) {
  if (!Array.isArray(s.labels) || s.labels.length !== n || s.labels.some(v => typeof v !== 'string' || !v.trim()) || new Set(s.labels).size !== n) fail('labels must name every column/period uniquely');
  return s.labels;
}

function waterfallData(s) {
  const data = rows(s, 1, 10);
  if (!finite(s.start)) fail('waterfall requires numeric start');
  let total = s.start;
  const parts = [{ label: s.startLabel || '期初', from: 0, to: total, total: true }];
  for (const row of data) {
    if (!finite(row.value)) fail('waterfall changes must be finite');
    const from = total; total = sum([s.start, ...parts.slice(1).map(part => part.value), row.value]);
    if (!finite(total)) fail('waterfall running balance is not finite');
    parts.push({ ...row, from, to: total });
  }
  parts.push({ label: s.endLabel || '期末', from: 0, to: total, total: true });
  if (new Set(parts.map(row => row.label)).size !== parts.length) fail('waterfall start/change/end labels must be unique');
  const tolerance = Number.EPSILON * 16 * Math.max(1, Math.abs(total), Math.abs(s.start), ...data.map(row => Math.abs(row.value)));
  if (s.end !== undefined && (!finite(s.end) || Math.abs(s.end - total) > tolerance)) fail('waterfall end does not equal start plus changes');
  return parts;
}

function histogramData(s) {
  const values = s.data;
  if (!Array.isArray(values) || values.length < 10 || values.length > 100000 || values.some(v => !finite(v))) fail('histogram needs 10–100000 raw numeric observations in data; summaries belong in box or a table');
  if (!finite(s.binWidth) || s.binWidth <= 0) fail('histogram requires a positive binWidth from the source or analysis plan');
  const min = Math.min(...values), max = Math.max(...values), width = s.binWidth;
  const start = s.binStart ?? Math.floor(min / width) * width;
  if (!finite(start) || start > min) fail('binStart must be at or below the smallest observation');
  // Half-open bins [a, a + width); tolerate decimal division noise at an edge.
  const index = v => Math.floor((v - start) / width + 1e-9), n = index(max) + 1;
  if (n < 3 || n > 30) fail('histogram needs 3–30 bins; choose a different binWidth');
  const counts = Array(n).fill(0);
  values.forEach(v => { counts[index(v)] += 1; });
  const edges = Array.from({ length: n + 1 }, (_, i) => Number((start + i * width).toPrecision(12)));
  if (edges.some((edge, i) => !finite(edge) || (i && edge <= edges[i - 1]))) fail('histogram bin edges are not distinguishable; change the declared unit or binWidth');
  return { counts, edges };
}

module.exports = { catFill, catText, categoryIndices, sum, percent, derived, difference, indexedData, waterfallData, histogramData, funnelRates, paretoData, categorySet, composition, C, esc, finite, fail, pos, el, text, line, rect, dot, countWidth, wrap, label, rows, namedFocus, extent, domain, observedDomain, niceStep, scale, num, tick, ticks, plot, xAxis, columns };
