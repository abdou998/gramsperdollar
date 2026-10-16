# Grams per Dollar — Handover

_Last updated: 15 Oct 2026. This repo is **public**, so nothing private goes in here (accounts,
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

## 5. Current status

- ✅ Site live, Search Console verified, sitemap submitted (first status "Couldn't fetch" — normal for a new property; recheck).
- ✅ Data system working with 3 recipes (Walmart, Oct 2026 prices, Sacramento CA default store):

| Recipe | Protein/serving | Cost/serving | Protein per $ |
|---|---|---|---|
| One-pot spiced chicken, red lentil & rice | 49.7 g | $1.90 | 26.2 g |
| Lemon-rosemary grilled chicken & veg | 48.7 g | $3.72 | 13.1 g |
| 31 g protein pancake | 31.8 g | $2.17 | 14.7 g |

- ✅ **Article #1 live:** `/high-protein-meal-prep-for-one` (3 recipes, 4-day plan, shopping list, prep timeline).
  Written as recipe guidance; it doesn't claim the recipes were kitchen-tested. Add real cooking notes once they're made.
- ✅ **Design system:** Archivo (display) + Source Serif 4 (body), shelf-tag yellow as the one bold element, dark mode, mobile tested.
- 👥 **Second author:** a contributor will write 2–3 posts a week (see `docs/WRITING.md`).
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

## 10. Next steps

1. Owner cooks the one-pot recipe and fills the `[YOUR NOTE]` lines.
2. Write article #1 "High protein meal prep for one person" (pancake breakfast, chicken & veg lunch, one-pot dinner, cost table, shopping list, prep timeline). Build the recipe-table component that reads `src/data/recipes.json`.
3. Recheck the sitemap status in Search Console.
4. Weekly: one article, then a Search Console check-in (impressions, queries, pages indexed).
5. Quarterly: refresh `data/prices.csv`.
6. Later: optional Kroger API for automated prices; affiliate links once there's traffic.
7. Recipe schema, decided 16 Oct: **no videos, ever** (the 'video' suggestions in Search Console stay unfixed on purpose).
   **Star ratings (`aggregateRating`) only once real readers arrive**: add a simple 1–5 rating on recipe pages and output
   it in the schema only when a recipe has real votes. Never invent ratings. Revisit when Search Console shows steady clicks.
