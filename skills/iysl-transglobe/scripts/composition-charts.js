'use strict';

// Composition and relative-change encodings.  The caller supplies the SVG frame and metadata.
const U = require('./chart-utils');
const { C, finite, fail, pos, el, text, line, rect, dot, label, rows, scale, tick, plot, columns, sum, composition } = U;
const fmt = value => U.num(Number(value.toFixed(3)));
const pct = value => U.num(Number(value.toFixed(1))); // derived shares; raw values stay exact
const cat = U.catFill, labelFill = U.catText;

function waffle(s, m) {
  const data = rows(s, 2, 5), values = data.map(row => row.value);
  if (values.some(value => !Number.isInteger(value) || value < 0) || sum(values) !== 100) fail('waffle values must be nonnegative whole percentages totaling 100');
  if (data.length === 5 && !/^(other|其他)$/i.test(data[4].label.trim())) fail('a fifth waffle category must be the existing Other category');
  const p = plot(m, 90, 260), size = Math.min(Math.floor(p.h / 10), Math.floor(p.w / 10));
  if (size < 18) fail('waffle grid is too small; enlarge the canvas or use a table');
  const gridWidth = size * 10, x = p.x + (p.w - gridWidth) / 2, y = p.y + (p.h - size * 10) / 2;
  let out = '', unit = 0;
  data.forEach((row, index) => {
    for (let i = 0; i < row.value; i += 1, unit += 1) {
      out += rect(x + (unit % 10) * size, y + Math.floor(unit / 10) * size, size - 1, size - 1, cat(index), {
        stroke: C.ink, 'stroke-opacity': .14, 'stroke-width': .6, 'data-unit': 1, 'data-category': row.label,
      });
    }
    const ly = p.y + 44 + index * Math.min(76, (p.h - 44) / data.length);
    out += rect(p.x + p.w + 34, ly - 13, 14, 14, cat(index), { stroke: C.ink, 'stroke-width': .5 });
    out += label(p.x + p.w + 56, ly, `${row.label} ${row.value}%`, 155, { fill: C.ink }, 1);
  });
  return out;
}

function stacked(s, m) {
  const { categories, data } = composition(s, m, 6), p = plot(m, 210, 60), rowHeight = p.h / data.length;
  if (rowHeight < 42) fail('stacked rows are too dense; enlarge, split, or use a table');
  let out = '', smallNotes = [];
  out += text(p.x + p.w, p.y - 60, `單位：${m.unit || '原始值'}`, { 'text-anchor': 'end', fill: C.muted, 'font-size': 18 });
  categories.forEach((name, index) => {
    const x = p.x + index * p.w / categories.length, y = p.y - 34;
    out += rect(x, y - 12, 13, 13, cat(index, categories), { stroke: C.ink, 'stroke-width': .5 });
    out += label(x + 19, y, name, p.w / categories.length - 24, { fill: C.muted, 'font-size': 18 }, 1);
  });
  data.forEach((row, r) => {
    const total = sum(row.values), height = Math.min(76, rowHeight - 18), y = p.y + r * rowHeight + (rowHeight - height) / 2;
    let x = p.x;
    out += label(p.x - 16, y + height / 2 - 7, row.label, p.x - 38, { 'text-anchor': 'end' });
    out += text(p.x - 16, y + height / 2 + 19, `總量 ${fmt(total)}`, { 'text-anchor': 'end', fill: C.muted, 'font-size': 18 });
    row.values.forEach((value, index) => {
      const width = p.w * value / total, share = value / total * 100;
      out += rect(x, y, width, height, cat(index, categories), {
        stroke: '#FFFFFF', 'stroke-width': 1.5, 'data-value': String(value), 'data-share': String(pos(share)), 'data-category': categories[index],
      });
      const direct = `${pct(share)}% · ${fmt(value)}`;
      if (width >= Math.max(62, U.countWidth(direct) * 18 + 12) && height >= 30) {
        out += text(x + width / 2, y + height / 2 + 5, direct, { 'text-anchor': 'middle', fill: labelFill(index), 'font-size': 18 });
      } else {
        if (width >= 62) out += text(x + width / 2, y + height / 2 + 5, `${pct(share)}%`, { 'text-anchor': 'middle', fill: labelFill(index), 'font-size': 18 });
        smallNotes.push(`${row.label}／${categories[index]} ${fmt(value)}/${fmt(total)}（${pct(share)}%）`);
      }
      x += width;
    });
  });
  out += text(p.x, p.y + p.h + 28, '每列＝100%；比較組成，非總規模', { fill: C.muted, 'font-size': 18 });
  if (smallNotes.length) {
    if (smallNotes.length > 4) fail('stacked has too many narrow segments for companion labels; split or use a table');
    out += label(p.x, p.y + p.h + 57, `窄區塊：${smallNotes.join('；')}`, p.w, { fill: C.muted, 'font-size': 18 }, 2);
  }
  return out;
}

