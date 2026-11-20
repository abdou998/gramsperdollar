# Pinterest pin images (1000x1500) for every priced recipe -> public/pins/<slug>.jpg.
# Run after mealmath: python3 tools/make_pins.py  (needs Python Playwright + Chromium and node_modules for the fonts).
# Stock photos are labelled "stock photo" on the pin; Sanae's are not.
import json, sys, pathlib, html
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'public' / 'pins'; OUT.mkdir(parents=True, exist_ok=True)
F = ROOT / 'node_modules/@fontsource-variable'
recipes = json.load(open(ROOT / 'src/data/recipes.json'))
stores = json.load(open(ROOT / 'src/data/stores.json'))

def best(r):
    st = r['stores']; k = max(st, key=lambda s: st[s]['protein_g_per_dollar'] or 0); return k, st[k]

def page(r):
    sid, s = best(r)
    total = (r.get('prep_minutes') or 0) + (r.get('cook_minutes') or 0)
    name = r.get('seo_name') or r['name']
    img = (ROOT / 'src/assets/images' / r['image']).as_uri()
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: B; src: url({(F/'bricolage-grotesque/files/bricolage-grotesque-latin-opsz-normal.woff2').as_uri()}) format('woff2'); font-weight: 200 800; }}
@font-face {{ font-family: S; src: url({(F/'source-serif-4/files/source-serif-4-latin-opsz-normal.woff2').as_uri()}) format('woff2'); font-weight: 200 900; }}
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1000px; height: 1500px; background: #f2f4ec; font-family: B; color: #1d2b20; overflow: hidden; }}
.ph {{ position: absolute; left: 40px; top: 40px; width: 920px; height: 860px; border-radius: 90px 22px 90px 22px; overflow: hidden; }}
.ph img {{ width: 100%; height: 100%; object-fit: cover; }}
.tag {{ position: absolute; left: 70px; top: 810px; background: #ffd23f; border-radius: 14px; padding: 18px 28px 20px; box-shadow: inset 0 -8px 0 rgba(0,0,0,.12); display: flex; align-items: flex-end; gap: 14px; }}
.tag b {{ font-size: 104px; font-weight: 800; letter-spacing: -3px; line-height: .9; }}
.tag span {{ font-size: 30px; font-weight: 650; line-height: 1.05; padding-bottom: 8px; }}
.txt {{ position: absolute; left: 70px; right: 70px; top: 990px; }}
h1 {{ font-size: {78 if len(name) < 30 else 66}px; line-height: 1.02; letter-spacing: -2.5px; font-weight: 800; }}
.facts {{ margin-top: 28px; display: flex; gap: 34px; font-size: 38px; font-weight: 650; color: #3d6b35; }}
.foot {{ position: absolute; left: 70px; right: 70px; bottom: 50px; font-family: S; font-size: 30px; color: #566454; display: flex; justify-content: space-between; }}
.foot strong {{ font-family: B; color: #1d2b20; }}
</style></head><body>
<div class="ph"><img src="{img}"></div>
<div class="tag"><b>{s['protein_g_per_dollar']:.1f}</b><span>g protein<br>per $1</span></div>
<div class="txt"><h1>{html.escape(name)}</h1>
<div class="facts"><span>{round(r['protein_g_per_serving'])} g protein</span><span>${s['cost_per_serving']:.2f} a serving</span>{f'<span>{total} min</span>' if total else ''}</div></div>
<div class="foot"><span>Priced at {stores[sid]['store']}, {stores[sid]['city']}{'' if 'Sanae' in (r.get('image_credit') or '') else ' · stock photo'}</span><strong>gramsperdollar.com</strong></div>
</body></html>'''

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1000, 'height': 1500})
    for r in recipes:
        f = pathlib.Path('/tmp') / f"{r['slug']}.html"; f.write_text(page(r))
        pg.goto(f.as_uri()); pg.wait_for_timeout(400)
        pg.screenshot(path=str(OUT / f"{r['slug']}.jpg"), type='jpeg', quality=86)
        print(r['slug'])
    b.close()
