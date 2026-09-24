'use strict';

const assert = require('assert');
const { scatter, box, matrix } = require('../scripts/statistical-charts');
const m = { w: 900, h: 600, unit: '天', plotTop: 96, plotBottom: 445 };
const copy = value => JSON.parse(JSON.stringify(value));

const scatterSpec = { data: [{ label: '甲', x: -3, y: 0 }, { label: '乙', x: 2, y: 4 }, { label: '丙', x: 8, y: -5 }], xLabel: '投入（小時）', yLabel: '滿意度（分）', focus: '乙' };
const scatterBefore = copy(scatterSpec), scatterSvg = scatter(scatterSpec, m);
assert(scatterSvg.includes('data-baseline="0"') && scatterSvg.includes('data-label="乙"') && scatterSvg.includes('甲 (-3, 0)') && !scatterSvg.includes('NaN'));
assert.deepStrictEqual(scatterSpec, scatterBefore);
assert.throws(() => scatter({ ...scatterSpec, data: [{ label: '甲', x: 1, y: 1 }, { label: '乙', x: 1, y: 1 }, { label: '丙', x: 2, y: 2 }] }, m), /overlap/);
assert.throws(() => scatter({ ...scatterSpec, data: [...scatterSpec.data, { label: '丁', x: 10, y: 10 }, { label: '戊', x: 12, y: 12 }, { label: '己', x: 14, y: 14 }, { label: '庚', x: 16, y: 16 }] }, m), /3–6 rows/);

const boxSpec = { data: [{ label: '甲', low: 1, q1: 2, median: 3, q3: 4, high: 5, whiskerRule: '1.5IQR', outliers: [8] }, { label: '乙', low: 2, q1: 3, median: 4, q3: 5, high: 6, whiskerRule: '1.5IQR', outliers: [] }], focus: '甲' };
const boxBefore = copy(boxSpec), boxSvg = box(boxSpec, m);
assert(boxSvg.includes('data-median="3"') && boxSvg.includes('data-outlier="8"') && !boxSvg.includes('NaN'));
assert.deepStrictEqual(boxSpec, boxBefore);
assert.throws(() => box({ data: [{ label: '壞資料', low: 1, q1: 2, median: 3, q3: 4, high: 8, whiskerRule: '1.5IQR', outliers: [] }, boxSpec.data[1]] }, m), /violates/);
assert.throws(() => box({ data: [{ ...boxSpec.data[0], outliers: [8, 9, 10, 11, 12] }, boxSpec.data[1]] }, m), /at most 4/);

const matrixSpec = { data: [{ label: '甲案', x: -2, y: 12 }, { label: '乙案', x: 6, y: 4 }], xLabel: '執行成本（百萬元）', yLabel: '預期影響（分）', xDomain: [-5, 10], yDomain: [0, 15], xThreshold: 3, yThreshold: 8, rubric: '成本與影響依 2026 年核定評分表。', focus: '甲案' };
const matrixBefore = copy(matrixSpec), matrixSvg = matrix(matrixSpec, m);
assert(matrixSvg.includes('data-x-threshold="3"') && matrixSvg.includes('data-y-threshold="8"') && !matrixSvg.includes('評分依據') && !matrixSvg.includes('NaN'));
assert.deepStrictEqual(matrixSpec, matrixBefore);
assert.throws(() => matrix({ ...matrixSpec, xDomain: [5, 5] }, m), /xDomain/);
assert.throws(() => matrix({ ...matrixSpec, xThreshold: -5 }, m), /strictly inside/);

console.log('statistical charts validated');
