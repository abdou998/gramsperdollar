import recipes from '../data/recipes.json';
import plans from '../data/plans.json';

export type Recipe = (typeof recipes)[number];
export type Plan = (typeof plans)[number];

import { DEFAULT_STORE, priceBasis } from './stores';
export { storeInfo, storeLabel, priceBasis, rankUrl, states, stateSlug, allStoreIds, DEFAULT_STORE } from './stores';
/** The store used where a page shows a single price (recipe cards, lists). */
export const STORE = DEFAULT_STORE;
export const PRICE_BASIS = priceBasis(DEFAULT_STORE);

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
  return (r.stores as Record<string, { cost_per_serving: number; protein_g_per_dollar: number | null; prices_checked: string | null; breakdown?: any[] }>)[store];
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
/** Lean = at least half the calories come from protein. */
export function leanness(share: number | null): { key: 'lean' | 'balanced' | 'carbfat'; label: string } {
  if (share == null) return { key: 'balanced', label: '' };
  if (share >= 0.5) return { key: 'lean', label: 'Lean protein' };
  if (share >= 0.25) return { key: 'balanced', label: 'Protein plus fat or carbs' };
  return { key: 'carbfat', label: 'Mostly carbs or fat' };
}

// ---- Store filters (homepage): "All stores", each state with 2+ stores, each store ----
import { states as _states, storeInfo as _info } from './stores';
export type View = { key: string; label: string; ids: string[]; group?: string };
export function storeViews(): View[] {
  const st = _states().map((s) => ({ ...s, ids: s.ids.filter((id) => storeRank(id).length >= 10) })).filter((s) => s.ids.length);
  const all: View = { key: 'all', label: 'All stores', ids: st.flatMap((s) => s.ids) };
  return [all, ...st.flatMap((s) => [
    ...(s.ids.length > 1 ? [{ key: s.slug, label: `All ${s.state} stores`, ids: s.ids, group: s.state }] : []),
    ...s.ids.map((id) => ({ key: id, label: `${_info(id).store}, ${_info(id).city}`, ids: [id], group: s.state })),
  ])];
}
/** Best protein per dollar for each food across the given stores, with the store that has it. */
export function bestFoods(ids: string[]): (RankRow & { store: string })[] {
  const best = new Map<string, RankRow & { store: string }>();
  for (const id of ids) for (const r of storeRank(id)) {
    const cur = best.get(r.item);
    if (!cur || r.protein_per_dollar > cur.protein_per_dollar) best.set(r.item, { ...r, store: id });
  }
  return [...best.values()].sort((a, b) => b.protein_per_dollar - a.protein_per_dollar);
}
/** Each recipe at its best-value store among the given stores (only stores that sell every ingredient). */
export function bestRecipes(ids: string[]) {
  return allRecipes().flatMap((r) => {
    const opts = ids.map((id) => ({ id, s: storeStats(r, id) })).filter((x) => x.s?.protein_g_per_dollar);
    if (!opts.length) return [];
    const b = opts.sort((a, c) => c.s.protein_g_per_dollar! - a.s.protein_g_per_dollar!)[0];
    return [{ r, s: b.s, store: b.id }];
  }).sort((a, b) => b.s.protein_g_per_dollar! - a.s.protein_g_per_dollar!);
}

/** Foods ranked at 2+ of the given stores, with each store's protein per $1, best first.
 *  `winner` is the store id with the most protein per $1, or null on a tie. */
export function compareStores(ids: string[]) {
  const rows = new Map<string, { item: string; name: string; group: string; vals: Record<string, number>; winner: string | null }>();
  for (const id of ids) for (const r of storeRank(id)) {
    if (!rows.has(r.item)) rows.set(r.item, { item: r.item, name: r.name, group: r.group, vals: {}, winner: null });
    rows.get(r.item)!.vals[id] = r.protein_per_dollar;
  }
  const out = [...rows.values()].filter((x) => Object.keys(x.vals).length >= 2);
  for (const row of out) {
    const best = Math.max(...Object.values(row.vals));
    const top = Object.keys(row.vals).filter((k) => row.vals[k] === best);
    row.winner = top.length === 1 ? top[0] : null;
  }
  return out.sort((a, b) => Math.max(...Object.values(b.vals)) - Math.max(...Object.values(a.vals)));
}
/** How many foods each store wins, plus ties. */
export function compareTally(ids: string[]) {
  const rows = compareStores(ids);
  const wins = ids.map((id) => ({ id, n: rows.filter((r) => r.winner === id).length })).sort((a, b) => b.n - a.n);
  return { rows, wins, ties: rows.filter((r) => !r.winner).length };
}
