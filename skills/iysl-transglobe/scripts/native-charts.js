'use strict';
// Native, editable PowerPoint charts for the chart families PowerPoint draws well.
// Each builder takes the same spec as render-chart.js; anything not listed here is embedded as SVG.
const U = require('./chart-utils');

const T = {
  ink: '111111', muted: '4A4A4A', grid: 'E3E3E6', axis: 'BFBFBF', blue: '28317B', gray: '7F7F7F',
  seq: ['D1DDF7', '9DB1D9', '7285BB', '4B5A9C', '28317B'],
  cat: ['28317B', '04696C', '4A8F5B', 'D09FE2'], other: 'DDDDDD',
};
const LABEL_PT = 15, AXIS_PT = 13.5;
const NATIVE = ['ranking', 'ordered', 'trend', 'tracking', 'grouped', 'stacked', 'sharetrend', 'combo'];

const fail = message => { throw new Error(`iysl-transglobe native chart: ${message}`); };
const isNum = v => typeof v === 'number' && Number.isFinite(v);
const text = v => typeof v === 'string' && v.trim();

function decimals(values) {
  return Math.min(3, Math.max(0, ...values.filter(isNum).map(v => {
    const [m, e = '0'] = String(v).split('e');
    return Math.max(0, (m.split('.')[1]?.length || 0) - Number(e));
  })));
}
// Keep source precision in labels; show an explicit plus sign when the data mixes signs.
function numberFormat(values, signed = values.some(v => isNum(v) && v < 0)) {
  const d = decimals(values), body = '#,##0' + (d ? '.' + '0'.repeat(d) : '');
  return signed ? `+${body};"−"${body};0` : body;
}

function rowsOf(spec, min = 1, max = 12) {
  const data = spec.data;
  if (!Array.isArray(data) || data.length < min || data.length > max) fail(`${spec.chart} needs ${min}–${max} rows`);
  if (data.some(r => !r || !text(r.label))) fail('every row needs a label');
  if (new Set(data.map(r => r.label)).size !== data.length) fail('row labels must be unique');
  return data;
}

function categoryColors(spec, names) {
  const domain = spec.categoryDomain || names;
  return names.map(name => {
    if (name === '其他' || name === 'Other') return T.other;
    const i = domain.filter(n => n !== '其他' && n !== 'Other').indexOf(name);
    if (i < 0) fail(`category ${name} is not in categoryDomain`);
    if (i > 3) fail('more than four named categories: split the chart, use a table, or keep the source\'s existing 其他/Other');
    return T.cat[i];
  });
}
// White labels on the two darkest categorical fills, ink elsewhere (matches chart-utils catText).
const labelOn = fill => ['28317B', '04696C', '4A8F5B'].includes(fill) ? 'FFFFFF' : T.ink;

const base = (box) => ({
  x: box.x, y: box.y, w: box.w, h: box.h,
  fontFace: 'Arial', catAxisLabelFontFace: 'Arial', valAxisLabelFontFace: 'Arial', dataLabelFontFace: 'Arial', legendFontFace: 'Arial',
  catAxisLabelFontSize: LABEL_PT, catAxisLabelColor: T.ink, valAxisLabelFontSize: AXIS_PT, valAxisLabelColor: T.muted,
  dataLabelFontSize: LABEL_PT, dataLabelColor: T.ink, legendFontSize: AXIS_PT, legendColor: T.ink,
  catAxisLineShow: true, catAxisLineColor: T.axis, valAxisLineShow: false,
  valGridLine: { color: T.grid, size: 0.75 }, catGridLine: { style: 'none' },
  plotArea: { fill: { color: 'FFFFFF' } }, showTitle: false, showLegend: false,
});

function bars(spec, box, ordered) {
  const data = rowsOf(spec, 1, 12);
  if (data.some(r => r.value !== null && !isNum(r.value))) fail('values must be numbers or null');
  if (spec.focus !== undefined && !data.some(r => r.label === spec.focus)) fail('focus must match a row label');
  const rows = ordered ? data : [...data].sort((a, b) => a.value === null ? 1 : b.value === null ? -1 : b.value - a.value);
  const values = rows.map(r => r.value), seen = values.filter(isNum);
  const lo = Math.min(...seen), hi = Math.max(...seen);
  const colors = rows.map(r => ordered ? T.seq[1 + Math.round((r.value - lo) / (hi - lo || 1) * 3)] : spec.focus === undefined || r.label === spec.focus ? T.blue : T.gray);
  const opts = {
    ...base(box), barDir: 'bar', barGapWidthPct: rows.length <= 4 ? 150 : 90, catAxisOrientation: 'maxMin', catAxisLabelPos: 'low',
    valAxisHidden: true, valGridLine: { style: 'none' }, chartColors: colors, invertedColors: colors,
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: numberFormat(values),
  };
  return { type: 'bar', data: [{ name: spec.unit, labels: rows.map(r => r.label), values }], opts, missing: rows.filter(r => r.value === null).map(r => r.label) };
}

