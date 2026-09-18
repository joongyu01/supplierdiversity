import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from scripts.build_offer_delivery import build


class OfferDeliveryTests(unittest.TestCase):
    def test_batches_reassemble_without_loss_or_duplicate_businesses(self):
        with TemporaryDirectory() as temp:
            site = Path(temp)
            (site / 'data').mkdir()
            businesses = [{'bizno': str(i), 'offers': ['가' * 4000]} for i in range(70)]
            source = {'schemaVersion': 2, 'report': {'scope': 'test'}, 'businesses': businesses}
            (site / 'data/offers.json').write_text(json.dumps(source), encoding='utf-8')
            boot = build(site)
            rebuilt = list(boot['businesses'])
            self.assertLess(len(rebuilt), len(businesses))
            for part in boot['parts']:
                raw = (site / 'data/offer-batches' / part['file']).read_bytes()
                self.assertEqual(part['file'], hashlib.sha256(raw).hexdigest()[:16] + '.json')
                batch = json.loads(raw)
                self.assertEqual(len(batch), part['businesses'])
                rebuilt.extend(batch)
            self.assertEqual(rebuilt, businesses)
            self.assertEqual(boot['report'], source['report'])
            self.assertEqual(boot['totalBusinesses'], len(businesses))

    def test_empty_collection_is_a_valid_complete_snapshot(self):
        with TemporaryDirectory() as temp:
            site = Path(temp)
            (site / 'data').mkdir()
            (site / 'data/offers.json').write_text('{"businesses": []}', encoding='utf-8')
            boot = build(site)
            self.assertEqual(boot['businesses'], [])
            self.assertEqual(boot['parts'], [])
            self.assertEqual(boot['totalBusinesses'], 0)
