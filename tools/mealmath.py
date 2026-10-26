"""
mealmath.py — turn recipes + nutrition + prices into the numbers the site publishes.

Inputs
  data/nutrition.csv     protein and kcal per 100 g, and the source.
  data/prices.csv        one row per (ingredient, store): pack size, price, month checked.
  data/recipes/*.toml    one file per recipe: servings, ingredients (grams + display amount),
                         steps, storage, tip, optional image. `optional = true` marks extras.
  data/plans/*.toml      multi-day plans: which recipes, how many servings of each.

Output
  src/data/recipes.json  per recipe: display fields + protein/kcal per serving and, per store
                         that prices every core ingredient, cost per serving, grams of protein
                         per dollar and the oldest price date.
  src/data/plans.json    per plan: daily totals and a shopping list (packs to buy per store),
                         with small-quantity pantry items listed separately.
  src/data/protein_rank.json  per store: the staples in data/protein_sources.csv ranked by grams
                         of protein per $1 (whole pack at the shelf price).

Usage
  python tools/mealmath.py            # rebuild both JSON files
  python tools/mealmath.py --print    # also print a summary

Standard library only (Python 3.11+). Cost counts only the grams used, not the whole pack.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NUTRITION = ROOT / "data" / "nutrition.csv"
PRICES = ROOT / "data" / "prices.csv"
RECIPES_DIR = ROOT / "data" / "recipes"
PLANS_DIR = ROOT / "data" / "plans"
OUT_RECIPES = ROOT / "src" / "data" / "recipes.json"
OUT_PLANS = ROOT / "src" / "data" / "plans.json"
SOURCES = ROOT / "data" / "protein_sources.csv"   # staples ranked on the cheapest-protein pages
OUT_RANK = ROOT / "src" / "data" / "protein_rank.json"
OUT_BOOK = ROOT / "src" / "data" / "pricebook.json"
OUT_STORES = ROOT / "src" / "data" / "stores.json"   # store + state metadata for the site   # what the in-browser meal planner prices with

AISLES = ROOT / "data" / "aisles.csv"     # shopping lists are grouped by store aisle
PANTRY = ROOT / "data" / "pantry.txt"   # staples listed apart from the checkout total
# Tolerance when rounding packs up (120 g of pepper is 1 pepper of ~119 g, not 2).
PACK_SLACK = 0.02

DISPLAY_FIELDS = ("published", "seo_name", "author", "intro", "meal", "cuisine", "tags", "description", "prep_minutes", "cook_minutes", "steps", "storage", "tip",
                  "image", "image_alt", "image_credit")


def _num(value: str, where: str) -> float:
    try:
        return float(value)
    except ValueError:
        sys.exit(f"{where}: '{value}' is not a number")


def load_nutrition(path: Path) -> dict[str, dict]:
    out = {}
    with path.open(newline="", encoding="utf-8") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            item = row["item"].strip().lower()
            if item:
                where = f"nutrition.csv line {n} ({item})"
                out[item] = {"protein": _num(row["protein_g_per_100g"], where),
                             "kcal": _num(row["kcal_per_100g"], where)}
    return out


STORES = ROOT / "data" / "stores.csv"   # which store + state each price set comes from
FREE_ITEMS = {"water"}                  # costs nothing at any store


def load_stores(path: Path) -> dict[str, dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
    return {r["id"].strip(): {k: v.strip() for k, v in r.items()} for r in rows}


def store_id(store: str, market: str) -> str:
    # "H-E-B" + "TX" -> "heb-tx": letters and digits only, so ids match data/stores.csv.
    return f"{''.join(c for c in store.lower() if c.isalnum())}-{market.strip().lower()}"


def load_prices(path: Path, stores: dict[str, dict]) -> dict[str, dict[str, dict]]:
    """item -> store id (e.g. 'walmart-ca') -> price row."""
    book: dict[str, dict[str, dict]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            item = row["item"].strip().lower()
            if not item or not row["price_usd"].strip():
                continue
            where = f"prices.csv line {n} ({item})"
            sid = store_id(row["store"], row.get("market") or "")
            if sid not in stores:
                sys.exit(f"{where}: store '{sid}' is not in data/stores.csv")
            pack = _num(row["pack_g"], where)
            if pack <= 0:
                sys.exit(f"{where}: pack_g must be > 0")
            book[item][sid] = {
                "product": row["product"].strip(),
                "pack_g": pack,
                "price": _num(row["price_usd"], where),
                "checked": row["checked"].strip(),
                "url": row.get("price_url", "").strip(),
                "unranked": (row.get("unranked") or "").strip().lower() in ("yes", "y", "1", "true"),
            }
    for item in FREE_ITEMS:
        for sid in stores:
            book[item].setdefault(sid, {"product": "Tap water", "pack_g": 1000, "price": 0.0, "checked": "",
                                        "url": "", "unranked": True})
    return book


def recipe_numbers(recipe: dict, nutrition: dict, prices: dict) -> dict:
    servings = recipe["servings"]
    lines = [{
        "item": i["item"].strip().lower(),
        "grams": float(i["grams"]),
        "amount": i.get("amount", f"{i['grams']} g"),
        "label": i.get("label", i["item"]),
        "optional": bool(i.get("optional", False)),
    } for i in recipe["ingredients"]]
    core = [l for l in lines if not l["optional"]]

    def totals(subset):
        p = sum(l["grams"] * nutrition[l["item"]]["protein"] / 100 for l in subset if l["item"] in nutrition)
        k = sum(l["grams"] * nutrition[l["item"]]["kcal"] / 100 for l in subset if l["item"] in nutrition)
        return p, k

    core_p, core_k = totals(core)
    all_p, all_k = totals(lines)

    priced = [set(prices.get(l["item"], {})) for l in core]
    stores = set.intersection(*priced) if priced else set()
    by_store = {}
    for store in sorted(stores):
        cost = sum(l["grams"] / prices[l["item"]][store]["pack_g"] * prices[l["item"]][store]["price"] for l in core)
        dates = [prices[l["item"]][store]["checked"] for l in core if prices[l["item"]][store]["price"] > 0]
        # Where the money goes: each core ingredient's cost and protein per serving, biggest cost first.
        breakdown = []
        for l in core:
            p = prices[l["item"]][store]
            c = l["grams"] / p["pack_g"] * p["price"] / servings
            prot = l["grams"] * nutrition.get(l["item"], {}).get("protein", 0) / 100 / servings
            breakdown.append({"label": l["label"], "item": l["item"], "cost": round(c, 2),
                              "share": round(c * servings / cost, 3) if cost else 0,
                              "protein": round(prot, 1), "product": p["product"], "url": p["url"]})
        breakdown.sort(key=lambda b: -b["cost"])
        by_store[store] = {
            "cost_per_serving": round(cost / servings, 2),
            "protein_g_per_dollar": round(core_p / cost, 1) if cost else None,
            "prices_checked": min(dates) if dates else None,
            "breakdown": breakdown,
        }

    out = {
        "name": recipe["name"],
        "slug": recipe["slug"],
        "servings": servings,
        "protein_g_per_serving": round(core_p / servings, 1),
        "kcal_per_serving": round(core_k / servings),
        "with_optional": {"protein_g_per_serving": round(all_p / servings, 1),
                          "kcal_per_serving": round(all_k / servings)},
        "stores": by_store,
        "cheapest_store": min(by_store, key=lambda s: by_store[s]["cost_per_serving"]) if by_store else None,
        "missing_nutrition": sorted({l["item"] for l in lines if l["item"] not in nutrition}),
        "unpriced_items": sorted({l["item"] for l in core if not prices.get(l["item"])}),
        "ingredients": lines,
    }
    for field in DISPLAY_FIELDS:
        if field in recipe:
            out[field] = recipe[field]
    return out


AISLE_ORDER = ["Produce", "Meat", "Dairy and eggs", "Frozen", "Dry goods and cans",
               "Protein powder", "Baking", "Oils and spices", "Other"]


def plan_numbers(plan: dict, recipes: dict[str, dict], raw: dict[str, dict], prices: dict,
                 pantry_items: set[str], aisles: dict[str, str]) -> dict:
    days = plan["days"]
    meals = []
    totals = {"protein": 0.0, "kcal": 0.0}
    for m in plan["meals"]:
        r = recipes.get(m["recipe"])
        if r is None:
            sys.exit(f"plan '{plan['slug']}': unknown recipe '{m['recipe']}'")
        meals.append({"slot": m["slot"], "recipe": r["slug"], "name": r["name"],
                      "servings": m["servings"], "note": m.get("note", "")})
        totals["protein"] += r["protein_g_per_serving"] * m["servings"]
        totals["kcal"] += r["kcal_per_serving"] * m["servings"]

    # Grams needed per ingredient across the plan (core ingredients only).
    need: dict[str, float] = defaultdict(float)
    for m in plan["meals"]:
        src = raw[m["recipe"]]
        factor = m["servings"] / src["servings"]
        for i in src["ingredients"]:
            if not i.get("optional"):
                need[i["item"].strip().lower()] += float(i["grams"]) * factor

    stores = set.intersection(*(set(prices.get(item, {})) for item in need)) if need else set()
    by_store = {}
    for store in sorted(stores):
        buy, pantry = [], []
        used_cost = checkout = 0.0
        for item, grams in sorted(need.items()):
            p = prices[item][store]
            if p["price"] == 0:
                continue  # free (tap water)
            used = grams / p["pack_g"] * p["price"]
            used_cost += used
            packs = max(1, math.ceil(grams / p["pack_g"] - PACK_SLACK))
            row = {"item": item, "aisle": aisles.get(item, "Other"),
                   "product": p["product"], "grams_needed": round(grams),
                   "packs": packs, "pack_price": p["price"], "url": p["url"]}
            if item in pantry_items:
                pantry.append(row)
            else:
                checkout += packs * p["price"]
                buy.append(row)
        order = {a: i for i, a in enumerate(AISLE_ORDER)}
        buy.sort(key=lambda r: (order.get(r["aisle"], 99), r["product"]))
        by_store[store] = {
            "cost_per_day": round(used_cost / days, 2),
            "cost_total_used": round(used_cost, 2),
            "checkout_total": round(checkout, 2),
            "buy": buy,
            "pantry": pantry,
        }

    return {
        "name": plan["name"], "slug": plan["slug"], "days": days, "meals": meals,
        "per_day": {"protein_g": round(totals["protein"] / days), "kcal": round(totals["kcal"] / days)},
        "stores": by_store,
    }


def protein_rank(nutrition: dict, prices: dict) -> dict:
    """Rank staples by grams of protein per $1, per store, using the whole pack at the shelf price."""
    with SOURCES.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
    by_store: dict[str, list] = defaultdict(list)
    for r in rows:
        item = r["item"].strip().lower()
        n = nutrition.get(item)
        if not n:
            sys.exit(f"protein_sources.csv: no nutrition for '{item}'")
        for store, p in prices.get(item, {}).items():
            if p["price"] <= 0 or p.get("unranked"):
                continue
            protein = p["pack_g"] * n["protein"] / 100
            by_store[store].append({
                "item": item, "name": r["name"].strip(), "group": r["group"].strip(),
                "product": p["product"], "pack_g": round(p["pack_g"]), "price": p["price"],
                "protein_per_pack": round(protein, 1),
                "protein_per_dollar": round(protein / p["price"], 1),
                "cost_per_30g": round(p["price"] * 30 / protein, 2) if protein else None,
                "protein_share": round(4 * n["protein"] / n["kcal"], 2) if n["kcal"] else None,
                "checked": p["checked"], "url": p["url"],
            })
    return {store: sorted(lst, key=lambda x: -x["protein_per_dollar"]) for store, lst in by_store.items()}


def stamp_published(path: Path) -> str:
    """First time a recipe is processed, record its publish date in its own file (so it never changes later).
    Uses the /write submission date when the recipe came from there, otherwise today."""
    import datetime, re as _re
    date = datetime.date.today().isoformat()
    for sub in (ROOT / "submissions").glob("*/recipe.md"):
        text = sub.read_text(encoding="utf-8")
        m_slug = _re.search(r"^slug:\s*(\S+)", text, _re.M)
        m_date = _re.search(r"^submitted:\s*(\d{4}-\d{2}-\d{2})", text, _re.M)
        if m_slug and m_date and m_slug.group(1) == path.stem:
            date = m_date.group(1)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    at = next((i + 1 for i, l in enumerate(lines) if l.startswith("name =")), 0)
    lines.insert(at, f'published = "{date}"\n')
    path.write_text("".join(lines), encoding="utf-8")
    print(f"{path.name}: published = {date} (added)")
    return date


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="print a summary")
    args = ap.parse_args()

    nutrition = load_nutrition(NUTRITION)
    stores_info = load_stores(STORES)
    prices = load_prices(PRICES, stores_info)
    with AISLES.open(newline="", encoding="utf-8") as f:
        aisles = {r["item"].strip().lower(): r["aisle"].strip() for r in csv.DictReader(f)}
    pantry_items = {l.strip().lower() for l in PANTRY.read_text(encoding="utf-8").splitlines()
                    if l.strip() and not l.startswith("#")}

    raw, recipes = {}, {}
    for path in sorted(RECIPES_DIR.glob("*.toml")):
        with path.open("rb") as f:
            r = tomllib.load(f)
        r["slug"] = path.stem
        if "published" not in r:
            r["published"] = stamp_published(path)
        raw[path.stem] = r
        recipes[path.stem] = recipe_numbers(r, nutrition, prices)

    plans = []
    for path in sorted(PLANS_DIR.glob("*.toml")):
        with path.open("rb") as f:
            p = tomllib.load(f)
        p["slug"] = path.stem
        plans.append(plan_numbers(p, recipes, raw, prices, pantry_items, aisles))

    OUT_RECIPES.parent.mkdir(parents=True, exist_ok=True)
    OUT_RECIPES.write_text(json.dumps(list(recipes.values()), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_PLANS.write_text(json.dumps(plans, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    book = {item: {"aisle": aisles.get(item, "Other"), "pantry": item in pantry_items,
                   "stores": {st: {"product": p["product"], "pack_g": p["pack_g"], "price": p["price"], "url": p["url"]}
                              for st, p in stores.items()}}
            for item, stores in prices.items()}
    OUT_BOOK.write_text(json.dumps({"aisle_order": AISLE_ORDER, "pack_slack": PACK_SLACK, "stores": stores_info, "items": book},
                                   ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_STORES.write_text(json.dumps(stores_info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rank = protein_rank(nutrition, prices)
    OUT_RANK.write_text(json.dumps(rank, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(recipes)} recipe(s) and {len(plans)} plan(s) to src/data/")

    if args.print:
        for r in recipes.values():
            w = r["with_optional"]
            print(f"\n{r['name']} ({r['servings']} serving(s))")
            print(f"  {r['protein_g_per_serving']} g protein, {r['kcal_per_serving']} kcal per serving"
                  f"  (with optional: {w['protein_g_per_serving']} g, {w['kcal_per_serving']} kcal)")
            for issue in ("missing_nutrition", "unpriced_items"):
                if r[issue]:
                    print(f"  ! {issue}: {', '.join(r[issue])}")
            for store, s in r["stores"].items():
                print(f"  {store:<11} ${s['cost_per_serving']:.2f}/serving  {s['protein_g_per_dollar']} g protein per $")
        for p in plans:
            print(f"\nPLAN {p['name']}: {p['per_day']['protein_g']} g protein, {p['per_day']['kcal']} kcal per day")
            for store, s in p["stores"].items():
                print(f"  {store}: ${s['cost_per_day']}/day used, ${s['cost_total_used']} used over {p['days']} days, "
                      f"checkout ${s['checkout_total']} ({len(s['buy'])} items + {len(s['pantry'])} pantry)")


        for store, lst in rank.items():
            print(f"\nCHEAPEST PROTEIN at {store}")
            for x in lst:
                print(f"  {x['protein_per_dollar']:>6} g/$  ${x['cost_per_30g']:.2f} per 30 g  {x['protein_share']:.0%} kcal  {x['name']}")


if __name__ == "__main__":
    main()
