// Stores and states (markets). Every price on the site comes from one named store in one state.
import stores from '../data/stores.json';

export type StoreInfo = { id: string; store: string; market: string; state: string; city: string; location: string; source: string; note: string };
const S = stores as Record<string, StoreInfo>;

export const DEFAULT_STORE = 'walmart-ca';
export const allStoreIds = () => Object.keys(S);
export const storeInfo = (id: string): StoreInfo => S[id];
export const slugify = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
export const stateSlug = (id: string) => slugify(S[id].state);
export const storeSlug = (id: string) => id.replace(/-[a-z]{2}$/, ''); // 'heb-tx' -> 'heb'
/** "Walmart (Houston, TX)" */
export const storeLabel = (id: string) => `${S[id].store} (${S[id].city}, ${S[id].market})`;
/** "Walmart.com prices for the Sacramento Gerber Rd Supercenter (95829), California" */
export const priceBasis = (id: string) => `${S[id].store} prices from ${S[id].source} for ${S[id].location}, ${S[id].state}`;
export const rankUrl = (id: string) => `/cheapest-protein/${stateSlug(id)}/${storeSlug(id)}`;
/** States we have prices for, each with its store ids. */
export function states(): { state: string; slug: string; market: string; ids: string[] }[] {
  const by = new Map<string, { state: string; slug: string; market: string; ids: string[] }>();
  for (const id of allStoreIds()) {
    const s = S[id];
    if (!by.has(s.market)) by.set(s.market, { state: s.state, slug: slugify(s.state), market: s.market, ids: [] });
    by.get(s.market)!.ids.push(id);
  }
  return [...by.values()].sort((a, b) => a.state.localeCompare(b.state));
}
