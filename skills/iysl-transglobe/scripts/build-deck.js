#!/usr/bin/env node
'use strict';
// deck.json → TransGlobe 16:9 PPTX. Page layouts follow the prototype deck (簡報樣板, 1920×1080 → 13.333×7.5 in, px ÷ 144 = in, px ÷ 2 = pt).
// Text, tables and the common chart families stay native and editable; other chart families embed the bundled SVG with a PNG fallback.
const fs = require('node:fs');
const path = require('node:path');
const U = require('./chart-utils');
const { render, footerLines } = require('./render-chart');
const { planNativeChart, addPlannedChart } = require('./native-charts');

function load(name) {
  try { return require(name); } catch {
    throw new Error(`missing dependency ${name}; run: npm install --prefix "${__dirname}"`);
  }
}

const W = 13.333, H = 7.5, ML = 0.667, MR = 0.667, MT = 0.667, MB = 0.583, CW = W - ML - MR;
const C = {
  ink: '111111', muted: '4A4A4A', line: 'E3E3E6', blue: '28317B', gray: '7F7F7F', coverTitle: '000066', pageTitle: '000099',
  dark: '142979', darkMuted: 'BDCCED', darkLine: '4C5C99', tint: 'F6F6FA', white: 'FFFFFF',
};
const PT = { cover: 48, chapter: 39, title: 27, body: 18, label: 15, caption: 13.5, source: 12, kpi: 90, metric: 39, secondary: 27, benchmark: 21 };
const LAYOUTS = ['cover', 'chapter', 'summary', 'kpi', 'chart', 'list', 'columns', 'process', 'flow', 'table', 'compare', 'decisions'];
const EXHIBITS = new Set(['chart', 'list', 'table', 'compare']);

const warnings = [];
let current = '';
const warn = message => warnings.push(`${current}: ${message}`);
const fail = message => { throw new Error(`${current}: ${message}`); };
const str = v => typeof v === 'string' && v.trim() !== '';
const lineCount = (value, widthIn, pt) => String(value ?? '').split('\n')
  .reduce((n, part) => n + Math.max(1, Math.ceil(U.countWidth(part) * pt / 72 / widthIn - 0.02)), 0);
const lineHeight = (pt, k = 1.5) => pt * k / 72;

// Text helpers ---------------------------------------------------------------------------------
function runs(value, opts = {}) {
  const parts = String(value).split('\n');
  return parts.map((part, i) => ({ text: part, options: { ...opts, breakLine: i < parts.length - 1 } }));
}
function addText(slide, value, box, o = {}) {
  if (value === undefined || value === null || value === '') return;
  const content = Array.isArray(value) ? value : runs(value);
  const size = o.size || PT.label, biggest = Math.max(size, ...content.map(r => r.options?.fontSize || 0));
  // Exact spacing mirrors CSS line-height, so layout does not drift with each font's built-in leading.
  slide.addText(content, {
    x: box.x, y: box.y, w: box.w, h: box.h, margin: 0, valign: o.valign || 'top', align: o.align || 'left',
    fontFace: o.serif ? 'Cambria' : 'Arial', fontSize: size, color: o.color || C.ink, bold: !!o.bold,
    lineSpacing: Math.round(biggest * (o.lh || 1.5) * 10) / 10, charSpacing: o.spacing, fit: 'none', wrap: true,
  });
}
// A value with a smaller unit after it, e.g. 6.3 pp.
const valueRuns = (value, unit, size, unitSize, color, bold = false) => [
  { text: String(value), options: { fontSize: size, color, bold } },
  ...(str(unit) ? [{ text: ' ' + unit, options: { fontSize: unitSize, color, bold: false } }] : []),
];
const rule = (slide, x, y, w, color = C.line, pt = 0.75) => slide.addShape('line', { x, y, w, h: 0, line: { color, width: pt } });
const vrule = (slide, x, y, h, color = C.line, pt = 0.75) => slide.addShape('line', { x, y, w: 0, h, line: { color, width: pt } });

// Shared page chrome ---------------------------------------------------------------------------
function header(slide, page, ctx, dark = false) {
  let y = MT;
  const muted = dark ? C.darkMuted : C.muted;
  if (str(page.eyebrow) || ctx.exhibit) {
    addText(slide, page.eyebrow || '', { x: ML, y, w: CW - 2, h: 0.28 }, { size: PT.caption, color: muted, spacing: 1 });
    if (ctx.exhibit) addText(slide, `EXHIBIT ${ctx.exhibit}`, { x: W - MR - 2, y, w: 2, h: 0.28 }, { size: PT.caption, color: muted, align: 'right', spacing: 1 });
    y += 0.28 + 0.125;
  }
  if (!str(page.title)) fail('needs a title that states the page conclusion');
  const titleLines = lineCount(page.title, 11.39, PT.title);
  if (titleLines > 2) warn('title wraps beyond two lines; shorten it to one clear judgement');
  const th = titleLines * lineHeight(PT.title, 1.3);
  addText(slide, page.title, { x: ML, y, w: 11.39, h: th + 0.05 }, { size: PT.title, bold: true, color: dark ? C.white : C.pageTitle, lh: 1.3 });
  y += th;
  if (str(page.lede)) {
    const lh = lineCount(page.lede, CW, PT.label) * lineHeight(PT.label);
    addText(slide, page.lede, { x: ML, y: y + 0.125, w: CW, h: lh }, { size: PT.label, color: dark ? C.darkMuted : C.ink });
    y += 0.125 + lh;
  }
  return y + 0.3;
}

