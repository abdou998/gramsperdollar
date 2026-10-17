# Grams per Dollar — Handover

_Last updated: 16 Oct 2026. This repo is **public**, so nothing private goes in here (accounts,
emails, personal history). Private notes live in the owner's Claude project "side hustle"._

## 1. What this is

**gramsperdollar.com** is a small static site about **high-protein meal prep on a budget**. Every
recipe shows protein per serving, cost per serving and **grams of protein per dollar**, priced at
real US stores with the month the prices were checked.

### Goals (in priority order)
1. **Learn SEO by doing.** Success = impressions and clicks in Google Search Console, and
   understanding *why* they happened. Revenue is secondary.
2. Build reusable skills (research, site setup, writing for search, reading GSC) for future niche sites.
3. Later: modest income from affiliates (kitchen gear, food). Not AdSense (see Challenges).

### Owner constraints
- 2–3 hours/week. ~$100 total budget (only the domain costs money).
- Faceless: no face or voice.
- Free tools only: Google Search Console, Keyword Planner, Google Trends, Ahrefs Webmaster Tools.
- Owner is based outside the US; the audience is English-speaking, mainly US.

## 2. Key decisions and why

| Decision | Why |
|---|---|
| Niche: high-protein meal prep (constraint-based: budget, cooking for one, no-cook, freezer) | Google Trends (US, 5 yrs): "high protein meal prep" grew ~6x since 2021, peaks every January. Weak results on long-tail queries (Reddit, Lemon8, Substack, Gumroad pages ranking). Recipes are not health advice → lower YMYL risk. |
| One site only for now | 2–3 h/week can't support two. A second site (minimal-equipment home workouts) is parked until Search Console data justifies it. |
| Store pages are a **side cluster**, not the core | Store-specific terms are small on Trends (Costco > Walmart > Trader Joe's > Aldi), prices vary by region, and retailers' own pages rank for "[store] high protein meal prep". Comparison pages ("cheapest store for high-protein meal prep") are fine — retailers won't publish those. |
| Recipes, not diet prescriptions | No weight-loss claims, no "X g protein a day" plans, no supplement stacks. Protein and cost per serving only. |
| No scraping of Walmart/Costco/Aldi | Their terms forbid automated access and they block bots. Prices are looked up manually (like a shopper) and refreshed quarterly. Kroger has an official developer API — an option for automation later. |
| Static site (Astro) on Cloudflare | Free hosting, fast pages, auto-deploy on every push. |

Full research trail: owner's Claude project docs `seo-niche-decision-2026-10-13.md` and
`meal-prep-site-first-10-articles.md`.

## 3. Architecture

```
GitHub (abdou998/gramsperdollar, public)
   │  push to main
   ▼
Cloudflare Worker "gramsperdollar" (static assets, free plan)
   │  build: npm run build   deploy: npx wrangler deploy
   ▼
https://gramsperdollar.com  →  Google Search Console (domain property)
```

- **Framework:** Astro 7, fully static. `astro.config.mjs` sets `site`, clean URLs (`/about`, not `/about.html`) and the sitemap.
- **Hosting config:** `wrangler.jsonc` serves `dist/` as static assets. Only `/api/*` runs code (`worker/index.ts`), for the private writing page. workers.dev URLs are **disabled** (avoids duplicate copies of the site).
- **SEO basics in place:** per-page title and meta description, canonical URLs (`src/layouts/Base.astro`), `public/robots.txt`, auto sitemap at `/sitemap-index.xml` (submitted to Search Console).
- **Domain:** registered at Cloudflare Registrar, auto-renew on. Search Console verified through Cloudflare DNS — **don't delete that TXT record**.

- **Private writing page:** `/write` (noindex, not in the sitemap). Password login → recipe + photos are committed to
  `submissions/<date>-<slug>/` in one commit through the GitHub API. Each one goes live straight away as a "not priced
  yet" recipe page (`src/lib/unpriced.ts`, `UnpricedRecipe.astro`); pricing it later keeps the same URL
  (steps in `submissions/README.md`). Needs two Worker secrets set in the Cloudflare dashboard:
  `WRITER_PASSWORD` and `GITHUB_TOKEN` (fine-grained, this repo only, Contents read/write; expires, renew it).
  Local testing: `.dev.vars` (git-ignored) + `npx wrangler dev`.

## 4. Repo map

| Path | What |
|---|---|
| `src/pages/` | `index.astro` (home), `about.astro`, `[slug].astro` (posts), `recipes/index.astro` (all recipes by meal), `recipes/[slug].astro` (one page per recipe, Recipe + Breadcrumb schema), `recipes/[facet]/[value].astro` (category pages). |
| `worker/index.ts` | The small server for `/api/*`: login, session cookie, and committing submissions to GitHub. |
| `submissions/` | Recipes sent from `/write`, waiting to be priced. Not read by the site. |
| `src/content/posts/` | Posts as `.md` (plain) or `.mdx` (can embed components). File name = URL. `_template.md` is never published. |
| `src/components/` | `ShelfTag` (yellow g/$ tag), `RecipeCard` (full recipe + Recipe schema), `Leaderboard`, `PlanSummary` (week table + shopping list). |
| `src/lib/taxonomy.ts` | Category rules (meal, protein band, cost band, store, style). A category page only exists once it has 3+ recipes and differs from /recipes — avoids thin pages. |
| `src/styles/global.css` | Design tokens: colours, type scale, the shelf tag. |
| `docs/WRITING.md` | How to write and publish a post without coding. |
| `src/layouts/Base.astro` | Shared layout + SEO tags. |
| `src/assets/images/` | Images + `CREDITS.md` (every stock photo needs a visible credit caption). |
| `src/data/recipes.json` | **Generated** by `tools/mealmath.py`. Pages read recipe numbers from here. |
| `data/nutrition.csv` | Protein + kcal per 100 g (USDA FoodData Central; whey from the product label). |
| `data/prices.csv` | One row per ingredient per store: pack size, price, month checked, URL. |
| `data/recipes/*.toml` | One file per recipe: servings, grams + display amount per ingredient, steps, storage, tip, image. |
| `data/plans/*.toml` | Multi-day plans (which recipes, how many servings). Produces day totals + a shopping list. |
| `data/pantry.txt`, `data/aisles.csv` | Pantry staples kept out of checkout totals; store aisle for each item. |
| `tools/mealmath.py` | Calculates per-serving protein/kcal/cost and protein per dollar per store. |
| `drafts/` | Unpublished writing (outside `src/pages`, so never deployed). |

### Daily workflow
```
python tools/mealmath.py --print   # recompute numbers after editing data/
npm run build                      # check the site builds
git push                           # Cloudflare deploys in ~40 seconds
```

## 5. Current status (16 Oct 2026)

- ✅ Site live on Cloudflare, Search Console verified, sitemap submitted ("Success").
- ✅ **Pages:** home, About, article #1 `/high-protein-meal-prep-for-one`, `/recipes`, one page per recipe, private `/write`.
- ✅ **Priced recipes** (Walmart, Oct 2026, Sacramento CA default store):

| Recipe | Protein/serving | Cost/serving | Protein per $ |
|---|---|---|---|
| One-pot spiced chicken, red lentils & rice | 49.7 g | $1.80 | 27.6 g |
| 31 g protein pancake | 31.8 g | $2.17 | 14.7 g |
| Banana oat Greek yogurt protein bowl (by Sanae) | 57 g | $3.53 | 16.2 g |
| Lemon-rosemary chicken with grilled squash | 48.7 g | $3.59 | 13.6 g |
| Garlic paprika shrimp and rice bowl (by Sanae, own photo) | 21 g | $2.58 | 8.2 g |

- ✅ **Unpriced:** none right now. Sanae's yogurt bowl (16 Oct) and shrimp bowl (17 Oct) are priced.
- ✅ **Contributor flow:** `/write` (password) → `submissions/` commit → live in ~1 min as unpriced → priced weekly in a batch.
- ✅ **Photos:** all 5 recipes have one (the shrimp bowl is Sanae's own; the rest are stock, credited in captions and `src/assets/images/CREDITS.md`). Replace with
  real photos when the dishes are cooked.
- ✅ **Recipe structured data:** Search Console shows 0 invalid. Added author, step name/url, category, keywords, cuisine
  (only where true). Validation started 16 Oct for those 6. 17 Oct email: 'Missing image' (critical) came from the
  one-pot being crawled before its photo was added; 'Missing nutrition' from the unpriced shrimp bowl. Both fixed. Unpriced
  recipes without a photo now output no Recipe schema at all, so they can't trigger a critical error. See decision 7 in Next steps for the 3 left on purpose.
- ✅ **Indexed (16 Oct):** the article and `/recipes` are on Google. New pages get found through the sitemap and internal links.
- ✅ **Cheapest protein at Walmart** (`/cheapest-protein/walmart`, 17 Oct): 21 staples ranked by g protein per $1 (whole pack,
  shelf price), with cost of 30 g protein and % of calories from protein (lean filter). Built from `data/protein_sources.csv`;
  one page per store with 10+ ranked items. Linked from the main menu and the homepage.
- ✅ **"Where the money goes"** on every priced recipe: per-ingredient cost, share and protein (`MoneyBreakdown.astro`).
- ✅ **Weekly meal planner** (`/planner`, 17 Oct): steppers per recipe + days → protein/kcal/cost per day and one shopping
  list by aisle with the checkout total (same pack maths as `mealmath.py`; reads `src/data/pricebook.json`). Saved in
  localStorage (`gpd-plan`) and in the URL (`#d=4&r=slug:4,...`) for sharing; copy list / copy link. "Add to my week" button
  on every priced recipe. Checked against the 4-day plan: identical totals.
- ✅ First category page live: `/recipes/protein/40g-plus` (3 recipes). Others unlock at 3+ recipes each.
- 📋 First 10 articles planned (owner's project doc `meal-prep-site-first-10-articles.md`).

### Site structure (hub and spokes)
- Posts (hubs) link to recipe pages (spokes) via `RecipeList`; recipe pages link back ("Part of") and to related recipes.
- One full recipe per page, so Recipe structured data is unambiguous.
- Category pages unlock automatically as recipes are added (`MIN_RECIPES = 3`).

## 6. Content rules (non-negotiable)

1. **First-hand or nothing.** A recipe isn't published until the owner has cooked it and added real notes.
2. **No lazy AI content.** No mass-produced pages, no templated "[store] + [recipe]" page farms (Google's scaled-content policy).
3. **No placeholder or thin pages.** Only publish pages that are useful on their own.
4. **Prices as approximate ranges** with "checked [month year]" and the store/location basis.
5. **No health claims.** Not medical, dietary or supplement advice.
6. **Images:** own photos preferred. Stock photos only with a visible credit, never presented as our cooking.
7. Every article gets one original element: cost table, protein-per-dollar table, printable list or prep timeline.

## 7. Challenges and risks

| Risk | Mitigation |
|---|---|
| **AI Overviews** answer generic meal-plan queries on the results page | Target long-tail, constraint-based queries; publish things summaries can't replace (cost tables, shopping lists, prep timelines). |
| **Price upkeep** from outside the US | ~30 reused staples, quarterly refresh (~30–45 min). Dates on every page. One data file feeds every page. |
| **Regional price differences** in the US | State the store and location basis; use ranges; avoid cent-exact claims. |
| **Competition** from big recipe publishers on head terms | Write hardest queries last (e.g. "7 day high protein meal prep"); win long-tail first. |
| **Owner's time** (2–3 h/week) | One article per week max; data system does the maths. |
| **Monetisation** | AdSense is not an option (details in private notes). Plan: affiliates and other ad networks once there's traffic. |
| **New-site sandbox** | Expect little or no Search Console data for weeks. Normal. |

## 8. Migration and portability

Everything is plain files, so nothing is locked in.

- **To another host (Netlify, Vercel, GitHub Pages, a VPS):** run `npm run build` and serve the `dist/` folder. Then point DNS at the new host. Keep the same URLs (they're in the sitemap) so rankings carry over.
- **To a Linux VPS (owner's long-term plan to host several projects):** build in CI or on the box, serve `dist/` with Caddy or Nginx, keep Cloudflare in front for DNS/SSL. Remove `wrangler.jsonc` only after the new host is live.
- **Domain transfer away from Cloudflare:** possible after the 60-day lock from registration. Search Console verification is DNS-based, so re-add the TXT record at the new DNS provider *before* switching.
- **If URLs ever change:** add 301 redirects (Cloudflare or a `_redirects`-style rule) from old to new, then resubmit the sitemap.
- **Data:** `data/*.csv` and `data/recipes/*.toml` are tool-agnostic. `mealmath.py` uses only the Python standard library (3.11+).
- **To a new Claude/AI session:** read this file first, then the owner's project docs (niche decision, first-10 plan, setup record, learning log).

## 9. Accounts and access (no secrets here)

| Service | Used for | Notes |
|---|---|---|
| GitHub | Code | Claude GitHub App has push access to this repo only. |
| Cloudflare | Domain + hosting | Cloudflare's GitHub app is scoped to this repo only. |
| Google Search Console | Search data | Domain property, verified via Cloudflare DNS. |
| Cloudflare Worker secrets | `/write` | `WRITER_PASSWORD` and `GITHUB_TOKEN` (fine-grained, this repo only, Contents read/write, **expires Oct 2027**: renew it and re-add the secret). |

## 10. Next steps

1. **Weekly batch (Claude):** "price new recipes": `git pull`, price every `status: unpriced` submission (see
   `submissions/README.md`), push. Then a Search Console check-in (impressions, queries, pages indexed, Recipes report:
   only act if **Invalid > 0**).
2. Owner: only use "Request indexing" for a brand-new or heavily changed page Google hasn't picked up after a few days.
3. Sanae: 2–3 recipes a week via `/write`. Ask for grams where possible and real phone photos.
4. Articles from the 10-article plan, each linking its recipes (hub and spokes).
5. Quarterly: refresh `data/prices.csv`.
6. **More stores (owner wants the big US chains):** Kroger (official free price API), Costco, Sam's Club, Aldi, H-E-B, Target.
   Each needs the ~25 ranked staples + recipe ingredients priced. Then: a `/cheapest-protein` hub comparing stores,
   "cheapest at X" on every recipe, store category pages unlock. Caveats: Costco/Sam's online prices differ from
   warehouse prices and need membership; Aldi online goes through Instacart (marked up) — label the source honestly.
   Next: look & feel
   (warmer palette, recipe prev/next, filter chips). Affiliate links once there's traffic.
7. Recipe schema, decided 16 Oct: **no videos, ever** (the 'video' and step image/video suggestions in Search Console stay
   unfixed on purpose and can't be dismissed). **Star ratings (`aggregateRating`) only once real readers arrive**: add a
   simple 1–5 rating on recipe pages and output it in the schema only when a recipe has real votes. Never invent ratings.
   Revisit when Search Console shows steady clicks.
