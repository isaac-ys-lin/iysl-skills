'use strict';

const { C, finite, fail, text, line, rect, dot, countWidth, rows, namedFocus, extent, scale, tick, plot, label } = require('./chart-utils');

const caption = { fill: C.muted, 'font-size': 14 };
const unitLabel = (value, name) => {
  if (typeof value !== 'string' || !value.trim() || !/[（(].+[）)]/.test(value)) fail(`${name} must state its unit, for example "處理時間（天）"`);
  return value;
};
const domain = (value, name) => {
  if (!Array.isArray(value) || value.length !== 2 || !value.every(finite) || value[0] >= value[1]) fail(`${name} must be [min, max] with min < max`);
  return value;
};
const placed = (items, what) => {
  for (let i = 0; i < items.length; i++) for (let j = 0; j < i; j++) {
    const a = items[i], b = items[j];
    if (Math.abs(a.x - b.x) < (a.w + b.w) / 2 + 10 && Math.abs(a.y - b.y) < 24) fail(`${what} labels overlap; enlarge, split, or use a table`);
  }
};

function axes(p, xDomain, yDomain, xLabel, yLabel, xLabelAbove = false) {
  let out = '';
  for (let i = 0; i <= 4; i++) {
    const x = p.x + p.w * i / 4, y = p.y + p.h * i / 4;
    out += line(x, p.y, x, p.y + p.h) + line(p.x, y, p.x + p.w, y);
    out += text(x, p.y + p.h + 20, tick(xDomain[0] + (xDomain[1] - xDomain[0]) * i / 4), { ...caption, 'text-anchor': 'middle' });
    out += text(p.x - 10, p.y + p.h - p.h * i / 4 + 5, tick(yDomain[0] + (yDomain[1] - yDomain[0]) * i / 4), { ...caption, 'text-anchor': 'end' });
  }
  if (xDomain[0] <= 0 && xDomain[1] >= 0) out += line(scale(0, ...xDomain, p.x, p.x + p.w), p.y, scale(0, ...xDomain, p.x, p.x + p.w), p.y + p.h, { stroke: C.gray, 'stroke-width': 1.5, 'data-baseline': 0 });
  if (yDomain[0] <= 0 && yDomain[1] >= 0) out += line(p.x, scale(0, ...yDomain, p.y + p.h, p.y), p.x + p.w, scale(0, ...yDomain, p.y + p.h, p.y), { stroke: C.gray, 'stroke-width': 1.5, 'data-baseline': 0 });
  return out + label(p.x + p.w, xLabelAbove ? p.y - 16 : p.y + p.h + 50, xLabelAbove ? `橫軸：${xLabel}` : xLabel, p.w / 2 - 12, { ...caption, 'text-anchor': 'end' }, 1) + label(p.x, p.y - 16, yLabel, p.w / 2 - 12, caption, 1);
}

function valueGrid(p, yDomain, yLabel) {
  let out = '';
  for (let i = 0; i <= 4; i++) {
    const value = yDomain[0] + (yDomain[1] - yDomain[0]) * i / 4, y = scale(value, ...yDomain, p.y + p.h, p.y);
    out += line(p.x, y, p.x + p.w, y) + text(p.x - 10, y + 5, tick(value), { ...caption, 'text-anchor': 'end' });
  }
  if (yDomain[0] <= 0 && yDomain[1] >= 0) out += line(p.x, scale(0, ...yDomain, p.y + p.h, p.y), p.x + p.w, scale(0, ...yDomain, p.y + p.h, p.y), { stroke: C.gray, 'stroke-width': 1.5, 'data-baseline': 0 });
  return out + text(p.x, p.y - 16, yLabel, caption);
}

function scatter(s, m) {
  const data = rows(s, 3, 6), xLabel = unitLabel(s.xLabel, 'xLabel'), yLabel = unitLabel(s.yLabel, 'yLabel');
  data.forEach((r, i) => { if (!finite(r.x) || !finite(r.y)) fail(`row ${i + 1} needs finite x and y`); });
  const focus = s.focus === undefined ? null : namedFocus(s, data), p = plot(m, 105, 55);
  const xDomain = extent(data.map(r => r.x)), yDomain = extent(data.map(r => r.y));
  const marks = data.map(r => ({ ...r, cx: scale(r.x, ...xDomain, p.x, p.x + p.w), cy: scale(r.y, ...yDomain, p.y + p.h, p.y) }));
  for (let i = 0; i < marks.length; i++) for (let j = 0; j < i; j++) if (Math.hypot(marks[i].cx - marks[j].cx, marks[i].cy - marks[j].cy) < 34) fail('points or their index labels overlap; enlarge, split, or use a table');
  let out = axes(p, xDomain, yDomain, xLabel, yLabel, true);
  marks.forEach((r, i) => {
    const color = r.label === focus ? C.blue : C.gray;
    out += dot(r.cx, r.cy, color, { r: r.label === focus ? 8 : 6, 'data-label': r.label, 'data-x': r.x, 'data-y': r.y }) + text(r.cx + 10, r.cy - 8, i + 1, { fill: C.ink, 'font-size': 14, 'font-weight': 700 });
  });
  marks.forEach((r, i) => { out += label(p.x + (i % 2) * p.w / 2, p.y + p.h + 48 + Math.floor(i / 2) * 18, `${i + 1}. ${r.label} (${String(r.x)}, ${String(r.y)})`, p.w / 2 - 12, { ...caption, fill: r.label === focus ? C.blue : C.muted }, 1); });
  return out;
}