function footer(slide, lines, ctx, dark = false) {
  const color = dark ? C.darkMuted : C.muted;
  const items = (lines || []).filter(str);
  let top = H - MB - 0.3;
  if (items.length) {
    const n = items.reduce((k, v) => k + lineCount(v, CW - 0.5, PT.source), 0);
    if (n > 4) warn('footer runs past four lines; move detail to speaker notes or an appendix table');
    const h = n * lineHeight(PT.source);
    top = H - MB - h;
    rule(slide, ML, top - 0.125, CW, dark ? C.darkLine : C.line);
    addText(slide, items.join('\n'), { x: ML, y: top, w: CW - 0.5, h }, { size: PT.source, color });
    top -= 0.125;
  }
  if (ctx.folio) addText(slide, ctx.folio, { x: W - MR - 0.8, y: H - MB - lineHeight(PT.source), w: 0.8, h: lineHeight(PT.source) }, { size: PT.source, color, align: 'right' });
  return top - 0.25;
}

function area(top, bottom) {
  const h = bottom - top;
  if (h < 1.5) warn('little room left for content; shorten the title, lede or footer');
  return { x: ML, y: top, w: CW, h };
}
// Vertically centre a block of known height inside an area.
const centre = (a, h) => a.y + Math.max(0, (a.h - h) / 2);

// Layouts --------------------------------------------------------------------------------------
function cover(slide, page, ctx) {
  if (str(ctx.logo)) slide.addImage({ path: ctx.logo, x: ML, y: MT, w: 2.01, h: 0.444, sizing: { type: 'contain', w: 2.01, h: 0.444 } });
  if (str(page.tag)) addText(slide, page.tag, { x: W - MR - 5, y: MT + 0.1, w: 5, h: 0.3 }, { size: PT.caption, color: C.muted, align: 'right', spacing: 1.6 });
  const meta = Array.isArray(page.meta) ? page.meta.slice(0, 3) : [];
  let metaTop = H - MB;
  if (meta.length) {
    const widths = [2, 1, 1].slice(0, meta.length), total = widths.reduce((a, b) => a + b), gap = 0.333;
    const unit = (CW - gap * (meta.length - 1)) / total;
    const valueH = Math.max(...meta.map((m, i) => lineCount(m.value, unit * widths[i], PT.caption))) * lineHeight(PT.caption, 1.6);
    metaTop = H - MB - (0.25 + valueH) - 0.167;
    rule(slide, ML, metaTop, CW);
    let x = ML;
    meta.forEach((m, i) => {
      const w = unit * widths[i];
      addText(slide, m.label, { x, y: metaTop + 0.167, w, h: 0.22 }, { size: PT.source, color: C.muted });
      addText(slide, m.value, { x, y: metaTop + 0.167 + 0.25, w, h: valueH }, { size: PT.caption, lh: 1.6 });
      x += w + gap;
    });
  }
  const titleLines = lineCount(page.title, 10.76, PT.cover);
  if (!str(page.title)) fail('cover needs a title');
  if (titleLines > 3) warn('cover title wraps beyond three lines');
  const eh = str(page.eyebrow) ? lineHeight(PT.body, 1.4) + 0.25 : 0;
  const th = titleLines * lineHeight(PT.cover, 1.3);
  const sh = str(page.summary) ? 0.25 + lineCount(page.summary, 9.65, PT.body) * lineHeight(PT.body, 1.6) : 0;
  const top = MT + 0.444, y = top + Math.max(0, (metaTop - top - (eh + th + sh)) / 2);
  if (eh) addText(slide, page.eyebrow, { x: ML, y, w: 10.76, h: lineHeight(PT.body, 1.4) }, { size: PT.body, color: C.muted, spacing: 0.7, lh: 1.4 });
  addText(slide, page.title, { x: ML, y: y + eh, w: 10.76, h: th + 0.05 }, { size: PT.cover, bold: true, serif: true, color: C.coverTitle, lh: 1.3 });
  if (sh) addText(slide, page.summary, { x: ML, y: y + eh + th + 0.25, w: 9.65, h: sh - 0.25 }, { size: PT.body, color: C.muted, lh: 1.6 });
}

function chapter(slide, page, ctx) {
  slide.background = { color: C.dark };
  const bottom = footer(slide, page.footer, ctx, true);
  const nh = str(page.number) ? PT.kpi / 72 + 0.25 : 0, th = lineCount(page.title, 10.76, PT.chapter) * lineHeight(PT.chapter, 1.3);
  const sh = str(page.summary) ? 0.25 + lineCount(page.summary, 8.33, PT.body) * lineHeight(PT.body, 1.6) : 0;
  const y = centre({ y: MT, h: bottom - MT }, nh + th + sh);
  if (nh) addText(slide, page.number, { x: ML, y, w: 4, h: PT.kpi / 72 }, { size: PT.kpi, color: C.darkMuted, lh: 1 });
  addText(slide, page.title, { x: ML, y: y + nh, w: 10.76, h: th + 0.05 }, { size: PT.chapter, bold: true, serif: true, color: C.white, lh: 1.3 });
  if (sh) addText(slide, page.summary, { x: ML, y: y + nh + th + 0.25, w: 8.33, h: sh - 0.25 }, { size: PT.body, color: C.darkMuted, lh: 1.6 });
}

