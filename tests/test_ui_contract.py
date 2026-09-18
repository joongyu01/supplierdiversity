"""Catch missing static entry points/assets before deploying a data-only update."""
from pathlib import Path
from urllib.parse import urlsplit
import unittest
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]

class PublishedUIContractTests(unittest.TestCase):
    def test_entry_points_and_local_assets_exist(self):
        for name in ['index.html', 'offers.html', 'catalog.html', 'cancellations.html', 'product-search.html']:
            with self.subTest(page=name):
                page = ROOT / 'site' / name
                self.assertTrue(page.is_file(), f'Missing entry point: {name}')
                soup = BeautifulSoup(page.read_text(encoding='utf-8'), 'html.parser')
                ids = [tag['id'] for tag in soup.select('[id]')]
                self.assertEqual(len(ids), len(set(ids)), f'Duplicate element IDs: {name}')
                for tag, attr in [('script[src]', 'src'), ('link[rel=stylesheet]', 'href'), ('img[src]', 'src')]:
                    for node in soup.select(tag):
                        uri = urlsplit(node[attr])
                        if not uri.scheme and not uri.netloc:
                            self.assertTrue((page.parent / uri.path).is_file(), node[attr])
                for a in soup.select('nav a[href]'):
                    target = urlsplit(a['href']).path
                    self.assertTrue((page.parent / (target + 'index.html' if target.endswith('/') else target)).is_file(), a['href'])

    def test_offer_controls_survive_template_updates(self):
        soup = BeautifulSoup((ROOT / 'site/offers.html').read_text(encoding='utf-8'), 'html.parser')
        for key in ['category', 'subcategory', 'category-search', 'category-buttons', 'subcategory-buttons', 'q', 'type', 'extra', 'status', 'source', 'pending', 'active-filters', 'results-top', 'source-details']:
            self.assertIsNotNone(soup.find(id=key), key)

if __name__ == '__main__':
    unittest.main()
