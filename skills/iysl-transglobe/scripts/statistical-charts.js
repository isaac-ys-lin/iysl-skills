'use strict';

const { C, finite, fail, warn, text, line, rect, dot, countWidth, rows, namedFocus, domain, observedDomain, scale, num, tick, ticks, plot, label } = require('./chart-utils');

const caption = { fill: C.muted, 'font-size': 18 };
const axisLabel = (value, name) => {
  if (typeof value !== 'string' || !value.trim()) fail(`${name} must name the axis and its unit, for example "處理時間（天）"`);
  return value;
};
const overlaps = (a, b, gap = 6) => a.left < b.right + gap && a.right + gap > b.left && a.top < b.bottom + gap && a.bottom + gap > b.top;

function axes(p, xDomain, yDomain, xLabel, yLabel, xLabelAbove = false) {
  let out = '';
  for (const v of ticks(...xDomain)) {
    const x = scale(v, ...xDomain, p.x, p.x + p.w);
    out += line(x, p.y, x, p.y + p.h) + text(x, p.y + p.h + 20, tick(v), { ...caption, 'text-anchor': 'middle' });
  }
  for (const v of ticks(...yDomain)) {
    const y = scale(v, ...yDomain, p.y + p.h, p.y);
    out += line(p.x, y, p.x + p.w, y) + text(p.x - 10, y + 5, tick(v), { ...caption, 'text-anchor': 'end' });
  }
  if (xDomain[0] <= 0 && xDomain[1] >= 0) out += line(scale(0, ...xDomain, p.x, p.x + p.w), p.y, scale(0, ...xDomain, p.x, p.x + p.w), p.y + p.h, { stroke: C.gray, 'stroke-width': 1.5, 'data-baseline': 0 });
  if (yDomain[0] <= 0 && yDomain[1] >= 0) out += line(p.x, scale(0, ...yDomain, p.y + p.h, p.y), p.x + p.w, scale(0, ...yDomain, p.y + p.h, p.y), { stroke: C.gray, 'stroke-width': 1.5, 'data-baseline': 0 });
  return out + label(p.x + p.w, xLabelAbove ? p.y - 16 : p.y + p.h + 50, xLabelAbove ? `橫軸：${xLabel}` : xLabel, p.w / 2 - 12, { ...caption, 'text-anchor': 'end' }, 1) + label(p.x, p.y - 16, yLabel, p.w / 2 - 12, caption, 1);
}

function valueGrid(p, yDomain, yLabel) {
  let out = '';
  for (const value of ticks(...yDomain)) {
    const y = scale(value, ...yDomain, p.y + p.h, p.y);
    out += line(p.x, y, p.x + p.w, y) + text(p.x - 10, y + 5, tick(value), { ...caption, 'text-anchor': 'end' });
  }
  if (yDomain[0] <= 0 && yDomain[1] >= 0) out += line(p.x, scale(0, ...yDomain, p.y + p.h, p.y), p.x + p.w, scale(0, ...yDomain, p.y + p.h, p.y), { stroke: C.gray, 'stroke-width': 1.5, 'data-baseline': 0 });
  return out + text(p.x, p.y - 16, yLabel, caption);
}