function summary(slide, page, ctx) {
  const a = area(header(slide, page, ctx), footer(slide, page.footer, ctx));
  const t = page.thesis || {}, ev = Array.isArray(page.evidence) ? page.evidence : [];
  if (!str(t.heading) || ev.length < 1 || ev.length > 4) fail('summary needs thesis.heading and 1–4 evidence rows');
  const lw = (CW - 0.667) * 5 / 12, rx = ML + lw + 0.667, rw = CW - lw - 0.667;
  const hh = lineCount(t.heading, lw, PT.title) * lineHeight(PT.title, 1.4), bh = str(t.body) ? lineCount(t.body, lw, PT.body) * lineHeight(PT.body) : 0;
  const lh = (str(t.label) ? 0.3 + 0.167 : 0) + hh + 0.167 + bh;
  let y = centre(a, lh);
  if (str(t.label)) { addText(slide, t.label, { x: ML, y, w: lw, h: 0.3 }, { size: PT.caption, color: C.muted, spacing: 1 }); y += 0.3 + 0.167; }
  addText(slide, t.heading, { x: ML, y, w: lw, h: hh + 0.05 }, { size: PT.title, lh: 1.4 });
  y += hh + 0.167;
  addText(slide, t.body, { x: ML, y, w: lw, h: bh }, { size: PT.body });
  const nw = 1.46, tw = rw - nw - 0.25;
  const heights = ev.map(r => 0.5 + Math.max(lineHeight(PT.secondary, 1.2), (lineCount(r.heading, tw, PT.label) + lineCount(r.body, tw, PT.label)) * lineHeight(PT.label)));
  if (heights.reduce((s, v) => s + v, 0) > a.h) warn('evidence rows overflow; keep 2–3 rows with one-line explanations');
  y = centre(a, heights.reduce((s, v) => s + v, 0));
  rule(slide, rx, y, rw);
  ev.forEach((r, i) => {
    if (!str(String(r.value ?? ''))) fail('every evidence row needs a value');
    const h = heights[i], mid = y + h / 2;
    addText(slide, valueRuns(r.value, r.unit, PT.secondary, PT.label, C.ink), { x: rx, y: mid - 0.25, w: nw, h: 0.5 }, { valign: 'middle', lh: 1.1 });
    addText(slide, [...(str(r.heading) ? [{ text: r.heading, options: { bold: true, breakLine: !!str(r.body) } }] : []), ...(str(r.body) ? runs(r.body) : [])],
      { x: rx + nw + 0.25, y: y + 0.25, w: tw, h: h - 0.5 }, { size: PT.label, valign: 'middle' });
    y += h;
    rule(slide, rx, y, rw);
  });
}

function kpi(slide, page, ctx) {
  const a = area(header(slide, page, ctx), footer(slide, page.footer, ctx));
  const m = page.main || {}, sec = Array.isArray(page.secondary) ? page.secondary : [], bm = Array.isArray(m.benchmarks) ? m.benchmarks : [];
  if (!str(String(m.value ?? ''))) fail('kpi needs main.value');
  if (sec.length > 4 || bm.length > 3) warn('keep at most 3 benchmarks and 4 secondary metrics');
  const lw = (CW - 0.667) * 1.05 / 2.05, inner = lw - 0.5, rx = ML + lw + 0.667, rw = CW - lw - 0.667;
  const mainH = 0.3 + 0.125 + PT.kpi * 1.05 / 72 + 0.25 + bm.length * 0.5;
  let y = centre(a, mainH);
  vrule(slide, ML + lw, centre(a, Math.max(mainH, sec.length * 0.78)), Math.max(mainH, sec.length * 0.78));
  addText(slide, m.label, { x: ML, y, w: inner, h: 0.3 }, { size: PT.label });
  y += 0.3 + 0.125;
  addText(slide, valueRuns(m.value, m.unit, PT.kpi, PT.secondary, C.blue), { x: ML, y, w: inner, h: PT.kpi * 1.05 / 72 }, { lh: 1, valign: 'bottom' });
  y += PT.kpi * 1.05 / 72 + 0.25;
  bm.forEach(b => {
    rule(slide, ML, y, inner);
    addText(slide, b.label, { x: ML, y: y + 0.125, w: inner / 2, h: 0.35 }, { size: PT.label, valign: 'bottom' });
    addText(slide, valueRuns(b.value, b.unit, PT.benchmark, PT.label, C.ink), { x: ML + inner / 2, y: y + 0.08, w: inner / 2, h: 0.4 }, { align: 'right', valign: 'bottom', lh: 1.1 });
    y += 0.5;
  });
  y = centre(a, sec.length * 0.78 - 0.333);
  sec.forEach(s => {
    addText(slide, s.label, { x: rx, y, w: rw / 2, h: 0.45 }, { size: PT.label, valign: 'bottom' });
    addText(slide, valueRuns(s.value, s.unit, PT.secondary, PT.label, C.ink), { x: rx + rw / 2, y, w: rw / 2, h: 0.45 }, { align: 'right', valign: 'bottom', lh: 1.1 });
    y += 0.78;
  });
}

