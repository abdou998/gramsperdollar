# Nutrition, prices + recipe maths

## Files
- `nutrition.csv` — one row per ingredient: protein and kcal **per 100 g (raw)**, plus the USDA FoodData Central source.
- `stores.csv` — one row per **store + state** we price (`id` like `walmart-ca`, `aldi-tx`), with the exact store location,
  the source website and a note shown on the site. Only compare stores within the same state.
- `prices.csv` — one row per ingredient **per store + state**:
  - `item` — must match `nutrition.csv` (e.g. `egg whole`)
  - `store` — `Walmart`, `Aldi`, `Costco`, `Kroger`…
  - `market` — state code (`CA`, `TX`…); `store` + `market` must match a row in `stores.csv`
  - `unranked` — `yes` to leave a row off the cheapest-protein ranking (e.g. a swap whose label we couldn't verify)
  - `product` — exact product name as listed by the store
  - `pack_g` — pack size in grams (1 lb = 453.6 g, 1 oz = 28.35 g, 1 gallon milk ≈ 3,900 g)
  - `price_usd` — shelf price for that pack
  - `checked` — month checked, `YYYY-MM`
  - `price_url` — product page the price came from
- `recipes/*.toml` — one file per recipe (copy `_TEMPLATE.toml.txt`). Mark add-ons with `optional = true`.
  Each recipe also needs `meal` (breakfast / lunch / dinner / snack) and `tags` (e.g. `["one-pot", "freezer-friendly",
  "no-cook", "vegetarian"]`). These drive the category pages. Optional `cuisine` (e.g. "Mexican") only when it genuinely fits. Optional `author` (shown as a byline) and `intro` (a paragraph in the contributor's words) for recipes from `/write`. Every recipe gets its own page at `/recipes/<file-name>`.

- `protein_sources.csv` — the staples ranked on `/cheapest-protein/<store>` (item, display name, filter group).
  A store gets its own ranking page once it has prices for 10+ of these. To add a store: add its rows to
  `prices.csv` (same `item` names, store name in `store`), run the script, and its page appears.

## Run
```
python tools/mealmath.py --print
```
Writes `src/data/recipes.json` (what the site's tables read, incl. a per-ingredient cost breakdown), `src/data/protein_rank.json` and prints protein/kcal per serving
(with and without optional extras), plus — once every core ingredient is priced at a store —
cost per serving, grams of protein per dollar, the cheapest store and the oldest price date.

## Refresh routine (every ~3 months)
Update `price_usd` and `checked` in `prices.csv`, run the script, push. Every page updates.
