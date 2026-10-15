# Submissions

Recipes sent from the private writing page (`gramsperdollar.com/write`) land here, one folder each:

```
submissions/2026-10-20-greek-yogurt-chicken-wraps-a1b2/
  recipe.md      title, meal, style tags, servings, times, intro, ingredients, steps, tips
  photo-1.jpg    main photo (already resized on the phone)
  photo-2.jpg …
```

Each one goes live about a minute after it's sent, at `/recipes/<slug>`, marked **"Not priced yet"**
(no protein, calories or cost shown). `status:` in `recipe.md` controls it:

- `unpriced`: live with the note (default)
- `priced`: hidden here, because the priced recipe in `data/recipes/<slug>.toml` now owns the same URL
- `hidden`: not shown anywhere (use for tests or anything not ready)

## Pricing a submission (keeps the same URL)

1. `git pull` to fetch new submissions.
2. Match each ingredient to `data/nutrition.csv` (USDA values) and `data/prices.csv`. Add any missing rows.
3. Write `data/recipes/<slug>.toml` (same `slug` as in `recipe.md`): copy `meal` and `tags` across, convert amounts to grams,
   keep her wording for steps and tips (tidy typos only).
4. Move the photos to `src/assets/images/<slug>-1.jpg` and set `image`, `image_alt` and `image_credit`.
5. Optional: if she wrote a longer story, it becomes a post in `src/content/posts/` with `recipes: ["<slug>"]`
   and `author:` set to her name.
6. `python tools/mealmath.py --print`, check the numbers look sane, `npm run build`, push.
7. Change `status:` in `recipe.md` to `priced` in the same commit, so the URL swaps over cleanly.

Category pages (breakfast, under $2, one-pot…) unlock on their own once 3 recipes share a category.
