'use strict';

// Skill extensions beyond the source design system v2.5.1. They reuse its colour roles, type sizes and
// data-eligibility style: grouped (multi-series magnitude), combo (amount + rate), histogram (raw
// distribution) and sharetrend (composition over ordered periods).
const U = require('./chart-utils');
const { C, finite, fail, el, text, line, rect, dot, label, rows, extent, scale, num, tick, ticks, plot, xAxis, composition, catFill, catText, countWidth } = U;

const caption = { fill: C.muted, 'font-size': 18 };
// Derived shares show one decimal; raw values stay exact in data-* attributes and metadata.
const pct = value => U.derived(value, 1);
const unitLabel = (value, name) => {
  if (typeof value !== 'string' || !value.trim() || !/[（(].+[）)]/.test(value)) fail(`${name} must state its unit, for example "年增率（%）"`);
  return value;
};
function legend(p, names, identities, y = p.y - 34) {
  return names.map((name, index) => {
    const x = p.x + index * p.w / names.length;
    return rect(x, y - 12, 13, 13, catFill(identities[index]), { stroke: C.ink, 'stroke-width': .5 }) + label(x + 19, y, name, p.w / names.length - 24, caption, 1);
  }).join('');
}

function grouped(s, m) {
  if (!Array.isArray(s.series) || s.series.length < 2 || s.series.length > 4 || s.series.some(v => typeof v !== 'string' || !v.trim()) || new Set(s.series).size !== s.series.length) fail('grouped needs 2–4 unique series names');
  const k = s.series.length, data = rows(s, 1, 8);
  const identities = U.categoryIndices(s, s.series);
  if (data.some(r => !Array.isArray(r.values) || r.values.length !== k || r.values.some(v => v !== null && !finite(v)))) fail('grouped rows need one number or null per series');
  const observed = data.flatMap(r => r.values).filter(finite), [lo, hi] = extent(observed);
  // Keep negative value labels in their own gutter, separate from the row names.
  const negativeGap = Math.max(0, ...observed.filter(v => v < 0).map(v => countWidth(num(v)) * 18 + 12));
  const p = plot(m, 220 + negativeGap, 110), slot = p.h / data.length;
  const bar = Math.min(22, (slot - 16) / k);
  if (bar < 17) fail('grouped rows too dense for readable value labels; increase height, split, or use a table');
  const X = v => scale(v, lo, hi, p.x, p.x + p.w), zero = X(0);
  let out = xAxis(p, lo, hi, m.unit) + legend(p, s.series, identities, p.y - 50);
  data.forEach((r, i) => {
    const top = p.y + i * slot + (slot - bar * k) / 2;
    out += label(p.x - 16 - negativeGap, top + bar * k / 2 + 6, r.label, p.x - 40 - negativeGap, { 'text-anchor': 'end' });
    r.values.forEach((v, j) => {
      const y = top + j * bar;
      if (v === null) { out += text(zero + 6, y + bar / 2 + 6, '未提供', caption); return; }
      const x = X(v);
      out += rect(Math.min(x, zero), y + 1, Math.abs(x - zero), bar - 2, catFill(identities[j]), { stroke: C.muted, 'stroke-width': .6, 'data-series': s.series[j], 'data-value': String(v), 'data-label': r.label });
      out += text(v < 0 ? x - 6 : x + 6, y + bar / 2 + 6, num(v), { ...caption, fill: C.ink, 'text-anchor': v < 0 ? 'end' : 'start' });
    });
  });
  return out;
}