function lines(spec, box) {
  const data = rowsOf(spec, 1, 6), labels = spec.labels;
  if (!Array.isArray(labels) || labels.length < 2 || labels.some(l => !text(l))) fail('trend needs labels for every period');
  if (data.some(r => !Array.isArray(r.values) || r.values.length !== labels.length || r.values.some(v => v !== null && !isNum(v)))) fail('each series needs one number or null per period');
  const tracking = spec.chart === 'tracking' || (spec.focus === undefined && data.length > 1);
  if (spec.focus !== undefined && !data.some(r => r.label === spec.focus)) fail('focus must match a series label');
  const all = data.flatMap(r => r.values).filter(isNum);
  const [lo, hi] = spec.yDomain || [Math.min(0, ...all), Math.max(0, ...all)];
  if (all.some(v => v < lo || v > hi)) fail('yDomain must cover every observed value');
  // Same nice range as the SVG renderer: zero included unless yDomain says otherwise, about four steps.
  const [niceLo, niceHi] = spec.yDomain ? [lo, hi] : U.extent(all), step = U.niceStep(niceHi - niceLo);
  const colors = tracking ? categoryColors(spec, data.map(r => r.label)) : data.map(r => spec.focus === undefined || r.label === spec.focus ? T.blue : T.gray);
  const dashes = ['solid', 'dash', 'sysDot', 'lgDashDot'], symbols = ['circle', 'square', 'triangle', 'diamond'];
  const format = numberFormat(all, false);
  // One chart part per series so focus, dash and labels can differ by series.
  const parts = data.map((r, i) => {
    const isFocus = !tracking && (spec.focus === undefined || r.label === spec.focus);
    return {
      type: 'line', data: [{ name: r.label, labels, values: r.values }],
      options: {
        chartColors: [colors[i]], lineSize: isFocus ? 3 : 2, lineDash: tracking || isFocus ? 'solid' : dashes[(i % 3) + 1],
        lineDataSymbol: tracking ? symbols[i % 4] : 'circle', lineDataSymbolSize: isFocus ? 8 : 6,
        lineDataSymbolLineColor: colors[i], showValue: isFocus || data.length === 1, dataLabelPosition: 't',
        dataLabelFormatCode: format, dataLabelColor: isFocus ? T.blue : T.ink, dataLabelFontBold: isFocus,
      },
    };
  });
  const opts = {
    ...base(box), displayBlanksAs: 'gap', valAxisMinVal: niceLo, valAxisMaxVal: niceHi, valAxisMajorUnit: step, valAxisLabelFormatCode: format,
    showLegend: data.length > 1, legendPos: 't',
  };
  return { type: 'multi', parts, opts };
}

function grouped(spec, box) {
  const series = spec.series, data = rowsOf(spec, 1, 8);
  if (!Array.isArray(series) || series.length < 2 || series.length > 4 || new Set(series).size !== series.length) fail('grouped needs 2–4 unique series names');
  if (data.some(r => !Array.isArray(r.values) || r.values.length !== series.length || r.values.some(v => v !== null && !isNum(v)))) fail('grouped rows need one number or null per series');
  const colors = categoryColors(spec, series), all = data.flatMap(r => r.values);
  const opts = {
    ...base(box), barDir: 'col', barGrouping: 'clustered', barGapWidthPct: 60, chartColors: colors,
    valAxisHidden: true, valGridLine: { style: 'none' }, showValue: true, dataLabelPosition: 'outEnd',
    dataLabelFontSize: AXIS_PT, dataLabelFormatCode: numberFormat(all), showLegend: true, legendPos: 't',
  };
  return { type: 'bar', data: series.map((name, j) => ({ name, labels: data.map(r => r.label), values: data.map(r => r.values[j]) })), opts };
}

