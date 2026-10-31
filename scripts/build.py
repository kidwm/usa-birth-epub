#!/usr/bin/env python3
"""Build the Markdown manuscript, then check EPUB resources and content fidelity."""
import argparse
from collections import Counter
import hashlib
import html
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
import zipfile

from setup_tools import PANDOC_VERSION

ROOT = Path(__file__).resolve().parents[1]
NS = {'h': 'http://www.w3.org/1999/xhtml', 'o': 'http://www.idpf.org/2007/opf',
      'c': 'urn:oasis:names:tc:opendocument:xmlns:container'}
EPUB_TYPE = '{http://www.idpf.org/2007/ops}type'
XLINK = '{http://www.w3.org/1999/xlink}href'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def normalize(value):
    return re.sub(r'\s+', '', value)


def nodes(value):
    if isinstance(value, dict):
        if 't' in value:
            yield value
        yield from nodes(value.get('c', []))
    elif isinstance(value, list):
        for item in value:
            yield from nodes(item)


def inline_text(value):
    """Text of a Pandoc inline sequence, excluding note markers and image alt."""
    if isinstance(value, list):
        return ''.join(inline_text(v) for v in value)
    if not isinstance(value, dict):
        return ''
    kind, content = value['t'], value.get('c', [])
    if kind in ('Str', 'MetaString'):
        return content
    if kind in ('Space', 'SoftBreak', 'LineBreak'):
        return ' '
    if kind in ('Note', 'Image', 'RawInline', 'RawBlock'):
        return ''
    if kind in ('Code', 'Math'):
        return content[1]
    if kind in ('Link', 'Span', 'Quoted'):
        return inline_text(content[1])
    return inline_text(content)


def xml_text(element):
    """Visible prose without automatically generated footnote reference numbers."""
    if element.get(EPUB_TYPE) == 'noteref' or 'footnote-back' in element.get('class', '').split():
        return ''
    value = element.text or ''
    for child in element:
        value += xml_text(child) + (child.tail or '')
    return value


def archive_link(current, link):
    url = urlsplit(link)
    if url.scheme or url.netloc:
        return None
    target = posixpath.normpath(posixpath.join(posixpath.dirname(current), unquote(url.path))) if url.path else current
    return target, unquote(url.fragment)


def finalize_titles(path, book_title):
    """Pandoc's chunk pagetitle is a filename; give each XHTML a plain-text title."""
    staged = path.with_suffix('.titles.epub')
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(staged, 'w') as target:
        for entry in source.infolist():
            data = source.read(entry.filename)
            if entry.filename.endswith('.xhtml'):
                doc = ET.fromstring(data)
                heading = doc.find('.//h:body//h:h1', NS)
                if heading is None:
                    heading = doc.find('.//h:body//h:h2', NS)
                title = re.sub(r'\s+', ' ', xml_text(heading)).strip() if heading is not None else book_title
                markup = data.decode('utf-8')
                markup, count = re.subn(r'<title>.*?</title>', lambda _: '<title>' + html.escape(title) + '</title>', markup, count=1, flags=re.S)
                require(count == 1, f'Missing XHTML title: {entry.filename}')
                data = markup.encode('utf-8')
            target.writestr(entry, data)
    staged.replace(path)


