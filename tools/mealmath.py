"""
mealmath.py — turn recipes + a price book into the numbers the site publishes.

Inputs
  data/ingredients.csv   one row per (ingredient, store): pack size, price, date checked,
                         protein and kcal per 100 g.
  data/recipes/*.toml    one file per recipe: servings + grams of each ingredient.

Output
  src/data/recipes.json  per recipe, per store: cost per serving, protein per serving,
                         kcal per serving, grams of protein per dollar, oldest price date.
                         Astro pages read this file, so tables update when prices change.

Usage
  python tools/mealmath.py            # rebuild src/data/recipes.json
  python tools/mealmath.py --print    # also print a readable summary

Only the standard library is used. Cost counts only the grams a recipe actually uses
(not the whole pack), which is how per-serving cost is normally quoted.
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
INGREDIENTS = ROOT / "data" / "ingredients.csv"
RECIPES_DIR = ROOT / "data" / "recipes"
OUTPUT = ROOT / "src" / "data" / "recipes.json"

REQUIRED_COLS = {
    "item", "store", "product", "pack_g", "price_usd", "checked",
    "protein_g_per_100g", "kcal_per_100g",
}


def load_price_book(path: Path) -> dict[str, dict[str, dict]]:
    """Return {item: {store: row}} with numbers parsed. Rows with no price yet are skipped."""
    book: dict[str, dict[str, dict]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLS - set(reader.fieldnames or [])
        if missing:
            sys.exit(f"ingredients.csv is missing columns: {sorted(missing)}")
        for n, row in enumerate(reader, start=2):
            item = row["item"].strip().lower()
            if not item or not row["price_usd"].strip():
                continue  # placeholder row, not priced yet
            try:
                row["pack_g"] = float(row["pack_g"])
                row["price_usd"] = float(row["price_usd"])
                row["protein_g_per_100g"] = float(row["protein_g_per_100g"])
                row["kcal_per_100g"] = float(row["kcal_per_100g"])
            except ValueError as e:
                sys.exit(f"ingredients.csv line {n} ({item}): bad number — {e}")
            if row["pack_g"] <= 0:
                sys.exit(f"ingredients.csv line {n} ({item}): pack_g must be > 0")
            book[item][row["store"].strip()] = row
    return book


def recipe_numbers(recipe: dict, book: dict) -> dict:
    """Totals per store. A store is included only if it prices every ingredient."""
    servings = recipe["servings"]
    items = [(i["item"].strip().lower(), float(i["grams"])) for i in recipe["ingredients"]]

    unknown = [name for name, _ in items if name not in book]
    stores = set.intersection(*(set(book[name]) for name, _ in items if name in book)) if items and not unknown else set()

    protein = kcal = 0.0
    any_store = None
    by_store = {}
    for store in sorted(stores):
        cost = 0.0
        protein = kcal = 0.0
        dates = []
        for name, grams in items:
            row = book[name][store]
            cost += grams / row["pack_g"] * row["price_usd"]
            protein += grams * row["protein_g_per_100g"] / 100
            kcal += grams * row["kcal_per_100g"] / 100
            dates.append(row["checked"])
        any_store = store
        by_store[store] = {
            "cost_per_serving": round(cost / servings, 2),
            "protein_g_per_dollar": round(protein / cost, 1) if cost else None,
            "prices_checked": min(dates),  # oldest price in the recipe — the honest date to show
        }

    return {
        "name": recipe["name"],
        "slug": recipe.get("slug", ""),
        "servings": servings,
        "protein_g_per_serving": round(protein / servings) if any_store else None,
        "kcal_per_serving": round(kcal / servings) if any_store else None,
        "stores": by_store,
        "cheapest_store": min(by_store, key=lambda s: by_store[s]["cost_per_serving"]) if by_store else None,
        "missing_ingredients": unknown,
        "ingredients": [{"item": n, "grams": g} for n, g in items],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="print a summary table")
    args = ap.parse_args()

    book = load_price_book(INGREDIENTS)
    results = []
    for path in sorted(RECIPES_DIR.glob("*.toml")):
        with path.open("rb") as f:
            recipe = tomllib.load(f)
        recipe.setdefault("slug", path.stem)
        results.append(recipe_numbers(recipe, book))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} recipe(s) to {OUTPUT.relative_to(ROOT)}")

    if args.print:
        for r in results:
            print(f"\n{r['name']} — {r['servings']} servings, "
                  f"{r['protein_g_per_serving']} g protein, {r['kcal_per_serving']} kcal per serving")
            if r["missing_ingredients"]:
                print(f"  ! not in price book: {', '.join(r['missing_ingredients'])}")
            for store, s in r["stores"].items():
                star = "  <- cheapest" if store == r["cheapest_store"] else ""
                print(f"  {store:<12} ${s['cost_per_serving']:.2f}/serving  "
                      f"{s['protein_g_per_dollar']} g protein per $  (prices {s['prices_checked']}){star}")


if __name__ == "__main__":
    main()
