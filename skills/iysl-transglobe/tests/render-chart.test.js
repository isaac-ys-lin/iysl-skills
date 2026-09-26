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
console.log(`rendered ${chartTypes.length} chart types`);
module.exports={specs,common,valid};
