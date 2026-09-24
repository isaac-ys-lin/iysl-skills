'use strict';
const assert = require('node:assert/strict');
const charts = require('../scripts/basic-charts');
const frame = { w: 1200, h: 700, unit: '百萬元' };
const data = [{ label: '海外', value: null }, { label: '南區', value: -12 }, { label: '中區', value: 0 }, { label: '北區', value: 75 }];
const spec = { data, focus: '北區' };
const before = JSON.stringify(spec);
const ranking = charts.ranking(spec, frame);
assert.equal(JSON.stringify(spec), before, 'sorting must not mutate the input');
assert(ranking.includes('未提供') && ranking.includes('data-value="-12"') && ranking.includes('data-value="0"'));
assert(ranking.indexOf('>北區<') < ranking.indexOf('>南區<'), 'observed rows sorted by value');
assert(!ranking.includes('#9D2324'), 'negative values do not imply risk status');
const bars = [...ranking.matchAll(/<rect[^>]+>/g)].map(m => m[0]);
assert.equal(bars.length, 3, 'missing value has no fake bar');
assert.equal(bars.filter(x => x.includes('#28317B')).length, 1);
assert(bars.every(x => !/width="-/.test(x)), 'signed data must not create negative widths');
assert.throws(() => charts.ranking({ data }, frame), /focus/);
assert.throws(() => charts.ranking({ data: [{ label: 'A', value: 1 }, { label: 'A', value: 2 }], focus: 'A' }, frame), /unique/);

const ordered = charts.ordered({ data: [{ label: '先', value: 9 }, { label: '後', value: 2 }] }, frame);
assert(ordered.indexOf('>先<') < ordered.indexOf('>後<'), 'ordered keeps declared order');
assert(ordered.includes('#D1DDF7') && ordered.includes('#28317B'), 'ordered intensity uses the blue ramp');

const bullet = charts.bullet({ data: [{ label: '甲', actual: -2, target: 3 }, { label: '乙', actual: 5, target: 4 }] }, frame);
assert(bullet.includes('data-actual="-2"') && bullet.includes('data-target="4"'));
assert(!/width="-/.test(bullet));
assert(bullet.includes('實際 / 目標'));

const heatmap = charts.heatmap({ labels: ['Q1', 'Q2'], data: [{ label: '醫療', values: [0, null] }, { label: '意外', values: [4, 8] }] }, frame);
assert(heatmap.includes('data-value="0"') && heatmap.includes('data-value="null"') && heatmap.includes('未提供'));
assert.throws(() => charts.heatmap({ data: [{ label: 'A', values: [1, 2] }], labels: ['Q1'] }, frame), /labels/);

const series = { labels: ['Q1', 'Q2', 'Q3'], focus: '主角', data: [{ label: '主角', values: [1, null, 3] }, { label: '同業', values: [2, 3, 4] }] };
const trend = charts.trend(series, frame);
const main = trend.match(/<path d="([^"]+)"[^>]+data-series="主角"/)[1];
assert.equal((main.match(/M/g) || []).length, 2, 'null breaks the path');
assert.equal((main.match(/L/g) || []).length, 0, 'no connecting line across missing time');
const tracking = charts.tracking(series, frame);
assert(tracking.includes('#04696C') && tracking.includes('stroke-dasharray="10 5"'), 'identity uses both categorical colors and line styles');
assert.throws(() => charts.tracking({ ...series, data: Array.from({ length: 5 }, (_, i) => ({ label: String(i), values: [1, 2, 3] })) }, frame), /1–4/);
console.log('basic chart data, encoding, and missing-value checks passed');