function combo(s, m) {
  const data = rows(s, 2, 12), rateLabel = unitLabel(s.rateLabel, 'rateLabel');
  if (data.some(r => (r.value !== null && !finite(r.value)) || (r.rate !== null && !finite(r.rate)))) fail('combo rows need numeric or null value and rate');
  const values = data.map(r => r.value).filter(finite), rates = data.map(r => r.rate).filter(finite);
  if (!rates.length) fail('combo needs at least one observed rate; use a column chart instead');
  const places = Math.max(...rates.map(rate => {
    const [mantissa, exponent = '0'] = String(rate).split('e');
    return Math.max(0, (mantissa.split('.')[1]?.length || 0) - Number(exponent));
  }));
  // Pad the shared precision without exposing binary toFixed noise or rounding tiny rates to zero.
  const rateFormat = places <= 100 ? new Intl.NumberFormat('en-US', { minimumFractionDigits: places, maximumFractionDigits: places }) : null;
  const [lo, hi] = extent(values), [rlo, rhi] = extent(rates), p = plot(m, 100, 110), slot = p.w / data.length;
  if (slot < 58) fail('combo periods too dense; split the chart or use a table');
  const padRates = rateFormat && rates.every(rate => countWidth(rateFormat.format(rate)) * 18 <= slot - 8);
  const Y = v => scale(v, lo, hi, p.y + p.h, p.y), R = v => scale(v, rlo, rhi, p.y + p.h, p.y), cx = i => p.x + (i + .5) * slot;
  let out = '';
  // Gridlines follow the column axis only; the independent rate axis gets tick marks so neither scale implies the other.
  for (const v of ticks(lo, hi)) out += line(p.x, Y(v), p.x + p.w, Y(v)) + text(p.x - 10, Y(v) + 5, tick(v), { ...caption, 'text-anchor': 'end' });
  for (const v of ticks(rlo, rhi)) out += line(p.x + p.w, R(v), p.x + p.w + 6, R(v), { stroke: C.blue }) + text(p.x + p.w + 10, R(v) + 5, tick(v), { ...caption, fill: C.blue });
  out += line(p.x, Y(0), p.x + p.w, Y(0), { stroke: C.gray, 'stroke-width': 1.5, 'data-baseline': 0 });
  out += rect(p.x, p.y - 36, 13, 13, C.gray) + label(p.x + 19, p.y - 24, `柱：${m.unit}（左軸）`, p.w / 2 - 24, caption, 1);
  out += line(p.x + p.w / 2, p.y - 30, p.x + p.w / 2 + 16, p.y - 30, { stroke: C.blue, 'stroke-width': 3 }) + label(p.x + p.w / 2 + 22, p.y - 24, `線：${rateLabel}（右軸）`, p.w / 2 - 24, { ...caption, fill: C.blue }, 1);
  let path = '', connected = false;
  data.forEach((r, i) => {
    const width = slot * .56, x = cx(i) - width / 2;
    out += label(cx(i), p.y + p.h + 26, r.label, slot - 6, { ...caption, 'text-anchor': 'middle' }, 1);
    if (r.value !== null) {
      out += rect(x, Math.min(Y(r.value), Y(0)), width, Math.abs(Y(r.value) - Y(0)), C.gray, { 'data-value': String(r.value), 'data-label': r.label });
      out += text(cx(i), r.value < 0 ? Y(0) + 20 : Y(0) - 8, num(r.value), { 'text-anchor': 'middle', fill: C.ink, 'font-size': 18 });
    }
    if (r.rate === null) { connected = false; return; }
    path += `${connected ? 'L' : 'M'}${U.pos(cx(i))},${U.pos(R(r.rate))} `;
    connected = true;
  });
  if (path) out += el('path', { d: path, fill: 'none', stroke: '#FFFFFF', 'stroke-width': 7 }) + el('path', { d: path, fill: 'none', stroke: C.blue, 'stroke-width': 3, 'data-rate-line': 'true' });
  data.forEach((r, i) => {
    if (r.rate === null) return;
    const value = padRates ? rateFormat.format(r.rate) : num(r.rate), width = countWidth(value) * 18 + 8;
    const y = R(r.rate) < p.y + 26 ? R(r.rate) + 32 : R(r.rate) - 14;
    out += dot(cx(i), R(r.rate), C.blue, { stroke: '#FFFFFF', 'stroke-width': 1.5, 'data-rate': String(r.rate) });
    out += rect(cx(i) - width / 2, y - 18, width, 24, '#FFFFFF') + label(cx(i), y, value, slot - 8, { 'text-anchor': 'middle', fill: C.blue, 'font-size': 18 }, 1);
  });
  return out + label(p.x, p.y + p.h + 60, '兩軸刻度各自獨立；柱高與線高不可互相比較', p.w, caption, 1);
}

