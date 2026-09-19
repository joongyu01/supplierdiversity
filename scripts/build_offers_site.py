"""Join product evidence to the registry strictly by business registration number."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def join_offers(offers, registry):
    businesses = {}
    for offer in offers:
        code = offer.get('bizno', '')
        row = registry.get(code)
        key = code or offer['id']
        if key not in businesses:
            businesses[key] = {'bizno': code, 'name': row[1] if row and row[1] else offer['supplier'],
                               'masks': row[2:7] if row else [0] * 5, 'offers': []}
        businesses[key]['offers'].append(offer)
    return sorted(businesses.values(), key=lambda b: (not bool(b['masks'][0]), b['name'], b['bizno']))


PRODUCT_URL = {'goods': 'https://www.goods.go.kr/pp/pd/product/view.do?goodsCode={}&menuNo=1205000',
               'sepp': 'https://www.sepp.or.kr/goods/value/prdctDtl?goodsNo={}'}


def compact(businesses):
    """Publish contacts once per business and offers as [id, title, category, observedAt, contact].

    site/offers.js restores the original offer fields; the product URL is rebuilt from the source ID.
    """
    result = []
    for b in businesses:
        contacts, index, offers = [], {}, []
        for o in b['offers']:
            source, code = o['id'].split(':', 1)
            if o['url'] != PRODUCT_URL[source].format(code):
                raise ValueError('Product URL does not match its source ID: ' + o['id'])
            key = (source, o.get('supplier', ''), o.get('phone', ''), o.get('address', ''), o.get('sellerUrl', ''))
            if key not in index:
                index[key] = len(contacts)
                contacts.append(dict(zip(('source', 'supplier', 'phone', 'address', 'sellerUrl'), key)))
            offers.append([o['id'], o['title'], o.get('category', ''), o['observedAt'], index[key]])
        result.append({'bizno': b['bizno'], 'name': b['name'], 'masks': b['masks'], 'contacts': contacts, 'offers': offers})
    return result


def validate_collection(offers, report, raw):
    if (report.get('publicationReady') is not True or report.get('scope') != 'all_listed'
            or report.get('listingComplete') is not True or report.get('detailsComplete') is not True
            or report.get('failures') or not offers
            or report.get('collectedProducts') != len(offers)
            or report.get('selectedProducts') != len(offers)):
        raise ValueError('Incomplete collection; existing published file preserved')
    if report.get('offersSha256') != hashlib.sha256(raw).hexdigest():
        raise ValueError('Collection data/report mismatch; existing published file preserved')
    if len({r['id'] for r in offers}) != len(offers):
        raise ValueError('Duplicate source product IDs')


def main():
    path = ROOT / 'data/offers'
    raw = (path / 'public-offers.jsonl').read_bytes()
    offers = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line]
    report = json.loads((path / 'collection-report.json').read_text(encoding='utf-8'))
    validate_collection(offers, report, raw)
    wanted = {r['bizno'] for r in offers if r['bizno']}
    registry = {}
    for part in sorted((ROOT / 'site/data/registry').glob('index-*.json')):
        for row in json.loads(part.read_text(encoding='utf-8')):
            if row[0] in wanted:
                registry[row[0]] = row
    businesses = join_offers(offers, registry)
    manifest = json.loads((ROOT / 'site/data/registry/manifest.json').read_text(encoding='utf-8'))
    report.update({'registryBuiltAt': manifest['builtAt'], 'registryTotal': manifest['total'],
                   'matchedBusinesses': len(registry), 'matchedProducts': sum(bool(registry.get(r['bizno'])) for r in offers),
                   'unmatchedProducts': sum(not bool(registry.get(r['bizno'])) for r in offers),
                   'businessesWithUnverifiedIdentity': sum(not bool(b['bizno']) for b in businesses),
                   'byType': {label: sum(bool(b['masks'][0] & (1 << i)) for b in businesses) for i, label in enumerate(manifest['labels'])}})
    data = {'schemaVersion': 2, 'productUrl': PRODUCT_URL, 'labels': manifest['labels'], 'report': report,
            'businesses': compact(businesses)}
    target = ROOT / 'site/data/offers.json'
    temp = target.with_suffix('.json.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    temp.replace(target)
    (path / 'join-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('coverage','failures')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
