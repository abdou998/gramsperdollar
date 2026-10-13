"""
mealmath.py — turn recipes + nutrition + prices into the numbers the site publishes.

Inputs
  data/nutrition.csv     one row per ingredient: protein and kcal per 100 g, and the USDA source.
  data/prices.csv        one row per (ingredient, store): pack size, price, month checked.
  data/recipes/*.toml    one file per recipe: servings + grams of each ingredient.
                         Mark extras with `optional = true` — they are reported separately.

Output
  src/data/recipes.json  per recipe: protein and kcal per serving (with and without optional
                         extras) and, per store that prices every core ingredient: cost per
                         serving, grams of protein per dollar, and the oldest price date.

Usage
  python tools/mealmath.py            # rebuild src/data/recipes.json
  python tools/mealmath.py --print    # also print a readable summary

Standard library only. Cost counts only the grams a recipe uses, not the whole pack.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NUTRITION = ROOT / "data" / "nutrition.csv"
PRICES = ROOT / "data" / "prices.csv"
RECIPES_DIR = ROOT / "data" / "recipes"
OUTPUT = ROOT / "src" / "data" / "recipes.json"


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
            if not item:
                continue
            where = f"nutrition.csv line {n} ({item})"
            out[item] = {
                "protein": _num(row["protein_g_per_100g"], where),
                "kcal": _num(row["kcal_per_100g"], where),
                "source": row.get("source", "").strip(),
            }
    return out


def load_prices(path: Path) -> dict[str, dict[str, dict]]:
    """{item: {store: {pack_g, price, checked}}}; rows without a price yet are skipped."""
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
                "pack_g": pack,
                "price": _num(row["price_usd"], where),
                "checked": row["checked"].strip(),
            }
    return book


def recipe_numbers(recipe: dict, nutrition: dict, prices: dict) -> dict:
    servings = recipe["servings"]
    lines = [
        {"item": i["item"].strip().lower(), "grams": float(i["grams"]),
         "optional": bool(i.get("optional", False)), "note": i.get("note", "")}
        for i in recipe["ingredients"]
    ]
    core = [l for l in lines if not l["optional"]]

    missing_nutrition = sorted({l["item"] for l in lines if l["item"] not in nutrition})

    def totals(subset):
        p = sum(l["grams"] * nutrition[l["item"]]["protein"] / 100 for l in subset if l["item"] in nutrition)
        k = sum(l["grams"] * nutrition[l["item"]]["kcal"] / 100 for l in subset if l["item"] in nutrition)
        return p, k

    core_p, core_k = totals(core)
    all_p, all_k = totals(lines)

    # Stores that price every core ingredient (zero-cost items like spices can be priced at 0).
    priced = [set(prices.get(l["item"], {})) for l in core]
    stores = set.intersection(*priced) if priced else set()
    by_store = {}
    for store in sorted(stores):
        cost = sum(l["grams"] / prices[l["item"]][store]["pack_g"] * prices[l["item"]][store]["price"] for l in core)
        by_store[store] = {
            "cost_per_serving": round(cost / servings, 2),
            "protein_g_per_dollar": round(core_p / cost, 1) if cost else None,
            "prices_checked": min(prices[l["item"]][store]["checked"] for l in core),
        }

    return {
        "name": recipe["name"],
        "slug": recipe.get("slug", ""),
        "servings": servings,
        "protein_g_per_serving": round(core_p / servings, 1),
        "kcal_per_serving": round(core_k / servings),
        "with_optional": {
            "protein_g_per_serving": round(all_p / servings, 1),
            "kcal_per_serving": round(all_k / servings),
        },
        "stores": by_store,
        "cheapest_store": min(by_store, key=lambda s: by_store[s]["cost_per_serving"]) if by_store else None,
        "missing_nutrition": missing_nutrition,
        "unpriced_items": sorted({l["item"] for l in core if not prices.get(l["item"])}),
        "ingredients": lines,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="print a summary")
    args = ap.parse_args()

    nutrition = load_nutrition(NUTRITION)
    prices = load_prices(PRICES)
    results = []
    for path in sorted(RECIPES_DIR.glob("*.toml")):
        with path.open("rb") as f:
            recipe = tomllib.load(f)
        recipe.setdefault("slug", path.stem)
        results.append(recipe_numbers(recipe, nutrition, prices))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} recipe(s) to {OUTPUT.relative_to(ROOT)}")

    if args.print:
        for r in results:
            w = r["with_optional"]
            print(f"\n{r['name']} ({r['servings']} serving(s))")
            print(f"  core:          {r['protein_g_per_serving']} g protein, {r['kcal_per_serving']} kcal per serving")
            print(f"  with optional: {w['protein_g_per_serving']} g protein, {w['kcal_per_serving']} kcal per serving")
            if r["missing_nutrition"]:
                print(f"  ! no nutrition data: {', '.join(r['missing_nutrition'])}")
            if r["unpriced_items"]:
                print(f"  ! no prices yet: {', '.join(r['unpriced_items'])}")
            for store, s in r["stores"].items():
                star = "  <- cheapest" if store == r["cheapest_store"] else ""
                print(f"  {store:<12} ${s['cost_per_serving']:.2f}/serving  "
                      f"{s['protein_g_per_dollar']} g protein per $  (prices {s['prices_checked']}){star}")


if __name__ == "__main__":
    main()
