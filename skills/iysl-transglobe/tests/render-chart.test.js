'use strict';
const assert=require('assert'),{render,chartTypes}=require('../scripts/render-chart');
const common={title:'測試圖',unit:'件',period:'2026 Q1',source:'測試資料',notes:[]};
const specs={ranking:{data:[{label:'甲',value:4},{label:'乙',value:-2}]},bullet:{data:[{label:'甲',actual:4,target:5},{label:'乙',actual:2,target:3}]},ordered:{data:[{label:'低',value:1},{label:'高',value:4}]},heatmap:{data:[{label:'甲',values:[1,2]},{label:'乙',values:[3,4]}]},trend:{data:[{label:'甲',values:[1,null,3]},{label:'乙',values:[2,3,4]}]},tracking:{data:[{label:'甲',values:[1,2]},{label:'乙',values:[2,1]}]},waterfall:{start:10,end:11,data:[{label:'增加',value:3},{label:'減少',value:-2}]},dumbbell:{data:[{label:'甲',before:3,after:4},{label:'乙',before:5,after:2}]},scatter:{data:[{label:'甲',x:2,y:3},{label:'乙',x:4,y:1},{label:'丙',x:1,y:5}]},box:{data:[{label:'甲',low:1,q1:2,median:3,q3:4,high:5,whiskerRule:'1.5IQR',outliers:[]},{label:'乙',low:1,q1:3,median:4,q3:5,high:6,whiskerRule:'1.5IQR',outliers:[]}]},funnel:{data:[{label:'接觸',value:100},{label:'成交',value:30}]},waffle:{data:[{label:'甲',value:60},{label:'乙',value:40}]},stacked:{categories:['A','B'],data:[{label:'甲',values:[3,7]},{label:'乙',values:[5,5]}]},indexed:{data:[{label:'甲',values:[10,12,15]},{label:'乙',values:[20,19,23]}]},pareto:{data:[{label:'甲',value:4},{label:'乙',value:2},{label:'丙',value:1}]},tornado:{baseline:0,model:'單因子結果',assumptions:['其他條件固定'],data:[{label:'甲',low:-2,high:3},{label:'乙',low:-1,high:1}]},mekko:{categories:['A','B'],data:[{label:'甲',values:[3,7]},{label:'乙',values:[5,5]}]},matrix:{data:[{label:'甲',x:2,y:4},{label:'乙',x:4,y:2}]},table:{data:[{label:'甲',value:1},{label:'乙',value:2}]},grouped:{series:['今年','去年'],data:[{label:'甲',values:[3,-1]},{label:'乙',values:[null,2]}]},combo:{rateLabel:'增率（%）',data:[{label:'P1',value:10,rate:null},{label:'P2',value:12,rate:20}]},histogram:{binWidth:1,data:[0,1,1,2,2,2,3,3,4,5]},sharetrend:{categories:['A','B'],data:[{label:'P1',values:[3,7]},{label:'P2',values:[5,5]}]}};
assert.deepStrictEqual(Object.keys(specs).sort(),chartTypes.sort());
function valid(chart,part){const spec={...common,chart,...part};if(['ranking','trend'].includes(chart))spec.focus=spec.data[0].label;if(['heatmap','trend','tracking','indexed'].includes(chart))spec.labels=spec.data[0].values.map((_,i)=>`P${i+1}`);if(chart==='funnel')spec.sameCohort=true;if(chart==='scatter')Object.assign(spec,{xLabel:'投入（小時）',yLabel:'成果（分）'});if(chart==='matrix')Object.assign(spec,{xLabel:'難度（分）',yLabel:'影響（分）',xDomain:[1,5],yDomain:[1,5],xThreshold:3,yThreshold:3,rubric:'來源定義的 1–5 分量表'});return spec;}
for(const [chart,part] of Object.entries(specs)){const svg=render(valid(chart,part));assert(svg.includes('<svg')&&svg.includes('測試圖')&&!svg.includes('NaN'));}
assert.throws(()=>render({...common,chart:'waffle',data:[{label:'x',value:1},{label:'y',value:1}]}),/totaling 100/);
assert.throws(()=>render({...common,chart:'waterfall',start:1,end:9,data:[{label:'x',value:1}]}),/does not equal/);
assert.throws(()=>render({...common,chart:'funnel',sameCohort:true,data:[{label:'x',value:1.5},{label:'y',value:1}]}),/nonnegative integers/);
assert.throws(()=>render({...common,chart:'tornado',baseline:1,data:[{label:'x',low:0,high:2},{label:'y',low:0,high:2}]}),/model and assumptions/);
const tornadoInput={...common,chart:'tornado',baseline:1,model:'model',assumptions:['fixed'],data:[{label:'wide',low:0,high:3},{label:'narrow',low:0,high:2}]}; const before=JSON.stringify(tornadoInput.data);assert(render(tornadoInput).includes('data-baseline="1"'));assert.strictEqual(JSON.stringify(tornadoInput.data),before);
const placementInput = valid('ranking', specs.ranking);
for (const [layout, widthInches, minBody, minFooter] of [['document', 6.1, 9, 8], ['slide', 12, 16, 12]]) {
  const svg = render({ ...placementInput, layout, placementWidthInches: widthInches });
  assert(Number(svg.match(/data-body-size-pt="([\d.]+)"/)[1]) >= minBody);
  assert(Number(svg.match(/data-footer-size-pt="([\d.]+)"/)[1]) >= minFooter);
  assert(svg.includes('data-value="-2"'));
}
assert.throws(() => render({ ...placementInput, layout:'document' }), /actual placementWidthInches/);
assert.throws(() => render({ ...placementInput, layout:'document', placementWidthInches:6.1, width:1200 }), /too small/);
assert.throws(() => render({ ...placementInput, layout:'slide', placementWidthInches:6 }), /too small/);
assert.throws(() => render({ ...placementInput, layout:'unknown' }), /layout must/);
assert.throws(() => render({ ...placementInput, layout:'document', placementWidthInches:Infinity }), /actual placementWidthInches/);
const examples = require('../assets/chart-examples.json').charts;
for (const chart of ['box', 'pareto']) assert(!/>(3\.75|11\.3|10\.5|31\.5)</.test(render(examples[chart])), `${chart} axis uses nice ticks, not quartered extents`);
assert(render(examples.table).includes('font-weight="700">全球人壽'), 'table focus row is emphasized');
for (const [chart, spec] of Object.entries(examples)) for (const [layout, inches] of [['document', 6.1], ['slide', 12], ['slide', 13.33]]) {
  assert.doesNotThrow(() => render({ ...spec, source: '設計原型（示意資料）', layout, placementWidthInches: inches }), `${chart} fits ${layout} at ${inches}in`);
}
const waterfallSvg = render(examples.waterfall);
assert(waterfallSvg.includes('>1,120<') && waterfallSvg.includes('data-to="1120"'), 'visible numbers use thousands separators; data attributes stay raw');
const tornadoSvg = render(examples.tornado), tornadoBars = [...tornadoSvg.matchAll(/<rect[^>]*fill="(#[0-9A-F]{6})"[^>]*data-(?:low|high)=/g)].map(match => match[1]);
assert(tornadoBars.slice(0, 2).every(color => color === '#28317B') && tornadoBars.slice(2).every(color => color === '#7F7F7F'), 'tornado uses Focus blue for the titled factor on both sides and gray elsewhere');
const hist = render({ ...common, chart: 'histogram', binWidth: 0.1, binStart: 0, data: [0, 0.1, 0.2, 0.3, 0.3, 0.3, 0.4, 0.5, 0.5, 0.59] });
assert(hist.includes('data-bin-start="0.3" data-bin-end="0.4" data-count="3"'), 'histogram bins are half-open and robust to float division');
assert.throws(() => render({ ...common, chart: 'histogram', binWidth: 1, data: [1, 2, 3] }), /raw numeric observations/);
assert.throws(() => render({ ...common, chart: 'combo', rateLabel: '增率', data: [{ label: 'a', value: 1, rate: 1 }, { label: 'b', value: 2, rate: 2 }] }), /state its unit/);
assert.throws(() => render({ ...common, chart: 'grouped', series: ['只有一組'], data: [{ label: 'a', values: [1] }] }), /2–4 unique series/);
assert(render(examples.combo).includes('數值：2022：4,210，年增率（%） 未提供'), 'desc carries the plotted values, including missing ones');
assert(!render(examples.dumbbell).match(/fill="#7F7F7F"[^>]*>\d/), 'no text is drawn in the 4.0:1 graphic gray');
const { countWidth } = require('../scripts/chart-utils');
const signedGrouped = { ...common, chart: 'grouped', series: ['本期', '上期'], data: [
  { label: '北區營業利益', values: [3000, -1000] }, { label: '南區營業利益', values: [1000, 2000] }
] };
for (const layout of ['web', 'document', 'slide']) {
  const svg = render({ ...signedGrouped, layout, ...(layout === 'web' ? {} : { placementWidthInches: layout === 'document' ? 6.1 : 12 }) });
  const rowRight = Number(svg.match(/<text x="([^"]+)"[^>]*>北區營業利益<\/text>/)[1]);
  const valueRight = Number(svg.match(/<text x="([^"]+)"[^>]*text-anchor="end">-1,000<\/text>/)[1]);
  assert(valueRight - countWidth('-1,000') * 18 > rowRight, 'negative value labels stay clear of row names');
  assert(svg.includes('data-value="-1000"'), 'label spacing preserves the signed data');
}
for (const rates of [[1e-7, 2e-7], [-1e-7, 0], [1.23456789, 2.34567891]]) {
  const svg = render({ ...common, chart: 'combo', rateLabel: '比率（%）', data: rates.map((rate, i) => ({ label: `P${i}`, value: i + 10, rate })) });
  const labels = [...svg.matchAll(/<circle[^>]*data-rate="([^"]+)"[^>]*><\/circle><rect[^>]*><\/rect><text[^>]*>([^<]+)<\/text>/g)];
  assert.deepStrictEqual(labels.map(m => [Number(m[1]), Number(m[2])]), rates.map(rate => [rate, rate]), 'visible rates retain their original precision');
}
const comboLabels = svg => [...svg.matchAll(/<circle[^>]*data-rate="[^"]+"[^>]*><\/circle><rect[^>]*><\/rect><text[^>]*>([^<]+)<\/text>/g)].map(m => m[1]);
assert.deepStrictEqual(comboLabels(render(examples.combo)), ['4.0', '3.2', '8.2', '4.7'], 'combo pads common precision without changing rates');
assert.deepStrictEqual(comboLabels(render({ ...common, chart: 'combo', rateLabel: '比率（%）', width: 2400,
  data: [{label:'P1',value:10,rate:0.1},{label:'P2',value:12,rate:1.2345678901234567}] })),
['0.1000000000000000', '1.2345678901234567'], 'padding does not expose binary floating-point digits');
for (const rate of [1e-99, 1e-100, 1e-101]) {
  assert.deepStrictEqual(comboLabels(render({ ...common, chart: 'combo', rateLabel: '比率（%）',
    data: [{label:'P1',value:10,rate},{label:'P2',value:12,rate:rate*2}] })), [String(rate),String(rate*2)], 'very small rates remain drawable on both sides of the fixed-decimal limit');
}
const smallTotals = render({ ...common, chart: 'sharetrend', categories: ['A', 'B'], data: [
  { label: 'P1', values: [0.0001, 0.0001] }, { label: 'P2', values: [0.0002, 0.0002] }
] });
assert(smallTotals.includes('>總量 0.0002<') && smallTotals.includes('>總量 0.0004<'), 'nonzero totals never round to zero');

// Compare semantic observations, not pixel positions, across destination layouts.
const facts = svg => [...svg.matchAll(/data-[\w-]+="[^"]*"/g)].map(match => match[0]).filter(value => !/^data-(layout|placement-|body-size-|footer-size-|reading-guide)/.test(value));
for (const spec of Object.values(examples)) {
  const input = { ...spec, source: '示意資料' }, original = JSON.stringify(input), webFacts = facts(render(input));
  for (const [layout, inches] of [['document', 6.1], ['slide', 12]]) {
    assert.deepStrictEqual(facts(render({ ...input, layout, placementWidthInches: inches })), webFacts, `${spec.chart}: layout preserves observations and their identities`);
  }
  assert.equal(JSON.stringify(input), original, 'rendering never mutates the source spec');
}
const attributes = tag => Object.fromEntries([...tag.matchAll(/([\w-]+)="([^"]*)"/g)].map(m => [m[1], m[2]]));
const identityMarks = svg => [...svg.matchAll(/<(?:rect|circle|polygon|path) [^>]*data-(?:category|series)=[^>]*>/g)].map(m => attributes(m[0]));
const categoryDomain = ['A', 'B', 'C', 'D', '其他'];
for (const chart of ['stacked', 'mekko', 'sharetrend', 'grouped', 'tracking', 'waffle']) {
  const names = ['其他', 'C'], rows = [{ label: 'P1', values: [40, 60] }, { label: 'P2', values: [60, 40] }];
  let input = { ...common, chart, categoryDomain, categories: names, data: rows };
  if (chart === 'grouped') input.series = names;
  if (chart === 'tracking') Object.assign(input, { labels: ['P1', 'P2'], data: names.map((label, i) => ({ label, values: [40 + i * 10, 60 - i * 10] })) });
  if (chart === 'waffle') input.data = names.map((label, i) => ({ label, value: [40, 60][i] }));
  const svg = render(input), marks = identityMarks(svg);
  for (const name of names) {
    const mark = marks.find(m => (m['data-category'] || m['data-series']) === name && (chart !== 'tracking' || m.d !== undefined));
    assert.equal(mark.fill === 'none' ? mark.stroke : mark.fill, name === 'C' ? '#4A8F5B' : '#DDDDDD', `${chart}: subset retains document identity`);
    if (chart !== 'tracking') {
      const legend = [...svg.matchAll(/<rect\b([^>]*)><\/rect><text\b[^>]*>([^<]+)<\/text>/g)].find(m => m[2] === name || m[2] === `${name} ${name === '其他' ? 40 : 60}%`);
      assert(legend, `${chart}: category is named beside its legend swatch`);
      assert.equal(attributes(legend[1]).fill, name === 'C' ? '#4A8F5B' : '#DDDDDD', `${chart}: legend and marks retain the same identity`);
    }
  }
  if (chart === 'tracking') assert(/<line[^>]*stroke="#4A4A4A"[^>]*stroke-width="1"><\/line><text[^>]*>其他<\/text>/.test(svg), 'Other endpoint has a readable leader');
  assert.throws(() => render({ ...input, categoryDomain: ['A', 'B'] }), /does not include/);
}
const trackInput = { ...common, chart: 'tracking', categoryDomain: ['A', 'B'], labels: ['P1', 'P2', 'P3'], data: [{ label: 'A', values: [5, null, 8] }, { label: 'B', values: [8, 6, 5] }] };
const seriesStyles = svg => identityMarks(svg).filter(m => m.d !== undefined).map(m => [m['data-series'], m.stroke, m['stroke-dasharray']]).sort();
assert.deepStrictEqual(seriesStyles(render(trackInput)), seriesStyles(render({ ...trackInput, data: [...trackInput.data].reverse() })), 'reordering preserves line colour and dash identity');
for (const chart of ['trend', 'tracking', 'indexed']) {
  const input = { ...trackInput, chart, focus: 'A' }; if (chart !== 'tracking') delete input.categoryDomain;
  const svg = render(input), path = svg.match(/<path d="([^"]*)"[^>]*data-series="A"/)[1];
  assert.equal((path.match(/M/g) || []).length, 2, `${chart}: missing observation breaks the line`);
  assert(svg.includes('>未提供：A／P2（缺值斷線）</text>'), `${chart}: gap is identified in visible text`);
  assert(!identityMarks(svg).some(m => m['data-series'] === 'A' && m['data-period'] === 'P2'), 'missing observation has no fabricated mark');
}
const comboGap = render({ ...common, chart: 'combo', rateLabel: '增率（%）', data: [{ label: 'P1', value: 0, rate: 1 }, { label: 'P2', value: null, rate: null }, { label: 'P3', value: 2, rate: 3 }] });
assert(comboGap.includes('>未提供：柱（件）／P2</text>') && comboGap.includes('>未提供：增率（%）／P2（缺值斷線）</text>'));
assert.equal((comboGap.match(/<path d="([^"]+)"[^>]*data-rate-line/)[1].match(/M/g) || []).length, 2);
assert(comboGap.includes('data-value="0"'), 'zero remains an observation');
const comboTop = render({ ...common, chart: 'combo', layout: 'document', placementWidthInches: 6.1, rateLabel: '增率（%）', data: [{ label: 'P1', value: 0, rate: 1 }, { label: 'P2', value: null, rate: null }, { label: 'P3', value: 2, rate: 3 }] });
const topLabel = comboTop.match(/<circle[^>]*cy="([^"]+)"[^>]*data-rate="3"[^>]*><\/circle><rect[^>]*><\/rect><text[^>]*y="([^"]+)"[^>]*>3<\/text>/);
assert(Number(topLabel[2]) - 18 > Number(topLabel[1]), 'top rate label stays inside the plot, clear of the legend');
for (const chart of ['trend', 'tracking']) {
  const input = { ...trackInput, chart, focus: 'A', yDomain: [4, 9] }; if (chart === 'trend') delete input.categoryDomain;
  const svg = render(input);
  assert(svg.includes('>顯示範圍：4–9 件；縱軸不含零</text>') && !svg.includes('>0</text>'));
  assert.throws(() => render({ ...input, yDomain: [5, 7] }), /cover every observed/);
  for (const yDomain of [[9, 4], [4, 4], [NaN, 9], [-1e308, 1e308]]) assert.throws(() => render({ ...input, yDomain }), /min < max/);
}
assert.throws(() => render({ ...placementInput, yDomain: [1, 5] }), /yDomain is only supported/);
assert.throws(() => render({ ...placementInput, categoryDomain: ['A'] }), /categorical charts/);
const U = require('../scripts/chart-utils');
for (const [value, places, expected] of [[1/1e9*100,1,'1e-7'],[100/3000,1,'0.033'],[-0.00004,3,'-0.00004'],[1e-101,3,'1e-101'],[Number.MIN_VALUE,3,'5e-324'],[0,3,'0']]) {
  assert.equal(U.derived(value,places), expected, 'small derived values stay concise and nonzero');
}
assert.throws(() => U.categoryIndices({}, ['A','B','C','D','E']), error => /categories/.test(error.message) && !/categoryDomain/.test(error.message));
assert.throws(() => U.categoryIndices({categoryDomain:['A','B','C','D','E']}, ['A']), /categoryDomain/);
assert.deepStrictEqual(U.categoryIndices({categoryDomain:['其他','A']}, ['其他','A']), [4,1], 'Other takes the neutral slot by name; other categories keep their domain order');
for (const [other, expected] of [[999999999,'1e-7'],[2999,'0.033']]) {
  const svg = render({...common, chart:'stacked', categories:['A','B'], data:[{label:'甲',values:[1,other]},{label:'乙',values:[1,other]}]});
  assert(svg.match(/<desc[^>]*>(.*?)<\/desc>/)[1].includes(`A ${expected}%`));
  assert([...svg.matchAll(/<text\b[^>]*>([^<]+)<\/text>/g)].some(m => m[1].includes(`（${expected}%）`)), 'tiny segment text agrees with its description');
  assert(svg.includes(`data-share="${1/(other+1)*100}"`), 'display formatting leaves the underlying share unchanged');
}
const funnelStages = [{label:'起點',value:3000},{label:'次階段',value:1},{label:'結束',value:0},{label:'後續',value:0}];
const funnelText = render({...common,chart:'funnel',sameCohort:true,data:funnelStages});
for (const [i, rate] of ['起始母體','0.03%','0%','不適用'].entries()) {
  assert(funnelText.includes(`${funnelStages[i].label} 階段率 ${rate}`));
  assert(funnelText.includes(`>${U.num(funnelStages[i].value)} / ${rate}</text>`), 'funnel rates agree in labels and desc, including zero denominators');
}
const paretoText = render({...common,chart:'pareto',data:[{label:'小',value:1},{label:'大',value:5},{label:'中',value:3}]});
for (const [name, share] of [['大','55.556'],['中','88.889'],['小','100']]) {
  assert(paretoText.includes(`${name} 累計 ${share}%`) && paretoText.includes(`>${share}%</text>`), 'pareto labels and description use the same sorted cumulative facts');
}
assert.equal(U.sum([0.0001, 0.0003]), 0.0004, 'decimal totals do not expose binary addition noise');
assert.equal(U.sum([1e16, 1, -1e16]), 1, 'sum preserves a small contribution despite cancellation');
assert.equal(U.sum([1e-300, 2e-300]), 3e-300, 'scientific notation preserves tiny nonzero sums');
assert.equal(U.difference(0.1, 0.3), 0.2, 'visible and accessible differences share decimal arithmetic');
const decimalWaterfall = render({ ...common, chart: 'waterfall', start: 0.1, end: 0.3, data: [{ label: '增加', value: 0.2 }] });
assert(decimalWaterfall.includes('data-to="0.3"') && decimalWaterfall.includes('期末 餘額 0.3'), 'waterfall marks and description share the same balance');
assert.deepStrictEqual(U.ticks(1e16, 1e16 + 4), [1e16, 1e16 + 2, 1e16 + 4], 'large offsets neither hang nor erase distinguishable ticks');
assert.equal(U.tick(1e16 + 4), '10,000,000,000,000,004');
for (const chart of ['stacked', 'mekko', 'sharetrend']) {
  const input = { ...common, chart, categories: ['A', 'B'], data: [{ label: 'P1', values: [1, 3] }, { label: 'P2', values: [3, 1] }] };
  const scaled = { ...input, data: input.data.map(row => ({ ...row, values: row.values.map(v => v * 8) })) };
  const shares = svg => [...svg.matchAll(/data-share="([^"]+)"/g)].map(m => Number(m[1]));
  assert.deepStrictEqual(shares(render(input)), shares(render(scaled)), `${chart}: unit conversion preserves shares`);
  const svg = render(input), desc = svg.match(/<desc[^>]*>(.*?)<\/desc>/)[1];
  assert(desc.includes('P1 總量 4，A 25%、B 75%'), `${chart}: accessible facts match visible values`);
}
console.log(`rendered ${chartTypes.length} chart types`);
module.exports={specs,common,valid};
