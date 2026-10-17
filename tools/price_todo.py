#!/usr/bin/env python3
"""Checklist for pricing one store: what's left to price, what to search, what to pick.

  python3 tools/price_todo.py heb-tx            # print the checklist (compact)
  python3 tools/price_todo.py heb-tx --tsv      # also write data/todo/heb-tx.tsv to fill in

The TSV has one row per missing item. Fill product, pack_g, price, url (and unranked=1 if the label
can't be trusted), then load it with tools/add_prices.py.
"""
import csv, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / 'data'

def rows(p):
    return list(csv.DictReader(l for l in open(p) if not l.startswith('#')))

def main():
    sid = sys.argv[1]
    stores = {r['id']: r for r in rows(D / 'stores.csv')}
    if sid not in stores:
        sys.exit(f'{sid} not in data/stores.csv. Add the store row first (id,store,market,state,city,location,source,note).')
    st = stores[sid]
    prices = rows(D / 'prices.csv')
    done = {r['item'] for r in prices if r['store'] == st['store'] and r['market'] == st['market']}
    terms = rows(D / 'search_terms.csv')
    todo = [t for t in terms if t['item'] not in done]
    print(f'{sid}: {len(done)} priced, {len(todo)} to go')
    for t in todo:
        print(f"- {t['item']}  [search: {t['search']}]  pick: {t['pick']}")
    if '--tsv' in sys.argv:
        (D / 'todo').mkdir(exist_ok=True)
        out = D / 'todo' / f'{sid}.tsv'
        with open(out, 'w') as f:
            f.write('item\tproduct\tpack_g\tprice\turl\tunranked\n')
            for t in todo:
                f.write(f"{t['item']}\t\t\t\t\t\n")
        print(f'wrote {out.relative_to(ROOT)}')

main()
