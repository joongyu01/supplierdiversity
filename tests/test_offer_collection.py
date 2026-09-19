"""Offline regression tests for cache freshness and complete-snapshot publication."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timedelta, timezone
import hashlib
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import collect_offers as collector
from scripts import build_offers_site as builder
from scripts.build_offer_delivery import build as build_delivery


NOW = datetime(2026, 9, 19, 15, 30, tzinfo=timezone.utc)
URL = 'https://www.goods.go.kr/fixture'


class CacheFreshnessTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.cache = Path(temp.name)
        for target, value in [('CACHE', self.cache), ('utc_now', lambda: NOW)]:
            p = patch.object(collector, target, value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(collector, 'urlopen')
        self.network = p.start()
        self.addCleanup(p.stop)
        self.network.return_value.__enter__.return_value.read.return_value = b'<html>NEW</html>'
        p = patch.object(collector.time, 'sleep')
        p.start()
        self.addCleanup(p.stop)
        collector.NEXT.clear()
        self.addCleanup(collector.NEXT.clear)

    def save(self, fetched_at=NOW - timedelta(hours=1), **overrides):
        saved = {'url': URL, 'fetchedAt': fetched_at.isoformat(),
                 'observedAt': fetched_at.astimezone(collector.KST).date().isoformat(),
                 'html': '<html>OLD</html>'}
        saved.update(overrides)
        path = self.cache / (hashlib.sha256(URL.encode()).hexdigest() + '.json')
        path.write_text(json.dumps(saved), encoding='utf-8')
        return path

    def test_fresh_cache_keeps_actual_observation_date_without_network(self):
        self.save()
        soup, observed = collector.fetch(URL)
        self.assertEqual(soup.get_text(), 'OLD')
        self.assertEqual(observed, '2026-09-19')
        self.network.assert_not_called()

    def test_cache_expires_at_ttl_boundary(self):
        path = self.save(NOW - timedelta(hours=24))
        soup, observed = collector.fetch(URL)
        self.assertEqual((soup.get_text(), observed), ('NEW', '2026-09-20'))
        self.network.assert_called_once()
        self.assertEqual(json.loads(path.read_text())['fetchedAt'], NOW.isoformat())

    def test_force_refresh_and_custom_ttl(self):
        for options in ({'refresh': True}, {'max_age_hours': .5}):
            with self.subTest(options=options):
                self.save()
                self.network.reset_mock()
                self.assertEqual(collector.fetch(URL, **options)[0].get_text(), 'NEW')
                self.network.assert_called_once()

    def test_legacy_and_invalid_cache_are_revalidated(self):
        for changes in ({'fetchedAt': None}, {'fetchedAt': 'invalid'},
                        {'fetchedAt': NOW.replace(tzinfo=None).isoformat()},
                        {'fetchedAt': (NOW + timedelta(hours=1)).isoformat()},
                        {'url': 'https://example.invalid/wrong'}, {'html': None},
                        {'observedAt': '2000-01-01'}):
            with self.subTest(changes=changes):
                self.save(**changes)
                self.network.reset_mock()
                self.assertEqual(collector.fetch(URL)[0].get_text(), 'NEW')
                self.network.assert_called_once()
        path = self.save()
        saved = json.loads(path.read_text())
        del saved['fetchedAt']
        path.write_text(json.dumps(saved), encoding='utf-8')
        self.assertEqual(collector.fetch(URL)[0].get_text(), 'NEW')
        path.write_text('{broken', encoding='utf-8')
        self.assertEqual(collector.fetch(URL)[0].get_text(), 'NEW')

    def test_failed_refresh_does_not_relabel_or_overwrite_old_evidence(self):
        path = self.save(NOW - timedelta(days=2))
        original = path.read_bytes()
        self.network.side_effect = TimeoutError('offline fixture')
        with self.assertRaises(TimeoutError):
            collector.fetch(URL)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(self.network.call_count, 5)


class CollectionPublicationTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.out = self.root / 'data/offers'
        self.out.mkdir(parents=True)
        self.raw_path = self.out / 'public-offers.jsonl'
        self.report_path = self.out / 'collection-report.json'
        self.raw_path.write_bytes(b'{"id":"previous"}\n')
        self.report_path.write_bytes(b'{"previous":true}')
        self.previous = (self.raw_path.read_bytes(), self.report_path.read_bytes())
        self.ids = ['101', '102']
        self.total = 2
        self.page_total = None
        self.failed_detail = None
        self.failed_listing = None
        self.fetches = []
        self.detail_options = []
        for name, value in [('OUT', self.out), ('utc_now', lambda: NOW),
                            ('fetch', self.fetch), ('listing', self.listing),
                            ('sepp_detail', self.detail)]:
            p = patch.object(collector, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(collector, 'goods_detail', side_effect=AssertionError('Unexpected goods detail'))
        p.start()
        self.addCleanup(p.stop)

    def fetch(self, url, refresh=False, max_age_hours=24):
        self.fetches.append((url, refresh))
        if self.failed_listing and self.failed_listing(url):
            raise TimeoutError('fixture listing failure')
        return url, '2026-09-20'

    def listing(self, url, source):
        if source != 'sepp':
            return [], 0
        if '?page=' in url:
            return ['111'], self.page_total if self.page_total is not None else self.total
        return list(self.ids), self.total

    def detail(self, code, refresh=False, max_age_hours=24):
        self.detail_options.append((refresh, max_age_hours))
        if code == self.failed_detail:
            raise TimeoutError('fixture detail failure')
        return {'id': 'sepp:' + code, 'source': 'sepp', 'title': '가상 상품 ' + code,
                'supplier': '가상 공급사', 'bizno': '1234567890', 'phone': '02-000-0000',
                'address': '가상 주소', 'observedAt': '2026-09-19', 'sellerObservedAt': '2026-09-19',
                'url': builder.PRODUCT_URL['sepp'].format(code)}

    def run_collection(self, *args):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            collector.main(['--workers', '1', *args])

    def assert_preserved(self, *args):
        with self.assertRaisesRegex(RuntimeError, 'previous output preserved'):
            self.run_collection(*args)
        self.assertEqual((self.raw_path.read_bytes(), self.report_path.read_bytes()), self.previous)
        report = json.loads((self.out / 'collection-attempt.json').read_text(encoding='utf-8'))
        self.assertFalse(report['publicationReady'])
        self.assertEqual(report['scope'], 'partial')
        return report

    def test_one_failed_detail_preserves_previous_snapshot(self):
        self.failed_detail = '102'
        report = self.assert_preserved()
        self.assertTrue(report['listingComplete'])
        self.assertFalse(report['detailsComplete'])
        self.assertEqual((report['selectedProducts'], report['collectedProducts']), (2, 1))
        self.assertEqual(len((self.out / 'candidate-offers.jsonl').read_text(encoding='utf-8').splitlines()), 1)

    def test_first_listing_failure_preserves_previous_snapshot(self):
        self.failed_listing = lambda url: 'sepp.or.kr' in url
        report = self.assert_preserved()
        self.assertFalse(report['listingComplete'])
        self.assertEqual(len(report['failures']), 1)

    def test_later_listing_failure_preserves_previous_snapshot(self):
        self.ids = [str(i) for i in range(101, 111)]
        self.total = 11
        self.failed_listing = lambda url: '?page=' in url
        self.assertFalse(self.assert_preserved()['listingComplete'])

    def test_changing_total_during_pagination_is_rejected(self):
        self.ids = [str(i) for i in range(101, 111)]
        self.total, self.page_total = 11, 12
        report = self.assert_preserved()
        self.assertEqual(report['failures'][0]['error'], 'ValueError')

    def test_missing_ids_even_without_request_errors_are_incomplete(self):
        self.total = 3
        report = self.assert_preserved()
        self.assertEqual(report['failures'], [])
        self.assertFalse(report['listingComplete'])

    def test_partial_category_or_page_limits_cannot_replace_full_catalog(self):
        self.assert_preserved('--goods-categories', '가구')
        self.ids = [str(i) for i in range(101, 111)]
        self.total = 11
        self.assert_preserved('--sepp-pages', '1')

    def test_empty_collection_preserves_previous_snapshot(self):
        self.ids, self.total = [], 0
        self.assertEqual(self.assert_preserved()['collectedProducts'], 0)

    def test_complete_collection_has_matching_digest_and_fresh_listings(self):
        self.run_collection('--refresh', '--cache-max-age-hours', '6')
        raw = self.raw_path.read_bytes()
        offers = [json.loads(line) for line in raw.splitlines()]
        report = json.loads(self.report_path.read_text(encoding='utf-8'))
        builder.validate_collection(offers, report, raw)
        self.assertTrue(report['publicationReady'])
        self.assertEqual(report['builtAt'], '2026-09-20')
        self.assertEqual(report['oldestObservedAt'], '2026-09-19')
        self.assertEqual(len(self.fetches), 13)
        self.assertTrue(all(refresh for _, refresh in self.fetches))
        self.assertEqual(self.detail_options, [(True, 6), (True, 6)])

    def test_complete_list_can_remove_products_without_treating_failure_as_deletion(self):
        self.run_collection()
        self.ids, self.total = ['101'], 1
        self.run_collection()
        self.assertEqual(len(self.raw_path.read_text(encoding='utf-8').splitlines()), 1)
        self.assertTrue(json.loads(self.report_path.read_text(encoding='utf-8'))['publicationReady'])

    def test_invalid_options_fail_before_touching_outputs(self):
        for args in [('--goods-categories', '오타'), ('--workers', '0'), ('--sepp-pages', '-1'),
                     ('--cache-max-age-hours', 'nan'), ('--interval', '.1')]:
            with self.subTest(args=args), self.assertRaises(SystemExit):
                self.run_collection(*args)
        self.assertEqual(self.fetches, [])
        self.assertEqual((self.raw_path.read_bytes(), self.report_path.read_bytes()), self.previous)

    def prepare_site(self):
        site = self.root / 'site/data'
        registry = site / 'registry'
        registry.mkdir(parents=True)
        (registry / 'manifest.json').write_text(json.dumps({'builtAt': '2026-09-19', 'total': 1, 'labels': ['유형']}), encoding='utf-8')
        (registry / 'index-0.json').write_text(json.dumps([['1234567890', '등록 공급사', 1, 0, 0, 0, 1]]), encoding='utf-8')
        target = site / 'offers.json'
        target.write_bytes(b'previous published output')
        return target

    def test_complete_collection_build_and_delivery_keep_public_contacts(self):
        self.run_collection()
        target = self.prepare_site()
        with patch.object(builder, 'ROOT', self.root), redirect_stdout(StringIO()):
            builder.main()
        data = json.loads(target.read_text(encoding='utf-8'))
        self.assertEqual(data['report']['matchedProducts'], 2)
        self.assertEqual(data['businesses'][0]['contacts'][0]['phone'], '02-000-0000')
        self.assertEqual(data['businesses'][0]['bizno'], '1234567890')
        boot = build_delivery(self.root / 'site')
        self.assertEqual(boot['businesses'], data['businesses'])

    def test_builder_rejects_incomplete_mismatched_or_legacy_report_without_replacing_site(self):
        self.run_collection()
        original_report = json.loads(self.report_path.read_text(encoding='utf-8'))
        target = self.prepare_site()
        for change in ({'publicationReady': False}, {'scope': 'partial'}, {'listingComplete': False},
                       {'detailsComplete': False}, {'selectedProducts': 3}, {'collectedProducts': 1},
                       {'failures': [{'id': '102'}]}, {'offersSha256': 'wrong'}, {'publicationReady': None}):
            with self.subTest(change=change):
                self.report_path.write_text(json.dumps({**original_report, **change}), encoding='utf-8')
                with patch.object(builder, 'ROOT', self.root), self.assertRaises(ValueError):
                    builder.main()
                self.assertEqual(target.read_bytes(), b'previous published output')

    def test_builder_rejects_changed_bytes_even_with_same_count(self):
        self.run_collection()
        raw = self.raw_path.read_bytes().replace(b'101', b'999')
        report = json.loads(self.report_path.read_text(encoding='utf-8'))
        offers = [json.loads(line) for line in raw.splitlines()]
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            builder.validate_collection(offers, report, raw)


if __name__ == '__main__':
    unittest.main()