function composition(spec, box) {
  if (!Array.isArray(spec.categories) || spec.categories.length < 2 || spec.categories.length > 5) fail('composition needs 2–4 categories (plus an existing 其他/Other)');
  const data = rowsOf(spec, spec.chart === 'sharetrend' ? 2 : 1, 12);
  if (data.some(r => !Array.isArray(r.values) || r.values.length !== spec.categories.length || r.values.some(v => !isNum(v) || v < 0))) fail('composition rows need one nonnegative number per category');
  if (data.some(r => U.sum(r.values) <= 0)) fail('every composition row needs a positive total');
  const colors = categoryColors(spec, spec.categories);
  // Plot shares so labels read as %, while the footer keeps the raw totals.
  const shares = data.map(r => r.values.map(v => U.percent(v, U.sum(r.values))));
  const bar = spec.chart === 'stacked';
  const opts = {
    ...base(box), barDir: bar ? 'bar' : 'col', barGrouping: 'percentStacked', barGapWidthPct: bar ? 60 : 50,
    catAxisOrientation: bar ? 'maxMin' : 'minMax', chartColors: colors, valAxisHidden: true, valGridLine: { style: 'none' },
    showValue: true, dataLabelPosition: 'ctr', dataLabelFormatCode: '0.0"%"', showLegend: true, legendPos: 't',
  };
  const totals = data.map(r => `${r.label} 合計 ${U.num(U.sum(r.values))}`).join('；');
  return {
    type: 'bar', opts, labelColors: colors.map(labelOn), extraFooter: [`每列＝100%；${totals} ${spec.unit}`],
    data: spec.categories.map((name, j) => ({ name, labels: data.map(r => r.label), values: shares.map(row => Number(row[j].toFixed(3))) })),
  };
}

function combo(spec, box) {
  const data = rowsOf(spec, 2, 12);
  if (!text(spec.rateLabel)) fail('combo needs rateLabel with its unit');
  if (data.some(r => (r.value !== null && !isNum(r.value)) || (r.rate !== null && !isNum(r.rate)))) fail('combo rows need numeric or null value and rate');
  const labels = data.map(r => r.label), values = data.map(r => r.value), rates = data.map(r => r.rate);
  const parts = [
    { type: 'bar', data: [{ name: spec.unit, labels, values }], options: { barDir: 'col', chartColors: [T.seq[1]], barGapWidthPct: 60, showValue: true, dataLabelPosition: 'inEnd', dataLabelFormatCode: numberFormat(values), dataLabelFontSize: AXIS_PT } },
    { type: 'line', data: [{ name: spec.rateLabel, labels, values: rates }], options: { chartColors: [T.blue], lineSize: 3, lineDataSymbol: 'circle', lineDataSymbolSize: 8, secondaryValAxis: true, secondaryCatAxis: true, showValue: true, dataLabelPosition: 't', dataLabelFormatCode: numberFormat(rates), dataLabelColor: T.blue, dataLabelFontBold: true } },
  ];
  const opts = {
    ...base(box), displayBlanksAs: 'gap', showLegend: true, legendPos: 't',
    valAxes: [{ showValAxisTitle: true, valAxisTitle: spec.unit, valAxisTitleFontSize: AXIS_PT, valAxisTitleColor: T.muted, valGridLine: { style: 'none' }, valAxisLabelFontSize: AXIS_PT, valAxisLabelColor: T.muted, valAxisLabelFormatCode: numberFormat(values, false) },
      { showValAxisTitle: true, valAxisTitle: spec.rateLabel, valAxisTitleFontSize: AXIS_PT, valAxisTitleColor: T.blue, valGridLine: { style: 'none' }, valAxisLabelFontSize: AXIS_PT, valAxisLabelColor: T.blue, valAxisLabelFormatCode: numberFormat(rates, false) }],
    catAxes: [{ catAxisTitle: '', catAxisLabelFontSize: LABEL_PT, catAxisLabelColor: T.ink }, { catAxisHidden: true }],
  };
  return { type: 'multi', parts, opts, extraFooter: ['柱讀左軸、線讀右軸；兩軸尺度獨立，不比較高度'] };
}

const builders = {
  ranking: (s, b) => bars(s, b, false), ordered: (s, b) => bars(s, b, true),
  trend: lines, tracking: lines, grouped, stacked: composition, sharetrend: composition, combo,
};

// Plan first (validates data and yields footer lines), then place once the slide knows the chart box.
function planNativeChart(spec) {
  const build = builders[spec.chart];
  if (!build) return null;
  const chart = build(spec, { x: 0, y: 0, w: 1, h: 1 });
  const extraFooter = [...(chart.extraFooter || [])];
  if (chart.missing?.length) extraFooter.push(`未提供：${chart.missing.join('、')}`);
  return { chart, extraFooter, labelColors: chart.labelColors || null };
}

function addPlannedChart(pptx, slide, plan, box) {
  const { chart } = plan, opts = { ...chart.opts, x: box.x, y: box.y, w: box.w, h: box.h };
  if (chart.type === 'multi') slide.addChart(chart.parts.map(p => ({ type: pptx.ChartType[p.type], data: p.data, options: p.options })), opts);
  else slide.addChart(pptx.ChartType[chart.type], chart.data, opts);
}

module.exports = { planNativeChart, addPlannedChart, NATIVE, T };
