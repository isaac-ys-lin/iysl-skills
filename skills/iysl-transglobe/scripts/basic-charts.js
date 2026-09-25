'use strict';
const { C, finite, fail, pos, el, text, line, rect, dot, label, rows, namedFocus, extent, scale, tick, ticks, plot, xAxis, columns } = require('./chart-utils');

function bars(s, m, ordered = false) {
  const input = rows(s);
  if (input.some(r => r.value !== null && !finite(r.value))) fail('values must be numbers or null');
  const observed = input.filter(r => r.value !== null);
  const [lo, hi] = extent(observed.map(r => r.value)), p = plot(m);
  if (!ordered) namedFocus(s, input);
  // Ranking sorts observed values; missing rows remain present at the end.
  const data = ordered ? input : [...input].sort((a, b) => a.value === null ? 1 : b.value === null ? -1 : b.value - a.value);
  const slot = p.h / data.length;
  if (slot < 40) fail('too many rows at this height; increase height or split the chart');
  const zero = scale(0, lo, hi, p.x, p.x + p.w), min = Math.min(...observed.map(r => r.value)), max = Math.max(...observed.map(r => r.value));
  let out = xAxis(p, lo, hi, m.unit);
  data.forEach((r, i) => {
    const y = p.y + (i + 0.5) * slot;
    out += label(p.x - 16, y - 4, r.label, p.x - 40, { 'text-anchor': 'end' });
    if (r.value === null) { out += text(p.x + p.w + 12, y + 5, '未提供', { fill: C.muted }); return; }
    const x = scale(r.value, lo, hi, p.x, p.x + p.w);
    const color = ordered ? C.seq[Math.round((r.value - min) / (max - min || 1) * 4)] : r.label === s.focus ? C.blue : C.gray;
    out += rect(Math.min(x, zero), y - 10, Math.abs(x - zero), 20, color, { stroke: C.gray, 'stroke-width': .8, 'data-value': String(r.value), 'data-label': r.label });
    if (r.value === 0) out += line(zero, y - 10, zero, y + 10, { stroke: color, 'stroke-width': 2 });
    out += text(p.x + p.w + 12, y + 5, String(r.value), { fill: C.ink });
  });
  return out;
}

function bullet(s, m) {
  const data = rows(s), p = plot(m, 220, 230);
  if (data.some(r => !finite(r.actual) || !finite(r.target))) fail('bullet needs numeric actual and target for every row');
  const [lo, hi] = extent(data.flatMap(r => [r.actual, r.target])), slot = p.h / data.length;
  if (slot < 46) fail('bullet rows too dense; enlarge or split');
  const X = v => scale(v, lo, hi, p.x, p.x + p.w), zero = X(0);
  let out = xAxis(p, lo, hi, m.unit);
  out += text(p.x + p.w + 32, p.y - 16, '實際 / 目標', { fill: C.muted, 'font-size': 18 });
  data.forEach((r, i) => {
    const y = p.y + (i + .5) * slot, x = X(r.actual);
    out += label(p.x - 16, y - 4, r.label, p.x - 40, { 'text-anchor': 'end' });
    out += rect(p.x, y - 10, p.w, 20, '#F6F6F6');
    out += rect(Math.min(zero, x), y - 10, Math.abs(x - zero), 20, C.blue, { 'data-actual': String(r.actual) });
    out += line(X(r.target), y - 18, X(r.target), y + 18, { stroke: C.ink, 'stroke-width': 3, 'data-target': String(r.target) });
    out += label(p.x + p.w + 32, y + 5, `${r.actual} / ${r.target}`, 190);
  });
  out += text(p.x, p.y + p.h + 28, '藍條＝實際；黑線＝目標', { fill: C.muted, 'font-size': 18 });
  return out;
}

function heatmap(s, m) {
  const data = rows(s, 1, 10);
  const n = data[0].values?.length;
  if (!Number.isInteger(n) || n < 1 || n > 12 || data.some(r => !Array.isArray(r.values) || r.values.length !== n || r.values.some(v => v !== null && !finite(v)))) fail('heatmap requires equal rows of numbers/null, at most 12 columns');
  const labels = columns(s, n), all = data.flatMap(r => r.values).filter(finite);
  if (!all.length) fail('heatmap has only missing values; use a table');
  const min = Math.min(...all), max = Math.max(...all), p = plot(m, 220, 50), cw = p.w / n, ch = p.h / data.length;
  if (cw < 58 || ch < 45) fail('heatmap cells too small; enlarge or split');
  let out = '';
  labels.forEach((v, i) => { out += label(p.x + (i + .5) * cw, p.y - 32, v, cw - 8, { 'text-anchor': 'middle', fill: C.muted }); });
  data.forEach((r, i) => {
    const y = p.y + i * ch;
    out += label(p.x - 16, y + ch / 2 - 4, r.label, p.x - 40, { 'text-anchor': 'end' });
    r.values.forEach((v, j) => {
      const x = p.x + j * cw, index = v === null ? 0 : Math.round((v - min) / (max - min || 1) * 4);
      out += rect(x, y, cw, ch, v === null ? '#FFFFFF' : C.seq[index], { stroke: C.gray, 'stroke-width': 1, 'data-value': v === null ? 'null' : String(v) });
      out += label(x + cw / 2, y + ch / 2 + 5, v === null ? '未提供' : String(v), cw - 8, { 'text-anchor': 'middle', fill: v !== null && index >= 3 ? '#FFFFFF' : C.ink }, 1);
    });
  });
  C.seq.forEach((color, i) => { out += rect(p.x + i * 28, p.y + p.h + 17, 28, 18, color, { stroke: C.gray, 'stroke-width': .5 }); });
  out += label(p.x + 158, p.y + p.h + 32, `淺 → 深：${min} → ${max} ${m.unit || ''}；空白格標示缺值`, p.w - 158, { fill: C.muted, 'font-size': 18 });
  return out;
}

