// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';
import fs from 'node:fs';

// Last-modified dates for the sitemap, so Google knows which pages changed.
// Recipes: their publish date. Posts: updated or published date. Store rankings: the month prices were checked.
const SITE = 'https://gramsperdollar.com';
const lastmod = new Map();
for (const r of JSON.parse(fs.readFileSync('./src/data/recipes.json', 'utf8'))) {
  if (r.published) lastmod.set(`/recipes/${r.slug}`, r.published);
}
for (const f of fs.readdirSync('./src/content/posts').filter((f) => /^[^_].*\.mdx?$/.test(f))) {
  const fm = fs.readFileSync(`./src/content/posts/${f}`, 'utf8').split('---')[1] ?? '';
  const d = (fm.match(/^updated:\s*(\S+)/m) ?? fm.match(/^published:\s*(\S+)/m))?.[1];
  if (d) lastmod.set(`/${f.replace(/\.mdx?$/, '')}`, d);
}
const stores = JSON.parse(fs.readFileSync('./src/data/stores.json', 'utf8'));
const rank = JSON.parse(fs.readFileSync('./src/data/protein_rank.json', 'utf8'));
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
for (const [id, rows] of Object.entries(rank)) {
  const months = rows.map((r) => r.checked).filter(Boolean).sort();
  if (months.length && stores[id]) lastmod.set(`/cheapest-protein/${slug(stores[id].state)}/${id.replace(/-[a-z]{2}$/, '')}`, months.at(-1));
}

// `site` is your live address. Astro uses it for canonical URLs and the sitemap.
export default defineConfig({
  site: SITE,
  trailingSlash: 'never',
  build: { format: 'file' }, // /about instead of /about/ — one clean URL per page
  integrations: [mdx(), sitemap({
    filter: (page) => !page.includes('/write') && !page.includes('/404'),
    serialize(item) {
      const path = new URL(item.url).pathname.replace(/\/$/, '') || '/';
      const d = lastmod.get(path);
      return d ? { ...item, lastmod: d } : item;
    },
  })],
});
