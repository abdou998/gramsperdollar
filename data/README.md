# Nutrition, prices + recipe maths

## Files
- `nutrition.csv` — one row per ingredient: protein and kcal **per 100 g (raw)**, plus the USDA FoodData Central source.
- `prices.csv` — one row per ingredient **per store**:
  - `item` — must match `nutrition.csv` (e.g. `egg whole`)
  - `store` — `Walmart`, `Aldi`, `Costco`, `Kroger`…
  - `product` — exact product name as listed by the store
  - `pack_g` — pack size in grams (1 lb = 453.6 g, 1 oz = 28.35 g, 1 gallon milk ≈ 3,900 g)
  - `price_usd` — shelf price for that pack
  - `checked` — month checked, `YYYY-MM`
  - `price_url` — product page the price came from
- `recipes/*.toml` — one file per recipe (copy `_TEMPLATE.toml.txt`). Mark add-ons with `optional = true`.
  Each recipe also needs `meal` (breakfast / lunch / dinner / snack) and `tags` (e.g. `["one-pot", "freezer-friendly",
  "no-cook", "vegetarian"]`). These drive the category pages. Every recipe gets its own page at `/recipes/<file-name>`.

## Run
```
python tools/mealmath.py --print
```
Writes `src/data/recipes.json` (what the site's tables read) and prints protein/kcal per serving
(with and without optional extras), plus — once every core ingredient is priced at a store —
cost per serving, grams of protein per dollar, the cheapest store and the oldest price date.

## Refresh routine (every ~3 months)
Update `price_usd` and `checked` in `prices.csv`, run the script, push. Every page updates.
