#!/usr/bin/env python3
"""Export sRGB cover deliverables, validate their sources, then package the EPUB."""
import base64
import datetime
import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

from PIL import Image, ImageCms

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output'
FINAL = ROOT / 'design/cover-final'
SOURCE_MAP = ROOT / 'design/cover-proposals/references/map-1783.jpg'
NS = {'s': 'http://www.w3.org/2000/svg', 'o': 'http://www.idpf.org/2007/opf'}
XLINK = '{http://www.w3.org/1999/xlink}href'

master = ET.parse(ROOT / 'cover.svg').getroot()
outlined = ET.parse(FINAL / 'cover-outlined.svg').getroot()
embedded_images = master.findall('.//s:image', NS)
assert len(embedded_images) == 1, 'Only the original historical map may be a raster layer'
map_image = embedded_images[0]
embedded_map = base64.b64decode(map_image.attrib[XLINK].split(',', 1)[1])
assert embedded_map == SOURCE_MAP.read_bytes(), 'Map source pixels changed'
map_width, map_height = Image.open(SOURCE_MAP).size
map_scale_x = float(map_image.attrib['width']) / map_width
map_scale_y = float(map_image.attrib['height']) / map_height
assert abs(map_scale_x - map_scale_y) < 1e-9
assert map_scale_x <= 1, 'The source map should not be upscaled'

stars = master.findall(".//s:g[@id='thirteen-stars']/s:polygon", NS)
assert len(stars) == 13
rows = Counter()
for star in stars:
    pts = [tuple(map(float, p.split(','))) for p in star.attrib['points'].split()]
    assert len(pts) == 10
    assert all(0 < x < 356 and 0 < y < 930 for x, y in pts), 'A star is clipped'
    rows[round(sum(y for _, y in pts) / len(pts))] += 1
assert [rows[y] for y in sorted(rows)] == [3, 2, 3, 2, 3]
assert len(master.findall('.//s:text', NS)) == 4
assert ''.join(e.text for e in master.findall('.//s:text', NS)) == '美國的誕生藍弋丰'
assert not outlined.findall('.//s:text', NS)
assert len(outlined.findall(".//s:g[@id='typography']//s:path", NS)) == 9

png_path = OUT / 'usa-birth-cover-1920x2560.png'
jpg_path = OUT / 'usa-birth-cover-1920x2560.jpg'
with Image.open(png_path) as image:
    assert image.size == (1920, 2560)
    if 'A' in image.getbands():
        assert image.getchannel('A').getextrema() == (255, 255)
    rgb = image.convert('RGB')
icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
rgb.save(png_path, format='PNG', icc_profile=icc, optimize=True)
rgb.save(jpg_path, format='JPEG', quality=92, subsampling=0, optimize=True, icc_profile=icc)
for path in [png_path, jpg_path]:
    with Image.open(path) as exported:
        assert exported.size == (1920, 2560) and exported.mode == 'RGB'
        assert exported.info.get('icc_profile') == icc
shutil.copyfile(jpg_path, ROOT / 'EPUB/cover.jpg')
shutil.copyfile(ROOT / 'cover.svg', OUT / 'usa-birth-cover-editable.svg')
shutil.copyfile(FINAL / 'cover-outlined.svg', OUT / 'usa-birth-cover-outlined.svg')

opf_path = ROOT / 'EPUB/content.opf'
timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
opf_text = opf_path.read_text()
opf_text, count = re.subn(r'(<meta property="dcterms:modified">)[^<]*(</meta>)', lambda m:m[1]+timestamp+m[2], opf_text)
assert count == 1
opf_path.write_text(opf_text)
opf = ET.fromstring(opf_text)
manifest = {e.attrib['id']: e.attrib for e in opf.find('o:manifest', NS)}
covers = [e for e in manifest.values() if 'cover-image' in e.get('properties', '').split()]
assert len(covers) == 1 and covers[0]['href'] == 'cover.jpg' and covers[0]['media-type'] == 'image/jpeg'
assert opf.find('o:spine', NS)[0].attrib['idref'] == 'cover-page'
for item in manifest.values():
    assert (ROOT / 'EPUB' / unquote(item['href'])).is_file(), item
local_links = 0
for path in (ROOT / 'EPUB').glob('*.xhtml'):
    tree = ET.parse(path)
    for element in tree.iter():
        for key, value in element.attrib.items():
            if key not in ('src', 'href', XLINK): continue
            url = urlsplit(value)
            if url.scheme or url.netloc or not url.path: continue
            assert (path.parent / unquote(url.path)).is_file(), (path.name, value)
            local_links += 1
for item in opf.find('o:spine', NS):
    assert item.attrib['idref'] in manifest

epub_path = OUT / 'usa-birth-new-cover.epub'
with zipfile.ZipFile(epub_path, 'w') as archive:
    archive.writestr('mimetype', b'application/epub+zip', compress_type=zipfile.ZIP_STORED)
    for folder in ['META-INF', 'EPUB']:
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file() and path.name != '.DS_Store':
                archive.write(path, path.relative_to(ROOT).as_posix(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
with zipfile.ZipFile(epub_path) as archive:
    assert archive.infolist()[0].filename == 'mimetype'
    assert archive.infolist()[0].compress_type == zipfile.ZIP_STORED
    assert archive.testzip() is None
    assert archive.read('EPUB/cover.jpg') == jpg_path.read_bytes()
    expected = {'EPUB/'+unquote(e['href']) for e in manifest.values()}
    packaged = {n for n in archive.namelist() if n.startswith('EPUB/') and n != 'EPUB/content.opf'}
    assert expected == packaged
    entry_count = len(archive.infolist())

report = {
    'status': 'passed',
    'created_utc': timestamp,
    'scope': 'Native SVG artwork, exact historical map bytes, vector stars, live text, outlined text, image export, EPUB cover references, local resource files, XML parsing, ZIP structure and CRCs.',
    'epubcheck': 'Full EPUBCheck not run: Java runtime and EPUBCheck are not installed.',
    'cover': {
        'width': 1920, 'height': 2560, 'aspect_ratio': '3:4',
        'color_space': 'sRGB', 'jpeg_quality': 92, 'jpeg_subsampling': 0,
        'vector_stars': 13, 'star_rows': [3, 2, 3, 2, 3],
        'all_stars_fully_visible': True,
        'editable_text_elements': 4, 'outlined_glyphs': 8,
        'png_bytes': png_path.stat().st_size, 'jpeg_bytes': jpg_path.stat().st_size,
    },
    'source': {
        'map': str(SOURCE_MAP.relative_to(ROOT)), 'map_size': [map_width, map_height],
        'embedded_bytes_equal_original': True, 'map_scale': map_scale_x,
        'map_sha256': hashlib.sha256(embedded_map).hexdigest(),
        'ai_mockup_pixels_in_final': False,
        'fonts': 'Noto Serif TC, weights 900 and 600; embedded subsets and original TTF supplied under SIL OFL.',
    },
    'epub': {'file': epub_path.name, 'bytes': epub_path.stat().st_size, 'entries': entry_count, 'local_resource_links_checked': local_links},
}
(OUT / 'validation-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
