#!/usr/bin/env node
'use strict';
// Builds the prototype deck and the all-layouts fixture, then checks the PPTX package itself:
// native charts and tables stay editable, SVG charts carry a real PNG fallback, fonts and notes are set.
const assert = require('node:assert/strict');
const path = require('node:path');
const { build } = require('../scripts/build-deck');
const { render } = require('../scripts/render-chart');
const JSZip = require('../scripts/node_modules/jszip');

const root = path.join(__dirname, '..');
const read = name => require(path.join(root, name));
const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47]);

async function unpack(deck) {
  const { buffer, warnings } = await build(deck, root);
  const zip = await JSZip.loadAsync(buffer);
  const names = Object.keys(zip.files);
  const text = async name => zip.file(name).async('string');
  return { zip, names, text, warnings };
}

(async () => {
  // Prototype deck: nine pages, two native charts, two native tables, no SVG needed.
  const example = await unpack(read('assets/example-deck.json'));
  const slides = example.names.filter(n => /^ppt\/slides\/slide\d+\.xml$/.test(n));
  assert.equal(slides.length, 9);
  assert.equal(example.names.filter(n => /^ppt\/charts\/chart\d+\.xml$/.test(n)).length, 2, 'ranking and trend are native charts');
  assert.equal(example.names.filter(n => /^ppt\/media\/.*\.svg$/.test(n)).length, 0);
  assert.deepEqual(example.warnings, []);
  let tables = 0;
  for (const name of slides) {
    const xml = await example.text(name);
    assert.ok(!xml.includes('<a:ea typeface="Arial"'), `${name} keeps Latin font as East Asian font`);
    if (xml.includes('<a:tbl>')) tables += 1;
  }
  assert.equal(tables, 2, 'market table and plan comparison are native tables');
  const cover = await example.text('ppt/slides/slide1.xml');
  assert.ok(cover.includes('<a:ea typeface="PMingLiU"'), 'cover title uses the display serif for Chinese');
  const theme = await example.text('ppt/theme/theme1.xml');
  assert.ok(theme.includes('<a:ea typeface="Microsoft JhengHei"/>') && theme.includes('<a:accent1><a:srgbClr val="28317B"/>'));
  const chart1 = await example.text(example.names.find(n => /^ppt\/charts\/chart\d+\.xml$/.test(n)));
  assert.ok(chart1.includes('28317B') && chart1.includes('7F7F7F'), 'focus bar blue, context bars gray');
  assert.ok(example.names.some(n => /^ppt\/embeddings\/.*\.xlsx$/.test(n)), 'native charts embed editable data');

  // All layouts and both chart paths.
  const all = await unpack(read('tests/fixtures/all-layouts-deck.json'));
  const svgs = all.names.filter(n => /^ppt\/media\/image-\d+-\d+\.svg$/.test(n));
  assert.equal(svgs.length, 3, 'waterfall, dumbbell and mekko embed as SVG');
  for (const svg of svgs) {
    const [, s, k] = svg.match(/image-(\d+)-(\d+)\.svg$/);
    const png = await all.zip.file(`ppt/media/image-${s}-${Number(k) - 1}.png`).async('nodebuffer');
    assert.ok(png.subarray(0, 4).equals(PNG) && png.length > 20000, `${svg} has a rendered PNG fallback`);
    const slide = await all.text(`ppt/slides/slide${s}.xml`);
    assert.ok(slide.includes('asvg:svgBlip') && /descr="[^"]+"/.test(slide), 'SVG extension and alt text are present');
    assert.ok(!(await all.zip.file(svg).async('string')).includes('資料來源'), 'bare SVG leaves the source to the slide footer');
  }
  // pptxgenjs numbers charts with a process-wide counter, so order by number rather than assuming chart1.
  const charts = all.names.filter(n => /^ppt\/charts\/chart\d+\.xml$/.test(n)).sort((a, b) => Number(a.match(/(\d+)\.xml$/)[1]) - Number(b.match(/(\d+)\.xml$/)[1]));
  assert.equal(charts.length, 4, 'stacked, grouped, tracking and combo are native');
  const stacked = await all.text(charts[0]);
  assert.ok(stacked.includes('percentStacked') && stacked.includes('FFFFFF'), 'composition labels are white on dark fills');
  const notes = all.names.filter(n => /^ppt\/notesSlides\/.*\.xml$/.test(n));
  const noteText = (await Promise.all(notes.map(n => all.text(n)))).join('');
  assert.ok(noteText.includes('三項設計重點'), 'speaker notes are written');
  const tracking = await all.text(charts[2]);
  assert.ok(tracking.includes('dispBlanksAs val="gap"'), 'missing values break the line');
  const trackingSlide = await all.text('ppt/slides/slide7.xml');
  assert.ok(trackingSlide.includes('未提供：業務員／2024'), 'missing value is named in the footer');

  // Guard rails report the page, and soft problems become warnings rather than refusals.
  await assert.rejects(build({ pages: [{ layout: 'poster', title: 'x' }] }), /page 1 \(poster\).*layout must be one of/);
  await assert.rejects(build({ pages: [{ layout: 'chart', title: '缺來源', chart: { chart: 'ranking', unit: '%', period: '2026', data: [{ label: 'A', value: 1 }] } }] }), /chart needs source/);
  const long = await build({ source: 's', pages: [{ layout: 'columns', title: '這是一個非常非常長的標題，' .repeat(6), items: [{ heading: 'A' }, { heading: 'B' }] }] });
  assert.ok(long.warnings.some(w => w.includes('title wraps')), 'long titles are flagged');
  const many = await build({ pages: [{ layout: 'process', title: 't', steps: Array.from({ length: 7 }, (_, i) => ({ heading: `S${i}` })) }] });
  assert.ok(many.warnings.some(w => w.includes('7 steps')), 'item counts outside the usual range warn instead of refusing');
  const dense = await build({ source: 's', pages: [{ layout: 'chart', title: 't', chart: { chart: 'ranking', unit: '%', period: 'p', data: Array.from({ length: 16 }, (_, i) => ({ label: `L${i}`, value: i })) } }] });
  assert.ok(dense.warnings.some(w => w.includes('dense') && w.includes('ranking')), 'chart legibility warnings reach the build output');
  // Native ranking does not require a focus; without one all bars share the focus blue.
  const nofocus = await build({ source: 's', pages: [{ layout: 'chart', title: 't', chart: { chart: 'ranking', unit: '%', period: 'p', data: [{ label: 'A', value: 2 }, { label: 'B', value: 1 }] } }] });
  assert.deepEqual(nofocus.warnings, []);
  // A missing value in an ordered chart still gets a valid colour (no val="undefined" in the chart XML).
  const gap = await JSZip.loadAsync((await build({ source: 's', pages: [{ layout: 'chart', title: 't', chart: { chart: 'ordered', unit: '%', period: 'p', data: [{ label: 'A', value: 10 }, { label: 'B', value: null }, { label: 'C', value: 20 }] } }] })).buffer);
  const gapChart = await gap.file(Object.keys(gap.files).find(n => /^ppt\/charts\/chart\d+\.xml$/.test(n))).async('string');
  assert.ok(!gapChart.includes('undefined'), 'ordered chart with a null value writes only valid colours');
  // Zeros survive into the editable workbook (pptxgenjs writes them as empty cells); grouped gaps are named in the footer.
  const zero = await JSZip.loadAsync((await build({ source: 's', pages: [{ layout: 'chart', title: 't', chart: { chart: 'grouped', unit: '%', period: 'p', series: ['x', 'y'], data: [{ label: 'A', values: [0, null] }, { label: 'B', values: [2, 3] }] } }] })).buffer);
  const book = await JSZip.loadAsync(await zero.file(Object.keys(zero.files).find(n => /^ppt\/embeddings\/.*\.xlsx$/.test(n))).async('nodebuffer'));
  const sheet = await book.file('xl/worksheets/sheet1.xml').async('string');
  assert.ok(sheet.includes('<c r="B2"><v>0</v></c>') && sheet.includes('<c r="C2"><v></v></c>'), 'workbook keeps 0 and leaves null blank');
  assert.ok((await zero.file('ppt/slides/slide1.xml').async('string')).includes('未提供：A／y'), 'grouped missing value is named');
  // Text decks: the deck source fills pages without a footer, and only data pages are numbered as exhibits by default.
  const text = await JSZip.loadAsync((await build({ source: '原文', pages: [
    { layout: 'list', title: 't', items: [{ heading: 'A' }, { heading: 'B' }] },
    { layout: 'list', title: 't', exhibit: true, footer: ['自訂頁尾'], items: [{ heading: 'A' }, { heading: 'B' }] },
  ] })).buffer);
  const [plain, numbered] = await Promise.all([1, 2].map(n => text.file(`ppt/slides/slide${n}.xml`).async('string')));
  assert.ok(plain.includes('資料來源：原文') && !plain.includes('EXHIBIT'), 'deck source becomes the default footer; lists are not auto-numbered');
  assert.ok(numbered.includes('EXHIBIT 1') && numbered.includes('自訂頁尾') && !numbered.includes('資料來源：原文'), 'opt-in exhibit and own footer win');
  // A source already written with its 資料來源 prefix is not prefixed twice.
  const prefixed = await JSZip.loadAsync((await build({ source: '資料來源：原文', pages: [{ layout: 'list', title: 't', items: [{ heading: 'A' }, { heading: 'B' }] }] })).buffer);
  const prefixedXml = await prefixed.file('ppt/slides/slide1.xml').async('string');
  assert.ok(prefixedXml.includes('資料來源：原文') && !prefixedXml.includes('資料來源：資料來源'), 'source prefix appears once');
  // highlight accepts a single row index as well as an array.
  const hl = await JSZip.loadAsync((await build({ pages: [{ layout: 'table', title: 't', columns: ['a', 'b'], rows: [['x', '1'], ['y', '2']], highlight: 1 }] })).buffer);
  assert.ok((await hl.file('ppt/slides/slide1.xml').async('string')).includes('F6F6FA'), 'single highlight index tints its row');

  // render(spec, { bare: true }) keeps metadata and description but drops title and footer chrome.
  const spec = read('assets/chart-examples.json').charts.waterfall;
  const bare = render({ ...spec, layout: 'slide', width: 960, height: 420, placementWidthInches: 12 }, { bare: true });
  assert.ok(bare.includes('<metadata>') && bare.includes('<desc') && !bare.includes('資料來源'));
  console.log('build-deck tests passed');
})().catch(error => { console.error(error); process.exit(1); });
