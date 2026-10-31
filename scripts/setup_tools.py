#!/usr/bin/env python3
"""Download checksum-pinned official tools into this repository's .tools/."""
import argparse
import hashlib
import io
from pathlib import Path
import platform
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PANDOC_VERSION = '3.13'
EPUBCHECK_VERSION = '5.4.0'
PANDOC_ARCHIVES = {
    ('Darwin', 'arm64'): ('arm64-macOS.zip', 'f436d18bebbfb3ddd326597686dacab9fac5dc23bd060495020f35a28a43a7c3'),
    ('Darwin', 'x86_64'): ('x86_64-macOS.zip', '1823278715aa405aaf21b59cde5dc789346aa8d4fc307467f9a9ee84162bedc5'),
    ('Linux', 'x86_64'): ('linux-amd64.tar.gz', '38aa33b325a2bc96a4c39409631212db55702f564250bcdbead180b3bf646389'),
    ('Linux', 'aarch64'): ('linux-arm64.tar.gz', '21e1d4ba09bd0b334590d204580fd4f6629b21be4ab6a32b26cc98982e9e0c68'),
}


def install(url, checksum):
    print('Downloading', url, flush=True)
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != checksum:
        raise SystemExit('Checksum mismatch; archive was not extracted.')
    target = ROOT / '.tools'
    target.mkdir(exist_ok=True)
    if url.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            archive.extractall(target)
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            # Only official, checksum-verified archives reach this extraction.
            archive.extractall(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--epubcheck', action='store_true', help='Also download EPUBCheck (requires Java 11+).')
    args = parser.parse_args()
    key = (platform.system(), platform.machine())
    if key not in PANDOC_ARCHIVES:
        raise SystemExit('Install Pandoc 3.13 manually on this platform and put it on PATH.')
    suffix, checksum = PANDOC_ARCHIVES[key]
    if not list((ROOT / '.tools').glob('pandoc-3.13*/bin/pandoc')):
        install(f'https://github.com/jgm/pandoc/releases/download/{PANDOC_VERSION}/pandoc-{PANDOC_VERSION}-{suffix}', checksum)
    for binary in (ROOT / '.tools').glob('pandoc-3.13*/bin/pandoc*'):
        binary.chmod(binary.stat().st_mode | 0o111)
    if args.epubcheck and not (ROOT / '.tools/epubcheck-5.4.0/epubcheck.jar').exists():
        install('https://github.com/w3c/epubcheck/releases/download/v5.4.0/epubcheck-5.4.0.zip',
                '33350c61038e71dfb3d45a76aed04bf5481e6d5500cb780f6e98db8bbd15a28c')
    print('Tools ready in', ROOT / '.tools')


if __name__ == '__main__':
    main()
