"""Keep HTML and its local CSS/JS in sync across browser caches on each deployment."""
import hashlib
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
ASSET_ATTRIBUTE = re.compile(r'''\b(href|src)=(['"])([^'"]+)\2''')


def version_assets(site):
    site = Path(site).resolve()
    versions = {}
    changed = 0
    for page in site.glob('*.html'):
        def replace(match):
            attr, quote, value = match.groups()
            url = urlsplit(value)
            if url.scheme or url.netloc or not url.path.endswith(('.css', '.js')):
                return match.group(0)
            asset = (page.parent / url.path).resolve()
            if not asset.is_relative_to(site) or not asset.is_file():
                raise ValueError(f'Missing local asset in {page.name}: {url.path}')
            if asset not in versions:
                versions[asset] = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
            params = [(key, val) for key, val in parse_qsl(url.query) if key != 'v']
            params.append(('v', versions[asset]))
            versioned = urlunsplit(url._replace(query=urlencode(params)))
            return f'{attr}={quote}{versioned}{quote}'

        original = page.read_text(encoding='utf-8')
        result = ASSET_ATTRIBUTE.sub(replace, original)
        if result != original:
            page.write_text(result, encoding='utf-8')
            changed += 1
    return changed


if __name__ == '__main__':
    print(f'Versioned CSS/JS references in {version_assets(ROOT / "site")} pages')
