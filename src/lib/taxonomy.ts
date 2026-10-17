// Recipe categories ("facets"). Each one is written to match how people actually search,
// e.g. "30g protein breakfast" or "high protein meals under $2".
//
// SEO rule: a category page is only published once it lists MIN_RECIPES or more recipes and
// isn't identical to the full /recipes list. Thin 1–2 item pages drag the whole site down.
// Pages appear on their own as new recipes are added.
import { allRecipes, storeStats, type Recipe } from './data';
import { storeInfo, slugify, storeSlug } from './stores';

export const MIN_RECIPES = 3;

type Value = { value: string; label: string; title: string; description: string };
type Facet = {
  key: string;          // URL segment: /recipes/{key}/{value}
  name: string;         // shown in filters
  values: (r: Recipe) => Value[];
};

const meals: Record<string, string> = { breakfast: 'Breakfast', lunch: 'Lunch', dinner: 'Dinner', snack: 'Snack' };

export const tagNames: Record<string, string> = {
  'one-pot': 'One-pot', 'freezer-friendly': 'Freezer-friendly', 'no-cook': 'No-cook', 'vegetarian': 'Vegetarian',
  'grilled': 'Grilled', 'low-carb': 'Low-carb', '5-minute': '5-minute', 'single-serve': 'Single-serve',
  'sheet-pan': 'Sheet-pan', 'slow-cooker': 'Slow cooker', 'air-fryer': 'Air fryer',
};
const tagLabel = (t: string) => tagNames[t] ?? t.replace(/-/g, ' ').replace(/^\w/, (c) => c.toUpperCase());

function proteinBand(g: number): Value {
  if (g >= 40) return { value: '40g-plus', label: '40 g+', title: 'High-Protein Meals With 40 g+ Protein', description: 'Meal prep recipes with at least 40 grams of protein a serving, each costed by the gram.' };
  if (g >= 30) return { value: '30g', label: '30–39 g', title: '30 g Protein Meals for Meal Prep', description: 'Recipes with 30 to 39 grams of protein a serving, with cost per serving and protein per dollar.' };
  return { value: '20g', label: '20–29 g', title: '20 g Protein Meals and Snacks', description: 'Recipes with 20 to 29 grams of protein a serving, with cost per serving and protein per dollar.' };
}

function costBand(c: number): Value {
  if (c < 2) return { value: 'under-2-dollars', label: 'Under $2', title: 'High-Protein Meals Under $2 a Serving', description: 'High-protein meal prep recipes that cost less than $2 a serving at the store.' };
  if (c < 3) return { value: 'under-3-dollars', label: '$2–3', title: 'High-Protein Meals for $2 to $3 a Serving', description: 'High-protein meal prep recipes that cost $2 to $3 a serving.' };
  return { value: '3-dollars-plus', label: '$3+', title: 'High-Protein Meals Over $3 a Serving', description: 'Higher-cost high-protein recipes, with protein per dollar so you can compare value.' };
}

export const FACETS: Facet[] = [
  {
    key: 'meal', name: 'Meal',
    values: (r) => r.meal ? [{
      value: r.meal, label: meals[r.meal] ?? r.meal,
      title: `High-Protein ${meals[r.meal] ?? r.meal} Meal Prep Recipes`,
      description: `High-protein ${r.meal} recipes for meal prep, with protein per serving, cost per serving and protein per dollar.`,
    }] : [],
  },
  { key: 'protein', name: 'Protein per serving', values: (r) => [proteinBand(r.protein_g_per_serving)] },
  {
    key: 'cost', name: 'Cost per serving',
    values: (r) => { const s = storeStats(r); return s ? [costBand(s.cost_per_serving)] : []; },
  },
  {
    key: 'store', name: 'Store',
    values: (r) => Object.keys(r.stores).map((id) => {
      const i = storeInfo(id);
      return {
        value: `${storeSlug(id)}-${slugify(i.state)}`, label: `${i.store} (${i.state})`,
        title: `${i.store} High-Protein Meal Prep in ${i.state}`,
        description: `High-protein meal prep recipes priced at ${i.store} in ${i.city}, ${i.market}, with cost per serving and protein per dollar.`,
      };
    }),
  },
  {
    key: 'style', name: 'Style',
    values: (r) => ((r.tags as string[] | undefined) ?? []).map((t) => ({
      value: t, label: tagLabel(t),
      title: `${tagLabel(t)} High-Protein Recipes`,
      description: `${tagLabel(t)} high-protein recipes for meal prep, each with cost per serving and protein per dollar.`,
    })),
  },
];

export type Category = Value & { facet: string; facetName: string; url: string; recipes: Recipe[] };

/** Every category value with its recipes, published or not. */
export function allCategories(): Category[] {
  const map = new Map<string, Category>();
  for (const f of FACETS) {
    for (const r of allRecipes()) {
      for (const v of f.values(r)) {
        const id = `${f.key}/${v.value}`;
        if (!map.has(id)) map.set(id, { ...v, facet: f.key, facetName: f.name, url: `/recipes/${id}`, recipes: [] });
        map.get(id)!.recipes.push(r);
      }
    }
  }
  return [...map.values()];
}

/** Only categories worth their own page: enough recipes, and not the same list as /recipes. */
export function publishedCategories(): Category[] {
  const total = allRecipes().length;
  return allCategories().filter((c) => c.recipes.length >= MIN_RECIPES && c.recipes.length < total);
}

export function categoriesFor(r: Recipe): Category[] {
  return publishedCategories().filter((c) => c.recipes.some((x) => x.slug === r.slug));
}