function scatter(s, m) {
  const data = rows(s, 2, 6), xLabel = axisLabel(s.xLabel, 'xLabel'), yLabel = axisLabel(s.yLabel, 'yLabel');
  data.forEach((r, i) => { if (!finite(r.x) || !finite(r.y)) fail(`row ${i + 1} needs finite x and y`); });
  const focus = s.focus === undefined ? null : namedFocus(s, data), p = plot(m, 105, 55);
  const explicitX = s.xDomain !== undefined, explicitY = s.yDomain !== undefined;
  const xDomain = observedDomain(data.map(r => r.x), s.xDomain, 'xDomain');
  const yDomain = observedDomain(data.map(r => r.y), s.yDomain, 'yDomain');
  const marks = data.map(r => ({ ...r, cx: scale(r.x, ...xDomain, p.x, p.x + p.w), cy: scale(r.y, ...yDomain, p.y + p.h, p.y) }));
  if (marks.some((a, i) => marks.slice(0, i).some(b => Math.hypot(a.cx - b.cx, a.cy - b.cy) < 34))) warn('points or their labels overlap; enlarge, split, or use a table');
  let out = axes(p, xDomain, yDomain, xLabel, yLabel, true);
  const labels = [], direct = marks.every((r, i) => {
    const value = `${r.label}（${num(r.x)}，${num(r.y)}）`, w = countWidth(value) * 20;
    const candidates = [[r.cx + 14, r.cy - 14, 'start'], [r.cx + 14, r.cy + 28, 'start'], [r.cx - 14, r.cy - 14, 'end'], [r.cx - 14, r.cy + 28, 'end']]
      .map(([x, y, anchor]) => ({ x, y, anchor, w, left: anchor === 'end' ? x - w : x, right: anchor === 'end' ? x : x + w, top: y - 22, bottom: y + 6 }));
    const placedLabel = candidates.find(candidate => candidate.left >= p.x && candidate.right <= p.x + p.w && candidate.top >= p.y && candidate.bottom <= p.y + p.h &&
      !labels.some(other => candidate.left < other.right + 8 && candidate.right + 8 > other.left && candidate.top < other.bottom + 8 && candidate.bottom + 8 > other.top) &&
      !marks.some((other, j) => j !== i && other.cx >= candidate.left - 8 && other.cx <= candidate.right + 8 && other.cy >= candidate.top - 8 && other.cy <= candidate.bottom + 8));
    if (!placedLabel) return false;
    labels.push(placedLabel);
    return true;
  });
  marks.forEach((r, i) => {
    const color = r.label === focus ? C.blue : C.gray;
    const labelColor = r.label === focus ? C.blue : C.muted;
    out += dot(r.cx, r.cy, color, { r: r.label === focus ? 8 : 6, 'data-label': r.label, 'data-x': r.x, 'data-y': r.y });
    if (direct) {
      const value = `${r.label}（${num(r.x)}，${num(r.y)}）`, placedLabel = labels[i];
      out += text(placedLabel.x, placedLabel.y, value, { fill: labelColor, 'font-size': 20, 'font-weight': 700, 'text-anchor': placedLabel.anchor });
    } else out += text(r.cx + 10, r.cy - 8, String(i + 1), { fill: C.ink, 'font-size': 20, 'font-weight': 700 });
  });
  const legendRows = direct ? 0 : Math.ceil(marks.length / 2);
  if (!direct) marks.forEach((r, i) => { out += label(p.x + (i % 2) * p.w / 2, p.y + p.h + 48 + Math.floor(i / 2) * 24, `${i + 1}. ${r.label}（${num(r.x)}，${num(r.y)}）`, p.w / 2 - 12, { ...caption, fill: r.label === focus ? C.blue : C.muted }, 1); });
  if (explicitX || explicitY) out += text(p.x, p.y + p.h + 50 + legendRows * 24, `顯示範圍：${xLabel} ${tick(xDomain[0])}–${tick(xDomain[1])}；${yLabel} ${tick(yDomain[0])}–${tick(yDomain[1])}`, caption);
  return out;
}