function chartPage(slide, page, ctx, pptx) {
  const spec0 = page.chart;
  if (!spec0 || typeof spec0 !== 'object' || !str(spec0.chart)) fail('chart page needs chart with a chart type');
  // Slide chrome carries title and source; fill the renderer's required fields from the page.
  const spec = { notes: [], ...spec0, title: spec0.title || page.title, source: spec0.source || page.source || ctx.source };
  for (const f of ['unit', 'period', 'source']) if (!str(spec[f])) fail(`chart needs ${f}`);
  const top = header(slide, { ...page, lede: page.lede ?? spec.subtitle }, ctx);
  const plan = page.svg === true ? null : planNativeChart(spec);
  const bottom = footer(slide, page.footer ? page.footer : [...footerLines(spec), ...(plan ? plan.extraFooter : [])], ctx);
  const aside = page.aside, a = area(top, bottom);
  const b = { x: a.x, y: a.y, w: aside ? a.w - 2.57 - 0.5 : a.w, h: a.h, area: a };
  if (plan) {
    addPlannedChart(pptx, slide, plan, b);
    ctx.chartMeta.push(plan.labelColors);
  } else {
    // SVG path: keep the chart's own aspect equal to the box so text sizes stay as designed.
    const width = 960, height = Math.max(350, Math.round(width * b.h / b.w));
    let svg;
    try { svg = render({ ...spec, layout: 'slide', width, height, placementWidthInches: Number(b.w.toFixed(3)) }, { bare: true }); }
    catch (e) { fail(`${e.message} (chart ${spec.chart})`); }
    const h = Math.min(b.h, b.w * height / width);
    slide.addImage({ data: 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64'), x: b.x, y: b.y + (b.h - h) / 2, w: h * width / height, h, altText: `${page.title}；${spec.unit}；${spec.period}` });
  }
  if (aside) {
    const x = b.x + b.w + 0.5, w = 2.57 - 0.333;
    const bh = (str(aside.label) ? 0.35 : 0) + (str(String(aside.value ?? '')) ? 0.7 : 0) + (str(aside.body) ? lineCount(aside.body, w, PT.label) * lineHeight(PT.label) + 0.25 : 0);
    vrule(slide, x, b.area.y, b.area.h);
    let y = centre(b.area, bh);
    if (str(aside.label)) { addText(slide, aside.label, { x: x + 0.333, y, w, h: 0.3 }, { size: PT.label }); y += 0.35; }
    if (str(String(aside.value ?? ''))) { addText(slide, valueRuns(aside.value, aside.unit, PT.metric, PT.label, C.blue), { x: x + 0.333, y, w, h: 0.65 }, { lh: 1.1 }); y += 0.7 + 0.25; }
    addText(slide, aside.body, { x: x + 0.333, y, w, h: lineCount(aside.body, w, PT.label) * lineHeight(PT.label) }, { size: PT.label });
  }
}

function list(slide, page, ctx) {
  const a = area(header(slide, page, ctx), footer(slide, page.footer, ctx));
  const items = Array.isArray(page.items) ? page.items : [];
  if (items.length < 2 || items.length > 5) fail('list needs 2–5 items');
  const hasTag = items.some(i => str(i.tag)), hasNote = items.some(i => str(i.note));
  const tagW = hasTag ? 1.53 : 0, noteW = hasNote ? 3.125 : 0, gap = 0.333;
  const midX = ML + (hasTag ? tagW + gap : 0), midW = CW - (hasTag ? tagW + gap : 0) - (hasNote ? noteW + gap : 0);
  const heights = items.map(it => 0.5 + Math.max(lineCount(it.heading, midW, PT.body) * lineHeight(PT.body, 1.4) + (str(it.body) ? 0.083 + lineCount(it.body, midW, PT.label) * lineHeight(PT.label) : 0),
    str(it.note) ? lineCount(it.note, noteW, PT.label) * lineHeight(PT.label) : 0));
  const total = heights.reduce((s, v) => s + v, 0);
  if (total > a.h) warn('list rows overflow the page; shorten bodies or split the list');
  let y = centre(a, total);
  items.forEach((it, i) => {
    if (!str(it.heading)) fail('every list item needs a heading');
    const focus = page.focus === i;
    if (hasTag) addText(slide, it.tag || '', { x: ML, y: y + 0.25, w: tagW, h: 0.35 }, { size: PT.label, color: focus ? C.blue : C.muted, bold: focus });
    const hh = lineCount(it.heading, midW, PT.body) * lineHeight(PT.body, 1.4);
    addText(slide, it.heading, { x: midX, y: y + 0.25, w: midW, h: hh }, { size: PT.body, bold: true, lh: 1.4, color: focus ? C.blue : C.ink });
    if (str(it.body)) addText(slide, it.body, { x: midX, y: y + 0.25 + hh + 0.083, w: midW, h: heights[i] - 0.5 - hh - 0.083 }, { size: PT.label });
    if (str(it.note)) addText(slide, it.note, { x: ML + CW - noteW, y: y + 0.25, w: noteW, h: heights[i] - 0.5 }, { size: PT.label });
    y += heights[i];
    rule(slide, ML, y, CW);
  });
}

function columns(slide, page, ctx) {
  const a = area(header(slide, page, ctx), footer(slide, page.footer, ctx));
  const items = Array.isArray(page.items) ? page.items : [];
  if (items.length < 2 || items.length > 4) fail('columns needs 2–4 items');
  const gap = 0.5, cw = (CW - gap * (items.length - 1)) / items.length;
  const hasValue = items.some(i => str(String(i.value ?? ''))), hasKicker = items.some(i => str(i.kicker));
  const blockH = it => 0.25 + (hasKicker ? 0.35 : 0) + (hasValue ? 0.75 : 0) + lineCount(it.heading, cw, PT.body) * lineHeight(PT.body, 1.4) + (str(it.body) ? 0.125 + lineCount(it.body, cw, PT.label) * lineHeight(PT.label) : 0);
  const total = Math.max(...items.map(blockH));
  if (total > a.h) warn('column text overflows; shorten bodies to two or three lines');
  const top = centre(a, total);
  items.forEach((it, i) => {
    if (!str(it.heading)) fail('every column needs a heading');
    const x = ML + i * (cw + gap), focus = page.focus === undefined || page.focus === i;
    rule(slide, x, top, cw, focus ? C.blue : C.line, focus ? 1.5 : 0.75);
    let y = top + 0.25;
    if (hasKicker) { addText(slide, it.kicker || '', { x, y, w: cw, h: 0.3 }, { size: PT.caption, color: C.muted, spacing: 1 }); y += 0.35; }
    if (hasValue) { addText(slide, str(String(it.value ?? '')) ? valueRuns(it.value, it.unit, PT.metric, PT.label, focus ? C.blue : C.ink) : '', { x, y, w: cw, h: 0.65 }, { lh: 1.1 }); y += 0.75; }
    const hh = lineCount(it.heading, cw, PT.body) * lineHeight(PT.body, 1.4);
    addText(slide, it.heading, { x, y, w: cw, h: hh }, { size: PT.body, bold: true, lh: 1.4 });
    if (str(it.body)) addText(slide, it.body, { x, y: y + hh + 0.125, w: cw, h: lineCount(it.body, cw, PT.label) * lineHeight(PT.label) }, { size: PT.label });
  });
}

function processPage(slide, page, ctx) {
  const a = area(header(slide, page, ctx), footer(slide, page.footer, ctx));
  const steps = Array.isArray(page.steps) ? page.steps : [];
  if (steps.length < 3 || steps.length > 6) fail('process needs 3–6 steps');
  const colW = CW / steps.length, tw = colW - 0.3, r = 0.11;
  const textH = Math.max(...steps.map(s => lineCount(s.heading, tw, PT.body) * lineHeight(PT.body, 1.4) + (str(s.body) ? 0.125 + lineCount(s.body, tw, PT.label) * lineHeight(PT.label) : 0)));
  const total = 0.35 + 0.2 + r * 2 + 0.3 + textH;
  if (total > a.h) warn('process step text overflows; shorten step bodies');
  const top = centre(a, total), lineY = top + 0.35 + 0.2 + r;
  rule(slide, ML + r, lineY, colW * (steps.length - 1), C.gray, 1.5);
  steps.forEach((s, i) => {
    if (!str(s.heading)) fail('every step needs a heading');
    const x = ML + i * colW, focus = page.focus === undefined || page.focus === i;
    addText(slide, s.label || String(i + 1).padStart(2, '0'), { x, y: top, w: tw, h: 0.35 }, { size: PT.caption, color: focus ? C.blue : C.muted, bold: focus, spacing: 1 });
    slide.addShape('ellipse', { x, y: lineY - r, w: r * 2, h: r * 2, fill: { color: focus ? C.blue : C.white }, line: { color: focus ? C.blue : C.gray, width: 1.5 } });
    const y = lineY + r + 0.3, hh = lineCount(s.heading, tw, PT.body) * lineHeight(PT.body, 1.4);
    addText(slide, s.heading, { x, y, w: tw, h: hh }, { size: PT.body, bold: true, lh: 1.4 });
    if (str(s.body)) addText(slide, s.body, { x, y: y + hh + 0.125, w: tw, h: lineCount(s.body, tw, PT.label) * lineHeight(PT.label) }, { size: PT.label });
  });
}

function flow(slide, page, ctx) {
  const a = area(header(slide, page, ctx), footer(slide, page.footer, ctx));
  const nodes = Array.isArray(page.nodes) ? page.nodes : [];
  if (nodes.length < 2 || nodes.length > 5) fail('flow needs 2–5 nodes');
  const joins = nodes.slice(1).map((_, i) => (Array.isArray(page.connectors) && page.connectors[i]) || '→');
  const gap = 0.5, w = (CW - gap * (nodes.length - 1)) / nodes.length, inner = w - 0.4;
  const focus = page.focus ?? nodes.length - 1;
  const textH = n => (str(n.label) ? 0.3 : 0) + lineCount(n.heading, inner, PT.body) * lineHeight(PT.body, 1.4) + (str(n.body) ? 0.125 + lineCount(n.body, inner, PT.label) * lineHeight(PT.label) : 0);
  const boxH = Math.max(...nodes.map(textH)) + 0.5;
  const noteH = str(page.note) ? 0.35 + lineCount(page.note, CW - 0.4, PT.label) * lineHeight(PT.label) + 0.2 : 0;
  if (boxH + noteH > a.h) warn('flow boxes overflow; shorten node text');
  const top = centre(a, boxH + noteH);
  nodes.forEach((n, i) => {
    if (!str(n.heading)) fail('every flow node needs a heading');
    const x = ML + i * (w + gap), on = i === focus;
    slide.addShape('rect', { x, y: top, w, h: boxH, fill: { color: on ? C.blue : C.white }, line: { color: on ? C.blue : '9DB1D9', width: 1 } });
    let y = top + 0.25;
    if (str(n.label)) { addText(slide, n.label, { x: x + 0.2, y, w: inner, h: 0.28 }, { size: PT.caption, color: on ? C.darkMuted : C.muted }); y += 0.3; }
    const hh = lineCount(n.heading, inner, PT.body) * lineHeight(PT.body, 1.4);
    addText(slide, n.heading, { x: x + 0.2, y, w: inner, h: hh }, { size: PT.body, bold: true, lh: 1.4, color: on ? C.white : C.blue });
    if (str(n.body)) addText(slide, n.body, { x: x + 0.2, y: y + hh + 0.125, w: inner, h: lineCount(n.body, inner, PT.label) * lineHeight(PT.label) }, { size: PT.label, color: on ? C.white : C.ink });
    if (i) addText(slide, joins[i - 1], { x: x - gap, y: top, w: gap, h: boxH }, { size: PT.secondary, color: C.gray, align: 'center', valign: 'middle', lh: 1 });
  });
  if (noteH) {
    const y = top + boxH + 0.35;
    vrule(slide, ML, y, noteH - 0.35, C.blue, 3);
    addText(slide, page.note, { x: ML + 0.2, y, w: CW - 0.4, h: noteH - 0.35 }, { size: PT.label, valign: 'middle' });
  }
}

const numeric = v => /^[+\-−]?[\d,]+(\.\d+)?\s*%?$/.test(String(v).trim());
const cell = (text, o) => ({ text: String(text ?? ''), options: o });
const border = (bottom, color = C.line, pt = 0.75) => [{ type: 'none' }, { type: 'none' }, bottom ? { type: 'solid', color, pt } : { type: 'none' }, { type: 'none' }];

function table(slide, page, ctx) {
  const a = area(header(slide, page, ctx), footer(slide, page.footer, ctx));
  const cols = page.columns, rows = page.rows;
  if (!Array.isArray(cols) || cols.length < 2 || !Array.isArray(rows) || !rows.length) fail('table needs columns and rows');
  if (rows.some(r => !Array.isArray(r) || r.length !== cols.length)) fail('every table row needs one cell per column');
  const colDefs = cols.map(c => typeof c === 'string' ? { label: c } : c);
  const align = colDefs.map((c, j) => c.align || (j > 0 && rows.every(r => numeric(r[j]) || r[j] === '' || r[j] === null) ? 'right' : 'left'));
  const weights = colDefs.map(c => c.width || 1), sum = weights.reduce((s, v) => s + v, 0);
  const rowH = 0.42, maxRows = Math.floor((a.h - 0.45) / rowH);
  if (rows.length > maxRows) warn(`table has ${rows.length} rows but about ${maxRows} fit; split it or move the full table to an appendix page`);
  const hl = new Set([].concat(page.highlight ?? []).map(Number));
  const body = rows.map((r, i) => r.map((v, j) => cell(v ?? '—', {
    align: align[j], bold: hl.has(i), color: hl.has(i) && align[j] === 'left' && j > 0 ? C.blue : C.ink,
    fill: hl.has(i) ? { color: C.tint } : undefined, border: border(true),
  })));
  const head = colDefs.map((c, j) => cell(c.label, { align: align[j], color: C.ink, fontSize: PT.caption, border: border(true, C.blue, 1.5) }));
  slide.addTable([head, ...body], {
    x: ML, y: a.y + Math.max(0, (a.h - rowH * (rows.length + 1)) / 2) * 0.3, w: CW, colW: weights.map(w => CW * w / sum),
    rowH, fontFace: 'Arial', fontSize: PT.label, color: C.ink, valign: 'middle', margin: [0.04, 0.17, 0.04, 0.17],
  });
}

function compare(slide, page, ctx) {
  const a = area(header(slide, page, ctx), footer(slide, page.footer, ctx));
  const opts = page.options, rows = page.rows;
  if (!Array.isArray(opts) || opts.length < 2 || opts.length > 4) fail('compare needs 2–4 options');
  if (!Array.isArray(rows) || !rows.length || rows.some(r => !str(r.label) || !Array.isArray(r.values) || r.values.length !== opts.length)) fail('every compare row needs a label and one value per option');
  const rec = page.recommended, labelW = 1.83, optW = (CW - labelW) / opts.length;
  const head = [cell(page.rowHeader || '比較項目', { bold: true, fontSize: PT.body, valign: 'top', border: border(true) }),
    ...opts.map((o, j) => ({ text: [{ text: o.label || '', options: { fontSize: PT.caption, breakLine: true } }, { text: o.name || '', options: { fontSize: PT.body, bold: true } }],
      options: { valign: 'top', color: j === rec ? C.white : C.ink, fill: j === rec ? { color: C.blue } : undefined, border: border(true) } }))];
  const body = rows.map(r => [cell(r.label, { color: C.ink, border: border(true) }),
    ...r.values.map((v, j) => cell(v, { fill: j === rec ? { color: C.tint } : undefined, border: border(true) }))]);
  const heights = rows.map(r => Math.max(...[r.label, ...r.values].map((v, j) => lineCount(v, (j ? optW : labelW) - 0.34, PT.label))) * lineHeight(PT.label, 1.45) + 0.17);
  const total = 0.85 + heights.reduce((s, v) => s + v, 0);
  if (total > a.h) warn('compare table overflows; shorten cells or drop rows that do not separate the options');
  slide.addTable([head, ...body], {
    x: ML, y: a.y, w: CW, colW: [labelW, ...opts.map(() => optW)], rowH: [0.85, ...heights],
    fontFace: 'Arial', fontSize: PT.label, color: C.ink, valign: 'top', margin: [0.08, 0.17, 0.08, 0.17], lineSpacingMultiple: 1.45,
  });
}

function decisions(slide, page, ctx) {
  slide.background = { color: C.dark };
  const a = area(header(slide, page, ctx, true), footer(slide, page.footer, ctx, true));
  const items = Array.isArray(page.items) ? page.items : [];
  if (items.length < 1 || items.length > 5) fail('decisions needs 1–5 items');
  const idxW = 0.5, ownW = 2.92, gap = 0.25, hw = CW - idxW - ownW - gap * 2;
  const heights = items.map(it => 0.5 + Math.max(lineCount(it.heading, hw, PT.body) * lineHeight(PT.body, 1.4), (lineCount(it.owner, ownW, PT.label) + (str(it.deadline) ? 1 : 0)) * lineHeight(PT.label) + 0.083));
  const total = heights.reduce((s, v) => s + v, 0);
  if (total > a.h) warn('decision rows overflow; keep each to a short heading, owner and date');
  let y = centre(a, total);
  items.forEach((it, i) => {
    if (!str(it.heading)) fail('every decision needs a heading');
    addText(slide, String(i + 1).padStart(2, '0'), { x: ML, y: y + 0.25, w: idxW, h: 0.3 }, { size: PT.label, color: C.darkMuted });
    addText(slide, it.heading, { x: ML + idxW + gap, y: y + 0.25, w: hw, h: heights[i] - 0.5 }, { size: PT.body, bold: true, color: C.white, lh: 1.4 });
    addText(slide, [...(str(it.owner) ? runs(it.owner, { color: C.darkMuted }) : []), ...(str(it.deadline) ? [{ text: '', options: { breakLine: true } }, { text: it.deadline, options: { color: C.white } }] : [])],
      { x: W - MR - ownW, y: y + 0.25, w: ownW, h: heights[i] - 0.5 }, { size: PT.label });
    y += heights[i];
    rule(slide, ML, y, CW, C.darkLine);
  });
}

const drawers = { cover, chapter, summary, kpi, chart: chartPage, list, columns, process: processPage, flow, table, compare, decisions };

// Post-processing: fonts, theme colours, per-series label colours and real PNG fallbacks for SVG ---------
async function finish(buffer, chartMeta) {
  const JSZip = load('jszip');
  const zip = await JSZip.loadAsync(buffer);
  const files = Object.keys(zip.files);
  const edit = async (name, fn) => zip.file(name, fn(await zip.file(name).async('string')));
  for (const name of files.filter(n => /^ppt\/slides\/slide\d+\.xml$/.test(n))) {
    await edit(name, xml => xml.replace(/<a:ea typeface="Arial"/g, '<a:ea typeface="Microsoft JhengHei"').replace(/<a:ea typeface="Cambria"/g, '<a:ea typeface="PMingLiU"').replace(/ lang="en-US"/g, ' lang="zh-TW" altLang="en-US"'));
  }
  const charts = files.filter(n => /^ppt\/charts\/chart\d+\.xml$/.test(n)).sort((a, b) => Number(a.match(/(\d+)\.xml$/)[1]) - Number(b.match(/(\d+)\.xml$/)[1]));
  for (const [i, name] of charts.entries()) {
    await edit(name, xml => {
      let out = xml.replace(/<a:latin typeface="Arial"\/>/g, '<a:latin typeface="Arial"/><a:ea typeface="Microsoft JhengHei"/>');
      const colors = chartMeta[i];
      if (colors) {
        let k = -1;
        out = out.replace(/<c:ser>[\s\S]*?<\/c:ser>/g, ser => { k += 1; return ser.replace(/(<c:dLbls>[\s\S]*?<a:srgbClr val=")[0-9A-Fa-f]{6}/, `$1${colors[k] || '111111'}`); });
      }
      return out;
    });
  }
  // pptxgenjs writes 0 as an empty workbook cell (`value || ''`), so Edit Data would turn zeros into gaps; restore them from the chart cache.
  for (const name of charts) {
    const rels = zip.file(name.replace('charts/', 'charts/_rels/') + '.rels');
    const target = rels && (await rels.async('string')).match(/Target="\.\.\/(embeddings\/[^"]+\.xlsx)"/);
    if (!target) continue;
    const xml = await zip.file(name).async('string'), zeros = [];
    for (const [, col, row, cache] of xml.matchAll(/<c:numRef><c:f>Sheet1!\$([A-Z]+)\$(\d+)(?::[^<]*)?<\/c:f>\s*<c:numCache>([\s\S]*?)<\/c:numCache>/g)) {
      for (const [, idx] of cache.matchAll(/<c:pt idx="(\d+)"><c:v>0<\/c:v><\/c:pt>/g)) zeros.push(`${col}${Number(row) + Number(idx)}`);
    }
    if (!zeros.length) continue;
    const book = await JSZip.loadAsync(await zip.file(`ppt/${target[1]}`).async('nodebuffer'));
    const sheet = 'xl/worksheets/sheet1.xml';
    book.file(sheet, zeros.reduce((s, ref) => s.replace(`<c r="${ref}"><v></v></c>`, `<c r="${ref}"><v>0</v></c>`), await book.file(sheet).async('string')));
    zip.file(`ppt/${target[1]}`, await book.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' }));
  }
  for (const name of files.filter(n => /^ppt\/theme\/theme\d+\.xml$/.test(n))) {
    await edit(name, xml => xml
      .replace(/<a:ea typeface=""\/>/g, '<a:ea typeface="Microsoft JhengHei"/>')
      .replace(/<a:font script="Hant" typeface="[^"]*"\/>/g, '<a:font script="Hant" typeface="Microsoft JhengHei"/>')
      .replace(/<a:dk2>[\s\S]*?<\/a:dk2>/, '<a:dk2><a:srgbClr val="142979"/></a:dk2>')
      .replace(/<a:accent(\d)><a:srgbClr val="[0-9A-F]{6}"\/><\/a:accent\1>/g, (m, n) => `<a:accent${n}><a:srgbClr val="${['28317B', '04696C', '4A8F5B', 'D09FE2', '7F7F7F', '9DB1D9'][n - 1]}"/></a:accent${n}>`)
      .replace(/<a:hlink>[\s\S]*?<\/a:hlink>/, '<a:hlink><a:srgbClr val="000099"/></a:hlink>'));
  }
  const svgs = files.filter(n => /^ppt\/media\/image-\d+-\d+\.svg$/.test(n));
  if (svgs.length) {
    const { Resvg } = load('@resvg/resvg-js');
    for (const name of svgs) {
      const [, s, k] = name.match(/image-(\d+)-(\d+)\.svg$/);
      const png = `ppt/media/image-${s}-${Number(k) - 1}.png`;
      if (!zip.file(png)) continue;
      const svg = await zip.file(name).async('string');
      const r = new Resvg(svg, { fitTo: { mode: 'width', value: 2400 }, font: { loadSystemFonts: true, defaultFontFamily: 'Arial' }, background: 'white' });
      zip.file(png, r.render().asPng());
    }
  }
  return zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
}

async function build(deck, baseDir = process.cwd()) {
  const PptxGenJS = load('pptxgenjs');
  warnings.length = 0;
  if (!deck || !Array.isArray(deck.pages) || !deck.pages.length) throw new Error('deck needs a nonempty pages array');
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.theme = { headFontFace: 'Arial', bodyFontFace: 'Arial' };
  if (str(deck.title)) pptx.title = deck.title;
  if (str(deck.author)) pptx.author = deck.author;
  const ctx = { source: deck.source, logo: str(deck.logo) ? path.resolve(baseDir, deck.logo) : '', chartMeta: [] };
  let exhibit = 0;
  deck.pages.forEach((page, i) => {
    current = `page ${i + 1}${page && page.layout ? ` (${page.layout})` : ''}`;
    if (!page || !LAYOUTS.includes(page.layout)) fail(`layout must be one of ${LAYOUTS.join(', ')}`);
    const slide = pptx.addSlide();
    slide.background = { color: 'FFFFFF' };
    const isExhibit = page.exhibit ?? EXHIBITS.has(page.layout);
    const pageCtx = Object.assign(ctx, { exhibit: isExhibit ? ++exhibit : 0, folio: page.layout === 'cover' ? '' : String(i + 1).padStart(2, '0') });
    drawers[page.layout](slide, page, pageCtx, pptx);
    if (str(page.speakerNotes)) slide.addNotes(page.speakerNotes);
  });
  const raw = await pptx.write({ outputType: 'nodebuffer' });
  return { buffer: await finish(raw, ctx.chartMeta), warnings: [...warnings] };
}

module.exports = { build, LAYOUTS };
if (require.main === module) {
  const [input, output] = process.argv.slice(2);
  if (!input || !output) { console.error('Usage: node build-deck.js deck.json out.pptx'); process.exit(2); }
  (async () => {
    const deck = JSON.parse(fs.readFileSync(input, 'utf8'));
    const { buffer, warnings: found } = await build(deck, path.dirname(path.resolve(input)));
    fs.writeFileSync(output, buffer);
    for (const w of found) console.error(`WARN ${w}`);
    console.log(`wrote ${output} (${deck.pages.length} pages${found.length ? `, ${found.length} warnings to fix` : ''})`);
  })().catch(error => { console.error(error.message); process.exit(1); });
}
