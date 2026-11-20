#!/usr/bin/env python3
"""Fetch store-level prices from the official Kroger Public API (free, 10,000 product calls/day).

Runs in GitHub Actions (.github/workflows/kroger.yml) with repo secrets KROGER_CLIENT_ID / KROGER_CLIENT_SECRET.
Never put the keys in this repo: it is public.

  python3 tools/kroger_fetch.py locations 77021        -> data/kroger/locations-77021.json
  python3 tools/kroger_fetch.py products <locationId>  -> data/kroger/<locationId>.json (top results per search term)

Step 2 (picking the product per item and writing prices.csv rows) is done by tools/kroger_pick.py once
we've checked what the API returns.
"""
import base64, csv, json, os, pathlib, sys, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'kroger'
API = 'https://api.kroger.com/v1'


def token():
    cid, sec = os.environ['KROGER_CLIENT_ID'].strip(), os.environ['KROGER_CLIENT_SECRET'].strip()
    req = urllib.request.Request(f'{API}/connect/oauth2/token', method='POST',
                                 data=b'grant_type=client_credentials&scope=product.compact',
                                 headers={'Authorization': 'Basic ' + base64.b64encode(f'{cid}:{sec}'.encode()).decode(),
                                          'Content-Type': 'application/x-www-form-urlencoded'})
    return json.load(urllib.request.urlopen(req))['access_token']


def get(tok, path, **q):
    url = f'{API}{path}?' + urllib.parse.urlencode(q)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/json'})
            return json.load(urllib.request.urlopen(req))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(5); continue
            raise


def locations(tok, zipcode):
    d = get(tok, '/locations', **{'filter.zipCode.near': zipcode, 'filter.radiusInMiles': 15, 'filter.limit': 20})
    rows = [{'locationId': l['locationId'], 'chain': l.get('chain'), 'name': l.get('name'),
             'address': l.get('address', {}).get('addressLine1'), 'city': l.get('address', {}).get('city'),
             'state': l.get('address', {}).get('state'), 'zip': l.get('address', {}).get('zipCode')}
            for l in d.get('data', [])]
    (OUT / f'locations-{zipcode}.json').write_text(json.dumps(rows, indent=1))
    print(f'{len(rows)} locations near {zipcode}')


def products(tok, loc):
    terms = [r for r in csv.DictReader(l for l in open(ROOT / 'data/search_terms.csv') if not l.startswith('#'))]
    out = {}
    for t in terms:
        d = get(tok, '/products', **{'filter.term': t['search'][:60], 'filter.locationId': loc, 'filter.limit': 12})
        items = []
        for p in d.get('data', []):
            it = (p.get('items') or [{}])[0]
            pr = it.get('price') or {}
            items.append({'id': p.get('productId'), 'brand': p.get('brand'), 'desc': p.get('description'),
                          'size': it.get('size'), 'soldBy': it.get('soldBy'),
                          'regular': pr.get('regular'), 'promo': pr.get('promo')})
        out[t['item']] = {'search': t['search'], 'results': items}
        time.sleep(0.3)
    (OUT / f'{loc}.json').write_text(json.dumps(out, indent=1))
    print(f'{len(out)} items fetched for {loc}')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    tok = token()
    {'locations': locations, 'products': products}[sys.argv[1]](tok, sys.argv[2])