def validate(epub_path, ast):
    source_nodes = list(nodes(ast['blocks']))
    headers = [n['c'] for n in source_nodes if n['t'] == 'Header' and n['c'][0] <= 2]
    expected_order = [h[1][0] for h in headers]
    require(len(set(expected_order)) == len(expected_order), 'Duplicate manuscript heading IDs')
    expected_prose = Counter(normalize(inline_text(n['c'])) for n in source_nodes if n['t'] == 'Para')
    figures = [n['c'] for n in source_nodes if n['t'] == 'Figure']
    expected_captions = [normalize(inline_text(f[1][1])) for f in figures]
    images = [n['c'] for n in source_nodes if n['t'] == 'Image']
    expected_images = []
    for image in images:
        path = image[2][0]
        require(not urlsplit(path).scheme, f'Use a local manuscript image: {path}')
        candidates = [ROOT / path, ROOT / 'content' / path]
        source = next((p for p in candidates if p.is_file()), None)
        require(source is not None, f'Missing manuscript image: {path}')
        expected_images.append((hashlib.sha256(source.read_bytes()).hexdigest(), inline_text(image[1])))
    with zipfile.ZipFile(epub_path) as archive:
        entries = archive.infolist()
        names = set(archive.namelist())
        require(len(names) == len(entries), 'Duplicate ZIP entries')
        require(entries[0].filename == 'mimetype' and entries[0].compress_type == zipfile.ZIP_STORED,
                'EPUB mimetype must be the first, uncompressed entry')
        require(archive.read('mimetype') == b'application/epub+zip', 'Invalid mimetype')
        require(archive.testzip() is None, 'ZIP CRC failure')
        container = ET.fromstring(archive.read('META-INF/container.xml'))
        opf_name = container.find('c:rootfiles/c:rootfile', NS).get('full-path')
        opf = ET.fromstring(archive.read(opf_name))
        manifest = {e.get('id'): e for e in opf.find('o:manifest', NS)}
        manifest_paths = {key: archive_link(opf_name, el.get('href'))[0] for key, el in manifest.items()}
        for name in manifest_paths.values():
            require(name in names, f'Manifest resource missing: {name}')
        docs = {name: ET.fromstring(archive.read(name)) for name in names if name.endswith('.xhtml')}
        ids = {}
        for name, doc in docs.items():
            title = doc.find('h:head/h:title', NS)
            require(title is not None and len(title) == 0 and (title.text or '').strip(), f'Invalid XHTML title: {name}')
            doc_ids = [e.get('id') for e in doc.iter() if e.get('id')]
            require(len(doc_ids) == len(set(doc_ids)), f'Duplicate XML IDs: {name}')
            ids[name] = set(doc_ids)
        local_links = 0
        for name, doc in docs.items():
            for element in doc.iter():
                for key in ('src', 'href', XLINK):
                    link = element.get(key)
                    if link is None:
                        continue
                    target = archive_link(name, link)
                    if target is None:
                        continue
                    path, fragment = target
                    require(path in names, f'Broken local link: {name} -> {link}')
                    if fragment:
                        require(fragment in ids.get(path, set()), f'Broken fragment: {name} -> {link}')
                    local_links += 1
        actual_order, prose, captions, actual_images = [], Counter(), [], []
        header_targets, heading_texts, chapter_paths = [], [], {}
        note_refs, notes = 0, 0
        for ref in opf.find('o:spine', NS):
            require(ref.get('idref') in manifest_paths, 'Unmanifested spine item')
            name = manifest_paths[ref.get('idref')]
            doc = docs[name]
            sections = [e for e in doc.findall('.//h:section', NS) if e.get('id') in expected_order]
            if not sections:
                continue
            for section in sections:
                identifier = section.get('id')
                actual_order.append(identifier)
                chapter_paths[identifier] = name
                header = next(e for e in section if e.tag in ('{'+NS['h']+'}h1', '{'+NS['h']+'}h2'))
                header_targets.append((name, identifier))
                heading_texts.append(normalize(xml_text(header)))
            for p in doc.findall('.//h:body//h:p', NS):
                prose[normalize(xml_text(p))] += 1
            for caption in doc.findall('.//h:figcaption', NS):
                captions.append(normalize(xml_text(caption)))
            for image in doc.findall('.//h:img', NS):
                path, _ = archive_link(name, image.get('src'))
                actual_images.append((hashlib.sha256(archive.read(path)).hexdigest(), image.get('alt', '')))
            note_refs += sum(e.get(EPUB_TYPE) == 'noteref' for e in doc.iter())
            notes += sum(e.get(EPUB_TYPE) == 'footnote' for e in doc.iter())
        require(actual_order == expected_order, 'EPUB reading order differs from manuscript headings')
        require(heading_texts == [normalize(inline_text(h[2])) for h in headers], 'Heading text changed')
        require(prose == expected_prose, f'Prose changed: missing {sum((expected_prose-prose).values())}, unexpected {sum((prose-expected_prose).values())} paragraphs')
        require(captions == expected_captions, 'Figure captions changed or reordered')
        require(actual_images == expected_images, 'Image bytes, alt text, or order changed')
        note_count = sum(n['t'] == 'Note' for n in source_nodes)
        require(note_refs == notes == note_count, 'Footnote references or definitions lost')
        nav_item = next(e for e in manifest.values() if 'nav' in e.get('properties', '').split())
        nav_name = manifest_paths[nav_item.get('id')]
        toc = next(e for e in docs[nav_name].iter() if e.get(EPUB_TYPE) == 'toc')
        links = toc.findall('.//h:a', NS)
        listed = [i for i, h in enumerate(headers) if 'unlisted' not in h[1][1]]
        require([archive_link(nav_name, a.get('href')) for a in links] == [header_targets[i] for i in listed],
                'Navigation order or targets differ from manuscript headings')
        require([normalize(xml_text(a)) for a in links] == [heading_texts[i] for i in listed],
                'Navigation titles differ from chapter titles')
    return {'status': 'passed', 'paragraphs_verified': sum(expected_prose.values()),
            'figures_verified': len(figures), 'images_verified': len(images), 'footnotes_verified': note_count,
            'chapters': sum(bool(re.fullmatch(r'chapter\d+', v)) for v in expected_order),
            'parts': sum(bool(re.fullmatch(r'part\d+', v)) for v in expected_order),
            'navigation_entries': len(listed), 'local_links_checked': local_links,
            'chapter_paths': chapter_paths}


