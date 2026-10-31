#!/usr/bin/env python3
"""Build the selected A cover from historical source pixels and vector artwork."""
import base64
import hashlib
import io
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[3]
FINAL = ROOT / 'design/cover-final'
MAP = ROOT / 'design/cover-proposals/references/map-1783.jpg'
FONT = FINAL / 'fonts/NotoSerifTC-VF.ttf'
GLYPHS = json.loads((FINAL / 'glyphs.json').read_text())
WIDTH, HEIGHT = 1920, 2560
TEXT = '美國的誕生藍弋丰'

def encoded(data):
    return base64.b64encode(data).decode('ascii')

def font_face(weight):
    font = TTFont(FONT)
    options = subset.Options()
    options.layout_features = ['*']
    sub = subset.Subsetter(options=options)
    sub.populate(text=TEXT)
    sub.subset(font)
    font = instantiateVariableFont(font, {'wght': weight}, inplace=False)
    font.flavor = 'woff2'
    buffer = io.BytesIO()
    font.save(buffer)
    data = buffer.getvalue()
    (FINAL / f'fonts/cover-serif-{weight}.woff2').write_bytes(data)
    return f"@font-face {{ font-family: 'Cover Serif'; font-weight: {weight}; font-style: normal; src: url(data:font/woff2;base64,{encoded(data)}) format('woff2'); }}"

FONT_CSS = '\n'.join(font_face(w) for w in [600, 900])
MAP_DATA = encoded(MAP.read_bytes())

def star(cx, cy, radius=42):
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * 0.38196601125
        pts.append(f'{cx+r*math.cos(angle):.3f},{cy+r*math.sin(angle):.3f}')
    return ' '.join(pts)

POSITIONS = []
for row, count in enumerate([3, 2, 3, 2, 3]):
    y = 165 + row * 130
    xs = [80, 178, 276] if count == 3 else [129, 227]
    POSITIONS.extend((x, y) for x in xs)
assert len(POSITIONS) == 13

def text_node(id_, text, x, y, size, weight, fill, spacing=0, outlined=False):
    if not outlined:
        return f'<text id="{id_}" x="{x}" y="{y}" font-family="Cover Serif, Noto Serif TC, serif" font-size="{size}" font-weight="{weight}" letter-spacing="{spacing}" fill="{fill}">{escape(text)}</text>'
    result = [f'<g id="{id_}" fill="{fill}" aria-label="{escape(text)}" data-original-text="{escape(text)}">']
    for char in text:
        g = GLYPHS[str(weight)]['glyphs'][char]
        result.append(f'<path transform="translate({x:.3f} {y}) scale({size/1000:.6f})" d="{g["path"]}"/>')
        x += g['advance'] * size / 1000 + spacing
    return '\n'.join(result) + '</g>'

