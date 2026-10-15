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

AISLES = ROOT / "data" / "aisles.csv"     # shopping lists are grouped by store aisle
PANTRY = ROOT / "data" / "pantry.txt"   # staples listed apart from the checkout total
# Tolerance when rounding packs up (120 g of pepper is 1 pepper of ~119 g, not 2).
PACK_SLACK = 0.02

DISPLAY_FIELDS = ("description", "prep_minutes", "cook_minutes", "steps", "storage", "tip",
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


def load_prices(path: Path) -> dict[str, dict[str, dict]]:
    book: dict[str, dict[str, dict]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            item = row["item"].strip().lower()
            if not item or not row["price_usd"].strip():
                continue
            where = f"prices.csv line {n} ({item})"
            pack = _num(row["pack_g"], where)
            if pack <= 0:
                sys.exit(f"{where}: pack_g must be > 0")
            book[item][row["store"].strip()] = {
                "product": row["product"].strip(),
                "pack_g": pack,
                "price": _num(row["price_usd"], where),
                "checked": row["checked"].strip(),
                "url": row.get("price_url", "").strip(),
            }
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
        by_store[store] = {
            "cost_per_serving": round(cost / servings, 2),
            "protein_g_per_dollar": round(core_p / cost, 1) if cost else None,
            "prices_checked": min(dates) if dates else None,
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


AISLE_ORDER = ["Produce", "Meat (frozen)", "Dairy and eggs", "Frozen", "Dry goods and cans",
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="print a summary")
    args = ap.parse_args()

    nutrition = load_nutrition(NUTRITION)
    prices = load_prices(PRICES)
    with AISLES.open(newline="", encoding="utf-8") as f:
        aisles = {r["item"].strip().lower(): r["aisle"].strip() for r in csv.DictReader(f)}
    pantry_items = {l.strip().lower() for l in PANTRY.read_text(encoding="utf-8").splitlines()
                    if l.strip() and not l.startswith("#")}

    raw, recipes = {}, {}
    for path in sorted(RECIPES_DIR.glob("*.toml")):
        with path.open("rb") as f:
            r = tomllib.load(f)
        r["slug"] = path.stem
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
                print(f"  {store:<10} ${s['cost_per_serving']:.2f}/serving  {s['protein_g_per_dollar']} g protein per $")
        for p in plans:
            print(f"\nPLAN {p['name']}: {p['per_day']['protein_g']} g protein, {p['per_day']['kcal']} kcal per day")
            for store, s in p["stores"].items():
                print(f"  {store}: ${s['cost_per_day']}/day used, ${s['cost_total_used']} used over {p['days']} days, "
                      f"checkout ${s['checkout_total']} ({len(s['buy'])} items + {len(s['pantry'])} pantry)")


if __name__ == "__main__":
    main()