def find_pandoc():
    binary = os.environ.get('PANDOC') or next(iter(sorted((ROOT / '.tools').glob('pandoc-3.13*/bin/pandoc'))), None) or shutil.which('pandoc')
    require(binary is not None, 'Run python3 scripts/setup_tools.py first (or set PANDOC).')
    version = subprocess.check_output([str(binary), '--version'], text=True).splitlines()[0]
    require(version == f'pandoc {PANDOC_VERSION}', f'Expected Pandoc {PANDOC_VERSION}; found {version}.')
    return str(binary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', default='output/usa-birth.epub')
    parser.add_argument('--epubcheck', action='store_true', help='Also run the W3C validator; Java 11+ required.')
    args = parser.parse_args()
    os.chdir(ROOT)
    output = Path(args.output).resolve()
    require(output.suffix == '.epub', 'Output filename must end in .epub')
    output.parent.mkdir(parents=True, exist_ok=True)
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    env = os.environ.copy()
    if 'SOURCE_DATE_EPOCH' not in env:
        commit = subprocess.run(['git', 'log', '-1', '--format=%ct'], capture_output=True, text=True)
        env['SOURCE_DATE_EPOCH'] = commit.stdout.strip() if commit.returncode == 0 and commit.stdout.strip() else '1793404800'
    pandoc = find_pandoc()
    command = [pandoc, '--defaults', 'book.yaml']
    subprocess.run(command + ['--to', 'json', '--output', str(build / 'book.json')], check=True, env=env)
    # Build to a temporary destination; publish only after all requested checks pass.
    temporary = build / 'usa-birth.epub'
    subprocess.run(command + ['--output', str(temporary)], check=True, env=env)
    ast = json.loads((build / 'book.json').read_text())
    finalize_titles(temporary, inline_text(ast['meta']['title']))
    report = validate(temporary, ast)
    report['epubcheck'] = 'not requested; run ./package.sh --epubcheck'
    if args.epubcheck:
        jar = Path(os.environ.get('EPUBCHECK_JAR', ROOT / '.tools/epubcheck-5.4.0/epubcheck.jar'))
        require(jar.is_file(), 'Run python3 scripts/setup_tools.py --epubcheck or set EPUBCHECK_JAR.')
        java = os.environ.get('JAVA') or next(iter(sorted((ROOT / '.tools').glob('*/Contents/Home/bin/java'))), None) or shutil.which('java')
        require(java is not None, 'Install Java 11+ or set JAVA to its executable.')
        checked = subprocess.run([str(java), '-jar', str(jar), str(temporary), '--failonwarnings'], capture_output=True, text=True)
        log = checked.stdout + checked.stderr
        (build / 'epubcheck.log').write_text(log)
        print(log.strip())
        require(checked.returncode == 0, 'EPUBCheck failed; see build/epubcheck.log')
        report['epubcheck'] = 'passed (warnings treated as errors)'
    if temporary.resolve() != output:
        shutil.copyfile(temporary, output)
    preview = build / 'epub'
    if preview.exists():
        shutil.rmtree(preview)
    with zipfile.ZipFile(temporary) as archive:
        archive.extractall(preview)
    report['epub'] = str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output)
    report['sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    report['source_date_epoch'] = env['SOURCE_DATE_EPOCH']
    (ROOT / 'output').mkdir(exist_ok=True)
    (ROOT / 'output/validation-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f'Built {output}\nVerified {report["chapters"]} chapters, {report["parts"]} parts, {report["figures_verified"]} figures, {report["footnotes_verified"]} footnotes.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Build failed: {error}', file=sys.stderr)
        sys.exit(1)
