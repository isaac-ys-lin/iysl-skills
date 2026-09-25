"""Throwaway prototype: three containers, one source-faithful SVG comparison."""
import json
from pathlib import Path
from html import escape
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / 'data.json').read_text())
ROWS = DATA['rows']
PALETTE = {'title': '#000099', 'focus': '#28317B', 'context': '#7F7F7F', 'text': '#111111', 'secondary': '#4A4A4A'}
FONT = 'Arial, Microsoft JhengHei, PingFang TC, sans-serif'
# ponytail: live-text SVG uses installed fonts; outline glyphs if cross-platform render drift appears.
def chart(after):
    state = 'after' if after else 'before'
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="420" viewBox="0 0 960 420" role="img" aria-labelledby="title-{state} desc-{state}"><title id="title-{state}">四通路保費比較</title><desc id="desc-{state}">{escape(DATA["source"])}；'+ '，'.join(f'{r["channel"]} {r["value"]} 百萬元' for r in ROWS) + f'</desc><rect width="960" height="420" fill="white"/><g font-family="{FONT}" fill="#111111">']
    pieces += ['<text x="118" y="32" font-size="20" fill="#4A4A4A">保費（百萬元）</text>']
    for tick in [0, 40, 80, 120]:
        x = 120 + tick * 5.5
        pieces.append(f'<line x1="{x}" y1="55" x2="{x}" y2="342" stroke="#E3E3E6"/><text x="{x}" y="383" text-anchor="middle" font-size="22">{tick}</text>')
    for i, r in enumerate(ROWS):
        y = 64 + i * 74
        color = (PALETTE['focus'] if i == 0 else PALETTE['context']) if after else ['#4472C4', '#ED7D31', '#70AD47', '#7030A0'][i]
        pieces.append(f'<text x="96" y="{y+31}" text-anchor="end" font-size="26">{escape(r["channel"])}</text><rect data-channel="{escape(r["channel"])}" data-value="{r["value"]}" x="120" y="{y}" width="{r["value"]*5.5}" height="44" fill="{color}"/><text x="{134+r["value"]*5.5}" y="{y+31}" font-size="26">{r["value"]}</text>')
    return ''.join(pieces) + '</g></svg>'

for state in ['before', 'after']:
    svg = chart(state == 'after')
    (ROOT / 'assets' / f'chart-{state}.svg').write_text(svg)
    doc = ET.fromstring(svg)
    marks = [r for r in doc.iter() if r.get('data-value')]
    assert [(r.get('data-channel'), float(r.get('data-value'))) for r in marks] == [(r['channel'], r['value']) for r in ROWS]
    assert all(float(r.get('width')) == float(r.get('data-value')) * 5.5 for r in marks)
    assert not any(r.tag.split('}')[-1] in ['image', 'script', 'foreignObject'] for r in doc.iter())
assert sum(r['value'] for r in ROWS) == 300
html = (ROOT / 'prototype-template.html').read_text()
html = html.replace('__DATA__', json.dumps(DATA, ensure_ascii=False)).replace('__BEFORE_SVG__', chart(False)).replace('__AFTER_SVG__', chart(True))
(ROOT / 'prototype.html').write_text(html)
print('Built prototype.html and SVGs; labels, values, scale, total and vector-only checks passed.')
