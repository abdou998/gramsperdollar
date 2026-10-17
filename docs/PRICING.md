# Pricing a new store (cheap and fast)

Start a **fresh chat** for each store and point it at this file. Long chats re-read everything each turn, which is where most tokens go.

## Steps
1. Add the store to `data/stores.csv` (id = store letters + state, e.g. `heb-tx`, `kroger-tx`). Pick one real store near the others in that city.
2. `python3 tools/price_todo.py <id> --tsv` → checklist + blank `data/todo/<id>.tsv`.
3. In the browser: set the store on the retailer's site, then for each item in `data/search_terms.csv`:
   `navigate` to the search URL → wait 6 s → run the site's extractor (`tools/scrape/<site>.js`).
   - Put 6–8 searches in ONE `browser_batch` call. Never read whole pages or take screenshots to find prices.
   - Store the extractor once in the site's localStorage (`localStorage.gpdx = '<script>'`), then each search only needs `eval(localStorage.gpdx)`.
   - Never fetch pages in the background or loop fast: that trips bot checks. If a check appears, stop and ask the user to clear it.
4. Fill the TSV (item, product, pack_g, price, url, unranked) and run
   `python3 tools/add_prices.py <id> data/todo/<id>.tsv` → it fills store/month and flags odd prices per kg.
5. `python3 tools/mealmath.py && npx astro build`, check `/cheapest-protein`, commit.

## Picking rules (same at every store)
- Regular price, not sale price (note the sale in the product name).
- The store's own everyday brand (Great Value, H-E-B / Hill Country Fare, Kroger, Aldi brands). When the store has two own brands, take the cheaper per unit.
- Value/family packs for meat when that's the normal shelf option; per lb for meat sold by weight.
- Swaps (zucchini for yellow squash etc.) are named in the product text.
- Labels we can't trust → `unranked=1` (used for recipe costs, kept off rankings).

## Extractors
- `tools/scrape/heb.js`: heb.com search page (reads `__NEXT_DATA__`; uses the in-store "ONLINE" price).
- Walmart: read `[data-item-id]` tiles slowly (1 page / ~10 s). Bulk fetches get challenged.
- Aldi (Instacart): in-store mode via "Change store".
