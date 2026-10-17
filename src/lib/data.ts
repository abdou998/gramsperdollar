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

// ---- Cheapest-protein rankings (built by tools/mealmath.py from data/protein_sources.csv) ----
import rank from '../data/protein_rank.json';
export type RankRow = (typeof rank)[keyof typeof rank][number];
export const rankStores = (): string[] => Object.keys(rank);
export const storeRank = (store: string): RankRow[] => (rank as Record<string, RankRow[]>)[store] ?? [];
export const storeSlug = (store: string) => store.toLowerCase().replace(/\W+/g, '-');
/** Lean = at least half the calories come from protein. */
export function leanness(share: number | null): { key: 'lean' | 'balanced' | 'carbfat'; label: string } {
  if (share == null) return { key: 'balanced', label: '' };
  if (share >= 0.5) return { key: 'lean', label: 'Lean protein' };
  if (share >= 0.25) return { key: 'balanced', label: 'Protein plus fat or carbs' };
  return { key: 'carbfat', label: 'Mostly carbs or fat' };
}