function mekko(s, m) {
  const { categories, data } = composition(s, m, 5), p = plot(m, 100, 45);
  const totals = data.map(row => sum(row.values)), grand = sum(totals), minWidth = 75;
  if (!finite(grand) || grand <= 0) fail('mekko grand total must be finite and positive');
  if (p.w * Math.min(...totals) / grand < minWidth) fail('mekko has a group too narrow to label; split it or use a table');
  let out = '', x = p.x, smallNotes = [];
  out += text(p.x + p.w, p.y - 60, `單位：${m.unit || '原始值'}`, { 'text-anchor': 'end', fill: C.muted, 'font-size': 18 });
  data.forEach((row, r) => {
    const total = totals[r], width = p.w * total / grand;
    let y = p.y;
    row.values.forEach((value, index) => {
      const height = p.h * value / total;
      out += rect(x, y, width, height, cat(index, categories), {
        stroke: '#FFFFFF', 'stroke-width': 1.5, 'data-value': String(value), 'data-share': String(pos(value / grand)), 'data-category': categories[index], 'data-row': row.label,
      });
      if (value === 0 || width < 92 || height < 35) smallNotes.push(`${row.label}／${categories[index]} ${fmt(value)}/${fmt(total)}（${pct(value / total * 100)}%）`);
      else if (width >= 92 && height >= 35) out += label(x + width / 2, y + height / 2 + 5, `${pct(value / total * 100)}% · ${fmt(value)}`, width - 8, {
        'text-anchor': 'middle', fill: labelFill(index), 'font-size': 18,
      }, 1);
      y += height;
    });
    out += label(x + width / 2, p.y + p.h + 27, `${row.label} ${fmt(total)}`, width - 5, { 'text-anchor': 'middle', fill: C.ink, 'font-size': 18 }, 1);
    out += text(x + width / 2, p.y + p.h + 51, `市場占比 ${pct(total / grand * 100)}%`, { 'text-anchor': 'middle', fill: C.muted, 'font-size': 18 });
    x += width;
  });
  categories.forEach((name, index) => {
    const x0 = p.x + index * p.w / categories.length;
    out += rect(x0, p.y - 34, 13, 13, cat(index, categories), { stroke: C.ink, 'stroke-width': .5 });
    out += label(x0 + 19, p.y - 22, name, p.w / categories.length - 24, { fill: C.muted, 'font-size': 18 }, 1);
  });
  if (smallNotes.length) {
    if (smallNotes.length > 4) fail('mekko has too many small cells for companion labels; split or use a table');
    out += label(p.x, p.y + p.h + 79, `小區塊：${smallNotes.join('；')}`, p.w, { fill: C.muted, 'font-size': 18 }, 2);
  }
  return out;
}

function pareto(s, m) {
  const input = rows(s, 3, 10);
  if (input.some(row => !Number.isSafeInteger(row.value) || row.value < 0)) fail('pareto needs nonnegative integer counts');
  const total = sum(input.map(row => row.value));
  if (!Number.isSafeInteger(total) || total <= 0) fail('pareto needs a positive safe-integer total count');
  const data = [...input].sort((a, b) => b.value - a.value), p = plot(m, 100, 105), slot = p.w / data.length;
  if (slot < 68) fail('pareto labels are too dense; split or use a table');
  // Counts share the cumulative scale (total = 100%), so a bar top never reads as a cumulative share.
  const Y = value => p.y + p.h - value / total * p.h;
  let out = '', cumulative = 0, points = [];
  for (const count of U.ticks(0, total)) out += line(p.x, Y(count), p.x + p.w, Y(count)) + text(p.x - 10, Y(count) + 5, tick(count), { 'text-anchor': 'end', fill: C.muted, 'font-size': 18 });
  for (const pct of [0, 25, 50, 75, 100]) {
    const y = p.y + p.h - pct / 100 * p.h;
    out += line(p.x + p.w, y, p.x + p.w + 6, y, { stroke: C.gray }) + text(p.x + p.w + 12, y + 5, `${pct}%`, { fill: C.muted, 'font-size': 18 });
  }
  data.forEach((row, index) => {
    const width = slot * .62, x = p.x + index * slot + (slot - width) / 2, y = Y(row.value), center = x + width / 2;
    cumulative += row.value;
    const pct = cumulative / total * 100, cy = p.y + p.h - pct / 100 * p.h;
    out += rect(x, y, width, p.y + p.h - y, C.gray, { 'data-count': String(row.value), 'data-label': row.label });
    out += text(center, p.y + p.h - 8, U.num(row.value), { 'text-anchor': 'middle', fill: C.ink, 'font-size': 18 });
    out += label(center, p.y + p.h + 24, row.label, slot - 5, { 'text-anchor': 'middle', fill: C.muted, 'font-size': 18 }, 2);
    points.push([center, cy, pct]);
  });
  const path = points.map(point => `${pos(point[0])},${pos(point[1])}`).join(' ');
  out += el('polyline', { points: path, fill: 'none', stroke: '#FFFFFF', 'stroke-width': 6 });
  out += el('polyline', { points: path, fill: 'none', stroke: C.blue, 'stroke-width': 3, 'data-cumulative-line': 'true' });
  points.forEach(([x, y, pct]) => {
    const labelY = y < p.y + 24 ? y + 32 : y - 14, value = `${fmt(pct)}%`, width = U.countWidth(value) * 18 + 8;
    out += dot(x, y, C.blue, { stroke: '#FFFFFF', 'stroke-width': 1.5, 'data-cumulative': String(pos(pct)) });
    out += rect(x - width / 2, labelY - 20, width, 26, '#FFFFFF');
    out += text(x, labelY, value, { 'text-anchor': 'middle', fill: C.blue, 'font-size': 18 });
  });
  out += text(p.x, p.y - 24, m.unit || '件數', { fill: C.muted, 'font-size': 18 });
  out += text(p.x + p.w + 12, p.y - 24, '累計占比', { fill: C.muted, 'font-size': 18 });
  return out;
}

