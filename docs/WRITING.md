# Writing a recipe

**The easy way: [gramsperdollar.com/write](https://gramsperdollar.com/write)** (ask Abdessamad for the password).

Fill in the title, tap the meal and anything that fits (one-pot, vegetarian…), add photos, ingredients and steps,
and press **Send recipe**. That's it. Prices, protein and calories get worked out for you before it goes live.
Your writing saves on your phone as you go, so you can stop halfway and come back.

Tips for that page:
- **Title:** what someone would type into Google. "Chicken burrito bowls", not "Tuesday bowls".
- **Ingredients:** one per line, with amounts. Grams are best (500 g chicken breast); cups and spoons are fine.
- **Steps:** one per line, in order.
- **Tell people about it:** a few real sentences. How it tasted, how it kept, what you'd change. This is
  the part Google can't find anywhere else, so it matters most.
- **Photos:** your own phone photos are great. If you use someone else's, say who took them.

---

The rest of this guide is the older, more technical way (editing files on GitHub). You don't need it.

## Writing a full post on GitHub

You don't need to code. You can write straight on GitHub in your browser.

## The quick way (GitHub website)

1. Go to `src/content/posts/` in the repo and open `_template.md`.
2. Copy everything in it.
3. Click **Add file → Create new file**. Name it after the post, all lowercase with dashes:
   `greek-yogurt-chicken-wraps.md`. That name becomes the web address.
4. Paste the template and fill it in. Keep `draft: true` while you're writing.
5. Click **Commit changes**. When it's ready, change `draft: true` to `draft: false` and commit again.
   The site updates itself in about a minute.

Not comfortable with that? Write the post anywhere (Google Docs, Notes, WhatsApp) and send it over.
It can be turned into a page as-is.

## Photos

- Your own photos are best, even from a phone. Shoot from above, near a window, on a clear spot.
- Put them in `src/assets/images/` (Add file → Upload files), then point `hero:` at them.
- Stock photos only with a credit in `heroCredit`, and never described as our food.

## What makes a good post here

- **You actually made it.** Say what happened: the timing, what you changed, how it kept.
- **Protein and cost.** If you want the yellow protein-per-dollar tag and cost table, list the
  ingredients with weights and it gets added to the price data (see `data/README.md`).
- **One clear search phrase** the post answers, used naturally in the title and first paragraph.
  Example: "chicken burrito bowl meal prep", not just "Tuesday dinner".
- **No health claims.** Say what's in it, not what it does to your body. No weight-loss promises.
- **Plain words.** Write like you'd text a friend the recipe.

## Checklist before `draft: false`

- [ ] Title under ~60 characters, with the main phrase in it
- [ ] Description under 155 characters
- [ ] Ingredients have amounts
- [ ] Steps are in order and someone could follow them
- [ ] "Our notes" section is filled in
- [ ] Photo has alt text (and a credit if it isn't yours)
