#!/usr/bin/env python3
"""Load a filled-in price TSV for one store into data/prices.csv, with sanity checks.

  python3 tools/add_prices.py heb-tx data/todo/heb-tx.tsv [--dry]

TSV columns: item, product, pack_g, price, url, unranked (blank or 1). Blank price = skipped (not sold).
Fills store, market and checked (this month). Replaces existing rows for the same item at that store.
Warns when the price per kg is more than 2.5x off the other stores (usually a pack-size slip).
"""
import csv, sys, pathlib, datetime
ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / 'data'
FIELDS = ['item', 'store', 'market', 'product', 'pack_g', 'price_usd', 'checked', 'price_url', 'unranked']

def main():
    sid, path = sys.argv[1], sys.argv[2]
    dry = '--dry' in sys.argv
    st = {r['id']: r for r in csv.DictReader(l for l in open(D / 'stores.csv') if not l.startswith('#'))}[sid]
    lines = open(D / 'prices.csv').read().splitlines(keepends=True)
    head = [l for l in lines if l.startswith('#')]
    old = list(csv.DictReader(l for l in lines if not l.startswith('#')))
    known = {r['item'] for r in old} | {r['item'] for r in csv.DictReader(l for l in open(D / 'search_terms.csv') if not l.startswith('#'))}
    ref = {}
    for r in old:
        if r['store'] != st['store'] or r['market'] != st['market']:
            ref.setdefault(r['item'], []).append(float(r['price_usd']) / float(r['pack_g']) * 1000)
    month = datetime.date.today().strftime('%Y-%m')
    new, problems = [], []
    for r in csv.DictReader(open(path), delimiter='\t'):
        if not (r.get('price') or '').strip():
            continue
        item = r['item'].strip()
        try:
            g, p = float(r['pack_g']), float(r['price'])
        except ValueError:
            problems.append(f'{item}: pack_g/price not numbers'); continue
        if item not in known: problems.append(f'{item}: unknown item (typo?)')
        if g <= 0 or p <= 0: problems.append(f'{item}: pack_g and price must be > 0')
        if ref.get(item):
            mid = sorted(ref[item])[len(ref[item]) // 2]
            k = p / g * 1000
            if not (mid / 2.5 <= k <= mid * 2.5):
                problems.append(f'{item}: ${k:.2f}/kg vs ${mid:.2f}/kg elsewhere, check pack_g')
        new.append({'item': item, 'store': st['store'], 'market': st['market'], 'product': r['product'].strip(),
                    'pack_g': f'{g:g}', 'price_usd': f'{p:.2f}', 'checked': month,
                    'price_url': r['url'].strip(), 'unranked': (r.get('unranked') or '').strip()})
    for m in problems: print('CHECK', m)
    keys = {(n['item'], n['store'], n['market']) for n in new}
    kept = [r for r in old if (r['item'], r['store'], r['market']) not in keys]
    print(f'{sid}: {len(new)} rows ({len(keys & {(r["item"], r["store"], r["market"]) for r in old})} replaced)')
    if dry: return
    with open(D / 'prices.csv', 'w', newline='') as f:
        f.writelines(head)
        w = csv.DictWriter(f, FIELDS, lineterminator='\n'); w.writeheader()
        for r in kept + new: w.writerow({k: r.get(k, '') for k in FIELDS})

main()