function box(s, m) {
  const data = rows(s, 2, 10);
  data.forEach((r, i) => {
    for (const key of ['low', 'q1', 'median', 'q3', 'high']) if (!finite(r[key])) fail(`row ${i + 1}.${key} must be finite`);
    if (r.whiskerRule !== '1.5IQR') fail(`row ${i + 1}.whiskerRule must be "1.5IQR"`);
    if (!Array.isArray(r.outliers) || r.outliers.length > 4 || r.outliers.some(v => !finite(v))) fail(`row ${i + 1}.outliers must be a numeric array of at most 4 values; split or use a table`);
    if (!(r.low <= r.q1 && r.q1 <= r.median && r.median <= r.q3 && r.q3 <= r.high)) fail(`row ${i + 1} summary must be ordered`);
    const iqr = r.q3 - r.q1, lo = r.q1 - 1.5 * iqr, hi = r.q3 + 1.5 * iqr;
    if (r.low < lo || r.high > hi || r.outliers.some(v => v >= lo && v <= hi)) fail(`row ${i + 1} violates its 1.5 IQR whisker/outlier definition`);
  });
  const focus = s.focus === undefined ? null : namedFocus(s, data), p = plot(m, 105, 55);
  if (p.w / (data.length + 1) < 100) fail('box groups need at least 100px each for readable median labels; enlarge, split, or use a table');
  const yDomain = extent(data.flatMap(r => [r.low, r.high, ...r.outliers]));
  let out = valueGrid(p, yDomain, `數值（${m.unit || '原始單位'}）`);
  data.forEach((r, i) => {
    const x = p.x + (i + 1) * p.w / (data.length + 1), y = v => scale(v, ...yDomain, p.y + p.h, p.y), color = r.label === focus ? C.blue : C.gray;
    out += line(x, y(r.low), x, y(r.high), { stroke: color, 'stroke-width': 2, 'data-whisker-rule': r.whiskerRule });
    out += line(x - 13, y(r.low), x + 13, y(r.low), { stroke: color, 'stroke-width': 2 }) + line(x - 13, y(r.high), x + 13, y(r.high), { stroke: color, 'stroke-width': 2 });
    out += rect(x - 24, y(r.q3), 48, y(r.q1) - y(r.q3), 'white', { stroke: color, 'stroke-width': 2, 'data-q1': r.q1, 'data-q3': r.q3 }) + line(x - 24, y(r.median), x + 24, y(r.median), { stroke: color, 'stroke-width': 3, 'data-median': r.median });
    r.outliers.forEach(v => { out += dot(x, y(v), 'white', { r: 4, stroke: color, 'stroke-width': 2, 'data-outlier': v }); });
    out += text(x + 30, y(r.median) + 4, `中位 ${String(r.median)}`, { ...caption, fill: color, 'font-size': 12 }) + label(x, p.y + p.h + 42, r.label, 95, { ...caption, 'text-anchor': 'middle', fill: color });
  });
  return out;
}

function matrix(s, m) {
  const data = rows(s, 1, 16), xLabel = unitLabel(s.xLabel, 'xLabel'), yLabel = unitLabel(s.yLabel, 'yLabel');
  if (typeof s.rubric !== 'string' || !s.rubric.trim()) fail('rubric must state the source-defined scoring meaning');
  const xDomain = domain(s.xDomain, 'xDomain'), yDomain = domain(s.yDomain, 'yDomain');
  if (!finite(s.xThreshold) || !finite(s.yThreshold) || s.xThreshold <= xDomain[0] || s.xThreshold >= xDomain[1] || s.yThreshold <= yDomain[0] || s.yThreshold >= yDomain[1]) fail('thresholds must be finite values strictly inside their explicit domains');
  data.forEach((r, i) => { if (!finite(r.x) || !finite(r.y) || r.x < xDomain[0] || r.x > xDomain[1] || r.y < yDomain[0] || r.y > yDomain[1]) fail(`row ${i + 1} must be inside the declared domains`); });
  const focus = s.focus === undefined ? null : namedFocus(s, data), p = plot(m, 105, 55);
  const marks = data.map(r => ({ ...r, cx: scale(r.x, ...xDomain, p.x, p.x + p.w), cy: scale(r.y, ...yDomain, p.y + p.h, p.y) }));
  const labels = marks.map(r => ({ x: r.cx, y: r.cy - 16, w: countWidth(r.label) * 16 }));
  if (labels.some(r => r.x - r.w / 2 < p.x || r.x + r.w / 2 > p.x + p.w || r.y - 14 < p.y)) fail('matrix labels exceed the plot; enlarge, split, or use a table');
  placed(labels, 'matrix');
  let out = axes(p, xDomain, yDomain, xLabel, yLabel);
  out += line(scale(s.xThreshold, ...xDomain, p.x, p.x + p.w), p.y, scale(s.xThreshold, ...xDomain, p.x, p.x + p.w), p.y + p.h, { stroke: C.gray, 'stroke-dasharray': '5 5', 'data-x-threshold': s.xThreshold });
  out += line(p.x, scale(s.yThreshold, ...yDomain, p.y + p.h, p.y), p.x + p.w, scale(s.yThreshold, ...yDomain, p.y + p.h, p.y), { stroke: C.gray, 'stroke-dasharray': '5 5', 'data-y-threshold': s.yThreshold });
  marks.forEach(r => { const color = r.label === focus ? C.blue : C.gray; out += dot(r.cx, r.cy, color, { r: r.label === focus ? 8 : 6, 'data-label': r.label, 'data-x': r.x, 'data-y': r.y }) + text(r.cx, r.cy - 14, r.label, { fill: color, 'font-size': 13, 'text-anchor': 'middle' }); });
  return out;
}

module.exports = { scatter, box, matrix };