function box(s, m) {
  const data = rows(s, 1, 10);
  data.forEach((r, i) => {
    for (const key of ['low', 'q1', 'median', 'q3', 'high']) if (!finite(r[key])) fail(`row ${i + 1}.${key} must be finite`);
    if (r.outliers !== undefined && (!Array.isArray(r.outliers) || r.outliers.some(v => !finite(v)))) fail(`row ${i + 1}.outliers must be an array of numbers`);
    if (!(r.low <= r.q1 && r.q1 <= r.median && r.median <= r.q3 && r.q3 <= r.high)) fail(`row ${i + 1} summary must be ordered low ≤ q1 ≤ median ≤ q3 ≤ high`);
  });
  const outliers = r => r.outliers || [];
  const focus = s.focus === undefined ? null : namedFocus(s, data), p = plot(m, 105, 55);
  if (p.w / data.length < 150) warn('box groups are narrow for quartile labels; enlarge, split, or use a table');
  const yDomain = observedDomain(data.flatMap(r => [r.low, r.high, ...outliers(r)]), s.yDomain, 'yDomain');
  let out = valueGrid(p, yDomain, m.unit);
  const outlierLabels = [];
  data.forEach((r, i) => {
    const slot = p.w / data.length, x = p.x + (i + .5) * slot, half = Math.min(58, slot * .32), y = v => scale(v, ...yDomain, p.y + p.h, p.y), color = r.label === focus ? C.blue : C.gray, labelColor = r.label === focus ? C.blue : C.muted;
    out += line(x, y(r.low), x, y(r.high), { stroke: color, 'stroke-width': 2, ...(r.whiskerRule ? { 'data-whisker-rule': r.whiskerRule } : {}) });
    out += line(x - 13, y(r.low), x + 13, y(r.low), { stroke: color, 'stroke-width': 2 }) + line(x - 13, y(r.high), x + 13, y(r.high), { stroke: color, 'stroke-width': 2 });
    out += rect(x - half, y(r.q3), half * 2, y(r.q1) - y(r.q3), 'white', { stroke: color, 'stroke-width': 2, 'data-q1': r.q1, 'data-q3': r.q3 }) + line(x - half, y(r.median), x + half, y(r.median), { stroke: color, 'stroke-width': 3, 'data-median': r.median });
    outliers(r).forEach(v => {
      const cy = y(v), value = num(v), note = `離群 ${value}`, item = { left: x + 9, right: x + 9 + countWidth(note) * 18, top: cy < p.y + 22 ? cy + 3 : cy - 22, bottom: cy < p.y + 22 ? cy + 22 : cy - 3 };
      if (item.right > p.x + p.w || outlierLabels.some(other => overlaps(item, other))) warn('box outlier labels overlap; enlarge, split, or use a table');
      outlierLabels.push(item);
      out += dot(x, cy, 'white', { r: 4, stroke: color, 'stroke-width': 2, 'data-outlier': v }) + text(item.left, item.bottom - 3, note, { ...caption, fill: labelColor });
    });
    out += label(x, p.y + p.h + 40, r.label, slot - 10, { ...caption, 'text-anchor': 'middle', fill: labelColor }, 1);
    out += label(x, p.y + p.h + 64, `Q1 ${num(r.q1)}／中位 ${num(r.median)}／Q3 ${num(r.q3)}`, slot - 10, { ...caption, 'text-anchor': 'middle', fill: labelColor }, 1);
  });
  return out;
}