function trend(s, m, tracking = false) {
  const data = rows(s, 1, tracking ? 4 : 6), n = data[0].values?.length;
  if (!Number.isInteger(n) || n < 2 || n > 20 || data.some(r => !Array.isArray(r.values) || r.values.length !== n || r.values.some(v => v !== null && !finite(v)))) fail('trend needs equal series of 2–20 numbers/null');
  const labels = columns(s, n), all = data.flatMap(r => r.values).filter(finite), [lo, hi] = extent(all);
  if (!tracking) namedFocus(s, data);
  const p = plot(m, 100, 260);
  // A fixed ordered-time grid is declared in the input guide. Irregular observations need explicit resampling with missing periods or another renderer.
  const step = p.w / (n - 1), X = i => p.x + i * step, Y = v => scale(v, lo, hi, p.y + p.h, p.y);
  if (p.h < data.length * 52) fail('series labels too dense; use small multiples or increase height');
  const endpoints = data.map((r, i) => {
    const j = r.values.findLastIndex(v => v !== null);
    return { i, j, y: j < 0 ? p.y + p.h : Y(r.values[j]) };
  }).sort((a, b) => a.y - b.y);
  endpoints.forEach((end, i) => { end.labelY = Math.max(p.y + 8, end.y, i ? endpoints[i - 1].labelY + 52 : p.y); });
  const overflow = Math.max(0, endpoints.at(-1).labelY + 24 - (p.y + p.h));
  for (const end of endpoints) end.labelY -= overflow;
  let out = '';
  for (const v of ticks(lo, hi)) {
    const y = Y(v);
    out += line(p.x, y, p.x + p.w, y) + text(p.x - 12, y + 5, tick(v), { 'text-anchor': 'end', fill: C.muted, 'font-size': 18 });
  }
  labels.forEach((v, i) => { out += label(X(i), p.y + p.h + 34, v, Math.min(step - 6, 90), { 'text-anchor': 'middle', fill: C.muted }); });
  if (m.unit) out += text(p.x, p.y - 14, m.unit, { fill: C.muted, 'font-size': 18 });
  data.forEach((r, i) => {
    const color = tracking ? C.cat[i] : r.label === s.focus ? C.blue : C.gray;
    const dash = ['', '10 5', '3 5', '12 4 3 4', '2 4', '10 4 2 4'][i];
    let path = '', connected = false;
    r.values.forEach((v, j) => {
      if (v === null) { connected = false; return; }
      path += `${connected ? 'L' : 'M'}${pos(X(j))},${pos(Y(v))} `; connected = true;
    });
    // Dark outline retains graphical contrast for the light purple categorical series.
    if (tracking && i === 3) out += el('path', { d: path, fill: 'none', stroke: C.muted, 'stroke-width': 6, 'stroke-dasharray': dash });
    out += el('path', { d: path, fill: 'none', stroke: color, 'stroke-width': 3, 'stroke-dasharray': dash, 'data-series': r.label });
    r.values.forEach((v, j) => {
      if (v === null) return;
      const attrs = { stroke: C.muted, 'stroke-width': .8, 'data-value': String(v), 'data-period': labels[j], 'data-series': r.label };
      if (!tracking || i === 0) out += dot(X(j), Y(v), color, attrs);
      else if (i === 1) out += rect(X(j) - 5, Y(v) - 5, 10, 10, color, attrs);
      else out += el('polygon', { points: i === 2 ? `${X(j)},${Y(v)-7} ${X(j)-6},${Y(v)+5} ${X(j)+6},${Y(v)+5}` : `${X(j)},${Y(v)-7} ${X(j)-6},${Y(v)} ${X(j)},${Y(v)+7} ${X(j)+6},${Y(v)}`, fill: color, ...attrs });
    });
    const end = endpoints.find(end => end.i === i), x = p.x + p.w + 24;
    if (end.j >= 0) out += line(X(end.j) + 7, end.y, x - 8, end.labelY - 5, { stroke: color, 'stroke-width': 1 });
    out += label(x, end.labelY, r.label, 225, { 'font-weight': r.label === s.focus ? 700 : 400 }, 1);
    out += label(x, end.labelY + 24, end.j < 0 ? '未提供' : `${r.values[end.j]}（${labels[end.j]}${end.j < n - 1 ? '，最後已知' : ''}）`, 225, { fill: C.muted, 'font-size': 18 }, 1);
  });
  return out;
}

module.exports = {
  ranking: (s, m) => bars(s, m), ordered: (s, m) => bars(s, m, true),
  bullet, heatmap, trend: (s, m) => trend(s, m), tracking: (s, m) => trend(s, m, true),
};
