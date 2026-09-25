'use strict';
const assert = require('node:assert/strict');
const charts = require('../scripts/composition-charts');
const frame = { w: 1200, h: 650, unit: '件', plotTop: 95, plotBottom: 495 };

const waffleData = { data: [{ label: '甲', value: 50 }, { label: '乙', value: 30 }, { label: '丙', value: 20 }] };
const waffle = charts.waffle(waffleData, frame);
assert.equal((waffle.match(/data-unit="1"/g) || []).length, 100, 'waffle renders one cell per percentage point');
assert.throws(() => charts.waffle({ data: [{ label: '甲', value: 99 }, { label: '乙', value: 0 }] }, frame), /totaling 100/);

const comp = { categories: ['A', 'B', 'C'], data: [{ label: '甲', values: [7, 2, 1] }, { label: '乙', values: [2, 3, 5] }] };
const before = JSON.stringify(comp);
const stacked = charts.stacked(comp, frame);
assert.equal(JSON.stringify(comp), before, 'composition renderers do not mutate inputs');
assert((stacked.match(/data-share=/g) || []).length === 6 && stacked.includes('每列＝100%'));
assert(stacked.includes('單位：件') && stacked.includes('70% · 7') && stacked.includes('總量 10') && !stacked.includes('7 件'), 'stacked shares a unit and keeps direct values and one denominator per row');
const narrowStack = charts.stacked({ categories: ['A', 'B', 'C'], data: [{ label: '甲', values: [98, 2, 0] }, { label: '乙', values: [70, 20, 10] }] }, frame);
assert(narrowStack.includes('窄區塊：甲／B 2/100（2%）') && narrowStack.includes('甲／C 0/100（0%）'), 'small and zero stacked segments retain their row denominator');
assert.throws(() => charts.stacked({ categories: ['A', 'B', 'C', 'D', 'E'], data: comp.data }, frame), /Other/);

const mekko = charts.mekko({ categories: ['A', 'B'], data: [{ label: '甲', values: [10, 0] }, { label: '乙', values: [10, 20] }] }, frame);
const cells = [...mekko.matchAll(/<rect[^>]+data-value="([^"]+)"[^>]+data-share="([^"]+)"/g)].map(match => [Number(match[1]), Number(match[2])]);
assert.equal(cells.reduce((area, [value, share]) => area + share, 0), 1, 'mekko cell areas sum to the grand-total share');
assert(mekko.includes('單位：件') && mekko.includes('甲／B 0/10（0%）') && mekko.includes('data-value="0"'), 'mekko shares a unit and keeps zero cells explicit with their denominator');

const paretoInput = { data: [{ label: '中', value: 2 }, { label: '大', value: 5 }, { label: '零', value: 0 }, { label: '小', value: 1 }] };
const paretoBefore = JSON.stringify(paretoInput), pareto = charts.pareto(paretoInput, frame);
assert.equal(JSON.stringify(paretoInput), paretoBefore, 'pareto sorting does not mutate input');
assert(pareto.includes('data-cumulative-line="true"') && pareto.includes('data-cumulative="100"'), 'pareto has connected cumulative line ending at 100%');
assert(pareto.indexOf('data-label="大"') < pareto.indexOf('data-label="中"'), 'pareto bars sort descending');
assert(pareto.includes('x="1107" y="500"') && pareto.includes('>0%</text>'), 'pareto right axis rises from 0% at the bottom');
assert.throws(() => charts.pareto({ data: [{ label: 'A', value: 1.5 }, { label: 'B', value: 1 }, { label: 'C', value: 1 }] }, frame), /integer/);

const indexedSpec = { labels: ['Q1', 'Q2', 'Q3', 'Q4'], data: [{ label: '甲', values: [10, 12, null, 15] }, { label: '乙', values: [20, 18, 22, 24] }] };
const indexed = charts.indexed(indexedSpec, frame);
const firstPath = indexed.match(/<path d="([^"]+)"[^>]+data-series="甲"/)[1];
assert.equal((firstPath.match(/M/g) || []).length, 2, 'null values split indexed paths');
assert(indexed.includes('data-original="10"') && indexed.includes('data-original-values="10,12,null,15"'), 'indexed preserves original observations');
assert((indexed.match(/stroke-dasharray="5 4"/g) || []).length >= 2, 'each panel draws the same 100 baseline');
assert((indexed.match(/>Q3</g) || []).length === 2 && indexed.includes('共用規律指數尺度 80–160'), 'missing values do not remove period labels and scale is disclosed');
const focusedIndexed = charts.indexed({ ...indexedSpec, focus: '甲' }, frame);
assert(focusedIndexed.includes('data-series="甲"') && focusedIndexed.includes('stroke="#28317B"') && focusedIndexed.includes('data-series="乙"') && focusedIndexed.includes('stroke="#7F7F7F"'), 'optional focus highlights one indexed series while keeping the others readable');
assert.throws(() => charts.indexed({ ...indexedSpec, focus: '不存在' }, frame), /focus must match/);
const negativeIndexed = charts.indexed({ labels: ['Q1', 'Q2', 'Q3'], data: [{ label: '甲', values: [10, -2, 8] }, { label: '乙', values: [10, 5, 12] }] }, frame);
assert(negativeIndexed.includes('>-'), 'regular indexed ticks retain negative observations when supplied');
const documentFrame = { ...frame, w: 840, h: 720, plotTop: 110, plotBottom: 540 };
assert.doesNotThrow(() => charts.stacked(comp, documentFrame));
assert.doesNotThrow(() => charts.mekko({ categories: ['A', 'B'], data: [{ label: '甲', values: [10, 20] }, { label: '乙', values: [15, 15] }] }, documentFrame));
assert.throws(() => charts.indexed({ labels: ['A', 'B', 'C'], data: [{ label: '甲', values: [0, 1, 2] }, { label: '乙', values: [1, 2, 3] }] }, frame), /positive base/);
console.log('composition charts preserve data, area, cumulative and missing-value semantics');