def build(outlined=False):
    styles = '' if outlined else f'<style type="text/css">{FONT_CSS}</style>'
    stars = '\n'.join(f'<polygon id="star-{i+1:02d}" points="{star(x,y)}"/>' for i,(x,y) in enumerate(POSITIONS))
    # The left strip is a crop of the stripe field. All 13 source stripes remain
    # editable; the 356 px cover strip exposes its first five, as in proposal A.
    stripes = '\n'.join(f'<rect id="stripe-{i+1:02d}" x="{i*71.2:.3f}" y="930" width="71.2" height="1630" fill="{("#aa3224" if i%2==0 else "#f6e9cf")}"/>' for i in range(13))
    titles = '\n'.join([
        text_node('title-america', '美國', 435, 450, 374, 900, '#8e2519', outlined=outlined),
        text_node('title-of', '的', 1190, 440, 260, 900, '#8e2519', outlined=outlined),
        text_node('title-birth', '誕生', 435, 835, 394, 900, '#0b2c43', outlined=outlined),
        text_node('author', '藍弋丰', 451, 1040, 94, 600, '#28251f', 13, outlined),
    ])
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="1920" height="2560" viewBox="0 0 1920 2560" role="img" aria-labelledby="cover-title cover-desc">
  <title id="cover-title">美國的誕生 — 藍弋丰</title>
  <desc id="cover-desc">A 版正式封面：原始 1783 年地圖、十三顆向量星星（3、2、3、2、3）、紅白旗紋，以及獨立的宋體書名與作者。文字{'已轉為向量路徑，搭配 cover.svg 可編輯母稿' if outlined else '可編輯，內嵌目前文字所需字型子集'}。</desc>
  <metadata id="source-metadata">Map: William Darton; William Guthrie, 1783; Library of Congress 74696218; Wikimedia Commons public-domain scan. Embedded JPEG SHA-256: {hashlib.sha256(MAP.read_bytes()).hexdigest()}. Typography: Noto Serif TC, SIL Open Font License. No AI mockup pixels are included.</metadata>
  <defs>
    {styles}
    <linearGradient id="paper-color" x1="0" y1="0" x2="0.7" y2="1">
      <stop offset="0" stop-color="#f6ecd7"/><stop offset="0.6" stop-color="#f1e4c8"/><stop offset="1" stop-color="#ebd9b5"/>
    </linearGradient>
    <linearGradient id="navy-ink" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#163551"/><stop offset="1" stop-color="#213e59"/></linearGradient>
    <filter id="paper-grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.48" numOctaves="3" seed="23" stitchTiles="stitch"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <filter id="soft-map-edge" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="42"/></filter>
    <mask id="map-reveal" maskUnits="userSpaceOnUse" x="0" y="0" width="1920" height="2560">
      <rect width="1920" height="2560" fill="black"/>
      <path d="M260 1220 C600 1180 860 1210 1110 1080 C1450 1030 1660 985 2040 910 L2040 2700 L260 2700 Z" fill="white" filter="url(#soft-map-edge)"/>
      <rect x="1400" y="2180" width="800" height="600" rx="100" fill="black" filter="url(#soft-map-edge)"/>
    </mask>
    <clipPath id="map-area"><rect x="356" width="1564" height="2560"/></clipPath>
    <clipPath id="flag-strip"><rect width="356" height="2560"/></clipPath>
  </defs>
  <g id="paper" inkscape:groupmode="layer" inkscape:label="01 米白紙色">
    <rect width="1920" height="2560" fill="url(#paper-color)"/>
    <rect width="1920" height="2560" filter="url(#paper-grain)" opacity="0.045"/>
  </g>
  <g id="historical-map" inkscape:groupmode="layer" inkscape:label="02 原始 1783 地圖" clip-path="url(#map-area)">
    <g mask="url(#map-reveal)">
      <image id="map-scan" x="-250" y="720" width="2367" height="2133" preserveAspectRatio="xMidYMid meet" xlink:href="data:image/jpeg;base64,{MAP_DATA}"/>
    </g>
  </g>
  <g id="flag" inkscape:groupmode="layer" inkscape:label="03 向量旗幟：13 星與條紋裁切" clip-path="url(#flag-strip)">
    {stripes}
    <rect id="canton" width="356" height="930" fill="url(#navy-ink)"/>
    <g id="thirteen-stars" fill="#faefd6" data-count="13" data-rows="3,2,3,2,3">{stars}</g>
    <rect width="356" height="2560" filter="url(#paper-grain)" opacity="0.035"/>
  </g>
  <g id="typography" inkscape:groupmode="layer" inkscape:label="04 書名與作者{'（轉曲）' if outlined else '（可編輯文字）'}">
    {titles}
    <path id="title-rule" d="M451 901 H1300" stroke="#a48851" stroke-width="2"/>
  </g>
</svg>
'''

for name, outlined in [('cover.svg',False),('cover-outlined.svg',True)]:
    p = ROOT / name if not outlined else FINAL / name
    p.write_text('\n'.join(line.rstrip() for line in build(outlined).splitlines())+'\n',encoding='utf-8')
    print(p.relative_to(ROOT),p.stat().st_size)
