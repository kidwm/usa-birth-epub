#!/usr/bin/env python3
"""Export sRGB cover deliverables, validate their sources, then package the EPUB."""
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path
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
shutil.copyfile(jpg_path, ROOT / 'assets/cover.jpg')
shutil.copyfile(ROOT / 'cover.svg', OUT / 'usa-birth-cover-editable.svg')
shutil.copyfile(FINAL / 'cover-outlined.svg', OUT / 'usa-birth-cover-outlined.svg')

# The manuscript build owns EPUB metadata, resources, validation and packaging.
subprocess.run([sys.executable, str(ROOT / 'scripts/build.py')], check=True)
epub_path = OUT / 'usa-birth.epub'
epub_report = json.loads((OUT / 'validation-report.json').read_text())
with zipfile.ZipFile(epub_path) as archive:
    entry_count = len(archive.infolist())

report = {
    'status': 'passed',
    'scope': 'Native SVG artwork, exact historical map bytes, vector stars, live text, outlined text, image export, and the Markdown EPUB build.',
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
    'epub': {'file': epub_path.name, 'bytes': epub_path.stat().st_size, 'entries': entry_count, 'validation': epub_report},
}
(OUT / 'cover-validation-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
