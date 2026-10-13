# Price book + recipe maths

## Files
- `ingredients.csv` — the price book. One row per ingredient **per store**.
  - `item` — short generic name, used by recipes (e.g. `chicken thighs boneless skinless`)
  - `store` — `Walmart`, `Aldi`, `Costco`, `Kroger`…
  - `product` — exact product name as listed by the store
  - `pack_g` — pack size in grams (1 lb = 453.6 g, 1 oz = 28.35 g)
  - `price_usd` — shelf price for that pack
  - `checked` — month the price was checked, `YYYY-MM`
  - `protein_g_per_100g`, `kcal_per_100g` — from USDA FoodData Central (raw weight)
  - `nutrition_source` — e.g. `USDA FDC 171477`
  - `price_url` — product page the price came from
- `recipes/*.toml` — one file per recipe (copy `_TEMPLATE.toml.txt`).

## Run
```
python tools/mealmath.py --print
```
Writes `src/data/recipes.json` (what the site's tables read) and prints a summary:
protein and kcal per serving, cost per serving and grams of protein per dollar at each store,
the cheapest store, and the oldest price date (shown on the page as "prices checked").

## Refresh routine (every ~3 months)
Update `price_usd` and `checked` for each row, run the script, push. Every page updates.