function matrix(s, m) {
  const data = rows(s, 1, 16), xLabel = axisLabel(s.xLabel, 'xLabel'), yLabel = axisLabel(s.yLabel, 'yLabel');
  const xDomain = domain(s.xDomain, 'xDomain'), yDomain = domain(s.yDomain, 'yDomain');
  if (!finite(s.xThreshold) || !finite(s.yThreshold) || s.xThreshold <= xDomain[0] || s.xThreshold >= xDomain[1] || s.yThreshold <= yDomain[0] || s.yThreshold >= yDomain[1]) fail('thresholds must be finite values strictly inside their explicit domains');
  if (s.quadrantLabels !== undefined && (!Array.isArray(s.quadrantLabels) || s.quadrantLabels.length !== 4 || s.quadrantLabels.some(value => typeof value !== 'string' || !value.trim()))) fail('quadrantLabels must be four nonempty labels in TL, TR, BL, BR order');
  if (s.highlightedQuadrant !== undefined && !['TL', 'TR', 'BL', 'BR'].includes(s.highlightedQuadrant)) fail('highlightedQuadrant must be TL, TR, BL, or BR');
  data.forEach((r, i) => { if (!finite(r.x) || !finite(r.y) || r.x < xDomain[0] || r.x > xDomain[1] || r.y < yDomain[0] || r.y > yDomain[1]) fail(`row ${i + 1} must be inside the declared domains`); });
  const focus = s.focus === undefined ? null : namedFocus(s, data), p = plot(m, 105, 55);
  const marks = data.map(r => ({ ...r, cx: scale(r.x, ...xDomain, p.x, p.x + p.w), cy: scale(r.y, ...yDomain, p.y + p.h, p.y) }));
  const tx = scale(s.xThreshold, ...xDomain, p.x, p.x + p.w), ty = scale(s.yThreshold, ...yDomain, p.y + p.h, p.y);
  const quadrants = [{ key: 'TL', x: p.x, y: p.y, w: tx - p.x, h: ty - p.y }, { key: 'TR', x: tx, y: p.y, w: p.x + p.w - tx, h: ty - p.y }, { key: 'BL', x: p.x, y: ty, w: tx - p.x, h: p.y + p.h - ty }, { key: 'BR', x: tx, y: ty, w: p.x + p.w - tx, h: p.y + p.h - ty }];
  // ponytail: try four corners greedily; add backtracking if valid dense layouts are rejected.
  const headers = (s.quadrantLabels || []).map((value, index) => {
    const q = quadrants[index], width = countWidth(value) * 18;
    if (width > q.w - 24 || q.h < 32) warn('matrix quadrant labels exceed their quadrant; enlarge or shorten them');
    const corners = [
      { x: q.x + 12, y: q.y + 22, anchor: 'start' },
      { x: q.x + q.w - 12, y: q.y + 22, anchor: 'end' },
      { x: q.x + 12, y: q.y + q.h - 10, anchor: 'start' },
      { x: q.x + q.w - 12, y: q.y + q.h - 10, anchor: 'end' },
    ];
    const outer = index;
    const candidates = [corners[outer], ...corners.filter((_, corner) => corner !== outer)].map(candidate => ({
      ...candidate, value, q, left: candidate.anchor === 'end' ? candidate.x - width : candidate.x,
      right: candidate.anchor === 'end' ? candidate.x : candidate.x + width, top: candidate.y - 18, bottom: candidate.y + 6,
    }));
    const placed = candidates.find(candidate => !marks.some(mark => mark.cx + 8 > candidate.left && mark.cx - 8 < candidate.right && mark.cy + 8 > candidate.top && mark.cy - 8 < candidate.bottom));
    if (!placed) warn('matrix quadrant labels overlap points; enlarge, split, or use a table');
    return placed || candidates[0];
  });
  if (headers.some((a, i) => headers.slice(0, i).some(b => overlaps(a, b)))) warn('matrix quadrant labels overlap; enlarge or shorten them');
  const occupied = [...headers], labels = [];
  for (const mark of marks) {
    const value = `${mark.label} ${num(mark.x)}／${num(mark.y)}`, width = countWidth(value) * 20;
    const candidates = [
      { x: mark.cx, y: mark.cy - 16, anchor: 'middle' }, { x: mark.cx, y: mark.cy + 30, anchor: 'middle' },
      { x: mark.cx - 12, y: mark.cy + 6, anchor: 'end' }, { x: mark.cx + 12, y: mark.cy + 6, anchor: 'start' },
    ].map(candidate => ({ ...candidate, value, left: candidate.anchor === 'end' ? candidate.x - width : candidate.anchor === 'start' ? candidate.x : candidate.x - width / 2, right: candidate.anchor === 'end' ? candidate.x : candidate.anchor === 'start' ? candidate.x + width : candidate.x + width / 2, top: candidate.y - 22, bottom: candidate.y + 6 }));
    const placed = candidates.find(candidate => candidate.left >= p.x && candidate.right <= p.x + p.w && candidate.top >= p.y && candidate.bottom <= p.y + p.h && !occupied.some(other => overlaps(candidate, other)) && !marks.some(other => other !== mark && candidate.left <= other.cx + 8 && candidate.right >= other.cx - 8 && candidate.top <= other.cy + 8 && candidate.bottom >= other.cy - 8));
    if (!placed) warn('matrix labels overlap; enlarge, split, or use a table');
    labels.push(placed || candidates[0]); occupied.push(placed || candidates[0]);
  }
  let out = '';
  if (s.highlightedQuadrant) {
    const q = quadrants.find(item => item.key === s.highlightedQuadrant);
    out += rect(q.x, q.y, q.w, q.h, '#F6F6F6', { 'data-highlighted-quadrant': q.key });
  }
  out += axes(p, xDomain, yDomain, xLabel, yLabel);
  out += line(tx, p.y, tx, p.y + p.h, { stroke: C.gray, 'stroke-dasharray': '5 5', 'data-x-threshold': s.xThreshold });
  out += line(p.x, ty, p.x + p.w, ty, { stroke: C.gray, 'stroke-dasharray': '5 5', 'data-y-threshold': s.yThreshold });
  headers.forEach(({ value, q, x, y, anchor }) => {
    out += label(x, y, value, q.w - 24, { ...caption, fill: q.key === s.highlightedQuadrant ? C.blue : C.muted, 'font-weight': q.key === s.highlightedQuadrant ? 700 : 400, 'text-anchor': anchor }, 1);
  });
  marks.forEach((r, i) => { const color = r.label === focus ? C.blue : C.gray, labelColor = r.label === focus ? C.blue : C.muted, placedLabel = labels[i]; out += dot(r.cx, r.cy, color, { r: r.label === focus ? 8 : 6, 'data-label': r.label, 'data-x': r.x, 'data-y': r.y }) + text(placedLabel.x, placedLabel.y, placedLabel.value, { fill: labelColor, 'font-size': 20, 'text-anchor': placedLabel.anchor }); });
  return out;
}

module.exports = { scatter, box, matrix };
