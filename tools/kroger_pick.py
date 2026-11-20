#!/usr/bin/env python3
"""Turn a Kroger API fetch (data/kroger/<locationId>.json) into a price TSV for tools/add_prices.py.

  python3 tools/kroger_pick.py <locationId> <store id> [--review]

Rules (same as hand pricing): regular price (promo noted), Kroger's own brands first and the cheaper per kg
of those, otherwise the cheapest per kg; produce sold by weight is priced per lb.
data/kroger/picks.csv pins a productId per item when the automatic choice is wrong (item,productId[,pack_g]).
"""
import csv, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / 'data'
OWN = {'kroger', 'simple truth', 'simple truth organic', 'private selection', 'smart way', 'heritage farm'}
OZ, LB = 28.35, 453.6
PRODUCE = {'banana', 'lemon juice and zest', 'garlic', 'rosemary fresh', 'mint fresh', 'parsley fresh', 'yellow squash', 'green beans', 'carrots',
           'red bell pepper', 'yellow bell pepper', 'green bell pepper', 'onion', 'romaine lettuce', 'spinach fresh', 'avocado', 'tomato',
           'cucumber', 'blueberries', 'blackberries', 'sweet potato', 'potatoes russet'}
SKIP = ['big deal', 'trail mix', 'sauce', 'coffee', 'burger', 'patties', 'chops', 'crumbs', 'syrup', 'ice cream', 'dressing']
# item: (words that must all appear in the description, extra words that rule a product out)
MATCH = {
 'whey protein isolate': ('whey', []), 'egg whole': ('large egg', []), 'milk whole': ('whole milk gallon', []),
 'banana': ('banana', ['organic', 'red', 'plantain', 'chips']), 'butter salted': ('salted butter', ['unsalted']),
 'baking powder': ('baking powder', []), 'cinnamon ground': ('ground cinnamon', []),
 'chicken breast': ('boneless skinless chicken breast', ['frozen', 'tenderloin', 'thin']), 'olive oil': ('extra virgin olive oil', ['spray']),
 'lemon juice and zest': ('lemon', ['juice', 'organic', 'lime', 'soda', 'tea', 'pepper']), 'garlic': ('garlic', ['minced', 'powder', 'salt', 'peeled', 'organic']),
 'rosemary fresh': ('rosemary', ['ground', 'leaves', 'dried']), 'kosher salt': ('kosher salt', []),
 'black pepper': ('ground black pepper', []), 'yellow squash': ('squash', ['butternut', 'spaghetti', 'acorn', 'organic', 'zucchini']),
 'green beans': ('green beans', ['canned', 'french style', 'frozen', 'cut green']), 'carrots': ('carrots', ['baby', 'shredded', 'chips', 'organic']),
 'red bell pepper': ('red bell pepper', ['organic', 'roasted', 'corn', 'mix']), 'yellow bell pepper': ('yellow bell pepper', ['organic']),
 'white rice': ('long grain white rice', ['instant', 'microwav', 'boil']), 'red lentils': ('red lentils', ['protein', 'pasta']),
 'onion': ('yellow onion', ['organic']), 'diced tomatoes canned': ('diced tomatoes', ['green chil', 'fire roasted', 'organic']),
 'frozen peas': ('peas', ['snap', 'snow', 'carrots', 'organic', 'canned']), 'cumin ground': ('ground cumin', []),
 'smoked paprika': ('smoked paprika', []), 'greek yogurt plain nonfat': ('plain nonfat greek yogurt', []),
 'rolled oats': ('old fashioned oats', []), 'walnuts': ('walnut', ['candied', 'glazed']), 'chia seeds': ('chia seeds', ['rice', 'quinoa', 'bar', 'pudding']),
 'honey': ('honey', ['graham', 'mustard', 'roasted', 'granola']), 'mint fresh': ('mint', ['chocolate', 'gum', 'tea']),
 'shrimp raw': ('raw shrimp', ['cooked']), 'paprika': ('paprika', ['smoked']), 'italian seasoning': ('italian seasoning', []),
 'tuna canned light drained': ('chunk light tuna in water', ['pouch']), 'chicken canned': ('chicken breast', ['soup', 'salad']),
 'black beans dry': ('black beans', ['can', 'refried', 'seasoned']), 'black beans canned': ('black bean', ['dry', 'refried', 'seasoned', 'organic']),
 'ground turkey 93': ('ground turkey', []), 'ground beef 80/20': ('ground beef', ['grass']),
 'chicken thigh boneless': ('boneless skinless chicken thigh', []), 'pork loin': ('pork loin', ['tenderloin', 'marinated']),
 'tofu firm': ('firm tofu', []), 'cottage cheese': ('cottage cheese', []), 'peanut butter': ('creamy peanut butter', ['reduced', 'natural']),
 'quinoa': ('quinoa', ['protein', 'rice', 'blend', 'microwav']), 'romaine lettuce': ('romaine', ['salad kit', 'caesar']),
 'spinach fresh': ('spinach', ['frozen', 'blend', 'kale', 'dip']), 'avocado': ('avocado', ['organic', 'oil', 'guacamole', 'mini']),
 'tomato': ('roma tomato', ['crushed', 'canned', 'paste', 'diced', 'can']), 'cucumber': ('cucumber', ['organic', 'mini', 'english', 'baby']), 'feta cheese': ('feta', []),
 'mustard yellow': ('yellow mustard', []), 'blueberries': ('blueberries', ['frozen', 'dried', 'organic']),
 'blackberries': ('blackberries', ['frozen', 'organic', 'strawberr']), 'pumpkin seeds': ('pepitas|pumpkin seeds', []),
 'granola': ('granola', ['bar', 'bites']), 'sweet potato': ('sweet potato', ['cut', 'fries', 'chips', 'organic', 'mashed', 'frozen', 'wedge', 'maple', 'pecan']),
 'cheddar cheese': ('cheddar', ['cracker', 'crackers', 'popcorn']), 'potatoes russet': ('russet potato', ['shredded', 'organic', 'mashed']),
 'green bell pepper': ('green bell pepper', ['organic']), 'parsley fresh': ('parsley', ['flakes', 'dried']),
 'chocolate chips': ('chocolate chips', ['cookie']),
}


