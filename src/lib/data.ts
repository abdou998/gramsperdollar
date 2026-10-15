import recipes from '../data/recipes.json';
import plans from '../data/plans.json';

export type Recipe = (typeof recipes)[number];
export type Plan = (typeof plans)[number];

export const STORE = 'Walmart';
export const PRICE_BASIS = 'Walmart.com prices for Sacramento, CA';

export function getRecipe(slug: string): Recipe {
  const r = recipes.find((x) => x.slug === slug);
  if (!r) throw new Error(`Unknown recipe "${slug}". Add data/recipes/${slug}.toml and run tools/mealmath.py.`);
  return r;
}

export function getPlan(slug: string): Plan {
  const p = plans.find((x) => x.slug === slug);
  if (!p) throw new Error(`Unknown plan "${slug}". Add data/plans/${slug}.toml and run tools/mealmath.py.`);
  return p;
}

export function allRecipes(): Recipe[] {
  return recipes;
}

export function storeStats(r: Recipe, store = STORE) {
  return (r.stores as Record<string, { cost_per_serving: number; protein_g_per_dollar: number | null; prices_checked: string | null }>)[store];
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

/** "2026-10" -> "October 2026" */
export function monthLabel(ym: string | null | undefined): string {
  if (!ym) return '';
  const [y, m] = ym.split('-').map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

export const usd = (n: number) => `$${n.toFixed(2)}`;
export const num = (n: number) => n.toLocaleString('en-US');

export function formatDate(d: Date): string {
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' });
}