function indexed(s, m) {
  const data = rows(s, 2, 5), n = data[0]?.values?.length;
  if (!Number.isInteger(n) || n < 3 || n > 12 || data.some(row => !Array.isArray(row.values) || row.values.length !== n ||
      !finite(row.values[0]) || row.values[0] <= 0 || row.values.some(value => value !== null && !finite(value)))) {
    fail('indexed needs 2–5 equal series with 3–12 finite numbers/null and a positive base');
  }
  const periods = columns(s, n), indexData = data.map(row => ({
    label: row.label, values: row.values.map(value => value === null ? null : value / row.values[0] * 100), originals: [...row.values],
  }));
  if (indexData.some(row => row.values.some(value => value !== null && !finite(value)))) fail('indexed calculation overflowed; change the declared unit');
  const focus = s.focus === undefined ? null : (typeof s.focus === 'string' && data.some(row => row.label === s.focus) ? s.focus : fail('indexed focus must match a series label'));
  const observed = indexData.flatMap(row => row.values).filter(finite);
  const rawLo = Math.min(100, ...observed), rawHi = Math.max(100, ...observed);
  const span = Math.max(rawHi - rawLo, 4), paddedLo = rawLo - Math.max(span * .08, 2), paddedHi = rawHi + Math.max(span * .08, 2);
  const step = U.niceStep(paddedHi - paddedLo);
  const lo = Math.floor(paddedLo / step) * step, hi = Math.ceil(paddedHi / step) * step;
  const ticks = Array.from({ length: Math.round((hi - lo) / step) + 1 }, (_, index) => lo + index * step);
  const p = plot(m, 68, 34), panelWidth = p.w / data.length;
  if (panelWidth < 165) fail('indexed panels are too narrow; split the chart or use a table');
  const Y = value => scale(value, lo, hi, p.y + p.h, p.y);
  let out = '';
  indexData.forEach((row, panel) => {
    const mark = focus && row.label !== focus ? C.gray : C.blue;
    const valueFill = focus && row.label !== focus ? C.muted : C.blue;
    const left = p.x + panel * panelWidth + 40, right = p.x + (panel + 1) * panelWidth - 28, width = right - left;
    if (width / (n - 1) < 32) fail('indexed period labels are too dense; split the chart or use a table');
    ticks.forEach(value => {
      const y = Y(value);
      out += line(left, y, right, y);
      if (panel === 0) out += text(left - 8, y + 5, tick(value), { 'text-anchor': 'end', fill: C.muted, 'font-size': 18 });
    });
    out += line(left, Y(100), right, Y(100), { stroke: C.gray, 'stroke-width': 1.5, 'stroke-dasharray': '5 4', 'data-baseline': 100 });
    out += label((left + right) / 2, p.y - 20, row.label, width, { 'text-anchor': 'middle', fill: C.ink, 'font-size': 18 }, 1);
    periods.forEach((period, index) => {
      const x = left + index * width / (n - 1);
      out += label(x, p.y + p.h + 25, period, Math.min(width / (n - 1) - 5, 90), { 'text-anchor': 'middle', fill: C.muted, 'font-size': 18 }, 1);
    });
    let path = '', connected = false;
    row.values.forEach((value, index) => {
      if (value === null) { connected = false; return; }
      const x = left + index * width / (n - 1), y = Y(value);
      path += `${connected ? 'L' : 'M'}${pos(x)},${pos(y)} `;
      connected = true;
      out += dot(x, y, mark, { 'data-index': String(pos(value)), 'data-original': String(row.originals[index]), 'data-period': periods[index], 'data-series': row.label });
      const endpoint = index === 0 ? { x: x + 6, anchor: 'start' } : index === n - 1 ? { x: x - 6, anchor: 'end' } : { x, anchor: 'middle' };
      out += text(endpoint.x, y - 10, fmt(value), { 'text-anchor': endpoint.anchor, fill: valueFill, 'font-size': 18 });
    });
    out += el('path', { d: path, fill: 'none', stroke: mark, 'stroke-width': 3, 'data-series': row.label, 'data-original-values': row.originals.map(value => value === null ? 'null' : value).join(',') });
  });
  out += text(p.x, p.y + p.h + 60, `各面板共用規律指數尺度 ${fmt(lo)}–${fmt(hi)}；首期＝100${m.unit ? `；原始單位：${m.unit}` : ''}`, { fill: C.muted, 'font-size': 18 });
  return out;
}

module.exports = { waffle, stacked, mekko, pareto, indexed };