def relevant(item, desc):
    d = re.sub(r'[®™]', '', (desc or '').lower())
    if any(w in d for w in SKIP):
        return False
    need, bad = MATCH.get(item, (item, []))
    ok = any(all(w in d for w in alt.split()) for alt in need.split('|'))
    return ok and not any(w in d for w in bad)


def ref_pack(item):
    """Typical pack_g for 'each' items (lemon, pepper...) from the stores we already price."""
    gs = [float(r['pack_g']) for r in csv.DictReader(l for l in open(D / 'prices.csv') if not l.startswith('#')) if r['item'] == item]
    return sorted(gs)[len(gs) // 2] if gs else None


def grams(size, item, density):
    s = (size or '').lower().replace('fl. oz', 'fl oz').replace('ounce', 'oz')
    m = re.findall(r'(\d+(?:\.\d+)?(?:/\d+)?)\s*(fl oz|ounce|oz|lb|lbs|gal|ct|count|ea|each|g|kg|qt|pt)\b', s)
    if not m:
        return None
    n, u = m[-1] if not any(x[1] in ('oz', 'lb', 'lbs', 'g', 'kg', 'fl oz') for x in m) else [x for x in m if x[1] in ('oz', 'lb', 'lbs', 'g', 'kg', 'fl oz')][-1]
    n = eval(n) if '/' in n else float(n)  # "1/2 gal"
    pk = re.search(r'/\s*(\d+)\s*pk\b|^(\d+)\s*pk\b', s)
    mult = int([g for g in pk.groups() if g][0]) if pk else 1
    if u == 'oz': g = n * OZ
    elif u in ('lb', 'lbs'): g = n * LB
    elif u == 'g': g = n
    elif u == 'kg': g = n * 1000
    elif u == 'fl oz': g = n * 29.57 * density
    elif u == 'gal': g = n * 3900
    elif u == 'qt': g = n * 975
    elif u == 'pt': g = n * 487
    elif u in ('ct', 'count'): g = n * 50 if item == 'egg whole' else (ref_pack(item) or 0) * n
    else: g = (ref_pack(item) or 0) * n
    return g * mult if g else None


def main():
    loc, sid = sys.argv[1], sys.argv[2]
    data = json.load(open(D / 'kroger' / f'{loc}.json'))
    pins = {}
    pf = D / 'kroger' / 'picks.csv'
    if pf.exists():
        for r in csv.DictReader(l for l in open(pf) if not l.startswith('#')):
            pins[r['item']] = r
    out = open(D / 'todo' / f'{sid}.tsv', 'w')
    out.write('item\tproduct\tpack_g\tprice\turl\tunranked\n')
    for item, v in data.items():
        density = 0.92 if 'oil' in item else 1.0
        cands = []
        for r in v['results']:
            if not r.get('regular') or not relevant(item, r.get('desc')):
                continue
            if r.get('soldBy') == 'WEIGHT':
                g = LB
            else:
                g = grams(r.get('size'), item, density)
            if not g:
                continue
            cands.append({**r, 'g': g, 'perkg': r['regular'] / g * 1000, 'own': (r.get('brand') or '').lower() in OWN})
        pick = None
        if item in pins:
            pick = next((c for c in cands if c['id'] == pins[item]['productId']), None)
            if pick and pins[item].get('pack_g'):
                pick['g'] = float(pins[item]['pack_g'])
        if not pick and cands:
            own = [c for c in cands if c['own']]
            pick = min(cands if item in PRODUCE else (own or cands), key=lambda c: c['perkg'])
        if '--review' in sys.argv:
            print(f"{item[:22]:22} -> " + (f"{pick['brand']}|{pick['desc'][:50]}|{pick['size']}|${pick['regular']}|{pick['g']:.0f}g|${pick['perkg']:.2f}/kg" if pick else 'NONE'))
        if not pick:
            continue
        name = re.sub(r'[®™]', '', pick['desc']).strip()
        note = f" {pick['size']}" if pick.get('size') and pick.get('soldBy') != 'WEIGHT' else ' (sold by weight, per lb)'
        if pick.get('promo') and pick['promo'] < pick['regular']:
            note += f" (regular price - on sale at ${pick['promo']:.2f})"
        out.write('\t'.join([item, name + note, f"{pick['g']:.1f}", f"{pick['regular']:.2f}",
                             f"https://www.kroger.com/p/x/{pick['id']}", '']) + '\n')


main()
