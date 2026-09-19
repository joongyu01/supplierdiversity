"""Public SEPP / goods.go.kr product evidence, resumable and rate limited.

Only collect public catalog fields. Never use portal footer business numbers.
By default every listed page of every source category is collected (0 = all pages).
Listings are always revalidated. Detail responses expire after 24 hours.
Incomplete batches are saved for diagnosis, never promoted for publication.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import threading
import time
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'private/offer-cache'
OUT = ROOT / 'data/offers'
KST = timezone(timedelta(hours=9))
DEFAULT_CACHE_MAX_AGE_HOURS = 24
LOCK = threading.Lock()
NEXT = {}
INTERVAL = .35
# 꿈드래 상품 대분류: (메뉴 번호, 대분류 코드, 이름)
GOODS_CATEGORIES = [('1202000', '1101', '가구'), ('1203000', '1102', '사무/문구'), ('1204000', '1103', '의류/침구'),
                    ('1205000', '1104', '식품'), ('1206000', '1105', '생활용품'), ('1207000', '1106', '일회용품'),
                    ('1208000', '1107', '인쇄/광고'), ('1209000', '1108', '디지털/가전'), ('1210000', '1109', '시설/설비'),
                    ('1211000', '1110', '공예'), ('1212000', '1111', '화훼'), ('1213000', '1112', '서비스')]


def clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def bizno(s):
    value = re.sub(r'\D', '', s or '')
    return value if len(value) == 10 else ''


def utc_now():
    return datetime.now(timezone.utc)


def fetch(url, refresh=False, max_age_hours=DEFAULT_CACHE_MAX_AGE_HOURS):
    key = hashlib.sha256(url.encode()).hexdigest()
    path = CACHE / (key + '.json')
    if path.exists() and not refresh:
        try:
            saved = json.loads(path.read_text(encoding='utf-8'))
            fetched_at = datetime.fromisoformat(saved['fetchedAt'])
            age = (utc_now() - fetched_at).total_seconds()
            if (saved['url'] == url and isinstance(saved['html'], str)
                    and saved['observedAt'] == fetched_at.astimezone(KST).date().isoformat()
                    and 0 <= age < max_age_hours * 3600):
                return BeautifulSoup(saved['html'], 'html.parser'), saved['observedAt']
        except (ValueError, KeyError, TypeError):
            pass  # Legacy, malformed or incomplete cache entries must be fetched again.
    host = urlparse(url).hostname
    for attempt in range(5):
        with LOCK:
            wait = max(0, NEXT.get(host, 0) - time.monotonic())
            NEXT[host] = time.monotonic() + wait + INTERVAL
        time.sleep(wait)
        try:
            with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; SupplierDirectory/1.0)', 'Accept': 'text/html'}), timeout=35) as r:
                html = r.read().decode('utf-8')
            if '<html' not in html.lower() and '<form' not in html.lower():
                raise ValueError('Unexpected page format')
            CACHE.mkdir(parents=True, exist_ok=True)
            temp = CACHE / (key + f'.{threading.get_ident()}.tmp')
            fetched_at = utc_now()
            observed = fetched_at.astimezone(KST).date().isoformat()
            temp.write_text(json.dumps({'url': url, 'fetchedAt': fetched_at.isoformat(),
                                        'observedAt': observed, 'html': html}, ensure_ascii=False), encoding='utf-8')
            temp.replace(path)
            return BeautifulSoup(html, 'html.parser'), observed
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def field_pairs(soup, kind):
    result = {}
    if kind == 'goods':
        for field in soup.select('.f_field'):
            key, val = field.select_one('.ff_title'), field.select_one('.ff_wrap')
            if key and val:
                result[clean(key.get_text(' ', strip=True))] = clean(val.get_text(' ', strip=True))
    else:
        for dt in soup.select('dt'):
            dd = dt.find_next_sibling('dd')
            if dd:
                result[clean(dt.get_text(' ', strip=True))] = clean(dd.get_text(' ', strip=True))
    return result


def goods_detail(code, refresh=False, max_age_hours=DEFAULT_CACHE_MAX_AGE_HOURS):
    url = f'https://www.goods.go.kr/pp/pd/product/view.do?goodsCode={code}&menuNo=1205000'
    soup, observed = fetch(url, refresh, max_age_hours)
    f = field_pairs(soup, 'goods')
    if f.get('상품코드') != code or not f.get('상품명'):
        raise ValueError('Product identity missing or different')
    return {'id': 'goods:' + code, 'source': 'goods', 'title': f['상품명'],
            'category': f.get('상품 분류', ''), 'bizno': bizno(f.get('사업자등록번호')),
            'supplier': f.get('시설명', f.get('생산시설명', '')), 'phone': f.get('전화번호', ''),
            'address': f.get('주소', ''), 'url': url, 'observedAt': observed}


def sepp_detail(code, refresh=False, max_age_hours=DEFAULT_CACHE_MAX_AGE_HOURS):
    url = f'https://www.sepp.or.kr/goods/value/prdctDtl?goodsNo={code}'
    soup, observed = fetch(url, refresh, max_age_hours)
    ld = soup.select_one('script[type="application/ld+json"]')
    product = json.loads(ld.get_text()) if ld else {}
    seller = soup.select_one('a[href*="/main/value/sclentIntrDtl?slrNo="]')
    if not product.get('name') or not seller:
        raise ValueError('Product name or seller link missing')
    sid = parse_qs(urlparse(seller['href']).query)['slrNo'][0]
    seller_url = 'https://www.sepp.or.kr/main/value/sclentIntrDtl?slrNo=' + sid
    seller_soup, seller_observed = fetch(seller_url, refresh, max_age_hours)
    f = field_pairs(seller_soup, 'sepp')
    if not f.get('기업명'):
        raise ValueError('Seller page unavailable')
    return {'id': 'sepp:' + code, 'source': 'sepp', 'title': clean(product['name']),
            'category': '', 'bizno': bizno(f.get('사업자번호')), 'supplier': f['기업명'],
            'phone': f.get('대표번호', ''), 'address': f.get('주소', ''),
            'url': url, 'sellerUrl': seller_url, 'observedAt': observed,
            'sellerObservedAt': seller_observed}


def listing(soup, source):
    param = 'goodsNo' if source == 'sepp' else 'goodsCode'
    ids = []
    for a in soup.select(f'a[href*="{param}="]'):
        value = parse_qs(urlparse(a['href']).query).get(param, [''])[0]
        if value.isdigit() and value not in ids:
            ids.append(value)
    if source == 'sepp':
        total = soup.select_one('.total strong')
        total = int(total.get_text().replace(',', '')) if total else None
    else:
        m = re.search(r'총\s*([\d,]+)\s*개의', soup.get_text(' ', strip=True))
        total = int(m[1].replace(',', '')) if m else None
    if total is None or (total and not ids):
        raise ValueError('Catalog total or product links missing')
    return ids, total


def atomic_write(path, content):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes(content)
    temp.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sepp-pages', type=int, default=0, help='0 = all pages')
    parser.add_argument('--goods-pages', type=int, default=0, help='0 = all pages')
    parser.add_argument('--goods-categories', default='', help='comma separated names, empty = all')
    parser.add_argument('--interval', type=float, default=INTERVAL, help='seconds between requests per host')
    parser.add_argument('--workers', type=int, default=4,
                        help='동시 요청 스레드. 요청 간격은 그대로 지켜지므로 초당 요청 수는 --interval 이 정합니다.')
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--cache-max-age-hours', type=float, default=DEFAULT_CACHE_MAX_AGE_HOURS,
                        help='상세 응답 캐시 유효시간 (기본 24시간). 목록은 항상 재조회합니다.')
    args = parser.parse_args(argv)
    if args.sepp_pages < 0 or args.goods_pages < 0 or args.workers < 1:
        parser.error('page limits must be nonnegative and workers must be positive')
    if not math.isfinite(args.interval) or args.interval < .35:
        parser.error('interval must be at least 0.35 seconds per host')
    if not math.isfinite(args.cache_max_age_hours) or args.cache_max_age_hours <= 0:
        parser.error('cache-max-age-hours must be finite and positive')
    globals()['INTERVAL'] = args.interval
    wanted = {c.strip() for c in args.goods_categories.split(',') if c.strip()}
    available = {name for _, _, name in GOODS_CATEGORIES}
    if wanted - available:
        parser.error('unknown goods categories: ' + ', '.join(sorted(wanted - available)))
    OUT.mkdir(parents=True, exist_ok=True)
    groups = [('sepp', '가치장터 인기 상품', None, None)] + [
        ('goods', name, menu, code) for menu, code, name in GOODS_CATEGORIES if not wanted or name in wanted]
    jobs, coverage, failures = {}, [], []
    for source, label, menu, category in groups:
        # 꿈드래 분류 첫 화면(index.do)은 무겁고 자주 끊겨서 목록 URL을 직접 씁니다.
        goods_list = lambda offset: (f'https://www.goods.go.kr/pp/pd/product/list.do?menuNo={menu}&condition.pageType=D'
                                     f'&condition.goodsLclasCode={category}&maxPageItems=10&pagerOffset={offset}')
        seed = 'https://www.sepp.or.kr/main/sclentIntrGdsLst' if source == 'sepp' else goods_list(0)
        try:
            soup, observed = fetch(seed, refresh=True)
            ids, total = listing(soup, source)
        except Exception as e:
            failures.append({'source': source, 'url': seed, 'error': type(e).__name__})
            coverage.append({'source': source, 'label': label, 'url': seed,
                             'sourceTotal': None, 'listedProducts': 0, 'scopeComplete': False})
            continue
        limit = args.sepp_pages if source == 'sepp' else args.goods_pages
        pages = math.ceil(total / 10) if limit <= 0 else min(limit, math.ceil(total / 10))
        urls = []
        for page in range(2, pages + 1):
            urls.append(f'{seed}?page={page}' if source == 'sepp' else goods_list((page - 1) * 10))
        seen = set(ids)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(fetch, u, True): u for u in urls}
            for future in as_completed(futures):
                try:
                    page_ids, page_total = listing(future.result()[0], source)
                    if page_total != total:
                        raise ValueError('Catalog total changed during pagination')
                    seen.update(page_ids)
                except Exception as e:
                    failures.append({'source': source, 'url': futures[future], 'error': type(e).__name__})
        coverage.append({'source': source, 'label': label, 'url': seed, 'observedAt': observed,
                         'sourceTotal': total, 'pageLimit': limit or pages, 'listedProducts': len(seen),
                         'scopeComplete': len(seen) == total})
        for code in sorted(seen):
            jobs[(source, code)] = code
        print(label, 'sourceTotal', total, 'selected', len(seen), 'listPageFailures',
              sum(f.get('source') == source and 'url' in f for f in failures), flush=True)
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(sepp_detail if src == 'sepp' else goods_detail,
                               code, args.refresh, args.cache_max_age_hours): (src, code)
                   for src, code in jobs}
        for i, future in enumerate(as_completed(futures), 1):
            src, code = futures[future]
            try:
                rows.append(future.result())
            except Exception as e:
                failures.append({'source': src, 'id': code, 'error': type(e).__name__})
            if i % 500 == 0:
                print('details', i, '/', len(jobs), 'failures', len(failures), flush=True)
    rows.sort(key=lambda x: x['id'])
    listing_complete = (not wanted or wanted == available) and all(c['scopeComplete'] for c in coverage)
    details_complete = len(rows) == len(jobs) and not any('id' in f for f in failures)
    ready = bool(rows) and listing_complete and details_complete and not failures
    content = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows).encode('utf-8')
    observed_dates = [r[k] for r in rows for k in ('observedAt', 'sellerObservedAt') if r.get(k)]
    report = {'builtAt': utc_now().astimezone(KST).date().isoformat(),
              'scope': 'all_listed' if ready else 'partial', 'coverage': coverage,
              'selectedProducts': len(jobs), 'collectedProducts': len(rows), 'failures': failures,
              'listingComplete': listing_complete, 'detailsComplete': details_complete,
              'publicationReady': ready, 'offersSha256': hashlib.sha256(content).hexdigest(),
              'oldestObservedAt': min(observed_dates, default=None),
              'newestObservedAt': max(observed_dates, default=None)}
    report_bytes = json.dumps(report, ensure_ascii=False, indent=2).encode('utf-8')
    # Attempt artifacts never replace the last verified snapshot on a partial run.
    atomic_write(OUT / 'candidate-offers.jsonl', content)
    atomic_write(OUT / 'collection-attempt.json', report_bytes)
    print(json.dumps({k:v for k,v in report.items() if k != 'coverage'}, ensure_ascii=False), flush=True)
    if not ready:
        raise RuntimeError('Incomplete collection; previous output preserved. See collection-attempt.json and candidate-offers.jsonl')
    # The builder verifies the digest, so an interruption between these two
    # replacements cannot publish a data/report pair from different runs.
    atomic_write(OUT / 'public-offers.jsonl', content)
    atomic_write(OUT / 'collection-report.json', report_bytes)


if __name__ == '__main__':
    main()