function histogram(s, m) {
  const { counts, edges } = U.histogramData(s), values = s.data, w = s.binWidth;
  const n = counts.length, edge = i => edges[i], top = Math.max(...counts);
  const p = plot(m, 100, 60), slot = p.w / n, Y = v => scale(v, 0, top, p.y + p.h, p.y);
  if (slot < 22) fail('histogram bins too narrow; widen the canvas or use fewer bins');
  let out = '';
  for (const v of ticks(0, top).filter(Number.isInteger)) out += line(p.x, Y(v), p.x + p.w, Y(v)) + text(p.x - 10, Y(v) + 5, tick(v), { ...caption, 'text-anchor': 'end' });
  out += text(p.x, p.y - 16, s.countLabel || '筆數', caption);
  const every = Math.ceil(60 / slot);
  counts.forEach((count, i) => {
    const x = p.x + i * slot;
    out += rect(x + 1, Y(count), slot - 2, p.y + p.h - Y(count), C.blue, { 'data-bin-start': edge(i), 'data-bin-end': edge(i + 1), 'data-count': count });
    if (slot >= 30 && count) out += text(x + slot / 2, Y(count) - 6, num(count), { 'text-anchor': 'middle', fill: C.ink, 'font-size': 18 });
  });
  for (let i = 0; i <= n; i += every) out += text(p.x + i * slot, p.y + p.h + 24, num(edge(i)), { ...caption, 'text-anchor': 'middle' });
  out += line(p.x, p.y + p.h, p.x + p.w, p.y + p.h, { stroke: C.gray, 'stroke-width': 1.5, 'data-baseline': 0 });
  return out + label(p.x, p.y + p.h + 56, `n＝${num(values.length)}；組距 ${num(w)}，每組含下界、不含上界`, p.w, caption, 1);
}

function sharetrend(s, m) {
  const { categories, data, totals, shares } = composition(s, m, 12), p = plot(m, 100, 60), slot = p.w / data.length;
  const identities = U.categoryIndices(s, categories);
  if (slot < 70) fail('sharetrend periods too dense; split the chart or use a table');
  let out = legend(p, categories, identities), smallNotes = [];
  data.forEach((row, r) => {
    const total = totals[r], width = slot * .62, x = p.x + r * slot + (slot - width) / 2;
    let y = p.y;
    row.values.forEach((value, index) => {
      const share = shares[r][index], height = p.h * share / 100, direct = `${pct(share)}%`;
      out += rect(x, y, width, height, catFill(identities[index]), { stroke: '#FFFFFF', 'stroke-width': 1.5, 'data-value': String(value), 'data-share': String(share), 'data-category': categories[index], 'data-period': row.label });
      if (height >= 26 && width >= countWidth(direct) * 18 + 8) out += text(x + width / 2, y + height / 2 + 6, direct, { 'text-anchor': 'middle', fill: catText(identities[index]), 'font-size': 18 });
      else smallNotes.push(`${row.label}／${categories[index]} ${pct(share)}%`);
      y += height;
    });
    out += label(x + width / 2, p.y + p.h + 26, row.label, slot - 6, { 'text-anchor': 'middle', fill: C.ink, 'font-size': 18 }, 1);
    out += label(x + width / 2, p.y + p.h + 48, `總量 ${num(total)}`, slot - 6, { ...caption, 'text-anchor': 'middle' }, 1);
  });
  if (smallNotes.length > 6) fail('sharetrend has too many small segments for companion labels; split or use a table');
  return out + label(p.x, p.y + p.h + 76, `每柱＝100%；比較組成變化，非總規模${smallNotes.length ? `。小區塊：${smallNotes.join('；')}` : ''}`, p.w, caption, 2);
}

module.exports = { grouped, combo, histogram, sharetrend };
