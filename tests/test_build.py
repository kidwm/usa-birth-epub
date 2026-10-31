"""Corrupt real built EPUBs to ensure publication checks reject content loss."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build import validate


class PublicationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book = ROOT / 'output/usa-birth.epub'
        if not cls.book.exists() or not (ROOT / 'build/book.json').exists():
            raise RuntimeError('Run ./package.sh before the regression tests.')
        cls.ast = json.loads((ROOT / 'build/book.json').read_text())
        cls.report = validate(cls.book, cls.ast)
        cls.chapter = cls.report['chapter_paths']['chapter01']

    def reject_change(self, filename, old, new, error):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'broken.epub'
            with zipfile.ZipFile(self.book) as source, zipfile.ZipFile(path, 'w') as target:
                for entry in source.infolist():
                    data = source.read(entry.filename)
                    if entry.filename == filename:
                        self.assertIn(old, data)
                        data = data.replace(old, new, 1)
                    target.writestr(entry, data)
            with self.assertRaisesRegex(ValueError, error):
                validate(path, self.ast)

    def test_missing_prose(self):
        self.reject_change(self.chapter, '說起美國，會聯想起什麼？'.encode(), b'', 'Prose changed')

    def test_altered_image_alt(self):
        self.reject_change(self.chapter, 'alt="美洲原住民"'.encode(), 'alt="錯誤描述"'.encode(), 'Image bytes, alt text, or order changed')

    def test_broken_footnote(self):
        self.reject_change(self.chapter, b'href="#fn1"', b'href="#missing-note"', 'Broken fragment')

    def test_incorrect_navigation_title(self):
        self.reject_change('EPUB/nav.xhtml', '沒錢萬萬不能'.encode(), '錢萬萬不能'.encode(), 'Navigation titles differ')


if __name__ == '__main__':
    unittest.main()
